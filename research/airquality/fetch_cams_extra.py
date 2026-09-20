"""Extract CAMS global (Open-Meteo S3 mirror, anonymous) hourly series at station + city grid cells via range reads."""
import sys, threading, numpy as np, pandas as pd, fsspec
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from omfiles import OmFileReader
VAR = sys.argv[1]
CHUNKS = range(2221, 2263)  # 2025-01-01 .. 2025-12-31 (217 h per chunk)
st = pd.read_csv("stations_extra.csv", dtype={"id": str})[["lat", "lon"]]
ci = pd.read_csv("cities_coverage.csv", keep_default_na=False); ci = ci[ci["pop"].astype(int) >= 500_000][["lat", "lon"]].astype(float)
p = st; i = np.rint((p.lat + 90) / 0.4).astype(int).clip(0, 450); j = (np.rint((p.lon + 180) / 0.4).astype(int)) % 900
cells = sorted(set(zip(i, j))); blocks = sorted({(a, b // 14) for a, b in cells})
tl = threading.local()
def work(chunk):
    def read(blk):
        if not hasattr(tl, "r"):
            tl.r = OmFileReader.from_fsspec(fsspec.filesystem("s3", anon=True), f"openmeteo/data/cams_global/{VAR}/chunk_{chunk}.om")
        a, b = blk
        return blk, tl.r[a, b * 14:min(b * 14 + 14, 900), :]
    with ThreadPoolExecutor(10) as ex:
        got = dict(ex.map(read, blocks))
    out = np.stack([got[(a, b // 14)][b % 14] for a, b in cells]).astype(np.float32)
    np.save(f"cams_x/{VAR}_{chunk}.npy", out)
    return chunk
if __name__ == "__main__":
    import os; os.makedirs("cams_x", exist_ok=True)
    pd.DataFrame(cells, columns=["i", "j"]).to_csv("cams_x/cells.csv", index=False)
    print(len(cells), "cells", len(blocks), "blocks", flush=True)
    todo = [c for c in CHUNKS if not os.path.exists(f"cams_x/{VAR}_{c}.npy")]
    with ProcessPoolExecutor(14) as ex:
        for c in ex.map(work, todo): print(c, flush=True)
