"""TROPOMI NO2 activity index vs CEMS NOx: ablations, 30-day index, leave-plants-out calibration, outage detection power."""
import numpy as np, pandas as pd, json
from scipy.stats import pearsonr, spearmanr
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold
d = pd.read_csv("no2_daily_us.csv", parse_dates=["day"]); d["plant"] = d.plant.astype(str)
pl = pd.read_csv("plants_no2_us.csv"); pl["plant"] = pl.plant_id_eia.astype(str); pl = pl.set_index("plant")
c = pd.read_parquet("cems_no2_us.parquet"); c["plant"] = c.plant_id_eia.astype(str); c["nox_lbs"] = c.nox_lbs.fillna(0)
# CEMS at overpass (3 h up to ~13:30 local solar) and daily all-hours mean
lab = []
for p, g in c.groupby("plant"):
    g = g.set_index("t").sort_index(); off = pd.Timedelta(hours=round(13.5 - pl.loc[p].longitude/15))
    r3 = g[["nox_lbs", "gross_mw"]].rolling("3h").mean(); r3.index = r3.index - off                   # index = local-day midnight + 0h when t == overpass hour
    o = r3[r3.index.hour == 0]; o.index = o.index.floor("D")
    dm = g[["nox_lbs", "gross_mw"]].copy(); dm.index = (dm.index - off + pd.Timedelta(hours=13)).floor("D"); dm = dm.groupby(level=0).mean()
    x = o.join(dm, rsuffix="_daymean"); x["plant"] = p; lab.append(x.rename_axis("day").reset_index())
lab = pd.concat(lab); d = d.merge(lab, on=["plant", "day"]); d["fuel"] = d.plant.map(pl.fuel)
res = []
def add(metric, value, n, note=""): res.append(dict(metric=metric, value=float(value), n=int(n), note=note)); print(f"{metric:70s} {value:8.3f} n={n} {note}")
# ---- 1. daily ablation
def per_plant_r(df, col, y="nox_lbs"):
    return pd.Series({p: pearsonr(g[col], g[y])[0] for p, g in df.groupby("plant") if len(g) > 30 and g[y].std() > 0})
ALPHA = 0.0
wf = d[d.ws.between(2, 9)].copy()
for a_ in (0.0, 0.5, 1.0): wf[f"idx{a_}"] = wf.enh*wf.ws**a_
# label-free detectability screen: long-run mean enhancement must be clearly > 0 (TROPOMI point-source detection limit)
det = wf.groupby("plant").enh.agg(["mean", "std", "size"]); det["t"] = det["mean"]/(det["std"]/np.sqrt(det["size"])); det["detectable"] = (det["mean"] >= 2.0) & (det.t >= 8)
det = det.join(pl[["plant_name_eia", "fuel", "nox_lbs_h"]]); det.to_csv("no2_detectability_us.csv")
add("plants passing label-free detectability screen (mean enh>=2 umol/m2, t>=8)", det.detectable.sum(), len(det), f"median CEMS NOx of passing {det[det.detectable].nox_lbs_h.median():.0f} lbs/h vs failing {det[~det.detectable].nox_lbs_h.median():.0f}")
for a_ in (0.0, 0.5, 1.0):
    rr = per_plant_r(wf[wf.plant.isin(det.index[det.detectable])], f"idx{a_}"); add(f"daily per-plant r, detectable plants, index=enh*u^{a_}", rr.median(), len(rr), f"IQR {rr.quantile(.25):.2f}-{rr.quantile(.75):.2f}")
for name, df, col in [("simple disc-annulus, all winds", d, "simple"), ("wind-rotated enh, all winds", d, "enh"), ("wind-rotated flux (enh*u), all winds", d, "flux"),
                      ("wind-rotated enh, 2-9 m/s", wf, "enh"), ("wind-rotated flux, 2-9 m/s", wf, "flux")]:
    r = per_plant_r(df, col); add(f"daily per-plant pearson r vs CEMS NOx, median [{name}]", r.median(), len(r), f"IQR {r.quantile(.25):.2f}-{r.quantile(.75):.2f}; plant-days {len(df)}")
r = per_plant_r(wf, "flux"); r.rename("r_daily_flux").to_csv("no2_per_plant_daily_r.csv")
for f_, g in wf.groupby("fuel"): rr = per_plant_r(g, "flux"); add(f"daily per-plant r, fuel={f_}", rr.median(), len(rr))
add("daily pooled pearson flux vs NOx", pearsonr(wf.flux, wf.nox_lbs)[0], len(wf)); add("daily pooled pearson flux vs MW", pearsonr(wf.flux, wf.gross_mw)[0], len(wf))
# ---- 2. rolling index
def rolling(df, win, minn):
    out = []
    for p, g in df.groupby("plant"):
        full = lab[lab.plant == p].set_index("day").sort_index(); g = g.set_index("day").reindex(full.index)
        o = pd.DataFrame({"flux": g.flux.rolling(f"{win}D", min_periods=minn).mean(), "nvalid": g.flux.rolling(f"{win}D").count(), "temp": g.temp.rolling(f"{win}D", min_periods=minn).mean(),
                          "nox_same": g.nox_lbs.rolling(f"{win}D", min_periods=minn).mean(), "nox_all": full.nox_lbs_daymean.rolling(f"{win}D", min_periods=win//2).mean(),
                          "mw_all": full.gross_mw_daymean.rolling(f"{win}D", min_periods=win//2).mean()})
        o["plant"] = p; out.append(o.reset_index())
    o = pd.concat(out).dropna(subset=["flux", "nox_all"])
    for col in ["flux", "nox_same", "nox_all", "mw_all"]: o[col+"_rel"] = o[col]/o.groupby("plant")[col].transform("mean")
    o["z"] = (o.flux - o.groupby("plant").flux.transform("mean"))/o.groupby("plant").flux.transform("std")
    return o
allroll = {}
for win, minn in [(14, 4), (30, 8), (60, 15)]:
    o = rolling(wf[wf.plant.isin(det.index[det.detectable])].assign(flux=lambda x: x[f"idx{ALPHA}"]), win, minn); allroll[win] = o
    s = o[(o.day - o.day.min()).dt.days % win == 0]                                                   # non-overlapping windows
    add(f"{win}-day index vs {win}-day mean CEMS NOx (relative to plant mean), pooled pearson, non-overlapping", pearsonr(s.flux_rel, s.nox_all_rel)[0], len(s), "spearman %.2f" % spearmanr(s.flux_rel, s.nox_all_rel)[0])
    wp = pd.Series({p: pearsonr(g.flux_rel, g.nox_all_rel)[0] for p, g in s.groupby("plant") if len(g) >= 8 and g.nox_all_rel.std() > 0.05})
    add(f"{win}-day index: within-plant pearson median", wp.median(), len(wp), f"IQR {wp.quantile(.25):.2f}-{wp.quantile(.75):.2f}")
    add(f"{win}-day index vs MW (relative), pooled pearson", pearsonr(s.flux_rel, s.mw_all_rel)[0], len(s))
o = allroll[30]
# ---- 3. temperature (NO2 lifetime) correction learned on training plants only
plants_u = o.plant.unique(); o["flux_rel_corr"] = np.nan; o["pred_rel"] = np.nan; o["lo"] = np.nan; o["hi"] = np.nan
for tr, te in GroupKFold(6).split(plants_u, groups=plants_u):
    trp, tep = plants_u[tr], plants_u[te]; a = o[o.plant.isin(trp) & (o.flux_rel > 0.05) & (o.nox_all_rel > 0.05)]
    b = np.polyfit(a.temp - 15, np.log(a.flux_rel/a.nox_all_rel), 1)[0]
    m = o.plant.isin(tep); corr = o.loc[m, "flux"]/np.exp(b*(o.loc[m, "temp"] - 15)); o.loc[m, "flux_rel_corr"] = corr/corr.groupby(o.loc[m, "plant"]).transform("mean")
    a = o[o.plant.isin(trp)].copy(); corr_a = a.flux/np.exp(b*(a.temp-15)); a["x"] = corr_a/corr_a.groupby(a.plant).transform("mean")
    k = np.polyfit(a.x, a.nox_all_rel, 1); resid = a.nox_all_rel - np.polyval(k, a.x); q = np.quantile(resid, [0.1, 0.9])
    o.loc[m, "pred_rel"] = np.polyval(k, o.loc[m, "flux_rel_corr"]); o.loc[m, "lo"] = o.loc[m, "pred_rel"] + q[0]; o.loc[m, "hi"] = o.loc[m, "pred_rel"] + q[1]
add("temperature coefficient of index/NOx ratio (per degC, last fold)", b, len(a), "negative = NO2 per unit NOx higher when cold (longer lifetime)")
s = o[(o.day - o.day.min()).dt.days % 30 == 0]
add("30-day held-out: pooled pearson, raw relative index", pearsonr(s.flux_rel, s.nox_all_rel)[0], len(s)); add("30-day held-out: pooled pearson, temperature-corrected index", pearsonr(s.flux_rel_corr, s.nox_all_rel)[0], len(s))
add("30-day held-out: 80% prediction-interval coverage", ((s.nox_all_rel >= s.lo) & (s.nox_all_rel <= s.hi)).mean(), len(s), f"mean interval width {np.mean(s.hi-s.lo):.2f} (in units of plant-mean NOx)")
add("30-day held-out: RMSE of relative NOx", np.sqrt(np.mean((s.pred_rel - s.nox_all_rel)**2)), len(s), f"vs sd of truth {s.nox_all_rel.std():.2f}")
o["zc"] = (o.flux_rel_corr - 1)/o.groupby("plant").flux_rel_corr.transform("std"); s = o[(o.day - o.day.min()).dt.days % 30 == 0]
cal = s.groupby(pd.cut(s.zc, [-9, -2, -1, 1, 2, 9])).nox_all_rel.describe(percentiles=[.1, .5, .9])[["count", "10%", "50%", "90%"]]; cal.to_csv("no2_calibration_by_z.csv"); print(cal.round(2))
calr = s.groupby(pd.cut(s.flux_rel_corr, [-5, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2, 9])).nox_all_rel.describe(percentiles=[.1, .5, .9])[["count", "10%", "50%", "90%"]]; calr.to_csv("no2_calibration_by_index.csv"); print(calr.round(2))
o.to_csv("no2_index_30d_us.csv", index=False)
a = o[(o.flux_rel > 0.05) & (o.nox_all_rel > 0.05)]; b_all = np.polyfit(a.temp - 15, np.log(a.flux_rel/a.nox_all_rel), 1)[0]
k_all = np.polyfit(o.flux_rel_corr.dropna(), o.nox_all_rel[o.flux_rel_corr.notna()], 1); rq = np.quantile(o.nox_all_rel - np.polyval(k_all, o.flux_rel_corr), [0.1, 0.9])
json.dump(dict(temp_coef_per_degC=float(b_all), slope=float(k_all[0]), intercept=float(k_all[1]), resid_q10=float(rq[0]), resid_q90=float(rq[1]), detect_mean_enh=2.0, detect_t=8.0, alpha=ALPHA), open("no2_calibration.json", "w"), indent=1)
w = o[(o.day - o.day.min()).dt.days % 10 == 0]; out_ = w[w.nox_all_rel < 0.3]; norm = w[w.nox_all_rel > 0.7]
if len(out_) >= 5:
    thr = np.quantile(norm.flux_rel_corr, 0.05)
    add("outage detection AUC, 30-day, temperature-corrected held-out index", roc_auc_score(np.r_[np.ones(len(out_)), np.zeros(len(norm))], -np.r_[out_.flux_rel_corr, norm.flux_rel_corr]), len(out_), f"{out_.plant.nunique()} plants")
    add("outage detection rate at 5% false alarms, 30-day, temperature-corrected", (out_.flux_rel_corr < thr).mean(), len(out_), f"threshold index<{thr:.2f} of plant mean")
# ---- 4. outage detection power (real CEMS outages, stride 10 d to limit overlap)
for win in (14, 30, 60):
    w = allroll[win]; w = w[(w.day - w.day.min()).dt.days % 10 == 0]
    out_ = w[w.nox_all_rel < 0.3]; norm = w[w.nox_all_rel > 0.7]
    if len(out_) < 5: continue
    y = np.r_[np.ones(len(out_)), np.zeros(len(norm))]; sc = -np.r_[out_.flux_rel, norm.flux_rel]; thr = np.quantile(norm.flux_rel, 0.05)
    add(f"outage detection AUC, {win}-day window (NOx<30% of normal vs >70%)", roc_auc_score(y, sc), len(out_), f"{out_.plant.nunique()} plants with outages; {len(norm)} normal windows")
    add(f"outage detection rate at 5% false alarms, {win}-day", (out_.flux_rel < thr).mean(), len(out_), f"threshold index<{thr:.2f} of plant mean")
pd.DataFrame(res).to_csv("no2_calibration_results.csv", index=False)
