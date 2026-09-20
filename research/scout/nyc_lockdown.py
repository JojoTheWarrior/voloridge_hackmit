import fsspec, pyarrow.parquet as pq, pandas as pd, numpy as np
from oaq import daily
def tlc(year, months):
    out=[]
    for m in months:
        with fsspec.open(f"https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_{year}-{m:02d}.parquet","rb",block_size=4*2**20) as f:
            t=pq.ParquetFile(f).read(columns=["tpep_pickup_datetime"]).to_pandas().iloc[:,0]
        t=t[(t.dt.year==year)&(t.dt.month==m)]; out.append(t.dt.floor("D").value_counts())
    return pd.concat(out).sort_index().rename("trips")
trips=tlc(2020,range(1,7)); trips.to_csv("data/tlc_daily_2020.csv")
res={}
for loc,name in [(857,"FortLee near-road (GW Bridge)"),(1122,"Jersey City")]:
    n20=daily(loc,2020,range(1,7),"no2"); n19=daily(loc,2019,range(1,7),"no2")
    df=pd.concat([trips,n20.rename("no2")],axis=1).dropna()
    pre,post=slice("2020-01-15","2020-03-07"),slice("2020-03-22","2020-04-30")
    d20=n20[post].mean()/n20[pre].mean()-1; n19.index=n19.index+pd.DateOffset(years=1); d19=n19[post].mean()/n19[pre].mean()-1
    wk=df.resample("W").mean()
    print(f"{name}: daily r(trips,NO2)={df.trips.corr(df.no2):.2f} n={len(df)}; weekly r={wk.trips.corr(wk.no2):.2f} n={len(wk)}; NO2 change lockdown vs pre: 2020 {d20:+.0%}, same calendar windows 2019 (placebo) {d19:+.0%}; DiD {d20-d19:+.0%}")
print(f"TLC yellow trips/day: pre {trips['2020-01-15':'2020-03-07'].mean():,.0f} -> lockdown {trips['2020-03-22':'2020-04-30'].mean():,.0f} ({trips['2020-03-22':'2020-04-30'].mean()/trips['2020-01-15':'2020-03-07'].mean()-1:+.0%})")
