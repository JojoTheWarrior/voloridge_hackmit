"""Shared site definitions and helpers for the S2/S1 strike-detection sub-study."""
import os
from pathlib import Path

os.environ.setdefault("AWS_NO_SIGN_REQUEST", "YES")
os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
os.environ.setdefault("GDAL_HTTP_MAX_RETRY", "4")
os.environ.setdefault("GDAL_HTTP_RETRY_DELAY", "2")
os.environ.setdefault("CPL_VSIL_CURL_ALLOWED_EXTENSIONS", ".tif,.tiff")

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "s2s1_out"
CACHE = OUT / "cache"
CACHE.mkdir(parents=True, exist_ok=True)

EARTH_SEARCH = "https://earth-search.aws.element84.com/v1"
PC_STAC = "https://planetarycomputer.microsoft.com/api/stac/v1"

# bbox = (lon_min, lat_min, lon_max, lat_max)
SITES = {
    "ras_laffan": dict(name="Ras Laffan, Qatar", bbox=(51.48, 25.85, 51.62, 25.95)),
    "south_pars": dict(name="South Pars / Asaluyeh, Iran", bbox=(52.55, 27.45, 52.70, 27.56)),
    "fujairah": dict(name="Fujairah oil terminal, UAE", bbox=(56.30, 25.12, 56.40, 25.24)),
    "tehran": dict(name="Tehran refinery (Rey), Iran", bbox=(51.38, 35.50, 51.48, 35.58)),
}
T0, T1 = "2026-01-15", "2026-04-30"
WAR_START = "2026-02-28"

SITE_EPSG = {"ras_laffan": "EPSG:32639", "south_pars": "EPSG:32639", "fujairah": "EPSG:32640", "tehran": "EPSG:32639"}


def site_grid(site):
    """Site bbox in its UTM zone, snapped to the 20 m Sentinel-2 grid: (left, bottom, right, top)."""
    from rasterio.warp import transform_bounds
    l, b, r, t = transform_bounds("EPSG:4326", SITE_EPSG[site], *SITES[site]["bbox"])
    snap = lambda v: round(v / 20) * 20
    return snap(l), snap(b), snap(r), snap(t)
