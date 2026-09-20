"""Opt-in mission -> report -> explorer check, all in one capped real session.

Requires both -m live and KINGDOM_LIVE_DELIVERY_MAX_ACU. Without an explicit
budget this is skipped, even when the ordinary one-ACU smoke test is enabled.
"""
from __future__ import annotations

import time

import pytest

from server.app import create_app
from server.devin import V3DevinClient
from server.poller import Poller
from server.store import Store
from warsignal.config import env

QUESTION = (
    "Compare five US hydropower plants: Hoover, Glen Canyon, Shasta, Oroville, and Fort Peck. "
    "Use official public sources to verify each plant's name, latitude, longitude, and installed "
    "capacity in MW. Run a small analysis that ranks these five plants by capacity. Include a "
    "table with coordinates and source URLs, plus a capacity chart. Report missing information "
    "honestly. Keep this small: five places only, no satellite downloads, no paid APIs. "
    "Narrate each step as you work and then give a conclusion and wait."
)


@pytest.mark.live
def test_new_live_mission_delivers_report_and_explorer(tmp_path, monkeypatch):
    key = env("DEVIN_API_KEY").strip()
    budget = env("KINGDOM_LIVE_DELIVERY_MAX_ACU").strip()
    if not key or not budget:
        pytest.skip("requires DEVIN_API_KEY and an explicitly approved KINGDOM_LIVE_DELIVERY_MAX_ACU")
    assert budget.isdigit() and int(budget) > 0, "budget must be a positive whole ACU count"
    monkeypatch.setenv("KINGDOM_MAX_ACU", budget)
    store = Store(tmp_path / "live-delivery.db")
    devin = V3DevinClient(key, mode="fast")
    api = create_app(store, devin, demo=False).test_client()
    poller = Poller(store, devin)
    response = api.post("/api/missions", json={"hypothesis": QUESTION, "datasetIds": []})
    assert response.status_code == 201
    mission = response.get_json()
    assert mission["status"] != "failed", mission
    mission_id = mission["id"]
    print(f"\nMission {mission_id}; one session capped at {budget} ACU: {mission.get('sessionUrl')}")

    def wait_for(label, ready):
        deadline = time.monotonic() + 15 * 60
        last_event = None
        while time.monotonic() < deadline:
            poller.tick()
            current = api.get(f"/api/missions/{mission_id}").get_json()
            if ready(current):
                print(f"{label}: delivered")
                return current
            errors = [event["text"] for event in current["events"] if event["kind"] == "error"]
            assert not errors, f"{label}: {errors}"
            assert current["status"] != "failed", f"{label}: mission failed"
            event_id = current["events"][-1]["id"] if current["events"] else None
            if event_id != last_event:
                print(f"{label}: {len(current['events'])} thread events, status={current['status']}")
                last_event = event_id
            time.sleep(5)
        pytest.fail(f"{label} did not arrive within 15 minutes; session remains subject to its original ACU cap")

    wait_for("Conclusion", lambda current: any(e["kind"] == "conclusion" for e in current["events"]))
    assert api.post(f"/api/missions/{mission_id}/report", json={}).status_code == 202
    current = wait_for("Report", lambda current: bool(current.get("report")))
    assert current["report"]["headline"]
    assert not current["reportPending"]
    assert api.post(f"/api/missions/{mission_id}/explorer", json={
        "instructions": "Map only the five verified plants from this mission. Rank by capacity and show source links."
    }).status_code == 202
    current = wait_for("Explorer", lambda current: bool(current.get("explorer")))
    assert not current["explorerPending"]
    entry = api.get(current["explorer"]["src"])
    assert entry.status_code == 200
    assert "sandbox allow-scripts" in entry.headers["Content-Security-Policy"]
    assert "allow-same-origin" not in entry.headers["Content-Security-Policy"]
    print(f"Explorer files for browser verification: {store.explorer_dir(mission_id, current['explorer']['version'])}")
