"""Cooling towers + chimneys near each plant from OpenStreetMap via keyless Overpass mirrors (batched). usage: osm_towers.py plants.csv out.csv [radius_m]"""
import requests, pandas as pd, numpy as np, sys, time
plants=pd.read_csv(sys.argv[1]); out=sys.argv[2]; R=int(sys.argv[3]) if len(sys.argv)>3 else 2200
idc=plants.columns[0]; rows=[]
EPS=["https://overpass.private.coffee/api/interpreter","https://maps.mail.ru/osm/tools/overpass/api/interpreter"]
for k in range(0,len(plants),12):
    sub=plants.iloc[k:k+12]; parts=""
    for p in sub.itertuples():
        a=f"(around:{R},{p.latitude},{p.longitude});"
        parts+=f'nwr["man_made"="cooling_tower"]{a}nwr["tower:type"="cooling"]{a}nwr["building"="cooling_tower"]{a}nwr["man_made"="chimney"]{a}'
    q=f"[out:json][timeout:180];({parts});out center tags;"
    for a in range(6):
        try:
            r=requests.post(EPS[a%2],data={"data":q},timeout=240,headers={"User-Agent":"Mozilla/5.0 (research script)"})
            if r.status_code==200: break
        except Exception as e: print("retry",e)
        time.sleep(15)
    for e in r.json().get("elements",[]):
        lat=e.get("lat") or e.get("center",{}).get("lat"); lon=e.get("lon") or e.get("center",{}).get("lon"); tg=e.get("tags",{})
        dist=np.hypot((sub.latitude-lat)*111,(sub.longitude-lon)*111*np.cos(np.radians(lat))); j=dist.values.argmin()
        kind="cooling_tower" if "cooling" in (tg.get("man_made","")+tg.get("tower:type","")+tg.get("building","")) else "chimney"
        rows.append(dict(plant=sub.iloc[j][idc],kind=kind,lat=lat,lon=lon,height=tg.get("height"),osm_type=e["type"],osm_id=e["id"]))
    print(k,len(rows),flush=True); time.sleep(3)
df=pd.DataFrame(rows).drop_duplicates(["osm_type","osm_id"]); df.to_csv(out,index=False)
print(df.groupby(["plant","kind"]).size().unstack(fill_value=0).reindex(plants[idc]).fillna(0).astype(int).to_string())
