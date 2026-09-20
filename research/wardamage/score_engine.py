"""Per-site VIIRS scoring: novel-cell detections, excess FRP over baseline, overpass/cloud proxy.

Detector (same rule for events and placebo windows):
  known cell  = 0.005 deg cell whose 3x3 neighbourhood was lit on >=2 distinct days in the baseline
                (all data from 2025-01-01 up to the day before the window start)
  novel pixel = detection within radius_km of the site in a cell that is not known
  FLAG        = within 72 h of window start: >=2 novel pixels, or 1 novel pixel with FRP>=10 MW,
                or a daily FRP sum > max(2 x baseline p99, baseline max) and >= 20 MW ("excess")
"""
import numpy as np, pandas as pd, glob
CELL = 0.005
WIN_H = 72

def load_hotspots():
    p = pd.read_parquet("data/hotspots_gulf.parquet")
    extra = [pd.read_parquet(f) for d in ("score_out/gibs_israel", "score_out/gibs_salalah") for f in glob.glob(d + "/*.parquet")]
    extra = [e for e in extra if len(e)]
    if extra:
        e = pd.concat(extra); e["date"] = pd.to_datetime(e.ACQ_DATE)
        p = pd.concat([p, e[[c for c in p.columns if c in e.columns]]])
    p = p.drop_duplicates(["LATITUDE", "LONGITUDE", "ACQ_DATE", "ACQ_TIME", "SATELLITE"])
    p["dt"] = pd.to_datetime(p.ACQ_DATE + " " + p.ACQ_TIME)
    p = p.rename(columns={"LATITUDE": "lat", "LONGITUDE": "lon"})
    return p[["lat", "lon", "dt", "date", "SATELLITE", "FRP", "DAYNIGHT", "CONFIDENCE", "SCAN"]].reset_index(drop=True)

def km(lat0, lon0, lat, lon):
    return np.hypot((lat - lat0) * 111.2, (lon - lon0) * 111.2 * np.cos(np.radians(lat0)))

def near(p, lat, lon, r_km):
    dlat = r_km / 111.2; dlon = dlat / np.cos(np.radians(lat))
    q = p[p.lat.between(lat - dlat, lat + dlat) & p.lon.between(lon - dlon, lon + dlon)].copy()
    q["dist_km"] = km(lat, lon, q.lat, q.lon)
    return q[q.dist_km <= r_km]

def mark_novel(site, t0):
    """site: detections within radius (+1 km margin). Baseline = everything before the UTC day of t0."""
    s = site.copy(); s["cx"] = (s.lon / CELL).round().astype(int); s["cy"] = (s.lat / CELL).round().astype(int)
    b = s[s.date < t0.normalize()].groupby(["cx", "cy"]).date.nunique()
    known = {(cx + dx, cy + dy) for (cx, cy), n in b.items() if n >= 2 for dx in (-1, 0, 1) for dy in (-1, 0, 1)}
    s["novel"] = np.array([(a, c) not in known for a, c in zip(s.cx, s.cy)], dtype=bool)
    return s

def baseline_stats(site, t0, lookback_days=180):
    lo = max(t0.normalize() - pd.Timedelta(days=lookback_days), pd.Timestamp("2025-01-01"))
    days = pd.date_range(lo, t0.normalize() - pd.Timedelta(days=1))
    d = site[(site.date >= lo) & (site.date < t0.normalize())].groupby("date").FRP.sum().reindex(days, fill_value=0.0)
    if not len(d): return dict(base_days=0, base_share_lit=np.nan, base_mean_frp=np.nan, base_p99_frp=np.nan, base_max_frp=np.nan)
    return dict(base_days=len(d), base_share_lit=round(float((d > 0).mean()), 3), base_mean_frp=round(float(d.mean()), 1),
                base_p99_frp=round(float(d.quantile(.99)), 1), base_max_frp=round(float(d.max()), 1))

def evaluate(p_site, t0, radius_km, follow_days=30):
    """p_site has dist_km. Returns dict of detector outputs for a window starting at t0 (UTC Timestamp)."""
    s = mark_novel(p_site, t0); s = s[s.dist_km <= radius_km]
    bs = baseline_stats(s, t0)
    w = s[(s.dt >= t0) & (s.dt < t0 + pd.Timedelta(hours=WIN_H))]
    nov = w[w.novel]
    daily = w.groupby("date").FRP.sum()
    thr = max(2 * (bs["base_p99_frp"] if bs["base_days"] else 0), bs["base_max_frp"] if bs["base_days"] else 0, 20.0)
    excess_days = daily[daily > thr]
    flag_novel = (len(nov) >= 2) or (len(nov) == 1 and nov.FRP.max() >= 10)
    flag_excess = len(excess_days) > 0
    out = dict(bs, n_det_72h=len(w), n_novel_72h=len(nov), novel_frp_72h=round(float(nov.FRP.sum()), 1),
               peak_daily_frp_72h=round(float(daily.max()), 1) if len(daily) else 0.0, excess_thr=round(thr, 1),
               flag_novel=bool(flag_novel), flag_excess=bool(flag_excess), flag=bool(flag_novel or flag_excess))
    first = None
    if flag_novel: first = nov.sort_values("dt").iloc[0]
    elif flag_excess: first = w[w.date == excess_days.index[0]].sort_values("dt").iloc[0]
    elif len(nov): first = nov.sort_values("dt").iloc[0]
    if first is not None:
        out.update(first_det_utc=first["dt"], first_det_sat=first.SATELLITE, first_det_daynight=first.DAYNIGHT,
                   first_det_frp=float(first.FRP), first_det_dist_km=round(float(first.dist_km), 2))
    # burn duration: run of days (gaps <=2 d) with novel pixels (frozen baseline) or excess FRP
    f = s[(s.dt >= t0) & (s.dt < t0 + pd.Timedelta(days=follow_days))]
    fd = f.groupby("date").agg(frp=("FRP", "sum"), nnov=("novel", "sum"))
    act = sorted(fd.index[(fd.nnov > 0) | (fd.frp > thr)])
    dur, last = 0, None
    for d in act:
        if last is None:
            if (d - t0.normalize()).days > 3: break
        elif (d - last).days > 3: break
        dur += 1; last = d
    out.update(burn_days=dur, burn_last_day=last, peak_daily_frp_30d=round(float(fd.frp.max()), 1) if len(fd) else 0.0,
               peak_day_30d=fd.frp.idxmax() if len(fd) else None, n_novel_30d=int(fd.nnov.sum()) if len(fd) else 0)
    return out

def overpass_check(p, lat, lon, t0, hours=24, flare_r_km=50, swath_r_km=250):
    """Cloud/coverage proxy. Pass = (satellite, ~6-min granule) with any detection within swath_r_km.
    Persistent neighbours = 0.02 deg cells within flare_r_km (excl. 3 km around site) lit on >=60% of the prior 60 days.
    Returns number of passes in the first `hours` and how many of them saw >=1 persistent neighbour."""
    reg = near(p, lat, lon, swath_r_km)
    nb = reg[(reg.dist_km <= flare_r_km) & (reg.dist_km > 3)].copy()
    nb["cell"] = list(zip((nb.lon / 0.02).round().astype(int), (nb.lat / 0.02).round().astype(int)))
    lo = t0.normalize() - pd.Timedelta(days=60)
    share = nb[(nb.date >= lo) & (nb.date < t0.normalize())].groupby("cell").date.nunique() / 60
    pers = set(share[share >= 0.6].index)
    w = reg[(reg.dt >= t0) & (reg.dt < t0 + pd.Timedelta(hours=hours))].copy()
    w["pass_id"] = w.SATELLITE + "_" + w.dt.dt.floor("10min").astype(str)
    passes = w.groupby("pass_id").dt.min().sort_values()
    wn = nb[(nb.dt >= t0) & (nb.dt < t0 + pd.Timedelta(hours=hours)) & nb.cell.isin(pers)].copy()
    wn["pass_id"] = wn.SATELLITE + "_" + wn.dt.dt.floor("10min").astype(str)
    seen = wn.groupby("pass_id").cell.nunique()
    return dict(n_persistent_neighbours=len(pers), n_passes_24h=len(passes), n_passes_neighbours_seen=int((seen > 0).sum()),
                best_pass_neighbour_frac=round(float(seen.max() / len(pers)), 2) if len(pers) and len(seen) else (0.0 if len(pers) else np.nan))
