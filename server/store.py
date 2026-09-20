from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from server.sync import SyncResult

LIVE_STATUSES = ("working", "waiting")

SCHEMA = """
create table if not exists missions (
    seq integer primary key autoincrement,
    id text not null unique,
    title text not null,
    hypothesis text not null,
    reference text,
    prompt text not null,
    status text not null,
    created_at text not null,
    updated_at text not null,
    dataset_ids text not null,
    session_id text,
    session_url text,
    needs_user text,
    answered_needs_user text,
    failures integer not null default 0
);
create table if not exists events (
    mission_id text not null,
    id text not null,
    position integer not null,
    at text not null,
    kind text not null,
    payload text not null,
    primary key (mission_id, id)
);
create index if not exists events_thread on events (mission_id, position);
create table if not exists datasets (
    seq integer primary key autoincrement,
    id text not null unique,
    name text not null,
    url text not null,
    kind text not null,
    series_count integer not null,
    date_range text not null,
    synced_at text not null
);
"""

SEED_DATASETS = (
    ("gdelt", "GDELT events", "https://www.gdeltproject.org", "events", 42, "Mar 2025 – Sep 2026"),
    ("yahoo", "Yahoo Finance", "https://finance.yahoo.com", "markets", 31, "Jan 2024 – Sep 2026"),
    ("open-meteo", "Open-Meteo weather", "https://open-meteo.com", "weather", 18, "Jan 2024 – Sep 2026"),
    ("cams", "CAMS air quality", "https://atmosphere.copernicus.eu", "air", 12, "Jun 2024 – Sep 2026"),
)

_MISSION_COLUMNS = (
    "id, title, hypothesis, reference, prompt, status, created_at, updated_at, dataset_ids, "
    "session_id, session_url, needs_user, answered_needs_user, failures"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass(frozen=True)
class MissionRow:
    id: str
    title: str
    hypothesis: str
    reference: str | None
    prompt: str
    status: str
    created_at: str
    updated_at: str
    dataset_ids: list[str]
    session_id: str | None
    session_url: str | None
    needs_user: str | None
    # The question the user last replied to, so a stale copy of it in Devin's
    # structured output does not flip the mission straight back to waiting.
    answered_needs_user: str | None
    failures: int


class Store:
    """SQLite persistence shared by the request threads and the poller."""

    def __init__(self, path: str | Path, *, now: Callable[[], str] = utc_now):
        self._now = now
        self._lock = threading.RLock()
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        with self._lock, self._db:
            self._db.executescript(SCHEMA)
            self._seed_datasets()

    # ---------- missions ----------

    def create_mission(
        self, hypothesis: str, *, title: str, dataset_ids: list[str], reference: str | None, prompt: str
    ) -> MissionRow:
        mission_id = f"m_{uuid.uuid4().hex[:8]}"
        now = self._now()
        with self._lock, self._db:
            self._db.execute(
                "insert into missions (id, title, hypothesis, reference, prompt, status, created_at, "
                "updated_at, dataset_ids) values (?, ?, ?, ?, ?, 'working', ?, ?, ?)",
                (mission_id, title, hypothesis, reference, prompt, now, now, json.dumps(dataset_ids)),
            )
        return self._require(mission_id)

    def get_mission(self, mission_id: str) -> MissionRow | None:
        with self._lock:
            row = self._db.execute(
                f"select {_MISSION_COLUMNS} from missions where id = ?", (mission_id,)
            ).fetchone()
        return _mission(row) if row else None

    def list_missions(self) -> list[MissionRow]:
        with self._lock:
            rows = self._db.execute(f"select {_MISSION_COLUMNS} from missions order by seq desc").fetchall()
        return [_mission(row) for row in rows]

    def live_missions(self) -> list[MissionRow]:
        """Missions the poller should sync: also what it resumes after a restart."""
        return [m for m in self.list_missions() if m.status in LIVE_STATUSES and m.session_id]

    def set_session(self, mission_id: str, session_id: str, session_url: str | None) -> None:
        with self._lock, self._db:
            self._update(mission_id, session_id=session_id, session_url=session_url)

    def fail(self, mission_id: str, message: str) -> None:
        with self._lock, self._db:
            self._insert(mission_id, self._event("error", {"text": message}), after=None)
            self._update(mission_id, status="failed", needs_user=None)

    def mark_done(self, mission_id: str) -> None:
        with self._lock, self._db:
            self._update(mission_id, status="done", needs_user=None)

    def reopen(self, mission_id: str) -> None:
        with self._lock, self._db:
            mission = self._require(mission_id)
            self._update(
                mission_id,
                status="working",
                needs_user=None,
                answered_needs_user=mission.needs_user or mission.answered_needs_user,
                failures=0,
            )

    def record_failure(self, mission_id: str) -> int:
        with self._lock, self._db:
            self._db.execute("update missions set failures = failures + 1 where id = ?", (mission_id,))
            return self._require(mission_id).failures

    def clear_failures(self, mission_id: str) -> None:
        with self._lock, self._db:
            self._db.execute("update missions set failures = 0 where id = ?", (mission_id,))

    # ---------- events ----------

    def append_event(
        self, mission_id: str, kind: str, payload: dict, *, event_id: str | None = None, at: str | None = None
    ) -> dict:
        event = self._event(kind, payload, event_id=event_id, at=at)
        with self._lock, self._db:
            self._insert(mission_id, event, after=None)
            self._touch(mission_id)
        return event

    def list_events(self, mission_id: str) -> list[dict]:
        with self._lock:
            rows = self._db.execute(
                "select id, at, kind, payload from events where mission_id = ? order by position",
                (mission_id,),
            ).fetchall()
        return [{"id": r["id"], "at": r["at"], "kind": r["kind"], **json.loads(r["payload"])} for r in rows]

    def apply_sync(self, mission_id: str, result: SyncResult, *, expected_status: str) -> None:
        """Persist a sync. `expected_status` is the status the sync was computed from:
        if the user marked the mission done or replied meanwhile, their status wins."""
        with self._lock, self._db:
            mission = self._require(mission_id)
            changed = False
            for new in result.new_events:
                changed |= self._insert(mission_id, new.event, after=new.after)
            for updated in result.updated_events:
                changed |= self._replace(mission_id, updated.event, move_to_end=updated.move_to_end)
            if mission.status == expected_status and (
                (result.status, result.needs_user) != (mission.status, mission.needs_user)
            ):
                self._update(mission_id, status=result.status, needs_user=result.needs_user)
            elif changed:
                self._touch(mission_id)

    # ---------- datasets ----------

    def list_datasets(self) -> list[dict]:
        with self._lock:
            rows = self._db.execute("select * from datasets order by seq desc").fetchall()
        return [_dataset(row) for row in rows]

    def get_datasets(self, dataset_ids: Iterable[str]) -> list[dict]:
        by_id = {dataset["id"]: dataset for dataset in self.list_datasets()}
        return [by_id[i] for i in dict.fromkeys(dataset_ids) if i in by_id]

    def add_dataset(self, name: str, url: str) -> dict:
        dataset_id = f"d_{uuid.uuid4().hex[:8]}"
        with self._lock, self._db:
            self._db.execute(
                "insert into datasets (id, name, url, kind, series_count, date_range, synced_at) "
                "values (?, ?, ?, 'other', 0, '', ?)",
                (dataset_id, name, url, self._now()),
            )
        return next(d for d in self.list_datasets() if d["id"] == dataset_id)

    # ---------- internals ----------

    def _seed_datasets(self) -> None:
        if self._db.execute("select 1 from datasets limit 1").fetchone():
            return
        now = self._now()
        # Listed newest first, so insert the seeds backwards to show them in this order.
        for seed in reversed(SEED_DATASETS):
            self._db.execute(
                "insert into datasets (id, name, url, kind, series_count, date_range, synced_at) "
                "values (?, ?, ?, ?, ?, ?, ?)",
                (*seed, now),
            )

    def _require(self, mission_id: str) -> MissionRow:
        mission = self.get_mission(mission_id)
        if mission is None:
            raise KeyError(mission_id)
        return mission

    def _event(self, kind: str, payload: dict, *, event_id: str | None = None, at: str | None = None) -> dict:
        return {"id": event_id or f"{kind}:{uuid.uuid4().hex[:10]}", "at": at or self._now(), "kind": kind, **payload}

    def _update(self, mission_id: str, **fields: object) -> None:
        assignments = ", ".join(f"{name} = ?" for name in fields)
        self._db.execute(
            f"update missions set {assignments}, updated_at = ? where id = ?",
            (*fields.values(), self._now(), mission_id),
        )

    def _touch(self, mission_id: str) -> None:
        self._db.execute("update missions set updated_at = ? where id = ?", (self._now(), mission_id))

    def _position(self, mission_id: str, event_id: str) -> int | None:
        row = self._db.execute(
            "select position from events where mission_id = ? and id = ?", (mission_id, event_id)
        ).fetchone()
        return row["position"] if row else None

    def _end(self, mission_id: str) -> int:
        row = self._db.execute(
            "select coalesce(max(position), 0) + 1 as next from events where mission_id = ?", (mission_id,)
        ).fetchone()
        return row["next"]

    def _insert(self, mission_id: str, event: dict, *, after: str | None) -> bool:
        if self._position(mission_id, event["id"]) is not None:
            return False
        anchor = self._position(mission_id, after) if after else None
        if anchor is None:
            position = self._end(mission_id)
        else:
            position = anchor + 1
            self._db.execute(
                "update events set position = position + 1 where mission_id = ? and position >= ?",
                (mission_id, position),
            )
        self._db.execute(
            "insert into events (mission_id, id, position, at, kind, payload) values (?, ?, ?, ?, ?, ?)",
            (mission_id, event["id"], position, event["at"], event["kind"], json.dumps(_payload(event))),
        )
        return True

    def _replace(self, mission_id: str, event: dict, *, move_to_end: bool) -> bool:
        position = self._position(mission_id, event["id"])
        if position is None:
            return False
        if move_to_end:
            position = self._end(mission_id)
        self._db.execute(
            "update events set position = ?, at = ?, kind = ?, payload = ? where mission_id = ? and id = ?",
            (position, event["at"], event["kind"], json.dumps(_payload(event)), mission_id, event["id"]),
        )
        return True


def _payload(event: dict) -> dict:
    return {key: value for key, value in event.items() if key not in ("id", "at", "kind")}


def _mission(row: sqlite3.Row) -> MissionRow:
    fields = dict(row)
    fields["dataset_ids"] = json.loads(fields["dataset_ids"])
    return MissionRow(**fields)


def _dataset(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "url": row["url"],
        "kind": row["kind"],
        "seriesCount": row["series_count"],
        "dateRange": row["date_range"],
        "syncedAt": row["synced_at"],
    }
