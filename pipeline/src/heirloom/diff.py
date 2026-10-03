"""Line diff between two memory snapshots of one agent.

Only lines that are new or changed can carry a newly written belief, so they are the claim candidates. Lines that
vanish are kept too: corrections and forgetting live there.
"""

import functools
import hashlib
import re
from collections import Counter
from dataclasses import dataclass, field

from rapidfuzz import fuzz, process

# A rewrite that keeps less than this share of the old length is a compression.
COMPRESSION_RATIO = 0.7
# Two lines this similar (0-100) are the same line edited, not a new one.
SAME_LINE_SCORE = 60

_BULLET = re.compile(r"^\s*(?:[•●▪◦*+\-–—>]+|\d{1,3}[.)]|[A-Za-z][.)])\s+")
_DIVIDER = re.compile(r"^[\s─━═\-_=*#~·.]*$")
_MARKUP = re.compile(r"\*\*|__|`")
_SPACES = re.compile(r"\s+")

# Anchors are taken in this order, and each match is blanked out before the next pattern runs, so a number inside
# an id ("…-93ad-…") or a URL never becomes a number anchor of its own.
_WHOLE = [
    re.compile(r"https?://\S+"),  # URLs
    re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"),  # emails
    re.compile(r"\b(?=[A-Za-z0-9_-]*\d)(?=[A-Za-z0-9_-]*[A-Za-z])[A-Za-z0-9_-]{12,}\b"),  # ids, hashes, doc keys
]
# Ticket, issue and order numbers ("Issue #846", "order #48213"): strong, written "no.846" so they never clash with
# the "#" that marks weak anchors ("#93", "#5 day"). Not after "&" (HTML entities such as "&#8470;") or a word.
_TICKET = re.compile(r"(?<![\w&#])#(\d{3,})\b")
# Before 3 Oct a ticket was a weak "#48213" (4+ digits only). The v0/v1 evidence checks rank evidence with these
# anchors, so a rebuild shows the checker exactly what it saw then (tieout.py).
_LEGACY_TICKET = re.compile(r"#\d{4,}\b")
_MONTH = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?"
_MODEL = (r"\b(?:Claude|Gemini|GPT|Grok|Kimi|GLM|DeepSeek|Qwen|Llama|Muse|o)[\s-]?\d+(?:\.\d+)?"
          r"(?:[\s-]?(?:Sonnet|Opus|Haiku|Pro|Flash|Lite|mini|Terra|Sol|Luna|Astra|Fable|Spark|V\d[\w.-]*))*"
          r"|\b\d+(?:\.\d+)?\s(?:Sonnet|Opus|Haiku|Pro|Flash)\b"
          r"|\b(?:Sonnet|Opus|Haiku|Fable|Pro|Flash|Gemini|GPT|Grok|Kimi|GLM|DeepSeek|Qwen|Terra|Sol|Luna|Astra)"
          r"[\s-]?V?\d+(?:\.\d+)*\b")
# Times, dates and model names ("Claude 3.7 Sonnet") change or repeat everywhere, so they are never anchors.
_NOISE = re.compile(
    r"\b\d{1,2}:\d{2}(?::\d{2})?(?:\s?[AaPp]\.?[Mm]\.?)?|\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}/\d{1,2}(?:/\d{2,4})?\b"
    rf"|\b\d{{1,2}}(?:st|nd|rd|th)?\s+{_MONTH}(?:\s+\d{{4}})?|{_MONTH}\s+\d{{1,2}}(?:st|nd|rd|th)?\b|\b(?:19|20)\d{{2}}\b"
    rf"|{_MODEL}", re.I)
_MONEY = re.compile(r"[$€£]\s?\d[\d,]*(?:\.\d+)?\s?[kKmM]?\b")
# "8/8 constraints", "40/40 tests" are scores (verification claims); "6/13" is a date and is dropped with the noise.
_FRACTION = re.compile(r"(?<![\w/])(\d{1,4})/(\d{1,4})(?![\w/])(?:\s+([A-Za-z]{3,}))?")
# The unit must end the word: "7fa9a37" (a commit hash) is not "7 fa".
_COUNT = re.compile(r"(?<![\w.#-])(\d[\d,]*(?:\.\d+)?)\s?(?:-\s?)?(%|[A-Za-z]{2,}(?!\w))?(?![\w])")
_QUOTED = re.compile(r"[“\"]([^”\"]{3,80})[”\"]")
_NOT_UNITS = {"and", "or", "to", "of", "the", "at", "in", "on", "for", "by", "am", "pm", "is", "was", "are", "per",
              "from", "with", "x", "vs", "a", "an", "pt", "utc", "et", "min", "mins", "sec", "secs", "h", "hr", "hrs",
              "more", "less", "near", "new", "total", "other", "adding", "added", "confirmed", "additional", "remaining",
              "left", "extra", "each", "out", "up", "down", "again", "times", "than", "into", "after", "before", "so"}
# Units that make a count weak: ordinals, durations and shares change all the time and pin down no fact.
_WEAK_UNITS = {"st", "nd", "rd", "th", "%", "second", "minute", "hour", "day", "week", "month", "year", "time",
               "step", "attempt", "try", "click", "row", "column", "line", "page", "tab", "px", "pixel"}
_AGENT_MAIL = re.compile(r"@agentvillage\.org$")


def _unit(word: str) -> str:
    word = word.lower()
    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"
    if word.endswith("sses"):
        return word[:-2]
    if word.endswith("s") and not word.endswith("ss") and len(word) > 3:
        return word[:-1]
    return word


@functools.lru_cache(maxsize=1_000_000)  # memory lines repeat across thousands of snapshots
def normalize(line: str) -> str:
    """Strip bullets, markdown and spacing; keep numbers, URLs and names exactly as written."""
    line = _BULLET.sub("", line.strip())
    line = _MARKUP.sub("", line).lstrip("#").strip()
    return _SPACES.sub(" ", line)


def lines_of(content: str) -> list[str]:
    out = []
    for raw in content.splitlines():
        if _DIVIDER.match(raw):
            continue
        line = normalize(raw)
        if len(line) >= 3:
            out.append(line)
    return out


_MD_HEADING = re.compile(r"^\s*#{1,6}\s+(.+)$")
_BOLD_HEADING = re.compile(r"^\s*\*\*([^*]{3,80})\*\*:?\s*$")


def _heading(raw: str) -> str | None:
    """A section heading: '## Notes', '**Notes**', 'C. TECH STATUS / BLOCKERS', 'TECHNICAL NOTES:'."""
    if m := _MD_HEADING.match(raw) or _BOLD_HEADING.match(raw):
        return normalize(m.group(1)).rstrip(":")
    text = normalize(raw).rstrip(":")
    letters = [c for c in text if c.isalpha()]
    if text.endswith((".", "!", "?")):  # a shouted sentence, not a heading
        return None
    if 4 <= len(letters) and len(text) <= 80 and sum(c.isupper() for c in letters) / len(letters) > 0.85:
        return text
    return None


def lines_in_context(content: str) -> list[str]:
    """lines_of(), with each line prefixed by the heading it sits under: "[TECHNICAL NOTES] line"."""
    out, section = [], None
    for raw in content.splitlines():
        if _DIVIDER.match(raw):
            continue
        if (h := _heading(raw)) is not None:
            section = h[:60]
            continue
        line = normalize(raw)
        if len(line) >= 3:
            out.append(f"[{section}] {line}" if section else line)
    return out


def body_of(line: str) -> str:
    """The line without its "[SECTION] " prefix (memory lines can start with "[" on their own, e.g. "[x] done")."""
    return line.split("] ", 1)[1] if line.startswith("[") and "] " in line else line


def line_hash(line: str) -> str:
    """Stable id of a normalized line; LLM results are stored per line hash."""
    return hashlib.sha256(line.encode("utf-8")).hexdigest()[:24]


@functools.lru_cache(maxsize=1_000_000)
def anchors(line: str, legacy: bool = False) -> frozenset[str]:
    """The exact things a line pins down: URLs, emails, ids, ticket numbers ("no.846"), money, counts with their unit
    ("93 contact"), quoted names. A bare number with no unit is kept as "#93": weaker, never enough on its own to make
    a line novel."""
    found: set[str] = set()
    text = line

    def take(pattern: re.Pattern, value) -> None:
        nonlocal text
        for m in pattern.finditer(text):
            v = value(m)
            if v:
                found.add(v)
        text = pattern.sub(lambda m: " " * len(m.group(0)), text)

    for pattern in _WHOLE:
        take(pattern, lambda m: m.group(0).rstrip(".,;:)]'\"").lower())
    if legacy:
        take(_LEGACY_TICKET, lambda m: m.group(0).lower())
    else:
        take(_TICKET, lambda m: f"no.{m.group(1)}")

    def quoted(m: re.Match) -> str | None:
        q = m.group(1).strip().lower()
        # One short word in quotes is usually a button or label ("Compose", "Next"), not a fact.
        return q if (" " in q or any(c.isdigit() for c in q) or len(q) >= 10) and any(c.isalnum() for c in q) \
            else None

    take(_QUOTED, quoted)

    def fraction(m: re.Match) -> str | None:
        a, b, word = int(m.group(1)), int(m.group(2)), m.group(3)
        if a != b and b <= 31:
            return None  # a date like 6/13: blanked, never an anchor
        unit = f" {_unit(word)}" if word and word.lower() not in _NOT_UNITS else ""
        return f"{a}/{b}{unit}"

    take(_FRACTION, fraction)
    take(_NOISE, lambda m: None)
    take(_MONEY, lambda m: re.sub(r"\s", "", m.group(0)).lower())

    def count(m: re.Match) -> str | None:
        number, unit = m.group(1).rstrip(".,"), m.group(2)
        if unit and unit.lower() not in _NOT_UNITS:
            u = _unit(unit)
            return f"#{number} {u}" if u in _WEAK_UNITS else f"{number} {u}"
        return f"#{number}" if len(number.replace(",", "")) >= 2 else None

    take(_COUNT, count)
    return frozenset(a for a in found if a)


def strong(anchor: str) -> bool:
    """Weak anchors never mark a line as new on their own: bare numbers and weak counts (prefixed "#") and the
    agents' own village email addresses (infrastructure every agent is given)."""
    return not anchor.startswith("#") and not _AGENT_MAIL.search(anchor)


def search_terms(anchor: str) -> list[str]:
    """What to look for in evidence text: "93 contact" is also found as "93-contact" or just "93"; a ticket number
    "no.846" is looked for as written, "#846"."""
    if anchor.startswith("no."):
        return [f"#{anchor[3:]}"]
    if anchor.startswith("#"):
        return [anchor[1:].split(" ")[0]]
    m = re.match(r"(\d[\d,.]*) (\S+)$", anchor)
    return [anchor, m.group(1)] if m else [anchor]


@dataclass
class Changed:
    old: str
    new: str


@dataclass
class Diff:
    added: list[str] = field(default_factory=list)
    changed: list[Changed] = field(default_factory=list)  # edited line whose anchors changed → a new claim
    reworded: list[Changed] = field(default_factory=list)  # edited line, same anchors → same claim
    vanished: list[str] = field(default_factory=list)
    old_chars: int = 0
    new_chars: int = 0

    @property
    def compression(self) -> bool:
        return self.old_chars > 0 and self.new_chars < COMPRESSION_RATIO * self.old_chars

    @property
    def candidates(self) -> list[str]:
        """Lines that may carry a newly written belief."""
        return self.added + [c.new for c in self.changed]

    def __bool__(self) -> bool:
        return bool(self.added or self.changed or self.reworded or self.vanished)


def diff(old: str | None, new: str) -> Diff:
    old_lines, new_lines = lines_of(old or ""), lines_of(new)
    # Multiset difference: a line repeated in both counts as kept as many times as it appears in both.
    removed = list((Counter(old_lines) - Counter(new_lines)).elements())
    added = list((Counter(new_lines) - Counter(old_lines)).elements())

    result = Diff(old_chars=len(old or ""), new_chars=len(new))
    pool = list(dict.fromkeys(removed))
    for line in added:
        match = process.extractOne(line, pool, scorer=fuzz.ratio, score_cutoff=SAME_LINE_SCORE) if pool else None
        if match is None:
            result.added.append(line)
            continue
        old_line = match[0]
        pool.remove(old_line)
        pair = Changed(old=old_line, new=line)
        (result.reworded if anchors(old_line) == anchors(line) else result.changed).append(pair)
    paired = {c.old for c in result.changed + result.reworded}
    result.vanished = [line for line in removed if line not in paired]
    return result
