"""Prompt tests - message structure sent to the LLM."""

import pytest

from backend.core.prompts import (
    DEFAULT_LENGTH,
    FINAL_MAX_TOKENS,
    LENGTH_SPECS,
    chunk_prompt,
    combine_prompt,
    final_max_tokens,
    final_prompt,
    length_spec,
)


def test_all_lengths_have_specs_and_tokens():
    assert set(LENGTH_SPECS) == {"short", "standard", "long", "xl"}
    assert set(FINAL_MAX_TOKENS) == set(LENGTH_SPECS)
    for length in LENGTH_SPECS:
        assert length_spec(length) in LENGTH_SPECS.values()
        assert final_max_tokens(length) > 0


@pytest.mark.parametrize("length", ["short", "standard", "long", "xl"])
def test_final_max_tokens_grow_with_length(length):
    order = ["short", "standard", "long", "xl"]
    idx = order.index(length)
    assert FINAL_MAX_TOKENS[length] == final_max_tokens(length)
    if idx > 0:
        assert FINAL_MAX_TOKENS[length] > FINAL_MAX_TOKENS[order[idx - 1]]


def test_unknown_length_falls_back_to_default():
    assert length_spec("nieznane") == LENGTH_SPECS[DEFAULT_LENGTH]
    assert final_max_tokens("nieznane") == FINAL_MAX_TOKENS[DEFAULT_LENGTH]


def test_chunk_prompt_structure():
    messages = chunk_prompt("raport.pdf", 2, 5, "treść fragmentu")

    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert "2/5" in messages[1]["content"]
    assert "treść fragmentu" in messages[1]["content"]
    assert "raport.pdf" in messages[1]["content"]


def test_final_prompt_structure():
    messages = final_prompt(
        "raport.pdf", "MATERIAŁ", lang="pl", length="standard", multi=False
    )

    assert messages[0]["role"] == "system"
    assert "Polish" in messages[0]["content"]
    user = messages[1]["content"]
    assert "raport.pdf" in user
    assert LENGTH_SPECS["standard"] in user
    assert "## W skrócie" in user
    assert "MATERIAŁ" in user
    assert "combined from multiple files" not in user


def test_final_prompt_multi_flag():
    messages = final_prompt("a.txt", "X", lang="pl", length="short", multi=True)
    assert "combined from multiple files" in messages[1]["content"]


def test_final_prompt_language():
    messages = final_prompt("a.txt", "X", lang="en", length="xl", multi=False)
    assert "English" in messages[0]["content"]


def test_combine_prompt_joins_partials():
    messages = combine_prompt(
        "raport.pdf", ["część pierwsza", "część druga"], lang="pl", length="long"
    )

    user = messages[1]["content"]
    assert "### Part 1/2" in user
    assert "część pierwsza" in user
    assert "### Part 2/2" in user
    assert "część druga" in user
    assert "coherent summary" in user
