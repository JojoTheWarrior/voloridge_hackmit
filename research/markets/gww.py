"""Global Water Watch (keyless) helpers with on-disk cache and polite backoff."""
import json, time, requests
from pathlib import Path
import pandas as pd
B = "https://api.globalwaterwatch.earth"
C = Path(__file__).parent / "data" / "gww"; C.mkdir(parents=True, exist_ok=True)
S = requests.Session()

def _req(method, url, **kw):
    for a in range(5):
        try:
            r = S.request(method, url, timeout=120, **kw)
            if r.status_code == 200: return r.json()
            if r.status_code in (404, 422): return None
        except Exception: pass
        time.sleep(2 + 3 * a)
    return None

def find(lon, lat, d=0.0):
    """Reservoir features at a point (d=0) or in a +-d degree box."""
    fn = C / f"find_{lon}_{lat}_{d}.json"
    if fn.exists(): return json.loads(fn.read_text())
    g = {"type": "Point", "coordinates": [lon, lat]} if d == 0 else {"type": "Polygon", "coordinates": [[[lon-d,lat-d],[lon+d,lat-d],[lon+d,lat+d],[lon-d,lat+d],[lon-d,lat-d]]]}
    j = _req("POST", B + "/reservoir/geometry", json=g) or {}
    out = [{"id": f["id"], "name": (f.get("properties") or {}).get("name"), "props": {k: v for k, v in (f.get("properties") or {}).items() if k != "geometry"}} for f in j.get("features", [])]
    fn.write_text(json.dumps(out)); time.sleep(1); return out

def area(rid, start="2000-01-01", stop="2026-09-19"):
    """Raw (per-image) surface water area in km2."""
    fn = C / f"area_{rid}.json"
    if not fn.exists():
        j = _req("GET", f"{B}/reservoir/{rid}/ts/surface_water_area", params={"start": start + "T00:00:00", "stop": stop + "T00:00:00"})
        fn.write_text(json.dumps(j or [])); time.sleep(1)
    j = json.loads(fn.read_text())
    s = pd.Series({pd.Timestamp(x["t"]).tz_localize(None): x["value"] / 1e6 for x in j}, dtype=float).sort_index()
    return s[~s.index.duplicated()]
