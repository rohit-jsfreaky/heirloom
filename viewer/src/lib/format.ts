// Timestamps in the dataset are naive UTC ("2025-06-10 19:48:20.556671").

export function toDate(at: string): Date {
  return new Date(at.replace(" ", "T").replace(/(\.\d{3})\d+/, "$1") + (/[zZ]|[+-]\d\d:?\d\d$/.test(at) ? "" : "Z"));
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const pad = (n: number) => String(n).padStart(2, "0");

export function utc(at: string, withSeconds = false): string {
  const d = toDate(at);
  const time = `${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}${withSeconds ? `:${pad(d.getUTCSeconds())}` : ""}`;
  return `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]} ${d.getUTCFullYear()}, ${time} UTC`;
}

export function day(at: string): string {
  const d = toDate(at);
  return `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]} ${d.getUTCFullYear()}`;
}

export function tick(ms: number, stepMs: number): string {
  const d = new Date(ms);
  const date = `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]}`;
  return stepMs < 86_400_000 ? `${date} ${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}` : date;
}

export function span(fromAt: string, toAt: string): string {
  const h = (toDate(toAt).getTime() - toDate(fromAt).getTime()) / 3_600_000;
  if (h < 1) return `${Math.max(1, Math.round(h * 60))} min`;
  if (h < 48) return `${h.toFixed(h < 10 ? 1 : 0)} h`;
  return `${(h / 24).toFixed(1)} days`;
}

/** Memory lines carry the heading they sit under: "[TECHNICAL NOTES] line". */
export function splitSection(text: string): { section: string | null; body: string } {
  if (text.startsWith("[") && text.includes("] ")) {
    const i = text.indexOf("] ");
    return { section: text.slice(1, i), body: text.slice(i + 2) };
  }
  return { section: null, body: text };
}

export const LABEL_TEXT: Record<string, string> = {
  supported: "supported",
  contradicted: "contradicted",
  hearsay: "hearsay",
  no_evidence: "no evidence",
  instruction: "instruction",
};

export const LABEL_HELP: Record<string, string> = {
  supported: "A tool output, file or human message in the agent's own window shows it.",
  contradicted: "Something in the agent's own window shows it is false.",
  hearsay: "The only source is another agent's chat message.",
  no_evidence: "Nothing in the agent's window speaks to it either way.",
  instruction: "A note the agent left for its future self.",
};

export const STATUS_TEXT: Record<string, string> = {
  "held at end of scan": "still held",
  corrected: "corrected",
  "dropped without correction": "forgot, never corrected",
  "never held": "never held",
};
