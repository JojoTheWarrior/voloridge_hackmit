"""Fairness checks: (a) station-grouped random CV (leaky, what many papers report), (b) ratio target, (c) per-country win rate."""
import numpy as np, pandas as pd, lightgbm as lgb, warnings
from sklearn.model_selection import GroupKFold
warnings.filterwarnings("ignore")
exec(open("model.py").read().split("P = dict")[0])
P = dict(objective="regression", n_estimators=400, learning_rate=0.03, num_leaves=15, min_child_samples=40, subsample=0.8, subsample_freq=1, colsample_bytree=0.8, reg_lambda=5, verbose=-1)
w = 1 / m.groupby("cc").cc.transform("size")
def run(groups, target, nfold=10, shuffle_groups=False):
    g = pd.Series(groups).astype(str).values
    if shuffle_groups:
        u = np.unique(g); rng = np.random.default_rng(0); g = pd.Series(g).map(dict(zip(u, rng.permutation(len(u))))).values
    pred = np.full(len(m), np.nan)
    for tr, te in GroupKFold(nfold).split(X, target, g):
        pred[te] = lgb.LGBMRegressor(**P).fit(X.iloc[tr], target.iloc[tr], sample_weight=w.iloc[tr]).predict(X.iloc[te])
    return pred
m["p_station"] = np.expm1(run(m.id, y, shuffle_groups=True))
m["p_lco"] = np.expm1(run(m.cc, y))
ratio = y - X.l_cams
m["p_ratio"] = np.expm1(run(m.cc, ratio) + X.l_cams)
ann = m.groupby("id").agg(o=("pm25", "mean"), cams=("cams_pm2_5", "mean"), p_station=("p_station", "mean"), p_lco=("p_lco", "mean"), p_ratio=("p_ratio", "mean"), cc=("cc", "first"), region=("region", "first"), n=("month", "size")).query("n>=9")
for c in ["cams", "p_station", "p_lco", "p_ratio"]:
    e = ann[c] - ann.o
    print(f"{c:10s} r={np.corrcoef(ann.o, ann[c])[0,1]:.2f} R2={1-(e**2).sum()/((ann.o-ann.o.mean())**2).sum():.2f} RMSE={np.sqrt((e**2).mean()):.2f} MAE={e.abs().mean():.2f}")
pc = ann.groupby("cc").apply(lambda g: pd.Series({"n": len(g), "mae_cams": (g.cams - g.o).abs().mean(), "mae_gbm": (g.p_lco - g.o).abs().mean(), "region": g.region.iloc[0]}))
pc["win"] = pc.mae_gbm < pc.mae_cams
print("\ncountries where GBM-LCO beats raw CAMS on station-annual MAE:", int(pc.win.sum()), "of", len(pc))
print(pc.groupby("region").agg(countries=("win", "size"), gbm_wins=("win", "sum"), mae_cams=("mae_cams", "mean"), mae_gbm=("mae_gbm", "mean")).round(2).to_string())
rng = np.random.default_rng(1); ccs = pc.index.values; diffs = []
for _ in range(2000):
    s = rng.choice(ccs, len(ccs)); diffs.append((pc.loc[s, "mae_cams"] - pc.loc[s, "mae_gbm"]).mean())
print("country-bootstrap mean MAE improvement (cams - gbm): %.2f [%.2f, %.2f] ug/m3" % (np.mean(diffs), *np.percentile(diffs, [2.5, 97.5])))
