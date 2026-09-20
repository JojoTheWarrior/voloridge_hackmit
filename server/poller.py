from __future__ import annotations

import json
import logging
import threading
from collections.abc import Callable
from dataclasses import replace
from hashlib import sha256

from server.artifacts import ATTACHMENT_PREFIX
from server.autonomy import advance, waiting_for_start
from server.devin import (
    Attachment,
    AttachmentRejected,
    AttachmentUnavailable,
    DevinClient,
    DevinUnavailable,
)
from server.explorer import ArchiveRejected, unpack
from server.store import MissionRow, Store, utc_now
from server.sync import (
    ExplorerDue,
    ExplorerOutcome,
    explorer_announced,
    explorer_due,
    sync,
)

log = logging.getLogger(__name__)

LOST_CONTACT_AFTER = 5
LOST_CONTACT = "Lost contact with Devin, still retrying"


class Poller:
    """Keeps every live mission's thread in step with its Devin session."""

    def __init__(
        self,
        store: Store,
        client: DevinClient,
        *,
        interval: float = 2.0,
        sleep: Callable[[float], object] | None = None,
        now: Callable[[], str] = utc_now,
    ):
        self._store = store
        self._client = client
        self._interval = interval
        self._stop = threading.Event()
        self._sleep = sleep or self._stop.wait
        self._now = now

    def tick(self) -> None:
        for mission in self._store.live_missions():
            try:
                self._sync(mission)
            except DevinUnavailable as exc:
                self._lost_contact(mission, exc)
            except Exception:
                log.exception("sync failed for mission %s", mission.id)

    def run(self) -> None:
        while not self._stop.is_set():
            try:
                self.tick()
            except Exception:
                log.exception("poller tick failed")
            self._sleep(self._interval)

    def start(self) -> threading.Thread:
        self._stop.clear()
        thread = threading.Thread(target=self.run, name="kingdom-poller", daemon=True)
        thread.start()
        return thread

    def stop(self) -> None:
        self._stop.set()

    def _sync(self, mission: MissionRow) -> None:
        snapshot = self._client.get_session(mission.session_id)
        messages = self._client.list_messages(mission.session_id)
        # Most runs never attach a file, so skip the extra request until one is referenced or awaited.
        refers_to_attachment = ATTACHMENT_PREFIX in json.dumps(snapshot.structured_output or {})
        awaits_archive = explorer_announced(mission, snapshot) is not None
        lists = refers_to_attachment or awaits_archive
        attachments = self._client.list_attachments(mission.session_id) if lists else []
        due = explorer_due(mission, snapshot, attachments)
        explorer = self._fetch_explorer(mission, due, attachments) if due is not None else None
        result = sync(
            mission, self._store.list_events(mission.id), snapshot, messages, attachments,
            now=self._now(), explorer=explorer,
        )
        fingerprint = sha256(json.dumps([
            snapshot.structured_output,
            [(m.id, m.text) for m in messages if m.role == "devin"],
        ], sort_keys=True).encode()).hexdigest()
        with self._store.run_lock(mission.id):
            current = self._store.get_mission(mission.id)
            if current is None or current.revision != mission.revision:
                return
            queued = waiting_for_start(mission, snapshot, fingerprint, self._now())
            if queued or (mission.auto_phase and result.status == "waiting"):
                result = replace(result, status="working", needs_user=None)
            if not self._store.apply_sync(
                mission.id, result, expected_status=mission.status, expected_revision=mission.revision
            ):
                return
            if mission.failures:
                self._store.clear_failures(mission.id)
            if queued:
                # Preserve the pre-message snapshot until Devin starts or emits genuinely new output.
                if not mission.last_snapshot:
                    self._store.record_snapshot(mission.id, fingerprint)
                return
            if (mission.awaiting_at and snapshot.status in ("waiting", "finished")
                    and fingerprint == mission.last_snapshot):
                self._store.fail(mission.id, "Devin has not picked up the latest message after two minutes. Send a message to retry.")
                return
            self._store.record_snapshot(mission.id, fingerprint)
            if mission.awaiting_at:
                self._store.set_autonomy(mission.id, awaiting_at=None)
            advance(self._store, self._client, self._store.get_mission(mission.id), snapshot, now=self._now())

    def _fetch_explorer(
        self, mission: MissionRow, due: ExplorerDue, attachments: list[Attachment]
    ) -> ExplorerOutcome | None:
        """Download and unpack a due build. None means it could not be fetched this time and is worth
        another try; the rest of the sync goes ahead either way."""
        archive = next(item for item in attachments if item.name == due.archive)
        try:
            data = self._client.download_file(archive)
            unpack(data, self._store.explorer_dir(mission.id, due.version), entry=due.entry)
        except (AttachmentUnavailable, DevinUnavailable, OSError) as exc:
            log.warning("explorer archive for mission %s not fetched yet: %s", mission.id, exc)
            return None
        except AttachmentRejected as exc:
            return ExplorerOutcome(due, rejected=f"its archive could not be downloaded ({exc})")
        except ArchiveRejected as exc:
            return ExplorerOutcome(due, rejected=str(exc))
        return ExplorerOutcome(due)

    def _lost_contact(self, mission: MissionRow, exc: DevinUnavailable) -> None:
        log.warning("Devin unavailable for mission %s: %s", mission.id, exc)
        if self._store.record_failure(mission.id) == LOST_CONTACT_AFTER:
            self._store.append_event(mission.id, "error", {"text": LOST_CONTACT})
