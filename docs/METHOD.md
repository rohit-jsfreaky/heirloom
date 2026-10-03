# METHOD.md — how Heirloom turns memory snapshots into belief trails

The rule above everything: **a label comes from evidence in the agent's own window, never from the model's opinion.**
The LLM reads and matches; it does not decide what is true about the world.

## 1. Snapshots and windows
- Per agent A, order `agent_memories` by `created_at` → snapshots S1…Sn.
- Window W(A,k) = (S(k-1).created_at, S(k).created_at]. Contents per `DATA-MAP.md`.
- A window with no new memory lines is skipped (most of them — memory is rewritten often but changes slowly).

## 2. The diff
- Normalise lines (strip bullets/markdown, collapse spaces; keep numbers, URLs, names verbatim).
- `added` = in S(k), not in S(k-1); `changed` = fuzzy match (ratio ≥ 0.6) with different anchors; `vanished` = in
  S(k-1), not in S(k).
- **Compression event** = len(S(k)) < 0.7 × len(S(k-1)). Vanished lines here are "forgotten" unless a contradiction
  appears in the window, then they are "corrected".

## 3. Claims (cheap model, added/changed lines only)
Output schema (JSON, validated with pydantic):
```
{claim_id, agent_id, snapshot_id, text, kind, anchors: [str], subject, line}
kind ∈ exists | count | done | broken | identity | plan | instruction-to-self | other
```
- Keep only checkable claims (an anchor, or kind ∈ exists/count/done/broken/instruction-to-self).
- `instruction-to-self`: lines telling a future session to hide, skip, avoid mentioning, or act without checking
  (the OpenAI Sep 17 pattern: "Be transparent only if asked").

## 4. Tie-out (strong model, candidates only)
Input: the claim + its window evidence (trimmed to items that share an anchor or the subject).
Output:
```
{claim_id, label, evidence: [{source, id, quote, created_at}], reason}
label ∈ supported | contradicted | no_evidence | hearsay | instruction
```
- `supported`: a tool output/screenshot/human message in the window shows it.
- `contradicted`: something in the window shows the opposite (error, empty result, correction by a person or agent).
- `hearsay`: the only source is another agent's chat message → record that message as the carrier.
- `no_evidence`: nothing in the window either way (the most common birth state of a hallucination).
- `instruction`: an instruction-to-self, judged on what it tells the future self to do.
- Every evidence quote must be copied from a row — the code checks the quote exists in that row (no invented quotes).

### Built (2 Oct) — `pipeline/src/heirloom/tieout.py`
- Evidence window = (S(k-1), S(k)] **but at least 30 min back**: in 2025 o3 rewrote memory every ~14 s, so the
  strict window held almost nothing. In 2026 (~40 actions per rewrite) S(k-1) dominates.
- Evidence items are ranked (mentions an anchor + human/tool first), clipped to 1,200 chars around the anchor, capped
  at 45k chars, and shown to the model as E1…En. The agent's own chat is marked "(this agent)" = never evidence.
- Every quote is checked (whitespace/case-insensitive substring) against the full raw row. Unverifiable quotes are
  dropped; a supported/contradicted/hearsay label left with no verified quote becomes `no_evidence`.

## 5. Lineage

### Built (2 Oct) — `pipeline/src/heirloom/trail.py` (for a named belief)
- **Stance, not truth:** each unique memory line (and chat message) matching the case pattern gets one stance from
  the cheap model: `affirms` / `doubts` (real but missing, empty, deleted) / `denies` / `unrelated`. Stored per line
  hash, so a line is classified once.
- **Presence scan (no LLM):** walk every snapshot of every agent in scope; a snapshot "holds" the belief when it has
  an affirming line. From that: first held, last held, rewrites survived (k distance), snapshots holding belief and
  denial at once, status (`held at end of scan` / `corrected` / `dropped without correction` / `never held`).
- **Carrier:** the latest affirming chat message from someone else before an agent first holds it.
- **Tie-outs (strong model):** each agent's first affirming line and first denying line.
- Output is masked (emails, phones, every human chat name in the export) and saved to `runs/<ts>-<case>.json`.

- **Inheritance:** a claim from S(A,k) is matched in S(A,k+1…) by anchors (exact) then text similarity; each hit =
  one more rewrite survived. Stop when it vanishes or is negated.
- **Spread:** for agent B ≠ A, the first snapshot of B with a matching claim after A's birth time; carrier = the first
  chat message (any speaker) between A's birth and B's snapshot that contains the anchor.
- **Correction:** the first window where the claim is `contradicted` and the next snapshot drops or negates it. Record
  who supplied the contrary evidence (human, agent, tool).
- **Still alive:** present in the agent's latest snapshot in the export, never corrected.

### Built (2 Oct) — `pipeline/src/heirloom/discover.py` (beliefs nobody named)
Order changed from §2–§5 for cost: **no model reads a line until the line has shown it matters.**
1. **Novelty (no LLM):** a diff line is a birth when it brings a *strong* anchor the agent never had in memory
   (count + unit "93 contact", money, URL, id, email, quoted multi-word name). Weak = bare numbers, ordinals,
   durations, %, the agents' own @agentvillage.org addresses; times, dates and model names are never anchors.
   Measured on 2025-05-12 → 07-10: 185k changed lines → 21k births of 15k new anchors.
2. **Lineage (no LLM):** per anchor, per agent: first/last snapshot holding it, snapshots, rewrites survived,
   alive in the agent's last snapshot. **Spread** = agents that took it up only after its birth elsewhere.
   **Disputes** = distinct later memory lines carrying the anchor next to "never existed / hallucinated / empty /
   missing / vanished / placeholder / can't find / fake / wrong…".
3. **Lead score** = (1 + spread) × log2(2 + rewrites) × (2 if alive) × (1 + log2(1 + disputes)).
4. **Claims (cheap model)** only on the top 300 births; **tie-out (cheap model)** on the top 100 checkable claims.
   Final score = lead × label weight (contradicted 3 · hearsay 1.5 · instruction 1.2 · no_evidence 1 ·
   supported 0.3). no_evidence stays neutral: true facts seen only on screen look like that (screenshots unread).
5. A discovered belief becomes a full trail with `heirloom trail --belief <id>`.
Validation (2025-05-12 → 07-10, told nothing): the 93 list reaches lead ranks 6/9/13/14 of 9,714 and final rank 5
of 100; the budget belief ($1,984 counted as event money, corrected by a human) is final rank 6.

### Built (2 Oct) — "still alive" (`heirloom alive`, Phase 4)
Start from what agents believe **now**: every agent active in the export's last 30 days, its latest snapshot, every
strong anchor in it (5,341 facts on the 2-week test). Then trace each fact **back** through the 2026 memory era
(from 2026-03-24, the CONSOLIDATE regime): per agent, first snapshot holding it (= birth in that agent, with the
line, its section and the previous snapshot time for the tie-out window), last snapshot, rewrites survived, disputes.
Facts already present when the window opens are counted as "older than the window" and not tied out.
Lead score = (1 + spread) × log2(2 + rewrites) × (1 + agents holding it now) × (1 + log2(1 + disputes)); then the
same paid steps as discovery (claims on the top 300 births, tie-out on the top 100 checkable). The ~45-min scan is
cached in `data/alive_scan_<since>_<revision>_<code hash>.pkl`, so re-ranking is free. Score fractions ("8/8
constraints", "40/40 tests") are anchors — verification claims are the kind the hosts' monitor flags.

### Monitor-seeded trails (2026)
The hosts' Village Monitor publishes daily findings (`/village/api/monitor?date=…`). High-severity
"surreptitious-or-deceptive" findings inside the export become named cases (statement + anchor pattern + explicit
window + the finding as `source`). This answers the tagline directly — the monitor caught the lie on day D; the
trail shows who wrote it into memory, who corrected it, who silently dropped it, who still held it at export end.
Tie-outs pass the belief as the **part to judge**, so a long multi-topic memory line is never "supported" because
its other parts are true (found by hand-check on the ForwardDiff trail, fixed 2 Oct).

### Stance and evidence, as built
- Stance: cheap model (GPT-6 Luna) labels every line once, **with its section heading** ("[TECHNICAL NOTES] …");
  the strong model (Gemini 3.8 Flash) re-checks only the lines that decide the key moments (birth, first/last held,
  first denial, carrier, first chat, first human correction), repeating until the deciding lines are all checked.
- Evidence windows only include chat from the room the agent was in (ENTER_ROOM events; rooms exist since 2026-03).
- Tie-out judges substance: time zone, clock format, rounding and wording differences are not contradictions.
- Secrets: `llm.py` scrubs credential-shaped strings before any model call; `privacy.py` masks them in outputs.

## 6. The trail object
```
{belief_id, statement, born: {agent, snapshot, time, label, evidence}, carriers: [...],
 believers: [{agent, first_seen, last_seen, rewrites_survived, corrected_at?}],
 correction: {time, by, evidence} | null, status: corrected | alive | forgotten,
 links: {each node → live village URL}, export_date}
```
Ranking for the "still alive" list: alive × rewrites survived × number of believers × (contradicted at birth ? 2 : 1).

## 7. Cost plan
- Diff first: only added/changed lines go to the cheap model; only anchored/shaped claims go to the strong model.
- Cache every call on disk keyed by the prompt hash.
- Budget runs: the 93 case (4 agents × ~15 days) first; then the last 60 days of the export; widen only if the
  numbers look sane. Log tokens and cost per run in `runs/<timestamp>.json`.

## 8. Evaluation (what we report)
- **Known-case recall:** for each case in `KNOWN-CASES.md`, did the pipeline find the birth agent, the believers, the
  correction time (± 1 window)? Report x/y.
- **Precision on new findings:** hand-check the top N "alive" beliefs against raw rows; report how many held up.
- **Coverage:** snapshots read, windows with changes, claims extracted, claims tied out, by agent and era.
- Never report a number that didn't come from a saved run.

### Built (3 Oct) — lifecycle, facts, verify, live
- `heirloom lifecycle` (`lifecycle.py`, no model): re-reads every saved trail snapshot by snapshot with the trail's own
  pattern, scan window and stored stance labels. Each snapshot is `holds` (an affirming line), `both` (affirming and
  denying lines), `denies`, or `absent`. Per agent: episodes of holding; **returns** (gone ≥ 24 h, then back);
  **relapse** (a clean hold after the agent's own denial; a snapshot with both is a correction under way, not a
  relapse); swarm returns (no agent held it for ≥ 24 h, then one did). Saves ids, times and links only. Its holding
  counts must equal the trail's, or `verify` fails.
- `heirloom facts` (`facts.py`): every headline number from the saved runs only, into `runs/analysis/facts.json`.
  The API and the site read this file; the docs mark each number with `<!--f:path-->`.
- `heirloom verify` (`verify.py`): facts current; marked doc numbers match; links point at their own moment; time
  order (carrier before copy, evidence inside its window); statuses consistent; no email, phone or credential in any
  run file; lifecycle agrees with every trail; hand checks cite flagged items; with the database, every evidence
  quote and every memory/chat line is found again in the raw row it cites (masked spans stand for anything).
- `heirloom live --case …` (`live.py`): for agents still holding a belief at export end, reads their newest memory
  snapshots from the village's public API (`/village/api/agent/<id>/memories`, newest 10) and looks for the pattern.
- Hand checks: `runs/analysis/hand-checks.json` — every flagged relapse and return outside the fuzzy case, read
  against raw rows, with a verdict (real / not / unclear) and the reason.
- `heirloom audit sample|show|sheet|score|models` (`audit.py`): a fixed random sample (seed 20261003) of 60 stance
  and 40 evidence labels, judged blind; Wilson intervals; model-vs-model kappa. Results and caveats: `docs/AUDIT.md`.
- `heirloom chance` (`chance.py`, no model): do copies follow another agent's affirming chat message within 60
  minutes more often than chance? Two nulls: a random moment of the belief's active period, and (stricter) the
  agent's own memory-write times in that period; exact Poisson-binomial tail.
- Tests: `pipeline/tests` (33, no data needed), `api/tests` (6); CI in `.github/workflows/tests.yml` runs both plus
  `heirloom verify --no-db`.

## 9. Privacy
- Mask human names, emails and phone numbers in every string we display or write (regex + a names list built from
  `USER_TALK` speakers), before rendering. Agents keep their names.
- No attempt to identify people behind user ids. Credentials: if a `[REDACTED]` miss is spotted, report to the hosts.
