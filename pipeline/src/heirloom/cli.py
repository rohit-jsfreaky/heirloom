"""The `heirloom` command."""

from datetime import datetime, time, timedelta
from typing import Annotated

import typer

app = typer.Typer(no_args_is_help=True, add_completion=False)

DATE_FORMATS = ["%Y-%m-%d", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"]


@app.callback()
def _root() -> None:
    """Heirloom: the life of a false belief inside a group of AI agents.

    Data: AI Digest / AI Village dataset (aidigestorg/ai-village), research use only.
    """


@app.command()
def download(
    latest: Annotated[bool, typer.Option(help="Fetch the newest export instead of the pinned one.")] = False,
) -> None:
    """Download the AI Village tables into data/raw (needs HF_TOKEN in .env)."""
    from heirloom import download as dl
    from heirloom.config import PINNED_REVISION

    revision = dl.latest_revision() if latest else PINNED_REVISION
    typer.echo(f"revision {revision}")
    dl.download(revision)


@app.command()
def load(
    only: Annotated[list[str] | None, typer.Option("--only", help="Reload just this table (repeatable).")] = None,
) -> None:
    """Load data/raw into data/heirloom.duckdb and check row counts against manifest.json."""
    from heirloom import load as loader
    from heirloom.db import connect

    with connect() as con:
        ok = loader.run(con, only)
    raise typer.Exit(0 if ok else 1)


@app.command("windows")
def windows_cmd(
    agent: Annotated[str, typer.Option(help='Agent name, part of it, or id prefix ("o3", "opus 4").')],
    start: Annotated[datetime, typer.Option("--from", formats=DATE_FORMATS, help="UTC.")],
    end: Annotated[datetime, typer.Option("--to", formats=DATE_FORMATS, help="UTC; a bare date means the whole day.")],
    grep: Annotated[str | None, typer.Option(help="Only show diff lines matching this regex.")] = None,
    show_evidence: Annotated[bool, typer.Option("--evidence", help="Also list each window's evidence.")] = False,
    show_all: Annotated[bool, typer.Option("--all", help="Also show windows where only wording changed.")] = False,
) -> None:
    """Print each memory rewrite of one agent with its line diff and its evidence window."""
    from heirloom.db import connect
    from heirloom.render import print_windows
    from heirloom.village import find_agent
    from heirloom.windows import windows

    if end.time() == time(0):
        end = end + timedelta(days=1) - timedelta(microseconds=1)
    with connect(read_only=True) as con:
        agent_id, name = find_agent(con, agent)
        print_windows(name, windows(con, agent_id, start, end), grep, show_evidence, show_all)


@app.command("discover")
def discover_cmd(
    start: Annotated[datetime, typer.Option("--from", formats=DATE_FORMATS, help="UTC.")],
    end: Annotated[datetime, typer.Option("--to", formats=DATE_FORMATS, help="UTC; a bare date means the whole day.")],
    history_days: Annotated[int, typer.Option(help="Memory read before --from, so old facts don't look new.")] = 42,
    top: Annotated[int, typer.Option(help="How many top beliefs a model reads (claims).")] = 300,
    check: Annotated[int, typer.Option(help="How many of those get an evidence check at birth.")] = 100,
    find: Annotated[str | None, typer.Option(help="Also show where beliefs matching this regex rank.")] = None,
) -> None:
    """Find beliefs nobody named: new facts in memory, ranked by spread and survival, checked at birth."""
    from heirloom import discover
    from heirloom.db import connect
    from heirloom.llm import LLM
    from heirloom.render import print_discover

    if end.time() == time(0):
        end = end + timedelta(days=1) - timedelta(microseconds=1)
    llm = LLM()
    with connect() as con:
        index, data = discover.run(con, llm, start, end, start - timedelta(days=history_days), top, check)
        data, path = discover.save(con, llm, data)
    print_discover(data, path, index, find)


@app.command("alive")
def alive_cmd(
    since: Annotated[datetime, typer.Option("--since", formats=DATE_FORMATS,
                                            help="Trace back to here (default: the 2026 memory era).")]
    = datetime(2026, 3, 24),
    top: Annotated[int, typer.Option(help="How many top beliefs a model reads (claims).")] = 300,
    check: Annotated[int, typer.Option(help="How many of those get an evidence check at birth.")] = 100,
    find: Annotated[str | None, typer.Option(help="Also show where beliefs matching this regex rank.")] = None,
    focus: Annotated[str, typer.Option(help="numbers = counts, amounts, scores only; all = links and names too.")]
    = "numbers",
) -> None:
    """Still alive: what every active agent believes now, each fact traced back to its birth and checked there."""
    from heirloom import discover
    from heirloom.db import connect
    from heirloom.llm import LLM
    from heirloom.render import print_discover

    llm = LLM()
    with connect() as con:
        index, data = discover.alive(con, llm, since, top, check, focus)
        data, path = discover.save(con, llm, data)
    print_discover(data, path, index, find)


@app.command()
def trail(
    case: Annotated[str | None, typer.Option(help="Known case to rebuild, e.g. 93-list.")] = None,
    belief: Annotated[str | None, typer.Option(help="Id of a belief from the latest `discover` run.")] = None,
    tie_outs: Annotated[bool, typer.Option("--tieout/--no-tieout", help="Check key lines against evidence.")] = True,
) -> None:
    """Rebuild one belief's trail from the raw data and save it to runs/."""
    from heirloom import trail as trails
    from heirloom.db import connect
    from heirloom.llm import LLM
    from heirloom.render import print_trail
    from heirloom.score import belief_case

    if bool(case) == bool(belief):
        raise typer.BadParameter("give exactly one of --case or --belief")
    if case and case not in trails.CASES:
        raise typer.BadParameter(f"known cases: {', '.join(trails.CASES)}")
    chosen = trails.CASES[case] if case else belief_case(belief)
    llm = LLM()
    with connect() as con:
        result = trails.build(con, llm, chosen, tie_outs)
        data, path = trails.save(con, llm, result)
    print_trail(data, path)


@app.command("lifecycle")
def lifecycle_cmd(
    case: Annotated[list[str] | None, typer.Option("--case", help="Only these saved trails (repeatable).")] = None,
) -> None:
    """Re-read each saved trail snapshot by snapshot (no model calls): episodes, returns, relapses."""
    import json

    from heirloom import lifecycle
    from heirloom.db import connect

    runs = lifecycle.latest_runs()
    with connect() as con:
        for slug, path in runs.items():
            if case and slug not in case:
                continue
            data = lifecycle.analyse(con, json.loads(path.read_text(encoding="utf-8")))
            out = lifecycle.save(data)
            cov = data["coverage"]
            typer.echo(f"{slug}: {len(data['agents'])} agents held it · "
                       f"{sum(len(a['returns']) for a in data['agents'])} returns · "
                       f"{sum(1 for a in data['agents'] if a['relapse'])} relapses · "
                       f"{len(data['swarm_returns'])} swarm returns · labelled {cov['labelled']}/{cov['lines']} · "
                       f"matches trail: {data['matches_trail']} → {out}")


@app.command("live")
def live_cmd(
    case: Annotated[list[str], typer.Option("--case", help="Saved trail(s) whose end-of-export holders to check.")],
) -> None:
    """Still held today? Read the live village's newest memories of every agent still holding a belief at export end."""
    from heirloom import live
    from heirloom.db import connect

    with connect(read_only=True) as con:
        for slug in case:
            data = live.check(con, slug)
            path = live.save(data)
            for a in data["agents"]:
                typer.echo(f"{slug} · {a['agent']}: {a['snapshots_matching_pattern']} of {a['snapshots_read']} "
                           f"newest snapshots ({a['from']} → {a['to']}) still match")
            typer.echo(f"saved {path}")


audit_app = typer.Typer(no_args_is_help=True, help="Label accuracy check: sample, judge blind, compare.")
app.add_typer(audit_app, name="audit")


@audit_app.command("sample")
def audit_sample() -> None:
    """Draw the fixed random sample (seed in audit.py) into data/audit/sample.json."""
    from collections import Counter

    from heirloom import audit
    from heirloom.db import connect

    with connect() as con:
        items = audit.sample(con)
    typer.echo(f"{len(items)} items: {dict(Counter((x['kind'], x['model_label']) for x in items))}")
    typer.echo(f"for Rohit: {', '.join(x['id'] for x in items if x['for_rohit'])}")
    typer.echo(f"saved {audit.SAMPLE}")


@audit_app.command("show")
def audit_show(
    first: Annotated[int, typer.Option(help="First item number.")] = 1,
    last: Annotated[int, typer.Option(help="Last item number.")] = 10,
    rohit: Annotated[bool, typer.Option(help="Only Rohit's items.")] = False,
) -> None:
    """Print items blind: no model label, quote or reason."""
    import json

    from heirloom import audit
    from heirloom.db import connect

    items = json.loads(audit.SAMPLE.read_text(encoding="utf-8"))
    pick = [x for x in items if x["for_rohit"]] if rohit else items[first - 1:last]
    with connect(read_only=True) as con:
        typer.echo(audit.blind(con, pick))


@audit_app.command("sheet")
def audit_sheet() -> None:
    """Write Rohit's blind sheet (his 20 items, definitions, an answer table) to docs/internal/AUDIT-ROHIT.md."""
    import json

    from heirloom import audit
    from heirloom.config import ROOT
    from heirloom.db import connect

    items = [x for x in json.loads(audit.SAMPLE.read_text(encoding="utf-8")) if x["for_rohit"]]
    with connect(read_only=True) as con:
        body = audit.blind(con, items)
    path = ROOT / "docs" / "internal" / "AUDIT-ROHIT.md"
    path.write_text(audit.SHEET_HEAD + body + "\n\n## Your answers\n\n| id | answer | note (optional) |\n|---|---|---|\n"
                    + "".join(f"| {x['id']} | | |\n" for x in items), encoding="utf-8")
    typer.echo(f"{len(items)} items → {path}")


@audit_app.command("models")
def audit_models() -> None:
    """Model vs model on the same lines (Cohen's kappa) → runs/analysis/model-agreement.json."""
    import json

    from heirloom import audit
    from heirloom.db import connect

    with connect(read_only=True) as con:
        data = audit.model_agreement(con)
    path = audit.ANALYSIS / "model-agreement.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    for row in data["pairs"]:
        typer.echo(f"{row['a']} vs {row['b']} on {row['lines']} lines ({row['sample']}): agree {row['agree']} · "
                   f"kappa {row['kappa']} · holds-or-not agree {row['holds_agree']} kappa {row['holds_kappa']}")
    typer.echo(f"saved {path}")


@audit_app.command("score")
def audit_score() -> None:
    """Compare every judge's labels with the model's; write runs/analysis/audit.json (masked)."""
    import json

    from heirloom import audit
    from heirloom.db import connect

    items = json.loads(audit.SAMPLE.read_text(encoding="utf-8"))
    judges = {name: j for name in ("claude", "claude-firstpass", "rohit") if (j := audit.load(name))}
    with connect(read_only=True) as con:
        path = audit.publish(con, items, judges)
    data = json.loads(path.read_text(encoding="utf-8"))
    for name, a in data["judges"].items():
        typer.echo(f"{name}: all {a['all']} · stance {({k: a['stance'][k] for k in ('n', 'agree', 'ci95')})} · "
                   f"evidence checks {({k: a['tieout'][k] for k in ('n', 'agree', 'ci95')})}")
    if "claude_vs_rohit" in data:
        typer.echo(f"claude vs rohit: {data['claude_vs_rohit']}")
    typer.echo(f"saved {path}")


@app.command("chance")
def chance_cmd() -> None:
    """Do copies follow another agent's affirming chat message closer than luck would? (no model calls)"""
    import json

    from heirloom import chance
    from heirloom.db import connect
    from heirloom.lifecycle import ANALYSIS, latest_runs

    runs = {s: json.loads(p.read_text(encoding="utf-8")) for s, p in latest_runs().items()
            if s in {x for slugs in chance.ERAS.values() for x in slugs}}
    with connect() as con:  # labels() makes sure its table exists, so not read-only
        data = chance.test(con, runs)
    path = ANALYSIS / "chance.json"
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    for era, row in data["eras"].items():
        typer.echo(f"{era}: {row['within_gap']} of {row['copies']} copies within {data['gap_minutes']:.0f} min of "
                   f"another agent's affirming message · expected by chance {row['expected_by_chance']} "
                   f"(p = {row['p_value']:.2g}); at the agent's own write times {row['expected_own_writes']} "
                   f"(p = {row['p_value_own_writes']:.2g})")
    typer.echo(f"saved {path}")


@app.command("facts")
def facts_cmd() -> None:
    """Recompute every headline number from the saved runs (no database, no model) into runs/analysis/facts.json."""
    import json

    from heirloom import facts

    data = facts.compute()
    path = facts.save(data)
    for key in ("public_2025", "discovery", "era_2025", "monitor_2026", "lifecycle"):
        typer.echo(f"{key}: {json.dumps(data[key], default=str)}")
    typer.echo(f"saved {path}")


@app.command("verify")
def verify_cmd(
    db: Annotated[bool, typer.Option("--db/--no-db", help="Also find every quote and line in its raw row.")] = True,
) -> None:
    """Re-check every saved result: facts, doc numbers, trail consistency, privacy, and (with --db) raw quotes."""
    from rich.console import Console
    from rich.table import Table

    from heirloom import verify
    from heirloom.config import DB_PATH

    with_db = db and DB_PATH.exists()
    if with_db:
        from heirloom.db import connect

        with connect(read_only=True) as con:
            checks = verify.run(con)
    else:
        checks = verify.run()
    path = verify.save(checks, with_db)
    t = Table(title="heirloom verify" + ("" if with_db else " (no database: raw-row checks skipped)"))
    for col in ("check", "result", "passed", "failed"):
        t.add_column(col)
    for c in checks:
        t.add_row(c.name, "[green]pass[/]" if c.passed else "[red]FAIL[/]", str(c.ok), str(len(c.failures)))
    console = Console()
    console.print(t)
    for c in checks:
        for f in c.failures[:5]:
            console.print(f"  [red]✗[/] {c.name}: {f}", highlight=False)
    console.print(f"saved {path}")
    raise typer.Exit(0 if all(c.passed for c in checks) else 1)


@app.command("score")
def score_cmd(
    case: Annotated[list[str] | None, typer.Option("--case", help="Only these cases (repeatable).")] = None,
) -> None:
    """Rebuild every known case and check it against the public accounts (KNOWN-CASES.md)."""
    from rich.console import Console
    from rich.table import Table

    from heirloom import score as scoring
    from heirloom import trail as trails
    from heirloom.db import connect
    from heirloom.llm import LLM

    llm, rows, export = LLM(), [], None
    with connect() as con:
        for slug, c in trails.CASES.items():
            if case and slug not in case:
                continue
            data, path = trails.save(con, llm, trails.build(con, llm, c))
            rows.append(scoring.score(c, data) | {"run": path})
            export = data["export"]
    path = scoring.save(rows, export)

    def mark(v):
        return "—" if v is None else ("✓" if v else "✗")

    t = Table(title="Known cases rebuilt from raw data (AI Digest / AI Village dataset)")
    for col in ("case", "born in (public)", "origin found", "birth", "believers", "expected found", "corrected",
                "verified quotes"):
        t.add_column(col)
    for r, c in zip(rows, [trails.CASES[x["case"]] for x in rows]):
        t.add_row(r["case"], c.expect_birth or "—", ", ".join(dict.fromkeys(r["origin"])) or "—",
                  mark(r["birth_agent_ok"]), ", ".join(r["believers"]) or "—", r["expected_believers_found"] or "—",
                  f"{'yes' if r['correction_found'] else 'no'} {mark(r['correction_ok'])}",
                  f"{r['verified_quotes']} ({r['dropped_quotes']} dropped)")
    Console().print(t)
    Console().print(f"LLM project spend ${llm.spent:.2f} of ${llm.limit:.2f} · saved {path}")
