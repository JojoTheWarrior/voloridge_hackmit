"""Per-cell clear-sky normalisation of Gulf flare FRP (NOAA-20 detections x NOAA-20 night clear-sky confidence, same overpass)."""
import pandas as pd, numpy as np, json, glob, os, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
RES=0.02; W0,S0,E0,N0=36.0,18.0,64.0,40.0
h=pd.read_parquet('data/hotspots_gulf.parquet'); h=h[(h.SATELLITE=='N20')&(h.DAYNIGHT=='N')].copy()
h['col']=((h.LONGITUDE-W0)/RES).astype(int); h['row']=((N0-h.LATITUDE)/RES).astype(int)
dates=pd.date_range('2025-01-01','2026-09-19'); di={d:i for i,d in enumerate(dates)}
base=h[h.date<'2026-02-28']; nb=base.date.nunique()
pers=base.groupby(['row','col']).date.nunique()/nb; cells=pers[pers>=0.10].index.to_frame(index=False)
print('persistent N20 flare cells:',len(cells))
R,C=cells.row.values,cells.col.values; ci={(r,c):i for i,(r,c) in enumerate(zip(R,C))}
F=np.zeros((len(dates),len(cells)),dtype='float32')
hh=h[[ (r,c) in ci for r,c in zip(h.row,h.col)]]
for d,r,c,f in zip(hh.date,hh.row,hh.col,hh.FRP): F[di[d],ci[(r,c)]]+=f
K=np.full((len(dates),len(cells)),np.nan,dtype='float32')
for i,d in enumerate(dates):
    f=f'data/cloud_gulf/{d.date()}.npy'
    if os.path.exists(f):
        a=np.load(f).astype('float32')/100; a[a<0]=np.nan
        # 3x3 min around the cell = conservative clear-sky
        K[i]=np.nanmin(np.stack([a[np.clip(R+dr,0,a.shape[0]-1),np.clip(C+dc,0,a.shape[1]-1)] for dr in(-1,0,1) for dc in(-1,0,1)]),axis=0)
print('nights with cloud grid:',int(np.isfinite(K).any(1).sum()),'of',len(dates))
bi=np.array([d<pd.Timestamp('2026-02-28') for d in dates])
# diagnostic: detection probability by clear-sky confidence bin (baseline)
bins=[-0.01,0.05,0.5,0.9,0.99,1.01]; diag=[]
for lo,hi in zip(bins[:-1],bins[1:]):
    m=(K[bi]>lo)&(K[bi]<=hi); diag.append({'conf_bin':f'({lo},{hi}]','share_of_cell_nights':round(float(m.sum()/np.isfinite(K[bi]).sum()),3),'P(detect)':round(float((F[bi][m]>0).mean()),3),'mean_FRP':round(float(F[bi][m].mean()),2)})
print(pd.DataFrame(diag).to_string()); pd.DataFrame(diag).to_csv('data/cloud_detection_diagnostic.csv',index=False)
clear=K>0.05   # "not confidently cloudy": the diagnostic shows flares themselves depress clear-sky confidence, so a strict >=0.95 cut selects against big flares
mu=np.where(clear[bi].sum(0)>=20,(F[bi]*clear[bi]).sum(0)/np.maximum(clear[bi].sum(0),1),np.nan)   # per-cell clear-night baseline mean
lat=N0-(R+0.5)*RES; lon=W0+(C+0.5)*RES
regions={'Qatar':(50.7,24.4,51.8,26.3),'Kuwait':(46.5,28.5,48.6,30.1),'Iraq-Basra':(46.3,30.1,48.1,31.6),'Iran-Khuzestan':(48.1,30.0,50.6,32.6),'Iran-SouthPars/Bushehr':(50.6,26.9,53.3,29.5),'Saudi-East':(47.8,24.3,50.6,28.4),'UAE':(51.9,22.6,56.0,25.6),'CTRL Iraq-Kirkuk/Kurdistan':(43.0,34.5,46.0,37.0),'CTRL Oman':(54.5,18.1,58.5,23.5),'CTRL Turkmenistan':(52.5,37.3,64.0,40.0)}
P={'closure':('2026-03-04','2026-04-08'),'same_weeks_2025':('2025-03-04','2025-04-08'),'pre(Dec1-Feb27)':('2025-12-01','2026-02-27'),'blockade(Apr12-Jun17)':('2026-04-12','2026-06-17'),'Jul-Sep26':('2026-07-01','2026-09-19')}
rng=np.random.default_rng(0); rows=[]; series={}
for rn,(w,s,e,n) in regions.items():
    m=(lon>=w)&(lon<=e)&(lat>=s)&(lat<=n)&np.isfinite(mu)
    obs=(F[:,m]*clear[:,m]).sum(1); exp=(mu[m][None,:]*clear[:,m]).sum(1); raw=F[:,m].sum(1)
    series[rn]=pd.DataFrame({'obs_clear':obs,'exp_clear':exp,'raw':raw,'clear_frac':clear[:,m].mean(1)},index=dates)
    row={'region':rn,'n_cells':int(m.sum())}
    for pn,(a,b) in P.items():
        sl=(dates>=a)&(dates<=b); o,x=obs[sl],exp[sl]
        ratio=o.sum()/x.sum() if x.sum()>0 else np.nan
        # weekly block bootstrap CI
        wk=np.arange(sl.sum())//7; u=np.unique(wk); bs=[]
        for _ in range(1000):
            pick=rng.choice(u,len(u)); oo=sum(o[wk==k].sum() for k in pick); xx=sum(x[wk==k].sum() for k in pick); bs.append(oo/xx if xx>0 else np.nan)
        row[pn+'_ratio']=round(float(ratio),3); row[pn+'_ci']=f"{np.nanpercentile(bs,2.5):.2f}-{np.nanpercentile(bs,97.5):.2f}"; row[pn+'_clearfrac']=round(float(clear[sl][:,m].mean()),2); row[pn+'_rawMW']=round(float(raw[sl].mean()),0)
    row['closure_vs_2025same_%']=round((row['closure_ratio']/row['same_weeks_2025_ratio']-1)*100,0); row['closure_vs_pre_%']=round((row['closure_ratio']/row['pre(Dec1-Feb27)_ratio']-1)*100,0)
    row['RAW_closure_vs_2025same_%']=round((row['closure_rawMW']/row['same_weeks_2025_rawMW']-1)*100,0)
    rows.append(row)
T=pd.DataFrame(rows); T.to_csv('data/cloud_normalised_flare_table.csv',index=False)
pd.set_option('display.width',300); print(T[['region','n_cells','closure_ratio','closure_ci','closure_clearfrac','same_weeks_2025_ratio','same_weeks_2025_ci','same_weeks_2025_clearfrac','pre(Dec1-Feb27)_ratio','closure_vs_2025same_%','closure_vs_pre_%','RAW_closure_vs_2025same_%','blockade(Apr12-Jun17)_ratio','Jul-Sep26_ratio']].to_string())
pd.concat(series,axis=1).to_csv('data/cloud_normalised_daily.csv')
fig,ax=plt.subplots(5,2,figsize=(14,14),sharex=True)
for a,(rn,s) in zip(ax.ravel(),series.items()):
    w=s.resample('W').sum(); a.plot(w.index,w.obs_clear/w.exp_clear,label='clear-sky normalised (obs/expected)'); a.plot(w.index,w.raw/w.raw[:'2026-02-27'].mean(),alpha=.5,label='raw / baseline mean'); a.set_title(rn,fontsize=9); a.axhline(1,c='grey',lw=.5)
    for d,c in [('2026-02-28','r'),('2026-03-04','k'),('2026-04-08','g'),('2026-06-18','b')]: a.axvline(pd.Timestamp(d),color=c,ls='--',lw=.8)
ax[0,0].legend(fontsize=7); fig.suptitle('Flare activity index with per-cell clear-sky normalisation (NOAA-20 night; observable = clear-sky conf>0.05)'); fig.tight_layout(); fig.savefig('fig_cloud_normalised_regions.png',dpi=110)
