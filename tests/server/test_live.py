"""Live smoke test against the real Devin v3 API. Spends up to 1 ACU.

Run by hand only:  .venv/bin/python -m pytest tests/server/test_live.py -m live -s
"""
from __future__ import annotations

import time

import pytest
import requests

from server.devin import V3DevinClient
from warsignal.config import env

PROMPT = (
    "This is an API smoke test. Reply with one short message saying hello, set structured_output "
    'to {"steps": [{"id": "s1", "label": "Say hello", "state": "done"}], "artifacts": []}, then wait. '
    "Do not clone anything or run any code."
)
SCHEMA = {
    "type": "object",
    "properties": {"steps": {"type": "array", "items": {"type": "object"}}, "artifacts": {"type": "array"}},
}


@pytest.mark.live
def test_a_real_session_produces_a_message():
    api_key = env("DEVIN_API_KEY").strip()
    if not api_key:
        pytest.skip("DEVIN_API_KEY is not set")
    client = V3DevinClient(api_key, mode="lite")
    ref = client.create_session(PROMPT, title="Kingdom: live smoke test", schema=SCHEMA, max_acu=1)
    print(f"\nsession {ref.session_id} {ref.url}")

    # The client hides raw values behind its normalisation, and those are what this test is for.
    session_url = f"{client.base_url}{client._sessions(ref.session_id)}"
    seen_states: set[tuple] = set()
    message_keys: set[str] = set()
    devin_messages = []
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline and not devin_messages:
        raw = requests.get(session_url, headers=client._headers, timeout=30).json()
        seen_states.add((raw.get("status"), raw.get("status_detail")))
        raw_messages = requests.get(f"{session_url}/messages", headers=client._headers, timeout=30).json()
        items = raw_messages.get("items", []) if isinstance(raw_messages, dict) else raw_messages
        for item in items:
            if isinstance(item, dict):
                message_keys.update(item)
        devin_messages = [m for m in client.list_messages(ref.session_id) if m.role == "devin"]
        time.sleep(5)

    snapshot = client.get_session(ref.session_id)
    print(f"raw (status, status_detail) values seen: {sorted(seen_states, key=str)}")
    print(f"message keys seen: {sorted(message_keys)}")
    print(f"normalised status: {snapshot.status}; structured_output keys: {sorted(snapshot.structured_output or {})}")
    print(f"roles: {[m.role for m in client.list_messages(ref.session_id)]}")
    assert devin_messages, "no Devin message arrived within 90s"
