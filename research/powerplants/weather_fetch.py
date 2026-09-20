"""Keyless ERA5-based hourly weather at plant coordinates from Open-Meteo archive (resumable, waits out rate limits).
usage: weather_fetch.py plants.csv START END out.parquet [vars] [sleep_s]"""
import requests, pandas as pd, time, sys, os, hashlib
plants=pd.read_csv(sys.argv[1]); start,end,out=sys.argv[2:5]
V=sys.argv[5] if len(sys.argv)>5 else "temperature_2m,relative_humidity_2m,dew_point_2m,wind_speed_10m,wind_speed_100m,wind_direction_100m,cloud_cover"
slp=float(sys.argv[6]) if len(sys.argv)>6 else 8
idc=plants.columns[0]; frames=[]; os.makedirs("wx_cache",exist_ok=True)
for p in plants.itertuples():
    key=hashlib.md5(f"{p.latitude}{p.longitude}{start}{end}{V}".encode()).hexdigest()[:12]; cf=f"wx_cache/{key}.parquet"
    if not os.path.exists(cf):
        while True:
            r=requests.get("https://archive-api.open-meteo.com/v1/archive",params=dict(latitude=p.latitude,longitude=p.longitude,start_date=start,end_date=end,hourly=V,wind_speed_unit="ms",timezone="UTC"),timeout=180)
            if r.status_code==200 and "hourly" in r.json(): break
            print(getattr(p,idc),r.status_code,r.text[:100],flush=True); time.sleep(300 if "Hourly" in r.text else 65)
        pd.DataFrame(r.json()["hourly"]).to_parquet(cf); time.sleep(slp)
    d=pd.read_parquet(cf); d["plant"]=str(getattr(p,idc)); frames.append(d); print(getattr(p,idc),len(d),flush=True)
w=pd.concat(frames); w["time"]=pd.to_datetime(w["time"]); w.to_parquet(out); print("done",len(w))
