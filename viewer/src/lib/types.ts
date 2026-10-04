// Shapes of the masked run files in runs/ (written by the pipeline) and runs/analysis/facts.json.

export type Evidence = {
  source: string; // turn | chat | human | search | session_summary | consolidate
  id: string;
  at: string;
  speaker: string;
  quote: string;
  link: string;
};

export type TieOut = {
  label: "supported" | "contradicted" | "hearsay" | "no_evidence" | "instruction";
  reason: string;
  evidence: Evidence[];
  carrier: { source: string; id: string; at: string; speaker: string; link: string } | null;
  window: { from: string; to: string } | null;
  dropped_quotes: number;
};

export type TrailNode = {
  kind: "memory" | "chat";
  agent: string | null;
  at: string;
  text: string;
  link: string;
  ref: string;
  k: number | null;
  tieout: TieOut | null;
};

export type Believer = {
  agent: string;
  snapshots_scanned: number;
  snapshots_holding: number;
  snapshots_with_both: number;
  first_held: TrailNode | null;
  last_held: TrailNode | null;
  first_doubt: TrailNode | null;
  first_denial: TrailNode | null;
  said_it_first: boolean;
  exposed_by: TrailNode | null;
  carrier: TrailNode | null;
  rewrites_survived: number;
  held_after_human_correction: number;
  hours_held_after_human_correction: number | null;
  status: "held at end of scan" | "corrected" | "dropped without correction" | "never held";
};

export type CaseSummary = {
  slug: string;
  title: string;
  statement: string;
  era: "2025" | "2026" | "discovered";
  monitor_date: string | null;
  source: string;
  note: { label: string; text: string } | null;
  first_said: TrailNode | null;
  born: TrailNode | null;
  agents_held: number;
  corrected: number;
  dropped: number;
  still_held: string[];
  human_corrections: number;
  snapshots_scanned: number;
  scan: { from: string; to: string; goal: string; pattern: string; agents: string[] };
};

export type Trail = {
  case: string;
  title: string;
  statement: string;
  scan: CaseSummary["scan"];
  export: { exported_at: string; revision: string; source: string };
  born: TrailNode | null;
  first_said_in_chat: TrailNode | null;
  believers: Believer[];
  human_corrections: TrailNode[];
  agent_corrections: TrailNode[];
  hours_birth_to_first_human_correction: number | null;
  counts: {
    snapshots_scanned: number;
    memory_lines_matched: number;
    chat_messages_matched: number;
    lines_by_stance: Record<string, number>;
    deciding_lines_rechecked?: number;
    labels_changed_by_recheck?: number;
    models?: { bulk: string; recheck: string; tieout: string | null };
  };
  saved_at: string;
  summary: CaseSummary;
};

export type Summary = {
  export: Trail["export"] | null;
  public_2025: { rebuilt: number; total: number; verified_quotes: number };
  discovery: { best_rank_93: number | null; checked: number; beliefs: number | null };
  monitor_2026: Omit<Era, "cases"> & { cases: number };
  featured: CaseSummary | null;
  snapshots_scanned: number;
  facts: Facts;
};

type Era = {
  cases: string[];
  copies: number;
  corrected: number;
  dropped: number;
  still_held: number;
  still_held_by: string[];
  still_held_in: string[];
  corrected_pct: number | null;
  dropped_pct: number | null;
  came_by_chat: number;
  first_hour: number;
  median_hours_held: number | null;
  human_corrections: number;
  agent_corrections: number;
};

type Agreement = { n: number; agree: number; ci95: [number, number]; rate?: number };

export type Facts = {
  export: Trail["export"];
  eras: Record<string, string>;
  monitor_dates: Record<string, string>;
  notes: Record<string, { label: string; text: string }>;
  featured: string;
  order: string[];
  trails: number;
  snapshots_scanned: number;
  public_2025: { rebuilt: number; total: number; verified_quotes: number };
  discovery: { best_rank_93: number | null; checked: number; beliefs: number | null };
  era_2025: Era;
  monitor_2026: Era;
  discovered: Era;
  held_after_human_no: { copies: number; max_hours: number | null; rows: { case: string; agent: string; snapshots: number; hours: number }[] };
  lifecycle: {
    trails: number;
    lines: number;
    relapses_flagged: number;
    relapses_checked: Record<string, number>;
    returns_flagged: number;
    returns_checked: Record<string, number>;
  };
  audit: {
    items: number;
    stance: Agreement;
    stance_holds_or_not: Agreement;
    affirms_precision: Agreement;
    evidence: Agreement;
    evidence_birth: Agreement;
    evidence_correction: Agreement;
    evidence_correction_either_reading: { n: number; agree: number };
    claude_vs_rohit: Agreement | null;
  } | null;
  chance: Record<"2025" | "2026", {
    copies: number;
    within_gap: number;
    expected_by_chance: number;
    p_value: number;
    expected_own_writes: number;
    p_value_own_writes: number;
  }> | null;
  population: Record<string, Population>;
  live: { agent: string; case: string; snapshots_read: number; snapshots_matching_pattern: number; from: string; to: string; checked_at: string }[];
};

export type Population = {
  beliefs: number;
  agents: number;
  spread: { beliefs: number; pct: number; copies: number; mean_other_agents: number; max_other_agents: number };
  chat_timing: {
    copies: number;
    within_gap: number;
    within_pct: number;
    expected_own_writes: number;
    expected_pct: number;
    no_chat_before: number;
    p_value_own_writes: number;
  };
  lifetime: {
    holdings: number;
    gone_for_good_pct: number;
    came_back: number;
    came_back_pct: number;
    median_hours_held: number;
    held_over_a_day_pct: number;
    copies: number;
    copies_gone_for_good_pct: number;
    copies_came_back: number;
    copies_median_hours_held: number;
  };
};

export type HandCheck = {
  case: string;
  agent: string;
  kind: "relapse" | "return";
  from: string;
  to: string;
  verdict: "real" | "not" | "unclear";
  note: string;
};

type Point = { at: string; ref: string; k: number; link: string };

export type Lifecycle = {
  case: string;
  agents: {
    agent: string;
    episodes: { from: Point; to: Point; snapshots: number }[];
    returns: { gone_from: Point; back_at: Point; hours_gone: number; denied_between: boolean }[];
    relapse: { denied: Point; held_again: Point } | null;
  }[];
};

export type ScoreRow = {
  case: string;
  title: string;
  source: string;
  origin: string[];
  birth_agent_ok: boolean | null;
  believers: string[];
  expected_believers_found: string | null;
  correction_found: boolean;
  verified_quotes: number;
  dropped_quotes: number;
};
