"""Tests for server.artifacts."""
from __future__ import annotations

import json
import logging

import pytest

from server.artifacts import (
    MAX_IMAGES,
    MAX_NODES,
    MAX_POINTS,
    MAX_SERIES,
    MAX_STATS,
    MAX_TABLE_COLUMNS,
    MAX_TABLE_ROWS,
    attachment_name,
    normalise_artifact,
)


def _norm(raw, attachments=()):
    return normalise_artifact(raw, mission_id="m_1", attachments=attachments)


def _chart(**over):
    base = {
        "id": "a1",
        "type": "chart",
        "title": "Severe share vs outage hours",
        "kind": "scatter",
        "x_label": "Severe share",
        "y_label": "Median outage hours",
        "headline": "r = 0.58",
        "series": [{"name": "Counties", "points": [[0.1, 4.2], [0.3, 9.1]]}],
    }
    base.update(over)
    return base


# ---------- common fields ----------

def test_chart_is_normalised_to_camel_case():
    assert _norm(_chart(caption="One dot per county", after_step="s1")) == {
        "id": "a1",
        "type": "chart",
        "title": "Severe share vs outage hours",
        "caption": "One dot per county",
        "kind": "scatter",
        "xLabel": "Severe share",
        "yLabel": "Median outage hours",
        "headline": "r = 0.58",
        "series": [{"name": "Counties", "points": [[0.1, 4.2], [0.3, 9.1]]}],
    }


def test_optional_fields_are_omitted_not_null():
    result = _norm(_chart(x_label=None, y_label="", headline=None))
    assert "xLabel" not in result and "yLabel" not in result
    assert "headline" not in result and "caption" not in result


def test_unknown_fields_are_dropped():
    result = _norm(_chart(colour="red", after_step="s1"))
    assert "colour" not in result and "after_step" not in result and "afterStep" not in result


@pytest.mark.parametrize("raw", [None, "chart", 3, [], {}])
def test_non_object_or_empty_is_invalid(raw):
    assert _norm(raw) is None


@pytest.mark.parametrize("field", ["id", "title", "type"])
@pytest.mark.parametrize("value", [None, "", "   ", 7, []])
def test_missing_or_blank_required_field_is_invalid(field, value):
    assert _norm(_chart(**{field: value})) is None


def test_unknown_type_is_invalid():
    assert _norm(_chart(type="hologram")) is None


def test_strings_are_trimmed():
    result = _norm(_chart(id=" a1 ", title="  Title  ", caption="  note "))
    assert (result["id"], result["title"], result["caption"]) == ("a1", "Title", "note")


def test_invalid_artifact_is_logged(caplog):
    with caplog.at_level(logging.WARNING, logger="server.artifacts"):
        assert _norm(_chart(kind="pie")) is None
    assert "a1" in caplog.text


def test_result_is_json_serialisable():
    json.dumps(_norm(_chart()))


# ---------- chart ----------

@pytest.mark.parametrize("kind", ["line", "scatter", "bar"])
def test_chart_kinds(kind):
    assert _norm(_chart(kind=kind))["kind"] == kind


@pytest.mark.parametrize("kind", ["pie", None, "", 3])
def test_chart_bad_kind_is_invalid(kind):
    assert _norm(_chart(kind=kind)) is None


def test_chart_accepts_string_x_values():
    series = [{"name": "Brent", "points": [["2026-01-01", 1.5], ["2026-01-02", 2]]}]
    assert _norm(_chart(kind="line", series=series))["series"][0]["points"] == [
        ["2026-01-01", 1.5],
        ["2026-01-02", 2],
    ]


def test_chart_drops_bad_points():
    points = [[1, 2], [1], "x", [1, "2"], [None, 2], [1, None], [True, 1], [1, False],
              [1, float("nan")], [float("inf"), 1], [3, 4, 5], [5, 6]]
    result = _norm(_chart(series=[{"name": "s", "points": points}]))
    assert result["series"][0]["points"] == [[1, 2], [5, 6]]


def test_chart_series_without_valid_points_is_dropped():
    series = [{"name": "empty", "points": []}, {"name": "ok", "points": [[1, 2]]}, "junk",
              {"points": [[1, 2]]}]
    result = _norm(_chart(series=series))
    assert [s["name"] for s in result["series"]] == ["ok", "Series 4"]


@pytest.mark.parametrize("series", [None, [], "x", [{"name": "s", "points": []}]])
def test_chart_without_usable_series_is_invalid(series):
    assert _norm(_chart(series=series)) is None


def test_chart_truncates_points_and_series():
    many = [[i, i] for i in range(MAX_POINTS + 50)]
    series = [{"name": f"s{i}", "points": many} for i in range(MAX_SERIES + 3)]
    result = _norm(_chart(series=series))
    assert len(result["series"]) == MAX_SERIES
    assert len(result["series"][0]["points"]) == MAX_POINTS
    assert result["series"][0]["points"][-1] == [MAX_POINTS - 1, MAX_POINTS - 1]


# ---------- images / image ----------

def _images(items):
    return {"id": "a2", "type": "images", "title": "Sample tiles", "items": items}


def test_images_valid():
    result = _norm(_images([{"src": "https://x.test/a.png", "caption": "Tile"},
                            {"src": "https://x.test/b.png"}]))
    assert result["items"] == [{"src": "https://x.test/a.png", "caption": "Tile"},
                               {"src": "https://x.test/b.png"}]


def test_images_truncated():
    items = [{"src": f"https://x.test/{i}.png"} for i in range(MAX_IMAGES + 4)]
    assert len(_norm(_images(items))["items"]) == MAX_IMAGES


@pytest.mark.parametrize("src", ["http://x.test/a.png", "javascript:alert(1)", "data:image/png;base64,AA",
                                 "/etc/passwd", "", None, 4, "https://", "attachment:"])
def test_images_bad_src_items_are_dropped(src):
    assert _norm(_images([{"src": src}])) is None
    kept = _norm(_images([{"src": src}, {"src": "https://x.test/ok.png"}]))
    assert kept["items"] == [{"src": "https://x.test/ok.png"}]


@pytest.mark.parametrize("items", [None, [], "x", [3, None]])
def test_images_without_items_is_invalid(items):
    assert _norm(_images(items)) is None


def test_attachment_ref_is_rewritten_to_proxy_url():
    result = _norm(_images([{"src": "attachment:tile 1.png"}]), attachments=["tile 1.png"])
    assert result["items"][0]["src"] == "/api/missions/m_1/attachments/tile%201.png"


def test_unresolved_attachment_is_dropped():
    items = [{"src": "attachment:missing.png"}, {"src": "attachment:here.png"}]
    result = _norm(_images(items), attachments=["here.png"])
    assert [i["src"] for i in result["items"]] == ["/api/missions/m_1/attachments/here.png"]


def test_attachment_name_with_path_separator_is_rejected():
    assert _norm(_images([{"src": "attachment:../secret.png"}]), attachments=["../secret.png"]) is None


def test_image_valid_and_invalid():
    raw = {"id": "a6", "type": "image", "title": "Map", "src": "attachment:map.png"}
    assert _norm(raw, attachments=["map.png"]) == {
        "id": "a6", "type": "image", "title": "Map", "src": "/api/missions/m_1/attachments/map.png"}
    assert _norm(raw) is None
    assert _norm({**raw, "src": "ftp://x.test/a.png"}) is None
    assert _norm({**raw, "src": "https://x.test/a.png"})["src"] == "https://x.test/a.png"


def test_attachment_name_round_trips_the_proxy_url():
    assert attachment_name("attachment:plot.png") == "plot.png"
    assert attachment_name("https://x.test/plot.png") is None
    assert attachment_name(None) is None


# ---------- relation ----------

def _relation(nodes, edges):
    return {"id": "a3", "type": "relation", "title": "How they join", "nodes": nodes, "edges": edges}


def test_relation_valid():
    result = _norm(_relation(
        [{"id": "img", "label": "Imagery"}, {"id": "out"}],
        [{"from": "img", "to": "out", "label": "county + week"}, {"from": "out", "to": "img"}],
    ))
    assert result["nodes"] == [{"id": "img", "label": "Imagery"}, {"id": "out", "label": "out"}]
    assert result["edges"] == [{"from": "img", "to": "out", "label": "county + week"},
                               {"from": "out", "to": "img"}]


def test_relation_drops_bad_nodes_duplicate_ids_and_dangling_edges():
    result = _norm(_relation(
        [{"id": "a", "label": "A"}, {"id": "a", "label": "again"}, {"label": "no id"}, "x", {"id": "b"}],
        [{"from": "a", "to": "b"}, {"from": "a", "to": "ghost"}, {"from": "a"}, "junk"],
    ))
    assert [n["id"] for n in result["nodes"]] == ["a", "b"]
    assert result["edges"] == [{"from": "a", "to": "b"}]


def test_relation_truncates_nodes_and_their_edges():
    nodes = [{"id": f"n{i}", "label": f"N{i}"} for i in range(MAX_NODES + 3)]
    edges = [{"from": "n0", "to": f"n{MAX_NODES}"}, {"from": "n0", "to": "n1"}]
    result = _norm(_relation(nodes, edges))
    assert len(result["nodes"]) == MAX_NODES
    assert result["edges"] == [{"from": "n0", "to": "n1"}]


def test_relation_edges_are_optional_but_nodes_are_not():
    assert _norm(_relation([{"id": "a"}], None))["edges"] == []
    assert _norm(_relation([], [])) is None
    assert _norm(_relation(None, [])) is None


# ---------- table ----------

def _table(columns, rows):
    return {"id": "a4", "type": "table", "title": "Top counties", "columns": columns, "rows": rows}


def test_table_valid_coerces_cells_to_strings():
    result = _norm(_table(["County", "Hours"], [["Lee", 9.5], ["Polk", None], ["Bay", True]]))
    assert result["columns"] == ["County", "Hours"]
    assert result["rows"] == [["Lee", "9.5"], ["Polk", ""], ["Bay", "True"]]


def test_table_rows_are_padded_and_clipped_to_the_columns():
    result = _norm(_table(["A", "B"], [["1"], ["1", "2", "3"], "junk", []]))
    assert result["rows"] == [["1", ""], ["1", "2"], ["", ""]]


def test_table_truncation():
    columns = [f"c{i}" for i in range(MAX_TABLE_COLUMNS + 2)]
    rows = [[str(i)] * len(columns) for i in range(MAX_TABLE_ROWS + 5)]
    result = _norm(_table(columns, rows))
    assert len(result["columns"]) == MAX_TABLE_COLUMNS
    assert len(result["rows"]) == MAX_TABLE_ROWS
    assert all(len(row) == MAX_TABLE_COLUMNS for row in result["rows"])


@pytest.mark.parametrize("columns", [None, [], "x"])
def test_table_without_columns_is_invalid(columns):
    assert _norm(_table(columns, [["1"]])) is None


def test_table_without_rows_is_valid_and_empty():
    assert _norm(_table(["A"], None))["rows"] == []


# ---------- stats ----------

def _stats(items):
    return {"id": "a5", "type": "stats", "title": "Core stats", "items": items}


def test_stats_valid_coerces_values():
    result = _norm(_stats([{"label": "Correlation", "value": 0.58}, {"label": "n", "value": "412"}]))
    assert result["items"] == [{"label": "Correlation", "value": "0.58"}, {"label": "n", "value": "412"}]


def test_stats_drops_bad_items_and_truncates():
    items = [{"label": "", "value": "1"}, {"value": "1"}, {"label": "x"}, "junk"]
    items += [{"label": f"l{i}", "value": i} for i in range(MAX_STATS + 2)]
    result = _norm(_stats(items))
    assert len(result["items"]) == MAX_STATS
    assert result["items"][0] == {"label": "l0", "value": "0"}


@pytest.mark.parametrize("items", [None, [], [{"label": "only"}]])
def test_stats_without_items_is_invalid(items):
    assert _norm(_stats(items)) is None
