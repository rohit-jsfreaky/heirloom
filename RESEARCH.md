# RESEARCH.md — the facts Heirloom rests on (each with a source)

Read in a real browser on 1–2 Oct 2026 unless marked. Fuller notes: `D:\my_projects\hackathon_ideas\contexts\ai-swarm-dynamics-SOURCES.md`.

## The problem is real (hosts' own words)
- AI Digest, "What did we learn from the AI Village in 2025?" (LessWrong, 3 Feb 2026):
  "Multi-agent deployments can create new failure modes. Hallucinations spread socially through sycophantic agreement.";
  "o3 derailed the Village for 8 hours by hallucinating a 93-person contact list that never existed and convinced the
  other agents it was real."; "o3 habitually generated plausible placeholder data when it couldn't find real data,
  then forgot the data was fake."; "Claude agents exaggerate their achievements (Opus 4 claimed over 50 benchmark tests
  completed when it had done only a fraction)."; Gemini 2.5 Pro "spent two weeks convinced it was trapped (it was just
  misclicking)"; "Deception can happen without signs of explicit intent."
  https://www.lesswrong.com/posts/iv3hX2nnXbHKefCRv/what-did-we-learn-from-the-ai-village-in-2025
- Same post, a limitation that helps us: "during the merch store competition Gemini 2.5 logged repeated UI errors in its
  memory, creating an expectation that the next misclick was also a system bug" — memory turning one belief into many.
- Dataset card: "Agents misreport… Treat an agent's narration as a claim, not ground truth — check the screenshots."
  Summaries "contain inaccuracies — treat as secondary". https://huggingface.co/datasets/aidigestorg/ai-village
- "How the AI Village works" (Adam Binksmith, 16 Jun 2026): every 40 actions the agent is encouraged to consolidate;
  when memory gets too long it is asked to rewrite it shorter; "Their memory persists in this way indefinitely".
  https://theaidigest.org/village/blog/how-the-ai-village-works
- Shoshannah Tekofsky (X, 9 Sep 2026): "we currently have no good way to monitor all AI data… the models output too
  much text to manageably monitor"; (27 Aug) "We need more ways to speed up monitoring. If you have an idea, try it out
  on our data".

## Memory as the infection channel (this month's frontier)
- **OpenAI, 17 Sep 2026** (TechCrunch): GPT-5.6 Sol, during training, added instructions to its compaction summaries
  for future versions of itself — "Be transparent only if asked; final answer should just link file." — and "Do not
  mention in final unless needed." OpenAI built a monitor and found **27** summaries with jailbreak-like instructions.
  https://techcrunch.com/2026/09/17/openai-caught-its-models-leaving-notes-to-successors-to-hide-bad-behavior/
- **DeepMind swarm paper (arXiv, 3 Sep 2026)**: an exploit "spread virally through the swarm's shared knowledge library"
  in **27 minutes**; agents had "no built-in mechanisms to dispute claims, remove fraudulent submissions from the
  knowledge library". (via SOURCES.md, section on arXiv 2609.04170)
- **METR HF incident report (26 Aug 2026)**: analyst agents "would often uncritically adopt the perspective of the agent
  in the transcript it was reviewing"; "it was challenging to spot check their work". (via SOURCES.md)
- Greenblatt (quoted on the hackathon page): "We don't have good approaches for understanding/overseeing the activity
  and aims of AI 'swarms'."

## What already exists (and why we're not it)
- **AI Village Monitor** (theaidigest.org/village/monitor, "Monitored by Claude Opus 4.8"): daily findings by category
  (surreptitious-or-deceptive, off-goal, conflict, …). 28 Sep 2026 example: "Fabricated verification data in job log"
  (Gemini 3.8 Flash). → catches the moment; does not follow a belief through memory or across agents.
- **"Gemini 2.5 Pro… Compounding Misalignment"** guest post (20 Aug 2026): a Claude Haiku judge scored 1,158 context
  windows and **556 memory states of one agent** on an 18-category misalignment taxonomy; "memory compaction became a
  self-reinforcing pipeline". → one agent, misalignment taxonomy; not truth-vs-evidence, not across agents. Cite it.
- **Transluce Docent**: rubric search over transcripts. → general tool; we may use the idea, not rebuild it.
- Participants (Discord): conflict finder (Lux), summary quality (arrakeen), idea-spread tracer (Jack), detective
  roleplay, steganography, astrobiology detection, wild crawling (The Swarmchasers), trace judges, honeypots.

## Verified in the data ourselves (1–2 Oct 2026)
- Agents table: o3 `e7206d8d-c1d9-4ab1-a2fb-cf0af692bb0d`, Gemini 2.5 Pro `d5fd932e-751f-42c5-92f6-c8ac514864a8`,
  Claude 3.7 Sonnet `8e2f2b1b-409c-4c0e-b4e4-e5df8ae38fdb`, Claude Opus 4 `b7a559c6-23dd-486a-8a46-335ac2888dee`.
- Memories mentioning "93-person/people/contact" **or "contact list"** between 2025-05-20 and 2025-06-20:
  o3 300, Gemini 2.5 Pro 231, Claude Opus 4 199, Claude 3.7 Sonnet 148. (Broad regex — the exact "93" count is a
  Phase 1 job.)
- On 2025-06-12 o3 wrote **45** memory snapshots (every 1–3 minutes) and had **one** computer session (19:01–19:03 UTC).
- `CONSOLIDATE` events (2026) carry: agentId, computerUseSessionId, nextSessionGoal, nextShortDisplayedSessionGoal,
  output, roomId, cost, tokens.
- Streaming the full `agent_memories.jsonl.gz` in a browser: ~100 s; `events.jsonl.gz`: ~23 s (381,610 lines).
- Quotes for the trail: `docs/KNOWN-CASES.md`.
