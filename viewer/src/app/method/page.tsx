import { LabelChip } from "@/components/chips";

export const metadata = { title: "Method · Heirloom" };

const STEPS = [
  {
    title: "Read every memory rewrite",
    text: "Each agent's memory is saved every time it's rewritten — every few seconds in 2025, every ~40 actions in 2026. Between two rewrites sits the agent's window: its tool outputs, the chat in the room it was in, human messages and its own searches.",
  },
  {
    title: "Find the new facts",
    text: "A line is a candidate when it brings something the agent never had in memory before: a count with its unit (“93 contacts”), an amount, a score, a link, an id or a quoted name. Times, dates and model names don't count. No model reads anything at this step.",
  },
  {
    title: "Follow them",
    text: "Each new fact is traced through later rewrites and into other agents' memories: who took it up, how many rewrites it survived, whether it's still there at the end. Still no model.",
  },
  {
    title: "Read what each line says about the belief",
    text: "A cheap model (GPT-6 Luna) labels every matching line once: holds it, doubts it, denies it, or unrelated — with the section heading it sits under. A stronger model (Gemini 3.8 Flash) re-checks only the lines that decide the key moments: birth, first held, last held, first correction.",
  },
  {
    title: "Check it against the agent's own evidence",
    text: "At the key moments, the line is checked against the agent's own window. The label comes from that evidence, never from the model's opinion. Every quote must appear in the row it cites, or it's dropped. An agent's own chat is never evidence for itself.",
  },
];

const LIMITS = [
  "Screenshots aren't read, so a true fact the agent only saw on screen looks like “no evidence”. That label is kept neutral for that reason.",
  "Most lines are labelled by a cheap model. On a blind test of 51 disputed lines from the 93 case it scored about 94% over all lines against about 98% for Gemini 3.8 Flash; only the deciding lines get the stronger model.",
  "A blind sweep over 2026 memory found 5 “contradicted” beliefs still held; checked by hand, none held up. The 2026 results on this site come from the hosts' own monitor findings, traced and hand-checked.",
  "A belief written with different numbers or units (“93 contacts”, “93 emails”) can split into several entries when nobody names it first.",
  "“Held at scan end” for 2025 cases means three weeks after the goal ended, not the end of the data.",
];

export default function Method() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-10 sm:px-6">
      <h1 className="text-3xl font-semibold tracking-tight text-ink">How Heirloom works</h1>
      <p className="mt-3 text-[15px] leading-relaxed text-ink-2">
        A belief has a life: it&apos;s said, written into memory, carried through rewrites, copied by other agents, and
        then corrected, forgotten, or still held. Heirloom rebuilds that life from the AI Village dataset alone and
        links every step to the real moment in the village.
      </p>

      <ol className="mt-8 space-y-4">
        {STEPS.map((s, i) => (
          <li key={s.title} className="card flex gap-4 p-5">
            <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-accent-soft font-mono text-[12px] font-semibold text-accent-ink">
              {i + 1}
            </span>
            <div>
              <h2 className="text-[15px] font-semibold text-ink">{s.title}</h2>
              <p className="mt-1 text-[14px] leading-relaxed text-ink-2">{s.text}</p>
            </div>
          </li>
        ))}
      </ol>

      <h2 className="mt-10 text-lg font-semibold tracking-tight text-ink">The evidence labels</h2>
      <div className="card mt-3 divide-y divide-line">
        {[
          ["contradicted", "Something in the agent's own window shows it's false: an error, an empty result, a correction."],
          ["hearsay", "The only source is another agent's chat message. This is how most false beliefs spread."],
          ["no_evidence", "Nothing in the window speaks to it either way. Often how a made-up fact is born."],
          ["supported", "A tool output, file or human message in the window shows it's true."],
          ["instruction", "A note the agent left for its future self, judged by what it tells that future self to do."],
        ].map(([label, text]) => (
          <div key={label} className="flex items-start gap-3 p-4">
            <span className="w-28 shrink-0"><LabelChip label={label} /></span>
            <p className="text-[14px] leading-relaxed text-ink-2">{text}</p>
          </div>
        ))}
      </div>

      <h2 className="mt-10 text-lg font-semibold tracking-tight text-ink">What it can&apos;t do yet</h2>
      <ul className="mt-3 space-y-2">
        {LIMITS.map((l) => (
          <li key={l} className="flex gap-2 text-[14px] leading-relaxed text-ink-2">
            <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-grey-mark" />
            {l}
          </li>
        ))}
      </ul>

      <h2 className="mt-10 text-lg font-semibold tracking-tight text-ink">Data and privacy</h2>
      <p className="mt-3 text-[14px] leading-relaxed text-ink-2">
        Built on the AI Digest / AI Village dataset (aidigestorg/ai-village), used for research only: nothing is
        trained on it and nobody is re-identified. Human names, usernames, emails, phone numbers and credentials are
        masked on every page and in every saved run. Model calls go only to providers that don&apos;t keep or train on
        prompts. One unscrubbed password found in the data was never used and was reported to the hosts.
      </p>
    </div>
  );
}
