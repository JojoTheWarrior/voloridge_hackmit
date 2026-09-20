"""Does clear-sky normalisation improve the Bakken gauge against the ND DMR gold label? (SNPP detections x SNPP night clear-sky confidence)"""
import pandas as pd, numpy as np, os, json
from flarelib import *
W0,S0,E0,N0=-104.1,46.9,-101.0,49.0; RES=0.02
h=load_gibs('data/gibs_bakken','SNPP'); h=h[(h.dn=='N')&(h.lon>W0)&(h.lon<E0)&(h.lat>S0)&(h.lat<N0)].copy()
h['col']=((h.lon-W0)/RES).astype(int); h['row']=((N0-h.lat)/RES).astype(int); h['yr']=h.date.dt.year
nights=h.groupby(['row','col']).date.nunique(); keep=set(nights[nights>=3].index); h=h[[(r,c) in keep for r,c in zip(h.row,h.col)]]
# cells "active" in a given year = lit >=2 nights that year -> the set over which observability is measured
act={y:np.array(list(g.groupby(['row','col']).date.nunique().loc[lambda s:s>=2].index)) for y,g in h.groupby('yr')}
rows=[]
for d,g in h.groupby('date'): pass
daily=h.groupby('date').frp.sum()
rec=[]
for d in pd.date_range('2012-03-01','2026-08-31'):
    f=f'data/cloud_bakken/{d.date()}.npy'
    if not os.path.exists(f) or d.year not in act: continue
    a=np.load(f).astype('float32')/100; a[a<0]=np.nan; rc=act[d.year]; k=a[np.clip(rc[:,0],0,a.shape[0]-1),np.clip(rc[:,1],0,a.shape[1]-1)]
    rec.append((d,float(np.nanmean(k>0.05)) if np.isfinite(k).any() else np.nan,float(np.nanmean(k>=0.95)) if np.isfinite(k).any() else np.nan,float(daily.get(d,0.0))))
D=pd.DataFrame(rec,columns=['date','obs_frac','clear95_frac','frp']).set_index('date').dropna(); D=D[~D.index.isin(bad_days('N'))]; D.to_csv('data/bakken_daily_cloud_frp.csv')
g=D.groupby(D.index.to_period('M'))
M=pd.DataFrame({'raw_mean':g.frp.mean(),'norm_obs':g.frp.sum()/g.obs_frac.sum(),'norm_clear95':g.frp.sum()/g.clear95_frac.sum(),'clear_nights_only':g.apply(lambda x:x.frp[x.obs_frac>0.8].mean()),'obs_frac':g.obs_frac.mean(),'n_clear_nights':g.apply(lambda x:int((x.obs_frac>0.8).sum()))}); M.index=M.index.to_timestamp()
y=pd.read_csv('labels/nd_dmr_gas_monthly.csv',index_col=0,parse_dates=True).flared_mcfd
out={}
for k in ['raw_mean','norm_obs','norm_clear95','clear_nights_only']:
    out[k]={a:b[0] if isinstance(b,tuple) else b for a,b in stats_pair(M[k],y).items()}
T=pd.DataFrame(out).T; print(T.to_string()); T.to_csv('data/bakken_cloudnorm_comparison.csv')
print('seasonal amplitude (max/min of month-of-year mean) raw: %.1f  norm_obs: %.1f  clear_nights_only: %.1f  label: %.2f'%tuple((lambda s:(s.groupby(s.index.month).mean().max()/s.groupby(s.index.month).mean().min()))(x.dropna()) for x in [M.raw_mean,M.norm_obs,M.clear_nights_only,y['2012':]]))
print(M.groupby(M.index.month)[['obs_frac','n_clear_nights','raw_mean','clear_nights_only']].mean().round(2).to_string())
