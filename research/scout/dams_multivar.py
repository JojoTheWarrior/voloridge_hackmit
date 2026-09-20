"""Does GloFAS inflow + satellite area beat area alone, out of sample? 5 US dams (EIA-923 gen) + 2 Brazil (ONS flow x head)."""
import glob, json, os, time, requests, numpy as np, pandas as pd
def om(U,params):
    for _ in range(6):
        j=requests.get(U,params=params,timeout=300).json()
        if isinstance(j,dict) and j.get("error"): time.sleep(65); continue
        return j
    raise SystemExit(f"open-meteo error: {j}")
from sklearn.linear_model import RidgeCV
from sklearn.metrics import r2_score
B="https://api.globalwaterwatch.earth"
DAMS={ # name: (gww_id, dam lat, lon, label)
 "Hoover":("90554",36.016,-114.737,("eia",[154,8902])), "GlenCanyon":("89454",36.937,-111.484,("eia",[153])),
 "Shasta":(None,40.718,-122.419,("eia",[445])), "Oroville":(None,39.539,-121.485,("eia",[437])),
 "FortPeck":(None,48.003,-106.41,("eia",[6623])), "Sobradinho":("92090",-9.43,-40.83,("ons","SOBRADINHO")), "Furnas":("91951",-20.67,-46.32,("ons","FURNAS"))}
PTS={"Shasta":(-122.30,40.78),"Oroville":(-121.40,39.58),"FortPeck":(-106.6,47.75)}
def area(name,gid):
    if gid is None:
        x,y=PTS[name]; gid=requests.post(B+"/reservoir/geometry",json={"type":"Point","coordinates":[x,y]},timeout=60).json()["features"][0]["id"]
    raw=requests.get(f"{B}/reservoir/{gid}/ts/surface_water_area",params={"start":"2001-01-01T00:00:00","stop":"2026-09-01T00:00:00"},timeout=120).json()
    s=pd.Series({pd.Timestamp(x['t']):x['value']/1e6 for x in raw}).sort_index(); s=s[s>0.5*s.quantile(0.9)]
    return s.resample('MS').median().interpolate(limit=2)
def glofas(name,lat,lon):
    fn=f"data/glofas_{name}.json"
    if not os.path.exists(fn):
        la=[round(lat+dy*0.05,3) for dy in range(-2,3) for dx in range(-2,3)]; lo=[round(lon+dx*0.05,3) for dy in range(-2,3) for dx in range(-2,3)]
        U="https://flood-api.open-meteo.com/v1/flood"
        j=om(U,{"latitude":",".join(map(str,la)),"longitude":",".join(map(str,lo)),"daily":"river_discharge","start_date":"2019-01-01","end_date":"2020-12-31"})
        if isinstance(j,dict): raise SystemExit(f"open-meteo error: {j}")
        best=max(j,key=lambda c:np.nanmean([x or 0 for x in c['daily']['river_discharge']]))
        full=om(U,{"latitude":best['latitude'],"longitude":best['longitude'],"daily":"river_discharge","start_date":"2001-01-01","end_date":"2026-08-31"}); time.sleep(20)
        if 'daily' not in full: raise SystemExit(f"open-meteo error: {full}")
        json.dump(full['daily'],open(fn,'w'))
    d=json.load(open(fn)); return pd.Series(d['river_discharge'],index=pd.to_datetime(d['time']),dtype=float).resample('MS').mean()
g=pd.read_parquet('data/core_eia923__monthly_generation_fuel.parquet',columns=['report_date','plant_id_eia','energy_source_code','net_generation_mwh']); g=g[g.energy_source_code=='WAT']
ons=pd.concat([pd.read_parquet(f,columns=['nom_reservatorio','din_instante','val_nivelmontante','val_niveljusante','val_vazaoturbinada']) for f in sorted(glob.glob('data/ons/*.parquet'))])
ons['din_instante']=pd.to_datetime(ons.din_instante)
for c in ons.columns[2:]: ons[c]=pd.to_numeric(ons[c].astype(str).str.replace(',','.'),errors='coerce')
frames={}
for n,(gid,lat,lon,(kind,key)) in DAMS.items():
    if kind=="eia": y=g[g.plant_id_eia.isin(key)].groupby('report_date').net_generation_mwh.sum(); y.index=pd.to_datetime(y.index)
    else:
        r=ons[ons.nom_reservatorio==key].set_index('din_instante'); y=(r.val_vazaoturbinada*(r.val_nivelmontante-r.val_niveljusante)).resample('MS').mean()
    df=pd.concat([y.rename('y'),area(n,gid).rename('area'),glofas(n,lat,lon).rename('q')],axis=1).dropna()
    for c in ['y','area','q']: df[c]=df[c]/df[c].mean()
    df['q3']=df.q.rolling(3).mean(); df['q12']=df.q.rolling(12).mean(); df=df.dropna()
    for m in range(1,13): df[f'm{m}']=(df.index.month==m).astype(float)
    df['dam']=n; frames[n]=df
S=[f'm{m}' for m in range(1,13)]
SETS={"season only":S,"season+area":S+['area'],"season+inflow":S+['q','q3','q12'],"season+area+inflow":S+['area','q','q3','q12']}
def fit(tr,te,cols): return r2_score(te.y,RidgeCV(alphas=np.logspace(-3,2,12)).fit(tr[cols],tr.y).predict(te[cols]))
print("A) per-dam time split: train <2017, test >=2017 (R2 out of sample)")
rows=[]
for n,df in frames.items():
    tr,te=df[df.index<'2017'],df[df.index>='2017']
    if len(tr)<36 or len(te)<24: print(n,'insufficient',len(tr),len(te)); continue
    rows.append(pd.Series({k:fit(tr,te,c) for k,c in SETS.items()},name=f"{n} (n_te={len(te)})"))
print(pd.DataFrame(rows).round(2).to_string())
print("\nB) leave-one-dam-out, pooled normalised model (zero-shot transfer to an unseen dam)")
allf=pd.concat(frames.values()); rows=[]
for n in frames:
    tr,te=allf[allf.dam!=n],allf[allf.dam==n]
    rows.append(pd.Series({k:fit(tr,te,c) for k,c in SETS.items()},name=n))
print(pd.DataFrame(rows).round(2).to_string())
print("\nC) US-only training -> Brazil zero-shot"); tr=allf[~allf.dam.isin(['Sobradinho','Furnas'])]
for n in ['Sobradinho','Furnas']: print(n,{k:round(fit(tr,frames[n],c),2) for k,c in SETS.items()})
