# AUDIT.md — how often are Heirloom's labels right?

Every trail rests on two kinds of model label:

- **Stance.** Where does one memory line stand on the belief: affirms / doubts / denies / unrelated? "Held",
  "corrected" and "dropped" are all computed from these.
- **Evidence check (tie-out).** At a trail's key moments, what does the writer's own evidence window show:
  supported / contradicted / hearsay / no_evidence / instruction?

This page measures both against a blind reader. Commands: `heirloom audit sample | show | sheet | score`.
Result file: `runs/analysis/audit.json` (ids, links and labels only, no text). The raw sample stays in
`data/audit/` because it holds dataset text.

## Design (fixed before judging)

- **Fixed random sample** (seed 20261003) from the saved trails:
  - 60 stance labels, 15 per label;
  - 40 evidence checks, stratified with more weight on "contradicted": contradicted 12, hearsay 14, no_evidence 8,
    supported 4, instruction 2.
- **Blind.** The reader saw what the model saw and nothing else: the belief and the line (with its section
  heading). For evidence checks, the reader also saw every item in the window that mentions the belief or the
  line's anchors, plus every human message. The reader never saw the model's label, quotes or reason.
- **Reader 1: Claude** (the build agent), on 3 Oct 2026. One item (A048) was not blind: its label had been seen
  earlier while hand-checking relapses. This is marked in its note.
- **Interval:** Wilson 95%.

## Results (reader 1)

| what | agree | interval |
|---|---|---|
| **Stance: does the line hold the belief or not** (the call every trail is built on) | **57<!--f:audit.stance_holds_or_not.agree--> of 60** | 86–98% |
| Stance, exact label | 48<!--f:audit.stance.agree--> of 60 | 68–88% |
| Stance: lines the model called "affirms" | 15<!--f:audit.affirms_precision.agree--> of 15 | 80–100% |
| Evidence check at a belief's birth | 13<!--f:audit.evidence_birth.agree--> of 23<!--f:audit.evidence_birth.n--> | 37–74% |
| Evidence check at a correction, exact label | 7<!--f:audit.evidence_correction.agree--> of 17 | 22–64% |
| Evidence check at a correction, either reading of the rubric (below) | 15<!--f:audit.evidence_correction_either_reading.agree--> of 17 | |

**What this means:**

- **The trails' backbone is sound.** Held, corrected, dropped and still held all come from stance, and on the
  holds-or-not call the reader and the model disagree on 3 lines in 60. Most remaining stance disagreements are
  doubts vs denies vs unrelated (for example, whether a line about a *rebuild* sheet is about the original list).
  Those don't change whether an agent holds the belief.
- **The evidence-check labels are the weak part,** and we say so. Two causes, both visible in the disagreements:
  1. **The rubric is ambiguous on correction lines.** For a line like "the #846 post never landed", the checker
     sometimes judges the line ("supported by Claude Opus 4.8's API check") and sometimes judges the belief
     ("contradicted"). It used both readings for the same situation. So did reader 1's first pass. The first pass
     is kept in `audit.json` (`claude_firstpass_label`); the scored pass maps correction lines to the belief
     reading with one fixed rule that doesn't look at the model's labels. Allowing either reading, the checker
     matches on 15 of 17.
  2. **At birth, the checker under-calls hearsay and over-calls "contradicted" on plan lines.** It said
     "no_evidence" where another agent's chat in the window carried the claim. And it called "contradicted" a line
     that only *schedules* the post ("posting to Issue #846 at 1–2 PM"). That second case is really a stance slip
     upstream: a plan line was labelled "affirms", so a few agents' "first held" in the ForwardDiff trail is a
     plan, not a belief that the post exists.
- **What we therefore claim:**
  - Every headline number is built on stance.
  - "Came by chat" is counted from carrier messages (another agent's affirming chat message before the copy), not
    from evidence-check labels.
  - The evidence-check label counts (`birth_labels` in `facts.json`) are shown as the model's reading only, never
    as a finding.
  - The evidence quotes themselves are a different matter: every one is found word for word in its raw row
    (`heirloom verify`).

## What the check changed (3 Oct)

- The re-check loop has a 6-round limit. Two 2026 trails had hit it without finishing:
  - fake commit hash: 10 of 12 copies had a strong-confirmed first line;
  - MuninnAI: 4 of 8.
- Fix: every "affirms" line in both went to the strong model ($0.089). It kept 14 of 103 and 42 of 242. Both trails
  were rebuilt (12 → 10 and 8 → 5 copies).
- Every copy in all four 2026 trails is now confirmed by the strong model at its first and last holding line.
- The 2026 headline moved from 50 to 45 copies (16 corrected, 28 dropped, 1 still held).
- The sample above was drawn from the runs as they were on 2 Oct. Its fake-commit and MuninnAI evidence items
  audit the old runs.

- **Plan lines** (found by this check: a line that only schedules the post was read as holding the belief): a rule with
  no model now marks those 14 ForwardDiff lines as "plan". The trail was rebuilt; copies are unchanged, and 7
  first-held times moved later.

## Evidence-check prompt v2 — tested, not shipped (3 Oct)

**v2 was tested (9 vs 9 on 15 held-out items), not shipped.** It stays in the code as an option,
`heirloom trail --case <slug> --checker v2`: the new prompt on Gemini 3.8 Flash, with the three fixes below. Every
default is what built the shipped runs (see "What a rebuild reproduces").

The audit's verdict on the evidence labels led to the new prompt (`tieout.py`).
- **One definition:** judge the trail's belief as the line asserts it, from this agent's window up to the moment the
  line was written. The line is a COPY (claim: the belief) or a CORRECTION (claim: the belief is false). The
  "instruction" label is gone; plan lines are excluded upstream.
- **Eight worked examples from audited rows.**
- **Three bugs the test found.** All three are still in the shipped checker; only v2 has the fixes.
  - **Quote matching:** a quote is compared to its row only up to spacing and case. Three correct v2 verdicts were
    rejected because the model dropped `**` or wrote a real newline for `\n`. v2 compares without markdown or
    escape characters. In the shipped runs this fix would change no trail, but 6 of the 100 birth labels of the
    `alive` sweep, so it is not in the default.
  - **Evidence ranking:** any item that shares a number with the line ranks high. "17" and "94%" filled the window
    and pushed the commit message out. v2 ranks by the belief and the line's strong anchors first.
  - **Own narration:** the agent's own session summaries are shown as evidence; only its own chat is marked as
    narration. v2 marks both.

**Test:** the 23 audited birth items with Gemini 3.8 Flash.
- Not scored: 4 items reused as worked examples, and 4 that are now plan lines. That leaves **15 held-out items**.
- The blind judgments were fixed before the run; the two old "instruction" ones were re-read under the new definition.
- The pass mark was set in advance: 12 of 15. The old checker scored 9 of 15 on the same items.

| setting | held-out (15) | the 4 example items | cost |
|---|---|---|---|
| old checker (as shipped) | 9 | — | — |
| v2, low effort, 24k-char window | 8 | 2 (quotes rejected) | $0.149 |
| v2 + the three fixes, low effort | 9 | 4 | $0.108 |
| v2 + the three fixes, medium effort | 9 | 4 | $0.233 |

**Result: no setting cleared 12/15, so the trails were not rebuilt.** The shipped evidence labels are still the old
ones described above.

**What still disagrees (the same 6 in both settings).** Most are judgment calls where the blind label itself is
debatable:
- A042: my own note said nothing in the window speaks to the commit, yet I labelled it hearsay.
- A045: the agent's own tool output shows it created the sheet empty, which is arguably "contradicted" under the new
  rule.
- A073, A076: does a line that only tracks outreach to @MuninnAI assert that MuninnAI's presence was verified?
- A004: is "~92-97 tasks total" the same as "more than 50 finished"?
- A067: only this one looks like a pure retrieval miss. The first-hand report is a day earlier in a long window.

The next useful step is a second reading of these six, not another prompt.

### What a rebuild reproduces (checked 3 Oct, $0)

Each trail pins the checker that built it; `--checker` overrides.

| checker | prompt | model | built |
|---|---|---|---|
| v0 | before "Part to judge" existed (2 Oct) | GPT-6 Luna; the 93-list on Gemini 3.8 Flash | the six 2025 trails, `belief-88f4b90fcf`, the `alive` sweep's birth checks |
| v1 | judges the "Part to judge" (the belief) inside the line | GPT-6 Luna | ForwardDiff #846, fake commit hash, MuninnAI, store $360.67 |
| none | — | — | 77% adoption, conjectures 357-359 |
| an earlier draft, not kept | — | GPT-6 Luna | the 2025 `discover` sweep's birth checks |

v0 and v1 rank evidence with the anchors as they were then: ticket numbers ("#846") became strong anchors on 3 Oct.

**The check.** Every trail was rebuilt from the cache with the spend limit at zero, so any call not already made
would have stopped the run. Each was then compared with its file in `runs/`, field by field. Spend was $6.1781
before and after.
- **All 13 trails:** every believer, status, time, label, evidence quote and link is the same.
- **What differs:**
  - Masking, by design: since 3 Oct a chat handle that is an everyday word ("zero", "charity") is masked only where
    it is clearly a name.
  - Run counters: strong re-checks done in this run (0 now, because they are stored), and a "plan: 0" count that
    older runs lack.
- **The `alive` sweep:** its 100 birth checks were re-derived from the cache with v0. All 100 have the same label;
  $0. The `discover` sweep's birth checks were not re-derived (their prompt is not kept).

**Two things a default rebuild had to pay for, both done 3 Oct ($0.0085 together):**
- **The 2025 trails' masking ($0.0049).** They were masked just before the name-finding prompt was made stronger
  (2 Oct, 12:10 UTC), so 14 masking calls were new. With the old prompt they rebuilt at $0, which is how they were
  checked. They were then saved again with the current masking (`runs/20261003T1252…`): content unchanged.
  - That re-save found a leak. The model listed a person's full name, but the text also uses the first name alone,
    and only the full name was masked. Each part of a full name is now masked too (`privacy.add_people`, tested).
  - A scan of every run file for parts of names the model ever returned found one more first name (32 times) in the
    superseded 2 Oct MuninnAI run. It is masked in that file now.
- **Conjectures 357-359 finished its re-check ($0.0036).** It had stopped at the 6-round limit on 2 Oct (44 lines
  re-checked, 44 changed), like the two trails fixed above. Three more rounds finished it: 9 lines, 7 changed, 3
  holders became 1 (`docs/KNOWN-CASES.md`). It is outside every total: facts and the chance test came out
  identical.

## Model vs model (`heirloom audit models` → `runs/analysis/model-agreement.json`)

- **Claude Sonnet 5.5 vs GPT-6 Luna, every matched line of one belief (2,023 lines):**
  - holds-or-not agreement 96.6%, kappa 0.87;
  - exact-label kappa 0.69.
- **Gemini 3.8 Flash vs GPT-6 Luna on the deciding lines only** (the earliest and latest "affirms" lines — the
  extremes, where a cheap model's slips collect): Gemini rejected 456 of Luna's 617 "affirms" there.
  - That is why the strong model re-checks exactly those lines until the trail's key moments stop moving.
  - It is also why the loop has to finish (see above).

## Next

- The rubric's frame stated explicitly (always judge the belief), with plan lines taken out: tested 3 Oct as v2
  (above), 9 vs 9, not shipped. Next is a second reading of the six disputed items.
