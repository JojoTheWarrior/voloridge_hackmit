"""Leakage-aware weather panels from cached histories and station archives; no HTTP."""
from functools import lru_cache

import numpy as np
import pandas as pd

from pmlib import DATA

TRAIN_END='2026-05-31'

@lru_cache(maxsize=64)
def observations(station):
    p=DATA/'station_observations'/f'{station}.parquet'
    return pd.read_parquet(p) if p.exists() else pd.DataFrame()

def history(token):
    p=DATA/'prices'/f'{token}.parquet'
    if not p.exists():return np.array([]),np.array([])
    d=pd.read_parquet(p).drop_duplicates('t').sort_values('t')
    return d.t.to_numpy(dtype=float),d.p.to_numpy(dtype=float)

def asof(t,p,at,max_age):
    i=np.searchsorted(t,at,side='right')-1
    if i<0 or at-t[i]>max_age:return np.nan
    return p[i]

def empirical_prob(values,lo,hi):
    values=np.asarray(values,float);values=values[np.isfinite(values)]
    if len(values)<30:return np.nan
    r=np.floor(values+.5)
    return np.mean((r>=lo)&(r<=hi))

def daily_forecasts(c):
    rows=[]
    for station,g in c[c.station.notna()].groupby('station'):
        p=DATA/'forecasts'/f'{station}.parquet'
        if not p.exists():continue
        x=pd.read_parquet(p);x['local']=pd.to_datetime(x.time,utc=True).dt.tz_convert(g.timezone.iloc[0])
        x['date']=x.local.dt.strftime('%Y-%m-%d');col='temperature_2m_previous_day3'
        if col not in x:continue
        z=x.groupby('date')[col].agg(['min','max','count']).reset_index()
        z=z[z['count']>=23];z['station']=station;rows.append(z)
    return pd.concat(rows,ignore_index=True) if rows else pd.DataFrame(columns=['station','date','min','max','count'])

def main():
    c=pd.read_parquet(DATA/'weather_sample_tokens.parquet')
    daily=pd.read_parquet(DATA/'station_daily.parquet')
    daily=daily[(daily.subset=='all')&daily.complete].copy()
    forecast=daily_forecasts(c);forecast.to_parquet(DATA/'forecast_daily.parquet',index=False)
    lookup={s:g.set_index('date').sort_index() for s,g in daily.groupby('station')}
    flook={s:g.set_index('date') for s,g in forecast.groupby('station')}
    calibration=[];crossings=[];events=[];sample_paths=[]
    for ei,(event,g) in enumerate(c.groupby('event_slug',sort=False)):
        a=g.iloc[0];day=pd.Timestamp(a.date,tz=a.timezone);start=day.timestamp();end=(day+pd.DateOffset(days=1)).timestamp()
        cutoff=(day-pd.DateOffset(days=1)+pd.Timedelta(hours=12)).timestamp()
        noon=(day+pd.Timedelta(hours=12)).timestamp()
        ob=observations(a.station);ob=ob[ob.date==a.date].copy() if not ob.empty else ob
        temps=ob.temperature.to_numpy(float) if not ob.empty else np.array([])
        if a.unit=='F':temps=temps*1.8+32
        rt=np.maximum.accumulate(temps) if a.kind=='highest' else np.minimum.accumulate(temps)
        rounded=np.floor(rt+.5)
        ot=ob.t.to_numpy(float) if not ob.empty else np.array([])
        ds=lookup.get(a.station);fc=flook.get(a.station)
        persist=np.array([]);clim=np.array([]);fvalues=np.array([])
        if ds is not None:
            col='tmax' if a.kind=='highest' else 'tmin'
            prior_date=(pd.Timestamp(a.date)-pd.Timedelta(days=2)).strftime('%Y-%m-%d')
            train_cut=min(prior_date,TRAIN_END)
            past=ds[ds.index<=train_cut][col].copy()
            if a.unit=='F':past=past*1.8+32
            # Two-calendar-day changes, not two adjacent nonmissing observations.
            aligned=past.reindex(pd.date_range(past.index.min(),past.index.max()).strftime('%Y-%m-%d')) if len(past) else past
            changes=aligned-aligned.shift(2)
            if prior_date in ds.index:
                prior=float(ds.loc[prior_date,col]);prior=prior*1.8+32 if a.unit=='F' else prior
                persist=prior+changes.dropna().to_numpy()
            doy=pd.to_datetime(past.index).dayofyear.to_numpy();target=pd.Timestamp(a.date).dayofyear
            dist=np.abs(doy-target);dist=np.minimum(dist,366-dist)
            clim=past.to_numpy()[dist<=30]
            if fc is not None and a.date in fc.index:
                fcol='max' if a.kind=='highest' else 'min'
                matching=past.to_frame('actual').join(fc[[fcol]].rename(columns={fcol:'forecast'}),how='inner')
                if a.unit=='F':matching['forecast']=matching.forecast*1.8+32
                residual=(matching.actual-matching.forecast).dropna().to_numpy()
                pred=float(fc.loc[a.date,fcol]);pred=pred*1.8+32 if a.unit=='F' else pred
                fvalues=pred+residual
        bucket_noon=[];bucket_next=[];night_changes=[];day_changes=[]
        for r in g.itertuples():
            t,p=history(r.yes_token)
            if len(t)==0:continue
            price=asof(t,p,cutoff,7200)
            # Market creation cutoff is independent of terminal outcome.
            created=pd.Timestamp(r.created).timestamp() if pd.notna(r.created) else np.inf
            if np.isfinite(price) and created<=cutoff:
                calibration.append(dict(event_slug=event,market_id=r.market_id,city=r.city,date=r.date,kind=r.kind,
                    station=r.station,bucket=r.bucket,lo=r.lo,hi=r.hi,tail=not(np.isfinite(r.lo)&np.isfinite(r.hi)),
                    p=price,y=float(r.yes_final>=.99),persistence=empirical_prob(persist,r.lo,r.hi),
                    climatology=empirical_prob(clim,r.lo,r.hi),forecast=empirical_prob(fvalues,r.lo,r.hi),
                    cutoff_t=cutoff,source_family=r.source_family,volume=r.volume))
            bucket_noon.append(asof(t,p,noon,900));bucket_next.append(asof(t,p,noon+3600,900))
            hours=np.arange(start,end+1,3600)
            prices=np.array([asof(t,p,h,900) for h in hours]);dp=np.abs(np.diff(prices))
            local_hours=pd.to_datetime(hours[:-1],unit='s',utc=True).tz_convert(a.timezone).hour
            night_changes.extend(dp[(local_hours>=0)&(local_hours<6)])
            day_changes.extend(dp[(local_hours>=12)&(local_hours<18)])
            # Only finite losing-side bounds are eliminable before midnight.
            mask=(rounded>r.hi) if a.kind=='highest' else (rounded<r.lo)
            if len(ot) and np.any(mask):
                crossing=float(ot[np.flatnonzero(mask)[0]]);available=crossing+1800
                p0=asof(t,p,available,900);p1=asof(t,p,available+3600,900)
                if available+3600>end:continue
                post=(t>=available)&(t<=end)&(p<=.03)
                delay=0. if np.isfinite(p0) and p0<=.03 else ((t[post][0]-available)/60 if np.any(post) else np.nan)
                crossings.append(dict(event_slug=event,market_id=r.market_id,token=r.yes_token,date=r.date,city=r.city,kind=r.kind,
                     bucket=r.bucket,station=r.station,observed_t=crossing,available_t=available,p0=p0,p60=p1,
                     effect=p1-p0,delay_minutes=delay,right_censored=not np.isfinite(delay),
                     resolved_yes=bool(r.yes_final>=.99),source_family=r.source_family,
                     coverage_hours=ob.hour.nunique(),threshold=(r.hi if a.kind=='highest' else r.lo)))
            # A few deterministic paths for demo; not selected by significance.
            if a.city in ['london','nyc','seoul','shanghai'] and a.date in ['2026-06-15','2026-07-15','2026-08-15','2026-09-15']:
                select=(t>=start)&(t<=end)
                sample_paths.extend(dict(event_slug=event,city=r.city,date=r.date,bucket=r.bucket,t=tt,p=pp) for tt,pp in zip(t[select],p[select]))
        sums_ok=len(bucket_noon)==len(g) and np.isfinite(bucket_noon).all() and np.isfinite(bucket_next).all()
        night=np.array(night_changes);dday=np.array(day_changes)
        events.append(dict(event_slug=event,date=a.date,city=a.city,kind=a.kind,n_buckets=len(g),
            sum_noon=float(np.sum(bucket_noon)) if sums_ok else np.nan,
            sum_13=float(np.sum(bucket_next)) if sums_ok else np.nan,
            night_abs=float(np.nanmean(night)) if np.isfinite(night).any() else np.nan,
            day_abs=float(np.nanmean(dday)) if np.isfinite(dday).any() else np.nan))
        if ei%250==0:print('weather panel',ei,flush=True)
    pd.DataFrame(calibration).to_parquet(DATA/'weather_calibration.parquet',index=False)
    pd.DataFrame(crossings).to_parquet(DATA/'weather_crossings.parquet',index=False)
    pd.DataFrame(events).to_parquet(DATA/'weather_event_metrics.parquet',index=False)
    pd.DataFrame(sample_paths).to_parquet(DATA/'weather_case_paths.parquet',index=False)
    print('panels',len(calibration),len(crossings),len(events),flush=True)

if __name__=='__main__':
    main()
