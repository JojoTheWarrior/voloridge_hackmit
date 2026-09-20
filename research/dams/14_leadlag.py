"""Does the reservoir deficit LEAD or LAG the generation deficit? Cross-correlation of area anomaly(t) with generation
anomaly(t+k) per dam (US + Brazil truth), summarised by residence time. k > 0 means orbit leads generation.
Output results/leadlag_per_dam.csv, results/leadlag_summary.csv"""
import pandas as pd

from common import RESULTS
from features import build, load_inputs

panel, st, clim = load_inputs()
ids = st[st.storage_dam & st.truth.isin(["eia923", "ons"])].gww_id
F = build(panel[panel.gww_id.isin(ids)], st, clim).dropna(subset=["a0"])
F = F[F.month < "2026-01-01"]
LAGS = range(-12, 13)
rows = []
for gid, d in F.groupby("gww_id"):
    d = d.set_index("month").asfreq("MS")
    if d.y.notna().sum() < 120:
        continue
    # 3-month smoothing on both sides so month-to-month noise does not decide the peak
    a, y = d.a0.rolling(3, min_periods=2).mean(), d.y.rolling(3, min_periods=2).mean()
    cc = {k: a.corr(y.shift(-k)) for k in LAGS}
    best = max(cc, key=lambda k: cc[k])
    rows.append({"gww_id": gid, "best_lag_months": best, "r_best": cc[best], "r_lag0": cc[0], "r_lead6": cc[6], "r_lag_minus6": cc[-6]})
L = pd.DataFrame(rows).merge(st[["gww_id", "name", "truth", "capacity_mw", "res_time_days", "gww_poly_km2", "area_cv"]], on="gww_id")
L.to_csv(RESULTS / "leadlag_per_dam.csv", index=False)
sig = L[L.r_best >= 0.3]
bins = pd.cut(sig.res_time_days, [0, 30, 100, 365, 1000, 1e5])
S = sig.groupby(bins).agg(n=("gww_id", "size"), median_best_lag=("best_lag_months", "median"), share_area_leads=("best_lag_months", lambda s: (s > 0).mean()),
                          share_area_lags=("best_lag_months", lambda s: (s < 0).mean()), median_r_best=("r_best", "median"),
                          median_r_lead6=("r_lead6", "median"), median_r_lagminus6=("r_lag_minus6", "median")).reset_index()
S.to_csv(RESULTS / "leadlag_summary.csv", index=False)
print("dams with any usable relation (r_best >= 0.3):", len(sig), "of", len(L))
print(S.round(2).to_string())
print(sig.groupby("truth").best_lag_months.describe().round(1))
