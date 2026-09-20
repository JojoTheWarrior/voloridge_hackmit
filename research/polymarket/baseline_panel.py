"""E's exact fixed horizon from original contract endDate; no terminal leakage."""
import json

import numpy as np
import pandas as pd

from pmlib import DATA, read_jsonl_gz
from weather_panel import history, asof

def main():
    c=pd.read_parquet(DATA/'weather_sample_tokens.parquet')
    raw={r['id']:r for r in read_jsonl_gz(DATA/'gamma/weather.jsonl.gz')}
    rows=[];descriptive=[]
    for r in c.itertuples():
        meta=raw.get(r.market_id)
        if not meta or not meta.get('endDate'):continue
        end=pd.Timestamp(meta['endDate']);cut=end.timestamp()-86400
        closed=pd.to_datetime(r.closed_time,utc=True,errors='coerce')
        t,p=history(r.yes_token)
        for hours in [168,24,6,1]:
            at=end.timestamp()-hours*3600
            if pd.notna(closed) and closed.timestamp()<=at:continue
            pp=asof(t,p,at,7200)
            if np.isfinite(pp):descriptive.append(dict(market_id=r.market_id,category='weather',hours=hours,p=pp,y=float(r.yes_final>=.99),date=r.date,volume=r.volume))
        if pd.notna(closed) and closed.timestamp()<=cut:continue
        pp=asof(t,p,cut,7200)
        if not np.isfinite(pp):continue
        rows.append(dict(market_id=r.market_id,category='weather',event_slug=r.event_slug,
                         date=pd.Timestamp(cut,unit='s',tz='UTC').strftime('%Y-%m-%d'),
                         p=pp,y=float(r.yes_final>=.99),volume=r.volume,question=r.event_slug+' '+r.bucket))
    oc=pd.read_parquet(DATA/'other_calibration.parquet')
    pd.concat([pd.DataFrame(rows),oc],ignore_index=True).drop_duplicates('market_id').to_parquet(DATA/'baseline_calibration.parquet',index=False)
    meta=pd.read_parquet(DATA/'other_markets_screened.parquet')
    for r in meta.itertuples():
        path=DATA/'other_prices'/f'{r.token}.parquet'
        if not path.exists() or not (r.y<=.01 or r.y>=.99):continue
        h=pd.read_parquet(path).sort_values('t');t=h.t.to_numpy(float);p=h.p.to_numpy(float)
        timestamp=pd.to_datetime(r.end,utc=True,errors='coerce')
        if h.empty or pd.isna(timestamp):continue
        end=timestamp.timestamp();closed=pd.to_datetime(r.closed_time,utc=True,errors='coerce')
        for hours in [168,24,6,1]:
            at=end-hours*3600
            if pd.notna(closed) and closed.timestamp()<=at:continue
            pp=asof(t,p,at,7200)
            if np.isfinite(pp):descriptive.append(dict(market_id=r.market_id,category=r.category,hours=hours,p=pp,y=float(r.y>=.99),date=pd.Timestamp(at,unit='s').strftime('%Y-%m-%d'),volume=np.nan))
    pd.DataFrame(descriptive).to_parquet(DATA/'baseline_horizon_descriptive.parquet',index=False)
    print('baseline weather rows',len(rows),'general rows',len(oc),flush=True)

if __name__=='__main__':
    main()
