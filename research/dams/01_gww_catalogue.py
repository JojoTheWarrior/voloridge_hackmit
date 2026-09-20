"""Download the full Global Water Watch reservoir catalogue (id, names, GRanD id, polygon) -> data/gww_catalogue.parquet."""
import geopandas as gpd
import pandas as pd
from shapely.geometry import shape

from common import DATA, GWW, cached_json

LIMIT = 1000
if (DATA / "gww_catalogue.parquet").exists():  # page cache is deleted after the build to save disk (~330 MB)
    raise SystemExit("catalogue already built")


def page(skip):
    """One catalogue page; pages with very detailed polygons time out upstream (502), so fall back to quarter pages."""
    try:
        return cached_json(f"{GWW}/reservoir", params={"skip": skip, "limit": LIMIT}, subdir="gww_catalogue", key=f"skip{skip}", sleep=0.5, retries=2)["features"]
    except RuntimeError:
        q = LIMIT // 4
        return [f for k in range(4) for f in cached_json(f"{GWW}/reservoir", params={"skip": skip + k * q, "limit": q}, subdir="gww_catalogue",
                                                         key=f"skip{skip + k * q}_q", sleep=0.5)["features"]]


rows, skip = [], 0
while True:
    fs = page(skip)
    if not fs:
        break
    for f in fs:
        p = f["properties"]
        rows.append({"gww_id": f["id"], "name": p.get("name"), "name_en": p.get("name_en"), "grand_id": p.get("grand_id"),
                     "source_name": p.get("source_name"), "source_id": p.get("source_id"), "geometry": shape(f["geometry"])})
    skip += LIMIT
    print(skip, len(rows), flush=True)

g = gpd.GeoDataFrame(rows, crs="EPSG:4326")
g["geometry"] = g.geometry.buffer(0)
eq = g.to_crs("ESRI:54034")  # cylindrical equal-area
g["poly_km2"] = eq.area / 1e6
c = g.geometry.representative_point()
g["lon"], g["lat"] = c.x, c.y
g.to_parquet(DATA / "gww_catalogue.parquet")
print(len(g), "reservoirs;", g.grand_id.notna().sum(), "with GRanD id;", (g.poly_km2 > 1).sum(), "> 1 km2")
print(pd.Series(g.source_name).value_counts())
