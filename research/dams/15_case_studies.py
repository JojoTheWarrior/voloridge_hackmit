"""Apply the pipeline where little or nothing is published: headline hydro-dependent reservoirs.
For each case reservoir: cleaned area, anomaly, expanding-window deficit z, US-trained predicted generation anomaly
(+10-90 % band). Then a scoreboard against curated, news-dated shortage episodes (data/known_events.csv): what did the
satellite series say 6 / 3 / 0 months before each episode, and when (if ever) did the pre-registered alert fire?
Outputs results/case_studies_monthly.csv, results/case_event_scoreboard.csv"""
import numpy as np
import pandas as pd

from apply_model import predict
from areas import monthly
from common import DATA, RESULTS

Z_ON = -1.5
cs = pd.read_csv(DATA / "case_studies.csv")
cat = pd.read_parquet(DATA / "gww_catalogue.parquet", columns=["gww_id", "source_name", "source_id", "poly_km2"])
cat["gww_id"] = cat.gww_id.astype(int)
hl = pd.read_parquet(DATA / "hydrolakes_pts.parquet").set_index("Hylak_id")
basins = pd.read_parquet(DATA / "basins.parquet")
clim = pd.read_parquet(DATA / "basin_climate.parquet")

rows, st_rows = [], []
for r in cs.itertuples():
    m = monthly(r.gww_id).reset_index(names="month")
    m = m[m.month >= "2001-01-01"].assign(gww_id=r.gww_id, capacity_mw=r.capacity_mw)
    rows.append(m)
    c = cat[cat.gww_id == r.gww_id].iloc[0]
    h = hl.loc[c.source_id] if c.source_name == "HydroLAKES" and c.source_id in hl.index else None
    st_rows.append({"gww_id": r.gww_id, "name": r.name, "country": r.country, "lat": r.lat, "lon": r.lon, "capacity_mw": r.capacity_mw,
                    "gww_poly_km2": c.poly_km2, "res_time_days": h.Res_time if h is not None else np.nan,
                    "depth_avg_m": h.Depth_avg if h is not None else np.nan, "elevation_m": h.Elevation if h is not None else np.nan})
panel = pd.concat(rows)
st = pd.DataFrame(st_rows).merge(basins, on="gww_id", how="left")
P = predict(panel, st, clim)


def expanding_z(s, min_prior=8, floor=0.02):
    z = pd.Series(np.nan, index=s.index)
    allmu = s.expanding().mean().shift(1)
    for moy in range(1, 13):
        x = s[s.index.month == moy]
        z[x.index] = ((x - x.expanding().mean().shift(1)) / np.maximum(x.expanding().std().shift(1), floor * allmu.reindex(x.index))).where(
            x.notna().cumsum().shift(1) >= min_prior)
    return z


out = []
for gid, d in P.groupby("gww_id"):
    d = d.set_index("month")
    d["z"] = expanding_z(panel[panel.gww_id == gid].set_index("month").area_km2.asfreq("MS")).reindex(d.index)
    d["alert_on"] = (d.z <= Z_ON) & (d.z.shift(1) <= Z_ON)
    out.append(d.reset_index())
C = pd.concat(out).merge(cs[["gww_id", "name", "iso3"]], on="gww_id")
keep = ["name", "iso3", "gww_id", "month", "area_km2", "n_obs", "a0", "z", "alert_on", "pred_gbm_area", "pred_gbm_climate", "pred_gbm_area+climate", "pred_lo", "pred_hi", "p12"]
C[keep].to_csv(RESULTS / "case_studies_monthly.csv", index=False)

ev = pd.read_csv(DATA / "known_events.csv")
sb = []
for e in ev.itertuples():
    t0 = pd.Timestamp(e.start + "-01")
    for res in e.reservoirs.split("|"):
        d = C[C.name == res].set_index("month")
        if d.empty:
            continue
        at = lambda k, col: d[col].reindex([t0 - pd.DateOffset(months=k)]).iloc[0]
        pre = d[(d.index >= t0 - pd.DateOffset(months=18)) & (d.index <= t0 + pd.DateOffset(months=6)) & d.alert_on]
        first = pre.index.min() if len(pre) else pd.NaT
        sb.append({"case": e.case, "reservoir": res, "hydrological": e.hydrological, "event_start": e.start,
                   "area_anom_t-6": at(6, "a0"), "area_anom_t-3": at(3, "a0"), "area_anom_t0": at(0, "a0"), "z_t-3": at(3, "z"), "z_t0": at(0, "z"),
                   "pred_gen_anom_t-3": at(3, "pred_gbm_area+climate"), "pred_gen_anom_t0": at(0, "pred_gbm_area+climate"),
                   "pred_climate_only_t0": at(0, "pred_gbm_climate"),
                   "first_alert_month": first, "alert_lead_months": (t0.to_period("M") - first.to_period("M")).n if pd.notna(first) else np.nan,
                   "valid_area_months_in_prior_year": int(d.area_km2.reindex(pd.date_range(t0 - pd.DateOffset(months=12), t0, freq="MS")).notna().sum())})
S = pd.DataFrame(sb)
S.to_csv(RESULTS / "case_event_scoreboard.csv", index=False)
print(S.round(2).to_string())
