"""Every headline number, computed from the saved runs only (no database, no model). One source for the write-up,
the README, the website and `heirloom verify`.

Data: AI Digest / AI Village dataset (aidigestorg/ai-village), research use only.
"""

import json
import re
import statistics
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from heirloom.lifecycle import ANALYSIS, latest_runs
from heirloom.trail import RUNS

# Public 2025 accounts are scored against the AI Digest write-ups; 2026 cases are seeded from the hosts' Village
# Monitor findings (date = the monitor's flag).
PUBLIC_2025 = ["93-list", "o3-budget", "charity-money", "opus-tasks", "gemini-ui-bugs", "heifer-partnership"]
MONITOR_2026 = {
    "forwarddiff-846": "2026-09-16",
    "fake-commit-hash": "2026-07-27",
    "muninn-verification": "2026-08-18",
    "adoption-77": "2026-06-29",
    "conjectures-357-359": "2026-07-29",
}
# Kept on the site, left out of every total, with the reason shown.
NOTES = {
    "o3-budget": ("not found as described", "In the data $7,500 is a venue's price quote that every agent calls far "
                  "over budget. No agent held a $7,500 budget. The money belief they did hold is the $1,984 one."),
    "conjectures-357-359": ("partly came true", "Claude Opus 5 really disproved conjectures 358 and 359 on 20 Aug "
                            "2026, three weeks after the fabrication; 357 is true. Not counted as a surviving false "
                            "belief."),
}
FEATURED = "93-list"
# Found blind and traced by name, but not shown false: kept out of every false-belief total.
DISCOVERED = ["store-360"]
# Beliefs whose lines come and go with every task ("it's a bug"): their returns are not counted.
FUZZY = {"gemini-ui-bugs"}
# The discovery run's 93-list entries (the belief splits by unit: contacts, emails, addresses).
LIST_93 = re.compile(r"\b(87|93)\b.{0,25}(contact|address|email|person|people|recipient)|resonance.?mailing|"
                     r"resonance-93", re.I)
FACTS = ANALYSIS / "facts.json"


def _load(path: Path | None) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path else {}


def _latest(pattern: str) -> Path | None:
    files = sorted(RUNS.glob(pattern))
    return files[-1] if files else None


def _hours(a: str, b: str) -> float:
    return (datetime.fromisoformat(b) - datetime.fromisoformat(a)).total_seconds() / 3600


def _start(trail: dict) -> str:
    """When the belief began: its first chat message or first memory line, else its earliest copy."""
    starts = [n["at"] for n in (trail.get("first_said_in_chat"), trail.get("born")) if n]
    return min(starts or [b["first_held"]["at"] for b in trail["believers"] if b.get("first_held")])


def _median(values: list[float]) -> float | None:
    return round(statistics.median(values), 1) if values else None


def copies(trails: dict[str, dict], slugs) -> list[dict]:
    """Every agent that wrote the belief into memory, one row per (case, agent)."""
    return [b | {"case": s} for s in slugs if s in trails for b in trails[s]["believers"]
            if b["status"] != "never held"]


def era(trails: dict[str, dict], slugs) -> dict:
    """Corrected / dropped / still held, how long a copy lived, and how it arrived."""
    rows = copies(trails, slugs)
    status = Counter(b["status"] for b in rows)
    labels = Counter((b["first_held"].get("tieout") or {}).get("label") or "not checked" for b in rows)
    n = len(rows)
    return {
        "cases": [s for s in slugs if s in trails],
        "copies": n,
        "corrected": status.get("corrected", 0),
        "dropped": status.get("dropped without correction", 0),
        "still_held": status.get("held at end of scan", 0),
        "still_held_by": [b["agent"] for b in rows if b["status"] == "held at end of scan"],
        "still_held_in": [b["case"] for b in rows if b["status"] == "held at end of scan"],
        "corrected_pct": round(100 * status.get("corrected", 0) / n) if n else None,
        "dropped_pct": round(100 * status.get("dropped without correction", 0) / n) if n else None,
        "said_it_first": sum(1 for b in rows if b["said_it_first"]),
        # Copies written within an hour of the belief's start (its first chat message or first memory line).
        "first_hour": sum(1 for b in rows if _hours(_start(trails[b["case"]]), b["first_held"]["at"]) <= 1),
        "came_by_chat": sum(1 for b in rows if b["carrier"]),
        "median_hours_held": _median([_hours(b["first_held"]["at"], b["last_held"]["at"]) for b in rows]),
        "max_hours_held": round(max(_hours(b["first_held"]["at"], b["last_held"]["at"]) for b in rows), 1)
        if rows else None,
        "median_rewrites_survived": _median([b["rewrites_survived"] for b in rows]),
        "birth_labels": dict(sorted(labels.items())),
        "human_corrections": sum(len(trails[s]["human_corrections"]) for s in slugs if s in trails),
        "agent_corrections": sum(len(trails[s]["agent_corrections"]) for s in slugs if s in trails),
    }


def compute() -> dict:
    runs = latest_runs()
    trails = {slug: _load(p) for slug, p in runs.items()}
    trails = {s: t for s, t in trails.items() if t.get("believers") is not None}
    score = _load(_latest("*-score.json"))
    by_case = {c["case"]: c for c in score.get("cases", [])}
    public = [by_case[s] for s in PUBLIC_2025 if s in by_case]
    disc = _load(_latest("*-discover-*.json"))
    ranks = [i for i, b in enumerate(disc.get("ranked", []), 1) if LIST_93.search(b.get("line", ""))]

    clean_2025 = [s for s in PUBLIC_2025 if s not in NOTES]
    clean_2026 = [s for s in MONITOR_2026 if s not in NOTES]

    after_human = [{"case": b["case"], "agent": b["agent"], "snapshots": b["held_after_human_correction"],
                    "hours": b["hours_held_after_human_correction"]}
                   for b in copies(trails, [*clean_2025, *clean_2026]) if b["held_after_human_correction"]]

    life = {p.stem.removeprefix("lifecycle-"): _load(p) for p in sorted(ANALYSIS.glob("lifecycle-*.json"))}
    counted = [s for s in [*clean_2025, *clean_2026] if s in life]
    checks = _load(ANALYSIS / "hand-checks.json").get("checks", [])

    def flagged(kind: str) -> int:
        if kind == "relapse":
            return sum(1 for s in counted for a in life[s]["agents"] if a["relapse"])
        return sum(len(a["returns"]) for s in counted if s not in FUZZY for a in life[s]["agents"])

    def verdicts(kind: str) -> dict:
        rows = [c for c in checks if c["kind"] == kind and c["case"] in counted]
        return dict(sorted(Counter(c["verdict"] for c in rows).items()))

    return {
        "kind": "facts",
        "computed_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "export": score.get("export"),
        "eras": {s: ("2025" if s in PUBLIC_2025 else "2026" if s in MONITOR_2026 else "discovered") for s in trails},
        "monitor_dates": MONITOR_2026,
        "notes": {k: {"label": v[0], "text": v[1]} for k, v in NOTES.items()},
        "featured": FEATURED,
        "order": [FEATURED, *[s for s in PUBLIC_2025 if s != FEATURED], *MONITOR_2026, *DISCOVERED],
        "trails": len(trails),
        "snapshots_scanned": sum(t["counts"]["snapshots_scanned"] for t in trails.values()),
        "public_2025": {"rebuilt": sum(1 for c in public if c.get("birth_agent_ok")), "total": len(public),
                        "verified_quotes": sum(c.get("verified_quotes", 0) for c in public)},
        "discovery": {"best_rank_93": ranks[0] if ranks else None, "checked": len(disc.get("ranked", [])),
                      "beliefs": disc.get("counts", {}).get("beliefs")},
        "era_2025": era(trails, clean_2025),
        "discovered": era(trails, DISCOVERED),
        "monitor_2026": era(trails, clean_2026),
        "held_after_human_no": {
            "copies": len(after_human),
            "max_hours": max((r["hours"] for r in after_human), default=None),
            "rows": after_human,
        },
        "lifecycle": {
            "trails": len(counted),
            "all_match_trails": all(life[s].get("matches_trail") for s in counted),
            "lines_labelled": sum(life[s]["coverage"]["labelled"] for s in counted),
            "lines": sum(life[s]["coverage"]["lines"] for s in counted),
            "relapses_flagged": flagged("relapse"),
            "relapses_checked": verdicts("relapse"),
            "returns_flagged": flagged("return"),
            "returns_checked": verdicts("return"),
            "fuzzy_cases_not_counted": sorted(FUZZY),
        },
        "audit": audit_summary(_load(ANALYSIS / "audit.json")),
        "chance": _load(ANALYSIS / "chance.json").get("eras"),
        # Every candidate belief, true or false, no model (`heirloom population`).
        "population": {_load(p)["era"]: _load(p)["summary"] | {"agents": _load(p)["agents"]}
                       for p in sorted(ANALYSIS.glob("population-*.json"))},
        "model_agreement": _load(ANALYSIS / "model-agreement.json").get("pairs"),
        "live": [a | {"case": d["case"], "checked_at": d["checked_at"]}
                 for p in sorted(ANALYSIS.glob("live-*.json")) for d in [_load(p)] for a in d["agents"]],
    }


def audit_summary(audit: dict) -> dict | None:
    """The label check (runs/analysis/audit.json): model labels vs a blind reader, with Wilson 95% intervals."""
    claude = audit.get("judges", {}).get("claude")
    if not claude:
        return None
    rows = [x for x in audit["items"] if x["kind"] == "tieout" and x["role"] == "first_denial"]
    either = sum(1 for x in rows if x["model_label"] in (x.get("claude_label"), x.get("claude_firstpass_label")))
    return {
        "judge": "claude (blind)",
        "items": claude["all"]["n"],
        "stance": {k: claude["stance"][k] for k in ("n", "agree", "ci95")},
        "stance_holds_or_not": claude["stance_holds_or_not"],
        "affirms_precision": claude["stance"]["by_model_label"].get("affirms"),
        "evidence": {k: claude["tieout"][k] for k in ("n", "agree", "ci95")},
        "evidence_birth": claude["tieout_by_role"]["first_held"],
        "evidence_correction": claude["tieout_by_role"]["first_denial"],
        "evidence_correction_either_reading": {"n": len(rows), "agree": either},
        "claude_vs_rohit": audit.get("claude_vs_rohit"),
    }


def save(data: dict) -> Path:
    ANALYSIS.mkdir(parents=True, exist_ok=True)
    FACTS.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    return FACTS
