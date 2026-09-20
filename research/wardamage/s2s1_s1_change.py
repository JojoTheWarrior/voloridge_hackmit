"""Sentinel-1 RTC orbit-matched backscatter log-ratio change detection with a pre-war null.

Amplitude only: interferometric coherence would need SLC pairs, which are not served as anonymous COGs.
"""
import sys, json
import numpy as np, pandas as pd
from scipy import ndimage as ndi
from s2s1_common import *
from s2s1_changelib import *
from s2s1_events import EVENTS, REPORTED
from s2s1_s2lib import load_site, pix2lonlat

N_PRE = 3              # pre image = mean power of the last N_PRE same-orbit scenes
Z_THR, MIN_PX = 4.0, 8  # blob = >=8 connected 10 m pixels (800 m2) with |z| > 4
BOX = 3                # boxcar multilook before the ratio
N_STACK = 4            # "stack" detector: mean of N_STACK post scenes vs N_STACK pre scenes, same orbit
STACK_DB, STACK_MIN_PX = 3.0, 8


def load_s1(site, pol):
    rows, arrs = [], []
    for f in sorted(CACHE.glob(f"s1_{site}_*_{pol}.npz")):
        if f.name.endswith(".part.npz"):
            continue
        z = np.load(f)
        m = json.loads(str(z["meta"]))
        a = z["data"]
        a = np.where(a > 0, a, np.nan)
        rows.append(dict(id=m["id"], dt=pd.Timestamp(m["datetime"]), orbit=m["orbit"], direction=m["direction"],
                         platform=m["platform"], valid=np.isfinite(a).mean()))
        arrs.append(a)
    idx = pd.DataFrame(rows)
    keep = idx.index[idx.valid > 0.99]
    order = idx.loc[keep].sort_values("dt").index
    # scenes from adjacent slices of one pass can both cover the site: keep one per pass
    idx2 = idx.loc[order].reset_index(drop=True)
    first = ~idx2.assign(day=idx2.dt.dt.floor("h")).duplicated(["orbit", "day"])
    stack = np.stack([arrs[i] for i in order])[first.to_numpy()]
    return idx2[first].reset_index(drop=True), stack


def db(power):
    return 10 * np.log10(ndi.uniform_filter(np.nan_to_num(power, nan=1e-4), BOX))


def log_ratio(stack, k, ks_pre):
    return db(stack[k]) - db(np.nanmean(stack[ks_pre], 0))


def analyse(site, pol="vv"):
    idx, stack = load_s1(site, pol)
    s2idx, st, _ = load_site(site, bands=["swir16"])
    pre2 = (s2idx.dt < pd.Timestamp(WAR_START, tz="UTC")) & (s2idx.cloud < 0.05)
    water = np.median(st["swir16"][pre2.to_numpy()], 0) < 0.06
    land = ~np.kron(ndi.binary_dilation(water, S8, iterations=4), np.ones((2, 2), bool))
    land = land[:stack.shape[1], :stack.shape[2]]
    war = pd.Timestamp(WAR_START, tz="UTC")

    blobs_out, null_out, stack_out, stack_null, maps = [], [], [], [], {}
    for (orb, direc), g in idx.groupby(["orbit", "direction"]):
        ks = g.index.to_numpy()
        # null log-ratios: scene k vs mean of its N_PRE predecessors, everything before the war
        nk = [i for i in range(N_PRE, len(ks)) if idx.dt[ks[i]] < war]
        nullLR = {i: log_ratio(stack, ks[i], ks[i - N_PRE:i]) for i in nk}

        def sigma(exclude=()):
            # drop null looks that share any scene with the look being scored
            use = [nullLR[i] for i in nk if not (set(range(i - N_PRE, i + 1)) & set(exclude))]
            if len(use) < 4:
                return None, len(use)
            sig = np.sqrt(np.mean(np.square(use), 0))
            return np.maximum(sig, np.median(sig[land])), len(use)

        for i in nk:
            sig, nuse = sigma(range(i - N_PRE, i + 1))
            null_type = "strict"
            if sig is None:
                # sparse archive (single satellite, 12-day repeat): only drop looks that contain this look's post
                # scene; looks sharing pre scenes stay, so this null is mildly anti-conservative
                sig, nuse = sigma([i])
                null_type = "relaxed"
            if sig is None:
                continue
            z = nullLR[i] / sig
            bl = blobs(np.abs(z), z, land, Z_THR, MIN_PX)
            null_out.append(dict(site=site, pol=pol, orbit=orb, direction=direc, post=idx.dt[ks[i]].strftime("%Y-%m-%d"),
                                 n_sigma_pairs=nuse, null_type=null_type, n_blobs=len(bl), max_blob_px=bl[0]["npix"] if bl else 0,
                                 blob_sizes=[b["npix"] for b in bl]))
        # stack detector null: consecutive N_STACK-vs-N_STACK windows entirely before the war
        npre = int((idx.dt[ks] < war).sum())
        for a in range(0, npre - 2 * N_STACK + 1, 2):
            lr = db(np.nanmean(stack[ks[a + N_STACK:a + 2 * N_STACK]], 0)) - db(np.nanmean(stack[ks[a:a + N_STACK]], 0))
            bl = blobs(np.abs(lr), lr, land, STACK_DB, STACK_MIN_PX)
            stack_null.append(dict(site=site, pol=pol, orbit=orb, start=idx.dt[ks[a]].strftime("%Y-%m-%d"), n_blobs=len(bl),
                                   max_blob_px=bl[0]["npix"] if bl else 0, blob_sizes=[b["npix"] for b in bl]))
        for ev in [e for e in EVENTS if e["site"] == site]:
            after = [i for i in range(len(ks)) if idx.dt[ks[i]] > ev["t"]][:N_STACK]
            before = [i for i in range(len(ks)) if idx.dt[ks[i]] < ev["t"] - pd.Timedelta(hours=ev["time_unc_h"])][-N_STACK:]
            if len(after) < N_STACK or len(before) < N_STACK:
                continue
            lr = db(np.nanmean(stack[ks[after]], 0)) - db(np.nanmean(stack[ks[before]], 0))
            for b in blobs(np.abs(lr), lr, land, STACK_DB, STACK_MIN_PX):
                lon, lat = pix2lonlat(site, [b["row"]], [b["col"]], res=10)
                near = min(((np.hypot((lat[0]-la)*111e3, (lon[0]-lo)*111e3*np.cos(np.radians(la))), nm)
                            for nm, la, lo, _ in REPORTED[site]), default=(np.nan, ""))
                b.update(site=site, pol=pol, event=ev["event"], orbit=orb, last_post=idx.dt[ks[after[-1]]].strftime("%Y-%m-%d"),
                         latency_d=round((idx.dt[ks[after[-1]]] - ev["t"]).total_seconds() / 86400, 1),
                         lat=round(lat[0], 5), lon=round(lon[0], 5), area_m2=b["npix"] * 100,
                         mean_dB=round(b["mean_signed"], 2), nearest_reported=near[1], dist_m=round(near[0]))
                stack_out.append(b)
            maps[f"{ev['event'][:10]}__{orb}__stack"] = dict(lr=lr.astype("float16"))

        sig, nuse = sigma()
        if sig is None:
            continue
        for ev in [e for e in EVENTS if e["site"] == site]:
            after = [i for i in range(len(ks)) if idx.dt[ks[i]] > ev["t"]]
            before = [i for i in range(len(ks)) if idx.dt[ks[i]] < ev["t"] - pd.Timedelta(hours=ev["time_unc_h"])]
            if not after or len(before) < N_PRE:
                continue
            i = after[0]
            lr = log_ratio(stack, ks[i], ks[before[-N_PRE:]])
            z = lr / sig
            bl = blobs(np.abs(z), z, land, Z_THR, MIN_PX)
            for b in bl:
                lon, lat = pix2lonlat(site, [b["row"]], [b["col"]], res=10)
                near = min(((np.hypot((lat[0]-la)*111e3, (lon[0]-lo)*111e3*np.cos(np.radians(la))), nm)
                            for nm, la, lo, _ in REPORTED[site]), default=(np.nan, ""))
                b.update(site=site, pol=pol, event=ev["event"], orbit=orb, direction=direc,
                         post=idx.dt[ks[i]].strftime("%Y-%m-%dT%H:%MZ"), platform=idx.platform[ks[i]],
                         latency_h=round((idx.dt[ks[i]] - ev["t"]).total_seconds() / 3600, 1),
                         lat=round(lat[0], 5), lon=round(lon[0], 5), area_m2=b["npix"] * 100,
                         mean_dB=round(float(np.mean(lr[int(b["row"])-1:int(b["row"])+2, int(b["col"])-1:int(b["col"])+2])), 2),
                         nearest_reported=near[1], dist_m=round(near[0]))
            blobs_out += bl
            maps[f"{ev['event'][:10]}__{orb}"] = dict(lr=lr.astype("float16"), z=z.astype("float16"),
                                                     post=idx.dt[ks[i]].strftime("%Y-%m-%dT%H:%MZ"))
            print(f"{site} {pol} | {ev['event']} | orbit {orb}{direc[0]}: first post {idx.dt[ks[i]]:%Y-%m-%d %H:%M} "
                  f"(+{(idx.dt[ks[i]] - ev['t']).total_seconds()/3600:.0f} h) blobs={len(bl)} max={bl[0]['npix'] if bl else 0}px n_null={nuse}")
    np.savez_compressed(OUT / f"s1_changemaps_{site}_{pol}.npz",
                        **{f"{k}__{kk}": vv for k, v in maps.items() for kk, vv in v.items()})
    return pd.DataFrame(blobs_out), pd.DataFrame(null_out), pd.DataFrame(stack_out), pd.DataFrame(stack_null)


if __name__ == "__main__":
    pol = "vh" if "vh" in sys.argv else "vv"
    res = [analyse(s, pol) for s in ([a for a in sys.argv[1:] if a in SITES] or SITES)]
    bl = pd.concat([r[0] for r in res], ignore_index=True)
    nl = pd.concat([r[1] for r in res], ignore_index=True)
    # false-alarm rate: placebo blobs per null look at least as large as each event blob
    if nl.empty:
        sys.exit("no null looks: pre-war S1 baseline too short")
    pooled = {s: np.concatenate([np.array(x, float) for x in g.blob_sizes] + [np.array([])]) for s, g in nl.groupby("site")}
    nlooks = nl.groupby("site").size()
    # sites with a sparse (12-day, single-satellite) archive have too few pre-war looks for a leave-out null
    bl["placebo_blobs_per_look_ge_size"] = [round((pooled[s] >= n).sum() / nlooks[s], 2) if s in pooled else np.nan
                                            for s, n in zip(bl.site, bl.npix)]
    bl.drop(columns=["row", "col"]).to_csv(OUT / f"s1_change_blobs_{pol}.csv", index=False)
    nl.drop(columns=["blob_sizes"]).to_csv(OUT / f"s1_change_null_{pol}.csv", index=False)
    sb = pd.concat([r[2] for r in res], ignore_index=True)
    sn = pd.concat([r[3] for r in res], ignore_index=True)
    spooled = {s: np.concatenate([np.array(x, float) for x in g.blob_sizes] + [np.array([])]) for s, g in sn.groupby("site")}
    sb["placebo_blobs_per_look_ge_size"] = [round((spooled[s] >= n).sum() / (sn.site == s).sum(), 2) if s in spooled else np.nan
                                            for s, n in zip(sb.site, sb.npix)]
    sb.drop(columns=["row", "col", "peak", "mean_signed"]).to_csv(OUT / f"s1_stack_blobs_{pol}.csv", index=False)
    sn.drop(columns=["blob_sizes"]).to_csv(OUT / f"s1_stack_null_{pol}.csv", index=False)
    pd.set_option("display.width", 250)
    print("first-look null (per look):\n", nl.groupby("site")[["n_blobs", "max_blob_px"]].describe().round(1).to_string())
    print("stack null (per window pair):\n", sn.groupby("site")[["n_blobs", "max_blob_px"]].describe().round(1).to_string())
    cols = ["site", "event", "orbit", "post", "latency_h", "npix", "area_m2", "lat", "lon", "peak", "mean_dB",
            "placebo_blobs_per_look_ge_size", "nearest_reported", "dist_m"]
    for _, g in bl.groupby(["site", "event", "orbit"], sort=False):
        print(f"first-look: n_blobs={len(g)}"); print(g[cols].head(4).to_string(index=False))
    cols = ["site", "event", "orbit", "last_post", "latency_d", "npix", "area_m2", "lat", "lon", "mean_dB",
            "placebo_blobs_per_look_ge_size", "nearest_reported", "dist_m"]
    for _, g in sb.groupby(["site", "event", "orbit"], sort=False):
        print(f"stack: n_blobs={len(g)}"); print(g[cols].head(6).to_string(index=False))
