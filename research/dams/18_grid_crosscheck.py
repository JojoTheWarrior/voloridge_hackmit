"""Grid cross-check: when hydro falls, does thermal rise on the same grid - and can the orbit-side hydro index see it?
Labels first (US Western Interconnection states from EIA-923; Brazil SIN from ONS), then the satellite-predicted hydro
anomaly against THERMAL generation. Year-over-year monthly differences (d12) remove seasonality and slow fleet trends.
Output results/grid_crosscheck.csv"""
import pandas as pd
import statsmodels.api as sm

from common import DATA, RESULTS

WEST = ["WA", "OR", "CA", "ID", "MT", "WY", "NV", "UT", "CO", "AZ", "NM"]
rows = []


def d12(s):
    return s - s.shift(12)


def report(scope, label, y, x, controls=None):
    df = pd.concat([y.rename("y"), x.rename("x")] + ([controls] if controls is not None else []), axis=1).dropna()
    X = sm.add_constant(df.drop(columns="y"))
    fit = sm.OLS(df.y, X).fit(cov_type="HAC", cov_kwds={"maxlags": 12})
    rows.append({"scope": scope, "test": label, "n_months": len(df), "r": df.y.corr(df.x), "slope_mwh_thermal_per_mwh_hydro": fit.params["x"],
                 "slope_se_hac": fit.bse["x"], "p_hac": fit.pvalues["x"], "r2": fit.rsquared})


# ---- US West, labels ----
g = pd.read_parquet(DATA / "core_eia923__monthly_generation_fuel.parquet", columns=["report_date", "plant_id_eia", "fuel_type_code_pudl", "prime_mover_code", "net_generation_mwh"])
pl = pd.read_parquet(DATA / "core_eia__entity_plants.parquet", columns=["plant_id_eia", "state"])
g = g.merge(pl, on="plant_id_eia")
g = g[g.state.isin(WEST) & (g.prime_mover_code != "PS")]
g["month"] = pd.to_datetime(g.report_date)
t = g.pivot_table(index="month", columns="fuel_type_code_pudl", values="net_generation_mwh", aggfunc="sum", observed=True)
t = t[t.index < "2026-01-01"]
fossil = t[["gas", "coal", "oil"]].sum(axis=1)
vre = t[["wind", "solar"]].sum(axis=1)
report("US West (11 states, EIA-923)", "labels: d12 fossil ~ d12 hydro", d12(fossil), d12(t.hydro))
report("US West (11 states, EIA-923)", "labels: + control d12 wind+solar", d12(fossil), d12(t.hydro),
       d12(vre).rename("vre"))

# ---- US West, orbit-side hydro index (leave-dams-out predictions -> MWh anomaly) ----
P = pd.read_parquet(RESULTS / "predictions_us_prereg_h0.parquet").query("design=='leave_dams_out'")
st = pd.read_csv(RESULTS / "dam_statics.csv")
P = P.merge(st[["gww_id", "state"]], on="gww_id")
P = P[P.state.isin(WEST)]
for col, lab in [("gbm_area+climate", "area+climate"), ("gbm_area", "area only"), ("gbm_climate", "climate only")]:
    sat = (P[col] * P.gen_mean).groupby(P.month).sum()
    n = P.groupby("month").gww_id.nunique()
    sat = sat[n >= 0.8 * n.max()]
    report("US West", f"orbit: d12 fossil ~ d12 satellite-predicted hydro anomaly ({lab}; unseen dams)", d12(fossil), d12(sat),
           d12(vre).rename("vre"))
    report("US West", f"orbit sanity: d12 actual West hydro ~ d12 satellite-predicted ({lab})", d12(t.hydro), d12(sat))

# ---- Brazil SIN, labels + zero-shot orbit index ----
o = pd.read_parquet(DATA / "ons" / "gen_monthly.parquet")
o = o[o.month < "2026-09-01"]
b = o.pivot_table(index="month", columns="nom_tipousina", values="mwh", aggfunc="sum")
hyd, thermal = b["HIDROELÉTRICA"], b["TÉRMICA"]
bvre = b[[c for c in b.columns if c in ("EOLIELÉTRICA", "FOTOVOLTAICA")]].sum(axis=1)
report("Brazil SIN (ONS)", "labels: d12 thermal ~ d12 hydro", d12(thermal), d12(hyd))
report("Brazil SIN (ONS)", "labels: + control d12 wind+solar", d12(thermal), d12(hyd), d12(bvre).rename("vre"))
B = pd.read_parquet(RESULTS / "predictions_brazil.parquet")
B = B[B.gww_id.isin(st[st.storage_dam & (st.truth == "ons")].gww_id)]
for col, lab in [("pred_gbm_area+climate", "area+climate"), ("pred_gbm_area", "area only")]:
    sat = (B[col] * B.gen_mean).groupby(B.month).sum()
    n = B.groupby("month").gww_id.nunique()
    sat = sat[n >= 0.8 * n.max()]
    report("Brazil SIN", f"orbit: d12 thermal ~ d12 satellite-predicted hydro anomaly ({lab}; zero-shot US model)", d12(thermal), d12(sat), d12(bvre).rename("vre"))
    report("Brazil SIN", f"orbit sanity: d12 actual SIN hydro ~ d12 satellite-predicted ({lab})", d12(hyd), d12(sat))
R = pd.DataFrame(rows)
R.to_csv(RESULTS / "grid_crosscheck.csv", index=False)
pd.set_option("display.width", 250)
print(R.round(3).to_string())
