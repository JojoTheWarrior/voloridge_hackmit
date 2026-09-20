"""Crude plume feature (bright-white anomaly vs per-plant median composite) vs CEMS load at S2 overpass hour."""
import numpy as np, pandas as pd, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from scipy.stats import pearsonr, spearmanr
d=np.load("s2_chips.npz"); rgb=d["rgb"]; meta=pd.DataFrame(dict(plant=d["plant"],id=d["id"],t=pd.to_datetime(d["t"],format="ISO8601").tz_localize(None),cc=d["cc"]))
cems=pd.read_parquet("cems_ndt.parquet").set_index(["plant_id_eia","t"]).sort_index(); names=pd.read_csv("plants_ndt.csv").set_index("plant_id_eia").plant_name_eia
n=rgb.shape[2]; yy,xx=np.mgrid[:n,:n]; r=np.hypot(yy-n/2,xx-n/2)*10  # metres from plant coord
rows=[]
for pid in meta.plant.unique():
    idx=np.where(meta.plant==pid)[0]; stack=rgb[idx].astype("float32"); white=stack.min(axis=1)       # min over RGB = "whiteness"
    med=np.median(white,axis=0); cap=cems.loc[pid].gross_mw.max()
    for k,i in enumerate(idx):
        anom=white[k]-med
        outer=(anom[r>1500]>60).mean()                     # bright stuff far from plant = cloud/haze/snow
        inner=(anom[r<1200]>60).sum()*100/1e6              # km2 of bright-white anomaly near plant
        th=meta.t[i].floor("h"); lab=cems.loc[pid].loc[th-pd.Timedelta(hours=1):th]
        rows.append(dict(plant=pid,name=names[pid],t=meta.t[i],cc=meta.cc[i],outer=outer,plume_km2=inner,mw=lab.gross_mw.fillna(0).mean(),cf=lab.gross_mw.fillna(0).mean()/cap,units_on=lab.n_units_on.max(),i=i))
df=pd.DataFrame(rows); df.to_csv("s2_vs_cems.csv",index=False)
clear=df[df.outer<0.02].copy(); print("scenes:",len(df),"locally clear:",len(clear), "scene-days/yr/plant clear:", round(len(clear)/5))
clear["on"]=clear.mw>50
print(clear.groupby("name").agg(n=("mw","size"),n_off=("on",lambda s:(~s).sum()),plume_on=("plume_km2",lambda s:s[clear.loc[s.index,'on']].median()),plume_off=("plume_km2",lambda s:s[~clear.loc[s.index,'on']].median())).round(3).to_string())
for nm,g in clear.groupby("name"):
    print(f"{nm:22s} n={len(g):3d} pearson(plume,MW)={pearsonr(g.plume_km2,g.mw)[0]:.2f} spearman={spearmanr(g.plume_km2,g.mw)[0]:.2f}  winter(Nov-Mar) spearman={spearmanr(g[g.t.dt.month.isin([11,12,1,2,3])].plume_km2,g[g.t.dt.month.isin([11,12,1,2,3])].mw)[0]:.2f} (n={g.t.dt.month.isin([11,12,1,2,3]).sum()})")
print("pooled spearman(plume, capacity factor): %.2f n=%d"%(spearmanr(clear.plume_km2,clear.cf)[0],len(clear)))
# on/off with a single global threshold
from itertools import product
best=max(((( (clear.plume_km2>th)==clear.on).mean(),th) for th in np.arange(0,0.3,0.005)))
print("on/off: base rate on=%.2f ; best single-threshold accuracy=%.2f at %.3f km2"%(clear.on.mean(),best[0],best[1]))
off=clear[~clear.on]; print("OFF scenes: n=%d, fraction with plume<thr: %.2f ; ON scenes with plume>thr: %.2f"%(len(off),(off.plume_km2<=best[1]).mean(),(clear[clear.on].plume_km2>best[1]).mean()))
# units-on (0..k) vs plume
print(clear.groupby("units_on").plume_km2.agg(["size","median","mean"]).round(3))
# montage for one plant sorted by load
for pid,tag in [(8102,"gavin"),(3935,"amos")]:
    g=clear[clear.plant==pid].sort_values("mw"); pick=g.iloc[np.linspace(0,len(g)-1,12).astype(int)]
    fig,ax=plt.subplots(2,6,figsize=(18,6.4))
    for a,rw in zip(ax.ravel(),pick.itertuples()):
        a.imshow(np.moveaxis(rgb[rw.i],0,-1)[80:320,80:320]); a.set_title(f"{rw.t:%Y-%m-%d} {rw.mw:.0f} MW plume={rw.plume_km2:.2f}",fontsize=9); a.axis("off")
    plt.tight_layout(); plt.savefig(f"s2_montage_{tag}.png",dpi=80)
fig,ax=plt.subplots(1,5,figsize=(20,4))
for a,(nm,g) in zip(ax,clear.groupby("name")):
    w=g.t.dt.month.isin([11,12,1,2,3]); a.scatter(g.mw[w],g.plume_km2[w],c="tab:blue",s=14,label="Nov-Mar"); a.scatter(g.mw[~w],g.plume_km2[~w],c="tab:red",s=14,label="Apr-Oct"); a.set(title=nm,xlabel="CEMS gross MW at overpass",ylabel="bright-anomaly area km2"); a.legend(fontsize=7)
plt.tight_layout(); plt.savefig("s2_vs_cems.png",dpi=90)
