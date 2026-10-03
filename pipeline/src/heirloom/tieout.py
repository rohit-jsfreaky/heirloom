"""Check one memory line against the evidence in the writer's own window.

The label comes from the evidence, never from the model's opinion of the world, and every quote is checked against
the row it claims to come from: a quote that is not in its row is dropped, and a label left with no real quote
falls back to no_evidence.

Three checkers, so that a rebuild reproduces exactly what was shipped (docs/AUDIT.md):
- v0 (2 Oct, before "Part to judge" existed): the 2025 trails, belief-88f4b90fcf and the `alive` sweep's birth checks.
- v1 (2 Oct afternoon on): judges the "Part to judge" (the trail's belief) inside the line. The 2026 trails.
- v2 (opt-in, `heirloom trail --checker v2`): one definition shared with the blind audit (judge the belief as the line
  asserts it; the line is a COPY or a CORRECTION), worked examples, evidence ranked by the belief, the agent's own
  summaries counted as narration, quotes matched without markdown or escaping, the strong model. Tested 3 Oct: 9 of
  15 held-out audited items, the same as v1, so not shipped.
v0 and v1 rank evidence with the anchors as they were then (ticket numbers not yet strong anchors). A rebuild with
them reproduces every shipped evidence check from the cache at $0.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Literal

import duckdb
from pydantic import BaseModel, ConfigDict, create_model

from heirloom.diff import anchors as line_anchors
from heirloom.diff import search_terms, strong
from heirloom.llm import LLM
from heirloom.windows import Evidence, evidence

# In 2025 an agent rewrote memory every few seconds, so (k-1, k] can be 14 s wide. What it writes comes from what it
# saw in the last stretch of work, so the window always reaches back at least this far.
MIN_LOOKBACK = timedelta(minutes=30)
ITEM_CHARS = 1_200
TOTAL_CHARS = 45_000
CHECKERS = ("v0", "v1", "v2")
# v2: 24k characters of evidence and low reasoning effort keep a Gemini 3.8 Flash check near $0.009.
V2_TOTAL_CHARS = 24_000
V2_EFFORT = "low"

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


# v2 has no "instruction" label (plan lines are excluded upstream). Same schema name, so its cached calls still match.
VerdictV2 = create_model("Verdict", __config__=ConfigDict(extra="forbid"),
                         label=(Literal["supported", "contradicted", "hearsay", "no_evidence"], ...),
                         quotes=(list[Quote], ...), carrier=(str, ...), reason=(str, ...))


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

_PART_RULE = ("- If a \"Part to judge\" is given, judge only that part of the line; the rest of a long line is "
              "context. A line whose other parts are true does not support the part to judge.\n")
SYSTEM_V0 = SYSTEM.replace(_PART_RULE, "")  # the prompt before "Part to judge" existed (checked against the cache)

SYSTEM_V2 = """You check one line that an AI agent wrote into its own long-term memory, against the evidence in that \
agent's own window. The agent lives in the AI Village, where AI agents work on shared goals with computers, email and \
a shared chat. Each evidence item has an id like E7.

WHAT TO JUDGE. The belief (given as "Belief"), as this line asserts it, using only the evidence listed: what the \
agent's window held up to the moment the line was written. Not what you believe about the world, and nothing later.
The line is one of two kinds (given as "The line is a ..."):
- COPY: it states the belief or takes it for granted. The claim is the belief.
- CORRECTION: it says the belief is false. The claim is that the belief is false.
Judge the claim. If the line says other things too, they are context only.

label:
- supported: the window shows the claim is true first hand: a tool output (including text a tool read from the \
screen), a file, an error message, or a human's message.
- contradicted: the window shows the claim is false: a tool output, an error, an empty result, a human, or another \
agent's first-hand report of what it just did or saw.
- hearsay: the only support for the claim is another agent's chat message saying so (a claim, not something the \
window shows). Several agents repeating it is still hearsay. Put the message's id in carrier.
- no_evidence: nothing in the window speaks to the claim either way.

Rules:
- Messages marked (this agent) are the agent's own narration. They are never evidence, for or against.
- Judge the substance: what exists, how many, what is done, broken or true. Time zones, clock formats, rounding and \
wording are not contradictions.
- If the window both backs and contradicts the claim: a first-hand item (tool output, human, an agent describing its \
own action) beats another agent's bare claim; otherwise the later item wins. Say which in reason.
- quotes: copy each quote exactly, character for character, from one evidence item, with that item's id; under 300 \
characters; 1 to 3 quotes for supported, contradicted and hearsay; none for no_evidence.
- carrier: for hearsay, the id of the other agent's message the claim most likely came from (the latest before the \
line); otherwise "".
- reason: one or two plain sentences.

Worked examples (real rows, shortened):
1. COPY. Belief: DeepSeek-V3.2 posted its ForwardDiff.jl contribution to GitHub Issue #846. Line: "DeepSeek-V3.2 \
executed release window at 1:00 PM PT on JuliaDiff/ForwardDiff.jl Issue #846". Evidence: E1 chat · DeepSeek-V3.2: \
"...to Julia (ForwardDiff.jl) beginning. ... Issue #846: https://github.com/JuliaDiff/ForwardDiff.jl/issues/846". \
-> hearsay, carrier E1: only DeepSeek's own message says it; nothing in the window shows the post.
2. COPY. Belief: the verification bundle is committed at commit a8e7d3f9... Line: "DeepSeek-V3.2 completed a \
17-document verification bundle under ai-village-agents/village/platform-verification-bundle (Commit: a8e7d3f9...)". \
Evidence: E1 chat · DeepSeek-V3.2: "GitLab Repository Created: .../platform-verification-bundle - will populate with \
all 17 verification documents." -> contradicted: the bundle's own author reports first hand that the repository was \
only just created and is still to be filled.
3. COPY. Belief: the agents have an original list of 87-93 real contacts. Line: "87 contacts in the 'RESONANCE \
Mailing List' Google Sheet". Evidence: E1 chat · Gemini 2.5 Pro (19:37): "I've successfully created a Google Sheet \
named 'RESONANCE Mailing List' ... ready to populate"; E2 chat · o3 (19:48): "87 contacts in the 'RESONANCE Mailing \
List' Google Sheet". -> contradicted: the agent that made the sheet reports first hand it is new and empty; o3's \
later message is only a claim.
4. COPY, written by the agent the belief is about. Line by DeepSeek-V3.2: "Active engagements: 2 -> 3 (PyTensor PR \
#2406, Issue #2387, ForwardDiff.jl Issue #846)". Evidence: E1 turn · tool: "=== FINAL FORWARDDIFF.JL CONTRIBUTION \
REVIEW === ... Checking final GitHub-ready version". -> contradicted: its own tool output shows the contribution still \
being prepared, not posted.
5. COPY. Belief: MuninnAI's public presence has been verified (a verified X account, a GitHub organization...). \
Line: "External Engagement: MuninnAI tracked (40 views, 1 like, 0 replies)". Evidence: chat about tweet metrics only. \
-> no_evidence: nothing in the window speaks to MuninnAI's presence being verified.
6. CORRECTION. Belief: the agents have an original list of 93 real contacts. Line: "The 'RESONANCE-Mailing-List-\
Export-93' spreadsheet is empty (headers only), or never contained data." Evidence: E1 human: "I see the Google Sheet \
and see that there are no addresses in the version history, I'm not sure there ever were any?" -> supported: a \
human backs the correction.
7. CORRECTION. Belief: DeepSeek-V3.2 posted to Issue #846. Line: "Opus 4.8 independently verified ... ForwardDiff \
#846 comments NEVER LANDED". Evidence: E1 chat · Claude Opus 4.8: "I independently checked your three GitHub threads \
via the public API ... no comment from your account". -> hearsay, carrier E1: the correction rests on another \
agent's message; that agent's check is not in this window.
8. CORRECTION, the agent's own check. Line by Claude Opus 4.8: "via public GitHub API found ... ForwardDiff.jl #846 \
- 1 comment from opener ... no DeepSeek comment". Evidence: E1 turn · tool: action curl \
"https://api.github.com/repos/JuliaDiff/ForwardDiff.jl/issues/846/comments", output listing the comment authors. \
-> supported: the agent's own tool output backs the correction."""


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


_ESCAPES = [("\\n", " "), ("\\t", " "), ('\\"', '"'), ("\\'", "'")]
_MARKDOWN = re.compile(r"\*\*|__|`")
_TYPOGRAPHY = str.maketrans({"“": '"', "”": '"', "‘": "'", "’": "'", "–": "-", "—": "-"})


def comparable(text: str) -> str:
    """Text reduced to what a quote has to match (v2): escaped newlines and quotes as in raw tool output, markdown
    markers, typographic quotes and dashes dropped; spacing and case aside. Models quote what a row says, not its
    escaping or bold markers (3 Oct: three correct v2 verdicts were rejected for exactly this)."""
    for a, b in _ESCAPES:
        text = text.replace(a, b)
    return _squash(_MARKDOWN.sub("", text.translate(_TYPOGRAPHY)))


def own_narration(row: Evidence, agent_name: str, summaries: bool = True) -> bool:
    """The agent's own words: its chat messages, and (v2) its session summaries and consolidation notes."""
    own_chat = row.source == "chat" and row.speaker == agent_name
    return own_chat or (summaries and row.source in ("session_summary", "consolidate"))


def quote_ok(quote: str, row: Evidence | None, agent_name: str, v2: bool = False) -> bool:
    """A quote counts only if it is really in the row it cites (spacing and case aside; v2 also markdown and escaping)
    and that row is not the agent's own narration: an agent's own words are never evidence for its own memory.
    v0/v1 keep the strict match: the lenient one would change 6 of the 100 birth labels of the shipped `alive` run."""
    text = quote.strip(" .…\"'")
    if row is None or not text or own_narration(row, agent_name, summaries=v2):
        return False
    if v2:
        return comparable(text) in comparable(row.text)
    return _squash(text) in _squash(row.text)


def _excerpt(text: str, keys: list[str], belief: re.Pattern | None = None) -> str:
    """Up to ITEM_CHARS of the item, centred on where it mentions the belief (v2), else on the first anchor."""
    if len(text) <= ITEM_CHARS:
        return text
    m = belief.search(text) if belief else None
    low = text.lower()
    hits = [m.start()] if m else [low.find(k) for k in keys if k and low.find(k) >= 0]
    start = max(0, min(hits) - ITEM_CHARS // 3) if hits else 0
    return ("…" if start else "") + text[start:start + ITEM_CHARS] + "…"


def _pick(items: list[Evidence], keys: list[str], agent_name: str) -> list[Evidence]:
    """v0/v1: items that mention an anchor, humans and other agents first; the rest fill up to TOTAL_CHARS in time
    order."""
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

    return _fill(items, rank, TOTAL_CHARS)


def _pick_v2(items: list[Evidence], keys: list[str], strong_keys: list[str], agent_name: str,
             belief: re.Pattern | None) -> list[Evidence]:
    """v2: items about the belief (its pattern or the line's strong anchors) from tools, searches and humans first;
    the same from other agents' chat; then items matching only a bare number from the line; humans; other agents; the
    rest. A bare number ("17", "94%") is everywhere in tool output, so it must not outrank the belief itself."""
    def rank(e: Evidence) -> int:
        low = e.text.lower()
        about = bool(belief and belief.search(e.text)) or any(k in low for k in strong_keys)
        own = own_narration(e, agent_name)
        if about and e.source in ("human", "turn", "search"):
            return 0
        if about and not own:
            return 1
        if any(k in low for k in keys) and e.source in ("human", "turn", "search"):
            return 2
        if e.source == "human":
            return 3
        if e.source == "chat" and not own:
            return 4
        return 5

    return _fill(items, rank, V2_TOTAL_CHARS)


def _fill(items: list[Evidence], rank, budget: int) -> list[Evidence]:
    chosen, used = [], 0
    for e in sorted(items, key=lambda e: (rank(e), e.created_at)):
        size = min(len(e.text), ITEM_CHARS)
        if used + size > budget:
            continue
        chosen.append(e)
        used += size
    return sorted(chosen, key=lambda e: e.created_at)


def tie_out(con: duckdb.DuckDBPyConnection, llm: LLM, agent_id: str, agent_name: str, line: str,
            window_start: datetime | None, written_at: datetime, model: str | None = None,
            focus: str | None = None, checker: str = "v1", role: str = "copy",
            belief_pattern: str | None = None) -> TieOut:
    """`focus`: the belief to judge (a trail's statement, a discovered claim; v0 ignores it). v2 only: `role`, "copy"
    (the line asserts the belief) or "correction" (the line says it is false), and `belief_pattern`, the trail's regex,
    to find evidence about the belief that the line's own anchors miss."""
    if checker not in CHECKERS:
        raise ValueError(f"checker must be one of {', '.join(CHECKERS)}")
    v2 = checker == "v2"
    start = min(window_start or written_at, written_at - MIN_LOOKBACK)
    items = evidence(con, agent_id, start, written_at)
    found = line_anchors(line) if v2 else line_anchors(line, legacy=True)
    keys = sorted({t.lower() for a in found for t in search_terms(a) if len(t) >= 2}, key=len, reverse=True)
    belief = re.compile(belief_pattern, re.I) if v2 and belief_pattern else None
    if v2:
        strong_keys = sorted({t.lower() for a in found if strong(a) for t in search_terms(a)[:1] if len(t) >= 2},
                             key=len, reverse=True)
        shown = _pick_v2(items, keys, strong_keys, agent_name, belief)
    else:
        shown = _pick(items, keys, agent_name)
    ids = {f"E{i + 1}": e for i, e in enumerate(shown)}

    def describe(e: Evidence) -> str:
        who = "(this agent)" if own_narration(e, agent_name, summaries=v2) else e.speaker
        return f"[{e.created_at:%Y-%m-%d %H:%M:%S}] {e.source} · {who}: {_excerpt(e.text, keys, belief)}"

    body = "\n\n".join(f"{i} {describe(e)}" for i, e in ids.items()) or "(no evidence in this window)"
    if v2:
        kind = "CORRECTION" if role == "correction" else "COPY"
        belief_line = f"Belief: {focus}\n" if focus else ""
        user = (f"Agent: {agent_name}\nThe line is a {kind}.\n{belief_line}"
                f"Written into memory at {written_at:%Y-%m-%d %H:%M:%S} UTC:\n{line}\n\n"
                f"Evidence from {start:%Y-%m-%d %H:%M:%S} to {written_at:%Y-%m-%d %H:%M:%S} UTC:\n\n{body}")
        verdict = llm.structured(model or llm.strong, SYSTEM_V2, user, VerdictV2, effort=V2_EFFORT)
    else:
        part = f"\nPart to judge: {focus}\n" if focus and checker == "v1" else ""
        user = (f"Agent: {agent_name}\nWritten into memory at {written_at:%Y-%m-%d %H:%M:%S} UTC:\n{line}\n{part}\n"
                f"Evidence from {start:%Y-%m-%d %H:%M:%S} to {written_at:%Y-%m-%d %H:%M:%S} UTC:\n\n{body}")
        system = SYSTEM if checker == "v1" else SYSTEM_V0
        verdict = llm.structured(model or llm.cheap, system, user, Verdict, effort="medium")

    result = TieOut(label=verdict.label, reason=verdict.reason, window=(start, written_at))
    for q in verdict.quotes:
        row = ids.get(q.item)
        if quote_ok(q.quote, row, agent_name, v2=v2):
            result.quotes.append((row, q.quote))
        else:
            result.dropped_quotes += 1
    result.carrier = ids.get(verdict.carrier)
    if result.label in ("supported", "contradicted", "hearsay") and not result.quotes:
        result.reason = f"[no verifiable quote; model said {result.label}] {result.reason}"
        result.label = "no_evidence"
    return result
