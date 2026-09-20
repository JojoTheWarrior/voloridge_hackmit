"""Bounded recovery of routine research pauses and automatic final-report delivery."""
from __future__ import annotations

from datetime import datetime

from server.brief import REPORT_REQUEST
from server.devin import DevinClient, DevinUnavailable, SessionSnapshot
from server.store import MissionRow, Store

CONTINUE = """Kingdom runs this research autonomously. Follow the user's latest direction. Unless the
user explicitly asked you to pause or stop, continue to a defensible conclusion without asking for
routine decisions or plan approval. Choose reasonable methods and assumptions and explain them.
Use accessible public alternatives for blocked sources; do not bypass access controls, approve
restricted operations, contact anyone, or expand the user's scope. If blocked, conclude with the
partial evidence and limitations. Publish concise progress summaries and artifacts as you work,
not private internal reasoning. Clear stale needs_user and conclusion when continuing. Set
run_status to working, complete at the conclusion, or paused only at the user's explicit request.
Kingdom will request the final report automatically. Keep the session available for follow-ups."""
MAX_NUDGES = 2
START_TIMEOUT = 120


def waiting_for_start(mission: MissionRow, snapshot: SessionSnapshot, fingerprint: str, now: str) -> bool:
    """A queued message can briefly leave the API reporting the previous turn's waiting state."""
    if not mission.awaiting_at or snapshot.status in ("running", "error"):
        return False
    unchanged = fingerprint == mission.last_snapshot or not mission.last_snapshot
    return unchanged and (datetime.fromisoformat(now) - datetime.fromisoformat(mission.awaiting_at)).total_seconds() < START_TIMEOUT


def advance(store: Store, client: DevinClient, mission: MissionRow, snapshot: SessionSnapshot, *, now: str) -> None:
    """Called under the session lock after a fresh snapshot is applied. Commands never repeat per poll."""
    if not mission.auto_phase or mission.status in ("done", "failed"):
        return
    output = snapshot.structured_output or {}
    if snapshot.status in ("waiting", "finished") and (
        output.get("run_status") == "paused" or snapshot.detail == "user_request"
    ):
        store.set_autonomy(mission.id, auto_phase="paused", status="waiting", needs_user="Paused at your request")
        return
    if mission.auto_phase == "paused":
        return
    if mission.auto_phase == "adopt":
        _send(store, client, mission, CONTINUE, now=now, phase="research")
        return
    if mission.awaiting:
        return
    if mission.auto_phase == "report":
        if mission.report:
            store.mark_done(mission.id)
        else:
            store.fail(mission.id, "Research finished, but the final report could not be delivered. You can retry it below.")
        return
    if snapshot.status not in ("waiting", "finished"):
        return
    conclusion = output.get("conclusion")
    if isinstance(conclusion, dict) and conclusion.get("verdict"):
        if _send(store, client, mission, REPORT_REQUEST, now=now, phase="report"):
            store.request_report(mission.id)
        return
    if mission.auto_nudges >= MAX_NUDGES:
        store.fail(mission.id, "Devin could not continue after two automatic recovery attempts. Send a new direction to retry.")
        return
    if _send(store, client, mission, CONTINUE, now=now, phase="research"):
        store.set_autonomy(mission.id, auto_nudges=mission.auto_nudges + 1)


def _send(store: Store, client: DevinClient, mission: MissionRow, text: str, *, now: str, phase: str) -> bool:
    # Reserve before sending: a timeout is ambiguous, so never blindly duplicate a paid command.
    store.set_autonomy(mission.id, auto_phase=phase, status="working", needs_user=None, awaiting_at=now)
    try:
        client.send_message(mission.session_id, text)
    except DevinUnavailable as exc:
        store.fail(mission.id, f"The automatic continuation could not be confirmed: {exc}. Send a message to retry.")
        return False
    return True
