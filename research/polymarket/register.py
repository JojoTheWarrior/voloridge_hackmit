"""Freeze the P2 family before any outcome analysis. Refuses to overwrite."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SPECS = [
    ('A1','A','Station threshold crossing predicts a price decline','Running maximum clears finite upper bucket bound (minimum clears lower bound), rounded in contract units','YES price change in next 60 minutes','post-minus-pre price, event mean', '0,60 minutes',-1,'A monotone running extreme rules out a bucket; observations delayed 30 minutes; >=30 independent local dates'),
    ('A2','A','Day-ahead market beats persistence','Market price and prior-day station extreme distribution','market Brier minus persistence Brier','paired score difference','previous local day 12:00',-1,'Price pools information beyond lagged weather; persistence uses day d-2, the latest complete day at cutoff'),
    ('A3','A','Day-ahead market beats seasonal climatology','Market price versus trailing seasonal empirical distribution','market Brier minus climatology Brier','paired score difference','previous local day 12:00',-1,'Price incorporates forecast innovations; trailing +/-30 calendar-day season window, past dates only, >=30 days'),
    ('A4','A','Archived forecast improves on day-ahead market','Fixed-model GFS prior-run forecast, temperature_2m_previous_day3','forecast Brier minus market Brier','paired score difference','previous local day 12:00',-1,'Every target-day hour at 72h offset precedes the cutoff; early-period residual distribution produces bucket probabilities'),
    ('A5','A','Open-ended tail buckets are overpriced','Open-ended vs finite temperature buckets at day-ahead cutoff','tail minus centre mean outcome-minus-price','calibration residual difference','previous local day 12:00',-1,'Longshot demand inflates tails; compare within event; calibration uses residuals, not level correlation'),
    ('A6','A','Bucket-sum discrepancy subsequently contracts','Sum of all bucket YES prices minus one','absolute discrepancy at +60m minus at cutoff','paired absolute-error difference','local 12:00 to 13:00',-1,'Complete partitions should normalize; all buckets must have nonstale histories'),
    ('A7','A','Prices update less overnight','Local night 00-06 versus day 12-18','night minus day mean absolute hourly price change','within-event volatility difference','local hourly',-1,'Trader activity differs by local clock; weather information arrival is a confound'),
    ('A8','A','Rounding explains station-settlement mismatch','Nearest integer in contract units versus unrounded extreme','rounded mismatch indicator minus raw mismatch indicator','paired error difference','complete local event day',-1,'Display precision changes bucket classification; diagnostic only, no causal or trading interpretation'),
    ('A9','A','METAR-only observations better reproduce settlement','FM15/FM16 extreme versus all quality-passing observations','METAR mismatch minus all-source mismatch','paired error difference','complete local event day',-1,'Different observation subsets can change daily extreme; diagnostic, not tradability'),
    ('B1','B','Dated news anchors concentrate market movement','Prelisted Iran timeline; Fed/election/hurricane/outage anchors where exact timestamps exist','absolute return after minus before event','paired absolute-return difference','24h before/after',1,'New information moves beliefs; date-only anchors use UTC day boundaries with no minute lead claims'),
    ('B2','B','News innovations precede market revisions','Daily change in topic news count','subsequent same-topic probability change','first difference news; probability return','1,2,3 days',0,'Beliefs absorb news with delay; choose lag on early 60%, max-statistic null across all three'),
    ('C1','C','Options divergence predicts crypto threshold drift','Matching digital probability from option call spread minus market','next-day threshold-market return','probability divergence vs return','24h',1,'Public derivatives and prediction markets price the same terminal threshold; exact expiry/settlement match required'),
    ('C2','C','Cross-venue divergence predicts convergence','Kalshi minus Polymarket probability on identical contracts','next-day Polymarket minus Kalshi return','gap change','24h',1,'Identical payoff markets should converge; contract language and timestamp match required'),
    ('C3','C','Fed futures divergence predicts prediction-market drift','Fed futures-implied probability minus market','next-day probability change','probability divergence vs return','24h',1,'Same decision reprices across venues; keyless historical futures and contract-matched timestamps required'),
    ('D1','D','Iran news tone predicts drift','Daily change in mean Iran GDELT tone','next-day Iran-market probability change','tone first difference and return','1 day',0,'Tone shocks may leave delayed belief revisions; no direction chosen after observing returns'),
    ('D2','D','Crypto news tone predicts drift','Daily change in mean crypto GDELT tone','next-day crypto-market probability change','tone first difference and return','1 day',0,'Same fixed tone specification across topics'),
    ('D3','D','Election news tone predicts drift','Daily change in mean election GDELT tone','next-day election-market probability change','tone first difference and return','1 day',0,'Same fixed tone specification across topics'),
    ('E1','E','Weather has lower forecast loss than politics','Category label at market creation','weather minus politics Brier score','date-clustered score difference','24h before scheduled end',-1,'Physical outcomes may be easier to forecast; descriptive category comparison with composition caveat'),
    ('E2','E','Longshots are overpriced relative to favourites','Price <=0.10 versus >=0.90','longshot minus favourite outcome-minus-price','calibration residual difference','24h before scheduled end',-1,'Replicate favourite-longshot distortion, one fixed horizon; liquidity strata descriptive only'),
    ('F1','F','Gulf flare recovery predicts reopening beliefs','Change in log1p Gulf daily flare index, delayed 48h','Hormuz reopening or ceasefire market return','lagged physical change and probability change','1,2,3 days',1,'Recovery can precede transport normalization; point-in-time source availability and no future hotspot-selection rule required'),
    ('F2','F','Storm intensification predicts hurricane beliefs','24h wind increase at contract-relevant station, delayed 30m','hurricane-market probability change','wind change vs future price return','24h',1,'Same named storm and contract geography required'),
    ('F3','F','Temperature anomaly innovations predict record-heat beliefs','Change in expanding running global anomaly estimate','hottest-month/year market return','anomaly change vs future price return','1 day',1,'Publication-vintage temperature estimate required; final revised anomaly is inadmissible'),
]

def main():
    p = ROOT / 'prereg.json'
    if p.exists():
        raise SystemExit('Already frozen; do not overwrite preregistration.')
    spec = dict(
        frozen_at=datetime.now(timezone.utc).isoformat(), seed=20260920, resamples=10000,
        family_size=len(SPECS), alpha=0.05,
        prior_looks='Read supplied brief, source code, column schema, two catalogue rows and one NOAA row. No historical prices fetched and no hypothesis tests run before freeze. Prior satellite-null work supplied by brief.',
        universe='Existing completed weather catalogue and vol10k crawl only; closed binary outcomes, exactly one winner per weather event. Event dates through 2026-09-18. No recrawl.',
        sampling='Weather price-history target: all buckets in 2400 events, deterministic SHA256(event_slug) ordering within city/month/kind round-robin; try 30 token access probes across early/middle/recent eras before bulk. If all valid historical endpoint variants give empty series, suspend bulk and label price tests blocked. Descriptive station audit uses all eligible events. Other categories: up to 60 markets per fixed topic/category, hash ordering, no outcome-based ranking.',
        time_split='Fixed train through 2026-05-31, held-out 2026-06-01 through 2026-09-18 for weather. Other missions first 60% of distinct overlapping dates train, last 40% held out. No late-period tuning.',
        station_rules='Parse ICAO from WU path or NWS site query. Do not substitute airport for non-airport authority. Use IANA local time/DST. Accept NOAA original-source QC 0,1,4,5,9 or blank with no GHCNh flags; plausible -80..65 C. >=18 distinct local hours, coverage reaches <=02 and >=21. Event winner status requires exactly one terminal YES and all binary prices. Round floor(x+0.5) in stated units; ties sensitivity descriptive. Both early closed losers and later settled winners belong to the same local event date.',
        point_in_time='NOAA archive has no ingestion timestamps: intraday 30m assumed publication lag is a retrospective proxy only, not certified executable information. Weather certainty means elimination of finite buckets or entry into absorbing open tail; never label afternoon finite winning bucket certain. Price asof must be at/before cutoff and <=120m old for calibration, <=15m for intraday, no terminal snapshot backfill. Outcomes only score predictions. Final volume is audit metadata, never a historical signal or liquidity filter.',
        inference='10,000 date-cluster bootstrap draws for mean score/error/return differences; null centered bootstrap two-sided p=(1+extreme)/(10001). Cluster on local date across cities, include all same-event buckets together. >=30 unique held-out dates and >=50 events otherwise insufficient. Serial robustness: 7-day moving block bootstrap CI, disclosed exploratory. Correlation tests use daily differences, 7-day block permutation and max absolute r over registered lag set, training-selected lag held fixed on late period; >=60 dates. BH over all 22 slots including blocked/insufficient as p=1. Supported only q<=.05 and expected sign (or sign=0).',
        power='For mean nulls, approximate 80% power two-sided MDE=(1.96+0.842)*SD(date means)/sqrt(n_dates); family-conservative MDE uses z(1-.05/(2*family_size))+0.842. Correlations: tanh((z+0.842)/sqrt(n_dates-3)). Undefined for inaccessible data, not zero.',
        controls='For every executable primary paired test, one seeded Rademacher sign flip of date-level effects followed by the identical 10,000 bootstrap test; report unadjusted placebo false-positive rate with denominator. Diagnostic mismatch also by city, source, season, max/min, completeness, and rounding, all descriptive. For correlation tests fixed 28-day signal shift placebo. No placebo counts when untestable.',
        costs='Never call price-history a bid/ask or fill. Audit public current fee-rate and order-book for representative live tokens, $100 size; current books cannot certify past costs. Historical bid/ask/size missing => historical tradability unverified. Report gross cents against illustrative 1/2/5-cent all-in costs only if gross edge measured, label assumptions.',
        access='Public GET only; disk cache all successful and failed requests; one request in flight per process and >=0.4s gap, exponential backoff for 429/5xx. Cached completed crawls immutable. No identity linkage, accounts, orders or credentials.',
        tests=[dict(id=i,mission=m,title=t,signal=s,target=y,transform=x,horizon_lag_range=h,expected_sign=sign,mechanism=mech,primary_specification=mech) for i,m,t,s,y,x,h,sign,mech in SPECS],
    )
    spec['family_size'] = len(spec['tests'])
    spec['inference'] = spec['inference'].replace('all 22 slots',f"all {len(SPECS)} slots")
    p.write_text(json.dumps(spec, indent=2)+'\n')
    digest = hashlib.sha256(p.read_bytes()).hexdigest()
    (ROOT/'prereg.sha256').write_text(digest+'  prereg.json\n')
    print(digest, 'family=',len(SPECS))

if __name__ == '__main__':
    main()
