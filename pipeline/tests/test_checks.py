"""The checks that keep labels honest: verified quotes, raw-row matching, live links, the facts arithmetic."""

from datetime import datetime

from heirloom.facts import era
from heirloom.tieout import quote_ok
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


def test_masked_text_is_found_in_the_raw_row():
    raw = "Per [person] and [person], the 93-email list was hallucinated"
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
    assert e["cases"] == ["case-a"] and e["human_corrections"] == 1
