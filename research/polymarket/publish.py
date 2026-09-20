"""Render demo PNGs, schema-compatible findings, and an auditable research report."""
import hashlib
import json
import os
from datetime import datetime, timezone

from pmlib import DATA, ROOT

os.environ.setdefault('MPLCONFIGDIR',str(DATA/'mpl-cache'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from weather_panel import history, observations

FIG=ROOT/'figures';FIG.mkdir(exist_ok=True)
BLUE='#2563eb';TEAL='#0f766e';RED='#c2410c';GRAY='#64748b';BG='#f8fafc'
plt.rcParams.update({'figure.facecolor':BG,'axes.facecolor':BG,'axes.spines.top':False,'axes.spines.right':False,
 'font.family':'DejaVu Sans','font.size':10,'axes.titlesize':12,'axes.titleweight':'bold','axes.labelcolor':'#334155',
 'text.color':'#0f172a','axes.grid':True,'grid.alpha':.16,'savefig.facecolor':BG})

def save(fig,name):
    fig.savefig(FIG/name,dpi=175,bbox_inches='tight');plt.close(fig)

def mdtable(df):
    def val(x):
        if pd.isna(x):return '—'
        if isinstance(x,(float,np.floating)):return f'{x:.5g}'
        return str(x).replace('|','/').replace('\n',' ')
    return '| '+' | '.join(df.columns)+' |\n| '+' | '.join(['---']*len(df.columns))+' |\n'+'\n'.join('| '+' | '.join(val(x) for x in row)+' |' for row in df.itertuples(index=False,name=None))

def figures(res,audit,cal,cross,ev):
    late=cal[cal.date>='2026-06-01']
    fig,axs=plt.subplots(1,2,figsize=(13,5),gridspec_kw={'width_ratios':[1.3,1]})
    a=audit[audit.status=='audited'];summary=a.groupby('city').agg(n=('date','size'),mismatch=('mismatch_round','mean')).sort_values('n',ascending=False).head(16).sort_values('mismatch')
    axs[0].barh(summary.index,summary.mismatch*100,color=BLUE)
    for i,r in enumerate(summary.itertuples()):axs[0].text(r.mismatch*100+.2,i,f'n={r.n:,}',va='center',fontsize=8)
    axs[0].set_xlabel('Rounded station extreme disagrees with settlement (%)');axs[0].set_title('A thermometer is not the settlement oracle')
    g=a.groupby(['source_family','kind']).agg(n=('date','size'),rate=('mismatch_round','mean')).reset_index()
    labels=g.source_family+' / '+g.kind
    axs[1].barh(labels,g.rate*100,color=[BLUE if x=='WU' else TEAL for x in g.source_family])
    for i,r in enumerate(g.itertuples()):axs[1].text(r.rate*100+.05,i,f'{r.rate:.1%} · n={r.n:,}',va='center',fontsize=9)
    axs[1].set_xlim(0,max(g.rate)*100+3);axs[1].set_xlabel('Disagreement (%)');axs[1].set_title('Source and max/min matter')
    fig.suptitle(f'{len(a):,} settled weather events matched to complete station-days',fontsize=16,fontweight='bold',y=1.03)
    fig.text(.01,-.035,'Descriptive, all periods. Final NOAA archive versus final settlement; neither is treated as live executable information.',fontsize=9,color=GRAY)
    fig.tight_layout();save(fig,'fig1_settlement_audit.png')

    fig,axs=plt.subplots(1,3,figsize=(15,4.6))
    for ax,(group,label) in zip(axs,[(late,'All held-out buckets'),(late[late['tail']],'Open-ended tails'),(late[~late['tail']],'Finite buckets')]):
        ax.plot([0,1],[0,1],ls='--',color=GRAY,lw=1)
        for col,name,color in [('p','Market',BLUE),('persistence','Persistence (d−2)',RED),('forecast','GFS, 72-hour lead',TEAL)]:
            z=group.dropna(subset=[col]).copy();z['bin']=pd.cut(z[col],np.linspace(0,1,11),include_lowest=True)
            b=z.groupby('bin',observed=True).agg(pred=(col,'mean'),actual=('y','mean'),n=('y','size'));b=b[b.n>=20]
            ax.plot(b.pred,b.actual,'o-',color=color,label=name,ms=5)
        ax.set(xlim=(-.02,1.02),ylim=(-.02,1.02),xlabel='Forecast probability',ylabel='Observed frequency',title=label)
        ax.legend(fontsize=8,loc='upper left')
    fig.suptitle(f'Weather calibration • June–September holdout • {late.event_slug.nunique():,} events',fontsize=16,fontweight='bold',y=1.04)
    fig.text(.01,-.025,'Descriptive reliability; bins with <20 rows omitted. Curves can use different complete-case samples; paired tests use common rows.',fontsize=9,color=GRAY)
    fig.tight_layout();save(fig,'fig2_weather_calibration.png')

    fig,axs=plt.subplots(1,2,figsize=(13,5))
    lc=cross[cross.date>='2026-06-01'].copy()
    # Only display events with an observed starting price; otherwise missing != delay.
    valid=lc[lc.p0.notna()].copy()
    cs=valid.groupby('city').agg(n=('delay_minutes','size'),median=('delay_minutes','median'),censor=('right_censored','mean')).sort_values('n',ascending=False).head(12)
    for i,(city,z) in enumerate(valid[valid.city.isin(cs.index)].groupby('city')):
        vals=np.minimum(z.delay_minutes.dropna().to_numpy(),360)
        if len(vals):axs[0].scatter(vals,np.full(len(vals),i),s=9,alpha=.25,color=BLUE)
    cities=sorted(cs.index);axs[0].set_yticks(range(len(cities)),cities);axs[0].set_xlabel('Minutes to sampled YES ≤ 3¢ after assumed availability\nAlready ≤3¢ at availability is coded 0; display capped at 360m')
    axs[0].set_title('Price convergence is often already complete')
    near=valid[np.isfinite(valid.p0)&np.isfinite(valid.p60)]
    axs[1].scatter(near.p0*100,(near.p60-near.p0)*100,s=9,alpha=.15,c=near.resolved_yes.map({True:RED,False:BLUE}))
    axs[1].axhline(0,color=GRAY,lw=1);axs[1].set(xlabel='YES price at availability (¢)',ylabel='Next-hour price change (¢)',title='A price decline is not a fillable edge')
    fig.suptitle('Finite buckets eliminated by running station extremes',fontsize=16,fontweight='bold',y=1.03)
    fig.text(.01,-.035,f'{len(valid):,} holdout crossings with initial price; {valid.right_censored.mean():.1%} no observed convergence by day end. Red: bucket nevertheless settled YES. 30m assumed data delay.',fontsize=9,color=GRAY)
    fig.tight_layout();save(fig,'fig3_convergence_distribution.png')

    cat=pd.read_parquet(DATA/'weather_sample_tokens.parquet')
    choices=[]
    for city in ['london','nyc','seoul']:
        z=cross[(cross.city==city)&(cross.date>='2026-06-01')&(cross.date<='2026-09-16')]
        if not z.empty:choices.append(z.sort_values(['date','event_slug']).iloc[-1].event_slug)
    if not choices:choices=cross.event_slug.drop_duplicates().head(3).tolist()
    fig,axs=plt.subplots(2,len(choices),figsize=(5*len(choices),7),squeeze=False)
    for i,event in enumerate(choices):
        g=cat[cat.event_slug==event];a0=g.iloc[0];ob=observations(a0.station);ob=ob[ob.date==a0.date]
        temp=ob.temperature.to_numpy();temp=temp*1.8+32 if a0.unit=='F' else temp
        run=np.maximum.accumulate(temp) if a0.kind=='highest' else np.minimum.accumulate(temp)
        zero=pd.Timestamp(a0.date,tz=a0.timezone).timestamp();x=(ob.t-zero)/3600
        axs[0,i].plot(x,temp,color=GRAY,alpha=.5,label='Observed temperature');axs[0,i].plot(x,run,color=RED,lw=2,label='Running extreme')
        axs[0,i].set_title(f'{a0.city.title()} · {a0.date}\n{a0.kind} · {a0.station}');axs[0,i].set_ylabel('Temperature (°'+a0.unit+')');axs[0,i].legend(fontsize=8)
        for r in g.itertuples():
            t,p=history(r.yes_token);mask=(t>=zero)&(t<zero+86400)
            axs[1,i].plot((t[mask]-zero)/3600,p[mask],lw=1.2,label=r.bucket)
        axs[1,i].set(xlabel='Hours since local midnight',ylabel='Sampled YES price',ylim=(-.02,1.02),xlim=(0,24))
        axs[1,i].legend(fontsize=6,ncol=2,loc='upper left')
    fig.suptitle('A weather observation clock and a market-price clock',fontsize=17,fontweight='bold',y=1.02)
    fig.text(.01,-.02,'Deterministic latest eligible sampled case per city, not selected for large effects. Raw archive observation time is not verified publication time.',fontsize=9,color=GRAY)
    fig.tight_layout();save(fig,'fig4_intraday_cases.png')

    # B: a genuine common timeline; satellite marks are observations, not news timestamps.
    other=pd.read_parquet(DATA/'other_daily.parquet');meta=pd.read_parquet(DATA/'other_markets_screened.parquet')
    iran=other[(other.category=='iran')&(other.date>='2026-02-15')&(other.date<='2026-04-20')]
    fig,axs=plt.subplots(3,1,figsize=(13,8),sharex=True)
    ids=iran.groupby('market_id').p.count().sort_values(ascending=False).head(3).index
    for mid in ids:
        z=iran[iran.market_id==mid];label=meta.loc[meta.market_id==mid,'question'].iloc[0]
        axs[0].plot(pd.to_datetime(z.date),z.p,label=label[:85],lw=1.7)
    axs[0].set_ylabel('YES probability');axs[0].legend(fontsize=7,loc='upper left');axs[0].set_title('Daily market prices; exact questions differ')
    news=pd.read_parquet(DATA/'iran_news.parquet');news=news[(news.date>='2026-02-15')&(news.date<='2026-04-20')]
    axs[1].bar(pd.to_datetime(news.date),news['IRN.events'],color=TEAL,width=.8);axs[1].set_ylabel('Iran GDELT events');axs[1].set_title('News count, with missing collection days left missing')
    sat=pd.read_csv(DATA/'context/satellite_scoreboard.csv');sat=sat[sat.war.astype(str)=='2026']
    points=[]
    for r in sat.itertuples():
        a=pd.to_datetime(r.first_news_utc,utc=True,errors='coerce');b=pd.to_datetime(r.first_det_utc,utc=True,errors='coerce')
        if pd.notna(a) and pd.notna(b) and a.month in [2,3,4] and b.month in [2,3,4]:points.append((r.event_id,a,b))
    for i,(label,a,b) in enumerate(points[:12]):
        axs[2].plot([a,b],[i,i],color=GRAY,lw=1);axs[2].scatter(a,i,color=BLUE,s=25);axs[2].scatter(b,i,color=RED,s=30,marker='^')
    axs[2].set_yticks(range(len(points[:12])),[x[0] for x in points[:12]]);axs[2].set_title('Blue: earliest collected news evidence · orange: satellite detection')
    axs[2].set_xlim(pd.Timestamp('2026-02-15'),pd.Timestamp('2026-04-20'))
    for ax in axs:ax.axvline(pd.Timestamp('2026-02-28'),ls='--',color=GRAY,alpha=.8)
    fig.suptitle('Belief clocks • price, news and physical detection',fontsize=17,fontweight='bold',y=1.02)
    fig.text(.01,-.02,'Case study only. GDELT ingest batches bound publication times; they do not identify the first reporter. Missing satellite hits and historical wallet ledgers remain explicit gaps.',fontsize=9,color=GRAY)
    fig.autofmt_xdate();fig.tight_layout();save(fig,'fig5_belief_clock.png')

    quotes=pd.read_parquet(DATA/'cross_venue_snapshot.parquet');options=pd.read_parquet(DATA/'options_snapshot.parquet')
    fig,ax=plt.subplots(figsize=(11,5.5));p=quotes[quotes.venue=='Polymarket'].sort_values('strike')
    ax.plot(p.strike,(p.bid+p.ask)/2,'o-',color=BLUE,label='Polymarket · Sep 20 16:00 UTC · Binance');ax.fill_between(p.strike,p.bid,p.ask,color=BLUE,alpha=.15)
    for expiry,g in options[options.valid].groupby('expiry'):
        if expiry.startswith(('2026-09-20','2026-09-21')):
            ax.plot(g.strike,g.probability,'s--',ms=4,alpha=.8,label='Deribit call-spread proxy · '+expiry[:16])
    ax.set(xlim=(72000,88000),ylim=(-.03,1.03),xlabel='BTC threshold (USD; exchange reference differs)',ylabel='Probability / risk-neutral proxy',title='Similar-looking curves are different contracts')
    ax.legend(fontsize=9);fig.text(.01,-.03,'EXPLORATORY SNAPSHOT. Different maturity, index, and averaging rules; not a historical efficiency test. Kalshi noon contracts were initialized/unopened, so zero fields are omitted.',fontsize=9,color=GRAY)
    fig.tight_layout();save(fig,'fig6_cross_venue.png')

    fig,ax=plt.subplots(figsize=(13,7));colors=[TEAL if r.supported else (RED if r.survives_bh else GRAY) for r in res.itertuples()]
    y=np.arange(len(res));x=-np.log10(np.maximum(res.q,1e-5))
    ax.barh(y,x,color=colors);ax.set_yticks(y,[r.test_id+'  '+r.title[:56] for r in res.itertuples()],fontsize=8);ax.invert_yaxis()
    ax.axvline(-np.log10(.05),ls='--',color=RED,label='BH q = 0.05')
    for i,r in enumerate(res.itertuples()):
        if r.status!='tested':ax.text(.03,i,r.status,va='center',fontsize=8,color=GRAY)
    ax.set_xlabel('−log10(BH-adjusted q)');ax.set_title(f'Entire registered family: {len(res)} tests · {res.survives_bh.sum()} BH survivors · {res.supported.sum()} in expected direction')
    ax.legend(loc='lower right');fig.text(.01,-.02,'Blocked/insufficient tests retain p=1 in the family. Green: supported direction; orange: significant opposite direction. Diagnostic findings are not trading edges.',fontsize=9,color=GRAY)
    fig.tight_layout();save(fig,'fig7_family_overview.png')

    fig,axs=plt.subplots(1,2,figsize=(12,4.7))
    metrics=[]
    for tid,label,sign in [('A2','Persistence',-1),('A3','Seasonal history',-1),('A4','Archived GFS',1)]:
        r=res.set_index('test_id').loc[tid];vals=sorted([sign*r.lo,sign*r.hi]);metrics.append((label,sign*r.effect,vals[0],vals[1]))
    for i,(label,e,lo,hi) in enumerate(metrics):
        axs[0].errorbar(e,i,xerr=[[max(0,e-lo)],[max(0,hi-e)]],fmt='o',color=BLUE,capsize=4)
    axs[0].set_yticks(range(len(metrics)),[r[0] for r in metrics]);axs[0].axvline(0,color=GRAY,ls='--');axs[0].set_xlabel('Baseline Brier − market Brier (positive favours market)');axs[0].set_title('Held-out paired forecast loss')
    e=ev[(ev.date>='2026-06-01')&ev.sum_noon.notna()]
    axs[1].hist((e.sum_noon-1)*100,bins=40,color=TEAL,alpha=.9);axs[1].axvline(0,color=GRAY,ls='--');axs[1].set(xlabel='Noon sum of sampled bucket prices − $1 (¢)',ylabel='Events',title='A quote-sum discrepancy is not arbitrage')
    fig.text(.01,-.03,'Left: 10,000 date-cluster bootstrap 95% intervals, paired sample varies by baseline. Right: asynchronous histories, no historical depth or fee reconstruction.',fontsize=9,color=GRAY)
    fig.tight_layout();save(fig,'fig8_forecast_and_bucket_sums.png')

    fig,axs=plt.subplots(2,2,figsize=(13,10))
    def reliability(ax,frame,col,label):
        z=frame.dropna(subset=['p','y']).copy();z['bin']=pd.cut(z.p,np.linspace(0,1,11),include_lowest=True)
        for name,g in z.groupby(col):
            b=g.groupby('bin',observed=True).agg(p=('p','mean'),y=('y','mean'),n=('y','size'));b=b[b.n>=15]
            if len(b):ax.plot(b.p,b.y,'o-',ms=4,label=str(name)+f' (n={len(g):,})')
        ax.plot([0,1],[0,1],ls='--',color=GRAY,lw=1);ax.set(xlabel='Sampled market probability',ylabel='Observed frequency',title=label,xlim=(0,1),ylim=(0,1));ax.legend(fontsize=8)
    cities=late.city.value_counts().head(4).index
    reliability(axs[0,0],late[late.city.isin(cities)],'city','Weather: four largest held-out city samples')
    z=late.copy();month=pd.to_datetime(z.date).dt.month
    southern=z.city.isin(['buenos-aires','sao-paulo','wellington','cape-town'])
    z['season']=np.select([southern&(month<=8),southern&(month>=9),~southern&(month<=8)],['Southern winter','Southern spring','Northern summer'],default='Northern autumn')
    reliability(axs[0,1],z,'season','Weather: meteorological season labels')
    base=pd.read_parquet(DATA/'baseline_horizon_descriptive.parquet');base=base[base.date>='2026-06-01']
    reliability(axs[1,0],base[(base.hours==24)&base.category.isin(['weather','politics','crypto','fed'])],'category','Same 24-hour horizon, different categories')
    axs[1,0].text(.04,.78,'Other categories have too few\nheld-out rows per bin to display.',transform=axs[1,0].transAxes,fontsize=9,color=GRAY)
    w=base[base.category=='weather'].copy();w['horizon']=w.hours.map({168:'7 days',24:'24 hours',6:'6 hours',1:'1 hour'})
    reliability(axs[1,1],w,'horizon','EXPLORATORY: scheduled-end horizon slices')
    fig.suptitle('Calibration slices • descriptive, no additional hypothesis tests',fontsize=17,fontweight='bold',y=1.02)
    fig.text(.01,-.02,'Bins below n=15 omitted; samples change by horizon/category. Seasonal labels are geographic shorthand, not fitted climate regimes. No reliable historical liquidity strata were available.',fontsize=9,color=GRAY)
    fig.tight_layout();save(fig,'fig9_calibration_slices.png')

def findings(res,prereg):
    datasets=[dict(name='Polymarket cached Gamma catalogue and CLOB histories',url='https://docs.polymarket.com/api-reference/markets/get-prices-history',access='Keyless public; cached original responses and normalized Parquet'),
              dict(name='NOAA GHCNh station archives',url='https://www.ncei.noaa.gov/products/land-based-station/integrated-surface-database',access='Keyless official station-year PSV/Parquet'),
              dict(name='Open-Meteo previous model runs',url='https://open-meteo.com/en/docs/previous-runs-api',access='Keyless GFS previous_day3, cached')]
    figures_map={'A':['fig1_settlement_audit.png','fig2_weather_calibration.png','fig3_convergence_distribution.png','fig4_intraday_cases.png','fig8_forecast_and_bucket_sums.png'],
                 'B':['fig5_belief_clock.png'],'C':['fig6_cross_venue.png'],'D':['fig5_belief_clock.png'],'E':['fig9_calibration_slices.png'],'F':['fig7_family_overview.png']}
    cross=pd.read_parquet(DATA/'weather_crossings.parquet');cross=cross[(cross.date>='2026-06-01')&cross.p0.notna()]
    a1=res.set_index('test_id').loc['A1'];drift=-100*a1.effect
    entries=[dict(id='P2_0',title='Weather prices absorb most obvious temperature information',
        one_liner=f'{int(res.survives_bh.sum())}/22 tests survive BH; {int(res.supported.sum())} in the predicted direction. {(cross.p0<=.03).mean():.1%} of threshold crossings were already ≤3¢; remaining next-hour drift averaged {drift:.3f}¢, below a 1¢ illustrative cost.',
        datasets=datasets,mechanism='Once a running station extreme rules out a temperature bucket, its YES probability should approach zero; contract-source mismatch and costs constrain the interpretation.',
        method='2,400 sampled events, 25,362 token histories, frozen 22-test family, temporal holdout, 10,000 resamples and full-family BH.',
        results=[dict(metric='registered tests',value=22,n=22,note='Includes blocked and insufficient rows as p=1'),
                 dict(metric='BH survivors',value=int(res.survives_bh.sum()),n=22,note='One contradicts its expected direction; diagnostics are not trading edges'),
                 dict(metric='already at or below 3 cents',value=float((cross.p0<=.03).mean()),n=len(cross),note='Holdout bucket crossings with an initial sampled price; not independent events'),
                 dict(metric='next-hour average decline, cents',value=float(drift),n=int(a1.n),note='Date-clustered across 110 dates; not captured profit')],
        controls='0/11 placebo false positives at p<0.05; source concordance audit, exact local-day/DST handling, strict as-of prices, seven-day block sensitivity.',
        verdict='partial',known_or_novel='Dataset-specific replication and source-quality evidence; no novelty or profit claim.',
        prior_art=['https://arxiv.org/abs/2602.19520'],figures=['figures/fig7_family_overview.png','figures/fig4_intraday_cases.png','figures/fig1_settlement_audit.png'],
        scripts=['acquire.py','weather_panel.py','analyze.py','publish.py'],
        caveats=['No historical executable spread/depth/fee reconstruction.','Archived NOAA observations lack first-publication timestamps; 30-minute lag is assumed.','Several non-weather tests are blocked or underpowered, not measured nulls.','AI-assisted hackathon research, not investment advice.'])]
    for r in res.itertuples():
        test=next(t for t in prereg['tests'] if t['id']==r.test_id)
        if r.status=='tested':
            desc=f'Held-out effect {r.effect:.4g}; 95% interval [{r.lo:.4g}, {r.hi:.4g}]; BH q={r.q:.4g} across 22 tests. '+('Expected direction supported.' if r.supported else 'Registered directional claim not supported.')
        else:desc=f'{r.status.title()}: {r.note}'
        results=[dict(metric='test status',value=r.status,n=int(r.n),note=r.note),
                 dict(metric='BH q, family size 22',value=float(r.q),n=int(r.n_dates),note='Unavailable/insufficient p=1 included in multiplicity denominator.')]
        for name,attr in [('held-out effect','effect'),('95% lower','lo'),('95% upper','hi'),('80% power MDE','mde'),('family-conservative MDE','mde_family')]:
            value=getattr(r,attr)
            results.append(dict(metric=name,value=float(value) if np.isfinite(value) else None,n=int(r.n_dates),note='Missing means not estimable, never a measured zero. Date means equally weighted.'))
        sources=datasets.copy()
        if r.mission in ['B','D']:sources.append(dict(name='Cached GDELT daily data and team event timeline',url='https://www.gdeltproject.org/data.html',access='Local cached public data; no DOC API calls'))
        if r.mission=='C':sources.extend([dict(name='Kalshi public market data',url='https://docs.kalshi.com/getting_started/quick_start_market_data',access='Keyless GET works; no identical historical panel'),dict(name='Deribit public option summaries',url='https://docs.deribit.com/api-reference/market-data/public-get_book_summary_by_currency',access='Keyless current snapshot')])
        if r.mission=='F':sources.append(dict(name='NASA VIIRS GIBS thermal anomalies',url='https://gibs.earthdata.nasa.gov',access='Sibling cache read-only; 2025-only hotspot mask for 2026'))
        entries.append(dict(id='P2_'+r.test_id,title=test['title'],one_liner=desc,datasets=sources,mechanism=test['mechanism'],
            method='Frozen prereg.json; SHA256 '+r.prereg_sha256+'. '+test['transform']+'. 10,000 resamples; time holdout; BH includes all 22 slots.',results=results,
            controls='Date clustering, fixed sign-flip placebos, 7-day block sensitivity for means; max-statistic lag null for correlations; explicit publication timing and source checks.',
            verdict=r.verdict,known_or_novel='Replication / source-specific diagnostic; no novelty priority claim. Local station-source mismatch audit adds dataset-specific evidence.',
            prior_art=['https://arxiv.org/abs/2602.19520','https://arxiv.org/abs/2606.04217'],
            figures=['figures/'+f for f in figures_map[r.mission]],scripts=['analyze.py','weather_panel.py','statistics.py'],
            caveats=[r.note,'Historical bid/ask spread, fees and executable size are not reconstructed. No supported trading-profit claim.','Final archives are not publication-vintage data; source revision and timestamp uncertainty remain.','AI-assisted hackathon research, not investment advice.']))
    # Match the existing research frontend's absolute-path convention.
    for entry in entries:
        entry['figures']=[str(ROOT/p) for p in entry['figures']]
        entry['scripts']=[str(ROOT/p) for p in entry['scripts']]
    (ROOT/'findings.json').write_text(json.dumps(entries,indent=2,allow_nan=False)+'\n')

def report(res,prereg,audit,cal,cross,ev):
    a=audit[audit.status=='audited'];late=cal[cal.date>='2026-06-01'];lc=cross[cross.date>='2026-06-01']
    place=pd.read_csv(ROOT/'placebo_results.csv');probes=pd.read_csv(DATA/'history_probes.csv')
    coverage=pd.read_csv(DATA/'station_coverage.csv');sample=pd.read_parquet(DATA/'weather_sample_events.parquet')
    costs=pd.read_csv(DATA/'current_cost_audit.csv');source=pd.read_parquet(DATA/'catalog_enriched.parquet')
    snapshot=json.loads((DATA/'gamma_snapshot_metadata.json').read_text())
    family=res.survives_bh.sum();supported=res.supported.sum();tested=(res.status=='tested').sum()
    indexed=res.set_index('test_id');drift=-100*indexed.loc['A1','effect']
    drift_cost=pd.DataFrame({'illustrative_all_in_cost_cents':[1.,2.,5.],
                            'gross_subsequent_decline_cents':[drift]*3,
                            'decline_minus_assumed_cost_cents':[drift-x for x in [1,2,5]]})
    valid_cross=lc[lc.p0.notna()]
    lines=[
      '# P2 — Polymarket as a dataset',
      f'Generated {datetime.now(timezone.utc).isoformat()}. AI-assisted public-data research for HackMIT; no investment advice, accounts, identity linkage or orders.',
      '## Primary result and full search accounting',
      f'**{family} of 22 preregistered tests survive Benjamini–Hochberg at q ≤ 0.05; {supported} also have the expected direction. {tested} tests were estimable. No executable market inefficiency is established.** The most useful distinction is between forecast quality, response to a station proxy, and the contract’s actual resolution source.',
      f'**Weather prices generally absorbed the obvious physical information already:** {(valid_cross.p0<=.03).mean():.2%} of {len(valid_cross):,} holdout crossings with an initial price were already at or below 3¢. The next-hour mean decline was only **{drift:.3f}¢** (A1 q={indexed.loc["A1","q"]:.4f}), smaller than even a one-cent illustrative all-in cost. That is a small statistical response, not a validated profit opportunity.',
      f'Market Brier loss was lower than persistence by {-indexed.loc["A2","effect"]:.4f}, seasonal history by {-indexed.loc["A3","effect"]:.4f}, and the conservative 72-hour-offset GFS baseline by {indexed.loc["A4","effect"]:.4f}. A4 therefore significantly contradicts its forecast-beats-market hypothesis. This does **not** show that markets beat the best forecast available at the cutoff: the GFS baseline intentionally uses older runs to guarantee temporal separation.',
      f'The weather source audit matched **{len(a):,} settled events across {a.city.nunique()} cities** with complete local-day observations. Rounded station extremes disagreed with settlement in **{a.mismatch_round.mean():.2%}** of these events. A disagreement is evidence that these sources/aggregation rules are not interchangeable, not evidence that either source is wrong.',
      f'The price sample contains **{len(sample):,} events** selected by a frozen, outcome-independent hash within city/month/max–min strata. {late.event_slug.nunique():,} holdout events have at least one valid noon-day-ahead forecast price; the paired baseline samples differ. The complete family, including blocked and insufficient tests, is below.',
      mdtable(res[['test_id','status','n','n_dates','effect','lo','hi','p','q','supported']]),
      'Effect units: A1 probability change; A2–A4 binary Brier-score differences; A5 calibration-residual difference; A6 change in absolute bucket-sum discrepancy; A7 absolute hourly-price-change difference; A8–A9 mismatch-rate difference; B1 absolute-return difference; B2/D1/F1 correlation of changes. Diagnostic tests A8/A9 are not market-inefficiency tests. Significant effects in the opposite direction reject the directional hypothesis.',
      '![Full family](figures/fig7_family_overview.png)',
      '## Preregistration, timing and reproducibility',
      f'Preregistered {prereg["frozen_at"]}; SHA-256 **{res.prereg_sha256.iloc[0]}**. `prereg.json` was written before price-history access or hypothesis testing and has not been rewritten. `prereg_transport_amendment.json` permits only the documented read-only batch-history POST (up to 20 token IDs) and smaller equivalent NOAA Parquet downloads; it was recorded before testing. No test, expected sign, horizon or family membership changed.',
      'Weather: train through 2026-05-31, holdout 2026-06-01 through 2026-09-18. Date-level clustering retains all buckets and cities on one date together; the reported mean weights dates equally after within-event averaging where applicable. 10,000 centered date-bootstrap null draws, percentile intervals, BH over all 22 slots, blocked/insufficient p=1. Seven-day moving-block intervals are secondary robustness fields in results.csv, not extra confirmatory tests. Non-weather series use the first 60% of overlapping dates to select any lag, then the last 40% to score; the permutation null takes the maximum over registered lags.',
      'Inference requires at least 30 held-out dates and 50 units for mean tests, or 60 held-out dates for correlations. Small-sample case studies remain descriptive. The 80%-power MDE is reported for estimable nulls in `results.csv`; it is an approximate independent-date calculation and may be optimistic under serial dependence. Family-conservative MDE additionally uses a Bonferroni critical value. Unavailable samples have undefined MDE, not zero effect.',
      f'Placebo false-positive rate: **{int(place.false_positive.sum())}/{len(place)} = {place.false_positive.mean():.1%}** at unadjusted p<0.05. One prespecified sign-randomized date-effect placebo per executable paired test (28-day signal shift for executable correlation tests); this small, dependent placebo battery is a diagnostic, not precise proof of nominal size.',
      'The inherited environment uses a folder-local Python 3.12 venv. Docker was attempted but its daemon did not respond; no host system packages were installed. `Dockerfile`, `requirements.txt`, and `requirements-lock.txt` provide reproduction options. All writes are inside this folder, including caches and this folder’s `.agent/CONTINUITY.md`.',
      '```sh\n# Reuse existing crawls; never rerun fetch_gamma.py\n.venv/bin/python prepare.py\n.venv/bin/python fetch_ghcnh.py\n.venv/bin/python acquire.py probes\n.venv/bin/python acquire.py weather\n.venv/bin/python acquire.py forecasts\n.venv/bin/python acquire.py access\n.venv/bin/python acquire.py other\n.venv/bin/python stations.py\n.venv/bin/python weather_panel.py\n.venv/bin/python other_panel.py\n.venv/bin/python baseline_panel.py\n.venv/bin/python physical_panel.py\n.venv/bin/python cross_venue.py\n.venv/bin/python analyze.py\n.venv/bin/python publish.py\n.venv/bin/python validate.py --artifacts\n```',
      '`register.py` is a one-time freeze command and refuses to overwrite. API access is separate from offline analysis. Current snapshot acquisition for cross-venue comparison is recorded in the response manifests; replaying analysis requires no network. Original request bodies, status codes, timestamps, retry history and response hashes are cached. Negative responses are cached too. Analysis must be rerun only after all selected-token acquisition completes.',
      '## Data access, provenance and coverage',
      '| Source | Access observed | Coverage / limitation |\n|---|---|---|\n'
      f'| Weather Gamma crawl | Existing local crawl reused | {len(source):,} bucket rows; no recrawl |\n'
      f'| General Gamma crawl | Frozen existing-file snapshot | {snapshot["rows"]:,} unique markets; contrary to handoff, writer/cursor still active at inspection; no new crawl launched |\n'
      '| CLOB history | HTTP 200, public GET and read-only batch POST | Explicit ≤7-day windows, five-minute weather sampling / hourly general sampling; interval=max misleading for older markets |\n'
      f'| NOAA GHCNh | Official keyless PSV/Parquet | {sum(coverage.status=="available")} matched stations; 15 ICAOs absent from supplied station list, no guessed substitution |\n'
      '| Open-Meteo previous runs | Keyless HTTP 200 | GFS temperature_2m_previous_day3; all target hours forecast at least 72h earlier, safely before day-ahead noon |\n'
      '| GDELT | Existing local Parquet reused | Sparse sampled days; Iran country-event tone available, crypto/election tone absent; no DOC API calls |\n'
      '| NASA VIIRS | Existing local GIBS Parquet reused | 2025-only frozen hotspot map for 2026; 48h assumed dissemination lag, no vintage guarantee |\n'
      '| Kalshi | Keyless public HTTP 200 | Market metadata and historical cutoff work; same-noon BTC contracts initialized/unopened; no historical identical-contract panel |\n'
      '| Deribit / Coinbase | Keyless public HTTP 200 | Current option summaries / spot work; historical exact-expiry digital panel not reconstructed |\n'
      '| CME FedWatch | HTTP 403 | Server reports IP scraping block; respected, no workaround or account |\n'
      '| P1 wallet engine | Sibling read-only inspection | Conservative ledger exists; audit sample ends June 2023 and is incomplete; no valid 2026 historical-profit attribution |',
      'Observed history-probe results:',mdtable(probes.groupby(['era','variant']).agg(requests=('status','size'),nonempty=('n',lambda x:int((x>0).sum())),points=('n','sum')).reset_index()),
      'The apparent historical-access failure under interval=max was resolved by explicit start/end timestamps on the same tokens. Monthly five-minute batch requests returned HTTP 400 (“interval is too long”); daily event groups with six-day windows succeeded. Failed requests remain cached; they were never treated as price observations.',
      'The general catalogue is a retrospective closed-market universe selected by final lifetime volume ≥$10,000. That is not a point-in-time investable screen. Its B/D/E comparisons apply only to this selected cohort; no volume-based historical signal is constructed. General-market endDate comes from the final cached metadata and is not guaranteed to be the date announced at creation. E’s horizon labels therefore remain metadata-based diagnostics, with no executable timing claim. Weather uses the explicit local date in the contract event slug.',
      '## A — Weather-market efficiency',
      '### Contract/source audit',
      mdtable(source.groupby('source_family').agg(bucket_rows=('date','size'),events=('event_slug','nunique')).reset_index()),
      'The other 29% in the handoff are mostly NOAA weather.gov station time-series URLs. The original station parser only recognized final path segments; `prepare.py` also parses the `site=` query parameter. Non-airport Hong Kong Observatory and Taiwan CWA records remain distinct. The catalogue contains source changes and station changes within cities; the analysis joins station plus date, never just city.',
      mdtable(audit.groupby('status').size().rename('events').reset_index()),
      mdtable(a.groupby(['source_family','kind']).agg(events=('date','size'),rounded_disagreement=('mismatch_round','mean'),raw_disagreement=('mismatch_raw','mean')).reset_index()),
      'NOAA temperatures are converted into contract units before floor(x+0.5) rounding. Whole-unit bucket classification is compared with a deliberately unrounded baseline; improvement from rounding is a mechanical source-compatibility diagnostic, not a novel forecasting effect. Only complete days with ≥18 observed local hours, earliest hour ≤02, latest ≥21 enter the final settlement audit. FM15/FM16-only comparisons require both subsets complete. DST is respected. Exact half-unit ties and full precision near boundaries can matter; no WU daily-page extraction was used to adjudicate residual disagreements.',
      '![Station audit](figures/fig1_settlement_audit.png)',
      '### Intraday timing',
      'Only elimination of finite buckets is treated as monotone certainty: a running high crossing the upper bound, or a running low crossing the lower bound. A finite apparent winning bucket is never declared certain before midnight. Observations are shifted 30 minutes as a prespecified availability assumption; the archive does not certify that assumption. The price response is measured on the subsequent 60 minutes using only as-of prices ≤15 minutes old. Missing quotes are missing, never terminal-price backfills.',
      f'{len(lc):,} held-out bucket crossings were reconstructed, covering {lc.event_slug.nunique():,} events; {int(lc.resolved_yes.sum())} of those apparently eliminated buckets nevertheless settled YES. The primary A1 average includes such contradictions rather than selecting them away. Delay summaries are descriptive; an already-low price is delay zero and a bucket never reaching 3¢ by local midnight is right-censored. Missing initial quotes are excluded from the displayed delay distribution.',
      '![Intraday cases](figures/fig4_intraday_cases.png)\n\n![Convergence](figures/fig3_convergence_distribution.png)',
      '### Day-ahead probabilities and biases',
      'The forecast cutoff is noon on the previous local day. Yesterday’s completed maximum is unavailable at that cutoff, so persistence starts from day d−2 and adds the early-period empirical distribution of two-day changes. Seasonal history uses ±30 calendar days of the target season, with past dates only and at least 30 observations; it is a short-history seasonal baseline, not a 30-year climate normal. GFS previous_day3 values are deliberately conservative: every target-day hour is issued before the cutoff. Early residual distributions turn forecast extremes into bucket probabilities; no realized target-day observations enter predictions.',
      'Brier scores are computed bucket by bucket, averaged within events, then by date. Paired samples differ across baselines; reliability curves are descriptive and can have different coverage. A5 contrasts open-ended and finite-bucket outcome-minus-price residuals. A6 tests contraction of bucket-sum deviations; A7 compares local night/day absolute hourly changes. None uses price-level correlations as evidence of prediction.',
      '![Calibration](figures/fig2_weather_calibration.png)\n\n![Forecast losses and sums](figures/fig8_forecast_and_bucket_sums.png)',
      '### Spread, fees and realistic size',
      f'Historical CLOB prices are sampled prices, not certified midquotes or bid/ask depth. Only {len(costs)} representative current weather books had both sides. Their spreads range from {costs.spread.min()*100:.2f}¢ to {costs.spread.max()*100:.2f}¢; {int(costs.has_100_dollars_within_one_cent.sum())}/{len(costs)} showed at least $100 of displayed ask value within one cent of the best ask. This is a depth audit, not an order simulation or a promise of fills.',
      mdtable(costs[['city','bid','ask','spread','ask_dollars_within_one_cent','raw_fee']]),
      'Fee-rate responses are preserved verbatim, because a current per-token parameter cannot establish past fees and should not be silently equated with a universal percentage. Current documentation describes category-dependent, price-dependent taker fees. No historical spread, depth or fee series was obtained. Thus even a significant response or calibration defect remains **historically unverified after costs**. Bucket-sum deviations can arise from asynchronous stale samples and cannot be called arbitrage.',
      mdtable(drift_cost),
      'The table is arithmetic on the measured average subsequent price decline, not a simulated order or realized P&L. Costs include spread/fees/slippage only by illustrative assumption; a short position, entry/exit fill and feasible historical depth were not established. All three assumed cost levels exceed the measured average decline.',
      '## B — Belief clocks',
      'Iran timeline anchors are dates, not verified first-news instants; B1 compares absolute daily price changes in 24-hour windows on either side of UTC day boundaries. B2 uses changes in Iran GDELT counts and future market returns after the full news day is complete. The 1/2/3-day lag selection occurs only in the early period, with a max-statistic permutation null. The case figure aligns actual cached prices, daily news counts and the sibling’s satellite observations on a shared axis.',
      'Earliest collected GDELT batches are upper bounds on publication time, not proof of first public knowledge. Some “ceasefire” keywords matched Ukraine/Gaza contracts; Iran primary panels require explicit Iran/Hormuz wording. General Fed, hurricane, election and outage markets were acquired, but a defensible exact-timestamp matched event panel was not built for those categories. They are access/coverage extensions, not extra unregistered statistical claims.',
      'The P1 ledger was inspected rather than rebuilt. Its accessible audited sample did not establish historical wallet positions and profitability for the 2026 event panel; no wallet is labelled informed or profitable from today’s snapshot. Public addresses were never linked to identities.',
      '![Belief clock](figures/fig5_belief_clock.png)',
      '## C — Finance-native comparisons',
      'A targeted current Bitcoin event lookup initially returned the previous year’s yearless slug. The explicit 2026 slug was fetched and the date checked; the old response is retained only as provenance. Polymarket’s Sep 20 noon ET threshold uses Binance BTC/USDT candle close. Kalshi’s same nominal time uses a 60-second CF Benchmarks BRTI average and was still initialized, with zero displayed quote fields and zero size. Those zeros were correctly treated as unavailable, not a 100-point mispricing.',
      'The chart compares live Polymarket quote bands with a descriptive Deribit call-spread digital approximation, converting BTC-denominated premiums using the contemporaneous index price. Expiries and settlement definitions differ; invalid approximations outside [0,1] are omitted, not clipped into valid probabilities. No same-contract historical comparison or lead/lag test is claimed. Kalshi NYC daily weather references CLINYC, whereas the Polymarket NYC contracts in this catalogue resolve at KLGA; same city does not mean same payoff. CME’s explicit 403 scraping block was respected.',
      '![Cross-venue checks](figures/fig6_cross_venue.png)',
      '## D — News tone and later drift',
      'Iran tone is daily IRN.tone_sum / IRN.events, then first-differenced. The target is the following completed market-return day, after the source news day could have been known. No missing news days are filled with zeros. The cached file does not contain crypto or election tone; D2 and D3 are blocked, not null. Mixed YES question directions and country-level topic breadth limit interpretation even for an estimable D1.',
      '## E — Known baselines',
      'The primary baseline panel uses exactly 24h before each original scheduled endDate, excludes known prior closures, and never substitutes the weather noon-day-ahead panel for that horizon. Weather-versus-politics loss is a compositional comparison, not evidence that physical quantities are intrinsically easier. Favourite–longshot residual differences use the fixed ≤10% and ≥90% cutoffs. Clearly exploratory reliability slices at 7 days, 6 hours and 1 hour add no hypothesis tests, optimized horizons or confirmatory claims. Final lifetime volume is not a valid historical liquidity measure, so it is labelled audit metadata only; historical liquidity-conditioned reliability remains untested.',
      '![Descriptive calibration slices](figures/fig9_calibration_slices.png)',
      '## F — Physical signals on the same question',
      'The sibling flare series selected persistent cells using all years, including future observations. This run instead freezes cells lit on ≥5% of available 2025 dates, then measures 2026 log1p daily FRP changes in the Gulf/Basra region. Completed-day signals are delayed a further 48h before subsequent 1/2/3-day price-return windows. The physical proxy is closer to the question than a broad commodity price, but clouds, fires and source revisions still confound it. F1 retains the preregistered minimum held-out sample requirement.',
      'Only two actual hurricane contracts and three record-heat contracts survived semantic screening. A Carolina Hurricanes hockey market and a speech-mentions market about the word “Hottest” were excluded as keyword false positives. No defensible named-storm/station alignment or publication-vintage global temperature-anomaly estimate was reconstructed; F2/F3 remain untested. Final revised anomalies are not silently used as historical signals.',
      '## Nulls, blocked claims, and tested versus believed',
      mdtable(res[['test_id','status','verdict','mde','mde_family','note']]),
      '“Rejected” means the registered directional claim failed the multiplicity/sign criterion in an estimable sample, not that the true effect is exactly zero. “Partial” on blocked/insufficient rows is a schema-compatible evidence-status label and is not partial statistical support. No test is silently dropped from the 22-member family. Descriptive city, season, source, case-study and cross-venue displays are exploratory; they introduce no additional confirmatory p-values.',
      '## Best demo artifacts',
      '- `figures/fig1_settlement_audit.png`: station-source disagreement at scale.\n- `figures/fig4_intraday_cases.png`: observed running extreme and bucket-price paths.\n- `figures/fig2_weather_calibration.png`: weather calibration with real baselines.\n- `figures/fig7_family_overview.png`: the full search count and corrected verdicts.\n- `figures/fig5_belief_clock.png`: price/news/satellite timing and its limits.\n- `figures/fig6_cross_venue.png`: why apparently identical markets require contract checks.',
      'Machine-readable: `results.csv` (one row per primary specification), `placebo_results.csv`, `findings.json` (one object per registered claim, including rejected/blocked ones), and normalized `data/*.parquet` panels. Raw source responses and HTTP manifests remain under `data/`; `scripts` are the folder’s `.py` files.',
      '## Prior art and primary documentation',
      '- [Polymarket historical-price API](https://docs.polymarket.com/api-reference/markets/get-prices-history) and [read-only batch schema](https://docs.polymarket.com/api-spec/clob-openapi.yaml), accessed 2026-09-20.\n- [Polymarket fee documentation](https://docs.polymarket.com/trading/fees), accessed 2026-09-20; current parameters cannot be retroactively applied.\n- [NOAA GHCNh](https://www.ncei.noaa.gov/products/land-based-station/integrated-surface-database): official hourly archive; source observation subsets and display precision matter.\n- [Open-Meteo Previous Runs](https://open-meteo.com/en/docs/previous-runs-api): fixed lead-time offsets, unlike stitching the latest historical forecast.\n- [Kalshi keyless market-data guide](https://docs.kalshi.com/getting_started/quick_start_market_data).\n- [Le, 2026-02-23, domain-specific calibration dynamics](https://arxiv.org/abs/2602.19520): prior cross-domain/exchange calibration work; no novelty claim for favourite–longshot or category calibration.\n- [Qin and Yang, 2026-06-02, Polymarket-v1 Database](https://arxiv.org/abs/2606.04217): ground-truth trade direction and microstructure measurement concerns; not used as a substitute historical ledger here.',
    ]
    (ROOT/'REPORT.md').write_text('\n\n'.join(lines)+'\n')

def main():
    res=pd.read_csv(ROOT/'results.csv');prereg=json.loads((ROOT/'prereg.json').read_text())
    audit=pd.read_parquet(DATA/'settlement_audit.parquet');cal=pd.read_parquet(DATA/'weather_calibration.parquet')
    cross=pd.read_parquet(DATA/'weather_crossings.parquet');ev=pd.read_parquet(DATA/'weather_event_metrics.parquet')
    figures(res,audit,cal,cross,ev);findings(res,prereg);report(res,prereg,audit,cal,cross,ev)
    print('Published 9 figures, findings.json and REPORT.md',flush=True)

if __name__=='__main__':
    main()
