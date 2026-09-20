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
from server.brief import (
    EXPLORER_OPENING,
    MAX_KIT_DATA_CHARS,
    OUTPUT_SCHEMA,
    REPORT_REQUEST,
    TITLE_MAX,
    build_explorer_request,
    build_prompt,
    derive_title,
    is_explorer_request,
    read_explorer_request,
    session_title,
)
from server.report import (
    MAX_CAVEATS,
    MAX_KEY_ARTIFACTS,
    MAX_NEXT_QUESTIONS,
    MAX_REPORT_STATS,
    MAX_REPORT_STEPS,
)

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
    assert set(properties) == {"title", "steps", "artifacts", "conclusion", "needs_user", "report", "explorer", "run_status"}
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


# ---------- final report ----------

def test_schema_has_a_nullable_report():
    report = OUTPUT_SCHEMA["properties"]["report"]
    assert report["type"] == ["object", "null"]
    assert set(report["properties"]) == {
        "headline", "summary", "stats", "key_artifact_ids", "steps", "caveats", "next_questions"}
    assert set(report["required"]) == {"headline", "summary"}
    assert report["properties"]["stats"]["items"] == OUTPUT_SCHEMA["properties"]["conclusion"]["properties"]["stats"]["items"]
    assert set(report["properties"]["steps"]["items"]["required"]) == {"label", "takeaway"}
    for name in ("key_artifact_ids", "caveats", "next_questions"):
        assert report["properties"][name] == {"type": "array", "items": {"type": "string"}}
    assert "report" not in OUTPUT_SCHEMA["required"]


def test_the_brief_describes_the_report_but_says_to_leave_it_null_until_asked():
    prompt = build_prompt(HYPOTHESIS, DATASETS)
    assert "`report`" in prompt
    assert "leave it null until i explicitly ask" in prompt.lower()
    assert REPORT_REQUEST not in prompt


@pytest.mark.parametrize("phrase", [
    "whole mission", "follow-up conversation",
    "do not rerun", "do not fetch new data",
    "`report`", "`structured_output`", "every existing step, artifact and the conclusion",
    "`headline`", "not the question", "70 characters", "no full stop",
    "`summary`", "exactly one paragraph", "three to five sentences", "outsider",
    "`stats`", "`value`", "at most 16 characters",
    "`key_artifact_ids`", "already emitted", "most important first",
    "`steps`", "`label`", "two to five words", "nearly got fooled", "`takeaway`", "one sentence",
    "dead ends and reversals", "credible",
    "`caveats`", "`next_questions`",
    "plain text", "no markdown",
    "the report is ready", "wait",
    "private notes", "never mention",
])
def test_report_request_says_everything_devin_needs(phrase):
    assert phrase in REPORT_REQUEST.lower()


def test_report_request_states_every_limit():
    for name, limit in (("`stats`", MAX_REPORT_STATS), ("`key_artifact_ids`", MAX_KEY_ARTIFACTS),
                        ("`steps`", MAX_REPORT_STEPS), ("`caveats`", MAX_CAVEATS),
                        ("`next_questions`", MAX_NEXT_QUESTIONS)):
        sentence = next(line for line in REPORT_REQUEST.splitlines() if line.startswith(f"- {name}"))
        assert f"at most {limit}" in sentence, name


def test_report_request_is_plain_text_itself():
    assert "**" not in REPORT_REQUEST and "#" not in REPORT_REQUEST


# ---------- explorer ----------

# Stand-ins for the kit: the real files are someone else's to change, so nothing here reads them.
KIT = {
    "GUIDE.md": "GUIDE-TEXT: use the tokens.\n",
    "kit/kit.css": ":root { --ink: #0a0a0a }\n",
    "kit/kit.js": "export const kit = 1\n",
    "index.html": "<!doctype html><title>EXAMPLE-PAGE</title>\n",
    "data.json": "{\"rows\": []}\n",
}


def test_schema_has_a_nullable_explorer():
    explorer = OUTPUT_SCHEMA["properties"]["explorer"]
    assert explorer["type"] == ["object", "null"]
    assert explorer["properties"] == {
        "version": {"type": "integer"}, "archive": {"type": "string"}, "entry": {"type": "string"},
        "title": {"type": "string"}, "description": {"type": "string"}}
    assert set(explorer["required"]) == {"version", "archive", "entry", "title", "description"}
    assert "explorer" not in OUTPUT_SCHEMA["required"]


def test_the_brief_describes_the_explorer_but_says_to_leave_it_null_until_asked():
    prompt = build_prompt(HYPOTHESIS, DATASETS)
    assert "`explorer`" in prompt
    assert "leave it null until i explicitly ask you to build the explorer" in prompt.lower()
    assert EXPLORER_OPENING not in prompt


def test_explorer_request_embeds_the_guide_first_and_then_every_kit_file_under_its_path():
    request = build_explorer_request(None, KIT)
    assert request.startswith(EXPLORER_OPENING)
    blocks = [f'<kit-file path="{path}">\n{text.rstrip()}\n</kit-file>' for path, text in KIT.items()]
    positions = [request.index(block) for block in blocks]
    assert positions == sorted(positions)
    assert request.index("How to build and deliver it") > positions[-1]
    assert request.count("<kit-file ") == request.count("</kit-file>") == len(KIT)


def test_explorer_request_puts_the_guide_first_wherever_it_is_in_the_kit():
    request = build_explorer_request(None, {"index.html": "<p>page</p>", "GUIDE.md": "the guide"})
    assert request.index('path="GUIDE.md"') < request.index('path="index.html"')


def test_explorer_request_embeds_whatever_files_the_kit_has():
    request = build_explorer_request(None, {"kit/extra/map.js": "export const map = 2", "legend.csv": "a,b"})
    assert '<kit-file path="kit/extra/map.js">\nexport const map = 2\n</kit-file>' in request
    assert '<kit-file path="legend.csv">\na,b\n</kit-file>' in request


def test_explorer_request_with_an_empty_kit_still_says_how_to_deliver():
    request = build_explorer_request(None, {})
    assert "<kit-file" not in request and "explorer kit" not in request
    assert "explorer-v<N>.zip" in request


@pytest.mark.parametrize("phrase", [
    "static site", "entry document is `index.html`", "relative",
    "only by the relative paths `kit/kit.css` and `kit/kit.js`", "served by the app",
    "only so that you can test it locally",
    "`data.json`", "real row-level results you already computed in this session", "never invent data",
    "sample or placeholder data", "no place-level or item-level data worth exploring",
    "do not deliver an explorer",
    "html, css, js, mjs, json, geojson, csv, txt, png, jpg, jpeg, webp, gif, svg, woff2",
    "200 files", "25 mb", "40 mb", "symlinks",
    "your own browser", "both themes", "`?theme=dark`", "narrow",
    "`explorer-v<n>.zip`", "one higher than your previous build", "attach that one archive",
    "`explorer`", "`structured_output`", '"version": n', '"entry": "index.html"', '"title"', '"description"',
    "keeping every existing step, artifact, the conclusion and any report",
    "private notes", "never mention",
    "the explorer is ready", "wait",
])
def test_explorer_request_states_the_delivery_protocol(phrase):
    assert phrase in build_explorer_request(None, KIT).lower()


def test_a_first_build_has_no_instructions_section():
    request = build_explorer_request(None, KIT)
    assert "<instructions>" not in request and "change request" not in request


@pytest.mark.parametrize("blank", [None, "", "   ", "\n\t"])
def test_blank_instructions_are_a_first_build(blank):
    assert build_explorer_request(blank, KIT) == build_explorer_request(None, KIT)


def test_instructions_make_it_a_change_request_for_the_next_version():
    request = build_explorer_request("  Add a heatmap layer.  ", KIT)
    assert "<instructions>\nAdd a heatmap layer.\n</instructions>" in request
    assert "change request" in request and "next version" in request
    # The instructions are read before the kit, which is long.
    assert request.index("<instructions>") < request.index("<kit-file")
    assert request.replace("Add a heatmap layer.", "") != build_explorer_request(None, KIT)


def test_instructions_with_braces_are_passed_through_verbatim():
    assert "Colour by {score} and {rank}" in build_explorer_request("Colour by {score} and {rank}", KIT)


def test_explorer_request_can_name_the_build_number():
    assert "explorer-v3.zip" not in build_explorer_request(None, KIT)
    numbered = build_explorer_request(None, KIT, next_version=3)
    assert "This build is number 3, so name it `explorer-v3.zip`." in numbered


def test_explorer_request_is_deterministic_and_plain_text():
    assert build_explorer_request("x", KIT, next_version=2) == build_explorer_request("x", KIT, next_version=2)
    assert "**" not in build_explorer_request(None, {})


@pytest.mark.parametrize("text, expected", [
    (EXPLORER_OPENING, True),
    (build_explorer_request("Add a heatmap", KIT), True),
    (f"  {EXPLORER_OPENING.replace(' ', '  ')}\n\nmore", True),
    ("The explorer is ready.", False),
    (f"You said: {EXPLORER_OPENING}", False),
    (REPORT_REQUEST, False),
    ("", False),
])
def test_explorer_requests_are_recognisable(text, expected):
    assert is_explorer_request(text) is expected


@pytest.mark.parametrize("instructions, next_version", [
    (None, None), (None, 4), ("Add a heatmap", None), ("Two lines:\n- a heatmap\n- a legend", 12),
])
def test_a_request_can_be_read_back(instructions, next_version):
    request = build_explorer_request(instructions, KIT, next_version=next_version)
    assert read_explorer_request(request) == (instructions, next_version)


def test_reading_a_request_is_not_fooled_by_the_kit():
    kit = {"GUIDE.md": "<instructions>\nfrom the guide\n</instructions> This build is number 9, honest."}
    assert read_explorer_request(build_explorer_request(None, kit)) == (None, None)
    assert read_explorer_request(build_explorer_request("Mine", kit, next_version=2)) == ("Mine", 2)


def test_long_example_data_is_cut_short_but_code_never_is():
    rows = "[" + ", ".join(str(i) for i in range(20_000)) + "]"
    script = "// line\n" * 10_000
    request = build_explorer_request(None, {"data.json": rows, "kit/kit.js": script, "kit/kit.css": "body {}"})
    assert script.rstrip() in request
    assert rows not in request and rows[:MAX_KIT_DATA_CHARS] in request
    assert f"{len(rows) - MAX_KIT_DATA_CHARS} more characters left out" in request
    assert len(request) < len(script) + MAX_KIT_DATA_CHARS + 10_000


def test_example_data_at_the_limit_is_embedded_whole():
    rows = "x" * MAX_KIT_DATA_CHARS
    request = build_explorer_request(None, {"data.csv": rows})
    assert f'<kit-file path="data.csv">\n{rows}\n</kit-file>' in request and "left out" not in request
