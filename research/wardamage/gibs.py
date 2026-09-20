"""Keyless VIIRS/MODIS active-fire points from NASA GIBS vector tiles (no MAP_KEY, no Earthdata login)."""
import requests, mapbox_vector_tile as mvt, pandas as pd, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
BASE = "https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/{layer}/default/{date}/{tms}/{z}/{row}/{col}.mvt"
S = requests.Session()

def tiles_for_bbox(w, s, e, n, z):
    span = 288 / 2**z
    c0, c1 = int((w + 180) // span), int((e + 180) // span)
    r0, r1 = int((90 - n) // span), int((90 - s) // span)
    return [(r, c) for r in range(r0, r1 + 1) for c in range(c0, c1 + 1)]

def fetch_tile(layer, date, z, row, col, tms="500m"):
    u = BASE.format(layer=layer, date=date, tms=tms, z=z, row=row, col=col)
    for a in range(4):
        try:
            r = S.get(u, timeout=60)
            if r.status_code == 200:
                if not r.content: return []
                d = mvt.decode(r.content)
                return [f["properties"] for v in d.values() for f in v["features"]]
            if r.status_code in (400, 404): return []
        except Exception:
            pass
        time.sleep(1 + a)
    return None

def fetch_day(layer, date, bbox, z=4, tms="500m"):
    rows = []
    for (r, c) in tiles_for_bbox(*bbox, z):
        p = fetch_tile(layer, date, z, r, c, tms)
        if p is None: raise RuntimeError(f"fail {layer} {date} {r} {c}")
        rows += p
    df = pd.DataFrame(rows)
    if len(df):
        w, s, e, n = bbox
        df = df[(df.LONGITUDE.between(w, e)) & (df.LATITUDE.between(s, n))]
    return df

def fetch_range(layer, dates, bbox, out, z=4, tms="500m", workers=8):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    def job(d):
        f = out / f"{layer}_{d}.parquet"
        if f.exists(): return
        try:
            df = fetch_day(layer, d, bbox, z, tms)
            df.to_parquet(f) if len(df) else pd.DataFrame().to_parquet(f)
        except Exception as ex:
            print("ERR", d, ex)
    with ThreadPoolExecutor(workers) as ex: list(ex.map(job, dates))
