"""Public-source panels for B--F, with explicit temporal and contract-matching limits."""
import json
import shutil

import numpy as np
import pandas as pd

from pmlib import DATA, ROOT
from weather_panel import asof

def main():
    # Read siblings, write only this research folder; record provenance of copied inputs.
    inputs={
        'gdelt_daily.parquet':ROOT.parent.parent/'voloridge_hackmit/data/cache/gdelt_daily.parquet',
        'iran_timeline.csv':ROOT.parent.parent/'voloridge_hackmit/data/reference/iran_timeline.csv',
        'satellite_scoreboard.csv':ROOT.parent/'wardamage/score_out/scoreboard.csv',
        'flare_daily.parquet':ROOT.parent/'markets/data/flare_daily.parquet',
    }
    local=DATA/'context';local.mkdir(exist_ok=True)
    for name,path in inputs.items():
        if path.exists() and not (local/name).exists():shutil.copyfile(path,local/name)
    m=pd.read_parquet(DATA/'other_markets.parquet')
    # A bare 'ceasefire' also matched Ukraine/Gaza; Iran tests require Iran/Hormuz text.
    m=m[(m.category!='iran')|m.question.str.contains('iran|hormuz',case=False,regex=True)].copy()
    m=m[~((m.category=='hurricane')&m.question.str.contains('NHL|Stanley Cup|Carolina Hurricanes',case=False,regex=True))]
    m=m[(m.category!='heat')|m.question.str.contains(r'year on record|month on record',case=False,regex=True)].copy()
    m.to_parquet(DATA/'other_markets_screened.parquet',index=False)
    rows=[];scores=[];anchor_rows=[]
    timeline=pd.read_csv(local/'iran_timeline.csv')
    for r in m.itertuples():
        path=DATA/'other_prices'/f'{r.token}.parquet'
        if not path.exists():continue
        h=pd.read_parquet(path).drop_duplicates('t').sort_values('t')
        if h.empty:continue
        t=h.t.to_numpy(float);p=h.p.to_numpy(float)
        days=pd.date_range(pd.to_datetime(t.min(),unit='s',utc=True).ceil('D'),pd.to_datetime(t.max(),unit='s',utc=True).floor('D'),freq='D')
        for d in days:
            p0=asof(t,p,d.timestamp()-86400,7200);p1=asof(t,p,d.timestamp(),7200)
            rows.append(dict(market_id=r.market_id,category=r.category,question=r.question,date=d.strftime('%Y-%m-%d'),p=p1,return_=p1-p0))
        end=pd.Timestamp(r.end)
        if end.tzinfo is None:end=end.tz_localize('UTC')
        cutoff=end.timestamp()-86400
        pp=asof(t,p,cutoff,7200)
        # Exclude markets whose actual known closure precedes the scheduled cutoff.
        closed=pd.to_datetime(r.closed_time,utc=True,errors='coerce')
        if np.isfinite(pp) and (r.y<=.01 or r.y>=.99) and (pd.isna(closed) or closed.timestamp()>cutoff):
            scores.append(dict(market_id=r.market_id,category=r.category,date=pd.Timestamp(cutoff,unit='s',tz='UTC').strftime('%Y-%m-%d'),p=pp,y=float(r.y>=.99),question=r.question))
        if r.category=='iran':
            for a in timeline.itertuples():
                at=pd.Timestamp(a.date,tz='UTC').timestamp()
                before=asof(t,p,at-86400,7200);atp=asof(t,p,at,7200);after=asof(t,p,at+86400,7200)
                if np.isfinite([before,atp,after]).all():
                    anchor_rows.append(dict(market_id=r.market_id,event=a.event,date=a.date,pre=atp-before,post=after-atp,
                                            effect=abs(after-atp)-abs(atp-before),resolution='UTC date only'))
    pd.DataFrame(rows).to_parquet(DATA/'other_daily.parquet',index=False)
    pd.DataFrame(scores).to_parquet(DATA/'other_calibration.parquet',index=False)
    pd.DataFrame(anchor_rows).to_parquet(DATA/'belief_anchor_effects.parquet',index=False)
    # Keep source dates sparse: a missing collection day is not a zero-news day.
    gd=pd.read_parquet(local/'gdelt_daily.parquet')
    gd['date']=pd.to_datetime(gd.date).dt.strftime('%Y-%m-%d')
    gd=gd.drop_duplicates('date').set_index('date').sort_index()
    gd=gd.reindex(pd.date_range(gd.index.min(),gd.index.max()).strftime('%Y-%m-%d'))
    gd.index.name='date'
    gd['iran_tone']=gd['IRN.tone_sum']/gd['IRN.events'].replace(0,np.nan)
    gd['tone_change']=gd.iran_tone.diff()
    gd['news_change']=gd['IRN.events'].diff()
    gd[['IRN.events','iran_tone','tone_change','news_change']].reset_index().to_parquet(DATA/'iran_news.parquet',index=False)
    print('other panels',len(rows),'daily prices;',len(scores),'calibration;',len(anchor_rows),'anchor pairs',flush=True)

if __name__=='__main__':
    main()
