"""Is a belief still held today? Checks the live AI Village, after the export ended.

For each agent a saved trail found still holding the belief at the end of the export, read the agent's newest memory
snapshots from the village's public API and look for the trail's own pattern. Saves counts, ids and times only.
"""

import json
import re
import time
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

import duckdb

from heirloom.diff import body_of, lines_in_context
from heirloom.lifecycle import ANALYSIS, case_from_run, latest_runs

API = "https://theaidigest.org/village/api"


def newest_memories(agent_id: str) -> list[dict]:
    """The public endpoint returns the agent's newest snapshots (10 at the time of writing), oldest first here."""
    req = urllib.request.Request(f"{API}/agent/{agent_id}/memories", headers={"Accept": "application/json",
                                                                           "User-Agent": "heirloom-research"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        memories = json.load(resp).get("memories", [])
    return sorted(memories, key=lambda m: m["createdAt"])


def check(con: duckdb.DuckDBPyConnection, slug: str) -> dict:
    run = json.loads(latest_runs()[slug].read_text(encoding="utf-8"))
    pattern = re.compile(case_from_run(run).pattern, re.I)
    ids = dict(con.execute("SELECT name, id FROM agents").fetchall())
    agents = []
    for b in run["believers"]:
        if b["status"] != "held at end of scan":
            continue
        memories = newest_memories(ids[b["agent"]])
        holding = [m for m in memories
                   if any(pattern.search(body_of(line)) for line in lines_in_context(m["content"]))]
        agents.append({
            "agent": b["agent"],
            "last_held_in_export": b["last_held"]["at"],
            "snapshots_read": len(memories),
            "from": memories[0]["createdAt"] if memories else None,
            "to": memories[-1]["createdAt"] if memories else None,
            "snapshots_matching_pattern": len(holding),
            "matching_ids": [m["id"] for m in holding],
        })
        time.sleep(1)
    return {
        "kind": "live-check",
        "case": slug,
        "checked_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "source": f"{API}/agent/<id>/memories (public, read-only)",
        "pattern": run["scan"]["pattern"],
        "note": ("A match only means the pattern appears; zero matches means the belief is not in any of these "
                 "snapshots. The endpoint shows only the newest snapshots, so when and how it left is not visible."),
        "agents": agents,
    }


def save(data: dict) -> Path:
    ANALYSIS.mkdir(parents=True, exist_ok=True)
    path = ANALYSIS / f"live-{data['case']}.json"
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return path
