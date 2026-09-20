"""Winter stack/tower plume index for Iranian & Iraqi plants (no labels): what moved in the 2026 war window vs the same calendar window in 2025?"""
import numpy as np, pandas as pd, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from scipy.stats import mannwhitneyu
f = pd.read_csv("s2_features_ir.csv"); f["t"] = pd.to_datetime(f.t, format="ISO8601").dt.tz_localize(None); f["hour"] = f.t.dt.floor("h")
wx = pd.read_parquet("wind_foreign2.parquet").rename(columns={"time": "hour"}); f = f.merge(wx, on=["plant", "hour"], how="left")
f["valid"] = (f.scl_cloud_away < 0.10) & (f.bright_away < 0.03) & (f.snow_frac < 0.2) & ~((f.plume_border) & (f.plume_km2 > 0.8))
v = f[f.valid].copy(); v["has_plume"] = v.plume_km2 > 0.01; v["month"] = v.t.dt.to_period("M")
WAR = ("2026-02-28", "2026-04-08"); REF = ("2025-02-28", "2025-04-08")
rows = []
for p, g in v.groupby("plant"):
    w = g[(g.t >= WAR[0]) & (g.t <= WAR[1])]; r = g[(g.t >= REF[0]) & (g.t <= REF[1])]; pre = g[(g.t >= "2026-01-15") & (g.t < WAR[0])]; post = g[(g.t > WAR[1]) & (g.t <= "2026-05-20")]
    cold = g[g.temperature_2m < 12]
    o = dict(plant=p, n_valid=len(g), plume_rate_all=g.has_plume.mean(), plume_rate_cold_lt12C=cold.has_plume.mean() if len(cold) > 5 else np.nan, median_area_cold=cold.plume_km2.median() if len(cold) > 5 else np.nan,
             n_war=len(w), n_ref2025=len(r), rate_war=w.has_plume.mean() if len(w) else np.nan, rate_ref2025=r.has_plume.mean() if len(r) else np.nan, area_war=w.plume_km2.mean() if len(w) else np.nan, area_ref2025=r.plume_km2.mean() if len(r) else np.nan,
             T_war=w.temperature_2m.mean() if len(w) else np.nan, T_ref2025=r.temperature_2m.mean() if len(r) else np.nan, rate_pre6wk=pre.has_plume.mean() if len(pre) else np.nan, n_pre=len(pre), rate_post6wk=post.has_plume.mean() if len(post) else np.nan, n_post=len(post))
    o["p_mannwhitney_area_war_vs_2025"] = mannwhitneyu(w.plume_km2, r.plume_km2).pvalue if len(w) >= 4 and len(r) >= 4 else np.nan
    rows.append(o)
R = pd.DataFrame(rows); R.to_csv("s2_iran_plume_index.csv", index=False); pd.set_option("display.width", 300); print(R.round(3).to_string())
m = v.groupby(["plant", "month"]).agg(n=("has_plume", "size"), rate=("has_plume", "mean"), area=("plume_km2", "mean"), T=("temperature_2m", "mean")).reset_index(); m.to_csv("s2_iran_plume_monthly.csv", index=False)
show = R.sort_values("plume_rate_cold_lt12C", ascending=False).plant.head(8).tolist()
fig, ax = plt.subplots(4, 2, figsize=(15, 11), sharex=True)
for a, p in zip(ax.ravel(), show):
    g = v[v.plant == p]; a.scatter(g.t, g.plume_km2, c=g.temperature_2m, cmap="coolwarm", s=16, vmin=-5, vmax=35); a.set_yscale("symlog", linthresh=0.02); a.set_ylim(0, 3)
    a.axvspan(pd.Timestamp(WAR[0]), pd.Timestamp(WAR[1]), color="red", alpha=.15); a.axvspan(pd.Timestamp("2025-06-13"), pd.Timestamp("2025-06-24"), color="orange", alpha=.25); a.set_title(f"{p}  (valid scenes {len(g)})", fontsize=10); a.set_ylabel("plume km2")
fig.suptitle("Sentinel-2 plume area attached to stacks/towers, colour = ERA5 2 m temperature; red band = 2026 war to ceasefire, orange = June 2025 12-day war"); plt.tight_layout(); plt.savefig("figs/iran_s2_plume_index.png", dpi=75)
