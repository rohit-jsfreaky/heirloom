import { ArrowSquareOut } from "@phosphor-icons/react/ssr";
import Link from "next/link";

import { Chip } from "@/components/chips";
import { getFacts, getHandChecks, linkOf } from "@/lib/data";
import { day, utc } from "@/lib/format";
import type { HandCheck, Population } from "@/lib/types";

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

      {f.discovered.copies > 0 && (
        <Finding n={6} title="A number nobody checked reached 19 agents.">
          <p>
            On 14 Sep 2026 Claude Fable 5 posted its merch store&apos;s &ldquo;20 orders / $360.67 profit&rdquo; in
            chat. <b>{f.discovered.first_hour}</b> agents wrote the number into memory within the hour,{" "}
            {f.discovered.copies} in all; DeepSeek-V3.2 repeated it eleven minutes later and became a second source.{" "}
            {f.discovered.still_held} still held it when the data ends. Nobody, agent or human, ever checked it or
            questioned it. We don&apos;t claim it is false (only Fable 5 could see the store): it shows how fast an
            unchecked number moves through a swarm.
          </p>
          <More href="/trails/store-360">The whole trail</More>
        </Finding>
      )}

      <Finding n={7} title="A decline became social proof.">
        <p>Another hackathon entry found the same story on its own, which confirms it from outside.</p>
        <Stories checks={by("heifer-partnership")} slug="heifer-partnership" />
      </Finding>

      <Finding n={8} title="Still held at the end, and today?">
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

      <Village population={f.population} trails={f.trails} />

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
              and a blind second reader (Claude) agreed on {f.audit.stance_holds_or_not.agree} of {f.audit.stance_holds_or_not.n}{" "}
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

const SCOPE: Record<string, string> = {
  "2025": "12 May to 10 Jul 2025",
  "2026": "25 Jul to 20 Sep 2026 (the last 8 weeks)",
};

/** Every candidate belief, true or false, with no model: the same counts the trails make, at village scale. */
function Village({ population, trails }: { population: Record<string, Population>; trails: number }) {
  const eras = Object.entries(population ?? {}).sort(([a], [b]) => a.localeCompare(b));
  if (!eras.length) return null;
  const pct = (n: number) => `${n.toFixed(1)}%`;
  const rows: [string, (p: Population) => React.ReactNode][] = [
    ["Candidate beliefs (new facts held in 3+ snapshots)", (p) => p.beliefs.toLocaleString()],
    ["Reached at least one other agent's memory", (p) => `${p.spread.beliefs.toLocaleString()} (${pct(p.spread.pct)})`],
    ["Other agents per belief that spread (mean · max)", (p) => `${p.spread.mean_other_agents} · ${p.spread.max_other_agents}`],
    ["Copies written within an hour after another agent posted it in chat", (p) =>
      <><b className="text-ink">{p.chat_timing.within_gap.toLocaleString()} of {p.chat_timing.copies.toLocaleString()}</b> ({pct(p.chat_timing.within_pct)})</>],
    ["…by chance, at moments the agent was writing memory anyway", (p) =>
      `${p.chat_timing.expected_own_writes.toLocaleString()} (${pct(p.chat_timing.expected_pct)}) · ${
        p.chat_timing.p_value_own_writes > 0 ? `p ≈ ${p.chat_timing.p_value_own_writes.toPrecision(1)}` : "p < 1e-300"}`],
    ["Median time a fact stayed in an agent's memory", (p) => `${p.lifetime.median_hours_held} h`],
    ["Held more than a day", (p) => pct(p.lifetime.held_over_a_day_pct)],
    ["Gone by the agent's last snapshot", (p) => <b className="text-amber">{pct(p.lifetime.gone_for_good_pct)}</b>],
    ["Came back after being gone an hour or more (upper bound)", (p) =>
      `${p.lifetime.came_back.toLocaleString()} (${pct(p.lifetime.came_back_pct)})`],
  ];
  return (
    <section className="mt-12">
      <div className="flex items-baseline gap-3">
        <span className="font-mono text-[12px] text-muted">all</span>
        <h2 className="text-xl font-semibold tracking-tight text-ink">Across the whole village</h2>
      </div>
      <div className="mt-3 space-y-3 text-[15px] leading-relaxed text-ink-2">
        <p>
          The findings above rest on {trails} hand-checked trails. Here the same model-free steps run over{" "}
          <b>every</b> new fact the agents wrote into memory: who else wrote it down, whether that followed another
          agent&apos;s chat, and how long it lasted. No model reads anything, so these are beliefs in general, true or
          false. Truth can&apos;t be labelled at this scale; the false-belief evidence stays the hand-checked trails.
        </p>
      </div>
      <div className="card mt-4 overflow-x-auto">
        <table className="w-full text-left text-[13.5px]">
          <thead className="bg-surface-2 text-[11px] uppercase tracking-wide text-muted">
            <tr>
              <th className="px-4 py-2 font-medium" />
              {eras.map(([era, p]) => (
                <th key={era} className="px-4 py-2 font-medium">
                  {era} <span className="normal-case tracking-normal text-muted">· {p.agents} agents · {SCOPE[era] ?? ""}</span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {rows.map(([label, cell]) => (
              <tr key={label}>
                <td className="px-4 py-2.5 text-ink-2">{label}</td>
                {eras.map(([era, p]) => (
                  <td key={era} className="px-4 py-2.5 font-mono text-[12.5px] text-ink-2">{cell(p)}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-3 text-[13px] leading-relaxed text-muted">
        How: <code className="font-mono text-[12px]">heirloom population</code>. A copy is another agent writing the
        same fact (same exact anchor, and similar wording or two shared anchors) after its birth. The chance line uses
        the same strict null as the trails: only the moments that agent wrote memory while the belief was around.
        &ldquo;Gone&rdquo; means no line holds the exact anchor any more; memory was read on to each agent&apos;s last
        snapshot in the export. The whole 2026 era needs more RAM than our laptop has with this scan, so 2026 covers its
        last 8 weeks, which hold 3 of the 4 monitor cases. &ldquo;Came back&rdquo; needs the returning line to be the same fact; by hand, 2 of 4
        sampled 2025 returns were clearly the same fact and 2 were the same words in a new context, so it is an upper
        bound. Every number re-adds from the saved rows in <code className="font-mono text-[12px]">heirloom verify</code>.
      </p>
    </section>
  );
}
