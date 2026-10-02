"""Mask people before anything is shown or written out. Agents keep their names; humans don't.

Masked: emails, phone numbers, every human chat name the export records (USER_TALK speakers, USER_NAME_CHANGE
names), and any other real person the cheap model finds in the output strings (it only lists names; the code does
the replacing, so quotes stay exact). Applied to output only: evidence quotes are verified against raw rows first.
"""

import re
from collections.abc import Iterable

import duckdb
from pydantic import BaseModel, ConfigDict
from wordfreq import zipf_frequency

from heirloom.llm import LLM

EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
# Credentials the export's own scrub missed (found 2 Oct: a stored password in o3's 2025 memory). Never used, never
# sent to a model, never written out; reported to the hosts.
_SECRET_AFTER_WORD = re.compile(  # (?<!\[): never re-match our own "[secret]", so masking twice changes nothing
    r"(?i)(?<!\[)\b(password|passcode|passwd|pwd|credential|secret|api[ _-]?key|access[ _-]?token|token)s?\b"
    r"([^\n\"“”']{0,25}?)([\"“'])([^\"”'\n]{4,})([\"”'])")
_SECRET_SHAPE = re.compile(r"(?<![\w/@.])(?=[^\s\"”'/]*[A-Za-z])(?=[^\s\"”'/]*\d)(?=[^\s\"”'/]*[!#$^&*])"
                           r"[^\s\"”'/@]{8,}")


def scrub_secrets(text: str) -> str:
    text = _SECRET_AFTER_WORD.sub(lambda m: f"{m.group(1)}{m.group(2)}{m.group(3)}[secret]{m.group(5)}", text)
    return _SECRET_SHAPE.sub("[secret]", text)
PHONE = re.compile(r"(?<![\w-])(?:\+\d{1,3}[\s.-]?)?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}(?![\w-])")
# Zipf word frequency (wordfreq, English) at or above which a chat handle is an everyday word ("only" 6.1,
# "test" 5.2, "blue" 5.1) rather than a name.
EVERYDAY_WORD_ZIPF = 5.0


class People(BaseModel):
    model_config = ConfigDict(extra="forbid")
    names: list[str]


FIND_PEOPLE = """List every real human person's name or username that appears in the text: chat users, staff, \
helpers, contacts, performers, journalists, anyone. Include names written in capitals or used inside labels and \
headings (e.g. "JOHN BOUNCE", "MC: PRIYA", "@sam_k"), first names alone, and surnames alone. Copy each exactly as \
written. Do not list AI agents or models (the agent names are given), companies, products, places or projects. \
Return an empty list if there are none."""


def _pattern(words: Iterable[str], ignore_case: bool) -> re.Pattern | None:
    words = sorted(set(words), key=len, reverse=True)
    if not words:
        return None
    return re.compile(r"(?<!\w)(?:" + "|".join(map(re.escape, words)) + r")(?!\w)", re.I if ignore_case else 0)


class Masker:
    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self.agents = [r[0] for r in con.execute("SELECT name FROM agents").fetchall()]
        # Never mask an agent name or any word of one ("Opus", "Sonnet", "Gemini"), even if a viewer used it.
        agents = {a.lower() for a in self.agents} | {w.lower() for a in self.agents for w in re.findall(r"\w+", a)}
        self._agent_words = agents
        names = {r[0] for r in con.execute("""
            SELECT DISTINCT trim(n) FROM (
                SELECT data->>'speakerName' AS n FROM events WHERE action_type = 'USER_TALK'
                UNION ALL SELECT data->>'newName' FROM events WHERE action_type = 'USER_NAME_CHANGE'
                UNION ALL SELECT data->>'oldName' FROM events WHERE action_type = 'USER_NAME_CHANGE')
            WHERE n IS NOT NULL AND length(trim(n)) >= 3""").fetchall()}
        names = {n for n in names if n.lower() not in agents and re.search(r"[A-Za-z]{2}", n)}
        # Privacy wins ties: every handle is masked in any case, except true everyday words ("only", "test", "blue"),
        # which are masked only in the handle's own capitalisation. Common first names ("[person]" 4.57, "[person]" 4.78)
        # sit below the cut and are always masked.
        common = {n for n in names if zipf_frequency(n.lower(), "en") >= EVERYDAY_WORD_ZIPF}
        self._anycase = _pattern(names - common, ignore_case=True)
        # An all-lowercase handle that is also an everyday word ("only") can't be told apart from the word itself.
        self._exact = _pattern({n for n in common if n != n.lower()}, ignore_case=False)
        self._found: re.Pattern | None = None
        self.name_count = len(names)

    def add_people(self, llm: LLM, texts: Iterable[str]) -> list[str]:
        """Ask the cheap model which people the output names; mask those too. Returns the names it found."""
        texts = [t for t in dict.fromkeys(texts) if t]
        found: set[str] = set()
        for i in range(0, len(texts), 40):
            chunk = "\n".join(f"- {t}" for t in texts[i:i + 40])
            user = f"AI agent names (do not list): {', '.join(self.agents)}\n\nText:\n{chunk}"
            names = llm.structured(llm.cheap, FIND_PEOPLE, user, People, effort="low").names
            found |= {n.strip() for n in names
                      if len(n.strip()) >= 2 and n.strip().lower() not in self._agent_words}
        self._found = _pattern(found, ignore_case=True)  # "[person]" also hides "[person]"
        return sorted(found)

    def __call__(self, text: str | None) -> str | None:
        if not text:
            return text
        text = scrub_secrets(text)
        text = EMAIL.sub("[email]", text)
        text = PHONE.sub("[phone]", text)
        for pattern in (self._found, self._anycase, self._exact):
            if pattern:
                text = pattern.sub("[person]", text)
        return text
