"""Sentinel-2 L2A chips (keyless COGs, Element84 Earth Search) at 20 m: TCI true-colour (8-bit) + SCL, 4 km box around each plant.
usage: s2_extract2.py plants.csv START END outdir [id_col name_col]   -> outdir/{id}.npz"""
import os, sys, requests, time, numpy as np, pandas as pd, rasterio
from rasterio.windows import from_bounds
from rasterio.warp import transform
from rasterio.enums import Resampling
from concurrent.futures import ThreadPoolExecutor
os.environ.update(AWS_NO_SIGN_REQUEST="YES", GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif",
                  GDAL_HTTP_MAX_RETRY="4", GDAL_HTTP_RETRY_DELAY="2", GDAL_HTTP_MULTIPLEX="YES", VSI_CACHE="FALSE")
ES = "https://earth-search.aws.element84.com/v1/search"
plants = pd.read_csv(sys.argv[1]); START, END, OUT = sys.argv[2], sys.argv[3], sys.argv[4]
IDC = sys.argv[5] if len(sys.argv) > 5 else "plant_id_eia"
HALF_M, N = 2000, 200

def items(p):
    body = {"collections": ["sentinel-2-l2a"], "intersects": {"type": "Point", "coordinates": [p.longitude, p.latitude]},
            "datetime": f"{START}T00:00:00Z/{END}T23:59:59Z", "query": {"eo:cloud_cover": {"lt": 90}}, "limit": 200}
    feats = []
    while True:
        for a in range(4):
            try: r = requests.post(ES, json=body, timeout=90).json(); break
            except Exception: time.sleep(5)
        feats += r["features"]; nxt = [l for l in r.get("links", []) if l["rel"] == "next"]
        if not nxt: break
        body = nxt[0]["body"]
    best = {}   # one item per acquisition day: newest processing wins
    for f in feats:
        k = f["properties"]["datetime"][:10]
        if k not in best or f["properties"].get("created", "") > best[k]["properties"].get("created", ""): best[k] = f
    return list(best.values())

def chip(args):
    p, it = args
    try:
        out = {}
        for k in ["visual", "scl"]:
            with rasterio.open(it["assets"][k]["href"]) as ds:
                xs, ys = transform("EPSG:4326", ds.crs, [p.longitude], [p.latitude]); x, y = xs[0], ys[0]
                b = ds.bounds
                if x-HALF_M < b.left or x+HALF_M > b.right or y-HALF_M < b.bottom or y+HALF_M > b.top: return None
                w = from_bounds(x-HALF_M, y-HALF_M, x+HALF_M, y+HALF_M, ds.transform)
                out[k] = ds.read(window=w, out_shape=(ds.count, N, N), resampling=Resampling.nearest if k == "scl" else Resampling.average)
        scl = out["scl"][0].astype("uint8")
        if (scl == 0).mean() > 0.02: return None
        pr = it["properties"]
        return dict(id=it["id"], t=pr["datetime"], cc=pr["eo:cloud_cover"], sza=90-pr.get("view:sun_elevation", np.nan),
                    saz=pr.get("view:sun_azimuth", np.nan), img=out["visual"].astype("uint8"), scl=scl)
    except Exception as e:
        print("ERR", it["id"], str(e)[:100], flush=True); return None

def do_plant(p):
    out = f"{OUT}/{getattr(p, IDC)}.npz"
    if os.path.exists(out): return
    t = time.time(); its = items(p)
    with ThreadPoolExecutor(int(os.environ.get("THREADS", 24))) as ex: recs = [r for r in ex.map(chip, [(p, i) for i in its]) if r]
    if not recs: print(getattr(p, IDC), "no chips", flush=True); return
    recs.sort(key=lambda r: r["t"])
    np.savez_compressed(out, id=[r["id"] for r in recs], t=[r["t"] for r in recs], cc=[r["cc"] for r in recs], sza=[r["sza"] for r in recs], saz=[r["saz"] for r in recs],
                        img=np.stack([r["img"] for r in recs]), scl=np.stack([r["scl"] for r in recs]))
    print(getattr(p, IDC), len(its), "items ->", len(recs), "chips", round(time.time()-t), "s", flush=True)

os.makedirs(OUT, exist_ok=True)
with ThreadPoolExecutor(int(os.environ.get("PLANTS_PAR", 3))) as ex: list(ex.map(do_plant, list(plants.itertuples())))
print("ALLDONE")
