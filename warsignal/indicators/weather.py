from __future__ import annotations

import gzip
from pathlib import Path

import pandas as pd

from warsignal.config import CITIES, DATA_RAW, STATIONS
from .base import IndicatorSpec, register


def _meteo(city, field):
    path = DATA_RAW / "open_meteo" / f"{city}.json"
    if not path.exists():
        raise FileNotFoundError(path)
    data = __import__("json").loads(path.read_text())
    daily = data.get("daily", {})
    values = daily.get(field, [])
    return pd.Series(values, index=pd.to_datetime(daily.get("time", [])))


def _isd(city, field):
    station = STATIONS[city]["usaf_wban"]
    paths = list((DATA_RAW / "noaa_isd").glob(f"2025/{city}-*.gz"))
    if not paths:
        raise FileNotFoundError(station)
    values = {}
    for path in paths:
        with gzip.open(path, "rt", errors="replace") as handle:
            for line in handle:
                try:
                    day = pd.to_datetime(line[14:22], format="%Y%m%d")
                    if field == "temp":
                        raw = line[87:92]; value = float(raw) / 10 if raw.strip() and raw != "99999" else None
                    elif field == "wind":
                        raw = line[65:69]; value = float(raw) / 10 if raw.strip() and raw != "9999" else None
                    else:
                        raw = line[78:83]; value = float(raw) if raw.strip() and raw != "999999" else None
                    if value is not None:
                        values.setdefault(day, []).append(value)
                except (ValueError, IndexError):
                    continue
    return pd.Series({day: sum(vals) / len(vals) for day, vals in values.items()})


def _anomaly(city):
    series = _meteo(city, "temperature_2m_mean")
    baseline = series[series.index.year == 2025]
    means = baseline.groupby(baseline.index.isocalendar().week).mean()
    return pd.Series([v - means.get(d.isocalendar().week, baseline.mean()) for d, v in series.items()], index=series.index)


for city in CITIES:
    for key, field in (("temp_mean", "temperature_2m_mean"), ("temp_max", "temperature_2m_max"), ("temp_min", "temperature_2m_min"),
                       ("precip", "precipitation_sum"), ("wind_max", "wind_speed_10m_max"), ("radiation", "shortwave_radiation_sum")):
        register(IndicatorSpec(f"weather.{city}.{key}", "weather", f"{city} {key}", "value", "D", city),
                 lambda city=city, field=field: _meteo(city, field))
    for key, field in (("isd_temp_mean", "temp"), ("isd_wind_mean", "wind"), ("isd_visibility_mean", "visibility")):
        register(IndicatorSpec(f"weather.{city}.{key}", "weather", f"{city} NOAA {key}", "value", "D", city),
                 lambda city=city, field=field: _isd(city, field))
    register(IndicatorSpec(f"weather.{city}.temp_anomaly", "weather", f"{city} temperature anomaly", "value", "D", city),
             lambda city=city: _anomaly(city))
