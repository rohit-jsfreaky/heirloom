"""Snapshots and the evidence window between them.

For snapshot k of agent A, the window is (snapshot k-1, snapshot k]: everything A did, saw or was told between two
memory rewrites. Same rule in both eras (2025: rewrites every few seconds to minutes; 2026: CONSOLIDATE every ~40
actions).
"""

from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime

import duckdb

from heirloom.diff import Diff, diff


@dataclass
class Snapshot:
    id: str
    agent_id: str
    created_at: datetime
    content: str


@dataclass
class Evidence:
    source: str  # turn | chat | human | search | session_summary | consolidate
    id: str
    created_at: datetime
    speaker: str  # agent name, "[person]" for humans, or the tool
    text: str


@dataclass
class Window:
    agent_id: str
    k: int  # index of the snapshot within the agent's whole history (0 = first ever)
    prev: Snapshot | None
    snap: Snapshot
    diff: Diff
    evidence: list[Evidence] = field(default_factory=list)

    @property
    def start(self) -> datetime | None:
        return self.prev.created_at if self.prev else None


def snapshots(con: duckdb.DuckDBPyConnection, agent_id: str, start: datetime, end: datetime
              ) -> Iterator[tuple[int, Snapshot]]:
    """Snapshots with created_at in [start, end], plus the one just before start (the k-1 of the first window)."""
    k0, = con.execute(
        "SELECT count(*) FROM agent_memories WHERE agent_id = ? AND created_at < ?", [agent_id, start]
    ).fetchone()
    rows = con.execute(
        """
        (SELECT id, created_at, content FROM agent_memories
          WHERE agent_id = $agent AND created_at < $start ORDER BY created_at DESC LIMIT 1)
        UNION ALL
        (SELECT id, created_at, content FROM agent_memories
          WHERE agent_id = $agent AND created_at >= $start AND created_at <= $end)
        ORDER BY created_at
        """,
        {"agent": agent_id, "start": start, "end": end},
    ).fetchall()
    first_k = k0 - 1 if k0 else 0
    for i, (sid, ts, content) in enumerate(rows):
        yield first_k + i, Snapshot(sid, agent_id, ts, content)


def windows(con: duckdb.DuckDBPyConnection, agent_id: str, start: datetime, end: datetime,
            with_evidence: bool = True) -> Iterator[Window]:
    prev: Snapshot | None = None
    for k, snap in snapshots(con, agent_id, start, end):
        if snap.created_at >= start:
            w = Window(agent_id, k, prev, snap, diff(prev.content if prev else None, snap.content))
            if with_evidence and w.diff and prev is not None:
                w.evidence = evidence(con, agent_id, prev.created_at, snap.created_at)
            yield w
        prev = snap


def room_timeline(con: duckdb.DuckDBPyConnection, agent_id: str, until: datetime):
    """Which chat room the agent was in at a given time. Everyone starts in #general; ENTER_ROOM moves them."""
    general, = con.execute("SELECT id FROM chat_rooms WHERE name = 'general'").fetchone()
    moves = con.execute(
        """SELECT created_at, data->>'roomId' FROM events
           WHERE action_type = 'ENTER_ROOM' AND agent_id = ? AND created_at <= ? ORDER BY event_index""",
        [agent_id, until],
    ).fetchall()

    def room_at(ts: datetime) -> str:
        room = general
        for at, rid in moves:
            if at > ts:
                break
            room = rid
        return room

    return room_at


def evidence(con: duckdb.DuckDBPyConnection, agent_id: str, t0: datetime, t1: datetime) -> list[Evidence]:
    """Everything in (t0, t1] the agent did, saw or was told."""
    window = {"agent": agent_id, "t0": t0, "t1": t1}
    items: list[Evidence] = []

    # The agent's own computer use: what it did and what the tools said back.
    for tid, ts, action, output, error in con.execute(
        """SELECT id, created_at, agent_action, output, error FROM computer_use_turns
           WHERE agent_id = $agent AND created_at > $t0 AND created_at <= $t1 ORDER BY created_at""",
        window,
    ).fetchall():
        parts = [f"action: {action}" if action else "", f"output: {output}" if output else "",
                 f"error: {error}" if error else ""]
        items.append(Evidence("turn", tid, ts, "tool", "\n".join(p for p in parts if p)))

    # Chat the agent could see: only the room it was in at the time (rooms exist since 2026-03; one room at a time).
    in_room = room_timeline(con, agent_id, t1)
    for mid, ts, speaker_type, name, content, room in con.execute(
        """SELECT c.id, c.created_at, c.speaker_type, a.name, c.content, c.room_id FROM chat_messages c
           LEFT JOIN agents a ON a.id = c.agent_speaker_id
           WHERE c.created_at > $t0 AND c.created_at <= $t1 ORDER BY c.created_at""",
        {"t0": t0, "t1": t1},
    ).fetchall():
        if room != in_room(ts):
            continue
        human = speaker_type != "agent"
        items.append(Evidence("human" if human else "chat", mid, ts, "[person]" if human else name, content))

    # The agent's searches, its own session summaries, and its consolidation notes.
    for eid, ts, kind, query, answer, summary, goal in con.execute(
        """SELECT id, created_at, action_type, data->>'query', data->>'answerToQuery', data->>'summary',
                  data->>'nextSessionGoal'
           FROM events
           WHERE agent_id = $agent AND created_at > $t0 AND created_at <= $t1
             AND action_type IN ('SEARCH_HISTORY', 'STOP_USING_COMPUTER', 'CONSOLIDATE')
           ORDER BY event_index""",
        window,
    ).fetchall():
        if kind == "SEARCH_HISTORY":
            items.append(Evidence("search", eid, ts, "search", f"Q: {query}\nA: {answer}"))
        elif kind == "STOP_USING_COMPUTER" and summary:
            items.append(Evidence("session_summary", eid, ts, "self", summary))
        elif kind == "CONSOLIDATE" and goal:
            items.append(Evidence("consolidate", eid, ts, "self", f"next goal: {goal}"))

    items.sort(key=lambda e: e.created_at)
    return items
