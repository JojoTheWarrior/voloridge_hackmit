"""Windowed COG reads of every Sentinel-2 L2A scene over each site (20 m grid), cached as npz."""
import sys, json
from concurrent.futures import ThreadPoolExecutor
import numpy as np, rasterio
from rasterio.windows import from_bounds
from rasterio.enums import Resampling
from pystac_client import Client
from s2s1_common import *

BANDS = ["swir22", "swir16", "nir08", "red", "green", "blue", "scl"]
SWIR_BANDS = ["swir22", "swir16", "nir08", "scl"]

def read_band(href, bounds, shape, nearest):
    with rasterio.open(href) as ds:
        win = from_bounds(*bounds, transform=ds.transform)
        return ds.read(1, window=win, out_shape=shape, boundless=True, fill_value=0,
                       resampling=Resampling.nearest if nearest else Resampling.average)

def fetch_item(site, item, bands):
    out = CACHE / f"s2_{site}_{item.id}.npz"
    if out.exists():
        return out.name, "cached"
    epsg = item.properties.get("proj:code") or f"EPSG:{item.properties['proj:epsg']}"
    assert epsg == SITE_EPSG[site], (epsg, site)
    bounds = site_grid(site)
    shape = (int((bounds[3] - bounds[1]) / 20), int((bounds[2] - bounds[0]) / 20))
    arrs = {}
    for b in bands:
        arrs[b] = read_band(item.assets[b].href, bounds, shape, nearest=(b == "scl"))
    meta = dict(id=item.id, datetime=item.properties["datetime"], epsg=epsg, bounds=bounds,
                boa_offset_applied=item.properties.get("earthsearch:boa_offset_applied"),
                baseline=item.properties.get("s2:processing_baseline"),
                tile=item.properties.get("grid:code"),
                scene_cloud=item.properties.get("eo:cloud_cover"))
    tmp = out.with_suffix(".part.npz")
    np.savez_compressed(tmp, meta=json.dumps(meta), **arrs)
    tmp.replace(out)
    return out.name, "ok"

def main(sites, t0=T0, t1=T1, bands=BANDS):
    c = Client.open(EARTH_SEARCH)
    jobs = []
    for s in sites:
        items = list(c.search(collections=["sentinel-2-l2a"], bbox=SITES[s]["bbox"],
                              datetime=f"{t0}/{t1}").items())
        jobs += [(s, i, bands) for i in items]
    def run(j):
        try:
            return fetch_item(*j)
        except Exception as e:
            return j[1].id, f"FAIL {type(e).__name__}: {e}"
    with ThreadPoolExecutor(24) as ex:
        for name, st in ex.map(run, jobs):
            print(name, st, flush=True)

if __name__ == "__main__":
    # usage: s2s1_fetch_s2.py [t0 t1 [swir]]  -- "swir" skips the visible bands (hot-pixel baseline only)
    a = sys.argv[1:]
    main(list(SITES), *(a[:2] or (T0, T1)), bands=SWIR_BANDS if "swir" in a else BANDS)
