import numpy as np, pandas as pd, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from sklearn.metrics import roc_curve
o = pd.read_csv("no2_index_30d_us.csv", parse_dates=["day"]); o["plant"] = o.plant.astype(str); r = pd.read_csv("no2_per_plant_daily_r.csv"); cal = pd.read_csv("no2_calibration_by_index.csv"); pl = pd.read_csv("plants_no2_us.csv"); pl["plant"] = pl.plant_id_eia.astype(str)
fig, ax = plt.subplots(1, 4, figsize=(22, 4.8))
ax[0].hist(r.r_daily_flux, bins=20, color="#9aa5b1"); ax[0].axvline(r.r_daily_flux.median(), c="k", ls="--"); ax[0].set_title(f"Daily: per-plant r(TROPOMI, CEMS NOx), median {r.r_daily_flux.median():.2f} (58 plants)"); ax[0].set_xlabel("Pearson r")
s = o[(o.day - o.day.min()).dt.days % 30 == 0]; ax[1].scatter(s.flux_rel_corr, s.nox_all_rel, s=6, alpha=.35); ax[1].plot(s.flux_rel_corr.sort_values(), s.pred_rel[s.flux_rel_corr.sort_values().index], "k-", lw=.8)
ax[1].set_xlim(-0.5, 3); ax[1].set_ylim(0, 2.5); ax[1].set_xlabel("30-day NO2 index / plant mean (held-out plants)"); ax[1].set_ylabel("30-day CEMS NOx / plant mean"); ax[1].set_title(f"30-day index, leave-plants-out: r={np.corrcoef(s.flux_rel_corr, s.nox_all_rel)[0,1]:.2f}, n={len(s)}")
w = o[(o.day - o.day.min()).dt.days % 10 == 0]; a, b = w[w.nox_all_rel < 0.3], w[w.nox_all_rel > 0.7]; fpr, tpr, _ = roc_curve(np.r_[np.ones(len(a)), np.zeros(len(b))], -np.r_[a.flux_rel_corr, b.flux_rel_corr])
ax[2].plot(fpr, tpr); ax[2].plot([0, 1], [0, 1], "k:", lw=.6); ax[2].axvline(0.05, c="r", lw=.6); ax[2].set_title(f"Detecting a real 30-day outage (NOx<30% of normal)\n{len(a)} outage windows at {a.plant.nunique()} plants"); ax[2].set_xlabel("false-alarm rate"); ax[2].set_ylabel("detection rate")
best = o.groupby("plant").apply(lambda g: np.corrcoef(g.flux_rel_corr, g.nox_all_rel)[0, 1]).sort_values(); p = best.index[len(best)//2]; g = o[o.plant == p]   # MEDIAN plant, not the best one
ax[3].plot(g.day, g.nox_all_rel, label="CEMS NOx (30-d mean / plant mean)", c="k"); ax[3].plot(g.day, g.flux_rel_corr, label="TROPOMI index", c="#1f6feb"); ax[3].fill_between(g.day, g.lo, g.hi, alpha=.15, color="#1f6feb", label="80% calibrated band")
ax[3].set_title(f"Median-skill plant: {pl.set_index('plant').plant_name_eia[p]} (r={best[p]:.2f})"); ax[3].legend(fontsize=7)
plt.tight_layout(); plt.savefig("figs/no2_us_calibration.png", dpi=80)
