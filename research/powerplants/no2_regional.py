"""Does aggregation rescue the weak per-plant daily signal? Sum of per-plant NO2 enhancements over a balancing authority vs EIA-930 fossil generation."""
import numpy as np, pandas as pd, glob, requests, time, os
from scipy.stats import pearsonr
PX = 0.035; HP = 30
tot = pd.read_csv("cems_2024_plant_totals.csv").groupby("plant_id_eia", as_index=False).sum(numeric_only=True)
pl = tot.merge(pd.read_csv("us_plant_candidates.csv")[["plant_id_eia", "plant_name_eia", "latitude", "longitude"]]).merge(pd.read_csv("plant_ba.csv")).dropna(subset=["latitude"])
pl = pl[(pl.nox_lbs_h >= 100) & pl.latitude.between(25.5, 48.5) & pl.longitude.between(-123, -68)]
bas = pl.groupby("ba").agg(n=("plant_id_eia", "size"), nox=("nox_lbs_h", "sum")); bas = bas[bas.n >= 4].sort_values("nox", ascending=False).head(16); pl = pl[pl.ba.isin(bas.index)]
print(bas.to_string())
if not os.path.exists("no2_regional_plant_daily.csv"):
    rows = []
    for f in sorted(glob.glob("grids/conus_no2_*.npz")):
        d = np.load(f); grid = d["grid"]; lon0, lat0, lon1, lat1 = d["bounds"]
        for p in pl.itertuples():
            c = int((p.longitude-lon0)/PX); r = int((lat1-p.latitude)/PX); win = grid[:, r-HP:r+HP+1, c-HP:c+HP+1].astype("float32")
            jj, ii = np.meshgrid(np.arange(-HP, HP+1), np.arange(-HP, HP+1)); rr = np.hypot(jj*PX*111.2*np.cos(np.radians(p.latitude)), ii*PX*111.2)
            core = win[:, rr < 15]; ann = win[:, (rr > 50) & (rr < 100)]
            ok = (np.isfinite(core).mean(1) > 0.7) & (np.isfinite(ann).mean(1) > 0.5)
            with np.errstate(all="ignore"): e = np.nanmean(core, 1) - np.nanmedian(ann, 1)
            rows += [(p.plant_id_eia, p.ba, str(dd), ee) for dd, ee, k in zip(d["days"], e, ok) if k]
        print(f, len(rows), flush=True)
    pd.DataFrame(rows, columns=["plant", "ba", "day", "simple"]).to_csv("no2_regional_plant_daily.csv", index=False)
x = pd.read_csv("no2_regional_plant_daily.csv", parse_dates=["day"])
g = pd.read_parquet("eia930_daily_fossil.parquet"); g["day"] = pd.to_datetime(g.day_local6); g = g[g.n >= 20]
gen = g.pivot_table(index=["ba", "day"], columns="src", values="mwh", aggfunc="sum").fillna(0); gen["fossil"] = gen.sum(axis=1); gen = gen.reset_index()
# BA temperature for NO2-lifetime correction (coefficient learned at plant level on CEMS, see no2_calibrate.py)
import json; B_T = json.load(open("no2_calibration.json"))["temp_coef_per_degC"]
if not os.path.exists("ba_temp.parquet"):
    out = []
    for ba, gg in pl.groupby("ba"):
        prm = dict(latitude=np.average(gg.latitude, weights=gg.nox_lbs_h), longitude=np.average(gg.longitude, weights=gg.nox_lbs_h),
                   start_date="2023-07-01", end_date="2026-06-30", daily="temperature_2m_mean", timezone="UTC")
        for _ in range(70):
            rj = requests.get("https://archive-api.open-meteo.com/v1/archive", params=prm, timeout=120).json()
            if "daily" in rj: break
            print("open-meteo:", str(rj)[:100], flush=True); time.sleep(120)
        r = rj["daily"]
        out.append(pd.DataFrame(dict(ba=ba, day=pd.to_datetime(r["time"]), temp=r["temperature_2m_mean"]))); time.sleep(3)
    pd.concat(out).to_parquet("ba_temp.parquet")
bt = pd.read_parquet("ba_temp.parquet")
res = []
for ba, xb in x.groupby("ba"):
    npl = pl[pl.ba == ba].plant_id_eia.nunique(); dly = xb.groupby("day").simple.agg(["mean", "size"]); dly = dly[dly["size"] >= max(2, 0.5*npl)]
    m = dly.rename(columns={"mean": "idx"}).reset_index().merge(gen[gen.ba == ba], on="day").merge(bt[bt.ba == ba], on="day")
    if len(m) < 150 or m.fossil.mean() <= 0: continue
    m["idx_tc"] = m.idx/np.exp(B_T*(m.temp-15))
    for tgt in ["fossil", "coal"]:
        if m[tgt].std() == 0: continue
        o = dict(ba=ba, n_plants=npl, target=tgt, n_days=len(m))
        for lab_, rule in [("daily", None), ("weekly", "W"), ("monthly", "MS")]:
            mm = m if rule is None else m.set_index("day").resample(rule).agg(idx=("idx", "mean"), idx_tc=("idx_tc", "mean"), y=(tgt, "mean"), k=("idx", "size")).rename(columns={"y": tgt}).query(f"k >= {3 if rule == 'W' else 8}").reset_index()
            o[f"r_{lab_}"] = pearsonr(mm.idx, mm[tgt])[0]; o[f"r_{lab_}_tempcorr"] = pearsonr(mm.idx_tc, mm[tgt])[0]; o[f"n_{lab_}"] = len(mm)
            if rule == "MS":                                                     # control: remove month-of-year climatology from both
                a = mm.idx_tc - mm.groupby(mm.day.dt.month).idx_tc.transform("mean"); b_ = mm[tgt] - mm.groupby(mm.day.dt.month)[tgt].transform("mean"); o["r_monthly_deseasonalised"] = pearsonr(a, b_)[0]
        res.append(o)
R = pd.DataFrame(res); R.to_csv("no2_regional_results.csv", index=False); pd.set_option("display.width", 250); print(R.round(2).to_string())
print(R.groupby("target")[[c for c in R if c.startswith("r_")]].median().round(2).to_string())
