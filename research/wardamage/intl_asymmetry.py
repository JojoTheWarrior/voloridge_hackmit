"""Exploratory follow-ups: (1) is |flare anomaly| (either sign) informative about production loss? (2) calibration restricted to high routine-flaring-intensity countries, chosen by FRP per kb/d (not by fit), applied to 2026."""
import pandas as pd, numpy as np, json
from scipy import stats as st
Q=pd.read_csv('data/intl_quarterly_yoy_panel.csv',parse_dates=['q']); EX=pd.read_csv('data/intl_where_it_works.csv'); W=pd.read_csv('data/war2026_prediction_vs_actual.csv')
cal=Q[Q.q<'2025-01-01']; out={}
out['abs_abs_r']=round(float(st.spearmanr(cal['df'].abs(),cal.dp.abs())[0]),3)
rows=[]
for nm,m in {'flare UP >50%':cal['df']>np.log(1.5),'flare DOWN >50%':cal['df']<np.log(.5),'|flare|<15%':cal['df'].abs()<np.log(1.15)}.items():
    s=cal[m]; rows.append({'condition':nm,'n':len(s),'n_countries':s.country.nunique(),'median_prod_%':round((np.exp(s.dp.median())-1)*100,1),'share_prod_down>10%':round(float((s.dp<np.log(.9)).mean()),2),'share_prod_up>10%':round(float((s.dp>np.log(1.1)).mean()),2)})
print(pd.DataFrame(rows).to_string()); pd.DataFrame(rows).to_csv('data/intl_asymmetry_table.csv',index=False)
hi=EX[EX.frp_per_kbd>=0.25].country.tolist(); lo=EX[EX.frp_per_kbd<0.25].country.tolist(); out['high_intensity_countries']=hi
for nm,grp in {'high_intensity':hi,'low_intensity':lo}.items():
    d=cal[cal.country.isin(grp)]; b,a,r,p,se=st.linregress(d['df'],d.dp); sd=float(np.std(d.dp-(a+b*d['df']),ddof=2))
    out[nm]={'slope':round(b,3),'intercept':round(a,3),'r':round(r,3),'n':len(d),'resid_sd':round(sd,3)}
    # leave-one-country-out r of predictions
    pr=[]
    for c in grp:
        tr=d[d.country!=c]; te=d[d.country==c]; bb,aa=np.polyfit(tr['df'],tr.dp,1); pr.append(pd.DataFrame({'p':aa+bb*te['df'],'y':te.dp}))
    pr=pd.concat(pr); out[nm]['LOCO_r']=round(float(pr.p.corr(pr.y)),3); out[nm]['LOCO_R2']=round(float(1-((pr.y-pr.p)**2).sum()/((pr.y-pr.y.mean())**2).sum()),3)
b,a,sd=out['high_intensity']['slope'],out['high_intensity']['intercept'],out['high_intensity']['resid_sd']
w=[]
for _,r in W.iterrows():
    if r.country in hi:
        x=np.log1p(r['flare_YoY_%']/100); p=a+b*x; w.append({'country':r.country,'flare_YoY_%':r['flare_YoY_%'],'pred_%':round((np.exp(p)-1)*100),'PI80':f"{(np.exp(p-1.28*sd)-1)*100:.0f}..{(np.exp(p+1.28*sd)-1)*100:.0f}",'actual_%':r['actual_prod_YoY_%(EIA)']})
out['war2026_high_intensity_only']=w; print(json.dumps(out,indent=1)); json.dump(out,open('data/intl_asymmetry.json','w'),indent=1)
