"""Control: does the same index fall at CITIES (no power-plant attribution) and at far-from-theatre sites? If yes, a war-window dip near a plant is not plant-specific."""
import numpy as np, pandas as pd, json
cal = json.load(open("no2_calibration.json")); meta = pd.read_csv("control_sites.csv").rename(columns={"plant_id_eia": "plant"})
d = pd.read_csv("no2_daily_controls.csv", parse_dates=["day"]); d = d[d.ws.between(2, 9)].copy(); d["idx"] = d.enh/np.exp(cal["temp_coef_per_degC"]*(d.temp-15))
WAR = (pd.Timestamp("2026-02-28"), pd.Timestamp("2026-04-08")); REF = (pd.Timestamp("2025-02-28"), pd.Timestamp("2025-04-08")); J25 = (pd.Timestamp("2025-06-13"), pd.Timestamp("2025-06-24")); rows = []
for p, g in d.groupby("plant"):
    g = g.set_index("day").sort_index(); base = g.idx[(g.index < WAR[0]) & ~((g.index >= J25[0]) & (g.index <= J25[1]))].mean(); rel = g.idx/base
    rows.append(dict(plant=p, mean_enh=g.enh.mean(), n_war=len(rel[WAR[0]:WAR[1]]), idx_war=rel[WAR[0]:WAR[1]].mean(), idx_same_window_2025=rel[REF[0]:REF[1]].mean(), idx_pre60=rel[WAR[0]-pd.Timedelta(days=60):WAR[0]-pd.Timedelta(days=1)].mean(), idx_post60=rel[WAR[1]+pd.Timedelta(days=1):WAR[1]+pd.Timedelta(days=60)].mean()))
R = meta[["plant", "plant_name_eia", "kind"]].merge(pd.DataFrame(rows)); R["war_over_2025"] = R.idx_war/R.idx_same_window_2025; R.to_csv("no2_controls_results.csv", index=False); print(R.round(2).to_string())
print(R.groupby("kind")[["idx_war", "idx_same_window_2025", "idx_pre60", "idx_post60", "war_over_2025"]].median().round(2))
F = pd.read_csv("foreign_activity_index.csv"); F = F[F.detectable]; F["war_over_2025"] = F.idx_war/F.idx_same_window_2025
print("plants:", F.groupby(F.country.where(F.country.isin(["IRN", "IRQ"]), "GULF")).war_over_2025.median().round(2).to_dict())
