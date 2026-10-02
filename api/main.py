"""Heirloom trail API — read-only, over the masked run files in runs/ (never the raw dataset).

Data: AI Digest / AI Village dataset (aidigestorg/ai-village), research use only. Human names, emails, phone
numbers and credentials are masked in every run file before it is written.
"""

import json
import os
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

RUNS = Path(os.environ.get("HEIRLOOM_RUNS", Path(__file__).resolve().parent.parent / "runs"))

# Eras, monitor dates, notes and every headline number come from one file the pipeline writes
# (`heirloom facts`), so the site, the write-up and `heirloom verify` can never disagree.
FACTS = RUNS / "analysis" / "facts.json"

app = FastAPI(title="Heirloom", description=__doc__, version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"])


def _latest(kind: str) -> Path | None:
    files = sorted(RUNS.glob(f"*-{kind}.json")) or sorted(RUNS.glob(f"*-{kind}-*.json"))
    return files[-1] if files else None


@lru_cache(maxsize=64)
def _read(path: str, mtime: float) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _load(path: Path | None) -> dict | None:
    return _read(str(path), path.stat().st_mtime) if path else None


def _trail_slugs() -> list[str]:
    slugs = set()
    for p in RUNS.glob("*.json"):
        m = re.match(r"^\d{8}T\d{6}Z-(.+)\.json$", p.name)
        if m and not m.group(1).startswith(("score", "discover-", "alive-")):
            slugs.add(m.group(1))
    return sorted(slugs)


def _facts() -> dict:
    data = _load(FACTS) if FACTS.exists() else None
    if data is None:
        raise HTTPException(503, "no facts file: run `heirloom facts` in pipeline/")
    return data


def _summary_of(slug: str, trail: dict, sources: dict) -> dict:
    held = [b for b in trail["believers"] if b["status"] != "never held"]
    statuses = Counter(b["status"] for b in held)
    facts = _facts()
    era = facts["eras"].get(slug, "discovered")
    note = facts["notes"].get(slug)
    return {
        "slug": slug,
        "title": trail["title"],
        "statement": trail["statement"],
        "era": era,
        "monitor_date": facts["monitor_dates"].get(slug),
        "source": sources.get(slug, ""),
        "note": note,
        "first_said": trail["first_said_in_chat"],
        "born": trail["born"],
        "agents_held": len(held),
        "corrected": statuses.get("corrected", 0),
        "dropped": statuses.get("dropped without correction", 0),
        "still_held": [b["agent"] for b in held if b["status"] == "held at end of scan"],
        "human_corrections": len(trail["human_corrections"]),
        "snapshots_scanned": trail["counts"]["snapshots_scanned"],
        "scan": trail["scan"],
    }


def _sources() -> dict:
    score = _load(_latest("score"))
    return {c["case"]: c.get("source", "") for c in (score or {}).get("cases", [])}


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "runs": len(list(RUNS.glob("*.json")))}


@app.get("/api/cases")
def cases() -> list[dict]:
    sources = _sources()
    out = []
    for slug in _trail_slugs():
        trail = _load(_latest(slug))
        if trail and trail.get("believers") is not None:
            out.append(_summary_of(slug, trail, sources))
    order = {s: i for i, s in enumerate(_facts()["order"])}
    return sorted(out, key=lambda c: (order.get(c["slug"], 99), c["slug"]))


@app.get("/api/trails/{slug}")
def trail(slug: str) -> dict:
    if not re.fullmatch(r"[a-z0-9-]+", slug):
        raise HTTPException(404, "no such trail")
    data = _load(_latest(slug))
    if not data or data.get("believers") is None:
        raise HTTPException(404, "no such trail")
    return data | {"summary": _summary_of(slug, data, _sources())}


@app.get("/api/score")
def score() -> dict:
    data = _load(_latest("score"))
    if not data:
        raise HTTPException(404, "no score run yet")
    return data | {"notes": _facts()["notes"]}


@app.get("/api/alive")
def alive() -> dict:
    data = _load(_latest("alive"))
    if not data:
        raise HTTPException(404, "no alive run yet")
    return data


@app.get("/api/discover")
def discover() -> dict:
    data = _load(_latest("discover"))
    if not data:
        raise HTTPException(404, "no discover run yet")
    return data


@app.get("/api/summary")
def summary() -> dict:
    """The headline numbers, as `heirloom facts` computed them from the saved runs."""
    facts = _facts()
    m = facts["monitor_2026"]
    return {
        "export": facts["export"],
        "public_2025": facts["public_2025"],
        "discovery": facts["discovery"],
        "monitor_2026": m | {"cases": len(m["cases"])},
        "featured": next((c for c in cases() if c["slug"] == facts["featured"]), None),
        "snapshots_scanned": facts["snapshots_scanned"],
        "facts": facts,
    }
