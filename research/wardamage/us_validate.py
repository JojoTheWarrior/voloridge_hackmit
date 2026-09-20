"""Validate VIIRS night flare FRP against ND DMR flared volumes (gold label) and EIA state vented&flared / crude production. Train 2012-2018, test 2019+."""
import pandas as pd, numpy as np, json, sys, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from flarelib import *
basin=sys.argv[1]
h=load_gibs(f'data/gibs_{basin}'); h=h[h.dn=='N']; h=add_cells(h)
if basin=='bakken': h=h[(h.lon>-104.05)&(h.lat<49.0)&(h.lat>46.9)&(h.lon<-101.0)]   # ND part of Williston
print(basin,len(h),h.sat.value_counts().to_dict())
g=pd.read_csv('labels/nd_dmr_gas_monthly.csv',index_col=0,parse_dates=True)
vf=pd.read_excel('labels/NG_PROD_SUM_A_EPG0_VGV_MMCF_M.xls',sheet_name='Data 1',header=2); vf['Date']=pd.to_datetime(vf.Date).dt.to_period('M').dt.to_timestamp(); vf=vf.set_index('Date')
vf=vf.div(vf.index.days_in_month,axis=0)
cr=pd.read_csv('labels/eia_state_crude_kbd_monthly.csv',index_col=0,parse_dates=True)
if basin=='bakken': labels={'ND DMR flared (MCF/d)':g.flared_mcfd,'ND DMR gas produced':g.prod_mcf/g.index.days_in_month,'EIA ND crude (kb/d)':cr['North Dakota']}
else: labels={'EIA TX+NM vented&flared (MMcf/d)':vf['Texas Natural Gas Vented and Flared (MMcf)']+vf['New Mexico Natural Gas Vented and Flared (MMcf)'],'EIA TX+NM crude (kb/d)':cr['Texas']+cr['New Mexico']}
res={}
variants={}
for sat in ['N']:   # SNPP only for the long consistent record
    n=h[h.sat==sat]
    nights=n.groupby(['cx','cy']).date.nunique()
    for minn in (1,3,10):
        keep=nights[nights>=minn].index; nn=n.set_index(['cx','cy']); nn=nn[nn.index.isin(keep)].reset_index()
        m=monthly_metrics(nn,pd.date_range('2012-02-01','2026-08-31').difference(bad_days('N')))
        for met in ['frp_mean','frp_p75','frp_p90','frp_tophalf','n_det']: variants[f'{met}|min{minn}']=m[met]
V=pd.DataFrame(variants); V.to_csv(f'data/{basin}_monthly_flare_metrics.csv')
lab0=list(labels)[0]; y=labels[lab0]
# choose the metric variant on TRAIN years only
train=slice('2012-03','2018-12'); test=slice('2019-01','2026-12')
sel=[]
for k in V:
    d=pd.concat([np.log(V[k].replace(0,np.nan)),np.log(y)],axis=1,keys=['x','y']).dropna()
    sel.append((k, d[train].corr().iloc[0,1], d[train].diff().corr().iloc[0,1], d[test].corr().iloc[0,1], d[test].diff().corr().iloc[0,1]))
S=pd.DataFrame(sel,columns=['variant','train_r_loglevel','train_r_mom','test_r_loglevel','test_r_mom']).round(3); print(S.to_string()); S.to_csv(f'data/{basin}_variant_selection.csv',index=False)
best=S.sort_values('train_r_loglevel').iloc[-1].variant; print('selected on train:',best)
x=V[best]
for ln,yy in labels.items(): res[ln]=stats_pair(x,yy); print(ln,res[ln])
# out-of-sample: fit log y = a + b log x on train, predict test; baselines: last-train-value persistence, and train mean
d=pd.concat([np.log(x.replace(0,np.nan)),np.log(y)],axis=1,keys=['x','y']).dropna(); tr,te=d[train],d[test]
b,a=np.polyfit(tr.x,tr.y,1); pred=a+b*te.x
def r2(y,p): return 1-((y-p)**2).sum()/((y-y.mean())**2).sum()
oos={'elasticity_b':round(b,3),'test_R2_model':round(r2(te.y,pred),3),'test_R2_persistence(last 12m train mean)':round(r2(te.y,pd.Series(tr.y.iloc[-12:].mean(),index=te.index)),3),
     'test_MAPE_model_%':round(float((np.exp(pred)/np.exp(te.y)-1).abs().mean()*100),1),'test_MAPE_persistence_%':round(float((np.exp(tr.y.iloc[-12:].mean())/np.exp(te.y)-1).abs().mean()*100),1),'n_train':len(tr),'n_test':len(te)}
# rolling-origin: refit on expanding window, predict next 12 months
errs=[]; errp=[]
for yr in range(2016,2026):
    trn=d[:f'{yr-1}-12']; tst=d[f'{yr}-01':f'{yr}-12']
    if len(tst)<6: continue
    bb,aa=np.polyfit(trn.x,trn.y,1); errs+=list((np.exp(aa+bb*tst.x)/np.exp(tst.y)-1).abs()); errp+=list((np.exp(trn.y.iloc[-12:].mean())/np.exp(tst.y)-1).abs())
oos['rolling_MAPE_model_%']=round(float(np.mean(errs))*100,1); oos['rolling_MAPE_persistence_%']=round(float(np.mean(errp))*100,1)
# month-fixed-effects model (removes the satellite's seasonal detection artifact), fit on train only
import numpy.linalg as la
def design(dd): 
    M=np.zeros((len(dd),12)); M[np.arange(len(dd)),dd.index.month-1]=1; return np.column_stack([dd.x.values,M])
coef=la.lstsq(design(tr),tr.y.values,rcond=None)[0]; predm=pd.Series(design(te)@coef,index=te.index)
oos['elasticity_b_monthFE']=round(float(coef[0]),3); oos['test_R2_monthFE']=round(r2(te.y,predm),3); oos['test_MAPE_monthFE_%']=round(float((np.exp(predm)/np.exp(te.y)-1).abs().mean()*100),1)
ann=d.groupby(d.index.year).mean(); ann=ann[(d.groupby(d.index.year).size()>=10)]
oos['annual_r_loglevel']=round(float(ann.corr().iloc[0,1]),3); oos['annual_r_dlog']=round(float(ann.diff().corr().iloc[0,1]),3); oos['n_years']=len(ann)
print(oos); json.dump({'basin':basin,'selected_variant':best,'label':lab0,'pair_stats':res,'oos':oos},open(f'data/{basin}_validation.json','w'),indent=1,default=str)
fig,ax=plt.subplots(2,1,figsize=(12,8))
ax[0].plot(x.index,x/x[train].mean(),label=f'VIIRS SNPP night flare FRP ({best}), idx'); ax[0].plot(y.index[y.index>='2012'],(y/y[train].mean())[y.index>='2012'],label=lab0+', idx'); ax[0].axvline(pd.Timestamp('2019-01-01'),c='k',ls='--'); ax[0].legend(); ax[0].set_title(f'{basin}: satellite flare power vs label (train<2019 | test>=2019)')
ax[1].scatter(tr.x,tr.y,s=10,label='train'); ax[1].scatter(te.x,te.y,s=10,c='r',label='test'); xs=np.linspace(d.x.min(),d.x.max(),10); ax[1].plot(xs,a+b*xs,'k-'); ax[1].set_xlabel('log FRP'); ax[1].set_ylabel('log label'); ax[1].legend()
fig.tight_layout(); fig.savefig(f'fig_{basin}_validation.png',dpi=110)
