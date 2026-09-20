"""Skeptic's controls on the area -> generation relation (US dams with truth, pre-registered storage set).
A. Placebo pairing: each dam's generation anomaly vs the area anomaly of (i) a far-away reservoir (> 1500 km) and
   (ii) its nearest OTHER reservoir (< 300 km). If (ii) ~ own-reservoir r, the 'signal' is regional drought, not the dam.
B. Look-ahead: the production despike filter is centred (uses up to 4 later observations). Re-run with a strictly causal
   filter and compare per-dam r.
C. Sensor eras: pooled mean area anomaly by year, to expose step changes when Landsat-8 (2013) / Sentinel-2 (2016-17) join.
Output results/robustness.csv"""
import numpy as np
import pandas as pd

from areas import fetch_raw
from common import RESULTS
from features import build, load_inputs

panel, st, clim = load_inputs()
us = st[(st.truth == "eia923") & st.storage_dam]
F = build(panel[panel.gww_id.isin(us.gww_id)], st, clim)
F = F[(F.month < "2026-01-01")].dropna(subset=["a0", "y"])
A = F.pivot(index="month", columns="gww_id", values="a0")
Y = F.pivot(index="month", columns="gww_id", values="y")
ids = [g for g in A.columns if Y[g].notna().sum() >= 120]
xy = us.set_index("gww_id").loc[ids, ["lat", "lon"]]
lat, lon = np.radians(xy.lat.values), np.radians(xy.lon.values)
D = 6371 * np.arccos(np.clip(np.sin(lat)[:, None] * np.sin(lat) + np.cos(lat)[:, None] * np.cos(lat) * np.cos(lon[:, None] - lon), -1, 1))
np.fill_diagonal(D, np.nan)
rng = np.random.default_rng(0)
own, near, far = [], [], []
for i, g in enumerate(ids):
    own.append(A[g].corr(Y[g]))
    j = np.nanargmin(D[i])
    if D[i, j] < 300:
        near.append(A[ids[j]].corr(Y[g]))
    cand = np.where(D[i] > 1500)[0]
    far.append(A[ids[rng.choice(cand)]].corr(Y[g]) if len(cand) else np.nan)
rows = [{"test": "A own reservoir", "n": len(own), "median_r": np.nanmedian(own)},
        {"test": "A placebo: nearest other reservoir (<300 km)", "n": len(near), "median_r": np.nanmedian(near)},
        {"test": "A placebo: random reservoir >1500 km away", "n": int(np.isfinite(far).sum()), "median_r": np.nanmedian(far)}]
carry = set(us[(us.res_time_days >= 100) & (us.gww_poly_km2 >= 10)].gww_id)
ci = [k for k, g in enumerate(ids) if g in carry]
rows += [{"test": "A own reservoir (carry-over subset)", "n": len(ci), "median_r": np.nanmedian([own[k] for k in ci])},
         {"test": "A nearest-other placebo (carry-over subset)", "n": len(ci), "median_r": np.nanmedian([A[ids[np.nanargmin(D[k])]].corr(Y[ids[k]]) for k in ci])}]


def causal_monthly(gid, k=6, rel=0.25):
    s = fetch_raw(gid)
    s = s[s > 0]
    keep, hist = [], []
    for v in s.values:
        ok = len(hist) < 3 or abs(v - np.median(hist[-k:])) <= rel * np.median(hist[-k:])
        keep.append(ok)
        if ok:
            hist.append(v)
    m = s[np.array(keep, bool)].resample("MS").median()
    return m.ffill(limit=2)  # carry the last observation forward, never interpolate towards the future


sub = [g for g in ids if g in carry]
rc, rp = [], []
for g in sub:
    a = causal_monthly(g)
    a = a[a.index >= "2001-01-01"]
    an = (a - a.groupby(a.index.month).transform("mean")) / a.mean()
    rc.append(an.reindex(Y.index).corr(Y[g]))
    rp.append(A[g].corr(Y[g]))
rows += [{"test": "B centred despike filter (production), carry-over", "n": len(sub), "median_r": np.nanmedian(rp)},
         {"test": "B strictly causal filter + forward-fill, carry-over", "n": len(sub), "median_r": np.nanmedian(rc)}]
yr = F.groupby(F.month.dt.year).a0.mean()
for y0, y1, lab in [(2001, 2012, "C mean pooled area anomaly 2001-2012 (Landsat 5/7)"), (2013, 2016, "C 2013-2016 (+Landsat 8)"), (2017, 2025, "C 2017-2025 (+Sentinel-2)")]:
    rows.append({"test": lab, "n": int(F[(F.month.dt.year >= y0) & (F.month.dt.year <= y1)].gww_id.nunique()), "median_r": np.nan, "value": yr.loc[y0:y1].mean()})
gy = F.groupby(F.month.dt.year).y.mean()
rows.append({"test": "C (for comparison) mean generation anomaly 2017-2025", "value": gy.loc[2017:2025].mean()})
R = pd.DataFrame(rows)
R.to_csv(RESULTS / "robustness.csv", index=False)
print(R.round(3).to_string())
