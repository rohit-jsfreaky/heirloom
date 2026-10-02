"""People are masked before anything is shown or saved; agents keep their names. Each test here is a leak or an
over-mask we actually hit on the real data (2 Oct 2026)."""

import json

import duckdb
import pytest

from heirloom.privacy import EMAIL, PHONE, Masker, scrub_secrets


@pytest.fixture
def mask() -> Masker:
    con = duckdb.connect()
    con.execute("CREATE TABLE agents (name VARCHAR)")
    con.executemany("INSERT INTO agents VALUES (?)", [("Claude Opus 4",), ("Gemini 2.5 Pro",), ("o3",)])
    con.execute("CREATE TABLE events (action_type VARCHAR, data JSON)")
    talk = [{"speakerName": n} for n in ("only", "Test", "[person]", "Opus", "[person]")]
    con.executemany("INSERT INTO events VALUES ('USER_TALK', ?)", [(json.dumps(d),) for d in talk])
    con.execute("INSERT INTO events VALUES ('USER_NAME_CHANGE', ?)",
                [json.dumps({"oldName": "[person]", "newName": "[person]_k"})])
    return Masker(con)


def test_human_handles_are_masked_in_any_case(mask):
    assert mask("[person] reviewed it; [person] and [person] agreed") == "[person] reviewed it; [person] and [person] agreed"
    assert mask("thanks [person] and [person]_k") == "thanks [person] and [person]"
    assert mask("[person] said so") == "[person] said so"


def test_everyday_word_handles_do_not_eat_the_language(mask):
    # "only" is a chat handle and one of the most common English words: never masked.
    assert mask("only 3 left") == "only 3 left"
    # "Test" is masked only as written, so the word "test" survives.
    assert mask("Test asked for a test") == "[person] asked for a test"


def test_agent_names_and_their_words_are_never_masked(mask):
    assert mask("Claude Opus 4 asked Opus and o3") == "Claude Opus 4 asked Opus and o3"


def test_emails_phones_and_credentials(mask):
    assert mask("write to help@example.org") == "write to [email]"
    assert mask("call 415-555-0134 today") == "call [phone] today"
    assert mask('the password "hunter2!x" failed') == 'the password "[secret]" failed'


def test_scrub_secrets_by_word_and_by_shape():
    assert scrub_secrets("api key: 'abcd1234efgh'") == "api key: '[secret]'"
    assert scrub_secrets("logged in with Pa55w0rd!xyz") == "logged in with [secret]"
    assert scrub_secrets("nothing to hide here, 93 contacts") == "nothing to hide here, 93 contacts"


def test_scrubbing_twice_changes_nothing():
    once = scrub_secrets('secret "The Steering Surface" and password "hunter2!x"')
    assert scrub_secrets(once) == once


def test_patterns_used_by_verify():
    assert EMAIL.search("a.b+c@mail.example.co.uk")
    assert not EMAIL.search("[email]")
    assert PHONE.search("+1 (415) 555-0134")
    assert not PHONE.search("1789589156584")  # a village link timestamp
