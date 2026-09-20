"""Load cached Sentinel-2 site stacks and derive per-scene QA (valid fraction, SCL cloud fraction)."""
import json
import numpy as np, pandas as pd
from s2s1_common import *

CLOUD_SCL = (3, 8, 9, 10)  # shadow, cloud medium, cloud high, thin cirrus
REFL = ["swir22", "swir16", "nir08", "red", "green", "blue"]


def load_site(site, bands=REFL):
    """Return (index DataFrame, dict of float32 reflectance stacks [t,y,x], scl stack), one scene per date.

    Scenes lacking any of `bands` (the SWIR-only pre-war baseline has no visible bands) are skipped.
    """
    rows, data = [], []
    for f in sorted(CACHE.glob(f"s2_{site}_*.npz")):
        if f.name.endswith(".part.npz"):
            continue
        z = np.load(f)
        if not set(bands) <= set(z.files):
            continue
        m = json.loads(str(z["meta"]))
        # baseline >= 04.00 DNs carry a +1000 offset unless earth-search already removed it
        off = 0 if m["boa_offset_applied"] else 1000
        b12 = z["swir22"]
        valid = b12 > 0
        scl = z["scl"]
        rows.append(dict(id=m["id"], dt=pd.Timestamp(m["datetime"]), tile=m["tile"], valid=valid.mean(),
                         cloud=np.isin(scl, CLOUD_SCL)[valid].mean() if valid.any() else 1.0))
        data.append({**{b: np.clip(z[b].astype("float32") - off, 0, None) for b in bands}, "scl": z["scl"]})
        rows[-1]["boa_offset_applied"] = bool(m["boa_offset_applied"])
    idx = pd.DataFrame(rows)
    idx["date"] = idx.dt.dt.strftime("%Y-%m-%d")
    # one scene per date: most valid pixels, then the latest reprocessing
    keep = idx.sort_values(["date", "valid", "id"]).groupby("date").tail(1).index
    keep = [i for i in keep if idx.valid[i] > 0.98]
    idx = idx.loc[keep].sort_values("dt")
    order = idx.index.to_list()
    stacks = {b: np.stack([data[i][b] for i in order]) / 1e4 for b in bands}
    scl = np.stack([data[i]["scl"] for i in order])
    idx = idx.reset_index(drop=True)
    # Sentinel-2 relative orbits differ in overpass time by minutes; bucket them to keep pairs same-geometry
    idx["tod_min"] = idx.dt.dt.hour * 60 + idx.dt.dt.minute
    idx["orbit_grp"] = (idx.tod_min / 10).round().astype(int)
    return idx, stacks, scl


def pix2lonlat(site, rows, cols, res=20):
    from rasterio.warp import transform
    l, b, r, t = site_grid(site)
    xs = l + (np.asarray(cols) + 0.5) * res
    ys = t - (np.asarray(rows) + 0.5) * res
    lon, lat = transform(SITE_EPSG[site], "EPSG:4326", xs, ys)
    return np.array(lon), np.array(lat)


def lonlat2pix(site, lon, lat, res=20):
    from rasterio.warp import transform
    l, b, r, t = site_grid(site)
    xs, ys = transform("EPSG:4326", SITE_EPSG[site], np.atleast_1d(lon), np.atleast_1d(lat))
    return (t - np.array(ys)) / res - 0.5, (np.array(xs) - l) / res - 0.5
