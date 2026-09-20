"""Download GDELT 2.0 raw 15-minute export files (keyless) for date ranges into score_out/gdelt_export/."""
import sys, requests, datetime as dt
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
OUT = Path("score_out/gdelt_export"); OUT.mkdir(parents=True, exist_ok=True)
S = requests.Session()
def job(ts):
    f = OUT / f"{ts}.export.CSV.zip"
    if f.exists(): return 0
    for a in range(3):
        try:
            r = S.get(f"https://data.gdeltproject.org/gdeltv2/{ts}.export.CSV.zip", timeout=60)
            if r.status_code == 200: f.write_bytes(r.content); return 1
            if r.status_code == 404: f.with_suffix(".missing").touch(); return 0
        except Exception: pass
    return 0
def stamps(a, b):
    t = dt.datetime.fromisoformat(a); e = dt.datetime.fromisoformat(b) + dt.timedelta(days=1)
    while t < e:
        yield t.strftime("%Y%m%d%H%M%S"); t += dt.timedelta(minutes=15)
if __name__ == "__main__":
    ts = [s for i in range(1, len(sys.argv), 2) for s in stamps(sys.argv[i], sys.argv[i + 1])]
    with ThreadPoolExecutor(16) as ex: n = sum(ex.map(job, ts))
    print("downloaded", n, "of", len(ts))
