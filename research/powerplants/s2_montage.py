"""Demo montage: valid (cloud-screened) scenes ordered by reported load, detected plume outlined, tower/stack sources marked.
usage: s2_montage.py chipdir plant_id country out.png "Title" """
import numpy as np, pandas as pd, sys, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from s2_features import plant_features, attached, THR
chipdir, pid, country, out, title = sys.argv[1:6]
plants = pd.read_csv("plants_s2_all.csv"); plants["id"] = plants.iloc[:, 0].astype(str); tw = pd.read_csv("osm_towers.csv"); tw["plant"] = tw.plant.astype(str)
df, aux = plant_features(f"{chipdir}/{pid}.npz", plants.set_index("id").loc[pid], tw[tw.plant == pid])
lab = pd.read_csv("s2_us_cv_predictions_v2.csv" if country == "us" else "s2_au_zero_shot_predictions_v2.csv"); lab = lab[lab.plant.astype(str) == pid]
m = df.merge(lab[["scene", "mw", "cf", "p_mono_gbt_img+wx", "temperature_2m"]], on="scene").sort_values("cf").reset_index(drop=True)
pick = m.iloc[np.unique(np.linspace(0, len(m)-1, 12).astype(int))]
img = np.load(f"{chipdir}/{pid}.npz", allow_pickle=True)["img"]; src = aux["src_t"] | aux["src_s"]
fig, ax = plt.subplots(2, 6, figsize=(19, 7.8)); c0, c1 = 40, 160
for a, r in zip(ax.ravel(), pick.itertuples()):
    B = aux["A"][r.idx] > THR; pl = attached(B, aux["src_t"]) | attached(B, aux["src_s"])
    a.imshow(np.clip(img[r.idx].transpose(1, 2, 0)[c0:c1, c0:c1].astype(float)*1.25, 0, 255).astype("uint8"), interpolation="bilinear")
    if pl[c0:c1, c0:c1].any(): a.contour(pl[c0:c1, c0:c1], levels=[0.5], colors="#00e5ff", linewidths=1.2)
    a.contour(src[c0:c1, c0:c1], levels=[0.5], colors="#ff3b30", linewidths=0.8)
    a.set_title(f"{r.t[:10]}  {r.mw:,.0f} MW (CF {r.cf:.2f})\nplume {r.plume_km2:.2f} km2  T={r.temperature_2m:.0f}C  model CF {getattr(r, '_'+str(list(pick.columns).index('p_mono_gbt_img+wx')+1)):.2f}", fontsize=9); a.axis("off")
for a in ax.ravel()[len(pick):]: a.axis("off")
fig.suptitle(title + "  |  cyan = detected plume attached to source, red = OSM cooling towers / stacks  |  2.4 km crop, Sentinel-2 L2A", fontsize=12); plt.tight_layout(h_pad=2.2); plt.savefig(out, dpi=80)
print(out, len(m), "valid labelled scenes")
