"""Own-extraction check: water area of GERD reservoir (Ethiopia) from Sentinel-2 SCL COG overviews, anonymous Earth Search."""
import time, numpy as np, rasterio
from rasterio.warp import transform_bounds
from rasterio.windows import from_bounds
from pystac_client import Client
cat=Client.open("https://earth-search.aws.element84.com/v1")
bbox=[35.0,10.5,35.45,11.25]
for dt in ["2020-03-01/2020-05-31","2025-11-01/2026-02-28"]:
    t=time.time()
    items=sorted(cat.search(collections=["sentinel-2-l2a"],bbox=bbox,datetime=dt,query={"eo:cloud_cover":{"lt":5}},max_items=40).items(),key=lambda i:i.properties["eo:cloud_cover"])
    tiles={}
    for it in items: tiles.setdefault(it.properties.get("grid:code"),it)
    print(dt,len(items),"scenes; tiles:",list(tiles), f"search {time.time()-t:.1f}s")
    for code,it in tiles.items():
        t=time.time()
        with rasterio.Env(AWS_NO_SIGN_REQUEST="YES"):
            with rasterio.open(it.assets["scl"].href) as ds:
                b=transform_bounds("EPSG:4326",ds.crs,*bbox)
                w=from_bounds(*b,ds.transform).intersection(rasterio.windows.Window(0,0,ds.width,ds.height))
                a=ds.read(1,window=w,out_shape=(int(w.height//4),int(w.width//4)))  # 80 m via overview
        print(f"  {code} {it.datetime.date()} cloud={it.properties['eo:cloud_cover']:.1f}% water={np.sum(a==6)*80*80/1e6:7.1f} km2  read {time.time()-t:.1f}s")
