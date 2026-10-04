"""The whole village, no model: every belief `discover` finds, true or false.

`discover` finds every new fact (a count with its unit, money, a link, an id) written into memory in its scan and keeps
the ones held in at least 3 snapshots: those are its candidate beliefs. With no model we can't say which are false,
so these numbers are about beliefs in general. The false-belief evidence stays the hand-checked trails.

For every candidate belief:
1. Spread: which other agents wrote the same fact into memory after its birth (same anchor, and their first line
   is the same fact: similar wording or two shared anchors, as in `alive`).
2. Chat timing: was each copy written within an hour after another agent posted the fact in chat? Against the same
   strict null as `heirloom chance`: the moments that agent wrote memory anyway while the belief was active.
3. Memory lifetime: each holder's memory is read on to its last snapshot (past the scan, to the export's end). Gone =
   no line holds the fact's exact anchor at a later rewrite; back = it returns after being gone.

Saved without memory or chat text: belief ids (hashes), agent names, times and counts only.
"""

import bisect
import gzip
import hashlib
import json
import pickle
import statistics
from collections import defaultdict
from datetime import datetime, timedelta

import duckdb
from rich.console import Console
from rich.progress import track

from heirloom import discover
from heirloom.chance import poisson_binomial_tail
from heirloom.config import DATA
from heirloom.diff import anchors, body_of, lines_in_context, strong
from heirloom.lifecycle import ANALYSIS

console = Console(highlight=False)
GAP = timedelta(minutes=60)  # same as `heirloom chance`
# Two eras, the same rules. 2025: exactly the `discover` run's scan (6 agents). 2026: the last 8 weeks of the export
# (3 of the 4 monitor cases fall in them; the whole era is too big for a laptop's RAM with this scan), with 14 days of
# earlier memory read so old facts don't look new (2026 memories are full rewrites, so that holds every kept fact).
ERAS = {"2025": None, "2026": (datetime(2026, 7, 25), None, 14)}


def out(era: str):
    return ANALYSIS / f"population-{era}.json"
# A return counts only when the fact was gone at least this long (not a rewrite that flickered) and the line that
# brings it back is the same fact (similar wording or two shared anchors), not another line sharing one anchor.
RETURN_GAP = timedelta(hours=1)
# The only fields saved per row: no memory or chat text, no anchors (they can hold names, emails or links).
COPY_KEYS = {"belief", "agent", "first_held", "gap_minutes", "within", "p_null_own_writes", "own_writes"}
HOLDING_KEYS = {"belief", "agent", "copy", "first", "last_held", "days_held", "held_at_end", "agent_last_snapshot",
                "gaps"}


def latest_discover() -> dict:
    path = sorted(discover.RUNS.glob("*-discover-*.json"))[-1]
    return json.loads(path.read_text(encoding="utf-8")) | {"_file": path.name}


def beliefs(con: duckdb.DuckDBPyConnection, start: datetime, end: datetime, history_from: datetime):
    """Exactly discover's candidate beliefs (same scan, same filter), cached: the scan reads every snapshot."""
    revision, = con.execute("SELECT revision FROM meta").fetchone()
    cache = DATA / f"population_scan_{start:%Y%m%d}_{end:%Y%m%d}_{history_from:%Y%m%d}_{revision[:8]}.pkl"
    if cache.exists():
        scan = pickle.loads(cache.read_bytes())
    else:
        scan = discover._scan(con, start, end, history_from)
        cache.write_bytes(pickle.dumps(scan))
    births, lives, disputed, final_k, names = scan
    return discover._beliefs(births, lives, disputed, final_k, names), names


def copies_of(b) -> list[dict]:
    """Other agents that took the fact up after its birth, with the same fact in their own first line."""
    return [x for x in b.believers
            if x["agent"] != b.born["agent"] and x["first_at"] > b.born["at"]
            and discover._same_belief(x["first_line"], b.line)]


def presence(con: duckdb.DuckDBPyConnection, holders: dict[str, dict[str, set[str]]], start: datetime):
    """agent → belief id → sorted snapshot times where any of its anchors is held, from `start` to the agent's last
    snapshot. holders: agent → anchor → belief ids."""
    seen: dict[str, dict[str, list[datetime]]] = {}
    ends: dict[str, datetime] = {}
    for agent, by_anchor in track(sorted(holders.items()), description="  memory lifetime", console=console):
        tracked = set(by_anchor)
        cache: dict[str, frozenset[str]] = {}
        out: dict[str, list[datetime]] = defaultdict(list)
        times: list[datetime] = []
        cur = con.execute("""SELECT m.created_at, m.content FROM agent_memories m JOIN agents a ON a.id = m.agent_id
                             WHERE a.name = ? AND m.created_at >= ? ORDER BY m.created_at""", [agent, start])
        while rows := cur.fetchmany(200):
            for at, content in rows:
                times.append(at)
                here: set[str] = set()
                for c in lines_in_context(content):
                    body = body_of(c)
                    hit = cache.get(body)
                    if hit is None:
                        hit = cache[body] = frozenset(a for a in anchors(body) if strong(a) and a in tracked)
                    here |= hit
                for bid in {bid for a in here for bid in by_anchor[a]}:
                    out[bid].append(at)
        seen[agent] = {"times": times, "held": dict(out)}
        ends[agent] = times[-1] if times else start
    return seen, ends


def lifetime(times: list[datetime], held: list[datetime], first: datetime) -> dict:
    """From the first snapshot holding it: gone at a later rewrite? back after that? days held?"""
    held_set = set(held)
    i = bisect.bisect_left(times, first)
    run_on, gaps, last_held = True, [], first
    gone_at = None
    for t in times[i:]:
        if t in held_set:
            if not run_on:
                gaps.append({"gone": gone_at, "back": t})
            run_on, last_held = True, t
        elif run_on:
            run_on, gone_at = False, t
    return {"first": first, "last_held": last_held, "gaps": gaps, "held_at_end": run_on,
            "snapshots_after": len(times) - i}


def same_on_return(con: duckdb.DuckDBPyConnection, holdings: list[dict], by_id: dict) -> None:
    """Mark each long-enough gap: is the line that brings the fact back the same fact?"""
    wanted: dict[str, set[datetime]] = defaultdict(set)
    for h in holdings:
        for g in h["gaps"]:
            if g["back"] - g["gone"] >= RETURN_GAP:
                wanted[h["agent"]].add(g["back"])
    content: dict[tuple[str, datetime], str] = {}
    for agent, times in track(sorted(wanted.items()), description="  returns", console=console):
        for at, text in con.execute("""SELECT m.created_at, m.content FROM agent_memories m
                                       JOIN agents a ON a.id = m.agent_id
                                       WHERE a.name = ? AND m.created_at IN (SELECT unnest(?))""",
                                    [agent, sorted(times)]).fetchall():
            content[(agent, at)] = text
    # Each snapshot parsed once: its lines with their strong anchors (many gaps return in the same snapshot).
    parsed = {key: [(body, {a for a in anchors(body) if strong(a)})
                    for body in (body_of(c) for c in lines_in_context(text))]
              for key, text in content.items()}
    for h in holdings:
        b = by_id[h["belief"]]
        mine = set(b.anchors)
        for g in h["gaps"]:
            g["hours"] = round((g["back"] - g["gone"]).total_seconds() / 3600, 2)
            lines = parsed.get((h["agent"], g["back"]), [])
            g["same_fact"] = any(discover._same_belief(body, b.line) for body, held in lines if mine & held)


def chat_index(con: duckdb.DuckDBPyConnection, start: datetime, end: datetime) -> dict[str, list[tuple]]:
    """anchor → [(time, agent)] for every agent chat message, anchors read the same way as memory lines."""
    index: dict[str, list[tuple]] = defaultdict(list)
    rows = con.execute("""SELECT c.created_at, a.name, c.content FROM chat_messages c
                          JOIN agents a ON a.id = c.agent_speaker_id
                          WHERE c.speaker_type = 'agent' AND c.created_at BETWEEN ? AND ? ORDER BY c.created_at""",
                       [start, end]).fetchall()
    for at, name, content in rows:
        found = {a for line in (content or "").splitlines() for a in anchors(line.strip()) if strong(a)}
        for a in found:
            index[a].append((at, name))
    return index


def gap_before(t: datetime, others: list[datetime]) -> timedelta | None:
    """Time since the latest message before t; others = sorted times of other agents' messages."""
    i = bisect.bisect_left(others, t)
    return t - others[i - 1] if i else None


def _median(values: list[float]) -> float | None:
    return round(statistics.median(values), 1) if values else None


def summarize(beliefs_n: int, rows: list[dict], holdings: list[dict]) -> dict:
    spread = {}
    for r in rows:
        spread.setdefault(r["belief"], set()).add(r["agent"])
    observed = sum(r["within"] for r in rows)
    ps = [r["p_null_own_writes"] for r in rows]
    gone = [h for h in holdings if h["gaps"] or not h["held_at_end"]]
    back = [h for h in holdings if any(g.get("same_fact") and g["hours"] >= RETURN_GAP.total_seconds() / 3600
                                       for g in h["gaps"])]
    gone_for_good = [h for h in holdings if not h["held_at_end"]]
    cps = [h for h in holdings if h["copy"]]
    cps_gone = [h for h in cps if not h["held_at_end"]]
    return {
        "beliefs": beliefs_n,
        "spread": {"beliefs": len(spread), "pct": round(100 * len(spread) / beliefs_n, 1) if beliefs_n else None,
                   "copies": len(rows),
                   "mean_other_agents": round(len(rows) / len(spread), 2) if spread else None,
                   "max_other_agents": max((len(v) for v in spread.values()), default=0)},
        "chat_timing": {"copies": len(rows), "within_gap": observed,
                        "within_pct": round(100 * observed / len(rows), 1) if rows else None,
                        "expected_own_writes": round(sum(ps), 1),
                        "expected_pct": round(100 * sum(ps) / len(rows), 1) if rows else None,
                        "no_chat_before": sum(1 for r in rows if r["gap_minutes"] is None),
                        "p_value_own_writes": poisson_binomial_tail(ps, observed)},
        "lifetime": {"holdings": len(holdings),
                     "gone_pct": round(100 * len(gone) / len(holdings), 1) if holdings else None,
                     "gone": len(gone),
                     "gone_for_good": len(gone_for_good),
                     "gone_for_good_pct": round(100 * len(gone_for_good) / len(holdings), 1) if holdings else None,
                     "came_back": len(back),
                     "came_back_pct_of_gone": round(100 * len(back) / len(gone), 1) if gone else None,
                     "came_back_pct": round(100 * len(back) / len(holdings), 1) if holdings else None,
                     "flickers_or_other_lines": sum(1 for h in holdings if h["gaps"]) - len(back),
                     "median_hours_held": _median([24 * h["days_held"] for h in holdings]),
                     "held_over_a_day_pct": round(100 * sum(1 for h in holdings if h["days_held"] > 1) / len(holdings),
                                                  1) if holdings else None,
                     "copies": len(cps),
                     "copies_gone_for_good_pct": round(100 * len(cps_gone) / len(cps), 1) if cps else None,
                     "copies_came_back": sum(1 for h in back if h["copy"]),
                     "copies_median_hours_held": _median([24 * h["days_held"] for h in cps])},
    }


def run(con: duckdb.DuckDBPyConnection, era: str = "2025") -> dict:
    disc = latest_discover()
    if ERAS[era] is None:
        scan = {k: datetime.fromisoformat(v) for k, v in disc["scan"].items()}
    else:
        frm, to, days = ERAS[era]
        to = to or con.execute("SELECT max(created_at) FROM agent_memories").fetchone()[0]
        scan = {"from": frm, "to": to, "history_from": frm - timedelta(days=days)}
    start, end, history_from = scan["from"], scan["to"], scan["history_from"]
    found, names = beliefs(con, start, end, history_from)
    # Today's parser on the same scan. The 2 Oct discover run counted a few more: it still read units like "4 has" or
    # "4 reported" as facts, which the parser has since dropped.
    console.print(f"  {len(found):,} candidate beliefs")

    holders: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    plan = []
    for b in found:
        cps = copies_of(b)
        plan.append((b, cps))
        for agent in [b.born["agent"], *(x["agent"] for x in cps)]:
            for a in b.anchors:
                holders[agent][a].add(b.id)
    key = hashlib.sha256(json.dumps({a: sorted((k, sorted(v)) for k, v in h.items()) for a, h in holders.items()},
                                    sort_keys=True).encode()).hexdigest()[:12]
    cache = DATA / f"population_presence_{key}.pkl"
    if cache.exists():
        seen, ends = pickle.loads(cache.read_bytes())
    else:
        seen, ends = presence(con, holders, start)
        cache.write_bytes(pickle.dumps((seen, ends)))
    chat = chat_index(con, history_from, end)

    rows, holdings = [], []
    for b, cps in track(plan, description="  chat timing", console=console):
        said = sorted({m for a in b.anchors for m in chat.get(a, [])})
        lives = {x["agent"]: x for x in b.believers}
        # A belief merged from several anchors keeps the believers of its widest one; its birth agent is the one
        # that wrote the line, held from that snapshot on.
        lives.setdefault(b.born["agent"], {"first_at": b.born["at"], "last_at": b.born["at"]})
        held = [b.born["agent"], *(x["agent"] for x in cps)]
        lo = min([b.born["at"], *(at for at, _ in said[:1])])
        hi = max(lives[a]["last_at"] for a in held)
        for a in held:
            first = lives[a]["first_at"] if a != b.born["agent"] else b.born["at"]
            life = lifetime(seen[a]["times"], seen[a]["held"].get(b.id, []), first)
            days = (life["last_held"] - first).total_seconds() / 86400
            holdings.append({"belief": b.id, "agent": a, "copy": a != b.born["agent"], "first": first,
                             "last_held": life["last_held"], "days_held": round(days, 3),
                             "held_at_end": life["held_at_end"], "agent_last_snapshot": ends[a],
                             "gaps": life["gaps"]})
        for x in cps:
            t = x["first_at"]
            others = [at for at, who in said if who != x["agent"]]
            gap = gap_before(t, others)
            times = seen[x["agent"]]["times"]
            own = times[bisect.bisect_left(times, lo):bisect.bisect_right(times, hi)]
            own_gaps = [gap_before(o, others) for o in own]
            p_own = sum(1 for g in own_gaps if g is not None and g <= GAP) / len(own) if own else 0.0
            rows.append({"belief": b.id, "agent": x["agent"], "first_held": t,
                         "gap_minutes": round(gap.total_seconds() / 60, 1) if gap else None,
                         "within": gap is not None and gap <= GAP, "p_null_own_writes": round(p_own, 4),
                         "own_writes": len(own)})

    same_on_return(con, holdings, {b.id: b for b, _ in plan})
    return {
        "kind": "population",
        "what": "every candidate belief discover finds (true or false: no model labels truth here)",
        "era": era,
        "agents": len(names),
        "discover_run": disc["_file"] if ERAS[era] is None else None,
        "discover_run_beliefs": disc["counts"]["beliefs"] if ERAS[era] is None else None,
        "scan": scan,
        "export": disc["export"],
        "gap_minutes": GAP.total_seconds() / 60,
        "null_own_writes": "copy time = any moment the same agent wrote memory while the belief was active "
                           "(its birth or first chat mention, to its last holding line in the scan)",
        "chat": "agent chat messages whose own anchors include the belief's anchor (same parser as memory lines)",
        "lifetime_horizon": "each holder's memory read to its last snapshot in the export",
        "summary": summarize(len(found), rows, holdings),
        "copies": rows,
        "holdings": holdings,
    }


def rows_path(era: str):
    return ANALYSIS / f"population-{era}-rows.json.gz"


def _columns(rows: list[dict], keys: list[str]) -> dict:
    return {"columns": keys, "rows": [[r[k] for k in keys] for r in rows]}


def save(data: dict) -> None:
    """The summary as plain JSON; every copy and holding row, column by column, gzipped (2026 has ~300,000)."""
    rows = {"copies": _columns(data["copies"], sorted(COPY_KEYS)),
            "holdings": _columns(data["holdings"], sorted(HOLDING_KEYS))}
    raw = json.dumps(rows, separators=(",", ":"), default=str).encode("utf-8")
    with open(rows_path(data["era"]), "wb") as f, gzip.GzipFile(fileobj=f, mode="wb", mtime=0, filename="") as z:
        z.write(raw)  # mtime=0: the same rows give the same bytes, so the file's hash is stable
    meta = {k: v for k, v in data.items() if k not in ("copies", "holdings")} | {"rows": rows_path(data["era"]).name}
    out(data["era"]).write_text(json.dumps(meta, indent=1, default=str), encoding="utf-8")


def load(era: str) -> dict:
    """Summary plus every row, as saved."""
    data = json.loads(out(era).read_text(encoding="utf-8"))
    with gzip.open(rows_path(era), "rt", encoding="utf-8") as z:
        rows = json.load(z)
    for name, table in rows.items():
        data[name] = [dict(zip(table["columns"], r)) for r in table["rows"]]
    return data
