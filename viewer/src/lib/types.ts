// Shapes of the Heirloom API (api/main.py), which serves the masked run files in runs/.

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
  public_2025: { rebuilt: number; total: number };
  discovery: { best_rank_93: number | null; checked: number; beliefs: number | null };
  monitor_2026: {
    cases: number;
    copies: number;
    corrected: number;
    dropped: number;
    still_held: number;
    still_held_by: string[];
  };
  featured: CaseSummary | null;
  snapshots_scanned: number;
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
