# PROGRESS.md — live state

Read at the start of every session. Update at the end.

## Final push (4 Oct 2026, evening; hard freeze 3:00 AM IST 5 Oct; $0 model spend)
- **Step 1 done:** the false "Other tools check a claim at one moment" line is replaced everywhere (README, WRITEUP,
  home page) by the real edge: other tools trace where a claim came from; Heirloom shows what happens to it inside
  memory (most 2026 copies silently forgotten, some came back). Video link placeholder `[ADD VIDEO LINK]` in README
  and WRITEUP. "Limits" block in README. Heifer finding: outside confirmation line (other entry not named).
  The video still says the old line aloud (segment H, ~2:04–2:10).
- **Step 3 done:** `/verify` page ("Check it" in the header, linked from home, README, WRITEUP). Shows every
  `heirloom verify` check from `runs/analysis/verify.json`; re-hashes every `runs/**/*.json` in the browser (Web
  Crypto SHA-256) against `public/results/manifest.json`, written before every build by `viewer/scripts/results.mjs`
  (`prebuild`/`predev`). Hashes are of the LF (git) bytes: checked equal to `git show HEAD:<file> | sha256sum`.
  Tamper switch flips one bit of facts.json → "1 of N changed". Tested headless (desktop + 390 px phone).
- **Step 2:** `heirloom population [--era 2025|2026]` (`population.py`) → `runs/analysis/population-<era>.json`
  (ids, agent names, times, counts; no text). Whole-village numbers, no model, beliefs in general (true or false).
  - 2025 = exactly the discover scan: today's parser finds 9,524 candidates (the 2 Oct run's 9,714 still read units
    like "4 has" as facts; shown by diffing its top 150 ids). Scan 2 min, lifetime pass 4 min (cached in data/).
  - 1,220 (12.8%) spread; 800 of 1,519 copies within 1 h after another agent's chat vs 495.1 by the strict own-writes
    null (p ≈ 3e-219); median 0.4 h held; 99.7% gone by the agent's last snapshot; 574 (5.2%) came back (strict:
    gone ≥ 1 h, returning line is the same fact).
  - Hand-read: 3 within-hour copies were real chat → memory copies; 2 of 4 strict returns were clearly the same fact,
    2 the same words in a new context → published as an upper bound. Lifetimes agree with the scan's own lineage on
    all 11,039 holdings.
  - facts.json `population.<era>`; verify `check_population` re-adds every number from the rows and rejects any
    extra (text) field; 5 tests. README "Across the whole village", Findings page section, WRITEUP finding 9,
    judge table row.
  - 2026 era: the whole era (24 Mar on, ~130k snapshots, 4.7 GB of text) was too big for the laptop's RAM with
    this scan (first run killed by the system; second stopped at Rohit's OK). Shipped: the last 8 weeks (25 Jul–20
    Sep, 32 agents, 14 days of earlier memory), ~1 h: 240,758 beliefs; 23,327 (9.7%) spread, max 19 agents;
    29,562 of 49,009 copies within 1 h after chat vs 12,204.1 by chance (p underflows to 0 → "below 1e-300");
    median 0.9 h held; 99.0% gone; 11,223 (3.9%) came back. Hand-read: copies are real (demo URL, SHA-256 copied
    minutes after chat); most 2026 "facts" are working artefacts (links, hashes, file names, titles).
  - Rows saved column-wise, gzipped (`population-<era>-rows.json.gz`, 2026 = 9.4 MB; plain JSON was 109 MB, over
    GitHub's limit). Re-running 2025 from cache gives byte-identical files. Verify allows the 0.1-min rounding of
    a saved gap (2 copies at "60.0" min were really a few seconds over the hour).
  - The /verify page hashes the .gz rows too (52 files).
  - Caches in data/: population_scan_*.pkl, population_presence_*.pkl (the 520 MB full-2026 scan cache is unused).

## Now (3 Oct 2026)
- **Read `docs/internal/COMPETITION-AND-PLAN.md` first.** It has the rival teams, our top-5 ranking, and the plan to
  raise each score (Rigor, Findings, Fit, Novelty, Build), with item IDs (R1–R5, F1–F6, T1–T3, N1–N3, B1–B4), costs
  and tick boxes. Git-ignored on purpose. Waiting on Rohit's "go" for step 1 (all $0).
- The deadline moved: **Mon 5 Oct, 5:30 AM IST** (target 2:00 AM). Form in Swarmchasing Slack `#announcements`.
- **Step 1 of the plan done (3 Oct, ~02:00–04:30 IST, $0 spent, still $5.51 of $6.00):**
  - `heirloom lifecycle` → `runs/analysis/lifecycle-*.json` (all 12 trails; every count matches its trail; 100% of
    lines labelled).
  - `heirloom facts` → `runs/analysis/facts.json` (the API now reads it; `api/main.py` no longer keeps its own case
    lists).
  - `heirloom verify` → all checks pass; with the DB, 290/290 quotes and 598/598 lines are found in their raw rows; 27
    numbers in KNOWN-CASES are marked `<!--f:…-->` and checked.
  - `heirloom live` → Muse Spark 1.3 no longer holds #846 in its 10 newest live snapshots (30 Sep–2 Oct). We do not
    claim "still held today".
  - Tests: `pipeline/tests` 32 + `api/tests` 6; CI file `.github/workflows/tests.yml`.
  - Hand checks: `runs/analysis/hand-checks.json` (13 flagged items: 7 real, 4 not, 2 unclear).
  - New findings are written up in `docs/KNOWN-CASES.md` → "Lifecycle" and "Two memory eras".
- Fixed 3 Oct:
  - The masker had masked our own case text ("charity", "user" are chat handles). `trail.save` now keeps our slug,
    title and statement; the two saved runs were restored.
  - `scrub_secrets` no longer re-matches "[secret]".
  - A punctuation-only quote no longer counts as verified (`tieout.quote_ok`).
- **Step 2 (3 Oct, $0 so far):**
  - Committed step 1 locally as `6183354` (Rohit asked Claude to commit, not push).
  - `heirloom audit sample|show|sheet|score|models` built. 100 labels judged blind by Claude
    (`data/audit/judged-claude*.json`, git-ignored) → `runs/analysis/audit.json` + `docs/AUDIT.md`.
    - Stance holds-or-not: 57/60.
    - Evidence checks are weak: birth 13/23; corrections 15/17 only when either reading of the rubric is allowed.
      The rubric frame is ambiguous: judge the line or the belief?
  - Rohit's blind sheet: `docs/internal/AUDIT-ROHIT.md` (20 items) — waiting on his answers.
  - Model agreement (`runs/analysis/model-agreement.json`):
    - Sonnet vs Luna on 2,023 lines: kappa 0.69; holds-or-not 96.6%.
    - Gemini vs Luna on deciding lines: Gemini rejects 456 of 617 of Luna's "affirms".
  - **FIXED: two 2026 trails had not converged** (re-check loop hit MAX_CHECK_ROUNDS=6). With Rohit's OK, every
    "affirms" line in fake-commit-hash and muninn-verification went to Gemini 3.8 Flash ($0.089; spend now $5.60 of
    $6.00). It kept 14/103 and 42/242. Both trails were rebuilt: 12 → 10 and 8 → 5 copies. All 45 copies in the four
    2026 trails are now strong-confirmed at their first and last line.
    **2026 headline: 45 copies → 16 corrected, 28 dropped, 1 still held** (KNOWN-CASES and AUDIT updated; verify
    passes with the DB: 310/310 quotes, 684/684 lines).
  - `heirloom chance` (R4, no model): 2026 → 27/45 copies written within 60 min after another agent's affirming chat
    message. Chance expects 4.8; 11.8 at the agent's own write times (p ≈ 9e-8). 2025 → 10/21 vs 4.2 (p ≈ 0.003).
  - Also found: plan lines ("posting to #846 at 1 PM") get "affirms", from both models. So some ForwardDiff
    first-held times are plans, not beliefs.
- **Step 3 (3 Oct, $0):**
  - **The site is now fully static** (`viewer/`, `output: "export"`): `src/lib/data.ts` reads `../runs` (or
    `HEIRLOOM_RUNS`) at build time. No API server is needed; `api/` stays as an optional read-only JSON API.
    Build: `cd viewer && npm ci && npm run build` → `out/`. Serve: `python -m http.server 3000 -d out`.
  - New **/findings** page: 7 hand-checked findings with village links, the still-held list, and the live check.
  - Trail pages gained **How it spread** (who-passed-it-to-whom tree from carrier messages; Claude Haiku 4.5's status
    broadcast and DeepSeek's own message, 30 s apart, came just before 18 of 19 ForwardDiff copies after the plan rule) and **Did it come back?** (hand-check verdicts).
  - Home stats and Method "How sure are we?" read facts / verify / audit / model-agreement.
  - Root **README.md** with screenshots (`docs/screenshots/`) and 54 doc numbers checked by verify; `.env.example`.
  - CI: a new `site` job (npm ci, lint, build).
- **Step 4 (3 Oct, $0.067; spend now $5.67 of $6.00):** new named case `store-360`
  (`heirloom trail --case store-360`): Claude Fable 5's self-reported "20 orders / $360.67 profit".
  - 19 agents wrote it into memory, 13 within the hour; 14 still held it at export end; 0 checks or corrections.
  - All 19 copies are strong-confirmed (38 deciding lines re-checked, 0 changed).
  - Not shown false → facts block `discovered`, kept out of the false-belief totals.
  - On the site: home "Found blind" section and Findings #6. Facts now also count `first_hour` per era.
- **Write-up drafted (3 Oct):** `docs/WRITEUP.md` = submission text + a ~2:50 video script. `verify` checks its numbers
  (82 doc numbers in total; markers can now index lists: `held_after_human_no.rows.0.hours`).
- **Judge polish (3 Oct, $0):**
  - README: "Judge it in 90 seconds" (4 headline numbers, open-first pages, no-dataset commands), a judge map (hosts'
    asks → pages), and the one-liner "Other tools check a claim at one moment…".
  - WRITEUP: George's and Hitch's quotes, the judge map, "What we found" marked as the results write-up.
    88 doc numbers are checked.
  - **Plan rule** (`trail.stance_of`, no model): for forwarddiff-846 only, the 14 lines that just schedule the post
    ("posting to #846 at 1-2 PM") count as "plan", not holding the belief. Lifecycle and chance read stances through
    the same function. Test added (34 tests).
  - Dry run: copies stay 19 (15/3/1); 7 agents' first-held moves later; the rebuild needs ~$0.03 (7 strong re-checks,
    7 new evidence checks, masking). **Waiting on Rohit's OK.** Until then the saved forwarddiff run predates the rule.
- **Plan-rule rebuild done (3 Oct, $0.018; spend $5.69 of $6.00):**
  - forwarddiff-846 rebuilt: still 19 copies (15/3/1), all strong-confirmed; 7 first-held times moved later.
  - Chance test 2026: **33/45** within an hour (was 27), vs 11.8 expected (p ≈ 4e-14). came_by_chat 35/45.
  - Docs updated; verify checks 88 numbers. Video script line reworded (two messages 30 s apart, 18 of 19 copies).
- **#8 + #9 + #7 round (3 Oct; spend $5.6887 → $6.1781, +$0.49):**
  - **#8 done:** ticket numbers are strong anchors `no.846` and searched as `#846`; HTML entities like `&#8470;` are
    no longer anchors; `score.belief_case` handles them. Tests added. runs/ untouched by #8.
  - **#9 code done:** a handle is a "word" only if wordfreq zipf ≥ 4.0 AND the agents' chat writes it mostly lowercase
    (35 handles: charity, user, only, test…). Those are masked only after @, as a speaker label, or as written / in
    capitals. "[person]" (403/2,757 lowercase) stays a name; zipf ≥ 3.5 alone would have re-leaked it ("[person]'s Blog")
    and "[person]". Tests added.
  - Applied only to store-360: a $0 cached rebuild, `runs/20261003T113514Z-store-360.json`; it un-masks only
    zero / Echo / cat. Other trails keep the old, stricter masking. (Corrected 3 Oct: a 2025 rebuild needs no new
    evidence checks with checker v0, only new masking calls; see below.)
  - **#7 tested, not shipped:** prompt v2 (one definition, COPY/CORRECTION, 8 examples) plus three fixes (quote
    comparison without markdown or escapes; retrieval ranked by belief and strong anchors, not bare numbers; session
    summaries count as narration). Held-out birth test: old 9/15; v2 8 → 9/15 (low effort) and 9/15 (medium). Pass
    mark 12/15 → **stopped, no rebuild** (see docs/AUDIT.md).
    - ~~Code defaults to v2~~ → **Rohit decided (3 Oct): defaults back to what built the shipped runs; v2 behind a
      flag.** Done, see next item.
  - verify (with DB) passes: 373/373 quotes, 994/994 lines, 88 doc numbers. 38 tests.
- **Defaults restored, v2 behind `--checker v2` (3 Oct; $0 spent, still $6.1781):**
  - The cache holds every evidence-check prompt ever sent. v0 (= v1 without the "Part to judge" rule, matched byte
    for byte) built the 2025 trails, belief-88f4b90fcf and the alive sweep; v1 built the 2026 trails; the discover
    sweep used an earlier draft (not kept). Each Case pins `checker` / `tie_outs`; `trail.BUILT_WITH` covers
    belief-88f4b90fcf; `discover.CHECKER = "v0"` for the sweeps. v0/v1 rank evidence with legacy anchors
    (`diff.anchors(legacy=True)`, checked equal to the old diff.py on all 1,151 lines in runs/).
  - Quote-match fix: changes 0 quotes in the 13 trails but 6/100 alive birth labels → v2 only (rule 3).
  - Rebuild check (scratchpad `rebuild_check.py`, spend limit 0): all 13 trails identical in believers, labels,
    quotes, links; differences are masking (#9, by design) and run counters. alive: 100/100 birth labels from cache.
  - Not $0 in a default rebuild (not run, ask first): 2025 trails' masking (name-finding prompt strengthened 2 Oct
    12:10 UTC, after they were saved: 14 calls ≈ $0.005); conjectures-357-359 never finished its re-check (6-round
    limit, 44/44 changed; ≈ $0.02; outside every total).
  - `belief_case` now finds a belief in any discover/alive run (newest first), so `trail --belief 88f4b90fcf` works.
  - 41 tests. Docs: AUDIT (v2 section + "What a rebuild reproduces"), WRITEUP Limits, README, METHOD.
- **Paid gaps closed (3 Oct, Rohit's OK, cap +$0.10; spend $6.1781 → $6.1866, +$0.0085):**
  - 2025 trails + belief-88f4b90fcf re-saved with current masking ($0.0049; runs/20261003T1252…–1253…). Content
    identical to the shipped files; only masks and run counters differ.
  - **Privacy fix found on the way:** the model returned a full name and the first name alone (a private
    insurance contact) showed. `privacy.add_people` now masks each part of a full name; test added. The leaky files were moved to
    scratchpad (never kept). A scan of every run file for parts of names the model ever returned found one more first name ×32 in
    the superseded 2 Oct MuninnAI run (committed in 6183354): masked in place. Still in local git history: not pushed.
- **Video plan (4 Oct):** `D:\my_projects\hackathons\heirloom-video\` (outside the repo): `VIDEO-SCRIPT.md`,
  `SHOT-LIST.md`, `VOICEOVER.md` (10 takes, Longtake format), `check_numbers.py` (every spoken number vs facts.json:
  20 rows pass), and the silent HyperFrames renders `intro.mp4` (15 s) and `outro.mp4` (11 s), 1920x1080 30 fps,
  `hyperframes check` clean. Runtime 2:46. Write-up video section updated with fact markers (verify: 100 doc
  numbers). Rohit records the walkthrough (0:15 to 2:35) and the voiceover.
  - Intro and outro re-rendered with the voiceover built in (Rohit's voice cloned with Chatterbox on the GPU,
    one clip per sentence, checked by Parakeet transcription and speaker similarity 0.91 to 0.94; AAC 48 kHz,
    about -17.5 LUFS). Rohit records only walkthrough takes 3 to 9.
  - **Full video built (4 Oct): `heirloom-video/heirloom-video.mp4`, 2:26.8.** Walkthrough recorded by script
    (Playwright, headless Chrome screencast at 1920x1080 from the live site; privacy guard: only the site and the repo
    may open) plus the two real terminal runs; cloned voice for every take (32 sentences, all exact by Parakeet);
    all parts at -18 LUFS. Final transcript vs script 99.2%. Rohit to watch it once before submitting.
- **History scrub prepared (3 Oct, read-only):** `../heirloom-scrub/` (outside the repo) has the scanner, hits,
  `replacements.txt` and COMMANDS.md. No secret anywhere in history. Real handles in tests/comments swapped for
  invented ones (Harbor, Victor, ZORVEX, Tamsin, Dana Whitlock, Bram, inkwell) so the rewrite touches only old commits.
  - conjectures-357-359 finished its re-check ($0.0036): 3 more rounds, 9 lines, 7 changed; holders 3 → 1 (Gemini
    3.5 Flash, 25 Aug, about the real 358/359 disproofs). Outside every total: facts and chance identical.
    Its hand-checked "relapse" (Claude Opus 5, verdict "not") is no longer flagged → moved to `retired` in
    hand-checks.json.
  - Lifecycle re-run for the 8 changed trails and store-360 (now points at runs/20261003T113514Z-store-360.json, the
    newest; kept). Facts, site and verify all read the newest file per trail (verify also walks every file).
  - 42 tests, 6 API tests, verify with DB passes (50,772 checks), site builds (13 trails).
- Known limits: ~~ticket numbers weak / #846 not an anchor~~ fixed 3 Oct (#8). ~~The masker over-masks "charity" /
  "user"~~ fixed in code 3 Oct (#9), but applied so far only to store-360 (see above).

## Earlier (2 Oct 2026, ~20:30 IST)
- **Claude writes the code** (Rohit, 2 Oct). Rohit does git. **LLM spend: $5.51 of the $6.00 cap** in `.env`
  ($0.49 left — Phases 5–6 need only name-masking calls, ~$0.05).
- **Phase 4 ✓** — results in `docs/KNOWN-CASES.md` → "2026". `uv run heirloom alive` (blind sweep, cached 26-min
  scan in `data/alive_scan_*.pkl`) + 5 monitor-seeded trails (`--case forwarddiff-846 | fake-commit-hash |
  muninn-verification | conjectures-357-359 | adoption-77`). Headline: 4 monitor-confirmed fabrications → 50
  agent-held copies → 16 corrected, 33 dropped without correction, 1 still held at export end (Muse Spark 1.3,
  hand-checked). Blind sweep's "contradicted" labels: 0/5 held up by hand — said plainly in the write-up.
- Claude Code's memory reaper stops long background runs when RAM is low: run trails one at a time in the
  foreground with `HEIRLOOM_DUCKDB_MEMORY=2GB`, and close the Playwright browser after use.
- **Phase 5 (viewer) — demo path done, 2 Oct ~21:00 IST.**
  - `api/` (uv, FastAPI 0.142): read-only over the masked `runs/*.json`; `/api/summary` (headline numbers computed
    from runs), `/api/cases`, `/api/trails/{slug}`, `/api/score`, `/api/alive`, `/api/discover`. Notes for the
    $7,500 and conjectures cases live in `api/main.py` (`NOTES`). Run: `cd api && uv run fastapi run main.py --port 8787`.
  - `viewer/` (create-next-app 16.3.8, Cache Components, `'use cache'` + `cacheLife('hours')`, Tailwind 4, Hanken
    Grotesk + JetBrains Mono, Phosphor): `/` (tagline, 4 headline numbers, featured 93 trail, 2026 monitor table,
    2025 public table), `/trails/[slug]` (timeline with one lane per agent, zoom presets, evidence panel with
    verified quotes + village links, per-agent table), `/method`. Run: `cd viewer && npm run build &&
    npx next start -p 3021` (needs the API up at build time; `HEIRLOOM_API_URL` overrides the default
    `http://localhost:8787`).
  - Checked in a real browser at 1440 px and 390 px: no horizontal page scroll; timeline and tables scroll inside
    their cards. tsc + eslint clean.
- **Next:** deploy (API + viewer), README, write-up, video (Phase 6).

## Earlier (2 Oct, ~17:45 IST)
- **Phases 0–3: 100% ✓.**
  - `uv run heirloom load` — all 11 tables ✓ vs manifest (DB 21.7 GB; if the memory reaper stops it, rerun with
    `--only <table>`).
  - `uv run heirloom windows --agent o3 --from … --to … --grep … --evidence` — diff + evidence, room-aware.
  - `uv run heirloom trail --case <slug>` / `--belief <id>` — full trail; `uv run heirloom score` — all known
    cases vs public accounts: **5 of 6 rebuilt** (miss = the press's "$7,500 budget", which is a venue quote in the
    data). Table in `docs/KNOWN-CASES.md` → "Score".
  - `uv run heirloom discover --from … --to …` — beliefs nobody named. Validated on 2025-05-12 → 07-10: the 93
    list at final rank 5, the $1,984 money belief at rank 6, told nothing.
- **Next: Phase 4** — 2026 "still alive" list. Plan: start from every agent's LATEST memory (32 agents, 5,797
  anchored lines), trace each belief back to its birth (no LLM), rank, check the top 100 at birth, build ~8 full
  trails, hand-check them against raw rows. Budget ≈ $0.85. Then the viewer (Phase 5).

## Budget (Rohit, 2 Oct): **$1–3 for all remaining LLM work.** Spent so far $3.69.
Measured 2 Oct on the 93 case (300 lines, Sonnet 5.5 labels as reference, routing `sort: price`):

| model | agrees w/ Sonnet | "affirms" precision / recall | cost per 300 lines |
|---|---|---|---|
| openai/gpt-6-luna | 87% | 97% / 92% | $0.009 |
| google/gemini-3.8-flash | 89% | 97% / 95% | $0.068 |
| google/gemini-3.1-flash-lite | 83% | 91% / 97% | $0.022 |
| google/gemini-3.5-flash-lite | 83% | 87% / 99% | $0.039 |

Whole 93 trail with Luna: $0.08 (Sonnet: $1.30). Same birth, believers, hearsay verdict, human corrections; only
"last held" moved (Luna read "RES-93-REBUILD-MASTER" lines as the original list).
**Blind test (2 Oct, $0):** a fresh helper agent labelled all 51 lines where Sonnet / Luna / Gemini 3.8 Flash don't
all agree, seeing no model answers. Score on those 51 (the other 249 of 300: all three agree):
Gemini 3.8 Flash 44 · Sonnet 5.5 39 · Gemini 3.1 Lite 39 · Gemini 3.5 Lite 35 · GPT-6 Luna 34. On the trail's key
call (affirms or not): Sonnet 46 · Gemini 3.8 46 · 3.1 Lite 47 · 3.5 Lite 46 · Luna 44. → Sonnet is not better than
Gemini 3.8 Flash here; Luna is a little worse (≈94% vs ≈98% over the 300). One case, one AI judge.
Also found: the stance prompt contradicted itself on rebuild sheets ("rebuilding it = doubts" vs "a rebuild sheet is
not this list") — fix before the next run.
**Decision (revised):** Luna for bulk; **Gemini 3.8 Flash** (not Sonnet) re-checks the lines that decide a
trail's key moments. Earlier text kept below for the record.
**Old decision:** Luna for bulk (claims, stance, triage tie-outs); Sonnet 5.5 only re-checks the lines that decide a
trail's key moments (first held / last held / first denial), ~1 call per trail. Keep a running cost; stop at $3.
**.env:** `LLM_MODEL_CHEAP=openai/gpt-6-luna`, `LLM_MODEL_STRONG=anthropic/claude-sonnet-5.5`,
`LLM_SPEND_LIMIT_USD=6.00` = hard cap on the project's TOTAL spend (summed from `cache/llm`; $3.69 already spent →
$2.31 left). `llm.py` refuses any new call at the cap; no limit set = no new paid calls. Tested 2 Oct, $0 spent.
Code still to switch when work resumes: stance bulk + tie-outs → cheap model, new Sonnet "decisive lines" check.

## Code map (`pipeline/src/heirloom/`)
`config` paths · `db` DuckDB connect (4–6 GB cap) · `download` / `load` · `diff` line diff, anchors (strong/weak),
section headings, line_hash (lru-cached) · `windows` snapshots + evidence window (room-aware) · `village` agent
lookup + live link · `llm` OpenRouter client, disk cache `cache/llm/`, cost, **spend cap**, secret scrubbing ·
`claims` (cheap model) · `stance` (cheap model + strong re-check of deciding lines) · `tieout` (quotes verified,
own chat never evidence, substance not time zones) · `trail` cases + presence scan + re-check loop · `discover`
novelty → lineage → disputes → rank → claims → tie-outs · `score` known-case recall + `--belief` cases ·
`privacy` names (export handles + wordfreq + model people-pass), emails, phones, secrets · `render` / `cli`.

## Known limits (say them in the write-up)
- ~~Stance without section heading~~ → fixed 2 Oct (lines carry "[SECTION]"). ~~Rooms~~ → fixed 2 Oct.
- Screenshots are not read; GUI-only evidence is invisible to the tie-out, so true facts seen on screen look like
  `no_evidence` (kept neutral in ranking for that reason).
- Bulk labels come from a cheap model (≈94% vs ≈98% for Gemini 3.8 Flash on the blind test); only the deciding
  lines get the strong model's second look.
- Discovery's birth labels say how a belief entered memory, not whether it was later disproved; the dispute
  signal and full trails cover the "later" part.
- A belief phrased with different numbers or units splits into several discovered entries (93 contacts / 93
  emails / 93 addresses).
- Name masking over-masks everyday words that are also chat handles ("max 5 people" → "[person] 5 people"):
  fixed in code 3 Oct (#9) but applied so far only to store-360; the other saved runs still over-mask (privacy-safe).

## LLM setup (decided 2 Oct, prices read live from openrouter.ai/api/v1/models)
- Provider: **OpenRouter**, called with the `openai` SDK (`base_url=https://openrouter.ai/api/v1`, per their quickstart).
- Claims (cheap, every diff): `google/gemini-3.8-flash` — $0.75 in / $3.75 out per M tokens. Runs only on Google.
- Tie-out (strong, candidates only): `anthropic/claude-sonnet-5.5` — $2 in / $10 out per M. Runs only on
  Anthropic / Bedrock / Vertex / Azure.
- Every request sends `provider: {"data_collection": "deny"}` (dataset terms: no training on the data).

## Data facts found while loading
- `computer_use_turns` has **no agent_id** — join `session_id` → `computer_use_sessions.agent_id`.
- `events.data` auto-detects as a STRUCT from a sample and guesses types (e.g. `cost` BIGINT) → load it as `JSON`
  and read fields with `data->>'actionType'`. Tested: 381,610 events read in ~6 s (DuckDB 1.5.6).
- Loading all 7 GB of memory text with one `ORDER BY` ran out of memory (6 GB cap, 12 threads, then 4). Fix in
  `load.py`: stage unsorted, then insert one agent at a time in time order (biggest agent 12 s). 4 threads.
- 93 case starts earlier than planned: goal page "Day 63" = 2025-06-03 (2025 counted every calendar day).
- Village page 13 Jun: a staff member told the agents to remove the belief "during the next memory compression"
  → per-agent check of whether they did = demo beat (see KNOWN-CASES).

## Decisions locked
- Idea: Heirloom — the life of a false belief (born → memory → inherited → spread → corrected / alive).
- Validation case: the June 2025 93-person contact list, rebuilt automatically.
- The window join (between two memory snapshots) is the evidence unit — works in both eras.
- Labels from evidence only; human names masked; dataset terms followed; AI Digest / AI Village cited.
- Stack: Python + uv + DuckDB + FastAPI + Next.js. No local GPU.

## For the hosts (report, don't use) — found 2 Oct
- A **plaintext password** (a stored credential o3 tried; the site said "Wrong password") is NOT scrubbed in the
  export: 28 memory snapshots of 4 agents (o3, Claude Opus 4, Claude 3.7 Sonnet, Gemini 2.5 Pro), 2025-05-28
  19:12–19:51 UTC (first: o3 snapshot `1dcc969f-7869-42b0-8398-45b10e2eeac9`), 1 chat message, 1 computer-use turn.
  It spread agent to agent through chat. Never used. Before 2 Oct ~17:00 IST it went into a few model prompts
  (OpenRouter, data_collection=deny); since then `llm.py` scrubs secrets before any call and `privacy.py` masks them
  in every output. Cached copies rewritten to `[secret]`. **Reported to George by Slack DM (3 Oct, 23:39 IST).
  His reply (4 Oct, 00:08): they are aware of some leakage and flagged it to the team; "feel free to basically
  ignore".** Done.

## Open questions
- ~~Can the public demo show short quotes from the dataset?~~ → **Yes.** George Ingebretsen, Slack DM, 4 Oct
  00:08 IST: "Yes please! That's totally encouraged". Quotes stay (masked, linked, cited).
- Where/how do we submit? (Not announced; watch Discord + email.)
- Next dataset refresh: the export is ~11 days old (≈ 20 Sep). The monitor's 28 Sep finding (Gemini 3.8 Flash
  "fabricated verification data") may not be in it yet — if a refresh lands before Oct 4, re-download events +
  memories for the newest days.
- ~~Live-village link format~~ → resolved 2 Oct: `?date=YYYY-MM-DD&time=<unix_ms>` (site rewrites `?day=` to it).
- ~~Which LLM key~~ → OpenRouter (see LLM setup below). Spend cap = set on the key.
- The Transluce swarm tooling shared at kickoff — read it, don't rebuild it.

## Log
- 2026-10-01 — idea picked by the engine (10-min kill loop 19:06:07 → 19:16:07 IST, survived).
- 2026-10-02 — verified in data: in June 2025 o3 wrote 45 memory snapshots in one day (every 1–3 min), while it
  had only one computer session that day → session-id linking can't work for 2025; the time-window join can.
  Folder set up.
- 2026-10-02 — Phases 0–3 built and run by Claude. 93 trail rebuilt (see KNOWN-CASES "Measured"). Stance prompt
  needed worked examples (rebuild sheets were read as the original list); stance moved to the strong model.
  Privacy masker fixed for handles that are everyday words ("only") and to protect agent names.
