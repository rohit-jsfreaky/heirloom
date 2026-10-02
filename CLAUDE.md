# CLAUDE.md — Heirloom (read this first, every session)

**Heirloom = the life of a false belief inside a group of AI agents.**

> **The monitor catches the lie. Heirloom shows who still believes it.**

AI agents in long-running groups rewrite their own memory all the time (in the AI Village: every ~40 actions since
March 2026, and every few minutes in 2025). Nothing checks that what goes into memory is true. A wrong belief gets
written down as a fact, read back as a fact, and copied by other agents — the June 2025 "93-person contact list"
that never existed cost the whole village days. Heirloom follows each false belief from the moment it is born
(next to the agent's own evidence that contradicts it), into memory, across rewrites, across agents, until it is
corrected — or until today, still alive. Every step links to the exact moment in the live AI Village.

Built for the **AI Swarm Dynamics Hackathon** (AI Village × Grove Research). Online. **Submissions due Sun Oct 4,
5:00 PM PT = Mon Oct 5, 5:30 AM IST** (changed 3 Oct — form link in the Swarmchasing Slack; our target 2:00 AM IST).
Building early is allowed. Solo. Rohit is registered (22 Sep) and has dataset
access (1 Oct). Rules are in `hackathon.md` — it outranks everything here.

Idea research: `D:\my_projects\hackathon_ideas\contexts\ai-swarm-dynamics*.md` (context, SOURCES, FIELD, BANLIST, IDEA).
`RESEARCH.md` here holds only the facts the build depends on, each with a source.

## ⛔ Locked decisions (2 Oct 2026)

1. **Claude writes the code** (changed 2 Oct by Rohit: "i am not writing code okay you do this"). Claude builds,
   runs and tests each piece end to end; Rohit steers and does git.
2. **Rohit does all git.** Never commit, never push, never create repos. Hand him a one-line commit message when a
   piece of work finishes.
3. **Official commands and live docs first** (`uv init`, `create-next-app`, the `huggingface_hub` and DuckDB docs).
   Never hand-write scaffolds.
4. **Dataset terms are hard rules:** research and analysis only; **no training or fine-tuning** on the data; **no
   re-identification of people**; cite "AI Digest / AI Village" everywhere results appear. If a credential shows up
   in the data, never use it — note it for the hosts.
5. **People's privacy on screen:** human names, emails and phone numbers inside agent memories are masked in every
   UI view and in the write-up (`[person]`, `[email]`). Agents are named; humans are not.
6. **Evidence beats narration.** A belief is "false" only when the agent's own window contains contrary evidence
   (tool output, error, another agent's or a human's correction, a screenshot) — never because an LLM thinks so.
   Labels: `supported`, `contradicted`, `no evidence`, `hearsay` (came from another agent's message), `instruction`
   (a note telling a future self to act). Every label shows the evidence quote and its link.
7. **Never fake a number.** Counts, timings and "caught x/y" come from real runs on the real data, with the export
   date. If something can't be reconstructed, the write-up says so.
8. **We never pitch "detection".** The Village's own monitor already flags fabrications on the day. Our unit is the
   *lifecycle*: birth → memory → inheritance → spread → correction / still alive.
9. **Never use the phrase "provenance memory"** (a crowded product label outside). Say "belief trail".
10. **Look:** calm pro research tool. Hanken Grotesk for text, a mono face for timestamps and ids, Phosphor icons.
    Cool near-black / cool grey, one accent Klein blue `#002FA7`. **A belief that is false or still alive = amber.**
    Never red, cream, beige, Inter, Material or Lucide icons. 2D only.
11. **"Heirloom" is a working name.** Collision check before any logo.
12. **Stack (familiar only):** Python 3.12 + uv, **DuckDB** over the gzipped JSONL, FastAPI for the trail API,
    Next.js for the viewer. LLM calls go through one small client with a provider switch in env (`LLM_PROVIDER`);
    cheap model for triage, strong model only for candidates. **No local GPU work** (the laptop GPU throttles).

## The method v1 (full spec in `docs/METHOD.md`)

- **Snapshots:** `agent_memories` holds the full memory text at each rewrite. Sort per agent by `created_at`.
- **The window:** for snapshot k of agent A, the evidence window is everything between snapshot k-1 and k:
  A's computer-use turns (action, output, error, screenshot ref), A's chat messages, chat A could see, human
  messages, `SEARCH_HISTORY` answers. Same rule in both eras (2025 frequent rewrites; 2026 `CONSOLIDATE` every ~40
  actions — there `computerUseSessionId` narrows it further).
- **Diff:** only lines that are new or changed between k-1 and k are candidates (cuts cost by orders of magnitude).
  Lines that *vanish* during a compression (memory got shorter) are tracked too — corrections and forgetting live there.
- **Claims:** an LLM pulls checkable claims from the diff (numbers, names, URLs, "X exists", "Y is done", "Z is
  broken", notes to a future self). Anchors (numbers, URLs, names) are kept verbatim.
- **Tie-out:** each claim is checked against its window → one of the 5 labels + the evidence quote.
- **Lineage:** the same claim is matched across later snapshots of the same agent (inheritance) and across other
  agents' snapshots (spread), anchors first, LLM confirmation second; the first chat message carrying it between the
  two agents is the "carrier".
- **The trail:** born → written → inherited (n rewrites) → spread (agents, carriers) → corrected (who, when, how)
  or alive. Every node has a link `https://theaidigest.org/village?date=YYYY-MM-DD&time=<unix_ms>` (verify format).

## The core feature — protect this above everything

**The Belief Trail for the 93-person contact list, rebuilt automatically from the raw data**, then the same trail for
new, unknown beliefs found in 2026 data. Everything else exists around that.

## The parts

| part | what it does | tech |
|---|---|---|
| **Loader** | download the tables, load into DuckDB, index by agent + time | `huggingface_hub`, DuckDB |
| **Windows** | snapshot k-1→k per agent + everything in that window | DuckDB SQL |
| **Diff + claims** | new/changed/vanished lines → checkable claims with anchors | Python difflib + LLM (cheap) |
| **Tie-out** | claim vs window evidence → label + quote | LLM (strong) on candidates only |
| **Lineage** | same claim across rewrites and agents; carrier message | anchors + embeddings/LLM confirm |
| **Trail API** | trails, beliefs, agents, search | FastAPI |
| **Viewer** | Belief Trail timeline, agent swimlanes, evidence panel, "still alive" list | Next.js |

## Folder map (planned)

```
heirloom/
├── CLAUDE.md          this file
├── hackathon.md       rules + submission checklist — outranks everything
├── MASTER-PLAN.md     the phases (dated)
├── PROGRESS.md        live state — read at the start of every session, update at the end
├── RESEARCH.md        every fact the build rests on, with its source
├── docs/
│   ├── DATA-MAP.md        tables, columns, joins, the two eras, download sizes
│   ├── METHOD.md          windows, diff, claims, labels, lineage, cost plan, evaluation
│   ├── KNOWN-CASES.md     validation set — the 93-list (verified quotes) + other documented cases
│   └── WRITEUP.md         submission write-up skeleton + the video script
│
└── (created with official init commands)
    ├── pipeline/      uv project: load, windows, diff, claims, tieout, lineage, CLI
    ├── api/           FastAPI over the DuckDB results
    ├── viewer/        Next.js
    └── data/          downloaded tables + heirloom.duckdb   (git-ignored, never committed)
```

## The 60-second demo (this path must work; nothing else has to)

1. (0–8 s) "AI agents rewrite their own memory. Nothing checks it's true." + the June 2025 village chat.
2. (8–28 s) Heirloom rebuilds the 93-person contact list on its own: born in o3's memory → copied into Gemini 2.5
   Pro, Claude 3.7 Sonnet and Claude Opus 4 → days of work → "NEVER EXISTED" (13 Jun) → last believer corrected.
   Each step: the memory line, the contrary evidence, a link to the live village moment.
3. (28–48 s) "Now on data nobody has read": the 2026 "still alive" list — false beliefs written into memory and never
   corrected, with their age in rewrites and how many agents carry them.
4. (48–60 s) "The monitor catches the lie. Heirloom shows who still believes it." + the numbers (snapshots read,
   beliefs checked, known cases recovered x/y).
