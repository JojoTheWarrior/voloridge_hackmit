"""Descriptive current public quotes and contract checks. No backtest or orders."""
import json
import re

import numpy as np
import pandas as pd

from pmlib import DATA

def main():
    pm=json.loads((DATA/'access_bitcoin-above-on-september-20-2026.json').read_text())
    kal=json.loads((DATA/'access_kalshi_btc_noon.json').read_text())
    rows=[]
    for m in pm['data'][0]['markets']:
        strike=float(re.search(r'\$([\d,]+)',m['question']).group(1).replace(',',''))
        rows.append(dict(venue='Polymarket',strike=strike,bid=m.get('bestBid'),ask=m.get('bestAsk'),
                         resolves_at=m.get('endDate'),source='Binance BTC/USDT 12:00 ET 1-minute candle close',
                         fetched_at=pm['meta']['fetched_at'],id=m['id'],status='closed' if m.get('closed') else 'active'))
    for m in kal['data']['markets']:
        try:
            strike=float(m['floor_strike'])
            bid=float(m.get('yes_bid_dollars') or 0);ask=float(m.get('yes_ask_dollars') or 1)
            if m.get('status')!='active' or float(m.get('yes_ask_size_fp') or 0)<=0:
                bid=ask=np.nan
        except (KeyError,TypeError,ValueError):continue
        rows.append(dict(venue='Kalshi',strike=strike,bid=bid,ask=ask,resolves_at=m['close_time'],
                         source='CF Benchmarks BRTI 60-second average before 12:00 ET',
                         fetched_at=kal['meta']['fetched_at'],id=m['ticker'],status=m.get('status')))
    q=pd.DataFrame(rows);q.to_parquet(DATA/'cross_venue_snapshot.parquet',index=False)
    # Compare near-equal strikes descriptively; reference index/payoff conventions
    # and sampling timestamps differ, so these are not identical claims.
    a=q[q.venue=='Polymarket'].sort_values('strike');b=q[q.venue=='Kalshi'].sort_values('strike')
    pairs=pd.merge_asof(a,b,on='strike',direction='nearest',tolerance=1,suffixes=('_pm','_kalshi'))
    pairs['mid_gap_pm_minus_kalshi']=(pairs.bid_pm+pairs.ask_pm-pairs.bid_kalshi-pairs.ask_kalshi)/2
    pairs['identical_contract']=False
    pairs.to_csv(DATA/'cross_venue_pairs.csv',index=False)
    # Current Deribit call-spread digital approximation: dollar-converted option
    # mid differences / strike interval, ignoring small discounting over <=days.
    d=json.loads((DATA/'access_deribit_options.json').read_text())['data']['result'];opts=[]
    for o in d:
        parts=o['instrument_name'].split('-')
        if len(parts)!=4 or parts[-1]!='C':continue
        bid=o.get('bid_price');ask=o.get('ask_price');index=o.get('estimated_delivery_price')
        if bid is None or ask is None or not index:continue
        try:expiry=pd.to_datetime(parts[1],format='%d%b%y',utc=True)+pd.Timedelta(hours=8)
        except ValueError:continue
        opts.append(dict(expiry=expiry,strike=float(parts[2]),call_usd=(bid+ask)/2*float(index),bid=bid,ask=ask))
    od=pd.DataFrame(opts);digital=[]
    for expiry,g in od.groupby('expiry'):
        if expiry>pd.Timestamp('2026-09-23',tz='UTC'):continue
        g=g.sort_values('strike');ks=g.strike.to_numpy();calls=g.call_usd.to_numpy()
        for i in range(len(g)-1):
            prob=(calls[i]-calls[i+1])/(ks[i+1]-ks[i])
            digital.append(dict(expiry=str(expiry),strike=(ks[i]+ks[i+1])/2,probability=prob,
                                valid=bool(0<=prob<=1),note='Exploratory risk-neutral call-spread approximation; different maturity and settlement index from Polymarket.'))
    pd.DataFrame(digital).to_parquet(DATA/'options_snapshot.parquet',index=False)
    books=[]
    for p in sorted(DATA.glob('access_book_*.json')):
        j=json.loads(p.read_text());book=j.get('data') or {}
        bids=[(float(x['price']),float(x['size'])) for x in book.get('bids',[])]
        asks=[(float(x['price']),float(x['size'])) for x in book.get('asks',[])]
        if not bids or not asks:continue
        best_bid=max(x[0] for x in bids);best_ask=min(x[0] for x in asks)
        depth=sum(price*size for price,size in asks if price<=best_ask+.01)
        fee_path=DATA/f'access_fee-rate_{j["city"]}.json'
        fee=json.loads(fee_path.read_text()).get('data') if fee_path.exists() else None
        books.append(dict(city=j['city'],token=j['token'],bid=best_bid,ask=best_ask,spread=best_ask-best_bid,
                          ask_dollars_within_one_cent=depth,has_100_dollars_within_one_cent=depth>=100,
                          fetched_at=j['meta']['fetched_at'],raw_fee=json.dumps(fee)))
    pd.DataFrame(books).to_csv(DATA/'current_cost_audit.csv',index=False)
    print('cross venue',len(q),'quotes;',pairs.mid_gap_pm_minus_kalshi.notna().sum(),'near-equal strike pairs; books',len(books),flush=True)

if __name__=='__main__':
    main()
