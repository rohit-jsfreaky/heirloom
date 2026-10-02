# DATA-MAP.md — the AI Village dataset, as Heirloom uses it

Source: https://huggingface.co/datasets/aidigestorg/ai-village (gated; access granted 1 Oct 2026). Card, `SCHEMA.md`
and `CHANGELOG.md` read 1–2 Oct. All tables = gzipped JSON Lines, near-verbatim Postgres dumps. Refreshed ~weekly
(the export we read was ~11 days old on 1 Oct) — record `manifest.json.exportedAt` with every run.

## Conventions (SCHEMA.md)
- ids = UUID strings. Timestamps like `2025-12-29 18:49:21.291984` — **UTC**, no suffix.
- Scrub markers: `[REDACTED]` (credentials, infra), `[BLOB_REMOVED]`, `[IMAGE_REMOVED]`.
- `agent_messages` / `data.output` shapes **vary by provider** (Anthropic content blocks; OpenAI Responses items with
  `reasoning` summaries; chat completions; Gemini `candidates.parts` with `"thought": true`). Match on
  `agents.model_string`.
- Village day 1 = 2025-04-02, increments ~17:00 UTC, skips most weekends (in 2025 every calendar day counted:
  Day 73 = 2025-06-13). **Site link (tested 2 Oct):** `https://theaidigest.org/village?date=YYYY-MM-DD&time={unix_ms}`
  — the site rewrites `?day={day}&time=` to this form, and the replay opens at that moment. The page shows times in
  the viewer's local timezone.

## Tables we download

Export in use: **`exportedAt` 2026-09-20T13:05:12Z**, repo last modified 2026-09-20 13:54 UTC (revision `838b415030…`).
Sizes = HF file list, rows = `manifest.json.rowCounts` (both read 2 Oct). The older row counts in this file came
from the HF viewer and were too low.

| table | size (gz) | rows | what we use |
|---|---|---|---|
| `agent_memories.jsonl.gz` | 2.44 GB | 246,151 | `id, content, agent_id, created_at` — the full memory text at each rewrite (avg ~28.6k chars, max ~809k) |
| `events.jsonl.gz` | 329 MB | 381,610 | `event_index` (canonical order), `data.actionType`, `created_at`: `AGENT_TALK`, `USER_TALK`, `START/STOP_USING_COMPUTER` (+ `summary` = the agent's own session summary), `CONSOLIDATE` (2026: agentId, computerUseSessionId, nextSessionGoal), `SEARCH_HISTORY` (query + answer), `ENTER_ROOM`, `REQUEST_HUMAN_HELPER`… |
| `chat_messages.jsonl.gz` | 52.5 MB | 183,485 | `speaker_type`, `agent_speaker_id`, `content`, `room_id`, `created_at` |
| `computer_use_turns.jsonl.gz` | 2.48 GB | 2,510,487 | `session_id`, `agent_action`, `agent_messages` (raw model response incl. thinking), `output` (~62% null), `error`, `created_at`; screenshot = `<id>.png` in `images/computer-use-turns/<PT-date>.tar` (370 tars). Dropped from the export: `base64_image`, `redaction_reason` |
| `computer_use_sessions.jsonl.gz` | 40.1 MB | 78,362 | `agent_id`, `session_goal`, `created_at` |
| `summaries.jsonl.gz` | 2.9 MB | 939 | secondary — only to compare against |
| `agents.jsonl.gz` | 5 KB | 46 | `id, name, model_string, created_at` |
| `village_goals.jsonl.gz`, `agent_goals.jsonl.gz`, `chat_rooms.jsonl.gz`, `manifest.json` | tiny | | context + export date |

Also downloaded: `SCHEMA.md`, `CHANGELOG.md`, `README.md`, `example.py` (the hosts' own loading example — read it
before writing the loader). Skip: `claude_code_*` (one agent, Jan–Apr 2026, 104 MB), `village-transcript.json`
(362 MB, a rendering of events + chat), screenshot tars (stretch only, by day). `summaries` are generated without
seeing computer use — use only to compare.

Laptop: 11.7 GB RAM → give DuckDB a `memory_limit` (~6 GB) and a `temp_directory` under `data/` so the memories
load can spill to disk.

## The two eras (CHANGELOG)
- **Before 2026-03-24:** discrete computer-use sessions (`START/STOP_USING_COMPUTER`). Memory rewrites were
  **frequent** — verified: o3 wrote 45 snapshots on 2025-06-12 with one computer session that day. Memory rows carry no
  session id.
- **From 2026-03-24 ("perma-computer-use"):** agents are always in computer use; every ~40 actions a `CONSOLIDATE`
  event; memory labels use time ranges. Treat the two as different regimes in every statistic.
- Other scaffolding changes that affect memory (CHANGELOG): consolidation prompt tweaks ("keep more of their memory"),
  chain-of-thought for consolidation, a `consolidate` tool for Anthropic agents, rooms (2026-02-25) changing who sees
  which chat, unseen events capped at 200 per turn. → a change in behaviour on those dates may be scaffolding.

## The join Heirloom is built on
```
snapshot(agent A, k) = agent_memories row, ordered by created_at within A
window(A, k)          = (snapshot(A,k-1).created_at, snapshot(A,k).created_at]
evidence(A, k)        = computer_use_turns of A's sessions in the window      (action, output, error)
                      + chat_messages in the window from rooms A was in       (incl. A's own messages)
                      + events of A in the window: SEARCH_HISTORY answers, STOP_USING_COMPUTER summaries
                      + USER_TALK (humans) in the window
2026 refinement       : CONSOLIDATE.computerUseSessionId pins the 40 actions behind snapshot k
```
Room membership before 2026-02-25: one shared chat. After: `ENTER_ROOM` events give each agent's room over time.

## Loading
- Download with `huggingface_hub.hf_hub_download(repo_id="aidigestorg/ai-village", repo_type="dataset",
  filename=..., token=HF_TOKEN)`.
- DuckDB reads gzipped JSONL directly (`read_json(..., format='newline_delimited')`); materialise into
  `heirloom.duckdb` once, with indexes/sort on (agent_id, created_at). Verify the exact DuckDB function names in the
  live docs on the day.
- Very long memory texts (up to ~809k chars): keep them in DuckDB, diff in Python one pair at a time.
