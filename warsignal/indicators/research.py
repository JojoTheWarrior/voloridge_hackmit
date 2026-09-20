from __future__ import annotations

import re

import pandas as pd

from warsignal.config import DATA_RAW, OPENALEX_QUERIES
from .base import IndicatorSpec, register


CROSSREF_TOPICS = {
    "tungsten", "lithium", "rare_earth", "hormuz", "iran", "lng", "hydrogen",
    "drone", "sanctions", "oil_price", "solar", "nuclear", "missile",
    "desalination", "shipping", "cybersecurity", "graphite", "uranium",
    "ammonia", "battery",
}


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
    register(IndicatorSpec(
        f"research.{key}.pubs", "research",
        f"Publications matching {key}; sparse OpenAlex S3 sample (n≈8); prefer research.*.crossref_*",
        "publications", "D", None, "sparse OpenAlex S3 sample (n≈8)",
    ),
             lambda key=key: _matches(key))
register(IndicatorSpec(
    "research.total_pubs", "research",
    "Sampled publications; sparse OpenAlex S3 sample (n≈8); prefer research.*.crossref_*",
    "publications", "D", None, "sparse OpenAlex S3 sample (n≈8)",
), lambda: _works().groupby("publication_date").size())
register(IndicatorSpec(
    "research.iran_affiliated_pubs", "research",
    "Iran-affiliated publications; sparse OpenAlex S3 sample (n≈8); prefer research.*.crossref_*",
    "publications", "D", None, "sparse OpenAlex S3 sample (n≈8)",
),
         lambda: _works()[_works().iran_affiliated].groupby("publication_date").size())
register(IndicatorSpec(
    "research.materials_science_share", "research",
    "Materials science share; sparse OpenAlex S3 sample (n≈8); prefer research.*.crossref_*",
    "share", "D", None, "sparse OpenAlex S3 sample (n≈8)",
),
         lambda: _works().assign(_one=1).groupby("publication_date").apply(lambda x: (x.primary_field == "Materials Science").mean()))
try:
    _fields = _works().primary_field.dropna().value_counts().head(10).index
except Exception:
    _fields = []
for field in _fields:
    slug = re.sub(r"[^a-z0-9]+", "_", str(field).lower()).strip("_")
    register(IndicatorSpec(
        f"research.field.{slug}.pubs", "research",
        f"Publications in {field}; sparse OpenAlex S3 sample (n≈8); prefer research.*.crossref_*",
        "publications", "D", None, "sparse OpenAlex S3 sample (n≈8)",
    ),
             lambda field=field: _works()[_works().primary_field == field].groupby("publication_date").size())


def _crossref(topic):
    path = DATA_RAW / "crossref" / f"{topic}.json"
    if not path.exists():
        raise FileNotFoundError(path)
    payload = pd.Series(pd.read_json(path, typ="series"), dtype="float64")
    payload.index = pd.to_datetime(payload.index)
    return payload.sort_index()


def _crossref_share(topic):
    topic_series = _crossref(topic)
    all_series = _crossref("all").reindex(topic_series.index).replace(0, float("nan"))
    return topic_series.div(all_series) * 1e4


for topic in sorted(CROSSREF_TOPICS):
    register(
        IndicatorSpec(
            f"research.{topic}.crossref_pubs",
            "research",
            f"Crossref weekly publications matching {topic}",
            "publications",
            "W",
            None,
            "2025-03..current week",
        ),
        lambda topic=topic: _crossref(topic),
    )
    register(
        IndicatorSpec(
            f"research.{topic}.crossref_share",
            "research",
            f"Crossref {topic} publications per 10k works created that week",
            "per 10k works created that week",
            "W",
            None,
            "2025-03..current week",
        ),
        lambda topic=topic: _crossref_share(topic),
    )
