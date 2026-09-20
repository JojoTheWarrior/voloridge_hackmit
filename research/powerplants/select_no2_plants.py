"""Builds plants_no2_us.csv: isolated CEMS NOx sources (needs cems_2024_plant_totals.csv from the 2024 CEMS aggregate query and us_plant_candidates.csv)."""
import pandas as pd, numpy as np
t = pd.read_csv("cems_2024_plant_totals.csv").groupby("plant_id_eia", as_index=False).sum(numeric_only=True)
c = pd.read_csv("us_plant_candidates.csv")[["plant_id_eia", "plant_name_eia", "state", "latitude", "longitude", "fuel", "max_mw", "frac_off"]]
d = t.merge(c, on="plant_id_eia").dropna(subset=["latitude"]); d = d[d.latitude.between(24.5, 49.5) & d.longitude.between(-124.5, -66.5)]
lat, lon = np.radians(d.latitude.values), np.radians(d.longitude.values)
dist = 6371*np.arccos(np.clip(np.sin(lat)[:, None]*np.sin(lat) + np.cos(lat)[:, None]*np.cos(lat)*np.cos(lon[:, None]-lon), -1, 1))
d["iso"] = (((dist < 60) & (dist > 0))*d.nox_lbs_h.values[None, :]).sum(1)/d.nox_lbs_h
coal = d[(d.fuel == "coal") & (d.nox_lbs_h >= 350) & (d.iso < 0.25)].nlargest(45, "nox_lbs_h"); gas = d[d.fuel.isin(["gas", "oil"]) & (d.nox_lbs_h >= 120) & (d.iso < 0.35)].nlargest(20, "nox_lbs_h")
pd.concat([coal, gas])[["plant_id_eia", "plant_name_eia", "state", "latitude", "longitude", "fuel", "nox_lbs_h", "so2_lbs_h", "mean_mw", "iso"]].to_csv("plants_no2_us.csv", index=False)
