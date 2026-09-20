"""Tests for server.report: Devin's snake_case report to the app's camelCase `Report`."""
from __future__ import annotations

import pytest

from server.report import (
    MAX_CAVEATS,
    MAX_KEY_ARTIFACTS,
    MAX_NEXT_QUESTIONS,
    MAX_REPORT_STATS,
    MAX_REPORT_STEPS,
    normalise_report,
)

KNOWN = {"a1", "a2", "a3", "a4", "a5"}


def _raw(**over):
    raw = {
        "headline": "Storm damage predicts outage length",
        "summary": "We asked whether damage predicts outages. It does, modestly.",
        "stats": [{"label": "Correlation", "value": "0.58"}],
        "key_artifact_ids": ["a5", "a2"],
        "steps": [{"label": "Read the data", "takeaway": "One tile in ten was unusable."}],
        "caveats": ["One region drives the extremes."],
        "next_questions": ["Does it hold next quarter?"],
    }
    raw.update(over)
    return raw


def test_well_formed_report_becomes_camel_case():
    assert normalise_report(_raw(), KNOWN) == {
        "headline": "Storm damage predicts outage length",
        "summary": "We asked whether damage predicts outages. It does, modestly.",
        "stats": [{"label": "Correlation", "value": "0.58"}],
        "keyArtifactIds": ["a5", "a2"],
        "steps": [{"label": "Read the data", "takeaway": "One tile in ten was unusable."}],
        "caveats": ["One region drives the extremes."],
        "nextQuestions": ["Does it hold next quarter?"],
    }


def test_only_headline_and_summary_are_required():
    assert normalise_report({"headline": "A leads B", "summary": "It does."}, KNOWN) == {
        "headline": "A leads B", "summary": "It does.", "stats": [], "keyArtifactIds": [], "steps": [],
        "caveats": [], "nextQuestions": [],
    }


@pytest.mark.parametrize("raw", [
    None, "report", 7, [], ["headline"], {},
    {"headline": "No summary"}, {"summary": "No headline."},
    {"headline": "", "summary": "x"}, {"headline": "  \n", "summary": "x"}, {"headline": "x", "summary": "  "},
    {"headline": 3, "summary": "x"}, {"headline": "x", "summary": ["x"]}, {"headline": None, "summary": None},
    {"headline": " . ", "summary": "Only a full stop for a headline."},
])
def test_without_a_headline_and_summary_there_is_no_report(raw):
    assert normalise_report(raw, KNOWN) is None


@pytest.mark.parametrize("headline, expected", [
    ("  A leads B by a week \n", "A leads B by a week"),
    ("A leads B by a week.", "A leads B by a week"),
    ("A leads B by a week. ", "A leads B by a week"),
    ("A leads\n  B by a week", "A leads B by a week"),
    ("r = 0.58 at lag 1", "r = 0.58 at lag 1"),
    ("Does A lead B?", "Does A lead B?"),
])
def test_headline_is_one_trimmed_line_without_a_trailing_full_stop(headline, expected):
    assert normalise_report(_raw(headline=headline), KNOWN)["headline"] == expected


def test_summary_is_folded_into_one_paragraph():
    report = normalise_report(_raw(summary="  First part.\n\nSecond part.  "), KNOWN)
    assert report["summary"] == "First part. Second part."


def test_stats_are_coerced_like_artifact_stats_and_capped():
    stats = [{"label": " n ", "value": 412}, {"label": "r", "value": 0.58}, {"label": "", "value": "x"},
             {"label": "blank", "value": None}, "junk", {"label": "p", "value": " 0.003 "},
             {"label": "Lag", "value": "1 week"}, {"label": "Fifth", "value": "5"}]
    assert normalise_report(_raw(stats=stats), KNOWN)["stats"] == [
        {"label": "n", "value": "412"}, {"label": "r", "value": "0.58"}, {"label": "p", "value": "0.003"},
        {"label": "Lag", "value": "1 week"}]
    assert MAX_REPORT_STATS == 4


def test_key_artifacts_must_be_known_and_unique_and_keep_their_order():
    ids = ["ghost", " a3 ", "a1", "a3", 7, None, "", "a2", "a4"]
    assert normalise_report(_raw(key_artifact_ids=ids), KNOWN)["keyArtifactIds"] == ["a3", "a1", "a2"]
    assert MAX_KEY_ARTIFACTS == 3


def test_unknown_artifacts_do_not_use_up_the_limit():
    ids = ["x1", "x2", "x3", "a1"]
    assert normalise_report(_raw(key_artifact_ids=ids), KNOWN)["keyArtifactIds"] == ["a1"]


def test_no_artifacts_are_known_by_default():
    assert normalise_report(_raw(), ())["keyArtifactIds"] == []


def test_steps_need_a_label_and_are_capped():
    steps = [{"label": " Read the data ", "takeaway": " Messy.\n"}, {"label": "", "takeaway": "No label"},
             {"takeaway": "No label"}, "junk", None, {"label": "No takeaway"}, {"label": 4, "takeaway": "x"},
             {"label": "Odd takeaway", "takeaway": ["x"]}]
    assert normalise_report(_raw(steps=steps), KNOWN)["steps"] == [
        {"label": "Read the data", "takeaway": "Messy."}, {"label": "No takeaway", "takeaway": ""},
        {"label": "Odd takeaway", "takeaway": ""}]

    many = [{"label": f"Step {i}", "takeaway": "x"} for i in range(12)]
    capped = normalise_report(_raw(steps=many), KNOWN)["steps"]
    assert [s["label"] for s in capped] == [f"Step {i}" for i in range(MAX_REPORT_STEPS)]
    assert MAX_REPORT_STEPS == 8


@pytest.mark.parametrize("field, key, limit", [
    ("caveats", "caveats", MAX_CAVEATS),
    ("next_questions", "nextQuestions", MAX_NEXT_QUESTIONS),
])
def test_sentence_lists_drop_blanks_and_are_capped(field, key, limit):
    raw = ["  First. ", "", "   ", None, 5, {"text": "x"}, "Second.", "Third.", "Fourth.", "Fifth."]
    assert normalise_report(_raw(**{field: raw}), KNOWN)[key] == ["First.", "Second.", "Third.", "Fourth.", "Fifth."][:limit]
    assert (MAX_CAVEATS, MAX_NEXT_QUESTIONS) == (4, 3)


@pytest.mark.parametrize("junk", [None, "text", 7, {"a": 1}, [[1, 2], [3]], [{"label": {"deep": []}, "value": [1]}]])
def test_garbage_in_the_lists_never_raises(junk):
    report = normalise_report(
        _raw(stats=junk, key_artifact_ids=junk, steps=junk, caveats=junk, next_questions=junk), KNOWN)
    assert report["headline"] == "Storm damage predicts outage length"
    assert report["keyArtifactIds"] == [] and report["steps"] == []
    assert report["caveats"] == [] and report["nextQuestions"] == []


def test_unhashable_artifact_ids_are_dropped():
    assert normalise_report(_raw(key_artifact_ids=[["a1"], {"id": "a1"}, "a1"]), KNOWN)["keyArtifactIds"] == ["a1"]


def test_unknown_fields_are_dropped_and_the_input_is_left_alone():
    raw = _raw(generated_at="yesterday", generatedAt="yesterday", author="Devin")
    frozen = repr(raw)
    assert set(normalise_report(raw, KNOWN)) == {
        "headline", "summary", "stats", "keyArtifactIds", "steps", "caveats", "nextQuestions"}
    assert repr(raw) == frozen
