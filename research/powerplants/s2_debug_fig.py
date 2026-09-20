import numpy as np, sys, glob, os, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from s2_features import plant_features
paths=sorted(glob.glob(sys.argv[1]+"/*.npz"))[:int(sys.argv[3]) if len(sys.argv)>3 else 99]
fig,ax=plt.subplots(len(paths),4,figsize=(12,3*len(paths)))
for r,p in enumerate(paths):
    df,aux=plant_features(p); d=np.load(p,allow_pickle=True); img=d["img"]
    ok=df[(df.scl_cloud_away<0.05)&(df.bright_away<0.02)]
    med=np.median(img[ok.idx.values[:60]],axis=0).transpose(1,2,0).astype("uint8")
    ax[r,0].imshow(np.clip(med*1.5,0,255).astype("uint8")); ax[r,0].contour(aux["src"],levels=[0.5],colors="r",linewidths=.8); ax[r,0].set_title(os.path.basename(p)[:-4]+" median+source",fontsize=8)
    ax[r,1].imshow(aux["F"],cmap="magma"); ax[r,1].set_title("bright-anomaly frequency max=%.2f"%aux["F"].max(),fontsize=8)
    for c,q in [(2,0.6),(3,0.95)]:
        k=ok.sort_values("plume_km2").iloc[int(q*(len(ok)-1))]; ax[r,c].imshow(img[int(k.idx)].transpose(1,2,0)); ax[r,c].set_title(f"{k.t[:10]} plume={k.plume_km2:.2f} shadow={k.shadow_score:.2f}@{k.shadow_dist_m:.0f}m",fontsize=8)
    for a in ax[r]: a.axis("off")
plt.tight_layout(); plt.savefig(sys.argv[2],dpi=60)
