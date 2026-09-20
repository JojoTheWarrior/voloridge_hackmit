"""Keyless night-lights: GIBS WMS PNG of VIIRS DNB at-sensor radiance, inverted through the published colormap."""
import requests, io, re, numpy as np, pandas as pd
from PIL import Image
from concurrent.futures import ThreadPoolExecutor
WMS="https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi"
def colormap(layer):
    x=requests.get(f"https://gibs.earthdata.nasa.gov/colormaps/v1.3/VIIRS_DayNightBand_At_Sensor_Radiance.xml",timeout=60).text
    ents=re.findall(r'<ColorMapEntry rgb="(\d+),(\d+),(\d+)"[^>]*?value="\[([^\],]+),([^\]\)]+)[\]\)]"',x)
    lut={}
    for r,g,b,lo,hi in ents:
        try: lut[(int(r),int(g),int(b))]=(float(lo)+float(hi))/2 if float(hi)<1e5 else float(lo)
        except ValueError: pass
    return lut
def grab(layer,date,bbox,lut,px=0.004):
    w,s,e,n=bbox; W=int((e-w)/px); H=int((n-s)/px)
    r=requests.get(WMS,params=dict(SERVICE='WMS',REQUEST='GetMap',VERSION='1.1.1',LAYERS=layer,STYLES='',FORMAT='image/png',TRANSPARENT='true',SRS='EPSG:4326',BBOX=f"{w},{s},{e},{n}",WIDTH=W,HEIGHT=H,TIME=date),timeout=90)
    if r.status_code!=200 or 'image' not in r.headers.get('content-type',''): return None
    im=np.array(Image.open(io.BytesIO(r.content)).convert('RGBA'))
    val=np.full(im.shape[:2],np.nan)
    rgb=im[...,:3].reshape(-1,3); a=im[...,3].ravel()
    keys=(rgb[:,0].astype(int)<<16)|(rgb[:,1].astype(int)<<8)|rgb[:,2]
    lk={(k[0]<<16)|(k[1]<<8)|k[2]:v for k,v in lut.items()}
    v=np.array([lk.get(k,np.nan) for k in keys]); v[a==0]=np.nan
    return v.reshape(im.shape[:2])
def series(layer,dates,bbox,workers=8):
    lut=colormap(layer); print(layer,'colormap entries',len(lut))
    def job(d):
        try: v=grab(layer,d,bbox,lut)
        except Exception: v=None
        if v is None: return d,np.nan,np.nan,np.nan,np.nan
        return d,np.nanmean(v),np.nanmedian(v),np.nanmean(v>=38.2),np.nanmean(v>5)
    with ThreadPoolExecutor(workers) as ex: rows=list(ex.map(job,dates))
    return pd.DataFrame(rows,columns=['date','mean','median','frac_sat','frac_gt5']).set_index('date')
if __name__=="__main__":
    import sys
    d=[x.strftime('%Y-%m-%d') for x in pd.date_range('2022-09-15','2023-01-31')]
    k=series('VIIRS_SNPP_DayNightBand_At_Sensor_Radiance',d,(30.30,50.33,30.75,50.56)); k.to_csv('data/dnb_kyiv_2022.csv'); print(k.describe())
    d=[x.strftime('%Y-%m-%d') for x in pd.date_range('2026-01-15','2026-04-30')]
    t=series('VIIRS_NOAA20_DayNightBand_At_Sensor_Radiance',d,(51.20,35.60,51.60,35.80)); t.to_csv('data/dnb_tehran_2026.csv'); print(t.describe())
