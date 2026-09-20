"""Per-plant daily TROPOMI enhancement from regional daily grids: wind-rotated downwind box minus upwind background.
usage: no2_index.py REGION PRODUCT plants.csv wind.parquet out.csv"""
import numpy as np, pandas as pd, glob, sys
region, product, pfile, wfile, out = sys.argv[1:6]
plants = pd.read_csv(pfile); idc = plants.columns[0]; plants[idc] = plants[idc].astype(str)
wind = pd.read_parquet(wfile); wind["plant"] = wind.plant.astype(str); wind = wind.set_index(["plant", "time"]).sort_index()
PX = 0.035; HALFPX = 36                                                   # +-1.26 deg window
rows = []
for f in sorted(glob.glob(f"grids/{region}_{product}_*.npz")):
    d = np.load(f); grid = d["grid"]; days = d["days"]; lon0, lat0, lon1, lat1 = d["bounds"]; Hh = grid.shape[1]
    for p in plants.itertuples():
        pid = getattr(p, idc); c = int((p.longitude-lon0)/PX); r = int((lat1-p.latitude)/PX)
        if r-HALFPX < 0 or c-HALFPX < 0 or r+HALFPX >= Hh or c+HALFPX >= grid.shape[2]: continue
        win = grid[:, r-HALFPX:r+HALFPX+1, c-HALFPX:c+HALFPX+1].astype("float32")
        jj, ii = np.meshgrid(np.arange(-HALFPX, HALFPX+1), np.arange(-HALFPX, HALFPX+1))
        x = jj*PX*111.2*np.cos(np.radians(p.latitude)); y = -ii*PX*111.2; rr = np.hypot(x, y)
        for k, day in enumerate(days):
            a = win[k]
            th = (pd.Timestamp(str(day)) + pd.Timedelta(hours=13.5 - p.longitude/15)).floor("h")
            try: w = wind.loc[(pid, th)]
            except KeyError: continue
            wd = np.radians(w.wind_direction_100m); ux, uy = -np.sin(wd), -np.cos(wd)
            dw = x*ux + y*uy; cw = -x*uy + y*ux
            box = (dw > -5) & (dw < 50) & (np.abs(cw) < 12); upw = (dw < -10) & (dw > -70) & (np.abs(cw) < 45)
            if np.isfinite(a[box]).mean() < 0.8 or np.isfinite(a[upw]).mean() < 0.5: continue
            bg = np.nanmedian(a[upw]); enh = np.nanmean(a[box]) - bg
            rows.append((pid, day, enh, enh*w.wind_speed_100m, w.wind_speed_100m, bg, np.nanmean(a[rr < 15]) - np.nanmedian(a[(rr > 50) & (rr < 100)]), w.get("temperature_2m", np.nan)))
    print(f, len(rows), flush=True)
pd.DataFrame(rows, columns=["plant", "day", "enh", "flux", "ws", "bg", "simple", "temp"]).to_csv(out, index=False)
