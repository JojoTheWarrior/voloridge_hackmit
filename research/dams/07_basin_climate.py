"""Upstream-basin climate for every monitored reservoir: HydroBASINS lev07 upstream trace x NOAA PREC/L precipitation
(1 deg monthly, gauge-based, near-real-time) and GHCN-CAMS 2 m temperature (0.5 deg). Keyless bulk files from NOAA PSL.
A 'snow-season precipitation' proxy is precipitation falling in months with basin-mean T < 0 C.
Output data/basin_climate.parquet (gww_id, month, precip_mm, temp_c, snow_mm) and data/basins.parquet (basin area)."""
import zipfile

import geopandas as gpd
import numpy as np
import pandas as pd
import xarray as xr
from shapely.geometry import Point

from common import DATA, RESULTS

HB = DATA / "hybas"
st = pd.read_csv(RESULTS / "dam_statics.csv")
extra = pd.read_csv(DATA / "case_studies.csv")
units = pd.concat([st[["gww_id", "lat", "lon"]], extra[["gww_id", "lat", "lon"]]]).drop_duplicates("gww_id").dropna()

frames = []
for z in sorted(HB.glob("hybas_*_lev07_v1c.zip")):
    d = HB / z.stem
    if not d.exists():
        zipfile.ZipFile(z).extractall(d)
    frames.append(gpd.read_file(next(d.glob("*.shp")))[["HYBAS_ID", "NEXT_DOWN", "SUB_AREA", "UP_AREA", "geometry"]])
hb = pd.concat(frames, ignore_index=True)
hb = gpd.GeoDataFrame(hb, crs=4326)
up = hb.groupby("NEXT_DOWN").HYBAS_ID.apply(list).to_dict()
cent = hb.geometry.representative_point()
hb["clat"], hb["clon"] = cent.y, cent.x

pts = gpd.GeoDataFrame(units, geometry=[Point(xy) for xy in zip(units.lon, units.lat)], crs=4326)
j = gpd.sjoin(pts, hb[["HYBAS_ID", "geometry"]], predicate="within").drop_duplicates("gww_id")
print("units located in a sub-basin:", len(j), "/", len(units))

pre = xr.open_dataset(DATA / "clim" / "precip.mon.mean.1x1.nc").precip.sel(time=slice("1999-01-01", None)).load()  # mm/day
tmp = xr.open_dataset(DATA / "clim" / "air.mon.mean.nc").air.sel(time=slice("1999-01-01", None)).load() - 273.15
idx = hb.set_index("HYBAS_ID")


def upstream(h):
    out, stack = [], [h]
    while stack:
        x = stack.pop()
        out.append(x)
        stack.extend(up.get(x, []))
    return out


def sample(da, lats, lons, w):
    """Area-weighted mean over the grid cells nearest to the sub-basin centroids (dedup by cell)."""
    la = da.lat.values[np.abs(da.lat.values[:, None] - lats[None, :]).argmin(0)]
    lo = da.lon.values[np.abs(da.lon.values[:, None] - (lons[None, :] % 360)).argmin(0)]
    cells = pd.DataFrame({"la": la, "lo": lo, "w": w}).groupby(["la", "lo"], as_index=False).w.sum()
    v = np.stack([da.sel(lat=r.la, lon=r.lo).values for r in cells.itertuples()])
    ww = np.where(np.isnan(v), 0, cells.w.values[:, None])
    return np.nansum(v * ww, 0) / np.maximum(ww.sum(0), 1e-9)


rows, meta = [], []
for r in j.itertuples():
    ids = upstream(r.HYBAS_ID)
    sub = idx.loc[ids]
    p = sample(pre, sub.clat.values, sub.clon.values, sub.SUB_AREA.values)
    t = sample(tmp, sub.clat.values, sub.clon.values, sub.SUB_AREA.values)
    df = pd.DataFrame({"month": pd.to_datetime(pre.time.values).to_period("M").to_timestamp(), "precip_mm": p}).merge(
        pd.DataFrame({"month": pd.to_datetime(tmp.time.values).to_period("M").to_timestamp(), "temp_c": t}), on="month", how="left")
    df["precip_mm"] = df.precip_mm * df.month.dt.days_in_month
    df["snow_mm"] = np.where(df.temp_c < 0, df.precip_mm, 0.0)
    df["gww_id"] = r.gww_id
    rows.append(df)
    meta.append({"gww_id": r.gww_id, "basin_km2": sub.SUB_AREA.sum(), "n_subbasins": len(ids)})
pd.concat(rows).to_parquet(DATA / "basin_climate.parquet")
pd.DataFrame(meta).to_parquet(DATA / "basins.parquet")
print(pd.DataFrame(meta).basin_km2.describe())
