"""Checkable claims in the lines an agent just wrote into memory (cheap model).

Claims depend only on the line, so each unique line is sent once, ever: a line re-added after a compression or
copied by another agent reuses the stored claims.
"""

from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from typing import Literal

import duckdb
from pydantic import BaseModel, ConfigDict
from rich.progress import track

from heirloom.diff import line_hash
from heirloom.llm import LLM

LINES_PER_CALL = 25
WORKERS = 8

Kind = Literal["exists", "count", "done", "broken", "identity", "plan", "instruction-to-self", "other"]


class Claim(BaseModel):
    model_config = ConfigDict(extra="forbid")
    line: int
    text: str
    kind: Kind
    anchors: list[str]
    subject: str


class ClaimList(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claims: list[Claim]


SYSTEM = """You read lines that an AI agent just wrote into its own long-term memory. The agent lives in the AI \
Village: several AI agents pursue goals together using computers, email and a shared chat, and each one rewrites its \
memory often. Whatever goes into memory is read back later as fact.

List the checkable claims in the lines. A claim is a statement about the world that evidence could confirm or refute: \
something exists, a count or amount, a task is done, something is broken or blocked, who someone is or what they said, \
a plan that contains a specific fact, or an instruction the agent leaves for its future self.

You do not decide whether a claim is true. Only extract.

Rules:
- One claim per fact. A line can hold zero, one or several claims.
- line: the number of the line the claim comes from.
- text: the claim as one short standalone sentence. Keep the agent's own names, numbers and links.
- anchors: the exact tokens from the line that pin the claim down: numbers, amounts, URLs, file / sheet / document \
names, ids, people or agent names, dates and times. Copy each one character for character from the line. Empty list \
if there are none.
- subject: what the claim is about, 2 to 6 words (e.g. "RSVP contact list", "Gmail login", "venue booking").
- kind:
  exists: something exists, was found or was created
  count: a number or amount of something
  done: a task or step is complete, sent or confirmed
  broken: something fails, is blocked, missing or empty
  identity: who someone is, their role or contact, or what they said
  plan: a scheduled or intended action that contains a checkable fact
  instruction-to-self: a note telling a future session what to do or not do, especially to hide, skip, not mention, \
not check, or treat something as settled
  other: checkable, but none of the above
- Skip headings, formatting, lines that only say when the memo was last updated, feelings, and lines with nothing \
checkable."""


def ensure_tables(con: duckdb.DuckDBPyConnection) -> None:
    con.execute("""
        CREATE TABLE IF NOT EXISTS line_claims (
            line_hash VARCHAR, line VARCHAR, claim_no INTEGER, text VARCHAR, kind VARCHAR,
            anchors VARCHAR[], subject VARCHAR, model VARCHAR
        )""")
    # A line that yielded no claims still gets a row (claim_no = -1) so it is never sent again.


def _ask(llm: LLM, agent_name: str, lines: list[str]) -> list[Claim]:
    numbered = "\n".join(f"L{i + 1}: {line}" for i, line in enumerate(lines))
    user = f"Agent: {agent_name}\nLines just written into its memory:\n{numbered}"
    return llm.structured(llm.cheap, SYSTEM, user, ClaimList, effort="low").claims


def extract(con: duckdb.DuckDBPyConnection, llm: LLM, agent_name: str, lines: Iterable[str]) -> int:
    """Extract and store claims for every line not seen before. Returns how many lines were sent."""
    ensure_tables(con)
    unique = list(dict.fromkeys(lines))
    known = {r[0] for r in con.execute(
        "SELECT DISTINCT line_hash FROM line_claims WHERE line_hash IN (SELECT unnest(?))",
        [[line_hash(line) for line in unique]],
    ).fetchall()} if unique else set()
    todo = [line for line in unique if line_hash(line) not in known]
    batches = [todo[i:i + LINES_PER_CALL] for i in range(0, len(todo), LINES_PER_CALL)]

    with ThreadPoolExecutor(WORKERS) as pool:
        results = pool.map(lambda b: (b, _ask(llm, agent_name, b)), batches)
        for batch, claims in track(results, total=len(batches), description=f"  claims · {agent_name}",
                                   transient=True):
            rows = []
            by_line: dict[int, list[Claim]] = {}
            for c in claims:
                if 1 <= c.line <= len(batch):
                    by_line.setdefault(c.line, []).append(c)
            for i, line in enumerate(batch, start=1):
                found = by_line.get(i, [])
                if not found:
                    rows.append((line_hash(line), line, -1, None, None, [], None, llm.cheap))
                for n, c in enumerate(found):
                    rows.append((line_hash(line), line, n, c.text, c.kind, c.anchors, c.subject, llm.cheap))
            con.executemany("INSERT INTO line_claims VALUES (?, ?, ?, ?, ?, ?, ?, ?)", rows)
    return len(todo)
