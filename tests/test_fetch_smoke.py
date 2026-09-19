from __future__ import annotations

import json
from datetime import date

import pytest

from warsignal.config import STATIONS
from warsignal.fetch.common import date_range, haversine_km, manifest, manifest_path
from warsignal.fetch.gdelt_live import v1_url, v2_url

def test_manifest_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr("warsignal.fetch.common.DATA_RAW", tmp_path)
    manifest("unit", "https://example.test/a", 12, date(2025, 1, 1), date(2025, 1, 2), status="downloaded")
    record = json.loads(manifest_path("unit").read_text())
    assert record["url"].endswith("/a")
    assert record["bytes"] == 12

def test_haversine():
    assert haversine_km(0, 0, 0, 1) == pytest.approx(111.195, rel=1e-3)

def test_gdelt_urls():
    day = date(2026, 2, 28)
    assert v1_url(day).endswith("/20260228.export.CSV.zip")
    assert v2_url(day, 6).endswith("/20260228060000.gkg.csv.zip")
    assert v2_url(day, 6, "export").endswith("/20260228060000.export.CSV.zip")

def test_date_range():
    assert list(date_range(date(2025, 1, 1), date(2025, 1, 3))) == [date(2025, 1, 1), date(2025, 1, 2), date(2025, 1, 3)]

def test_stations():
    assert len(STATIONS) == 19
    assert all(-90 <= value["lat"] <= 90 and -180 <= value["lon"] <= 180 for value in STATIONS.values())
