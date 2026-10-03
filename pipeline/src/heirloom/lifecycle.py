"""How a belief lives in each agent's memory, snapshot by snapshot: episodes, gaps, returns, relapses.

No model is called. It re-reads memory with the saved trail's own pattern and scan window and reuses the stance
labels that trail stored (table line_stance). A line with no stored label counts as unrelated, as in the trail, and
the share of labelled lines is reported. Output holds ids, times and links only, never memory text.
"""

import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import duckdb
from rich.console import Console

from heirloom.diff import line_hash
from heirloom.stance import labels
from heirloom.trail import CASES, RUNS, Case, _scan_agent, stance_of
from heirloom.village import village_link

console = Console(highlight=False)
ANALYSIS = RUNS / "analysis"
# Gone from an agent's memory (or from every agent's) for at least this long, then back: a return, not a wobble
# in wording between two rewrites.
RETURN_GAP = timedelta(hours=24)


def latest_runs() -> dict[str, Path]:
    """Newest saved trail per case (file names start with a UTC timestamp, so they sort by time)."""
    out: dict[str, Path] = {}
    for p in sorted(RUNS.glob("*.json")):
        m = re.match(r"^\d{8}T\d{6}Z-(.+)\.json$", p.name)
        if m and not m.group(1).startswith(("score", "discover-", "alive-")):
            out[m.group(1)] = p
    return out


def case_from_run(run: dict) -> Case:
    """The case exactly as the saved trail ran it: its pattern and scan window. Named cases keep their unmasked
    statement (the stance labels are stored under it)."""
    known = CASES.get(run["case"])
    return Case(
        slug=run["case"],
        title=run["title"],
        statement=known.statement if known else run["statement"],
        pattern=run["scan"]["pattern"],
        goal_match="",
        start=datetime.fromisoformat(run["scan"]["from"]),
        end=datetime.fromisoformat(run["scan"]["to"]),
        plan_pattern=known.plan_pattern if known else None,
        done_pattern=known.done_pattern if known else None,
    )


def state(stances: set[str]) -> str:
    """One snapshot: holds (an affirming line, no denying one), both (each), denies (a denying line only), or
    absent. The trail counts holds and both as holding."""
    if "affirms" in stances:
        return "both" if "denies" in stances else "holds"
    return "denies" if "denies" in stances else "absent"


HOLDING = ("holds", "both")


def episodes(states: list[str]) -> list[tuple[int, int]]:
    """Runs of consecutive holding snapshots, as (first index, last index)."""
    out, start = [], None
    for i, s in enumerate(states + ["absent"]):
        if s in HOLDING and start is None:
            start = i
        elif s not in HOLDING and start is not None:
            out.append((start, i - 1))
            start = None
    return out


@dataclass
class Gap:
    gone_from: int  # first snapshot without the belief
    back_at: int  # first snapshot holding it again
    denied_between: bool  # the agent wrote a denial while it was gone


def gaps(states: list[str], times: list[datetime], min_gap: timedelta = RETURN_GAP) -> list[Gap]:
    """Times the belief left an agent's memory for at least `min_gap` and then came back."""
    eps = episodes(states)
    out = []
    for (_, last), (first, _) in zip(eps, eps[1:]):
        if times[first] - times[last + 1] >= min_gap:
            out.append(Gap(last + 1, first, "denies" in states[last + 1:first]))
    return out


def relapse(states: list[str]) -> tuple[int, int] | None:
    """(first snapshot that denies without holding, first later snapshot that holds again with no denial beside
    it), if any. A snapshot holding the belief and its denial at once is a correction under way, not a relapse."""
    denied = next((i for i, s in enumerate(states) if s == "denies"), None)
    if denied is None:
        return None
    again = next((j for j in range(denied + 1, len(states)) if states[j] == "holds"), None)
    return (denied, again) if again is not None else None


def swarm_returns(events: list[tuple[datetime, str, bool]], min_gap: timedelta = RETURN_GAP) -> list[dict]:
    """events: (time, agent, holds) for every snapshot. An agent holds the belief from a holding snapshot until its
    next non-holding one. Returns each time no agent held it for at least `min_gap` and then one did again."""
    holders: set[str] = set()
    empty_since: datetime | None = None
    seen = False
    out = []
    for at, agent, holds in sorted(events, key=lambda e: e[0]):
        if holds:
            if not holders and seen and empty_since and at - empty_since >= min_gap:
                out.append({"gone_from": empty_since, "back_at": at, "agent": agent})
            holders.add(agent)
            seen = True
        elif agent in holders:
            holders.discard(agent)
            if not holders:
                empty_since = at
    return out


def _point(at: datetime, ref: str, k: int) -> dict:
    return {"at": at, "ref": ref, "k": k, "link": village_link(at)}


def analyse(con: duckdb.DuckDBPyConnection, run: dict) -> dict:
    """`run` is a saved trail; every per-agent holding count is compared with the trail's own."""
    case = case_from_run(run)
    models = run["counts"].get("models") or {}
    llm = SimpleNamespace(cheap=models.get("bulk"), strong=models.get("recheck"))
    current, _ = labels(con, llm, case.statement)
    pattern = re.compile(case.pattern, re.I)
    names = run["scan"]["agents"]
    ids = dict(con.execute("SELECT name, id FROM agents").fetchall())
    expected = {b["agent"]: b["snapshots_holding"] for b in run["believers"] if b["snapshots_holding"]}

    agents, events, seen_lines = [], [], set()
    for name in names:
        with console.status(f"{case.slug}: {name}"):
            snaps = _scan_agent(con, ids[name], case.start, case.end, pattern)
        states = []
        for s in snaps:
            seen_lines.update(s.lines)
            states.append(state({stance_of(case, current, line) for line in s.lines}))
            events.append((s.at, name, states[-1] in HOLDING))
        holding = sum(1 for x in states if x in HOLDING)
        if not holding:
            continue
        times = [s.at for s in snaps]
        eps = episodes(states)
        rel = relapse(states)
        agents.append({
            "agent": name,
            "snapshots": len(snaps),
            "holding": holding,
            "matches_trail": holding == expected.get(name),
            "episodes": [{"from": _point(snaps[a].at, snaps[a].id, snaps[a].k),
                          "to": _point(snaps[b].at, snaps[b].id, snaps[b].k), "snapshots": b - a + 1}
                         for a, b in eps],
            "returns": [{"gone_from": _point(snaps[g.gone_from].at, snaps[g.gone_from].id, snaps[g.gone_from].k),
                         "back_at": _point(snaps[g.back_at].at, snaps[g.back_at].id, snaps[g.back_at].k),
                         "hours_gone": round((times[g.back_at] - times[g.gone_from]).total_seconds() / 3600, 1),
                         "denied_between": g.denied_between} for g in gaps(states, times)],
            "relapse": ({"denied": _point(snaps[rel[0]].at, snaps[rel[0]].id, snaps[rel[0]].k),
                         "held_again": _point(snaps[rel[1]].at, snaps[rel[1]].id, snaps[rel[1]].k)}
                        if rel else None),
        })

    labelled = sum(1 for line in seen_lines if line_hash(line) in current)
    found = {a["agent"]: a["holding"] for a in agents}
    return {
        "kind": "lifecycle",
        "case": case.slug,
        "trail_run": run.get("saved_at"),
        "scan": {"from": case.start, "to": case.end, "pattern": case.pattern},
        "export": run["export"],
        "return_gap_hours": RETURN_GAP.total_seconds() / 3600,
        "coverage": {"lines": len(seen_lines), "labelled": labelled},
        "matches_trail": found == expected,
        "agents": agents,
        "swarm_returns": [r | {"gone_from_link": village_link(r["gone_from"]), "back_at_link": village_link(r["back_at"])}
                          for r in swarm_returns(events)],
    }


def save(data: dict) -> Path:
    ANALYSIS.mkdir(parents=True, exist_ok=True)
    path = ANALYSIS / f"lifecycle-{data['case']}.json"
    path.write_text(json.dumps(data, indent=2, default=str, ensure_ascii=False), encoding="utf-8")
    return path
