"""Figures for the 5 most informative relationships (hits and nulls). One y-axis per panel; stacked panels share time."""
import json, numpy as np, pandas as pd, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from pathlib import Path
H = Path(__file__).parent; D = H / "data"; F = H / "figures"; PRE = json.load(open(H / "prereg.json"))
BLUE, ORANGE, AQUA, RED, INK, MUTED, GRID, SURF = "#2a78d6", "#eb6834", "#1baf7a", "#e34948", "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
plt.rcParams.update({"figure.facecolor": SURF, "axes.facecolor": SURF, "savefig.facecolor": SURF, "axes.edgecolor": GRID, "axes.labelcolor": MUTED, "xtick.color": MUTED, "ytick.color": MUTED, "text.color": INK,
                     "axes.grid": True, "grid.color": GRID, "grid.linewidth": .6, "axes.spines.top": False, "axes.spines.right": False, "font.size": 9, "axes.titlesize": 10, "axes.titleweight": "bold", "axes.titlelocation": "left", "lines.linewidth": 1.6})
SM, TM = pd.read_parquet(D / "signals_monthly.parquet"), pd.read_parquet(D / "targets_monthly.parquet"); R = pd.read_csv(H / "results.csv"); P = pd.read_parquet(D / "yf_daily.parquet")
def events(ax, ev, label=False):
    for d, n in ev.items():
        ax.axvline(pd.Timestamp(d if len(d) > 7 else d + "-15"), color=RED, lw=.9, ls=(0, (4, 3)), zorder=0)
def note(fig, s): fig.text(0.01, 0.005, s, fontsize=7.5, color=MUTED, ha="left", va="bottom", wrap=True)

# 1 Yunnan case study
z = pd.read_parquet(D / "z_yunnan_area.parquet"); fig, ax = plt.subplots(3, 1, figsize=(10, 8), sharex=True, height_ratios=[1.1, 1, 1])
ax[0].plot(z.index, z.Xiaowan, color=BLUE, label="Xiaowan", marker="o", ms=2.5); ax[0].plot(z.index, z.Nuozhadu, color=ORANGE, label="Nuozhadu", marker="o", ms=2.5); ax[0].axhline(0, color=MUTED, lw=.7)
ax[0].set_title("Lancang (Yunnan) reservoir surface-area anomaly from orbit, z-score vs expanding month-of-year mean"); ax[0].legend(frameon=False, ncol=2, loc="lower left"); ax[0].set_ylabel("z")
al = P["SHFE_AL"].dropna()["2018-06":]; ax[1].plot(al.index, al / 1000, color=INK, lw=1.2); ax[1].set_title("SHFE aluminium, main contract (CNY '000/t)"); ax[1].set_ylabel("CNY k/t")
r = R[R.id == "Y1_z"].iloc[0]; d = pd.concat([SM["yunnan_area|z"], TM["SHFE_AL"].shift(-(1 + int(r.best_lag)))], axis=1).dropna(); d.columns = ["z", "ret"]
ax[2].bar(d.index, d.ret * 100, width=20, color=np.where(d.z < -0.5, ORANGE, "#b9b8b2")); ax[2].set_title(f"SHFE monthly return at the best tradeable lag (orange = known z < -0.5)   r={r.r:+.2f}, n={int(r.n)}, max-stat p={r.maxstat_p:.2f}"); ax[2].set_ylabel("% per month")
for a in ax: events(a, PRE["case_study_events"]["yunnan_curtailments"]); a.set_xlim(pd.Timestamp("2018-10-01"), pd.Timestamp("2026-09-01"))
note(fig, "Red dashes: smelter curtailment announcements (2021-05, 2021-09, 2022-09, 2023-02, 2023-11). At 3 of 5 the satellite anomaly knowable at the time was POSITIVE. Gaps = monsoon cloud. Null result: 0/10 Yunnan tests significant.")
fig.tight_layout(rect=(0, .03, 1, 1)); fig.savefig(F / "fig1_yunnan_aluminium_case_study.png", dpi=130); plt.close(fig)

# 2 Brazil: the link that IS there (satellite -> official storage -> marginal cost), and the one that is not (-> equities)
ear = pd.read_parquet(D / "ear_seco_monthly.parquet").ear_seco_pct; cmo = pd.read_parquet(D / "cmo_se_monthly.parquet").cmo_se
fig, ax = plt.subplots(3, 1, figsize=(10, 8.5), sharex=True)
ax[0].plot(SM.index, SM["brazil_seco_area|z"], color=BLUE, label="satellite area, 9 SE/CO reservoirs (GWW)"); ax[0].plot(SM.index, SM["brazil_ear_seco|z"], color=ORANGE, label="official stored energy (ONS EAR)"); ax[0].axhline(0, color=MUTED, lw=.7)
ax[0].legend(frameon=False, ncol=2, loc="upper left"); ax[0].set_ylabel("z"); ax[0].set_title(f"Brazil SE/CO storage anomaly: orbit vs operator   3-month changes r={R[R.id=='P1'].r.iloc[0]:+.2f} (test-period r={R[R.id=='P1'].r_test.iloc[0]:+.2f})")
ax[1].plot(cmo.index, cmo, color=INK, lw=1.2); ax[1].set_yscale("symlog", linthresh=10); ax[1].set_ylabel("R$/MWh (log)"); ax[1].set_title(f"Marginal operating cost SE/CO (PLD basis): satellite d3 vs d3 log CMO r={R[R.id=='P2'].r.iloc[0]:+.2f}; official EAR r={R[R.id=='P4'].r.iloc[0]:+.2f}")
ax_ = P["AXIA3.SA"].dropna(); bv = P["^BVSP"].dropna(); rel = np.log(ax_ / bv.reindex(ax_.index).ffill()); rel = rel["2006":] - rel["2006":].iloc[0]
ax[2].plot(rel.index, rel, color=AQUA); ax[2].set_ylabel("log relative"); ax[2].set_title(f"Eletrobras/Axia vs Bovespa: satellite z -> later excess return r={R[R.id=='B1_z'].r.iloc[0]:+.2f}, max-stat p={R[R.id=='B1_z'].maxstat_p.iloc[0]:.2f}; official EAR p={R[R.id=='G1_z'].maxstat_p.iloc[0]:.2f}")
for a in ax: a.set_xlim(pd.Timestamp("2006-01-01"), pd.Timestamp("2026-09-01")); [a.axvspan(pd.Timestamp(s), pd.Timestamp(e), color="#f1e3d8", zorder=0, lw=0) for s, e in [("2014-01-01", "2015-12-31"), ("2021-04-01", "2021-12-31")]]
note(fig, "Shaded: 2014-15 and 2021 hydrological crises. The physical->administrative-price link survives BH (q=0.001) and out-of-sample; the equity leg does not, even with the operator's own data as the signal.")
fig.tight_layout(rect=(0, .03, 1, 1)); fig.savefig(F / "fig2_brazil_storage_cmo_equity.png", dpi=130); plt.close(fig)

# 3 Libya flares: orbit sees the blockade, Brent does not follow
fw = pd.read_parquet(D / "flare_weekly_clear.parquet"); fig, ax = plt.subplots(2, 1, figsize=(10, 6.2), sharex=True)
ax[0].plot(fw.index, fw.libya.rolling(4, min_periods=2).mean(), color=BLUE, label="Libya"); ax[0].plot(fw.index, fw.algeria.rolling(4, min_periods=2).mean(), color="#b9b8b2", label="Algeria (placebo)", lw=1.1)
ax[0].legend(frameon=False, ncol=2, loc="upper left"); ax[0].set_ylabel("MW"); ax[0].set_title("Night-time gas-flare radiative power, clear-sky weekly index, 4-week mean (VIIRS S-NPP via NASA GIBS, keyless)")
bz = P["BZ=F"].dropna()["2012":]; ax[1].plot(bz.index, bz, color=INK, lw=1.1); ax[1].set_ylabel("USD/bbl"); r = R[R.id == "F1"].iloc[0]
ax[1].set_title(f"Brent front month   2-week flare change -> next 1-4 week Brent return: r={r.r:+.3f}, n={int(r.n)}, max-stat p={r.maxstat_p:.2f}")
for a in ax: events(a, PRE["case_study_events"]["libya"])
note(fig, "Red dashes: 2013-07 blockades, 2020-01-18 LNA blockade (flares -53%), 2022-04-17 Sharara shut, 2024-08-26 shut-in. Orbit measures the outage's size and duration; the price reacts to the news, not to the later satellite confirmation.")
fig.tight_layout(rect=(0, .04, 1, 1)); fig.savefig(F / "fig3_libya_flares_brent.png", dpi=130); plt.close(fig)

# 4 the whole family at a glance: observed |r| vs the |r| needed, plus p-value QQ for family and placebos
pw = pd.read_csv(H / "power.csv"); M = R.merge(pw, on="id"); M = M.iloc[::-1].reset_index(drop=True); PL = pd.read_csv(H / "placebo_results.csv")
fig, ax = plt.subplots(1, 2, figsize=(12, 9), width_ratios=[1.5, 1]); y = np.arange(len(M))
ax[0].barh(y, M.crit_r_p05, color="#e4e3df", height=.7, label="|r| needed for p<0.05 (own max-stat null)"); ax[0].scatter(M.r.abs(), y, s=22, color=np.where(M.survives_bh05, ORANGE, BLUE), zorder=3, label="observed |r| (orange = survives BH q<=0.05)")
ax[0].set_yticks(y); ax[0].set_yticklabels([f"{i}  {s.split('_')[0]}->{t[:22]}" for i, s, t in zip(M.id, M.signal, M.target)], fontsize=6.5); ax[0].set_xlabel("|r| at best pre-registered lag"); ax[0].legend(frameon=False, loc="lower right", fontsize=7.5); ax[0].set_title(f"All {len(R)} pre-registered tests"); ax[0].grid(axis="y", visible=False)
for lab, p, c in [("family: market tier", R[R.tier == "market"].maxstat_p, BLUE), ("family: physical tier", R[R.tier == "physical"].maxstat_p, ORANGE), ("placebo reservoirs/regions, market targets", PL[PL.tier == "market"].maxstat_p, AQUA)]:
    p = np.sort(p); ax[1].plot((np.arange(len(p)) + .5) / len(p), p, marker="o", ms=3, lw=1, color=c, label=f"{lab} (n={len(p)})")
ax[1].plot([0, 1], [0, 1], color=MUTED, lw=.8, ls="--"); ax[1].set_xlabel("expected p under the null (uniform quantile)"); ax[1].set_ylabel("observed max-stat p"); ax[1].legend(frameon=False, fontsize=7.5, loc="upper left"); ax[1].set_title("p-value calibration")
note(fig, "Market-tier p-values sit on or above the diagonal (no excess of small p) and look like the placebos. Only the physical tier departs from the null.")
fig.tight_layout(rect=(0, .02, 1, 1)); fig.savefig(F / "fig4_family_overview.png", dpi=130); plt.close(fig)

# 5 lag profiles for the four headline relationships
fig, ax = plt.subplots(1, 4, figsize=(12, 3.2), sharey=True)
for a, (i, ttl) in zip(ax, [("P1", "sat area -> official storage"), ("P2", "sat area -> marginal cost"), ("Y1_z", "Yunnan area -> SHFE Al"), ("F1", "Libya flares -> Brent")]):
    r = R[R.id == i].iloc[0]; rb = json.loads(r.r_by_lag); lg = json.loads(r.lags); c = pw[pw.id == i].crit_r_p05.iloc[0]
    a.bar(lg, rb, color=ORANGE if r.survives_bh05 else BLUE, width=.55); a.axhspan(-c, c, color="#e4e3df", alpha=.6, lw=0, zorder=0); a.axhline(0, color=MUTED, lw=.7); a.set_xticks(lg); a.set_title(f"{i}: {ttl}", fontsize=8.5); a.set_xlabel(f"lag ({'months' if r.freq=='M' else 'weeks'}) after knowable date")
ax[0].set_ylabel("Pearson r"); note(fig, "Grey band: |r| below the 5% max-stat critical value. Orange = survives BH.")
fig.tight_layout(rect=(0, .05, 1, 1)); fig.savefig(F / "fig5_lag_profiles.png", dpi=130); plt.close(fig)
print("ok")
