"""Terminal output for the pipeline commands."""

import re
from collections import Counter
from collections.abc import Iterable

from rich.console import Console
from rich.markup import escape

from heirloom.village import village_link
from heirloom.windows import Window

console = Console(highlight=False)

LINE_WIDTH = 220
EVIDENCE_WIDTH = 240


def _clip(text: str, width: int) -> str:
    text = " ".join(text.split())
    return escape(text if len(text) <= width else text[: width - 1] + "…")


def print_windows(agent_name: str, windows: Iterable[Window], grep: str | None, show_evidence: bool,
                  show_all: bool) -> None:
    pattern = re.compile(grep, re.I) if grep else None
    keep = (lambda s: bool(pattern.search(s))) if pattern else (lambda s: True)
    total = shown = 0

    for w in windows:
        total += 1
        d = w.diff
        added = [line for line in d.added if keep(line)]
        changed = [c for c in d.changed if keep(c.new) or keep(c.old)]
        reworded = [c for c in d.reworded if keep(c.new) or keep(c.old)] if show_all else []
        vanished = [line for line in d.vanished if keep(line)]
        if not (added or changed or reworded or vanished):
            continue
        shown += 1

        kinds = Counter(e.source for e in w.evidence)
        span = f"{(w.snap.created_at - w.start).total_seconds():,.0f} s" if w.start else "first snapshot"
        ev = ", ".join(f"{n} {k}" for k, n in kinds.most_common()) or "nothing"
        squeeze = f"  [yellow]compression {d.old_chars:,}→{d.new_chars:,} chars[/yellow]" if d.compression else ""
        console.print(
            f"\n[bold]#{w.k}[/bold]  {w.snap.created_at:%Y-%m-%d %H:%M:%S} UTC  ·  "
            f"[green]+{len(d.added)}[/green] [cyan]~{len(d.changed)}[/cyan] [dim]≈{len(d.reworded)}[/dim] "
            f"[magenta]−{len(d.vanished)}[/magenta]  ·  {d.new_chars:,} chars  ·  window {span}: {ev}{squeeze}"
        )
        for line in added:
            console.print(f"  [green]+ {_clip(line, LINE_WIDTH)}[/green]")
        for c in changed:
            console.print(f"  [cyan]~ {_clip(c.old, LINE_WIDTH)}[/cyan]")
            console.print(f"  [cyan]→ {_clip(c.new, LINE_WIDTH)}[/cyan]")
        for c in reworded:
            console.print(f"  [dim]≈ {_clip(c.new, LINE_WIDTH)}[/dim]")
        for line in vanished:
            console.print(f"  [magenta]− {_clip(line, LINE_WIDTH)}[/magenta]")
        if show_evidence:
            for e in w.evidence:
                console.print(f"    [dim]{e.created_at:%H:%M:%S} {e.source:<15} {escape(e.speaker or '?'):<18}[/dim] "
                              f"{_clip(e.text, EVIDENCE_WIDTH)}")
        console.print(f"  [dim]{village_link(w.snap.created_at)}[/dim]")

    console.print(f"\n[bold]{agent_name}[/bold]: {total:,} snapshots read, {shown:,} shown"
                  + (f" (lines matching /{grep}/)" if grep else ""))


def print_discover(data: dict, path: str, index: list, find: str | None, show: int = 25) -> None:
    c = data["counts"]
    if data["kind"] == "alive":
        console.print(f"\n[bold]Still alive[/bold] — facts in the agents' latest memories, traced back to "
                      f"{data['scan']['from'][:10]} · {c['agents']} agents · {c['facts_in_latest_memory']:,} facts · "
                      f"{c['beliefs']:,} born in the window ({c['older_than_window']:,} older) · {c['read_by_model']} "
                      f"read by a model · {c['tied_out']} checked at birth")
    else:
        console.print(f"\n[bold]Beliefs found[/bold] {data['scan']['from'][:10]} → {data['scan']['to'][:10]} · "
                      f"{c['agents']} agents · {c['anchors_born']:,} new anchors · {c['beliefs']:,} beliefs held in "
                      f"3+ snapshots · {c['read_by_model']} read by a model · {c['tied_out']} checked at birth")
    console.print(f"[dim]labels at birth: {c['labels']}[/dim]\n")
    for i, b in enumerate(data["ranked"][:show], 1):
        t = b["tieout"] or {}
        alive = f" · [yellow]still held by {len(b['alive_in'])}[/yellow]" if b["alive_in"] else ""
        console.print(f"[bold]{i:>2}.[/bold] score {b['score']:<7} [bold]{t.get('label', '?')}[/bold] · "
                      f"{b['agents']} agent(s) · {b['rewrites']:,} rewrites{alive} · born {_when(str(b['born']['at']))} "
                      f"in {escape(b['born']['agent'])}")
        claim = (b.get("claim") or {}).get("text") or b["line"]
        console.print(f"     “{_clip(claim, 180)}”  [dim]{', '.join(b['anchors'][:3])}[/dim]")
    if find:
        import re

        pattern = re.compile(find, re.I)
        hits = [row for row in index if pattern.search(row[3])]
        console.print(f"\n[bold]/{escape(find)}/[/bold]: {len(hits)} of {len(index):,} beliefs match; best lead ranks:")
        for rank, agent, at, line, anchors_ in hits[:8]:
            checked = next((i for i, b in enumerate(data["ranked"], 1) if b["line"][:60] == line[:60]), None)
            console.print(f"  lead rank {rank:>5} · final rank {checked or '—':>4} · {at:%Y-%m-%d %H:%M} "
                          f"{escape(agent)} · {', '.join(anchors_)} · “{_clip(line, 110)}”")
    console.print(f"\nLLM cost this run: ${data['llm']['total_cost']:.4f} · project ${data['llm']['project_spent']:.2f}"
                  f" of ${data['llm']['project_limit']:.2f} · saved {path}")


def _when(at: str) -> str:
    return at[:19].replace("T", " ") + " UTC"


def _node_line(label: str, node: dict | None, colour: str = "white") -> None:
    if not node:
        console.print(f"  {label:<22} [dim]—[/dim]")
        return
    who = node.get("agent") or "[person]"
    k = f" · rewrite #{node['k']}" if node.get("k") is not None else ""
    console.print(f"  {label:<22} [{colour}]{_when(node['at'])}[/{colour}]  {escape(who)}{k}")
    console.print(f"  {'':<22} [dim]“{_clip(node['text'], LINE_WIDTH)}”[/dim]")
    t = node.get("tieout")
    if t:
        console.print(f"  {'':<22} tie-out: [bold]{t['label']}[/bold] — {_clip(t['reason'], 200)}")
        for ev in t["evidence"]:
            console.print(f"  {'':<24} [dim]{ev['source']} · {escape(str(ev['speaker']))} · {_when(ev['at'])}:[/dim] "
                          f"“{_clip(ev['quote'], 200)}”")
    console.print(f"  {'':<22} [dim]{node['link']}[/dim]")


def print_trail(trail: dict, path: str) -> None:
    console.print(f"\n[bold]Belief trail · {escape(trail['title'])}[/bold]")
    console.print(f"[dim]{escape(trail['statement'])}[/dim]")
    scan = trail["scan"]
    console.print(f"[dim]scan {_when(scan['from'])} → {_when(scan['to'])} · goal “{escape(scan['goal'])}” · "
                  f"export {trail['export']['exported_at']}[/dim]\n")

    _node_line("first said in chat", trail["first_said_in_chat"], "yellow")
    _node_line("born in memory", trail["born"], "yellow")

    for b in trail["believers"]:
        if b["status"] == "never held":
            continue
        console.print(f"\n[bold]{escape(b['agent'])}[/bold] · {b['status']} · held in {b['snapshots_holding']:,} of "
                      f"{b['snapshots_scanned']:,} snapshots · survived {b['rewrites_survived']:,} rewrites"
                      + (f" · {b['snapshots_with_both']:,} snapshots hold the belief and its denial"
                         if b["snapshots_with_both"] else ""))
        if b["held_after_human_correction"]:
            console.print(f"  [yellow]still held in {b['held_after_human_correction']:,} snapshots, for "
                          f"{b['hours_held_after_human_correction']:,} h, after a human first said it isn't real"
                          f"[/yellow]")
        if b["said_it_first"]:
            console.print("  [yellow]said it first, in chat[/yellow]")
        _node_line("first exposed by", b["exposed_by"], "cyan")
        _node_line("carried by", b["carrier"], "cyan")
        _node_line("first held", b["first_held"], "yellow")
        _node_line("first doubt", b["first_doubt"])
        _node_line("first denial", b["first_denial"], "green")
        _node_line("last held", b["last_held"], "yellow")

    if trail["human_corrections"]:
        console.print(f"\n[bold]Humans said it isn't real[/bold] ({len(trail['human_corrections'])} messages)")
        for n in trail["human_corrections"][:5]:
            _node_line("", n, "green")
    never = [b["agent"] for b in trail["believers"] if b["status"] == "never held"]
    if never:
        console.print(f"\n[dim]never held it: {escape(', '.join(never))}[/dim]")
    c = trail["counts"]
    console.print(f"\n{c['snapshots_scanned']:,} snapshots scanned · {c['memory_lines_matched']:,} unique lines matched "
                  f"· stance {c['lines_by_stance']} · {c['chat_messages_matched']:,} chat messages matched")
    if trail["hours_birth_to_first_human_correction"] is not None:
        console.print(f"birth → first human correction: {trail['hours_birth_to_first_human_correction']} h")
    console.print(f"LLM cost this run: ${trail['llm']['total_cost']:.4f} · saved {path}")
