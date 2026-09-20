"""Same crude upwind/downwind NO2 enhancement, applied to Gulf/Iran plants (no labels). Are they even detectable?"""
import numpy as np, pandas as pd, requests, time, os
plants = pd.read_csv("plants_foreign.csv").set_index("plant_id_eia")
if not os.path.exists("wind_foreign.parquet"):
    out=[]
    for pid,p in plants.iterrows():
        r=requests.get("https://archive-api.open-meteo.com/v1/archive",params=dict(latitude=p.latitude,longitude=p.longitude,start_date="2025-05-15",end_date="2025-07-15",hourly="wind_speed_100m,wind_direction_100m",wind_speed_unit="ms",timezone="UTC"),timeout=120)
        d=pd.DataFrame(r.json()["hourly"]); d["plant_id_eia"]=pid; out.append(d); time.sleep(1)
    w=pd.concat(out); w["time"]=pd.to_datetime(w["time"]); w.to_parquet("wind_foreign.parquet")
wind=pd.read_parquet("wind_foreign.parquet").set_index(["plant_id_eia","time"]).sort_index()
d=np.load("s5p_foreign.npz"); no2,qa,pid,stamp=d["no2"]*1e6,d["qa"],d["plant"],d["stamp"]
if qa.max()>1.5: qa=qa/100
n=no2.shape[1]; c=n//2; px=0.035; rows=[]
for i in range(len(pid)):
    p=plants.loc[pid[i]]; lat,lon=p.latitude,p.longitude
    th=(pd.Timestamp(stamp[i][:8])+pd.Timedelta(hours=13.5-lon/15)).floor("h")
    jj,ii=np.meshgrid(np.arange(n)-c,np.arange(n)-c); x=jj*px*111.2*np.cos(np.radians(lat)); y=-ii*px*111.2; r=np.hypot(x,y)
    a=np.where(qa[i]>=0.75,no2[i],np.nan)
    if np.isfinite(a[r<60]).mean()<0.85: continue
    w=wind.loc[(pid[i],th)]; wd=np.radians(w.wind_direction_100m); ux,uy=-np.sin(wd),-np.cos(wd)
    dw=x*ux+y*uy; cw=-x*uy+y*ux
    enh=np.nanmean(a[(dw>-5)&(dw<45)&(np.abs(cw)<12)])-np.nanmedian(a[(dw<-10)&(dw>-60)&(np.abs(cw)<40)])
    rows.append(dict(name=p.plant_name_eia,day=th.floor("D"),enh=enh,bg=np.nanmedian(a[(r>50)&(r<100)]),ws=w.wind_speed_100m))
df=pd.DataFrame(rows).groupby(["name","day"],as_index=False).mean(numeric_only=True); df.to_csv("s5p_foreign.csv",index=False)
war=(df.day>="2025-06-13")&(df.day<="2025-06-24")
g=df.groupby("name").agg(n_days=("enh","size"),enh_mean=("enh","mean"),enh_sd=("enh","std"),bg=("bg","mean"))
g["t_stat"]=g.enh_mean/(g.enh_sd/np.sqrt(g.n_days))
g["enh_war"]=df[war].groupby("name").enh.mean(); g["n_war"]=df[war].groupby("name").enh.size(); g["enh_nonwar"]=df[~war].groupby("name").enh.mean()
pd.set_option("display.width",250); print(g.round(1).to_string()); print("of 62 possible days")
