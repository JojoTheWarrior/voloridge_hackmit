"""Per-site panels (pre RGB, post RGB, post SWIR false colour, S2 change score, S1 log-ratio) with reported
strike locations / VIIRS hotspots marked, full site plus 2 km zooms; and the flare time-series figure."""
import sys
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from s2s1_s2lib import *
from s2s1_events import EVENTS, REPORTED

# which event pair to draw per site: (event key prefix, S2 pair tag)
DRAW = {"ras_laffan": ("2026-03-18", "first_clear"), "south_pars": ("2026-03-18", "first_usable"),
        "fujairah": ("2026-03-03", "first_usable"), "tehran": ("2026-03-07", "first_usable")}
ZOOM_HALF = 50  # 20 m px -> 2 km window


def stretch(rgb, hi):
    return np.clip(rgb / hi, 0, 1) ** 0.8


def panel(site):
    evkey, tag = DRAW[site]
    idx, st, _ = load_site(site)
    cm = np.load(OUT / f"s2_changemaps_{site}.npz")
    pre_d, post_d = str(cm[f"{evkey}__{tag}__pre"]), str(cm[f"{evkey}__{tag}__post"])
    i, j = idx.index[idx.date == pre_d][0], idx.index[idx.date == post_d][0]
    score = cm[f"{evkey}__{tag}__score"].astype("float32")
    s1 = np.load(OUT / f"s1_changemaps_{site}_vv.npz")
    s1keys = sorted(k for k in s1.files if k.startswith(evkey) and k.endswith("__z"))
    hot = pd.read_csv(OUT / "s2_novel_hot_clusters.csv").query("site == @site and npix >= 3")
    ev_t = next(e["t"] for e in EVENTS if e["site"] == site and e["event"].startswith(evkey))
    hot = hot[(pd.to_datetime(hot.date, utc=True) > ev_t - pd.Timedelta(days=1)) &
              (pd.to_datetime(hot.date, utc=True) < ev_t + pd.Timedelta(days=12))]
    blobs = pd.read_csv(OUT / "s2_change_blobs.csv").query("site == @site and pair == @tag")
    blobs = blobs[blobs.event.str.startswith(evkey)].head(10)

    rgb = lambda k: stretch(np.dstack([st[b][k] for b in ("red", "green", "blue")]), 0.35)
    swir = lambda k: stretch(np.dstack([st[b][k] for b in ("swir22", "swir16", "nir08")]), 0.6)
    layers = [(f"S2 RGB pre {pre_d}", rgb(i), {}), (f"S2 RGB post {post_d}", rgb(j), {}),
              (f"S2 SWIR (B12,B11,B8A) post {post_d}", swir(j), {}),
              (f"S2 change score (placebo z), top-10 blobs circled", score, dict(cmap="magma", vmin=0, vmax=10))]
    if s1keys:
        z = s1[s1keys[0]].astype("float32")
        z20 = z[:z.shape[0] // 2 * 2, :z.shape[1] // 2 * 2].reshape(z.shape[0] // 2, 2, z.shape[1] // 2, 2).mean((1, 3))
        layers.append((f"S1 VV log-ratio z, orbit {s1keys[0].split('__')[1]}, post {s1[s1keys[0][:-3] + '__post']}",
                       z20, dict(cmap="RdBu_r", vmin=-6, vmax=6)))
    rep = REPORTED[site]
    rr, cc = zip(*[[v[0] for v in lonlat2pix(site, lo, la)] for _, la, lo, _ in rep])
    nrow = 1 + len(rep)
    fig, axs = plt.subplots(nrow, len(layers), figsize=(4.2 * len(layers), 3.6 * nrow), squeeze=False)
    for r in range(nrow):
        for c, (title, img, kw) in enumerate(layers):
            ax = axs[r, c]
            ax.imshow(img, interpolation="nearest", **kw)
            for (nm, la, lo, kind), y, x in zip(rep, rr, cc):
                ax.plot(x, y, marker="+" if kind == "reported" else "x", color="cyan" if kind == "reported" else "lime",
                        ms=14, mew=1.8, ls="none")
            if len(hot):
                hy, hx = lonlat2pix(site, hot.lon.to_numpy(), hot.lat.to_numpy())
                ax.scatter(hx, hy, s=60, facecolors="none", edgecolors="yellow", linewidths=1.2)
            if c == 3 and len(blobs):
                by, bx = lonlat2pix(site, blobs.lon.to_numpy(), blobs.lat.to_numpy())
                ax.scatter(bx, by, s=160, facecolors="none", edgecolors="white", linewidths=0.9)
            if r == 0:
                ax.set_title(title, fontsize=8)
            else:
                y, x = rr[r - 1], cc[r - 1]
                ax.set_xlim(x - ZOOM_HALF, x + ZOOM_HALF); ax.set_ylim(y + ZOOM_HALF, y - ZOOM_HALF)
                if c == 0:
                    ax.set_ylabel(f"2 km zoom: {rep[r-1][0]}", fontsize=7)
            ax.set_xticks([]); ax.set_yticks([])
    fig.suptitle(f"{SITES[site]['name']} - event {evkey}. cyan + = reported target (OSM), green x = VIIRS hotspot, "
                 f"yellow o = novel S2 hot cluster within -1..+12 d", fontsize=10)
    fig.tight_layout()
    fig.savefig(OUT / f"panel_{site}.png", dpi=110)
    plt.close(fig)


def flare_figure():
    ts = pd.read_csv(OUT / "s2_hot_timeseries.csv", parse_dates=["dt"])
    fig, axs = plt.subplots(len(SITES), 1, figsize=(11, 2.6 * len(SITES)), sharex=True)
    for ax, site in zip(axs, SITES):
        g = ts[ts.site == site]
        ok = g.cloud < 0.2
        ax.plot(g.dt[ok], g.flare_b12_sum[ok], "o-", color="#c2410c", ms=4, lw=1, label="persistent-flare B12 sum, scenes <20% cloud")
        ax.plot(g.dt[~ok], g.flare_b12_sum[~ok], "o", mfc="none", color="#9ca3af", ms=4, label="cloudy scene (lower bound)")
        ax2 = ax.twinx()
        ax2.bar(g.dt, g.max_novel_cluster, width=1.2, color="#2563eb", alpha=0.6)
        ax2.set_ylabel("largest novel hot cluster (px)", fontsize=8, color="#2563eb")
        ax.axvline(pd.Timestamp(WAR_START, tz="UTC"), color="k", lw=0.8, ls=":")
        for e in EVENTS:
            if e["site"] == site:
                ax.axvline(e["t"], color="red", lw=1, ls="--")
        ax.set_ylabel("sum B12 reflectance", fontsize=8); ax.set_title(SITES[site]["name"], fontsize=9, loc="left")
    axs[0].legend(fontsize=7, loc="upper right")
    axs[-1].set_xlim(pd.Timestamp("2025-10-01", tz="UTC"), pd.Timestamp("2026-05-02", tz="UTC"))
    fig.suptitle("Sentinel-2 20 m flare activity over pre-war persistent hot pixels (red dashed = strikes, dotted = war start)", fontsize=10)
    fig.tight_layout(); fig.savefig(OUT / "flare_timeseries_s2.png", dpi=120); plt.close(fig)


if __name__ == "__main__":
    for s in sys.argv[1:] or SITES:
        panel(s)
    flare_figure()
