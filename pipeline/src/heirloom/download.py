"""Download the AI Village tables Heirloom needs from Hugging Face (gated dataset, needs HF_TOKEN)."""

import os

from huggingface_hub import HfApi, snapshot_download

from heirloom.config import RAW, REPO_ID

FILES = [
    "agent_memories.jsonl.gz",
    "computer_use_turns.jsonl.gz",
    "events.jsonl.gz",
    "chat_messages.jsonl.gz",
    "computer_use_sessions.jsonl.gz",
    "agents.jsonl.gz",
    "village_goals.jsonl.gz",
    "agent_goals.jsonl.gz",
    "chat_rooms.jsonl.gz",
    "villages.jsonl.gz",
    "summaries.jsonl.gz",
    "manifest.json",
    "SCHEMA.md",
    "CHANGELOG.md",
    "README.md",
]


def latest_revision() -> str:
    return HfApi(token=os.environ.get("HF_TOKEN")).dataset_info(REPO_ID).sha


def download(revision: str) -> None:
    snapshot_download(
        repo_id=REPO_ID,
        repo_type="dataset",
        revision=revision,
        allow_patterns=FILES,
        local_dir=RAW,
        token=os.environ.get("HF_TOKEN"),
    )


def downloaded_revision() -> str | None:
    """The commit the files in data/raw came from (huggingface_hub writes it next to each file)."""
    meta = RAW / ".cache" / "huggingface" / "download" / "manifest.json.metadata"
    if not meta.exists():
        return None
    return meta.read_text().splitlines()[0].strip()
