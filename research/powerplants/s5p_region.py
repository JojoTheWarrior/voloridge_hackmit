"""Daily qa-filtered TROPOMI composites on a fixed 0.035deg grid for a region, from keyless COGs on s3://meeo-s5p.
usage: s5p_region.py REGION PRODUCT(no2|so2) START END   -> grids/{region}_{product}_{YYYY-MM}.npz (float16, umol/m2)"""
import os, sys, re, time, datetime as dt, numpy as np, s3fs, rasterio
from rasterio.windows import from_bounds
from rasterio.enums import Resampling
from concurrent.futures import ThreadPoolExecutor
os.environ.update(AWS_NO_SIGN_REQUEST="YES", GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif",
                  GDAL_HTTP_MAX_RETRY="4", GDAL_HTTP_RETRY_DELAY="2", VSI_CACHE="FALSE")
REGIONS = {  # lon0, lat0, lon1, lat1, first/last UTC hour of orbit start
    "conus": (-125.0, 24.0, -66.0, 50.0, 15, 23), "me": (34.0, 12.0, 64.0, 40.0, 6, 12),
    "au": (138.0, -40.0, 154.0, -20.0, 1, 7), "idn": (118.0, -6.0, 130.0, 3.0, 2, 7)}
PROD = {"no2": ("L2__NO2___", "PRODUCT_nitrogendioxide_tropospheric_column_4326.tif", 0.75),
        "so2": ("L2__SO2___", "PRODUCT_sulfurdioxide_total_vertical_column_4326.tif", 0.5)}
PX = 0.035
region, product = sys.argv[1], sys.argv[2]
start, end = dt.date.fromisoformat(sys.argv[3]), dt.date.fromisoformat(sys.argv[4])
lon0, lat0, lon1, lat1, h0, h1 = REGIONS[region]; pdir, suffix, qmin = PROD[product]
W, H = round((lon1-lon0)/PX), round((lat1-lat0)/PX)
fs = s3fs.S3FileSystem(anon=True)

def read(path):
    with rasterio.open("/vsis3/" + path) as ds:
        w = from_bounds(lon0, lat0, lon1, lat1, ds.transform)
        return ds.read(1, window=w, out_shape=(H, W), boundless=True, fill_value=-9999, resampling=Resampling.nearest).astype("float32")

def day_composite(day):
    for attempt in range(3):
        try:
            try: names = fs.ls(f"meeo-s5p/COGT/OFFL/{pdir}/{day:%Y/%m/%d}/", refresh=True)
            except FileNotFoundError: return day, None, 0
            acc = np.zeros((H, W), "float32"); cnt = np.zeros((H, W), "uint8"); n = 0
            for p in names:
                if not p.endswith(suffix): continue
                h = int(re.search(r"____(\d{8})T(\d{2})", p).group(2))
                if not (h0 <= h <= h1): continue
                a = read(p); q = read(p.replace(suffix, "PRODUCT_qa_value_4326.tif"))
                if q.max() > 1.5: q = q/100
                ok = (a != -9999) & (q >= qmin) & np.isfinite(a)
                acc[ok] += a[ok]*1e6; cnt[ok] += 1; n += 1
            out = np.where(cnt > 0, acc/np.maximum(cnt, 1), np.nan)
            return day, np.clip(out, -6e4, 6e4).astype("float16"), n
        except Exception as e:
            err = e; time.sleep(5)
    print("FAIL", day, err, flush=True); return day, None, 0

months = sorted({(d.year, d.month) for d in (start + dt.timedelta(i) for i in range((end-start).days+1))})
with ThreadPoolExecutor(int(os.environ.get("THREADS", 24))) as ex:
    for y, m in months:
        out = f"grids/{region}_{product}_{y}-{m:02d}.npz"
        if os.path.exists(out): continue
        days = [d for d in (dt.date(y, m, 1) + dt.timedelta(i) for i in range(31)) if d.month == m and start <= d <= end]
        t = time.time(); res = [r for r in ex.map(day_composite, days) if r[1] is not None]
        if not res: print(y, m, "no data", flush=True); continue
        np.savez_compressed(out, days=np.array([str(r[0]) for r in res]), grid=np.stack([r[1] for r in res]), norbits=np.array([r[2] for r in res]),
                            bounds=np.array([lon0, lat0, lon1, lat1]))
        print(out, len(res), "days", round(time.time()-t), "s", flush=True)
