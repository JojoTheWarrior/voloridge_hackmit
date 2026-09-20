from __future__ import annotations

import re

import pandas as pd

from warsignal.config import DATA_RAW, OPENALEX_QUERIES
from .base import IndicatorSpec, register


def _works():
    path = DATA_RAW / "openalex" / "works_sample.parquet"
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_parquet(path)


def _matches(key):
    frame = _works()
    query = OPENALEX_QUERIES[key].lower().replace(" OR ", "|")
    text = (frame.title.fillna("") + " " + frame.abstract_words.fillna("") + " " + frame.keywords.fillna("")).str.lower()
    return frame[pd.Series(text.str.contains(query, regex=True), index=frame.index)].groupby("publication_date").size()


for key in OPENALEX_QUERIES:
    register(IndicatorSpec(f"research.{key}.pubs", "research", f"Publications matching {key}", "publications", "D"),
             lambda key=key: _matches(key))
register(IndicatorSpec("research.total_pubs", "research", "Sampled publications", "publications", "D"), lambda: _works().groupby("publication_date").size())
register(IndicatorSpec("research.iran_affiliated_pubs", "research", "Iran-affiliated publications", "publications", "D"),
         lambda: _works()[_works().iran_affiliated].groupby("publication_date").size())
register(IndicatorSpec("research.materials_science_share", "research", "Materials science share", "share", "D"),
         lambda: _works().assign(_one=1).groupby("publication_date").apply(lambda x: (x.primary_field == "Materials Science").mean()))
try:
    _fields = _works().primary_field.dropna().value_counts().head(10).index
except Exception:
    _fields = []
for field in _fields:
    slug = re.sub(r"[^a-z0-9]+", "_", str(field).lower()).strip("_")
    register(IndicatorSpec(f"research.field.{slug}.pubs", "research", f"Publications in {field}", "publications", "D"),
             lambda field=field: _works()[_works().primary_field == field].groupby("publication_date").size())
