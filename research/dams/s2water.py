"""Own water-area extraction from Sentinel-2 L2A (Element84 Earth Search, anonymous COG reads) for reservoirs GWW lacks.

Per month: pick the clearest acquisition date whose tiles cover the bbox, read B03/B11/SCL overviews (~80 m), classify water
as MNDWI > 0 and SCL not cloud/shadow/snow, mosaic tiles on a common lat/lon grid, count water area. Cloudy pixels are
filled from a running "last known state" so a partly cloudy scene does not read as a smaller lake.
"""
import json

import numpy as np
import rasterio
from pystac_client import Client
from rasterio.enums import Resampling
from rasterio.transform import from_bounds as tf_from_bounds
from rasterio.warp import reproject

from common import CACHE

STAC = "https://earth-search.aws.element84.com/v1"
CLOUDY = (0, 1, 3, 8, 9, 10, 11)  # nodata, saturated, shadow, cloud med/high, cirrus, snow


def grid(bbox, res_deg):
    w, s, e, n = bbox
    nx, ny = int(round((e - w) / res_deg)), int(round((n - s) / res_deg))
    return tf_from_bounds(w, s, e, n, nx, ny), (ny, nx)


def read_to_grid(href, transform, shape, resampling, overview_level):
    """Warp one COG onto the target grid, reading from its ~80 m overview rather than full resolution."""
    dst = np.zeros(shape, np.float32)
    with rasterio.Env(AWS_NO_SIGN_REQUEST="YES", GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR"):
        with rasterio.open(href, overview_level=overview_level) as ds:
            reproject(rasterio.band(ds, 1), dst, dst_transform=transform, dst_crs="EPSG:4326", resampling=resampling)
    return dst


def search(bbox, start, end, max_cloud=40):
    cat = Client.open(STAC)
    items = list(cat.search(collections=["sentinel-2-l2a"], bbox=bbox, datetime=f"{start}/{end}",
                            query={"eo:cloud_cover": {"lt": max_cloud}}, max_items=5000).items())
    by_date = {}
    for it in items:
        by_date.setdefault(str(it.datetime.date()), []).append(it)
    return by_date


def scene_masks(items, transform, shape):
    """Return (water, valid) boolean grids for one acquisition date, mosaicking its tiles."""
    water = np.zeros(shape, bool)
    valid = np.zeros(shape, bool)
    for it in items:
        a = it.assets
        green = read_to_grid(a["green"].href, transform, shape, Resampling.bilinear, 2)
        swir = read_to_grid(a["swir16"].href, transform, shape, Resampling.bilinear, 1)
        scl = read_to_grid(a["scl"].href, transform, shape, Resampling.nearest, 1)
        ok = (green > 0) & (swir > 0) & ~np.isin(scl, CLOUDY)
        mndwi = (green - swir) / np.maximum(green + swir, 1)
        water |= ok & (mndwi > 0)
        valid |= ok
    return water, valid


def monthly_series(name, bbox, start, end, res_deg=0.00075, max_cloud=40):
    """One clearest scene-date per month. Returns list of dicts and caches JSON + per-month water masks (npz)."""
    out_fn = CACHE / "s2" / f"{name}.json"
    out_fn.parent.mkdir(exist_ok=True)
    done = json.loads(out_fn.read_text()) if out_fn.exists() else {}
    transform, shape = grid(bbox, res_deg)
    lat_mid = (bbox[1] + bbox[3]) / 2
    px_km2 = (res_deg * 111.32) ** 2 * np.cos(np.radians(lat_mid))
    by_date = search(bbox, start, end, max_cloud)
    months = {}
    for d, its in by_date.items():
        months.setdefault(d[:7], []).append((np.mean([i.properties["eo:cloud_cover"] for i in its]), -len(its), d))
    state = None
    for ym in sorted(months):
        if ym in done:
            if (CACHE / "s2" / f"{name}_{ym}.npz").exists():
                state = np.load(CACHE / "s2" / f"{name}_{ym}.npz")["state"]
            continue
        cloud, ntiles, d = sorted(months[ym])[0]
        try:
            water, valid = scene_masks(by_date[d], transform, shape)
        except Exception as e:  # a missing/corrupt COG should not kill the series
            print(name, ym, "read failed", repr(e)[:120], flush=True)
            continue
        if state is None:
            state = np.zeros(shape, bool)
        state = np.where(valid, water, state)
        rec = {"date": d, "scene_cloud": float(cloud), "valid_frac": float(valid.mean()),
               "water_km2_scene": float(water.sum() * px_km2), "water_km2_filled": float(state.sum() * px_km2)}
        done[ym] = rec
        np.savez_compressed(CACHE / "s2" / f"{name}_{ym}.npz", state=state)
        out_fn.write_text(json.dumps(done))
        print(name, ym, rec, flush=True)
    return done
