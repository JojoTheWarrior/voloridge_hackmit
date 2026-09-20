from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import pandas as pd

from warsignal.config import DATA_RAW, ROOT


@dataclass(frozen=True)
class IndicatorSpec:
    name: str
    source: str
    description: str
    unit: str
    freq: str
    region: str | None = None


class IndicatorUnavailable(RuntimeError):
    def __init__(self, name: str, reason: str):
        self.name, self.reason = name, reason
        super().__init__(f"{name}: {reason}")


REGISTRY: dict[str, IndicatorSpec] = {}
_LOADERS: dict[str, Callable[[], pd.Series]] = {}


def register(spec: IndicatorSpec, loader: Callable[[], pd.Series]) -> None:
    REGISTRY[spec.name] = spec
    _LOADERS[spec.name] = loader


def list_indicators(source: str | None = None) -> list[IndicatorSpec]:
    values = list(REGISTRY.values())
    return sorted((s for s in values if source is None or s.source == source), key=lambda s: s.name)


def _cache_path(name: str) -> Path:
    safe = name.replace("/", "_")
    path = ROOT / "data" / "cache" / "indicators" / f"{safe}.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _normalise(name: str, value) -> pd.Series:
    if isinstance(value, pd.DataFrame):
        if value.shape[1] != 1:
            raise IndicatorUnavailable(name, "loader returned a DataFrame")
        value = value.iloc[:, 0]
    series = pd.Series(value, dtype="float64")
    index = pd.to_datetime(series.index, errors="coerce").tz_localize(None)
    frame = pd.DataFrame({"date": index, "value": pd.to_numeric(series.values, errors="coerce")}).dropna(subset=["date"])
    frame = frame.groupby("date", as_index=False)["value"].mean().sort_values("date")
    result = pd.Series(frame["value"].to_numpy(), index=pd.DatetimeIndex(frame["date"]), name=name, dtype="float64")
    return result


def get_series(name: str, start=None, end=None) -> pd.Series:
    if name not in REGISTRY:
        raise IndicatorUnavailable(name, "indicator is not registered")
    path = _cache_path(name)
    series = None
    if path.exists() and time.time() - path.stat().st_mtime < 86400:
        try:
            cached = pd.read_parquet(path)
            series = pd.Series(cached["value"].to_numpy(), index=pd.to_datetime(cached["date"]), name=name)
        except Exception:
            series = None
    if series is None:
        try:
            series = _normalise(name, _LOADERS[name]())
        except IndicatorUnavailable:
            raise
        except Exception as exc:
            raise IndicatorUnavailable(name, str(exc)) from exc
        pd.DataFrame({"date": series.index, "value": series.values}).to_parquet(path, index=False)
    if start is not None:
        series = series[series.index >= pd.Timestamp(start)]
    if end is not None:
        series = series[series.index <= pd.Timestamp(end)]
    series.name = name
    return series


def catalogue_text() -> str:
    return "\n".join(f"{s.name} | {s.freq} | {s.description}" for s in list_indicators())
