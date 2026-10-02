"""Agents by name, and links back to the live AI Village replay."""

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import duckdb

PT = ZoneInfo("America/Los_Angeles")


def village_link(ts: datetime) -> str:
    """Opens the village replay at this moment. Tested 2 Oct 2026: the site rewrites ?day= links to this form.

    Timestamps in the export are naive UTC.
    """
    utc = ts.replace(tzinfo=UTC) if ts.tzinfo is None else ts
    return f"https://theaidigest.org/village?date={utc.astimezone(PT):%Y-%m-%d}&time={int(utc.timestamp() * 1000)}"


def find_agent(con: duckdb.DuckDBPyConnection, query: str) -> tuple[str, str]:
    """Match an agent by exact name, id prefix, or a unique part of its name ("o3", "opus 4", "e7206d8d")."""
    rows = con.execute("SELECT id, name FROM agents ORDER BY created_at").fetchall()
    q = query.strip().lower()
    for pick in (
        [r for r in rows if r[1].lower() == q],
        [r for r in rows if r[0].startswith(q)],
        [r for r in rows if q in r[1].lower()],
    ):
        if len(pick) == 1:
            return pick[0]
        if len(pick) > 1:
            raise ValueError(f"'{query}' matches {len(pick)} agents: {', '.join(r[1] for r in pick)}")
    raise ValueError(f"no agent matches '{query}'")
