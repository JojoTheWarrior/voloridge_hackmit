from __future__ import annotations

import json
import logging
import threading
from collections.abc import Callable

from server.artifacts import ATTACHMENT_PREFIX
from server.devin import DevinClient, DevinUnavailable
from server.store import MissionRow, Store, utc_now
from server.sync import sync

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
        interval: float = 5.0,
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
        # Most runs never attach a file, so skip the extra request until one is referenced.
        refers_to_attachment = ATTACHMENT_PREFIX in json.dumps(snapshot.structured_output or {})
        attachments = self._client.list_attachments(mission.session_id) if refers_to_attachment else []
        result = sync(
            mission, self._store.list_events(mission.id), snapshot, messages, attachments, now=self._now()
        )
        self._store.apply_sync(mission.id, result, expected_status=mission.status)
        if mission.failures:
            self._store.clear_failures(mission.id)

    def _lost_contact(self, mission: MissionRow, exc: DevinUnavailable) -> None:
        log.warning("Devin unavailable for mission %s: %s", mission.id, exc)
        if self._store.record_failure(mission.id) == LOST_CONTACT_AFTER:
            self._store.append_event(mission.id, "error", {"text": LOST_CONTACT})
