import { LABEL_HELP, LABEL_TEXT, STATUS_TEXT } from "@/lib/format";

const TONES = {
  amber: "bg-amber-soft text-amber ring-amber-mark/30",
  blue: "bg-accent-soft text-accent-ink ring-accent/20",
  grey: "bg-surface-2 text-muted ring-line-strong",
  outline: "bg-surface text-ink-2 ring-line-strong",
} as const;

export function Chip({ tone, children, title }: { tone: keyof typeof TONES; children: React.ReactNode; title?: string }) {
  return (
    <span
      title={title}
      className={`inline-flex items-center gap-1 whitespace-nowrap rounded-full px-2 py-0.5 text-[11px] font-medium leading-5 ring-1 ring-inset ${TONES[tone]}`}
    >
      {children}
    </span>
  );
}

const LABEL_TONE: Record<string, keyof typeof TONES> = {
  contradicted: "amber",
  hearsay: "amber",
  no_evidence: "grey",
  supported: "blue",
  instruction: "outline",
};

export function LabelChip({ label }: { label: string }) {
  return (
    <Chip tone={LABEL_TONE[label] ?? "outline"} title={LABEL_HELP[label]}>
      {LABEL_TEXT[label] ?? label}
    </Chip>
  );
}

const STATUS_TONE: Record<string, keyof typeof TONES> = {
  "held at end of scan": "amber",
  corrected: "blue",
  "dropped without correction": "grey",
  "never held": "outline",
};

export function StatusChip({ status, short }: { status: string; short?: boolean }) {
  const text = STATUS_TEXT[status] ?? status;
  return <Chip tone={STATUS_TONE[status] ?? "outline"} title={text}>{short ? text.split(",")[0] : text}</Chip>;
}
