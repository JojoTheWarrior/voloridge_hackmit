"""Figures for the reported-vs-observed scoreboard (static PNG; marker shape doubles the colour encoding)."""
import pandas as pd, numpy as np, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
s = pd.read_csv("score_out/scoreboard.csv", parse_dates=["event_date", "first_det_utc", "first_news_utc"])
INK, MUTED, SURF = "#0b0b0b", "#52514e", "#fcfcfb"
V = {"hit": ("#2a78d6", "o"), "ambiguous": ("#eb6834", "s"), "miss": ("#1baf7a", "X")}
plt.rcParams.update({"font.size": 9, "axes.edgecolor": "#c9c8c2", "axes.labelcolor": MUTED, "xtick.color": MUTED, "ytick.color": MUTED, "figure.facecolor": SURF, "axes.facecolor": SURF, "axes.spines.top": False, "axes.spines.right": False})
# Fig 1: timeline strip (2026 war) by asset group
w = s[(s.war == 2026)].copy()
grp = {"refinery": "refinery / gas / LNG", "gas_processing": "refinery / gas / LNG", "lng": "refinery / gas / LNG", "depot": "depot / tank farm / terminal", "tank_farm": "depot / tank farm / terminal", "terminal": "depot / tank farm / terminal",
       "petrochemical": "petrochem / steel / smelter", "steel": "petrochem / steel / smelter", "smelter": "petrochem / steel / smelter", "port": "port / tanker", "tanker": "port / tanker"}
w["g"] = w.asset_type.map(grp).fillna("airbase / airport / other"); w.loc[w.discovery == "satellite_first", "g"] = "satellite-first candidates"
order = ["refinery / gas / LNG", "depot / tank farm / terminal", "petrochem / steel / smelter", "port / tanker", "airbase / airport / other", "satellite-first candidates"]
fig, ax = plt.subplots(figsize=(12, 4.6)); rng = np.random.default_rng(1)
for v, (c, m) in V.items():
    d = w[w.verdict == v]; y = d.g.map({g: i for i, g in enumerate(order)}) + rng.uniform(-.28, .28, len(d))
    ax.scatter(d.event_date, y, s=np.where(d.verdict == "hit", 30 + 12 * np.sqrt(d.peak_daily_frp_72h.clip(0, 2000)), 42), c=c, marker=m, edgecolor=SURF, linewidth=1, label=f"{v} (n={len(d)})", zorder=3)
for k, r in enumerate(w[(w.verdict == "hit") & (w.peak_daily_frp_72h >= 700)].sort_values("event_date").itertuples()):
    ax.annotate(r.place.split(",")[0].split("(")[0][:26], (r.event_date, order.index(r.g)), xytext=(6, -18 if k % 2 else 22), textcoords="offset points", fontsize=7.5, color=INK)
ax.set_yticks(range(len(order))); ax.set_yticklabels(order); ax.invert_yaxis(); ax.grid(axis="x", color="#e6e5e0", lw=.6); ax.axvline(pd.Timestamp("2026-04-08"), color=MUTED, lw=.8, ls=":"); ax.text(pd.Timestamp("2026-04-09"), 4.45, "ceasefire 8 Apr", fontsize=7.5, color=MUTED)
ax.set_title("Reported strikes vs VIIRS verdict, 2026 Iran war (hit marker area ~ peak daily FRP in first 72 h)", loc="left", color=INK, fontsize=10.5); ax.legend(frameon=False, ncol=3, loc="upper right", bbox_to_anchor=(1, 1.0), fontsize=8, markerscale=.6)
fig.tight_layout(); fig.savefig("score_out/fig_timeline_strip.png", dpi=160); plt.close(fig)
# Fig 2: hit/miss by site class and asset group + latency vs news
nf = s[s.discovery == "news_first"].copy(); nf["g"] = nf.asset_type.map(grp).fillna("airbase / airport / other")
fig, axs = plt.subplots(1, 3, figsize=(13.5, 4), gridspec_kw={"width_ratios": [1, 1.5, 1.4]})
def stack(ax, col, cats, title):
    left = np.zeros(len(cats))
    for v, (c, _) in V.items():
        n = np.array([((nf[col] == k) & (nf.verdict == v)).sum() for k in cats]); ax.barh(cats, n, left=left, color=c, edgecolor=SURF, linewidth=2, height=.55, label=v)
        for i, (x, l) in enumerate(zip(n, left)):
            if x: ax.text(l + x / 2, i, str(x), ha="center", va="center", fontsize=8, color=INK)
        left += n
    ax.invert_yaxis(); ax.set_title(title, loc="left", color=INK, fontsize=10); ax.set_xlabel("events"); ax.grid(axis="x", color="#e6e5e0", lw=.6); ax.set_axisbelow(True)
stack(axs[0], "site_class", ["non_flare", "permanent_flare"], "By site class"); axs[0].legend(frameon=False, fontsize=8, loc="upper center", bbox_to_anchor=(.5, -.18), ncol=3)
stack(axs[1], "g", order[:5], "By asset group")
h = nf[(nf.verdict == "hit") & nf.latency_vs_news_h.notna()].sort_values("latency_vs_news_h")
axs[2].barh(h.event_id + " " + h.place.str.split(",").str[0].str[:20], h.latency_vs_news_h, color="#2a78d6", height=.55); axs[2].axvline(0, color=MUTED, lw=.8); axs[2].axvline(3, color=MUTED, lw=.8, ls=":")
axs[2].text(3.2, len(h) - .6, "+3 h = typical NRT\ndata availability", fontsize=7, color=MUTED, va="top")
axs[2].invert_yaxis(); axs[2].set_title("Hits: first VIIRS overpass minus first site-naming\nGDELT article (h; negative = overpass earlier)", loc="left", color=INK, fontsize=9.5); axs[2].grid(axis="x", color="#e6e5e0", lw=.6); axs[2].set_axisbelow(True); axs[2].tick_params(axis="y", labelsize=7.5)
fig.tight_layout(); fig.savefig("score_out/fig_hitmiss_latency.png", dpi=160); plt.close(fig)
