"""Approximate causal NBA fills ledger and forecast panel. No lifecycle inference."""
import json,sys,time
from pathlib import Path
import numpy as np
import pandas as pd
R=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(R/'scripts'))
EXCHANGES={'0x4bfb41d5b3570defd03c39a9a4d8de6bd8b8982e','0xc5d563a36ae78145c45a50134d48a1215220f80a','0xe111180000d2663c0091e4f400237545b87b996b','0xe2222d279d744050d28e00520010520000310f59'}

def normalize(markets,version='v1'):
 paths=sorted((R/'data/nba/filtered').glob(version+'_*.parquet'))
 raw=pd.concat([pd.read_parquet(p) for p in paths],ignore_index=True)
 nraw=len(raw)
 raw=raw.drop_duplicates(['block_number','log_index','contract'])
 raw=raw[~raw.maker.str.lower().isin(EXCHANGES)].copy()
 making=raw.maker_amount_filled.astype(float)/1e6;taking=raw.taker_amount_filled.astype(float)/1e6;fee=raw.fee.astype(float)/1e6
 buy=raw.maker_asset_id.eq('0') if version=='v1' else raw.side.eq(0)
 token=np.where(buy,raw.taker_asset_id,raw.maker_asset_id) if version=='v1' else raw.token_id.to_numpy()
 shares=np.where(buy,taking-(fee if version=='v1' else 0),-making)
 cash=np.where(buy,-making-(fee if version=='v2' else 0),taking-fee)
 notional=np.where(buy,making,taking)
 price=np.where(buy,making/taking,taking/making)
 tokens=pd.concat([markets.assign(token=markets.token0,token_index=0),markets.assign(token=markets.token1,token_index=1)])
 f=pd.DataFrame({'timestamp':raw.timestamp.to_numpy(dtype='int64'),'block':raw.block_number.to_numpy(dtype='int64'),'log_index':raw.log_index.to_numpy(dtype='int64'),'wallet':raw.maker.str.lower().to_numpy(),'token':token,'shares':shares,'cash':cash,'notional':notional,'price':price,'buy':buy.to_numpy()})
 f=f.merge(tokens[['token','market','token_index','created','resolution','outcome','cohort']],on='token',validate='many_to_one')
 f=f[(f.timestamp>=f.created)&(f.timestamp<=f.resolution)&(f.price>=0)&(f.price<=1)&(f.notional>0)].sort_values(['timestamp','block','log_index']).reset_index(drop=True)
 f['market_price']=np.where(f.token_index.eq(0),f.price,1-f.price)
 f['net_shares']=f.groupby(['wallet','market','token_index'],sort=False).shares.cumsum()
 f['negative_now']=f.net_shares.lt(-1e-6)
 f['buy_volume']=np.where(f.buy,f.notional,0);f['sell_volume']=np.where(f.buy,0,f.notional)
 neg=f[f.negative_now].groupby(['wallet','market']).timestamp.min().rename('negative_first')
 f=f.join(neg,on=['wallet','market'])
 del raw, tokens
 import gc
 gc.collect()
 for col in ['wallet','market','cohort']:
  f[col]=f[col].astype('category')
 f=f.drop(columns=['token','created'])
 f[['market','timestamp','market_price','notional']].to_parquet(R/f'data/nba/prices_{version}.parquet',index=False,compression='zstd')
 bad=f.negative_first.notna()
 summary={'version':version,'raw_filtered_rows':nraw,'normalized_rows':len(f),'wallets':f.wallet.nunique(),'markets':f.market.nunique(),'wallet_market_pairs':f.groupby(['wallet','market']).ngroups,'negative_pairs':neg.size,'wallets_with_negative_pair':f.loc[bad,'wallet'].nunique(),'removed_pair_notional_fullpath':float(f.loc[bad,'notional'].sum()),'total_wallet_side_notional':float(f.notional.sum()),'negative_row_count':int(f.negative_now.sum()),'note':'Full-path totals are diagnostics; primary snapshot exclusions use negative_first <= signal time.'}
 (R/f'data/nba/ledger_audit_{version}.json').write_text(json.dumps(summary,indent=2));print(summary,flush=True)
 return f

def group_state(f):
 x=f.assign(q0=np.where(f.token_index.eq(0),f.shares,0),q1=np.where(f.token_index.eq(1),f.shares,0))
 pairs=x.groupby(['wallet','market'],sort=False).agg(q0=('q0','sum'),q1=('q1','sum'),cash=('cash','sum'),cost=('buy_volume','sum'),buy_volume=('buy_volume','sum'),sell_volume=('sell_volume','sum'),fills=('cash','size'),notional=('notional','sum'),negative_first=('negative_first','min'),resolution=('resolution','first'),outcome=('outcome','first')).reset_index()
 pairs['pnl']=pairs.cash+pairs.q0*pairs.outcome+pairs.q1*(1-pairs.outcome)
 pairs['valid']=pairs.negative_first.isna()
 pairs.to_parquet(R/'data/nba/wallet_market_pnl.parquet',index=False,compression='zstd')
 good=pairs[pairs.valid].sort_values(['resolution','market','wallet']).copy()
 good['n']=1;good['wins']=good.pnl.gt(0).astype(int)
 for col in ['pnl','cost','n','wins']:
  good['past_'+col]=good.groupby('wallet',sort=False)[col].cumsum()
 history=good[['wallet','resolution','past_pnl','past_cost','past_n','past_wins']].drop_duplicates(['wallet','resolution'],keep='last').sort_values('resolution')
 flow=f[['wallet','timestamp','notional','buy_volume','sell_volume','cash']].copy();flow['n_fills']=1
 for col in ['notional','buy_volume','sell_volume','cash','n_fills']:
  flow['flow_'+col]=flow.groupby('wallet',sort=False)[col].cumsum()
 flow=flow[['wallet','timestamp']+[c for c in flow if c.startswith('flow_')]].drop_duplicates(['wallet','timestamp'],keep='last').sort_values('timestamp')
 return pairs,history,flow

def build_snapshots(f,markets,history,flow):
 holders=[];base=[]
 for market,g in f.groupby('market',sort=False):
  meta=markets.set_index('market').loc[market]
  for horizon in [24,6,1]:
   t=int(meta.resolution-horizon*3600)
   if t<=meta.created:continue
   z=g[g.timestamp<=t]
   if z.empty:continue
   last=z.iloc[-1];stale=t-int(last.timestamp)
   if stale>48*3600:continue
   w=z.assign(q0=np.where(z.token_index.eq(0),z.shares,0),q1=np.where(z.token_index.eq(1),z.shares,0)).groupby('wallet',sort=False).agg(q0=('q0','sum'),q1=('q1','sum'),negative_first=('negative_first','min')).reset_index()
   w['valid_asof']=w.negative_first.isna()|w.negative_first.gt(t)
   w=w[(w.q0+w.q1)>1e-6].copy()
   w['view']=w.q0/(w.q0+w.q1);w['size']=w.q0+w.q1
   w['market']=market;w['horizon']=horizon;w['timestamp']=t
   holders.append(w)
   base.append({'market':market,'event_id':meta.event_id,'category':'NBA','question':meta.question,'horizon':horizon,'timestamp':t,'resolution':int(meta.resolution),'market_price':float(last.market_price),'price_staleness_hours':stale/3600,'outcome':int(meta.outcome),'pre_signal_notional':float(z.notional.sum()),'n_holders_raw':len(w),'n_holders_negative_asof':int((~w.valid_asof).sum()),'quality_status':'approximate_fills_only','cohort':'train' if t<1735689600 else ('holdout' if t>=1735776000 else 'embargo')})
 h=pd.concat(holders,ignore_index=True).sort_values('timestamp')
 h=pd.merge_asof(h,history,left_on='timestamp',right_on='resolution',by='wallet',allow_exact_matches=False,direction='backward').drop(columns='resolution')
 h=pd.merge_asof(h,flow,on='timestamp',by='wallet',allow_exact_matches=True,direction='backward')
 for col in [c for c in h if c.startswith('past_') or c.startswith('flow_')]:h[col]=h[col].fillna(0)
 h['market_maker']=(h.flow_n_fills>=100)&(h.flow_buy_volume>=.25*h.flow_notional)&(h.flow_sell_volume>=.25*h.flow_notional)&(h.flow_notional/(1+h.flow_cash.abs())>10)
 h.to_parquet(R/'data/nba/holder_panel.parquet',index=False,compression='zstd')
 return pd.DataFrame(base),h

def select_experts(h,variant='primary'):
 z=h[h.valid_asof & (~h.market_maker if variant!='include_mm' else True)].copy()
 minpast=5 if variant=='minpast5' else (20 if variant=='minpast20' else 10)
 z=z[z.past_n>=minpast]
 threshold=10000
 if variant.startswith('threshold_'):
  val=variant.removeprefix('threshold_')
  if val.isdigit():threshold=float(val)
  else:
   z=z[z.past_pnl>0].sort_values('past_pnl',ascending=False)
   return z.head(25 if val=='top25' else max(1,int(np.ceil(.1*len(z)))))
 z=z[z.past_pnl>threshold]
 if variant=='exclude_top3':z=z.drop(z.nlargest(3,'flow_notional').index)
 if variant=='complete_pair_expost':z=z[z.negative_first.isna()]
 return z

def prob(z,weight='pnl_size'):
 if len(z)<3:return np.nan
 weights={'equal':np.ones(len(z)),'pnl':z.past_pnl,'size':z['size'],'pnl_size':z.past_pnl*z['size'],'roi_shrunk':z.past_pnl/(z.past_cost+1000),'hit_rate_shrunk':(z.past_wins+5)/(z.past_n+10)}[weight]
 return float(np.average(z['view'],weights=weights)) if np.sum(weights)>0 else np.nan

def add_signals(base,h):
 variants=['threshold_1000','threshold_5000','threshold_50000','threshold_top25','threshold_top10percent','minpast5','minpast20','include_mm','exclude_top3','complete_pair_expost']
 rows=[]
 train=h[h.timestamp<1735689600]
 edges={col:np.unique(np.quantile(train[col],[.2,.4,.6,.8])) for col in ['flow_notional','flow_n_fills']}
 h=h.copy()
 for col in edges:h['bin_'+col]=np.searchsorted(edges[col],h[col])
 for key,g in h.groupby(['market','horizon'],sort=False):
  z=select_experts(g)
  d={'market':key[0],'horizon':key[1],'n_experts':len(z),'total_expert_exposure':float(z['size'].sum()),'n_market_makers':int(g.market_maker.sum()),'n_clean_holders':int(g.valid_asof.sum())}
  for weight in ['equal','pnl','size','pnl_size','roi_shrunk','hit_rate_shrunk']:d['expert_prob_'+weight]=prob(z,weight)
  d['expert_prob']=d['expert_prob_pnl_size']
  for v in variants:d['prob_'+v]=prob(select_experts(g,v))
  pool=g[g.valid_asof&~g.market_maker&(g.past_n>=10)]
  for k in range(10):
   value=np.nan;dist=[]
   if len(z)>=3 and len(pool)>=len(z):
    seed=4100+k+int(key[0])*31+key[1]
    rng=np.random.default_rng(seed);available=pool.copy();views=[];weights=[]
    for _,expert in z.iterrows():
     distance=(available.bin_flow_notional-expert.bin_flow_notional).abs()+(available.bin_flow_n_fills-expert.bin_flow_n_fills).abs()
     close=available[distance==distance.min()]
     ix=rng.choice(close.index.to_numpy());chosen=available.loc[ix]
     views.append(chosen['view']);weights.append(expert.past_pnl*chosen['size']);dist.append(float(distance.loc[ix]));available=available.drop(ix)
    value=float(np.average(views,weights=weights))
   d[f'placebo_{k:02d}']=value;d[f'placebo_distance_{k:02d}']=np.mean(dist) if dist else np.nan
  rows.append(d)
 out=base.merge(pd.DataFrame(rows),on=['market','horizon'],validate='one_to_one')
 out['divergence']=out.expert_prob-out.market_price;out['blend_prob']=.5*(out.expert_prob+out.market_price)
 cuts=np.quantile(out.loc[(out.cohort=='train')&(out.horizon==24),'pre_signal_notional'],[1/3,2/3])
 out['liquidity_bucket']=pd.cut(out.pre_signal_notional,[-np.inf,*cuts,np.inf],labels=['low','mid','high']).astype(str)
 out.to_parquet(R/'expert_panel.parquet',index=False,compression='zstd')
 (R/'data/nba/train_cuts.json').write_text(json.dumps({'liquidity':cuts.tolist(),'placebo_bins':{k:v.tolist() for k,v in edges.items()}},indent=2))
 print('PANEL',len(out),'rows; eligible',out.groupby(['cohort','horizon']).expert_prob.count().to_dict(),flush=True)
 return out

def main():
 markets=pd.read_parquet(R/'data/nba/markets.parquet');markets=markets[markets.cohort=='primary']
 f=normalize(markets);pairs,history,flow=group_state(f)
 base,h=build_snapshots(f,markets,history,flow)
 add_signals(base,h)
if __name__=='__main__':main()
