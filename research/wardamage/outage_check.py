"""Per-satellite outage calendar. SNPP 2012-2024 from FIRMS archive night+day detection counts summed over 16 countries; 2025-26 (all three satellites) from the Gulf GIBS pull. A day is 'outage' if count==0, 'degraded' if < 25% of the centred 31-day rolling median."""
import pandas as pd, numpy as np, glob, os
from flarelib import load_firms
C=['Iraq','Libya','Algeria','Nigeria','Venezuela','Kazakhstan','Iran','Saudi_Arabia','Qatar','Kuwait','United_Arab_Emirates','Oman','Egypt','Turkmenistan','Syria','Yemen']
cnt=None
for c in C:
    h=load_firms(c,range(2012,2025)); s=h.groupby('date').size(); cnt=s if cnt is None else cnt.add(s,fill_value=0)
idx=pd.date_range('2012-01-20','2024-12-31'); cnt=cnt.reindex(idx,fill_value=0)
g=pd.read_parquet('data/hotspots_gulf.parquet'); gs=g.groupby(['date','SATELLITE']).size().unstack(fill_value=0).reindex(pd.date_range('2025-01-01','2026-09-19'),fill_value=0)
def flag(s):
    med=s.rolling(31,center=True,min_periods=10).median(); return pd.DataFrame({'count':s,'rollmed':med,'outage':s==0,'degraded':(s<0.25*med)&(s>0)})
A=flag(cnt); A['sat']='N'; parts=[A]
for sat in gs: 
    x=flag(gs[sat]); x['sat']=sat; parts.append(x)
O=pd.concat(parts); O.index.name='date'; O.to_csv('data/satellite_outage_calendar.csv')
for sat,x in O.groupby('sat'):
    bad=x[x.outage|x.degraded]; 
    # collapse to windows
    d=bad.index.to_series(); grp=(d.diff().dt.days>1).cumsum(); w=d.groupby(grp).agg(['min','max','size'])
    print(sat,'bad days:',len(bad),'| windows >=3 days:'); print(w[w['size']>=3].to_string(header=False))
