"""Normalize official station-year archives and audit local-day settlement agreement."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from pmlib import DATA

COLS=['DATE','temperature','temperature_Quality_Code','temperature_Report_Type',
      'temperature_Source_Station_ID','wind_speed','sea_level_pressure']

def normalize():
    cat=pd.read_parquet(DATA/'catalog_enriched.parquet')
    sl=pd.read_csv(DATA/'ghcnh/ghcnh-station-list.csv',dtype=str)
    rows=[];daily=[];out=DATA/'station_observations';out.mkdir(exist_ok=True)
    for station,g in cat[cat.station.notna()].groupby('station'):
        st=sl[sl.ICAO==station]
        if st.empty:
            rows.append(dict(station=station,status='ICAO absent from official station list',observations=0));continue
        frames=[]
        for sid in st.GHCN_ID:
            for year in (2025,2026):
                base=DATA/'ghcnh'/f'GHCNh_{sid}_{year}'
                if base.with_suffix('.psv').exists():
                    x=pd.read_csv(base.with_suffix('.psv'),sep='|',usecols=COLS,dtype={'temperature_Quality_Code':str},low_memory=False)
                elif base.with_suffix('.parquet').exists():
                    x=pd.read_parquet(base.with_suffix('.parquet'),columns=COLS)
                else:continue
                frames.append(x)
        if not frames:
            rows.append(dict(station=station,status='no archive downloaded',observations=0));continue
        x=pd.concat(frames,ignore_index=True)
        n_raw=len(x)
        qc=x.temperature_Quality_Code.fillna('').astype(str).str.strip()
        temp=pd.to_numeric(x.temperature,errors='coerce')
        x=x[qc.isin(['','0','1','4','5','9']) & temp.between(-80,65)].copy()
        x['temperature']=pd.to_numeric(x.temperature)
        x['t']=pd.to_datetime(x.DATE,utc=True).dt.as_unit('s').astype('int64')
        assert x.t.between(1700000000,1900000000).all(), 'Unexpected archive timestamp scale'
        x=x.sort_values('t').drop_duplicates('t',keep='first')
        tz=g.timezone.iloc[0]
        local=pd.to_datetime(x.t,unit='s',utc=True).dt.tz_convert(tz)
        x['date']=local.dt.strftime('%Y-%m-%d');x['hour']=local.dt.hour
        x['metar']=x.temperature_Report_Type.isin(['FM15','FM16'])
        x[['t','date','hour','temperature','metar','wind_speed','sea_level_pressure']].to_parquet(out/f'{station}.parquet',index=False)
        for label,z in [('all',x),('metar',x[x.metar])]:
            d=z.groupby('date').agg(tmax=('temperature','max'),tmin=('temperature','min'),n=('t','size'),hours=('hour','nunique'),first_hour=('hour','min'),last_hour=('hour','max')).reset_index()
            d['complete']=(d.hours>=18)&(d.first_hour<=2)&(d.last_hour>=21)
            d['station']=station;d['subset']=label;daily.append(d)
        rows.append(dict(station=station,status='available',raw_rows=n_raw,observations=len(x),first_date=x.date.min(),last_date=x.date.max(),timezone=tz))
    pd.DataFrame(rows).to_csv(DATA/'station_coverage.csv',index=False)
    pd.concat(daily,ignore_index=True).to_parquet(DATA/'station_daily.parquet',index=False)

def audit():
    c=pd.read_parquet(DATA/'catalog_enriched.parquet')
    daily=pd.read_parquet(DATA/'station_daily.parquet')
    all_d=daily[daily.subset=='all'].set_index(['station','date'])
    met_d=daily[daily.subset=='metar'].set_index(['station','date'])
    rows=[]
    for event,g in c.groupby('event_slug',sort=False):
        a=g.iloc[0]
        base=dict(event_slug=event,date=a.date,city=a.city,kind=a.kind,station=a.station,unit=a.unit,
                  source_family=a.source_family,source_domain=a.source_domain,n_buckets=len(g),volume=g.volume.sum())
        if a.date>'2026-09-18' or not g.closed.all() or not ((g.yes_final<=.01)|(g.yes_final>=.99)).all() or (g.yes_final>=.99).sum()!=1:
            base['status']='unresolved_or_invalid_partition';rows.append(base);continue
        winner=g[g.yes_final>=.99].iloc[0]
        base.update(winner_lo=winner.lo,winner_hi=winner.hi,winner_bucket=winner.bucket)
        if (a.station,a.date) not in all_d.index:
            base['status']='no_station_day';rows.append(base);continue
        d=all_d.loc[(a.station,a.date)]
        base.update(hours=int(d.hours),complete=bool(d.complete))
        if not d.complete:
            base['status']='incomplete_day';rows.append(base);continue
        raw=float(d.tmax if a.kind=='highest' else d.tmin)
        raw=raw*1.8+32 if a.unit=='F' else raw
        rounded=float(np.floor(raw+.5))
        base.update(status='audited',raw_extreme=raw,rounded_extreme=rounded,
                    mismatch_raw=not(winner.lo<=raw<=winner.hi),mismatch_round=not(winner.lo<=rounded<=winner.hi))
        base['outside_distance']=max(float(winner.lo-raw),float(raw-winner.hi),0)
        if (a.station,a.date) in met_d.index:
            md=met_d.loc[(a.station,a.date)]
            if md.complete:
                mr=float(md.tmax if a.kind=='highest' else md.tmin)
                mr=mr*1.8+32 if a.unit=='F' else mr
                base.update(metar_extreme=mr,mismatch_metar=not(winner.lo<=np.floor(mr+.5)<=winner.hi))
        rows.append(base)
    df=pd.DataFrame(rows);df.to_parquet(DATA/'settlement_audit.parquet',index=False)
    print('station audit',df.status.value_counts().to_dict(),flush=True)

if __name__=='__main__':
    normalize();audit()
