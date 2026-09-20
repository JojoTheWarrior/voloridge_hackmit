import requests, pandas as pd, time
plants=pd.read_csv("plants.csv"); out=[]
for p in plants.itertuples():
    r=requests.get("https://archive-api.open-meteo.com/v1/archive",params=dict(latitude=p.latitude,longitude=p.longitude,start_date="2025-04-01",end_date="2025-09-30",
        hourly="wind_speed_100m,wind_direction_100m,wind_speed_10m,temperature_2m,relative_humidity_2m,cloud_cover",wind_speed_unit="ms",timezone="UTC"),timeout=120)
    print(p.plant_id_eia,r.status_code)
    d=pd.DataFrame(r.json()["hourly"]); d["plant_id_eia"]=p.plant_id_eia; out.append(d); time.sleep(1)
w=pd.concat(out); w["time"]=pd.to_datetime(w["time"]); w.to_parquet("wind.parquet"); print(w.describe().T)
