"""Probe NAIP vintages + flight dates on Planetary Computer STAC (anonymous) for candidate storm areas."""
import json, sys, collections
from pystac_client import Client
cat = Client.open("https://planetarycomputer.microsoft.com/api/stac/v1")
AREAS = {
 "lake_charles_LA": [-93.30, 30.15, -93.12, 30.28],
 "houma_LA": [-90.78, 29.55, -90.65, 29.63],
 "laplace_LA": [-90.55, 30.04, -90.42, 30.10],
 "panama_city_FL": [-85.72, 30.13, -85.58, 30.22],
 "fort_myers_FL": [-81.95, 26.55, -81.80, 26.68],
 "rockport_TX": [-97.10, 27.98, -97.00, 28.08],
 "wilmington_NC": [-77.98, 34.18, -77.85, 34.27],
 "san_juan_PR": [-66.12, 18.38, -66.02, 18.45],
 "st_thomas_VI": [-64.98, 18.32, -64.88, 18.37],
}
out = {}
for name, bbox in AREAS.items():
    items = list(cat.search(collections=["naip"], bbox=bbox, max_items=500).items())
    by = collections.defaultdict(list)
    for it in items:
        by[it.properties.get("naip:year")].append((it.datetime.date().isoformat(), it.properties.get("gsd")))
    out[name] = {y: {"n": len(v), "dates": sorted(set(d for d, _ in v)), "gsd": sorted(set(g for _, g in v))} for y, v in sorted(by.items())}
    print(name, json.dumps(out[name]))
json.dump(out, open("data/naip_vintages.json", "w"), indent=1)
