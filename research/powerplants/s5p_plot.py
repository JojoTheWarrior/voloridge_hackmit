import pandas as pd, numpy as np, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
df=pd.read_csv("s5p_vs_cems.csv"); pp=pd.read_csv("s5p_per_plant.csv")
fig,ax=plt.subplots(1,3,figsize=(16,4.8))
for nm in ["Colstrip","Jim Bridger"]:
    g=df[df.name==nm]; ax[0].scatter(g.nox,g.enh,s=14,alpha=.7,label=f"{nm} (r={np.corrcoef(g.nox,g.enh)[0,1]:.2f}, n={len(g)})")
ax[0].set(xlabel="CEMS NOx, lbs/h (3h before overpass)",ylabel="TROPOMI downwind-upwind NO2, umol/m2",title="Best case: single-day, two isolated plants"); ax[0].legend(fontsize=8); ax[0].axhline(0,c="grey",lw=.5)
ax[1].scatter(df.nox,df.flux,s=5,alpha=.35); ax[1].set(xlabel="CEMS NOx, lbs/h",ylabel="enhancement x wind speed",title=f"All 16 plants, daily: r={np.corrcoef(df.nox,df.flux)[0,1]:.2f} (n={len(df)})"); ax[1].set_ylim(-150,300)
ax[2].scatter(pp.nox_mean,pp.enh_mean); 
for r in pp.itertuples(): ax[2].annotate(r.name[:12],(r.nox_mean,r.enh_mean),fontsize=7)
ax[2].set(xlabel="mean CEMS NOx, lbs/h",ylabel="6-month mean enhancement, umol/m2",title=f"Per-plant 6-month means: r={np.corrcoef(pp.nox_mean,pp.enh_mean)[0,1]:.2f} (n=16)")
plt.tight_layout(); plt.savefig("s5p_vs_cems.png",dpi=110)
