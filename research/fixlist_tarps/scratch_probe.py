import time, rasterio, planetary_computer as pc
from pystac_client import Client
from rasterio.windows import from_bounds
from rasterio.warp import transform_bounds
cat = Client.open("https://planetarycomputer.microsoft.com/api/stac/v1", modifier=pc.sign_inplace)
bbox=[-93.45,30.10,-93.10,30.33]
items=list(cat.search(collections=["naip"],bbox=bbox,max_items=1000).items())
import collections
c=collections.Counter(i.properties["naip:year"] for i in items); print(c)
for yr in ["2019","2021","2023"]:
    it=[i for i in items if i.properties["naip:year"]==yr and i.bbox[0]<-93.2<i.bbox[2] and i.bbox[1]<30.21<i.bbox[3]][0]
    href=it.assets["image"].href
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR"):
        with rasterio.open(href) as ds:
            print(yr,it.id,it.datetime.date(),ds.crs,ds.res,ds.shape,ds.count,ds.overviews(1),ds.profile.get("compress"),ds.block_shapes[0])
            b=transform_bounds(4326,ds.crs,-93.205,30.205,-93.195,30.213)
            t=time.time(); a=ds.read(window=from_bounds(*b,ds.transform)); print(" full",a.shape,round(time.time()-t,1),"s")
