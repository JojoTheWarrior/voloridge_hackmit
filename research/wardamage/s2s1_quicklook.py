"""Contact sheets (SWIR false colour B12/B11/B8A) of every S2 scene per site, for eyeballing cloud/smoke."""
import sys
import numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from s2s1_s2lib import *

for site in sys.argv[1:] or list(SITES):
    idx, st, scl = load_site(site)
    n = len(idx); nc = 6; nr = int(np.ceil(n / nc))
    fig, axs = plt.subplots(nr, nc, figsize=(nc * 3.2, nr * 3.2 * st["red"].shape[1] / st["red"].shape[2] + 0.4))
    for ax in axs.ravel(): ax.axis("off")
    for k, ax in zip(range(n), axs.ravel()):
        rgb = np.dstack([st[b][k] for b in ("swir22", "swir16", "nir08")])
        ax.imshow(np.clip(rgb / 0.6, 0, 1)[::2, ::2])
        ax.set_title(f"{idx.date[k]} cl={idx.cloud[k]:.2f}", fontsize=8)
    fig.tight_layout(); fig.savefig(OUT / f"quicklook_swir_{site}.png", dpi=70); plt.close(fig)
