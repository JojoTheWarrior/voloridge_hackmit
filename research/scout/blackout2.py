import io, time, requests, numpy as np, pandas as pd
B="https://api.globalwaterwatch.earth"
def gdelt(q):
    for _ in range(8):
        time.sleep(6)
        r=requests.get("https://api.gdeltproject.org/api/v2/doc/doc",params={"query":q,"mode":"timelinevolraw","format":"csv","startdatetime":"20170101000000","enddatetime":"20260901000000"},timeout=120)
        if r.status_code==200 and "Date" in r.text[:10]: break
    d=pd.read_csv(io.StringIO(r.text.lstrip("﻿"))); d['Date']=pd.to_datetime(d['Date'])
    p=d.pivot_table(index='Date',columns='Series',values='Value',aggfunc='sum')
    return (p['Article Count']/p['Total Monitored Articles']*1e6).resample('MS').mean().rename('news')
def deficit(gid):
    raw=requests.get(f"{B}/reservoir/{gid}/ts/surface_water_area",params={"start":"2008-01-01T00:00:00","stop":"2026-09-01T00:00:00"},timeout=120).json()
    s=pd.Series({pd.Timestamp(x['t']):x['value']/1e6 for x in raw}).sort_index(); s=s[s>0.5*s.quantile(0.9)]
    a=s.resample('MS').median().interpolate(limit=3); clim=a.groupby(a.index.month).transform('mean'); return (-(a-clim)/clim*100).rename('deficit')
for name,gid,q in [("Itezhi-Tezhi/Zambia","90229",'("load shedding" OR loadshedding) zambia'),("Kariba/Zambia-only query","92438",'("load shedding" OR loadshedding) zambia')]:
    df=pd.concat([deficit(gid),gdelt(q)],axis=1).dropna(); df['ln']=np.log1p(df.news)
    print(name,"n=",len(df)); print(df.resample('YS').mean().round(1).T.to_string())
    print("  lag(months, +ve = deficit leads): "+"  ".join(f"{k:+d}:{df.deficit.corr(df.ln.shift(-k)):.2f}" for k in range(-6,13,2)))
    if gid=="90229": print(df.loc["2023-09":"2025-06",["deficit","news"]].round(1).T.to_string())
