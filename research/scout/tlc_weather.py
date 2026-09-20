import fsspec, pyarrow.parquet as pq, pandas as pd, numpy as np
fr=[]
for m in range(1,13):
    with fsspec.open(f"https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2024-{m:02d}.parquet","rb",block_size=4*2**20) as f:
        t=pq.ParquetFile(f).read(columns=["tpep_pickup_datetime","trip_distance","tpep_dropoff_datetime"]).to_pandas()
    t=t[(t.tpep_pickup_datetime.dt.year==2024)&(t.tpep_pickup_datetime.dt.month==m)]
    t["h"]=t.tpep_pickup_datetime.dt.floor("h"); dur=(t.tpep_dropoff_datetime-t.tpep_pickup_datetime).dt.total_seconds()/3600
    t["mph"]=np.where((dur>0.03)&(dur<3)&(t.trip_distance>0.3)&(t.trip_distance<60),t.trip_distance/dur,np.nan)
    fr.append(t.groupby("h").agg(trips=("mph","size"),mph=("mph","median")))
y=pd.concat(fr); y.to_csv("data/tlc_hourly_2024.csv")
d=pd.read_csv("data/isd/LGA_2024.csv",usecols=["DATE","REPORT_TYPE","AA1","TMP"],low_memory=False); d=d[d.REPORT_TYPE.str.strip()=="FM-15"]
d["h"]=(pd.to_datetime(d.DATE)-pd.Timedelta(hours=5)).dt.floor("h")   # UTC -> approx local (EST)
a=d.AA1.fillna("01,0000,9,9").str.split(",",expand=True); d["mm"]=np.where(a[0].astype(float)==1,a[1].astype(float)/10,np.nan); d.loc[d.mm>=999,"mm"]=np.nan
w=d.groupby("h").mm.max()
df=pd.concat([y,w],axis=1).dropna(subset=["trips","mm"]); df["how"]=df.index.dayofweek*24+df.index.hour; df["mon"]=df.index.month
for c in ("trips","mph"): df[c+"_rel"]=df[c]/df.groupby(["how","mon"])[c].transform("mean")-1
for lab,mask in [("dry",df.mm==0),("light rain 0-2mm/h",(df.mm>0)&(df.mm<2)),("heavy rain >=2mm/h",df.mm>=2)]:
    s=df[mask]; print(f"{lab:22s} n_hours={len(s):5d}  trips vs same hour-of-week/month norm {s.trips_rel.mean():+.1%} (se {s.trips_rel.std()/np.sqrt(len(s)):.1%})   median speed {s.mph_rel.mean():+.1%} (se {s.mph_rel.std()/np.sqrt(len(s)):.1%})")
print(f"hourly r(rain mm, speed residual)={df.mm.corr(df.mph_rel):.2f}, r(rain mm, trips residual)={df.mm.corr(df.trips_rel):.2f}, n={len(df)}")
