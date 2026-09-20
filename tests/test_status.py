import json

from warsignal.mission import status as st


def test_status_lifecycle_and_followup(tmp_path, monkeypatch):
    monkeypatch.setattr(st, "STATUS_DIR", tmp_path / "status")
    monkeypatch.setattr(st, "QUEUE", tmp_path / "queue.txt")
    st._atomic_write(st.status_path("R2-0001"), st.new_status("R2-0001", "Hormuz share leads FRO", parent_mission_id=None))
    queued = st.read_status("R2-0001")
    assert queued["state"] == "queued" and queued["progress"] == 0.0 and queued["round"] == "iran-round-2"

    running = st.update_status("R2-0001", state="running", stage="stats", message="permutation")
    assert running["started_at"] and running["progress"] == 0.3 and running["signal"] is None

    st.update_status("R2-0001", scores={"validity": 6.0, "actionability": 4.0})
    line = st.append_followup("R2-0001", "Hormuz share leads DHT by 2 days (+); trade long DHT 3d [gdelt.gkg.hormuz_share -> finance.DHT.log_return]")
    assert line.startswith("R2 | ") and line.endswith("(parent: R2-0001)")
    assert st.QUEUE.read_text().splitlines() == [line]
    assert st.append_followup("R2-0001", line) == line and len(st.QUEUE.read_text().splitlines()) == 1

    done = st.update_status("R2-0001", state="done")
    assert done["stage"] == "done" and done["progress"] == 1.0 and done["finished_at"]
    assert done["signal"] == 0.6 and done["followup_hypothesis"] == line
    assert json.loads(st.status_path("R2-0001").read_text())["state"] == "done"
