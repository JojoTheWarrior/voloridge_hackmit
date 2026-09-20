"""Write the immutable analysis plan before any statistical or unit test."""

import datetime
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
cats = [
    "NBA",
    "NFL",
    "soccer",
    "other_sports",
    "politics",
    "crypto_price",
    "weather",
    "culture",
]
tests = []


def add(name, signal, target, transform, sign, mechanism, **kw):
    tests.append(
        dict(
            id=name,
            signal=signal,
            target=target,
            transform=transform,
            horizons_hours=[24],
            expected_sign=sign,
            mechanism=mechanism,
            primary_specification=True,
            **kw,
        )
    )


for cat in ["all"] + cats:
    for metric in ["brier", "logloss", "blend_brier"]:
        add(
            f"{metric}_{cat}",
            "category realised-PnL times open-share exposure consensus, threshold USD10000, >=10 prior resolved markets",
            metric + " market loss minus expert loss",
            "paired event-cluster mean loss difference",
            "positive",
            "Past category skill reduces crowd forecast errors",
            category=cat,
        )
for h in [6, 1, "open_plus_6"]:
    for m in ["brier", "logloss"]:
        add(
            f"{m}_h{h}",
            "same primary consensus",
            m + " improvement",
            "paired loss difference",
            "positive",
            "Expert information varies over lifecycle",
            category="all",
            evaluation_horizon=h,
        )
add(
    "sports_advantage",
    "primary consensus",
    "sports minus non-sports Brier improvement",
    "difference in means",
    "positive",
    "Emotional sports participation reduces crowd accuracy",
    category="all",
)
add(
    "outcome_divergence",
    "expert probability minus market mid",
    "resolution outcome",
    "logistic outcome ~ logit(mid) + divergence; held-out incremental log loss",
    "positive",
    "Expert divergence contains incremental information",
    category="all",
)
add(
    "drift_max_horizon",
    "expert probability minus market mid",
    "subsequent mid-price change",
    "signed slope; max absolute studentized statistic across 1,6,24h",
    "positive",
    "Prices incorporate expert information later",
    category="all",
    search_horizons_hours=[1, 6, 24],
)
for weighting in ["equal", "pnl", "size", "roi_shrunk", "hit_rate_shrunk"]:
    add(
        "weight_" + weighting,
        weighting + " weighted qualified wallet consensus",
        "Brier improvement",
        "paired loss difference",
        "positive",
        "Different aggregation of past skill",
        category="all",
    )
for threshold in ["1000", "5000", "50000", "top25", "top10percent"]:
    add(
        "threshold_" + threshold,
        "expert qualification " + threshold,
        "Brier improvement",
        "paired loss difference",
        "positive",
        "Skill signal should not depend on one threshold",
        category="all",
    )
for variant in [
    "minpast5",
    "minpast20",
    "overall_pnl",
    "exclude_mm",
    "exclude_top3",
    "liquidity_low",
    "liquidity_mid",
    "liquidity_high",
]:
    add(
        "robust_" + variant,
        variant + " primary consensus",
        "Brier improvement",
        "paired loss difference",
        "positive",
        "Expert effect should survive composition controls",
        category="all",
    )
for cat in ["all"] + cats:
    for metric in ["spearman", "decile_spread"]:
        add(
            f"persistence_{metric}_{cat}",
            "past resolved category PnL",
            "future resolved category PnL",
            metric,
            "positive",
            "Persistent skill rather than hindsight selection",
            category=cat,
        )
for i in range(10):
    add(
        f"placebo_{i:02d}",
        "random wallets matched by early-period exposure/activity deciles; fixed seed "
        + str(4100 + i),
        "Brier improvement",
        "paired loss difference",
        "zero",
        "Matched random wallets should not mimic skill",
        category="all",
    )
add(
    "economic_primary",
    "sign of divergence at 24h",
    "USD100 quote-depth-adjusted resolution payoff less spread and fees",
    "mean net payoff per share, event bootstrap",
    "positive",
    "Forecast improvement must clear observed costs",
    category="all",
)
plan = {
    "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "version": 1,
    "status": "registered_before_data_analysis_or_tests",
    "primary_test": "brier_all",
    "family_size": len(tests),
    "family": tests,
    "time_split": {
        "train_end": "2025-01-01T00:00:00Z",
        "test_start": "2025-01-01T00:00:00Z",
        "test_end": "2026-09-01T00:00:00Z",
        "embargo_hours": 24,
        "rule": "Only events resolved in holdout; prior market resolution strictly before signal timestamp. No tuning on holdout. Warmup starts at contract inception; prior categories may update causally in holdout.",
    },
    "selection": "All mapped resolved binary outcomes with complete lifecycle history, timestamped payout finality and contemporaneous two-sided quotes; no filtering on final volume or today leaderboards. Market event clusters are resampling units. Exclude ambiguous mappings and insufficient history.",
    "signal": {
        "primary_horizon_hours": 24,
        "other_horizons_hours": [6, 1],
        "open_plus_hours": 6,
        "threshold_usd": 10000,
        "min_past_markets": 10,
        "min_experts": 3,
        "wallet_view": "YES shares / (YES+NO shares), nonnegative audited balances; per-wallet total dollar exposure from contemporaneous mid",
        "weights": "positive resolved category PnL times gross outcome share exposure",
        "blend": "0.5 market + 0.5 expert; fixed",
        "shrinkage": "ROI numerator / (cost+1000); hit rate (wins+5)/(resolved+10)",
        "top_selection": "positive PnL, min history, sorted past PnL, among causally observed active category wallets",
        "probability_clip": 0.001,
        "market_maker": "prior 30d buy and sell each >=25% gross volume, turnover/gross end exposure >10 and >=100 fills; inventory AR1 <0.8 from prior daily series; no future classification",
        "largest_wallet_exclusion": "three largest past gross-exposure wallets at each timestamp",
        "liquidity_buckets": "USD100 executable depth tertiles fixed from train only",
    },
    "inference": {
        "resamples": 10000,
        "seed": 20260920,
        "alpha": 0.05,
        "multiple_testing": "BH over entire registered family; unestimable tests conservatively p=1 internally, displayed p/q null and status blocked",
        "bootstrap": "paired cluster bootstrap by event; two-sided centered null; percentile 95% CI",
        "lags": "max-statistic null over registered horizons, no picking best uncorrected lag",
        "minimum_n_events": 50,
        "minimum_detectable_effect": "(z(1-alpha/(2*family_size))+z(0.8))*cluster SD/sqrt(n); unavailable without usable clusters",
        "placebo_fpr": "unadjusted p<.05 fraction and BH survivor fraction over 10 evaluable matched placebos; NA if blocked",
    },
    "hard_validity_gates": [
        "complete wallet discovery independent of future leaderboard rank",
        "all fills, ERC1155 transfers, splits, merges, redemptions and neg-risk conversions from inception or audited opening state",
        "deduplicate maker/taker settlement roles by transaction; do not double-count exchange legs",
        "contract-version-specific fee units and fee recipient cash flows",
        "on-chain payout finality timestamps, not market scheduled end or mutable closedTime",
        "historical bid, ask, depth and fee schedule at signal time",
        "unit tests and independent same-definition as-of PnL reconciliation",
    ],
    "blocked_policy": "Preserve every registered test as blocked in results.csv if required data unavailable. Never replace missing observations with synthetic data, zero effects, or current snapshots. Empty typed panel is permitted only with explicit blocked status; this is NOT a statistical null.",
    "exploratory": [
        "net expert buying predicts mid changes at 1/6/24h",
        "dated news: earliest large trades vs past PnL",
        "lockstep pseudonymous address clusters",
        "specialists vs generalists",
        "resolved net profit concentration top 0.1% and 1% by category",
        "bulk schema and ledger-completeness audits; these do not establish skill",
    ],
    "public_readonly": True,
    "no_identities": True,
}
p = ROOT / "prereg.json"
if p.exists():
    raise SystemExit("Refusing to overwrite preregistration")
p.write_text(json.dumps(plan, indent=2) + "\n")
h = hashlib.sha256(p.read_bytes()).hexdigest()
(ROOT / "prereg.sha256").write_text(h + "  prereg.json\n")
print("registered", len(tests), "tests", h)
