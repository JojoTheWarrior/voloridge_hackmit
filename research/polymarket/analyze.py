"""Execute the frozen family on cached, point-in-time panels; no network calls."""
import hashlib
import json

import numpy as np
import pandas as pd

from pmlib import DATA, ROOT
from statistics import bh, paired, correlations

def main():
    digest=hashlib.sha256((ROOT/'prereg.json').read_bytes()).hexdigest()
    assert digest==(ROOT/'prereg.sha256').read_text().split()[0]
    prereg=json.loads((ROOT/'prereg.json').read_text())
    rows={t['id']:dict(test_id=t['id'],mission=t['mission'],title=t['title'],expected_sign=t['expected_sign'],
             family_size=prereg['family_size'],status='blocked',n=0,n_dates=0,p=1.,effect=np.nan,
             lo=np.nan,hi=np.nan,mde=np.nan,mde_family=np.nan,placebo_p=np.nan,prereg_sha256=digest,note='') for t in prereg['tests']}
    def run(t,df,note):
        early=df[df.date<'2026-06-01'];late=df[(df.date>='2026-06-01')&(df.date<='2026-09-18')]
        rows[t].update(paired(late));rows[t].update(n_train=len(early),train_effect=early.effect.mean(),note=note)
    audit=pd.read_parquet(DATA/'settlement_audit.parquet');audit=audit[audit.status=='audited'].copy()
    audit['effect']=audit.mismatch_round.astype(float)-audit.mismatch_raw.astype(float)
    run('A8',audit,'Source-agreement diagnostic; lower error after rounding is not a price edge. All available matched station events, not just price sample.')
    z=audit.dropna(subset=['mismatch_metar']).copy();z['effect']=z.mismatch_metar.astype(float)-z.mismatch_round.astype(float)
    run('A9',z,'Both observation subsets must have >=18 local hours. Signed effect below zero supports METAR-only advantage; mismatch remains a source-proxy comparison.')
    cal=pd.read_parquet(DATA/'weather_calibration.parquet')
    cross=pd.read_parquet(DATA/'weather_crossings.parquet')
    ev=pd.read_parquet(DATA/'weather_event_metrics.parquet')
    # Every bucket belongs to one event; give each event equal weight within dates.
    z=cross.groupby(['event_slug','date']).effect.mean().reset_index()
    run('A1',z,'YES price 60m minus price at station crossing+30m; no conditioning on final winner or initial nonzero price. Reconstructed observation availability; not executable latency.')
    for tid,col in [('A2','persistence'),('A3','climatology'),('A4','forecast')]:
        z=cal.dropna(subset=['p',col]).copy()
        z['effect']=(z.p-z.y)**2-(z[col]-z.y)**2
        if tid=='A4':z['effect']=-z.effect
        z=z.groupby(['event_slug','date']).effect.mean().reset_index()
        run(tid,z,'Equal-event mean binary Brier difference; paired complete cases. Empirical baseline distributions use early-period data only; persistence observes d-2, forecast uses previous_day3 GFS.')
    z=cal.assign(residual=cal.y-cal.p).groupby(['event_slug','date','tail']).residual.mean().unstack('tail')
    if True in z and False in z:
        z['effect']=z[True]-z[False];run('A5',z.reset_index(),'Within-event open-tail minus finite-bucket outcome-price residual; no level correlation.')
    ev['effect']=(ev.sum_13-1).abs()-(ev.sum_noon-1).abs()
    run('A6',ev,'All bucket histories required within 15m; sums use asynchronous last sampled prices, not simultaneous executable quotes. No arbitrage claim.')
    ev['effect']=ev.night_abs-ev.day_abs
    run('A7',ev,'Night 00-06 minus day 12-18 mean absolute hourly change, IANA local time. Information timing confounds activity interpretation.')
    anchors=pd.read_parquet(DATA/'belief_anchor_effects.parquet')
    if not anchors.empty:
        dates=sorted(anchors.date.unique());cut=dates[int(.6*len(dates))]
        z=anchors.groupby(['event','date']).effect.mean().reset_index();late=z[z.date>=cut]
        rows['B1'].update(paired(late));rows['B1'].update(n_train=len(z[z.date<cut]),note='Iran date-only anchors; UTC 24h before/after, no minute lead inference. Other event types have no verified precise anchor panel in this run.')
    news=pd.read_parquet(DATA/'iran_news.parquet').set_index('date')
    other=pd.read_parquet(DATA/'other_daily.parquet')
    iran=other[other.category=='iran'].groupby('date').return_.mean()
    joined=news.join(iran.rename('y'))
    # News day d is complete at start of d+1; y on day d+lag+1 ends at
    # start of the following day. lag 1 therefore follows information availability.
    for tid,col,lags in [('B2','news_change',[1,2,3]),('D1','tone_change',[1])]:
        z=joined[[col,'y']].rename(columns={col:'x'})
        z['y']=z.y.shift(-1)  # Daily news must be complete before the return starts.
        rows[tid].update(correlations(z,lags));rows[tid]['note']='Daily Iran topic changes; sparse source days remain missing. First 60% dates select lag; last 40% score, 7-day block max-stat permutation. Broad YES questions differ in direction; no causal interpretation.'
    for tid,note in {
        'C1':'Public Deribit current option summaries accessible, but no synchronized historical same-strike/same-expiry digital panel acquired. Current snapshot is exploratory only; option settlement and Polymarket definitions differ.',
        'C2':'Kalshi public market data accessible. Exact payoff, resolution source and timestamp matching required; current NYC weather uses a different thermometer, so it is not an identical contract. No historical matched panel.',
        'C3':'CME FedWatch public page probed; no keyless historical futures-implied decision probability series reconstructed. Current pages cannot be backfilled into historical signals.',
        'D2':'Cached GDELT file has country and Gulf-topic aggregates, no crypto tone series. No substitute topic was tested.',
        'D3':'Cached GDELT file has no election-specific tone series. Country-wide tone is not an election-tone substitute.',
        'F1':'Existing flare_daily series uses full-history persistent-hotspot selection; no certified point-in-time hotspot universe or historical publication-vintage series. Excluded from primary test to prevent look-ahead.',
        'F2':'Only two actual weather-hurricane contracts after excluding the Carolina Hurricanes hockey false positive; no validated named-storm/station/landfall alignment with historical wind observations. No arbitrary nearest station substitution.',
        'F3':'No publication-vintage running global temperature anomaly series; final monthly revisions cannot stand in for an available-at-the-time signal.',
    }.items():rows[tid]['note']=note
    fp=DATA/'flare_point_in_time.parquet'
    if fp.exists():
        physical=pd.read_parquet(fp).set_index('date')
        screened=pd.read_parquet(DATA/'other_markets_screened.parquet')
        ids=screened.loc[(screened.category=='iran')&screened.question.str.contains('reopen|ceasefire|normal|transit',case=False,regex=True),'market_id']
        target=other[other.market_id.isin(ids)].groupby('date').return_.mean()
        z=physical[['change']].rename(columns={'change':'x'}).join(target.rename('y'))
        # x_d available at d+3 00:00 after full day d plus 48h delay.
        # y's date is its ending midnight: shift 3 then registered lag >=1.
        z['y']=z.y.shift(-3)
        rows['F1'].update(correlations(z,[1,2,3]));rows['F1']['note']='553 persistent Gulf cells fixed using 2025 only, avoiding sibling full-history selection. log1p FRP changes delayed 48h after completed observation day; next 1/2/3-day returns. No historical dissemination timestamps; archive revisions and clouds limit interpretation. Only screened Iran/Hormuz reopening/ceasefire/transit questions.'
    # E uses the fixed 24h-before-scheduled-end scores across general categories.
    # Weather day-ahead noon is a different horizon and is deliberately not substituted.
    oc=pd.read_parquet(DATA/'other_calibration.parquet')
    rows['E1']['note']='General panel supplies politics but weather noon-day-ahead panel has a different cutoff. E1 requires scheduled-end minus 24h; computed separately when weather endpoint metadata are available.'
    # Weather endDate from frozen Gamma weather records is mapped by market ID in E panel.
    ep=DATA/'baseline_calibration.parquet'
    if ep.exists():
        e=pd.read_parquet(ep);e['brier']=(e.p-e.y)**2;e['residual']=e.y-e.p
        z=e[e.category.isin(['weather','politics'])].groupby(['date','category']).brier.mean().unstack()
        if 'weather' in z and 'politics' in z:
            z['effect']=z.weather-z.politics;z=z.reset_index().dropna(subset=['effect'])
            dates=sorted(z.date.unique());split=int(.6*len(dates))
            if dates:
                rows['E1'].update(paired(z[z.date>=dates[split]]));rows['E1']['note']='Matched calendar dates, mean weather minus politics Brier at scheduled-end minus 24h. Different outcome difficulty and event composition preclude causal category claims.'
        tail=e[e.p<=.1].groupby('date').residual.mean();fav=e[e.p>=.9].groupby('date').residual.mean()
        z=(tail-fav).rename('effect').reset_index().dropna()
        dates=sorted(z.date.unique());split=int(.6*len(dates))
        if dates:
            rows['E2'].update(paired(z[z.date>=dates[split]]));rows['E2']['note']='Longshot (<=.10) minus favourite (>=.90) calibration residual on same dates, fixed 24h horizon; category and terminal-volume strata descriptive.'
    else:rows['E2']['note']='Baseline scheduled-end panel not built.'
    res=pd.DataFrame(rows.values());res['q']=bh(res.p.to_numpy())
    res['survives_bh']=(res.q<=.05)&(res.status=='tested')
    res['expected_sign_met']=(res.expected_sign==0)|(np.sign(res.effect)==res.expected_sign)
    res['supported']=res.survives_bh&res.expected_sign_met
    res['verdict']=np.where(res.supported,'supported',np.where(res.status.isin(['blocked','insufficient']),'partial','rejected'))
    res.to_csv(ROOT/'results.csv',index=False)
    placebo=res[res.placebo_p.notna()][['test_id','placebo_p']].copy();placebo['false_positive']=placebo.placebo_p<.05
    placebo.to_csv(ROOT/'placebo_results.csv',index=False)
    print(res[['test_id','status','n','n_dates','effect','p','q','supported']].to_string(index=False))

if __name__=='__main__':
    main()
