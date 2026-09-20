"""Eight predetermined training-rank wallet comparisons; public data, no identities."""
import sys,json
from pathlib import Path
import numpy as np
import pandas as pd
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'scripts'))
from access import get

def main():
 p=pd.read_parquet(R/'data/nba/wallet_market_pnl.parquet');p=p[p.valid]
 train=p[p.resolution<1735689600].groupby('wallet',observed=True).agg(pnl=('pnl','sum'),n=('pnl','size'))
 train=train[train.n>=10].sort_values(['pnl'],ascending=False)
 # Deterministic ranks span the distribution; never select by current leaderboard.
 ranks=np.unique(np.round(np.linspace(0,len(train)-1,8)).astype(int))
 total=p.groupby('wallet',observed=True).pnl.sum();rows=[]
 for rank in ranks:
  wallet=str(train.index[rank]);row={'wallet':wallet,'train_rank':int(rank+1),'train_pnl':float(train.iloc[rank].pnl),'sample_nba_pnl':float(total.loc[wallet])}
  for category in ['NBA','SPORTS','OVERALL']:
   name='nba_sanity_'+wallet+'_'+category
   meta,body=get(name,'https://data-api.polymarket.com/v1/leaderboard',{'user':wallet,'timePeriod':'ALL','category':category,'limit':1})
   row[category.lower()+'_http_status']=meta['status']
   try:
    data=json.loads(body);data=data if isinstance(data,list) else data.get('data',[])
    match=next((x for x in data if str(x.get('proxyWallet','')).lower()==wallet),None)
    value=float(match['pnl']) if match is not None else np.nan
   except (ValueError,TypeError,KeyError):value=np.nan
   row[category.lower()+'_leaderboard_pnl']=value
   row[category.lower()+'_signed_difference']=row['sample_nba_pnl']-value
   row[category.lower()+'_absolute_difference']=abs(row['sample_nba_pnl']-value)
  row['comparable']=False;row['note']='Current all-time board versus NBA sample Apr2024-Jun2025; differing windows, exclusions, accounting and categories. Error is mismatch, not validation accuracy.'
  rows.append(row);print('sanity rank',rank+1,'NBA difference',row['nba_signed_difference'],flush=True)
 pd.DataFrame(rows).to_csv(R/'data/nba/leaderboard_comparison.csv',index=False)
 # Three case-study games, chosen on pre-signal exposure, independent of forecast success.
 panel=pd.read_parquet(R/'expert_panel.parquet');catalog=pd.read_parquet(R/'data/nba/markets.parquet').set_index('market')
 cases=panel[(panel.cohort=='holdout')&(panel.horizon==24)].dropna(subset=['expert_prob']).nlargest(3,'total_expert_exposure')
 records=[]
 for _,r in cases.iterrows():
  token=catalog.loc[r.market].token0
  meta,body=get('nba_pricehistory_'+str(r.market),'https://clob.polymarket.com/prices-history',{'market':token,'startTs':int(r.timestamp-86400),'endTs':int(r.resolution),'fidelity':60})
  try:count=len(json.loads(body).get('history',[]))
  except (ValueError,AttributeError):count=0
  records.append({'market':r.market,'token':token,'route':'CLOB prices-history','http_status':meta['status'],'observations':count,'historical_spread':None,'note':'Even returned trade/mid history does not supply paired quotes or depth.'})
  meta,body=get('nba_book_'+str(r.market),'https://clob.polymarket.com/book',{'token_id':token})
  records.append({'market':r.market,'token':token,'route':'CLOB current book','http_status':meta['status'],'observations':None,'historical_spread':None,'note':'Current book cannot establish historical spread.'})
 (R/'data/nba/price_access.json').write_text(json.dumps(records,indent=2))
if __name__=='__main__':main()
