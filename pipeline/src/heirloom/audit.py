"""Label accuracy check: a fixed random sample of the labels the trails rest on, judged blind against the raw text,
then compared with the model's labels.

- Stance: STANCE_PER_LABEL lines per label (affirms / doubts / denies / unrelated), across every saved trail. The
  judge sees what the model saw: the belief and the line with its section heading.
- Evidence checks (tie-outs at a trail's key moments), stratified by label. The judge sees the line, the part to
  judge, and every item of the writer's evidence window that mentions the line's anchors, plus every human message
  in it. Not the model's quotes or reason.

The sample and the raw text stay in data/audit/ (git-ignored: raw dataset text). Judgments are JSON files there,
{"A001": {"label": "...", "note": "..."}}. The published result, runs/analysis/audit.json, holds masked text only.
"""

import json
import math
import random
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import duckdb

from heirloom.config import DATA
from heirloom.diff import anchors, line_hash, lines_in_context, search_terms, strong
from heirloom.lifecycle import ANALYSIS, case_from_run, latest_runs
from heirloom.privacy import Masker
from heirloom.stance import labels
from heirloom.tieout import MIN_LOOKBACK
from heirloom.verify import found_in
from heirloom.village import village_link
from heirloom.windows import evidence

SEED = 20261003
STANCE_PER_LABEL = 15
TIEOUT_QUOTA = {"contradicted": 12, "hearsay": 14, "no_evidence": 8, "supported": 4, "instruction": 2}
STANCES = ("affirms", "doubts", "denies", "unrelated")
TIEOUTS = ("supported", "contradicted", "hearsay", "no_evidence", "instruction")
FOR_ROHIT = 20
DIR = DATA / "audit"
SAMPLE = DIR / "sample.json"
EXCERPT = 420


def _runs() -> dict[str, dict]:
    return {slug: json.loads(p.read_text(encoding="utf-8")) for slug, p in latest_runs().items()}


def _raw_memory_line(con, snapshot_id: str, masked: str) -> str:
    content, = con.execute("SELECT content FROM agent_memories WHERE id = ?", [snapshot_id]).fetchone()
    return next((line for line in lines_in_context(content) if found_in(masked, line)), masked)


def sample(con: duckdb.DuckDBPyConnection) -> list[dict]:
    rng = random.Random(SEED)
    runs = _runs()
    by_label: dict[str, list[dict]] = defaultdict(list)
    for slug, run in sorted(runs.items()):
        case = case_from_run(run)
        models = run["counts"]["models"]
        current, strong = labels(con, SimpleNamespace(cheap=models["bulk"], strong=models["recheck"]), case.statement)
        rows = con.execute("SELECT DISTINCT line_hash, line FROM line_stance WHERE line_hash IN "
                           "(SELECT unnest(?::VARCHAR[]))", [list(current)]).fetchall()
        for h, line in sorted(rows):
            by_label[current[h]].append({"kind": "stance", "case": slug, "statement": case.statement, "text": line,
                                         "model_label": current[h],
                                         "model": models["recheck"] if h in strong else models["bulk"]})
    items = [x for label in STANCES for x in rng.sample(by_label[label], STANCE_PER_LABEL)]

    ties: dict[str, list[dict]] = defaultdict(list)
    for slug, run in sorted(runs.items()):
        case = case_from_run(run)
        for b in run["believers"]:
            for role in ("first_held", "first_denial"):
                node = b.get(role)
                if node and node.get("tieout"):
                    t = node["tieout"]
                    ties[t["label"]].append({"kind": "tieout", "case": slug, "statement": case.statement,
                                             "agent": b["agent"], "role": role, "ref": node["ref"], "at": node["at"],
                                             "masked_text": node["text"], "window": t["window"],
                                             "model_label": t["label"], "model": run["counts"]["models"]["tieout"]})
    for label, n in TIEOUT_QUOTA.items():
        items += rng.sample(ties[label], min(n, len(ties[label])))

    for x in items:
        if x["kind"] == "tieout":
            x["text"] = _raw_memory_line(con, x["ref"], x.pop("masked_text"))
    rng.shuffle(items)
    for i, x in enumerate(items, 1):
        x["id"] = f"A{i:03d}"
    rohit = set(rng.sample([x["id"] for x in items], FOR_ROHIT))
    for x in items:
        x["for_rohit"] = x["id"] in rohit
    DIR.mkdir(parents=True, exist_ok=True)
    SAMPLE.write_text(json.dumps(items, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    return items


def _excerpt(text: str, keys: list[str]) -> str:
    low = text.lower()
    hits = [low.find(k) for k in keys if k and low.find(k) >= 0]
    if not hits:
        return text[:EXCERPT]
    start = max(0, min(hits) - EXCERPT // 3)
    return ("…" if start else "") + text[start:start + EXCERPT] + ("…" if start + EXCERPT < len(text) else "")


def window_view(con: duckdb.DuckDBPyConnection, item: dict, limit: int = 14) -> list[str]:
    """What the judge reads for an evidence check: anchor-mentioning items and human messages in the window."""
    ids = dict(con.execute("SELECT name, id FROM agents").fetchall())
    start = datetime.fromisoformat(item["window"]["from"])
    end = datetime.fromisoformat(item["window"]["to"])
    start = min(start, end - MIN_LOOKBACK)
    keys = sorted({t.lower() for a in anchors(item["text"]) for t in search_terms(a) if len(t) >= 2}, key=len,
                  reverse=True)
    belief = re.compile(json.loads(latest_runs()[item["case"]].read_text(encoding="utf-8"))["scan"]["pattern"], re.I)
    strong_keys = [t.lower() for a in anchors(item["text"]) if strong(a) for t in search_terms(a)[:1]]
    picked = []
    for e in evidence(con, ids[item["agent"]], start, end):
        own = e.source == "chat" and e.speaker == item["agent"]
        low = e.text.lower()
        on_topic = bool(belief.search(e.text)) or any(k in low for k in strong_keys)
        mentions = on_topic or any(k in low for k in keys)
        if mentions or e.source == "human":
            # On-topic tool output, searches and humans first (what can support or contradict), then other agents'
            # on-topic chat, then the rest (bare-number matches, off-topic humans, the agent's own chat).
            rank = 0 if on_topic and e.source in ("turn", "search", "human") else 1 if on_topic and not own else 2
            who = f"{e.speaker} (this agent: not evidence)" if own else e.speaker
            picked.append((rank, e.created_at, f"[{e.created_at:%m-%d %H:%M:%S}] {e.source} · {who}: "
                                               f"{_excerpt(e.text, keys)}"))
    keep = sorted(sorted(picked)[:limit], key=lambda x: x[1])
    return [text for _, _, text in keep]


def blind(con: duckdb.DuckDBPyConnection, items: list[dict]) -> str:
    """The judging view: no model label, no model quotes, no model reason."""
    parts = []
    for x in items:
        head = f"### {x['id']} · {x['kind']} · {x['case']}"
        if x["kind"] == "stance":
            parts.append(f"{head}\nBelief: {x['statement']}\nLine: {x['text']}\nAnswer: affirms / doubts / denies / "
                         f"unrelated")
        else:
            view = window_view(con, x)
            parts.append(f"{head} · {x['agent']} wrote it {x['at']} UTC ({x['role']})\nBelief (part to judge): "
                         f"{x['statement']}\nLine: {x['text']}\nWindow {x['window']['from']} → {x['window']['to']}, "
                         f"items mentioning the line's anchors or the belief, or from humans ({len(view)} shown):\n"
                         + ("\n".join(f"  - {v}" for v in view) or "  (none)")
                         + "\nAnswer: supported / contradicted / hearsay / no_evidence / instruction")
    return "\n\n".join(parts)


SHEET_HEAD = """# Label check — Rohit's 20 (blind)

Internal, git-ignored: raw village text, real names inside. ~30–40 minutes.
For each item, pick ONE answer. You are not shown what the model said. Reply in chat like `A007 contradicted`.

## Stance items — where does the LINE stand on the BELIEF?
- **affirms** — states the belief, or takes it for granted as current fact (uses it, plans with it, reports its
  size or contents as real).
- **doubts** — treats the thing as real but in trouble: missing, empty, deleted, unconfirmed, "can't find it",
  or describes searching for it / trying to recover it.
- **denies** — says the belief is false: never existed, hallucinated, fiction, corrected, "falsely claimed".
  Hedged versions ("may never have existed") count. Under a "mistakes to avoid" heading = denies.
- **unrelated** — about something else. A NEW replacement (a rebuild sheet made from scratch) is unrelated unless
  the line also says something about the original. Just naming a file or label is unrelated.

## Evidence items — what does the agent's own window show about the BELIEF (the "part to judge")?
Judge the belief, not the line. The window lists the items that mention the belief or the line's anchors, and
every human message. "(this agent: not evidence)" marks the agent's own chat: never counts.
- **supported** — a tool output, file, error message or a human shows the belief is TRUE.
- **contradicted** — something shows the belief is FALSE: a tool output, an error, a human, or another agent's
  correction.
- **hearsay** — the only support for the belief is another agent's chat message.
- **no_evidence** — nothing in the window speaks to the belief.
- **instruction** — the line is a note or plan for the future (a task, a schedule), not a statement of fact.

---

"""


def kappa(pairs: list[tuple[str, str]]) -> float | None:
    """Cohen's kappa for two raters over the same items."""
    n = len(pairs)
    if not n:
        return None
    observed = sum(a == b for a, b in pairs) / n
    left, right = Counter(a for a, _ in pairs), Counter(b for _, b in pairs)
    expected = sum(left[k] * right[k] for k in left) / (n * n)
    return round((observed - expected) / (1 - expected), 3) if expected < 1 else 1.0


def model_agreement(con: duckdb.DuckDBPyConnection) -> dict:
    """Every pair of models that labelled the same lines for the same belief and prompt (line_stance)."""
    rows = con.execute("""
        WITH l AS (SELECT belief_key, line_hash, model, any_value(stance) AS s FROM line_stance GROUP BY 1, 2, 3)
        SELECT a.belief_key, a.model, b.model, a.s, b.s FROM l a JOIN l b USING (belief_key, line_hash)
        WHERE a.model < b.model""").fetchall()
    groups: dict[tuple[str, str], list[tuple[str, str]]] = defaultdict(list)
    keys: dict[tuple[str, str], set[str]] = defaultdict(set)
    for key, ma, mb, sa, sb in rows:
        groups[(ma, mb)].append((sa, sb))
        keys[(ma, mb)].add(key)
    pairs = []
    for (ma, mb), labs in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        holds = [(a == "affirms", b == "affirms") for a, b in labs]
        pairs.append({
            "a": ma, "b": mb, "lines": len(labs), "beliefs": len(keys[(ma, mb)]),
            # The strong model only re-checks the lines that decide a trail's key moments: not a random sample.
            "sample": "every matched line of one belief" if len(keys[(ma, mb)]) == 1 else "deciding lines only",
            "agree": round(sum(a == b for a, b in labs) / len(labs), 3), "kappa": kappa(labs),
            "holds_agree": round(sum(a == b for a, b in holds) / len(holds), 3),
            "holds_kappa": kappa([(str(a), str(b)) for a, b in holds]),
        })
    return {"kind": "model-agreement", "pairs": pairs}


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (round(max(0.0, centre - half), 3), round(min(1.0, centre + half), 3))


def agreement(items: list[dict], judged: dict[str, dict]) -> dict:
    """Model label vs judge label, overall and per kind and per model label, with Wilson 95% intervals."""
    def block(rows: list[dict]) -> dict:
        k = sum(1 for x in rows if judged[x["id"]]["label"] == x["model_label"])
        lo, hi = wilson(k, len(rows))
        return {"n": len(rows), "agree": k, "rate": round(k / len(rows), 3) if rows else None, "ci95": [lo, hi]}

    rows = [x for x in items if x["id"] in judged]
    out = {"all": block(rows)}
    for kind, names in (("stance", STANCES), ("tieout", TIEOUTS)):
        sub = [x for x in rows if x["kind"] == kind]
        out[kind] = block(sub) | {
            "by_model_label": {n: block([x for x in sub if x["model_label"] == n]) for n in names
                               if any(x["model_label"] == n for x in sub)},
            "confusion": {n: dict(Counter(judged[x["id"]]["label"] for x in sub if x["model_label"] == n))
                          for n in names if any(x["model_label"] == n for x in sub)},
        }
    ties = [x for x in rows if x["kind"] == "tieout"]
    out["tieout_by_role"] = {role: block([x for x in ties if x.get("role") == role])
                             for role in ("first_held", "first_denial")}
    # The call a trail rests on: does the line hold the belief (affirms) or not?
    st = [x for x in rows if x["kind"] == "stance"]
    k = sum(1 for x in st if (judged[x["id"]]["label"] == "affirms") == (x["model_label"] == "affirms"))
    out["stance_holds_or_not"] = {"n": len(st), "agree": k, "ci95": list(wilson(k, len(st)))}
    return out


def publish(con: duckdb.DuckDBPyConnection, items: list[dict], judges: dict[str, dict[str, dict]]) -> Path:
    mask = Masker(con)
    rows = []
    for x in items:
        rows.append({
            "id": x["id"], "kind": x["kind"], "case": x["case"], "agent": x.get("agent"), "role": x.get("role"),
            "at": x.get("at"),
            "link": village_link(datetime.fromisoformat(x["at"])) if x.get("at") else None,
            # No text: some lines name real people the handle list can't know. The text is rebuilt locally from
            # data/audit/sample.json (raw dataset rows).
            "line_hash": line_hash(x["text"]) if x["kind"] == "stance" else None, "snapshot": x.get("ref"),
            "model": x["model"], "model_label": x["model_label"],
            **{f"{name.replace('-', '_')}_label": j.get(x["id"], {}).get("label") for name, j in judges.items()},
            **{f"{name.replace('-', '_')}_note": mask(j.get(x["id"], {}).get("note")) for name, j in judges.items()},
        })
    data = {
        "kind": "audit",
        "seed": SEED,
        "design": {"stance_per_label": STANCE_PER_LABEL, "tieout_quota": TIEOUT_QUOTA, "for_rohit": FOR_ROHIT},
        "judges": {name: agreement(items, j) for name, j in judges.items()},
        "items": rows,
    }
    if {"claude", "rohit"} <= judges.keys():
        both = [x for x in items if x["id"] in judges["rohit"] and x["id"] in judges["claude"]]
        k = sum(1 for x in both if judges["rohit"][x["id"]]["label"] == judges["claude"][x["id"]]["label"])
        data["claude_vs_rohit"] = {"n": len(both), "agree": k, "ci95": list(wilson(k, len(both)))}
    path = ANALYSIS / "audit.json"
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    return path


def load(name: str) -> dict[str, dict]:
    path = DIR / f"judged-{name}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}

