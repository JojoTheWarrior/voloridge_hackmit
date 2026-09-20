"""Join plume features with labels (US CEMS hourly, AU AEMO 5-min) + ERA5 weather; leave-whole-plants-out CV on US; zero-shot on Australia."""
import numpy as np, pandas as pd, json, sys
from sklearn.ensemble import HistGradientBoostingRegressor, HistGradientBoostingClassifier
from sklearn.model_selection import GroupKFold
from sklearn.metrics import roc_auc_score, average_precision_score
from scipy.stats import spearmanr
rng = np.random.default_rng(0)
IMG = ["plume_km2", "plume_tower_km2", "plume_stack_km2", "plume_extent_m", "plume_mean_anom", "src_anom", "src_bright_frac", "src_anom_max", "shadow_score", "shadow_dist_m",
       "plume_border", "bright_away", "scl_cloud_away", "dark_away", "n_towers", "n_stacks", "log_cap", "plume_per_gw"]
WX = ["temperature_2m", "relative_humidity_2m", "dewdep", "wind_speed_10m", "sza"]

def load(feat_csv, country):
    f = pd.read_csv(feat_csv); f["plant"] = f.plant.astype(str); f["t"] = pd.to_datetime(f.t, format="ISO8601").dt.tz_localize(None)
    wx = pd.read_parquet("weather_s2.parquet"); wx["plant"] = wx.plant.astype(str)
    f["hour"] = f.t.dt.floor("h"); f = f.merge(wx.rename(columns={"time": "hour"}), on=["plant", "hour"], how="left"); f["dewdep"] = f.temperature_2m - f.dew_point_2m
    if country == "us":
        c = pd.read_parquet("cems_s2_us.parquet"); c["plant"] = c.plant_id_eia.astype(str)
        cap = c.groupby("plant").gross_mw.quantile(0.995).rename("cap")
        f = f.merge(c[["plant", "t", "gross_mw", "n_units_on", "n_units"]].rename(columns={"t": "hour"}), on=["plant", "hour"], how="left").merge(cap, on="plant")
        f["mw"] = f.gross_mw
        meta = pd.read_csv("plants_s2_us.csv"); meta["plant"] = meta.plant_id_eia.astype(str); f = f.merge(meta[["plant", "plant_name_eia", "group"]], on="plant")
    else:
        s = pd.read_parquet("aemo/scada.parquet"); meta = pd.read_csv("plants_au.csv"); name2id = dict(zip(meta.plant_name_eia, meta.plant_id_eia))
        s["plant"] = s.plant.map(name2id); s = s.dropna(subset=["plant"]); s["t_utc"] = s.t_aest - pd.Timedelta(hours=10)
        s["on"] = s.SCADAVALUE > 20
        tot = s.groupby(["plant", "t_utc"]).agg(mw=("SCADAVALUE", "sum"), n_units_on=("on", "sum")).reset_index().sort_values("t_utc")
        cap = tot.groupby("plant").mw.quantile(0.995).rename("cap")
        tot["mw"] = tot.groupby("plant").mw.transform(lambda x: x.rolling(5, min_periods=1).mean())       # mean of the 25 min up to t
        f = pd.merge_asof(f.sort_values("t"), tot.rename(columns={"t_utc": "t"}), on="t", by="plant", direction="backward", tolerance=pd.Timedelta(minutes=10)).merge(cap, on="plant")
        f = f.merge(meta.rename(columns={"plant_id_eia": "plant", "cooling": "group"})[["plant", "plant_name_eia", "group"]], on="plant")
    f = f.dropna(subset=["mw", "temperature_2m"]); f["cf"] = (f.mw/f.cap).clip(0, 1.1); f["on"] = (f.cf > 0.05).astype(int)
    f["log_cap"] = np.log(f.cap); f["plume_per_gw"] = f.plume_km2/(f.cap/1000); f["plume_border"] = f.plume_border.astype(int); f["country"] = country
    f["valid"] = (f.scl_cloud_away < 0.10) & (f.bright_away < 0.03) & (f.snow_frac < 0.2) & ~((f.plume_border == 1) & (f.plume_km2 > 0.8))   # last term: cloud sitting on the source
    return f

def metrics(df, pred, tag, cuts):
    o = dict(model=tag, n=len(df), n_off=int((df.on == 0).sum()))
    if df.on.nunique() == 2: o["auc_onoff"] = roc_auc_score(df.on, pred); o["ap_off"] = average_precision_score(1-df.on, -pred)
    o["spearman_cf"] = spearmanr(pred, df.cf)[0]
    on = df.on == 1; o["spearman_cf_on_only"] = spearmanr(pred[on], df.cf[on])[0]
    wp = [spearmanr(pred[df.plant == p], df.cf[df.plant == p])[0] for p in df.plant.unique() if (df.plant == p).sum() >= 15 and df.cf[df.plant == p].std() > 0.05]
    o["within_plant_spearman_median"] = float(np.nanmedian(wp)) if wp else np.nan; o["n_plants"] = df.plant.nunique()
    yt = np.digitize(df.cf, cuts); yp = np.digitize(pred, np.quantile(pred, [(yt == 0).mean(), (yt <= 1).mean()]))   # rank-matched terciles (no label leakage beyond class priors)
    o["tercile_acc"] = float((yt == yp).mean()); o["tercile_majority_baseline"] = float(np.bincount(yt).max()/len(yt))
    return o

def cv_predict(df, feats, groups):
    pred = np.zeros(len(df))
    for tr, te in GroupKFold(n_splits=min(6, groups.nunique())).split(df, groups=groups):
        m = HistGradientBoostingRegressor(max_depth=4, max_iter=250, learning_rate=0.05, min_samples_leaf=25, random_state=0).fit(df.iloc[tr][feats], df.iloc[tr].cf)
        pred[te] = m.predict(df.iloc[te][feats])
    return pred

if __name__ == "__main__":
    us = load("s2_features_us.csv", "us"); au = load("s2_features_au.csv", "au")
    print("US scenes", len(us), "valid", int(us.valid.sum()), "| AU scenes", len(au), "valid", int(au.valid.sum()))
    pd.concat([us, au]).to_csv("s2_scenes_labeled.csv", index=False)
    res = []
    for grp, sel in [("US towers+FGD (natural+mech draft)", us.group.isin(["natural_draft", "mech_draft"])), ("US natural-draft only", us.group == "natural_draft"),
                     ("US mech-draft only", us.group == "mech_draft"), ("US once-through controls", us.group == "once_through_control")]:
        d = us[sel & us.valid].reset_index(drop=True); cuts = np.quantile(us[us.group.isin(["natural_draft", "mech_draft"]) & us.valid].cf, [1/3, 2/3])
        preds = {"raw_plume_area": d.plume_km2.values, "raw_area_per_GW": d.plume_per_gw.values, "weather_only(control)": cv_predict(d, WX + ["log_cap"], d.plant),
                 "image_only_GBT": cv_predict(d, IMG, d.plant), "image+weather_GBT": cv_predict(d, IMG + WX, d.plant)}
        for k, v in preds.items():
            r = metrics(d, v, k, cuts); r["subset"] = grp; res.append(r)
        if grp.startswith("US towers"):
            d["pred"] = preds["image+weather_GBT"]; d["pred_img"] = preds["image_only_GBT"]; d.to_csv("s2_us_cv_predictions.csv", index=False); uscv = d
    # condition splits on the main subset
    d = uscv; d["season"] = np.where(d.t.dt.month.isin([11, 12, 1, 2, 3]), "Nov-Mar", "Apr-Oct")
    d["Tbin"] = pd.cut(d.temperature_2m, [-40, 5, 15, 25, 50]); d["RHbin"] = pd.cut(d.relative_humidity_2m, [0, 40, 60, 80, 101])
    cond = []
    for col in ["season", "Tbin", "RHbin"]:
        for k, g in d.groupby(col, observed=True):
            if g.on.nunique() < 2 or len(g) < 40: continue
            cond.append(dict(split=col, bin=str(k), n=len(g), n_off=int((g.on == 0).sum()), auc_raw=roc_auc_score(g.on, g.plume_km2), auc_model=roc_auc_score(g.on, g.pred),
                             spearman_raw=spearmanr(g.plume_km2, g.cf)[0], spearman_img=spearmanr(g.pred_img, g.cf)[0], spearman_model=spearmanr(g.pred, g.cf)[0]))
    pd.DataFrame(cond).to_csv("s2_us_condition_splits.csv", index=False); print(pd.DataFrame(cond).round(3).to_string())
    # plant-bootstrap CI for headline numbers
    def boot(d, col):
        pl = d.plant.unique(); out = []
        for _ in range(500):
            s = pd.concat([d[d.plant == p] for p in rng.choice(pl, len(pl))]); 
            out.append((roc_auc_score(s.on, s[col]) if s.on.nunique() == 2 else np.nan, spearmanr(s[col], s.cf)[0]))
        return np.nanpercentile(np.array(out), [2.5, 97.5], axis=0)
    ci = {c: boot(uscv, c).round(3).tolist() for c in ["plume_km2", "pred_img", "pred"]}; print("plant-bootstrap 95% CI [AUC, Spearman] lo/hi:", ci)
    # zero-shot Australia
    tr = us[us.group.isin(["natural_draft", "mech_draft"]) & us.valid]; cuts = np.quantile(tr.cf, [1/3, 2/3])
    m_full = HistGradientBoostingRegressor(max_depth=4, max_iter=250, learning_rate=0.05, min_samples_leaf=25, random_state=0).fit(tr[IMG + WX], tr.cf)
    m_img = HistGradientBoostingRegressor(max_depth=4, max_iter=250, learning_rate=0.05, min_samples_leaf=25, random_state=0).fit(tr[IMG], tr.cf)
    a = au[au.valid].reset_index(drop=True); a["pred"] = m_full.predict(a[IMG + WX]); a["pred_img"] = m_img.predict(a[IMG]); a.to_csv("s2_au_zero_shot_predictions.csv", index=False)
    for grp, sel in [("AU zero-shot: tower plants", a.group.isin(["natural_draft", "mixed"])), ("AU zero-shot: no-tower controls", ~a.group.isin(["natural_draft", "mixed"]))]:
        for k, col in [("raw_plume_area", "plume_km2"), ("image_only_GBT", "pred_img"), ("image+weather_GBT", "pred")]:
            r = metrics(a[sel].reset_index(drop=True), a[sel][col].values, k, cuts); r["subset"] = grp; res.append(r)
    per = []
    for (p, nm, g_), g in a.groupby(["plant", "plant_name_eia", "group"]):
        per.append(dict(plant=nm, group=g_, n=len(g), cf_mean=g.cf.mean(), cf_sd=g.cf.std(), spearman_raw=spearmanr(g.plume_km2, g.cf)[0], spearman_model=spearmanr(g.pred, g.cf)[0],
                        spearman_units_on=spearmanr(g.pred, g.n_units_on)[0], mae_cf=float(np.abs(g.pred-g.cf).mean()), bias_cf=float((g.pred-g.cf).mean())))
    pd.DataFrame(per).to_csv("s2_au_per_plant.csv", index=False); print(pd.DataFrame(per).round(3).to_string())
    R = pd.DataFrame(res); R.to_csv("s2_model_results.csv", index=False); pd.set_option("display.width", 250); print(R.round(3).to_string())
    json.dump(ci, open("s2_us_bootstrap_ci.json", "w"))
