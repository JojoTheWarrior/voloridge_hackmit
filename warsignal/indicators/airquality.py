from __future__ import annotations

import gzip
import csv
import json
from pathlib import Path

import pandas as pd

from warsignal.config import CITIES, DATA_RAW
from .base import IndicatorSpec, IndicatorUnavailable, register
from warsignal.fetch.common import haversine_km

_PARAMETERS = {
    "pm25": {"pm25", "pm2.5", "pm2_5"},
    "pm10": {"pm10", "pm10.0"},
    "no2": {"no2", "nitrogen_dioxide"},
    "o3": {"o3", "ozone"},
    "so2": {"so2", "sulphur_dioxide", "sulfur_dioxide"},
    "co": {"co", "carbon_monoxide"},
}
_PARAM_CACHE = DATA_RAW.parent / "cache" / "openaq_city_params.json"


def _index():
    path = DATA_RAW / "openaq" / "location_index.csv"
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def available_cities():
    return sorted(_city_params())


def _matched_ids(city, frame):
    return [
        str(row.id)
        for row in frame.itertuples()
        if pd.notna(row.lat)
        and pd.notna(row.lon)
        and haversine_km(
            float(row.lat), float(row.lon), CITIES[city]["lat"], CITIES[city]["lon"]
        ) <= 50
    ]


def _canonical_parameter(value):
    value = str(value).strip().lower()
    for parameter, aliases in _PARAMETERS.items():
        if value in aliases:
            return parameter
    return value


def _city_params():
    frame = _index()
    if frame.empty:
        return {}
    files = list((DATA_RAW / "openaq" / "records").glob("csv.gz/locationid=*/year=*/month=*/*.csv.gz"))
    id_to_cities = {}
    for city, coords in CITIES.items():
        for location_id in _matched_ids(city, frame):
            id_to_cities.setdefault(location_id, set()).add(city)
    result = {city: set() for city in CITIES}
    for path in files:
        location_id = path.parts[-4].split("=")[-1]
        cities = id_to_cities.get(location_id, ())
        if not cities:
            continue
        try:
            with gzip.open(path, "rt", errors="replace", newline="") as handle:
                for row in csv.DictReader(handle):
                    parameter = row.get("parameter") or row.get("parameter_name")
                    if parameter:
                        for city in cities:
                            result[city].add(_canonical_parameter(parameter))
        except (OSError, csv.Error):
            continue
    result = {city: sorted(values) for city, values in result.items() if values}
    _PARAM_CACHE.parent.mkdir(parents=True, exist_ok=True)
    _PARAM_CACHE.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    return result


def _load(city, parameter):
    frame = _index()
    if frame.empty:
        raise IndicatorUnavailable(f"airquality.{city}.{parameter}", "OpenAQ location index is missing or empty")
    ids = _matched_ids(city, frame)
    if not ids:
        raise IndicatorUnavailable(f"airquality.{city}.{parameter}", "no OpenAQ locations matched within 50 km")
    rows = []
    for path in (DATA_RAW / "openaq" / "records").glob(f"csv.gz/locationid=*/year=*/month=*/*.csv.gz"):
        if path.parts[-4].split("=")[-1] not in ids:
            continue
        with gzip.open(path, "rt", errors="replace") as handle:
            rows.extend(csv.DictReader(handle))
    if not rows:
        raise FileNotFoundError("no downloaded OpenAQ rows")
    data = pd.DataFrame(rows)
    pcol = "parameter" if "parameter" in data else "parameter_name"
    dcol = "datetime" if "datetime" in data else "date.utc"
    data = data[data[pcol].map(_canonical_parameter) == parameter]
    if data.empty:
        raise IndicatorUnavailable(
            f"airquality.{city}.{parameter}", "no downloaded OpenAQ rows for parameter"
        )
    dates = pd.to_datetime(data[dcol], errors="coerce", utc=True).dt.tz_localize(None)
    return pd.Series(
        pd.to_numeric(data["value"], errors="coerce").to_numpy(), index=dates
    ).resample("D").mean()


for city, parameters in _city_params().items():
    for parameter in parameters:
        if parameter in _PARAMETERS:
            register(IndicatorSpec(
                f"airquality.{city}.{parameter}", "airquality",
                f"{city} OpenAQ ground-sensor {parameter}", "concentration", "D", city,
                "downloaded observations",
            ), lambda city=city, parameter=parameter: _load(city, parameter))
