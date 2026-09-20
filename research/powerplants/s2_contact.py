"""One recent low-cloud Sentinel-2 true-colour view per site, for hand-checking coordinates. usage: s2_contact.py plants.csv out.png half_m"""
import os, sys, requests, numpy as np, pandas as pd, rasterio, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from rasterio.windows import from_bounds
from rasterio.warp import transform
from concurrent.futures import ThreadPoolExecutor
os.environ.update(AWS_NO_SIGN_REQUEST="YES", GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif")
CC=float(sys.argv[5]) if len(sys.argv)>5 else 5
pl=pd.read_csv(sys.argv[1]); HALF=float(sys.argv[3]); DT=sys.argv[4] if len(sys.argv)>4 else "2025-08-01T00:00:00Z/2025-11-30T00:00:00Z"
def one(p):
    try:
        r=requests.post("https://earth-search.aws.element84.com/v1/search",json={"collections":["sentinel-2-l2a"],"intersects":{"type":"Point","coordinates":[p.longitude,p.latitude]},
          "datetime":DT,"query":{"eo:cloud_cover":{"lt":CC}},"limit":40,"sortby":[{"field":"properties.eo:cloud_cover","direction":"asc"}]},timeout=90).json()
        best=None; tried=0
        for it in r["features"]:
            with rasterio.open(it["assets"]["visual"]["href"]) as ds:
                xs,ys=transform("EPSG:4326",ds.crs,[p.longitude],[p.latitude]); x,y=xs[0],ys[0]; b=ds.bounds
                if x-HALF<b.left or x+HALF>b.right or y-HALF<b.bottom or y+HALF>b.top: continue
                a=ds.read(window=from_bounds(x-HALF,y-HALF,x+HALF,y+HALF,ds.transform),out_shape=(3,260,260))
                if (a==0).mean()<0.05:
                    cl=(a.min(0)>190).mean()
                    if best is None or cl<best[2]: best=(a, it["properties"]["datetime"][:10], cl)
                    tried+=1
                    if cl<0.03 or tried>=10: break
        if best: return best[0], best[1]
    except Exception as e: print("ERR",p[1],e)
    return None,None
with ThreadPoolExecutor(8) as ex: res=list(ex.map(one,list(pl.itertuples())))
n=len(pl); cols=7; rows=(n+cols-1)//cols; fig,ax=plt.subplots(rows,cols,figsize=(cols*2.6,rows*2.8))
for a in ax.ravel(): a.axis("off")
for a,p,(im,dt) in zip(ax.ravel(),pl.itertuples(),res):
    if im is not None: a.imshow(np.clip(im.transpose(1,2,0).astype(float)*1.3,0,255).astype("uint8")); a.plot(130,130,"r+",ms=10)
    a.set_title(f"{p[1]}\n{dt}",fontsize=7)
plt.tight_layout(); plt.savefig(sys.argv[2],dpi=75)
