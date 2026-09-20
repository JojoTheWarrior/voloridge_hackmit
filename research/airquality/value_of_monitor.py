"""How much does the k-th monitor in a country help? Calibrate CAMS with a single country-level ratio from k random stations; test on the rest."""
import numpy as np, pandas as pd
a = pd.read_csv("cv_station_annual.csv"); rng = np.random.default_rng(0); rows = []
for cc, g in a.groupby("cc"):
    if len(g) < 6: continue
    for k in (0, 1, 2, 3, 5):
        errs = []
        for _ in range(200):
            idx = rng.permutation(len(g)); cal, test = g.iloc[idx[:k]], g.iloc[idx[5:]]  # test set fixed size-independent of k
            ratio = 1.0 if k == 0 else np.exp(np.mean(np.log(cal.pm25 / cal.cams_pm2_5)))
            errs.append((test.cams_pm2_5 * ratio - test.pm25).abs().mean())
        rows.append({"cc": cc, "region": g.region.iloc[0], "k": k, "mae": np.mean(errs), "gbm_lco_mae": (g.gbm_lco - g.pm25).abs().mean()})
r = pd.DataFrame(rows); p = r.pivot(index="cc", columns="k", values="mae")
print("countries:", len(p)); print("mean station-annual MAE by k calibration monitors:\n", p.mean().round(2).to_string())
print("GBM leave-country-out MAE, same countries: %.2f" % r.drop_duplicates("cc").gbm_lco_mae.mean())
poor = r[r.region.isin(["Sub-Saharan Africa", "South Asia", "MENA", "Central Asia", "South America", "Other Asia"])]
print("\nnon-Western subset (%d countries):\n" % poor.cc.nunique(), poor.pivot(index="cc", columns="k", values="mae").mean().round(2).to_string(), "\nGBM-LCO: %.2f" % poor.drop_duplicates("cc").gbm_lco_mae.mean())
