"""Tests for check_claim: how it searches, cites sources and handles bad model output."""

import main
from fakes import FakeOpenAI, FakeTavily, result, search_reply, tool_reply, verdict_reply


def run(replies, results_per_search=(), repeat_last=False):
    openai = FakeOpenAI(replies, repeat_last=repeat_last)
    tavily = FakeTavily(results_per_search)
    answer = main.check_claim(openai, tavily, "Some claim about hantavirus")
    return answer, openai, tavily


# --- citations ---------------------------------------------------------------

def test_cites_only_the_sources_the_model_picked():
    answer, _, _ = run(
        [search_reply(), verdict_reply("TRUE", source_ids=[1, 3])],
        [[result(1), result(2), result(3)]],
    )
    assert answer["verdict"] == "TRUE"
    assert answer["sources"] == [
        {"title": "Page 1", "url": "https://www.cdc.gov/page1"},
        {"title": "Page 3", "url": "https://www.cdc.gov/page3"},
    ]


def test_ignores_source_ids_that_do_not_exist():
    # 0, 3 (one past the end), 99 and -1 are out of range, "1" is a string, True is a bool
    # pretending to be 1, and the second 2 is a duplicate. Only source 2 should survive, once.
    answer, _, _ = run(
        [search_reply(), verdict_reply(source_ids=[0, 3, 99, -1, "1", True, 2, 2])],
        [[result(1), result(2)]],
    )
    assert [s["url"] for s in answer["sources"]] == ["https://www.cdc.gov/page2"]


def test_source_numbers_continue_across_searches():
    # First search finds pages 1-2, second finds page 3, so page 3 is source number 3.
    answer, _, _ = run(
        [search_reply("first"), search_reply("second"), verdict_reply(source_ids=[3])],
        [[result(1), result(2)], [result(3)]],
    )
    assert [s["url"] for s in answer["sources"]] == ["https://www.cdc.gov/page3"]


def test_search_results_are_numbered_for_the_model():
    _, openai, _ = run([search_reply(), verdict_reply()], [[result(1), result(2)]])
    tool_message = [m for m in openai.requests[-1]["messages"] if isinstance(m, dict) and m["role"] == "tool"][0]
    assert tool_message["content"].startswith("[1] Page 1 (https://www.cdc.gov/page1)")
    assert "[2] Page 2" in tool_message["content"]


# --- verdicts ----------------------------------------------------------------

def test_verdict_is_case_insensitive():
    answer, _, _ = run([search_reply(), verdict_reply("false")], [[result(1)]])
    assert answer["verdict"] == "FALSE"


def test_unknown_verdict_becomes_insufficient_evidence():
    answer, _, _ = run([search_reply(), verdict_reply("MAYBE")], [[result(1)]])
    assert answer["verdict"] == "INSUFFICIENT_EVIDENCE"


def test_answering_without_any_search_is_insufficient_evidence():
    answer, _, tavily = run([verdict_reply("TRUE", source_ids=[1])])
    assert answer["verdict"] == "INSUFFICIENT_EVIDENCE"
    assert answer["sources"] == []
    assert tavily.searches == []


def test_search_with_no_results_cannot_produce_a_verdict_with_sources():
    answer, _, _ = run([search_reply(), verdict_reply("TRUE", source_ids=[1])], [[]])
    assert answer["verdict"] == "INSUFFICIENT_EVIDENCE"
    assert answer["sources"] == []


# --- searching ---------------------------------------------------------------

def test_searches_only_cdc_and_who():
    _, _, tavily = run([search_reply("rodent droppings"), verdict_reply()], [[result(1)]])
    sent = tavily.searches[0]
    assert sent["include_domains"] == ["cdc.gov", "who.int"]
    assert sent["query"] == "rodent droppings"
    assert sent["search_depth"] == "basic"
    assert sent["timeout"] == main.REQUEST_TIMEOUT


def test_search_budget_forces_an_answer():
    replies = [search_reply()] * main.MAX_SEARCHES + [verdict_reply(source_ids=[1])]
    answer, openai, tavily = run(replies, [[result(1)]] * main.MAX_SEARCHES)
    assert len(tavily.searches) == main.MAX_SEARCHES
    assert [r["tool_choice"] for r in openai.requests[:-1]] == ["required"] * main.MAX_SEARCHES
    assert openai.requests[-1]["tool_choice"]["function"]["name"] == "submit_verdict"
    assert answer["sources"]


# --- bad model output --------------------------------------------------------

def test_recovers_from_malformed_json():
    answer, openai, _ = run(
        [tool_reply("search_trusted_sources", '{"query": "han'), search_reply(), verdict_reply(source_ids=[1])],
        [[result(1)]],
    )
    assert answer["verdict"] == "TRUE"
    error = [m for m in openai.requests[-1]["messages"] if isinstance(m, dict) and m["role"] == "tool"][0]
    assert "not valid JSON" in error["content"]


def test_recovers_when_arguments_are_not_a_json_object():
    answer, _, _ = run(
        [tool_reply("search_trusted_sources", "[1, 2]"), search_reply(), verdict_reply(source_ids=[1])],
        [[result(1)]],
    )
    assert answer["verdict"] == "TRUE"


def test_gives_up_when_the_model_never_produces_valid_json():
    answer, openai, _ = run([tool_reply("search_trusted_sources", "{bad")], repeat_last=True)
    assert answer["verdict"] == "INSUFFICIENT_EVIDENCE"
    assert len(openai.requests) == main.MAX_STEPS


def test_reply_without_a_tool_call_is_insufficient_evidence():
    from types import SimpleNamespace
    answer, _, _ = run([SimpleNamespace(tool_calls=None)])
    assert answer["verdict"] == "INSUFFICIENT_EVIDENCE"
