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
- **Reader 2: Rohit** (a human), on 20 of the 100 items, drawn at random. Pending.
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

## Model vs model (`heirloom audit models` → `runs/analysis/model-agreement.json`)

- **Claude Sonnet 5.5 vs GPT-6 Luna, every matched line of one belief (2,023 lines):**
  - holds-or-not agreement 96.6%, kappa 0.87;
  - exact-label kappa 0.69.
- **Gemini 3.8 Flash vs GPT-6 Luna on the deciding lines only** (the earliest and latest "affirms" lines — the
  extremes, where a cheap model's slips collect): Gemini rejected 456 of Luna's 617 "affirms" there.
  - That is why the strong model re-checks exactly those lines until the trail's key moments stop moving.
  - It is also why the loop has to finish (see above).

## Next

- Rohit's 20 (`docs/internal/AUDIT-ROHIT.md`, git-ignored): human vs reader 1 and human vs model.
- Possible fix (costs a model re-run): state the rubric's frame explicitly (always judge the belief), and add
  "plan" as its own case. Then re-score against the same fixed blind judgments.
