"""Tests for server.brief."""
from __future__ import annotations

import json

import pytest

from server.artifacts import (
    MAX_IMAGES,
    MAX_NODES,
    MAX_POINTS,
    MAX_STATS,
    MAX_TABLE_COLUMNS,
    MAX_TABLE_ROWS,
)
from server.brief import OUTPUT_SCHEMA, TITLE_MAX, build_prompt, derive_title, session_title

DATASETS = [
    {"id": "gdelt", "name": "GDELT events", "url": "https://www.gdeltproject.org"},
    {"id": "yahoo", "name": "Yahoo Finance", "url": "https://finance.yahoo.com"},
]
HYPOTHESIS = "Do tanker attacks lead Brent crude returns?"
REFERENCE = "Prior run: lag 3 days, r=0.42, used GDELT CAMEO 19x counts."


def test_prompt_contains_hypothesis_and_every_dataset():
    prompt = build_prompt(HYPOTHESIS, DATASETS)
    assert HYPOTHESIS in prompt
    for dataset in DATASETS:
        assert dataset["name"] in prompt and dataset["url"] in prompt


def test_prompt_without_datasets_tells_devin_to_find_data():
    prompt = build_prompt(HYPOTHESIS, [])
    assert "No datasets were linked" in prompt


def test_prompt_carries_the_standing_instructions():
    prompt = build_prompt(HYPOTHESIS, DATASETS).lower()
    for phrase in ("think out loud", "structured_output", "artifact", "p-value", "falsify",
                   "null result", "do not end the session", "first person", "no markdown"):
        assert phrase in prompt, phrase


def test_prompt_documents_every_artifact_type_and_limit():
    prompt = build_prompt(HYPOTHESIS, DATASETS)
    for kind in ("chart", "images", "relation", "table", "stats", "image"):
        assert f"`{kind}`" in prompt
    for limit in (MAX_POINTS, MAX_IMAGES, MAX_NODES, MAX_TABLE_ROWS, MAX_TABLE_COLUMNS, MAX_STATS):
        assert str(limit) in prompt
    assert "attachment:<name>" in prompt
    assert "after_step" in prompt


def test_reference_is_included_only_when_given():
    without = build_prompt(HYPOTHESIS, DATASETS)
    assert "private notes" not in without.lower()
    assert "never mention" not in without.lower()

    with_reference = build_prompt(HYPOTHESIS, DATASETS, REFERENCE)
    assert REFERENCE in with_reference
    lowered = with_reference.lower()
    for phrase in ("private notes", "never mention", "as your own", "follow the data", "never adjust"):
        assert phrase in lowered, phrase


@pytest.mark.parametrize("blank", [None, "", "   \n"])
def test_blank_reference_is_treated_as_absent(blank):
    assert build_prompt(HYPOTHESIS, DATASETS, blank) == build_prompt(HYPOTHESIS, DATASETS)


def test_prompt_is_deterministic():
    assert build_prompt(HYPOTHESIS, DATASETS, REFERENCE) == build_prompt(HYPOTHESIS, DATASETS, REFERENCE)


def test_schema_shape():
    json.dumps(OUTPUT_SCHEMA)
    assert OUTPUT_SCHEMA["type"] == "object"
    properties = OUTPUT_SCHEMA["properties"]
    assert set(properties) == {"title", "steps", "artifacts", "conclusion", "needs_user"}
    assert properties["steps"]["items"]["properties"]["state"]["enum"] == ["active", "done"]
    artifact = properties["artifacts"]["items"]
    assert artifact["properties"]["type"]["enum"] == ["chart", "images", "relation", "table", "stats", "image"]
    assert set(artifact["required"]) == {"id", "type", "title"}
    assert "null" in properties["conclusion"]["type"]
    assert "null" in properties["needs_user"]["type"]


@pytest.mark.parametrize("hypothesis, title", [
    ("Do storms predict outages?", "Do storms predict outages"),
    ("Short one...", "Short one"),
    ("  padded!  ", "padded"),
    ("x" * 200, "x" * TITLE_MAX),
    ("Do satellite images of storm damage predict how long power outages last?",
     "Do satellite images of storm damage predict how long power outages last"),
    ("Do satellite images of storm damage across the whole Gulf Coast predict how long outages last?",
     "Do satellite images of storm damage across the whole Gulf Coast predict how long"),
])
def test_derive_title(hypothesis, title):
    assert derive_title(hypothesis) == title
    assert len(derive_title(hypothesis)) <= TITLE_MAX


def test_session_title():
    assert session_title("Storms vs outages") == "Kingdom: Storms vs outages"


def test_schema_and_guide_ask_for_a_short_title():
    assert OUTPUT_SCHEMA["properties"]["title"] == {"type": "string"}
    assert "`title`" in build_prompt("Does A lead B?", [], None)


@pytest.mark.parametrize("phrase", [
    "before you start each step",          # narrate as you go, not in one batch at the end
    "as soon as each step finishes",       # incremental structured output
    "never go more than a couple of minutes",
    "plain text",                          # no markdown emphasis in messages
    "different units",                     # mixed-unit series guidance
    "at most 16 characters",               # short stat values and headlines
])
def test_prompt_demands_a_live_legible_thread(phrase):
    assert phrase in build_prompt("Does A lead B?", [], None)
