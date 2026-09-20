"""Does the satellite reservoir deficit lead GDELT load-shedding coverage? Kariba/Zambia + Zimbabwe, 2017-2026."""
import io, time, requests, numpy as np, pandas as pd
B="https://api.globalwaterwatch.earth"
def gdelt(q):
    for _ in range(5):
        r=requests.get("https://api.gdeltproject.org/api/v2/doc/doc",params={"query":q,"mode":"timelinevolraw","format":"csv","startdatetime":"20170101000000","enddatetime":"20260901000000"},timeout=120)
        if r.status_code==200 and r.text.strip().lower().startswith(("date","﻿date")): break
        print("gdelt retry",r.status_code,r.text[:100]); time.sleep(8)
    d=pd.read_csv(io.StringIO(r.text.lstrip("﻿"))); d['Date']=pd.to_datetime(d['Date'])
    p=d.pivot_table(index='Date',columns='Series',values='Value',aggfunc='sum'); print(q,'->',list(p.columns),len(p)); return p
p=gdelt('("load shedding" OR loadshedding OR "power cuts" OR blackout) (zambia OR zimbabwe OR kariba)')
art=p.filter(like='Article').iloc[:,0]; tot=p.filter(like='Total').iloc[:,0] if p.filter(like='Total').shape[1] else None
news=(art/tot*1e6 if tot is not None else art).resample('MS').mean().rename('news')
raw=requests.get(f"{B}/reservoir/92438/ts/surface_water_area",params={"start":"2008-01-01T00:00:00","stop":"2026-09-01T00:00:00"},timeout=120).json()
s=pd.Series({pd.Timestamp(x['t']):x['value']/1e6 for x in raw}).sort_index(); s=s[s>0.5*s.quantile(0.9)]
a=s.resample('MS').median().interpolate(limit=3)
clim=a.groupby(a.index.month).transform('mean'); deficit=(-(a-clim)/clim*100).rename('deficit_pct')
df=pd.concat([deficit,news],axis=1).dropna(); df['lnews']=np.log1p(df.news)
print(df.resample('YS').mean().round(2).to_string())
print("\nlag k = news shifted back k months (k>0: deficit LEADS news)")
for k in range(-6,13):
    print(f"k={k:+3d}  r={df.deficit_pct.corr(df.lnews.shift(-k)):.2f}  n={df.lnews.shift(-k).notna().sum()}")
df.to_csv('data/kariba_leadlag.csv')
