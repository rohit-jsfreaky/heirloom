"""Known-case recall: does each rebuilt trail match what the public accounts say? (METHOD.md §8)"""

import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

from heirloom.config import ROOT
from heirloom.trail import RUNS, Case


def score(case: Case, trail: dict) -> dict:
    held = [b for b in trail["believers"] if b["status"] != "never held"]
    origin = [n["agent"] for n in (trail["first_said_in_chat"], trail["born"]) if n and n.get("agent")]
    birth_ok = None if case.expect_birth is None else any(case.expect_birth in a for a in origin)
    names = [b["agent"] for b in held]
    found = [e for e in case.expect_believers if e in names]
    corrected = bool(trail["human_corrections"] or trail["agent_corrections"] or any(b["first_denial"] for b in held))
    tieouts = [n["tieout"] for b in held for n in (b["first_held"], b["first_denial"]) if n and n.get("tieout")]
    quotes = sum(len(t["evidence"]) for t in tieouts)
    return {
        "case": case.slug,
        "title": case.title,
        "source": case.source,
        "origin": origin,
        "birth_agent_ok": birth_ok,
        "believers": names,
        "expected_believers_found": f"{len(found)}/{len(case.expect_believers)}" if case.expect_believers else None,
        "correction_found": corrected,
        "correction_ok": None if case.expect_correction is None else corrected == case.expect_correction,
        "tieouts": len(tieouts),
        "verified_quotes": quotes,
        "dropped_quotes": sum(t.get("dropped_quotes", 0) for t in tieouts),
        "labels": [t["label"] for t in tieouts],
        "snapshots_scanned": trail["counts"]["snapshots_scanned"],
    }


def save(rows: list[dict], export: dict) -> str:
    RUNS.mkdir(exist_ok=True)
    path = RUNS / f"{datetime.now(UTC):%Y%m%dT%H%M%SZ}-score.json"
    path.write_text(json.dumps({"kind": "score", "export": export, "cases": rows}, indent=2, default=str,
                               ensure_ascii=False), encoding="utf-8")
    return str(path)


def latest_discover() -> Path:
    """The newest `discover` or `alive` run (file names start with a UTC timestamp, so they sort by time)."""
    runs = sorted([*RUNS.glob("*-discover-*.json"), *RUNS.glob("*-alive-*.json")], key=lambda p: p.name)
    if not runs:
        raise FileNotFoundError("no discover/alive run in runs/: run `heirloom discover` or `heirloom alive` first")
    return runs[-1]


def belief_case(belief_id: str, run: Path | None = None, tail_days: int = 21) -> Case:
    """Turn a discovered belief into a Case, so `heirloom trail` can follow it like a named one."""
    data = json.loads((run or latest_discover()).read_text(encoding="utf-8"))
    pool = data["ranked"] + data.get("unchecked_head", [])
    b = next((x for x in pool if x["id"] == belief_id), None)
    if b is None:
        raise ValueError(f"belief {belief_id} is not in {run or latest_discover()}")
    parts = []
    for a in b["anchors"]:
        if "[" in a:  # masked email or name: not searchable
            continue
        m = re.match(r"^(\d[\d,.]*) (\S+)$", a)
        parts.append(rf"\b{re.escape(m.group(1))}\b[\s-]*{re.escape(m.group(2))}" if m else re.escape(a))
    if not parts:
        raise ValueError(f"belief {belief_id} has no searchable anchor")
    born = datetime.fromisoformat(str(b["born"]["at"]))
    scan_end = datetime.fromisoformat(str(data["scan"]["to"]))
    claim = (b.get("claim") or {}).get("text") or b["line"]
    return Case(
        slug=f"belief-{belief_id}",
        title=claim[:80],
        statement=claim,
        pattern="|".join(parts),
        goal_match="",
        start=born - timedelta(days=1),
        end=scan_end + timedelta(days=tail_days),
    )


__all__ = ["score", "save", "belief_case", "latest_discover", "ROOT"]
