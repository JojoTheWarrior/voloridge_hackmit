"""Keyless fetchers: Nord Pool day-ahead prices (Energi Data Service), GloFAS discharge (Open-Meteo Flood API), NVE reservoir filling."""
import json, time, requests, numpy as np, pandas as pd
from pathlib import Path
D = Path(__file__).parent / "data"

def nordpool():
    fn = D / "nordpool_daily.parquet"
    if fn.exists(): return
    out = []
    for ds, tcol, pcol, y0, y1 in [("Elspotprices", "HourUTC", "SpotPriceEUR", 1999, 2025), ("DayAheadPrices", "TimeUTC", "DayAheadPriceEUR", 2025, 2026)]:
        for y in range(y0, y1 + 1):
            for _ in range(8):
                j = requests.get(f"https://api.energidataservice.dk/dataset/{ds}", params={"start": f"{y}-01-01", "end": f"{y+1}-01-01", "filter": json.dumps({"PriceArea": ["SYS", "NO2", "SE3", "DK1"]}), "limit": 0, "columns": f"{tcol},PriceArea,{pcol}"}, timeout=300).json()
                if j.get("statusCode") != 429: break
                time.sleep(120)
            rec = j.get("records", [])
            if rec:
                df = pd.DataFrame(rec).rename(columns={tcol: "t", pcol: "eur"}); df["t"] = pd.to_datetime(df.t)
                out.append(df.groupby([df.t.dt.floor("D"), "PriceArea"]).eur.mean().unstack())
            print(ds, y, len(rec), flush=True); time.sleep(20)
    d = pd.concat(out); d = d.groupby(d.index).mean(); d.to_parquet(fn)

def glofas(name, lat, lon, start="1995-01-01", end="2026-09-18"):
    """Snap to the 0.05-degree cell with the largest mean discharge in a 5x5 neighbourhood, then pull the full daily series."""
    fn = D / f"glofas_{name}.parquet"
    if fn.exists(): return pd.read_parquet(fn).q
    U = "https://flood-api.open-meteo.com/v1/flood"
    la = [round(lat + dy * 0.05, 3) for dy in range(-2, 3) for dx in range(-2, 3)]; lo = [round(lon + dx * 0.05, 3) for dy in range(-2, 3) for dx in range(-2, 3)]
    def get(p):
        for _ in range(6):
            j = requests.get(U, params=p, timeout=300).json()
            if isinstance(j, dict) and j.get("error"): time.sleep(65); continue
            return j
        raise RuntimeError(j)
    j = get({"latitude": ",".join(map(str, la)), "longitude": ",".join(map(str, lo)), "daily": "river_discharge", "start_date": "2019-01-01", "end_date": "2020-12-31"})
    best = max(j, key=lambda c: np.nanmean([x or 0 for x in c["daily"]["river_discharge"]]))
    time.sleep(5)
    f = get({"latitude": best["latitude"], "longitude": best["longitude"], "daily": "river_discharge", "start_date": start, "end_date": end})
    s = pd.Series(f["daily"]["river_discharge"], index=pd.to_datetime(f["daily"]["time"]), dtype=float, name="q")
    s.to_frame().assign(lat=best["latitude"], lon=best["longitude"]).to_parquet(fn); time.sleep(10)
    return s

if __name__ == "__main__":
    nordpool()
    for n, (la, lo) in {"rhine_kaub": (50.085, 7.765), "danube_placebo_budapest": (47.50, 19.05), "loire_placebo_saumur": (47.26, -0.08)}.items():
        s = glofas(n, la, lo); print(n, len(s), s.index.min().date(), s.index.max().date(), round(s.mean()), flush=True)
