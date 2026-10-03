"""People are masked before anything is shown or saved; agents keep their names. Each test here is a leak or an
over-mask we actually hit on the real data (2 Oct 2026)."""

import json

import duckdb
import pytest

from heirloom.privacy import EMAIL, PHONE, Masker, scrub_secrets


def _village(chat: list[str] | None) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute("CREATE TABLE agents (name VARCHAR)")
    con.executemany("INSERT INTO agents VALUES (?)", [("Claude Opus 4",), ("Gemini 2.5 Pro",), ("o3",)])
    con.execute("CREATE TABLE events (action_type VARCHAR, data JSON)")
    talk = [{"speakerName": n} for n in ("only", "Test", "Victor", "Opus", "ZORVEX", "Harbor")]
    con.executemany("INSERT INTO events VALUES ('USER_TALK', ?)", [(json.dumps(d),) for d in talk])
    con.execute("INSERT INTO events VALUES ('USER_NAME_CHANGE', ?)",
                [json.dumps({"oldName": "Tamsin", "newName": "tamsin_q"})])
    if chat is not None:
        # How the agents write these words decides word vs name: "harbor", "test", "only" mostly lowercase (words),
        # "Victor" capitalised (a name).
        con.execute("CREATE TABLE chat_messages (content VARCHAR)")
        con.executemany("INSERT INTO chat_messages VALUES (?)", [(c,) for c in chat])
    return con


CHAT = ["the harbor drive raised $1,984", "money for harbor", "a harbor event", "Victor said hi", "ask Victor",
        "thanks victor", "Victor is here", "run the test", "test passed", "only 3 left", "only one"]


@pytest.fixture
def mask() -> Masker:
    return Masker(_village(CHAT))


def test_a_handle_that_is_an_everyday_word_is_masked_only_where_it_is_a_name(mask):
    assert mask("the harbor money went to malaria nets") == "the harbor money went to malaria nets"
    assert mask("thanks @harbor") == "thanks @[person]"
    assert mask("harbor: can you check?") == "[person]: can you check?"
    assert mask("Harbor asked; HARBOR agreed") == "[person] asked; [person] agreed"  # as the handle is written


def test_without_chat_to_tell_word_from_name_every_handle_is_masked():
    # Privacy wins ties: no evidence that "harbor" is a word here, so it is treated as a name.
    assert Masker(_village(None))("the harbor money") == "the [person] money"


def test_human_handles_are_masked_in_any_case(mask):
    assert mask("Victor reviewed it; victor and VICTOR agreed") == "[person] reviewed it; [person] and [person] agreed"
    assert mask("thanks Tamsin and tamsin_q") == "thanks [person] and [person]"
    assert mask("ZORVEX said so") == "[person] said so"


def test_everyday_word_handles_do_not_eat_the_language(mask):
    # "only" is a chat handle and one of the most common English words: never masked.
    assert mask("only 3 left") == "only 3 left"
    # "Test" is masked only as written, so the word "test" survives.
    assert mask("Test asked for a test") == "[person] asked for a test"


class _FindsFullName:
    """Stands in for the model: like the real call on 3 Oct, it lists only the full name."""
    cheap = "cheap"

    def structured(self, model, system, user, schema, effort="low"):
        return schema(names=["Dana Whitlock", "Claude Opus 4"])


def test_a_full_name_found_once_is_masked_by_each_part_too(mask):
    mask.add_people(_FindsFullName(), ["Dana Whitlock wrote back", "I emailed Dana; Opus too"])
    assert mask("I emailed Dana; DANA replied") == "I emailed [person]; [person] replied"
    assert mask("Dana Whitlock wrote back") == "[person] wrote back"
    assert mask("Claude Opus 4 asked Opus") == "Claude Opus 4 asked Opus"  # an agent's name, never its parts


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
