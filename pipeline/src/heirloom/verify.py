"""`heirloom verify`: re-check every saved result before anyone reads it.

Without the database: the facts file is current, every number marked in the docs matches it, every trail is
internally consistent (links, time order, statuses), and no run file holds an email, phone number or credential.
With the database: every evidence quote and every memory or chat line in every run is found again in the raw row it
cites (masked spans may stand for anything).
"""

import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from heirloom import facts
from heirloom.config import ROOT
from heirloom.diff import lines_in_context, normalize
from heirloom.lifecycle import ANALYSIS
from heirloom.privacy import EMAIL, PHONE, scrub_secrets
from heirloom.tieout import comparable
from heirloom.trail import RUNS, _KEEP
from heirloom.village import village_link

# Numbers in the docs carry a hidden marker naming the fact they come from: 50<!--f:monitor_2026.copies-->
MARKER = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s*%?\**\s*<!--\s*f:([\w.]+)\s*-->")
DOCS = [ROOT / "README.md", *sorted((ROOT / "docs").glob("*.md")), ROOT / "pipeline" / "README.md"]
MASKED = re.compile(r"\[(?:person|email|phone|secret)\]")
QUOTE_STRIP = " .…\"'"
OUR_LINKS = "https://theaidigest.org/village?date="  # our own replay links: "&time=" looks like a credential


@dataclass
class Check:
    name: str
    ok: int = 0
    failures: list[str] = field(default_factory=list)

    def test(self, cond: bool, what: str) -> None:
        if cond:
            self.ok += 1
        else:
            self.failures.append(what)

    @property
    def passed(self) -> bool:
        return not self.failures


def _squash(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def found_in(masked: str, raw: str) -> bool:
    """`masked` (a quote or line as saved, after masking) occurs in `raw`; each masked span stands for 1-300 chars."""
    parts = [re.escape(comparable(p)) for p in MASKED.split(masked)]
    if not any(parts):
        return False  # nothing but masks or punctuation: nothing to find
    # The same comparison the evidence check used to accept the quote (tieout.comparable).
    return re.search(r"[\s\S]{1,300}?".join(parts), comparable(raw)) is not None


def _at(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _run_files() -> list[Path]:
    return sorted(RUNS.glob("*.json"))


def _slug(path: Path) -> str:
    m = re.match(r"^\d{8}T\d{6}Z-(.+)\.json$", path.name)
    return m.group(1) if m else path.stem


def _walk(value, visit, key: str | None = None) -> None:
    visit(value, key)
    if isinstance(value, dict):
        for k, v in value.items():
            _walk(v, visit, k)
    elif isinstance(value, list):
        for v in value:
            _walk(v, visit, key)


def check_facts() -> Check:
    c = Check("facts file is current (runs/analysis/facts.json = recomputed)")
    saved = json.loads(facts.FACTS.read_text(encoding="utf-8")) if facts.FACTS.exists() else None
    now = facts.compute()
    if saved is None:
        c.test(False, "no facts file: run `heirloom facts`")
        return c
    for key in now:
        if key == "computed_at":
            continue
        c.test(json.dumps(now[key], sort_keys=True, default=str) == json.dumps(saved.get(key), sort_keys=True,
                                                                             default=str), f"{key} changed")
    return c


def check_docs() -> Check:
    c = Check("numbers marked in the docs match the facts")
    data = facts.compute()
    for doc in DOCS:
        if not doc.exists():
            continue
        for m in MARKER.finditer(doc.read_text(encoding="utf-8")):
            value: object = data
            for part in m.group(2).split("."):  # dict keys, or list indexes: held_after_human_no.rows.0.hours
                if isinstance(value, list) and part.isdigit():
                    value = value[int(part)] if int(part) < len(value) else None
                else:
                    value = value.get(part) if isinstance(value, dict) else None
            ok = isinstance(value, (int, float)) and float(m.group(1).replace(",", "")) == float(value)
            c.test(ok, f"{doc.name}: '{m.group(1)}' but {m.group(2)} = {value}")
    return c


def check_trails() -> list[Check]:
    links, order, status = (Check("every village link points at its own moment"),
                            Check("time order holds (carrier before copy, first held before last, evidence in window)"),
                            Check("statuses agree with the trail's own nodes"))
    for path in _run_files():
        run = json.loads(path.read_text(encoding="utf-8"))

        def visit(v, _key):
            if isinstance(v, dict) and isinstance(v.get("link"), str) and v.get("at"):
                links.test(v["link"] == village_link(_at(str(v["at"]))), f"{path.name}: {v['link']}")

        _walk(run, visit)
        if run.get("believers") is None:
            continue
        held = [b for b in run["believers"] if b["status"] != "never held"]
        for b in run["believers"]:
            who = f"{path.name}: {b['agent']}"
            status.test((b["first_held"] is None) == (b["status"] == "never held"), f"{who} status/first_held")
            status.test(b["status"] != "corrected" or b["first_denial"] is not None, f"{who} corrected, no denial")
            status.test(b["snapshots_holding"] <= b["snapshots_scanned"], f"{who} holding > scanned")
            if b["first_held"]:
                order.test(_at(b["first_held"]["at"]) <= _at(b["last_held"]["at"]), f"{who} first after last")
                if b["carrier"]:
                    order.test(_at(b["carrier"]["at"]) < _at(b["first_held"]["at"]), f"{who} carrier after copy")
                for node in (b["first_held"], b["first_denial"]):
                    t = (node or {}).get("tieout") or {}
                    w = t.get("window")
                    for e in t.get("evidence", []):
                        order.test(w is not None and _at(w["from"]) <= _at(str(e["at"])) <= _at(w["to"]),
                                   f"{who} evidence outside its window")
        if held:
            born = min(_at(b["first_held"]["at"]) for b in held)
            order.test(run["born"] is not None and _at(run["born"]["at"]) == born, f"{path.name}: birth")
    return [links, order, status]


def check_privacy() -> Check:
    c = Check("no email, phone number or credential in any run file")
    for path in [*_run_files(), *[p for p in sorted(ANALYSIS.glob("*.json")) if p.name != "verify.json"]]:
        def visit(v, key, p=path):
            if isinstance(v, str) and key not in _KEEP and not v.startswith(OUR_LINKS):
                c.test(not EMAIL.search(v), f"{p.name}: email in '{v[:60]}'")
                c.test(not PHONE.search(v), f"{p.name}: phone in '{v[:60]}'")
                c.test(scrub_secrets(v) == v, f"{p.name}: credential in '{v[:60]}'")

        _walk(json.loads(path.read_text(encoding="utf-8")), visit)
    return c


def _rows(con, table: str, ids: set[str], columns: str) -> dict[str, tuple]:
    if not ids:
        return {}
    con.execute("CREATE OR REPLACE TEMP TABLE _ids (id VARCHAR)")
    con.executemany("INSERT INTO _ids VALUES (?)", [(i,) for i in ids])
    rows = con.execute(f"SELECT t.id, {columns} FROM {table} t JOIN _ids USING (id)").fetchall()
    return {r[0]: r[1:] for r in rows}


def check_against_raw(con) -> list[Check]:
    quotes, lines = (Check("every evidence quote is in the raw row it cites"),
                     Check("every memory and chat line is in the raw snapshot or message it cites"))
    want: dict[str, set[str]] = defaultdict(set)
    items: list[tuple[str, dict]] = []
    for path in _run_files():
        def visit(v, _key, p=path):
            if not isinstance(v, dict):
                return
            if {"source", "id", "quote"} <= v.keys():
                table = {"turn": "computer_use_turns", "chat": "chat_messages", "human": "chat_messages"}.get(
                    v["source"], "events")
                want[table].add(v["id"])
                items.append((p.name, v))
            elif v.get("kind") in ("memory", "chat") and v.get("ref") and v.get("text"):
                want["agent_memories" if v["kind"] == "memory" else "chat_messages"].add(v["ref"])
                items.append((p.name, v))

        _walk(json.loads(path.read_text(encoding="utf-8")), visit)

    turns = _rows(con, "computer_use_turns", want["computer_use_turns"], "agent_action, output, error")
    chat = _rows(con, "chat_messages", want["chat_messages"], "content")
    events = _rows(con, "events", want["events"], "action_type, data->>'query', data->>'answerToQuery', "
                                                  "data->>'summary', data->>'nextSessionGoal'")
    memories = _rows(con, "agent_memories", want["agent_memories"], "content")

    def evidence_text(source: str, rid: str) -> str | None:
        if source == "turn" and rid in turns:
            a, o, e = turns[rid]
            return "\n".join(p for p in (f"action: {a}" if a else "", f"output: {o}" if o else "",
                                         f"error: {e}" if e else "") if p)
        if source in ("chat", "human") and rid in chat:
            return chat[rid][0]
        if rid in events:
            kind, q, a, summary, goal = events[rid]
            return {"SEARCH_HISTORY": f"Q: {q}\nA: {a}", "STOP_USING_COMPUTER": summary,
                    "CONSOLIDATE": f"next goal: {goal}"}.get(kind)
        return None

    for name, v in items:
        if "quote" in v:
            raw = evidence_text(v["source"], v["id"])
            quotes.test(raw is not None and found_in(v["quote"].strip(QUOTE_STRIP), raw),
                        f"{name}: {v['source']} {v['id']}: '{v['quote'][:60]}'")
        elif v["kind"] == "memory":
            raw = memories.get(v["ref"])
            lines.test(raw is not None and found_in(v["text"], "\n".join(lines_in_context(raw[0]))),
                       f"{name}: memory {v['ref']}: '{v['text'][:60]}'")
        else:
            raw = chat.get(v["ref"])
            lines.test(raw is not None and found_in(v["text"], normalize(raw[0])),
                       f"{name}: chat {v['ref']}: '{v['text'][:60]}'")
    return [quotes, lines]


def check_lifecycle() -> Check:
    c = Check("snapshot-by-snapshot re-read agrees with every trail; hand checks cite flagged items")
    flagged = set()
    for path in sorted(ANALYSIS.glob("lifecycle-*.json")):
        d = json.loads(path.read_text(encoding="utf-8"))
        c.test(bool(d.get("matches_trail")), f"{path.name}: holding counts differ from the trail")
        c.test(d["coverage"]["labelled"] == d["coverage"]["lines"], f"{path.name}: unlabelled lines")
        for a in d["agents"]:
            for r in a["returns"]:
                flagged.add(("return", d["case"], a["agent"], r["gone_from"]["ref"], r["back_at"]["ref"]))
            if a["relapse"]:
                r = a["relapse"]
                flagged.add(("relapse", d["case"], a["agent"], r["denied"]["ref"], r["held_again"]["ref"]))
    checks = json.loads((ANALYSIS / "hand-checks.json").read_text(encoding="utf-8"))["checks"]
    for h in checks:
        c.test((h["kind"], h["case"], h["agent"], h["from"], h["to"]) in flagged,
               f"hand check not among flagged items: {h['case']} {h['agent']} {h['kind']}")
    return c


def run(con=None) -> list[Check]:
    checks = [check_facts(), check_docs(), *check_trails(), check_privacy(), check_lifecycle()]
    if con is not None:
        checks += check_against_raw(con)
    return checks


def save(checks: list[Check], with_db: bool) -> Path:
    out = ANALYSIS / "verify.json"
    out.write_text(json.dumps({
        "kind": "verify",
        "at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "with_database": with_db,
        "passed": all(c.passed for c in checks),
        "checks": [{"name": c.name, "passed": c.passed, "ok": c.ok, "failed": len(c.failures),
                    "failures": c.failures[:20]} for c in checks],
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    return out

