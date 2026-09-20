"""ISD airport visibility as a PM2.5 sensor: Delhi Palam (ISD 42181) vs OpenAQ IGI Airport T3 + Sirifort."""
import numpy as np, pandas as pd
from oaq import hourly
fr=[]
for y in (2019,2020):
    d=pd.read_csv(f"data/isd/DEL_{y}.csv",usecols=["DATE","VIS","TMP","DEW"],low_memory=False); d["t"]=pd.to_datetime(d.DATE).dt.floor("h")
    v=d.VIS.str.split(",",expand=True)[0].astype(float); d["vis"]=np.where(v>=999999,np.nan,v)
    for c in ("TMP","DEW"): x=d[c].str.split(",",expand=True)[0].astype(float); d[c.lower()]=np.where(x==9999,np.nan,x/10)
    fr.append(d.groupby("t")[["vis","tmp","dew"]].mean())
w=pd.concat(fr); w["rh"]=100*np.exp(17.625*w.dew/(243.04+w.dew))/np.exp(17.625*w.tmp/(243.04+w.tmp)); w["ext"]=3912/w.vis.clip(lower=50)  # Koschmieder, 1/Mm-ish
for loc,name in [(5650,"IGI Airport T3"),(5586,"Sirifort")]:
    pm=pd.concat([hourly(loc,y,range(1,13),"pm25") for y in (2019,2020)])
    df=pd.concat([w,pm.rename("pm")],axis=1).dropna(); df=df[(df.pm>0)&(df.pm<1000)]
    dd=df.resample("D").mean().dropna()
    dry=df[df.rh<70]
    tr,te=dd[:"2019-12-31"],dd["2020-01-01":]
    if len(tr)>30 and len(te)>30:
        b=np.polyfit(np.log(tr.ext),np.log(tr.pm),1); pred=np.exp(np.polyval(b,np.log(te.ext))); r2=1-((te.pm-pred)**2).sum()/((te.pm-te.pm.mean())**2).sum()
    else: r2=np.nan
    print(f"{name}: hourly n={len(df)} r(log ext, log PM2.5)={np.log(df.ext).corr(np.log(df.pm)):.2f} (RH<70%: {np.log(dry.ext).corr(np.log(dry.pm)):.2f}, n={len(dry)}); daily r={np.log(dd.ext).corr(np.log(dd.pm)):.2f} n={len(dd)}; train-2019 -> test-2020 daily R2={r2:.2f}")
