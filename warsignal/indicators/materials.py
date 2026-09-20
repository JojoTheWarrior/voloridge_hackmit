from __future__ import annotations

import pandas as pd

from warsignal.config import DATA_RAW
from .base import IndicatorSpec, register


def _docs():
    path = DATA_RAW / "materials_project" / "doc_dates.csv"
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path, low_memory=False)


def _date_count(column):
    return _docs().assign(date=pd.to_datetime(_docs()[column], errors="coerce")).dropna(subset=["date"]).groupby("date").size()


register(IndicatorSpec("materials.docs_updated", "materials", "Materials documents updated", "documents", "D"), lambda: _date_count("last_updated"))
register(IndicatorSpec("materials.docs_created", "materials", "Materials documents created", "documents", "D"), lambda: _date_count("created_at"))
for element in ("W", "Al", "He", "S", "Cu", "Li", "U"):
    register(IndicatorSpec(f"materials.{element}.docs_updated", "materials", f"{element} documents updated", "documents", "D"),
             lambda element=element: _docs()[_docs().chemsys.fillna("").str.split("-").apply(lambda xs: element in xs)].assign(date=lambda x: pd.to_datetime(x.last_updated, errors="coerce")).groupby("date").size())
