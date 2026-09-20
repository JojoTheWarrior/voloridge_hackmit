"""Tests for server.sync: a pure function from (stored state, Devin snapshot) to thread changes."""
from __future__ import annotations

import pytest

from server.devin import Attachment, DevinMessage, SessionSnapshot
from server.store import Store
from server.sync import SyncResult, sync

NOW = "2026-09-20T13:00:00Z"
PROMPT = "You are a research analyst.\n\nThe question:\nDo storms predict outages?"


@pytest.fixture
def store(tmp_path):
    return Store(tmp_path / "k.db")


@pytest.fixture
def mission(store):
    row = store.create_mission(
        "Do storms predict outages?", title="Storms", dataset_ids=[], reference=None, prompt=PROMPT)
    store.set_session(row.id, "devin-abc", None)
    store.append_event(row.id, "user_message", {"text": "Do storms predict outages?"}, event_id="user:first")
    return store.get_mission(row.id)


def _snapshot(output=None, status="running", detail=None):
    return SessionSnapshot(status, detail, output)


def _output(steps=(), artifacts=(), conclusion=None, needs_user=None):
    return {"steps": list(steps), "artifacts": list(artifacts), "conclusion": conclusion, "needs_user": needs_user}


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
