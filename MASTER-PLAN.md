# MASTER-PLAN.md — Heirloom

Due **Mon Oct 5, 9:30 AM IST** (Sun 9 PM PT). Submit target **Mon 6:00 AM IST**. Building early is allowed.
Each phase ends with something that runs. The validation case (93-list) is the test the whole pipeline must pass.

Calendar: today is Fri Oct 2. The BAND Dark Factory final run is planned for Sun Oct 4 (it's a dark run — Rohit
dispatches it and it runs on its own), due Tue Oct 6 12:29 PM IST. Plan Heirloom's heavy LLM runs around it.

**Status 2 Oct 20:30 IST:** Phases 0–4 done (see PROGRESS.md). Score 5/6 public 2025 cases; discovery validated
(93 list rank 5 unaided); 2026: five monitor-seeded trails, hand-checked. LLM spend $5.51 of $6.00. Next: Phase 5.

## Phase 0 — Setup (Fri Oct 2)
- [ ] Hugging Face **read token** (huggingface.co/settings/tokens) → `HF_TOKEN` in `.env` (never committed).
- [ ] LLM key in `.env`; `LLM_PROVIDER` switch. Set a spend cap on the provider dashboard.
- [ ] Free disk: ~6 GB for the tables (memories 2.44 GB gz, turns 2.48 GB gz, events 329 MB, chat 52 MB, sessions
      40 MB, small tables) + the DuckDB file. Check before downloading.
- [ ] `uv init pipeline` (official command). Deps: duckdb, huggingface_hub, the LLM SDK, pydantic, typer, rich.
- [ ] Download only the tables we need (see `docs/DATA-MAP.md`) with `hf_hub_download`, record the export date from
      `manifest.json`.
- Done when: DuckDB opens all tables and `select count(*)` matches `manifest.json` roughly.

## Phase 1 — Windows + diff (Fri night → Sat morning)
- Per agent: snapshots ordered by `created_at`; window k = (snapshot k-1, snapshot k].
- Window contents: the agent's turns, its chat messages, room chat it could see, human messages, search answers.
- Line diff per snapshot pair: added / changed / vanished lines; flag compressions (length drops > 30%).
- **Test on the 93 case first:** agents o3 `e7206d8d`, Gemini 2.5 Pro `d5fd932e`, Claude 3.7 Sonnet `8e2f2b1b`,
  Claude Opus 4 `b7a559c6`; dates 2025-06-05 → 2025-06-20. The diff must surface the first "93" line per agent.
- Done when: `heirloom windows --agent o3 --from 2025-06-10 --to 2025-06-13` prints windows with their diffs.

## Phase 2 — Claims + tie-out (Sat)
- Claim extraction prompt (cheap model) over added/changed lines only; anchors verbatim.
- Tie-out prompt (strong model) only for claims with an anchor or a "exists / done / broken / note-to-self" shape.
- Labels: supported / contradicted / no evidence / hearsay / instruction — each with the evidence quote + link.
- Cache every LLM call on disk (hash of prompt) — re-runs are free.
- Done when: on the 93 window set, the 93-list claim is labelled hearsay/no-evidence at birth and contradicted by
  13 Jun, with the right quotes.

## Phase 3 — Lineage + the trail (Sat night)
- Inheritance: same claim in later snapshots of the same agent (anchor match, then fuzzy).
- Spread: first appearance in another agent's snapshot; carrier = the chat message between them that holds the
  anchor, sent before the receiving snapshot.
- Correction: the first window where the claim is contradicted and the next snapshot drops or negates it.
- Trail JSON per belief; `heirloom trail --case 93-list` writes it.
- Done when: the 93 trail matches `docs/KNOWN-CASES.md` (birth, believers, correction, last mention).

## Phase 4 — New findings on 2026 data (Sun morning IST)
- Pick windows: the last 60 days of the export, all agents (or the most active 10 if cost bites).
- Run the full pipeline; rank beliefs by (alive × age in rewrites × number of agents carrying it).
- **Hand-check the top 10** against the raw rows before calling anything a finding. Only verified ones go in the
  results write-up.
- Done when: a "still alive" list of ≥ 5 hand-verified beliefs with trails.

## Phase 5 — Viewer (Sun)
- `create-next-app` viewer + FastAPI over DuckDB results.
- Screens: the Belief Trail (timeline, agent swimlanes, born/written/inherited/spread/corrected nodes), the evidence
  panel (memory line ↔ contrary evidence, live-village link), the "still alive" list, the numbers page.
- Mask human names/emails in every rendered string.
- Done when: the 60-second demo path runs in the browser.

## Phase 6 — Write-up, video, submit (Sun night → Mon 6:00 AM IST)
- README + `docs/WRITEUP.md` final + results write-up with every number from `runs/`.
- Video (aim ≤ 3 min): the demo script in `CLAUDE.md`.
- Submit as the hosts specify; save the confirmation; update the sheet; log in `IDEAS-LOG.md`.

## If time runs short, cut in this order
1. Screenshot checks (keep text evidence only)
2. Cross-agent spread beyond the first carrier (keep born → memory → corrected per agent)
3. The viewer's agent swimlanes (keep the timeline + evidence panel)
4. 2026 coverage (fewer agents, keep the hand-verified findings)
5. **Never cut:** the 93-list trail rebuilt from raw data, evidence quotes with live links, at least a few
   hand-verified new findings, privacy masking, the citation.
