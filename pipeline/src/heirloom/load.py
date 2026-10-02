"""Load the AI Village export into DuckDB.

Every column is typed by hand: auto-detection reads a sample and guesses wrong (events.data.cost came back as
BIGINT). Big tables are sorted by (agent_id, created_at) so per-agent time-window queries stay fast.
"""

import json
import time
from dataclasses import dataclass

import duckdb
from rich.console import Console
from rich.progress import track
from rich.table import Table

from heirloom.config import RAW
from heirloom.download import downloaded_revision

V, TS = "VARCHAR", "TIMESTAMP"
console = Console()


@dataclass(frozen=True)
class Spec:
    table: str
    source: str  # file in data/raw
    columns: dict[str, str]
    select: str = "*"
    joins: str = ""
    order_by: str | None = None
    # Too big to sort in one go (7 GB of memory text ran a 6 GB cap out of memory): stage unsorted, then copy
    # one agent at a time in created_at order. Result is sorted by (agent_id, created_at).
    by_agent: bool = False
    manifest_key: str | None = None  # row count to compare against; defaults to the table name


SPECS = [
    Spec("agents", "agents", {"id": V, "name": V, "model_string": V, "is_participating": "BOOLEAN", "created_at": TS}),
    Spec("village_goals", "village_goals", {"id": V, "goal": V, "start_time": TS, "end_time": TS},
         order_by="start_time"),
    Spec("agent_goals", "agent_goals",
         {"id": V, "agent_id": V, "name": V, "short_name": V, "description": V, "start_time": TS, "end_time": TS},
         order_by="agent_id, start_time"),
    Spec("chat_rooms", "chat_rooms", {"id": V, "name": V, "created_at": TS, "deleted_at": TS}),
    Spec("summaries", "summaries",
         {"id": V, "type": V, "summary_target": V, "summary_date": "DATE", "content": V, "generated_by": V,
          "created_at": TS},
         order_by="created_at"),
    Spec("events", "events",
         {"id": V, "event_index": "BIGINT", "data": "JSON", "created_at": TS},
         # USER_TALK puts the human's id in speakerId, so speakerId only names an agent on AGENT_TALK.
         select="""id, event_index, data->>'actionType' AS action_type,
                   coalesce(data->>'agentId',
                            CASE WHEN (data->>'actionType') = 'AGENT_TALK' THEN data->>'speakerId' END) AS agent_id,
                   data->>'roomId' AS room_id, created_at, data""",
         order_by="event_index"),
    Spec("chat_messages", "chat_messages",
         {"id": V, "speaker_type": V, "agent_speaker_id": V, "user_speaker_id": V, "content": V, "room_id": V,
          "created_at": TS},
         order_by="created_at"),
    Spec("computer_use_sessions", "computer_use_sessions",
         {"id": V, "agent_id": V, "session_goal": V, "created_at": TS},
         order_by="agent_id, created_at"),
    Spec("agent_memories", "agent_memories", {"id": V, "agent_id": V, "content": V, "created_at": TS},
         by_agent=True),
    # Turns carry no agent_id: it comes from the session. Needs computer_use_sessions loaded first.
    Spec("computer_use_turns", "computer_use_turns",
         {"id": V, "session_id": V, "agent_action": "JSON", "output": V, "error": V, "system": V,
          "screenshot_is_redacted": "BOOLEAN", "created_at": TS},
         select="t.id, s.agent_id, t.session_id, t.agent_action, t.output, t.error, t.system, "
                "t.screenshot_is_redacted, t.created_at",
         joins="LEFT JOIN computer_use_sessions s ON s.id = t.session_id",
         by_agent=True),
    # The raw model response per turn (reasoning + what the agent said it saw). Kept apart so the turns table
    # stays light; join on id when a window needs it.
    Spec("turn_messages", "computer_use_turns", {"id": V, "agent_messages": "JSON"},
         manifest_key="computer_use_turns"),
]


def _source_sql(spec: Spec) -> str:
    path = (RAW / f"{spec.source}.jsonl.gz").as_posix()
    cols = ", ".join(f"'{name}': '{typ}'" for name, typ in spec.columns.items())
    return f"read_json('{path}', format = 'newline_delimited', columns = {{{cols}}})"


def load_table(con: duckdb.DuckDBPyConnection, spec: Spec) -> None:
    alias = " t" if spec.joins else ""
    select = f"SELECT {spec.select} FROM {_source_sql(spec)}{alias} {spec.joins}"
    if not spec.by_agent:
        order = f" ORDER BY {spec.order_by}" if spec.order_by else ""
        con.execute(f"CREATE OR REPLACE TABLE {spec.table} AS {select}{order}")
        return

    stage = f"_stage_{spec.table}"
    con.execute(f"CREATE OR REPLACE TABLE {stage} AS {select}")
    con.execute(f"CREATE OR REPLACE TABLE {spec.table} AS FROM {stage} LIMIT 0")
    agents = [r[0] for r in con.execute(f"SELECT DISTINCT agent_id FROM {stage} ORDER BY 1 NULLS LAST").fetchall()]
    con.execute("SET enable_progress_bar = false")  # rich draws the per-agent bar instead
    for agent in track(agents, description="  sorting by agent", console=console):
        con.execute(
            f"INSERT INTO {spec.table} FROM {stage} WHERE agent_id IS NOT DISTINCT FROM ? ORDER BY created_at",
            [agent],
        )
    con.execute("SET enable_progress_bar = true")
    con.execute(f"DROP TABLE {stage}")
    con.execute("CHECKPOINT")


def write_meta(con: duckdb.DuckDBPyConnection, manifest: dict) -> None:
    con.execute(
        # Naive UTC like every other timestamp in the export (a TIMESTAMPTZ would need pytz to read back).
        "CREATE OR REPLACE TABLE meta AS SELECT timezone('UTC', ?::TIMESTAMPTZ) AS exported_at, ? AS revision, "
        "timezone('UTC', now()) AS loaded_at, ? AS duckdb_version",
        [manifest["exportedAt"], downloaded_revision(), duckdb.__version__],
    )


def check_counts(con: duckdb.DuckDBPyConnection, manifest: dict) -> bool:
    expected = manifest["rowCounts"]
    out = Table(title=f"heirloom.duckdb vs manifest.json (export {manifest['exportedAt']})")
    for col, justify in [("table", "left"), ("rows in DuckDB", "right"), ("rows in manifest", "right"), ("", "center")]:
        out.add_column(col, justify=justify)
    loaded = {r[0] for r in con.execute("SELECT table_name FROM information_schema.tables").fetchall()}
    all_ok = True
    for spec in SPECS:
        want = expected.get(spec.manifest_key or spec.table)
        if spec.table not in loaded:
            all_ok = False
            out.add_row(spec.table, "not loaded", f"{want:,}", "✗")
            continue
        got = con.execute(f"SELECT count(*) FROM {spec.table}").fetchone()[0]
        ok = got == want
        all_ok &= ok
        out.add_row(spec.table, f"{got:,}", f"{want:,}", "✓" if ok else "✗")
    console.print(out)

    if "computer_use_turns" in loaded:
        orphans = con.execute("SELECT count(*) FROM computer_use_turns WHERE agent_id IS NULL").fetchone()[0]
        if orphans:
            console.print(f"[yellow]{orphans:,} turns have no session row, so no agent_id[/yellow]")
    return all_ok


def run(con: duckdb.DuckDBPyConnection, only: list[str] | None = None) -> bool:
    manifest = json.loads((RAW / "manifest.json").read_text())
    unknown = set(only or []) - {s.table for s in SPECS}
    if unknown:
        raise ValueError(f"unknown table(s): {', '.join(sorted(unknown))}")
    # Measured on the 11.7 GB laptop: 4 threads stage the 7 GB memories table inside the 6 GB cap.
    con.execute("SET threads = 4")

    for spec in SPECS:
        if only and spec.table not in only:
            continue
        console.print(f"loading [bold]{spec.table}[/bold] …")
        start = time.perf_counter()
        load_table(con, spec)
        console.print(f"  done in {time.perf_counter() - start:,.1f} s")

    write_meta(con, manifest)
    return check_counts(con, manifest)
