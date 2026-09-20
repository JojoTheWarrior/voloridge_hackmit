"""Smoke test: does a GBM on CAMS + ERA5 + VIIRS + context beat raw CAMS under leave-countries-out / leave-region-out?"""
import numpy as np, pandas as pd, lightgbm as lgb, warnings
from sklearn.model_selection import GroupKFold
from sklearn.linear_model import LinearRegression
warnings.filterwarnings("ignore")
d = pd.read_parquet("dataset_daily.parquet")
d = d[d.cams_pm2_5.notna()]
sd = d.groupby("id").pm25.agg(["std", "mean", "size"])
good = sd[(sd["std"] > 0.5) & sd["mean"].between(1, 400) & (sd["size"] >= 40)].index
d = d[d.id.isin(good)]
num = [c for c in d.columns if c.startswith(("cams_", "era_"))] + ["viirs_aod", "log_pop50"]
m = d.groupby(["id", "month"]).agg(pm25=("pm25", "mean"), n=("pm25", "size"), **{c: (c, "mean") for c in num},
    lat=("lat", "first"), lon=("lon", "first"), cc=("cc", "first"), region=("region", "first"), kind=("kind", "first")).reset_index()
m = m[m.n >= 5]
def feats(x):
    f = pd.DataFrame({"l_cams": np.log1p(x.cams_pm2_5), "l_dust": np.log1p(x.cams_dust), "cams_aod": x.cams_aerosol_optical_depth, "l_no2": np.log1p(x.cams_nitrogen_dioxide),
        "viirs_aod": x.viirs_aod, "log_pop50": x.log_pop50, "abslat": x.lat.abs(), "season": np.cos(2 * np.pi * (x.month - 1) / 12) * np.sign(x.lat)})
    if "era_boundary_layer_height" in x:
        f["blh"] = x.era_boundary_layer_height; f["t2m"] = x.era_temperature_2m; f["precip"] = x.era_precipitation
        f["wind"] = np.hypot(x.era_wind_u_component_10m, x.era_wind_v_component_10m); f["dpd"] = x.era_temperature_2m - x.era_dew_point_2m
    return f
X, y = feats(m), np.log1p(m.pm25)
print(len(m), "station-months;", m.id.nunique(), "stations;", m.cc.nunique(), "countries; features:", list(X.columns))
P = dict(objective="regression", n_estimators=400, learning_rate=0.03, num_leaves=15, min_child_samples=40, subsample=0.8, subsample_freq=1, colsample_bytree=0.8, reg_lambda=5, verbose=-1)
# balance: each country contributes equal total weight (else Europe dominates)
w = 1 / m.groupby("cc").cc.transform("size")
def cv(groups, name, nfold):
    pred = np.full(len(m), np.nan); lin = np.full(len(m), np.nan)
    for tr, te in GroupKFold(nfold).split(X, y, groups):
        pred[te] = lgb.LGBMRegressor(**P).fit(X.iloc[tr], y.iloc[tr], sample_weight=w.iloc[tr]).predict(X.iloc[te])
        lr = LinearRegression().fit(X[["l_cams"]].iloc[tr], y.iloc[tr], sample_weight=w.iloc[tr]); lin[te] = lr.predict(X[["l_cams"]].iloc[te])
    m[f"gbm_{name}"] = np.expm1(pred); m[f"lin_{name}"] = np.expm1(lin)
cv(m.cc, "lco", 10)
cv(m.region, "lro", m.region.nunique())
def met(o, p):
    return {"r": np.corrcoef(o, p)[0, 1], "R2": 1 - ((o - p) ** 2).sum() / ((o - o.mean()) ** 2).sum(), "RMSE": np.sqrt(((o - p) ** 2).mean()), "MAE": (o - p).abs().mean(), "NMB%": 100 * (p - o).sum() / o.sum()}
def table(df, label):
    rows = {}
    for nm, col in [("raw CAMS", "cams_pm2_5"), ("CAMS log-linear rescale (LCO)", "lin_lco"), ("GBM leave-countries-out", "gbm_lco"), ("GBM leave-REGION-out", "gbm_lro")]:
        rows[nm] = met(df.pm25, df[col])
    print(f"\n== {label} (n={len(df)}) ==\n", pd.DataFrame(rows).T.round(2).to_string())
table(m, "station-month, all")
ann = m.groupby("id").agg(pm25=("pm25", "mean"), cams_pm2_5=("cams_pm2_5", "mean"), lin_lco=("lin_lco", "mean"), gbm_lco=("gbm_lco", "mean"), gbm_lro=("gbm_lro", "mean"),
                          region=("region", "first"), cc=("cc", "first"), kind=("kind", "first"), nmo=("month", "size")).query("nmo>=9")
table(ann, "station-annual, all"); table(ann[ann.kind == "reference_likely"], "station-annual, reference-likely only")
print("\n== station-annual by region: RMSE / NMB% (raw CAMS vs GBM-LCO vs GBM-LRO) ==")
rows = []
for r, g in ann.groupby("region"):
    if len(g) < 5: continue
    a, b, c = met(g.pm25, g.cams_pm2_5), met(g.pm25, g.gbm_lco), met(g.pm25, g.gbm_lro)
    rows.append({"region": r, "n": len(g), "n_cc": g.cc.nunique(), "obs": g.pm25.mean(), "RMSE_cams": a["RMSE"], "RMSE_lco": b["RMSE"], "RMSE_lro": c["RMSE"], "NMB_cams": a["NMB%"], "NMB_lco": b["NMB%"], "NMB_lro": c["NMB%"], "r_cams": a["r"], "r_lco": b["r"]})
print(pd.DataFrame(rows).round(2).to_string(index=False))
# country-mean level (what a city ranking really needs)
cm = ann.groupby("cc")[["pm25", "cams_pm2_5", "gbm_lco"]].mean()
print("\ncountry-mean level: raw", {k: round(v, 2) for k, v in met(cm.pm25, cm.cams_pm2_5).items()}, "\n                    gbm", {k: round(v, 2) for k, v in met(cm.pm25, cm.gbm_lco).items()})
m.to_parquet("cv_predictions.parquet"); ann.to_csv("cv_station_annual.csv")
full = lgb.LGBMRegressor(**P).fit(X, y, sample_weight=w)
print("\nfeature importance (gain):", dict(sorted(zip(X.columns, (full.booster_.feature_importance("gain") / full.booster_.feature_importance("gain").sum()).round(3)), key=lambda t: -t[1])))
import joblib; joblib.dump({"model": full, "cols": list(X.columns)}, "model.joblib")
