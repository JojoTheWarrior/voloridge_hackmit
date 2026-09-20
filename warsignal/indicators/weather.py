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


def _parse_isd_line(line):
    if len(line) < 104:
        raise ValueError("short ISD record")
    day = pd.to_datetime(line[15:23], format="%Y%m%d")

    def number(start, end, missing):
        raw = line[start:end].strip()
        if not raw or raw.lstrip("+-") == missing:
            return None
        return float(raw)

    return {
        "date": day,
        "wind_dir": number(60, 63, "999"),
        "temp": (value / 10 if (value := number(87, 92, "9999")) is not None else None),
        "wind": (value / 10 if (value := number(65, 69, "9999")) is not None else None),
        "visibility": number(78, 84, "999999"),
        "dew": (value / 10 if (value := number(93, 98, "9999")) is not None else None),
        "slp": (value / 10 if (value := number(99, 104, "99999")) is not None else None),
    }


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
                    parsed = _parse_isd_line(line)
                    day, value = parsed["date"], parsed[field]
                    if not (pd.Timestamp("2025-03-01") <= day <= pd.Timestamp("2025-08-31")):
                        continue
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
        register(IndicatorSpec(f"weather.{city}.{key}", "weather",
                               f"{city} NOAA ISD 2025-03..2025-08 only {key}", "value", "D", city,
                               "2025-03..2025-08"),
                 lambda city=city, field=field: _isd(city, field))
    register(IndicatorSpec(f"weather.{city}.temp_anomaly", "weather", f"{city} temperature anomaly", "value", "D", city),
             lambda city=city: _anomaly(city))
