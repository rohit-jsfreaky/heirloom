"""The checks that keep labels honest: verified quotes, raw-row matching, live links, the facts arithmetic."""

from datetime import datetime

import pytest

from heirloom.facts import PUBLIC_2025, era
from heirloom.tieout import SYSTEM, SYSTEM_V0, quote_ok, tie_out
from heirloom.trail import CASES
from heirloom.verify import MARKER, found_in
from heirloom.village import village_link
from heirloom.windows import Evidence

ROW = Evidence("turn", "t1", datetime(2025, 6, 12), "tool", "output: Spreadsheet RESONANCE-93 is   EMPTY (headers only)")


def test_a_quote_must_really_be_in_its_row():
    assert quote_ok("spreadsheet resonance-93 is empty", ROW, "o3")  # spacing and case aside
    assert quote_ok('"Spreadsheet RESONANCE-93 is EMPTY."', ROW, "o3")
    assert not quote_ok("Spreadsheet RESONANCE-93 has 93 rows", ROW, "o3")
    assert not quote_ok("...", ROW, "o3")  # punctuation alone verifies nothing
    assert not quote_ok("Spreadsheet", None, "o3")


def test_an_agents_own_chat_is_never_its_evidence():
    own = Evidence("chat", "c1", datetime(2025, 6, 12), "o3", "The list has 93 contacts")
    other = Evidence("chat", "c2", datetime(2025, 6, 12), "Claude Opus 4", "The list has 93 contacts")
    assert not quote_ok("The list has 93 contacts", own, "o3")
    assert quote_ok("The list has 93 contacts", other, "o3")


def test_only_checker_v2_matches_quotes_without_markdown_and_counts_summaries_as_narration():
    row = Evidence("turn", "t2", datetime(2026, 9, 14), "tool", 'output: **Commit:** a8e7d3f9\\n"pushed"')
    assert quote_ok('Commit: a8e7d3f9 "pushed"', row, "GPT-5.1", v2=True)
    assert not quote_ok('Commit: a8e7d3f9 "pushed"', row, "GPT-5.1")  # v0/v1: strict, as shipped
    summary = Evidence("session_summary", "s1", datetime(2026, 9, 14), "GPT-5.1", "Posted to Issue #846")
    assert quote_ok("Posted to Issue #846", summary, "GPT-5.1")
    assert not quote_ok("Posted to Issue #846", summary, "GPT-5.1", v2=True)


def test_the_shipped_checkers_are_pinned_per_trail():
    assert SYSTEM_V0 == SYSTEM.replace(SYSTEM[SYSTEM.index('- If a "Part to judge"'):SYSTEM.index("- Judge the")], "")
    assert {c.checker for s, c in CASES.items() if s in PUBLIC_2025} == {"v0"}
    assert {c.checker for s, c in CASES.items() if s not in PUBLIC_2025} == {"v1"}
    assert {s for s, c in CASES.items() if not c.tie_outs} == {"adoption-77", "conjectures-357-359"}
    with pytest.raises(ValueError):
        tie_out(None, None, "a", "o3", "line", None, datetime(2025, 6, 12), checker="v3")


def test_masked_text_is_found_in_the_raw_row():
    raw = "Per Bram and inkwell, the 93-email list was hallucinated"
    assert found_in("Per [person] and [person], the 93-email list was hallucinated", raw)
    assert not found_in("Per [person], the 87-email list was hallucinated", raw)
    assert not found_in("[person]", raw)


def test_village_link_uses_the_pacific_date_and_utc_millis():
    # Seen in a saved trail: GPT-5's memory at 2026-09-16 20:05:56.584847 UTC.
    assert village_link(datetime(2026, 9, 16, 20, 5, 56, 584847)) == \
        "https://theaidigest.org/village?date=2026-09-16&time=1789589156584"
    # 03:00 UTC is still the previous evening in California.
    assert village_link(datetime(2025, 6, 13, 3, 0)).startswith("https://theaidigest.org/village?date=2025-06-12&")


def test_doc_markers_name_the_fact_behind_a_number():
    text = "Of **50**<!--f:monitor_2026.copies--> copies, 66%<!-- f:monitor_2026.dropped_pct --> were dropped."
    assert [(m.group(1), m.group(2)) for m in MARKER.finditer(text)] == \
        [("50", "monitor_2026.copies"), ("66", "monitor_2026.dropped_pct")]


def _believer(agent, status, first, last, carrier=False, first_said=False, label=None):
    node = {"at": first, "tieout": {"label": label} if label else None}
    return {"agent": agent, "status": status, "first_held": node if status != "never held" else None,
            "last_held": {"at": last} if status != "never held" else None, "rewrites_survived": 10,
            "carrier": {"at": first} if carrier else None, "said_it_first": first_said}


def test_era_counts_each_copy_once():
    trails = {"case-a": {"believers": [
        _believer("o3", "corrected", "2025-06-01 00:00:00", "2025-06-02 00:00:00", first_said=True, label="instruction"),
        _believer("Gemini 2.5 Pro", "dropped without correction", "2025-06-01 06:00:00", "2025-06-01 18:00:00",
                  carrier=True, label="hearsay"),
        _believer("Claude Opus 4", "never held", None, None),
    ], "human_corrections": [{}], "agent_corrections": []}}
    e = era(trails, ["case-a", "missing-case"])
    assert (e["copies"], e["corrected"], e["dropped"], e["still_held"]) == (2, 1, 1, 0)
    assert (e["corrected_pct"], e["came_by_chat"], e["said_it_first"]) == (50, 1, 1)
    assert e["median_hours_held"] == 18.0 and e["max_hours_held"] == 24.0
    assert e["birth_labels"] == {"hearsay": 1, "instruction": 1}
    assert e["first_hour"] == 1  # o3 at the start; Gemini 6 h later
    assert e["cases"] == ["case-a"] and e["human_corrections"] == 1


def test_chance_helpers():
    from datetime import timedelta

    from heirloom.chance import gap_before, poisson_binomial_tail

    t0 = datetime(2026, 9, 17, 22, 0)
    chat = [(t0 - timedelta(minutes=50), "DeepSeek-V3.2"), (t0 - timedelta(minutes=5), "Kimi K3")]
    assert gap_before(t0, chat, "Kimi K3") == timedelta(minutes=50)  # its own message never counts
    assert gap_before(t0, chat, "GPT-5") == timedelta(minutes=5)
    assert gap_before(t0 - timedelta(hours=2), chat, "GPT-5") is None
    assert abs(poisson_binomial_tail([0.5, 0.5], 1) - 0.75) < 1e-12
    assert abs(poisson_binomial_tail([0.1] * 5, 0) - 1.0) < 1e-12


def test_a_scheduled_post_is_a_plan_not_the_belief():
    from heirloom.diff import line_hash
    from heirloom.trail import CASES, stance_of

    case = CASES["forwarddiff-846"]

    def says(line: str) -> str:
        return stance_of(case, {line_hash(line): "affirms"}, line)

    # Only schedules the post: not "it was posted".
    assert says("DeepSeek-V3.2: ForwardDiff.jl Issue #846 posting 1:00-2:00 PM PT (resumed 12:53:58 PM)") == "plan"
    assert says("[NEXT] Paused 1800s, resuming ~12:53:58 PM for 1:00 PM posting to Issue #846") == "plan"
    assert says("EXPANDED to ForwardDiff.jl (Julia), posting to Issue #846 at 1-2 PM PT.") == "plan"
    # Says it happened: still holds the belief.
    assert says("ForwardDiff.jl Issue #846 posting LIVE at 1:00 PM PT (DeepSeek-V3.2)") == "affirms"
    assert says("DeepSeek-V3.2 executed posting at 1:00 PM PT to JuliaDiff/ForwardDiff.jl Issue #846") == "affirms"
    # The time belongs to another post; the line still claims a reply on #846.
    assert says("ForwardDiff.jl Issue #846: 1 maintainer response. brms posting at 1:00 PM PT.") == "affirms"
    # Other cases have no plan rule: a plan to use the 93-person list still holds it.
    assert stance_of(CASES["93-list"], {line_hash("Send the blast to the 93-person list at 1 PM"): "affirms"},
                     "Send the blast to the 93-person list at 1 PM") == "affirms"
