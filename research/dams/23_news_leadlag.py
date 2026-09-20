"""Lead time vs the news, measured rather than asserted: cross-correlation between each hydro-dependent country's
satellite reservoir deficit (capacity-weighted area anomaly, sign flipped) and log GDELT power-shortage coverage.
k > 0 means the reservoir deficit LEADS the news by k months. 2017+ only (GDELT DOC index).
Output results/news_leadlag.csv"""
import numpy as np
import pandas as pd

from common import DATA, RESULTS

news = pd.read_parquet(DATA / "gdelt_shortage_news.parquet")
P = pd.read_parquet(RESULTS / "predictions_world.parquet")
cs = pd.read_csv(RESULTS / "case_studies_monthly.csv", parse_dates=["month"])
yr = pd.read_parquet(DATA / "ember" / "yearly_country.parquet")
share = (yr[(yr.year >= 2015) & (yr.year <= 2023)].assign(s=lambda d: d.hydro_twh / d.total_twh).groupby("iso3").s.mean())
LAGS = range(-6, 13)
rows = []
for iso, nw in news.groupby("iso3"):
    ln = np.log1p(nw.set_index("month").share_ppm)
    ln = ln - ln.rolling(24, min_periods=12).median().shift(1).bfill()  # coverage drifts; score departures from the recent norm
    d = P[P.iso3 == iso]
    src = "monitored fleet (capacity-weighted)"
    if d.gww_id.nunique() < 1:
        d = cs[cs.iso3 == iso].rename(columns={"pred_gbm_area+climate": "pred"}).assign(capacity_mw=1.0)
        src = "case-study reservoirs"
    if d.empty:
        continue
    w = d.capacity_mw.fillna(1).clip(lower=1)
    deficit = -((d.a0 * w).groupby(d.month).sum() / w.groupby(d.month).sum())
    deficit = deficit.rolling(3, min_periods=2).mean()
    cc = {k: deficit.corr(ln.shift(-k)) for k in LAGS}
    best = max(cc, key=lambda k: cc[k])
    rows.append({"iso3": iso, "hydro_share_of_generation": share.get(iso, np.nan), "n_reservoirs": int(d.gww_id.nunique()), "index_source": src,
                 "n_months": int(pd.concat([deficit, ln], axis=1).dropna().shape[0]), "r_lag0": cc[0], "r_deficit_leads_3mo": cc[3],
                 "r_deficit_leads_6mo": cc[6], "r_news_leads_3mo": cc[-3], "best_lag_months": best, "r_best": cc[best]})
R = pd.DataFrame(rows).sort_values("r_best", ascending=False)
R.to_csv(RESULTS / "news_leadlag.csv", index=False)
pd.set_option("display.width", 250)
print(R.round(2).to_string())
dep = R[R.hydro_share_of_generation >= 0.4]
print(f"\nhydro-dependent (>=40%) countries: n={len(dep)}, median r_lag0={dep.r_lag0.median():.2f}, median r_best={dep.r_best.median():.2f}, "
      f"median best lag={dep.best_lag_months.median():.0f} mo, share with r_best>=0.3: {(dep.r_best >= 0.3).mean():.2f}")

# Post-hoc illustration (NOT part of the pre-registered country test): Zambia with reservoir-specific series.
ln = np.log1p(news[news.iso3 == "ZMB"].set_index("month").share_ppm)
itt = -cs[cs.name == "Itezhi-Tezhi"].set_index("month").a0.rolling(3, min_periods=2).mean()
k = pd.read_csv(RESULTS / "s2_kariba_matusadona_area.csv")
k = k[(k.valid_frac >= 0.97) & (k.scene_cloud < 10)].assign(month=lambda d: pd.to_datetime(d.month + "-01"))
s = k.set_index("month").water_km2_scene.asfreq("MS").interpolate(limit=3)
kar = -(s - s.groupby(s.index.month).transform("mean")) / s.mean()
gww = -cs[cs.name == "Kariba"].set_index("month").a0.rolling(3, min_periods=2).mean()
Z = pd.DataFrame([{"series": n, **{f"r_k={kk:+d}": x.corr(ln.shift(-kk)) for kk in (-4, -2, 0, 2, 4, 6)}}
                  for n, x in [("Kariba whole-lake (GWW)", gww), ("Kariba shallow sector (own Sentinel-2)", kar), ("Itezhi-Tezhi (GWW)", itt)]])
Z.to_csv(RESULTS / "news_leadlag_zambia_posthoc.csv", index=False)
print(Z.round(2).to_string())
