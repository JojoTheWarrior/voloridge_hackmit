"""Builds plants_s2_us.csv from us_plant_candidates.csv (as run in round 2)."""
import pandas as pd
df = pd.read_csv("us_plant_candidates.csv"); df["ctypes"] = df.ctypes.fillna("")
rn = df[df.ctypes.str.contains("RN")].assign(group="natural_draft")
md = df[(~df.ctypes.str.contains("RN")) & df.ctypes.str.contains("RI|RF") & (df.fuel == "coal") & (df.max_mw > 1100)]
md = pd.concat([md[md.frac_off.between(0.03, 0.7)].nlargest(16, "max_mw"), md[md.frac_off < 0.03].nlargest(4, "max_mw")]).assign(group="mech_draft")
ot = df[df.ctypes.str.fullmatch(r"(O[A-Z]?,?)+") & (df.fuel == "coal") & (df.max_mw > 1200)].nlargest(5, "max_mw").assign(group="once_through_control")
pd.concat([rn, md, ot]).to_csv("plants_s2_us.csv", index=False)
