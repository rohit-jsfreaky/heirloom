"""Line diff and anchors: what makes a memory line a new, checkable belief."""

from heirloom.diff import anchors, body_of, diff, lines_in_context, normalize, search_terms, strong


def test_count_keeps_its_unit_singular():
    assert anchors("Send the invite to all 93 contacts on the list") == {"93 contact"}


def test_money_and_scores_are_strong_anchors():
    assert anchors("Budget: $1,984") == {"$1,984"}
    assert anchors("Passed 8/8 tests") == {"8/8 test"}
    assert all(strong(a) for a in anchors("Budget: $1,984 and 8/8 tests"))


def test_dates_times_and_model_names_are_never_anchors():
    assert anchors("Meeting on 6/13 at 3:00 PM") == frozenset()
    assert anchors("Claude 3.7 Sonnet and Gemini 2.5 Pro agree") == frozenset()


def test_a_commit_hash_is_not_read_as_a_count():
    # "7fa9a37" must not become "7 fa"
    assert not any(a.startswith("7 ") for a in anchors("Commit 7fa9a37 pushed"))


def test_ids_urls_and_quoted_names_are_kept_whole():
    assert anchors("id a8e7d3f9c2b14e7d9 saved") == {"a8e7d3f9c2b14e7d9"}
    assert anchors("see https://example.com/a?b=1.") == {"https://example.com/a?b=1"}
    assert anchors('The "Resonance Mailing List" is ready') == {"resonance mailing list"}


def test_one_word_button_labels_are_not_facts():
    assert anchors('Click "Next"') == frozenset()


def test_weak_anchors_never_make_a_line_new_on_their_own():
    assert anchors("Took 5 minutes") == {"#5 minute"}
    assert not strong("#5 minute")
    assert not strong("ops@agentvillage.org")  # every agent's own village address
    assert strong("93 contact")


def test_search_terms_also_find_the_bare_number():
    assert search_terms("93 contact") == ["93 contact", "93"]
    assert search_terms("#93") == ["93"]
    assert search_terms("$1,984") == ["$1,984"]


def test_normalize_strips_bullets_and_markdown_only():
    assert normalize("  - **Budget**:   $600  ") == "Budget: $600"
    assert normalize("1. First item") == "First item"
    assert normalize("## Heading") == "Heading"


def test_lines_carry_their_section_heading():
    content = "## Notes\n- a line here\nTECH STATUS:\n* another line\n---\n[x] done task"
    assert lines_in_context(content) == ["[Notes] a line here", "[TECH STATUS] another line",
                                         "[TECH STATUS] [x] done task"]
    assert body_of("[TECH STATUS] [x] done task") == "[x] done task"
    assert body_of("plain line") == "plain line"


def test_diff_sorts_lines_into_added_changed_reworded_vanished():
    old = "a line one\nkeep this line\nold count is 12 apples\nwill vanish soon"
    new = "keep this line\nold count is 13 apples\nbrand new line\na line one!"
    d = diff(old, new)
    assert d.added == ["brand new line"]
    assert [(c.old, c.new) for c in d.changed] == [("old count is 12 apples", "old count is 13 apples")]
    assert [(c.old, c.new) for c in d.reworded] == [("a line one", "a line one!")]
    assert d.vanished == ["will vanish soon"]
    assert d.candidates == ["brand new line", "old count is 13 apples"]
    assert not d.compression


def test_a_much_shorter_rewrite_is_a_compression():
    assert diff("x" * 1000 + "\nline b", "line b").compression


def test_first_snapshot_has_everything_added():
    d = diff(None, "first line\nsecond line")
    assert d.added == ["first line", "second line"] and not d.vanished
