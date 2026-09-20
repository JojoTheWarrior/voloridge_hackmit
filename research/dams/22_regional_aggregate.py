"""Does dam-level noise average out? Regional aggregation of leave-dams-out predictions (every prediction comes from a
model that never saw that dam) vs (a) the summed generation of the same monitored dams and (b) ALL EIA-923 hydro
generation in the region, including plants with no monitored reservoir. Anomalies in MWh, then as % of regional normal.
Output results/regional_aggregate.csv, results/regional_aggregate_series.csv"""
import pandas as pd

from common import DATA, RESULTS

REGIONS = {"California": ["CA"], "Pacific Northwest": ["WA", "OR", "ID", "MT"], "Colorado basin / Southwest": ["AZ", "NV", "UT", "CO", "NM", "WY"],
           "Southeast (TVA + Carolinas + AL/GA)": ["TN", "AL", "GA", "NC", "SC", "KY"], "Missouri / Plains": ["ND", "SD", "NE", "OK", "AR", "MO", "TX", "KS"],
           "Northeast": ["NY", "NH", "VT", "ME", "MA", "CT", "PA"]}
PALL = pd.read_parquet(RESULTS / "predictions_us_prereg_h0.parquet")
st = pd.read_csv(RESULTS / "dam_statics.csv")
PALL = PALL.merge(st[["gww_id", "state"]], on="gww_id")
g = pd.read_parquet(DATA / "core_eia923__monthly_generation_fuel.parquet", columns=["report_date", "plant_id_eia", "energy_source_code", "prime_mover_code", "net_generation_mwh"])
g = g[(g.energy_source_code == "WAT") & (g.prime_mover_code == "HY")].merge(pd.read_parquet(DATA / "core_eia__entity_plants.parquet", columns=["plant_id_eia", "state"]), on="plant_id_eia")
g["month"] = pd.to_datetime(g.report_date)
MODELS = {"area only": "gbm_area", "climate only": "gbm_climate", "area+climate": "gbm_area+climate", "damped persistence, 3-month-old label": "damped_persistence_lag3",
          "area+climate+3-month-old label": "gbm_persist3+area+climate"}
rows, series = [], []
for design, reg, states in [(dz, r, s) for dz in ("leave_dams_out", "strict") for r, s in REGIONS.items()]:
    P = PALL[PALL.design == design]  # strict = unseen dams AND unseen years (2019-2025, climatology from <=2018)
    d = P[P.state.isin(states)]
    n = d.groupby("month").gww_id.nunique()
    ok = n[n >= 0.8 * n.max()].index
    d = d[d.month.isin(ok)]
    norm = d.groupby("month").gen_mean.sum()
    obs = (d.y * d.gen_mean).groupby(d.month).sum() / norm
    allh = g[g.state.isin(states) & (g.month < "2026-01-01")].groupby("month").net_generation_mwh.sum()
    ref = allh[allh.index <= "2018-12-01"] if design == "strict" else allh
    alla = (allh - allh.index.month.map(ref.groupby(ref.index.month).mean())) / ref.mean()
    r = {"design": design, "region": reg, "n_dams": int(n.max()), "n_months": len(obs), "monitored_share_of_regional_hydro_mwh": d.groupby("month").mwh.sum().sum() / allh.reindex(ok).sum()}
    for lab, col in MODELS.items():
        hat = (d[col] * d.gen_mean).groupby(d.month).sum() / norm
        r[f"r_monitored [{lab}]"] = obs.corr(hat)
        r[f"r_all_regional_hydro [{lab}]"] = alla.reindex(hat.index).corr(hat)
        if lab == "area+climate":
            series.append(pd.DataFrame({"design": design, "region": reg, "month": hat.index, "predicted_anom": hat.values,
                                        "actual_all_regional_hydro_anom": alla.reindex(hat.index).values}))
    rows.append(r)
R = pd.DataFrame(rows)
R.to_csv(RESULTS / "regional_aggregate.csv", index=False)
pd.concat(series).to_csv(RESULTS / "regional_aggregate_series.csv", index=False)
pd.set_option("display.width", 250)
print(R.set_index(["design", "region"]).round(2).T.to_string())
