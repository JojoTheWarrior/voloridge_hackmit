import requests
B="https://api.globalwaterwatch.earth"
sites={"Xiaowan":(100.09,24.70),"Nuozhadu":(100.43,22.64),"Three Gorges":(110.9,30.85),"Sobradinho":(-41.5,-9.6),"Furnas":(-46.0,-20.8),"Mazar":(-78.63,-2.58),"Ataturk":(38.6,37.55),"GERD":(35.2,11.0),"Nurek":(69.5,38.4)}
for n,(x,y) in sites.items():
    d=0.25
    poly={"type":"Polygon","coordinates":[[[x-d,y-d],[x+d,y-d],[x+d,y+d],[x-d,y+d],[x-d,y-d]]]}
    fs=requests.post(B+"/reservoir/geometry",json=poly,timeout=90).json().get("features",[])
    out=[]
    for f in fs[:40]:
        p=f["properties"]; out.append((f["id"],p.get("name")))
    named=[o for o in out if o[1]]
    print(f"{n:14s} {len(fs)} reservoirs in box; named: {named[:6]}")
