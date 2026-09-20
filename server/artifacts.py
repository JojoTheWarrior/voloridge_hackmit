from __future__ import annotations

import logging
import math
from collections.abc import Callable, Collection
from urllib.parse import quote, unquote, urlsplit

log = logging.getLogger(__name__)

MAX_SERIES = 6
MAX_POINTS = 500
MAX_IMAGES = 8
MAX_NODES = 12
MAX_TABLE_ROWS = 10
MAX_TABLE_COLUMNS = 6
MAX_STATS = 6

CHART_KINDS = ("line", "scatter", "bar")
ATTACHMENT_PREFIX = "attachment:"

SrcResolver = Callable[[object], "str | None"]


def normalise_artifact(raw: object, *, mission_id: str, attachments: Collection[str] = ()) -> dict | None:
    """Turn one of Devin's snake_case artifact specs into the app's camelCase shape.

    Returns None (and logs) when the spec cannot be rendered. Over-limit payloads are
    truncated, unknown fields dropped, and `attachment:<name>` sources rewritten to the
    mission's attachment proxy when the session really has that attachment.
    """
    if not isinstance(raw, dict):
        return None
    artifact_id, title, kind = _text(raw.get("id")), _text(raw.get("title")), raw.get("type")
    builder = _BUILDERS.get(kind) if isinstance(kind, str) else None
    if not artifact_id or not title or builder is None:
        log.warning("skipping artifact %r: missing id/title or unknown type %r", raw.get("id"), kind)
        return None

    def resolve(src: object) -> str | None:
        return _resolve_src(src, mission_id, attachments)

    body = builder(raw, resolve)
    if body is None:
        log.warning("skipping %s artifact %r: unusable payload", kind, artifact_id)
        return None
    artifact = {"id": artifact_id, "type": kind, "title": title}
    if caption := _text(raw.get("caption")):
        artifact["caption"] = caption
    return {**artifact, **body}


def normalise_stats(raw: object, limit: int = MAX_STATS) -> list[dict]:
    items = []
    for item in _dicts(raw):
        label, value = _text(item.get("label")), _cell(item.get("value"))
        if label and value:
            items.append({"label": label, "value": value})
    return items[:limit]


def attachment_name(src: object) -> str | None:
    """The attachment a `attachment:<name>` source points at, else None."""
    if not isinstance(src, str) or not src.startswith(ATTACHMENT_PREFIX):
        return None
    return src[len(ATTACHMENT_PREFIX):].strip() or None


def _resolve_src(src: object, mission_id: str, attachments: Collection[str]) -> str | None:
    if not isinstance(src, str):
        return None
    src = src.strip()
    if src.startswith(ATTACHMENT_PREFIX):
        name = attachment_name(src)
        if not name or "/" in name or "\\" in name or name not in attachments:
            return None
        return f"/api/missions/{mission_id}/attachments/{quote(name)}"
    parts = urlsplit(src)
    if parts.scheme == "https" and parts.netloc:
        return proxy_devin_image(src, mission_id)
    return None


def devin_image_name(src: object) -> str | None:
    """Recognize private Devin attachment links without accepting arbitrary download URLs."""
    if not isinstance(src, str):
        return None
    parts = urlsplit(src)
    if parts.scheme != "https" or parts.hostname not in ("app.devin.ai", "api.devin.ai"):
        return None
    segments = parts.path.split("/")
    if len(segments) != 4 or segments[1] != "attachments" or not segments[2]:
        return None
    name = unquote(segments[3])
    return name if name and name not in (".", "..") and not any(c in name for c in ("/", "\\", "\0")) else None


def proxy_devin_image(src: str, mission_id: str) -> str:
    name = devin_image_name(src)
    return f"/api/missions/{mission_id}/attachments/{quote(name, safe='')}" if name else src


def image_sources(artifact: dict) -> list[str]:
    items = artifact.get("items", []) if artifact.get("type") == "images" else [artifact] if artifact.get("type") == "image" else []
    if not isinstance(items, list):
        return []
    return [i["src"] for i in items if isinstance(i, dict) and isinstance(i.get("src"), str)]


def proxy_artifact_images(artifact: dict, mission_id: str) -> dict:
    """Also repair reports already saved before private-link normalization was added."""
    if artifact.get("type") == "image":
        return {**artifact, "src": proxy_devin_image(artifact["src"], mission_id)}
    if artifact.get("type") == "images":
        return {**artifact, "items": [{**item, "src": proxy_devin_image(item["src"], mission_id)} for item in artifact["items"]]}
    return artifact


def _chart(raw: dict, resolve: SrcResolver) -> dict | None:
    if raw.get("kind") not in CHART_KINDS:
        return None
    series = []
    for index, item in enumerate(_list(raw.get("series")), start=1):
        if not isinstance(item, dict):
            continue
        points = [list(p) for p in _list(item.get("points")) if _is_point(p)][:MAX_POINTS]
        if points:
            series.append({"name": _text(item.get("name")) or f"Series {index}", "points": points})
    if not series:
        return None
    body: dict = {"kind": raw["kind"]}
    for source, target in (("x_label", "xLabel"), ("y_label", "yLabel"), ("headline", "headline")):
        if value := _text(raw.get(source)):
            body[target] = value
    body["series"] = series[:MAX_SERIES]
    return body


def _images(raw: dict, resolve: SrcResolver) -> dict | None:
    items = []
    for item in _dicts(raw.get("items")):
        src = resolve(item.get("src"))
        if src is None:
            continue
        image = {"src": src}
        if caption := _text(item.get("caption")):
            image["caption"] = caption
        items.append(image)
    return {"items": items[:MAX_IMAGES]} if items else None


def _relation(raw: dict, resolve: SrcResolver) -> dict | None:
    nodes: dict[str, dict] = {}
    for item in _dicts(raw.get("nodes")):
        node_id = _text(item.get("id"))
        if node_id and node_id not in nodes and len(nodes) < MAX_NODES:
            nodes[node_id] = {"id": node_id, "label": _text(item.get("label")) or node_id}
    if not nodes:
        return None
    edges = []
    for item in _dicts(raw.get("edges")):
        source, target = _text(item.get("from")), _text(item.get("to"))
        if source not in nodes or target not in nodes:
            continue
        edge = {"from": source, "to": target}
        if label := _text(item.get("label")):
            edge["label"] = label
        edges.append(edge)
    return {"nodes": list(nodes.values()), "edges": edges}


def _table(raw: dict, resolve: SrcResolver) -> dict | None:
    columns = [_cell(c) for c in _list(raw.get("columns"))][:MAX_TABLE_COLUMNS]
    if not columns:
        return None
    rows = []
    for row in _list(raw.get("rows")):
        if isinstance(row, list):
            cells = [_cell(c) for c in row[: len(columns)]]
            rows.append(cells + [""] * (len(columns) - len(cells)))
    return {"columns": columns, "rows": rows[:MAX_TABLE_ROWS]}


def _stats(raw: dict, resolve: SrcResolver) -> dict | None:
    items = normalise_stats(raw.get("items"))
    return {"items": items} if items else None


def _image(raw: dict, resolve: SrcResolver) -> dict | None:
    src = resolve(raw.get("src"))
    return {"src": src} if src else None


_BUILDERS: dict[str, Callable[[dict, SrcResolver], dict | None]] = {
    "chart": _chart,
    "images": _images,
    "relation": _relation,
    "table": _table,
    "stats": _stats,
    "image": _image,
}


def _text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _cell(value: object) -> str:
    return "" if value is None else str(value).strip()


def _list(value: object) -> list:
    return value if isinstance(value, list) else []


def _dicts(value: object) -> list[dict]:
    return [item for item in _list(value) if isinstance(item, dict)]


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _is_point(point: object) -> bool:
    if not isinstance(point, (list, tuple)) or len(point) != 2:
        return False
    x, y = point
    return (_is_number(x) or (isinstance(x, str) and bool(x.strip()))) and _is_number(y)
