"""Time strips of 20 m SWIR false colour (top) and RGB (bottom) around a point: s2s1_zoomstrip.py site lat lon half_px date..."""
import sys
import numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from s2s1_s2lib import *

site, lat, lon, half = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), int(sys.argv[4])
dates = sys.argv[5:]
idx, st, _ = load_site(site)
r, c = (int(v[0]) for v in lonlat2pix(site, lon, lat))
sl = (slice(max(r - half, 0), r + half), slice(max(c - half, 0), c + half))
fig, axs = plt.subplots(2, len(dates), figsize=(3.4 * len(dates), 7), squeeze=False)
for a, d in enumerate(dates):
    k = idx.index[idx.date == d][0]
    axs[0, a].imshow(np.clip(np.dstack([st[b][k][sl] for b in ("swir22", "swir16", "nir08")]) / 0.6, 0, 1), interpolation="nearest")
    axs[1, a].imshow(np.clip(np.dstack([st[b][k][sl] for b in ("red", "green", "blue")]) / 0.35, 0, 1) ** 0.8, interpolation="nearest")
    axs[0, a].set_title(d, fontsize=9)
    for ax in axs[:, a]:
        ax.set_xticks([]); ax.set_yticks([])
fig.suptitle(f"{site} {lat:.4f}N {lon:.4f}E +-{half*20} m", fontsize=9)
fig.tight_layout(); fig.savefig(OUT / f"zoom_{site}_{lat:.4f}_{lon:.4f}.png", dpi=80); plt.close(fig)
