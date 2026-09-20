"""Signal check: Landsat surface-temp anomaly of water near Pilgrim NPP (shut down 2019-05-31), before vs after."""
import numpy as np, rasterio, planetary_computer as pc
from rasterio.warp import transform
from rasterio.windows import from_bounds
from pystac_client import Client
cat=Client.open("https://planetarycomputer.microsoft.com/api/stac/v1",modifier=pc.sign_inplace)
lon,lat=-70.578,41.944
def chip(href,x,y,r):
    with rasterio.open(href) as ds:
        return ds.read(1,window=from_bounds(x-r,y-r,x+r,y+r,ds.transform)), ds.crs
for label,dt in [("ON  (2017-18)","2017-01-01/2018-12-31"),("OFF (2020-21)","2020-01-01/2021-12-31")]:
    items=list(cat.search(collections=["landsat-c2-l2"],intersects={"type":"Point","coordinates":[lon,lat]},datetime=dt,query={"eo:cloud_cover":{"lt":10},"platform":{"in":["landsat-8"]}}).items())[:7]
    for it in items:
        with rasterio.open(it.assets["lwir11"].href) as ds:
            xs,ys=transform("EPSG:4326",ds.crs,[lon],[lat]); x,y=xs[0],ys[0]
            st=ds.read(1,window=from_bounds(x-3000,y-3000,x+3000,y+3000,ds.transform)).astype(float)
        with rasterio.open(it.assets["qa_pixel"].href) as ds:
            qa=ds.read(1,window=from_bounds(x-3000,y-3000,x+3000,y+3000,ds.transform))
        water=((qa>>7)&1==1)&(st>0)
        if water.sum()<500: print(label,it.id[:25],"few water px"); continue
        t=st[water]*0.00341802+149.0-273.15
        print(f"{label} {it.datetime.date()} water_px={water.sum():5d} median={np.median(t):5.1f}C  p99-median={np.percentile(t,99)-np.median(t):4.1f}C  max-median={t.max()-np.median(t):4.1f}C")
