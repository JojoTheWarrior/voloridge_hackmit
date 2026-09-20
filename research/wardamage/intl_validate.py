"""Country-month flare FRP vs EIA crude production: per-country stats, named natural experiments, pooled calibration of d(production) on d(FRP), applied out-of-sample to the 2026 Gulf war."""
import pandas as pd, numpy as np, json, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from flarelib import stats_pair
M=pd.read_csv('data/intl_monthly_flare_frp.csv',index_col=0,parse_dates=True)
P=pd.read_csv('labels/eia_intl_crude_kbd_monthly.csv',index_col=0,parse_dates=True).rename(columns={'Russia':'Russian_Federation'})
cs=[c for c in M if c in P]; rows=[]
for c in cs:
    r=stats_pair(M[c][:'2024-12'],P[c][:'2024-12']); rows.append({'country':c,**{k:(v[0] if isinstance(v,tuple) else v) for k,v in r.items()}})
T=pd.DataFrame(rows).round(3); T.to_csv('data/intl_country_correlations.csv',index=False); pd.set_option('display.width',250); print(T.to_string())
# ---------- quarterly YoY panel (non-overlapping quarters), pre-2025 = calibration set
def q(s): 
    x=s.resample('QS').mean(); n=s.resample('QS').count(); return x[n>=3]
rec=[]
for c in cs:
    f,p=q(M[c]),q(P[c]); d=pd.concat([np.log(f.replace(0,np.nan)).diff(4),np.log(p.replace(0,np.nan)).diff(4)],axis=1,keys=['df','dp']).dropna()
    for t,r in d.iterrows(): rec.append({'country':c,'q':t,'df':r.df,'dp':r.dp})
Q=pd.DataFrame(rec); Q.to_csv('data/intl_quarterly_yoy_panel.csv',index=False)
cal=Q[Q.q<'2025-01-01']; war=Q[Q.q>='2026-01-01']
from scipy import stats as st
def fit(d): 
    b,a,r,p,se=st.linregress(d['df'],d.dp); return dict(slope=round(b,3),intercept=round(a,3),r=round(r,3),n=len(d),resid_sd=round(float(np.std(d.dp-(a+b*d['df']),ddof=2)),3))
res={'pooled_all':fit(cal)}
# country-cluster bootstrap for slope CI
rng=np.random.default_rng(1); bs=[]
for _ in range(2000):
    pick=rng.choice(cs,len(cs)); dd=pd.concat([cal[cal.country==c] for c in pick]); bs.append(st.linregress(dd['df'],dd.dp)[0])
res['pooled_all']['slope_ci95_cluster_boot']=[round(float(np.percentile(bs,2.5)),3),round(float(np.percentile(bs,97.5)),3)]
# placebo: pair each country's flare series with ANOTHER country's production (same quarters)
pl=[]; wide_f=cal.pivot(index='q',columns='country',values='df'); wide_p=cal.pivot(index='q',columns='country',values='dp')
for _ in range(1000):
    perm=rng.permutation(cs)
    while any(a==b for a,b in zip(cs,perm)): perm=rng.permutation(cs)
    x=np.concatenate([wide_f[a].values for a in cs]); y=np.concatenate([wide_p[b].values for b in perm]); ok=np.isfinite(x)&np.isfinite(y); pl.append(np.corrcoef(x[ok],y[ok])[0,1])
res['placebo_mismatched_country']={'mean_r':round(float(np.mean(pl)),3),'p95_r':round(float(np.percentile(pl,95)),3),'p_value_true_r':round(float((np.array(pl)>=res['pooled_all']['r']).mean()),4)}
# within-country (demeaned) 
cd=cal.copy(); cd[['df','dp']]=cd.groupby('country')[['df','dp']].transform(lambda s:s-s.mean()); res['within_country']=fit(cd)
# big-move subsets: the question the user asked -> conditional distribution of production change given a flare drop
cond=[]
for lo,hi in [(-9,-0.69),(-0.69,-0.36),(-0.36,-0.16),(-0.16,0.16),(0.16,9)]:
    s=cal[(cal['df']>lo)&(cal['df']<=hi)]
    cond.append({'flare_YoY_change_bin':f'{(np.exp(max(lo,-5))-1)*100:.0f}%..{(np.exp(min(hi,5))-1)*100:.0f}%','n_country_quarters':len(s),'n_countries':s.country.nunique(),'median_prod_change_%':round((np.exp(s.dp.median())-1)*100,1),'p10_%':round((np.exp(s.dp.quantile(.1))-1)*100,1),'p90_%':round((np.exp(s.dp.quantile(.9))-1)*100,1),'share_prod_down_>10%':round(float((s.dp<np.log(.9)).mean()),2),'share_prod_down_>30%':round(float((s.dp<np.log(.7)).mean()),2)})
CD=pd.DataFrame(cond); CD.to_csv('data/intl_conditional_calibration.csv',index=False); print(CD.to_string())
# leave-one-country-out predictive skill for big production moves
big=cal[cal.dp.abs()>np.log(1.15)]; res['big_prod_moves(|dP|>15%)']={**fit(big),'sign_agreement':round(float((np.sign(big['df'])==np.sign(big.dp)).mean()),3)}
res['flare_big_drop(<-30%)_sign_agreement_prod_down']={'n':int((cal['df']<np.log(.7)).sum()),'share_prod_down':round(float((cal[cal['df']<np.log(.7)].dp<0).mean()),3),'share_prod_down_>10%':round(float((cal[cal['df']<np.log(.7)].dp<np.log(.9)).mean()),3)}
print(json.dumps(res,indent=1))
# ---------- named natural experiments: (country, pre window, event window)
NE=[('Libya','2013 port blockades','2013-01','2013-06','2013-09','2014-05'),('Libya','2020 Haftar blockade','2019-07','2019-12','2020-02','2020-08'),('Libya','2014-16 civil war low','2012-07','2013-06','2015-07','2016-06'),
 ('Saudi_Arabia','Abqaiq Sep-2019','2019-06','2019-08','2019-09','2019-09'),('Saudi_Arabia','OPEC+ cut 2020','2020-01','2020-03','2020-05','2020-07'),('Iraq','OPEC+ cut 2020','2020-01','2020-03','2020-05','2020-07'),
 ('Kuwait','OPEC+ cut 2020','2020-01','2020-03','2020-05','2020-07'),('United_Arab_Emirates','OPEC+ cut 2020','2020-01','2020-03','2020-05','2020-07'),('Russian_Federation','OPEC+ cut 2020','2020-01','2020-03','2020-05','2020-07'),
 ('Kazakhstan','OPEC+ cut 2020','2020-01','2020-03','2020-05','2020-07'),('Algeria','OPEC+ cut 2020','2020-01','2020-03','2020-05','2020-07'),('Nigeria','OPEC+ cut 2020','2020-01','2020-03','2020-05','2020-07'),('Angola','OPEC+ cut 2020','2020-01','2020-03','2020-05','2020-07'),('Oman','OPEC+ cut 2020','2020-01','2020-03','2020-05','2020-07'),
 ('Venezuela','2016->2020 collapse','2016-01','2016-12','2020-01','2020-12'),('Iran','2018-19 sanctions','2017-07','2018-04','2019-07','2020-04'),('Iran','2012-13 sanctions','2012-02','2012-04','2013-02','2013-04'),('Iran','2016 sanctions relief','2015-01','2015-12','2016-07','2017-06'),
 ('Russian_Federation','Apr-May 2022','2022-01','2022-02','2022-04','2022-05'),('Kazakhstan','Aug-2022 Kashagan/Tengiz outage','2022-05','2022-07','2022-08','2022-09'),('Yemen','2015 war','2014-04','2015-02','2015-05','2016-03'),('Syria','2012->2014 collapse','2012-02','2012-06','2014-01','2014-12'),
 ('Nigeria','2016 Niger Delta Avengers','2015-07','2015-12','2016-05','2016-09'),('Iraq','2014 ISIS (north lost)','2014-01','2014-05','2014-07','2014-12')]
ne=[]
for c,nm,a,b,e,f in NE:
    if c not in M or c not in P: continue
    same=lambda s,x,y: s[x:y].mean()
    # seasonal control: compare event months with the same calendar months one year before the PRE window end, when windows are < 12 months
    dF=np.log(same(M[c],e,f)/same(M[c],a,b)); dP=np.log(same(P[c],e,f)/same(P[c],a,b))
    ne.append({'country':c,'episode':nm,'prod_change_%':round((np.exp(dP)-1)*100,1),'flare_change_%':round((np.exp(dF)-1)*100,1),'same_sign':bool(np.sign(dF)==np.sign(dP)),'ratio_dlogF/dlogP':round(dF/dP,2) if abs(dP)>0.02 else None})
NEd=pd.DataFrame(ne); NEd.to_csv('data/intl_natural_experiments.csv',index=False); print(NEd.to_string())
big_ne=NEd[NEd['prod_change_%'].abs()>=15]; res['named_experiments']={'n':len(NEd),'same_sign_all':round(float(NEd.same_sign.mean()),2),'n_big(|dP|>=15%)':len(big_ne),'same_sign_big':round(float(big_ne.same_sign.mean()),2),'r_dlog':round(float(np.corrcoef(np.log1p(NEd['prod_change_%']/100),np.log1p(NEd['flare_change_%']/100))[0,1]),3)}
# ---------- apply to 2026 Gulf war (true out-of-sample): Mar-May 2026 vs Mar-May 2025
b,a,sd=res['pooled_all']['slope'],res['pooled_all']['intercept'],res['pooled_all']['resid_sd']
bb,ab,sdb=res['big_prod_moves(|dP|>15%)']['slope'],res['big_prod_moves(|dP|>15%)']['intercept'],res['big_prod_moves(|dP|>15%)']['resid_sd']
w=[]
for c in ['Iraq','Qatar','Kuwait','Saudi_Arabia','United_Arab_Emirates','Iran','Oman']:
    if c not in M: continue
    dF=np.log(M[c]['2026-03':'2026-05'].mean()/M[c]['2025-03':'2025-05'].mean()); dP=np.log(P[c]['2026-03':'2026-05'].mean()/P[c]['2025-03':'2025-05'].mean())
    pred=a+b*dF
    w.append({'country':c,'flare_YoY_%':round((np.exp(dF)-1)*100,0),'pred_prod_%(pooled)':round((np.exp(pred)-1)*100,0),'pred_80%PI':f"{(np.exp(pred-1.28*sd)-1)*100:.0f}..{(np.exp(pred+1.28*sd)-1)*100:.0f}",'actual_prod_YoY_%(EIA)':round((np.exp(dP)-1)*100,0),'actual_in_PI':bool(pred-1.28*sd<=dP<=pred+1.28*sd)})
W=pd.DataFrame(w); W.to_csv('data/war2026_prediction_vs_actual.csv',index=False); print(W.to_string())
res['war2026']={'r_flare_vs_actual_dlog':round(float(np.corrcoef([np.log1p(x/100) for x in W['flare_YoY_%']],[np.log1p(x/100) for x in W['actual_prod_YoY_%(EIA)']])[0,1]),3),'spearman':round(float(st.spearmanr(W['flare_YoY_%'],W['actual_prod_YoY_%(EIA)'])[0]),3),'n':len(W),'PI_coverage':round(float(W.actual_in_PI.mean()),2)}
# which countries does the gauge work in? flaring intensity (FRP per kb/d) and label volatility as explanatory variables
ex=[]
for c in cs:
    k=cal[cal.country==c]
    ex.append({'country':c,'yoy_q_r':round(float(k['df'].corr(k.dp)),3),'frp_per_kbd':round(float(M[c][:'2024'].mean()/P[c]['2012':'2024'].mean()),3),'sd_prod_yoy':round(float(k.dp.std()),3),'sd_flare_yoy':round(float(k['df'].std()),3)})
EX=pd.DataFrame(ex).sort_values('yoy_q_r',ascending=False); EX.to_csv('data/intl_where_it_works.csv',index=False); print(EX.to_string())
res['where_it_works']={'spearman(r, flaring_intensity)':round(float(st.spearmanr(EX.yoy_q_r,EX.frp_per_kbd)[0]),3),'spearman(r, production_volatility)':round(float(st.spearmanr(EX.yoy_q_r,EX.sd_prod_yoy)[0]),3),'n_countries':len(EX)}
json.dump(res,open('data/intl_validation.json','w'),indent=1,default=str); print(json.dumps(res['named_experiments']),json.dumps(res['war2026']))
# figures
fig,ax=plt.subplots(1,3,figsize=(18,5.5))
ax[0].scatter((np.exp(cal['df'])-1)*100,(np.exp(cal.dp)-1)*100,s=6,alpha=.4); ax[0].set_xlim(-100,200); ax[0].set_ylim(-100,100); ax[0].set_xlabel('flare FRP YoY % (quarter)'); ax[0].set_ylabel('crude production YoY %'); ax[0].set_title(f"Calibration panel 2013-2024: n={len(cal)}, r={res['pooled_all']['r']}")
ax[0].scatter(W['flare_YoY_%'],W['actual_prod_YoY_%(EIA)'],c='r',s=40,label='2026 war (out of sample)'); [ax[0].annotate(r.country[:4],(r['flare_YoY_%'],r['actual_prod_YoY_%(EIA)'])) for _,r in W.iterrows()]; ax[0].legend()
ax[1].scatter(NEd['flare_change_%'],NEd['prod_change_%']); [ax[1].annotate(f"{r.country[:4]} {r.episode[:12]}",(r['flare_change_%'],r['prod_change_%']),fontsize=6) for _,r in NEd.iterrows()]; ax[1].axhline(0,c='grey'); ax[1].axvline(0,c='grey'); ax[1].set_xlabel('flare change %'); ax[1].set_ylabel('production change %'); ax[1].set_title('Named natural experiments')
for c in ['Libya','Iraq','Venezuela']:
    ax[2].plot(M[c].rolling(3).mean()/M[c][:'2024'].mean(),label=c+' flare (3m)'); ax[2].plot(P[c]['2012':]/P[c]['2012':'2024'].mean(),ls='--',label=c+' production')
ax[2].legend(fontsize=7); ax[2].set_title('Indexed flare FRP (solid) vs production (dashed)')
fig.tight_layout(); fig.savefig('fig_intl_calibration.png',dpi=110)
