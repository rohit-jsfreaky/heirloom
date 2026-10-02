"""Where a memory line stands on one belief (cheap model).

The trail never asks the model whether a belief is true. It only asks what each line says about it; the presence
scan over snapshots and the tie-out against evidence do the rest.
"""

import hashlib
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from typing import Literal

import duckdb
from pydantic import BaseModel, ConfigDict
from rich.progress import track

from heirloom.diff import line_hash
from heirloom.llm import LLM

LINES_PER_CALL = 30
WORKERS = 8

StanceLabel = Literal["affirms", "doubts", "denies", "unrelated"]


class LineStance(BaseModel):
    model_config = ConfigDict(extra="forbid")
    line: int
    stance: StanceLabel
    why: str


class StanceList(BaseModel):
    model_config = ConfigDict(extra="forbid")
    lines: list[LineStance]


SYSTEM = """You read lines from the long-term memory of AI agents in the AI Village (several AI agents working on \
shared goals). You get one belief and a numbered list of memory lines. For each line, say where it stands on the \
belief. Do not judge whether the belief is true; only read what the line says or takes for granted.

A line may start with [SECTION], the heading it sits under in the agent's memory. Use it as context: the same line \
under "MISTAKES TO AVOID" or "CORRECTED" means something different than under "CURRENT STATUS".

stance:
- affirms: the line states the belief or takes it for granted as current fact: it uses the thing, plans to use it, \
demands or expects its contents, or reports its size, contents or location as real and available.
- doubts: the line treats the thing as real but in trouble: missing, empty, deleted, lost, inaccessible, \
unconfirmed, "alleged", "could not locate"; or it describes searching for it or trying to recover it.
- denies: the line says the belief is false: it never existed, was a hallucination, fiction or placeholders, or \
was corrected. Hedged versions ("may never have existed", "may have been hallucinated") are denies too.
- unrelated: the line is about something else. This includes a new replacement made later (a new list, sheet, \
booking or plan built from scratch) unless the line also says something about the original; and lines that only \
name a file or label containing a matching word or number without saying whether the thing itself exists.

A line that both repeats the belief and denies it is denies. A line that only reports what someone else said \
takes that person's stance unless the line itself disagrees. A failure that still assumes the thing is real \
("the email went to 3 people instead of the 40-person list") affirms or doubts; it never denies.

Worked example. Belief: "The team has a confirmed booking for the Oakland hall on 14 June."
- "Oakland hall booked for 14 Jun, deposit paid" → affirms
- "Send directions to the Oakland hall to all guests" → affirms
- "Oakland hall booking not showing in the venue portal; asked Sam to check" → doubts
- "Find the Oakland booking confirmation email again" → doubts
- "Started a new venue shortlist because the Oakland booking fell through" → doubts
- "Added 3 venues to the new shortlist sheet" → unrelated
- "The hall says there was never a booking for 14 Jun" → denies
- "Oakland booking may have been a hallucination" → denies
- "[MISTAKES TO AVOID] Oakland hall booked for 14 Jun" → denies
- "Draft: Oakland-hall-14Jun.docx" → unrelated
- "Bought 14 chairs for the garden party" → unrelated

why: at most 12 words, quoting the deciding words from the line.
Answer for every line number."""


def belief_key(statement: str) -> str:
    return hashlib.sha256(statement.encode("utf-8")).hexdigest()[:16]


def ensure_tables(con: duckdb.DuckDBPyConnection) -> None:
    con.execute("""
        CREATE TABLE IF NOT EXISTS line_stance (
            belief_key VARCHAR, line_hash VARCHAR, line VARCHAR, stance VARCHAR, why VARCHAR, model VARCHAR
        )""")


def labels(con: duckdb.DuckDBPyConnection, llm: LLM, statement: str) -> tuple[dict[str, str], set[str]]:
    """Current label per line hash: the cheap model's, overridden wherever the strong model re-checked the line.
    Also returns the set of hashes the strong model has checked."""
    ensure_tables(con)
    key = belief_key(SYSTEM + statement)
    cheap = dict(con.execute("SELECT line_hash, stance FROM line_stance WHERE belief_key = ? AND model = ?",
                             [key, llm.cheap]).fetchall())
    strong = dict(con.execute("SELECT line_hash, stance FROM line_stance WHERE belief_key = ? AND model = ?",
                              [key, llm.strong]).fetchall())
    return cheap | strong, set(strong)


def classify(con: duckdb.DuckDBPyConnection, llm: LLM, statement: str, lines: Iterable[str],
             model: str) -> dict[str, str]:
    """Label every line not yet labelled by `model`; returns {line_hash: stance} from that model.

    The cheap model labels everything; the strong model only re-checks the few lines that decide a trail's key
    moments (see trail.build). Blind test on the 93 case, 2 Oct: Gemini 3.8 Flash 44/51 disputed lines,
    GPT-6 Luna 34/51, Sonnet 5.5 39/51.
    """
    ensure_tables(con)
    key = belief_key(SYSTEM + statement)  # a new prompt or statement starts a fresh set of labels
    unique = list(dict.fromkeys(lines))
    known = dict(con.execute(
        "SELECT line_hash, stance FROM line_stance WHERE belief_key = ? AND model = ?", [key, model]
    ).fetchall())
    todo = [line for line in unique if line_hash(line) not in known]
    batches = [todo[i:i + LINES_PER_CALL] for i in range(0, len(todo), LINES_PER_CALL)]

    def ask(batch: list[str]) -> tuple[list[str], list[LineStance]]:
        numbered = "\n".join(f"L{i + 1}: {line}" for i, line in enumerate(batch))
        user = f"Belief: {statement}\n\nMemory lines:\n{numbered}"
        return batch, llm.structured(model, SYSTEM, user, StanceList, effort="low").lines

    with ThreadPoolExecutor(WORKERS) as pool:
        for batch, answers in track(pool.map(ask, batches), total=len(batches), description="  stance",
                                    transient=True):
            by_line = {a.line: a for a in answers if 1 <= a.line <= len(batch)}
            rows = []
            for i, line in enumerate(batch, start=1):
                a = by_line.get(i)
                # A line the model skipped stays unclassified and is retried on the next run.
                if a is None:
                    continue
                rows.append((key, line_hash(line), line, a.stance, a.why, model))
                known[line_hash(line)] = a.stance
            if rows:
                con.executemany("INSERT INTO line_stance VALUES (?, ?, ?, ?, ?, ?)", rows)
    return {line_hash(line): known[line_hash(line)] for line in unique if line_hash(line) in known}
