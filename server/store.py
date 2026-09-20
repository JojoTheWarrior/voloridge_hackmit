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

LEGACY_DATASETS = (
    ("gdelt", "GDELT events", "https://www.gdeltproject.org", "events", 42, "Mar 2025 – Sep 2026"),
    ("yahoo", "Yahoo Finance", "https://finance.yahoo.com", "markets", 31, "Jan 2024 – Sep 2026"),
    ("open-meteo", "Open-Meteo weather", "https://open-meteo.com", "weather", 18, "Jan 2024 – Sep 2026"),
    ("cams", "CAMS air quality", "https://atmosphere.copernicus.eu", "air", 12, "Jun 2024 – Sep 2026"),
)

STARTER_DATASETS = json.loads((Path(__file__).resolve().parents[1] / "shared/starter-datasets.json").read_text())
SEED_DATASETS = tuple((d["id"], d["name"], d["url"], d["kind"], 0, "") for d in STARTER_DATASETS)

# Columns added since the first release. `create table if not exists` leaves an existing
# table alone, so these are added one by one to whatever database is already on disk.
ADDED_MISSION_COLUMNS = (
    ("report", "text"),
    ("report_pending", "integer not null default 0"),
    ("report_requested_at", "text"),
    ("report_restore_done", "integer not null default 0"),
    ("explorer", "text"),
    ("explorer_pending", "integer not null default 0"),
    ("explorer_requested_at", "text"),
    ("explorer_restore_done", "integer not null default 0"),
    ("explorer_seen_version", "integer not null default 0"),
    ("auto_phase", "text not null default ''"),
    ("revision", "integer not null default 0"),
    ("last_snapshot", "text not null default ''"),
    ("awaiting_at", "text"),
    ("auto_nudges", "integer not null default 0"),
)

_MISSION_COLUMNS = (
    "id, title, hypothesis, reference, prompt, status, created_at, updated_at, dataset_ids, "
    "session_id, session_url, needs_user, answered_needs_user, failures, "
    "report, report_pending, report_requested_at, report_restore_done, "
    "explorer, explorer_pending, explorer_requested_at, explorer_restore_done, explorer_seen_version, "
    "auto_phase, revision, last_snapshot, awaiting_at, auto_nudges"
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
    # The last delivered report, in the app's camelCase shape.
    report: dict | None
    report_pending: bool
    report_requested_at: str | None
    # The mission was done when the report was requested, and goes back to done once that is settled.
    report_restore_done: bool
    # The last explorer build that was unpacked: version, title, description, entry, builtAt.
    explorer: dict | None
    explorer_pending: bool
    explorer_requested_at: str | None
    explorer_restore_done: bool
    # The highest version Devin has offered so far, used or rejected. Only a higher one is a new build,
    # so an archive that was turned down is not fetched again when the user asks for another.
    explorer_seen_version: int
    auto_phase: str = ""
    revision: int = 0
    last_snapshot: str = ""
    awaiting_at: str | None = None
    auto_nudges: int = 0

    @property
    def awaiting(self) -> bool:
        """Devin owes this mission a report or an explorer, so it is followed whatever its status."""
        return self.report_pending or self.explorer_pending

    @property
    def restore_done(self) -> bool:
        return self.report_restore_done or self.explorer_restore_done


class Store:
    """SQLite persistence shared by the request threads and the poller."""

    def __init__(self, path: str | Path, *, now: Callable[[], str] = utc_now):
        self._now = now
        self._lock = threading.RLock()
        self._run_locks: dict[str, threading.RLock] = {}
        # Absolute, because explorer files are handed to Flask, which resolves relative paths against the package.
        path = Path(path).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        self._explorers = path.parent / "explorers"
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        with self._lock, self._db:
            self._db.executescript(SCHEMA)
            self._migrate()
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
        """Missions the poller should sync: also what it resumes after a restart.
        A mission marked done while a report or an explorer is being made is followed until that lands."""
        return [m for m in self.list_missions() if (m.status in LIVE_STATUSES or m.awaiting) and m.session_id]

    def set_session(self, mission_id: str, session_id: str, session_url: str | None) -> None:
        with self._lock, self._db:
            self._update(mission_id, session_id=session_id, session_url=session_url)

    def fail(self, mission_id: str, message: str) -> None:
        with self._lock, self._db:
            self._insert(mission_id, self._event("error", {"text": message}), after=None)
            self._update(mission_id, status="failed", needs_user=None)

    def mark_done(self, mission_id: str) -> None:
        with self._lock, self._db:
            mission = self._require(mission_id)
            self._update(mission_id, status="done", needs_user=None, revision=mission.revision + 1,
                         auto_phase="complete" if mission.auto_phase else "", awaiting_at=None)

    def run_lock(self, mission_id: str):
        """Serialize commands for one session without blocking other missions or database reads."""
        with self._lock:
            return self._run_locks.setdefault(mission_id, threading.RLock())

    def set_autonomy(self, mission_id: str, **fields: object) -> None:
        with self._lock, self._db:
            self._update(mission_id, **fields)

    def record_snapshot(self, mission_id: str, fingerprint: str) -> None:
        # A poll is not itself research activity: do not advance the visible last-update timestamp.
        with self._lock, self._db:
            self._db.execute("update missions set last_snapshot = ? where id = ?", (fingerprint, mission_id))

    def reopen(self, mission_id: str) -> None:
        with self._lock, self._db:
            mission = self._require(mission_id)
            self._update(
                mission_id,
                status="working",
                needs_user=None,
                answered_needs_user=mission.needs_user or mission.answered_needs_user,
                failures=0,
                revision=mission.revision + 1,
                auto_phase="research" if mission.auto_phase else "",
                awaiting_at=self._now(),
                auto_nudges=0,
                # A reply is the user carrying on, so a pending report or explorer no longer closes the mission.
                report_restore_done=0,
                explorer_restore_done=0,
            )

    def request_report(self, mission_id: str) -> None:
        with self._lock, self._db:
            mission = self._require(mission_id)
            self._update(
                mission_id,
                status="working",
                report_pending=1,
                report_requested_at=self._now(),
                report_restore_done=int(mission.status == "done" or mission.restore_done),
                failures=0,
            )

    def request_explorer(self, mission_id: str) -> None:
        with self._lock, self._db:
            mission = self._require(mission_id)
            self._update(
                mission_id,
                status="working",
                explorer_pending=1,
                explorer_requested_at=self._now(),
                explorer_restore_done=int(mission.status == "done" or mission.restore_done),
                failures=0,
            )

    def explorer_dir(self, mission_id: str, version: int) -> Path:
        """Where one build's files live. Older versions stay on disk next to it."""
        return self._explorers / mission_id / str(version)

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

    def apply_sync(
        self, mission_id: str, result: SyncResult, *, expected_status: str, expected_revision: int | None = None
    ) -> bool:
        """Persist a sync. `expected_status` is the status the sync was computed from:
        if the user marked the mission done or replied meanwhile, their status wins."""
        with self._lock, self._db:
            mission = self._require(mission_id)
            if expected_revision is not None and mission.revision != expected_revision:
                return False
            changed = False
            if result.report_settled and mission.report_pending:
                self._settle_report(mission_id, result.report)
                changed = True
            if result.explorer_settled and mission.explorer_pending:
                self._settle_explorer(mission, result.explorer, result.explorer_seen)
                changed = True
            for new in result.new_events:
                changed |= self._insert(mission_id, new.event, after=new.after)
            for updated in result.updated_events:
                changed |= self._replace(mission_id, updated.event, move_to_end=updated.move_to_end)
            if result.title and result.title != mission.title:
                self._update(mission_id, title=result.title)
                changed = True
            # A sync only closes a mission to put it back where a report or an explorer request found
            # it, and a reply that landed while the sync was being computed has called that off.
            user_acted = mission.status != expected_status or (result.status == "done" and not mission.restore_done)
            if not user_acted and (result.status, result.needs_user) != (mission.status, mission.needs_user):
                self._update(mission_id, status=result.status, needs_user=result.needs_user)
            elif changed:
                self._touch(mission_id)
            return True

    # ---------- datasets ----------

    def list_datasets(self) -> list[dict]:
        with self._lock:
            rows = self._db.execute("select * from datasets where archived = 0 order by seq desc").fetchall()
        return [_dataset(row) for row in rows]

    def get_datasets(self, dataset_ids: Iterable[str]) -> list[dict]:
        # Old missions can still resolve their original sources after the starter catalog changes.
        with self._lock:
            by_id = {row["id"]: _dataset(row) for row in self._db.execute("select * from datasets")}
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

    def _migrate(self) -> None:
        dataset_columns = {row["name"] for row in self._db.execute("pragma table_info(datasets)")}
        if "archived" not in dataset_columns:
            self._db.execute("alter table datasets add column archived integer not null default 0")
        existing = {row["name"] for row in self._db.execute("pragma table_info(missions)")}
        for name, definition in ADDED_MISSION_COLUMNS:
            if name not in existing:
                self._db.execute(f"alter table missions add column {name} {definition}")

    def _settle_report(self, mission_id: str, report: dict | None) -> None:
        fields: dict = {"report_pending": 0, "report_requested_at": None, "report_restore_done": 0}
        if report is not None:
            fields["report"] = json.dumps(report)
        self._update(mission_id, **fields)

    def _settle_explorer(self, mission: MissionRow, explorer: dict | None, seen: int | None) -> None:
        fields: dict = {"explorer_pending": 0, "explorer_requested_at": None, "explorer_restore_done": 0}
        if explorer is not None:
            fields["explorer"] = json.dumps(explorer)
        if seen is not None:
            fields["explorer_seen_version"] = max(seen, mission.explorer_seen_version)
        self._update(mission.id, **fields)

    def _seed_datasets(self) -> None:
        now = self._now()
        # Preserve the original source records for mission history, but retire untouched
        # old defaults from the picker. Never remove or replace a user-linked source.
        for seed in LEGACY_DATASETS:
            self._db.execute(
                "insert or ignore into datasets (id, name, url, kind, series_count, date_range, synced_at, archived) "
                "values (?, ?, ?, ?, ?, ?, ?, 1)", (*seed, now),
            )
            if seed[0] != "open-meteo":
                self._db.execute("update datasets set archived = 1 where id = ? and name = ? and url = ?", seed[:3])
        # Weather remains a starter; remove its former illustrative series/range metadata.
        weather = next(seed for seed in SEED_DATASETS if seed[0] == "open-meteo")
        self._db.execute(
            "update datasets set name = ?, url = ?, kind = ?, series_count = 0, date_range = '', archived = 0 "
            "where id = 'open-meteo' and name = 'Open-Meteo weather'",
            weather[1:4],
        )
        # Listed newest first, so insert the seeds backwards to show them in this order.
        for seed in reversed(SEED_DATASETS):
            self._db.execute(
                "insert or ignore into datasets (id, name, url, kind, series_count, date_range, synced_at) "
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
    fields["report"] = json.loads(fields["report"]) if fields["report"] else None
    fields["report_pending"] = bool(fields["report_pending"])
    fields["report_restore_done"] = bool(fields["report_restore_done"])
    fields["explorer"] = json.loads(fields["explorer"]) if fields["explorer"] else None
    fields["explorer_pending"] = bool(fields["explorer_pending"])
    fields["explorer_restore_done"] = bool(fields["explorer_restore_done"])
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
