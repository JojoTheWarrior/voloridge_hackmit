import numpy as np, pandas as pd, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
us = pd.read_csv("s2_us_cv_predictions_v2.csv"); au = pd.read_csv("s2_au_zero_shot_predictions_v2.csv"); c = pd.read_csv("s2_us_condition_splits_v2.csv"); per = pd.read_csv("s2_au_per_plant_v2.csv")
fig, ax = plt.subplots(1, 4, figsize=(21, 4.8)); M = "p_mono_gbt_img+wx"
t = c[c.split == "Tbin"].copy(); t["lo"] = t.bin.str.extract(r"\(([-\d.]+),").astype(float); t = t.sort_values("lo"); x = np.arange(len(t))
ax[0].bar(x-0.2, t.auc_raw_area_per_GW, 0.4, label="raw plume area / GW", color="#9aa5b1"); ax[0].bar(x+0.2, t["auc_mono_gbt_img+wx"], 0.4, label="image+weather model", color="#1f6feb")
ax[0].set_xticks(x); ax[0].set_xticklabels([f"{b} C\nn={n} ({o} off)" for b, n, o in zip(t.bin, t.n, t.n_off)], fontsize=8); ax[0].set_ylim(0.5, 1); ax[0].set_ylabel("on/off AUC (held-out plants)"); ax[0].legend(fontsize=8); ax[0].set_title("US: plume visibility is temperature-limited")
us["bin"] = pd.cut(us.cf, [-0.01, 0.05, 0.35, 0.65, 1.2], labels=["off", "low", "mid", "high"]); ax[1].boxplot([us[us.bin == b][M] for b in ["off", "low", "mid", "high"]], tick_labels=[f"{b}\nn={int((us.bin == b).sum())}" for b in ["off", "low", "mid", "high"]], showfliers=False)
ax[1].set_ylabel("predicted capacity factor (plant never seen in training)"); ax[1].set_xlabel("CEMS capacity factor at overpass"); ax[1].set_title("US leave-plants-out: 41 plants, %d scenes" % len(us))
per = per.sort_values("rho_mono_gbt_img+wx"); col = ["#d1242f" if "control" in g else "#1f6feb" for g in per.group]; ax[2].barh(per.plant, per["rho_mono_gbt_img+wx"], color=col); ax[2].axvline(0, c="k", lw=.5)
ax[2].set_xlabel("Spearman(model, AEMO capacity factor)"); ax[2].set_title("AUSTRALIA zero-shot (blue = cooling towers, red = no-tower controls)")
tw = au[au.group.isin(["natural_draft", "mixed"])]; ax[3].scatter(tw.cf, tw[M], s=8, alpha=.5); ax[3].plot([0, 1], [0, 1], "k--", lw=.6); ax[3].set_xlabel("AEMO capacity factor"); ax[3].set_ylabel("US-trained model prediction"); ax[3].set_title("AU zero-shot: rank transfers, level is biased low")
plt.tight_layout(); plt.savefig("figs/s2_summary.png", dpi=80)
