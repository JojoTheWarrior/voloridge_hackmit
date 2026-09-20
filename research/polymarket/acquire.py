"""Low-concurrency cached historical prices, weather forecasts and public access probes."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from pmlib import DATA, ROOT, audited_json, cached_response

def hashed(s):
    return hashlib.sha256(str(s).encode()).hexdigest()

def select_weather():
    c = pd.read_parquet(DATA/'catalog_enriched.parquet')
    e = c.groupby('event_slug').agg(date=('date','first'),city=('city','first'),kind=('kind','first'),
             closed=('closed','all'),winners=('yes_final',lambda x:(x>=.99).sum()),
             binary=('yes_final',lambda x:((x<=.01)|(x>=.99)).all()))
    e=e[e.closed & e.binary & (e.winners==1) & (e.date<='2026-09-18')].reset_index()
    e['month']=e.date.str[:7]; e['hash']=e.event_slug.map(hashed)
    e=e.sort_values('hash'); e['round']=e.groupby(['city','month','kind']).cumcount()
    e=e.sort_values(['round','hash']).head(2400)
    e.to_parquet(DATA/'weather_sample_events.parquet',index=False)
    selected=c[c.event_slug.isin(e.event_slug)].copy()
    selected.to_parquet(DATA/'weather_sample_tokens.parquet',index=False)
    return selected

def save_history(tokens, start, end, tag):
    out=DATA/'prices';out.mkdir(exist_ok=True)
    pending=[str(t) for t in tokens if not (out/f'{t}.parquet').exists()]
    log=[]
    for i in range(0,len(pending),20):
        batch=pending[i:i+20]
        args=dict(markets=batch,start_ts=int(start),end_ts=int(end),fidelity=5)
        m,j=audited_json('https://clob.polymarket.com/batch-prices-history',read_batch=args,cache_dir='price_batches',retries=5)
        hist=(j or {}).get('history',{})
        if not isinstance(hist,dict): hist={}
        if m['status']!=200:
            print('BATCH ERROR',m['status'],str(j)[:180],flush=True)
            raise RuntimeError('Batch access failed; inspect cached response')
        for t in batch:
            rows=hist.get(t,[])
            df=pd.DataFrame(rows,columns=['t','p'])
            df['token']=t
            df.to_parquet(out/f'{t}.parquet',index=False)
            log.append(dict(token=t,tag=tag,status=m['status'],n=len(rows)))
    if log:
        p=DATA/'price_acquisition.jsonl'
        with p.open('a') as f:
            for r in log:f.write(json.dumps(r)+'\n')

def probes():
    c=pd.read_parquet(DATA/'catalog_enriched.parquet')
    rows=[]
    for label,lo,hi in [('early','2025-02-01','2025-12-31'),('middle','2026-01-01','2026-05-31'),('late','2026-06-01','2026-09-18')]:
        s=c[(c.date>=lo)&(c.date<=hi)].copy();s['hash']=s.market_id.map(hashed)
        for r in s.sort_values('hash').head(10).itertuples():
            t=int(pd.Timestamp(r.date,tz='UTC').timestamp())
            for variant,args in [('max',dict(interval='max',fidelity=60)),('explicit',dict(startTs=t-259200,endTs=t+172800,fidelity=5))]:
                m,j=audited_json('https://clob.polymarket.com/prices-history',dict(market=r.yes_token,**args))
                h=(j or {}).get('history',[])
                rows.append(dict(era=label,variant=variant,market_id=r.market_id,date=r.date,city=r.city,status=m['status'],n=len(h)))
    pd.DataFrame(rows).to_csv(DATA/'history_probes.csv',index=False)
    print('history probes',pd.DataFrame(rows).groupby(['era','variant']).n.agg(['count','sum']).to_string(),flush=True)

def weather():
    c=select_weather()
    # Group by month for a bounded explicit window; five-minute response sampling.
    for month,g in c.groupby('date'):
        start=pd.Timestamp(g.date.min(),tz='UTC')-pd.Timedelta(days=4)
        end=pd.Timestamp(g.date.max(),tz='UTC')+pd.Timedelta(days=2)
        save_history(g.yes_token,start.timestamp(),end.timestamp(),'weather_'+month)
        print('weather month',month,'tokens',len(g),'complete',flush=True)

def forecasts():
    c=pd.read_parquet(DATA/'weather_sample_tokens.parquet')
    sl=pd.read_csv(DATA/'ghcnh/ghcnh-station-list.csv').dropna(subset=['ICAO'])
    out=DATA/'forecasts';out.mkdir(exist_ok=True)
    for station,g in c[c.station.notna()].groupby('station'):
        st=sl[sl.ICAO==station]
        if st.empty:continue
        st=st.iloc[0]; dest=out/f'{station}.parquet'
        if dest.exists():continue
        params=dict(latitude=float(st.LATITUDE),longitude=float(st.LONGITUDE),start_date=g.date.min(),end_date=g.date.max(),
                    hourly='temperature_2m_previous_day3',models='gfs_seamless',timezone='GMT')
        m,j=audited_json('https://previous-runs-api.open-meteo.com/v1/forecast',params,cache_dir='forecast_http')
        if m['status']==200 and j and 'hourly' in j:
            pd.DataFrame(j['hourly']).to_parquet(dest,index=False)
        print('forecast',station,m['status'],flush=True)

PATTERNS={
 'iran':r'iran|hormuz', 'crypto':r'bitcoin.*(?:above|below|reach)|ethereum.*(?:above|below|reach)',
 'politics':r'election|president|nominee|win.*(?:senate|governor)',
 'fed':r'fed.*(?:rate|cut|decision)|cpi|inflation', 'hurricane':r'hurricane|landfall',
 'outage':r'outage|blackout|internet.*(?:down|shut)', 'heat':r'hottest.*(?:month|year)|warmest.*(?:month|year)'}

def other():
    d=pd.read_parquet(DATA/'gamma_snapshot.parquet');selection=DATA/'other_markets.parquet'
    rows=pd.read_parquet(selection).to_dict('records') if selection.exists() else []
    # Keep the originally frozen raw keyword sample on replay; semantic false
    # positives are transparently removed by other_panel.py, never replaced.
    categories=[] if selection.exists() else list(PATTERNS.items())
    for category,pattern in categories:
        s=d[d.question.str.contains(pattern,case=False,regex=True,na=False)].copy()
        s['hash']=s.id.map(hashed);s=s.sort_values('hash').head(60)
        for r in s.to_dict('records'):
            try:
                tokens=json.loads(r['clobTokenIds']);outcomes=json.loads(r['outcomes']);prices=json.loads(r['outcomePrices'])
                k=outcomes.index('Yes');token=tokens[k];y=float(prices[k])
                end=pd.Timestamp(r['endDate']);start=pd.Timestamp(r['createdAt'])
                if end.tzinfo is None:end=end.tz_localize('UTC')
                if start.tzinfo is None:start=start.tz_localize('UTC')
                # Bound to Jan 2025 and last available pre-snapshot day; no lifetime terminal prices.
                start=max(start,pd.Timestamp('2025-01-01',tz='UTC'))
                end=min(end+pd.Timedelta(days=2),pd.Timestamp('2026-09-19',tz='UTC'))
                if start>=end:continue
            except (ValueError,TypeError,KeyError):continue
            rows.append(dict(market_id=r['id'],category=category,question=r['question'],token=token,y=y,
                             created=r['createdAt'],end=r['endDate'],closed_time=r['closedTime'],condition_id=r['conditionId'],description=r['description']))
        print('other',category,len(s),flush=True)
        pd.DataFrame(rows).drop_duplicates(['market_id','category']).to_parquet(DATA/'other_markets.parquet',index=False)
    meta=pd.DataFrame(rows).drop_duplicates('token')
    meta['start_ts']=pd.to_datetime(meta.created,utc=True,format='mixed')
    meta['end_ts']=pd.to_datetime(meta.end,utc=True,format='mixed')+pd.Timedelta(days=2)
    all_history={t:[] for t in meta.token}
    for a in pd.date_range('2025-01-01','2026-09-18',freq='7D',tz='UTC'):
        b=min(a+pd.Timedelta(days=7),pd.Timestamp('2026-09-19',tz='UTC'))
        tokens=meta.loc[(meta.start_ts<b)&(meta.end_ts>a),'token'].tolist()
        for i in range(0,len(tokens),20):
            batch=tokens[i:i+20]
            m,j=audited_json('https://clob.polymarket.com/batch-prices-history',read_batch=dict(markets=batch,start_ts=int(a.timestamp()),end_ts=int(b.timestamp()),fidelity=60),cache_dir='other_batches')
            if m['status']!=200:raise RuntimeError(f'Other-history batch failed: {m["status"]}: {str(j)[:100]}')
            for t,h in (j or {}).get('history',{}).items():all_history[t].extend(h)
        print('other week',str(a.date()),len(tokens),'tokens',flush=True)
    out=DATA/'other_prices';out.mkdir(exist_ok=True)
    for t,h in all_history.items():
        pd.DataFrame(h,columns=['t','p']).drop_duplicates('t').sort_values('t').to_parquet(out/f'{t}.parquet',index=False)

def access():
    queries=[
      ('kalshi_markets','https://api.elections.kalshi.com/trade-api/v2/markets',dict(limit=100,status='open')),
      ('kalshi_historical_cutoff','https://api.elections.kalshi.com/trade-api/v2/historical/cutoff',None),
      ('deribit_options','https://www.deribit.com/api/v2/public/get_book_summary_by_currency',dict(currency='BTC',kind='option')),
      ('coinbase_spot','https://api.coinbase.com/v2/prices/BTC-USD/spot',None),
      ('data_trades','https://data-api.polymarket.com/trades',dict(limit=5)),
    ]
    rows=[]
    for name,url,params in queries:
        m,j=audited_json(url,params,cache_dir='access_http')
        (DATA/f'access_{name}.json').write_text(json.dumps(dict(meta=m,data=j),indent=2))
        rows.append(dict(name=name,status=m['status'],bytes=m['bytes']))
    c=pd.read_parquet(DATA/'catalog_enriched.parquet')
    live=c[(~c.closed)&(c.date>='2026-09-20')].copy()
    live['distance_to_half']=(live.yes_final-.5).abs()
    for r in live.sort_values(['city','date','distance_to_half']).groupby('city').head(1).head(12).itertuples():
        for endpoint in ['book','fee-rate']:
            m,j=audited_json('https://clob.polymarket.com/'+endpoint,dict(token_id=r.yes_token),cache_dir='access_http')
            (DATA/f'access_{endpoint}_{r.city}.json').write_text(json.dumps(dict(city=r.city,token=r.yes_token,meta=m,data=j),indent=2))
    pd.DataFrame(rows).to_csv(DATA/'access_summary.csv',index=False)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('stage',choices=['probes','weather','forecasts','other','access']);a=ap.parse_args()
    globals()[a.stage]()
