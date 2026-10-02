"""One way to open the Heirloom DuckDB file, with limits that fit an 11.7 GB laptop."""

import duckdb

from heirloom.config import DB_PATH, DUCKDB_MEMORY, DUCKDB_TMP


def connect(read_only: bool = False) -> duckdb.DuckDBPyConnection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    DUCKDB_TMP.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DB_PATH), read_only=read_only)
    con.execute(f"SET memory_limit = '{DUCKDB_MEMORY}'")
    con.execute(f"SET temp_directory = '{DUCKDB_TMP.as_posix()}'")
    # Big CREATE TABLE ... ORDER BY loads spill to disk instead of running out of RAM.
    con.execute("SET preserve_insertion_order = false")
    return con
