"""Chance test for spread by chat: do copies follow another agent's chat message closer than luck would?

For every copy (an agent's first memory line holding the belief), the gap is the time since the latest chat message
from another agent that affirms the belief. The null keeps everything about the belief's chat fixed and moves the
copy: a time drawn uniformly from the belief's active period (birth or first saying, to the last line holding it).
p = how often a random time lands within GAP of an affirming message from someone else. Observed vs expected copies
within GAP, with an exact Poisson-binomial tail. No model is called: chat stances are the trail's stored labels.
"""

import random
from datetime import datetime, timedelta
from types import SimpleNamespace

import duckdb

from heirloom.diff import line_hash, normalize
from heirloom.facts import MONITOR_2026, NOTES, PUBLIC_2025
from heirloom.lifecycle import case_from_run
from heirloom.stance import labels
from heirloom.trail import CASES, CHAT_CHARS, stance_of

GAP = timedelta(minutes=60)
# The clean cases only (the ones in every total).
ERAS = {"2025": [s for s in PUBLIC_2025 if s not in NOTES], "2026": [s for s in MONITOR_2026 if s not in NOTES]}
DRAWS = 4000
SEED = 20261003


def affirming_chat(con: duckdb.DuckDBPyConnection, run: dict) -> list[tuple[datetime, str]]:
    """(time, agent) of every agent chat message in the scan that the trail's labels call affirming."""
    case = case_from_run(run)
    known = CASES.get(run["case"])
    pattern = case.pattern + (f"|{known.correction_pattern}" if known and known.correction_pattern else "")
    models = run["counts"]["models"]
    current, _ = labels(con, SimpleNamespace(cheap=models["bulk"], strong=models["recheck"]), case.statement)
    rows = con.execute("""
        SELECT c.created_at, c.speaker_type, a.name, c.content FROM chat_messages c
        LEFT JOIN agents a ON a.id = c.agent_speaker_id
        WHERE c.created_at BETWEEN ? AND ? AND regexp_matches(c.content, ?, 'i') ORDER BY c.created_at""",
                       [case.start, case.end, pattern]).fetchall()
    return [(at, name) for at, kind, name, content in rows
            if kind == "agent" and stance_of(case, current, normalize(content)[:CHAT_CHARS]) == "affirms"]


def gap_before(t: datetime, chat: list[tuple[datetime, str]], agent: str) -> timedelta | None:
    before = [at for at, who in chat if who != agent and at < t]
    return t - max(before) if before else None


def poisson_binomial_tail(ps: list[float], k: int) -> float:
    """P(X >= k) where X is a sum of independent Bernoulli(p_i)."""
    dist = [1.0]
    for p in ps:
        nxt = [0.0] * (len(dist) + 1)
        for i, q in enumerate(dist):
            nxt[i] += q * (1 - p)
            nxt[i + 1] += q * p
        dist = nxt
    return sum(dist[k:])


def test(con: duckdb.DuckDBPyConnection, runs: dict[str, dict]) -> dict:
    rng = random.Random(SEED)
    rows, cases = [], {}
    for slug, run in runs.items():
        held = [b for b in run["believers"] if b["status"] != "never held"]
        if not held:
            continue
        chat = affirming_chat(con, run)
        starts = [datetime.fromisoformat(n["at"]) for n in (run["born"], run["first_said_in_chat"]) if n]
        lo, hi = min(starts), max(datetime.fromisoformat(b["last_held"]["at"]) for b in held)
        span = (hi - lo).total_seconds()
        draws = [lo + timedelta(seconds=rng.random() * span) for _ in range(DRAWS)]
        for b in held:
            first = datetime.fromisoformat(b["first_held"]["at"])
            real = gap_before(first, chat, b["agent"])
            null = [gap_before(t, chat, b["agent"]) for t in draws]
            p = sum(1 for g in null if g is not None and g <= GAP) / DRAWS
            # Stricter null: only the moments this agent actually wrote memory while the belief was active, so busy
            # hours (when both chat and memory writes happen) count for the null too.
            own = [at for (at,) in con.execute(
                """SELECT m.created_at FROM agent_memories m JOIN agents a ON a.id = m.agent_id
                   WHERE a.name = ? AND m.created_at BETWEEN ? AND ?""", [b["agent"], lo, hi]).fetchall()]
            own_gaps = [gap_before(t, chat, b["agent"]) for t in own]
            p_own = sum(1 for g in own_gaps if g is not None and g <= GAP) / len(own) if own else p
            rows.append({"case": slug, "agent": b["agent"], "first_held": first,
                         "gap_minutes": round(real.total_seconds() / 60, 1) if real else None,
                         "within": real is not None and real <= GAP, "p_null": round(p, 4),
                         "p_null_own_writes": round(p_own, 4), "own_writes": len(own)})
        cases[slug] = {"affirming_chat": len(chat), "active_from": lo, "active_to": hi}

    def summary(sub: list[dict]) -> dict:
        observed = sum(r["within"] for r in sub)
        return {"copies": len(sub), "within_gap": observed,
                "expected_by_chance": round(sum(r["p_null"] for r in sub), 1),
                "p_value": poisson_binomial_tail([r["p_null"] for r in sub], observed),
                "expected_own_writes": round(sum(r["p_null_own_writes"] for r in sub), 1),
                "p_value_own_writes": poisson_binomial_tail([r["p_null_own_writes"] for r in sub], observed)}

    by_era = {era: summary([r for r in rows if r["case"] in slugs]) for era, slugs in ERAS.items()}
    return {"kind": "chance", "gap_minutes": GAP.total_seconds() / 60, "draws": DRAWS, "seed": SEED,
            "null": "copy time uniform over the belief's active period; the chat stays where it was",
            "null_own_writes": "copy time = any moment the same agent wrote memory in the active period",
            "eras": by_era, "cases": cases, "copies": rows}
