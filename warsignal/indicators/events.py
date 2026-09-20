from __future__ import annotations

import pandas as pd

from warsignal.config import DATA_REF
from .base import IndicatorSpec, register


def load_timeline():
    path = DATA_REF / "iran_timeline.csv"
    if not path.exists():
        return pd.DataFrame(columns=["date", "category", "event", "description", "market_note", "source_url"])
    frame = pd.read_csv(path)
    frame["date"] = pd.to_datetime(frame["date"])
    return frame


def war_phase(value):
    return "pre_war" if pd.Timestamp(value) < pd.Timestamp("2026-02-28") else "war"


_timeline = load_timeline()
_categories = sorted(set(_timeline.get("category", [])))
for category in _categories:
    register(IndicatorSpec(f"events.{category}.count", "events", f"Timeline events in {category}", "events", "D"),
             lambda category=category: _load_category(category))
register(IndicatorSpec("events.any.count", "events", "Any timeline event", "events", "D"), lambda: _load_category(None))


def _load_category(category):
    if _timeline.empty:
        return pd.Series(dtype=float)
    frame = _timeline if category is None else _timeline[_timeline.category == category]
    return frame.groupby("date").size().astype(float)
