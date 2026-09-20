"""Nord Pool day-ahead prices via Energi Data Service (keyless, strict rate limit): one request per year, cached, honours the server's retry-after message."""
import json, re, time, requests, pandas as pd
from pathlib import Path
D = Path(__file__).parent / "data" / "nordpool"; D.mkdir(parents=True, exist_ok=True)
for ds, tcol, pcol, y0, y1 in [("Elspotprices", "HourUTC", "SpotPriceEUR", 2000, 2025), ("DayAheadPrices", "TimeUTC", "DayAheadPriceEUR", 2025, 2026)]:
    for y in range(y0, y1 + 1):
        fn = D / f"{ds}_{y}.parquet"
        if fn.exists(): continue
        for _ in range(40):
            j = requests.get(f"https://api.energidataservice.dk/dataset/{ds}", params={"start": f"{y}-01-01", "end": f"{y+1}-01-01", "filter": json.dumps({"PriceArea": ["SYS", "NO2"]}), "limit": 0, "columns": f"{tcol},PriceArea,{pcol}"}, timeout=300).json()
            if j.get("statusCode") != 429: break
            m = re.search(r"(\d+) seconds", j.get("message", "")); time.sleep(int(m.group(1)) + 10 if m else 300)
        else: raise SystemExit(f"rate-limited out at {ds} {y}")
        df = pd.DataFrame(j.get("records", []))
        if len(df):
            df = df.rename(columns={tcol: "t", pcol: "eur"}); df["t"] = pd.to_datetime(df.t)
            df = df.groupby([df.t.dt.floor("D"), "PriceArea"]).eur.mean().unstack()
        df.to_parquet(fn); print(ds, y, len(df), flush=True); time.sleep(30)
fr = [pd.read_parquet(f) for f in sorted(D.glob("*.parquet"))]; d = pd.concat([f for f in fr if len(f)]); d = d.groupby(d.index).mean()
d.to_parquet(D.parent / "nordpool_daily.parquet"); print("done", d.shape, d.index.min(), d.index.max(), d.notna().sum().to_dict())
