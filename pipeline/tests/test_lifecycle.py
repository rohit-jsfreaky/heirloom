"""Snapshot-by-snapshot life of a belief inside one agent, and across the swarm."""

from datetime import datetime, timedelta

from heirloom.lifecycle import episodes, gaps, relapse, state, swarm_returns

T0 = datetime(2025, 6, 10)


def hours(*hs: float) -> list[datetime]:
    return [T0 + timedelta(hours=h) for h in hs]


def test_state_of_one_snapshot():
    assert state({"affirms", "unrelated"}) == "holds"
    assert state({"affirms", "denies"}) == "both"
    assert state({"denies", "doubts"}) == "denies"
    assert state({"doubts"}) == "absent"
    assert state(set()) == "absent"


def test_episodes_count_both_as_holding():
    assert episodes(["absent", "holds", "both", "absent", "holds"]) == [(1, 2), (4, 4)]
    assert episodes(["absent", "denies"]) == []


def test_a_gap_is_a_return_only_after_a_day_away():
    states = ["holds", "absent", "holds", "absent", "absent", "holds"]
    times = hours(0, 1, 2, 3, 20, 30)
    (g,) = gaps(states, times)  # the 1-hour gap is a wobble; the 27-hour one is a return
    assert (g.gone_from, g.back_at, g.denied_between) == (3, 5, False)


def test_return_remembers_a_denial_in_between():
    (g,) = gaps(["holds", "denies", "absent", "holds"], hours(0, 1, 30, 40))
    assert g.denied_between


def test_relapse_needs_a_clean_hold_after_a_denial():
    assert relapse(["holds", "denies", "both", "holds"]) == (1, 3)  # "both" is a correction under way
    assert relapse(["holds", "denies", "both"]) is None
    assert relapse(["holds", "absent", "holds"]) is None


def test_swarm_return_after_nobody_held_it_for_a_day():
    events = [
        (T0, "o3", True),
        (T0 + timedelta(hours=1), "Sonnet", True),
        (T0 + timedelta(hours=2), "o3", False),
        (T0 + timedelta(hours=3), "Sonnet", False),  # nobody holds it from here
        (T0 + timedelta(hours=30), "Sonnet", True),  # back after 27 hours
        (T0 + timedelta(hours=31), "Sonnet", False),
        (T0 + timedelta(hours=32), "o3", True),  # back after 1 hour: not a return
    ]
    assert swarm_returns(events) == [{"gone_from": T0 + timedelta(hours=3), "back_at": T0 + timedelta(hours=30),
                                      "agent": "Sonnet"}]
