"""Tests for server.store."""
from __future__ import annotations

import itertools
import sqlite3
import threading

import pytest

from server.store import Store
from server.sync import NewEvent, SyncResult, UpdatedEvent


class Clock:
    """Each reading is one second later than the last."""

    def __init__(self):
        self._seconds = itertools.count()

    def __call__(self) -> str:
        return f"2026-09-20T12:00:{next(self._seconds):02d}Z"


@pytest.fixture
def store(tmp_path):
    return Store(tmp_path / "nested" / "kingdom.db", now=Clock())


def _mission(store, hypothesis="Do storms predict outages?", **over):
    fields = {"title": "Storms vs outages", "dataset_ids": ["gdelt"], "reference": None, "prompt": "the brief"}
    fields.update(over)
    return store.create_mission(hypothesis, **fields)


def _thought(event_id, text="hm"):
    return {"id": event_id, "at": "2026-09-20T12:30:00Z", "kind": "thought", "text": text}


def _ids(store, mission_id):
    return [event["id"] for event in store.list_events(mission_id)]


# ---------- missions ----------

def test_creates_parent_directory_and_file(tmp_path):
    Store(tmp_path / "a" / "b" / "k.db")
    assert (tmp_path / "a" / "b" / "k.db").exists()


def test_mission_round_trip(store):
    created = _mission(store, reference="prior notes")
    loaded = store.get_mission(created.id)
    assert loaded == created
    assert loaded.id.startswith("m_")
    assert loaded.status == "working"
    assert loaded.dataset_ids == ["gdelt"]
    assert loaded.reference == "prior notes"
    assert loaded.prompt == "the brief"
    assert loaded.session_id is None and loaded.session_url is None and loaded.needs_user is None
    assert loaded.created_at == loaded.updated_at == "2026-09-20T12:00:01Z"
    assert loaded.failures == 0


def test_get_unknown_mission_is_none(store):
    assert store.get_mission("m_nope") is None


def test_mission_ids_are_unique(store):
    assert len({_mission(store).id for _ in range(50)}) == 50


def test_missions_list_newest_first_even_within_one_second(tmp_path):
    store = Store(tmp_path / "k.db", now=lambda: "2026-09-20T12:00:00Z")
    ids = [_mission(store).id for _ in range(3)]
    assert [m.id for m in store.list_missions()] == ids[::-1]


def test_set_session(store):
    mission = _mission(store)
    store.set_session(mission.id, "devin-abc", "https://app.devin.ai/sessions/devin-abc")
    loaded = store.get_mission(mission.id)
    assert (loaded.session_id, loaded.session_url) == ("devin-abc", "https://app.devin.ai/sessions/devin-abc")


def test_fail_sets_status_and_appends_error(store):
    mission = _mission(store)
    store.fail(mission.id, "Devin is unreachable")
    assert store.get_mission(mission.id).status == "failed"
    assert [(e["kind"], e["text"]) for e in store.list_events(mission.id)] == [("error", "Devin is unreachable")]


def test_mark_done_then_reopen(store):
    mission = _mission(store)
    store.apply_sync(mission.id, SyncResult([], [], "waiting", "Drop the outlier?"), expected_status="working")
    store.mark_done(mission.id)
    done = store.get_mission(mission.id)
    assert done.status == "done" and done.needs_user is None
    assert done.updated_at > mission.updated_at

    store.reopen(mission.id)
    reopened = store.get_mission(mission.id)
    assert reopened.status == "working"
    assert reopened.needs_user is None


def test_reopen_remembers_the_question_it_answered(store):
    mission = _mission(store)
    store.apply_sync(mission.id, SyncResult([], [], "waiting", "Drop the outlier?"), expected_status="working")
    store.reopen(mission.id)
    reopened = store.get_mission(mission.id)
    assert reopened.answered_needs_user == "Drop the outlier?"
    assert reopened.needs_user is None and reopened.status == "working"


def test_live_missions_are_working_or_waiting_with_a_session(store):
    working, waiting, done, failed, sessionless = (_mission(store) for _ in range(5))
    for mission in (working, waiting, done, failed):
        store.set_session(mission.id, f"devin-{mission.id}", None)
    store.apply_sync(waiting.id, SyncResult([], [], "waiting", None), expected_status="working")
    store.mark_done(done.id)
    store.fail(failed.id, "boom")
    assert {m.id for m in store.live_missions()} == {working.id, waiting.id}


def test_restart_reloads_everything(tmp_path):
    path = tmp_path / "k.db"
    first = Store(path, now=Clock())
    mission = _mission(first)
    first.set_session(mission.id, "devin-abc", None)
    first.append_event(mission.id, "user_message", {"text": "hello"})
    first.add_dataset("Mine", "https://x.test")

    second = Store(path, now=Clock())
    assert [m.id for m in second.live_missions()] == [mission.id]
    assert [e["text"] for e in second.list_events(mission.id)] == ["hello"]
    assert len(second.list_datasets()) == 5


# ---------- events ----------

def test_append_event_shape_and_order(store):
    mission = _mission(store)
    first = store.append_event(mission.id, "user_message", {"text": "hi"})
    second = store.append_event(mission.id, "error", {"text": "oops"})
    assert first == {"id": first["id"], "at": first["at"], "kind": "user_message", "text": "hi"}
    assert mission.created_at < first["at"] < second["at"]
    assert first["id"] != second["id"]
    assert store.list_events(mission.id) == [first, second]
    assert store.get_mission(mission.id).updated_at >= second["at"]


def test_append_event_keeps_a_given_id_and_time(store):
    mission = _mission(store)
    event = store.append_event(mission.id, "thought", {"text": "x"}, event_id="msg:7", at="2026-01-01T00:00:00Z")
    assert (event["id"], event["at"]) == ("msg:7", "2026-01-01T00:00:00Z")


def test_events_are_scoped_to_their_mission(store):
    a, b = _mission(store), _mission(store)
    store.append_event(a.id, "thought", {"text": "a"}, event_id="msg:1")
    store.append_event(b.id, "thought", {"text": "b"}, event_id="msg:1")
    assert [e["text"] for e in store.list_events(a.id)] == ["a"]
    assert [e["text"] for e in store.list_events(b.id)] == ["b"]


def test_apply_sync_appends_and_inserts_after(store):
    mission = _mission(store)
    store.apply_sync(mission.id, SyncResult(
        [NewEvent(_thought("t1")), NewEvent(_thought("t2")), NewEvent(_thought("t3"))], [], "working", None,
    ), expected_status="working")
    store.apply_sync(mission.id, SyncResult(
        [NewEvent(_thought("x"), after="t1"), NewEvent(_thought("y"), after="x"), NewEvent(_thought("z"))],
        [], "working", None,
    ), expected_status="working")
    assert _ids(store, mission.id) == ["t1", "x", "y", "t2", "t3", "z"]


def test_apply_sync_insert_after_unknown_id_appends(store):
    mission = _mission(store)
    store.apply_sync(mission.id, SyncResult(
        [NewEvent(_thought("t1")), NewEvent(_thought("x"), after="ghost")], [], "working", None,
    ), expected_status="working")
    assert _ids(store, mission.id) == ["t1", "x"]


def test_apply_sync_is_safe_to_repeat(store):
    mission = _mission(store)
    result = SyncResult([NewEvent(_thought("t1"))], [], "working", None)
    store.apply_sync(mission.id, result, expected_status="working")
    store.apply_sync(mission.id, result, expected_status="working")
    assert _ids(store, mission.id) == ["t1"]


def test_apply_sync_updates_in_place_or_moves_to_end(store):
    mission = _mission(store)
    step = {"id": "step:s1", "at": "2026-09-20T12:30:00Z", "kind": "step", "stepId": "s1", "label": "Read", "state": "active"}
    store.apply_sync(mission.id, SyncResult(
        [NewEvent(step), NewEvent(_thought("c", "old")), NewEvent(_thought("t9"))], [], "working", None,
    ), expected_status="working")

    store.apply_sync(mission.id, SyncResult([], [
        UpdatedEvent({**step, "state": "done"}),
        UpdatedEvent(_thought("c", "new"), move_to_end=True),
    ], "working", None), expected_status="working")

    events = store.list_events(mission.id)
    assert [e["id"] for e in events] == ["step:s1", "t9", "c"]
    assert events[0]["state"] == "done"
    assert events[2]["text"] == "new"


def test_apply_sync_sets_status_and_needs_user(store):
    mission = _mission(store)
    store.apply_sync(mission.id, SyncResult([], [], "waiting", "Drop it?"), expected_status="working")
    loaded = store.get_mission(mission.id)
    assert (loaded.status, loaded.needs_user) == ("waiting", "Drop it?")


def test_apply_sync_does_not_undo_a_concurrent_mark_done(store):
    mission = _mission(store)
    store.mark_done(mission.id)
    store.apply_sync(mission.id, SyncResult([NewEvent(_thought("t1"))], [], "waiting", "Q?"),
                     expected_status="working")
    loaded = store.get_mission(mission.id)
    assert (loaded.status, loaded.needs_user) == ("done", None)
    assert _ids(store, mission.id) == ["t1"]


def test_apply_sync_touches_updated_at_only_on_change(store):
    mission = _mission(store)
    store.apply_sync(mission.id, SyncResult([], [], "working", None), expected_status="working")
    assert store.get_mission(mission.id).updated_at == mission.updated_at
    store.apply_sync(mission.id, SyncResult([NewEvent(_thought("t1"))], [], "working", None),
                     expected_status="working")
    assert store.get_mission(mission.id).updated_at > mission.updated_at


def test_failure_counter(store):
    mission = _mission(store)
    assert [store.record_failure(mission.id) for _ in range(3)] == [1, 2, 3]
    store.clear_failures(mission.id)
    assert store.get_mission(mission.id).failures == 0
    assert store.record_failure(mission.id) == 1


def test_concurrent_writers_do_not_lose_events(store):
    mission = _mission(store)

    def write(prefix):
        for index in range(25):
            store.append_event(mission.id, "thought", {"text": f"{prefix}{index}"})

    threads = [threading.Thread(target=write, args=(name,)) for name in "abcd"]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    events = store.list_events(mission.id)
    assert len(events) == 100
    assert len({event["id"] for event in events}) == 100


# ---------- datasets ----------

def test_datasets_are_seeded_once(tmp_path):
    path = tmp_path / "k.db"
    seeded = Store(path).list_datasets()
    assert [d["id"] for d in seeded] == ["gdelt", "yahoo", "open-meteo", "cams"]
    assert [d["kind"] for d in seeded] == ["events", "markets", "weather", "air"]
    assert set(seeded[0]) == {"id", "name", "url", "kind", "seriesCount", "dateRange", "syncedAt"}
    assert len(Store(path).list_datasets()) == 4


def test_added_dataset_comes_first(store):
    added = store.add_dataset("County outages", "https://x.test/outages.csv")
    assert added == {
        "id": added["id"], "name": "County outages", "url": "https://x.test/outages.csv",
        "kind": "other", "seriesCount": 0, "dateRange": "", "syncedAt": added["syncedAt"],
    }
    assert added["id"].startswith("d_")
    assert [d["id"] for d in store.list_datasets()][:2] == [added["id"], "gdelt"]


def test_get_datasets_by_ids_keeps_request_order_and_skips_unknown(store):
    found = store.get_datasets(["yahoo", "ghost", "gdelt", "yahoo"])
    assert [d["id"] for d in found] == ["yahoo", "gdelt"]


def test_schema_uses_a_real_sqlite_file(store, tmp_path):
    with sqlite3.connect(tmp_path / "nested" / "kingdom.db") as db:
        tables = {row[0] for row in db.execute("select name from sqlite_master where type='table'")}
    assert {"missions", "events", "datasets"} <= tables


def test_apply_sync_retitles_the_mission(store):
    mission = _mission(store)
    store.apply_sync(mission.id, SyncResult([], [], "working", None, title="Storm damage vs outages"),
                     expected_status="working")
    assert store.get_mission(mission.id).title == "Storm damage vs outages"


def test_apply_sync_without_a_title_keeps_the_current_one(store):
    mission = _mission(store)
    store.apply_sync(mission.id, SyncResult([], [], "working", None, title="First"), expected_status="working")
    store.apply_sync(mission.id, SyncResult([], [], "working", None), expected_status="working")
    assert store.get_mission(mission.id).title == "First"


def test_apply_sync_retitles_even_when_the_user_changed_the_status(store):
    mission = _mission(store)
    store.mark_done(mission.id)
    store.apply_sync(mission.id, SyncResult([], [], "working", None, title="Late title"), expected_status="working")
    done = store.get_mission(mission.id)
    assert (done.status, done.title) == ("done", "Late title")


# ---------- reports ----------

REPORT = {"headline": "A leads B", "summary": "It does.", "stats": [], "keyArtifactIds": [], "steps": [],
          "caveats": [], "nextQuestions": [], "generatedAt": "2026-09-20T12:40:00Z"}

# The missions table as it was before reports existed; a database like this is in use.
OLD_MISSIONS = """
create table missions (
    seq integer primary key autoincrement, id text not null unique, title text not null,
    hypothesis text not null, reference text, prompt text not null, status text not null,
    created_at text not null, updated_at text not null, dataset_ids text not null,
    session_id text, session_url text, needs_user text, answered_needs_user text,
    failures integer not null default 0
);
"""


def _settled(report=None, status="waiting", new_events=()):
    return SyncResult(list(new_events), [], status, None, report=report, report_settled=True)


def test_a_new_mission_has_no_report(store):
    mission = _mission(store)
    assert (mission.report, mission.report_pending, mission.report_requested_at, mission.report_restore_done) == (
        None, False, None, False)


@pytest.mark.parametrize("before, restore", [("working", False), ("waiting", False), ("done", True)])
def test_request_report_sets_pending_and_working_and_remembers_done(store, before, restore):
    mission = _mission(store)
    if before == "waiting":
        store.apply_sync(mission.id, SyncResult([], [], "waiting", "Drop it?"), expected_status="working")
    elif before == "done":
        store.mark_done(mission.id)
    asked = store.get_mission(mission.id)

    store.request_report(mission.id)
    pending = store.get_mission(mission.id)
    assert (pending.status, pending.report_pending, pending.report_restore_done) == ("working", True, restore)
    assert asked.updated_at < pending.report_requested_at <= pending.updated_at
    assert pending.needs_user == asked.needs_user
    assert store.list_events(mission.id) == []


def test_request_report_for_an_unknown_mission_raises(store):
    with pytest.raises(KeyError):
        store.request_report("m_nope")


def test_a_pending_report_keeps_a_done_mission_live(store):
    done, pending_done, sessionless = _mission(store), _mission(store), _mission(store)
    for mission in (done, pending_done):
        store.set_session(mission.id, f"devin-{mission.id}", None)
    store.mark_done(done.id)
    store.request_report(pending_done.id)
    store.mark_done(pending_done.id)
    store.request_report(sessionless.id)
    assert [m.id for m in store.live_missions()] == [pending_done.id]


def test_apply_sync_delivers_a_report(store):
    mission = _mission(store)
    store.request_report(mission.id)
    before = store.get_mission(mission.id)
    store.apply_sync(mission.id, _settled(REPORT), expected_status="working")
    after = store.get_mission(mission.id)
    assert after.report == REPORT
    assert (after.status, after.report_pending, after.report_requested_at, after.report_restore_done) == (
        "waiting", False, None, False)
    assert after.updated_at > before.updated_at


def test_apply_sync_returns_a_mission_to_done(store):
    mission = _mission(store)
    store.mark_done(mission.id)
    store.request_report(mission.id)
    store.apply_sync(mission.id, _settled(REPORT, status="done"), expected_status="working")
    after = store.get_mission(mission.id)
    assert (after.status, after.report, after.report_restore_done) == ("done", REPORT, False)


def test_a_failed_request_clears_pending_and_keeps_the_old_report(store):
    mission = _mission(store)
    store.request_report(mission.id)
    store.apply_sync(mission.id, _settled(REPORT), expected_status="working")
    store.request_report(mission.id)
    error = {"id": "error:report:1", "at": "2026-09-20T12:50:00Z", "kind": "error", "text": "The report did not arrive"}
    store.apply_sync(mission.id, _settled(None, new_events=[NewEvent(error)]), expected_status="working")
    after = store.get_mission(mission.id)
    assert (after.report, after.report_pending, after.report_requested_at, after.status) == (
        REPORT, False, None, "waiting")
    assert _ids(store, mission.id) == ["error:report:1"]


def test_a_report_in_a_sync_that_settles_nothing_is_not_stored(store):
    mission = _mission(store)
    store.request_report(mission.id)
    store.apply_sync(mission.id, SyncResult([], [], "working", None, report=REPORT), expected_status="working")
    after = store.get_mission(mission.id)
    assert (after.report, after.report_pending) == (None, True)


def test_a_settled_sync_does_nothing_when_no_report_is_pending(store):
    mission = _mission(store)
    store.apply_sync(mission.id, _settled(REPORT, status="working"), expected_status="working")
    after = store.get_mission(mission.id)
    assert (after.report, after.report_pending, after.updated_at) == (None, False, mission.updated_at)


def test_mark_done_while_a_report_is_pending_wins_and_the_report_still_lands(store):
    mission = _mission(store)
    store.request_report(mission.id)
    store.mark_done(mission.id)
    assert store.get_mission(mission.id).report_pending

    store.apply_sync(mission.id, _settled(REPORT, status="waiting"), expected_status="working")
    after = store.get_mission(mission.id)
    assert (after.status, after.report, after.report_pending) == ("done", REPORT, False)


def test_a_reply_while_a_report_is_pending_cancels_the_return_to_done(store):
    mission = _mission(store)
    store.mark_done(mission.id)
    store.request_report(mission.id)
    store.reopen(mission.id)
    reopened = store.get_mission(mission.id)
    assert (reopened.status, reopened.report_pending, reopened.report_restore_done) == ("working", True, False)

    # This sync was computed before the reply, when the mission was still due to go back to done.
    store.apply_sync(mission.id, _settled(REPORT, status="done"), expected_status="working")
    after = store.get_mission(mission.id)
    assert (after.status, after.report, after.report_pending) == ("working", REPORT, False)


def test_report_state_survives_a_restart(tmp_path):
    path = tmp_path / "k.db"
    first = Store(path, now=Clock())
    delivered, pending = _mission(first), _mission(first)
    first.request_report(delivered.id)
    first.apply_sync(delivered.id, _settled(REPORT), expected_status="working")
    first.mark_done(pending.id)
    first.request_report(pending.id)

    second = Store(path, now=Clock())
    assert second.get_mission(delivered.id).report == REPORT
    assert second.get_mission(pending.id) == first.get_mission(pending.id)
    assert second.get_mission(pending.id).report_restore_done


def test_a_database_from_before_reports_is_migrated_in_place(tmp_path):
    path = tmp_path / "old.db"
    with sqlite3.connect(path) as db:
        db.executescript(OLD_MISSIONS)
        db.execute(
            "insert into missions (id, title, hypothesis, prompt, status, created_at, updated_at, dataset_ids, "
            "session_id, needs_user) values ('m_old', 'Old', 'Does A lead B?', 'brief', 'waiting', "
            "'2026-09-19T10:00:00Z', '2026-09-19T11:00:00Z', '[\"gdelt\"]', 'devin-old', 'Drop it?')")
    db.close()

    store = Store(path, now=Clock())
    old = store.get_mission("m_old")
    assert (old.title, old.status, old.dataset_ids, old.needs_user) == ("Old", "waiting", ["gdelt"], "Drop it?")
    assert (old.report, old.report_pending, old.report_requested_at, old.report_restore_done) == (
        None, False, None, False)

    store.request_report("m_old")
    store.apply_sync("m_old", _settled(REPORT), expected_status="working")
    assert store.get_mission("m_old").report == REPORT
    newer = _mission(store)
    assert [m.id for m in store.list_missions()] == [newer.id, "m_old"]

    reopened = Store(path, now=Clock())
    assert reopened.get_mission("m_old").report == REPORT
