import requests, json
bbox=[-108.52,36.66,-108.44,36.72]  # Four Corners
def search(api, coll, extra=None, dt="2025-06-01/2025-08-31"):
    body={"collections":[coll],"bbox":bbox,"datetime":dt,"limit":100}
    if extra: body.update(extra)
    r=requests.post(api+"/search",json=body,timeout=60); 
    print(api.split('/')[2], coll, r.status_code, end=" ")
    if r.ok:
        f=r.json()["features"]; print(len(f),"items"); return f
    print(r.text[:200]); return []
es="https://earth-search.aws.element84.com/v1"; pc="https://planetarycomputer.microsoft.com/api/stac/v1"
f=search(es,"sentinel-2-l2a")
if f:
    it=f[0]; print(it["id"], it["properties"].get("eo:cloud_cover")); h=it["assets"]["red"]["href"]; print(h)
    r=requests.get(h,headers={"Range":"bytes=0-1023"}); print(" anon range GET:",r.status_code)
f=search(es,"landsat-c2-l2")
if f:
    it=f[0]; print(it["id"], list(it["assets"])[:12]); h=it["assets"]["lwir11"]["href"]; print(h)
    alt=it["assets"]["lwir11"].get("alternate"); print(" alt:",alt)
    r=requests.get(h,headers={"Range":"bytes=0-1023"}); print(" anon range GET:",r.status_code)
for c in ["sentinel-2-l2a","landsat-c2-l2","sentinel-5p-l2-netcdf","sentinel-3-slstr-frp-l2-netcdf"]:
    f=search(pc,c)
    if f:
        it=f[0]; k=[a for a in it["assets"]][:8]; print(" ",it["id"],k)
        a = it["assets"].get("lwir11") or it["assets"].get("B04") or it["assets"].get("no2") or list(it["assets"].values())[0]
        h=a["href"]; print("  href",h[:120])
        r=requests.get(h,headers={"Range":"bytes=0-1023"}); print("  unsigned GET:",r.status_code)
        s=requests.get("https://planetarycomputer.microsoft.com/api/sas/v1/sign",params={"href":h},timeout=60); print("  anon sign:",s.status_code)
        if s.ok:
            r=requests.get(s.json()["href"],headers={"Range":"bytes=0-1023"}); print("  signed GET:",r.status_code, r.headers.get("Content-Range"))
# CDSE
r=requests.post("https://stac.dataspace.copernicus.eu/v1/search",json={"collections":["sentinel-2-l2a"],"bbox":bbox,"datetime":"2025-07-01/2025-07-10","limit":2},timeout=60)
print("CDSE stac",r.status_code, len(r.json().get("features",[])) if r.ok else r.text[:200])
if r.ok and r.json()["features"]:
    a=r.json()["features"][0]["assets"]; k=list(a)[0]; print(k, a[k]["href"][:150])
    h=a[k]["href"]
    if h.startswith("http"):
        g=requests.get(h,headers={"Range":"bytes=0-1023"},timeout=60,allow_redirects=True); print(" CDSE anon asset GET:",g.status_code)
