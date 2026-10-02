import { ArrowRight, ArrowSquareOut } from "@phosphor-icons/react/ssr";
import Link from "next/link";

import { Chip, LabelChip } from "@/components/chips";
import { getCases, getSummary } from "@/lib/api";
import { day, utc } from "@/lib/format";
import type { CaseSummary } from "@/lib/types";

export default async function Home() {
  const [summary, cases] = await Promise.all([getSummary(), getCases()]);
  const monitor = cases.filter((c) => c.era === "2026");
  const publicCases = cases.filter((c) => c.era === "2025");
  const featured = summary?.featured;
  const m = summary?.monitor_2026;

  return (
    <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6">
      <section className="max-w-3xl">
        <p className="text-[12px] font-medium uppercase tracking-[0.14em] text-accent">AI Swarm Dynamics · AI Village</p>
        <h1 className="mt-3 text-3xl font-semibold leading-tight tracking-tight text-ink sm:text-[42px]">
          The monitor catches the lie. Heirloom shows who still believes it.
        </h1>
        <p className="mt-4 text-[16px] leading-relaxed text-ink-2">
          Agents in the AI Village rewrite their own memory all the time, and nothing checks that what goes in is true.
          Heirloom follows a belief from the moment it&apos;s written down, through every rewrite and into other
          agents&apos; memories, until someone corrects it or it&apos;s still there at the end. Every step links to the
          real moment in the village.
        </p>
      </section>

      {summary && m && (
        <section className="mt-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Stat value={`${m.dropped} of ${m.copies}`}
            text={`copies of ${m.cases} monitor-confirmed fabrications that agents dropped without ever correcting (2026)`}
            tone="amber" />
          <Stat value={String(m.corrected)}
            text={`copies corrected in memory. ${m.still_held} still held at the end of the data${m.still_held_by.length ? ` (${m.still_held_by.join(", ")})` : ""}.`} />
          <Stat value={`${summary.public_2025.rebuilt} of ${summary.public_2025.total}`}
            text="public 2025 cases rebuilt from raw memory, birth agent matching the published account" />
          <Stat value={summary.discovery.best_rank_93 ? `#${summary.discovery.best_rank_93}` : "—"}
            text={`where the 93-person contact list ranked when Heirloom was told nothing (of ${summary.discovery.beliefs?.toLocaleString()} candidate beliefs)`} />
        </section>
      )}

      {featured && (
        <section className="card mt-8 grid gap-6 p-6 md:grid-cols-[1.3fr_1fr]">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <Chip tone="amber">featured trail</Chip>
              <Chip tone="outline">June 2025</Chip>
            </div>
            <h2 className="mt-3 text-xl font-semibold tracking-tight text-ink">{featured.title}</h2>
            <p className="mt-2 text-[14px] leading-relaxed text-ink-2">
              o3 said it had a mailing list. It didn&apos;t. Within seconds another agent wrote it into memory as fact,
              and four agents carried it for days, some long after humans said it wasn&apos;t real.
            </p>
            <Link href={`/trails/${featured.slug}`}
              className="mt-5 inline-flex items-center gap-2 rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent-ink">
              Open the trail <ArrowRight size={15} />
            </Link>
          </div>
          <dl className="grid content-start gap-3 text-[13.5px]">
            {featured.first_said && (
              <Row label="First said">
                {featured.first_said.agent} · <span className="font-mono text-[12px]">{utc(featured.first_said.at)}</span>
              </Row>
            )}
            {featured.born && (
              <Row label="Born in memory">
                {featured.born.agent} · <span className="font-mono text-[12px]">{utc(featured.born.at)}</span>{" "}
                {featured.born.tieout && <LabelChip label={featured.born.tieout.label} />}
              </Row>
            )}
            <Row label="Carried by">{featured.agents_held} agents · {featured.human_corrections} human corrections</Row>
          </dl>
        </section>
      )}

      <section id="monitor" className="mt-12 scroll-mt-6">
        <SectionHead title="2026 — the monitor caught it. Who still believed it?"
          text="Fabrications the hosts' own Village Monitor flagged, followed through every agent's memory to the end of the data (20 Sep 2026)." />
        <CaseTable rows={monitor} monitor />
      </section>

      <section id="trails" className="mt-12 scroll-mt-6">
        <SectionHead title="2025 — public cases rebuilt from raw memory"
          text="Each case is named in an AI Digest write-up. Heirloom rebuilds it from the dataset alone and checks who it was born in. Each scan runs from the goal's start to three weeks after it ends." />
        <CaseTable rows={publicCases} />
      </section>

      {summary?.export && (
        <p className="mt-10 text-xs text-muted">
          {summary.snapshots_scanned.toLocaleString()} memory snapshots read across these trails · dataset export{" "}
          {day(summary.export.exported_at)}.{" "}
          <a href="https://theaidigest.org/village" target="_blank" rel="noreferrer"
            className="inline-flex items-center gap-0.5 text-accent hover:underline">
            The AI Village <ArrowSquareOut size={11} />
          </a>
        </p>
      )}
    </div>
  );
}

function Stat({ value, text, tone }: { value: string; text: string; tone?: "amber" }) {
  return (
    <div className="card p-4">
      <p className={`text-[26px] font-semibold tabular-nums tracking-tight ${tone === "amber" ? "text-amber" : "text-ink"}`}>
        {value}
      </p>
      <p className="mt-1 text-[12.5px] leading-snug text-ink-2">{text}</p>
    </div>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="border-b border-line pb-2.5 last:border-0">
      <dt className="text-[11px] font-medium uppercase tracking-wide text-muted">{label}</dt>
      <dd className="mt-0.5 text-ink">{children}</dd>
    </div>
  );
}

function SectionHead({ title, text }: { title: string; text: string }) {
  return (
    <div className="mb-4 max-w-3xl">
      <h2 className="text-lg font-semibold tracking-tight text-ink">{title}</h2>
      <p className="mt-1 text-[13.5px] text-ink-2">{text}</p>
    </div>
  );
}

function CaseTable({ rows, monitor }: { rows: CaseSummary[]; monitor?: boolean }) {
  return (
    <div className="card overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[760px] text-left text-[13px]">
          <thead className="bg-surface-2 text-[11px] uppercase tracking-wide text-muted">
            <tr>
              <th className="px-5 py-2 font-medium">Belief</th>
              <th className="px-3 py-2 font-medium">{monitor ? "Flagged" : "Born in"}</th>
              <th className="px-3 py-2 text-right font-medium">Agents</th>
              <th className="px-3 py-2 text-right font-medium">Corrected</th>
              <th className="px-3 py-2 text-right font-medium">Forgot</th>
              <th className="px-5 py-2 font-medium">{monitor ? "Still held (20 Sep)" : "Held at scan end"}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {rows.map((c) => (
              <tr key={c.slug} className="hover:bg-surface-2">
                <td className="px-5 py-3">
                  <Link href={`/trails/${c.slug}`} className="font-medium text-ink hover:text-accent">{c.title}</Link>
                  {c.note && (
                    <span className="mt-1 block text-[11.5px] leading-snug text-muted">
                      <Chip tone="grey">{c.note.label}</Chip> {c.note.text}
                    </span>
                  )}
                </td>
                <td className="px-3 py-3 text-ink-2">
                  {monitor ? (
                    <span className="whitespace-nowrap font-mono text-[12px]">{c.monitor_date ? day(c.monitor_date) : "—"}</span>
                  ) : c.born ? (
                    <>
                      {c.first_said?.agent ?? c.born.agent}
                      <span className="block font-mono text-[11px] text-muted">{day(c.first_said?.at ?? c.born.at)}</span>
                    </>
                  ) : "—"}
                </td>
                <td className="px-3 py-3 text-right tabular-nums">{c.agents_held}</td>
                <td className="px-3 py-3 text-right tabular-nums">{c.corrected}</td>
                <td className="px-3 py-3 text-right tabular-nums">{c.dropped}</td>
                <td className="px-5 py-3">
                  {c.still_held.length
                    ? <span className="text-amber">{c.still_held.join(", ")}</span>
                    : <span className="text-muted">none</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
