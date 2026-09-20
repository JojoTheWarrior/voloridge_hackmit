import requests
bbox=[-108.52,36.66,-108.44,36.72]; dt="2025-06-01T00:00:00Z/2025-08-31T23:59:59Z"
es="https://earth-search.aws.element84.com/v1"
for c,k in [("sentinel-2-l2a","red"),("sentinel-2-c1-l2a","red"),("landsat-c2-l2","lwir11")]:
    r=requests.post(es+"/search",json={"collections":[c],"bbox":bbox,"datetime":dt,"limit":100},timeout=60)
    f=r.json().get("features",[]); print(c,r.status_code,len(f))
    if f:
        it=f[0]; h=it["assets"][k]["href"]; print(" ",it["id"],it["properties"].get("eo:cloud_cover"),h)
        if h.startswith("s3://"): print("  s3 href only (requester pays?)"); continue
        g=requests.get(h,headers={"Range":"bytes=0-1023"}); print("  anon GET",g.status_code,g.headers.get("Content-Range"))
        import numpy as np
        cc=[x["properties"].get("eo:cloud_cover") for x in f]; print("  n scenes 3 months:",len(f),"cloud<20%:",sum(1 for x in cc if x is not None and x<20))
r=requests.post("https://stac.dataspace.copernicus.eu/v1/search",json={"collections":["sentinel-2-l2a"],"bbox":bbox,"datetime":"2025-07-01T00:00:00Z/2025-07-10T00:00:00Z","limit":2},timeout=60)
print("CDSE",r.status_code)
if r.ok:
    a=r.json()["features"][0]["assets"]; 
    for k in list(a)[:3]:
        print(k,a[k]["href"][:140], a[k].get("alternate",{}).keys() if isinstance(a[k].get("alternate"),dict) else "")
    for k in a:
        alt=a[k].get("alternate",{})
        h=alt.get("https",{}).get("href") if alt else None
        if h:
            g=requests.get(h,headers={"Range":"bytes=0-1023"},timeout=60); print(" CDSE https asset anon GET:",g.status_code, g.text[:120]); break
