from warsignal.indicators import REGISTRY, catalogue_text, get_series, list_indicators
from warsignal.indicators import research
from warsignal.analysis.stats import transform


def test_catalogue_and_transforms():
    assert catalogue_text()
    assert list_indicators()
    for kind in ("level", "diff", "pct_change", "log_return", "zscore", "anomaly"):
        transform([1, 2, 3], kind)


def test_crossref_registration_and_fake_json(tmp_path, monkeypatch):
    root = tmp_path / "crossref"
    root.mkdir()
    (root / "tungsten.json").write_text(
        '{"2025-03-03": 12, "2025-03-10": 15}', encoding="utf-8"
    )
    (root / "all.json").write_text(
        '{"2025-03-03": 1200, "2025-03-10": 1500}', encoding="utf-8"
    )
    monkeypatch.setattr(research, "DATA_RAW", tmp_path)
    series = research._crossref("tungsten")
    share = research._crossref_share("tungsten")
    assert "research.tungsten.crossref_pubs" in REGISTRY
    assert REGISTRY["research.tungsten.crossref_pubs"].freq == "W"
    assert series.iloc[0] == 12
    assert share.iloc[0] == 100


def test_catalogue_excludes_sparse_and_snapshot_sources():
    text = catalogue_text()
    assert "research.tungsten.pubs" not in text
    assert "materials.docs_updated" not in text
    assert "Materials Project data is a snapshot" in text
    assert "research.tungsten.crossref_pubs" in text
