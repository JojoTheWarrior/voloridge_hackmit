"""Second-pass S2 models (all leave-whole-plants-out): (a) on/off classifier, (b) monotone compact GBT, (c) physics-style weather-normalised plume index
   cf_hat = area_per_GW / g(weather), g learned on training plants only. Compares against raw area; then zero-shot on Australia."""
import numpy as np, pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor as HGR, HistGradientBoostingClassifier as HGC
from sklearn.model_selection import GroupKFold
from sklearn.metrics import roc_auc_score, average_precision_score
from scipy.stats import spearmanr
from s2_model import load, metrics
us = load("s2_features_us.csv", "us"); au = load("s2_features_au.csv", "au")
for d in (us, au): d["l_area"] = np.log1p(d.plume_per_gw*100); d["l_tower"] = np.log1p(d.plume_tower_km2*100); d["l_stack"] = np.log1p(d.plume_stack_km2*100)
COMPACT = ["l_area", "l_tower", "l_stack", "src_anom", "src_bright_frac", "plume_mean_anom", "shadow_score"]; WX = ["temperature_2m", "relative_humidity_2m", "dewdep", "wind_speed_10m", "sza"]
MONO = [1]*len(COMPACT) + [0]*len(WX)
def fit_predict(tr, te):
    o = {}
    o["clf_onoff_img+wx"] = HGC(max_depth=3, max_iter=150, learning_rate=0.05, min_samples_leaf=30, monotonic_cst=MONO, random_state=0).fit(tr[COMPACT+WX], tr.on).predict_proba(te[COMPACT+WX])[:, 1]
    o["clf_onoff_img"] = HGC(max_depth=3, max_iter=150, learning_rate=0.05, min_samples_leaf=30, monotonic_cst=MONO[:len(COMPACT)], random_state=0).fit(tr[COMPACT], tr.on).predict_proba(te[COMPACT])[:, 1]
    o["mono_gbt_img+wx"] = HGR(max_depth=3, max_iter=200, learning_rate=0.05, min_samples_leaf=30, monotonic_cst=MONO, random_state=0).fit(tr[COMPACT+WX], tr.cf).predict(te[COMPACT+WX])
    o["mono_gbt_img"] = HGR(max_depth=3, max_iter=200, learning_rate=0.05, min_samples_leaf=30, monotonic_cst=MONO[:len(COMPACT)], random_state=0).fit(tr[COMPACT], tr.cf).predict(te[COMPACT])
    on = tr[tr.cf > 0.2]; g = HGR(max_depth=3, max_iter=150, learning_rate=0.05, min_samples_leaf=40, random_state=0).fit(on[WX], np.log((on.plume_per_gw + 0.002)/on.cf))
    o["weather_normalised_area"] = (te.plume_per_gw + 0.002)/np.exp(g.predict(te[WX]))
    return o
res = []; 
for grp, sel in [("US towers+FGD (natural+mech draft)", us.group.isin(["natural_draft", "mech_draft"])), ("US natural-draft only", us.group == "natural_draft")]:
    d = us[sel & us.valid].reset_index(drop=True); cuts = np.quantile(us[us.group.isin(["natural_draft", "mech_draft"]) & us.valid].cf, [1/3, 2/3]); P = {}
    for tr, te in GroupKFold(6).split(d, groups=d.plant):
        for k, v in fit_predict(d.iloc[tr], d.iloc[te]).items(): P.setdefault(k, np.zeros(len(d)))[te] = v
    P["raw_area_per_GW"] = d.plume_per_gw.values
    for k, v in P.items(): r = metrics(d, np.asarray(v), k, cuts); r["subset"] = grp; res.append(r)
    if grp.startswith("US towers"):
        for k, v in P.items(): d["p_"+k] = v
        d["season"] = np.where(d.t.dt.month.isin([11, 12, 1, 2, 3]), "Nov-Mar", "Apr-Oct"); d["Tbin"] = pd.cut(d.temperature_2m, [-40, 5, 15, 25, 50]).astype(str); d["DDbin"] = pd.cut(d.dewdep, [-1, 5, 10, 15, 60]).astype(str)
        cond = []
        for col in ["season", "Tbin", "DDbin"]:
            for kk, g_ in d.groupby(col):
                if len(g_) < 40 or g_.on.nunique() < 2: continue
                row = dict(split=col, bin=kk, n=len(g_), n_off=int((g_.on == 0).sum()), median_area_when_on_km2=float(g_[g_.on == 1].plume_km2.median()))
                for m in ["raw_area_per_GW", "weather_normalised_area", "mono_gbt_img+wx", "clf_onoff_img+wx"]: row["auc_"+m] = roc_auc_score(g_.on, g_["p_"+m]); row["rho_"+m] = spearmanr(g_["p_"+m], g_.cf)[0]
                cond.append(row)
        C = pd.DataFrame(cond); C.to_csv("s2_us_condition_splits_v2.csv", index=False); pd.set_option("display.width", 300); print(C.round(3).to_string()); d.to_csv("s2_us_cv_predictions_v2.csv", index=False)
        # pooled-vs-within-bin: does conditioning on weather matter? compare pooled rho of raw area with rho of weather-normalised area, plant-bootstrap the difference
        rng = np.random.default_rng(1); pl = d.plant.unique(); diffs = []
        for _ in range(1000):
            s = pd.concat([d[d.plant == p] for p in rng.choice(pl, len(pl))]); diffs.append([spearmanr(s["p_weather_normalised_area"], s.cf)[0] - spearmanr(s["p_raw_area_per_GW"], s.cf)[0],
                           spearmanr(s["p_mono_gbt_img+wx"], s.cf)[0] - spearmanr(s["p_mono_gbt_img"], s.cf)[0], roc_auc_score(s.on, s["p_clf_onoff_img+wx"]) - roc_auc_score(s.on, s["p_clf_onoff_img"]),
                           roc_auc_score(s.on, s["p_clf_onoff_img+wx"]) - roc_auc_score(s.on, s["p_raw_area_per_GW"])])
        D = np.array(diffs); names = ["rho(weather-normalised) - rho(raw area/GW)", "rho(mono img+wx) - rho(mono img)", "AUC(clf img+wx) - AUC(clf img)", "AUC(clf img+wx) - AUC(raw area/GW)"]
        boot = pd.DataFrame(dict(contrast=names, mean=D.mean(0), lo95=np.percentile(D, 2.5, 0), hi95=np.percentile(D, 97.5, 0), p_gt0=(D > 0).mean(0))); boot.to_csv("s2_weather_gain_bootstrap.csv", index=False); print(boot.round(3).to_string())
# zero-shot AU
tr = us[us.group.isin(["natural_draft", "mech_draft"]) & us.valid]; a = au[au.valid].reset_index(drop=True); cuts = np.quantile(tr.cf, [1/3, 2/3])
P = fit_predict(tr, a); P["raw_area_per_GW"] = a.plume_per_gw.values
for k, v in P.items(): a["p_"+k] = np.asarray(v)
tw = a.group.isin(["natural_draft", "mixed"])
for k in P:
    r = metrics(a[tw].reset_index(drop=True), a[tw]["p_"+k].values, k, cuts); r["subset"] = "AU zero-shot: tower plants"; res.append(r)
    r = metrics(a[~tw].reset_index(drop=True), a[~tw]["p_"+k].values, k, cuts); r["subset"] = "AU zero-shot: no-tower controls"; res.append(r)
per = []
for (nm, g_), g in a.groupby(["plant_name_eia", "group"]):
    row = dict(plant=nm, group=g_, n=len(g), cf_mean=g.cf.mean(), cf_sd=g.cf.std())
    for k in P: row["rho_"+k] = spearmanr(g["p_"+k], g.cf)[0]
    row["rho_units_on(mono)"] = spearmanr(g["p_mono_gbt_img+wx"], g.n_units_on)[0]; row["mae_cf(mono)"] = float(np.abs(g["p_mono_gbt_img+wx"]-g.cf).mean()); row["bias_cf(mono)"] = float((g["p_mono_gbt_img+wx"]-g.cf).mean()); per.append(row)
pd.DataFrame(per).to_csv("s2_au_per_plant_v2.csv", index=False); print(pd.DataFrame(per).round(2).to_string()); a.to_csv("s2_au_zero_shot_predictions_v2.csv", index=False)
# AU: low-vs-high load detection (whole-plant off never happens): bottom-quartile CF vs top-quartile CF per plant
rows = []
for nm, g in a[tw].groupby("plant_name_eia"):
    lo, hi = g[g.cf <= g.cf.quantile(.25)], g[g.cf >= g.cf.quantile(.75)]
    if len(lo) >= 8: rows.append(dict(plant=nm, n_lo=len(lo), n_hi=len(hi), auc_low_vs_high=roc_auc_score(np.r_[np.zeros(len(lo)), np.ones(len(hi))], np.r_[lo["p_mono_gbt_img+wx"], hi["p_mono_gbt_img+wx"]])))
print(pd.DataFrame(rows).round(2).to_string()); pd.DataFrame(rows).to_csv("s2_au_low_vs_high.csv", index=False)
R = pd.DataFrame(res); R.to_csv("s2_model_results_v2.csv", index=False); print(R.round(3).to_string())
