"""Windowed reads of every Sentinel-1 RTC scene (VV, VH; gamma0 linear power) per site onto the 10 m site grid.

Planetary Computer blob storage is slow per connection from here, so parallelise per (item, polarisation).
"""
import sys, json
from concurrent.futures import ThreadPoolExecutor
import numpy as np, rasterio
from rasterio.vrt import WarpedVRT
from rasterio.windows import from_bounds
from rasterio.transform import from_origin
from rasterio.enums import Resampling
from pystac_client import Client
import planetary_computer as pc
from s2s1_common import *

os.environ.update(GDAL_HTTP_MULTIPLEX="YES", GDAL_HTTP_VERSION="2", GDAL_HTTP_MERGE_CONSECUTIVE_RANGES="YES")


def fetch(site, item, pol):
    out = CACHE / f"s1_{site}_{item.id}_{pol}.npz"
    if out.exists():
        return out.name, "cached"
    l, b, r, t = site_grid(site)
    w, h = int((r - l) / 10), int((t - b) / 10)
    with rasterio.open(item.assets[pol].href) as ds:
        if str(ds.crs) == SITE_EPSG[site]:
            arr = ds.read(1, window=from_bounds(l, b, r, t, transform=ds.transform), out_shape=(h, w),
                          boundless=True, fill_value=np.nan)
        else:
            with WarpedVRT(ds, crs=SITE_EPSG[site], transform=from_origin(l, t, 10, 10), width=w, height=h,
                           resampling=Resampling.bilinear) as vrt:
                arr = vrt.read(1)
    p = item.properties
    meta = dict(id=item.id, datetime=p["datetime"], orbit=p["sat:relative_orbit"], direction=p["sat:orbit_state"],
                platform=p["platform"], pol=pol, native_crs=str(ds.crs))
    tmp = out.with_suffix(".part.npz")
    np.savez_compressed(tmp, meta=json.dumps(meta), data=arr.astype("float32"))
    tmp.replace(out)
    return out.name, "ok"


def main(sites, pols, t0=T0, t1=T1):
    c = Client.open(PC_STAC, modifier=pc.sign_inplace)
    jobs = []
    for pol in pols:
        for s in sites:
            jobs += [(s, i, pol) for i in c.search(collections=["sentinel-1-rtc"], bbox=SITES[s]["bbox"],
                                                   datetime=f"{t0}/{t1}").items() if pol in i.assets]
    def run(j):
        try:
            return fetch(*j)
        except Exception as e:
            return f"{j[1].id}_{j[2]}", f"FAIL {type(e).__name__}: {e}"
    with ThreadPoolExecutor(64) as ex:
        for name, st in ex.map(run, jobs):
            print(name, st, flush=True)


if __name__ == "__main__":
    # usage: s2s1_fetch_s1.py [vv] [vh] [t0 t1]
    dates = [a for a in sys.argv[1:] if a[:2] == "20"]
    main(list(SITES), [a for a in sys.argv[1:] if a in ("vv", "vh")] or ["vv", "vh"], *dates)
