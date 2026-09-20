import requests
B="https://api.globalwaterwatch.earth"
sites={"Xiaowan (Yunnan)":(100.05,24.75),"Nuozhadu (Yunnan)":(100.40,22.75),"Toktogul (Kyrgyz)":(72.9,41.8),"Akosombo/Volta":(0.1,7.0),"Cahora Bassa":(31.8,-15.7),"Mazar (Ecuador)":(-78.63,-2.58),"Itezhi-Tezhi (Zambia)":(26.0,-15.75),"Three Gorges":(110.6,30.95),"Ataturk (Turkey)":(38.5,37.6),"Mosul (Iraq)":(42.7,36.7),"Sobradinho (Brazil)":(-41.8,-9.6),"Furnas (Brazil)":(-45.9,-20.9)}
for n,(x,y) in sites.items():
    fs=requests.post(B+"/reservoir/geometry",json={"type":"Point","coordinates":[x,y]},timeout=60).json().get("features",[])
    if not fs: print(f"{n:24s} NOT FOUND at point"); continue
    rid=fs[0]["id"]
    ts=requests.get(f"{B}/reservoir/{rid}/ts/surface_water_area_monthly",params={"start":"2015-01-01T00:00:00","stop":"2026-09-19T00:00:00"},timeout=60).json()
    v=[d['value']/1e6 for d in ts]
    print(f"{n:24s} id={rid} months={len(v)} last={ts[-1]['t'][:7] if ts else None} min/max km2={min(v):.0f}/{max(v):.0f}" if v else f"{n} id={rid} empty")
