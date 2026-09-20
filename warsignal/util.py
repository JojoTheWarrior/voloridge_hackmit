"""Shared conversion helpers for JSON and CSV boundaries."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
import math

import numpy as np
import pandas as pd


def to_jsonable(obj):
    """Recursively convert scientific Python values to JSON-safe values."""
    if obj is None or isinstance(obj, (str, bool, int)):
        return obj
    if obj is pd.NaT or obj is pd.NA:
        return None
    if isinstance(obj, (datetime, date, pd.Timestamp)):
        return obj.isoformat()
    if is_dataclass(obj):
        return to_jsonable(asdict(obj))
    if isinstance(obj, np.generic):
        return to_jsonable(obj.item())
    if isinstance(obj, np.ndarray):
        return to_jsonable(obj.tolist())
    if isinstance(obj, Mapping):
        return {str(key): to_jsonable(value) for key, value in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [to_jsonable(value) for value in obj]
    if isinstance(obj, float):
        return None if not math.isfinite(obj) else obj
    if pd.isna(obj):
        return None
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    return str(obj)
