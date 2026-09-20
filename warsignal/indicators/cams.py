from __future__ import annotations

import json

import pandas as pd

from warsignal.config import CITIES, DATA_RAW
from .base import IndicatorSpec, IndicatorUnavailable, register


_FIELDS = {
    "cams_pm25": "pm2_5",
    "cams_pm10": "pm10",
    "cams_no2": "nitrogen_dioxide",
    "cams_so2": "sulphur_dioxide",
    "cams_o3": "ozone",
    "cams_co": "carbon_monoxide",
    "cams_dust": "dust",
    "cams_aod": "aerosol_optical_depth",
}


def _load(city, field):
    path = DATA_RAW / "open_meteo_aq" / f"{city}.json"
    if not path.exists():
        raise IndicatorUnavailable(f"airquality.{city}.{field}", "Open-Meteo CAMS data is missing")
    payload = json.loads(path.read_text(encoding="utf-8"))
    hourly = payload.get("hourly", {})
    times = pd.to_datetime(hourly.get("time", []), errors="coerce")
    values = pd.to_numeric(hourly.get(field, []), errors="coerce")
    if len(times) == 0 or len(values) == 0:
        raise IndicatorUnavailable(f"airquality.{city}.{field}", "Open-Meteo CAMS data is empty")
    return pd.Series(values, index=times).resample("D").mean()


for city in CITIES:
    for name, field in _FIELDS.items():
        register(
            IndicatorSpec(
                f"airquality.{city}.{name}",
                "airquality",
                f"{city} CAMS model reanalysis via Open-Meteo (not ground sensors)",
                "concentration",
                "D",
                city,
                "2025-03..2026-09 archive window",
            ),
            lambda city=city, field=field: _load(city, field),
        )
