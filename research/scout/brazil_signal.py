"""Cross-country check: GWW satellite area vs ONS (Brazil) ground truth level / turbined flow / hydraulic power proxy."""
import glob, requests, pandas as pd, numpy as np
B="https://api.globalwaterwatch.earth"
d=pd.concat([pd.read_parquet(f,columns=['nom_reservatorio','din_instante','val_nivelmontante','val_niveljusante','val_volumeutilcon','val_vazaoturbinada']) for f in sorted(glob.glob('data/ons/*.parquet'))])
d['din_instante']=pd.to_datetime(d.din_instante)
for c in ['val_nivelmontante','val_niveljusante','val_volumeutilcon','val_vazaoturbinada']: d[c]=pd.to_numeric(d[c].astype(str).str.replace(',','.'),errors='coerce')
d['p']=d.val_vazaoturbinada*(d.val_nivelmontante-d.val_niveljusante)*9.81*0.9/1000  # MW proxy
for ons,gid in [("SOBRADINHO","92090"),("FURNAS","91951")]:
    r=d[d.nom_reservatorio==ons].set_index('din_instante').resample('MS').mean(numeric_only=True)
    ts=requests.get(f"{B}/reservoir/{gid}/ts/surface_water_area_monthly",params={"start":"2012-01-01T00:00:00","stop":"2026-09-01T00:00:00"},timeout=60).json()
    a=pd.Series({pd.Timestamp(x['t'][:10]):x['value']/1e6 for x in ts},name='area')
    df=r.join(a,how='inner').dropna(subset=['area','p'])
    ann=df.groupby(df.index.year).mean()
    print(f"{ons:11s} months={len(df)} r(area,level)={df.area.corr(df.val_nivelmontante):.2f} r(area,useful_vol%)={df.area.corr(df.val_volumeutilcon):.2f} r(area,power_proxy) monthly={df.area.corr(df.p):.2f} annual={ann.area.corr(ann.p):.2f}")
