import pandas as pd, numpy as np, glob
fs=sorted(glob.glob('data/gibs_gulf/*.parquet'))
dfs=[]
for f in fs:
    d=pd.read_parquet(f)
    if len(d): dfs.append(d)
h=pd.concat(dfs,ignore_index=True).drop_duplicates(['LATITUDE','LONGITUDE','ACQ_DATE','ACQ_TIME','SATELLITE'])
h['date']=pd.to_datetime(h.ACQ_DATE)
h.to_parquet('data/hotspots_gulf.parquet')
print(len(h)); print(h.groupby('SATELLITE').date.agg(['min','max','count']))
assets=pd.read_csv('assets.csv')
R=5.0
rows=[]
lat=h.LATITUDE.values; lon=h.LONGITUDE.values
for _,a in assets.iterrows():
    d=6371*2*np.arcsin(np.sqrt(np.sin(np.radians(lat-a.lat)/2)**2+np.cos(np.radians(a.lat))*np.cos(np.radians(lat))*np.sin(np.radians(lon-a.lon)/2)**2))
    s=h[d<=R].copy(); s['asset']=a['name']; s['dist_km']=d[d<=R]; rows.append(s)
p=pd.concat(rows); p.to_parquet('data/asset_hotspots.parquet'); print(len(p))
