"""Country-month SNPP night flare FRP 2012-2024 (FIRMS archive) [+2025-26 from GIBS for Gulf countries], persistent-flare cells only."""
import pandas as pd, numpy as np, sys, os
from flarelib import *
C=['Iraq','Libya','Algeria','Nigeria','Venezuela','Kazakhstan','Iran','Saudi_Arabia','Qatar','Kuwait','United_Arab_Emirates','Oman','Egypt','Angola','Turkmenistan','Syria','Yemen','Russian_Federation']
GULF=['Iraq','Iran','Saudi_Arabia','Qatar','Kuwait','United_Arab_Emirates','Oman','Turkmenistan','Syria','Yemen']
g=pd.read_parquet('data/hotspots_gulf.parquet'); g=g[(g.SATELLITE=='N')&(g.DAYNIGHT=='N')].rename(columns={'LATITUDE':'lat','LONGITUDE':'lon','FRP':'frp'}); g=add_cells(g)
daily={}; meta=[]
for c in C:
    fs=[y for y in range(2012,2025) if os.path.exists(f'data/firms_archive/viirs-snpp_{y}_{c}.csv') and os.path.getsize(f'data/firms_archive/viirs-snpp_{y}_{c}.csv')>1000]
    if len(fs)<13: print('skip (incomplete)',c,len(fs)); continue
    h=load_firms(c,range(2012,2025)); h=h[h.dn=='N']; h=add_cells(h)
    st=h.groupby(['cx','cy']).date.agg(['nunique','min','max']); keep=st[(st['nunique']>=24)&((st['max']-st['min']).dt.days>=180)].index
    hh=h.set_index(['cx','cy']); hh=hh[hh.index.isin(keep)]
    d=hh.groupby('date').frp.sum()
    if c in GULF:
        gg=g.set_index(['cx','cy']); gg=gg[gg.index.isin(keep)]; d=pd.concat([d,gg.groupby('date').frp.sum()['2025-01-01':]])
    daily[c]=d; meta.append({'country':c,'night_dets':len(h),'flare_cells':len(keep),'share_dets_in_flare_cells':round(len(hh)/len(h),3)}); print(meta[-1],flush=True)
D=pd.DataFrame(daily)
# SNPP outage days: no detections in ANY country -> drop; otherwise missing = 0
alld=pd.date_range(D.index.min(),D.index.max()); D=D.reindex(alld); outage=D.isna().all(axis=1); print('outage days',int(outage.sum()))
D=D[~outage].fillna(0.0); D=D[~D.index.isin(bad_days('N'))]; print('days kept',len(D))
for c in D: 
    if c not in GULF: D.loc['2025-01-01':,c]=np.nan
D.to_csv('data/intl_daily_flare_frp.csv')
M=D.groupby(D.index.to_period('M')).mean(); M.index=M.index.to_timestamp(); cnt=D.groupby(D.index.to_period('M')).size(); M=M[cnt.values>=15]
M.to_csv('data/intl_monthly_flare_frp.csv'); P90=D.groupby(D.index.to_period('M')).quantile(.9); P90.index=P90.index.to_timestamp(); P90.to_csv('data/intl_monthly_flare_frp_p90.csv')
pd.DataFrame(meta).to_csv('data/intl_flare_cell_meta.csv',index=False)
