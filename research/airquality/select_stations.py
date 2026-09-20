import pandas as pd, numpy as np
from sklearn.neighbors import BallTree
a = pd.read_csv("pm25_locations.csv", dtype={"id": str})
c = pd.read_csv("cities_coverage.csv", keep_default_na=False)
t = BallTree(np.radians(c[["lat", "lon"]].values.astype(float)), metric="haversine")
dist, idx = t.query(np.radians(a[["lat", "lon"]].values), k=1)
a["cc"] = c.cc.values[idx[:, 0]]; a["region"] = c.region.values[idx[:, 0]]; a["city_km"] = dist[:, 0] * 6371
a = a[a.n2025 >= 200]
print(a.groupby(["region", "kind"]).agg(n=("id", "size"), countries=("cc", "nunique")).to_string())
rng = np.random.default_rng(0)
a["r"] = rng.random(len(a))
ref = a[a.kind == "reference_likely"].sort_values("r").groupby("cc").head(25)
low = a[a.kind == "lowcost"].sort_values("r").groupby("cc").head(6)
s = pd.concat([ref, low])
print(len(ref), len(low), s.cc.nunique(), "countries;", ref.cc.nunique(), "with reference")
s.to_csv("stations_sample.csv", index=False)
