from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from server.artifacts import normalise_artifact, normalise_stats
from server.devin import Attachment, DevinMessage, SessionSnapshot

if TYPE_CHECKING:
    from server.store import MissionRow

STEP_STATES = ("active", "done")
CONCLUSION_ID = "conclusion"
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

    if output is not None:
        for step in _steps(output.get("steps")):
            thread.upsert(f"step:{step['stepId']}", "step", step)
        names = {attachment.name for attachment in attachments}
        for raw in _list(output.get("artifacts")):
            artifact = normalise_artifact(raw, mission_id=mission.id, attachments=names)
            if artifact is not None:
                thread.upsert(
                    f"artifact:{artifact['id']}", "artifact", {"artifact": artifact},
                    after_step=f"step:{raw.get('after_step')}",
                )

    if output is not None and (conclusion := _conclusion(output.get("conclusion"))):
        thread.upsert(CONCLUSION_ID, "conclusion", conclusion, replace_at_end=True)

    if snapshot.status == "error":
        if mission.status != "failed":
            errors = sum(event["kind"] == "error" for event in stored_events)
            thread.add(f"error:session:{errors + 1}", "error", {"text": _error_text(snapshot.detail)})
        return SyncResult(thread.new, thread.updated, "failed", None)

    needs_user = mission.needs_user if output is None else _needs_user(output.get("needs_user"), mission)
    waiting = snapshot.status in ("waiting", "finished") or needs_user is not None
    return SyncResult(thread.new, thread.updated, "waiting" if waiting else "working", needs_user)


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
            at = self._now if replace_at_end else stored["at"]
            self.updated.append(UpdatedEvent({"id": event_id, "at": at, "kind": kind, **payload}, replace_at_end))

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


def _needs_user(raw: object, mission: MissionRow) -> str | None:
    question = _text(raw)
    return question if question and question != mission.answered_needs_user else None


def _error_text(detail: str | None) -> str:
    if not detail or detail == "error":
        return "The Devin session ended with an error."
    return f"The Devin session stopped: {detail.replace('_', ' ')}."
