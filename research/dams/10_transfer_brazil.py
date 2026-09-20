"""Zero-shot transfer: the US-trained model scored against Brazil ONS actual per-plant generation.
Also scores satellite area against ONS's own gauge (useful volume %) as a storage sanity check, and splits results by
ONS's run-of-river / storage label. Outputs results/transfer_brazil_{skill,per_dam}.csv, predictions_brazil.parquet."""
import numpy as np
import pandas as pd

from apply_model import predict
from common import DATA, RESULTS
from features import load_inputs
from scoring import metrics

panel, st, clim = load_inputs()
br = st[(st.truth == "ons")]
print("ONS reservoirs matched to GWW:", len(br), "| pass storage filter:", int(br.storage_dam.sum()))
P = predict(panel[panel.gww_id.isin(br.gww_id)], st, clim)
P = P[(P.month < "2026-01-01")].dropna(subset=["y"])
P["y_lag1"], P["y_lag3"] = P.groupby("gww_id").y.shift(1), P.groupby("gww_id").y.shift(3)
P = P.dropna(subset=["y_lag1", "y_lag3"])

us_fit = pd.read_parquet(RESULTS / "predictions_us_prereg_h0.parquet").query("design=='leave_dams_out'")
slope = np.polyfit(us_fit.a0, us_fit.y, 1)   # the US pooled univariate line, applied unchanged


def table(d, label):
    pred = pd.DataFrame({"climatology": 0.0, "persistence_lag1 (needs labels)": d.y_lag1, "area_linear_pooled (US slope)": np.polyval(slope, d.a0),
                         "gbm_area": d.pred_gbm_area, "gbm_climate": d.pred_gbm_climate, "gbm_area+climate": d["pred_gbm_area+climate"]}, index=d.index)
    return metrics(d, pred, label)


rows = table(P[P.gww_id.isin(br[br.storage_dam].gww_id)], "Brazil zero-shot: all filtered storage reservoirs")
for tipo, ids in br[br.storage_dam].groupby("ons_tipo").gww_id:
    rows += table(P[P.gww_id.isin(ids)], f"Brazil zero-shot: ONS label = {tipo}")
carry = br[br.storage_dam & (br.res_time_days >= 100) & (br.gww_poly_km2 >= 10)]
rows += table(P[P.gww_id.isin(carry.gww_id)], "Brazil zero-shot: carry-over subset (res time >= 100 d, >= 10 km2)")
sk = pd.DataFrame(rows)
sk.to_csv(RESULTS / "transfer_brazil_skill.csv", index=False)
print(sk.round(3).to_string())

# storage sanity check against ONS gauges
h = pd.read_parquet(DATA / "ons" / "hidro_monthly.parquet")
m = pd.read_parquet(DATA / "matches.parquet").query("truth=='ons' and status=='matched'")
m["gww_id"] = m.gww_id.astype(int)
h = h.merge(m[["ons_reservatorio", "gww_id"]].drop_duplicates("ons_reservatorio"), left_on="nom_reservatorio", right_on="ons_reservatorio")
z = panel.merge(h[["gww_id", "month", "val_volumeutilcon", "val_nivelmontante", "val_vazaoturbinada", "val_vazaoafluente"]], on=["gww_id", "month"])
per = P.groupby("gww_id").apply(lambda d: pd.Series({
    "n_months": len(d), "r_gen_area_linear": np.corrcoef(d.y, d.a0)[0, 1], "r_gen_gbm_area": np.corrcoef(d.y, d.pred_gbm_area)[0, 1],
    "r_gen_gbm_climate": np.corrcoef(d.y, d.pred_gbm_climate)[0, 1], "r_gen_gbm_all": np.corrcoef(d.y, d["pred_gbm_area+climate"])[0, 1]})).reset_index()
lvl = z.dropna(subset=["area_km2", "val_volumeutilcon"]).groupby("gww_id").apply(
    lambda d: pd.Series({"r_area_vs_gauge_volume": d.area_km2.corr(d.val_volumeutilcon) if len(d) > 36 and d.val_volumeutilcon.std() > 0 else np.nan,
                         "gauge_volume_sd_pct": d.val_volumeutilcon.std()})).reset_index()
per = per.merge(lvl, on="gww_id", how="left").merge(br, on="gww_id")
per.to_csv(RESULTS / "transfer_brazil_per_dam.csv", index=False)
print(per.groupby("ons_tipo")[["r_area_vs_gauge_volume", "r_gen_area_linear", "r_gen_gbm_all"]].median().round(2))
P.to_parquet(RESULTS / "predictions_brazil.parquet")
