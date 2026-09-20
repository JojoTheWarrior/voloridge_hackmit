"""EXPLORATORY -- NOT pre-registered, NOT in the BH family. Everything here was chosen after seeing the confirmatory results; p-values are uncorrected
and only descriptive. Outputs exploratory_results.csv, power.csv, case_studies.json."""
import json, numpy as np, pandas as pd
from pathlib import Path
import engine
H = Path(__file__).parent; D = H / "data"; PRE = json.load(open(H / "prereg.json"))
SM, SW = pd.read_parquet(D / "signals_monthly.parquet"), pd.read_parquet(D / "signals_weekly.parquet")
TM, TW = pd.read_parquet(D / "targets_monthly.parquet"), pd.read_parquet(D / "targets_weekly.parquet")
rows = []
def rec(eid, desc, o, **kw): rows.append({"id": eid, "description": desc, **{k: o.get(k) for k in ("n", "best_lag", "r", "maxstat_p", "circ_p", "r_train", "r_test", "p_test")}, **kw})

# E1 coincident co-movement (lag 0, latency ignored): does the market move WITH the physical anomaly at all?
for t in PRE["family"]:
    if t["tier"] == "market" and t["freq"] == "M" and t["signal"].endswith("_area"):
        rec("E1_" + t["id"], f"coincident lag0 {t['signal']}|{t['transform']} vs {t['target']}", engine.run_test(SM[f"{t['signal']}|{t['transform']}"], TM[t["target"]], [0], 0, "M", seed=11))
# E2 does the satellite add anything once official storage is known?
d = pd.concat([SM["brazil_seco_area|dz3"], SM["brazil_ear_seco|dz3"], TM["d3_logCMO_SE"]], axis=1).dropna(); d.columns = ["sat", "ear", "cmo"]
res = lambda a, b: a - np.polyval(np.polyfit(b, a, 1), b)
rows.append({"id": "E2", "description": "partial r(sat dz3, d3 logCMO | official EAR dz3), lag 0", "n": len(d), "r": float(np.corrcoef(res(d.sat, d.ear), res(d.cmo, d.ear))[0, 1]), "r_sat_only": float(d.sat.corr(d.cmo)), "r_ear_only": float(d.ear.corr(d.cmo))})
# E3 clean, non-overlapping prediction of the Brazilian marginal cost: signal at m -> log CMO change over the 3 months AFTER it is knowable
cmo = np.log1p(pd.read_parquet(D / "cmo_se_monthly.parquet").cmo_se)
for sig, L in [("brazil_seco_area", 1), ("brazil_ear_seco", 0)]:
    for tr in ("z", "dz3"):
        y = (cmo.shift(-3) - cmo)                                  # change from t to t+3, aligned at t
        rec(f"E3_{sig}_{tr}", f"{sig}|{tr} at m -> log(1+CMO) change m+{L}..m+{L+3} (non-overlapping with signal window)", engine.run_test(SM[f"{sig}|{tr}"], y, [0], L, "M", seed=13))
# E4 geography-matched US test: California reservoirs vs CAISO hydro (WECC hydro is dominated by the Columbia basin, which the pre-registered composite does not cover)
import pyarrow.dataset as ds
from signals import SCOUT930
t = ds.dataset(SCOUT930).to_table(filter=ds.field("balancing_authority_code_eia") == "CISO").to_pandas(); t["v"] = t.net_generation_adjusted_mwh.fillna(t.net_generation_reported_mwh)
src = t.generation_energy_source.astype(str).replace({"hydro_excluding_pumped_storage": "hydro", "pumped_storage": "hydro"})
c = t.groupby([t.datetime_utc.dt.to_period("M").dt.to_timestamp(), src]).v.sum().unstack(); c = c[(c.index >= "2018-07-01") & (c.index < "2026-09-01")] / 1e6
ds_ = lambda s: s - s.groupby(s.index.month).transform("mean")
z = pd.read_parquet(D / "z_uswest_area.parquet"); ca = z[["Shasta", "Oroville", "NewMelones", "DonPedro"]].mean(axis=1)
for nm, y in [("CISO hydro", ds_(c.hydro)), ("CISO gas", ds_(c.gas))]:
    rec("E4_z_" + nm, f"California 4-reservoir z LEVEL vs deseasonalised {nm} LEVEL (TWh), lag 0 (anomaly levels, both stationary by construction)", engine.run_test(ca, y, [0], 0, "M", seed=17))
    rec("E4_dz3_" + nm, f"California 4-reservoir dz3 vs d3 {nm} anomaly, lags 0-2", engine.run_test(ca.diff(3), y.diff(3), [0, 1, 2], 0, "M", seed=17))
w = pd.read_parquet(D / "wecc_monthly.parquet"); w = w[(w.index >= "2018-07-01") & (w.index < "2026-09-01")] / 1e6
rec("E4_wecc_hydro_fossil", "replication of scout: WECC deseasonalised hydro vs gas+coal, lag 0 (ground truth vs ground truth)", engine.run_test(ds_(w.hydro), ds_(w.gas + w.coal), [0], 0, "M", seed=17), slope=float(np.polyfit(ds_(w.hydro), ds_(w.gas + w.coal), 1)[0]))
pd.DataFrame(rows).to_csv(H / "exploratory_results.csv", index=False)

# E7 power: the |r| each confirmatory test needed to reach p<0.05 (95th pct of its own max-stat null) and, Bonferroni-ish, 0.05/53
engine.N_PERM = 4000; pw = []
for t in PRE["family"]:
    S, T = (SM, TM) if t["freq"] == "M" else (SW, TW)
    if t["target"] not in T: continue
    idx, xv, Y = engine.frame(S[f"{t['signal']}|{t['transform']}"].dropna(), T[t["target"]].dropna(), [t["latency"] + k for k in t["lags"]])
    R = np.nanmax(np.abs(engine.null_max(engine.surrogates(xv, 6 if t["freq"] == "M" else 8, 4000, np.random.default_rng(5)), Y)), axis=1)
    pw.append({"id": t["id"], "crit_r_p05": float(np.quantile(R, .95)), "crit_r_p001": float(np.quantile(R, .999))})
pd.DataFrame(pw).to_csv(H / "power.csv", index=False)

# E5/E8 case studies (n is tiny: description, not statistics)
P = pd.read_parquet(D / "yf_daily.parquet"); al = P["SHFE_AL"].dropna(); zy = SM["yunnan_area|z"]
cs = {"yunnan": [], "libya": []}
for m, note in PRE["case_study_events"]["yunnan_curtailments"].items():
    m0 = pd.Timestamp(m + "-01"); px = al.resample("ME").last(); px.index = px.index.to_period("M").to_timestamp()
    cs["yunnan"].append({"event_month": m, "note": note, "z_known_at_event (month m-2)": None if pd.isna(zy.get(m0 - pd.DateOffset(months=2))) else round(float(zy[m0 - pd.DateOffset(months=2)]), 2),
        "z_same_month": None if pd.isna(zy.get(m0)) else round(float(zy[m0]), 2), "shfe_al_ret_prev3m_%": round(100 * float(np.log(px[m0 - pd.DateOffset(months=1)] / px[m0 - pd.DateOffset(months=4)])), 1),
        "shfe_al_ret_event_month_%": round(100 * float(np.log(px[m0] / px[m0 - pd.DateOffset(months=1)])), 1), "shfe_al_ret_next3m_%": round(100 * float(np.log(px[m0 + pd.DateOffset(months=3)] / px[m0])), 1)})
fw = pd.read_parquet(D / "flare_weekly_clear.parquet").libya; bz = P["BZ=F"].dropna()
for d0, note in PRE["case_study_events"]["libya"].items():
    d0 = pd.Timestamp(d0 if len(d0) > 7 else d0 + "-15"); pre = fw[d0 - pd.Timedelta(weeks=8):d0 - pd.Timedelta(days=1)].mean(); post = fw[d0 + pd.Timedelta(weeks=2):d0 + pd.Timedelta(weeks=10)].mean()
    half = fw[d0 - pd.Timedelta(weeks=2):]; half = half[half < (pre + post) / 2]
    g = lambda a, b: round(100 * float(np.log(bz.asof(b) / bz.asof(a))), 1)
    cs["libya"].append({"event": str(d0.date()), "note": note, "flare_MW_pre8w": round(float(pre)), "flare_MW_post(2-10w)": round(float(post)), "change_%": round(100 * (post / pre - 1)), "first_week_below_half_move": str(half.index[0].date()) if len(half) and post < pre else None,
        "brent_ret_event_week_%": g(d0 - pd.Timedelta(days=3), d0 + pd.Timedelta(days=4)), "brent_ret_next4w_%": g(d0 + pd.Timedelta(days=4), d0 + pd.Timedelta(days=32))})
json.dump(cs, open(H / "case_studies.json", "w"), indent=1)
print(pd.DataFrame(rows).round(3).to_string()); print(json.dumps(cs, indent=1)); print(pd.DataFrame(pw).round(3).to_string())

# E9 sensor-outage robustness for flares (found when plotting: the Jul-Aug 2022 S-NPP safe-mode gap shows up as a 'collapse' in Libya AND the Algeria placebo)
fl = pd.read_parquet(D / "flare_weekly_clear.parquet"); lr = np.log(fl.libya.where(fl.libya > 0) / fl.algeria.where(fl.algeria > 0))
from signals import expanding_anom
a, _ = expanding_anom(lr.dropna(), lr.dropna().index.isocalendar().week.to_numpy(), 3); x = a.diff(2); x.index = x.index + pd.Timedelta(days=1)
ex = [{"id": "E9_" + t, "description": f"log(Libya/Algeria) flare ratio d2 -> {t}, lags 1-4 (controls common sensor/cloud artefacts)", **{k: v for k, v in engine.run_test(x, TW[t], [1, 2, 3, 4], 0, "W", seed=19).items() if k in ("n", "best_lag", "r", "maxstat_p", "circ_p", "r_train", "r_test", "p_test")}} for t in ["BZ=F", "d_BZ-CL_spread", "TANKERS(FRO,DHT)-^GSPC"]]
pd.concat([pd.read_csv(H / "exploratory_results.csv"), pd.DataFrame(ex)]).to_csv(H / "exploratory_results.csv", index=False); print(pd.DataFrame(ex).round(3).to_string())

# E10 Nordic price leg on the later sample (the pre-registered SYS series is only served for 2000-2010): NO2 area price 2011-2025
o = engine.run_test(SW["nve_fill|d1"], TW["dlog_NordPool_NO2"], [0, 1, 2, 3, 4], 0, "W", seed=23)
ex = [{"id": "E10_NO2", "description": "NVE filling anomaly d1 -> dlog Nord Pool NO2 weekly price 2011-2025, lags 0-4", **{k: o[k] for k in ("n", "best_lag", "r", "maxstat_p", "circ_p", "r_train", "r_test", "p_test")}, "r_by_lag": str(o["r_by_lag"])}]
pd.concat([pd.read_csv(H / "exploratory_results.csv"), pd.DataFrame(ex)]).to_csv(H / "exploratory_results.csv", index=False); print(pd.DataFrame(ex).round(3).to_string())
