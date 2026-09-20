from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from server.artifacts import normalise_artifact, normalise_stats
from server.brief import REPORT_REQUEST
from server.devin import Attachment, DevinMessage, SessionSnapshot
from server.report import normalise_report

if TYPE_CHECKING:
    from server.store import MissionRow

STEP_STATES = ("active", "done")
TITLE_MAX = 60
CONCLUSION_ID = "conclusion"
REPORT_ID = "report"
REPORT_TIMEOUT_SECONDS = 5 * 60
REPORT_MISSING = "The report did not arrive"
# Below this length a containment match on the brief would be too easy to hit by accident.
MIN_PROMPT_MATCH = 40


@dataclass(frozen=True)
class NewEvent:
    event: dict
    # Id of the event this one goes directly after; None appends to the thread.
    after: str | None = None


@dataclass(frozen=True)
class UpdatedEvent:
    event: dict
    move_to_end: bool = False


@dataclass(frozen=True)
class SyncResult:
    new_events: list[NewEvent]
    updated_events: list[UpdatedEvent]
    status: str
    needs_user: str | None
    title: str | None = None
    # The report delivered by this sync, in the app's shape with `generatedAt`.
    report: dict | None = None
    # The pending report request ended here: delivered, given up on, or lost with the session.
    report_settled: bool = False


def sync(
    mission: MissionRow,
    stored_events: Sequence[dict],
    snapshot: SessionSnapshot,
    messages: Sequence[DevinMessage],
    attachments: Sequence[Attachment],
    *,
    now: str,
) -> SyncResult:
    """Diff a Devin snapshot against the stored thread. Pure, and idempotent once applied."""
    thread = _Thread(stored_events, now)
    output = snapshot.structured_output if isinstance(snapshot.structured_output, dict) else None

    # Structured output carries no timestamps, so order within one sync is a choice: Devin tends to
    # say what it is doing and then show it, so its words go first and the figures follow them.
    echoes = _Echoes(mission.prompt, stored_events)
    for message in messages:
        text = message.text.strip()
        if message.role == "devin" and text and not echoes.matches(text):
            thread.add(f"msg:{message.id}", "thought", {"text": text}, at=message.at or now)
    thread.raise_floor()

    artifact_ids = {event["artifact"]["id"] for event in stored_events if event["kind"] == "artifact"}
    if output is not None:
        for step in _steps(output.get("steps")):
            thread.upsert(f"step:{step['stepId']}", "step", step)
        names = {attachment.name for attachment in attachments}
        for raw in _list(output.get("artifacts")):
            artifact = normalise_artifact(raw, mission_id=mission.id, attachments=names)
            if artifact is not None:
                artifact_ids.add(artifact["id"])
                thread.upsert(
                    f"artifact:{artifact['id']}", "artifact", {"artifact": artifact},
                    after_step=f"step:{raw.get('after_step')}",
                )

    title = _title(output.get("title")) if output is not None else None

    if output is not None and (conclusion := _conclusion(output.get("conclusion"))):
        thread.upsert(CONCLUSION_ID, "conclusion", conclusion, replace_at_end=True)
    # The report marker closes the thread below the conclusion, so it is no reason to move the conclusion.
    thread.keep_last(CONCLUSION_ID, ignoring=REPORT_ID)

    report = _report(mission, output, artifact_ids, now) if mission.report_pending else None
    if report is not None:
        thread.put_last(REPORT_ID, "report")
    else:
        thread.keep_last(REPORT_ID)

    failed = snapshot.status == "error"
    settled = mission.report_pending and (report is not None or failed or _overdue(mission, now))
    errors = sum(event["kind"] == "error" for event in stored_events)
    if failed:
        if mission.status != "failed":
            thread.add(f"error:session:{errors + 1}", "error", {"text": _error_text(snapshot.detail)})
        return SyncResult(thread.new, thread.updated, "failed", None, title, report, settled)
    if settled and report is None:
        thread.add(f"error:report:{errors + 1}", "error", {"text": REPORT_MISSING})

    needs_user = mission.needs_user if output is None else _needs_user(output.get("needs_user"), mission)
    waiting = snapshot.status in ("waiting", "finished") or needs_user is not None
    status = "waiting" if waiting else "working"
    if mission.status == "done" or (settled and mission.report_restore_done):
        # Done missions are only synced for a report, which leaves them done or puts them back there.
        status, needs_user = "done", None
    elif mission.report_pending and not settled and needs_user is None:
        # Devin can take a moment to pick the request up, and until then its session still says waiting.
        status = "working"
    return SyncResult(thread.new, thread.updated, status, needs_user, title, report, settled)


class _Thread:
    """The stored thread plus this sync's changes, in the order the store will end up with."""

    def __init__(self, stored_events: Sequence[dict], now: str):
        self._now = now
        self._stored = {event["id"]: event for event in stored_events}
        self._order = [event["id"] for event in stored_events]
        self._kinds = {event["id"]: event["kind"] for event in stored_events}
        self._floor = self._order[-1] if self._order else None
        self._seen: set[str] = set()
        self.new: list[NewEvent] = []
        self.updated: list[UpdatedEvent] = []

    def add(self, event_id: str, kind: str, payload: dict, *, at: str | None = None) -> None:
        if event_id not in self._kinds:
            self._place({"id": event_id, "at": at or self._now, "kind": kind, **payload}, after=None)

    def raise_floor(self) -> None:
        """Nothing placed from here on may go above what is already in the thread."""
        self._floor = self._order[-1] if self._order else None

    def upsert(
        self, event_id: str, kind: str, payload: dict, *, after_step: str | None = None, replace_at_end: bool = False
    ) -> None:
        if event_id in self._seen:
            return
        self._seen.add(event_id)
        stored = self._stored.get(event_id)
        if stored is None:
            self._place({"id": event_id, "at": self._now, "kind": kind, **payload}, after=self._anchor(after_step))
        elif {key: value for key, value in stored.items() if key not in ("id", "at", "kind")} != payload:
            if replace_at_end:
                self._to_end({"id": event_id, "at": self._now, "kind": kind, **payload})
            else:
                self.updated.append(UpdatedEvent({"id": event_id, "at": stored["at"], "kind": kind, **payload}))

    def keep_last(self, event_id: str, *, ignoring: str | None = None) -> None:
        """A conclusion closes Devin's turn, so anything Devin adds after it slides in above.
        Once the user has replied below it, that turn is over and it stays where it is."""
        stored = self._stored.get(event_id)
        if stored is None or any(update.event["id"] == event_id for update in self.updated):
            return
        following = [later for later in self._order[self._order.index(event_id) + 1:] if later != ignoring]
        if following and "user_message" not in (self._kinds[later] for later in following):
            self._to_end(stored)

    def put_last(self, event_id: str, kind: str) -> None:
        """Make a payload-free marker the last event of the thread, stamped with this sync's time."""
        event = {"id": event_id, "at": self._now, "kind": kind}
        if event_id not in self._kinds:
            self._place(event, after=None)
            # The store adds new events before it moves old ones, so without a move of its own
            # a new marker would end up above anything else this sync sends to the end.
            if not any(update.move_to_end for update in self.updated):
                return
        self._to_end(event)

    def _anchor(self, after_step: str | None) -> str | None:
        """Where an artifact goes: after its step and that step's earlier artifacts, but never above
        the floor: events from a previous sync, which the user may have read past, and this sync's thoughts."""
        if after_step not in self._kinds:
            return None
        index = self._order.index(after_step)
        if self._floor is not None:
            index = max(index, self._order.index(self._floor))
        while index + 1 < len(self._order) and self._kinds[self._order[index + 1]] == "artifact":
            index += 1
        return self._order[index]

    def _to_end(self, event: dict) -> None:
        self._order.remove(event["id"])
        self._order.append(event["id"])
        self.updated.append(UpdatedEvent(event, move_to_end=True))

    def _place(self, event: dict, *, after: str | None) -> None:
        if after is None:
            self._order.append(event["id"])
        else:
            self._order.insert(self._order.index(after) + 1, event["id"])
        self._kinds[event["id"]] = event["kind"]
        self.new.append(NewEvent(event, after))


class _Echoes:
    """Recognises our own words coming back from Devin's message list. Role detection should
    already catch them; this is the backstop that keeps the brief (and any reference in it)
    out of the thread if Devin's message shape ever changes."""

    def __init__(self, prompt: str, stored_events: Sequence[dict]):
        self._prompt = _squash(prompt)
        self._sent = {_squash(event["text"]) for event in stored_events if event["kind"] == "user_message"}
        self._sent.add(_squash(REPORT_REQUEST))

    def matches(self, text: str) -> bool:
        text = _squash(text)
        if text in self._sent or text == self._prompt:
            return True
        return len(self._prompt) >= MIN_PROMPT_MATCH and self._prompt in text


def _squash(text: str) -> str:
    return " ".join(text.split())


def _list(value: object) -> list:
    return value if isinstance(value, list) else []


def _text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _steps(raw: object) -> list[dict]:
    steps = []
    for item in _list(raw):
        if not isinstance(item, dict):
            continue
        step_id, label, state = _text(item.get("id")), _text(item.get("label")), item.get("state")
        if step_id and label and state in STEP_STATES:
            steps.append({"stepId": step_id, "label": label, "state": state})
    return steps


def _conclusion(raw: object) -> dict | None:
    if not isinstance(raw, dict) or not _text(raw.get("verdict")):
        return None
    return {
        "verdict": _text(raw.get("verdict")),
        "summary": _text(raw.get("summary")),
        "stats": normalise_stats(raw.get("stats")),
    }


def _report(mission: MissionRow, output: dict | None, artifact_ids: set[str], now: str) -> dict | None:
    """The report to deliver now, if there is one."""
    found = normalise_report(output.get("report"), artifact_ids) if output is not None else None
    if found is None:
        return None
    stored = {key: value for key, value in (mission.report or {}).items() if key != "generatedAt"}
    # An unchanged report is most likely the previous one still sitting in the output, so it only
    # counts once Devin has had its time to write another.
    if found == stored and not _overdue(mission, now):
        return None
    return {**found, "generatedAt": now}


def _overdue(mission: MissionRow, now: str) -> bool:
    try:
        waited = _moment(now) - _moment(mission.report_requested_at)
    except (TypeError, ValueError):
        return True
    return waited.total_seconds() > REPORT_TIMEOUT_SECONDS


def _moment(stamp: str | None) -> datetime:
    return datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ")


def _title(raw: object) -> str | None:
    title = _text(raw).rstrip(".")[:TITLE_MAX].strip()
    return title or None


def _needs_user(raw: object, mission: MissionRow) -> str | None:
    question = _text(raw)
    return question if question and question != mission.answered_needs_user else None


def _error_text(detail: str | None) -> str:
    if not detail or detail == "error":
        return "The Devin session ended with an error."
    return f"The Devin session stopped: {detail.replace('_', ' ')}."
