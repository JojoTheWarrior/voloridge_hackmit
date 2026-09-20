# Codex handoff

Codex owns all Polymarket work (briefs P1 and P2 — start here). Briefs 1–4 further down are
optional extras nobody is working on. Paste the "Shared rules" block plus one brief per session.
P1 and P2 hit the same APIs from one IP: if you run them at the same time, share one cache
directory and keep total request concurrency modest.

## Project context (give this to Codex too)
HackMIT 2026, Voloridge (quant hedge fund) track, "Signal in the Noise": build something
interesting from real public data; judged on Originality, Technical Excellence, Insight,
Execution. Judges are quant researchers — the first thing they ask of any finding is "how many
things did you test?". The product: "point the system at datasets, assign a mission to find a
connection, get back a tested verdict." Findings are showcase examples; known results are fine if
real, novel ones are the prize. No need to tie anything to the sponsor's example dataset list.
Every research folder under `~/projects/kingdom/explore/` writes a `findings.json` in one shared
schema (below) that the team's frontend will read. `explore/IDEAS.md` is the running summary.

## Shared rules (prepend to every brief)
- Work only in your brief's folder under `~/projects/kingdom/explore/` (own venv). Read sibling
  folders for hints; modify nothing outside your folder.
- Read-only research on public data. Do not create accounts, connect or create wallets, enter
  credentials or API keys, accept terms, or place/simulate orders through any interface. A login
  wall is a blocker to record, not to work around.
- Public wallet-level data is in scope: trades, positions, holders and P&L by address are public
  and analysing them is standard. Treat addresses as pseudonymous addresses — do NOT try to link
  a wallet to a real-world identity. Behavioural clustering of addresses is fine; naming people
  is not.
- No look-ahead, anywhere. Anything used at time t must have been knowable at time t.
- Pre-register: write `prereg.json` (every test: signal, target, transform, horizon/lag range,
  expected sign, mechanism, and ONE primary specification) BEFORE running anything, and record
  its sha256. Run exactly those; everything else goes in a clearly labelled exploratory section.
- Statistics: changes/returns, not levels. Permutation or bootstrap with ≥10,000 resamples; when
  you search over lags/horizons use a max-statistic null. Benjamini-Hochberg across the ENTIRE
  pre-registered family; report family size and survivors first. Hold out by time — define and
  tune everything on the early period, score on the late period. Add placebos/controls and
  report the placebo false-positive rate. State the minimum detectable effect for nulls.
- Any apparent market inefficiency must be checked against the bid-ask spread, fees and
  realistic size. Most edges die inside the spread — say so plainly when they do.
- Report nulls bluntly. A clean, well-characterised null is a good outcome; an overclaimed hit is
  the worst outcome. (Reference for the standard expected: `explore/markets/` —
  `prereg.json`, `test_engine.py`, `results.csv`, `figures/fig4_family_overview.png`. That agent
  pre-registered 53 tests of satellite signals vs prices; 0 of 46 market tests survived, and that
  null is now a showcase item.)
- Be polite to free APIs: on-disk cache, exponential backoff on 429/5xx, modest concurrency.
- Output, in your folder: scripts; cached data (parquet); `prereg.json`; `results.csv` (one row
  per test/spec); demo-quality PNG figures in `figures/`; and `findings.json` — a list of
  `{id, title, one_liner, datasets:[{name,url,access}], mechanism, method,
  results:[{metric,value,n,note}], controls, verdict: supported|partial|rejected,
  known_or_novel, prior_art:[urls], figures:[paths], scripts:[paths], caveats}` — one object per
  claim, INCLUDING rejected ones. Also write `REPORT.md`: primary result first, family size and
  survivors, data-access table, tested vs believed, best figures, nulls.
- Research for a hackathon demo, not investment advice. Describe statistical relationships; make
  no recommendations to trade.

---

## Brief P1 — Expert-weighted consensus & whale watching (`explore/polymarket_experts/`)
**This is the priority brief.** The folder exists but holds only an empty venv — the previous
agent was stopped during data-access discovery. Its one lead: several bulk mirrors of on-chain
Polymarket `OrderFilled` events exist (Kaggle / HuggingFace / GitHub); it was about to read their
READMEs for schema, provenance and coverage. Start by finding and evaluating those — a bulk
mirror is far faster than paging an API for every trade.

**The idea** (from a team member who built a version of it while working at Polymarket): for a
market in a category (e.g. NBA games), take everyone with an open position; compute each wallet's
lifetime realised P&L on PAST markets in that same category; a wallet is an "expert" if that P&L
exceeds a threshold (originally $10k); compute a new implied probability from experts only,
weighted by P&L and bet size. Hypothesis: crowd prices in emotional categories (sports above all)
are biased, and the expert-weighted consensus is a more accurate probability than the price.

1. **Data access, for real.** Evaluate every keyless route to wallet-level history at scale and
   record depth, pagination limits, rate limits, gaps: Polymarket Data API (`/trades`,
   `/positions`, `/holders`, `/activity`, leaderboards); Gamma API (markets, events, tags,
   resolution — a resumable keyset crawler already exists at `explore/polymarket/fetch_gamma.py`,
   and `explore/polymarket/data/gamma/vol10k.jsonl.gz` already holds ~120k+ markets with volume
   ≥ $10k, crawl marked DONE); CLOB `prices-history`; Goldsky-hosted subgraphs (positions, PnL,
   activity, orderbook); raw Polygon logs of the CTF Exchange / neg-risk exchange /
   conditional-token contracts via public RPC or public dumps; bulk mirrors (above). You need
   enough to reconstruct, for any wallet and any past timestamp, its position in every market and
   its realised P&L up to then.
2. **Point-in-time reconstruction — this makes or breaks the result.** Expert status at time t
   uses ONLY markets resolved before t. Positions at t are rebuilt from trades up to t, never
   from today's snapshot. Handle YES/NO and multi-outcome neg-risk markets, splits / merges /
   redemptions, fees, and proxy wallets. Flag market makers (high-turnover, two-sided, inventory
   mean-reverting) separately: a market maker's inventory is not a view. Unit-test the P&L engine
   against a handful of wallets whose leaderboard P&L you can read from the public site/API.
3. **Build the signal.** For each market at fixed horizons before resolution (24 h, 6 h, 1 h;
   plus open + X hours) compute: market mid price; expert-weighted implied probability under
   several weightings (equal; by category P&L; by position size; P&L × size; category ROI or hit
   rate with shrinkage for small samples); number of experts; total expert exposure;
   expert-minus-market divergence. Save as `expert_panel.parquet` (market, category, horizon,
   market_price, expert_prob variants, n_experts, outcome) — the frontend will query this.
4. **Primary test (pre-register it).** Out-of-sample Brier score and log loss: expert consensus
   vs market price vs a blend; paired bootstrap (≥10,000) on the difference; reliability curves
   for both. Report by category — NBA / NFL / soccer / other sports, politics, crypto-price,
   weather, culture. The hypothesis says sports shows the biggest gain: check whether it does.
5. **Does divergence carry information?** Regress outcome on market price + divergence. Does
   divergence predict later price drift toward the expert view? Over what horizon?
6. **Robustness.** Threshold sweep ($1k, $5k, $10k, $50k, top-N, top-percentile); minimum number
   of past markets; category-specific vs overall P&L; excluding market makers; excluding the few
   largest wallets; liquidity buckets. **Is expertise persistent?** Does past category P&L predict
   future category P&L out of sample (rank correlation, decile spreads) — or is it luck and
   survivorship? Placebo: random wallets matched on size and activity.
7. **Economic sanity.** Would acting on divergence have cleared spread + fees at realistic size?
   n, average edge in cents, bootstrap interval. If it dies inside the spread, say so.
8. **Whale-watching extras (exploratory, labelled).** (a) Does net buying by proven-profitable
   wallets lead price over the next 1–24 h? (b) Around dated news events, who trades first — are
   the earliest large trades made by historically profitable wallets? (c) Clusters of addresses
   trading in lockstep (address clusters only). (d) Specialists vs generalists. (e) P&L
   concentration: share of all profit captured by the top 0.1% / 1% of wallets, by category.
9. **Prior art.** Published/blogged work on Polymarket smart money, leaderboard-following,
   wallet-skill persistence, copy-trading tools. Say what is known and what is new here.

Figures wanted: reliability curves (market vs expert consensus) by category; Brier improvement by
category with intervals; skill-persistence decile chart; P&L concentration curve; 2–3
single-market case studies (price vs expert consensus through time, resolution marked).

---

## Brief P2 — Polymarket as a dataset: weather markets, belief clocks, cross-venue (`explore/polymarket/`)
The previous agent was stopped early but left useful groundwork — build on it, don't redo it:
- `pmlib.py` — cached GET with backoff + tolerant jsonl.gz reader. `fetch_gamma.py` — resumable
  keyset crawler for the keyless Gamma API (`https://gamma-api.polymarket.com`), slim market
  records incl. `clobTokenIds`, `resolutionSource`, `negRisk`, tags.
- `data/gamma/weather.jsonl.gz` and `data/gamma/vol10k.jsonl.gz` — both crawls finished
  (cursor files end in DONE).
- `build_weather_catalog.py` → `data/weather_catalog.parquet`: **140,128 temperature-bucket
  markets in 13,270 events across 55 cities, 2025-02-01 → 2026-09-22**, 97.5% closed, $914M
  total volume (median bucket ≈ $3k). 111,627 "highest temperature" and 28,501 "lowest". Columns
  include city, date, bucket, lo, hi, unit, yes_token, yes_final, volume, created/start/closed
  times, res_url, station. Biggest by volume: London $98M, NYC $76M, Seoul $60M, Hong Kong $51M,
  Shanghai $37M, Paris $30M. Event count is exploding: 362 in Feb 2026 → 2,208 in Sep 2026.
- 71% of these markets resolve on a Weather Underground daily-history page for a specific airport
  station; the ICAO code is parsed from the resolution URL into `station` (55 stations, e.g. EGLC
  for London). Check what the other 29% resolve on.
- `fetch_ghcnh.py` + `data/ghcnh/` — NOAA GHCNh hourly station files (the successor to ISD; same
  METAR/synoptic feed; keyless from ncei.noaa.gov) for 2025–2026, ~23 station-year files pulled
  so far; finish the rest. (The AWS ISD mirror is stale: 2025 stops ~Oct, no 2026 — don't use it.)
- Not yet done: any price history, any analysis, `prereg.json`, figures.

Missions (pre-register; A is the deepest):
A. **Weather-market efficiency.** Pull CLOB `prices-history` for the bucket tokens (check
   granularity and depth; cache). (1) Intraday: at what local time does the station's observed
   running max/min make the outcome near-certain, and when does the price converge? Measure the
   gap in minutes across thousands of events, by city. Mind the resolution source's quirks —
   Weather Underground's displayed daily max vs the raw METAR values (rounding, °C→°F conversion,
   which observations it includes); quantify how often GHCNh-derived and resolved outcomes
   disagree, because that disagreement is itself a finding. (2) Calibration of day-ahead prices vs
   baselines: climatology + persistence, and archived forecasts (Open-Meteo's historical-forecast
   API is keyless). Reliability curves by city / season / bucket position (tails vs centre). (3)
   Systematic biases: favourite-longshot in tail buckets, neg-risk bucket sums ≠ 1, stale
   pricing overnight in the station's time zone. Spread/size check on everything.
B. **Belief clock — who knows first?** For well-dated real-world events with liquid markets,
   align at the finest resolution available: Polymarket price moves, news volume, and (where
   relevant) physical detection. For the 2026 Iran-war scenario the team has a timeline at
   `~/projects/kingdom/voloridge_hackmit/data/reference/iran_timeline.csv` (strikes from ~28 Feb
   2026; Hormuz closed ~4 Mar–8 Apr 2026; ceasefire; reopening) and first-satellite-detection
   times for strikes in `explore/wardamage/` (finding so far: satellites are ≥8 h slower than
   news). Add hurricanes, elections, Fed decisions, outages. GDELT's DOC API rate-limits hard
   (429s) — use GDELT raw files on AWS or the repo's `data/cache/gdelt_daily.parquet`, or any
   keyless news source with better timestamps. Add the wallet angle: who traded first, how big,
   and were those addresses historically profitable (coordinate with P1's P&L engine if it
   exists; don't rebuild it). n is small — case studies plus an honest aggregate.
C. **Finance-native comparisons.** Crypto-price threshold markets vs probabilities implied by
   spot/perp/options from keyless exchange APIs (Deribit public endpoints, Binance/Coinbase
   public data); Fed/CPI markets vs futures-implied odds if keyless; election markets vs polling
   averages; identical questions on Polymarket vs Kalshi (Kalshi's public market-data endpoints
   if they work without a key) — persistent gaps, who leads, and whether gaps exceed costs.
D. **News tone → drift.** Topic news shocks vs subsequent price drift (under/over-reaction)
   across many markets, with full multiple-testing control.
E. **Baseline (known, needed as a sanity check of the data).** Reliability curve by category,
   time-to-resolution and liquidity; favourite-longshot bias; physical-quantity markets (weather)
   vs political ones.
F. **Physical signal → market on the same question** (expect a null — `explore/markets/` found 0
   of 46 satellite→price tests survive — but these markets are closer to the physical quantity):
   "Hormuz reopens by…" / "ceasefire by…" vs the Gulf flare-recovery series in
   `explore/wardamage/`; hurricane markets vs station pressure/wind; "hottest month/year" markets
   vs running temperature anomalies.

Figures wanted: intraday convergence panel (observed running max vs bucket prices for a few
events); time-to-certainty vs time-to-price distribution by city; weather calibration curves;
an event-clock panel (market price, news volume, satellite detection on one time axis);
Polymarket-vs-Kalshi or vs-options-implied comparison.

---

# Optional extras (not Polymarket; nobody is working on these)

## Brief 1 — Uber vs Lyft from NYC taxi records (`explore/rideshare/`)
NYC TLC High-Volume For-Hire Vehicle trip records (s3://nyc-tlc / the TLC CloudFront parquet
files, keyless; column-only reads are ~5–8 s/month) carry `hvfhs_license_num`: HV0003 = Uber,
HV0005 = Lyft (HV0002 Juno, HV0004 Via, historical). From Feb 2019 onward the files include
fares, driver pay, tips, tolls, congestion fees, trip miles/time, shared-ride flags.
Build monthly and quarterly per-company series: trips, gross fares, take rate
(1 − driver_pay / base_passenger_fare), average fare per mile, wait time
(on_scene − request), share of trips. Then test against reported company results: Uber and Lyft
quarterly gross bookings / revenue / rides (from their press releases or SEC EDGAR — EDGAR is
keyless with a User-Agent header). Questions: does NYC trip/fare growth track company-level
growth (r on YoY changes, n ≈ 25 quarters)? Does the NYC Uber:Lyft share shift lead reported
share? Does the take-rate series show the 2019 NYC driver-pay rule and later changes? Note TLC
publication lag (~2 months) and say honestly whether the series would have been available before
each earnings date. Known idea in alt-data circles; the showcase value is reproducing a Wall
Street alt-data product from public records. Figures: share over time with events marked; NYC
growth vs reported growth scatter; take-rate timeline.

## Brief 2 — Heat → demand → emissions → prices chain (`explore/heatchain/`)
A scout already showed one airport thermometer predicts state electricity demand (NOAA station
data × PUDL EIA-930: Texas from DFW held-out R² 0.70–0.80, +2.9 %/°C above 25 °C; NY from LGA
+4.0 %/°C). Extend it into a chain across every large balancing authority: temperature → EIA-930
demand → fossil generation by fuel (EIA-930) → hourly CO2/NOx (EPA CEMS in PUDL,
s3://pudl.catalyst.coop/nightly/, anonymous, 4.9 GB parquet — filter with duckdb) → downwind
ground NO2/O3 (OpenAQ S3 archive; readers in `explore/scout/oaq.py`). Deliver per-region marginal
responses (% demand per °C, MWh fossil per °C, tonnes CO2 per °C-day) with hold-out validation,
and which grids are most temperature-fragile. Notes: the AWS ISD mirror is stale — use NOAA GHCNh
over HTTPS (`explore/polymarket/fetch_ghcnh.py` shows how) or Open-Meteo's ERA5 archive; from
mid-2024 EIA-930 splits `hydro` into `hydro_excluding_pumped_storage` + `pumped_storage`.
Financial leg (Henry Hub, utility equities around heat waves) is exploratory — `explore/markets/`
found US-West hydro → Henry Hub null. Figures: per-BA response curves; US map of °C-sensitivity;
chain diagram with measured coefficients.

## Brief 3 — Science follows the headlines, at scale (`explore/newslag/`)
A scout measured that mpox papers peak ~3 months after mpox news (GDELT × OpenAlex, r=0.61 at
lag 3 vs 0.39 at lag 0; 8,149 papers). n=2 topics. Scale it: 50–100 well-dated shock topics
(outbreaks, disasters, technologies, conflicts, materials like LK-99/perovskites). Use GDELT raw
files/GKG on AWS (the DOC API rate-limits hard) and the OpenAlex S3 snapshot or its keyless
polite-pool API (mailto header, no key). Estimate the distribution of news→paper lags by field,
which fields react fastest, preprint vs journal, and whether news volume predicts eventual
citation count. Control for secular growth in publishing (the ChatGPT case was
trend-confounded). Figures: lag distribution by field; a gallery of 6 paired news/paper curves.

## Brief 4 — Wildfire smoke, measured twice (`explore/smoke/`)
Satellite fire detections upwind → ground PM2.5 downwind. Fires: VIIRS hotspots from NASA GIBS
vector tiles, keyless, 2012→yesterday — working fetcher at `explore/wardamage/gibs.py`
(read-only; note a probable Suomi-NPP outage around Jul–Aug 2022 — check per-satellite counts).
Ground truth: OpenAQ S3 archive (`explore/scout/oaq.py`, `explore/airquality/` have readers and a
station index). Wind: ERA5 via Open-Meteo archive (keyless). Cases: Canada 2023 → NYC/Chicago,
California 2020, Australia 2019–20, Indian stubble burning → Delhi each Oct–Nov, Indonesian peat
fires → Singapore. Build an upwind fire-radiative-power index weighted by wind trajectory and
test how many days ahead it predicts PM2.5 exceedances (hold-out years; baseline = persistence +
CAMS forecast). Figures: event maps with fire pixels, wind arrows and station PM2.5; lead-time
skill curve.
