from __future__ import annotations

import csv
import io
import os
import re
import zipfile
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pandas as pd

from warsignal.config import DATA_RAW, END, START
from .base import IndicatorSpec, register

COUNTRIES = {"IRN", "ISR", "USA", "QAT", "SAU", "ARE", "KWT", "IRQ", "OMN", "LBN", "BHR"}
GKG_TERMS = {
    "hormuz": ("HORMUZ",), "tanker": ("TANKER", "MARITIME"), "helium": ("HELIUM",),
    "semiconductor": ("SEMICONDUCTOR",), "food_prices": ("FOOD_PRICE", "FOOD_SECURITY"),
    "fertilizer": ("FERTILIZER",), "sanctions": ("SANCTIONS",), "cyber": ("CYBER_ATTACK",),
    "drone": ("DRONE",), "ceasefire": ("CEASEFIRE",), "oil": ("ENV_OIL", "OIL"),
    "lng": ("NATURAL_GAS", "LNG"), "protest": ("PROTEST",), "qatar": ("#QA#",),
    "oman": ("#MU#",),
}


def _iter_zip(path):
    with zipfile.ZipFile(path) as archive:
        name = archive.namelist()[0]
        with archive.open(name) as raw:
            for line in io.TextIOWrapper(raw, encoding="utf-8", errors="replace"):
                yield line.rstrip("\n").split("\t")


def _float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _day(value):
    value = str(value)[:8]
    if len(value) != 8 or not value.isdigit():
        raise ValueError(f"invalid GDELT date: {value!r}")
    return f"{value[:4]}-{value[4:6]}-{value[6:8]}"


def _process_zip(path):
    events = defaultdict(lambda: defaultdict(float))
    gkg = defaultdict(lambda: defaultdict(float))
    is_gkg = ".gkg." in path.name
    for row in _iter_zip(path):
        try:
            if is_gkg:
                day = _day(row[1])
                gkg[day]["docs"] += 1
                themes = row[7] if len(row) > 7 else ""
                locations = row[9] if len(row) > 9 else ""
                haystack = f"{themes} {locations}".upper()
                for key, terms in GKG_TERMS.items():
                    if any(term in haystack for term in terms):
                        gkg[day][key] += 1
                if len(row) > 3 and row[3].lower().endswith(".ir"):
                    gkg[day]["iran_source_docs"] += 1
                continue
            if len(row) < 55:
                continue
            v2 = len(row) >= 61
            day = _day(row[1])
            item = events[day]
            item["total_events"] += 1
            countries = [row[7], row[17], row[53 if v2 else 51]]
            for country in COUNTRIES.intersection(countries):
                item[f"{country}.events"] += 1
                item[f"{country}.tone_sum"] += _float(row[34])
                item[f"{country}.goldstein_sum"] += _float(row[30])
                item[f"{country}.mentions"] += _float(row[31])
                item[f"{country}.conflict_events"] += row[29] == "4"
                item[f"{country}.coop_events"] += row[29] == "1"
                for code, name in (("14", "protest_events"), ("18", "assault_events"), ("19", "fight_events"),
                                   ("17", "coerce_events"), ("04", "negotiate_events")):
                    item[f"{country}.{name}"] += row[28] == code
            if (row[7] == "IRN" and row[17] == "ISR") or (row[7] == "ISR" and row[17] == "IRN"):
                item["iran_israel_dyad_events"] += 1
            if (row[7] == "IRN" and row[17] == "USA") or (row[7] == "USA" and row[17] == "IRN"):
                item["iran_usa_dyad_events"] += 1
        except (ValueError, IndexError, TypeError):
            continue
    return {day: dict(values) for day, values in events.items()}, {day: dict(values) for day, values in gkg.items()}


def _daily(rebuild=False):
    cache = DATA_RAW.parent / "cache" / "gdelt_daily.parquet"
    manifest = DATA_RAW / "gdelt_live" / "_manifest.jsonl"
    if not rebuild and cache.exists() and (not manifest.exists() or manifest.stat().st_mtime <= cache.stat().st_mtime):
        return pd.read_parquet(cache)
    result = defaultdict(lambda: defaultdict(float))
    gkg = defaultdict(lambda: defaultdict(float))
    paths = sorted((DATA_RAW / "gdelt_live").rglob("*.zip"))
    max_files = int(os.getenv("WARSIGNAL_GDELT_MAX_FILES", "0"))
    if max_files:
        exports = [path for path in paths if ".gkg." not in path.name]
        gkg_paths = [path for path in paths if ".gkg." in path.name]
        half = max_files // 2
        paths = exports[-half:] + gkg_paths[-(max_files - half):]
    with ProcessPoolExecutor(max_workers=os.cpu_count() or 1) as executor:
        for event_values, gkg_values in executor.map(_process_zip, paths):
            for day, values in event_values.items():
                for key, value in values.items():
                    result[day][key] += value
            for day, values in gkg_values.items():
                for key, value in values.items():
                    gkg[day][key] += value
    rows = []
    days = sorted(set(result) | set(gkg))
    for day in days:
        item = {"date": day}
        item.update(result[day])
        item.update(gkg[day])
        docs = item.get("docs", 0)
        for key in GKG_TERMS:
            item[f"gkg.{key}_share"] = item.get(key, 0) * 1000 / docs if docs else 0
        rows.append(item)
    frame = pd.DataFrame(rows).fillna(0).sort_values("date")
    cache.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(cache, index=False)
    return frame


def rebuild_cache():
    return _daily(rebuild=True)


def _series(column):
    frame = _daily().set_index("date")
    frame.index = pd.to_datetime(frame.index)
    frame = frame[(frame.index >= pd.Timestamp(START)) & (frame.index <= pd.Timestamp(END))]
    if column.endswith(".tone") or column.endswith(".goldstein"):
        prefix, field = column.rsplit(".", 1)
        numerator = frame.get(f"{prefix}.{field}_sum", pd.Series(0, index=frame.index))
        denom = frame.get(f"{prefix}.events", pd.Series(0, index=frame.index))
        return numerator.divide(denom.replace(0, pd.NA))
    return frame.get(column, pd.Series(dtype=float))


for country in COUNTRIES:
    for suffix, description in (("events", "events"), ("tone", "mean tone"), ("goldstein", "mean Goldstein"), ("mentions", "mentions"),
                                ("conflict_events", "material conflict"), ("coop_events", "verbal cooperation"), ("protest_events", "protests"),
                                ("fight_events", "fights"), ("negotiate_events", "negotiations")):
        name = f"gdelt.{country.lower()}.{suffix}"
        register(IndicatorSpec(name, "gdelt", f"GDELT {country} {description}", "count" if suffix.endswith("events") else "value", "D", country),
                 lambda country=country, suffix=suffix: _series(f"{country}.{suffix}"))
for name in ("iran_israel_dyad_events", "iran_usa_dyad_events", "total_events"):
    register(IndicatorSpec(f"gdelt.{name}", "gdelt", f"GDELT {name}", "events", "D"),
             lambda name=name: _series(name))
register(IndicatorSpec("gdelt.gkg.docs", "gdelt", "Sampled GKG documents", "documents", "D"), lambda: _series("docs"))
register(IndicatorSpec("gdelt.gkg.iran_source_docs", "gdelt", "GKG Iran-source documents", "documents", "D"), lambda: _series("iran_source_docs"))
for key in GKG_TERMS:
    register(IndicatorSpec(f"gdelt.gkg.{key}_share", "gdelt", f"GKG {key} share per thousand", "per 1000", "D"),
             lambda key=key: _series(f"gkg.{key}_share"))
