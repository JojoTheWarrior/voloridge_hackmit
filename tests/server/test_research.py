import json

import pytest

from server.app import create_app
from server.devin import FakeDevin
from server.research import MAX_REFERENCE_CHARS, RESEARCH_DIR, list_findings
from server.store import Store


def write_findings(root, name, rows):
    path = root / name / "findings.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows), encoding="utf-8")


def test_library_to_mission_keeps_full_evidence_out_of_thread(tmp_path):
    root = tmp_path / "research"
    finding = {"title": "Reservoirs under stress", "one_liner": "Inspect the evidence.",
               "verdict": "partial", "caveats": "Not causal", "results": [{"n": 42}]}
    write_findings(root, "dams", [finding])
    store = Store(tmp_path / "kingdom.db")
    client = create_app(store, FakeDevin(), demo=True, research_dir=root).test_client()
    response = client.get("/api/research")
    assert response.status_code == 200
    row, = response.get_json()
    assert row["source"] == "dams"
    assert json.loads(row["reference"]) == finding
    response = client.post("/api/missions", json={"hypothesis": row["title"], "reference": row["reference"]})
    assert response.status_code == 201
    mission = response.get_json()
    saved = store.get_mission(mission["id"])
    assert saved.reference == row["reference"]
    assert "Not causal" in saved.prompt
    assert "Not causal" not in json.dumps(mission)


def test_library_excludes_archives_and_tolerates_bad_files(tmp_path):
    write_findings(tmp_path, "good", [{"title": "Valid"}, None, {"title": 9}, {"title": " "}])
    write_findings(tmp_path, "good/archive", [{"title": "Old"}])
    write_findings(tmp_path, "wrong", {"title": "Not a list"})
    write_findings(tmp_path, "huge", [{"title": "Too big", "data": "a" * MAX_REFERENCE_CHARS}])
    broken = tmp_path / "broken" / "findings.json"
    broken.parent.mkdir()
    broken.write_text("{bad")
    assert [row["title"] for row in list_findings(tmp_path)] == ["Valid"]
    assert list_findings(tmp_path / "missing") == []


def test_oversized_reference_does_not_create_a_mission(tmp_path):
    store = Store(tmp_path / "kingdom.db")
    client = create_app(store, FakeDevin(), demo=True).test_client()
    response = client.post("/api/missions", json={"hypothesis": "Test", "reference": "a" * (MAX_REFERENCE_CHARS + 1)})
    assert response.status_code == 422
    assert response.get_json()["field"] == "reference"
    assert store.list_missions() == []


def test_reviewed_index_supersedes_legacy_and_preserves_evidence(tmp_path):
    write_findings(tmp_path, "fixlist_flares", [{"title": "Old 38-site claim"}])
    finding = {"id": "fixlist_flares:priority", "mission": "fixlist_flares",
               "title": "37 sites", "verdict": "partial", "source_verdict": None,
               "source_evidence": {"results": {"sites": 37}, "caveats": ["Not exposure"]}}
    (tmp_path / "library.json").write_text(json.dumps([
        finding, finding, None, {"title": "Missing identity"},
        {**finding, "id": "large", "extra": "x" * MAX_REFERENCE_CHARS},
    ]))
    row, = list_findings(tmp_path)
    assert row["id"] == finding["id"]
    assert row["source"] == "fixlist_flares"
    assert row["verdict"] == "partial"
    assert json.loads(row["reference"]) == finding


@pytest.mark.parametrize("content", ["{bad", '{}', '[]'])
def test_present_index_never_silently_resurrects_legacy_claims(tmp_path, content):
    write_findings(tmp_path, "old", [{"title": "Stale claim"}])
    (tmp_path / "library.json").write_text(content)
    assert list_findings(tmp_path) == []


def test_shipped_library_coverage_and_top_prospects_reach_devin(tmp_path):
    packaged = json.loads((RESEARCH_DIR / "library.json").read_text())
    store = Store(tmp_path / "kingdom.db")
    client = create_app(store, FakeDevin(), demo=True).test_client()
    rows = client.get("/api/research").get_json()
    assert len(rows) == len(packaged) == 111
    assert len({row["source"] for row in rows}) == 13
    assert len({row["id"] for row in rows}) == len(rows)
    assert [json.loads(row["reference"]) for row in rows] == packaged
    for source in ("powerplants", "markets", "fixlist_darkclinics", "fixlist_tarps", "fixlist_flares"):
        row = next(row for row in rows if row["source"] == source)
        response = client.post("/api/missions", json={
            "hypothesis": row["title"], "reference": row["reference"],
        })
        assert response.status_code == 201
        saved = store.get_mission(response.get_json()["id"])
        assert saved.reference == row["reference"]
        assert row["reference"] in saved.prompt
