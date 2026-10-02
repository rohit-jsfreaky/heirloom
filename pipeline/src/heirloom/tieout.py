"""Check one memory line against the evidence in the writer's own window (strong model).

The label comes from the evidence, never from the model's opinion of the world, and every quote is checked against
the row it claims to come from: a quote that is not in its row is dropped, and a label left with no real quote
falls back to no_evidence.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Literal

import duckdb
from pydantic import BaseModel, ConfigDict

from heirloom.diff import anchors as line_anchors
from heirloom.diff import search_terms
from heirloom.llm import LLM
from heirloom.windows import Evidence, evidence

# In 2025 an agent rewrote memory every few seconds, so (k-1, k] can be 14 s wide. What it writes comes from what it
# saw in the last stretch of work, so the window always reaches back at least this far.
MIN_LOOKBACK = timedelta(minutes=30)
ITEM_CHARS = 1_200
TOTAL_CHARS = 45_000

Label = Literal["supported", "contradicted", "hearsay", "no_evidence", "instruction"]


class Quote(BaseModel):
    model_config = ConfigDict(extra="forbid")
    item: str  # "E7"
    quote: str


class Verdict(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: Label
    quotes: list[Quote]
    carrier: str  # item id of the other agent's message the belief came from, or ""
    reason: str


SYSTEM = """You check one line that an AI agent wrote into its own long-term memory. The agent lives in the AI \
Village, where several AI agents work on shared goals with computers, email and a shared chat. You get the line and \
the evidence from the agent's own recent activity: its computer actions and what the tools returned, the chat it \
could see, messages from humans, and its own searches. Each evidence item has an id like E7.

Decide what the evidence shows. Not what you believe about the world.

label:
- supported: a tool output, file content, error message or a human message shows the line is true.
- contradicted: something in the evidence shows the line is false or no longer true: an error, an empty result, \
"does not exist", or a correction from a human or another agent.
- hearsay: the only support is another agent's chat message (not a tool output, not a human). Put that message's id \
in carrier.
- no_evidence: nothing in the evidence speaks to the line either way.
- instruction: the line is a note to the agent's future self; judge it by what it tells the future self to do.

Rules:
- If a "Part to judge" is given, judge only that part of the line; the rest of a long line is context. A line \
whose other parts are true does not support the part to judge.
- Judge the substance of the line: what exists, how many, what is done, broken or true. Differences only in time \
zone, clock format, rounding, spelling or wording are not contradictions.
- Messages marked (this agent) were written by the agent itself. They are its own narration, never evidence.
- quotes: copy each quote exactly, character for character, from one evidence item, with that item's id. Keep each \
under 300 characters. Give 1 to 3 quotes for supported, contradicted and hearsay; none for no_evidence.
- If the evidence both supports and contradicts the line, choose the later one and say so in reason.
- carrier: the id of the other agent's message the line most likely came from, or "" if none.
- reason: one or two plain sentences."""


@dataclass
class TieOut:
    label: str
    reason: str
    quotes: list[tuple[Evidence, str]] = field(default_factory=list)  # (row, verified quote)
    carrier: Evidence | None = None
    window: tuple[datetime, datetime] | None = None
    dropped_quotes: int = 0


def _squash(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def quote_ok(quote: str, row: Evidence | None, agent_name: str) -> bool:
    """A quote counts only if it is really in the row it cites (spacing and case aside) and that row is not the
    agent's own chat message: an agent's narration is never evidence for its own memory."""
    text = quote.strip(" .…\"'")
    if row is None or not text or (row.source == "chat" and row.speaker == agent_name):
        return False
    return _squash(text) in _squash(row.text)


def _excerpt(text: str, keys: list[str]) -> str:
    """Up to ITEM_CHARS of the item, centred on the first anchor it contains."""
    if len(text) <= ITEM_CHARS:
        return text
    low = text.lower()
    hits = [low.find(k) for k in keys if k and low.find(k) >= 0]
    start = max(0, min(hits) - ITEM_CHARS // 3) if hits else 0
    return ("…" if start else "") + text[start:start + ITEM_CHARS] + "…"


def _pick(items: list[Evidence], keys: list[str], agent_name: str) -> list[Evidence]:
    """Items that mention an anchor, humans and other agents first; the rest fill up to TOTAL_CHARS in time order."""
    def rank(e: Evidence) -> int:
        mentions = any(k in e.text.lower() for k in keys)
        if mentions and e.source in ("human", "turn", "search"):
            return 0
        if mentions:
            return 1
        if e.source == "human":
            return 2
        if e.source == "chat" and e.speaker != agent_name:
            return 3
        return 4

    chosen, used = [], 0
    for e in sorted(items, key=lambda e: (rank(e), e.created_at)):
        size = min(len(e.text), ITEM_CHARS)
        if used + size > TOTAL_CHARS:
            continue
        chosen.append(e)
        used += size
    return sorted(chosen, key=lambda e: e.created_at)


def tie_out(con: duckdb.DuckDBPyConnection, llm: LLM, agent_id: str, agent_name: str, line: str,
            window_start: datetime | None, written_at: datetime, model: str | None = None,
            focus: str | None = None) -> TieOut:
    """`focus`: the one claim to judge inside a long line (a trail's belief, a discovered claim)."""
    start = min(window_start or written_at, written_at - MIN_LOOKBACK)
    items = evidence(con, agent_id, start, written_at)
    keys = sorted({t.lower() for a in line_anchors(line) for t in search_terms(a) if len(t) >= 2},
                  key=len, reverse=True)
    shown = _pick(items, keys, agent_name)
    ids = {f"E{i + 1}": e for i, e in enumerate(shown)}

    def describe(e: Evidence) -> str:
        who = "(this agent)" if e.source == "chat" and e.speaker == agent_name else e.speaker
        return f"[{e.created_at:%Y-%m-%d %H:%M:%S}] {e.source} · {who}: {_excerpt(e.text, keys)}"

    body = "\n\n".join(f"{i} {describe(e)}" for i, e in ids.items()) or "(no evidence in this window)"
    part = f"\nPart to judge: {focus}\n" if focus else ""
    user = (f"Agent: {agent_name}\nWritten into memory at {written_at:%Y-%m-%d %H:%M:%S} UTC:\n{line}\n{part}\n"
            f"Evidence from {start:%Y-%m-%d %H:%M:%S} to {written_at:%Y-%m-%d %H:%M:%S} UTC:\n\n{body}")
    verdict = llm.structured(model or llm.cheap, SYSTEM, user, Verdict, effort="medium")

    result = TieOut(label=verdict.label, reason=verdict.reason, window=(start, written_at))
    for q in verdict.quotes:
        row = ids.get(q.item)
        if quote_ok(q.quote, row, agent_name):
            result.quotes.append((row, q.quote))
        else:
            result.dropped_quotes += 1
    result.carrier = ids.get(verdict.carrier)
    if result.label in ("supported", "contradicted", "hearsay") and not result.quotes:
        result.reason = f"[no verifiable quote; model said {result.label}] {result.reason}"
        result.label = "no_evidence"
    return result
