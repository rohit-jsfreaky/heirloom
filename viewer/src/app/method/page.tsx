import { LabelChip } from "@/components/chips";
import { getFacts, getModelAgreement, getVerify } from "@/lib/data";
import { day } from "@/lib/format";

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
    text: "A cheap model (GPT-6 Luna) labels every matching line once: holds it, doubts it, denies it, or unrelated — with the section heading it sits under. A stronger model (Gemini 3.8 Flash) re-checks the lines that decide the key moments (birth, first held, last held, first correction) and repeats until those moments stop moving. In 2026 trails every copy's first and last line is strong-checked.",
  },
  {
    title: "Check it against the agent's own evidence",
    text: "At the key moments, the line is checked against the agent's own window. The label comes from that evidence, never from the model's opinion. Every quote must appear in the row it cites, or it's dropped. An agent's own chat is never evidence for itself.",
  },
];

const LIMITS = [
  "Screenshots aren't read, so a true fact the agent only saw on screen looks like “no evidence”.",
  "The evidence labels are the weak part: a blind check agreed with them about half the time (details above). The rubric is ambiguous on correction lines, and the checker under-calls hearsay at a belief's birth. No headline number rests on them.",
  "A line that only schedules something (“posting to #846 at 1 PM”) is read as holding the belief by both models. For the ForwardDiff trail a rule with no model now marks those lines as plans; other beliefs about an event have no such rule yet.",
  "A blind sweep over 2026 memory found 5 “contradicted” beliefs still held; checked by hand, none held up. The 2026 results here start from the hosts' own monitor findings instead.",
  "A belief written with different numbers or units (“93 contacts”, “93 emails”) can split into several entries when nobody names it first.",
  "“Held at scan end” for 2025 cases means three weeks after the goal ended, not the end of the data.",
  "Name masking errs on the side of privacy: a few everyday words that are also chat handles get masked too.",
];

const MODEL = (id: string) =>
  ({ "openai/gpt-6-luna": "GPT-6 Luna", "google/gemini-3.8-flash": "Gemini 3.8 Flash", "anthropic/claude-sonnet-5.5": "Claude Sonnet 5.5" })[id] ?? id;

export default function Method() {
  const facts = getFacts();
  const audit = facts.audit;
  const verify = getVerify();
  const quotes = verify?.checks.find((c) => c.name.startsWith("every evidence quote"));
  const lines = verify?.checks.find((c) => c.name.startsWith("every memory and chat line"));
  const sonnet = getModelAgreement().find((p) => p.sample.startsWith("every"));
  const chance = facts.chance?.["2026"];
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

      <h2 className="mt-10 text-lg font-semibold tracking-tight text-ink">How sure are we?</h2>
      <div className="card mt-3 divide-y divide-line text-[14px] leading-relaxed text-ink-2">
        {verify && (
          <p className="p-4">
            <b className="text-ink">Every saved result is re-checked</b> by <code className="font-mono text-[12.5px]">heirloom verify</code>{" "}
            ({day(verify.at)}{verify.with_database ? ", with the dataset" : ""}): {quotes?.ok ?? "—"} of{" "}
            {(quotes?.ok ?? 0) + (quotes?.failed ?? 0)} evidence quotes and {lines?.ok ?? "—"} of{" "}
            {(lines?.ok ?? 0) + (lines?.failed ?? 0)} memory and chat lines are found word for word in the raw rows they
            cite; links, time order, statuses and privacy all pass; every number in the write-up is checked against the
            saved runs.
          </p>
        )}
        {audit && (
          <p className="p-4">
            <b className="text-ink">A blind label check</b> ({audit.items} random labels, fixed seed): on whether a memory
            line holds the belief, the model and a careful reader agreed on {audit.stance_holds_or_not.agree} of{" "}
            {audit.stance_holds_or_not.n}. The evidence labels are weaker: {audit.evidence_birth.agree} of{" "}
            {audit.evidence_birth.n} at a belief&apos;s birth; at corrections {audit.evidence_correction_either_reading.agree}{" "}
            of {audit.evidence_correction_either_reading.n} once both readings of the rubric are allowed.
            {audit.claude_vs_rohit
              ? ` A human re-checked ${audit.claude_vs_rohit.n} of them and agreed with the reader on ${audit.claude_vs_rohit.agree}.`
              : " A human re-check of 20 is under way."}
          </p>
        )}
        {sonnet && (
          <p className="p-4">
            <b className="text-ink">Two models on the same {sonnet.lines.toLocaleString()} lines</b> ({MODEL(sonnet.a)} and{" "}
            {MODEL(sonnet.b)}) agree on holds-or-not {(sonnet.holds_agree * 100).toFixed(1)}% of the time (kappa{" "}
            {sonnet.holds_kappa}).
          </p>
        )}
        {chance && (
          <p className="p-4">
            <b className="text-ink">Spread by chat is tested against chance:</b> {chance.within_gap} of {chance.copies}{" "}
            2026 copies came within an hour after another agent posted the belief, against about{" "}
            {chance.expected_own_writes} if the copy had landed at any moment the agent was writing memory anyway.
          </p>
        )}
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
        prompts. One unscrubbed password found in the data was never used, is masked everywhere, and is flagged for the
        hosts.
      </p>
    </div>
  );
}
