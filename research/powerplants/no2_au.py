"""Out-of-country check of the NO2 index: Australian coal plants vs AEMO 5-min generation (no NOx labels exist; AU coal has no SCR so NOx ~ MW)."""
import numpy as np, pandas as pd, json
from scipy.stats import pearsonr
cal = json.load(open("no2_calibration.json"))
d = pd.read_csv("no2_daily_au.csv", parse_dates=["day"]); d = d[d.ws.between(2, 9)].copy(); d["idx"] = d.enh/np.exp(cal["temp_coef_per_degC"]*(d.temp-15))
meta = pd.read_csv("plants_au.csv"); name2id = dict(zip(meta.plant_name_eia, meta.plant_id_eia))
s = pd.read_parquet("aemo/scada.parquet"); s["plant"] = s.plant.map(name2id); s = s.dropna(subset=["plant"])
tot = s.groupby(["plant", "t_aest"]).SCADAVALUE.sum().reset_index(); tot["day"] = tot.t_aest.dt.floor("D")
daily = tot.groupby(["plant", "day"]).SCADAVALUE.mean().rename("mw_day").reset_index()
over = tot[tot.t_aest.dt.hour.between(11, 13)].groupby(["plant", "day"]).SCADAVALUE.mean().rename("mw_overpass").reset_index()
d = d.merge(daily, on=["plant", "day"]).merge(over, on=["plant", "day"])
det = d.groupby("plant").enh.agg(["mean", "std", "size"]); det["t"] = det["mean"]/(det["std"]/np.sqrt(det["size"])); det["detectable"] = (det["mean"] >= cal["detect_mean_enh"]) & (det.t >= cal["detect_t"])
rows = []
for p, g in d.groupby("plant"):
    g = g.set_index("day").sort_index(); full = daily[daily.plant == p].set_index("day").mw_day
    roll = g.idx.rolling("30D", min_periods=8).mean(); mw = full.rolling("30D", min_periods=15).mean().reindex(roll.index)
    k = (np.arange(len(roll)) % 1 == 0); x = pd.DataFrame(dict(i=roll, m=mw)).dropna(); xs = x.groupby((x.index - x.index.min()).days // 30).first()      # one value per 30-day block
    rows.append(dict(plant=p, n_days=len(g), mean_enh=det.loc[p, "mean"], t=det.loc[p, "t"], detectable=bool(det.loc[p, "detectable"]), r_daily_overpass=pearsonr(g.enh, g.mw_overpass)[0],
                     r_30d_all=pearsonr(x.i, x.m)[0], n_nonoverlap=len(xs), r_30d_nonoverlap=pearsonr(xs.i, xs.m)[0] if len(xs) >= 6 else np.nan, cv_mw_30d=float(x.m.std()/x.m.mean())))
R = pd.DataFrame(rows); R.to_csv("no2_au_results.csv", index=False); print(R.round(2).to_string())
