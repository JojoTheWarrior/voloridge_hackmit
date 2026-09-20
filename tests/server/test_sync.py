"""Tests for server.sync: a pure function from (stored state, Devin snapshot) to thread changes."""
from __future__ import annotations

import dataclasses
from datetime import datetime, timedelta

import pytest

from server.brief import REPORT_REQUEST
from server.devin import Attachment, DevinMessage, SessionSnapshot
from server.store import Store
from server.sync import REPORT_MISSING, REPORT_TIMEOUT_SECONDS, SyncResult, sync

NOW = "2026-09-20T13:00:00Z"
# The store's clock, fixed a little before NOW so a report requested through it is not yet overdue.
STORED_AT = "2026-09-20T12:58:00Z"
PROMPT = "You are a research analyst.\n\nThe question:\nDo storms predict outages?"


@pytest.fixture
def store(tmp_path):
    return Store(tmp_path / "k.db", now=lambda: STORED_AT)


@pytest.fixture
def mission(store):
    row = store.create_mission(
        "Do storms predict outages?", title="Storms", dataset_ids=[], reference=None, prompt=PROMPT)
    store.set_session(row.id, "devin-abc", None)
    store.append_event(row.id, "user_message", {"text": "Do storms predict outages?"}, event_id="user:first")
    return store.get_mission(row.id)


def _snapshot(output=None, status="running", detail=None):
    return SessionSnapshot(status, detail, output)


def _output(steps=(), artifacts=(), conclusion=None, needs_user=None, title=None, report=None):
    return {"title": title, "steps": list(steps), "artifacts": list(artifacts), "conclusion": conclusion,
            "needs_user": needs_user, "report": report}


def _step(step_id, state="done", label=None):
    return {"id": step_id, "label": label or f"Step {step_id}", "state": state}


def _stats(artifact_id, after_step=None, value="1"):
    return {"id": artifact_id, "after_step": after_step, "type": "stats", "title": f"Stats {artifact_id}",
            "items": [{"label": "n", "value": value}]}


def _devin(message_id, text, at="2026-09-20T12:59:00Z"):
    return DevinMessage(message_id, "devin", text, at)


CONCLUSION = {"verdict": "A modest link.", "summary": "r = 0.58 at one week.",
              "stats": [{"label": "Correlation", "value": 0.58}]}


def _run(store, mission_id, snapshot, messages=(), attachments=(), now=NOW) -> SyncResult:
    """Sync against what is stored and persist the result, as the poller does."""
    row = store.get_mission(mission_id)
    result = sync(row, store.list_events(mission_id), snapshot, list(messages), list(attachments), now=now)
    store.apply_sync(mission_id, result, expected_status=row.status)
    return result


def _event(store, mission_id, event_id):
    return next(event for event in store.list_events(mission_id) if event["id"] == event_id)


def _thread(store, mission_id):
    return [event["id"] for event in store.list_events(mission_id)]


# ---------- first sync, idempotence ----------

def test_first_sync_builds_the_thread(store, mission):
    snapshot = _snapshot(_output(
        steps=[_step("s1"), _step("s2", "active")],
        artifacts=[_stats("a1", "s1")],
    ))
    result = _run(store, mission.id, snapshot, [_devin("m1", "Reading the data")])

    assert _thread(store, mission.id) == ["user:first", "msg:m1", "step:s1", "artifact:a1", "step:s2"]
    events = {e["id"]: e for e in store.list_events(mission.id)}
    assert events["step:s1"] == {"id": "step:s1", "at": NOW, "kind": "step", "stepId": "s1",
                                 "label": "Step s1", "state": "done"}
    assert events["artifact:a1"]["artifact"] == {"id": "a1", "type": "stats", "title": "Stats a1",
                                                 "items": [{"label": "n", "value": "1"}]}
    assert events["msg:m1"] == {"id": "msg:m1", "at": "2026-09-20T12:59:00Z", "kind": "thought",
                                "text": "Reading the data"}
    assert (result.status, result.needs_user) == ("working", None)


def test_resync_of_the_same_snapshot_changes_nothing(store, mission):
    snapshot = _snapshot(_output([_step("s1")], [_stats("a1", "s1")], CONCLUSION, "Drop the outlier?"), "waiting")
    messages = [_devin("m1", "One"), _devin("m2", "Two")]
    _run(store, mission.id, snapshot, messages)
    before = store.list_events(mission.id)

    again = _run(store, mission.id, snapshot, messages, now="2026-09-20T14:00:00Z")
    assert again.new_events == [] and again.updated_events == []
    assert (again.status, again.needs_user) == ("waiting", "Drop the outlier?")
    assert store.list_events(mission.id) == before


def test_sync_does_not_mutate_its_inputs(store, mission):
    stored = store.list_events(mission.id)
    output = _output([_step("s1")], [_stats("a1", "s1")], dict(CONCLUSION))
    frozen_stored, frozen_output = repr(stored), repr(output)
    sync(mission, stored, _snapshot(output), [_devin("m1", "x")], [], now=NOW)
    assert (repr(stored), repr(output)) == (frozen_stored, frozen_output)


# ---------- messages ----------

def test_new_message_is_appended(store, mission):
    _run(store, mission.id, _snapshot(), [_devin("m1", "One")])
    result = _run(store, mission.id, _snapshot(), [_devin("m1", "One"), _devin("m2", "Two")])
    assert [n.event["id"] for n in result.new_events] == ["msg:m2"]
    assert _thread(store, mission.id) == ["user:first", "msg:m1", "msg:m2"]


def test_message_without_a_timestamp_gets_now(store, mission):
    _run(store, mission.id, _snapshot(), [_devin("m1", "One", at="")])
    assert store.list_events(mission.id)[-1]["at"] == NOW


def test_user_role_messages_are_skipped(store, mission):
    messages = [DevinMessage("u1", "user", PROMPT, ""), DevinMessage("u2", "user", "typed in Devin's own UI", "")]
    assert _run(store, mission.id, _snapshot(), messages).new_events == []


def test_own_echo_is_skipped_even_when_the_role_is_wrong(store, mission):
    store.append_event(mission.id, "user_message", {"text": "What about  the outlier?"})
    messages = [
        _devin("e1", PROMPT.replace("\n\n", "\n \n")),
        _devin("e2", "  What about the outlier?\n"),
        _devin("e3", "Do storms predict outages?"),
        _devin("m1", "A real thought"),
    ]
    result = _run(store, mission.id, _snapshot(), messages)
    assert [n.event["id"] for n in result.new_events] == ["msg:m1"]


def test_brief_is_never_shown_even_if_devin_wraps_it(store, mission):
    wrapped = _devin("e1", f"Task received:\n{PROMPT}\n--")
    assert _run(store, mission.id, _snapshot(), [wrapped]).new_events == []


def test_blank_messages_are_skipped(store, mission):
    assert _run(store, mission.id, _snapshot(), [_devin("m1", "  \n ")]).new_events == []


def test_messages_still_sync_when_structured_output_is_malformed(store, mission):
    for output in (None, {"steps": "nope", "artifacts": 3, "conclusion": "x", "needs_user": 9}):
        result = _run(store, mission.id, _snapshot(output), [_devin("m1", "Still here")])
        assert result.status == "working"
    assert _thread(store, mission.id) == ["user:first", "msg:m1"]


# ---------- steps ----------

def test_step_state_change_updates_in_place(store, mission):
    _run(store, mission.id, _snapshot(_output([_step("s1", "active")])), [_devin("m1", "One")])
    result = _run(store, mission.id, _snapshot(_output([_step("s1", "done"), _step("s2", "active")])),
                  [_devin("m1", "One")])

    assert [u.event["id"] for u in result.updated_events] == ["step:s1"]
    assert not result.updated_events[0].move_to_end
    assert _thread(store, mission.id) == ["user:first", "msg:m1", "step:s1", "step:s2"]
    assert _event(store, mission.id, "step:s1")["state"] == "done"


def test_step_label_change_updates_and_keeps_its_time(store, mission):
    _run(store, mission.id, _snapshot(_output([_step("s1", "active", "Read")])))
    _run(store, mission.id, _snapshot(_output([_step("s1", "active", "Read both datasets")])), now="2026-09-20T15:00:00Z")
    step = store.list_events(mission.id)[1]
    assert (step["label"], step["at"]) == ("Read both datasets", NOW)


@pytest.mark.parametrize("bad", [
    "junk", None, {}, {"id": "s9"}, {"id": "", "label": "x", "state": "done"},
    {"id": "s9", "label": "", "state": "done"}, {"id": "s9", "label": "x", "state": "pending"},
    {"id": 9, "label": "x", "state": "done"},
])
def test_bad_steps_are_skipped_without_losing_good_ones(store, mission, bad):
    _run(store, mission.id, _snapshot(_output([bad, _step("s1")])))
    assert _thread(store, mission.id) == ["user:first", "step:s1"]


def test_duplicate_step_ids_in_one_snapshot_yield_one_event(store, mission):
    _run(store, mission.id, _snapshot(_output([_step("s1", "active"), _step("s1", "done")])))
    assert _thread(store, mission.id) == ["user:first", "step:s1"]


def test_a_step_that_disappears_is_kept(store, mission):
    _run(store, mission.id, _snapshot(_output([_step("s1"), _step("s2")])))
    _run(store, mission.id, _snapshot(_output([_step("s2")])))
    assert _thread(store, mission.id) == ["user:first", "step:s1", "step:s2"]


# ---------- artifacts ----------

def test_artifacts_in_one_batch_are_ordered_by_after_step(store, mission):
    snapshot = _snapshot(_output(
        steps=[_step("s1"), _step("s2"), _step("s3", "active")],
        artifacts=[_stats("a3", "s3"), _stats("a1", "s1"), _stats("a2", "s1"), _stats("a4"), _stats("a5", "ghost")],
    ))
    _run(store, mission.id, snapshot, [_devin("m1", "One")])
    assert _thread(store, mission.id) == [
        "user:first", "msg:m1", "step:s1", "artifact:a1", "artifact:a2", "step:s2", "step:s3",
        "artifact:a3", "artifact:a4", "artifact:a5",
    ]


def test_artifacts_follow_their_step_in_an_empty_thread(mission):
    snapshot = _snapshot(_output([_step("s1"), _step("s2")], [_stats("a1", "s1")]))
    result = sync(mission, [], snapshot, [], [], now=NOW)
    assert [(n.event["id"], n.after) for n in result.new_events] == [
        ("step:s1", None), ("step:s2", None), ("artifact:a1", "step:s1")]


def test_a_later_artifact_lands_below_what_was_read_and_below_new_thoughts(store, mission):
    _run(store, mission.id, _snapshot(_output([_step("s1", "active")])), [_devin("m1", "One")])
    snapshot = _snapshot(_output([_step("s1"), _step("s2", "active")], [_stats("a1", "s1")]))
    _run(store, mission.id, snapshot, [_devin("m1", "One"), _devin("m2", "Two")])
    assert _thread(store, mission.id) == [
        "user:first", "msg:m1", "step:s1", "msg:m2", "artifact:a1", "step:s2"]


def test_invalid_artifact_is_skipped_and_the_rest_sync(store, mission):
    bad = {"id": "bad", "type": "chart", "title": "No series", "kind": "line", "series": []}
    _run(store, mission.id, _snapshot(_output([_step("s1")], [bad, "junk", _stats("a1", "s1")])))
    assert _thread(store, mission.id) == ["user:first", "step:s1", "artifact:a1"]


def test_changed_artifact_is_updated_in_place(store, mission):
    _run(store, mission.id, _snapshot(_output([_step("s1")], [_stats("a1", "s1", value="1")])), [_devin("m1", "x")])
    result = _run(store, mission.id, _snapshot(_output([_step("s1")], [_stats("a1", "s1", value="2")])),
                  [_devin("m1", "x")])
    assert [u.event["id"] for u in result.updated_events] == ["artifact:a1"]
    assert _thread(store, mission.id) == ["user:first", "msg:m1", "step:s1", "artifact:a1"]
    assert _event(store, mission.id, "artifact:a1")["artifact"]["items"][0]["value"] == "2"


def test_attachment_artifact_waits_for_the_attachment_then_points_at_the_proxy(store, mission):
    image = {"id": "a1", "after_step": "s1", "type": "image", "title": "Map", "src": "attachment:map.png"}
    snapshot = _snapshot(_output([_step("s1")], [image]))

    _run(store, mission.id, snapshot)
    assert _thread(store, mission.id) == ["user:first", "step:s1"]

    _run(store, mission.id, snapshot, attachments=[Attachment("map.png", "https://files.test/map.png")])
    artifact = store.list_events(mission.id)[-1]["artifact"]
    assert artifact["src"] == f"/api/missions/{mission.id}/attachments/map.png"


def test_duplicate_artifact_ids_in_one_snapshot_yield_one_event(store, mission):
    _run(store, mission.id, _snapshot(_output([], [_stats("a1"), _stats("a1", value="9")])))
    assert _thread(store, mission.id) == ["user:first", "artifact:a1"]


# ---------- conclusion ----------

def test_conclusion_is_appended_last_and_normalised(store, mission):
    _run(store, mission.id, _snapshot(_output([_step("s1")], [], CONCLUSION), "waiting"), [_devin("m1", "Done")])
    assert _thread(store, mission.id) == ["user:first", "msg:m1", "step:s1", "conclusion"]
    assert store.list_events(mission.id)[-1] == {
        "id": "conclusion", "at": NOW, "kind": "conclusion", "verdict": "A modest link.",
        "summary": "r = 0.58 at one week.", "stats": [{"label": "Correlation", "value": "0.58"}]}


def test_changed_conclusion_replaces_the_old_one_at_the_end(store, mission):
    _run(store, mission.id, _snapshot(_output([], [], CONCLUSION), "waiting"), [_devin("m1", "One")])
    revised = {**CONCLUSION, "verdict": "No link after all."}
    later = "2026-09-20T16:00:00Z"
    result = _run(store, mission.id, _snapshot(_output([], [], revised), "waiting"),
                  [_devin("m1", "One"), _devin("m2", "I was wrong")], now=later)

    assert [(u.event["id"], u.move_to_end) for u in result.updated_events] == [("conclusion", True)]
    assert _thread(store, mission.id) == ["user:first", "msg:m1", "msg:m2", "conclusion"]
    conclusion = store.list_events(mission.id)[-1]
    assert (conclusion["verdict"], conclusion["at"]) == ("No link after all.", later)
    assert [e["kind"] for e in store.list_events(mission.id)].count("conclusion") == 1


def test_conclusion_going_back_to_null_keeps_the_stored_one(store, mission):
    _run(store, mission.id, _snapshot(_output([], [], CONCLUSION), "waiting"))
    result = _run(store, mission.id, _snapshot(_output([], [], None)))
    assert result.updated_events == []
    assert _thread(store, mission.id) == ["user:first", "conclusion"]


@pytest.mark.parametrize("bad", ["text", [], {}, {"summary": "no verdict"}, {"verdict": "  ", "summary": "x"},
                                 {"verdict": 3, "summary": "x"}])
def test_bad_conclusion_is_ignored(store, mission, bad):
    _run(store, mission.id, _snapshot(_output([], [], bad)))
    assert _thread(store, mission.id) == ["user:first"]


def test_conclusion_tolerates_missing_summary_and_stats(store, mission):
    _run(store, mission.id, _snapshot(_output([], [], {"verdict": "Null result."})))
    event = store.list_events(mission.id)[-1]
    assert (event["summary"], event["stats"]) == ("", [])


# ---------- status ----------

@pytest.mark.parametrize("session_status, needs_user, expected", [
    ("running", None, ("working", None)),
    ("running", "", ("working", None)),
    ("running", "   ", ("working", None)),
    ("running", 7, ("working", None)),
    ("running", "Drop the outlier?", ("waiting", "Drop the outlier?")),
    ("waiting", None, ("waiting", None)),
    ("waiting", " Which region? ", ("waiting", "Which region?")),
    ("finished", None, ("waiting", None)),
])
def test_status_and_needs_user(store, mission, session_status, needs_user, expected):
    result = _run(store, mission.id, _snapshot(_output(needs_user=needs_user), session_status))
    assert (result.status, result.needs_user) == expected
    row = store.get_mission(mission.id)
    assert (row.status, row.needs_user) == expected


def test_running_session_with_a_conclusion_is_still_working(store, mission):
    assert _run(store, mission.id, _snapshot(_output([], [], CONCLUSION), "running")).status == "working"


def test_an_answered_question_does_not_bounce_the_mission_back_to_waiting(store, mission):
    asked = _snapshot(_output(needs_user="Drop the outlier?"), "waiting")
    _run(store, mission.id, asked)
    store.reopen(mission.id)

    stale = _snapshot(_output(needs_user="Drop the outlier?"), "running")
    assert _run(store, mission.id, stale).status == "working"
    assert store.get_mission(mission.id).needs_user is None

    fresh = _snapshot(_output(needs_user="And the second one?"), "running")
    result = _run(store, mission.id, fresh)
    assert (result.status, result.needs_user) == ("waiting", "And the second one?")


def test_malformed_output_keeps_the_current_question(store, mission):
    _run(store, mission.id, _snapshot(_output(needs_user="Drop it?"), "waiting"))
    result = _run(store, mission.id, _snapshot(None, "waiting"))
    assert (result.status, result.needs_user) == ("waiting", "Drop it?")


@pytest.mark.parametrize("detail, fragment", [
    (None, "ended with an error"),
    ("out_of_credits", "out of credits"),
    ("usage_limit_exceeded", "usage limit exceeded"),
    ("error", "ended with an error"),
])
def test_session_error_fails_the_mission_with_one_error_event(store, mission, detail, fragment):
    snapshot = _snapshot(_output([_step("s1")], needs_user="ignored"), "error", detail)
    result = _run(store, mission.id, snapshot, [_devin("m1", "Last words")])

    assert (result.status, result.needs_user) == ("failed", None)
    events = store.list_events(mission.id)
    assert [e["kind"] for e in events] == ["user_message", "thought", "step", "error"]
    assert fragment in events[-1]["text"]
    assert store.get_mission(mission.id).status == "failed"

    again = sync(store.get_mission(mission.id), store.list_events(mission.id), snapshot,
                 [_devin("m1", "Last words")], [], now=NOW)
    assert again.new_events == [] and again.status == "failed"


def test_a_second_failure_after_reopening_gets_its_own_error_event(store, mission):
    snapshot = _snapshot(None, "error")
    _run(store, mission.id, snapshot)
    store.reopen(mission.id)
    _run(store, mission.id, snapshot)
    errors = [e for e in store.list_events(mission.id) if e["kind"] == "error"]
    assert len(errors) == 2 and errors[0]["id"] != errors[1]["id"]


# ---------- title ----------

@pytest.mark.parametrize("raw, expected", [
    ("Storm damage vs outages", "Storm damage vs outages"),
    ("  Padded title \n", "Padded title"),
    ("Ends with a full stop.", "Ends with a full stop"),
    ("x" * 200, "x" * 60),
    ("", None),
    ("   ", None),
    (None, None),
    (42, None),
    (["list"], None),
])
def test_title_comes_from_the_structured_output(mission, raw, expected):
    result = sync(mission, [], _snapshot(_output(title=raw)), [], [], now=NOW)
    assert result.title == expected


def test_no_title_without_structured_output(mission):
    assert sync(mission, [], _snapshot(None), [], [], now=NOW).title is None
    assert sync(mission, [], _snapshot("not a dict"), [], [], now=NOW).title is None


# ---------- the conclusion closes Devin's turn ----------

def test_a_thought_that_arrives_after_the_conclusion_goes_above_it(store, mission):
    output = _output([_step("s1")], [], CONCLUSION)
    _run(store, mission.id, _snapshot(output, "waiting"), [_devin("m1", "Working")])
    result = _run(store, mission.id, _snapshot(output, "waiting"), [_devin("m1", "Working"), _devin("m2", "I have an answer")])
    assert _thread(store, mission.id) == ["user:first", "msg:m1", "step:s1", "msg:m2", "conclusion"]
    assert [(u.event["id"], u.move_to_end) for u in result.updated_events] == [("conclusion", True)]
    # The conclusion itself did not change, so it keeps its original time.
    assert _event(store, mission.id, "conclusion")["at"] == NOW


def test_late_steps_and_artifacts_also_stay_above_the_conclusion(store, mission):
    _run(store, mission.id, _snapshot(_output([_step("s1")], [], CONCLUSION), "waiting"))
    late = _output([_step("s1"), _step("s2")], [_stats("a1", "s2")], CONCLUSION)
    _run(store, mission.id, _snapshot(late, "waiting"))
    assert _thread(store, mission.id) == ["user:first", "step:s1", "step:s2", "artifact:a1", "conclusion"]


def test_a_settled_conclusion_is_not_moved_again(store, mission):
    output = _output([_step("s1")], [], CONCLUSION)
    messages = [_devin("m1", "Working"), _devin("m2", "I have an answer")]
    _run(store, mission.id, _snapshot(output, "waiting"), messages)
    assert _run(store, mission.id, _snapshot(output, "waiting"), messages).updated_events == []


def test_the_conclusion_stays_put_once_the_user_has_replied_below_it(store, mission):
    output = _output([_step("s1")], [], CONCLUSION)
    _run(store, mission.id, _snapshot(output, "waiting"))
    store.append_event(mission.id, "user_message", {"text": "And in winter only?"})
    _run(store, mission.id, _snapshot(output), [_devin("m9", "Checking winter")])
    kinds = [event["kind"] for event in store.list_events(mission.id)]
    assert kinds == ["user_message", "step", "conclusion", "user_message", "thought"]


# ---------- final report ----------

RAW_REPORT = {
    "headline": "Storm damage predicts outage length.",
    "summary": "We asked whether damage predicts outages. It does, modestly.",
    "stats": [{"label": "Correlation", "value": 0.58}],
    "key_artifact_ids": ["a1", "ghost"],
    "steps": [{"label": "Read the data", "takeaway": "One tile in ten was unusable."}],
    "caveats": ["One region drives the extremes."],
    "next_questions": ["Does it hold next quarter?"],
}
REPORT = {
    "headline": "Storm damage predicts outage length",
    "summary": "We asked whether damage predicts outages. It does, modestly.",
    "stats": [{"label": "Correlation", "value": "0.58"}],
    "keyArtifactIds": ["a1"],
    "steps": [{"label": "Read the data", "takeaway": "One tile in ten was unusable."}],
    "caveats": ["One region drives the extremes."],
    "nextQuestions": ["Does it hold next quarter?"],
}
REPORT_EVENT = {"id": "report", "at": NOW, "kind": "report"}
STAMP = "%Y-%m-%dT%H:%M:%SZ"


def _concluded(report=None, conclusion=CONCLUSION, artifacts=None):
    return _output([_step("s1")], [_stats("a1", "s1")] if artifacts is None else artifacts, conclusion, report=report)


def _after_request(store, mission_id, seconds):
    asked = datetime.strptime(store.get_mission(mission_id).report_requested_at, STAMP)
    return (asked + timedelta(seconds=seconds)).strftime(STAMP)


@pytest.fixture
def concluded(store, mission):
    """A mission whose run has ended in a conclusion and is waiting for the user."""
    _run(store, mission.id, _snapshot(_concluded(), "waiting"), [_devin("m1", "Working")])
    assert _thread(store, mission.id) == ["user:first", "msg:m1", "step:s1", "artifact:a1", "conclusion"]
    return store.get_mission(mission.id)


@pytest.fixture
def reported(store, concluded):
    """The same mission once a first report has been delivered."""
    store.request_report(concluded.id)
    _run(store, concluded.id, _snapshot(_concluded(RAW_REPORT), "waiting"), [_devin("m1", "Working")])
    assert _thread(store, concluded.id)[-2:] == ["conclusion", "report"]
    return store.get_mission(concluded.id)


def test_a_report_nobody_asked_for_is_ignored(store, concluded):
    result = _run(store, concluded.id, _snapshot(_concluded(RAW_REPORT), "waiting"), [_devin("m1", "Working")])
    assert (result.report, result.report_settled, result.new_events, result.updated_events) == (None, False, [], [])
    assert store.get_mission(concluded.id).report is None


def test_a_requested_report_is_delivered_after_the_conclusion(store, concluded):
    store.request_report(concluded.id)
    result = _run(store, concluded.id, _snapshot(_concluded(RAW_REPORT), "waiting"), [_devin("m1", "Working")])

    assert result.report == {**REPORT, "generatedAt": NOW}
    assert (result.report_settled, result.status) == (True, "waiting")
    assert [(n.event, n.after) for n in result.new_events] == [(REPORT_EVENT, None)]
    assert store.list_events(concluded.id)[-2:] == [_event(store, concluded.id, "conclusion"), REPORT_EVENT]
    row = store.get_mission(concluded.id)
    assert (row.report, row.report_pending, row.status) == ({**REPORT, "generatedAt": NOW}, False, "waiting")


def test_delivery_is_idempotent(store, reported):
    before = store.list_events(reported.id)
    again = _run(store, reported.id, _snapshot(_concluded(RAW_REPORT), "waiting"), [_devin("m1", "Working")],
                 now="2026-09-20T14:00:00Z")
    assert (again.new_events, again.updated_events, again.report, again.report_settled) == ([], [], None, False)
    assert store.list_events(reported.id) == before
    assert store.get_mission(reported.id).report["generatedAt"] == NOW


def test_a_mission_without_a_conclusion_can_still_get_a_report(store, mission):
    store.request_report(mission.id)
    _run(store, mission.id, _snapshot(_output([_step("s1")], report=RAW_REPORT), "waiting"))
    assert _thread(store, mission.id) == ["user:first", "step:s1", "report"]


@pytest.mark.parametrize("session_status, needs_user, expected", [
    ("running", None, ("working", None)),
    ("waiting", None, ("working", None)),
    ("finished", None, ("working", None)),
    ("waiting", "Include the winter run?", ("waiting", "Include the winter run?")),
])
def test_a_pending_report_holds_the_mission_at_working(store, concluded, session_status, needs_user, expected):
    store.request_report(concluded.id)
    output = {**_concluded(), "needs_user": needs_user}
    result = _run(store, concluded.id, _snapshot(output, session_status), [_devin("m1", "Working")])
    assert (result.status, result.needs_user) == expected
    assert (result.report, result.report_settled) == (None, False)
    assert store.get_mission(concluded.id).report_pending


@pytest.mark.parametrize("bad", [
    None, "soon", 7, [], {}, {"headline": "No summary yet"}, {"headline": " ", "summary": "x"},
    {"headline": ["x"], "summary": {"x": 1}, "steps": "junk", "stats": [[1]], "key_artifact_ids": {"a": [1]}},
])
def test_an_unusable_report_keeps_the_request_waiting(store, concluded, bad):
    store.request_report(concluded.id)
    result = _run(store, concluded.id, _snapshot(_concluded(bad), "waiting"), [_devin("m1", "Working")])
    assert (result.report, result.report_settled, result.status) == (None, False, "working")
    assert "report" not in _thread(store, concluded.id)


def test_missing_structured_output_keeps_the_request_waiting(store, concluded):
    store.request_report(concluded.id)
    result = _run(store, concluded.id, _snapshot(None, "waiting"), [_devin("m1", "Working")])
    assert (result.report, result.report_settled, result.status) == (None, False, "working")


def test_featured_artifacts_are_those_in_the_thread_or_in_this_snapshot(store, concluded):
    store.request_report(concluded.id)
    raw = {**RAW_REPORT, "key_artifact_ids": ["a2", "bad", "a1", "ghost"]}
    bad = {"id": "bad", "type": "chart", "title": "No series", "kind": "line", "series": []}
    # a1 is only in the stored thread now, a2 arrives with the report, `bad` never renders.
    output = _concluded(raw, artifacts=[_stats("a2", "s1"), bad])
    result = _run(store, concluded.id, _snapshot(output, "waiting"), [_devin("m1", "Working")])
    assert result.report["keyArtifactIds"] == ["a2", "a1"]


def test_the_report_request_is_never_shown_even_if_it_comes_back_as_devins(store, concluded):
    store.request_report(concluded.id)
    echo = _devin("e1", REPORT_REQUEST.replace("\n\n", "\n \n"))
    result = _run(store, concluded.id, _snapshot(_concluded(), "running"), [_devin("m1", "Working"), echo])
    assert result.new_events == []


# ---------- regenerating ----------

def test_the_old_report_still_in_the_output_is_not_a_new_delivery(store, reported):
    store.request_report(reported.id)
    result = _run(store, reported.id, _snapshot(_concluded(RAW_REPORT), "running"), [_devin("m1", "Working")],
                  now=_after_request(store, reported.id, REPORT_TIMEOUT_SECONDS))
    assert (result.report, result.report_settled, result.status) == (None, False, "working")
    assert (result.new_events, result.updated_events) == ([], [])


def test_a_regenerated_report_replaces_the_old_one_and_restamps_the_marker(store, reported):
    store.request_report(reported.id)
    later = "2026-09-20T16:00:00Z"
    revised = {**RAW_REPORT, "summary": "Looking back again, the link also holds in both halves."}
    result = _run(store, reported.id, _snapshot(_concluded(revised), "waiting"), [_devin("m1", "Working")], now=later)

    assert result.report == {**REPORT, "summary": revised["summary"], "generatedAt": later}
    assert [(u.event, u.move_to_end) for u in result.updated_events] == [({**REPORT_EVENT, "at": later}, True)]
    assert store.list_events(reported.id)[-1] == {**REPORT_EVENT, "at": later}
    assert [e["kind"] for e in store.list_events(reported.id)].count("report") == 1
    assert store.get_mission(reported.id).report["generatedAt"] == later


# ---------- giving up ----------

def test_an_unchanged_report_is_accepted_once_the_request_is_overdue(store, reported):
    store.request_report(reported.id)
    overdue = _after_request(store, reported.id, REPORT_TIMEOUT_SECONDS + 1)
    result = _run(store, reported.id, _snapshot(_concluded(RAW_REPORT), "waiting"), [_devin("m1", "Working")],
                  now=overdue)
    assert result.report == {**REPORT, "generatedAt": overdue}
    assert (result.report_settled, result.status) == (True, "waiting")
    assert [e["kind"] for e in store.list_events(reported.id)].count("error") == 0
    assert not store.get_mission(reported.id).report_pending


def test_a_report_that_never_arrives_is_given_up_on_with_one_error(store, concluded):
    store.request_report(concluded.id)
    snapshot, messages = _snapshot(_concluded(), "waiting"), [_devin("m1", "Working")]
    on_time = _run(store, concluded.id, snapshot, messages,
                   now=_after_request(store, concluded.id, REPORT_TIMEOUT_SECONDS))
    assert (on_time.report_settled, on_time.new_events) == (False, [])

    overdue = _after_request(store, concluded.id, REPORT_TIMEOUT_SECONDS + 1)
    result = _run(store, concluded.id, snapshot, messages, now=overdue)
    assert (result.report, result.report_settled, result.status) == (None, True, "waiting")
    (error,) = result.new_events
    assert (error.event["kind"], error.event["text"], error.event["at"]) == ("error", REPORT_MISSING, overdue)
    assert REPORT_MISSING == "The report did not arrive"
    row = store.get_mission(concluded.id)
    assert (row.report, row.report_pending, row.status) == (None, False, "waiting")

    again = _run(store, concluded.id, snapshot, messages, now=overdue)
    assert not again.report_settled
    assert [e["kind"] for e in store.list_events(concluded.id)].count("error") == 1


def test_each_request_that_is_given_up_on_gets_its_own_error(store, concluded):
    for _ in range(2):
        store.request_report(concluded.id)
        _run(store, concluded.id, _snapshot(_concluded(), "waiting"), [_devin("m1", "Working")],
             now=_after_request(store, concluded.id, REPORT_TIMEOUT_SECONDS + 1))
    errors = [e for e in store.list_events(concluded.id) if e["kind"] == "error"]
    assert len(errors) == 2 and errors[0]["id"] != errors[1]["id"]


@pytest.mark.parametrize("requested_at", [None, "", "yesterday"])
def test_a_request_with_no_usable_start_time_counts_as_overdue(store, concluded, requested_at):
    store.request_report(concluded.id)
    row = dataclasses.replace(store.get_mission(concluded.id), report_requested_at=requested_at)
    result = sync(row, store.list_events(concluded.id), _snapshot(_concluded(), "waiting"), [], [], now=NOW)
    assert result.report_settled and result.new_events[-1].event["text"] == REPORT_MISSING


def test_a_session_error_ends_the_request_without_a_second_error(store, concluded):
    store.request_report(concluded.id)
    result = _run(store, concluded.id, _snapshot(_concluded(), "error", "out_of_credits"), [_devin("m1", "Working")],
                  now=_after_request(store, concluded.id, REPORT_TIMEOUT_SECONDS + 1))
    assert (result.status, result.report, result.report_settled) == ("failed", None, True)
    assert [e["text"] for e in store.list_events(concluded.id) if e["kind"] == "error"] == [
        "The Devin session stopped: out of credits."]
    row = store.get_mission(concluded.id)
    assert (row.status, row.report_pending) == ("failed", False)


# ---------- back to done ----------

def test_a_done_mission_returns_to_done_when_the_report_arrives(store, concluded):
    store.mark_done(concluded.id)
    store.request_report(concluded.id)
    waiting = _run(store, concluded.id, _snapshot({**_concluded(), "needs_user": "Stale question?"}, "waiting"))
    assert waiting.status == "waiting"

    result = _run(store, concluded.id, _snapshot({**_concluded(RAW_REPORT), "needs_user": "Stale question?"}, "running"))
    assert (result.status, result.needs_user) == ("done", None)
    row = store.get_mission(concluded.id)
    assert (row.status, row.needs_user, row.report_pending, row.report_restore_done) == ("done", None, False, False)
    assert row.report["headline"] == REPORT["headline"]


def test_a_done_mission_returns_to_done_when_the_report_never_arrives(store, concluded):
    store.mark_done(concluded.id)
    store.request_report(concluded.id)
    result = _run(store, concluded.id, _snapshot(_concluded(), "waiting"),
                  now=_after_request(store, concluded.id, REPORT_TIMEOUT_SECONDS + 1))
    assert (result.status, result.report_settled) == ("done", True)
    assert store.get_mission(concluded.id).status == "done"
    assert store.list_events(concluded.id)[-1]["text"] == REPORT_MISSING


def test_a_mission_marked_done_while_the_report_is_pending_stays_done(store, concluded):
    store.request_report(concluded.id)
    store.mark_done(concluded.id)
    pending = _run(store, concluded.id, _snapshot(_concluded(), "running"))
    assert (pending.status, pending.report_settled) == ("done", False)
    assert store.get_mission(concluded.id).status == "done"

    delivered = _run(store, concluded.id, _snapshot(_concluded(RAW_REPORT), "waiting"))
    assert (delivered.status, delivered.report_settled) == ("done", True)
    row = store.get_mission(concluded.id)
    assert (row.status, row.report_pending, row.report["headline"]) == ("done", False, REPORT["headline"])
    assert store.live_missions() == []


def test_a_reply_while_the_report_is_pending_means_it_no_longer_returns_to_done(store, concluded):
    store.mark_done(concluded.id)
    store.request_report(concluded.id)
    store.append_event(concluded.id, "user_message", {"text": "Actually, one more thing"})
    store.reopen(concluded.id)
    result = _run(store, concluded.id, _snapshot(_concluded(RAW_REPORT), "running"))
    assert (result.status, result.report_settled) == ("working", True)
    assert store.get_mission(concluded.id).status == "working"


# ---------- the report closes the thread ----------

def test_a_thought_that_comes_with_the_report_goes_above_the_conclusion_and_the_report(store, concluded):
    store.request_report(concluded.id)
    messages = [_devin("m1", "Working"), _devin("m2", "The report is ready.")]
    _run(store, concluded.id, _snapshot(_concluded(RAW_REPORT), "waiting"), messages)
    assert _thread(store, concluded.id) == [
        "user:first", "msg:m1", "step:s1", "artifact:a1", "msg:m2", "conclusion", "report"]
    assert _run(store, concluded.id, _snapshot(_concluded(RAW_REPORT), "waiting"), messages).updated_events == []


def test_a_thought_that_arrives_after_the_report_goes_above_both(store, reported):
    messages = [_devin("m1", "Working"), _devin("m2", "The report is ready.")]
    result = _run(store, reported.id, _snapshot(_concluded(RAW_REPORT), "waiting"), messages,
                  now="2026-09-20T14:00:00Z")
    assert _thread(store, reported.id) == [
        "user:first", "msg:m1", "step:s1", "artifact:a1", "msg:m2", "conclusion", "report"]
    assert [(u.event["id"], u.move_to_end) for u in result.updated_events] == [("conclusion", True), ("report", True)]
    # Neither changed, so both keep their times.
    assert _event(store, reported.id, "report")["at"] == NOW
    assert _run(store, reported.id, _snapshot(_concluded(RAW_REPORT), "waiting"), messages).updated_events == []


def test_the_conclusion_does_not_jump_below_a_report_that_is_already_last(store, reported):
    result = _run(store, reported.id, _snapshot(_concluded(RAW_REPORT), "waiting"), [_devin("m1", "Working")])
    assert result.updated_events == []
    assert _thread(store, reported.id)[-2:] == ["conclusion", "report"]


def test_late_steps_and_artifacts_stay_above_the_conclusion_and_the_report(store, reported):
    late = _output([_step("s1"), _step("s2")], [_stats("a1", "s1"), _stats("a2", "s1")], CONCLUSION, report=RAW_REPORT)
    _run(store, reported.id, _snapshot(late, "waiting"), [_devin("m1", "Working")])
    assert _thread(store, reported.id) == [
        "user:first", "msg:m1", "step:s1", "artifact:a1", "artifact:a2", "step:s2", "conclusion", "report"]


def test_a_revised_conclusion_keeps_the_report_below_it(store, reported):
    revised = {**CONCLUSION, "verdict": "No link after all."}
    _run(store, reported.id, _snapshot(_concluded(RAW_REPORT, conclusion=revised), "waiting"), [_devin("m1", "Working")])
    assert _thread(store, reported.id)[-2:] == ["conclusion", "report"]
    assert _event(store, reported.id, "conclusion")["verdict"] == "No link after all."


def test_once_the_user_replies_below_the_report_it_stays_where_it_was_delivered(store, reported):
    store.append_event(reported.id, "user_message", {"text": "And in winter only?"}, event_id="user:second")
    store.reopen(reported.id)
    messages = [_devin("m1", "Working"), _devin("m9", "Checking winter")]
    _run(store, reported.id, _snapshot(_concluded(RAW_REPORT)), messages)
    settled = ["user:first", "msg:m1", "step:s1", "artifact:a1", "conclusion", "report", "user:second", "msg:m9"]
    assert _thread(store, reported.id) == settled

    # Devin revises its conclusion: that goes to the end, the old report marker stays put.
    revised = {**CONCLUSION, "verdict": "Stronger in winter."}
    _run(store, reported.id, _snapshot(_concluded(RAW_REPORT, conclusion=revised), "waiting"), messages)
    assert _thread(store, reported.id) == [
        "user:first", "msg:m1", "step:s1", "artifact:a1", "report", "user:second", "msg:m9", "conclusion"]

    # A regenerated report then closes the thread again, below the new conclusion.
    store.request_report(reported.id)
    rewritten = {**RAW_REPORT, "headline": "The link is a winter effect"}
    messages.append(_devin("m10", "The report is ready."))
    _run(store, reported.id, _snapshot(_concluded(rewritten, conclusion=revised), "waiting"), messages)
    assert _thread(store, reported.id) == [
        "user:first", "msg:m1", "step:s1", "artifact:a1", "user:second", "msg:m9", "msg:m10", "conclusion", "report"]
    assert [e["kind"] for e in store.list_events(reported.id)].count("report") == 1


def test_a_regenerated_report_goes_below_a_conclusion_the_user_replied_under(store, reported):
    store.append_event(reported.id, "user_message", {"text": "Thanks"}, event_id="user:second")
    store.request_report(reported.id)
    rewritten = {**RAW_REPORT, "headline": "Still a modest link"}
    _run(store, reported.id, _snapshot(_concluded(rewritten), "waiting"), [_devin("m1", "Working")])
    assert _thread(store, reported.id) == [
        "user:first", "msg:m1", "step:s1", "artifact:a1", "conclusion", "user:second", "report"]


def test_sync_with_a_pending_report_does_not_mutate_its_inputs(store, reported):
    store.request_report(reported.id)
    row, stored = store.get_mission(reported.id), store.list_events(reported.id)
    output = _concluded({**RAW_REPORT, "summary": "Changed."})
    frozen = repr((row, stored, output))
    sync(row, stored, _snapshot(output), [_devin("m2", "x")], [], now=NOW)
    assert repr((row, stored, output)) == frozen
