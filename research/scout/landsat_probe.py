import time, numpy as np, rasterio, planetary_computer as pc
from rasterio.warp import transform
from rasterio.windows import from_bounds
from pystac_client import Client
t=time.time()
cat=Client.open("https://planetarycomputer.microsoft.com/api/stac/v1",modifier=pc.sign_inplace)
lon,lat=-97.785,32.298  # Comanche Peak NPP, Squaw Creek Reservoir cooling lake
s=cat.search(collections=["landsat-c2-l2"],intersects={"type":"Point","coordinates":[lon,lat]},datetime="2019-01-01/2019-12-31",query={"eo:cloud_cover":{"lt":20},"platform":{"in":["landsat-8","landsat-9"]}})
items=list(s.items()); print(len(items),"scenes 2019 <20% cloud; search",round(time.time()-t,1),"s")
it=items[0]; print(it.id, list(it.assets)[:12])
t=time.time()
with rasterio.open(it.assets["lwir11"].href) as ds:
    xs,ys=transform("EPSG:4326",ds.crs,[lon],[lat]); x,y=xs[0],ys[0]
    w=from_bounds(x-4000,y-4000,x+4000,y+4000,ds.transform)
    a=ds.read(1,window=w).astype(float)
    k=a*0.00341802+149.0-273.15; k[a==0]=np.nan
print("chip",a.shape,"read",round(time.time()-t,1),"s  ST degC min/med/max",np.nanmin(k).round(1),np.nanmedian(k).round(1),np.nanmax(k).round(1))
