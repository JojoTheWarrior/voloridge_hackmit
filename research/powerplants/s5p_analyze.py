"""Crude TROPOMI NO2 enhancement vs CEMS NOx / load. No plume model, no AMF correction: deliberately hackathon-grade."""
import numpy as np, pandas as pd, glob, sys
from scipy.stats import pearsonr, spearmanr
f = sys.argv[1]
d = np.load(f); no2, qa, pid, stamp = d["no2"]*1e6, d["qa"], d["plant"], d["stamp"]   # umol/m2
if qa.max() > 1.5: qa = qa/100
plants = pd.read_csv("plants.csv").set_index("plant_id_eia")
cems = pd.read_parquet("cems_plants.parquet"); wind = pd.read_parquet("wind.parquet")
cems = cems.set_index(["plant_id_eia","t"]).sort_index(); wind = wind.set_index(["plant_id_eia","time"]).sort_index()
n = no2.shape[1]; c = n//2; px = 0.035
rows = []
for i in range(len(pid)):
    p = plants.loc[pid[i]]; lat, lon = p.latitude, p.longitude
    day = pd.Timestamp(stamp[i][:8])
    t_over = day + pd.Timedelta(hours=13.5 - lon/15)             # ~13:30 local solar
    th = t_over.floor("h")
    jj, ii = np.meshgrid(np.arange(n)-c, np.arange(n)-c)         # ii rows (south+), jj cols (east+)
    x = jj*px*111.2*np.cos(np.radians(lat)); y = -ii*px*111.2     # km east, km north
    r = np.hypot(x, y)
    a = np.where(qa[i] >= 0.75, no2[i], np.nan)
    if np.isfinite(a[r<60]).mean() < 0.85 or not np.isfinite(a[r<12]).any(): continue
    try: w = wind.loc[(pid[i], th)]
    except KeyError: continue
    ws, wd = w.wind_speed_100m, np.radians(w.wind_direction_100m)  # direction wind comes FROM
    ux, uy = -np.sin(wd), -np.cos(wd)                              # unit vector wind blows TO
    dw = x*ux + y*uy; cw = -x*uy + y*ux                            # downwind / crosswind km
    bg_ann = np.nanmedian(a[(r>50)&(r<100)])
    simple = np.nanmean(a[r<15]) - bg_ann
    up = np.nanmedian(a[(dw<-10)&(dw>-60)&(np.abs(cw)<40)])
    box = (dw>-5)&(dw<45)&(np.abs(cw)<12)
    enh = np.nanmean(a[box]) - up
    lab = cems.loc[pid[i]].loc[th-pd.Timedelta(hours=3):th]
    rows.append(dict(plant=pid[i], name=p.plant_name_eia, t=t_over, ws=ws, simple=simple, enh=enh, flux=enh*ws,
                     peak=np.nanmax(a[r<25])-bg_ann, nox=lab.nox_lbs.mean(), mw=lab.gross_mw.mean(), cloud=w.cloud_cover))
df = pd.DataFrame(rows).dropna(subset=["nox","enh"])
# multiple orbits same day: keep the one... just average per plant-day
df["day"] = df.t.dt.floor("D"); df = df.groupby(["plant","name","day"], as_index=False).mean(numeric_only=True)
df.to_csv("s5p_vs_cems.csv", index=False)
print("valid plant-days:", len(df), "of", len(pid), "windows")
print("\n== per-plant daily correlations (pearson r; n)")
res=[]
for (pl,nm), g in df.groupby(["plant","name"]):
    g2 = g[g.ws.between(2, 9)]
    res.append(dict(name=nm, n=len(g), nox_mean=g.nox.mean(), nox_cv=g.nox.std()/g.nox.mean(), mw_mean=g.mw.mean(),
        enh_mean=g.enh.mean(), simple_mean=g.simple.mean(), snr_daily=g.enh.mean()/g.enh.std(),
        r_simple=pearsonr(g.simple,g.nox)[0], r_enh=pearsonr(g.enh,g.nox)[0], r_flux=pearsonr(g.flux,g.nox)[0],
        r_flux_mw=pearsonr(g.flux,g.mw)[0], r_flux_windfilt=pearsonr(g2.flux,g2.nox)[0] if len(g2)>5 else np.nan, n_wf=len(g2)))
res = pd.DataFrame(res); pd.set_option("display.width",250); print(res.round(2).to_string())
res.to_csv("s5p_per_plant.csv", index=False)
print("\n== pooled daily: flux vs nox  pearson %.2f spearman %.2f (n=%d)" % (pearsonr(df.flux,df.nox)[0], spearmanr(df.flux,df.nox)[0], len(df)))
print("== pooled daily: flux vs MW   pearson %.2f" % pearsonr(df.flux,df.mw)[0])
print("== cross-plant 6-mo means: enh_mean vs nox_mean pearson %.2f ; flux mean vs nox: %.2f (n=%d plants)" % (pearsonr(res.enh_mean,res.nox_mean)[0], pearsonr(df.groupby('plant').flux.mean(), df.groupby('plant').nox.mean())[0], len(res)))
print("== cross-plant means: enh vs MW pearson %.2f" % pearsonr(res.enh_mean,res.mw_mean)[0])
df["month"]=df.day.dt.to_period("M"); m=df.groupby(["plant","month"]).agg(flux=("flux","mean"),nox=("nox","mean"),mw=("mw","mean"),n=("flux","size")).query("n>=8")
print("== plant-month means (n>=8 days): flux vs nox pearson %.2f (n=%d)" % (pearsonr(m.flux,m.nox)[0], len(m)))
# within-plant monthly (demeaned) — the thing an alt-data nowcast actually needs
mm = m.copy(); mm["flux_d"]=mm.flux-mm.groupby("plant").flux.transform("mean"); mm["nox_d"]=mm.nox/mm.groupby("plant").nox.transform("mean")
print("== within-plant monthly anomalies: pearson %.2f" % pearsonr(mm.flux_d, mm.nox_d)[0])
# on/off style: low-output days vs high-output days
df["rel"]=df.nox/df.groupby("plant").nox.transform("max")
lo, hi = df[df.rel<0.25], df[df.rel>0.6]
print("== days with NOx<25%% of plant max: n=%d mean enh %.1f | >60%%: n=%d mean enh %.1f umol/m2" % (len(lo), lo.enh.mean(), len(hi), hi.enh.mean()))
