"""Sentinel-2 before/after differencing per event with placebo-calibrated z-scores and blob-level nulls.

Features are B12, B11 and B8A (burn scars / soot / collapsed or scorched metal all darken NIR-SWIR), so the
SWIR-only pre-war baseline (Oct-Feb) can serve as the placebo pool.
"""
import sys, itertools
import numpy as np, pandas as pd
from scipy import ndimage as ndi
from s2s1_s2lib import *
from s2s1_changelib import *
from s2s1_events import EVENTS, REPORTED
from s2s1_s2_hot import hot_mask

FEATS = ["swir22", "swir16", "nir08"]
CLEAR_SCENE = 0.10      # SCL cloud fraction for a "clear" scene; residual cloud is masked per pixel
USABLE_POST = 0.35      # a post scene is usable if at most this cloudy
Z_THR, MIN_PX = 5.0, 4  # blob = >=4 connected 20 m pixels (1600 m2) with combined z > 5
PLACEBO_DT = (4, 40)    # days between placebo scenes, spanning the event pair separations
LOCAL = 51              # px; remove change smoother than ~1 km (haze, BRDF, moisture)


def local_diff(st, i, j, valid):
    d = np.stack([st[f][j] - st[f][i] for f in FEATS])
    out = np.full_like(d, np.nan)
    w = valid.astype("float32")
    wm = np.maximum(ndi.uniform_filter(w, LOCAL), 1e-3)
    for f in range(len(d)):
        # masked local mean as the smooth background (a median filter this size is too slow; blobs are small
        # relative to the window so the mean is barely biased by them)
        bg = ndi.uniform_filter(np.where(valid, d[f], 0), LOCAL) / wm
        out[f] = np.where(valid, d[f] - bg, np.nan)
    return out


def analyse(site):
    idx, st, scl = load_site(site, bands=FEATS)
    n = len(idx)
    pre = (idx.dt < pd.Timestamp(WAR_START, tz="UTC")).to_numpy()
    clear = (idx.cloud < CLEAR_SCENE).to_numpy()
    base = np.nonzero(pre & clear)[0]
    land = ~ndi.binary_dilation(np.median(st["swir16"][base], 0) < 0.06, S8, iterations=2)
    hot_any = np.any([hot_mask(st["swir22"][k], st["swir16"][k]) for k in range(n)], 0)
    static = land & ~ndi.binary_dilation(hot_any, S8, iterations=3)
    cloud = np.isin(scl, CLOUD_SCL)
    false_cloud = cloud[base].mean(0) > 0.3   # SCL calls some bright roofs "cloud" in every scene
    cloudm = np.stack([ndi.binary_dilation(cloud[k] & ~false_cloud, S8, iterations=5) for k in range(n)])

    pairs = [(i, j) for i, j in itertools.combinations(base, 2)
             if PLACEBO_DT[0] <= (idx.dt[j] - idx.dt[i]).days <= PLACEBO_DT[1] and idx.orbit_grp[i] == idx.orbit_grp[j]]
    pdiff = {p: local_diff(st, *p, static & ~cloudm[p[0]] & ~cloudm[p[1]]) for p in pairs}
    sq = {p: np.nan_to_num(d) ** 2 for p, d in pdiff.items()}
    cnt = {p: np.isfinite(d).astype("float32") for p, d in pdiff.items()}
    SQ, CNT = sum(sq.values()), sum(cnt.values())

    def score(d, exclude):
        """Combined z over features; sigma = per-pixel placebo RMS from pairs sharing no scene with `exclude`."""
        ex = [p for p in pairs if set(p) & set(exclude)]
        s2 = (SQ - sum(sq[p] for p in ex)) / np.maximum(CNT - sum(cnt[p] for p in ex), 1)
        sig = np.sqrt(s2)
        sig = np.maximum(sig, np.nanmedian(sig[:, static], 1)[:, None, None])
        z = d / sig
        return np.nan_to_num(np.sqrt(np.nanmean(z ** 2, 0))), z, len(pairs) - len(ex)

    null, null_sizes, null_peaks = [], [], []
    for p in pairs:
        s, z, nuse = score(pdiff[p], p)
        bl = blobs(s, z[0], static, Z_THR, MIN_PX)
        null_sizes += [b["npix"] for b in bl]
        null_peaks += [b["peak"] for b in bl]
        null.append(dict(site=site, pre=idx.date[p[0]], post=idx.date[p[1]], n_sigma_pairs=nuse, n_blobs=len(bl),
                         max_blob_px=bl[0]["npix"] if bl else 0, frac_gt_thr=float((s > Z_THR)[static].mean())))
    null = pd.DataFrame(null)
    null_sizes, null_peaks = np.array(null_sizes, float), np.array(null_peaks, float)

    out, maps = [], {}
    for ev in [e for e in EVENTS if e["site"] == site]:
        prek = [k for k in np.nonzero(clear)[0] if idx.dt[k] < ev["t"] - pd.Timedelta(hours=ev["time_unc_h"])]
        postk = [k for k in range(n) if idx.dt[k] > ev["t"] and idx.cloud[k] < USABLE_POST]
        if not prek or not postk:
            continue
        i = prek[-1]
        tried = {}
        for tag, j in (("first_usable", postk[0]), ("first_clear", next((k for k in postk if clear[k]), postk[0]))):
            if j in tried:
                continue
            tried[j] = tag
            valid = static & ~cloudm[i] & ~cloudm[j]
            d = local_diff(st, i, j, valid)
            s, z, nuse = score(d, (i,))
            bl = blobs(s, z[0], valid, Z_THR, MIN_PX)
            for rank, b in enumerate(bl, 1):
                lon, lat = pix2lonlat(site, [b["row"]], [b["col"]])
                r0, c0 = int(round(b["row"])), int(round(b["col"]))
                box = (slice(max(r0 - 1, 0), r0 + 2), slice(max(c0 - 1, 0), c0 + 2))
                near = min(((np.hypot((lat[0]-la)*111e3, (lon[0]-lo)*111e3*np.cos(np.radians(la))), nm)
                            for nm, la, lo, _ in REPORTED[site]), default=(np.nan, ""))
                b.update(site=site, event=ev["event"], pair=tag, pre=idx.date[i], post=idx.date[j], rank=rank,
                         lat=round(lat[0], 5), lon=round(lon[0], 5), area_m2=b["npix"] * 400,
                         dB12=round(float(np.nanmean(d[0][box])), 3), dB8A=round(float(np.nanmean(d[2][box])), 3),
                         placebo_blobs_per_pair_ge_size=round(float((null_sizes >= b["npix"]).sum() / len(pairs)), 2),
                         placebo_blobs_per_pair_ge_size_and_peak=round(float(
                             ((null_sizes >= b["npix"]) & (null_peaks >= b["peak"])).sum() / len(pairs)), 2),
                         frac_placebo_pairs_with_ge_size=round(float((null.max_blob_px >= b["npix"]).mean()), 3),
                         nearest_reported=near[1], dist_m=round(near[0]))
            out += bl
            maps[f"{ev['event'][:10]}__{tag}"] = dict(score=s.astype("float16"), dB12=d[0].astype("float16"),
                                                    pre=idx.date[i], post=idx.date[j])
            print(f"{site} | {ev['event']} | {tag}: {idx.date[i]} -> {idx.date[j]} ({idx.dt[j]:%H:%M}Z, cloud {idx.cloud[j]:.2f}, "
                  f"+{(idx.dt[j]-ev['t']).total_seconds()/86400:.1f} d) valid={valid.mean():.2f} blobs={len(bl)} "
                  f"max={bl[0]['npix'] if bl else 0}px frac>thr={float((s > Z_THR)[valid].mean()):.4f} || placebo pairs={len(pairs)} "
                  f"n_blobs p50/p95={null.n_blobs.median():.0f}/{null.n_blobs.quantile(.95):.0f} "
                  f"max_blob p50/p95/max={null.max_blob_px.median():.0f}/{null.max_blob_px.quantile(.95):.0f}/{null.max_blob_px.max()} "
                  f"frac>thr p50={null.frac_gt_thr.median():.4f}")
    np.savez_compressed(OUT / f"s2_changemaps_{site}.npz", **{f"{k}__{kk}": vv for k, v in maps.items() for kk, vv in v.items()})
    return pd.DataFrame(out), null


if __name__ == "__main__":
    res = [analyse(s) for s in (sys.argv[1:] or SITES)]
    bl = pd.concat([r[0] for r in res], ignore_index=True)
    nl = pd.concat([r[1] for r in res], ignore_index=True)
    bl.drop(columns=["row", "col"]).to_csv(OUT / "s2_change_blobs.csv", index=False)
    nl.to_csv(OUT / "s2_change_placebo_null.csv", index=False)
    pd.set_option("display.width", 250)
    cols = ["rank", "npix", "area_m2", "lat", "lon", "peak", "dB12", "dB8A", "placebo_blobs_per_pair_ge_size",
            "placebo_blobs_per_pair_ge_size_and_peak", "frac_placebo_pairs_with_ge_size", "nearest_reported", "dist_m"]
    for (s, e, p), g in bl.groupby(["site", "event", "pair"], sort=False):
        print(f"--- {s} | {e} | {p}")
        print(g[cols].head(8).to_string(index=False))
