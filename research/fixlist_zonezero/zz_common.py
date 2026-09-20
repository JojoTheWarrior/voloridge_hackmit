"""Shared helpers: MS footprints by bbox (streamed, subset on the fly), NAIP STAC search, feature extraction."""
import math, gzip, json, io, os, time
import numpy as np, pandas as pd, geopandas as gpd, requests
from shapely.geometry import shape, box

LINKS = "data/ms_dataset_links.csv"

def quadkey(lat, lon, z=9):
    x = int((lon + 180) / 360 * 2**z)
    s = math.sin(math.radians(lat))
    y = int((0.5 - math.log((1 + s) / (1 - s)) / (4 * math.pi)) * 2**z)
    return "".join(str(((x >> i) & 1) + 2 * ((y >> i) & 1)) for i in range(z - 1, -1, -1))

def quadkeys_for_bbox(bbox, z=9):
    w, s, e, n = bbox
    qs = set()
    for la in np.linspace(s, n, 12):
        for lo in np.linspace(w, e, 12):
            qs.add(quadkey(la, lo, z))
    return qs

def ms_footprints(bbox, keep=None):
    """Stream MS Global ML Building Footprints tiles covering bbox; keep only buildings intersecting bbox
    (and, if keep is a prepared geometry / callable, only those passing keep(geom)). Nothing is cached to disk."""
    links = pd.read_csv(LINKS, dtype=str)
    links = links[(links.Location == "UnitedStates") & links.QuadKey.isin(quadkeys_for_bbox(bbox))]
    bb = box(*bbox)
    rows = []
    for url in links.Url:
        for attempt in range(4):
            try:
                raw = gzip.decompress(requests.get(url, timeout=600).content).decode(); break
            except Exception as e:
                print("retry", e); time.sleep(5)
        for line in raw.splitlines():
            f = json.loads(line)
            c = f["geometry"]["coordinates"][0][0]
            if not (bbox[0] - 0.01 <= c[0] <= bbox[2] + 0.01 and bbox[1] - 0.01 <= c[1] <= bbox[3] + 0.01):
                continue
            g = shape(f["geometry"])
            if g.intersects(bb) and (keep is None or keep(g)):
                p = f.get("properties", {})
                rows.append({"geometry": g, "ms_height": p.get("height"), "ms_conf": p.get("confidence")})
        del raw
    return gpd.GeoDataFrame(rows, geometry="geometry", crs=4326)
