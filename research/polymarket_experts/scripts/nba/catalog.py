"""Freeze the selected market/token catalog from the read-only sibling Gamma cache."""
import gzip,json,re,hashlib
from pathlib import Path
import pandas as pd
R=Path(__file__).resolve().parents[2]
SOURCE=R.parent/'polymarket/data/gamma/vol10k.jsonl.gz'
def main():
 dest=R/'data/nba/markets.parquet'
 if dest.exists():
  print('Using frozen catalog:',len(pd.read_parquet(dest)));return
 rows=[]
 with gzip.open(SOURCE,'rt') as stream:
  for line in stream:
   m=json.loads(line)
   if not re.fullmatch(r'nba-[a-z]{2,4}-[a-z]{2,4}-\d{4}-\d\d-\d\d',m.get('slug','')):continue
   def arr(k):
    x=m.get(k,[]);return json.loads(x) if isinstance(x,str) else x
   tok=arr('clobTokenIds');prices=arr('outcomePrices');outcomes=arr('outcomes')
   if not m.get('closed') or len(tok)!=2 or len(prices)!=2:continue
   prices=list(map(float,prices))
   if min(abs(prices[0]),abs(prices[0]-1))>1e-4 or abs(sum(prices)-1)>1e-4:continue
   created=pd.to_datetime(m.get('createdAt'),utc=True,errors='coerce');resolution=pd.to_datetime(m.get('closedTime'),utc=True,errors='coerce')
   if pd.isna(created) or pd.isna(resolution):continue
   cohort='primary' if created>=pd.Timestamp('2024-04-01',tz='UTC') and resolution<pd.Timestamp('2025-07-01',tz='UTC') else ('v2_extension' if resolution>=pd.Timestamp('2026-04-28',tz='UTC') and resolution<pd.Timestamp('2026-08-01',tz='UTC') else None)
   if cohort is None:continue
   events=m.get('events',[]);event=str(events[0]['id']) if events else str(m['id'])
   rows.append(dict(market=str(m['id']),event_id=event,slug=m['slug'],question=m.get('question',''),category='NBA',token0=str(tok[0]),token1=str(tok[1]),outcome0=outcomes[0],outcome1=outcomes[1],outcome=int(round(prices[0])),created=int(created.timestamp()),resolution=int(resolution.timestamp()),cohort=cohort,neg_risk=bool(m.get('negRisk',False))))
 pd.DataFrame(rows).drop_duplicates('market',keep='last').to_parquet(dest,index=False,compression='zstd')
 print('Created catalog',len(rows))
if __name__=='__main__':main()
