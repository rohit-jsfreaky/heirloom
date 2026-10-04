"""Whole-village numbers (no model): copies, chat timing against the strict null, memory lifetime."""

from datetime import datetime, timedelta
from types import SimpleNamespace

from heirloom.population import copies_of, gap_before, lifetime, summarize

T0 = datetime(2025, 6, 1, 12)


def at(minutes: float) -> datetime:
    return T0 + timedelta(minutes=minutes)


def test_lifetime_sees_gone_and_back():
    times = [at(m) for m in range(6)]
    life = lifetime(times, [at(1), at(2), at(4)], at(1))
    assert life["gaps"] == [{"gone": at(3), "back": at(4)}]  # gone at a later rewrite, then back
    assert not life["held_at_end"]  # gone again by the agent's last snapshot
    assert life["last_held"] == at(4)
    kept = lifetime(times, times[2:], at(2))
    assert kept["gaps"] == [] and kept["held_at_end"] and kept["last_held"] == at(5)


def test_gap_counts_only_messages_before_the_copy():
    others = [at(0), at(30), at(90)]
    assert gap_before(at(45), others) == timedelta(minutes=15)
    assert gap_before(at(30), others) == timedelta(minutes=30)  # a message at the same moment is not "before"
    assert gap_before(at(-5), others) is None


def test_a_copy_is_the_same_fact_taken_up_after_birth():
    line = "Contact list: 93 contacts in the RESONANCE sheet"
    b = SimpleNamespace(line=line, born={"agent": "o3", "at": at(0)}, believers=[
        {"agent": "o3", "first_at": at(0), "first_line": line},
        {"agent": "Claude Opus 4", "first_at": at(10), "first_line": "RESONANCE sheet has 93 contacts (from o3)"},
        {"agent": "GPT-4.1", "first_at": at(20), "first_line": "Lunch budget: 93 contacts? no, $93 for snacks today"},
        {"agent": "Gemini 2.5 Pro", "first_at": at(-60), "first_line": line},  # had it before the birth
    ])
    assert [x["agent"] for x in copies_of(b)] == ["Claude Opus 4"]


def test_summary_counts_and_strict_null():
    copies = [
        {"belief": "b1", "agent": "x", "within": True, "gap_minutes": 5.0, "p_null_own_writes": 0.1},
        {"belief": "b1", "agent": "y", "within": False, "gap_minutes": None, "p_null_own_writes": 0.1},
        {"belief": "b2", "agent": "x", "within": True, "gap_minutes": 30.0, "p_null_own_writes": 0.2},
    ]
    holdings = [
        {"copy": False, "gaps": [], "held_at_end": True, "days_held": 3.0},
        {"copy": True, "gaps": [{"hours": 5.0, "same_fact": True}], "held_at_end": True, "days_held": 1.0},
        {"copy": True, "gaps": [{"hours": 0.1, "same_fact": True}], "held_at_end": False, "days_held": 0.5},  # flicker
        {"copy": True, "gaps": [{"hours": 9.0, "same_fact": False}], "held_at_end": False, "days_held": 1.5},
    ]
    s = summarize(4, copies, holdings)
    assert s["spread"] == {"beliefs": 2, "pct": 50.0, "copies": 3, "mean_other_agents": 1.5, "max_other_agents": 2}
    t = s["chat_timing"]
    assert (t["within_gap"], t["expected_own_writes"], t["no_chat_before"]) == (2, 0.4, 1)
    # P(at least 2 of 3) with p = 0.1, 0.1, 0.2
    assert abs(t["p_value_own_writes"] - (0.1 * 0.1 * 0.8 + 2 * 0.1 * 0.9 * 0.2 + 0.1 * 0.1 * 0.2)) < 1e-12
    life = s["lifetime"]
    assert (life["gone"], life["gone_for_good"], life["came_back"], life["flickers_or_other_lines"]) == (3, 2, 1, 2)
    assert life["median_hours_held"] == 30.0 and life["held_over_a_day_pct"] == 50.0
    assert (life["copies"], life["copies_gone_for_good_pct"], life["copies_came_back"]) == (3, 66.7, 1)


def test_verify_catches_a_doctored_number_or_extra_text():
    from heirloom.verify import Check, _check_population

    copies = [{"belief": "b1", "agent": "x", "first_held": "2025-06-01 12:10:00", "gap_minutes": 5.0, "within": True,
               "p_null_own_writes": 0.25, "own_writes": 4}]
    holdings = [{"belief": "b1", "agent": "x", "copy": True, "first": "2025-06-01 12:10:00",
                 "last_held": "2025-06-02 12:10:00", "days_held": 1.0, "held_at_end": False,
                 "agent_last_snapshot": "2025-07-01 00:00:00", "gaps": []}]
    good = {"gap_minutes": 60.0, "copies": copies, "holdings": holdings, "summary": summarize(1, copies, holdings)}
    c = Check("t")
    _check_population(c, good)
    assert c.passed
    doctored = good | {"summary": good["summary"] | {"chat_timing": good["summary"]["chat_timing"] | {"within_gap": 9}}}
    c = Check("t")
    _check_population(c, doctored)
    assert not c.passed
    leaky = good | {"copies": [copies[0] | {"line": "memory text"}]}
    c = Check("t")
    _check_population(c, leaky)
    assert not c.passed
