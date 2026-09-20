"""Engine self-tests on synthetic data: calibration under the null (incl. autocorrelated signal), power on a planted lead, no look-ahead, BH."""
import numpy as np, pandas as pd, engine
engine.N_PERM = 1000
idx = pd.date_range("2000-01-01", periods=240, freq="MS")
def ar1(n, phi, rng):
    e = rng.standard_normal(n); x = np.zeros(n)
    for i in range(1, n): x[i] = phi * x[i - 1] + e[i]
    return x
def test_null_calibration():
    ps = []
    for s in range(200):
        rng = np.random.default_rng(s)
        x = pd.Series(ar1(240, 0.9, rng), idx); y = pd.Series(ar1(240, 0.3, rng), idx)
        ps.append(engine.run_test(x, y, [1, 2, 3], 1, "M", seed=s)["maxstat_p"])
    rate = np.mean(np.array(ps) < 0.05); print("null rejection rate @0.05:", rate); assert rate < 0.10
def test_power_and_lag():
    rng = np.random.default_rng(1); x = pd.Series(rng.standard_normal(240), idx)
    y = 0.5 * x.shift(3) + pd.Series(rng.standard_normal(240), idx)           # y_t depends on x_{t-3} = latency 1 + lag 2
    o = engine.run_test(x, y, [1, 2, 3], 1, "M"); print(o["best_lag"], round(o["r"], 2), o["maxstat_p"], o["r_test"], o["p_test"])
    assert o["best_lag"] == 2 and o["maxstat_p"] < 0.01 and o["p_test"] < 0.05
def test_no_lookahead():
    ps = []                                                                    # contemporaneous + target-LEADS-signal dependence must be invisible
    for s in range(80):
        rng = np.random.default_rng(100 + s); x = pd.Series(rng.standard_normal(240), idx)
        y = 0.9 * x + 0.9 * x.shift(-2) + 0.1 * pd.Series(rng.standard_normal(240), idx)
        ps.append(engine.run_test(x, y, [1, 2, 3], 1, "M", seed=s)["maxstat_p"])
    rate = np.mean(np.array(ps) < 0.05); print("look-ahead rejection rate @0.05:", rate); assert rate < 0.12
def test_nan_gaps():
    rng = np.random.default_rng(3); x = pd.Series(rng.standard_normal(240), idx); y = 0.6 * x.shift(1) + pd.Series(rng.standard_normal(240), idx)
    x.iloc[50:70] = np.nan; y.iloc[100:110] = np.nan
    o = engine.run_test(x.dropna(), y.dropna(), [1, 2], 0, "M"); assert o["best_lag"] == 1 and o["maxstat_p"] < 0.01 and o["n"] < 215
def test_bh():
    q = engine.bh([0.001, 0.04, 0.03, 0.5]); assert np.allclose(q, [0.004, 0.0533333, 0.0533333, 0.5], atol=1e-6)
def test_residualise():
    rng = np.random.default_rng(4); f = pd.DataFrame({"f": rng.standard_normal(240)}, idx); y = 2 * f.f + pd.Series(rng.standard_normal(240), idx)
    assert abs(engine.residualise(y, f).corr(f.f)) < 1e-10
if __name__ == "__main__":
    for k, v in list(globals().items()):
        if k.startswith("test_"): v(); print("ok", k)
