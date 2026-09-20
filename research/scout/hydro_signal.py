"""Quick signal check: GWW satellite reservoir area vs EIA-923 monthly hydro generation."""
import requests, pandas as pd, numpy as np
B="https://api.globalwaterwatch.earth"
g=pd.read_parquet('data/core_eia923__monthly_generation_fuel.parquet',columns=['report_date','plant_id_eia','energy_source_code','net_generation_mwh'])
g=g[g.energy_source_code=='WAT']
p=pd.read_parquet('data/core_eia__entity_plants.parquet')[['plant_id_eia','plant_name_eia','latitude','longitude']]
# (label plant ids, point inside reservoir)
sites={"Hoover/Mead":([154,8902],(-114.60,36.13)),"Glen Canyon/Powell":([153],(-111.30,37.05)),
       "Shasta":(None,(-122.30,40.78)),"Oroville":(None,(-121.40,39.58)),"Garrison/Sakakawea":([2815],(-102.0,47.6)),
       "Oahe":([3356],(-100.5,45.0)),"Libby/Koocanusa":([6172],(-115.25,48.7)),"Fort Peck":(None,(-106.6,47.75))}
names={"Shasta":"Shasta","Oroville":"Edward C Hyatt","Fort Peck":"Fort Peck"}
for n,(ids,(x,y)) in sites.items():
    if ids is None:
        m=p[p.plant_name_eia.str.contains(names[n],case=False,na=False)]
        ids=m.plant_id_eia.tolist()
    fs=requests.post(B+"/reservoir/geometry",json={"type":"Point","coordinates":[x,y]},timeout=60).json().get("features",[])
    if not fs: print(n,"no GWW reservoir"); continue
    rid=fs[0]["id"]
    ts=requests.get(f"{B}/reservoir/{rid}/ts/surface_water_area_monthly",params={"start":"2001-01-01T00:00:00","stop":"2026-06-01T00:00:00"},timeout=60).json()
    a=pd.Series({pd.Timestamp(d['t'][:7]+'-01'):d['value']/1e6 for d in ts}).sort_index()
    y_=g[g.plant_id_eia.isin(ids)].groupby('report_date').net_generation_mwh.sum(); y_.index=pd.to_datetime(y_.index)
    if a.empty or y_.empty: print(n,'empty',len(a),len(y_),ids); continue
    df=pd.concat([a.rename('area'),y_.rename('gen')],axis=1).dropna()
    ann=df.groupby(df.index.year).agg(area=('area','median'),gen=('gen','sum'),n=('gen','size')); ann=ann[ann.n>=10]
    # deseasonalised monthly
    ds=df-df.groupby(df.index.month).transform('mean')
    print(f"{n:22s} plants={ids} months={len(df)} r_monthly={df.corr().iloc[0,1]:.2f} r_deseason={ds.corr().iloc[0,1]:.2f} r_annual={ann[['area','gen']].corr().iloc[0,1]:.2f} (n_years={len(ann)})")
