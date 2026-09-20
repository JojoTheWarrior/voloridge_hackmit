"""Seasonality control: does the 30-day index track THIS year's NOx better than the same calendar dates one year earlier/later?"""
import numpy as np, pandas as pd
o = pd.read_csv("no2_index_30d_us.csv", parse_dates=["day"]); rows = []
for p, g in o.groupby("plant"):
    g = g.set_index("day").sort_index(); s = g[(g.index - g.index.min()).days % 30 == 0]
    lag = g.nox_all_rel.copy(); lag.index = lag.index + pd.Timedelta(days=364); x = s.join(lag.rename("nox_lag1y"), how="inner").dropna(subset=["flux_rel_corr", "nox_all_rel", "nox_lag1y"])
    if len(x) >= 10: rows.append(dict(plant=p, n=len(x), r_actual=np.corrcoef(x.flux_rel_corr, x.nox_all_rel)[0, 1], r_lag1y=np.corrcoef(x.flux_rel_corr, x.nox_lag1y)[0, 1], r_nox_autocorr_1y=np.corrcoef(x.nox_all_rel, x.nox_lag1y)[0, 1]))
R = pd.DataFrame(rows); R.to_csv("no2_placebo_lag1y.csv", index=False)
print(R[["r_actual", "r_lag1y", "r_nox_autocorr_1y"]].describe().loc[["count", "25%", "50%", "75%"]].round(2)); print("plants where actual > lagged:", int((R.r_actual > R.r_lag1y).sum()), "of", len(R))
