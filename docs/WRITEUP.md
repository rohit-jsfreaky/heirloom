# WRITEUP.md — submission skeleton (fill only with numbers from saved runs)

## Title
Heirloom — the life of a false belief in a village of AI agents

## One line
The monitor catches the lie. Heirloom shows who still believes it.

## The problem (≤ 120 words)
Long-running agents rewrite their own memory constantly. In the AI Village that's every ~40 actions (every few minutes
in 2025). Nothing checks that what goes into memory is true. A wrong belief becomes a "fact", is read back next session,
and is copied by other agents — the 2025 retrospective: "Hallucinations spread socially through sycophantic agreement."
In swarms the same channel carries worse things: OpenAI's models left notes to future selves in compaction summaries
("Be transparent only if asked"); DeepMind's swarm spread an exploit through its shared knowledge library in 27 minutes.
Investigators of the Hugging Face incident said "we don't have good approaches for understanding… AI swarms".

## What Heirloom does
For every belief written into an agent's memory: born (with the contrary evidence from the agent's own window) →
written as fact → inherited across rewrites → spread to other agents (the carrier message) → corrected, or still alive.
Each step links to the moment in the live village.

## How it works (≤ 150 words)
Memory snapshots → windows between snapshots → line diff → checkable claims → tie-out against the window's tool outputs,
chat, human messages and searches → lineage across rewrites and agents. Labels come from evidence, never from the
model's opinion; every quote is verified to exist in a real row. Same method across both scaffolding eras.

## Results
- Validation: the 93-person contact list rebuilt automatically — [birth, believers, correction, hours, rewrites].
- Known cases recovered: [x / y] (table from KNOWN-CASES.md).
- New findings (hand-verified): [N] beliefs still alive in the [date range] export, top ones with trails.
- Coverage: [snapshots], [windows with changes], [claims], [tied out], cost [$].

## Limits (say them plainly)
LLM extraction misses some claims; screenshots not yet checked; "no evidence" ≠ false; scaffolding changes (CHANGELOG)
can look like behaviour changes; the export is ≈ [date].

## Data and citation
AI Digest / AI Village dataset (aidigestorg/ai-village), used under its research terms: no training, no
re-identification; human names masked. Prior work built on: "Gemini 2.5 Pro… Compounding Misalignment" (memory states
of one agent), the AI Village Monitor.

## Video script (≤ 3 min) — follows the 60-second demo in CLAUDE.md, then 1 minute of new findings + 30 s on method.
