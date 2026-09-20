"""Sample HREA v1.1 COGs (windowed, remote) around every geolocated facility in the
WHO/KEMRI sub-Saharan Africa master facility list. Nothing is downloaded whole."""
import os, sys, math, numpy as np, pandas as pd, rasterio
from rasterio.windows import Window
from concurrent.futures import ThreadPoolExecutor

os.environ.update(AWS_NO_SIGN_REQUEST="YES", GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
                  GDAL_HTTP_MULTIPLEX="YES", VSI_CACHE="TRUE", GDAL_CACHEMAX="512",
                  CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif")
ISO = {"Angola":"AGO","Benin":"BEN","Botswana":"BWA","Burkina Faso":"BFA","Burundi":"BDI","Cameroon":"CMR",
 "Cape Verde":"CPV","Central African Republic":"CAF","Chad":"TCD","Comoros":"COM","Congo":"COG",
 "Cote d'Ivoire":"CIV","Democratic Republic of the Congo":"COD","Djibouti":"DJI","Equatorial Guinea":"GNQ",
 "Eritrea":"ERI","Ethiopia":"ETH","Gabon":"GAB","Gambia":"GMB","Ghana":"GHA","Guinea":"GIN",
 "Guinea Bissau":"GNB","Kenya":"KEN","Lesotho":"LSO","Liberia":"LBR","Madagascar":"MDG","Malawi":"MWI",
 "Mali":"MLI","Mauritania":"MRT","Mauritius":"MUS","Mozambique":"MOZ","Namibia":"NAM","Niger":"NER",
 "Nigeria":"NGA","Rwanda":"RWA","Sao Tome and Principe":"STP","Senegal":"SEN","Sierra Leone":"SLE",
 "Somalia":"SOM","South Africa":"ZAF","South Sudan":"SSD","Sudan":"SDN","Tanzania":"TZA","Zanzibar":"TZA",
 "Togo":"TGO","Uganda":"UGA","Zambia":"ZMB","Zimbabwe":"ZWE","eSwatini":"SWZ"}
BASE = "/vsis3/globalnightlight/HREAv1.1_COGs/{c}/{c}/"
YEAR = 2020
R_NEAR, R_CATCH = 500.0, 5000.0          # metres


def sample_country(iso, df):
    paths = dict(ls=BASE.format(c=iso)+f"set_lightscore/{iso}_set_lightscore_{YEAR}.tif",
                 pop=BASE.format(c=iso)+f"{iso}_set_pop.tif",
                 rad=BASE.format(c=iso)+f"rade9lnmu/{iso}_rade9lnmu_{YEAR}.tif")
    ds = {k: rasterio.open(v) for k, v in paths.items()}
    ref = ds["ls"]; res = abs(ref.transform.a); H, W = ref.height, ref.width
    out = []
    for r in df.itertuples():
        row, col = ref.index(r.lon, r.lat)
        ky = 111320.0 * res; kx = ky * math.cos(math.radians(r.lat))
        ry, rx = int(R_CATCH/ky)+1, int(R_CATCH/kx)+1
        if not (0 <= row < H and 0 <= col < W):
            out.append(dict(fid=r.fid, in_raster=False)); continue
        win = Window(col-rx, row-ry, 2*rx+1, 2*ry+1)
        a = {k: d.read(1, window=win, boundless=True, fill_value=np.nan).astype("float32") for k, d in ds.items()}
        for k, d in ds.items():
            if d.nodata is not None: a[k][a[k] == d.nodata] = np.nan
        yy, xx = np.mgrid[-ry:ry+1, -rx:rx+1]
        dist = np.hypot(yy*ky, xx*kx)
        ls, pop, rad = a["ls"], a["pop"], a["rad"]
        sett = np.isfinite(ls)
        near = sett & (dist <= R_NEAR); catch = sett & (dist <= R_CATCH)
        lit = catch & (ls >= 0.5)
        p = np.where(np.isfinite(pop), pop, 0)
        out.append(dict(fid=r.fid, in_raster=True,
            n_sett_500=int(near.sum()),
            ls_max_500=float(np.nanmax(ls[near])) if near.any() else np.nan,
            ls_mean_500=float(np.nanmean(ls[near])) if near.any() else np.nan,
            dist_sett_m=float(dist[sett].min()) if sett.any() else np.nan,
            pop_500=float(p[near].sum()), pop_5km=float(p[catch].sum()),
            pop_lit_5km=float(p[lit].sum()),
            ls_max_5km=float(np.nanmax(ls[catch])) if catch.any() else np.nan,
            dist_lit_m=float(dist[lit].min()) if lit.any() else np.nan,
            rad_max_500=float(np.nanmax(rad[dist<=R_NEAR])) if np.isfinite(rad[dist<=R_NEAR]).any() else np.nan))
    for d in ds.values(): d.close()
    return pd.DataFrame(out)

if __name__ == "__main__":
    mfl = pd.read_parquet("data/mfl_raw.parquet")
    mfl["iso3"] = mfl.country.map(ISO)
    os.makedirs("data/hrea_samples", exist_ok=True)
    todo = [c for c in sorted(mfl.iso3.dropna().unique()) if not os.path.exists(f"data/hrea_samples/{c}.parquet")]
    if len(sys.argv) > 1: todo = [c for c in todo if c in sys.argv[1:]]
    def run(iso):
        sub = mfl[(mfl.iso3 == iso) & mfl.lat.notna() & mfl.lon.notna()]
        try:
            res = sample_country(iso, sub)
            res.to_parquet(f"data/hrea_samples/{iso}.parquet")
            return iso, len(res), "ok"
        except Exception as e:
            return iso, len(sub), f"FAIL {type(e).__name__}: {str(e)[:150]}"
    with ThreadPoolExecutor(8) as ex:
        for iso, n, msg in ex.map(run, todo): print(iso, n, msg, flush=True)
