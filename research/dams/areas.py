"""GWW raw surface-water-area series: cached fetch + cloud/outlier filter + monthly aggregation."""
import numpy as np
import pandas as pd

from common import GWW, cached_json

START, STOP = "1999-01-01T00:00:00", "2026-09-19T00:00:00"


def fetch_raw(gww_id):
    j = cached_json(f"{GWW}/reservoir/{int(gww_id)}/ts/surface_water_area", params={"start": START, "stop": STOP},
                    subdir="gww_ts", key=str(int(gww_id)), sleep=0.2, ok=lambda j: isinstance(j, list))
    if not j:
        return pd.Series(dtype=float)
    s = pd.Series({pd.Timestamp(x["t"]): x["value"] / 1e6 for x in j}).sort_index()
    return s[~s.index.duplicated()]


def despike(s, k=4, max_days=150, rel=0.20, nmad=4.0):
    """Drop observations far from the median of their +-k neighbours (clouds, ice, SLC-off stripes, partial tiles).
    Centred, so the last k observations are filtered with fewer neighbours, as they would be in live use."""
    s = s[s > 0]
    if len(s) < 12:
        return s
    v, t = s.values, s.index.values.astype("datetime64[D]").astype(float)
    keep = np.ones(len(v), bool)
    for i in range(len(v)):
        lo, hi = max(0, i - k), min(len(v), i + k + 1)
        nb = np.r_[v[lo:i], v[i + 1:hi]]
        tn = np.r_[t[lo:i], t[i + 1:hi]]
        nb = nb[np.abs(tn - t[i]) <= max_days]
        if len(nb) < 3:
            continue
        ref = np.median(nb)
        mad = 1.4826 * np.median(np.abs(nb - ref))
        keep[i] = abs(v[i] - ref) <= max(rel * ref, nmad * mad)
    return s[keep]


def monthly(gww_id, interp_limit=2):
    s = despike(fetch_raw(gww_id))
    if s.empty:
        return pd.DataFrame(columns=["area_km2", "n_obs"])
    m = s.resample("MS").agg(["median", "count"]).rename(columns={"median": "area_km2", "count": "n_obs"})
    m["interp"] = m.area_km2.isna()
    m["area_km2"] = m.area_km2.interpolate(limit=interp_limit, limit_area="inside")
    return m
