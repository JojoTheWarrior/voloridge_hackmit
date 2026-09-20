from __future__ import annotations

import gzip
import csv
from pathlib import Path

import pandas as pd

from warsignal.config import CITIES, DATA_RAW
from .base import IndicatorSpec, IndicatorUnavailable, register
from warsignal.fetch.common import haversine_km


def _index():
    path = DATA_RAW / "openaq" / "location_index.csv"
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def available_cities():
    frame = _index()
    if frame.empty:
        return []
    result = []
    for city, coords in CITIES.items():
        if any(haversine_km(float(row.lat), float(row.lon), coords["lat"], coords["lon"]) <= 50 for row in frame.itertuples() if pd.notna(row.lat)):
            result.append(city)
    return result


def _load(city, parameter):
    frame = _index()
    if frame.empty:
        raise IndicatorUnavailable(f"airquality.{city}.{parameter}", "OpenAQ location index is missing or empty")
    ids = [str(row.id) for row in frame.itertuples() if pd.notna(row.lat) and haversine_km(float(row.lat), float(row.lon), CITIES[city]["lat"], CITIES[city]["lon"]) <= 50]
    if not ids:
        raise IndicatorUnavailable(f"airquality.{city}.{parameter}", "no OpenAQ locations matched within 50 km")
    rows = []
    for path in (DATA_RAW / "openaq" / "records").glob(f"csv.gz/locationid=*/year=*/month=*/*.csv.gz"):
        if path.parent.parent.name.split("=")[-1] not in ids:
            continue
        with gzip.open(path, "rt", errors="replace") as handle:
            rows.extend(csv.DictReader(handle))
    if not rows:
        raise FileNotFoundError("no downloaded OpenAQ rows")
    data = pd.DataFrame(rows)
    pcol = "parameter" if "parameter" in data else "parameter_name"
    dcol = "datetime" if "datetime" in data else "date.utc"
    data = data[data[pcol].astype(str).str.lower() == parameter.lower()]
    return pd.Series(pd.to_numeric(data["value"], errors="coerce").to_numpy(), index=pd.to_datetime(data[dcol], errors="coerce")).resample("D").mean()


for city in available_cities():
    for parameter in ("pm25", "pm10", "no2", "o3", "so2", "co"):
        register(IndicatorSpec(f"airquality.{city}.{parameter}", "airquality", f"{city} {parameter}", "concentration", "D", city),
                 lambda city=city, parameter=parameter: _load(city, parameter))
