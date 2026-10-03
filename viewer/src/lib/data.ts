// Reads the saved, masked run files in ../runs at build time. The site is a static export: no server, no API.
// Every number comes from runs/analysis/facts.json, which `heirloom facts` computes and `heirloom verify` checks.

import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";

import type { CaseSummary, Facts, HandCheck, Lifecycle, ScoreRow, Summary, Trail } from "./types";

const RUNS = process.env.HEIRLOOM_RUNS ?? path.join(process.cwd(), "..", "runs");
const ANALYSIS = path.join(RUNS, "analysis");
const RUN_NAME = /^\d{8}T\d{6}Z-(.+)\.json$/;

const memo = new Map<string, unknown>();
function readJson<T>(file: string): T | null {
  if (!memo.has(file)) {
    try {
      memo.set(file, JSON.parse(readFileSync(file, "utf-8")));
    } catch {
      memo.set(file, null);
    }
  }
  return memo.get(file) as T | null;
}

/** Newest saved file per run name (file names start with a UTC timestamp, so they sort by time). */
function latestRuns(): Map<string, string> {
  const out = new Map<string, string>();
  for (const name of readdirSync(RUNS).sort()) {
    const m = RUN_NAME.exec(name);
    if (m) out.set(m[1], path.join(RUNS, name));
  }
  return out;
}

const isTrail = (slug: string) => !/^(score|discover-|alive-)/.test(slug);

export function getFacts(): Facts {
  const facts = readJson<Facts>(path.join(ANALYSIS, "facts.json"));
  if (!facts) throw new Error(`no facts file in ${ANALYSIS}: run \`uv run heirloom facts\` in pipeline/`);
  return facts;
}

function sources(): Record<string, string> {
  const score = getScore();
  return Object.fromEntries((score?.cases ?? []).map((c) => [c.case, c.source ?? ""]));
}

function summaryOf(slug: string, trail: Omit<Trail, "summary">, facts: Facts, src: Record<string, string>): CaseSummary {
  const held = trail.believers.filter((b) => b.status !== "never held");
  const count = (s: string) => held.filter((b) => b.status === s).length;
  return {
    slug,
    title: trail.title,
    statement: trail.statement,
    era: (facts.eras[slug] ?? "discovered") as CaseSummary["era"],
    monitor_date: facts.monitor_dates[slug] ?? null,
    source: src[slug] ?? "",
    note: facts.notes[slug] ?? null,
    first_said: trail.first_said_in_chat,
    born: trail.born,
    agents_held: held.length,
    corrected: count("corrected"),
    dropped: count("dropped without correction"),
    still_held: held.filter((b) => b.status === "held at end of scan").map((b) => b.agent),
    human_corrections: trail.human_corrections.length,
    snapshots_scanned: trail.counts.snapshots_scanned,
    scan: trail.scan,
  };
}

export function getTrail(slug: string): Trail | null {
  const file = latestRuns().get(slug);
  if (!file || !isTrail(slug)) return null;
  const trail = readJson<Omit<Trail, "summary">>(file);
  if (!trail?.believers) return null;
  return { ...trail, summary: summaryOf(slug, trail, getFacts(), sources()) };
}

export function getCases(): CaseSummary[] {
  const facts = getFacts();
  const order = new Map(facts.order.map((s, i) => [s, i]));
  return [...latestRuns().keys()]
    .filter(isTrail)
    .map((slug) => getTrail(slug)?.summary)
    .filter((c): c is CaseSummary => Boolean(c))
    .sort((a, b) => (order.get(a.slug) ?? 99) - (order.get(b.slug) ?? 99) || a.slug.localeCompare(b.slug));
}

export function getScore(): { cases: ScoreRow[] } | null {
  const file = latestRuns().get("score");
  return file ? readJson<{ cases: ScoreRow[] }>(file) : null;
}

export function getSummary(): Summary {
  const facts = getFacts();
  return {
    export: facts.export,
    public_2025: facts.public_2025,
    discovery: facts.discovery,
    monitor_2026: { ...facts.monitor_2026, cases: facts.monitor_2026.cases.length },
    featured: getCases().find((c) => c.slug === facts.featured) ?? null,
    snapshots_scanned: facts.snapshots_scanned,
    facts,
  };
}

export function getLifecycle(slug: string): Lifecycle | null {
  return readJson<Lifecycle>(path.join(ANALYSIS, `lifecycle-${slug}.json`));
}

export function getHandChecks(): HandCheck[] {
  return readJson<{ checks: HandCheck[] }>(path.join(ANALYSIS, "hand-checks.json"))?.checks ?? [];
}

/** The village link of a snapshot that a lifecycle file recorded (hand checks cite snapshot ids). */
export function linkOf(slug: string, ref: string): { at: string; link: string } | null {
  const life = getLifecycle(slug);
  for (const a of life?.agents ?? []) {
    for (const p of [
      ...a.episodes.flatMap((e) => [e.from, e.to]),
      ...a.returns.flatMap((r) => [r.gone_from, r.back_at]),
      ...(a.relapse ? [a.relapse.denied, a.relapse.held_again] : []),
    ]) {
      if (p.ref === ref) return { at: p.at, link: p.link };
    }
  }
  return null;
}

export type VerifyRun = {
  at: string;
  with_database: boolean;
  passed: boolean;
  checks: { name: string; passed: boolean; ok: number; failed: number }[];
};

/** The last `heirloom verify` run (with the dataset, when it was available). */
export function getVerify(): VerifyRun | null {
  return readJson<VerifyRun>(path.join(ANALYSIS, "verify.json"));
}

export type ModelPair = { a: string; b: string; lines: number; sample: string; kappa: number; holds_agree: number; holds_kappa: number };

export function getModelAgreement(): ModelPair[] {
  return readJson<{ pairs: ModelPair[] }>(path.join(ANALYSIS, "model-agreement.json"))?.pairs ?? [];
}
