import io, requests, numpy as np, pandas as pd
fr=[]; off=0
while True:
    r=requests.get("https://api.carbonmapper.org/api/v1/catalog/plume-csv",params={"plume_gas":"CH4","limit":5000,"offset":off},timeout=300)
    d=pd.read_csv(io.StringIO(r.text),usecols=["plume_id","plume_latitude","plume_longitude","datetime","country","region","ipcc_sector","emission_auto","emission_uncertainty_auto","platform"])
    fr.append(d); off+=5000
    if len(d)<5000 or off>60000: break
p=pd.concat(fr).drop_duplicates("plume_id"); p.to_csv("data/carbonmapper_ch4.csv",index=False)
print("plumes",len(p)); print(p.country.value_counts().head(6).to_dict()); print(p.ipcc_sector.value_counts().head(6).to_dict())
us=p[p.country=="United States"].copy()
pl=pd.read_parquet("data/core_eia__entity_plants.parquet")[["plant_id_eia","plant_name_eia","latitude","longitude","state"]].dropna()
g=pd.read_parquet("data/core_eia923__monthly_generation_fuel.parquet",columns=["plant_id_eia","fuel_type_code_pudl","net_generation_mwh","report_date"])
g=g[pd.to_datetime(g.report_date)>="2022-01-01"]; fuel=g.groupby(["plant_id_eia","fuel_type_code_pudl"]).net_generation_mwh.sum().reset_index().sort_values("net_generation_mwh").groupby("plant_id_eia").tail(1).set_index("plant_id_eia").fuel_type_code_pudl
pl["fuel"]=pl.plant_id_eia.map(fuel); pl=pl.dropna(subset=["fuel"])
from scipy.spatial import cKDTree
R=6371.0
def xyz(lat,lon): lat,lon=np.radians(lat),np.radians(lon); return np.c_[np.cos(lat)*np.cos(lon),np.cos(lat)*np.sin(lon),np.sin(lat)]
tree=cKDTree(xyz(pl.latitude.values,pl.longitude.values)); dist,idx=tree.query(xyz(us.plume_latitude.values,us.plume_longitude.values)); us["km"]=2*R*np.arcsin(dist/2); us["plant"]=pl.plant_name_eia.values[idx]; us["fuel"]=pl.fuel.values[idx]; us["pid"]=pl.plant_id_eia.values[idx]
near=us[us.km<=1.0]
print(f"US plumes {len(us)}; within 1 km of an EIA power plant: {len(near)} ({len(near)/len(us):.1%}); distinct plants {near.pid.nunique()}")
# placebo: shift plumes 0.1 deg (~10 km) east
d2,_=tree.query(xyz(us.plume_latitude.values,us.plume_longitude.values+0.1)); print(f"placebo (plumes shifted ~9 km east): {(2*R*np.arcsin(d2/2)<=1.0).mean():.1%}")
print(near.groupby("fuel").agg(plumes=("plume_id","size"),plants=("pid","nunique"),median_kg_h=("emission_auto","median")).sort_values("plumes",ascending=False).to_string())
top=near.groupby(["plant","fuel"]).agg(plumes=("plume_id","size"),mean_kg_h=("emission_auto","mean")).sort_values("plumes",ascending=False).head(8); print(top.round(0).to_string())
print("sector of plumes near gas plants:",near[near.fuel=="gas"].ipcc_sector.value_counts().head(4).to_dict())
