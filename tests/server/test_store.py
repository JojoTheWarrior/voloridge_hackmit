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
