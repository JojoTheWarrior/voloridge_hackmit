"""Extract ERA5 (Open-Meteo S3 mirror, anonymous) hourly series for station + city cells, saved as daily means."""
import sys, os, threading, numpy as np, pandas as pd, fsspec
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from omfiles import OmFileReader
VAR = sys.argv[1]
CHUNKS = range(956, 975)  # 504 h per chunk; covers 2025
pts = [pd.read_csv(f, dtype={"id": str})[["lat", "lon"]] for f in ("stations_sample.csv", "stations_extra.csv")]
ci = pd.read_csv("cities_coverage.csv", keep_default_na=False); pts.append(ci[ci["pop"].astype(int) >= 500_000][["lat", "lon"]].astype(float))
p = pd.concat(pts); i = np.rint((p.lat + 90) / 0.25).astype(int).clip(0, 720); j = np.rint((p.lon + 180) / 0.25).astype(int) % 1440
cells = sorted(set(zip(i, j))); blocks = sorted({(a, b // 6) for a, b in cells})
tl = threading.local()
def work(chunk):
    def read(blk):
        if not hasattr(tl, "r"):
            tl.r = OmFileReader.from_fsspec(fsspec.filesystem("s3", anon=True), f"openmeteo/data/copernicus_era5/{VAR}/chunk_{chunk}.om")
        a, b = blk
        return blk, tl.r[a, b * 6:b * 6 + 6, :]
    with ThreadPoolExecutor(10) as ex:
        got = dict(ex.map(read, blocks))
    np.save(f"era5/{VAR}_{chunk}.npy", np.stack([got[(a, b // 6)][b % 6] for a, b in cells]).astype(np.float32))
    return chunk
if __name__ == "__main__":
    os.makedirs("era5", exist_ok=True)
    pd.DataFrame(cells, columns=["i", "j"]).to_csv("era5/cells.csv", index=False)
    print(len(cells), len(blocks), flush=True)
    todo = [c for c in CHUNKS if not os.path.exists(f"era5/{VAR}_{c}.npy")]
    with ProcessPoolExecutor(10) as ex:
        for c in ex.map(work, todo): print(c, flush=True)
