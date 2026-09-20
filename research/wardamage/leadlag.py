import sys, pandas as pd, numpy as np, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
R='/Users/tomalmog/projects/kingdom/voloridge_hackmit'; sys.path.insert(0,R)
import importlib; S=importlib.import_module('warsignal.analysis.stats')
p=pd.read_parquet(R+'/data/raw/finance/prices.parquet'); p['date']=pd.to_datetime(p.date)
px=p.pivot_table(index='date',columns='ticker',values='close')
g=pd.read_parquet(R+'/data/cache/gdelt_daily.parquet'); g['date']=pd.to_datetime(g.date); g=g.set_index('date')
h=pd.read_parquet('data/hotspots_gulf.parquet'); h=h[h.DAYNIGHT=='N']
def reg(w,s,e,n): 
    x=h[h.LONGITUDE.between(w,e)&h.LATITUDE.between(s,n)]; return x.groupby('date').FRP.sum().reindex(pd.date_range('2025-01-01','2026-09-19'),fill_value=0)
basra=reg(46.3,30.1,48.1,31.6); qatar=reg(50.7,24.4,51.8,26.3); ctrl=reg(43.0,34.5,46.0,37.0)+reg(54.5,18.1,58.5,23.5)
# shut-in index: log ratio of Hormuz-dependent flaring to control flaring, 7d rolling (controls cloud/season to first order)
idx=np.log((basra+qatar).rolling(7).mean()/ctrl.rolling(7).mean()).dropna(); idx.name='flare_shutin_idx'
idx.to_csv('data/flare_shutin_index.csv')
win=slice('2026-01-15','2026-07-15')
out={}
for name,b in {'Brent (BZ=F) level':px['BZ=F'],'TTF level':px['TTF=F'],'gkg.hormuz_share':g['gkg.hormuz_share']}.items():
    a=idx[win]; bb=b[win].dropna()
    lc=S.lagged_correlation(a,bb,10); pv=S.permutation_pvalue(a,bb,n_perm=500,max_lag=10)
    # differenced (weekly changes) - the honest test
    lcd=S.lagged_correlation(a.diff(5).dropna(),bb.diff(5).dropna(),10)
    out[name]=dict(level_best_lag=lc['best_lag'],level_best_r=round(lc['best_r'],2),perm_p=round(pv,3),diff5_best_lag=lcd['best_lag'],diff5_best_r=round(lcd['best_r'],2))
print(pd.DataFrame(out).T.to_string())
fig,ax=plt.subplots(3,1,figsize=(12,9),sharex=True)
ax[0].plot(basra.rolling(7).mean()['2025-10-01':],label='Basra night flare FRP 7d (MW)'); ax[0].plot(qatar.rolling(7).mean()['2025-10-01':]*5,label='Qatar x5'); ax[0].legend(); 
ax[1].plot(px['BZ=F']['2025-10-01':],c='k',label='Brent'); ax[1].legend(); ax2=ax[1].twinx(); ax2.plot(px['TTF=F']['2025-10-01':],c='orange',label='TTF'); ax2.legend(loc='lower right')
ax[2].plot(g['gkg.hormuz_share']['2025-10-01':].rolling(3).mean(),c='g',label='GDELT hormuz share (3d)'); ax[2].legend()
for a in ax:
    for d,c in [('2026-02-28','r'),('2026-03-04','k'),('2026-04-08','g'),('2026-06-18','b')]: a.axvline(pd.Timestamp(d),color=c,ls='--',lw=.8)
fig.tight_layout(); fig.savefig('flare_vs_brent_gdelt.png',dpi=110)
# timing table: first day each series crosses half of its eventual move
def half_cross(s,pre,post,start='2026-02-20'):
    lo=s[pre[0]:pre[1]].mean(); hi=s[post[0]:post[1]].mean(); mid=(lo+hi)/2; ss=s[start:]
    c=ss[(ss-mid)*(hi-lo)>0]; return c.index[0].date() if len(c) else None
print('half-move dates:', {'Basra flares (3d mean)':half_cross(basra.rolling(3).mean(),('2026-02-01','2026-02-27'),('2026-03-10','2026-03-31')),
 'Brent':half_cross(px['BZ=F'].dropna(),('2026-02-01','2026-02-27'),('2026-03-10','2026-03-31')),
 'GDELT hormuz':half_cross(g['gkg.hormuz_share'],('2026-02-01','2026-02-27'),('2026-03-10','2026-03-31'))})
