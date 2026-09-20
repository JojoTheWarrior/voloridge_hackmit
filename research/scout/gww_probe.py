import requests, json, time
B="https://api.globalwaterwatch.earth"
print(requests.get(B+"/variables",timeout=30).text[:400])
sites={"Lake Mead/Hoover":(-114.60,36.13),"Lake Powell":(-111.30,37.05),"Guri (Venezuela)":(-62.85,7.45),"Kariba":(27.9,-16.9),"GERD (Ethiopia)":(35.15,11.10),"Nurek (Tajikistan)":(69.45,38.40)}
for n,(x,y) in sites.items():
    t=time.time()
    r=requests.post(B+"/reservoir/geometry",json={"type":"Point","coordinates":[x,y]},timeout=60)
    try:
        fs=r.json().get("features",[])
    except Exception: print(n,r.status_code,r.text[:200]); continue
    if not fs: print(n,"no reservoir at point",r.status_code); continue
    rid=fs[0]["id"]; props={k:v for k,v in fs[0]["properties"].items() if k!='geometry'}
    ts=requests.get(f"{B}/reservoir/{rid}/ts/surface_water_area",params={"start":"2000-01-01T00:00:00","stop":"2026-09-19T00:00:00"},timeout=60).json()
    v=[(d['t'][:10],round(d['value']/1e6,1)) for d in ts]
    print(f"{n}: id={rid} n={len(v)} first={v[:1]} last={v[-2:]} ({time.time()-t:.1f}s)", props.get('name'))
