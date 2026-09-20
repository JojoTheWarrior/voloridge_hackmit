"""Sentinel-2 20 m SWIR active-heat detection: persistent (flare-stack) vs novel hot pixels, with a
leave-one-out pre-war null, plus a flare-activity time series over the persistent mask."""
import sys
import numpy as np, pandas as pd
from scipy import ndimage as ndi
from s2s1_s2lib import *

HOT_D = 0.30          # B12-B11 reflectance excess; see threshold sweep printed by this script
SAT = 1.2             # both SWIR bands above this = saturated core of a very hot source
KNOWN_DILATE = 3      # px (60 m): flame wander + bloom + geolocation
PERSIST_FREQ = 0.25
USABLE_CLOUD = 0.5    # hot sources shine through thin cloud; only drop mostly-overcast scenes from baselines
S8 = np.ones((3, 3), bool)


def hot_mask(b12, b11, thr=HOT_D):
    core = (b12 - b11) > thr
    sat = (b12 > SAT) & (b11 > SAT)
    # saturated pixels count only when attached to a spectrally-hot pixel (bright cloud/glint also saturates)
    return core | (sat & ndi.binary_dilation(core, S8, iterations=2))


def clusters(mask, site, D, date):
    lab, n = ndi.label(mask, S8)
    out = []
    for i in range(1, n + 1):
        rr, cc = np.nonzero(lab == i)
        lon, lat = pix2lonlat(site, [rr.mean()], [cc.mean()])
        out.append(dict(site=site, date=date, npix=len(rr), area_m2=len(rr) * 400, lat=round(lat[0], 5),
                        lon=round(lon[0], 5), maxD=round(float(D[rr, cc].max()), 3)))
    return out


def analyse(site):
    idx, st, scl = load_site(site, bands=["swir22", "swir16", "nir08"])
    b12, b11 = st["swir22"], st["swir16"]
    D = b12 - b11
    pre = (idx.dt < pd.Timestamp(WAR_START, tz="UTC")).to_numpy()
    usable = (idx.cloud < USABLE_CLOUD).to_numpy()
    base = pre & usable

    # threshold sweep: leave-one-out novel pixels in pre-war baseline scenes, per candidate threshold
    sweep = []
    for thr in (0.1, 0.15, 0.2, 0.3, 0.4, 0.5):
        hot = np.stack([hot_mask(b12[k], b11[k], thr) for k in range(len(idx))])
        tot = hot[base].sum(0)
        nov = [(hot[k] & ~ndi.binary_dilation((tot - hot[k]) > 0, S8, iterations=KNOWN_DILATE)).sum()
               for k in np.nonzero(base)[0]]
        sweep.append(dict(site=site, thr=thr, n_base=int(base.sum()), hot_med=int(np.median(hot[base].sum((1, 2)))),
                          loo_novel_med=float(np.median(nov)), loo_novel_p95=float(np.percentile(nov, 95)),
                          loo_novel_max=int(max(nov))))

    hot = np.stack([hot_mask(b12[k], b11[k]) for k in range(len(idx))])
    tot = hot[base].sum(0)
    freq = tot / base.sum()
    persistent = ndi.binary_dilation(freq >= PERSIST_FREQ, S8, iterations=2)

    rows, clus = [], []
    for k in range(len(idx)):
        others = tot - hot[k] if base[k] else tot
        known = ndi.binary_dilation(others > 0, S8, iterations=KNOWN_DILATE)
        novel = hot[k] & ~known
        cl = clusters(novel, site, D[k], idx.date[k])
        clus += cl
        hp = hot[k] & persistent
        rows.append(dict(site=site, date=idx.date[k], dt=idx.dt[k], cloud=round(idx.cloud[k], 3), prewar=bool(pre[k]),
                         baseline=bool(base[k]), n_hot=int(hot[k].sum()), n_hot_persistent=int(hp.sum()),
                         flare_b12_sum=round(float(b12[k][hp].sum()), 2), flare_D_sum=round(float(D[k][hp].sum()), 2),
                         n_novel=int(novel.sum()), max_novel_cluster=max([c["npix"] for c in cl], default=0),
                         n_novel_clusters_ge3=sum(c["npix"] >= 3 for c in cl)))
    np.savez_compressed(OUT / f"s2_hotmaps_{site}.npz", freq=freq.astype("float32"), persistent=persistent,
                        dates=idx.date.to_numpy().astype(str), hot=np.packbits(hot, axis=None), shape=hot.shape)
    return pd.DataFrame(rows), pd.DataFrame(clus), pd.DataFrame(sweep)


if __name__ == "__main__":
    res = [analyse(s) for s in (sys.argv[1:] or SITES)]
    ts, cl, sw = (pd.concat(x, ignore_index=True) for x in zip(*res))
    ts.to_csv(OUT / "s2_hot_timeseries.csv", index=False)
    cl.to_csv(OUT / "s2_novel_hot_clusters.csv", index=False)
    sw.to_csv(OUT / "s2_hot_threshold_sweep.csv", index=False)
    pd.set_option("display.width", 250)
    print(sw.to_string())
    for s, g in ts.groupby("site", sort=False):
        print(g.drop(columns=["site", "dt"]).to_string())
