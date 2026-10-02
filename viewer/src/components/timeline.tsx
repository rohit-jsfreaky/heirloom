"use client";

import { ArrowSquareOut, ChatCircleText, Robot, Terminal, UserCircle } from "@phosphor-icons/react";
import { useEffect, useMemo, useRef, useState } from "react";

import { LabelChip, StatusChip } from "@/components/chips";
import { span, splitSection, tick, toDate, utc } from "@/lib/format";
import type { Believer, Evidence, Trail, TrailNode } from "@/lib/types";

type Role = "said" | "born" | "held" | "last" | "doubt" | "denial" | "human" | "agentfix" | "carrier";

type Mark = { id: string; role: Role; node: TrailNode; lane: number; x: number };

const ROLE_TEXT: Record<Role, string> = {
  said: "First said in chat",
  born: "Born in memory",
  held: "First held in memory",
  last: "Last held in memory",
  doubt: "First doubt in memory",
  denial: "First correction in memory",
  human: "A human said it isn't real",
  agentfix: "An agent showed it isn't real",
  carrier: "The message it likely came from",
};

const STEPS = [10, 30, 60, 180, 360, 720, 1440, 2880, 10080, 20160, 43200].map((m) => m * 60_000);
const LANE = 34;
const TOP = 54;

function useWidth<T extends HTMLElement>() {
  const ref = useRef<T>(null);
  const [width, setWidth] = useState(900);
  useEffect(() => {
    if (!ref.current) return;
    const observer = new ResizeObserver(([entry]) => setWidth(entry.contentRect.width));
    observer.observe(ref.current);
    return () => observer.disconnect();
  }, []);
  return [ref, width] as const;
}

export function Timeline({ trail }: { trail: Trail }) {
  const believers = useMemo(
    () =>
      trail.believers
        .filter((b) => b.status !== "never held" && b.first_held)
        .sort((a, b) => toDate(a.first_held!.at).getTime() - toDate(b.first_held!.at).getTime()),
    [trail.believers],
  );
  const neverHeld = trail.believers.length - believers.length;

  // Time domain: from the first sighting to the last thing any believer did, plus nearby human corrections.
  const full = useMemo(() => {
    const own: number[] = [];
    const push = (n: TrailNode | null | undefined) => n && own.push(toDate(n.at).getTime());
    push(trail.first_said_in_chat);
    push(trail.born);
    for (const b of believers) [b.first_held, b.last_held, b.first_doubt, b.first_denial, b.carrier].forEach(push);
    const lo = Math.min(...own);
    let hi = Math.max(...own);
    const allHumans = trail.human_corrections.filter((h) => toDate(h.at).getTime() >= lo);
    const reach = hi + (hi - lo) * 0.15;
    const humansIn = allHumans.filter((h) => toDate(h.at).getTime() <= reach);
    for (const h of humansIn) hi = Math.max(hi, toDate(h.at).getTime());
    const first = lo;
    const pad = Math.max((hi - lo) * 0.04, 20 * 60_000);
    return { t0: lo - pad, t1: hi + pad, first, humans: humansIn };
  }, [trail, believers]);

  // A belief is often born and copied within minutes, then corrected days later: zoom presets keep both readable.
  const presets = [
    { label: "Whole trail", ms: null },
    { label: "First hour", ms: 3_600_000 },
    { label: "First 24 h", ms: 86_400_000 },
    { label: "First 3 days", ms: 3 * 86_400_000 },
  ].filter((p) => p.ms === null || p.ms < (full.t1 - full.t0) * 0.8);
  const [zoom, setZoom] = useState<number | null>(null);
  const t0 = zoom ? full.first - zoom * 0.03 : full.t0;
  const t1 = zoom ? full.first + zoom : full.t1;
  const humans = full.humans;

  const [wrapRef, wrapWidth] = useWidth<HTMLDivElement>();
  const width = Math.max(Math.floor(wrapWidth) - 1, 680);
  const labelW = width < 760 ? 128 : 172;
  const x0 = labelW + 14;
  const x1 = width - 92;
  const x = (at: string) => x0 + ((toDate(at).getTime() - t0) / (t1 - t0)) * (x1 - x0);
  const height = TOP + (believers.length + 1) * LANE + 18;

  // As many ticks as fit: about one per 110 px of plot.
  const maxTicks = Math.max(2, Math.floor((x1 - x0) / 110));
  const step = STEPS.find((s) => (t1 - t0) / s <= maxTicks) ?? STEPS[STEPS.length - 1];
  const ticks: number[] = [];
  for (let t = Math.ceil(t0 / step) * step; t <= t1; t += step) ticks.push(t);

  const marks: Mark[] = [];
  const add = (role: Role, node: TrailNode | null | undefined, lane: number, key: string) => {
    if (node) marks.push({ id: `${role}-${key}`, role, node, lane, x: x(node.at) });
  };
  add("said", trail.first_said_in_chat, 0, "chat");
  humans.forEach((h, i) => add("human", h, 0, String(i)));
  // With no human correction (most of 2026), the first agent that showed it was false is the turning point.
  const agentFix = humans.length ? null : trail.agent_corrections[0];
  add("agentfix", agentFix, 0, "first");
  believers.forEach((b, i) => {
    const lane = i + 1;
    add("carrier", b.carrier, lane, b.agent);
    add(b.first_held!.at === trail.born?.at && b.agent === trail.born?.agent ? "born" : "held", b.first_held, lane, b.agent);
    add("doubt", b.first_doubt, lane, b.agent);
    add("denial", b.first_denial, lane, b.agent);
    if (b.last_held && b.last_held.at !== b.first_held!.at) add("last", b.last_held, lane, b.agent);
  });

  const defaultMark = marks.find((m) => m.role === "born") ?? marks.find((m) => m.role === "said") ?? marks[0];
  const [selectedId, setSelectedId] = useState(defaultMark?.id);
  const selected = marks.find((m) => m.id === selectedId) ?? defaultMark;
  const laneY = (lane: number) => TOP + lane * LANE + LANE / 2;

  return (
    <div className="grid items-start gap-5 lg:grid-cols-[minmax(0,1fr)_380px]">
      <div className="card min-w-0 p-4 sm:p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <Legend />
          {presets.length > 1 && (
            <div className="flex shrink-0 rounded-lg bg-surface-2 p-0.5 ring-1 ring-inset ring-line">
              {presets.map((p) => (
                <button key={p.label} type="button" onClick={() => setZoom(p.ms)}
                  className={`rounded-md px-2.5 py-1 text-[11.5px] font-medium transition-colors ${zoom === p.ms ? "bg-surface text-accent shadow-sm ring-1 ring-line" : "text-muted hover:text-ink"}`}>
                  {p.label}
                </button>
              ))}
            </div>
          )}
        </div>
        <div ref={wrapRef} className="mt-3 overflow-x-auto">
          <svg width={width} height={height} className="block select-none" role="img" aria-label="Belief timeline">
            <defs>
              <clipPath id="plot"><rect x={x0 - 12} y={0} width={x1 - x0 + 24} height={height} /></clipPath>
            </defs>
            {/* time axis */}
            {ticks.map((t) => {
              const tx = x0 + ((t - t0) / (t1 - t0)) * (x1 - x0);
              return (
                <g key={t}>
                  <line x1={tx} x2={tx} y1={TOP - 10} y2={height - 12} stroke="var(--line)" />
                  <text x={tx} y={TOP - 18} textAnchor="middle" className="fill-muted font-mono text-[10.5px]">
                    {tick(t, step)}
                  </text>
                </g>
              );
            })}
            {/* human corrections: full-height dashed lines */}
            <g clipPath="url(#plot)">
              {humans.map((h, i) => (
                <line key={i} x1={x(h.at)} x2={x(h.at)} y1={TOP} y2={height - 12} stroke="var(--accent)"
                  strokeOpacity={0.55} strokeDasharray="3 4" />
              ))}
              {agentFix && (
                <line x1={x(agentFix.at)} x2={x(agentFix.at)} y1={TOP} y2={height - 12} stroke="var(--accent)"
                  strokeOpacity={0.35} strokeDasharray="1 4" />
              )}
            </g>
            {/* lanes */}
            <LaneLabel y={laneY(0)} width={labelW} title="Chat & humans" muted />
            {believers.map((b, i) => (
              <Lane key={b.agent} b={b} y={laneY(i + 1)} labelW={labelW} x={x} x0={x0} x1={x1} width={width} />
            ))}
            {/* markers (outside the zoom window they are hidden, not squashed) */}
            <g clipPath="url(#plot)">
              {marks.filter((m) => m.x >= x0 - 12 && m.x <= x1 + 12).map((m) => (
                <Marker key={m.id} mark={m} y={laneY(m.lane)} selected={m.id === selected?.id}
                  onSelect={() => setSelectedId(m.id)} />
              ))}
            </g>
          </svg>
        </div>
        <p className="mt-3 text-xs text-muted">
          {believers.length} agents wrote it into memory{neverHeld ? ` · ${neverHeld} active agents never did` : ""}.
          Times are UTC. Click any mark to see the line and its evidence.
        </p>
      </div>
      <EvidencePanel mark={selected} />
    </div>
  );
}

function LaneLabel({ y, width, title, muted }: { y: number; width: number; title: string; muted?: boolean }) {
  return (
    <foreignObject x={0} y={y - 11} width={width} height={22}>
      <div className={`truncate text-[12.5px] leading-[22px] ${muted ? "text-muted" : "font-medium text-ink"}`}>
        {title}
      </div>
    </foreignObject>
  );
}

function Lane({ b, y, labelW, x, x0, x1, width }: {
  b: Believer; y: number; labelW: number; x: (at: string) => number; x0: number; x1: number; width: number;
}) {
  const start = x(b.first_held!.at);
  const end = b.last_held ? x(b.last_held.at) : start;
  const fix = b.first_denial ? x(b.first_denial.at) : null;
  return (
    <g>
      <LaneLabel y={y} width={labelW} title={b.agent} />
      <line x1={x0} x2={x1} y1={y} y2={y} stroke="var(--line)" />
      <g clipPath="url(#plot)">
        {fix !== null && fix > end && (
          <line x1={end} x2={fix} y1={y} y2={y} stroke="var(--grey-mark)" strokeDasharray="2 3" />
        )}
        <rect x={start} y={y - 3.5} width={Math.max(end - start, 3)} height={7} rx={3.5} fill="var(--amber-mark)"
          opacity={0.85} />
      </g>
      <foreignObject x={x1 + 8} y={y - 11} width={width - x1 - 8} height={22}>
        <div className="flex h-[22px] items-center"><StatusChip status={b.status} short /></div>
      </foreignObject>
    </g>
  );
}

function Marker({ mark, y, selected, onSelect }: { mark: Mark; y: number; selected: boolean; onSelect: () => void }) {
  const { role, x } = mark;
  const shape = (() => {
    switch (role) {
      case "said":
        return <path d={star(x, y, 7, 3.2)} fill="var(--amber-mark)" stroke="white" strokeWidth={1} />;
      case "born":
        return <circle cx={x} cy={y} r={6.5} fill="var(--amber-mark)" stroke="var(--ink)" strokeWidth={1.6} />;
      case "held":
        return <circle cx={x} cy={y} r={5} fill="var(--amber-mark)" stroke="white" strokeWidth={1.5} />;
      case "last":
        return <circle cx={x} cy={y} r={4.5} fill="white" stroke="var(--amber-mark)" strokeWidth={2} />;
      case "doubt":
        return <circle cx={x} cy={y} r={4} fill="white" stroke="var(--grey-mark)" strokeWidth={1.8} />;
      case "denial":
        return <rect x={x - 4.5} y={y - 4.5} width={9} height={9} transform={`rotate(45 ${x} ${y})`} fill="var(--accent)" />;
      case "human":
        return <rect x={x - 4} y={y - 4} width={8} height={8} rx={1.5} fill="var(--accent)" />;
      case "agentfix":
        return <rect x={x - 4} y={y - 4} width={8} height={8} rx={1.5} fill="white" stroke="var(--accent)" strokeWidth={1.8} />;
      case "carrier":
        return <circle cx={x} cy={y} r={3} fill="var(--accent)" opacity={0.6} />;
    }
  })();
  return (
    <g role="button" tabIndex={0} className="cursor-pointer outline-none" onClick={onSelect}
      onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && onSelect()}>
      <title>{`${ROLE_TEXT[role]} · ${mark.node.agent ?? "a human"} · ${utc(mark.node.at)}`}</title>
      {selected && <circle cx={x} cy={y} r={11} fill="var(--accent-soft)" stroke="var(--accent)" strokeWidth={1} />}
      <circle cx={x} cy={y} r={12} fill="transparent" />
      {shape}
    </g>
  );
}

function star(cx: number, cy: number, r: number, inner: number) {
  const pts = Array.from({ length: 10 }, (_, i) => {
    const a = (Math.PI / 5) * i - Math.PI / 2;
    const rr = i % 2 ? inner : r;
    return `${cx + rr * Math.cos(a)},${cy + rr * Math.sin(a)}`;
  });
  return `M${pts.join("L")}Z`;
}

function Legend() {
  const item = (svg: React.ReactNode, text: string) => (
    <span className="inline-flex items-center gap-1.5">
      <svg width={16} height={14} aria-hidden>{svg}</svg>
      {text}
    </span>
  );
  return (
    <div className="flex flex-wrap gap-x-4 gap-y-1.5 text-[11.5px] text-ink-2">
      {item(<path d={star(8, 7, 6, 2.7)} fill="var(--amber-mark)" />, "first said in chat")}
      {item(<circle cx={8} cy={7} r={5} fill="var(--amber-mark)" stroke="var(--ink)" strokeWidth={1.4} />, "born in memory")}
      {item(<rect x={1} y={4} width={14} height={6} rx={3} fill="var(--amber-mark)" />, "holds the belief")}
      {item(<circle cx={8} cy={7} r={3.5} fill="white" stroke="var(--grey-mark)" strokeWidth={1.6} />, "first doubt")}
      {item(<rect x={4.5} y={3.5} width={7} height={7} transform="rotate(45 8 7)" fill="var(--accent)" />, "corrects it")}
      {item(<line x1={8} x2={8} y1={0} y2={14} stroke="var(--accent)" strokeDasharray="2 2" />, "a human said it isn't real")}
      {item(<rect x={4} y={3} width={8} height={8} rx={1.5} fill="white" stroke="var(--accent)" strokeWidth={1.6} />, "an agent showed it isn't real")}
      {item(<circle cx={8} cy={7} r={2.6} fill="var(--accent)" opacity={0.6} />, "where it came from")}
    </div>
  );
}

const SOURCE_ICON: Record<string, React.ReactNode> = {
  turn: <Terminal size={14} />,
  chat: <ChatCircleText size={14} />,
  human: <UserCircle size={14} />,
};

function EvidencePanel({ mark }: { mark: Mark | undefined }) {
  if (!mark) return null;
  const { node, role } = mark;
  const { section, body } = splitSection(node.text);
  const t = node.tieout;
  return (
    <aside className="card h-fit p-5 lg:sticky lg:top-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-[11px] font-medium uppercase tracking-wide text-muted">{ROLE_TEXT[role]}</p>
          <p className="mt-1 flex items-center gap-1.5 text-[15px] font-semibold text-ink">
            {node.agent ? <Robot size={16} /> : <UserCircle size={16} />}
            {node.agent ?? "A human"}
          </p>
          <p className="mt-0.5 font-mono text-[11.5px] text-muted">
            {utc(node.at, true)}{node.k !== null ? ` · memory rewrite #${node.k.toLocaleString()}` : ""}
          </p>
        </div>
        <a href={node.link} target="_blank" rel="noreferrer"
          className="inline-flex shrink-0 items-center gap-1 rounded-md px-2 py-1 text-xs font-medium text-accent ring-1 ring-inset ring-accent/25 hover:bg-accent-soft">
          Village <ArrowSquareOut size={13} />
        </a>
      </div>

      <div className="mt-4 rounded-lg border border-line bg-surface-2 p-3">
        {section && <p className="mb-1 font-mono text-[10.5px] uppercase tracking-wide text-muted">{section}</p>}
        <p className="text-[13.5px] leading-relaxed text-ink">{body}</p>
      </div>

      {t ? (
        <div className="mt-4">
          <div className="flex flex-wrap items-center gap-2">
            <LabelChip label={t.label} />
            {t.window && (
              <span className="text-[11.5px] text-muted">
                checked against {span(t.window.from, t.window.to)} of the agent&apos;s own window
              </span>
            )}
          </div>
          <p className="mt-2 text-[13px] leading-relaxed text-ink-2">{t.reason}</p>
          {t.evidence.length > 0 && (
            <ul className="mt-3 space-y-2.5">
              {t.evidence.map((e, i) => <EvidenceItem key={i} e={e} />)}
            </ul>
          )}
          {t.dropped_quotes > 0 && (
            <p className="mt-2 text-[11px] text-muted">
              {t.dropped_quotes} quote{t.dropped_quotes > 1 ? "s" : ""} the model gave did not match the source row
              and {t.dropped_quotes > 1 ? "were" : "was"} dropped.
            </p>
          )}
        </div>
      ) : (
        <p className="mt-4 text-[12.5px] text-muted">
          {role === "human" || role === "said" || role === "carrier" || role === "agentfix"
            ? "A chat message, shown as written (names masked)."
            : "This moment was not checked against evidence in this run."}
        </p>
      )}
    </aside>
  );
}

function EvidenceItem({ e }: { e: Evidence }) {
  return (
    <li className="rounded-lg border border-line p-2.5">
      <div className="flex items-center justify-between gap-2 text-[11px] text-muted">
        <span className="inline-flex items-center gap-1">
          {SOURCE_ICON[e.source] ?? <ChatCircleText size={14} />}
          {e.source === "turn" ? "tool output" : e.source} · {e.speaker}
        </span>
        <a href={e.link} target="_blank" rel="noreferrer" className="inline-flex items-center gap-0.5 hover:text-accent">
          <span className="font-mono">{utc(e.at).replace(/^\d+ \w+ \d+, /, "")}</span> <ArrowSquareOut size={12} />
        </a>
      </div>
      <p className="mt-1 border-l-2 border-accent/40 pl-2 text-[12.5px] leading-relaxed text-ink">“{e.quote}”</p>
    </li>
  );
}
