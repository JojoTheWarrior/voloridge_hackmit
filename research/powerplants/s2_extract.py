"""Pull 4km Sentinel-2 L2A chips (keyless COGs via Element84 Earth Search) around plants with natural-draft cooling towers."""
import os, sys, requests, numpy as np, pandas as pd, rasterio
from rasterio.windows import Window
from rasterio.warp import transform
from concurrent.futures import ThreadPoolExecutor
os.environ.update(AWS_NO_SIGN_REQUEST="YES", GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif")
ES = "https://earth-search.aws.element84.com/v1/search"
plants = pd.read_csv(sys.argv[1]); DT = sys.argv[2]; out = sys.argv[3]
HALF = 200  # px at 10 m

def items(p):
    body = {"collections":["sentinel-2-l2a"], "intersects":{"type":"Point","coordinates":[p.longitude,p.latitude]}, "datetime":DT,
            "query":{"eo:cloud_cover":{"lt":70}}, "limit":100}
    feats=[]; 
    while True:
        r = requests.post(ES, json=body, timeout=60).json(); feats += r["features"]
        nxt = [l for l in r.get("links",[]) if l["rel"]=="next"]
        if not nxt: break
        body = nxt[0]["body"]
    return feats

def chip(args):
    p, it = args
    try:
        bands=[]
        for k in ["blue","green","red"]:
            with rasterio.open(it["assets"][k]["href"]) as ds:
                xs, ys = transform("EPSG:4326", ds.crs, [p.longitude], [p.latitude]); r, c = ds.index(xs[0], ys[0])
                if r-HALF<0 or c-HALF<0 or r+HALF>ds.height or c+HALF>ds.width: return None
                bands.append(ds.read(1, window=Window(c-HALF, r-HALF, 2*HALF, 2*HALF)))
        a = np.stack(bands).astype("float32")
        if (a==0).mean() > 0.05: return None
        return dict(plant=p.plant_id_eia, id=it["id"], t=it["properties"]["datetime"], cc=it["properties"]["eo:cloud_cover"],
                    rgb=np.clip(a/10000*255/0.6, 0, 255).astype("uint8"))   # 0.6 reflectance -> 255
    except Exception as e:
        print("ERR", it["id"], e, flush=True); return None

jobs = []
for p in plants.itertuples():
    f = items(p); print(p.plant_name_eia, len(f), "items", flush=True); jobs += [(p, it) for it in f]
with ThreadPoolExecutor(16) as ex: recs = [r for r in ex.map(chip, jobs) if r]
np.savez_compressed(out, plant=[r["plant"] for r in recs], id=[r["id"] for r in recs], t=[r["t"] for r in recs], cc=[r["cc"] for r in recs], rgb=np.stack([r["rgb"] for r in recs]))
print("saved", len(recs))
