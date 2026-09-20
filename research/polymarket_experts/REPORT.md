# P1 — Expert-weighted consensus & whale watching

**83 tests preregistered; 0 evaluated; 83 blocked; 0 supported statistical conclusions.**
The expert-consensus hypothesis remains **untested**. This is an incomplete empirical study with a measured data-access/accounting audit, **not a clean statistical null**. All requested output paths exist, but `expert_panel.parquet` is a typed **zero-row** panel; the requested empirical charts are explicitly unavailable. It would be misleading to show expert probabilities, Brier gains, or profit concentration from these inputs.

Generated 2026-09-20T07:18:53.036518+00:00. SHA256 of immutable preregistration: `05cc3745052423283536e4a78d0e334f217b51cfd33eea25788eaea858d13a71`.

## Primary result and what was actually tested

The audit downloaded **126,752 actual V1 OrderFilled rows**, representing **51,419 transactions**, **4,817 maker addresses**, and **2,636 outcome tokens**, from 2022-11-21T19:49:29+00:00 to 2023-06-30T23:56:45+00:00. Zero duplicate event keys were found. The audit slice is the first eight monthly shards, chosen for a bounded, reproducible check of original event semantics, not for predictive performance. It is outside the registered holdout and never treated as an out-of-sample test.

**51,419 rows (40.6%) name the Exchange as taker.** These correspond to aggregate taker-order settlement rows in this slice. Appending an opposite taker position to every maker row would double count some matched order flow. A maker-only replay, with V1 fees in the received asset, has **3,515 negative inventory observations in 1,252 wallet–token pairs**. This diagnostic identifies missing lifecycle/opening-state information or other unresolved accounting, not literal short balances. Nonnegative paths are not proof of completeness either.

Three public historical RPC receipts contain 27 logs, including 6 CTF logs and 6 exchange fills. **6/6 fills match** five raw integer fields plus maker/taker addresses. This spot check validates those rows, not the full archive. Three pseudonymous wallets' current all-time leaderboard P&L agrees with the same provider's `realized_pnl` atom. **Independent engine-versus-leaderboard lifetime P&L reconciliation was not achieved.** The latter comparison is a consistency test, not independent validation, and these leaderboard-selected wallets never enter an expert cohort.

## Data-access evaluation

Discovery and bulk README/schema evaluation preceded any Polymarket API paging. All activity was public read-only HTTP or read-only RPC. No account, API credential, wallet connection, signature, payment, order, or order simulation was used. No address was linked to a real identity. Raw endpoint responses may carry public display fields; analytic exports retain addresses and numeric data only.

| Route | Observed access | Depth / coverage | Pagination / rate limits | Gaps |
|---|---|---|---|---|
| Hugging Face wzsg V1 | 200; 8 parquet shards downloaded | 1,206,105,187 rows; 2022-11-21 to 2026-04-28; 71.06 GB, 289 files (publisher manifest) | Monthly immutable parquet; anonymous; no rate quota found | Fills only; excludes pre-CLOB AMM; maker/taker aggregate legs; no transfers/lifecycle/quotes |
| Hugging Face wzsg V2 | 200 metadata; not downloaded | 575,630,861 rows; through 2026-08-03; 33.62 GB (retrieved card) | Monthly parquet; different ABI; no rate quota found | V2 collateral/fee semantics differ; no lifecycle or historical quotes |
| Hugging Face SII-WANGZJ | 200 README and file listing | Raw file 110.30 GB; README older 689M-row snapshot through 2026-03-04 | Monolithic parquet; file listing newer than card; no rate quota found | Derived YES-normalized user data unsafe as original inventory; no lifecycle; stale card sizes |
| Kaggle ethanbensadoun/polymarket-dataset | 200 public metadata and file list | 39.48 GB raw orderFilled_complete.csv; updated 2026-04-07 | File download route not exercised; unknown data time boundaries/rate quota | warproxxx/Goldsky-derived; no additional lifecycle or depth files listed; no need to download redundant CSV |
| GitHub warproxxx/poly_data | 200 README | V2 collector; old v1-final tag | Current HyperSync backend requires token since 2025-11-03 | Code rather than keyless mirror; credentials prohibited |
| Rocklabs | 200 public README/catalog | Advertises 1.5B+ chain events and 438M+ lifecycle rows | Research access by contacting provider; no public bulk URL in catalog | Not anonymously downloadable from evaluated catalog; no contact/account created |
| Data API v1 trades | 200; offset=10001 -> 400 | Observed error: max historical offset 10000 | 200 req/10s documented; bounded probes only | Offset ceiling; default taker-only view must not substitute for full ledger |
| Data API v1 activity | 200; offset=10001 -> 400 | Observed error: max historical offset 5000 | General 1000 req/10s; wallet-anchored | Includes lifecycle types but bounded offset; no full history fetched |
| Data API v1 positions / closed-positions | 200 for 3 wallets | Current/closed snapshots; 5 rows per probe | 150 req/10s each documented; full page cap not live-tested | Current state is not historical state; window filtering is not an as-of reconstruction |
| Data API holders / leaderboards | 200 | Current top holders and current ranks; 3 validation wallets | Snapshot-oriented; no historical panel; general Data API quota | Used for endpoint validation only; never discover historical experts from current winners |
| Data API V2 trades/activity | 200, second cursor pages verified | user + start=1 requests full history; omitted start defaults 3y; max page 1000 | Keyset cursor; trades 300/10s, activity 200/10s; retain user on activity resume | Promising wallet history route, but universe-wide complete ledger not fetched or independently reconciled |
| Data API V2 positions/PnL/leaderboard | 200; 3 same-wallet PnL checks | PnL atoms, current position economics; all-time board is realized-only | Positions max page 1000, 200 req/10s; PnL is aggregated series | Position start/end filters last-event time, not historic holdings; same-provider agreement is not independent validation |
| Gamma local cache + API | 200 probe; local frozen file has truncated gzip tail | 348374 complete market records retained; >=USD10k source filter; actively growing sibling | Existing keyset crawler read only; /markets 300 req/10s | Not DONE at inspection; partial snapshot; final-volume selection unsuitable for confirmatory universe |
| CLOB prices-history | 200; oldest-market probe returned empty history | Depth varies by token; one old-market probe is not a universal depth claim | 1000 req/10s; interval/fidelity; no bid/ask depth in history | No price substituted for midpoint; no historical size/spread acquired |
| Data API V2 prices-history (docs) | Public OpenAPI evaluated; endpoint not probed | 3h/12h permanent since 2022; fine grains expire; explicit windows <=15d | max page 10000; cursor; as_of mode; 200 req/10s | Terminal synthetic settlement point is not an ordinary price observation; no full book depth |
| Goldsky orderbook/positions/activity/PnL subgraphs | All four HTTP 429 with ENDPOINT_DEPRECATED | Paused after 2026-04-28 V2 migration | Bounded exponential retries performed; not ordinary throttling | Provider explicitly says stale/incorrect; do not crawl |
| Goldsky Edge / Turbo | Edge public probe -> HTTP 402; docs require key | Activity, balances, positions advertised | API key or payment; Turbo requires account | Blocked by no credentials/payments/accounts rule |
| Polygon PublicNode | 200 head/recent logs; old logs returned JSON-RPC error | Recent CTF logs available; 2022 sample pruned | Small 11-block and 101-block probes; quota not load-tested | Cannot infer archive support from HTTP 200; no historical result |
| Polygon dRPC | 200; 57 old CTF logs; 3 receipts; 66 standard + 147 neg-risk logs | Historical sample from block 35896869 available | Serial small ranges; 1001-block topic query failed, 101-block retry succeeded; exact cap unconfirmed | Potential public full ledger route; entire backfill and reconciliation remain unperformed |
| polygon-rpc.com | 401 | No usable keyless response | No authenticated retry | Access blocked |
| PMXT archive | Network failure after bounded retries | Web index advertises hourly orderbooks; no file acquired | Public parquet archive; quota unknown | Do not assert service is globally unavailable; no verified quotes in this run |
| CryptoHouse | 200 web shell | No SQL dataset queried | No anonymous SQL endpoint verified in this run | Additional lead, not an evaluated-complete history source |

The named route set in the brief was evaluated, including both exchanges and the CTF route; this is not proof that every public dump on the internet was discovered. Bulk-size figures are publisher metadata, not independent full-download verification. Rate quotas are documentation values as accessed on 2026-09-20, not stress-test results. Serial requests, on-disk caches and bounded exponential retries kept load modest; brief independent probes ran in at most two processes. The sibling cache is read-only and all new network caches are local to this folder, respecting the stronger folder-write restriction.

The [official API rate documentation](https://docs.polymarket.com/api-reference/rate-limits) and cached V2 OpenAPI describe current pagination. V1 trades actually rejected offset 10001 with a 10000 cap; activity rejected it with a 5000 cap. **V2 changes the answer:** wallet trades/activity support keyset cursors and `start=1` for full history. A trades cursor resumed alone; an activity cursor initially returned 400 without `user`, then succeeded with `user`. This is a viable continuation route, not a blanket access failure.

All four old Goldsky hosts returned HTTP 429 with an `ENDPOINT_DEPRECATED` body, rather than ordinary temporary throttling. [Goldsky's current documentation](https://docs.goldsky.com/chains/polymarket) confirms the V2 migration. Its Edge activity route returned **402 Payment Required**, and its OpenAPI declares API-key security. No payment/login workaround was attempted. Public dRPC did serve an old 101-block window; PublicNode returned a pruned-history JSON-RPC error despite HTTP 200. Historical probes also returned 66 standard-exchange and 147 neg-risk-exchange logs. A 1001-block finality-topic query returned a range error (claiming a 10000-block cap despite the smaller request); a 101-block retry returned an empty successful result. The effective provider limit is therefore unconfirmed. A full historical backfill remains engineering work, not demonstrated impossibility.

The [V1 mirror](https://huggingface.co/datasets/wzsg/polymarket-orderfilled-v1) and [V2 mirror](https://huggingface.co/datasets/wzsg/polymarket-orderfilled-v2) are the best bulk fill starting points found. [SII-WANGZJ](https://huggingface.co/datasets/SII-WANGZJ/Polymarket_data) has monolithic derived files; its README sizes disagree with the newer live tree, so downloaded/listed bytes win. [Kaggle](https://www.kaggle.com/datasets/ethanbensadoun/polymarket-dataset) traces to warproxxx/Goldsky and adds no listed lifecycle archive. [Rocklabs](https://rocklabs.io/data) advertises precisely the missing data but requires contacting it for access.

## Point-in-time accounting and implementation

`scripts/ledger.py` implements a conservative ledger over **audited, coalesced transaction/account/condition cash and token deltas**. Raw fill decoding is separate. V1 BUY fees reduce received shares; V2 BUY fees increase collateral paid. Decimal arithmetic preserves amounts. Splits, merges, redemptions, multi-token payout vectors, explicit transfer basis and audited neg-risk conversion allocations are supported in the normalized representation. Missing opening state, unaudited inputs, duplicate transaction-condition entries, unsupported events, missing transfer/conversion basis, and negative inventory raise errors. No proxy-to-owner consolidation is inferred.

Expert P&L includes only conditions with verified payout finality strictly before signal time. Remaining resolved shares are valued at the payout vector; subsequent redemption replaces entitlement with cash without adding profit again. This **resolved-market accrual definition** differs from a platform's realized trading profit on still-open markets, rebates, reward income and other accounting atoms. A valid leaderboard reconciliation must bridge these definitions at the same as-of time. Same-provider agreement does not do that.

**Not implemented/validated end-to-end:** a complete chain-log-to-normalized-ledger adapter (including pre-CLOB FPMM, all transfers, proxy migrations, conversions, external basis, fee/refund allocations and finality), a complete causal wallet universe, and historical orderbook acquisition. These are required upstream stages, not optional statistical robustness. The engine must not be described as a validated production P&L engine.

`scripts/panel.py` supplies causal aggregation for equal, P&L, size, P&L×size, shrunk ROI and shrunk hit-rate weights. Primary weights use positive past category P&L × gross outcome shares; each wallet contributes YES/(YES+NO) holdings. `total_expert_exposure` is **gross outcome shares**, not dollars; dollars need both current outcome prices. Fixed blend is 50/50. The gate is USD10000 past category P&L, >=10 previous resolved markets, >=3 qualified holders. No signal is invented when that gate fails. Market-maker rules are preregistered but cannot be populated from the incomplete history; filled two-sided activity is only a behavioral proxy, not proof of quoting intent.

Finality-aligned horizons are 24h/6h/1h, plus open+6h. Exact eventual-finality time is an ex-post evaluation clock, not a deployable signal known in advance. At each resulting timestamp, features themselves must be available causally. Operational quote eligibility requires a verified two-sided quote no more than five minutes old; this added conservative implementation gate is documented here and produced no evaluated test. Separate binary CTF conditions represent neg-risk outcomes; inference clusters related outcomes under event ID.

## Registered inference, robustness and nulls

The primary endpoint is paired event-level Brier improvement, market loss minus P&L×size expert loss, at 24h. Training ends 2025-01-01, followed by 24h embargo; holdout runs through 2026-09-01. Resolved histories may expand causally through holdout. No tuning has occurred.

The **83-member family** contains 27 category/all Brier/log-loss/blend tests, 6 alternative-horizon tests, sports advantage, outcome divergence, max-statistic drift at 1/6/24h, 5 alternate weights, 5 alternate thresholds, 8 robustness variants, 18 persistence tests and 10 matched-wallet placebos plus one economic test. `results.csv` has one row for each. Missing tests contribute p=1 internally to whole-family BH, while displayed p/q remain missing. There are no empirical p-values or confidence intervals. The reproducible utilities implement 10000 paired bootstrap draws, joint max-statistic sign-flip inference, full-family BH, and a conservative 80%-power MDE formula. Synthetic unit tests exercise these routines; they are not research resamples or evidence.

**MDE for the blocked tests: undefined**, because no eligible event-cluster variance or sample exists. **Placebo false-positive rate: undefined (0/10 placebos evaluated)**. No null hypothesis was empirically accepted or rejected. Threshold sweeps, minimum-history changes, overall-vs-category P&L, excluding market makers/largest wallets, liquidity strata, rank persistence and decile spreads remain blocked. Their full empirical dispatch and matched-placebo construction remain to be connected to complete upstream data; existing inference utilities do not imply these analyses ran.

## Economic sanity and whale extras

There is no observed gross forecast edge to compare with costs. Historical spread, depth, version-correct fee schedules and realistic USD100 size are unavailable in the acquired sample. **n=0, mean net edge and bootstrap interval unavailable.** We cannot say an edge survives costs, nor that it dies inside the spread. Last-trade prices are never represented as historical midpoints.

All five extras are explicitly exploratory and not estimated: expert net buying vs later drift, first trades around dated news, lockstep address clusters, specialists vs generalists, and profit share captured by the top 0.1%/1%. No names or insider accusations are inferred. `exploratory_results.csv` records each unavailable claim. Volume concentration is not substituted for P&L concentration.

## Metadata and sample limitations

The brief described the shared Gamma crawl as DONE. At inspection it was actively growing with a non-DONE cursor. A local byte snapshot retained **348,374 distinct markets** (696,826 tokens) before a truncated gzip tail; malformed complete lines: 0. Snapshot SHA256: `b46fdf3a1ca010e9fa3f005edde7f42555b3f44f1588553f89f2bdcc32128b0d`. **105,723/126,752 fill rows** match metadata, but only **551/2636 outcome tokens** match. The final-volume >=USD10000 source filter creates survivorship/selection bias and cannot define the confirmation sample. Heuristic categories are audit labels only, not validated historical tags. Gamma `closedTime`, scheduled end and terminal prices do not prove on-chain payout-finality time.

## Best figures and frontend contract

- `figures/family_overview.png`: real audit size and blocked family status.
- `figures/ledger_completeness.png`: measured exchange-taker and negative inventory diagnostics.
- `figures/reliability_by_category.png`, `brier_improvement_by_category.png`, `skill_persistence_deciles.png`, `pnl_concentration.png`: explicit unavailable panels, **not empirical curves**.
- `figures/case_study_1.png` through `case_study_3.png`: three most-observed distinct mapped markets, showing the highest-count outcome token in each. Real executed prices only; no consensus. Gamma close, where shown, is clearly labelled unverified, not resolution.

`findings.json` uses the requested list schema, including rejected claims. `verdict=partial` on untested hypotheses reflects the schema's lack of a blocked enum; each title/result/caveat states untested. `verdict=rejected` applies to **fill-only accounting sufficiency**, not to expert accuracy. `expert_panel.schema.json` tells the frontend why the valid typed panel is empty. Never render a missing result as 0% accuracy or zero Brier improvement.

## Prior art and novelty

[Prediction Market Accuracy: Crowd Wisdom or Informed Minority?](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6617059), revised 2026-06-25, reports persistent skill concentrated among a small minority. This run read the public abstract, not the full paper, and does not independently reproduce it. [Hashdive](https://hashdive.com/), [PolyTrack](https://www.polytrackhq.app/) and [Prediction Pro](https://predictionpro.app/) already advertise historical-wallet scores, whale following or profitable-wallet weighted signals; marketing claims are not efficacy evidence. [Fill-side non-retail research](https://arxiv.org/abs/2605.11640) cautions against attributing wallet-level quote behavior from fills. `prior_art.json` records read scope and dates.

The concept is known. A complete category-specific, causal, multiplicity-controlled consensus evaluation could add evidence, but **this run makes no novel predictive claim**. Its useful result is identifying concrete current access changes and measuring the accounting failure of an attractive shortcut.

## Reproduce and validation

All files stay in this directory. Container workflow: `docker build -t polymarket-experts .` then `docker run --rm -v "$PWD:/work" polymarket-experts`. Docker daemon checks timed out; the Docker build attempt is recorded in `data/build.log`. The pre-existing local `.venv` was used; only venv packages were added, no host system packages.

Offline reproduction from cached public data:

```sh
.venv/bin/python scripts/run.py
.venv/bin/python -m pytest -q tests
.venv/bin/ruff check scripts tests
.venv/bin/python -m compileall -q scripts tests
```

Network acquisition scripts: `fetch_bulk.py` (pinned bounded shard download), `probe_routes.py`, `probe_archives.py`, `probe_followup.py`, `probe_final.py`, `probe_contracts.py`; each uses cached serial read-only access. `register.py` refuses to overwrite preregistration. `data/source_manifest.json` hashes local source files; per-request access records retain source URLs, timestamps, status and response hash. `data/environment.json` records installed package versions. The run does not require or use paid data.

Verification: **18 tests passed**, lint and compilation passed. The container build was attempted but blocked by the unavailable daemon. Artifact schema/path checks passed; all nine PNGs were visually inspected. Detailed outcomes are in `data/validation.json` and test/lint/build logs. Receipt comparisons and three live-wallet cross-endpoint comparisons are included in tests, with their limited scope explicit. Code and report were prepared with AI assistance.

## Remaining work to complete the empirical brief

Acquire an inception/opening-state-complete ledger for a causally chosen market cohort using the now-verified public V2/RPC routes; implement and independently reconcile full lifecycle/fee accounting; establish on-chain finality; acquire matching historical bid/ask depth; populate the panel; then implement and run all 83 registered specifications with 10000 resamples, whole-family BH and matched placebos. This is substantial unfinished work, not a request for account access. No modification outside this folder or paid/authenticated route is needed for the artifacts delivered here.
