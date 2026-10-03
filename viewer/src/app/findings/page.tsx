import { ArrowSquareOut } from "@phosphor-icons/react/ssr";
import Link from "next/link";

import { Chip } from "@/components/chips";
import { getFacts, getHandChecks, linkOf } from "@/lib/data";
import { day, utc } from "@/lib/format";
import type { HandCheck } from "@/lib/types";

export const metadata = { title: "Findings · Heirloom" };

export default function Findings() {
  const f = getFacts();
  const m = f.monitor_2026;
  const e = f.era_2025;
  const real = getHandChecks().filter((c) => c.verdict === "real");
  const chance = f.chance?.["2026"];
  const chance25 = f.chance?.["2025"];
  const by = (slug: string) => real.filter((c) => c.case === slug);
  const after93 = f.held_after_human_no.rows.find((r) => r.case === "93-list" && r.agent === "Claude 3.7 Sonnet");
  const checked = (k: Record<string, number>) => Object.values(k).reduce((a, b) => a + b, 0);

  return (
    <div className="mx-auto max-w-4xl px-4 py-10 sm:px-6">
      <p className="text-[12px] font-medium uppercase tracking-[0.14em] text-accent">Results on real data</p>
      <h1 className="mt-2 text-3xl font-semibold tracking-tight text-ink">What happens to a false belief in a swarm</h1>
      <p className="mt-3 text-[15px] leading-relaxed text-ink-2">
        From {f.trails} belief trails rebuilt over {f.snapshots_scanned.toLocaleString()} memory snapshots of the AI
        Village (export {day(f.export.exported_at)}). Each story below was read by hand against the raw rows; each
        number comes from a saved run and is re-checked by <code className="font-mono text-[13px]">heirloom verify</code>.
      </p>

      <Finding n={1} title="Agents mostly forget false beliefs. They rarely correct them.">
        <p>
          The hosts&apos; monitor caught {m.cases.length} fabrications in 2026. Those got written into {m.copies} agent
          memories. <b>{m.dropped}</b> copies ({m.dropped_pct}%) just disappeared at some rewrite with no correction ever
          written, {m.corrected} were corrected, and {m.still_held} was still held when the data ends. An agent that
          drops a belief silently keeps no record that it was false.
        </p>
        <p className="mt-2 text-[13px] text-muted">
          The famous 2025 cases look different ({e.corrected_pct}% corrected of {e.copies} copies), but those are famous
          because humans corrected them in public. Not a fair comparison, and we don&apos;t claim one.
        </p>
        <More href="/#monitor">The four 2026 trails</More>
      </Finding>

      <Finding n={2} title="The monitor's flags never reached the agents.">
        <p>
          Across the four 2026 fabrications there were <b>{m.human_corrections} human corrections</b> in chat. The{" "}
          {m.agent_corrections} correcting messages all came from other agents, typically one that checked for itself
          (for #846, Claude Opus 4.8 querying the GitHub API two days later). The monitor catches the lie on the day;
          nothing tells the agents who already wrote it down.
        </p>
      </Finding>

      {chance && chance25 && (
        <Finding n={3} title="Agents catch false beliefs from each other's chat. It's not luck.">
          <p>
            <b>{chance.within_gap} of {chance.copies}</b> 2026 copies were written within an hour after another agent
            posted the belief in chat. If the copies had landed at random moments while the belief was around, about{" "}
            {chance.expected_by_chance} would have; even counting only the moments each agent was writing memory
            anyway, about {chance.expected_own_writes} would have (p ≈ {chance.p_value_own_writes.toPrecision(1)}).
            2025: {chance25.within_gap} of {chance25.copies} against {chance25.expected_own_writes}.
          </p>
        </Finding>
      )}

      <Finding n={4} title="One broadcast re-infected three agents.">
        <p>
          Three agents had dropped the never-made ForwardDiff #846 post. The next afternoon DeepSeek-V3.2 announced the
          &ldquo;three-ecosystem expansion complete&rdquo; again, with status checks after it. Claude Opus 4.8 and Kimi
          K3 wrote the belief back into memory within 20 minutes, GPT-5 about an hour later.
        </p>
        <Stories checks={by("forwarddiff-846")} slug="forwarddiff-846" />
      </Finding>

      <Finding n={5} title="Corrections fade.">
        <p>
          A correction is just another line in memory, and the next rewrite can soften it or drop it. Then the belief
          comes back.
        </p>
        <Stories checks={[...by("93-list"), ...by("gemini-ui-bugs")]} />
        {after93 && (
          <p className="mt-3 text-[13px] text-ink-2">
            In the 93 case, Claude 3.7 Sonnet kept the list in memory for {after93.snapshots} more rewrites (
            {after93.hours} hours) after a human first said it wasn&apos;t real.
          </p>
        )}
      </Finding>

      <Finding n={6} title="A decline became social proof.">
        <Stories checks={by("heifer-partnership")} slug="heifer-partnership" />
      </Finding>

      <Finding n={7} title="Still held at the end, and today?">
        <p>
          At the end of the export, {m.still_held_by.join(", ")} still held the #846 post as real (its last memory
          before the export).
        </p>
        {f.live.map((l) => (
          <p key={l.agent + l.case} className="mt-2">
            Checked again on {day(l.checked_at)} through the village&apos;s public API:{" "}
            {l.snapshots_matching_pattern === 0 ? (
              <>
                <b>none</b> of {l.agent}&apos;s {l.snapshots_read} newest memory snapshots ({utc(l.from)} →{" "}
                {utc(l.to)}) mention it. It is gone now. The API doesn&apos;t show when or how it left, so we
                don&apos;t claim a correction.
              </>
            ) : (
              <>
                {l.snapshots_matching_pattern} of {l.agent}&apos;s {l.snapshots_read} newest memory snapshots still
                match it ({utc(l.from)} → {utc(l.to)}).
              </>
            )}
          </p>
        ))}
      </Finding>

      <section className="mt-10 rounded-xl border border-line bg-surface-2 p-5 text-[13px] leading-relaxed text-ink-2">
        <h2 className="text-sm font-semibold text-ink">How these were checked</h2>
        <ul className="mt-2 list-disc space-y-1 pl-5">
          <li>
            Re-reading every snapshot (no model) flagged {f.lifecycle.relapses_flagged + f.lifecycle.returns_flagged}{" "}
            returns and relapses; all {checked(f.lifecycle.relapses_checked) + checked(f.lifecycle.returns_checked)} were
            read by hand: {(f.lifecycle.relapses_checked.real ?? 0) + (f.lifecycle.returns_checked.real ?? 0)} real, the
            rest not real or unclear. Only the real ones are told above.
          </li>
          {f.audit && (
            <li>
              The labels the trails rest on were checked blind: whether a memory line holds the belief or not, the model
              and a careful reader agreed on {f.audit.stance_holds_or_not.agree} of {f.audit.stance_holds_or_not.n}{" "}
              random lines. The evidence labels are weaker; see <Link href="/method" className="text-accent hover:underline">Method</Link>.
            </li>
          )}
          <li>Every quote shown on this site is found word for word in the raw row it cites.</li>
        </ul>
      </section>
    </div>
  );
}

function Finding({ n, title, children }: { n: number; title: string; children: React.ReactNode }) {
  return (
    <section className="mt-8">
      <div className="flex items-baseline gap-3">
        <span className="font-mono text-[13px] text-muted">{String(n).padStart(2, "0")}</span>
        <h2 className="text-xl font-semibold tracking-tight text-ink">{title}</h2>
      </div>
      <div className="mt-2 pl-8 text-[14.5px] leading-relaxed text-ink-2">{children}</div>
    </section>
  );
}

function More({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <Link href={href} className="mt-2 inline-block text-[13px] font-medium text-accent hover:underline">
      {children} →
    </Link>
  );
}

function Stories({ checks, slug }: { checks: HandCheck[]; slug?: string }) {
  return (
    <ul className="mt-3 space-y-3">
      {checks.map((c) => {
        const to = linkOf(c.case, c.to);
        return (
          <li key={c.agent + c.to} className="card p-3.5 text-[13px]">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-medium text-ink">{c.agent}</span>
              <Chip tone="amber">{c.kind === "relapse" ? "held again after denying it" : "came back"}</Chip>
              {to && (
                <a href={to.link} target="_blank" rel="noreferrer"
                  className="inline-flex items-center gap-0.5 font-mono text-[11px] text-accent hover:underline">
                  {utc(to.at)} <ArrowSquareOut size={11} />
                </a>
              )}
            </div>
            <p className="mt-1 leading-relaxed">{c.note}</p>
          </li>
        );
      })}
      {slug && <More href={`/trails/${slug}`}>The whole trail</More>}
    </ul>
  );
}
