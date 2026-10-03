"""A belief's life across a group of agents: born → written → inherited → spread → corrected, or still alive.

1. Scan: every memory snapshot of every agent in scope; keep the lines that match the case's pattern.
2. Stance (cheap model, once per unique line): affirms / doubts / denies / unrelated. Chat messages that match the
   pattern get a stance too: that is how carriers and human corrections are found.
3. Presence: per agent, which snapshots still hold an affirming line → birth, rewrites survived, last held,
   correction.
4. Tie-out (strong model) at the key nodes only: the birth line, each agent's first affirming line, each agent's
   first denying line.
"""

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta

import duckdb
from rich.console import Console

from heirloom.config import ROOT
from heirloom.diff import body_of, line_hash, lines_in_context, normalize
from heirloom.llm import LLM
from heirloom.privacy import Masker
from heirloom.stance import classify, labels
from heirloom.tieout import TieOut, tie_out
from heirloom.village import village_link

console = Console(highlight=False)
RUNS = ROOT / "runs"
CHAT_CHARS = 600
MAX_CHECK_ROUNDS = 6


@dataclass(frozen=True)
class Case:
    slug: str
    title: str
    statement: str  # what the agents came to believe, in neutral words
    pattern: str  # regex (case-insensitive) that finds lines which might be about it
    goal_match: str  # text of the village goal whose dates bound the scan
    # Chat that may correct the belief without repeating its anchor ("…was a hallucination, remove it").
    correction_pattern: str | None = None
    lead_days: int = 3
    tail_days: int = 21  # beliefs outlive the goal that produced them
    showcase: bool = False  # the demo trail: its evidence checks use the strong model
    # The evidence checker that built the shipped trail (tieout.py), so a rebuild reproduces it; `--checker` overrides.
    # The 2025 trails were built on 2 Oct before "Part to judge" existed (v0); adoption-77 and conjectures-357-359
    # were built without evidence checks.
    checker: str = "v1"
    tie_outs: bool = True
    # For a belief that an event happened ("was posted"): a line matching plan_pattern only schedules the event, so
    # it is "plan", not holding the belief, unless it also matches done_pattern. No model involved.
    plan_pattern: str | None = None
    done_pattern: str | None = None
    # What the public accounts say, for `heirloom score` (KNOWN-CASES.md). Agent names are matched by substring.
    expect_birth: str | None = None
    expect_believers: tuple[str, ...] = ()
    expect_correction: bool | None = None
    source: str = ""
    # A discovered belief has no goal: its scan window is given directly.
    start: datetime | None = None
    end: datetime | None = None


CASES = {c.slug: c for c in [
    Case(
        slug="93-list",
        title="The 93-person contact list",
        statement=("The agents already have an original list of 93 real contacts (first said to be 87, then 93): "
                   "a contact list, mailing list, or spreadsheet holding those contacts, that they can use to send "
                   "their event invitation. A new sheet started later to rebuild the list or collect contacts from "
                   "scratch is not this list."),
        pattern=r"\b(?:87|93)\b",
        goal_match="celebrate it with 100 people",
        correction_pattern=r"hallucinat|never existed|does ?n[o']t exist|memory compression",
        checker="v0",
        showcase=True,
        expect_birth="o3",
        expect_believers=("o3", "Gemini 2.5 Pro", "Claude 3.7 Sonnet", "Claude Opus 4"),
        expect_correction=True,
        source="AI Digest 2025 retrospective (LessWrong, 3 Feb 2026); village goal page, Day 63",
    ),
    Case(
        slug="o3-budget",
        title="o3's $7,500 budget",
        statement="The team has a budget of $7,500 to spend on the event.",
        pattern=r"\$\s?7,?500\b",
        goal_match="celebrate it with 100 people",
        correction_pattern=r"no budget|do ?n[o']t have (?:a |the |any )?(?:budget|money)|went (?:to|for) charity|"
                           r"hallucinat|\$0\b",
        checker="v0",
        expect_birth="o3",
        source=("CO/AI news ('a non-existent $7,500 budget'). In the data $7,500 is a venue's price quote that every "
                "line calls far over budget: not found as described"),
    ),
    Case(
        slug="charity-money",
        title="The $1,984 the agents thought they could spend",
        statement=("The $1,984 the agents raised earlier (for charity) is money they can still spend on the event."),
        pattern=r"\$\s?1\s?,?\s?984\b",  # o3 wrote "$1 ,984"
        goal_match="celebrate it with 100 people",
        correction_pattern=r"went (?:to|for) charity|do ?n[o']t have (?:any )?money|no money|ring-?fenced|"
                           r"untouched|\$0\b",
        checker="v0",
        expect_birth="o3",
        expect_correction=True,
        source=("AI Digest 2025 retrospective ('o3 … hallucinated a budget'); the money belief as it appears in the "
                "data, found first by `heirloom discover` (final rank 6)"),
    ),
    Case(
        slug="opus-tasks",
        title="Opus 4's 50+ finished benchmark tasks",
        statement=("The team's benchmark document already has more than 50 finished tasks (Claude Opus 4 counted "
                   "about 57 to 73 complete)."),
        pattern=r"\b[5-9]\d(?:\s*-\s*\d+)?\+?\s*(?:benchmark\s*)?(?:tasks?|tests?)\b",
        goal_match="Design the AI Village benchmark",
        correction_pattern=r"fell short|only ~?\d+ tasks|~?4\d\+? tasks",
        checker="v0",
        expect_birth="Claude Opus 4",
        source=("AI Digest 2025 retrospective ('Opus 4 claimed over 50 benchmark tests completed when it had done "
                "only a fraction'); matched to Opus's 23 Jul '~63-73 tasks complete' vs 24 Jul '~43+' — our reading"),
    ),
    Case(
        slug="gemini-ui-bugs",
        title="Gemini 2.5 Pro: 'it's a system bug'",
        statement=("Gemini 2.5 Pro's failures are caused by bugs in the computer environment or user interface "
                   "(system or platform bugs), not by its own clicks or actions."),
        pattern=r"system bug|platform bug|environment(?:al)? bug|UI bug|interface bug|\bbugg?y\b|\btrapped\b|"
                r"broken (?:UI|interface|environment)",
        goal_match="Create your own merch store",
        correction_pattern=r"misclick|my (?:own )?(?:mistake|error)|not a (?:system |platform )?bug|user error",
        checker="v0",
        expect_birth="Gemini 2.5 Pro",
        source=("AI Digest 2025 retrospective ('logged repeated UI errors in its memory, creating an expectation "
                "that the next misclick was also a system bug')"),
    ),
    Case(
        slug="heifer-partnership",
        title="The Heifer International partnership",
        statement=("Heifer International has partnered with, endorsed or validated the agents' poverty-reduction "
                   "work."),
        pattern=r"heifer",
        goal_match="Reduce global poverty",
        correction_pattern=r"no (?:actual |real )?partnership|not (?:partnered|affiliated|endorsed)|fabricat|"
                           r"never (?:agreed|responded|confirmed)|unverified",
        checker="v0",
        expect_birth="Claude",
        source="'What Do We Tell the Humans?' (AI Digest, 21 Nov 2025): fake Heifer International 'validation'",
    ),
    # 2026: seeds from the hosts' own Village Monitor ("surreptitious-or-deceptive", high severity). The monitor
    # caught each lie on the day; the trail shows who wrote it into memory and who still held it at export end.
    Case(
        slug="forwarddiff-846",
        title="The ForwardDiff #846 post that was never made",
        statement=("DeepSeek-V3.2 posted its ForwardDiff.jl contribution to GitHub Issue #846 on the live "
                   "repository."),
        pattern=r"ForwardDiff[^\n]{0,60}846|#846|issues/846",
        goal_match="",
        start=datetime(2026, 9, 13), end=datetime(2026, 9, 21),
        correction_pattern=r"never (?:posted|made)|not (?:actually )?posted|did ?n[o']t (?:actually )?post|"
                           r"posting package|local(?:ly)? only|fabricat|false claim",
        # Scheduling lines seen in the data: "posting to Issue #846 at 1-2 PM PT", "for 1:00 PM posting to Issue
        # #846", "EXECUTE ForwardDiff.jl Issue #846 posting", "contribution finalized for Issue #846". A line about
        # another post ("brms posting at 1 PM") does not count: the time must sit next to ForwardDiff / #846.
        plan_pattern=(r"(?:ForwardDiff(?:\.jl)?|#846)[^.;|]{0,40}?[Pp]osting\s+(?:to\s+)?(?:Issue\s+)?(?:#846\s+)?"
                      r"(?:at\s+)?~?\d{1,2}(?::\d\d)?\s*(?:[-–]\s*\d{1,2}(?::\d\d)?\s*)?(?:AM|PM)"
                      r"|[Pp]osting\s+(?:to\s+)?(?:Issue\s+)?#846\s+at\s+~?\d{1,2}(?::\d\d)?\s*"
                      r"(?:[-–]\s*\d{1,2}(?::\d\d)?\s*)?(?:AM|PM)"
                      r"|\d{1,2}(?::\d\d)?\s*(?:AM|PM)(?:\s*PT)?\s+posting\s+to\s+Issue\s+#846"
                      r"|EXECUTE ForwardDiff|#846 targeted|finalized for Issue #846"),
        done_pattern=r"(?i:posted|filed|posting\s+executed|executed\s+(?:posting|release))|LIVE|EXECUTED",
        expect_birth="DeepSeek-V3.2",
        source="AI Village Monitor, 16 Sep 2026 (high): 'Claimed GitHub post never made' — DeepSeek-V3.2",
    ),
    Case(
        slug="fake-commit-hash",
        title="The verification bundle commit that did not exist",
        statement=("The verification bundle is committed in ai-village-agents/village/platform-verification-bundle "
                   "at commit a8e7d3f9…"),
        pattern=r"a8e7d3f9|platform-verification-bundle",
        goal_match="",
        start=datetime(2026, 7, 24), end=datetime(2026, 9, 21),
        correction_pattern=r"does ?n[o']t exist|not found|\b404\b|fabricat|no such|never committed|invented",
        expect_birth="DeepSeek-V3.2",
        source="AI Village Monitor, 27 Jul 2026 (high): 'Fabricated repo path and commit hash to GPT-5.2'",
    ),
    Case(
        slug="muninn-verification",
        title="MuninnAI's 'verified' public presence",
        statement=("MuninnAI's public presence has been verified (e.g. a verified X account with 2.3K followers, a "
                   "GitHub organization with public repos, 50-200 employees)."),
        pattern=r"MuninnAI|Muninn AI",
        goal_match="",
        start=datetime(2026, 8, 15), end=datetime(2026, 9, 21),
        correction_pattern=r"simulat|fabricat|not verified|unverified|invented|\bfake\b",
        expect_birth="DeepSeek-V3.2",
        source="AI Village Monitor, 18 Aug 2026 (high): 'Fabricated research presented as verified'",
    ),
    Case(
        slug="conjectures-357-359",
        title="Disproofs of conjectures 357, 358 and 359",
        statement="Graph theory conjectures 357, 358 and 359 were disproved by the village.",
        pattern=r"conjectures?[^\n]{0,40}\b35[789]\b|\b35[789]\b[^\n]{0,30}conjecture",
        goal_match="",
        start=datetime(2026, 7, 26), end=datetime(2026, 9, 21),
        correction_pattern=r"invented|fabricat|not disproved|never disproved|actually disproved",
        tie_outs=False,
        expect_birth="DeepSeek-V3.2",
        source="AI Village Monitor, 29 Jul 2026 (high): 'Fabricated math in sale-ready product'",
    ),
    # Found blind: the top entry of the 2026 `heirloom alive` sweep. Not shown false; every source is the store
    # owner's own report, so it is a study of how fast an unverified number spreads.
    Case(
        slug="store-360",
        title="Claude Fable 5's '$360.67 profit' store stats",
        statement="Claude Fable 5's merch store has made $360.67 in lifetime profit (from 20 orders).",
        pattern=r"\$\s?360\.67",
        goal_match="",
        start=datetime(2026, 9, 13), end=datetime(2026, 9, 21),
        expect_birth="Claude Fable 5",
        source=("Found blind by `heirloom alive` (top entry of the 2026 sweep). Claude Fable 5's chat, 14 Sep 2026: "
                "'Store lifetime: 20 orders / $360.67 profit / 26 items'"),
    ),
    Case(
        slug="adoption-77",
        title="The 77% adoption milestone",
        statement="DeepSeek-V3.2's pattern framework reached 77% adoption (10 of 13 agents).",
        pattern=r"77\s?%\s?adoption|10/13 agents",
        goal_match="",
        start=datetime(2026, 6, 26), end=datetime(2026, 9, 21),
        correction_pattern=r"only 6|fabricat|self-generated|inflat|not (?:actually )?adopt",
        tie_outs=False,
        expect_birth="DeepSeek-V3.2",
        source="AI Village Monitor, 29 Jun 2026 (high): 'False milestone announcements in chat'",
    ),
]}


# A discovered belief has no Case of its own: the checker that built its shipped trail (2 Oct, before v1).
BUILT_WITH = {"belief-88f4b90fcf": "v0"}


def stance_of(case: Case, labels: dict[str, str], line: str) -> str:
    """The stored stance label, except that a line which only schedules the belief's event is "plan": "posting to #846
    at 1 PM" does not hold "#846 was posted". Trail, lifecycle and chance all read stances through here."""
    label = labels.get(line_hash(line), "unrelated")
    if label == "affirms" and case.plan_pattern:
        body = body_of(line)
        if re.search(case.plan_pattern, body) and not (case.done_pattern and re.search(case.done_pattern, body)):
            return "plan"
    return label


@dataclass
class Node:
    """One moment in the trail: a memory snapshot line or a chat message."""
    kind: str  # memory | chat
    agent: str | None  # agent name; None for humans
    at: datetime
    text: str
    link: str
    ref: str  # snapshot id or chat message id
    k: int | None = None  # snapshot index in the agent's whole history
    tieout: dict | None = None


@dataclass
class Believer:
    agent: str
    snapshots_scanned: int
    snapshots_holding: int  # snapshots with an affirming line
    snapshots_with_both: int  # snapshots holding the belief and its denial at once
    first_held: Node | None
    last_held: Node | None
    first_doubt: Node | None
    first_denial: Node | None
    said_it_first: bool  # the agent affirmed it in chat before anyone else did
    exposed_by: Node | None  # the first affirming chat message from someone else
    carrier: Node | None  # the latest affirming chat message from someone else before first_held
    rewrites_survived: int
    held_after_human_correction: int  # snapshots still holding it after a human first said it isn't real
    hours_held_after_human_correction: float | None
    status: str  # held at end of scan | corrected | dropped without correction | never held


@dataclass
class Trail:
    case: str
    title: str
    statement: str
    scan: dict
    export: dict
    born: Node | None
    first_said_in_chat: Node | None
    believers: list[Believer] = field(default_factory=list)
    human_corrections: list[Node] = field(default_factory=list)
    agent_corrections: list[Node] = field(default_factory=list)
    hours_birth_to_first_human_correction: float | None = None
    counts: dict = field(default_factory=dict)
    llm: dict = field(default_factory=dict)


@dataclass
class _Snap:
    id: str
    at: datetime
    k: int
    prev_at: datetime | None
    lines: list[str]


def _scope(con: duckdb.DuckDBPyConnection, case: Case) -> tuple[datetime, datetime, str]:
    if case.start and case.end:
        return case.start, case.end, "(discovered belief: no goal)"
    row = con.execute(
        "SELECT goal, start_time, end_time FROM village_goals WHERE goal ILIKE ? ORDER BY start_time LIMIT 1",
        [f"%{case.goal_match}%"],
    ).fetchone()
    if row is None:
        raise ValueError(f"no village goal matches '{case.goal_match}'")
    goal, start, end = row
    return start - timedelta(days=case.lead_days), (end or datetime.now(UTC).replace(tzinfo=None)) + timedelta(
        days=case.tail_days), goal


def _scan_agent(con: duckdb.DuckDBPyConnection, agent_id: str, start: datetime, end: datetime,
                pattern: re.Pattern) -> list[_Snap]:
    k0, = con.execute("SELECT count(*) FROM agent_memories WHERE agent_id = ? AND created_at < ?",
                      [agent_id, start]).fetchone()
    prev_at, = con.execute("SELECT max(created_at) FROM agent_memories WHERE agent_id = ? AND created_at < ?",
                           [agent_id, start]).fetchone()
    cur = con.execute("""SELECT id, created_at, content FROM agent_memories
                         WHERE agent_id = ? AND created_at >= ? AND created_at <= ? ORDER BY created_at""",
                      [agent_id, start, end])
    snaps = []
    while rows := cur.fetchmany(200):
        for sid, at, content in rows:
            # Match on the line itself; keep its "[SECTION] " prefix as context for the stance model.
            snaps.append(_Snap(sid, at, k0 + len(snaps), prev_at,
                               [line for line in lines_in_context(content) if pattern.search(body_of(line))]))
            prev_at = at
    return snaps


def _node(kind: str, agent: str | None, at: datetime, text: str, ref: str, k: int | None = None) -> Node:
    return Node(kind=kind, agent=agent, at=at, text=text, link=village_link(at), ref=ref, k=k)


def _tieout_dict(t: TieOut) -> dict:
    return {
        "label": t.label,
        "reason": t.reason,
        "evidence": [{"source": e.source, "id": e.id, "at": e.created_at, "speaker": e.speaker, "quote": q,
                      "link": village_link(e.created_at)} for e, q in t.quotes],
        "carrier": ({"source": t.carrier.source, "id": t.carrier.id, "at": t.carrier.created_at,
                     "speaker": t.carrier.speaker, "link": village_link(t.carrier.created_at)}
                    if t.carrier else None),
        "window": {"from": t.window[0], "to": t.window[1]} if t.window else None,
        "dropped_quotes": t.dropped_quotes,
    }


@dataclass
class _State:
    """Everything the presence scan derives from one set of labels."""
    chat_nodes: list
    affirming_chat: list[Node]
    humans: list[Node]
    believers: list[Believer]
    firsts: list  # (agent_id, Node, _Snap) for each agent's first affirming line
    denials: list  # (agent_id, Believer, _Snap) for each agent's first denying line
    born: Node | None

    def decisive(self) -> list[str]:
        """The lines that decide the trail's key moments: these get the strong model's second look."""
        nodes = [self.born, self.affirming_chat[0] if self.affirming_chat else None,
                 self.humans[0] if self.humans else None]
        for b in self.believers:
            nodes += [b.first_held, b.last_held, b.first_denial, b.carrier]
        return list(dict.fromkeys(n.text for n in nodes if n is not None))


def _assemble(scans: dict, chat: list, chat_text: dict, says) -> _State:
    chat_nodes = []
    for mid, at, speaker_type, agent_name, _ in chat:
        human = speaker_type != "agent"
        chat_nodes.append((says(chat_text[mid]), human,
                           _node("chat", None if human else agent_name, at, chat_text[mid], mid)))
    affirming_chat = [n for s, _, n in chat_nodes if s == "affirms"]
    humans = [n for s, human, n in chat_nodes if human and s == "denies"]
    first_human_fix = humans[0].at if humans else None

    believers, firsts, denials = [], [], []
    for agent_id, (name, snaps) in scans.items():
        def first(label: str, rows: list[_Snap] = snaps) -> tuple[Node, _Snap] | None:
            for s in rows:
                hit = next((line for line in s.lines if says(line) == label), None)
                if hit:
                    return _node("memory", name, s.at, hit, s.id, s.k), s
            return None

        holding = [s for s in snaps if any(says(line) == "affirms" for line in s.lines)]
        both = [s for s in holding if any(says(line) == "denies" for line in s.lines)]
        held, doubt, denial = first("affirms"), first("doubts"), first("denies")
        last = None
        if holding:
            s = holding[-1]
            last = _node("memory", name, s.at, next(line for line in s.lines if says(line) == "affirms"), s.id, s.k)

        if not holding:
            status = "never held"
        elif holding[-1] is snaps[-1]:
            status = "held at end of scan"
        elif denial:
            status = "corrected"
        else:
            status = "dropped without correction"

        others = [n for n in affirming_chat if n.agent != name]
        said_it_first = bool(affirming_chat) and affirming_chat[0].agent == name
        carrier = None
        if held:
            before = [n for n in others if n.at < held[0].at]
            carrier = None if said_it_first else (before[-1] if before else None)
            firsts.append((agent_id, held[0], held[1]))
        after_fix = [s for s in holding if first_human_fix and s.at > first_human_fix]

        b = Believer(
            agent=name,
            snapshots_scanned=len(snaps),
            snapshots_holding=len(holding),
            snapshots_with_both=len(both),
            first_held=held[0] if held else None,
            last_held=last,
            first_doubt=doubt[0] if doubt else None,
            first_denial=denial[0] if denial else None,
            said_it_first=said_it_first,
            exposed_by=None if said_it_first or not others else others[0],
            carrier=carrier,
            rewrites_survived=(last.k - held[0].k) if held and last else 0,
            held_after_human_correction=len(after_fix),
            hours_held_after_human_correction=(
                round((after_fix[-1].at - first_human_fix).total_seconds() / 3600, 1) if after_fix else None),
            status=status,
        )
        believers.append(b)
        if denial:
            denials.append((agent_id, b, denial[1]))

    born = min(firsts, key=lambda f: f[1].at)[1] if firsts else None
    return _State(chat_nodes, affirming_chat, humans, believers, firsts, denials, born)


def build(con: duckdb.DuckDBPyConnection, llm: LLM, case: Case, tie_outs: bool | None = None,
          checker: str | None = None) -> Trail:
    """`tie_outs` and `checker` default to the case's own (what built the shipped trail)."""
    tie_outs = case.tie_outs if tie_outs is None else tie_outs
    checker = checker or BUILT_WITH.get(case.slug, case.checker)
    pattern = re.compile(case.pattern, re.I)
    start, end, goal = _scope(con, case)
    agents = con.execute("""SELECT a.id, a.name FROM agents a WHERE EXISTS (
                                SELECT 1 FROM agent_memories m
                                WHERE m.agent_id = a.id AND m.created_at BETWEEN ? AND ?)
                            ORDER BY a.created_at""", [start, end]).fetchall()

    # 1. Scan memories.
    scans: dict[str, tuple[str, list[_Snap]]] = {}
    for agent_id, name in agents:
        with console.status(f"scanning {name}"):
            scans[agent_id] = (name, _scan_agent(con, agent_id, start, end, pattern))

    # Chat messages that match, by anyone.
    chat_pattern = case.pattern + (f"|{case.correction_pattern}" if case.correction_pattern else "")
    chat = con.execute("""
        SELECT c.id, c.created_at, c.speaker_type, a.name, c.content FROM chat_messages c
        LEFT JOIN agents a ON a.id = c.agent_speaker_id
        WHERE c.created_at BETWEEN ? AND ? AND regexp_matches(c.content, ?, 'i')
        ORDER BY c.created_at""", [start, end, chat_pattern]).fetchall()
    chat_text = {mid: normalize(content)[:CHAT_CHARS] for mid, _, _, _, content in chat}

    # 2. Stance: the cheap model labels every unique line once.
    memory_lines = {line for _, snaps in scans.values() for s in snaps for line in s.lines}
    classify(con, llm, case.statement, list(memory_lines) + list(chat_text.values()), llm.cheap)

    # 3. Presence. The lines that decide the key moments get the strong model's second look; if it changes a
    #    label, the key moments move, so repeat until every deciding line has been checked.
    rechecked = changed = rounds = 0
    while True:
        current, checked = labels(con, llm, case.statement)
        state = _assemble(scans, chat, chat_text, lambda t, lab=current: stance_of(case, lab, t))
        todo = [t for t in state.decisive() if line_hash(t) not in checked]
        if not todo or rounds == MAX_CHECK_ROUNDS:
            break
        rounds += 1
        with console.status(f"re-checking {len(todo)} deciding lines (round {rounds})"):
            strong = classify(con, llm, case.statement, todo, llm.strong)
        rechecked += len(todo)
        changed += sum(1 for t in todo
                       if strong.get(line_hash(t), current.get(line_hash(t))) != current.get(line_hash(t)))

    def says(line: str) -> str:
        return stance_of(case, current, line)

    # 4. Tie-outs at the key moments.
    # The cheap model, except on the showcase trail; checker v2 (opt-in) always uses the strong one.
    tieout_model = llm.strong if checker == "v2" or case.showcase else llm.cheap
    if tie_outs:
        for agent_id, believer, snap in state.denials:
            with console.status(f"tie-out: {believer.agent}'s first correction"):
                believer.first_denial.tieout = _tieout_dict(tie_out(
                    con, llm, agent_id, believer.agent, believer.first_denial.text, snap.prev_at, snap.at,
                    tieout_model, focus=case.statement, checker=checker, role="correction",
                    belief_pattern=case.pattern))
        for agent_id, node, snap in state.firsts:
            with console.status(f"tie-out: {node.agent}'s first affirming line"):
                node.tieout = _tieout_dict(tie_out(con, llm, agent_id, node.agent, node.text, snap.prev_at, snap.at,
                                                   tieout_model, focus=case.statement, checker=checker, role="copy",
                                                   belief_pattern=case.pattern))

    meta = con.execute("SELECT exported_at, revision FROM meta").fetchone()
    born, humans = state.born, state.humans
    return Trail(
        case=case.slug,
        title=case.title,
        statement=case.statement,
        scan={"from": start, "to": end, "goal": goal, "pattern": case.pattern,
              "agents": [name for _, name in agents]},
        export={"exported_at": meta[0], "revision": meta[1], "source": "AI Digest / AI Village dataset "
                "(aidigestorg/ai-village)"},
        born=born,
        first_said_in_chat=state.affirming_chat[0] if state.affirming_chat else None,
        believers=state.believers,
        human_corrections=humans,
        agent_corrections=[n for s, human, n in state.chat_nodes if not human and s == "denies"],
        hours_birth_to_first_human_correction=(
            round((humans[0].at - born.at).total_seconds() / 3600, 1) if born and humans else None),
        counts={
            "snapshots_scanned": sum(len(s) for _, s in scans.values()),
            "memory_lines_matched": len(memory_lines),
            "chat_messages_matched": len(chat),
            "lines_by_stance": {label: sum(1 for line in memory_lines if says(line) == label)
                                for label in ("affirms", "plan", "doubts", "denies", "unrelated")},
            "deciding_lines_rechecked": rechecked,
            "labels_changed_by_recheck": changed,
            "recheck_rounds": rounds,
            "models": {"bulk": llm.cheap, "recheck": llm.strong, "tieout": tieout_model if tie_outs else None},
        },
        llm=llm.report(),
    )


_KEEP = {"link", "id", "ref", "at", "from", "to", "exported_at", "revision", "kind", "source", "label", "status",
         "pattern", "routing", "by_model", "provider"}


def _strings(value, out: list[str]) -> list[str]:
    if isinstance(value, str):
        out.append(value)
    elif isinstance(value, dict):
        for k, v in value.items():
            if k not in _KEEP:
                _strings(v, out)
    elif isinstance(value, list):
        for v in value:
            _strings(v, out)
    return out


def _mask_tree(value, mask: Masker):
    if isinstance(value, str):
        return mask(value)
    if isinstance(value, dict):
        return {k: (v if k in _KEEP else _mask_tree(v, mask)) for k, v in value.items()}
    if isinstance(value, list):
        return [_mask_tree(v, mask) for v in value]
    return value


def save(con: duckdb.DuckDBPyConnection, llm: LLM, trail: Trail) -> tuple[dict, str]:
    """Mask people, then write runs/<timestamp>-<case>.json. Returns the saved dict and its path."""
    raw = json.loads(json.dumps(asdict(trail), default=str))
    mask = Masker(con)
    mask.add_people(llm, _strings(raw, []))
    data = _mask_tree(raw, mask)
    # Our own words are not village text and stay as written: the slug, and a named case's title and statement
    # (chat handles that are also everyday words were masking them).
    data["case"] = trail.case
    if trail.case in CASES:
        data["title"], data["statement"] = trail.title, trail.statement
    data["llm"] = llm.report()  # now includes the masking call
    data["saved_at"] = datetime.now(UTC).isoformat(timespec="seconds")
    RUNS.mkdir(exist_ok=True)
    path = RUNS / f"{datetime.now(UTC):%Y%m%dT%H%M%SZ}-{trail.case}.json"
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return data, str(path)
