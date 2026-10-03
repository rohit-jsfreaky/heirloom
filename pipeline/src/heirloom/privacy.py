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
# A chat handle that is also an everyday English word ("charity" 4.45, "user" 4.69, "only" 6.1 on wordfreq's zipf
# scale) AND that the agents' own chat mostly writes in lowercase is treated as a word: it is masked only where it is
# clearly a name. Both tests are needed: one handle, a common first name (4.57), is common in English but the chat
# writes it lowercase only 403 times in 2,757, so it stays a name; another is mostly lowercase in chat but no
# everyday word (3.51), so it stays a name too. Privacy wins ties: anything unsure is masked everywhere.
EVERYDAY_WORD_ZIPF = 4.0
WORD_LOWERCASE_SHARE = 0.5


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


def lowercase_share(con: duckdb.DuckDBPyConnection, words: Iterable[str]) -> dict[str, float]:
    """For each word, the share of its uses in the agents' chat written in lowercase. Unknown (no chat table, or the
    word never appears) means absent from the result, which callers treat as a name."""
    words = sorted({w.lower() for w in words})
    if not words:
        return {}
    try:
        rows = con.execute("""
            WITH w AS (SELECT unnest(regexp_extract_all(content, '[A-Za-z]+')) AS t FROM chat_messages)
            SELECT lower(t), count(*) FILTER (WHERE t = lower(t)), count(*) FROM w
            WHERE lower(t) IN (SELECT unnest(?::VARCHAR[])) GROUP BY 1""", [words]).fetchall()
    except duckdb.Error:
        return {}
    return {w: lo / n for w, lo, n in rows if n}


def word_like(con: duckdb.DuckDBPyConnection, handles: Iterable[str]) -> set[str]:
    """The handles that are everyday words in this data (see EVERYDAY_WORD_ZIPF)."""
    common = {h for h in handles if zipf_frequency(h.lower(), "en") >= EVERYDAY_WORD_ZIPF}
    share = lowercase_share(con, common)
    return {h for h in common if share.get(h.lower(), 0.0) >= WORD_LOWERCASE_SHARE}


def _clearly_a_name(words: Iterable[str]) -> re.Pattern | None:
    """Where a word-like handle is clearly a name: right after "@", or as a speaker label ("charity: thanks")."""
    words = sorted(set(words), key=len, reverse=True)
    if not words:
        return None
    alt = "|".join(map(re.escape, words))
    return re.compile(rf"(?<=@)(?:{alt})(?!\w)|(?<![\w@])(?:{alt})(?=\s*:)", re.I)


def _as_written(words: Iterable[str]) -> re.Pattern | None:
    """A word-like handle written the way the handle is (and in capitals): "Harbor", "HARBOR", but not "harbor".
    An all-lowercase handle ("only") can't be told apart from the word, so it is left to _clearly_a_name."""
    named = {w for w in words if w != w.lower()}
    return _pattern(named | {w.upper() for w in named}, ignore_case=False)


class Masker:
    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con
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
        # Privacy wins ties: every handle is masked in any case, except handles that are everyday words in this data
        # ("charity", "user", "only"): those are masked only where they are clearly a name.
        self._words = word_like(con, names)
        self._anycase = _pattern(names - self._words, ignore_case=True)
        self._set_word_patterns()
        self._found: re.Pattern | None = None
        self.name_count = len(names)

    def _set_word_patterns(self) -> None:
        self._clear = _clearly_a_name(self._words)
        self._exact = _as_written(self._words)

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
        # A full name found once ("Dana Whitlock") is written elsewhere by one part alone ("email Dana"): each
        # part is a name too (3 Oct: the model listed only a full name, and the first name alone showed).
        found |= {w for n in found if " " in n for w in re.findall(r"[A-Za-z][A-Za-z'-]+", n)
                  if len(w) >= 3 and w.lower() not in self._agent_words}
        # Names the model found get the same test: an everyday word in this data is masked only where clearly a name.
        found_words = word_like(self._con, found)
        self._found = _pattern(found - found_words, ignore_case=True)  # "Zorvex" also hides "ZORVEX"
        self._words |= found_words
        self._set_word_patterns()
        return sorted(found)

    def __call__(self, text: str | None) -> str | None:
        if not text:
            return text
        text = scrub_secrets(text)
        text = EMAIL.sub("[email]", text)
        text = PHONE.sub("[phone]", text)
        for pattern in (self._found, self._anycase, self._clear, self._exact):
            if pattern:
                text = pattern.sub("[person]", text)
        return text
