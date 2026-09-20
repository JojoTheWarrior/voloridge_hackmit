"""dams_latest.geojson / .csv: every monitored storage reservoir with its latest satellite state and the US-trained
predicted generation anomaly (fraction of the dam's own seasonal normal) with a 10-90 % band. Feeds the map frontend."""
import json

import numpy as np
import pandas as pd

from common import RESULTS, ROOT

P = pd.read_parquet(RESULTS / "predictions_world.parquet")
st = pd.read_csv(RESULTS / "dam_statics.csv")
P = P[P.interp != True].sort_values("month")  # noqa: E712  latest OBSERVED month, not an interpolated one
last = P.groupby("gww_id").tail(1)
last = last[last.month >= "2025-09-01"]
m3 = P.groupby("gww_id").tail(3).groupby("gww_id")[["a0", "pred_gbm_area+climate"]].mean().add_suffix("_3mo")
d = last.merge(m3, on="gww_id").merge(st[["gww_id", "reservoir_name", "lat", "lon", "res_time_days", "gww_poly_km2", "match_method"]], on="gww_id")
d["confidence"] = np.where((d.res_time_days >= 100) & (d.gww_poly_km2 >= 10), "carry-over storage (validated class)",
                           np.where(d.res_time_days.isna(), "unknown residence time", "short residence time (weak area signal)"))
out = pd.DataFrame({"gww_id": d.gww_id, "name": d.name, "reservoir": d.reservoir_name, "country": d.country, "iso3": d.iso3, "lat": d.lat, "lon": d.lon,
                    "capacity_mw": d.capacity_mw.round(1), "latest_month": d.month.dt.strftime("%Y-%m"), "area_km2": d.area_km2.round(2),
                    "area_anomaly": d.a0.round(3), "area_anomaly_3mo": d.a0_3mo.round(3), "precip_12mo_anomaly": d.p12.round(3),
                    "pred_gen_anomaly": d["pred_gbm_area+climate"].round(3), "pred_gen_anomaly_lo": d.pred_lo.round(3),
                    "pred_gen_anomaly_hi": d.pred_hi.round(3), "pred_gen_anomaly_3mo": d["pred_gbm_area+climate_3mo"].round(3),
                    "has_generation_truth": d.truth.isin(["eia923", "ons"]), "confidence": d.confidence, "match_method": d.match_method})
out.to_csv(ROOT / "dams_latest.csv", index=False)
feats = [{"type": "Feature", "geometry": {"type": "Point", "coordinates": [r.lon, r.lat]},
          "properties": {k: (None if isinstance(v, float) and np.isnan(v) else v) for k, v in r._asdict().items() if k not in ("lat", "lon", "Index")}}
         for r in out.itertuples()]
(ROOT / "dams_latest.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": feats}))
print(len(out), "dams;", out.country.nunique(), "countries; latest months:", out.latest_month.value_counts().head(4).to_dict())
print(out.sort_values("pred_gen_anomaly").head(12)[["name", "country", "capacity_mw", "latest_month", "area_anomaly", "pred_gen_anomaly", "pred_gen_anomaly_lo", "pred_gen_anomaly_hi"]].to_string())
