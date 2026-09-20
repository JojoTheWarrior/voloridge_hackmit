import pandas as pd, numpy as np, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
a = pd.read_csv("cv_station_annual.csv"); a = a[a.region != "?"]; regs = sorted(a.region.unique()); cm = plt.get_cmap("tab20")
fig, ax = plt.subplots(1, 2, figsize=(13, 6), sharex=True, sharey=True)
for k, (c, t) in enumerate([("cams_pm2_5", "Raw CAMS (0.4°)"), ("gbm_lco", "GBM, leave-countries-out")]):
    for i, r in enumerate(regs):
        g = a[a.region == r]; ax[k].scatter(g.pm25, g[c], s=8, alpha=.7, color=cm(2 * i % 20), label=f"{r} (n={len(g)})")
    ax[k].plot([1, 200], [1, 200], "k-", lw=.8); ax[k].set_xscale("log"); ax[k].set_yscale("log"); ax[k].set_xlim(2, 200); ax[k].set_ylim(2, 200)
    e = a[c] - a.pm25; ax[k].set_title(f"{t}: r={np.corrcoef(a.pm25, a[c])[0,1]:.2f}, RMSE={np.sqrt((e**2).mean()):.1f}, NMB={100*e.sum()/a.pm25.sum():.0f}%"); ax[k].set_xlabel("OpenAQ observed 2025 mean PM2.5 (µg/m³)")
ax[0].set_ylabel("predicted"); ax[0].legend(fontsize=7, loc="upper left"); plt.tight_layout(); plt.savefig("fig_cams_vs_openaq.png", dpi=130)
c = pd.read_csv("city_predictions.csv"); st = pd.read_csv("pm25_locations.csv"); st = st[st.kind == "reference_likely"]
fig, ax = plt.subplots(figsize=(14, 7)); ax.scatter(st.lon, st.lat, s=1, color="#bbbbbb", label="OpenAQ reference-likely PM2.5 monitors active 2024-25")
u = c[c.n_ref_25 == 0]; s = ax.scatter(u.lon, u.lat, s=u["pop"] / 1e5, c=u.pred, cmap="inferno_r", vmin=5, vmax=60, edgecolor="k", lw=.3, label="cities ≥500k with none within 25 km")
plt.colorbar(s, label="predicted 2025 PM2.5 (µg/m³)", shrink=.7); ax.set_xlim(-130, 160); ax.set_ylim(-45, 65); ax.legend(loc="lower left")
ax.set_title("Monitor deserts: 718 cities ≥500k lack a reference-likely PM2.5 feed in OpenAQ (294 are in China, which measures but isn't in OpenAQ)")
plt.tight_layout(); plt.savefig("fig_monitor_deserts.png", dpi=130)
