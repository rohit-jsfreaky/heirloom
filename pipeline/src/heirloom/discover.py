"""Find beliefs nobody named. No model sees a line until the line has shown it matters.

1. Novelty (no LLM): a line is a birth when it brings a strong anchor (a count with its unit, money, URL, id, email,
   quoted name) that the agent never had in memory before.
2. Lineage (no LLM): for every anchor born in scope, where it lives afterwards: per agent, the first and last
   snapshot holding it, how many rewrites it survived, whether it is still there in the agent's last snapshot.
3. Rank by spread and survival. Only the top births go to the models:
4. Claims (cheap model): the checkable claim each top birth line makes.
5. Tie-out (cheap model) at birth: supported / contradicted / hearsay / no_evidence / instruction.
"""

import hashlib
import inspect
import json
import math
import pickle
import re
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

import duckdb
from rapidfuzz import fuzz
from rich.console import Console
from rich.progress import track

from heirloom.claims import extract
from heirloom.config import DATA, ROOT
from heirloom.diff import anchors, body_of, diff, line_hash, lines_in_context, search_terms, strong
from heirloom.llm import LLM
from heirloom.tieout import tie_out
from heirloom.village import village_link

console = Console(highlight=False)
RUNS = ROOT / "runs"
MIN_SNAPSHOTS = 3  # an anchor held in fewer snapshots than this never became a belief
CHECKABLE = {"exists", "count", "done", "broken", "identity", "instruction-to-self"}
# no_evidence is also how true facts seen only on screen look (screenshots are not read), so it stays neutral.
LABEL_WEIGHT = {"contradicted": 3.0, "hearsay": 1.5, "no_evidence": 1.0, "instruction": 1.2, "supported": 0.3}
WORKERS = 6
# Words that dispute a fact. A belief that keeps meeting them and still survives is what we are looking for.
DISPUTE = re.compile(
    r"never existed|does ?n[o']t exist|did ?n[o']t exist|hallucinat\w*|fabricat\w*|placeholder\w*|\bfake\b|"
    r"fiction\w*|vanished|\bempty\b|\bmissing\b|\blost\b|\bdeleted\b|not found|\b404\b|"
    r"(?:can'?t|cannot|could ?n[o']t) (?:find|locate|access)|\bwrong\b|incorrect|inaccurate|\bfalse\b|mistaken|"
    r"misremember\w*|confabulat\w*|does ?n[o']t match|no such", re.I)


@dataclass
class Birth:
    anchor: str
    agent_id: str
    agent: str
    snapshot_id: str
    k: int
    at: datetime
    prev_at: datetime | None
    line: str
    section: str | None


@dataclass
class Life:
    """One anchor inside one agent's memory."""
    first_k: int
    first_at: datetime
    last_k: int
    last_at: datetime
    snapshots: int = 1


@dataclass
class Belief:
    id: str
    anchors: list[str]
    line: str
    born: dict
    believers: list[dict]
    agents: int
    rewrites: int
    alive_in: list[str]
    disputes: int  # later memory lines (any agent) that carry the anchor next to a disputing word
    lead_score: float
    claim: dict | None = None
    tieout: dict | None = None
    carriers: list[dict] = field(default_factory=list)
    score: float = 0.0


def _scan(con: duckdb.DuckDBPyConnection, start: datetime, end: datetime, history_from: datetime):
    births: dict[str, list[Birth]] = defaultdict(list)
    lives: dict[str, dict[str, Life]] = defaultdict(dict)
    disputed: dict[str, set[str]] = defaultdict(set)  # anchor → hashes of distinct lines disputing it
    final_k: dict[str, int] = {}
    names: dict[str, str] = {}
    agents = con.execute("""SELECT a.id, a.name FROM agents a WHERE EXISTS (SELECT 1 FROM agent_memories m
                            WHERE m.agent_id = a.id AND m.created_at BETWEEN ? AND ?) ORDER BY a.created_at""",
                         [start, end]).fetchall()
    for agent_id, name in track(agents, description="  novelty + lineage", console=console):
        names[agent_id] = name
        k0, = con.execute("SELECT count(*) FROM agent_memories WHERE agent_id = ? AND created_at < ?",
                          [agent_id, history_from]).fetchone()
        cur = con.execute("""SELECT id, created_at, content FROM agent_memories
                             WHERE agent_id = ? AND created_at >= ? AND created_at <= ? ORDER BY created_at""",
                          [agent_id, history_from, end])
        seen: set[str] = set()
        prev, prev_at, k = None, None, k0 - 1
        while rows := cur.fetchmany(200):
            for sid, at, content in rows:
                k += 1
                context = lines_in_context(content)
                section_of = {}
                for c in context:
                    body = body_of(c)
                    if body is not c:
                        section_of[body] = c[1:c.index("] ")]
                held = {a for c in context for a in anchors(body_of(c)) if strong(a)}
                if at >= start:
                    if prev is not None:
                        for line in diff(prev, content).candidates:
                            for a in anchors(line):
                                if strong(a) and a not in seen:
                                    births[a].append(Birth(a, agent_id, name, sid, k, at, prev_at, line,
                                                           section_of.get(line)))
                    for a in held:
                        life = lives[a].get(agent_id)
                        if life is None:
                            lives[a][agent_id] = Life(k, at, k, at)
                        else:
                            life.last_k, life.last_at, life.snapshots = k, at, life.snapshots + 1
                    for c in context:
                        body = body_of(c)
                        if DISPUTE.search(body):
                            for a in anchors(body):
                                if strong(a):
                                    disputed[a].add(line_hash(body))
                    final_k[agent_id] = k
                seen |= held
                prev, prev_at = content, at
    return births, lives, disputed, final_k, names


def _beliefs(births, lives, disputed, final_k, names) -> list[Belief]:
    by_line: dict[str, Belief] = {}
    for anchor, bs in births.items():
        life = lives.get(anchor, {})
        total = sum(x.snapshots for x in life.values())
        if total < MIN_SNAPSHOTS:
            continue
        b = min(bs, key=lambda x: x.at)
        rewrites = sum(x.last_k - x.first_k for x in life.values())
        alive = [names[a] for a, x in life.items() if x.last_k == final_k.get(a)]
        # Spread = agents that only took it up after it was born somewhere else. Facts every agent already had
        # (official links, team rosters) don't spread; beliefs passed agent to agent do.
        caught = sum(1 for a, x in life.items() if a != b.agent_id and x.first_at > b.at)
        believers = [{"agent": names[a], "first_at": x.first_at, "last_at": x.last_at, "first_k": x.first_k,
                      "last_k": x.last_k, "snapshots": x.snapshots, "rewrites": x.last_k - x.first_k,
                      "alive": names[a] in alive,
                      "first_line": next((y.line for y in bs if y.agent_id == a), None)}
                     for a, x in sorted(life.items(), key=lambda kv: kv[1].first_at)]
        disputes = len(disputed.get(anchor, ()))
        lead = (1 + caught) * math.log2(2 + rewrites) * (2 if alive else 1) * (1 + math.log2(1 + disputes))
        key = line_hash(b.agent_id + b.line)
        if key in by_line:  # one birth line, several new anchors: one belief
            by_line[key].anchors.append(anchor)
            if lead > by_line[key].lead_score:
                x = by_line[key]
                x.lead_score, x.believers, x.agents, x.rewrites = round(lead, 2), believers, len(life), rewrites
                x.alive_in, x.disputes = alive, disputes
            continue
        by_line[key] = Belief(
            id=hashlib.sha256(key.encode()).hexdigest()[:10], anchors=[anchor], line=b.line,
            born={"agent": b.agent, "agent_id": b.agent_id, "snapshot": b.snapshot_id, "k": b.k, "at": b.at,
                  "prev_at": b.prev_at, "section": b.section, "link": village_link(b.at)},
            believers=believers, agents=len(life), rewrites=rewrites, alive_in=alive, disputes=disputes,
            lead_score=round(lead, 2))
    return sorted(by_line.values(), key=lambda x: x.lead_score, reverse=True)


def _carriers(con: duckdb.DuckDBPyConnection, belief: Belief) -> list[dict]:
    """For each agent that picked the belief up after its birth: the first chat message in between that holds it."""
    terms = [t for a in belief.anchors for t in search_terms(a)][:1]
    out = []
    for x in belief.believers:
        if x["agent"] == belief.born["agent"] or x["first_at"] <= belief.born["at"]:
            continue
        row = con.execute("""SELECT c.id, c.created_at, coalesce(a.name, '[person]'), c.content FROM chat_messages c
                             LEFT JOIN agents a ON a.id = c.agent_speaker_id
                             WHERE c.created_at > ? AND c.created_at < ? AND contains(lower(c.content), ?)
                             ORDER BY c.created_at LIMIT 1""",
                          [belief.born["at"], x["first_at"], terms[0]]).fetchone()
        if row:
            out.append({"to": x["agent"], "id": row[0], "at": row[1], "speaker": row[2], "text": row[3][:400],
                        "link": village_link(row[1])})
    return out


def _check(con: duckdb.DuckDBPyConnection, llm: LLM, beliefs: list[Belief], top: int, check: int):
    """The only paid part: claims for the top births, then an evidence check at birth for the top checkable ones."""
    head = beliefs[:top]
    by_agent: dict[str, list[str]] = defaultdict(list)
    for b in head:
        by_agent[b.born["agent"]].append(b.line)
    for agent, lines in by_agent.items():
        extract(con, llm, agent, lines)
    claims = defaultdict(list)
    rows = con.execute(
        """SELECT line_hash, text, kind, anchors, subject FROM line_claims
           WHERE line_hash IN (SELECT unnest(?)) AND claim_no >= 0""",
        [[line_hash(b.line) for b in head]]).fetchall() if head else []
    for h, text, kind, anchors_, subject in rows:
        claims[h].append({"text": text, "kind": kind, "anchors": anchors_, "subject": subject})
    for b in head:
        options = claims.get(line_hash(b.line), [])
        terms = [t.lower() for a in b.anchors for t in search_terms(a)]
        covering = [c for c in options if any(t in (c["text"] + " " + " ".join(c["anchors"])).lower() for t in terms)]
        b.claim = (covering or options or [None])[0]

    checkable = [b for b in head if b.claim and b.claim["kind"] in CHECKABLE][:check]

    def check_one(b: Belief) -> Belief:
        cur = con.cursor()  # one DuckDB cursor per thread
        t = tie_out(cur, llm, b.born["agent_id"], b.born["agent"], b.line, b.born["prev_at"], b.born["at"],
                    focus=(b.claim or {}).get("text"))
        b.tieout = {"label": t.label, "reason": t.reason, "model": llm.cheap,
                    "evidence": [{"source": e.source, "id": e.id, "at": e.created_at, "speaker": e.speaker,
                                  "quote": q, "link": village_link(e.created_at)} for e, q in t.quotes]}
        b.carriers = _carriers(cur, b)
        b.score = round(b.lead_score * LABEL_WEIGHT.get(t.label, 1.0), 2)
        return b

    with ThreadPoolExecutor(WORKERS) as pool:
        for _ in track(pool.map(check_one, checkable), total=len(checkable), description="  tie-outs at birth",
                       console=console):
            pass
    return head, checkable, sorted(checkable, key=lambda b: b.score, reverse=True)


def _export(con: duckdb.DuckDBPyConnection) -> dict:
    meta = con.execute("SELECT exported_at, revision FROM meta").fetchone()
    return {"exported_at": meta[0], "revision": meta[1],
            "source": "AI Digest / AI Village dataset (aidigestorg/ai-village)"}


def run(con: duckdb.DuckDBPyConnection, llm: LLM, start: datetime, end: datetime, history_from: datetime,
        top: int = 300, check: int = 100) -> tuple[list, dict]:
    births, lives, disputed, final_k, names = _scan(con, start, end, history_from)
    beliefs = _beliefs(births, lives, disputed, final_k, names)
    console.print(f"  {sum(len(v) for v in births.values()):,} births of {len(births):,} new anchors → "
                  f"{len(beliefs):,} beliefs held in ≥{MIN_SNAPSHOTS} snapshots")
    head, checkable, ranked = _check(con, llm, beliefs, top, check)
    # Every belief's lead rank, for --find (printed, never saved: it is raw memory text).
    index = [(i + 1, b.born["agent"], b.born["at"], b.line, b.anchors) for i, b in enumerate(beliefs)]
    return index, {
        "kind": "discover",
        "scan": {"from": start, "to": end, "history_from": history_from},
        "export": _export(con),
        "counts": {"agents": len(names), "anchors_born": len(births),
                   "births": sum(len(v) for v in births.values()), "beliefs": len(beliefs),
                   "read_by_model": len(head), "tied_out": len(checkable),
                   "labels": {lab: sum(1 for b in checkable if b.tieout["label"] == lab) for lab in LABEL_WEIGHT}},
        "ranked": [asdict(b) for b in ranked],
        "unchecked_head": [asdict(b) for b in head if b not in checkable][:50],
        "llm": llm.report(),
    }


# ── Still alive: start from what every agent believes now, trace each fact back to its birth ─────────────────

ACTIVE_DAYS = 30  # an agent counts as active if it wrote memory in the export's last 30 days


def _alive_scan(con: duckdb.DuckDBPyConnection, since: datetime):
    until, = con.execute("SELECT max(created_at) FROM agent_memories").fetchone()
    latest = con.execute("""
        SELECT a.id, a.name, m.content FROM agent_memories m JOIN agents a ON a.id = m.agent_id
        WHERE (m.agent_id, m.created_at) IN (SELECT agent_id, max(created_at) FROM agent_memories GROUP BY 1)
          AND m.created_at >= ?""", [until - timedelta(days=ACTIVE_DAYS)]).fetchall()
    holders: dict[str, set[str]] = defaultdict(set)  # anchor → agents whose latest memory holds it
    for _, name, content in latest:
        for c in lines_in_context(content):
            for a in anchors(body_of(c)):
                if strong(a):
                    holders[a].add(name)
    tracked = set(holders)

    births: dict[str, list[Birth]] = defaultdict(list)
    lives: dict[str, dict[str, Life]] = defaultdict(dict)
    disputed: dict[str, set[str]] = defaultdict(set)
    final_k: dict[str, int] = {}
    names: dict[str, str] = {}
    old: set[tuple[str, str]] = set()  # (anchor, agent) already present when the window opens
    agents = con.execute("""SELECT a.id, a.name FROM agents a WHERE EXISTS (SELECT 1 FROM agent_memories m
                            WHERE m.agent_id = a.id AND m.created_at >= ?) ORDER BY a.created_at""",
                         [since]).fetchall()
    for agent_id, name in track(agents, description="  tracing beliefs back", console=console):
        names[agent_id] = name
        k0, prev_at = con.execute("SELECT count(*), max(created_at) FROM agent_memories WHERE agent_id = ? "
                                  "AND created_at < ?", [agent_id, since]).fetchone()
        cur = con.execute("""SELECT id, created_at, content FROM agent_memories
                             WHERE agent_id = ? AND created_at >= ? ORDER BY created_at""", [agent_id, since])
        # Facts already in the first snapshot are older than the window, unless the agent is new (no history).
        k, first = k0 - 1, k0 > 0
        while rows := cur.fetchmany(100):
            for sid, at, content in rows:
                k += 1
                for c in lines_in_context(content):
                    body = body_of(c)
                    here = [a for a in anchors(body) if a in tracked]
                    if not here:
                        continue
                    dispute = bool(DISPUTE.search(body))
                    for a in here:
                        life = lives[a].get(agent_id)
                        if life is None:
                            lives[a][agent_id] = Life(k, at, k, at)
                            if first:
                                old.add((a, agent_id))
                            else:
                                section = c[1:c.index("] ")] if body is not c else None
                                births[a].append(Birth(a, agent_id, name, sid, k, at, prev_at, body, section))
                        elif life.last_k != k:
                            life.last_k, life.last_at, life.snapshots = k, at, life.snapshots + 1
                        if dispute:
                            disputed[a].add(line_hash(body))
                prev_at, first = at, False
                final_k[agent_id] = k
    return holders, births, lives, disputed, final_k, names, old, until


# Counts of these are everyday bookkeeping in 2026 memories ("2 commits", "3 files", "5 paras"): they collide
# across unrelated lines, so they never make a belief on their own.
_GENERIC_UNITS = {"file", "commit", "para", "paragraph", "part", "line", "turn", "statu", "status", "ok", "open",
                  "unique", "but", "while", "no", "merged", "session", "step", "item", "issue", "pr", "link", "page",
                  "word", "char", "character", "byte", "kb", "mb", "gb", "ms", "insertion", "deletion", "change",
                  "section", "chapter", "ch", "language", "lang", "agent", "model", "message", "comment", "reply",
                  "hex", "column", "field", "key", "token", "pixel", "slot", "level", "hp", "xp"}


def _specific(anchor: str) -> bool:
    m = re.match(r"^(\d[\d,.]*) (\S+)$", anchor)
    if m:
        return m.group(2) not in _GENERIC_UNITS and not anchor.startswith(("0 ", "1 "))
    m = re.match(r"^(\d+)/(\d+)", anchor)
    if m:
        return int(m.group(2)) >= 3  # "1/1", "0/0" say nothing
    return True


def _same_belief(line: str | None, birth_line: str) -> bool:
    """Did this agent pick up the same fact, or just a line that happens to share a number? Similar wording, or
    two shared anchors."""
    if not line:
        return False
    if fuzz.token_set_ratio(line, birth_line) >= 60:
        return True
    return len({a for a in anchors(line) if strong(a)} & {a for a in anchors(birth_line) if strong(a)}) >= 2


def _alive_beliefs(holders, births, lives, disputed, final_k, names, old) -> tuple[list[Belief], int]:
    by_line: dict[str, Belief] = {}
    older = 0
    id_of = {v: k for k, v in names.items()}
    for anchor, alive in holders.items():
        if not _specific(anchor):
            continue
        if any((anchor, id_of.get(n)) in old for n in alive):
            older += 1  # held since before the window opened: born before the 2026 era scanned here
            continue
        bs = births.get(anchor)
        life = lives.get(anchor, {})
        if not bs or sum(x.snapshots for x in life.values()) < MIN_SNAPSHOTS:
            continue
        b = min(bs, key=lambda x: x.at)
        first_line = {y.agent_id: y.line for y in bs}
        # Only agents whose own first line is the same fact count as carriers of this belief.
        same = {a for a in life if a == b.agent_id or _same_belief(first_line.get(a), b.line)}
        life = {a: x for a, x in life.items() if a in same}
        alive = {names[a] for a in same} & set(alive)
        if not alive:
            continue
        rewrites = sum(x.last_k - x.first_k for x in life.values())
        caught = sum(1 for a, x in life.items() if a != b.agent_id and x.first_at > b.at)
        disputes = len(disputed.get(anchor, ()))
        lead = (1 + caught) * math.log2(2 + rewrites) * (1 + len(alive)) * (1 + math.log2(1 + disputes))
        believers = [{"agent": names[a], "first_at": x.first_at, "last_at": x.last_at, "first_k": x.first_k,
                      "last_k": x.last_k, "snapshots": x.snapshots, "rewrites": x.last_k - x.first_k,
                      "alive": names[a] in alive, "first_line": first_line.get(a)}
                     for a, x in sorted(life.items(), key=lambda kv: kv[1].first_at)]
        key = line_hash(b.agent_id + b.line)
        if key in by_line:
            by_line[key].anchors.append(anchor)
            if lead > by_line[key].lead_score:
                x = by_line[key]
                x.lead_score, x.believers, x.agents, x.rewrites = round(lead, 2), believers, len(life), rewrites
                x.alive_in, x.disputes = sorted(alive), disputes
            continue
        by_line[key] = Belief(
            id=hashlib.sha256(key.encode()).hexdigest()[:10], anchors=[anchor], line=b.line,
            born={"agent": b.agent, "agent_id": b.agent_id, "snapshot": b.snapshot_id, "k": b.k, "at": b.at,
                  "prev_at": b.prev_at, "section": b.section, "link": village_link(b.at)},
            believers=believers, agents=len(life), rewrites=rewrites, alive_in=sorted(alive), disputes=disputes,
            lead_score=round(lead, 2))
    return sorted(by_line.values(), key=lambda x: x.lead_score, reverse=True), older


def _scan_cache_path(con: duckdb.DuckDBPyConnection, since: datetime) -> Path:
    """The scan takes ~45 min for the 2026 era, so it is kept on disk: keyed by the export revision and by the
    anchor/line code itself, so any change to how lines or anchors are read starts a fresh scan."""
    import heirloom.diff as diff_mod

    revision, = con.execute("SELECT revision FROM meta").fetchone()
    code = hashlib.sha256(inspect.getsource(diff_mod).encode()).hexdigest()[:8]
    return DATA / f"alive_scan_{since:%Y%m%d}_{revision[:8]}_{code}.pkl"


_NUMERIC = re.compile(r"^(?:\$[\d,.]+[km]?|\d[\d,.]*\s\S+|\d+/\d+(?:\s\S+)?)$")


def _numeric(b: Belief) -> bool:
    """Counts, money and scores: where 2026 fabrication and exaggeration live ("20 orders, $360.67", "306/306
    checks"). In 2026 memories bare links are mostly true project facts, so by default the paid steps skip them."""
    return any(_NUMERIC.match(a) and not a.startswith(("0/0", "0 ")) for a in b.anchors)


def alive(con: duckdb.DuckDBPyConnection, llm: LLM, since: datetime, top: int = 300,
          check: int = 100, focus: str = "numbers") -> tuple[list, dict]:
    path = _scan_cache_path(con, since)
    if path.exists():
        console.print(f"  scan read from {path.name}")
        scanned = pickle.loads(path.read_bytes())
    else:
        scanned = _alive_scan(con, since)
        path.write_bytes(pickle.dumps(scanned))
    holders, births, lives, disputed, final_k, names, old, until = scanned
    beliefs, older = _alive_beliefs(holders, births, lives, disputed, final_k, names, old)
    console.print(f"  {len(holders):,} facts in the agents' latest memories → {len(beliefs):,} born since "
                  f"{since:%Y-%m-%d} and held in ≥{MIN_SNAPSHOTS} snapshots ({older:,} older than that)")
    if focus == "numbers":
        beliefs = [b for b in beliefs if _numeric(b)]
        console.print(f"  focus numbers: {len(beliefs):,} beliefs carry a count, amount or score")
    head, checkable, ranked = _check(con, llm, beliefs, top, check)
    index = [(i + 1, b.born["agent"], b.born["at"], b.line, b.anchors) for i, b in enumerate(beliefs)]
    return index, {
        "kind": "alive",
        "scan": {"from": since, "to": until, "active_days": ACTIVE_DAYS, "focus": focus},
        "export": _export(con),
        "counts": {"agents": len(names), "facts_in_latest_memory": len(holders), "beliefs": len(beliefs),
                   "older_than_window": older, "read_by_model": len(head), "tied_out": len(checkable),
                   "labels": {lab: sum(1 for b in checkable if b.tieout["label"] == lab) for lab in LABEL_WEIGHT}},
        "ranked": [asdict(b) for b in ranked],
        "unchecked_head": [asdict(b) for b in head if b not in checkable][:50],
        "llm": llm.report(),
    }


def save(con: duckdb.DuckDBPyConnection, llm: LLM, data: dict) -> tuple[dict, str]:
    """Mask people (same rules as trails), then write runs/<timestamp>-<kind>-<from>.json."""
    from heirloom.privacy import Masker
    from heirloom.trail import _mask_tree, _strings

    raw = json.loads(json.dumps(data, default=str))
    mask = Masker(con)
    mask.add_people(llm, _strings(raw, []))
    data = _mask_tree(raw, mask)
    data["llm"] = llm.report()
    data["saved_at"] = datetime.now(UTC).isoformat(timespec="seconds")
    RUNS.mkdir(exist_ok=True)
    path = RUNS / f"{datetime.now(UTC):%Y%m%dT%H%M%SZ}-{data['kind']}-{data['scan']['from'][:10]}.json"
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return data, str(path)
