import pandas as pd, numpy as np, pyarrow.parquet as pq, pyarrow.dataset as ds
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
def isd(name,years):
    fr=[]
    for y in years:
        d=pd.read_csv(f"data/isd/{name}_{y}.csv",usecols=["DATE","REPORT_TYPE","TMP","WND"],low_memory=False)
        d=d[d.REPORT_TYPE.str.strip().isin(["FM-15","FM-12"])]
        d["t"]=pd.to_datetime(d.DATE).dt.floor("h")
        tmp=d.TMP.str.split(",",expand=True)[0].astype(float); d["temp"]=np.where(tmp==9999,np.nan,tmp/10)
        w=d.WND.str.split(",",expand=True)[3].astype(float); d["wind"]=np.where(w==9999,np.nan,w/10)
        fr.append(d.groupby("t")[["temp","wind"]].mean())
    return pd.concat(fr)
gen=ds.dataset('data/core_eia930__hourly_net_generation_by_energy_source.parquet')
def g930(ba,src=None):
    f=(ds.field("balancing_authority_code_eia")==ba)
    t=gen.to_table(filter=f,columns=["datetime_utc","generation_energy_source","net_generation_adjusted_mwh","net_generation_reported_mwh"]).to_pandas()
    t["v"]=t.net_generation_adjusted_mwh.fillna(t.net_generation_reported_mwh)
    return t.pivot_table(index="datetime_utc",columns="generation_energy_source",values="v",aggfunc="sum",observed=True)
dem=pd.read_parquet('data/out_eia930__hourly_aggregated_demand.parquet'); print("demand groups:",dem.aggregation_level.unique().tolist(), dem.aggregation_group.unique()[:30].tolist())

# ---- T1 heat vs demand: train 2023, test 2024 ----
for grp,st in [("tex","DFW"),("ny","LGA")]:
    w=isd(st,[2023,2024]); y=dem[dem.aggregation_group==grp].set_index("datetime_utc").demand_imputed_pudl_mwh
    df=pd.concat([w.temp,y.rename("y")],axis=1).dropna(); df=df[df.y>0]
    X=lambda d: np.c_[np.clip(d.temp-18,0,None),np.clip(18-d.temp,0,None),np.clip(d.temp-18,0,None)**2]+0
    def feats(d,full):
        f=[np.clip(d.temp-18,0,None),np.clip(d.temp-18,0,None)**2,np.clip(18-d.temp,0,None)]
        if full: f+= [(d.index.hour==h).astype(float) for h in range(24)]+[(d.index.dayofweek>=5).astype(float)]
        return np.column_stack(f)
    tr,te=df[:"2023-12-31"],df["2024-01-01":]
    for full in (False,True):
        m=LinearRegression().fit(feats(tr,full),tr.y); print(f"T1 {grp}<-{st}: hourly demand ~ one airport thermometer{' + hour/weekend' if full else ''}: test-2024 R2={r2_score(te.y,m.predict(feats(te,full))):.2f} n={len(te)}")
    dd=df.resample("D").agg({"temp":"max","y":"sum"}); hot=dd[dd.temp>25]; s=np.polyfit(hot.temp,hot.y,1)[0]; print(f"   daily: above 25C each +1C of daily max = {s/hot.y.mean():+.1%} demand; r={hot.temp.corr(hot.y):.2f} n={len(hot)}")
# ---- T2 ISD wind vs ERCOT wind generation ----
e=g930("ERCO"); print("ERCO sources:",list(e.columns))
ws=pd.concat([isd(s,[2023,2024]).wind.rename(s) for s in ["ABI","MAF","LBB"]],axis=1).mean(axis=1)
df=pd.concat([ws.rename("w"),e["wind"].rename("y")],axis=1).dropna(); df=df[df.y>=0]
df["w3"]=np.clip(df.w,0,12)**3
print(f"T2 ERCOT wind gen vs mean 10m wind at 3 W-Texas airports: hourly r(speed)={df.w.corr(df.y):.2f}, r(clipped cube)={df.w3.corr(df.y):.2f} n={len(df)}; daily r={df.resample('D').mean().w.corr(df.resample('D').mean().y):.2f}")
pl=pd.concat([isd('LGA',[2023,2024]).wind.rename('w'),e['wind'].rename('y')],axis=1).dropna(); print(f"   placebo (NYC LaGuardia wind vs ERCOT wind gen): hourly r={pl.w.corr(pl.y):.2f}")
# ---- T3 hydro deficit -> gas fills the gap (grid from space, ground side) ----
for ba in ["CISO","BPAT"]:
    g=g930(ba); m=g.resample("MS").sum(); m=m[(m.index>="2019-01-01")&(m.index<"2026-06-01")]
    cols=[c for c in ["hydro","natural_gas","solar","wind","coal"] if c in m]; a=m[cols]-m[cols].groupby(m.index.month).transform("mean")
    yr=m[cols].groupby(m.index.year).sum()
    print(f"T3 {ba}: monthly deseasonalised r(hydro,gas)={a.hydro.corr(a.natural_gas):.2f} n={len(a)}; slope={np.polyfit(a.hydro,a.natural_gas,1)[0]:+.2f} MWh gas per MWh hydro; annual r={yr.hydro.corr(yr.natural_gas):.2f} (n={len(yr)})" if "natural_gas" in m else f"{ba} no gas")
