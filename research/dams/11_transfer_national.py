"""Out-of-country transfer at national scale: capacity-weighted satellite prediction vs Ember national hydro generation.

National hydro fleets grow, so the truth is converted to a capacity factor (Ember annual hydro GW, interpolated) before
taking anomalies against the country's own seasonal normal. Monthly where Ember has monthly data, annual otherwise.
Outputs results/predictions_world.parquet, results/transfer_national_{monthly,annual}.csv"""
import numpy as np
import pandas as pd
import pycountry

from apply_model import predict
from common import DATA, RESULTS
from features import load_inputs

MODELS = {"area_only": "pred_gbm_area", "climate_only": "pred_gbm_climate", "area+climate": "pred_gbm_area+climate"}
FIX = {"Russia": "RUS", "Turkey": "TUR", "Iran": "IRN", "Vietnam": "VNM", "Laos": "LAO", "South Korea": "KOR", "North Korea": "PRK",
       "Bolivia": "BOL", "Venezuela": "VEN", "Tanzania": "TZA", "Syria": "SYR", "Democratic Republic of the Congo": "COD",
       "Congo": "COG", "Ivory Coast": "CIV", "Cote d'Ivoire": "CIV", "Macedonia": "MKD", "Czech Republic": "CZE", "USA": "USA",
       "United States of America": "USA", "BRA": "BRA", "Myanmar": "MMR", "Kosovo": "XKX", "Swaziland": "SWZ", "Taiwan": "TWN"}


def iso3(name):
    if name in FIX:
        return FIX[name]
    try:
        return pycountry.countries.lookup(name).alpha_3
    except LookupError:
        return None


panel, st, clim = load_inputs()
st["iso3"] = st.country.map(iso3)
print("unmapped countries:", sorted(st[st.iso3.isna()].country.unique()))
mon = st[st.storage_dam]
P = predict(panel[panel.gww_id.isin(mon.gww_id)], st, clim)
P = P.merge(mon[["gww_id", "iso3", "name"]], on="gww_id")
P.to_parquet(RESULTS / "predictions_world.parquet")

# national satellite index: capacity-weighted mean of dam-level predicted anomalies
w = P.assign(w=P.capacity_mw.fillna(0))
cols = list(MODELS.values()) + ["a0"]
nat = w.groupby(["iso3", "month"]).apply(lambda d: pd.Series({**{c: np.average(d[c], weights=d.w) if d.w.sum() > 0 else np.nan for c in cols},
                                                              "mw_reporting": d.w.sum(), "n_dams": len(d)})).reset_index()
tot = mon.groupby("iso3").capacity_mw.sum().rename("mw_monitored")
nat = nat.merge(tot, on="iso3")
nat = nat[nat.mw_reporting >= 0.6 * nat.mw_monitored]

yr = pd.read_parquet(DATA / "ember" / "yearly_country.parquet")
em = pd.read_parquet(DATA / "ember" / "hydro_monthly.parquet").rename(columns={"date": "month"})
em["month"] = pd.to_datetime(em.month)
em["year"] = em.month.dt.year
em = em.merge(yr[["iso3", "year", "hydro_gw"]], on=["iso3", "year"], how="left")
em["hydro_gw"] = em.groupby("iso3").hydro_gw.transform(lambda s: s.interpolate(limit_direction="both"))
em["cf"] = em.hydro_twh * 1e3 / (em.hydro_gw * em.month.dt.days_in_month * 24)
em = em[(em.month >= "2001-01-01") & em.cf.notna() & np.isfinite(em.cf)]
cm = em.groupby(["iso3", em.month.dt.month]).cf.transform("mean")
em["y_nat"] = (em.cf - cm) / em.groupby("iso3").cf.transform("mean")

rows = []
J = nat.merge(em[["iso3", "month", "y_nat"]], on=["iso3", "month"])
for c, d in J.groupby("iso3"):
    if len(d) < 60 or d.n_dams.median() < 3:
        continue
    ann = d.assign(y=d.month.dt.year).groupby("y").agg({**{v: "mean" for v in MODELS.values()}, "y_nat": "mean", "month": "size"}).query("month>=10")
    r = {"iso3": c, "n_months": len(d), "n_dams": int(d.n_dams.median()), "mw_monitored": d.mw_monitored.iloc[0]}
    for k, v in MODELS.items():
        r[f"r_monthly_{k}"] = d[v].corr(d.y_nat)
        r[f"r_annual_{k}"] = ann[v].corr(ann.y_nat) if len(ann) >= 8 else np.nan
    r["r_monthly_raw_area_anom"] = d.a0.corr(d.y_nat)
    rows.append(r)
M = pd.DataFrame(rows)
cap = yr.groupby("iso3").hydro_gw.last()
M["monitored_share_of_hydro_capacity"] = M.mw_monitored / 1e3 / M.iso3.map(cap)
M.sort_values("r_monthly_area+climate", ascending=False).round(3).to_csv(RESULTS / "transfer_national_monthly.csv", index=False)
print(M.sort_values("r_monthly_area+climate", ascending=False).round(2).to_string())
print("median r (monthly):", M.filter(like="r_monthly").median().round(3).to_dict())
print("median r (annual):", M.filter(like="r_annual").median().round(3).to_dict())

# annual-only countries (no Ember monthly series): capacity factor anomaly vs prior-5-year mean
yr["cf"] = yr.hydro_twh * 1e3 / (yr.hydro_gw * 8766)
yr["y_nat"] = yr.groupby("iso3").cf.transform(lambda s: s / s.rolling(5, min_periods=3).mean().shift(1) - 1)
na = nat.assign(year=nat.month.dt.year).groupby(["iso3", "year"]).agg({**{v: "mean" for v in MODELS.values()}, "month": "size", "n_dams": "median"}).query("month>=10").reset_index()
JA = na.merge(yr[["iso3", "year", "y_nat", "hydro_twh"]], on=["iso3", "year"]).dropna(subset=["y_nat"])
rows = []
for c, d in JA.groupby("iso3"):
    if len(d) < 10 or c in set(M.iso3):
        continue
    # Ember back-fills some countries with repeated values; flag those series rather than trust them
    flat = (d.hydro_twh.diff().abs() < 1e-9).mean()
    rows.append({"iso3": c, "n_years": len(d), "n_dams": int(d.n_dams.median()), "share_repeated_truth_values": flat,
                 **{f"r_annual_{k}": d[v].corr(d.y_nat) for k, v in MODELS.items()}})
A = pd.DataFrame(rows)
A.round(3).to_csv(RESULTS / "transfer_national_annual.csv", index=False)
print(A.round(2).to_string())
