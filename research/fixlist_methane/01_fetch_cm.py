"""Fetch all Carbon Mapper CH4 plumes (CSV) and DBSCAN sources (GeoJSON, carries observation/detection date counts).
Anonymous, paged, 1 s pause between pages. Source: Carbon Mapper (data.carbonmapper.org); non-commercial ToU, attribution required."""
import io, json, time, requests, pandas as pd
UA = {"User-Agent": "kingdom-hackathon-research/0.1 (noncommercial methane mitigation demo)"}
API = "https://api.carbonmapper.org/api/v1/catalog"

def plumes():
    fr, off = [], 0
    while True:
        r = requests.get(f"{API}/plume-csv", params={"plume_gas": "CH4", "limit": 5000, "offset": off}, headers=UA, timeout=300)
        r.raise_for_status()
        d = pd.read_csv(io.StringIO(r.text))
        fr.append(d); off += 5000; print("plumes", off, len(d), flush=True)
        if len(d) < 5000: break
        time.sleep(1)
    p = pd.concat(fr).drop_duplicates("plume_id")
    p.to_csv("data/cm_plumes_full.csv", index=False); print("total plumes", len(p))

def sources():
    feats, off = [], 0
    while True:
        r = requests.get(f"{API}/sources.geojson", params={"plume_gas": "CH4", "limit": 1000, "offset": off}, headers=UA, timeout=300)
        r.raise_for_status()
        f = r.json()["features"]; feats += f; off += 1000; print("sources", off, len(f), flush=True)
        if len(f) < 1000: break
        time.sleep(1)
    json.dump({"type": "FeatureCollection", "features": feats}, open("data/cm_sources.geojson", "w"))
    print("total sources", len(feats))

if __name__ == "__main__":
    plumes(); sources()
