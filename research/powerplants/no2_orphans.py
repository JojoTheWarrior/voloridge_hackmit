"""Persistent NO2 hot spots with no plant in WRI GPPD nearby. usage: no2_orphans.py REGION out_prefix"""
import numpy as np, pandas as pd, glob, sys, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from scipy import ndimage as ndi
region, out = sys.argv[1], sys.argv[2]; PX = 0.035
S = None
for f in sorted(glob.glob(f"grids/{region}_no2_*.npz")):
    d = np.load(f); g = d["grid"].astype("float32"); ok = np.isfinite(g)
    if S is None: S = np.zeros(g.shape[1:]); S2 = S.copy(); N = S.copy(); lon0, lat0, lon1, lat1 = d["bounds"]
    S += np.where(ok, g, 0).sum(0); S2 += np.where(ok, g**2, 0).sum(0); N += ok.sum(0)
mean = S/np.maximum(N, 1); sd = np.sqrt(np.maximum(S2/np.maximum(N, 1) - mean**2, 0)); mean[N < 25] = np.nan
fill = np.where(np.isfinite(mean), mean, np.nanmedian(mean))
bg = ndi.median_filter(fill, size=31)                                       # ~120 km background
enh = ndi.uniform_filter(fill - bg, 3); t = enh/(sd/np.sqrt(np.maximum(N, 1)) + 1e-9)
ok_ = (enh > 6) & (t > 5) & np.isfinite(mean); sc = np.where(ok_, enh, -1e9); mx = ok_ & (sc == ndi.maximum_filter(sc, size=9))
rr, cc = np.where(mx); cand = pd.DataFrame(dict(lat=lat1-(rr+0.5)*PX, lon=lon0+(cc+0.5)*PX, enh=enh[rr, cc], mean_no2=mean[rr, cc], ndays=N[rr, cc])).sort_values("enh", ascending=False)
gp = pd.read_csv("gppd.csv", low_memory=False); gp = gp[gp.primary_fuel.isin(["Coal", "Gas", "Oil", "Petcoke", "Waste", "Biomass", "Cogeneration"])]
ct = pd.read_csv("cities15000.txt", sep="\t", header=None, usecols=[1, 4, 5, 14], names=["city", "lat", "lon", "pop"])
def near(df, la, lo, km):
    dd = np.hypot((df.lat if "lat" in df else df.latitude)-la, ((df.lon if "lon" in df else df.longitude)-lo)*np.cos(np.radians(la)))*111.2; return df[dd < km].assign(dist=dd[dd < km])
out_rows = []
for c in cand.itertuples():
    g_ = near(gp, c.lat, c.lon, 25); ci = near(ct[ct["pop"] > 100000], c.lat, c.lon, 30)
    out_rows.append(dict(lat=round(c.lat, 3), lon=round(c.lon, 3), enh_umol_m2=round(c.enh, 1), ndays=int(c.ndays), gppd_mw_within_25km=float(g_.capacity_mw.sum()),
        gppd_names="; ".join(g_.sort_values("capacity_mw", ascending=False).name.head(3)), city_within_30km="; ".join(f"{r.city}({r['pop']//1000}k)" for _, r in ci.sort_values("pop", ascending=False).head(2).iterrows())))
R = pd.DataFrame(out_rows); R["orphan"] = (R.gppd_mw_within_25km < 50) & (R.city_within_30km == ""); R.to_csv(f"{out}.csv", index=False)
np.savez_compressed(f"{out}_maps.npz", mean=mean.astype("float32"), enh=enh.astype("float32"), N=N.astype("int16"), bounds=np.array([lon0, lat0, lon1, lat1]))
print(R.head(40).to_string()); print("hot spots", len(R), "orphans", int(R.orphan.sum()))
fig, ax = plt.subplots(figsize=(11, 8)); im = ax.imshow(mean, extent=[lon0, lon1, lat0, lat1], vmin=0, vmax=np.nanpercentile(mean, 99.5), cmap="magma"); plt.colorbar(im, label="mean tropospheric NO2, umol/m2", shrink=.7)
ax.scatter(R[~R.orphan].lon, R[~R.orphan].lat, s=40, facecolors="none", edgecolors="cyan", label="hot spot with GPPD plant or city"); ax.scatter(R[R.orphan].lon, R[R.orphan].lat, s=70, marker="s", facecolors="none", edgecolors="lime", label="orphan hot spot")
ax.legend(loc="lower left"); ax.set_title(f"TROPOMI NO2 mean, {region}"); plt.tight_layout(); plt.savefig(f"{out}.png", dpi=90)
