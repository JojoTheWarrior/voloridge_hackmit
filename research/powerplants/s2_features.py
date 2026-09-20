"""Label-free plume features from Sentinel-2 TCI+SCL chips (20 m, 4 km box).
 1. whiteness (min RGB) anomaly vs a temporally-local 30th-percentile reference built from SCL-clear scenes (handles mines/ash dams that change over years)
 2. plume source = OSM cooling towers / chimneys (keyless Overpass); fallback = recurring-bright-anomaly hot spot
 3. plume = bright connected components ATTACHED to a source  4. cloud-leak guards: SCL cloud away from source, bright-away fraction, border touch,
    shadow displacement (low steam plume -> near shadow; cloud -> far shadow)
usage: s2_features.py chipdir plants.csv osm_towers.csv out.csv"""
import numpy as np, pandas as pd, sys, glob, os, re
from scipy import ndimage as ndi
PX = 20.0; THR = 45; DARK = -18; K = 21; H = 200

def tower_pixels(tw, lat0, lon0, zone):
    cm = -183 + 6*zone; g = np.radians((lon0-cm)*np.sin(np.radians(lat0)))          # grid convergence
    e = (tw.lon.values-lon0)*np.cos(np.radians(lat0))*111320; n = (tw.lat.values-lat0)*110574
    x = e*np.cos(g) - n*np.sin(g); y = e*np.sin(g) + n*np.cos(g)
    return H/2 - y/PX, H/2 + x/PX                                                  # row, col

def disc_mask(rows, cols, r):
    yy, xx = np.mgrid[:H, :H]; m = np.zeros((H, H), bool)
    for a, b in zip(rows, cols): m |= np.hypot(yy-a, xx-b) <= r
    return m

def attached(B, srcd):
    lab, k = ndi.label(B, structure=np.ones((3, 3))); ids = np.unique(lab[srcd & (lab > 0)])
    return np.isin(lab, ids) if len(ids) else np.zeros_like(B)

def plant_features(path, plant_row=None, towers=None):
    d = np.load(path, allow_pickle=True); img = d["img"].astype("float32"); scl = d["scl"]; n = len(img); pid = os.path.basename(path)[:-4]
    W = img.min(axis=1); L = img.mean(axis=1)
    cloudy = np.isin(scl, [3, 8, 9, 10]); snow = scl == 11
    clear_frac = 1 - cloudy.mean(axis=(1, 2)); tnum = pd.to_datetime(pd.Series(d["t"]), format="ISO8601").astype("int64").values/8.64e13
    ref_ok = np.where((clear_frac > 0.95) & (snow.mean(axis=(1, 2)) < 0.02))[0]
    if len(ref_ok) < K: ref_ok = np.argsort(-clear_frac)[:max(K, n//3)]
    A = np.empty_like(W); AL = np.empty_like(L)
    for i in range(n):
        idx = ref_ok[np.argsort(np.abs(tnum[ref_ok]-tnum[i]))[:K+1]]; idx = idx[idx != i][:K]
        A[i] = W[i] - np.percentile(W[idx], 30, axis=0); AL[i] = L[i] - np.percentile(L[idx], 50, axis=0)
    A -= np.median(A, axis=(1, 2), keepdims=True); AL -= np.median(AL, axis=(1, 2), keepdims=True)
    B = A > THR
    yy, xx = np.mgrid[:H, :H]
    src_kind = "none"; src_t = src_s = np.zeros((H, H), bool)
    if towers is not None and len(towers) and plant_row is not None:
        zone = int(re.search(r"_(\d{2})[A-Z]{3}_", str(d["id"][0])).group(1))
        for kind in ("cooling_tower", "chimney"):
            tw = towers[towers.kind == kind]
            if len(tw):
                r, c = tower_pixels(tw, plant_row.latitude, plant_row.longitude, zone); keep = (r > 5) & (r < H-5) & (c > 5) & (c < H-5)
                m = disc_mask(r[keep], c[keep], 5 if kind == "cooling_tower" else 4)
                if kind == "cooling_tower": src_t = m
                else: src_s = m
        if src_t.any() or src_s.any(): src_kind = "osm"
    if not src_t.any():                                                             # no mapped cooling tower: recurring bright-anomaly hot spot (near chimneys if mapped)
        if src_s.any(): cy, cx = ndi.center_of_mass(src_s)
        else: cy, cx = H/2, H/2
        rc = np.hypot(yy-cy, xx-cx)*PX
        far = np.array([(B[i] & (rc > 1200)).mean() for i in range(n)]); use = np.where(far < 0.01)[0]
        F = ndi.uniform_filter(B[use].mean(axis=0).astype("float32"), 3) if len(use) >= 10 else np.zeros((H, H), "float32")
        if F.max() >= 0.06:
            Fm = np.where(rc < 800, F, 0) if src_s.any() else F
            if Fm.max() >= 0.06:
                py, px_ = np.unravel_index(Fm.argmax(), Fm.shape); src_t = (Fm >= 0.5*Fm.max()) & (np.hypot(yy-py, xx-px_)*PX < 400); src_kind = "osm+auto" if src_s.any() else "auto"
    src = src_t | src_s
    sy, sx = (np.array(ndi.center_of_mass(src)) if src.any() else (H/2, H/2)); rs = np.hypot(yy-sy, xx-sx)*PX
    away = rs > 900
    rows = []
    for i in range(n):
        pt = attached(B[i], src_t) if src_t.any() else np.zeros((H, H), bool)
        ps = attached(B[i], src_s) if src_s.any() else np.zeros((H, H), bool)
        plume = pt | ps; area = plume.sum()*PX*PX/1e6
        border = bool(plume[0].any() or plume[-1].any() or plume[:, 0].any() or plume[:, -1].any())
        best, bestd = 0.0, 0
        if area > 0 and np.isfinite(d["saz"][i]):
            az = np.radians(float(d["saz"][i]) + 180); dark = (AL[i] < DARK) & ~plume
            for dd in range(3, 41, 2):
                sh = (ndi.shift(plume.astype("float32"), (-np.cos(az)*dd, np.sin(az)*dd), order=0) > 0.5) & ~plume
                s = (dark & sh).sum()/max(sh.sum(), 1)
                if s > best: best, bestd = s, dd
        rows.append(dict(plant=pid, scene=str(d["id"][i]), t=str(d["t"][i]), cc_tile=float(d["cc"][i]), sza=float(d["sza"][i]), chip_clear_scl=float(clear_frac[i]), snow_frac=float(snow[i].mean()),
            plume_km2=area, plume_tower_km2=pt.sum()*PX*PX/1e6, plume_stack_km2=ps.sum()*PX*PX/1e6, plume_extent_m=float(rs[plume].max()) if area > 0 else 0.0, plume_border=border,
            plume_mean_anom=float(A[i][plume].mean()) if area > 0 else 0.0, src_anom=float(A[i][src].mean()) if src.any() else 0.0, src_bright_frac=float(B[i][src].mean()) if src.any() else 0.0,
            src_anom_max=float(A[i][src].max()) if src.any() else 0.0, scl_cloud_away=float((cloudy[i] & away & ~plume).sum()/away.sum()), bright_away=float((B[i] & away & ~plume).sum()/away.sum()),
            dark_away=float(((AL[i] < DARK) & away).sum()/away.sum()), shadow_score=float(best), shadow_dist_m=bestd*PX, src_kind=src_kind, n_towers=int(ndi.label(src_t)[1]), n_stacks=int(ndi.label(src_s)[1]), idx=i))
    return pd.DataFrame(rows), dict(src_t=src_t, src_s=src_s, A=A)

if __name__ == "__main__":
    plants = pd.read_csv(sys.argv[2]); plants[plants.columns[0]] = plants[plants.columns[0]].astype(str); plants = plants.set_index(plants.columns[0])
    tw = pd.read_csv(sys.argv[3]); tw["plant"] = tw.plant.astype(str); out = []
    for p in sorted(glob.glob(sys.argv[1] + "/*.npz")):
        pid = os.path.basename(p)[:-4]
        df, aux = plant_features(p, plants.loc[pid] if pid in plants.index else None, tw[tw.plant == pid]); out.append(df)
        print(pid, len(df), df.src_kind.iloc[0], "towers", df.n_towers.iloc[0], "stacks", df.n_stacks.iloc[0], flush=True)
    pd.concat(out).to_csv(sys.argv[4], index=False)
