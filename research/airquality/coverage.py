"""Q1: how many large cities have no (reference-likely) PM2.5 monitor in OpenAQ (active 2024/25)?"""
import pandas as pd, numpy as np
from sklearn.neighbors import BallTree
cols = "gid name ascii alt lat lon fclass fcode cc cc2 a1 a2 a3 a4 pop elev dem tz mod".split()
c = pd.read_csv("cities15000.txt", sep="\t", names=cols, quoting=3, keep_default_na=False, low_memory=False)
ci = pd.read_csv("countryInfo.txt", sep="\t", comment="#", header=None, keep_default_na=False, usecols=[0, 4, 8], names=["cc", "country", "cont"])
c = c.merge(ci, on="cc", how="left")
SUB = {"IN":"South Asia","PK":"South Asia","BD":"South Asia","NP":"South Asia","LK":"South Asia","AF":"South Asia","CN":"China",
       "KZ":"Central Asia","UZ":"Central Asia","TJ":"Central Asia","KG":"Central Asia","TM":"Central Asia"}
MENA = set("DZ EG LY MA TN SD IQ IR SA YE SY JO LB IL PS AE QA KW BH OM TR".split())
def region(r):
    if r.cc in SUB: return SUB[r.cc]
    if r.cc in MENA: return "MENA"
    return {"AF":"Sub-Saharan Africa","AS":"Other Asia","EU":"Europe","NA":"North/Central America","SA":"South America","OC":"Oceania"}.get(r.cont, "?")
c["region"] = c.apply(region, axis=1)
c["pop"] = c["pop"].astype(int)
d = pd.read_csv("location_index.csv", dtype={"id": str})
a = d[d.active & d.has_pm25 & d.lat.notna()].copy()
lowcost = a.params.str.contains(r"um\d|pm1(?:\||$)") | a.provider.isin(["clarity", "habitatmap", "cmu", "senstate"])
a["kind"] = np.where(lowcost, "lowcost", "reference_likely")
a["days"] = a.n2024.fillna(0) + a.n2025.fillna(0)
a.to_csv("pm25_locations.csv", index=False)
print(a.kind.value_counts())
def nearest(sub, km):
    t = BallTree(np.radians(sub[["lat", "lon"]].values), metric="haversine")
    return t.query_radius(np.radians(c[["lat", "lon"]].values), r=km / 6371.0, count_only=True)
ref = a[(a.kind == "reference_likely") & (a.days >= 60)]
for km in (25, 50):
    c[f"n_ref_{km}"] = nearest(ref, km); c[f"n_any_{km}"] = nearest(a[a.days >= 60], km)
c.to_csv("cities_coverage.csv", index=False)
for thr in (500_000, 1_000_000):
    big = c[c["pop"] >= thr]
    g = big.groupby("region").agg(cities=("pop", "size"), pop_M=("pop", lambda s: s.sum() / 1e6),
        no_ref_25=("n_ref_25", lambda s: (s == 0).sum()), no_ref_50=("n_ref_50", lambda s: (s == 0).sum()),
        no_any_25=("n_any_25", lambda s: (s == 0).sum()))
    g["pop_no_ref25_M"] = big[big.n_ref_25 == 0].groupby("region")["pop"].sum() / 1e6
    g.loc["TOTAL"] = g.sum()
    g["pct_no_ref_25"] = (100 * g.no_ref_25 / g.cities).round(0)
    print(f"\n=== cities >= {thr:,} ===\n", g.round(1).fillna(0).to_string())
print("\nLargest cities with no reference-likely PM2.5 within 25km:")
print(c[c.n_ref_25 == 0].nlargest(40, "pop")[["name", "cc", "pop", "n_ref_50", "n_any_25"]].to_string(index=False))
