"""Keyless per-cell night clear-sky confidence (NOAA-20 VIIRS cloud mask) from GIBS WMS, sampled on a 0.02 deg grid over the Gulf bbox."""
import requests, io, re, numpy as np, pandas as pd, sys
from PIL import Image
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
WMS="https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi"; LAYER='VIIRS_SNPP_Clear_Sky_Confidence_Night'
BBOX=(-104.1,46.9,-101.0,49.0); RES=0.02; W=int(round((BBOX[2]-BBOX[0])/RES)); H=int(round((BBOX[3]-BBOX[1])/RES))
def lut():
    x=requests.get('https://gibs.earthdata.nasa.gov/colormaps/v1.3/VIIRS_Clear_Sky_Confidence.xml',timeout=60).text
    t=np.full(1<<24,np.nan,dtype='float32')
    for r,g,b,lo,hi in re.findall(r'rgb="(\d+),(\d+),(\d+)" transparent="false" value="\[([\d.]+),([\d.]+)[\)\]]"',x): t[(int(r)<<16)|(int(g)<<8)|int(b)]=(float(lo)+float(hi))/2
    return t
T=lut(); out=Path('data/cloud_bakken'); out.mkdir(exist_ok=True,parents=True)
def job(d):
    f=out/f'{d}.npy'
    if f.exists(): return
    for a in range(4):
        try:
            r=requests.get(WMS,params=dict(SERVICE='WMS',REQUEST='GetMap',VERSION='1.1.1',LAYERS=LAYER,STYLES='',FORMAT='image/png',TRANSPARENT='true',SRS='EPSG:4326',BBOX="%s,%s,%s,%s"%BBOX,WIDTH=W,HEIGHT=H,TIME=d),timeout=180)
            if r.status_code==200 and 'image' in r.headers.get('content-type',''):
                im=np.array(Image.open(io.BytesIO(r.content)).convert('RGBA')).astype(np.uint32)
                v=T[(im[...,0]<<16)|(im[...,1]<<8)|im[...,2]]; v[im[...,3]==0]=np.nan
                np.save(f,(np.nan_to_num(v,nan=-0.01)*100).round().astype(np.int8)); return   # -1 = no data
        except Exception as e: pass
    print('FAIL',d,flush=True)
dates=[x.strftime('%Y-%m-%d') for x in pd.date_range(sys.argv[1],sys.argv[2])]
with ThreadPoolExecutor(10) as ex: list(ex.map(job,dates))
print('done')
