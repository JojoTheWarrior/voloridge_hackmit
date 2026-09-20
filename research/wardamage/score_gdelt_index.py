"""Collapse downloaded GDELT 15-min export files to first-seen time per article URL (+ geo names coded on it)."""
import pandas as pd, glob, zipfile, io
from concurrent.futures import ProcessPoolExecutor
def one(f):
    try:
        with zipfile.ZipFile(f) as z:
            d = pd.read_csv(io.BytesIO(z.read(z.namelist()[0])), sep="\t", header=None, usecols=[52, 59, 60], dtype=str, on_bad_lines="skip")
    except Exception: return None
    d.columns = ["geo", "added", "url"]
    return d.groupby("url").agg(added=("added", "min"), geo=("geo", lambda s: "|".join(sorted(set(s.dropna()))[:6]))).reset_index()
if __name__ == "__main__":
    fs = sorted(glob.glob("score_out/gdelt_export/*.zip"))
    with ProcessPoolExecutor(8) as ex: parts = [d for d in ex.map(one, fs, chunksize=50) if d is not None]
    a = pd.concat(parts).sort_values("added").drop_duplicates("url")
    a["added"] = pd.to_datetime(a.added, format="%Y%m%d%H%M%S")
    a.to_parquet("score_out/gdelt_urls.parquet"); print(len(fs), "files ->", len(a), "urls", a.added.min(), a.added.max())
