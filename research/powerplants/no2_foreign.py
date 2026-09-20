"""Activity index + US-calibrated bands for Gulf/Iran/Iraq plants, contamination flags, war-window test with placebo windows, SO2 detectability."""
import numpy as np, pandas as pd, json, glob, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from scipy import ndimage as ndi
cal = json.load(open("no2_calibration.json")); PX = 0.035
pl = pd.read_csv("plants_foreign2.csv").rename(columns={"plant_id_eia": "plant", "plant_name_eia": "name", "state": "country"})
MANUAL = {"SAU_RABIGH": "PetroRabigh refinery/petchem adjacent", "IRN_MONTAZERI": "Isfahan refinery adjacent + Isfahan city", "IRN_SHAZAND": "Arak (Shazand) refinery adjacent", "IRN_BANDARABBAS": "refinery + port city",
          "QAT_RASLAFFAN": "Ras Laffan LNG/industrial city", "QAT_MESAIEED": "Mesaieed industrial city", "SAU_JUBAIL": "Jubail industrial city", "ARE_JEBELALI": "Dubai/Jebel Ali port+smelter", "KWT_AZZOUR": "Al-Zour refinery adjacent",
          "IRQ_SHATTBASRA": "Basra oil-field flaring", "KWT_DOHA": "Kuwait City", "IRN_RAMIN": "Ahvaz city + oil-field flaring", "SAU_RIYADH9": "Riyadh metro", "SAU_RIYADH10": "Riyadh metro", "ARE_TAWEELAH": "Taweelah aluminium smelter (EGA) adjacent",
          "SAU_RASALKHAIR": "Ma'aden aluminium/phosphate complex adjacent", "BHR_ALDUR": "Bahrain (Alba smelter 15 km)", "SAU_JAZAN": "coordinates fall in Jazan town, plant not visible at cross"}
# mean maps -> automatic contamination metrics
def mean_map(prod, d0, d1):
    S = N = None
    for f in sorted(glob.glob(f"grids/me_{prod}_*.npz")):
        if not (d0 <= f[-11:-4] <= d1): continue
        d = np.load(f); g = d["grid"].astype("float32"); ok = np.isfinite(g)
        if S is None: S = np.zeros(g.shape[1:]); N = S.copy(); b = d["bounds"]
        S += np.where(ok, g, 0).sum(0); N += ok.sum(0)
    return np.where(N > 20, S/np.maximum(N, 1), np.nan), b
mm, (lon0, lat0, lon1, lat1) = mean_map("no2", "2025-01", "2025-12"); fill = np.where(np.isfinite(mm), mm, np.nanmedian(mm)); enhmap = fill - ndi.median_filter(fill, size=31)
ct = pd.read_csv("cities15000.txt", sep="\t", header=None, usecols=[1, 4, 5, 14], names=["city", "lat", "lon", "pop"]); gp = pd.read_csv("gppd.csv", low_memory=False); gp = gp[gp.primary_fuel.isin(["Gas", "Oil", "Coal"])]
rows = []
for p in pl.itertuples():
    r, c = int((lat1-p.latitude)/PX), int((p.longitude-lon0)/PX); w = enhmap[r-12:r+13, c-12:c+13]; jj, ii = np.meshgrid(np.arange(-12, 13), np.arange(-12, 13)); dist = np.hypot(jj*PX*111.2*np.cos(np.radians(p.latitude)), ii*PX*111.2)
    at = np.nanmean(w[dist < 8]); k = np.nanargmax(np.where(dist < 45, w, -1e9)); pk = w.flat[k]; pkd = dist.flat[k]
    dc = np.hypot(ct.lat-p.latitude, (ct.lon-p.longitude)*np.cos(np.radians(p.latitude)))*111.2; city = ct[(dc < 30) & (ct["pop"] > 300000)].sort_values("pop", ascending=False)
    dg = np.hypot(gp.latitude-p.latitude, (gp.longitude-p.longitude)*np.cos(np.radians(p.latitude)))*111.2; other = gp[(dg > 5) & (dg < 30)].capacity_mw.sum()
    flags = []
    if pkd > 12 and pk > 1.5*max(at, 1): flags.append(f"stronger NO2 peak {pkd:.0f} km away")
    if len(city): flags.append(f"city {city.iloc[0].city} ({city.iloc[0]['pop']/1e6:.1f}M) <30km")
    if other > 0.5*p.capacity_mw: flags.append(f"other GPPD thermal {other:.0f} MW within 5-30 km")
    if p.plant in MANUAL: flags.append("manual: " + MANUAL[p.plant])
    rows.append(dict(plant=p.plant, enh_at_plant_2025=at, peak_within_45km=pk, peak_dist_km=pkd, flags="; ".join(flags), contaminated=len(flags) > 0))
C = pd.DataFrame(rows)
# daily index
d = pd.read_csv("no2_daily_foreign.csv", parse_dates=["day"]); d = d[d.ws.between(2, 9)].copy(); d["idx"] = d.enh/np.exp(cal["temp_coef_per_degC"]*(d.temp-15))
det = d.groupby("plant").enh.agg(["mean", "std", "size"]); det["t"] = det["mean"]/(det["std"]/np.sqrt(det["size"])); det["detectable"] = (det["mean"] >= cal["detect_mean_enh"]) & (det.t >= cal["detect_t"])
WAR = (pd.Timestamp("2026-02-28"), pd.Timestamp("2026-04-08")); REF = (pd.Timestamp("2025-02-28"), pd.Timestamp("2025-04-08")); J25 = (pd.Timestamp("2025-06-13"), pd.Timestamp("2025-06-24"))
base = d[(d.day < WAR[0]) & ~d.day.between(*J25)]; bmean = base.groupby("plant").idx.mean()
rng = np.random.default_rng(0); out = []; series = {}
for p, g in d.groupby("plant"):
    g = g.set_index("day").sort_index(); rel = g.idx/bmean[p]; roll = rel.rolling("30D", min_periods=8).mean(); series[p] = roll
    w = rel[WAR[0]:WAR[1]]; r = rel[REF[0]:REF[1]]; pre = rel[WAR[0]-pd.Timedelta(days=60):WAR[0]-pd.Timedelta(days=1)]; post = rel[WAR[1]+pd.Timedelta(days=1):WAR[1]+pd.Timedelta(days=60)]
    # placebo: same 40-day window pair shifted through the non-war record -> null distribution of (window mean - rest mean)
    nonwar = rel[:WAR[0]-pd.Timedelta(days=1)]; null = []
    for s0 in pd.date_range(nonwar.index.min(), nonwar.index.max()-pd.Timedelta(days=40), freq="10D"):
        x = nonwar[s0:s0+pd.Timedelta(days=39)]
        if len(x) >= 8: null.append(x.mean())
    null = np.array(null); wm = w.mean() if len(w) >= 8 else np.nan
    implied = cal["intercept"] + cal["slope"]*wm if np.isfinite(wm) else np.nan
    out.append(dict(plant=p, n_days=len(g), n_war=len(w), idx_war=wm, idx_same_window_2025=r.mean() if len(r) >= 8 else np.nan, idx_pre60=pre.mean() if len(pre) >= 8 else np.nan, idx_post60=post.mean() if len(post) >= 8 else np.nan,
                    placebo_p_low=float((null <= wm).mean()) if np.isfinite(wm) and len(null) > 10 else np.nan, placebo_sd=float(null.std()) if len(null) > 10 else np.nan,
                    implied_rel_nox=implied, implied_lo80=implied+cal["resid_q10"] if np.isfinite(implied) else np.nan, implied_hi80=implied+cal["resid_q90"] if np.isfinite(implied) else np.nan,
                    idx_jun2025_war=rel[J25[0]:J25[1]].mean() if len(rel[J25[0]:J25[1]]) >= 5 else np.nan))
R = pl[["plant", "name", "country", "capacity_mw", "fuel"]].merge(det.reset_index()[["plant", "mean", "t", "detectable"]].rename(columns={"mean": "mean_enh_umol_m2", "t": "t_stat"})).merge(C).merge(pd.DataFrame(out))
# SO2
try:
    s = pd.read_csv("so2_daily_foreign.csv", parse_dates=["day"]); s = s[s.ws.between(2, 9)]; sd = s.groupby("plant").enh.agg(["mean", "std", "size"]); sd["so2_t"] = sd["mean"]/(sd["std"]/np.sqrt(sd["size"]))
    R = R.merge(sd.reset_index()[["plant", "mean", "so2_t"]].rename(columns={"mean": "so2_mean_enh_umol_m2"}), how="left")
except FileNotFoundError: pass
R.to_csv("foreign_activity_index.csv", index=False); pd.set_option("display.width", 320); pd.set_option("display.max_colwidth", 60)
print(R.drop(columns=["flags"]).round(2).to_string()); print(R[["plant", "flags"]].to_string())
clean = R[R.detectable & ~R.contaminated]; print("\nclean+detectable:", len(clean), "| detectable:", int(R.detectable.sum()), "| contaminated:", int(R.contaminated.sum()))
for grp, g in [("all detectable", R[R.detectable]), ("clean detectable", clean), ("Iran detectable", R[R.detectable & (R.country == "IRN")]), ("Gulf (SAU/KWT/QAT/ARE/BHR) detectable", R[R.detectable & R.country.isin(["SAU", "KWT", "QAT", "ARE", "BHR"])])]:
    print(f"{grp:45s} n={len(g):2d} median idx war={g.idx_war.median():.2f} same-window-2025={g.idx_same_window_2025.median():.2f} pre60={g.idx_pre60.median():.2f} post60={g.idx_post60.median():.2f}  plants with placebo_p<0.05: {int((g.placebo_p_low < 0.05).sum())}")
pd.concat(series, names=["plant"]).rename("idx30").reset_index().to_csv("foreign_index_30d.csv", index=False)
show = R[R.detectable].sort_values("placebo_p_low").plant.head(12).tolist(); fig, ax = plt.subplots(4, 3, figsize=(17, 11), sharex=True)
for a, p in zip(ax.ravel(), show):
    sr = series[p]; a.plot(sr.index, sr.values, lw=1.2); a.axhline(1, c="grey", lw=.5); a.axvspan(*WAR, color="red", alpha=.15); a.axvspan(*J25, color="orange", alpha=.3)
    a.fill_between(sr.index, cal["nochange_index_q10"], cal["nochange_index_q90"], color="grey", alpha=.12)
    rr = R.set_index("plant").loc[p]; a.set_title(f"{rr['name']} ({rr.country}) war idx={rr.idx_war:.2f} placebo p={rr.placebo_p_low:.2f}{'  [CONTAMINATED]' if rr.contaminated else ''}", fontsize=9); a.set_ylim(-0.5, 3)
fig.suptitle("30-day TROPOMI NO2 activity index (relative to pre-war mean, temperature-corrected with US-learned coefficient). Grey = US-calibrated 80% no-change band. Red = 28 Feb-8 Apr 2026."); plt.tight_layout(); plt.savefig("figs/foreign_no2_index.png", dpi=75)
