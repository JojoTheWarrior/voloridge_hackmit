"""Per-dam monthly panel: satellite area + generation truth (US EIA-923, Brazil ONS) + statics, with the pre-registered
label-free storage filter. One unit == one reservoir (all matched plants on it are summed).
Outputs results/dam_statics.csv, results/panel_monthly.parquet, results/filter_report.csv."""
import numpy as np
import pandas as pd

from common import DATA, RESULTS

MIN_KM2, MIN_MONTHS, MIN_CV = 1.0, 120, 0.03   # preregistration.json

m = pd.read_parquet(DATA / "matches.parquet").query("status=='matched'").copy()
m["gww_id"] = m.gww_id.astype(int)
m["has_pumped_storage"] = m.has_pumped_storage.fillna(False).astype(bool)  # only known for the US
area = pd.read_parquet(DATA / "area_monthly.parquet")
area = area[(area.month >= "2001-01-01")]

# ---------- generation truth ----------
g = pd.read_parquet(DATA / "core_eia923__monthly_generation_fuel.parquet",
                    columns=["report_date", "plant_id_eia", "energy_source_code", "prime_mover_code", "net_generation_mwh"])
g = g[(g.energy_source_code == "WAT") & (g.prime_mover_code == "HY")]
g = g.groupby(["plant_id_eia", "report_date"], as_index=False).net_generation_mwh.sum()
# Annual-only respondents carry EIA-imputed monthly shapes -> not truth. The per-year code is only populated reliably from
# 2023 (before that 'AM' respondents were coded 'A'), so use each plant's latest code.
n0 = len(g)
keep = "US" + g.plant_id_eia.astype(str)
g = g[keep.isin(m.loc[m.reporting_frequency.isin(["M", "AM"]), "plant_id"])]
print(f"EIA plant-months kept after dropping annual-only reporters (matched plants only): {len(g)}/{n0}")
g["plant_id"] = "US" + g.plant_id_eia.astype(str)
us = g.rename(columns={"report_date": "month", "net_generation_mwh": "mwh"})[["plant_id", "month", "mwh"]]
us["month"] = pd.to_datetime(us.month)

ons_fn = DATA / "ons" / "gen_monthly.parquet"
br = pd.DataFrame(columns=["plant_id", "month", "mwh"])
if ons_fn.exists():
    o = pd.read_parquet(ons_fn)
    o = o[o.nom_tipousina.str.contains("HIDRO", na=False)].groupby(["ceg", "month"], as_index=False).mwh.sum()
    br = o.merge(m.loc[m.truth == "ons", ["plant_id", "ceg"]].drop_duplicates("ceg"), on="ceg")[["plant_id", "month", "mwh"]]

gen = pd.concat([us, br]).merge(m[["plant_id", "gww_id", "has_pumped_storage"]], on="plant_id")
gen = gen[~gen.has_pumped_storage]
# a reservoir-month is valid only if every plant that normally reports on that reservoir reported
npl = gen.groupby("gww_id").plant_id.nunique().rename("n_plants")
gm = gen.groupby(["gww_id", "month"]).agg(mwh=("mwh", "sum"), n_rep=("plant_id", "nunique")).reset_index().merge(npl, on="gww_id")
gm = gm[gm.n_rep == gm.n_plants]

# ---------- statics ----------
def wavg(x, w):
    ok = x.notna() & w.notna()
    return np.average(x[ok], weights=w[ok]) if ok.any() and w[ok].sum() > 0 else np.nan


rows = []
for gid, d in m[~m.has_pumped_storage].groupby("gww_id"):
    big = d.sort_values("capacity_mw", ascending=False).iloc[0]
    rows.append({"gww_id": gid, "name": big.plant_name, "reservoir_name": big.gww_name if pd.notna(big.gww_name) else big.Lake_name,
                 "country": big.country, "truth": big.truth, "lat": big.lat, "lon": big.lon, "n_plants": len(d),
                 "capacity_mw": d.capacity_mw.sum(), "match_method": big.match_method, "gww_poly_km2": big.gww_poly_km2,
                 "res_time_days": big.Res_time, "depth_avg_m": big.Depth_avg, "vol_mcm": big.Vol_total, "dis_avg_m3s": big.Dis_avg,
                 "elevation_m": big.Elevation, "wshd_km2": big.Wshd_area, "head_m": wavg(d.glo_head_m, d.capacity_mw),
                 "dam_height_m": wavg(d.glo_dam_height_m, d.capacity_mw), "glo_plant_type": big.glo_plant_type,
                 "ons_tipo": big.get("ons_tipo"), "ba": big.get("ba"), "state": big.get("state")})
st = pd.DataFrame(rows)

a = area.dropna(subset=["area_km2"])
a = a[a.month < "2026-01-01"]
q = a.groupby("gww_id").area_km2.agg(n_area_months="count", area_mean="mean", area_sd="std",
                                     area_p05=lambda s: s.quantile(.05), area_p95=lambda s: s.quantile(.95)).reset_index()
q["area_cv"] = q.area_sd / q.area_mean
q["area_range_rel"] = (q.area_p95 - q.area_p05) / q.area_mean
st = st.merge(q, on="gww_id", how="left")
st["pass_size"] = st.gww_poly_km2 >= MIN_KM2
st["pass_months"] = st.n_area_months >= MIN_MONTHS
st["pass_cv"] = st.area_cv >= MIN_CV
st["storage_dam"] = st.pass_size & st.pass_months & st.pass_cv
st.to_csv(RESULTS / "dam_statics.csv", index=False)

rep = st.groupby("truth").agg(reservoirs=("gww_id", "size"), pass_size=("pass_size", "sum"), pass_months=("pass_months", "sum"),
                              pass_cv=("pass_cv", "sum"), storage_dam=("storage_dam", "sum"),
                              capacity_gw=("capacity_mw", lambda s: s.sum() / 1e3)).reset_index()
rep["storage_capacity_gw"] = st[st.storage_dam].groupby("truth").capacity_mw.sum().reindex(rep.truth).values / 1e3
rep.to_csv(RESULTS / "filter_report.csv", index=False)
print(rep.to_string())
# independent label check of the satellite-only filter
for col in ["glo_plant_type", "ons_tipo"]:
    print(pd.crosstab(st[col], st.storage_dam))

panel = area.merge(gm[["gww_id", "month", "mwh"]], on=["gww_id", "month"], how="left").merge(
    st[["gww_id", "truth", "country", "capacity_mw", "storage_dam"]], on="gww_id")
panel["cf"] = panel.mwh / (panel.capacity_mw * panel.month.dt.days_in_month * 24)
panel.to_parquet(RESULTS / "panel_monthly.parquet")
ok = panel[panel.storage_dam & panel.mwh.notna()]
print("storage dams with generation truth:", ok.groupby("truth").gww_id.nunique().to_dict(), "dam-months:", len(ok))
