"""Join OpenAQ daily PM2.5 (every 4th day of 2025) with CAMS + ERA5 daily means, VIIRS monthly AOD, and population context."""
import glob, os, numpy as np, pandas as pd, xarray as xr
from sklearn.neighbors import BallTree
CAMS_VARS = ["pm2_5", "dust", "aerosol_optical_depth", "nitrogen_dioxide"]
ERA_VARS = ["boundary_layer_height", "temperature_2m", "wind_u_component_10m", "wind_v_component_10m", "precipitation", "dew_point_2m"]
def daily(d, var, c0, c1, clen):
    x = np.concatenate([np.load(f"{d}/{var}_{c}.npy") for c in range(c0, c1)], axis=1)
    t = pd.Timestamp("1970-01-01") + pd.Timedelta(hours=c0 * clen) + pd.to_timedelta(np.arange(x.shape[1]), unit="h")
    df = pd.DataFrame(x.T, index=t)
    return df[(df.index >= "2025-01-01") & (df.index < "2026-01-01")].resample("D").mean()
def cell_lookup(d, res, n_i, n_j):
    c = pd.read_csv(f"{d}/cells.csv"); ix = {(a, b): k for k, (a, b) in enumerate(zip(c.i, c.j))}
    return lambda lat, lon: [ix[(a, b)] for a, b in zip(np.rint((lat + 90) / res).astype(int).clip(0, n_i), np.rint((lon + 180) / res).astype(int) % n_j)]
def attach(df, d, vars_, prefix, c0, c1, clen, res, n_i, n_j):
    df = df.copy(); df["_cell"] = cell_lookup(d, res, n_i, n_j)(df.lat.astype(float), df.lon.astype(float))
    out = {}
    for v in vars_:
        if not os.path.exists(f"{d}/{v}_{c1 - 1}.npy"): print("missing", d, v); continue
        out[prefix + v] = daily(d, v, c0, c1, clen)
    return df, out
cities = pd.read_csv("cities_coverage.csv", keep_default_na=False); cities[["lat", "lon", "pop"]] = cities[["lat", "lon", "pop"]].astype(float)
tree = BallTree(np.radians(cities[["lat", "lon"]].values), metric="haversine")
def pop_features(df):
    idx = tree.query_radius(np.radians(df[["lat", "lon"]].astype(float).values), r=50 / 6371)
    df["log_pop50"] = [np.log10(cities["pop"].values[i].sum() + 1e4) for i in idx]
    return df
vi = {m: xr.open_dataset(f"viirs/2025{m:02d}.nc").aod for m in range(1, 13)}
def viirs(lat, lon, m):
    return vi[m].sel(lat=xr.DataArray(np.asarray(lat, float)), lon=xr.DataArray(np.asarray(lon, float)), method="nearest").values

frames = []
for tag, sfile, cdir in [("s", "stations_sample.csv", "cams"), ("x", "stations_extra.csv", "cams_x")]:
    st = pd.read_csv(sfile, dtype={"id": str})
    obs = pd.concat([pd.read_csv(f, dtype={"id": str}) for f in glob.glob("pm25_daily_x*.csv" if tag == "x" else "pm25_daily_[0-9]*.csv")])
    obs = obs[obs.n_ok >= 12].merge(st[["id", "name", "lat", "lon", "cc", "region", "kind", "provider", "params"]], on="id")
    obs["date"] = pd.to_datetime(obs.date)
    for d, vars_, pre, args in [(cdir, CAMS_VARS, "cams_", (2221, 2263, 217, 0.4, 450, 900)), ("era5", ERA_VARS, "era_", (956, 975, 504, 0.25, 720, 1440))]:
        obs, out = attach(obs, d, vars_, pre, *args)
        for name, df in out.items():
            obs = obs.merge(df.stack().rename(name).rename_axis(["date", "_cell"]).reset_index(), on=["date", "_cell"], how="left")
    frames.append(obs.drop(columns="_cell"))
obs = pop_features(pd.concat(frames, ignore_index=True))
obs["month"] = obs.date.dt.month; obs["viirs_aod"] = np.nan
for m, g in obs.groupby("month"): obs.loc[g.index, "viirs_aod"] = viirs(g.lat, g.lon, m)
obs.to_parquet("dataset_daily.parquet")
print(len(obs), obs.id.nunique(), "stations", obs.cc.nunique(), "countries", list(obs.columns))

# city x month table for prediction
ci = cities[cities["pop"] >= 500_000].copy()
rows = []
base, outs = ci, {}
for d, vars_, pre, args in [("cams", CAMS_VARS, "cams_", (2221, 2263, 217, 0.4, 450, 900)), ("era5", ERA_VARS, "era_", (956, 975, 504, 0.25, 720, 1440))]:
    b, out = attach(ci, d, vars_, pre, *args)
    for name, df in out.items():
        mm = df.groupby(df.index.month).mean()  # month x cell
        outs[name] = mm.values[:, b._cell.values]  # 12 x ncity
for m in range(1, 13):
    r = ci[["gid", "name", "cc", "country", "region", "lat", "lon", "pop", "n_ref_25", "n_ref_50", "n_any_25"]].copy(); r["month"] = m
    for name, arr in outs.items(): r[name] = arr[m - 1]
    r["viirs_aod"] = viirs(r.lat, r.lon, m); rows.append(r)
pop_features(pd.concat(rows, ignore_index=True)).to_parquet("cities_monthly.parquet")
