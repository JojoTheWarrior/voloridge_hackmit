"""Dispatch exactly the amended family, with 10,000 resamples per evaluated test."""
import json,sys,hashlib
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.special import expit,logit
from scipy.optimize import minimize
from scipy.stats import norm,rankdata
R=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(R/'scripts'))
from inference import bh,loss_delta
B=10000;SEED=20260920;FAMILY=42

def bootstrap(x,seed=SEED):
 x=np.asarray(x,float);x=x[np.isfinite(x)];n=len(x)
 d=dict(n_events=n,estimate=float(x.mean()) if n else np.nan,resamples=0,status='insufficient_n',ci_low=np.nan,ci_high=np.nan,p_value=np.nan,mde_80pct=np.nan)
 if n>1:d['mde_80pct']=float((norm.ppf(1-.05/(2*FAMILY))+norm.ppf(.8))*x.std(ddof=1)/np.sqrt(n))
 if n<20:return d
 rng=np.random.default_rng(seed);means=np.concatenate([x[rng.integers(n,size=(100,n))].mean(1) for _ in range(B//100)])
 d.update(status='evaluated',resamples=B,ci_low=float(np.quantile(means,.025)),ci_high=float(np.quantile(means,.975)),p_value=float((1+(np.abs(means-x.mean())>=abs(x.mean())).sum())/(B+1)))
 return d

def compare(z,col='expert_prob',metric='brier'):
 z=z.dropna(subset=[col,'market_price','outcome'])
 d=bootstrap(loss_delta(z.outcome,z.market_price,z[col],metric))
 if len(z):
  if metric=='brier':a=(z.market_price-z.outcome)**2;b=(z[col]-z.outcome)**2
  else:
   y=z.outcome;pm=z.market_price.clip(.001,.999);pe=z[col].clip(.001,.999)
   a=-y*np.log(pm)-(1-y)*np.log1p(-pm);b=-y*np.log(pe)-(1-y)*np.log1p(-pe)
  d.update(market_loss=float(a.mean()),signal_loss=float(b.mean()))
 return d

def persistence():
 p=pd.read_parquet(R/'data/nba/wallet_market_pnl.parquet');p=p[p.valid]
 train=p[p.resolution<1735689600].groupby('wallet',observed=True).agg(train_pnl=('pnl','sum'),train_n=('pnl','size'))
 flags=pd.read_parquet(R/'data/nba/training_wallet_activity.parquet').set_index('wallet').market_maker
 train=train.join(flags).fillna({'market_maker':False})
 train=train[(train.train_n>=10)&~train.market_maker]
 fut=p[(p.resolution>=1735776000)&(p.resolution<1751328000)].groupby('wallet',observed=True).pnl.sum()
 w=train.join(fut.rename('future_pnl')).fillna({'future_pnl':0})
 w['decile']=pd.qcut(w.train_pnl.rank(method='first'),10,labels=False)+1
 w.to_parquet(R/'data/nba/persistence_wallets.parquet',compression='zstd')
 x=rankdata(w.train_pnl);y=rankdata(w.future_pnl);x=(x-x.mean())/x.std();y=(y-y.mean())/y.std();rho=float(np.mean(x*y))
 rng=np.random.default_rng(SEED);null=np.array([np.mean(x*rng.permutation(y)) for _ in range(B)])
 boots=[];wa=w.train_pnl.to_numpy();wb=w.future_pnl.to_numpy()
 for _ in range(B):
  ix=rng.integers(len(w),size=len(w));a=rankdata(wa[ix]);b=rankdata(wb[ix]);boots.append(np.corrcoef(a,b)[0,1])
 rank=dict(status='evaluated',n_events=len(w),estimate=rho,ci_low=float(np.nanquantile(boots,.025)),ci_high=float(np.nanquantile(boots,.975)),p_value=float((1+(abs(null)>=abs(rho)).sum())/(B+1)),resamples=B,mde_80pct=float((norm.ppf(1-.05/(2*FAMILY))+norm.ppf(.8))/np.sqrt(len(w)-3)),unit='wallets',note='Spearman; zero future profit retained for inactive training wallets; CI paired wallet bootstrap; correlation MDE approximate')
 a=w[w.decile==10].future_pnl.to_numpy();b=w[w.decile==1].future_pnl.to_numpy()
 means=np.concatenate([a[rng.integers(len(a),size=(100,len(a)))].mean(1)-b[rng.integers(len(b),size=(100,len(b)))].mean(1) for _ in range(B//100)])
 est=float(a.mean()-b.mean());se=np.sqrt(a.var(ddof=1)/len(a)+b.var(ddof=1)/len(b))
 dec=dict(status='evaluated',n_events=len(a)+len(b),estimate=est,ci_low=float(np.quantile(means,.025)),ci_high=float(np.quantile(means,.975)),p_value=float((1+(abs(means-est)>=abs(est)).sum())/(B+1)),resamples=B,mde_80pct=float((norm.ppf(1-.05/(2*FAMILY))+norm.ppf(.8))*se),unit='USD per wallet',note='Independent top/bottom wallet bootstrap; sample-period NBA PnL, not lifetime PnL')
 chart=[]
 for k,g in w.groupby('decile'):
  d=bootstrap(g.future_pnl);chart.append({'decile':int(k),'mean_future_pnl':float(g.future_pnl.mean()),'median_future_pnl':float(g.future_pnl.median()),'n':len(g),'ci_low':d['ci_low'],'ci_high':d['ci_high']})
 pd.DataFrame(chart).to_csv(R/'data/nba/persistence_deciles.csv',index=False)
 return rank,dec

def drift(panel):
 z=panel[(panel.cohort=='holdout')&(panel.horizon==24)].dropna(subset=['expert_prob']).copy()
 fills=pd.read_parquet(R/'data/nba/prices_v1.parquet',columns=['market','timestamp','market_price'])
 rows=[]
 for market,g in fills.groupby('market',observed=True,sort=False):
  q=z[z.market==market]
  if q.empty:continue
  r=q.iloc[0];d={'market':market,'divergence':r.divergence}
  for lag in [1,6,24]:
   target=r.timestamp+lag*3600;past=g[g.timestamp<=target]
   d[str(lag)]=float(r.divergence*(past.iloc[-1].market_price-r.market_price)) if len(past) and target-past.iloc[-1].timestamp<=48*3600 else np.nan
  rows.append(d)
 a=pd.DataFrame(rows).dropna();a.to_csv(R/'data/nba/drift.csv',index=False)
 x=a[['1','6','24']].to_numpy();se=x.std(0,ddof=1)/np.sqrt(len(x));t=x.mean(0)/se;k=int(np.argmax(abs(t)))
 rng=np.random.default_rng(SEED);null=[]
 for _ in range(B//100):
  signs=rng.choice([-1.,1.],size=(100,len(x)));null.extend(np.max(abs(signs@x/len(x)/se),axis=1))
 d=bootstrap(x[:,k]);d['p_value']=float((1+(np.asarray(null)>=max(abs(t))).sum())/(B+1));d['selected_lag_hours']=[1,6,24][k];d['note']='Joint game sign-flip max statistic over 1/6/24h; selected-lag CI is marginal, not selection-adjusted. 24h target reaches metadata close; no synthetic payout point.'
 return d

def main():
 original=hashlib.sha256((R/'prereg.json').read_bytes()).hexdigest();assert original=='05cc3745052423283536e4a78d0e334f217b51cfd33eea25788eaea858d13a71'
 amend=json.loads((R/'amendment_nba_v1.json').read_text());assert len(amend['family'])==FAMILY
 panel=pd.read_parquet(R/'expert_panel.parquet');assert len(panel)>0
 assert not panel.duplicated(['market','horizon']).any()
 assert not panel.duplicated(['event_id','horizon']).any(), 'Event-cluster correction required'
 hold=panel[panel.cohort=='holdout'];z=hold[hold.horizon==24]
 rank,dec=persistence();rows=[]
 for spec in amend['family']:
  id=spec['id'];note='';d=None
  if id.startswith(('brier_','logloss_','blend_brier_')):
   metric='logloss' if id.startswith('logloss') else 'brier';col='blend_prob' if id.startswith('blend') else 'expert_prob'
   d=compare(hold[hold.horizon==spec['horizon']],col,metric)
  elif id.startswith('threshold_'):d=compare(z,'prob_'+id)
  elif id.startswith('weight_'):d=compare(z,'expert_prob_'+id.removeprefix('weight_'))
  elif id.startswith('robust_'):
   v=spec['variant'];q=z[z.liquidity_bucket==v.removeprefix('liquidity_')] if v.startswith('liquidity_') else z
   d=compare(q,'expert_prob' if v.startswith('liquidity_') else 'prob_'+v)
   if v=='complete_pair_expost':note='Ex-post exclusion uses future inventory failures; deliberately biased diagnostic, never primary evidence.'
  elif id.startswith('placebo_'):d=compare(z,id)
  elif id=='persistence_rank':d=rank
  elif id=='persistence_decile':d=dec
  elif id=='outcome_divergence':
   train=panel[(panel.resolution<1735689600)&(panel.horizon==24)].dropna(subset=['expert_prob']);q=z.dropna(subset=['expert_prob'])
   def objective(beta):
    p=expit(logit(train.market_price.clip(.001,.999))+beta[0]+beta[1]*train.divergence)
    return float((-train.outcome*np.log(p.clip(.001,.999))-(1-train.outcome)*np.log(1-p.clip(.001,.999))).mean()+1e-6*np.dot(beta,beta))
   fit=minimize(objective,np.zeros(2),method='BFGS');assert fit.success,fit.message
   q=q.copy();q['corrected']=expit(logit(q.market_price.clip(.001,.999))+fit.x[0]+fit.x[1]*q.divergence)
   d=compare(q,'corrected','logloss');note='Fixed market logit offset plus fitted intercept/divergence; trained only on games resolved before 2025-01-01. Intercept means improvement not solely attributable to divergence.'
   (R/'data/nba/outcome_model.json').write_text(json.dumps({'intercept':float(fit.x[0]),'divergence_coefficient':float(fit.x[1]),'train_n':len(train),'holdout_n':len(q)}))
  elif id=='drift_max':d=drift(panel)
  elif id=='economic_2c':
   q=z.dropna(subset=['expert_prob']);gross=np.sign(q.divergence)*(q.outcome-q.market_price);d=bootstrap(gross-.02)
   costs=[{'cost_cents':100*c,**bootstrap(gross-c)} for c in [0,.01,.02,.05,.10]]
   (R/'data/nba/cost_sensitivity.json').write_text(json.dumps(costs,indent=2));note='Analytical one-share payoff at last execution; 2c assumed all-in cost; no order simulation, historical quote/depth or executable profit validation.'
  assert d is not None,id
  rows.append({'test_id':id,'primary':id==amend['primary_test'],'family_size':FAMILY,'metric':spec['target'],'expected_sign':spec['expected_sign'],'horizon_hours':spec.get('horizon',24),**d,'note':d.get('note',note),'original_prereg_sha256':original,'amendment_sha256':hashlib.sha256((R/'amendment_nba_v1.json').read_bytes()).hexdigest()})
  print(id,d['status'],d['n_events'],round(d['estimate'],6),d['p_value'],flush=True)
 out=pd.DataFrame(rows);out['q_value']=bh(out.p_value,FAMILY);out['reject_null']=out.q_value.lt(.05);out['supports_expected_positive']=out.reject_null & out.estimate.gt(0)&out.expected_sign.eq('positive')
 out.to_csv(R/'results.csv',index=False)
 pl=out[out.test_id.str.startswith('placebo_')];summary={'family_size':FAMILY,'evaluated':int(out.status.eq('evaluated').sum()),'two_sided_BH_survivors':int(out.reject_null.sum()),'expected_positive_BH_survivors':int(out.supports_expected_positive.sum()),'placebo_two_sided_raw_rejection_rate':float(pl.p_value.lt(.05).mean()),'placebo_positive_raw_rejection_rate':float((pl.p_value.lt(.05)&pl.estimate.gt(0)).mean()),'placebo_BH_rejection_rate':float(pl.reject_null.mean()),'placebo_count':len(pl),'seed':SEED,'resamples':B}
 (R/'data/nba/inference_summary.json').write_text(json.dumps(summary,indent=2));print(summary,flush=True)
if __name__=='__main__':main()
