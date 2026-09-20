import pandas as pd, numpy as np
from oaq import daily
W=range(1,7)
rows={}
for loc,name in [(1122,"Jersey City (Holland Tunnel side) NO2","no2"),(857,"Fort Lee (GW Bridge, untolled zone) NO2","no2"),(631,"Queens PM2.5","pm25")] and [(1122,"JerseyCity NO2"),(857,"FortLee NO2"),(1496,"Bayonne NO2"),(971,"Elizabeth NJTP NO2")]:
    a=daily(loc,2024,W,"no2"); b=daily(loc,2025,W,"no2")
    if len(a)<60 or len(b)<60: print(name,"insufficient",len(a),len(b)); continue
    a,b=a["2024-01-05":"2024-06-30"],b["2025-01-05":"2025-06-30"]
    # paired by day-of-year for a bootstrap CI
    x=pd.concat([a.groupby(a.index.dayofyear).mean(),b.groupby(b.index.dayofyear).mean()],axis=1).dropna(); x.columns=["y24","y25"]
    bs=[ (s.y25.mean()/s.y24.mean()-1) for s in (x.sample(len(x),replace=True,random_state=i) for i in range(500))]
    print(f"{name}: 2024 {a.mean():.4f} -> 2025 {b.mean():.4f}  change {b.mean()/a.mean()-1:+.1%}  (95% CI {np.percentile(bs,2.5):+.1%}..{np.percentile(bs,97.5):+.1%}, n_days={len(x)})")
