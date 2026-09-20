from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from warsignal.config import DATA_RAW


def daily(values, dates=None) -> pd.Series:
    if dates is None:
        dates = values.index
    result = pd.Series(values, index=pd.to_datetime(dates).tz_localize(None), dtype="float64")
    return result.groupby(level=0).mean().sort_index()


def timeline_range(series: pd.Series) -> pd.Series:
    if series.empty:
        return series
    return series.asfreq("D", fill_value=0)


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"missing raw file {path}") from exc
