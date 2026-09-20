"""Fetch named industrial OSM features per site (context for where reported strike targets sit)."""
import json, urllib.parse, urllib.request
from s2s1_common import *
for k, s in SITES.items():
    l, b, r, t = s["bbox"]
    bb = f"{b-0.01},{l-0.02},{t+0.01},{r+0.02}"
    q = (f'[out:json][timeout:80];(nwr["name"]["landuse"="industrial"]({bb});nwr["name"]["industrial"]({bb});'
         f'nwr["name"]["man_made"~"works|storage_tank"]({bb});nwr["man_made"="flare"]({bb}););out center tags 300;')
    for host in ["https://overpass.private.coffee/api/interpreter", "https://overpass-api.de/api/interpreter"]:
        try:
            req = urllib.request.Request(host + "?data=" + urllib.parse.quote(q), headers={"User-Agent": "s2s1-research/0.1"})
            d = json.load(urllib.request.urlopen(req, timeout=100))
            break
        except Exception as e:
            print(k, host, "fail", e); d = None
    if d is None: continue
    json.dump(d, open(OUT / f"osm_{k}.json", "w"))
    for e in d["elements"]:
        c = e.get("center", e); tg = e["tags"]
        print(k, round(c.get("lat", 0), 4), round(c.get("lon", 0), 4), tg.get("name"), "|", tg.get("name:en", ""), "|", tg.get("man_made", ""), tg.get("operator", ""))
