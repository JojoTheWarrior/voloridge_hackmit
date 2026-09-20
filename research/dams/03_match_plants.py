"""Match hydro plants to satellite-monitored reservoirs.

Truth-side plants: US (EIA-923/860 via PUDL), Brazil (ONS reservoir registry). Rest of world: GloHydroRes.
Reservoir side: HydroLAKES pour points (the lake outlet == the dam, which disambiguates the upstream reservoir from the
downstream one in cascades) -> GWW id; fallback: nearest GWW polygon of any source (lower confidence).
Outputs data/matches.parquet (one row per plant) and results/match_report.csv (match-rate + failure-mode accounting).
"""
import geopandas as gpd
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

from common import DATA, RESULTS

R_EARTH = 6371.0
POUR_KM = 3.0        # plant <-> HydroLAKES pour point
POLY_KM = 1.0        # plant <-> GWW polygon edge (fallback)
MIN_KM2 = 0.5        # below this, Landsat/S2 area series are mostly noise


def xyz(lat, lon):
    la, lo = np.radians(lat), np.radians(lon)
    return np.c_[np.cos(la) * np.cos(lo), np.cos(la) * np.sin(lo), np.sin(la)]


def load_us():
    g = pd.read_parquet(DATA / "core_eia923__monthly_generation_fuel.parquet",
                        columns=["report_date", "plant_id_eia", "energy_source_code", "prime_mover_code", "net_generation_mwh"])
    g = g[(g.energy_source_code == "WAT") & (g.prime_mover_code == "HY")]
    ids = g.groupby("plant_id_eia").net_generation_mwh.agg(n_months="count", mean_mwh="mean").reset_index()
    ps = set(pd.read_parquet(DATA / "core_eia923__monthly_generation_fuel.parquet", columns=["plant_id_eia", "prime_mover_code"])
             .query("prime_mover_code=='PS'").plant_id_eia)
    gen = pd.read_parquet(DATA / "core_eia860__scd_generators.parquet", columns=["plant_id_eia", "report_date", "prime_mover_code", "capacity_mw"])
    gen = gen[gen.prime_mover_code == "HY"]
    cap = gen.groupby(["plant_id_eia", "report_date"]).capacity_mw.sum().groupby("plant_id_eia").max().rename("capacity_mw")
    pl = pd.read_parquet(DATA / "core_eia860__scd_plants.parquet", columns=["plant_id_eia", "report_date", "reporting_frequency_code", "balancing_authority_code_eia"])
    pl = pl.sort_values("report_date").groupby("plant_id_eia").agg(
        reporting_frequency=("reporting_frequency_code", lambda s: s.dropna().iloc[-1] if s.notna().any() else None),
        ba=("balancing_authority_code_eia", lambda s: s.dropna().iloc[-1] if s.notna().any() else None))
    e = pd.read_parquet(DATA / "core_eia__entity_plants.parquet", columns=["plant_id_eia", "plant_name_eia", "latitude", "longitude", "state"])
    d = ids.merge(e, on="plant_id_eia").merge(cap, on="plant_id_eia", how="left").merge(pl, on="plant_id_eia", how="left")
    d["has_pumped_storage"] = d.plant_id_eia.isin(ps)
    return d.rename(columns={"plant_id_eia": "plant_id", "plant_name_eia": "plant_name", "latitude": "lat", "longitude": "lon"}).assign(
        country="USA", truth="eia923", plant_id=lambda x: "US" + x.plant_id.astype(str))


def load_br():
    r = pd.read_parquet(DATA / "ons" / "reservatorios.parquet")
    c = pd.read_parquet(DATA / "ons" / "capacidade.parquet")
    cap = c[c.nom_tipousina.str.contains("HIDRO", na=False)].groupby("ceg").val_potenciaefetiva.sum().rename("capacity_mw")
    r = r.merge(cap, on="ceg", how="left")
    return pd.DataFrame({"plant_id": "BR" + r.res_id.astype(str), "plant_name": r.nom_usina, "lat": r.val_latitude, "lon": r.val_longitude,
                         "capacity_mw": r.capacity_mw, "country": "BRA", "truth": "ons", "ons_reservatorio": r.nom_reservatorio,
                         "ons_tipo": r.tip_reservatorio, "ceg": r.ceg})


GLO = pd.read_csv(DATA / "glohydrores.csv", low_memory=False, encoding="latin-1").dropna(subset=["plant_lat", "plant_lon"]).reset_index(drop=True)


def load_world():
    """Rest of world from GloHydroRes (Shah et al. 2025; merges WRI GPPD, JRC, EHA, RePP). >= 30 MW, non-pumped."""
    w = GLO[~GLO.country.isin(["United States of America", "Brazil"]) & (GLO.capacity_mw >= 30) & (GLO.plant_type != "PS")]
    return pd.DataFrame({"plant_id": "GLO" + w.ID.astype(str), "plant_name": w.name, "lat": w.plant_lat, "lon": w.plant_lon,
                         "capacity_mw": w.capacity_mw, "country": w.country, "truth": "none"})


plants = pd.concat([load_us(), load_br(), load_world()], ignore_index=True).dropna(subset=["lat", "lon"])
print(plants.groupby("truth").size())

# attach GloHydroRes curated attributes (plant type, head, its own HydroLAKES link) to every plant by proximity (<= 2 km)
gt = cKDTree(xyz(GLO.plant_lat.values, GLO.plant_lon.values))
dist, idx = gt.query(xyz(plants.lat.values, plants.lon.values))
near = 2 * R_EARTH * np.arcsin(dist / 2) <= 2.0
for src, dst in [("plant_type", "glo_plant_type"), ("head_m", "glo_head_m"), ("dam_height_m", "glo_dam_height_m"), ("hydrolakes_id", "glo_hylak_id")]:
    plants[dst] = np.where(near, GLO[src].values[idx], None)
for c in ["glo_head_m", "glo_dam_height_m", "glo_hylak_id"]:
    plants[c] = pd.to_numeric(plants[c], errors="coerce")

hl = pd.read_parquet(DATA / "hydrolakes_pts.parquet")
cat = gpd.read_parquet(DATA / "gww_catalogue.parquet")
# a few HydroLAKES lakes are split into several GWW polygons: keep the largest part
cat_hl = cat[cat.source_name == "HydroLAKES"].sort_values("poly_km2", ascending=False).drop_duplicates("source_id").set_index("source_id").gww_id
hl["gww_id"] = hl.Hylak_id.map(cat_hl)

# 1) HydroLAKES pour point within POUR_KM of the plant; among candidates take the largest lake (a powerhouse sits at its own
#    dam; tiny afterbays/forebays nearby would otherwise win on distance alone).
tree = cKDTree(xyz(hl.Pour_lat.values, hl.Pour_long.values))
chord = 2 * np.sin(POUR_KM / R_EARTH / 2)
cands = tree.query_ball_point(xyz(plants.lat.values, plants.lon.values), chord)
P = xyz(plants.lat.values, plants.lon.values)
H = xyz(hl.Pour_lat.values, hl.Pour_long.values)
rows = []
for i, c in enumerate(cands):
    if not c:
        rows.append((None, np.nan, 0))
        continue
    c = np.array(c)
    j = c[np.argmax(hl.Lake_area.values[c])]
    rows.append((j, 2 * R_EARTH * np.arcsin(np.linalg.norm(P[i] - H[j]) / 2), len(c)))
plants["hl_idx"], plants["pour_dist_km"], plants["n_pour_cands"] = zip(*rows)
m = plants.hl_idx.notna()
for col in ["Hylak_id", "Lake_name", "Lake_type", "Grand_id", "Lake_area", "Vol_total", "Depth_avg", "Dis_avg", "Res_time", "Elevation", "Wshd_area", "Pour_lat", "Pour_long", "gww_id"]:
    plants.loc[m, col] = hl[col].values[plants.loc[m, "hl_idx"].astype(int)]
plants["match_method"] = np.where(m & plants.gww_id.notna(), "hydrolakes_pour", None)

# 2) fallback: GWW polygon edge within POLY_KM (any source). Ambiguous in cascades -> flagged lower confidence.
todo = plants[plants.match_method.isna()]
pts = gpd.GeoDataFrame(todo[["plant_id"]], geometry=gpd.points_from_xy(todo.lon, todo.lat), crs=4326)
deg = POLY_KM / 111.0
buf = pts.copy()
buf["geometry"] = [p.buffer(deg / max(0.2, np.cos(np.radians(p.y)))) for p in pts.geometry]  # generous in lon, exact check below
j = gpd.sjoin(buf, cat[cat.poly_km2 >= MIN_KM2][["gww_id", "poly_km2", "geometry"]], predicate="intersects")
j = j.sort_values("poly_km2", ascending=False).drop_duplicates("plant_id").set_index("plant_id")
fb = plants.plant_id.map(j.gww_id)
use = plants.match_method.isna() & fb.notna()
plants.loc[use, "gww_id"] = fb[use]
plants.loc[use, "match_method"] = "gww_polygon"
plants["gww_poly_km2"] = plants.gww_id.map(cat.set_index("gww_id").poly_km2)
plants["gww_name"] = plants.gww_id.map(cat.set_index("gww_id").name)

# failure-mode accounting
def why(r):
    if pd.notna(r.match_method):
        return "too_small" if r.gww_poly_km2 < MIN_KM2 else "matched"
    if pd.notna(r.hl_idx):
        return "hydrolakes_lake_not_in_gww"
    return "no_reservoir_within_range"
plants["status"] = plants.apply(why, axis=1)
plants.drop(columns=["hl_idx"]).to_parquet(DATA / "matches.parquet")
rep = plants.groupby(["truth", "status"]).agg(n=("plant_id", "size"), capacity_gw=("capacity_mw", lambda s: s.sum() / 1e3)).reset_index()
rep["share_n"] = rep.n / rep.groupby("truth").n.transform("sum")
rep["share_capacity"] = rep.capacity_gw / rep.groupby("truth").capacity_gw.transform("sum")
rep.round(3).to_csv(RESULTS / "match_report.csv", index=False)
print(rep.round(3).to_string())
both = plants[(plants.match_method == "hydrolakes_pour") & plants.glo_hylak_id.notna()]
print("geometric pour-point match vs GloHydroRes curated HydroLAKES link: agree on", (both.Hylak_id == both.glo_hylak_id).mean().round(3), "of", len(both))
ok = plants[plants.status == "matched"]
print("matched plants", len(ok), "-> distinct reservoirs", ok.gww_id.nunique(), "| by method:", ok.match_method.value_counts().to_dict())
