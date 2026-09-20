import pandas as pd, numpy as np
pd.set_option('display.width',250)
CELL=0.005
def novel_series(p,base_end,min_frp=0):
    p=p.copy(); p['cx']=(p.lon/CELL).round().astype(int); p['cy']=(p.lat/CELL).round().astype(int)
    # a cell and its 8 neighbours lit on >=2 baseline days => "known heat source"
    b=p[p.date<=base_end].groupby(['cx','cy']).date.nunique(); known=set()
    for (cx,cy),n in b.items():
        if n>=2:
            for dx in(-1,0,1):
                for dy in(-1,0,1): known.add((cx+dx,cy+dy))
    p['novel']=[(a,b_) not in known for a,b_ in zip(p.cx,p.cy)]
    return p
# 1) Abqaiq 2019
df=pd.concat([pd.read_csv(f'data/firms_archive/viirs-{s}_2019_Saudi_Arabia.csv') for s in('snpp','jpss1')]).rename(columns={'latitude':'lat','longitude':'lon','frp':'FRP'})
df['date']=pd.to_datetime(df.acq_date)
a=df[df.lat.between(25.88,25.99)&df.lon.between(49.62,49.76)]
a=novel_series(a,pd.Timestamp('2019-09-13'))
d=a[a.novel].groupby('date').FRP.agg(['size','sum']); print('Abqaiq 2019 novel-cell detections after baseline:'); print(d['2019-09-01':'2019-10-15'])
# 2) war window assets
p=pd.read_parquet('data/asset_hotspots.parquet').rename(columns={'LATITUDE':'lat','LONGITUDE':'lon'})
out=[]
for asset,g in p.groupby('asset'):
    g=novel_series(g,pd.Timestamp('2026-02-27'))
    w=g[g.novel&(g.date>='2026-02-28')]
    dd=w.groupby('date').FRP.agg(n='size',frp='sum')
    for dt,r in dd.iterrows(): out.append((asset,dt.date(),int(r.n),round(r.frp,1)))
o=pd.DataFrame(out,columns=['asset','date','n_novel','novel_frp']); o.to_csv('data/novel_detections.csv',index=False)
print('\nasset-days with novel hotspots since war start:',len(o),' assets:',o.asset.nunique())
big=o[(o.novel_frp>=20)|(o.n_novel>=3)].sort_values('date'); print(big.to_string(index=False))
