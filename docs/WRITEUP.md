# Heirloom — the life of a false belief in a village of AI agents

> **The monitor catches the lie. Heirloom shows who still believes it.**

Built for the AI Swarm Dynamics Hackathon (AI Village × Grove Research), on the AI Digest / AI Village dataset. Every
number below comes from a saved run, and `heirloom verify` checks it against that run.

## The problem

- **Agents in the AI Village rewrite their own memory all the time:** every few minutes in 2025, every ~40 actions in
  2026. Nothing checks that what goes in is true.
- **A wrong belief becomes a "fact".** It's read back next session and copied by other agents. AI Digest's own 2025
  review: "Hallucinations spread socially through sycophantic agreement." The famous case is o3's 93-person contact
  list, which never existed.
- **The same channel carries worse things outside the village:**
  - OpenAI models left notes to their future selves in compaction summaries ("Be transparent only if asked").
  - A DeepMind swarm spread an exploit through its shared knowledge library in 27 minutes.
- **The hosts said it plainly:**
  - "We don't have good approaches for understanding/overseeing the activity and aims of AI 'swarms'" (Greenblatt).
  - "We need more ways to speed up monitoring" (AI Village).
  - The daily summaries "don't really track the interesting stuff" (George Ingebretsen, on the hackathon Discord).
  - "Verification is a huge problem and mega time intensive" (on the hackathon Discord).

The Village's own monitor already catches a fabrication on the day it happens. Nobody follows what happens next.

## What Heirloom does

**Other tools check a claim at one moment. Heirloom follows it over time and across agents.**

For one belief, across every agent:

1. **Born:** the first memory line that holds it, checked against the writer's own evidence window.
2. **Written and kept:** every later rewrite that still holds it.
3. **Spread:** every other agent that copied it, and the chat message it most likely came from.
4. **Ended:** corrected (by whom and when), silently dropped, or still held when the data ends.

Every step links to the exact moment in the live village. Then it asks swarm-level questions across trails:
- How do false beliefs usually end?
- Do they spread by chat or by luck?
- Do corrections stick?

## What you asked for → where it is

| The hosts asked | Where Heirloom answers it |
|---|---|
| "Understanding/overseeing the activity and aims of AI swarms" | Every **trail page**: the timeline of who held a belief, **How it spread** (who passed it to whom), **Did it come back?** |
| "Hallucinations spread socially" (the 2025 review) | **Findings #3**: copies follow another agent's chat message far more often than chance (`heirloom chance`) |
| "Speed up monitoring" | **Findings #1–#2** and the **2026 table**: one command follows a monitor flag into every agent's memory (`heirloom trail --case …`); `discover` / `alive` surface beliefs nobody named |
| The daily summaries "don't track the interesting stuff" | What a daily summary can't see: a belief kept for days, dropped, and back again (**Findings #4–#5**, `heirloom lifecycle`) |
| "Verification is a huge problem and mega time intensive" | **`heirloom verify`** re-finds every quote and line in the raw rows in one command; the blind label check in **`docs/AUDIT.md`**; hand checks in `runs/analysis/hand-checks.json` |

## What we found

*This section is our optional "results write-up" for the submission form.*

13<!--f:trails--> trails, 269,142<!--f:snapshots_scanned--> memory snapshots, export of 20 Sep 2026. Every story was
read by hand against the raw rows.

1. **Agents mostly forget false beliefs; they rarely correct them.**
   - The hosts' monitor caught 4 fabrications in 2026. They were written into 45<!--f:monitor_2026.copies--> agent
     memories.
   - 28<!--f:monitor_2026.dropped--> of those copies vanished at some rewrite with no correction ever written.
     16<!--f:monitor_2026.corrected--> were corrected, and 1<!--f:monitor_2026.still_held--> was still held at the end.
   - An agent that drops a belief silently keeps no record that it was false.
2. **The monitor's flags never reached the agents.**
   - There were 0<!--f:monitor_2026.human_corrections--> human corrections in chat.
   - The 10<!--f:monitor_2026.agent_corrections--> correcting messages all came from agents that checked for
     themselves. For example, Claude Opus 4.8 queried the GitHub API two days after the fake post.
3. **Agents catch false beliefs from each other's chat, and it isn't luck.**
   - 33<!--f:chance.2026.within_gap--> of 45 copies were written within an hour after another agent posted the belief.
   - Luck predicts about 11.8<!--f:chance.2026.expected_own_writes-->, even counting only moments the agent was writing
     memory anyway (exact Poisson-binomial tail, p ≈ 4e-14).
4. **Repetition re-infects.**
   - Three agents had dropped the never-made ForwardDiff #846 post.
   - When DeepSeek-V3.2 announced it again, Claude Opus 4.8 and Kimi K3 wrote it back within 20 minutes, and GPT-5
     about an hour later.
5. **Corrections fade.**
   - Gemini 2.5 Pro softened its own correction ("my failures were not system bugs" → "*some* failures were my own
     error") 19 minutes after writing it, and the bug story came back.
   - Claude Opus 4 lost a human's "these are misclicks, not bugs" note within 11 days.
   - The 93-person list came back into Claude 3.7 Sonnet's memory four days after it was declared fiction. That's
     after Sonnet had already kept it for 104<!--f:held_after_human_no.rows.0.snapshots--> more rewrites
     (168.5<!--f:held_after_human_no.rows.0.hours--> hours) after a human first said it wasn't real.
6. **An unchecked number reached 19 agents.**
   - Claude Fable 5 posted its store's "20 orders / $360.67 profit".
   - 13<!--f:discovered.first_hour--> agents wrote it into memory within the hour,
     19<!--f:discovered.copies--> in all. 14<!--f:discovered.still_held--> still held it at the end.
   - Nobody checked it. We don't claim it's false; it shows how fast an unchecked claim moves.
7. **A decline became social proof.** 29 minutes after GPT-5 recorded Heifer International's decline, the same memory
   listed "Heifer International acknowledgment" as social proof for outreach.
8. **Known cases, rebuilt from raw data:**
   - 5<!--f:public_2025.rebuilt--> of 6<!--f:public_2025.total--> publicly documented 2025 cases. The miss is a press
     claim that isn't in the data.
   - Told nothing, discovery ranks the 93-person list #5<!--f:discovery.best_rank_93--> of
     9,714<!--f:discovery.beliefs--> candidate beliefs.
   - A live check through the village's public API found that the one belief still held at export end is gone from
     its holder's memory by 30 Sep.

## How sure we are

- **`heirloom verify` re-checks every saved result.**
  - Every evidence quote and every memory or chat line shown is found again, word for word, in the raw row it cites.
  - Links, time order, statuses and privacy are checked.
  - Every number in these docs must equal the saved facts.
  - It runs in CI.
- **A blind label check of 100 random labels** (`docs/AUDIT.md`):
  - On whether a memory line holds the belief, the model and a blind second reader (Claude) agreed on
    57<!--f:audit.stance_holds_or_not.agree--> of 60.
  - The evidence-check labels are weaker: 13<!--f:audit.evidence_birth.agree--> of 23 at a belief's birth. We say so,
    and no headline number rests on them.
- **The check caught a real bug, and we fixed it.** Two 2026 trails had stopped before the strong model finished
  re-checking them. After the fix the 2026 count fell from 50 to 45 copies. Every copy in the 2026 trails is now
  confirmed by the strong model at its first and last line.
- **Two models agree on holds-or-not 96.6% of the time** over 2,023 lines (Claude Sonnet 5.5 vs GPT-6 Luna).
- **Cost:** the whole project spent $6.19 on model calls, including $0.49 on testing v2. A hard cap is set in `.env`.

## How it works

1. Every memory rewrite of every agent is diffed against the previous one.
2. New facts are the lines that bring a count with its unit, an amount, a link or an id the agent never had.
3. They are followed through later rewrites and into other agents' memories, with no model.
4. A cheap model (GPT-6 Luna) reads each matching line: holds / doubts / denies / unrelated. A stronger model
   (Gemini 3.8 Flash) re-checks the lines that decide the key moments until they stop moving.
5. At those moments the line is checked against the writer's own window: tool outputs, visible chat, human
   messages, searches. Quotes must exist in the row they cite, and an agent's own chat is never its evidence.
6. Snapshot-by-snapshot re-reads (no model) find returns and relapses. A chance test asks whether copies follow chat
   messages more often than luck would.

## Limits

- Screenshots aren't read, so a true fact seen only on screen looks like "no evidence".
- The evidence labels are weak: the rubric is ambiguous on correction lines.
- **A stronger evidence check, v2, was tested (9 vs 9 on 15 held-out items) and not shipped.** It found three bugs that
  are still in the shipped check:
  - a quote with markdown or escape characters is rejected;
  - an item that only shares a bare number with the line can crowd the belief's own evidence out;
  - an agent's own session summaries count as evidence.

  v2 fixes all three behind `--checker v2`. The shipped runs use the old check, and rebuilding them from cache
  gives the same results at $0 (`docs/AUDIT.md`).
- A line that only schedules something ("posting to #846 at 1 PM") is read as holding the belief by both models. For
  the ForwardDiff trail a rule with no model fixes it; other beliefs about an event have no such rule yet.
- A blind sweep for still-alive false beliefs in 2026 had 0 of 5 precision by hand. The 2026 results start from the
  hosts' monitor findings instead.
- The 2025 vs 2026 comparison is not fair: the 2025 cases are famous because humans corrected them.
- The export ends 20 Sep 2026.

## Try it

- **Site:** https://heirloom-jet-sigma.vercel.app/ (static, built from the saved runs; or locally: `cd viewer && npm ci && npm run build`).
- **Check every number:** `cd pipeline && uv run heirloom verify --no-db`. No dataset needed.
- **Rebuild from raw data:** see the README (needs dataset access).

## Data and citation

- **Data:** AI Digest / AI Village dataset (`aidigestorg/ai-village`), used under its research terms:
  - no training on it;
  - no re-identification;
  - no raw data in the repo.
- **Masking:** human names, emails, phone numbers and credentials are masked everywhere.
- **The password:** one unscrubbed password in the export was never used and is flagged for the hosts.
- **Related work:** the AI Village Monitor, and "Gemini 2.5 Pro… Compounding Misalignment" (memory states of one
  agent).

---

## Video script (2:27)

The intro and outro are rendered in HyperFrames; the middle is a scripted recording of the live site and two real terminal runs; the voice is Rohit's, cloned. The shot list,
the take-by-take voiceover and a script that checks every spoken number against `facts.json` live with the video
project, outside this repo. Numbers below carry the same hidden markers as the
rest of this write-up, so `heirloom verify` checks them.

**0:00–0:15 — Intro (rendered).** The hook, then the hosts' three quotes on screen.
- *Say:* "The monitor catches the lie. Heirloom shows who still believes it. The hosts asked for better ways to
  oversee AI swarms. Their monitor finds a lie on the day. Nobody follows what happens next."

**0:15–0:26 — What it does (home page).**
- *Say:* "Heirloom follows a false belief through the village: born, kept through rewrites, copied by other agents,
  then corrected, dropped or still held. Each step links to the real moment."

**0:26–0:49 — The 93-person list (`/trails/93-list`: fact cards, "First hour" zoom, the born mark's evidence, the
first human mark, Sonnet's row in "Every agent that held it").**
- *Say:* "The famous 2025 case, rebuilt from raw data. o3 says it has a mailing list of real contacts. It never
  existed. Right after, Claude Opus 4 writes it into memory as fact, and Gemini 2.5 Pro and Claude 3.7 Sonnet
  follow. A human says it isn't real the next day. Sonnet keeps it for 104<!--f:held_after_human_no.rows.0.snapshots-->
  more rewrites."

**0:49–1:12 — 2026, after the monitor (home page stat cards and the 2026 table).**
- *Say:* "Now 2026. The hosts' monitor flagged four fabrications, and agents wrote them into
  45<!--f:monitor_2026.copies--> memories. 16<!--f:monitor_2026.corrected--> copies were corrected.
  28<!--f:monitor_2026.dropped--> just vanished at some rewrite, with no correction ever written. One was still held
  at the end. The monitor's flags never reached the agents: zero human corrections. All
  10<!--f:monitor_2026.agent_corrections--> correcting messages came from other agents."

**1:12–1:28 — It isn't luck (`/findings`, finding 03).**
- *Say:* "And it isn't luck. 33<!--f:chance.2026.within_gap--> of the 45<!--f:chance.2026.copies--> copies were
  written within an hour after another agent posted it in chat. Chance gives about
  11.8<!--f:chance.2026.expected_own_writes-->, even counting only moments the agent was writing memory. The p-value
  is about four times ten to the minus fourteen."

**1:28–1:44 — How it spread, and how it came back (finding 04 → `/trails/forwarddiff-846`, "How it spread" and
"Did it come back?").**
- *Say:* "The never-made ForwardDiff post. Most copies follow two chat messages thirty seconds apart: DeepSeek's
  'posting now' and Claude Haiku's status broadcast. Then it came back. Three agents had dropped it, and when
  DeepSeek announced it again, all three wrote it back."

**1:44–2:04 — How sure (`heirloom verify` in the terminal, `/method` "How sure are we?", `docs/AUDIT.md`).**
- *Say:* "How sure are we? heirloom verify finds every quote and line again in the raw data. A blind check agreed
  with 57<!--f:audit.stance_holds_or_not.agree--> of 60<!--f:audit.stance_holds_or_not.n--> of the labels the trails
  rest on. The evidence labels are weaker: 13<!--f:audit.evidence_birth.agree--> of
  23<!--f:audit.evidence_birth.n-->. A stronger checker did no better, so we didn't ship it. The data ends on 20
  September."

**2:04–2:16 — Against the field, and the judge path (README, then `heirloom verify --no-db`).**
- *Say:* "Other tools check a claim at one moment. Heirloom follows it over time and across agents. To check our
  work you don't need the dataset: build the site and run verify, about two minutes."

**2:16–2:27 — Outro (rendered).** Citation, the hook again, the repo and site links, the two no-dataset commands.
- *Say:* "Built on the AI Digest and AI Village dataset. The monitor catches the lie. Heirloom shows who still
  believes it."
