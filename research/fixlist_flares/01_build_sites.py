"""Step 1. Persistent night-time thermal sources -> proto flare SITES, per country.

Input : FIRMS keyless country-year CSVs (VIIRS S-NPP 375 m, 2012-2024).
        * read-only local copies from ../wardamage/data/firms_archive where they exist
        * otherwise STREAMED over HTTP into memory (raw detections are never written to disk)
Output: cache/sites_{country}.parquet       one row per proto-site (loose superset; thresholds applied in step 2)
        cache/siteyear_{country}.parquet    site x year  : nights, frp stats, brightness, FIRMS type shares
        cache/sitemonth_{country}.parquet   site x month : nights, sum of nightly FRP
Method: night detections (confidence n/h), outage days dropped (wardamage calendar, never zero-filled),
        0.01 deg cells; candidate cell = >=8 detection-nights in >=2 calendar years;
        candidate cells are grouped into sites by hill-climbing on smoothed night counts (peaks >=3.3 km apart),
        all statistics are then recomputed from detections at SITE level (unique nights).
"""
import sys, io, os, time, numpy as np, pandas as pd, requests
from pathlib import Path
from scipy.spatial import cKDTree

HERE = Path(__file__).parent
WD = HERE.parent / "wardamage" / "data"
ARCH = WD / "firms_archive"
CACHE = HERE / "cache"; CACHE.mkdir(exist_ok=True)
UA = {"User-Agent": "fixlist_flares-research/0.1 (hackathon research; polite, cached)"}
URL = "https://firms.modaps.eosdis.nasa.gov/data/country/viirs-snpp/{y}/viirs-snpp_{y}_{c}.csv"
COLS = ["latitude", "longitude", "bright_ti4", "acq_date", "confidence", "bright_ti5", "frp", "daynight", "type"]
RES = 0.01

def bad_days():
    o = pd.read_csv(WD / "satellite_outage_calendar.csv", index_col=0, parse_dates=True)
    o = o[(o.sat == "N") & (o.outage | o.degraded)]
    b = set()
    for d in o.index:
        for k in (-1, 0, 1): b.add(d + pd.Timedelta(days=k))
    return pd.DatetimeIndex(sorted(b))

def read_year(c, y):
    p = ARCH / f"viirs-snpp_{y}_{c}.csv"
    if p.exists() and p.stat().st_size > 2000:
        d = pd.read_csv(p, usecols=COLS)
    else:
        for a in range(4):
            try:
                r = requests.get(URL.format(y=y, c=c), headers=UA, timeout=900)
                if r.status_code == 404: return None
                r.raise_for_status()
                d = pd.read_csv(io.BytesIO(r.content), usecols=COLS); break
            except Exception as ex:
                print("  retry", c, y, repr(ex)[:80], flush=True); time.sleep(5 + 10 * a)
        else:
            return None
    n_all = len(d)
    d = d[(d.daynight == "N") & (d.confidence != "l")]
    d = d.assign(date=pd.to_datetime(d.acq_date)).drop(columns=["acq_date", "daynight", "confidence"])
    for k in ["bright_ti4", "bright_ti5", "frp"]: d[k] = d[k].astype("float32")
    d["type"] = d["type"].astype("int8")
    return d, n_all

def build(c, years):
    out = CACHE / f"sites_{c}.parquet"
    if out.exists(): print("skip", c); return
    t0 = time.time(); parts = []; got = []
    for y in years:
        r = read_year(c, y)
        if r is None: print("  missing", c, y, flush=True); continue
        parts.append(r[0]); got.append(y)
    if not parts: print("NO DATA", c); return
    h = pd.concat(parts, ignore_index=True); del parts
    h = h[~h.date.isin(bad_days())]
    h["cx"] = np.round(h.longitude / RES).astype("int32"); h["cy"] = np.round(h.latitude / RES).astype("int32")
    h["year"] = h.date.dt.year.astype("int16")
    # candidate cells
    cy_n = h.groupby(["cx", "cy", "year"]).date.nunique()
    ok = (cy_n >= 8).groupby(level=[0, 1]).sum()
    cand = ok[ok >= 2].index
    tot = h.groupby(["cx", "cy"]).date.nunique().loc[cand]
    if len(tot) == 0:
        pd.DataFrame().to_parquet(out); print(c, "no candidates"); return
    cells = tot.reset_index(name="nights")
    lat = cells.cy * RES; lon = cells.cx * RES
    xy = np.c_[lon * 111.32 * np.cos(np.radians(lat)), lat * 110.57]
    # NB: x uses local cos(lat); fine for neighbour searches at <5 km scale
    tr = cKDTree(xy)
    nb17 = tr.query_ball_point(xy, 1.7); w = cells.nights.values.astype(float)
    s = np.array([w[i].sum() for i in nb17])
    nb33 = tr.query_ball_point(xy, 3.3)
    ptr = np.array([max(n, key=lambda j: (s[j], -j)) for n in nb33])
    for _ in range(50):
        nxt = ptr[ptr]
        if (nxt == ptr).all(): break
        ptr = nxt
    cells["site"] = ptr
    h = h.merge(cells[["cx", "cy", "site"]], on=["cx", "cy"], how="inner")
    h["sid"] = c + "_" + h.site.astype(str)
    # nightly sums per site
    nightly = h.groupby(["sid", "date"]).agg(frp=("frp", "sum"), npx=("frp", "size"), ti4=("bright_ti4", "max"), ti5=("bright_ti5", "mean")).reset_index()
    nightly["year"] = nightly.date.dt.year; nightly["month"] = nightly.date.dt.to_period("M").dt.to_timestamp()
    sy = nightly.groupby(["sid", "year"]).agg(nights=("date", "size"), frp_sum=("frp", "sum"), frp_med=("frp", "median"), frp_mean=("frp", "mean"),
                                              npx_mean=("npx", "mean"), ti4_max_mean=("ti4", "mean"), ti5_mean=("ti5", "mean")).reset_index()
    sm = nightly.groupby(["sid", "month"]).agg(nights=("date", "size"), frp_sum=("frp", "sum")).reset_index()
    g = h.groupby("sid")
    wsum = g.frp.sum()
    site = pd.DataFrame({
        "lat": (h.latitude * h.frp).groupby(h.sid).sum() / wsum, "lon": (h.longitude * h.frp).groupby(h.sid).sum() / wsum,
        "lat_med": g.latitude.median(), "lon_med": g.longitude.median(),
        "lat_sd_km": g.latitude.std() * 110.57, "n_det": g.size(), "n_cells": h.groupby("sid").apply(lambda x: len(set(zip(x.cx, x.cy))), include_groups=False),
        "type0": g.type.apply(lambda x: (x == 0).mean()), "type1": g.type.apply(lambda x: (x == 1).mean()),
        "type2": g.type.apply(lambda x: (x == 2).mean()), "type3": g.type.apply(lambda x: (x == 3).mean()),
        "ti4_mean": g.bright_ti4.mean(), "ti5_mean": g.bright_ti5.mean(), "frp_px_med": g.frp.median()}).reset_index()
    site["country_file"] = c; site["years_read"] = ",".join(map(str, got))
    site.to_parquet(out); sy.to_parquet(CACHE / f"siteyear_{c}.parquet"); sm.to_parquet(CACHE / f"sitemonth_{c}.parquet")
    print(f"{c}: night det {len(h):,} in {len(site):,} proto-sites; years {got[0]}-{got[-1]} ({len(got)}); {time.time()-t0:.0f}s", flush=True)

if __name__ == "__main__":
    ALL = list(range(2012, 2025)); SUB = [2013, 2016, 2019, 2021, 2022, 2023, 2024]
    for a in sys.argv[1:]:
        c, _, mode = a.partition(":")
        try: build(c, SUB if mode == "sub" else ALL)
        except OSError as ex:
            print("DISK/OS ERROR - stopping", ex); raise
