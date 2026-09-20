"""Pull +-1deg TROPOMI NO2 windows (keyless COGs on s3://meeo-s5p) around each plant for every US-daytime orbit."""
import os, sys, re, time, datetime as dt, numpy as np, pandas as pd, s3fs, rasterio
from rasterio.windows import from_bounds
from concurrent.futures import ThreadPoolExecutor
os.environ.update(AWS_NO_SIGN_REQUEST="YES", GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif")
plants = pd.read_csv(os.environ.get("PLANTS","plants.csv"))
fs = s3fs.S3FileSystem(anon=True)
start, end = dt.date.fromisoformat(sys.argv[1]), dt.date.fromisoformat(sys.argv[2])
HALF = 1.0

def orbit_files(day):
    d = f"meeo-s5p/COGT/OFFL/L2__NO2___/{day:%Y/%m/%d}/"
    try: names = fs.ls(d)
    except FileNotFoundError: return []
    out = []
    for n in names:
        if not n.endswith("PRODUCT_nitrogendioxide_tropospheric_column_4326.tif"): continue
        m = re.search(r"NO2____(\d{8}T\d{6})_", n); h = int(m.group(1)[9:11])
        h0,h1=map(int,os.environ.get("HOURS","15,22").split(",")); 
        if h0 <= h <= h1: out.append((m.group(1), n))
    return out

def read_orbit(args):
    stamp, path = args
    qa_path = path.replace("PRODUCT_nitrogendioxide_tropospheric_column_4326", "PRODUCT_qa_value_4326")
    recs = []
    try:
        with rasterio.open("/vsis3/" + path) as ds, rasterio.open("/vsis3/" + qa_path) as qa:
            for p in plants.itertuples():
                w = from_bounds(p.longitude-HALF, p.latitude-HALF, p.longitude+HALF, p.latitude+HALF, ds.transform).round_offsets().round_lengths()
                a = ds.read(1, window=w).astype("float32"); a[a == -9999] = np.nan
                if np.isnan(a[23:34, 23:34]).all(): continue
                q = qa.read(1, window=w).astype("float32")
                recs.append((p.plant_id_eia, stamp, a, q))
    except Exception as e:
        print("ERR", stamp, e, flush=True)
    return recs

days = [start + dt.timedelta(n) for n in range((end-start).days+1)]
with ThreadPoolExecutor(16) as ex:
    orbits = [o for lst in ex.map(orbit_files, days) for o in lst]
    print(len(orbits), "orbits", flush=True)
    t = time.time(); allrecs = []
    for i, recs in enumerate(ex.map(read_orbit, orbits)):
        allrecs += recs
        if i % 50 == 0: print(i, len(allrecs), round(time.time()-t), flush=True)
ids = np.array([r[0] for r in allrecs]); stamps = np.array([r[1] for r in allrecs])
np.savez_compressed(os.environ.get("OUT",f"s5p_windows_{start}_{end}.npz"), plant=ids, stamp=stamps, no2=np.stack([r[2] for r in allrecs]), qa=np.stack([r[3] for r in allrecs]))
print("done", len(allrecs))
