import { cacheLife } from "next/cache";

import type { CaseSummary, ScoreRow, Summary, Trail } from "./types";

// The FastAPI service in api/ (read-only, masked run files). Server-side only.
const API = process.env.HEIRLOOM_API_URL ?? "http://localhost:8787";

async function get<T>(path: string): Promise<T | null> {
  "use cache";
  cacheLife("hours"); // run files change only when the pipeline is re-run
  const res = await fetch(`${API}${path}`);
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`Heirloom API ${path}: ${res.status}`);
  return (await res.json()) as T;
}

export const getSummary = () => get<Summary>("/api/summary");
export const getCases = async () => (await get<CaseSummary[]>("/api/cases")) ?? [];
export const getTrail = (slug: string) => get<Trail>(`/api/trails/${encodeURIComponent(slug)}`);
export const getScore = () =>
  get<{ cases: ScoreRow[]; notes: Record<string, { label: string; text: string }> }>("/api/score");
