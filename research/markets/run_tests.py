"""Run exactly the pre-registered family (prereg.json), its partial-out controls and the placebo batteries. Per-test results are cached so a late-arriving
dataset only adds its own rows; seeds are fixed per test id. Outputs results.csv, placebo_results.csv."""
import json, zlib, sys
import numpy as np, pandas as pd
from pathlib import Path
import engine
H = Path(__file__).parent; D = H / "data"; CACHE = D / "test_cache"; CACHE.mkdir(exist_ok=True)
PRE = json.load(open(H / "prereg.json"))
SIG = {"M": pd.read_parquet(D / "signals_monthly.parquet"), "W": pd.read_parquet(D / "signals_weekly.parquet")}
TGT = {"M": pd.read_parquet(D / "targets_monthly.parquet"), "W": pd.read_parquet(D / "targets_weekly.parquet")}
FAC = {"M": pd.read_parquet(D / "factors_monthly.parquet"), "W": pd.read_parquet(D / "factors_weekly.parquet")}
ENERGY = {"BZ=F", "NG=F", "d_BZ-CL_spread"}

def factors(target, freq):
    if target in ENERGY: cols = ["DX-Y.NYB"]                     # deviation from prereg, see DEVIATIONS: ^SPGSCI is ~60% energy, partialling it out of Brent removes the target itself
    elif target in {"SHFE_AL", "ALI=F", "HG=F"}: cols = ["^SPGSCI", "DX-Y.NYB", "000001.SS"]
    elif target == "USDZMW": cols = ["^SPGSCI", "DX-Y.NYB", "HG=F"]
    else: cols = ["^SPGSCI", "DX-Y.NYB"]
    return FAC[freq][cols]

def cached(key, fn):
    f = CACHE / (key.replace("/", "_").replace("|", "_") + ".json")
    if f.exists(): return json.loads(f.read_text())
    o = fn(); f.write_text(json.dumps(o)); return o

def one(t, signal=None, tag="main", partial=False):
    s = signal or t["signal"]; col = f"{s}|{t['transform']}"
    if col not in SIG[t["freq"]] or t["target"] not in TGT[t["freq"]]: return None
    x, y = SIG[t["freq"]][col], TGT[t["freq"]][t["target"]]
    if partial: y = engine.residualise(y, factors(t["target"], t["freq"]))
    key = f"{tag}_{t['id']}_{s}"
    return cached(key, lambda: engine.run_test(x, y, t["lags"], t["latency"], t["freq"], seed=zlib.crc32(key.encode()), year_shuffle=(t["freq"] == "M" and tag == "main")))

rows = []
for t in PRE["family"]:
    o = one(t)
    if o is None: print("MISSING DATA", t["id"]); continue
    row = {**{k: t[k] for k in ("id", "tier", "signal", "transform", "target", "expected_sign", "freq", "latency")}, "lags": str(t["lags"]), **o}
    if t["tier"] == "market":
        p = one(t, tag="partial", partial=True); row.update(r_partial=p["r"], lag_partial=p["best_lag"], p_partial=p["maxstat_p"])
    rows.append(row); print(t["id"], round(o["r"], 3), o["maxstat_p"], flush=True)
R = pd.DataFrame(rows)
R["bh_q"] = engine.bh(R.maxstat_p); R["sign_ok"] = (R.expected_sign == 0) | (np.sign(R.r) == R.expected_sign)
R["oos_same_sign"] = np.sign(R.r_train) == np.sign(R.r_test)
R["survives_bh05"] = (R.bh_q <= 0.05) & R.sign_ok
first = ["id", "tier", "signal", "transform", "target", "expected_sign", "freq", "latency", "lags", "n", "best_lag", "r", "beta", "spearman", "perm_p", "maxstat_p", "bh_q", "sign_ok", "survives_bh05", "circ_p", "yearshuffle_p", "r_partial", "p_partial", "r_train", "r_test", "p_test", "oos_same_sign"]
R[first + [c for c in R if c not in first]].to_csv(H / "results.csv", index=False)
print(f"\nFAMILY: {len(R)} of {PRE['family_size']} run; p<0.05 uncorrected: {(R.maxstat_p < .05).sum()}; BH q<=0.05: {(R.bh_q <= .05).sum()}; and sign ok: {R.survives_bh05.sum()}")

# placebos (outside the family)
P = []
for t in PRE["family"]:
    if t["signal"] in ("yunnan_area", "brazil_seco_area", "zambia_itt_area", "uswest_area"):
        for pl in ("placebo_argyle", "placebo_guri", "placebo_volta", "placebo_toktogul"):
            o = one(t, signal=pl, tag="placebo"); P.append({"id": t["id"], "placebo_signal": pl, "target": t["target"], "tier": t["tier"], **{k: o[k] for k in ("n", "best_lag", "r", "maxstat_p")}})
for tid, pl in [("F1", "algeria_flare"), ("R1", "danube_stress"), ("R1", "loire_stress")]:
    t = next(x for x in PRE["family"] if x["id"] == tid); o = one(t, signal=pl, tag="placebo")
    P.append({"id": tid, "placebo_signal": pl, "target": t["target"], "tier": t["tier"], **{k: o[k] for k in ("n", "best_lag", "r", "maxstat_p")}})
P = pd.DataFrame(P); P.to_csv(H / "placebo_results.csv", index=False)
print(f"PLACEBOS: {len(P)} tests; p<0.05: {(P.maxstat_p < .05).sum()} ({(P.maxstat_p < .05).mean():.1%}); p<0.01: {(P.maxstat_p < .01).sum()}")
