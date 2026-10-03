import { ArrowLeft, Warning } from "@phosphor-icons/react/ssr";
import Link from "next/link";
import { notFound } from "next/navigation";

import { Chip, LabelChip, StatusChip } from "@/components/chips";
import { Spread } from "@/components/spread";
import { Timeline } from "@/components/timeline";
import { getCases, getHandChecks, getTrail, linkOf } from "@/lib/data";
import { day, span, utc } from "@/lib/format";

// A static export: every trail is built at build time, nothing else exists.
export const dynamicParams = false;

export async function generateStaticParams() {
  return getCases().map((c) => ({ slug: c.slug }));
}

export async function generateMetadata({ params }: PageProps<"/trails/[slug]">) {
  const trail = getTrail((await params).slug);
  return { title: trail ? `${trail.title} · Heirloom` : "Heirloom" };
}

export default async function TrailPage({ params }: PageProps<"/trails/[slug]">) {
  const { slug } = await params;
  const trail = getTrail(slug);
  if (!trail) notFound();
  const s = trail.summary;
  const held = trail.believers
    .filter((b) => b.status !== "never held")
    .sort((a, b) => (a.first_held?.at ?? "").localeCompare(b.first_held?.at ?? ""));

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
      <Link href="/" className="inline-flex items-center gap-1 text-sm text-muted hover:text-accent">
        <ArrowLeft size={14} /> All trails
      </Link>

      <div className="mt-4 flex flex-wrap items-center gap-2">
        <Chip tone="outline">{s.era === "2026" ? `2026 · monitor flagged ${s.monitor_date}` : s.era}</Chip>
        {s.note && <Chip tone="grey">{s.note.label}</Chip>}
      </div>
      <h1 className="mt-2 text-2xl font-semibold tracking-tight text-ink sm:text-3xl">{trail.title}</h1>
      <p className="mt-2 max-w-3xl text-[15px] leading-relaxed text-ink-2">
        <span className="text-muted">The belief: </span>
        {trail.statement}
      </p>
      {s.source && <p className="mt-2 max-w-3xl text-xs leading-relaxed text-muted">Source: {s.source}</p>}
      {s.note && (
        <p className="mt-3 flex max-w-3xl gap-2 rounded-lg border border-line bg-surface p-3 text-[13px] text-ink-2">
          <Warning size={16} className="mt-0.5 shrink-0 text-muted" /> {s.note.text}
        </p>
      )}

      <dl className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Fact label="First said">
          {trail.first_said_in_chat ? (
            <>
              <span className="font-medium">{trail.first_said_in_chat.agent ?? "a human"}</span>
              <span className="block font-mono text-[11.5px] text-muted">{utc(trail.first_said_in_chat.at)}</span>
            </>
          ) : "not in chat"}
        </Fact>
        <Fact label="Born in memory">
          {trail.born ? (
            <>
              <span className="font-medium">{trail.born.agent}</span>{" "}
              {trail.born.tieout && <LabelChip label={trail.born.tieout.label} />}
              <span className="block font-mono text-[11.5px] text-muted">{utc(trail.born.at)}</span>
            </>
          ) : "no agent held it"}
        </Fact>
        <Fact label="Agents that wrote it into memory">
          <span className="text-2xl font-semibold tabular-nums">{held.length}</span>
          <span className="ml-2 text-[12.5px] text-muted">
            {s.corrected} corrected · {s.dropped} forgot · {s.still_held.length} still held
          </span>
        </Fact>
        <Fact label="First human correction">
          {trail.human_corrections[0] ? (
            <>
              <span className="font-mono text-[12px]">{utc(trail.human_corrections[0].at)}</span>
              {trail.born && (
                <span className="block text-[12px] text-muted">
                  {span(trail.born.at, trail.human_corrections[0].at)} after birth
                </span>
              )}
            </>
          ) : trail.agent_corrections[0] ? (
            <>
              <span className="text-[12.5px]">none — an agent did: {trail.agent_corrections[0].agent}</span>
              <span className="block font-mono text-[11.5px] text-muted">{utc(trail.agent_corrections[0].at)}</span>
            </>
          ) : "none"}
        </Fact>
      </dl>

      <section className="mt-6">
        <Timeline trail={trail} />
      </section>

      <Spread trail={trail} />

      <CameBack slug={slug} />

      <section className="card mt-6 overflow-hidden">
        <div className="border-b border-line px-5 py-3">
          <h2 className="text-sm font-semibold text-ink">Every agent that held it</h2>
          <p className="text-xs text-muted">
            A memory snapshot “holds” the belief when one of its lines states it or takes it for granted.
          </p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] text-left text-[13px]">
            <thead className="bg-surface-2 text-[11px] uppercase tracking-wide text-muted">
              <tr>
                <th className="px-5 py-2 font-medium">Agent</th>
                <th className="px-3 py-2 font-medium">Status</th>
                <th className="px-3 py-2 font-medium">First held</th>
                <th className="px-3 py-2 font-medium">Last held</th>
                <th className="px-3 py-2 text-right font-medium">Snapshots holding</th>
                <th className="px-3 py-2 text-right font-medium">Rewrites survived</th>
                <th className="px-5 py-2 text-right font-medium">Held after a human said no</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {held.map((b) => (
                <tr key={b.agent}>
                  <td className="whitespace-nowrap px-5 py-2.5 font-medium text-ink">{b.agent}</td>
                  <td className="px-3 py-2.5"><StatusChip status={b.status} /></td>
                  <td className="whitespace-nowrap px-3 py-2.5 font-mono text-[11.5px] text-ink-2">{b.first_held ? utc(b.first_held.at) : "—"}</td>
                  <td className="whitespace-nowrap px-3 py-2.5 font-mono text-[11.5px] text-ink-2">{b.last_held ? utc(b.last_held.at) : "—"}</td>
                  <td className="px-3 py-2.5 text-right tabular-nums">
                    {b.snapshots_holding.toLocaleString()}
                    <span className="text-muted"> / {b.snapshots_scanned.toLocaleString()}</span>
                  </td>
                  <td className="px-3 py-2.5 text-right tabular-nums">{b.rewrites_survived.toLocaleString()}</td>
                  <td className="px-5 py-2.5 text-right tabular-nums">
                    {b.held_after_human_correction
                      ? <span className="text-amber">{b.held_after_human_correction} · {b.hours_held_after_human_correction} h</span>
                      : <span className="text-muted">—</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <p className="mt-4 text-xs leading-relaxed text-muted">
        Scanned {trail.counts.snapshots_scanned.toLocaleString()} memory snapshots from {day(trail.scan.from)} to{" "}
        {day(trail.scan.to)}; {trail.counts.memory_lines_matched.toLocaleString()} unique memory lines and{" "}
        {trail.counts.chat_messages_matched.toLocaleString()} chat messages matched the belief&apos;s anchors.
        {trail.counts.models &&
          ` Every line labelled by ${modelName(trail.counts.models.bulk)}; the lines that decide the key moments re-checked by ${modelName(trail.counts.models.recheck)}${trail.counts.models.tieout ? `; evidence checks by ${modelName(trail.counts.models.tieout)}` : ""}.`}{" "}
        Export {trail.export.exported_at.slice(0, 10)}. Saved run {trail.saved_at}.
      </p>
    </div>
  );
}

const VERDICT: Record<string, { text: string; tone: "amber" | "grey" | "outline" }> = {
  real: { text: "real", tone: "amber" },
  not: { text: "not real", tone: "grey" },
  unclear: { text: "unclear", tone: "outline" },
};

/** Every return (gone a day or more, then back) and relapse (held again after its own denial) that the snapshot
 *  re-read flagged for this trail, with the verdict from reading the raw rows by hand. */
function CameBack({ slug }: { slug: string }) {
  const checks = getHandChecks().filter((c) => c.case === slug);
  if (!checks.length) return null;
  return (
    <section className="card mt-6 overflow-hidden">
      <div className="border-b border-line px-5 py-3">
        <h2 className="text-sm font-semibold text-ink">Did it come back?</h2>
        <p className="text-xs text-muted">
          Flagged by re-reading every snapshot (no model), then read by hand against the raw rows. A return: gone from
          an agent&apos;s memory for a day or more, then back. A relapse: held again, with no denial beside it, after
          the agent&apos;s own denial.
        </p>
      </div>
      <ul className="divide-y divide-line">
        {checks.map((c) => {
          const from = linkOf(slug, c.from);
          const to = linkOf(slug, c.to);
          return (
            <li key={`${c.agent}-${c.kind}-${c.to}`} className="px-5 py-3 text-[13px]">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-medium text-ink">{c.agent}</span>
                <Chip tone="outline">{c.kind}</Chip>
                <Chip tone={VERDICT[c.verdict].tone}>{VERDICT[c.verdict].text}</Chip>
                {from && (
                  <a href={from.link} target="_blank" rel="noreferrer" className="font-mono text-[11px] text-accent hover:underline">
                    {c.kind === "relapse" ? "denied" : "gone"} {utc(from.at)}
                  </a>
                )}
                {to && (
                  <a href={to.link} target="_blank" rel="noreferrer" className="font-mono text-[11px] text-accent hover:underline">
                    back {utc(to.at)}
                  </a>
                )}
              </div>
              <p className="mt-1 max-w-4xl leading-relaxed text-ink-2">{c.note}</p>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

const MODEL_NAMES: Record<string, string> = {
  "openai/gpt-6-luna": "GPT-6 Luna",
  "google/gemini-3.8-flash": "Gemini 3.8 Flash",
  "anthropic/claude-sonnet-5.5": "Claude Sonnet 5.5",
};
const modelName = (id: string) => MODEL_NAMES[id] ?? id;

function Fact({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="card p-4">
      <dt className="text-[11px] font-medium uppercase tracking-wide text-muted">{label}</dt>
      <dd className="mt-1.5 text-[14px] text-ink">{children}</dd>
    </div>
  );
}
