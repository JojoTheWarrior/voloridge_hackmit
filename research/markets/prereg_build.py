"""Builds prereg.json. Written and frozen BEFORE any signal-vs-target statistic was computed (only data-availability probes had been run)."""
import json, datetime
META = {
 "frozen_at": datetime.datetime.now().isoformat(timespec="seconds"),
 "prior_exploration_disclosed": [
  "scout round 2 (another agent) already looked at Yunnan reservoir area vs aluminium next-3-month return: r=0.06, n=144 (null). Counted as 1 prior look; our version is still run as specified below.",
  "wardamage round 1 looked at a Gulf flare index vs Brent/TTF in levels and 5-day diffs over Jan-Jul 2026 (perm p=0.20 Brent). Counted as 2 prior looks.",
  "scout reports Kariba satellite area does not track level (steep lake) -> Kariba excluded a priori, Itezhi-Tezhi used for Zambia.",
  "scout reports Western-Interconnection monthly hydro vs fossil generation anomalies slope -0.85, R2=0.64, n=89 -> our P5/P6 are replications of a known link, the new leg is the price/market leg."],
 "statistic": "Pearson r between signal x_t and target y_{t+L+k}; test statistic = max over the pre-registered lags k of |r_k| (two-sided). A test is 'supported' only if BH q<=0.05 AND the sign at the best lag equals expected_sign (expected_sign 0 = no directional prior).",
 "null": "10,000 surrogates of the signal: random permutation of contiguous blocks (block=6 months / 8 weeks) followed by a random circular shift; the max-|r|-over-lags is recomputed for each surrogate; p=(1+#{null>=obs})/(1+10000). Secondary: exact circular-shift p over all admissible shifts (resolution 1/n, reported, not used for BH).",
 "multiplicity": "Benjamini-Hochberg across ALL tests in 'family' (both tiers) on the max-stat p. Placebos/controls/exploratory are outside the family and reported separately.",
 "oos": "Chronological split of each test's overlapping sample: first 60% train, last 40% test. Lag k* and sign are chosen on train; report r_test at k* and its one-sided block-permutation p (10,000).",
 "frequency_and_timing": {
  "monthly_satellite": "GWW area: monthly median per reservoir. Value for month m is assumed knowable at the END of month m+1 (L=1). Market-tier lags k in {1,2,3}: target month = m+1+k.",
  "monthly_ground_truth": "ONS EAR / EIA-930 are published within days: L=0, k in {1,2,3}.",
  "weekly_flares_glofas": "Signal weeks end THURSDAY (VIIRS night data available ~1 day later, i.e. before Friday close); returns are Friday-close to Friday-close; L=0, k in {1,2,3,4} -> first target week starts at the Friday close after the signal week ended.",
  "weekly_nve": "NVE publishes week w filling on Wednesday of w+1 -> L=1, k in {1,2,3,4}.",
  "physical_link_tier": "Targets are non-traded physical/administrative quantities; purpose is nowcast validity, so L=0 and k in {0,1,2} (k in {0..4} weekly)."},
 "transforms": {
  "z": "per-reservoir anomaly = monthly value minus EXPANDING month-of-year mean (>=min_years prior values of that calendar month), divided by expanding std of past anomalies; composite = mean of member z. No full-sample statistics enter the signal.",
  "dz3": "z_m - z_{m-3}",
  "QC": "drop single-image areas < 0.4 x reservoir median (partial/cloudy scenes); monthly median; linear interpolation of gaps <= 2 months.",
  "flare_index": "night VIIRS S-NPP FRP summed over persistent flare cells (0.02 deg cells lit on >=5% of nights 2012-2026; geography only) per day; weekly value = mean of the 3 largest daily sums in the Fri-Thu week (clear-sky proxy); log; minus expanding week-of-year mean (>=3 yrs); signal = 2-week change.",
  "rhine_stress": "weekly mean GloFAS discharge Q at Kaub; stress = max(0, log(q10/Q)) with q10 = expanding 10th percentile of daily Q (>=10 yrs); signal = 1-week change in stress.",
  "nve": "Norway total filling (% of capacity) minus expanding week-of-year median (>=5 yrs); signal = 1-week change.",
  "targets": "log returns from month-end / Friday closes. Equities are in excess of the stated local index (difference of log returns). CMO: log(1+CMO SE/CO R$/MWh) monthly mean. Generation targets: deseasonalised (full-sample month-of-year mean; target side only) share or MWh anomaly. Physical-link monthly tests use 3-month changes on both sides (dz3 vs d3 target)."},
 "controls": {
  "partial": "re-run every market-tier test with the target residualised on contemporaneous factor returns [^SPGSCI, DX-Y.NYB] (+ 000001.SS for aluminium/copper, + HG=F for USDZMW); report r_partial, p_partial.",
  "placebo_reservoirs": "Argyle (AUS), Guri (VEN), Volta (GHA), Toktogul (KGZ): same transforms, same targets, same procedure for every reservoir market-tier test. Expect ~5% with p<0.05.",
  "year_shuffle": "signal with whole calendar years permuted (10,000), monthly tests; p_yearshuffle.",
  "flare_placebo": "Algeria (Hassi Messaoud/Hassi R'Mel) flare index vs Brent; Rhine placebos: Danube at Budapest, Loire at Saumur vs BAS.DE."},
 "economic": "Only for BH survivors in the market tier: position = expected_sign*sign(x) (flat if |z|<0.5 for z signals), held one period at the train-selected lag, 10 bps per unit turnover, test segment only; mean return with 10,000-draw stationary-bootstrap CI and n position changes.",
 "not_tested_and_why": {"TROPOMI NO2 / S2 plumes": "only Apr-Sep 2025 (6 months) exists -> no time series long enough", "Kariba area": "known-bad physical proxy (scout)", "Eurobond/sovereign spreads, Brent-Dubai, PLD (CCEE), TTF/CAISO prices, coal barge rates": "no keyless series found or not attempted; ONS CMO used as the PLD proxy (PLD = CMO with floor/cap)", "Iraq/Libya/Nigeria FX": "pegged or managed currencies"}}
RES = {"yunnan_area": {"gww": {"Xiaowan": "89601", "Nuozhadu": "90084"}, "start": "2015-01", "min_years": 3, "note": "both reservoirs fully impounded by 2014"},
 "brazil_seco_area": {"gww": {"Furnas": "91951", "SerraDaMesa": "91687", "TresMarias": "91678", "Emborcacao": "90065", "Itumbiara": "90348", "NovaPonte": "90286", "AguaVermelha": "90540", "IlhaSolteira": "91947", "Marimbondo": "90312"}, "start": "2000-01", "min_years": 5},
 "zambia_itt_area": {"gww": {"ItezhiTezhi": "90229"}, "start": "2000-01", "min_years": 5},
 "uswest_area": {"gww": {"Shasta": "89304", "Oroville": "88197", "NewMelones": "87879", "DonPedro": "87987", "Mead": "90554", "Powell": "89454"}, "start": "2000-01", "min_years": 5},
 "placebo_argyle": {"gww": {"Argyle": "90627"}, "start": "2000-01", "min_years": 5}, "placebo_guri": {"gww": {"Guri": "92390"}, "start": "2000-01", "min_years": 5},
 "placebo_volta": {"gww": {"Volta": "92429"}, "start": "2000-01", "min_years": 5}, "placebo_toktogul": {"gww": {"Toktogul": "89729"}, "start": "2000-01", "min_years": 5}}
F = []
def add(id, signal, transform, target, sign, tier, freq, L, lags, mech):
    F.append(dict(id=id, signal=signal, transform=transform, target=target, expected_sign=sign, tier=tier, freq=freq, latency=L, lags=lags, mechanism=mech))
M = [1, 2, 3]
mk = [("Y1", "yunnan_area", "SHFE_AL", -1, "Low Lancang storage -> Yunnan hydro deficit -> smelter curtailment (Yunnan ~12% of China Al capacity) -> tighter metal -> SHFE aluminium up"),
 ("Y2", "yunnan_area", "ALI=F", -1, "same, COMEX/LME-linked aluminium future"),
 ("Y3", "yunnan_area", "000807.SZ-000001.SS", +1, "Yunnan Aluminium loses volume when curtailed (volume loss assumed to dominate price gain)"),
 ("Y4", "yunnan_area", "AA-^GSPC", -1, "non-Chinese producer gains from Chinese supply loss"),
 ("Y5", "yunnan_area", "NHY.OL-OSEBX.OL", -1, "non-Chinese producer gains from Chinese supply loss"),
 ("B1", "brazil_seco_area", "AXIA3.SA-^BVSP", +1, "Eletrobras/Axia is hydro-long: low storage -> GSF deficit, buys at high PLD"),
 ("B2", "brazil_seco_area", "CMIG4.SA-^BVSP", +1, "hydro-heavy integrated utility, same GSF exposure"),
 ("B3", "brazil_seco_area", "EGIE3.SA-^BVSP", +1, "hydro-heavy generator"),
 ("B4", "brazil_seco_area", "ENEV3.SA-^BVSP", -1, "gas-fired generator dispatched more when storage is low"),
 ("B5", "brazil_seco_area", "ENGI11.SA-^BVSP", +1, "distributor: low storage -> costly thermal energy / rationing risk"),
 ("Z1", "zambia_itt_area", "HG=F", -1, "Kafue hydro deficit -> load-shedding at Copperbelt mines -> less copper (Zambia ~3% of world supply; weak prior)"),
 ("Z2", "zambia_itt_area", "FM.TO-^GSPTSE", +1, "First Quantum's Kansanshi/Sentinel depend on ZESCO power"),
 ("Z3", "zambia_itt_area", "USDZMW", -1, "drought -> power imports, lost copper exports, food imports -> weaker kwacha (USDZMW up)"),
 ("U1", "uswest_area", "NG=F", -1, "low western hydro -> more gas burn (known at interconnection scale) -> Henry Hub up (weak prior: West is small vs US gas market)"),
 ("U2", "uswest_area", "PCG-XLU", +1, "PG&E owns hydro; drought also raises wildfire liability"),
 ("U3", "uswest_area", "EIX-XLU", +1, "drought -> wildfire liability, procurement cost")]
for i, s, t, sg, m in mk:
    for tr in ("z", "dz3"): add(f"{i}_{tr}", s, tr, t, sg, "market", "M", 1, M, m)
for i, t, sg in [("G1", "AXIA3.SA-^BVSP", +1), ("G2", "ENEV3.SA-^BVSP", -1), ("G3", "CMIG4.SA-^BVSP", +1)]:
    for tr in ("z", "dz3"): add(f"{i}_{tr}", "brazil_ear_seco", tr, t, sg, "market", "M", 0, M, "UPPER BOUND: official ONS stored-energy (what a perfect satellite would measure) vs the same equities")
P = [0, 1, 2]
add("P1", "brazil_seco_area", "dz3", "d3_EAR_SECO_anom", +1, "physical", "M", 0, P, "validation: satellite area composite should track official stored energy")
add("P2", "brazil_seco_area", "dz3", "d3_logCMO_SE", -1, "physical", "M", 0, P, "storage down -> water value up -> marginal operating cost (basis of PLD spot price) up")
add("P3", "brazil_seco_area", "dz3", "d3_thermal_share_SIN", -1, "physical", "M", 0, P, "storage down -> thermal dispatch up")
add("P4", "brazil_ear_seco", "dz3", "d3_logCMO_SE", -1, "physical", "M", 0, P, "UPPER BOUND for P2 with official storage")
add("P5", "uswest_area", "dz3", "d3_WECC_hydro_anom", +1, "physical", "M", 0, P, "reservoir area -> western hydro generation (EIA-930)")
add("P6", "uswest_area", "dz3", "d3_WECC_fossil_anom", -1, "physical", "M", 0, P, "reservoir area -> western gas+coal generation fills the gap")
add("P7", "wecc_hydro_anom", "dz3", "NG=F", -1, "market", "M", 0, M, "price leg of the known hydro->gas-burn link, using ground-truth EIA-930 hydro anomaly as the signal (upper bound for the satellite)")
add("P8", "nve_fill", "d1", "dlog_NordPool_SYS", -1, "physical", "W", 0, [0, 1, 2, 3, 4], "hydro balance is the textbook driver of Nordic system price (ground-truth signal, not satellite)")
add("N1", "nve_fill", "d1", "NHY.OL-OSEBX.OL", 0, "market", "W", 1, [1, 2, 3, 4], "Hydro is both a hydropower seller and a smelter power buyer: sign ambiguous")
W = [1, 2, 3, 4]
add("F1", "libya_flare", "d2", "BZ=F", -1, "market", "W", 0, W, "flaring collapse = field shut-in (blockades 2013-14, 2020, 2022, 2024) -> supply loss -> Brent up")
add("F2", "libya_flare", "d2", "d_BZ-CL_spread", -1, "market", "W", 0, W, "Libyan light-sweet loss tightens Brent-linked grades vs WTI")
add("F3", "libya_flare", "d2", "TANKERS(FRO,DHT)-^GSPC", 0, "market", "W", 0, W, "fewer Med cargoes vs longer-haul replacement: ambiguous")
add("F4", "basra_flare", "d2", "BZ=F", -1, "market", "W", 0, W, "Basra flaring tracks southern Iraq output (~3-4 mb/d)")
add("F5", "basra_flare", "d2", "TANKERS(FRO,DHT)-^GSPC", 0, "market", "W", 0, W, "Gulf export disruption: fewer cargoes vs rate spike, ambiguous")
add("R1", "rhine_stress", "d1", "BAS.DE-^GDAXI", -1, "market", "W", 0, W, "Kaub low water -> barge light-loading -> BASF Ludwigshafen logistics cost/curtailment (2018: ~EUR250m)")
EVENTS = {"yunnan_curtailments": {"2021-05": "power rationing, smelters cut from mid-May 2021", "2021-09": "further cuts (energy dual-control + hydro)", "2022-09": "10% then 20-30% cuts", "2023-02": "cuts deepened to ~40% (approx. 0.65-0.8 Mt)", "2023-11": "dry-season cuts 9-40% at four smelters (~1.15 Mt)"},
 "libya": {"2013-07": "port/field blockades begin (to mid-2014)", "2020-01-18": "LNA blockade (to 2020-09-18)", "2022-04-17": "Sharara/El Feel + ports shut", "2024-08-26": "central-bank dispute shut-in"},
 "gulf": {"2019-09-14": "Abqaiq attack", "2026-03-04": "Hormuz closure"}}
json.dump({"meta": META, "reservoir_signals": RES, "family": F, "family_size": len(F), "case_study_events": EVENTS}, open("prereg.json", "w"), indent=1, ensure_ascii=False)
print("family size", len(F))
