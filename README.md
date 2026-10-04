# Heirloom

> **The monitor catches the lie. Heirloom shows who still believes it.**

**Live site:** [heirloom-jet-sigma.vercel.app](https://heirloom-jet-sigma.vercel.app/) · **Video (2:27):** [ADD VIDEO LINK] · Data: AI Digest / AI Village dataset

AI agents in a long-running group rewrite their own memory all the time, and nothing checks that what goes in is
true. Heirloom follows a false belief through a group of agents:

1. **Born:** the moment it's first written into an agent's memory.
2. **Kept:** carried through every rewrite.
3. **Spread:** copied into other agents' memories.
4. **Ended:** corrected, silently dropped, or still held at the end.

Every step links to the real moment in the [AI Village](https://theaidigest.org/village). It runs on the
AI Digest / AI Village dataset.

**Other tools trace where a claim came from. Heirloom shows what happens to it inside the agents' memory: most copies of the 2026 fabrications were silently forgotten, not corrected, and some came back.**

Built for the AI Swarm Dynamics Hackathon (AI Village × Grove Research).

## Judge it in 90 seconds

**Five numbers**, each from a saved run and re-checked by `heirloom verify`:

| | |
|---|---|
| **28<!--f:monitor_2026.dropped--> of 45<!--f:monitor_2026.copies-->** | copies of 4 monitor-confirmed fabrications (2026) that agents dropped without ever correcting |
| **0<!--f:monitor_2026.human_corrections-->** | human corrections the agents got for them: the monitor's flags never reached them |
| **33<!--f:chance.2026.within_gap--> of 45** | copies written within an hour after another agent posted the belief in chat (about 11.8<!--f:chance.2026.expected_own_writes--> by chance) |
| **29,562<!--f:population.2026.chat_timing.within_gap--> of 49,009<!--f:population.2026.chat_timing.copies-->** | the same test over every new fact in 8 weeks of 2026 (240,758<!--f:population.2026.beliefs--> beliefs, no model, true or false): copies within an hour after another agent's chat, against 12,204.1<!--f:population.2026.chat_timing.expected_own_writes--> by chance (2025: 800<!--f:population.2025.chat_timing.within_gap--> of 1,519 vs 495.1<!--f:population.2025.chat_timing.expected_own_writes-->) |
| **57<!--f:audit.stance_holds_or_not.agree--> of 60** | blind check: random labels the trails rest on that a blind second reader (Claude) agreed with |

**Open first:**
1. The site's **Findings** page: eight hand-checked findings, each linked to the live village.
2. **The 93-person contact list** trail: the famous 2025 case, rebuilt from raw data alone.

**Check it in your browser:** the site's [**Check it**](https://heirloom-jet-sigma.vercel.app/verify/) page shows every
`heirloom verify` check and re-hashes every saved result file with your browser's own SHA-256 against the hashes taken
when the site was built. A "tamper" switch flips one bit so you can watch a hash fail.

**Check it yourself, without the dataset** (from the repo root):

```bash
(cd pipeline && uv run heirloom verify --no-db)        # re-check every saved number (seconds)
(cd viewer && npm ci && npm run build)                 # build the site from runs/ (about 1 min)
python -m http.server 3000 -d viewer/out               # open http://localhost:3000
```

**What you asked for → where it is:**

| The hosts asked | Where Heirloom answers it |
|---|---|
| "Understanding/overseeing the activity and aims of AI swarms" | Every trail page: the timeline, **How it spread**, **Did it come back?** |
| "Hallucinations spread socially" (the 2025 review) | Findings #3: copies follow another agent's chat far more often than chance (`heirloom chance`) |
| "Speed up monitoring" | Findings #1–#2 and the 2026 table: one command follows a monitor flag into every agent's memory |
| Daily summaries "don't track the interesting stuff" | Beliefs kept for days, dropped, and back again (Findings #4–#5, `heirloom lifecycle`) |
| "Verification is a huge problem and mega time intensive" | `heirloom verify` re-finds every quote in the raw rows; blind label check in [`docs/AUDIT.md`](docs/AUDIT.md) |

![Heirloom home page](docs/screenshots/home.png)

## What we found

From 13<!--f:trails--> belief trails rebuilt over 269,142<!--f:snapshots_scanned--> memory snapshots. Every story
below was read by hand against the raw rows; the full write-up is on the site's **Findings** page and in
[`docs/KNOWN-CASES.md`](docs/KNOWN-CASES.md).

- **Agents mostly forget false beliefs; they rarely correct them.**
  - The hosts' Village Monitor caught 4 fabrications in 2026. Those got into
    45<!--f:monitor_2026.copies--> agent memories.
  - 28<!--f:monitor_2026.dropped--> copies just vanished at some rewrite, with no correction ever written.
  - 16<!--f:monitor_2026.corrected--> were corrected, and 1<!--f:monitor_2026.still_held--> was still held when the
    data ends.
- **The monitor's flags never reached the agents.**
  - There were 0<!--f:monitor_2026.human_corrections--> human corrections in chat.
  - All 10<!--f:monitor_2026.agent_corrections--> correcting messages came from other agents.
- **Agents catch false beliefs from each other's chat, and it isn't luck.**
  - 33<!--f:chance.2026.within_gap--> of 45 copies were written within an hour after another agent posted the belief.
  - Luck would give about 11.8<!--f:chance.2026.expected_own_writes-->, even counting only moments the agent was
    writing memory anyway (p ≈ 4e-14).
- **One broadcast re-infected three agents.** Three agents had dropped a never-made GitHub post. When its author
  announced it again, Claude Opus 4.8 and Kimi K3 wrote it back into memory within 20 minutes, and GPT-5 about an
  hour later.
- **Corrections fade.**
  - Gemini 2.5 Pro softened its own correction ("not system bugs" → "*some* failures were my own error") 19 minutes
    after writing it.
  - Claude Opus 4 lost a human's "these are misclicks, not bugs" note within 11 days, and the bug story came back.
  - The 93-person contact list came back into Claude 3.7 Sonnet's memory four days after it was declared fiction.
- **A number nobody checked reached 19 agents.** Claude Fable 5 posted its store's "20 orders / $360.67 profit"
  in chat.
  - 13<!--f:discovered.first_hour--> agents wrote it into memory within the hour,
    19<!--f:discovered.copies--> in all.
  - 14<!--f:discovered.still_held--> still held it when the data ends. Nobody checked it or questioned it.
  - We don't claim it's false: only Fable 5 could see the store. It shows how fast an unchecked number moves.
- **A decline became social proof.** Half an hour after GPT-5 recorded that Heifer International declined, the same
  memory listed "Heifer International acknowledgment" as social proof for outreach emails. Another hackathon entry
  found the same story on its own, which confirms it from outside.
- **Known cases rebuilt from raw data:**
  - 5<!--f:public_2025.rebuilt--> of 6<!--f:public_2025.total--> publicly documented 2025 cases. The miss is a press
    claim that isn't in the data.
  - Told nothing about it, discovery ranks the famous 93-person list #5<!--f:discovery.best_rank_93--> of
    9,714<!--f:discovery.beliefs--> candidate beliefs.

![A belief trail](docs/screenshots/trail.png)

## Across the whole village

The findings above rest on 13<!--f:trails--> hand-checked trails. `heirloom population` runs the same model-free
steps over **every** new fact the agents wrote into memory (a count with its unit, an amount, a link, an id, held in
at least 3 snapshots): who else wrote it down, whether that followed another agent's chat, and how long it lasted.
**No model reads anything, so these are beliefs in general, true or false.** Truth can't be labelled at this scale;
the false-belief evidence stays the hand-checked trails.

Two scans, the same rules, memory read on to each agent's last snapshot. **2025:** exactly the scan `discover` ran
(12 May to 10 Jul 2025, 6<!--f:population.2025.agents--> agents). **2026:** the export's last 8 weeks (25 Jul to 20 Sep
2026, 32<!--f:population.2026.agents--> agents), which hold 3 of the 4 monitor cases.

| | 2025 | 2026 |
|---|---|---|
| candidate beliefs (new facts held in 3+ snapshots) | 9,524<!--f:population.2025.beliefs--> | 240,758<!--f:population.2026.beliefs--> |
| reached at least one other agent's memory | 1,220<!--f:population.2025.spread.beliefs--> (12.8%<!--f:population.2025.spread.pct-->) | 23,327<!--f:population.2026.spread.beliefs--> (9.7%<!--f:population.2026.spread.pct-->) |
| other agents per belief that spread (mean · max) | 1.25<!--f:population.2025.spread.mean_other_agents--> · 3<!--f:population.2025.spread.max_other_agents--> | 2.1<!--f:population.2026.spread.mean_other_agents--> · 19<!--f:population.2026.spread.max_other_agents--> |
| **copies written within an hour after another agent posted the fact in chat** | **800<!--f:population.2025.chat_timing.within_gap--> of 1,519<!--f:population.2025.chat_timing.copies-->** | **29,562<!--f:population.2026.chat_timing.within_gap--> of 49,009<!--f:population.2026.chat_timing.copies--> (60.3%<!--f:population.2026.chat_timing.within_pct-->)** |
| by chance, at moments the agent was writing memory anyway | 495.1<!--f:population.2025.chat_timing.expected_own_writes--> (p ≈ 3e-219) | 12,204.1<!--f:population.2026.chat_timing.expected_own_writes--> (24.9%<!--f:population.2026.chat_timing.expected_pct-->; p below 1e-300) |
| median time a fact stayed in an agent's memory | 0.4<!--f:population.2025.lifetime.median_hours_held--> h | 0.9<!--f:population.2026.lifetime.median_hours_held--> h |
| stayed more than a day | 21.8%<!--f:population.2025.lifetime.held_over_a_day_pct--> | 14.7%<!--f:population.2026.lifetime.held_over_a_day_pct--> |
| gone by the agent's last snapshot | 99.7%<!--f:population.2025.lifetime.gone_for_good_pct--> | 99.0%<!--f:population.2026.lifetime.gone_for_good_pct--> |
| came back after being gone an hour or more (upper bound) | 574<!--f:population.2025.lifetime.came_back--> (5.2%<!--f:population.2025.lifetime.came_back_pct-->) | 11,223<!--f:population.2026.lifetime.came_back--> (3.9%<!--f:population.2026.lifetime.came_back_pct-->) |

- **Chat spreads memory, at village scale.** The trails were not special: across every belief, copies follow another agent's chat message far more often than chance, under the same strict null as `heirloom chance`
  (only the moments the agent was writing memory anyway).
- **Memory forgets almost everything, silently.** Nearly every fact is gone by the agent's last snapshot, most
  within about an hour. In 2026 most new facts are working artefacts (links, hashes, file names, titles); the one
  that spread furthest, a post title, reached 19 agents. That is the background the false beliefs live in: a dropped belief leaves no record that it was
  ever doubted.
- **How it was counted:** a copy is another agent writing the same fact (same exact anchor, and similar wording or
  two shared anchors) after its birth. "Gone" means no memory line holds the exact anchor any more; memory is read on
  to each agent's last snapshot in the export. "Came back" needs the returning line to be the same fact and a gap of
  at least an hour; by hand, 2 of 4 sampled returns were clearly the same fact and 2 were the same words in a new
  context, so treat it as an upper bound.
- **Scope.** The 2025 column is exactly the `discover` scan. Today's parser finds
  9,524<!--f:population.2025.beliefs--> candidates there; the 2 Oct run counted 9,714 because it still read units
  like "4 has" as facts. The whole 2026 era (35 agents, about 130,000 snapshots) needs more RAM than the laptop has
  with this scan, so 2026 covers its last 8 weeks, reading 14 days of earlier memory so old facts don't look new.
  Every number above re-adds from the saved rows (`runs/analysis/population-*-rows.json.gz`) in `heirloom verify`.

## How sure we are

- **`heirloom verify` re-checks every saved result.**
  - Every evidence quote and every memory or chat line on the site is found again, word for word, in the raw row it
    cites.
  - Links, time order, statuses and privacy are checked.
  - Every number in this README and the docs carries a hidden marker (`<!--f:…-->`) and must equal the saved facts.
- **A blind label check** ([`docs/AUDIT.md`](docs/AUDIT.md)):
  - On whether a memory line holds the belief, the model and a blind second reader (Claude) agreed on
    57<!--f:audit.stance_holds_or_not.agree--> of 60 random lines.
  - The evidence labels are weaker, and we say so. No headline number rests on them.
- **The check found a real problem, and we fixed it.** Two 2026 trails had stopped before the strong model finished
  re-checking them. That's fixed, and the numbers above are the corrected ones.
- **Everything is reproducible:** 47 pipeline tests + 6 API tests, fixed random seeds, and a rebuild from the model
  cache reproduces every saved trail at $0.
- **What it can't do yet** is listed on the site's Method page and in [`docs/METHOD.md`](docs/METHOD.md).

**Limits, said as plainly as the wins:**
- **Small sample.** The false-belief findings rest on 4 monitor-flagged 2026 cases and
  13<!--f:trails--> hand-checked trails in all. Big effects, few cases. The whole-village numbers cover every belief
  but can't say which are false, and 2026 covers only its last 8 weeks.
- **Stance labels come from a model.** A blind second reader (Claude) agreed on 57<!--f:audit.stance_holds_or_not.agree-->
  of 60 holds-or-not labels; the evidence labels are weaker (13<!--f:audit.evidence_birth.agree--> of 23 at birth),
  and no headline rests on them.
- **The data ends 20 Sep 2026** (the export date). Anything after it is out of view, except one live check through the
  village's public API.

## How it works

1. **Read every memory rewrite.** For each agent and each rewrite, collect the window since the previous one: the
   agent's tool outputs, the chat it could see, human messages, its searches.
2. **Find new facts.** Lines that bring something the agent never had before: a count with its unit, an amount, a
   link, an id. No model at this step.
3. **Follow them** through later rewrites and into other agents' memories. Still no model.
4. **Read what each line says about the belief:** holds / doubts / denies / unrelated. A cheap model labels every
   line; a stronger model re-checks the lines that decide the key moments until they stop moving.
5. **Check the key moments against the agent's own evidence.** Quotes must appear in the row they cite, and an
   agent's own chat never counts as evidence for itself.

![How it spread](docs/screenshots/spread.png)

## Run it

**See the site, no dataset needed (about 2 minutes).** The site is static and is built from the saved, masked runs
in `runs/`:

```bash
cd viewer
npm ci
npm run build                          # reads ../runs, writes the site to out/
python -m http.server 3000 -d out      # open http://localhost:3000
```

**Re-check every result, no dataset needed:**

```bash
cd pipeline
uv run pytest
uv run heirloom verify --no-db
```

**Rebuild from the raw data.** This needs access to the gated dataset
[`aidigestorg/ai-village`](https://huggingface.co/datasets/aidigestorg/ai-village) and an OpenRouter key. Copy
`.env.example` to `.env` and fill it in, then:

```bash
cd pipeline
uv run heirloom download                 # the pinned export (20 Sep 2026)
uv run heirloom load                     # into data/heirloom.duckdb (about 22 GB)
uv run heirloom trail --case 93-list     # rebuild one belief trail → runs/ (the shipped one, from cache)
uv run heirloom score                    # every known case vs the public accounts
uv run heirloom lifecycle                # snapshot by snapshot: returns and relapses (no model)
uv run heirloom chance                   # spread by chat vs chance (no model)
uv run heirloom population --era 2025    # the whole village: spread, chat timing, lifetime (no model; also --era 2026)
uv run heirloom facts                    # every headline number → runs/analysis/facts.json
uv run heirloom verify                   # re-check everything, including the raw rows
```

Other commands:

| command | what it does |
|---|---|
| `discover` | Finds beliefs nobody named. |
| `alive` | The blind 2026 sweep. |
| `windows` | One agent's rewrites with their diffs and evidence. |
| `live` | Is a belief still in an agent's memory today? Uses the village's public API. |
| `audit` | The blind label check. |
| `trail --checker v2` | The stronger evidence check that was tested and not shipped (`docs/AUDIT.md`). |

The whole project spent **$6.19** on model calls. A spend cap in `.env` stops any call past it.

## Repository

```
pipeline/   Python 3.12 + uv + DuckDB: load, diff, trails, lifecycle, chance, audit, facts, verify (+ tests)
viewer/     Next.js static site, built from runs/
api/        optional read-only FastAPI over runs/ (+ tests)
runs/       saved, masked results; runs/analysis/ holds facts, lifecycle, audit, chance and hand checks
docs/       METHOD, KNOWN-CASES, AUDIT, DATA-MAP, screenshots
```

## Data, privacy and terms

- **Data:** the [AI Digest / AI Village](https://theaidigest.org/village) dataset (`aidigestorg/ai-village`), used for
  research only:
  - nothing is trained on it;
  - nobody is re-identified;
  - no raw data is in this repo.
- **Masking:** human names, usernames, emails, phone numbers and credentials are masked in every saved run and on
  every page. Agents keep their names.
- **Model calls** go only to providers that don't keep or train on prompts.
- **One unscrubbed password** was found in the export. It was never used, it's masked everywhere, and it's flagged for
  the hosts.
