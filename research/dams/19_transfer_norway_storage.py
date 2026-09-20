"""Second keyless truth: Norway's NVE weekly reservoir filling (national, % of capacity) vs the capacity-weighted satellite
area anomaly of the monitored Norwegian reservoirs. This scores STORAGE (what orbit sees), not generation.
Winter months are scored separately because ice and snow break optical water detection.
Output results/transfer_norway_storage.csv"""
import json

import pandas as pd

from common import CACHE, RESULTS, cached_json

URL = "https://biapi.nve.no/magasinstatistikk/api/Magasinstatistikk/HentOffentligData"
fn = CACHE / "nve.json"
j = json.loads(fn.read_text()) if fn.exists() else cached_json(URL, subdir="nve", key="nve")
d = pd.DataFrame(j)
d = d[d.omrType == "NO"].assign(month=lambda x: pd.to_datetime(x.dato_Id).dt.to_period("M").dt.to_timestamp())
fill = d.groupby("month").fyllingsgrad.mean()
fill_anom = fill - fill.groupby(fill.index.month).transform("mean")

P = pd.read_parquet(RESULTS / "predictions_world.parquet")
N = P[P.iso3 == "NOR"]
w = N.capacity_mw.fillna(1)
sat = (N.a0 * w).groupby(N.month).sum() / w.groupby(N.month).sum()
n = N.groupby("month").gww_id.nunique()
sat = sat[n >= 0.6 * n.max()]
df = pd.concat([fill_anom.rename("nve_fill_anom"), sat.rename("sat_area_anom")], axis=1).dropna()
rows = []
for lab, m in [("all months", df), ("ice-free months (Jun-Oct)", df[df.index.month.isin(range(6, 11))]), ("winter (Dec-Apr)", df[df.index.month.isin([12, 1, 2, 3, 4])])]:
    ann = m.groupby(m.index.year).mean()
    rows.append({"subset": lab, "n_months": len(m), "n_reservoirs": int(n.max()), "r_monthly": m.nve_fill_anom.corr(m.sat_area_anom),
                 "r_annual_means": ann.nve_fill_anom.corr(ann.sat_area_anom), "n_years": len(ann)})
R = pd.DataFrame(rows)
R.to_csv(RESULTS / "transfer_norway_storage.csv", index=False)
print(R.round(3).to_string())
