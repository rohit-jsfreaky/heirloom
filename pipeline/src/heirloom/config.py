"""Paths and settings shared by every Heirloom command."""

import os
from pathlib import Path

from dotenv import load_dotenv

# pipeline/src/heirloom/config.py -> the heirloom repo root
ROOT = Path(os.environ.get("HEIRLOOM_ROOT") or Path(__file__).resolve().parents[3])
load_dotenv(ROOT / ".env")

DATA = ROOT / "data"
RAW = DATA / "raw"
DB_PATH = DATA / "heirloom.duckdb"
DUCKDB_TMP = DATA / "duckdb_tmp"
DUCKDB_MEMORY = os.environ.get("HEIRLOOM_DUCKDB_MEMORY", "6GB")

REPO_ID = "aidigestorg/ai-village"
# The export every number in the write-up comes from (manifest exportedAt 2026-09-20T13:05:12Z).
PINNED_REVISION = "838b4150303ca8228e8edb432d8b8ccae353d258"
