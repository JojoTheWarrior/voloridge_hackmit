"""Pull daily VIIRS S-NPP 375 m thermal anomalies (NASA GIBS vector tiles, keyless) 2012-2026 for three z=4 tiles:
North Africa W (0-18E), North Africa E (18-36E), Gulf (36-54E); all 18-36N. Night detections only are kept (local solar hour 21-06). Cached per day."""
import sys, time, requests, pandas as pd, mapbox_vector_tile as mvt
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
L = "VIIRS_SNPP_Thermal_Anomalies_375m_All"
U = "https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/" + L + "/default/{d}/500m/4/3/{c}.mvt"
OUT = Path(__file__).parent / "data" / "gibs"; OUT.mkdir(parents=True, exist_ok=True)
S = requests.Session(); KEEP = ["LATITUDE", "LONGITUDE", "FRP", "CONFIDENCE", "ACQ_TIME", "VERSION"]

def tile(d, c):
    for a in range(5):
        try:
            r = S.get(U.format(d=d, c=c), timeout=90)
            if r.status_code == 200:
                if not r.content: return []
                return [f["properties"] for v in mvt.decode(r.content).values() for f in v["features"]]
            if r.status_code in (400, 404): return []
        except Exception: pass
        time.sleep(2 + 2 * a)
    raise RuntimeError(f"fail {d} {c}")

def job(d):
    f = OUT / f"{d}.parquet"
    if f.exists(): return
    try:
        rows = [dict(p, col=c) for c in (10, 11, 12) for p in tile(d, c)]
        df = pd.DataFrame(rows)
        if len(df):
            for k in ("LATITUDE", "LONGITUDE", "FRP"): df[k] = pd.to_numeric(df[k], errors="coerce")
            # archive tiles lack DAYNIGHT: derive night from local solar hour (S-NPP passes ~01:30 / 13:30 local)
            h = (df.ACQ_TIME.str[:2].astype(int) + df.ACQ_TIME.str[3:5].astype(int) / 60 + df.LONGITUDE / 15) % 24
            df = df[(h >= 21) | (h < 6)][KEEP + ["col"]].astype({"VERSION": str, "CONFIDENCE": str})
        df.to_parquet(f)
    except Exception as e: print("ERR", d, e, flush=True)

if __name__ == "__main__":
    a, b = sys.argv[1], sys.argv[2]
    days = [x.strftime("%Y-%m-%d") for x in pd.date_range(a, b)]
    with ThreadPoolExecutor(6) as ex: list(ex.map(job, days))
    print("done", a, b, flush=True)
