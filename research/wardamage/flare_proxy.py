import pandas as pd, numpy as np, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
h=pd.read_parquet('data/hotspots_gulf.parquet')
h=h[h.DAYNIGHT=='N'].copy()
h['cx']=(h.LONGITUDE/0.02).round().astype(int); h['cy']=(h.LATITUDE/0.02).round().astype(int)
base=h[h.date<'2026-02-28']; nd=base.date.nunique()
pers=base.groupby(['cx','cy']).date.nunique()/nd
flare_cells=pers[pers>=0.25].index           # cell lit on >=25% of baseline nights => permanent flare
print('persistent flare cells',len(flare_cells),'of',len(pers))
f=h.set_index(['cx','cy']).loc[lambda d:d.index.isin(flare_cells)].reset_index()
print('share of all night detections that are persistent flares: %.1f%%'%(100*len(f)/len(h)))
regions={'Qatar':(50.7,24.4,51.8,26.3),'Kuwait':(46.5,28.5,48.6,30.1),'Iraq-Basra':(46.3,30.1,48.1,31.6),'Iran-Khuzestan':(48.1,30.0,50.6,32.6),
 'Iran-SouthPars/Bushehr':(50.6,26.9,53.3,29.5),'Saudi-East':(47.8,24.3,50.6,28.4),'UAE':(51.9,22.6,56.0,25.6),
 'CTRL Iraq-Kirkuk/Kurdistan':(43.0,34.5,46.0,37.0),'CTRL Oman':(54.5,18.1,58.5,23.5),'CTRL Turkmenistan':(52.5,37.3,64.0,40.0)}
wk={}
for r,(w,s,e,n) in regions.items():
    x=f[f.LONGITUDE.between(w,e)&f.LATITUDE.between(s,n)]
    wk[r]=x.groupby('date').FRP.sum().reindex(pd.date_range('2025-01-01','2026-09-19'),fill_value=0).resample('W').sum()
wk=pd.DataFrame(wk); wk.to_csv('data/flare_weekly_frp.csv')
P={'base(Oct25-Feb27)':('2025-10-01','2026-02-27'),'closure(Mar4-Apr8)':('2026-03-04','2026-04-08'),'blockade(Apr12-Jun17)':('2026-04-12','2026-06-17'),'Jul-Sep26':('2026-07-01','2026-09-19'),'same wks 2025 (Mar4-Apr8)':('2025-03-04','2025-04-08')}
t=pd.DataFrame({k:wk[a:b].mean() for k,(a,b) in P.items()}).round(0)
t['closure_vs_base_%']=((t['closure(Mar4-Apr8)']/t['base(Oct25-Feb27)']-1)*100).round(0)
t['closure_vs_2025same_%']=((t['closure(Mar4-Apr8)']/t['same wks 2025 (Mar4-Apr8)']-1)*100).round(0)
pd.set_option('display.width',250); print(t.to_string()); t.to_csv('data/flare_period_table.csv')
fig,ax=plt.subplots(5,2,figsize=(14,14),sharex=True)
for a,r in zip(ax.ravel(),wk.columns):
    a.plot(wk.index,wk[r],lw=1.2); a.set_title(r+' — weekly night flare FRP (MW)',fontsize=9)
    for d,c in [('2026-02-28','r'),('2026-03-04','k'),('2026-04-08','g'),('2026-06-18','b')]: a.axvline(pd.Timestamp(d),color=c,ls='--',lw=.8)
fig.suptitle('Persistent-flare radiative power by region (VIIRS via GIBS, keyless). red=war start, black=Hormuz closed, green=ceasefire, blue=Hormuz reopen')
fig.tight_layout(); fig.savefig('flare_proxy_regions.png',dpi=110)
