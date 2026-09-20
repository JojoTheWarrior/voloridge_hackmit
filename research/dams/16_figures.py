"""All figures (PNG). Palette and mark rules follow the repo's dataviz reference palette: categorical blue/orange/aqua in
fixed order, diverging blue<->red around neutral gray, one y-axis per panel (stacked panels instead of dual axes)."""
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm

from common import CACHE, DATA, FIGURES, RESULTS

SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
BLUE, ORANGE, AQUA, GRAY, RED = "#2a78d6", "#eb6834", "#1baf7a", "#8a8984", "#d03b3b"
DIV = LinearSegmentedColormap.from_list("div", ["#c0392b", "#e34948", "#f0efec", "#2a78d6", "#184f95"])
plt.rcParams.update({"figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE, "font.family": "DejaVu Sans",
                     "font.size": 10, "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
                     "text.color": INK, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.titlesize": 11, "axes.titleweight": "bold", "axes.titlelocation": "left"})


def save(fig, name):
    fig.savefig(FIGURES / name, dpi=170, bbox_inches="tight")
    plt.close(fig)
    print("wrote", name)


def fig_skill():
    s = pd.read_csv(RESULTS / "skill_table.csv")
    s = s[(s.horizon_months == 0) & s.design.str.startswith("strict")]
    order = [("damped_persistence_lag1", "last month's generation (label needed)", GRAY),
             ("damped_persistence_lag3", "generation 3 months ago (EIA publication lag)", GRAY),
             ("climatology", '"it\'s April" (seasonal normal)', GRAY),
             ("area_linear_pooled", "reservoir area, linear", BLUE), ("gbm_area", "reservoir area, GBM", BLUE),
             ("gbm_climate", "basin rain + temperature only", ORANGE), ("gbm_area+climate", "area + basin climate", AQUA),
             ("gbm_persist3+area+climate", "area + climate + 3-month-old label", AQUA)]
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6), sharey=True, sharex=True)
    for ax, (tag, title) in zip(axes, [("prereg", "All pre-registered 'storage' dams"), ("carryover", "Carry-over storage only (res. time ≥100 d, ≥10 km²) — exploratory")]):
        d = s[s.subset == tag].set_index("model")
        for i, (m, lab, col) in enumerate(order[::-1]):
            r = d.loc[m]
            ax.barh(i, r.anom_skill_vs_clim, color=col, height=0.62, zorder=3)
            ax.plot([r.skill_ci_lo, r.skill_ci_hi], [i, i], color=INK, lw=1.2, zorder=4)
            ax.text(max(r.skill_ci_hi, 0) + 0.012, i, f"{r.anom_skill_vs_clim:.2f}", va="center", fontsize=9, color=INK)
        ax.set_yticks(range(len(order)), [o[1] for o in order[::-1]])
        ax.axvline(0, color=INK2, lw=1)
        ax.set_title(f"{title}\n{int(d.n_dams.iloc[0])} US dams, unseen dams AND unseen years (2019–2025)", fontsize=10)
        ax.grid(axis="y", visible=False)
    fig.supxlabel("skill on monthly generation anomalies (1 − MSE / MSE of the seasonal normal); whiskers = 95 % bootstrap CI over dams", fontsize=10, color=INK2)
    fig.suptitle("How much does orbit add beyond the calendar?  Reservoir area alone: little. Area + basin climate: real but modest.",
                 x=0.01, y=1.06, ha="left", fontsize=12, fontweight="bold")
    save(fig, "skill_vs_baseline.png")


def fig_where_signal():
    us = pd.read_csv(RESULTS / "per_dam_skill.csv")
    br = pd.read_csv(RESULTS / "transfer_brazil_per_dam.csv")
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.4), gridspec_kw={"wspace": 0.5})
    ax = axes[0]
    d = us.dropna(subset=["res_time_days"])
    ax.scatter(d.res_time_days, d.r_area_linear, s=14, color=BLUE, alpha=0.45, lw=0, zorder=3, label="one US dam (leave-dams-out)")
    bins = np.logspace(0, 3.7, 9)
    mid = d.groupby(pd.cut(d.res_time_days, bins)).r_area_linear.median()
    ax.plot([np.sqrt(i.left * i.right) for i in mid.index], mid.values, color=INK, lw=2, marker="o", ms=5, zorder=4, label="binned median")
    ax.axhline(0, color=INK2, lw=1)
    ax.set_xscale("log")
    ax.set_xlabel("reservoir residence time, days (storage ÷ mean flow, HydroLAKES)")
    ax.set_ylabel("r, area anomaly vs generation anomaly")
    ax.set_title("The signal lives in carry-over storage")
    ax.legend(frameon=False, loc="upper left")
    ax = axes[1]
    groups = [("US pre-registered set", us.r_area_linear, BLUE), ("US carry-over", us[(us.res_time_days >= 100) & (us.gww_poly_km2 >= 10)].r_area_linear, BLUE),
              ("Brazil: ONS run-of-river", br[br.storage_dam & (br.ons_tipo == "FIO DAGUA")].r_gen_area_linear, ORANGE),
              ("Brazil: ONS storage", br[br.storage_dam & (br.ons_tipo != "FIO DAGUA")].r_gen_area_linear, ORANGE)]
    for i, (lab, v, col) in enumerate(groups):
        v = v.dropna()
        ax.scatter(v, np.full(len(v), i) + np.random.default_rng(1).uniform(-0.18, 0.18, len(v)), s=12, color=col, alpha=0.4, lw=0, zorder=3)
        ax.plot([v.median()] * 2, [i - 0.32, i + 0.32], color=INK, lw=2.5, zorder=4)
        ax.text(1.02, i, f"median {v.median():.2f}  (n={len(v)})", va="center", fontsize=9)
    ax.set_yticks(range(len(groups)), [g[0] for g in groups])
    ax.set_xlim(-0.6, 1.0)
    ax.axvline(0, color=INK2, lw=1)
    ax.set_xlabel("per-dam r, satellite area anomaly vs actual generation anomaly")
    ax.set_title("Brazil's own run-of-river label is a clean negative control")
    ax.grid(axis="y", visible=False)
    save(fig, "where_the_signal_lives.png")


def fig_transfer_national():
    m = pd.read_csv(RESULTS / "transfer_national_monthly.csv").sort_values("r_monthly_area+climate")
    fig, ax = plt.subplots(figsize=(7.5, 9))
    y = np.arange(len(m))
    ax.hlines(y, m["r_monthly_climate_only"], m["r_monthly_area+climate"], color=GRID, lw=2, zorder=2)
    ax.scatter(m["r_monthly_area_only"], y, s=26, color=BLUE, zorder=3, label="area only")
    ax.scatter(m["r_monthly_climate_only"], y, s=26, color=ORANGE, zorder=3, label="basin climate only")
    ax.scatter(m["r_monthly_area+climate"], y, s=34, color=AQUA, zorder=4, label="area + climate")
    ax.set_yticks(y, [f"{c}  ({n} dams)" for c, n in zip(m.iso3, m.n_dams)], fontsize=8)
    ax.axvline(0, color=INK2, lw=1)
    ax.set_xlabel("r, US-trained prediction vs Ember national hydro capacity-factor anomaly (monthly)")
    ax.set_title(f"Zero-shot national transfer, {len(m)} countries — median r = {m['r_monthly_area+climate'].median():.2f}")
    ax.legend(frameon=False, loc="lower right")
    ax.grid(axis="y", visible=False)
    save(fig, "transfer_national.png")


def shade_events(axes, name):
    ev = pd.read_csv(DATA / "known_events.csv")
    for e in ev[ev.reservoirs.str.split("|").apply(lambda r: name in r)].itertuples():
        for ax in axes:
            ax.axvspan(pd.Timestamp(e.start + "-01"), pd.Timestamp(e.end + "-28"), color=RED if e.hydrological != "no" else GRAY, alpha=0.10, lw=0, zorder=1)
        axes[0].text(pd.Timestamp(e.start + "-01"), 1.02, e.case.split(" ", 1)[-1] + ("" if e.hydrological != "no" else " (grid fault, not hydrology)"),
                     transform=axes[0].get_xaxis_transform(), fontsize=8, color=INK2, ha="left", va="bottom")


def fig_case(name, iso3, fname, truth_gww=None, s2_csv=None, start="2009-01-01"):
    c = pd.read_csv(RESULTS / "case_studies_monthly.csv", parse_dates=["month"])
    d = c[(c.name == name) & (c.month >= start)].set_index("month")
    news_fn = DATA / "gdelt_shortage_news.parquet"
    news = pd.read_parquet(news_fn) if news_fn.exists() else pd.DataFrame(columns=["iso3", "month", "share_ppm"])
    news = news[news.iso3 == iso3].set_index("month").share_ppm
    em = pd.read_parquet(DATA / "ember" / "yearly_country.parquet")
    em = em[(em.iso3 == iso3) & em.hydro_twh.notna() & (em.year >= pd.Timestamp(start).year)]
    rows = 2 + (s2_csv is not None) + (len(news) > 0) + (len(em) > 0)
    fig, axes = plt.subplots(rows, 1, figsize=(11, 2.35 * rows), sharex=True)
    ax = axes[0]
    ax.plot(d.index, d.area_km2, color=BLUE, lw=2, zorder=3)
    clim = d.area_km2.groupby(d.index.month).transform("mean")
    ax.plot(d.index, clim, color=GRAY, lw=1, ls="--", zorder=2)
    ax.set_ylabel("km²")
    ax.set_title(f"{name}: reservoir surface area from orbit (GWW Landsat/Sentinel-2; dashed = seasonal normal)", pad=16)
    k = 1
    if s2_csv is not None:
        s = pd.read_csv(RESULTS / s2_csv)
        s["month"] = pd.to_datetime(s.month + "-01")
        s = s[(s.valid_frac >= 0.97) & (s.scene_cloud < 10)]
        axes[k].plot(s.month, s.water_km2_scene, color=BLUE, lw=2, marker="o", ms=3, zorder=3)
        axes[k].set_ylabel("km²")
        axes[k].set_title("Own Sentinel-2 extraction: shallow Matusadona–Sanyati shore sector (clear scenes only)")
        k += 1
    ax = axes[k]
    ax.fill_between(d.index, d.pred_lo * 100, d.pred_hi * 100, color=AQUA, alpha=0.18, lw=0, zorder=2)
    ax.plot(d.index, d["pred_gbm_area+climate"] * 100, color=AQUA, lw=2, zorder=3, label="predicted (US-trained, zero-shot), 10–90 % band")
    if truth_gww is not None:
        t = pd.read_parquet(RESULTS / "predictions_brazil.parquet")
        t = t[t.gww_id == truth_gww].set_index("month").y * 100
        ax.plot(t.index, t.rolling(3, min_periods=1).mean(), color=INK, lw=1.4, zorder=4, label="actual (ONS plant generation, 3-mo mean)")
    ax.axhline(0, color=INK2, lw=1)
    ax.set_ylabel("% of seasonal normal")
    ax.set_title("Generation anomaly")
    ax.legend(frameon=False, loc="lower left", fontsize=8, ncols=2)
    if len(em):
        k += 1
        ax = axes[k]
        ax.bar(pd.to_datetime(em.year.astype(str) + "-07-01"), em.hydro_twh, width=300, color=GRAY, zorder=3)
        ax.set_ylabel("TWh / year")
        ax.set_title("Reported national hydro generation (Ember, annual; recent years may be estimates)")
    if len(news):
        ax = axes[k + 1]
        ax.bar(news.index, news.values, width=25, color=ORANGE, zorder=3)
        ax.set_ylabel("articles per million")
        ax.set_title("GDELT: power-shortage coverage mentioning the country (2017→)")
    shade_events(list(axes), name)
    axes[-1].set_xlim(pd.Timestamp(start), pd.Timestamp("2026-09-01"))
    save(fig, fname)


def fig_gerd():
    fn = RESULTS / "gerd_s2_area.csv"
    if not fn.exists():
        return print("gerd not ready")
    g = pd.read_csv(fn)
    g["t"] = pd.to_datetime(g.month + "-01")
    clear = g[g.valid_frac >= 0.97]
    picks = []
    for y in range(2019, 2027):
        c = clear[clear.t.dt.year == y]
        c = c[c.t.dt.month >= 10] if len(c[c.t.dt.month >= 10]) else c  # post-rainy-season peak where available
        if len(c):
            picks.append(c.iloc[-1])
    fig = plt.figure(figsize=(13, 6.4))
    gs = fig.add_gridspec(2, max(len(picks), 1), height_ratios=[1.35, 1])
    for i, p in enumerate(picks):
        ax = fig.add_subplot(gs[0, i])
        m = np.load(CACHE / "s2" / f"gerd_{p.month}.npz")["state"]
        ax.imshow(np.where(m[::3, ::3], 1.0, np.nan), cmap=LinearSegmentedColormap.from_list("w", [BLUE, BLUE]), interpolation="nearest")
        ax.set_facecolor("#efeee9")
        ax.set_xticks([]); ax.set_yticks([]); ax.grid(False)
        ax.set_title(f"{p.month}\n{p.water_km2_filled:,.0f} km²", fontsize=9, loc="center")
    ax = fig.add_subplot(gs[1, :])
    ax.plot(clear.t, clear.water_km2_scene, color=BLUE, lw=2, marker="o", ms=3.5, zorder=3)
    ax.set_ylabel("water area in window, km²")
    ax.set_title("GERD reservoir filling, own Sentinel-2 extraction (MNDWI on ~80 m overviews; clear scenes; river baseline ≈ 15 km²)")
    fig.suptitle("Grand Ethiopian Renaissance Dam: a reservoir with no published level or output, measured from anonymous public imagery",
                 x=0.01, ha="left", fontsize=12, fontweight="bold")
    save(fig, "gerd_filling_sequence.png")


def fig_map():
    import cartopy.crs as ccrs
    import cartopy.feature as cf
    from common import ROOT
    d = pd.read_csv(ROOT / "dams_latest.csv").sort_values("capacity_mw")
    fig = plt.figure(figsize=(14, 7))
    ax = plt.axes(projection=ccrs.Robinson())
    ax.set_extent([-170, 180, -56, 78], crs=ccrs.PlateCarree())
    ax.add_feature(cf.LAND, facecolor="#efeee9", lw=0)
    ax.add_feature(cf.COASTLINE, lw=0.3, edgecolor=GRAY)
    ax.add_feature(cf.BORDERS, lw=0.2, edgecolor=GRAY)
    sc = ax.scatter(d.lon, d.lat, c=d.pred_gen_anomaly_3mo * 100, s=6 + np.sqrt(d.capacity_mw.clip(1, 20000)) * 0.9, cmap=DIV, norm=TwoSlopeNorm(0, -40, 40),
                    transform=ccrs.PlateCarree(), edgecolor=SURFACE, lw=0.3, zorder=3)
    cb = plt.colorbar(sc, ax=ax, orientation="horizontal", fraction=0.04, pad=0.03, aspect=50)
    cb.set_label("predicted hydro generation anomaly, latest 3 months (% of the dam's own seasonal normal); dot size ∝ √capacity")
    cb.outline.set_visible(False)
    ax.set_title(f"{len(d):,} storage reservoirs monitored from orbit in {d.country.nunique()} countries — latest state ({d.latest_month.max()})")
    ax.spines["geo"].set_visible(False)
    save(fig, "world_map_latest.png")


def fig_regional():
    d = pd.read_csv(RESULTS / "regional_aggregate_series.csv", parse_dates=["month"])
    R = pd.read_csv(RESULTS / "regional_aggregate.csv")
    regs = ["California", "Southeast (TVA + Carolinas + AL/GA)", "Colorado basin / Southwest", "Pacific Northwest"]
    fig, axes = plt.subplots(len(regs), 1, figsize=(11, 2.3 * len(regs)), sharex=True)
    for ax, reg in zip(axes, regs):
        x = d[(d.region == reg) & (d.design == "leave_dams_out")].set_index("month").asfreq("MS")  # gaps stay gaps
        ax.plot(x.index, x.actual_all_regional_hydro_anom * 100, color=INK, lw=1.4, zorder=3, label="actual: ALL EIA-923 hydro in region")
        ax.plot(x.index, x.predicted_anom * 100, color=AQUA, lw=2, zorder=4, label="predicted from orbit + basin climate (no labels from these dams)")
        q = R[R.region == reg].set_index("design")["r_all_regional_hydro [area+climate]"]
        ax.axvspan(pd.Timestamp("2019-01-01"), x.index.max(), color=GRID, alpha=0.35, lw=0, zorder=1)
        ax.axhline(0, color=INK2, lw=1)
        ax.set_title(f"{reg}:  r = {q['leave_dams_out']:.2f} (unseen dams)   |   r = {q['strict']:.2f} (unseen dams AND 2019–25 only, shaded)", fontsize=10)
        ax.set_ylabel("% of normal")
    axes[0].legend(frameon=False, fontsize=8, loc="upper right", ncols=2)
    fig.suptitle("Regional hydro output from orbit: dam-level noise averages out — where storage matters", x=0.01, ha="left", fontsize=12, fontweight="bold")
    fig.tight_layout()
    save(fig, "regional_aggregate.png")


FIGS = {"regional": fig_regional, "skill": fig_skill, "where": fig_where_signal, "national": fig_transfer_national, "gerd": fig_gerd, "map": fig_map,
        "guri": lambda: fig_case("Guri", "VEN", "case_guri_venezuela.png"),
        "zambia": lambda: fig_case("Itezhi-Tezhi", "ZMB", "case_zambia_itezhitezhi_kariba.png", s2_csv="s2_kariba_matusadona_area.csv", start="2012-01-01"),
        "tresmarias": lambda: fig_case("Tres Marias", "BRA", "case_brazil_tres_marias.png", truth_gww=91678),
        "mtera": lambda: fig_case("Mtera", "TZA", "case_tanzania_mtera.png"),
        "toktogul": lambda: fig_case("Toktogul", "KGZ", "case_kyrgyzstan_toktogul.png")}
for k in sys.argv[1:] or FIGS:
    try:
        FIGS[k]()
    except Exception as e:  # keep producing the other figures
        print("FAILED", k, repr(e))
