"""Publish honest blocked inference plus measured data-quality diagnostics."""

import hashlib
import json
import os
import textwrap
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault(
    "MPLCONFIGDIR", str(Path(__file__).resolve().parents[1] / ".cache/matplotlib")
)
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from access import ROOT
from panel import empty_panel
from inference import bh

BG = "#101928"
FG = "#e6edf6"
MUTED = "#a5b6cb"
TEAL = "#47c9bb"
AMBER = "#ffc66d"


def style():
    plt.rcParams.update(
        {
            "figure.facecolor": BG,
            "axes.facecolor": BG,
            "savefig.facecolor": BG,
            "text.color": FG,
            "axes.labelcolor": MUTED,
            "xtick.color": MUTED,
            "ytick.color": MUTED,
            "axes.edgecolor": "#3a4a60",
            "font.family": "DejaVu Sans",
            "font.size": 11,
            "axes.titleweight": "bold",
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )


def save(fig, name):
    fig.savefig(ROOT / "figures" / name, dpi=180, bbox_inches="tight")
    plt.close(fig)


def notice(name, title, lines):
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.axis("off")
    ax.text(0, 1, title, fontsize=24, weight="bold", va="top", transform=ax.transAxes)
    ax.text(
        0,
        0.77,
        "NOT ESTIMABLE FROM THE VERIFIED DATA",
        color=AMBER,
        fontsize=14,
        weight="bold",
        transform=ax.transAxes,
    )
    for i, line in enumerate(lines):
        ax.text(
            0,
            0.56 - i * 0.15,
            textwrap.fill(line, 100),
            fontsize=12,
            transform=ax.transAxes,
            va="top",
            color=MUTED,
        )
    save(fig, name)


def access_table():
    return [
        [
            "Hugging Face wzsg V1",
            "200; 8 parquet shards downloaded",
            "1,206,105,187 rows; 2022-11-21 to 2026-04-28; 71.06 GB, 289 files (publisher manifest)",
            "Monthly immutable parquet; anonymous; no rate quota found",
            "Fills only; excludes pre-CLOB AMM; maker/taker aggregate legs; no transfers/lifecycle/quotes",
        ],
        [
            "Hugging Face wzsg V2",
            "200 metadata; not downloaded",
            "575,630,861 rows; through 2026-08-03; 33.62 GB (retrieved card)",
            "Monthly parquet; different ABI; no rate quota found",
            "V2 collateral/fee semantics differ; no lifecycle or historical quotes",
        ],
        [
            "Hugging Face SII-WANGZJ",
            "200 README and file listing",
            "Raw file 110.30 GB; README older 689M-row snapshot through 2026-03-04",
            "Monolithic parquet; file listing newer than card; no rate quota found",
            "Derived YES-normalized user data unsafe as original inventory; no lifecycle; stale card sizes",
        ],
        [
            "Kaggle ethanbensadoun/polymarket-dataset",
            "200 public metadata and file list",
            "39.48 GB raw orderFilled_complete.csv; updated 2026-04-07",
            "File download route not exercised; unknown data time boundaries/rate quota",
            "warproxxx/Goldsky-derived; no additional lifecycle or depth files listed; no need to download redundant CSV",
        ],
        [
            "GitHub warproxxx/poly_data",
            "200 README",
            "V2 collector; old v1-final tag",
            "Current HyperSync backend requires token since 2025-11-03",
            "Code rather than keyless mirror; credentials prohibited",
        ],
        [
            "Rocklabs",
            "200 public README/catalog",
            "Advertises 1.5B+ chain events and 438M+ lifecycle rows",
            "Research access by contacting provider; no public bulk URL in catalog",
            "Not anonymously downloadable from evaluated catalog; no contact/account created",
        ],
        [
            "Data API v1 trades",
            "200; offset=10001 -> 400",
            "Observed error: max historical offset 10000",
            "200 req/10s documented; bounded probes only",
            "Offset ceiling; default taker-only view must not substitute for full ledger",
        ],
        [
            "Data API v1 activity",
            "200; offset=10001 -> 400",
            "Observed error: max historical offset 5000",
            "General 1000 req/10s; wallet-anchored",
            "Includes lifecycle types but bounded offset; no full history fetched",
        ],
        [
            "Data API v1 positions / closed-positions",
            "200 for 3 wallets",
            "Current/closed snapshots; 5 rows per probe",
            "150 req/10s each documented; full page cap not live-tested",
            "Current state is not historical state; window filtering is not an as-of reconstruction",
        ],
        [
            "Data API holders / leaderboards",
            "200",
            "Current top holders and current ranks; 3 validation wallets",
            "Snapshot-oriented; no historical panel; general Data API quota",
            "Used for endpoint validation only; never discover historical experts from current winners",
        ],
        [
            "Data API V2 trades/activity",
            "200, second cursor pages verified",
            "user + start=1 requests full history; omitted start defaults 3y; max page 1000",
            "Keyset cursor; trades 300/10s, activity 200/10s; retain user on activity resume",
            "Promising wallet history route, but universe-wide complete ledger not fetched or independently reconciled",
        ],
        [
            "Data API V2 positions/PnL/leaderboard",
            "200; 3 same-wallet PnL checks",
            "PnL atoms, current position economics; all-time board is realized-only",
            "Positions max page 1000, 200 req/10s; PnL is aggregated series",
            "Position start/end filters last-event time, not historic holdings; same-provider agreement is not independent validation",
        ],
        [
            "Gamma local cache + API",
            "200 probe; local frozen file has truncated gzip tail",
            "348374 complete market records retained; >=USD10k source filter; actively growing sibling",
            "Existing keyset crawler read only; /markets 300 req/10s",
            "Not DONE at inspection; partial snapshot; final-volume selection unsuitable for confirmatory universe",
        ],
        [
            "CLOB prices-history",
            "200; oldest-market probe returned empty history",
            "Depth varies by token; one old-market probe is not a universal depth claim",
            "1000 req/10s; interval/fidelity; no bid/ask depth in history",
            "No price substituted for midpoint; no historical size/spread acquired",
        ],
        [
            "Data API V2 prices-history (docs)",
            "Public OpenAPI evaluated; endpoint not probed",
            "3h/12h permanent since 2022; fine grains expire; explicit windows <=15d",
            "max page 10000; cursor; as_of mode; 200 req/10s",
            "Terminal synthetic settlement point is not an ordinary price observation; no full book depth",
        ],
        [
            "Goldsky orderbook/positions/activity/PnL subgraphs",
            "All four HTTP 429 with ENDPOINT_DEPRECATED",
            "Paused after 2026-04-28 V2 migration",
            "Bounded exponential retries performed; not ordinary throttling",
            "Provider explicitly says stale/incorrect; do not crawl",
        ],
        [
            "Goldsky Edge / Turbo",
            "Edge public probe -> HTTP 402; docs require key",
            "Activity, balances, positions advertised",
            "API key or payment; Turbo requires account",
            "Blocked by no credentials/payments/accounts rule",
        ],
        [
            "Polygon PublicNode",
            "200 head/recent logs; old logs returned JSON-RPC error",
            "Recent CTF logs available; 2022 sample pruned",
            "Small 11-block and 101-block probes; quota not load-tested",
            "Cannot infer archive support from HTTP 200; no historical result",
        ],
        [
            "Polygon dRPC",
            "200; 57 old CTF logs; 3 receipts; 66 standard + 147 neg-risk logs",
            "Historical sample from block 35896869 available",
            "Serial small ranges; 1001-block topic query failed, 101-block retry succeeded; exact cap unconfirmed",
            "Potential public full ledger route; entire backfill and reconciliation remain unperformed",
        ],
        [
            "polygon-rpc.com",
            "401",
            "No usable keyless response",
            "No authenticated retry",
            "Access blocked",
        ],
        [
            "PMXT archive",
            "Network failure after bounded retries",
            "Web index advertises hourly orderbooks; no file acquired",
            "Public parquet archive; quota unknown",
            "Do not assert service is globally unavailable; no verified quotes in this run",
        ],
        [
            "CryptoHouse",
            "200 web shell",
            "No SQL dataset queried",
            "No anonymous SQL endpoint verified in this run",
            "Additional lead, not an evaluated-complete history source",
        ],
    ]


def main():
    plan = json.loads((ROOT / "prereg.json").read_text())
    digest = hashlib.sha256((ROOT / "prereg.json").read_bytes()).hexdigest()
    assert digest == (ROOT / "prereg.sha256").read_text().split()[0]
    audit = json.loads((ROOT / "data/audit_summary.json").read_text())
    receipt = json.loads((ROOT / "data/receipt_summary.json").read_text())
    reason = "Incomplete lifecycle/opening-state history, unverified payout-finality coverage, no contemporaneous bid/ask panel, and no independent full-wallet PnL reconciliation."
    rows = []
    for spec in plan["family"]:
        rows.append(
            {
                "test_id": spec["id"],
                "category": spec["category"],
                "horizon": str(spec.get("evaluation_horizon", 24)),
                "status": "blocked_data",
                "estimate": np.nan,
                "ci_low": np.nan,
                "ci_high": np.nan,
                "p_value": np.nan,
                "q_value": np.nan,
                "n_events": 0,
                "n_markets": 0,
                "resamples": 0,
                "planned_resamples": 10000,
                "mde_80pct": np.nan,
                "family_size": plan["family_size"],
                "reason": reason,
                "prereg_sha256": digest,
            }
        )
    results = pd.DataFrame(rows)
    results["q_value"] = bh(results.p_value, plan["family_size"])
    results.to_csv(ROOT / "results.csv", index=False)
    empty_panel().to_parquet(ROOT / "expert_panel.parquet", index=False)
    (ROOT / "expert_panel.schema.json").write_text(
        json.dumps(
            {
                "status": "blocked_data",
                "rows": 0,
                "reason": reason,
                "columns": {c: str(t) for c, t in empty_panel().dtypes.items()},
                "units": {
                    "total_expert_exposure": "gross outcome shares",
                    "market_price": "verified historical midpoint, USD/share",
                },
                "warning": "Empty is not zero experts, a null effect, or evidence against the hypothesis.",
            },
            indent=2,
        )
    )
    pd.DataFrame(
        [
            {"claim": s, "status": "not_estimable", "reason": reason}
            for s in plan["exploratory"][:5]
        ]
    ).to_csv(ROOT / "exploratory_results.csv", index=False)
    a = access_table()
    pd.DataFrame(
        a,
        columns=["route", "observed_access", "depth", "pagination_and_limits", "gaps"],
    ).to_csv(ROOT / "data_access.csv", index=False)
    reconciliation = []
    for i in range(3):
        b = json.loads((ROOT / f"data/access/v2_board_{i}.body").read_text())["data"]
        p = json.loads((ROOT / f"data/access/v2_pnl_{i}.body").read_text())["data"][
            "points"
        ][-1]
        reconciliation.append(
            {
                "wallet": b["user_id"],
                "leaderboard_realized_pnl": b["pnl"],
                "api_realized_pnl": p["realized_pnl"],
                "api_economic_pnl": p["economic_pnl"],
                "difference": b["pnl"] - p["realized_pnl"],
                "independent_engine_pnl": None,
                "status": "same_provider_consistency_only",
            }
        )
    pd.DataFrame(reconciliation).to_parquet(
        ROOT / "data/leaderboard_reconciliation.parquet", index=False
    )
    style()
    fig, axs = plt.subplots(1, 3, figsize=(14, 5))
    fig.suptitle(
        "Expert consensus: evidence gate before inference",
        fontsize=21,
        weight="bold",
        y=1.02,
    )
    for ax, big, label in zip(
        axs,
        [f"{audit['fill_rows']:,}", "83", "0"],
        [
            "Real bulk fills audited",
            "Tests preregistered",
            "Eligible forecast observations",
        ],
    ):
        ax.axis("off")
        ax.text(
            0.5,
            0.65,
            big,
            ha="center",
            fontsize=42,
            color=TEAL if label.startswith("Real") else AMBER,
            weight="bold",
        )
        ax.text(0.5, 0.40, label, ha="center", fontsize=13)
    fig.text(
        0.5,
        0.08,
        "0 tests evaluated · 83 blocked · no statistical verdict on expert skill",
        ha="center",
        fontsize=14,
        color=MUTED,
    )
    save(fig, "family_overview.png")
    fig, axs = plt.subplots(1, 2, figsize=(13, 5))
    fig.suptitle(
        "A fill archive is not a complete wallet ledger", fontsize=21, weight="bold"
    )
    axs[0].barh(
        ["Exchange is taker", "Other taker"],
        [
            audit["exchange_taker_rows"],
            audit["fill_rows"] - audit["exchange_taker_rows"],
        ],
        color=[AMBER, TEAL],
    )
    axs[0].set_xlabel("OrderFilled rows (Nov 2022–Jun 2023)")
    axs[1].axis("off")
    axs[1].text(
        0.05,
        0.70,
        f"{audit['negative_fill_only_wallet_token_pairs']:,}",
        fontsize=44,
        color=AMBER,
        weight="bold",
    )
    axs[1].text(
        0.05,
        0.47,
        "Wallet–token pairs with negative\nfill-only reconstructed inventory",
        fontsize=15,
    )
    axs[1].text(
        0.05,
        0.16,
        "Diagnostic of omitted history or opening state.\nNot short positions and not a profit estimate.",
        color=MUTED,
        fontsize=11,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.90))
    save(fig, "ledger_completeness.png")
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
    fig, axs = plt.subplots(2, 4, figsize=(14, 7))
    fig.suptitle(
        "Reliability by category: no eligible paired forecasts",
        fontsize=20,
        weight="bold",
    )
    for ax, c in zip(axs.ravel(), cats):
        ax.set_title(c.replace("_", " "))
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_xticks([0, 0.5, 1])
        ax.set_yticks([0, 0.5, 1])
        ax.text(0.5, 0.55, "NOT ESTIMABLE", ha="center", color=AMBER, fontsize=11)
        ax.text(
            0.5, 0.38, "n = 0 verified pairs", ha="center", color=MUTED, fontsize=10
        )
    fig.supxlabel("Forecast probability")
    fig.supylabel("Observed frequency")
    fig.tight_layout(rect=(0, 0.03, 1, 0.92))
    save(fig, "reliability_by_category.png")
    notice(
        "brier_improvement_by_category.png",
        "Brier improvement: estimates withheld",
        [
            "All eight categories lack an eligible point-in-time expert panel. No confidence intervals can be computed.",
            "The missing estimates are not zeros. Family size 83; evaluated tests 0; supported conclusions 0.",
            "Minimum detectable effects and placebo false-positive rates are undefined without usable event clusters.",
        ],
    )
    notice(
        "skill_persistence_deciles.png",
        "Skill persistence: past-to-future ranking is untested",
        [
            "A lifetime leaderboard observed today cannot define experts in an earlier period.",
            "Complete resolved-market P&L, known before each signal time, is required to assign past-skill deciles.",
            "No decile spread or rank correlation is reported from this incomplete ledger.",
        ],
    )
    notice(
        "pnl_concentration.png",
        "Profit concentration cannot be recovered from these fills",
        [
            "Sales proceeds and trading volume are not profit. Split, merge, redemption and transfer accounting are incomplete.",
            "Top 0.1% / 1% shares of category profit are therefore not estimable. No substitute volume curve is labelled P&L.",
        ],
    )
    f = pd.read_parquet(ROOT / "data/fill_audit_mapped.parquet")
    market_counts = f[f.market.notna()].groupby("market").size().nlargest(3)
    cases = [
        f[f.market == market].groupby("token").size().idxmax()
        for market in market_counts.index
    ]
    case_rows = []
    for i, token in enumerate(cases, 1):
        s = f[f.token == token].sort_values(["timestamp", "log_index"])
        meta = s.iloc[0]
        ts = pd.to_datetime(s.timestamp, unit="s", utc=True)
        fig, ax = plt.subplots(figsize=(12, 5))
        ax.plot(
            ts,
            s.execution_price,
            color=TEAL,
            lw=1,
            alpha=0.8,
            label="Observed fill price (not midpoint)",
        )
        ax.set_ylim(-0.03, 1.03)
        ax.set_ylabel("USD per outcome share")
        ax.set_xlabel("UTC time")
        ax.set_title(
            textwrap.fill(meta.question, 85) + f"\nOutcome token: {meta.outcome_label}",
            fontsize=14,
            loc="left",
            pad=15,
        )
        close = pd.to_datetime(meta.closed_time_metadata, utc=True, errors="coerce")
        if (
            pd.notna(close)
            and close >= ts.min() - pd.Timedelta(days=7)
            and close <= ts.max() + pd.Timedelta(days=30)
        ):
            ax.axvline(
                close,
                color=AMBER,
                ls="--",
                label="Gamma closedTime (unverified finality)",
            )
        ax.text(
            0.02,
            0.06,
            "Expert consensus unavailable; payout-finality time unverified",
            transform=ax.transAxes,
            color=AMBER,
            bbox={"facecolor": BG, "edgecolor": "none", "alpha": 0.9},
        )
        ax.legend(loc="upper left", facecolor=BG, labelcolor=FG, fontsize=9)
        fig.autofmt_xdate()
        save(fig, f"case_study_{i}.png")
        case_rows.append(
            {
                "case": i,
                "market": meta.market,
                "token": token,
                "question": meta.question,
                "outcome_label": meta.outcome_label,
                "n_fills": len(s),
                "selection": "Three most-observed distinct mapped markets, highest-count outcome token per market; descriptive, chosen by fill count, never by forecast performance",
                "verified_resolution_timestamp": None,
            }
        )
    pd.DataFrame(case_rows).to_parquet(ROOT / "data/case_studies.parquet", index=False)
    prior = [
        {
            "url": "https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6617059",
            "title": "Gomez-Cram et al., Prediction Market Accuracy: Crowd Wisdom or Informed Minority?",
            "date": "2026-06-25 revision",
            "read_scope": "Public abstract; not a full-paper replication",
            "relevance": "Prior research reports persistent skill concentrated in a minority; smart-money hypothesis is not novel.",
        },
        {
            "url": "https://hashdive.com/",
            "title": "Hashdive",
            "read_scope": "Public product description",
            "relevance": "Historical-performance smart scores and wallet analytics already exist; product claims are not validation.",
        },
        {
            "url": "https://www.polytrackhq.app/",
            "title": "PolyTrack",
            "read_scope": "Public product description only; no login or wallet",
            "relevance": "Whale monitoring and leaderboard following already commercialized.",
        },
        {
            "url": "https://predictionpro.app/",
            "title": "Prediction Pro",
            "read_scope": "Public product description",
            "relevance": "Aggregates profitable wallets weighted by exposure; close conceptual prior art.",
        },
        {
            "url": "https://arxiv.org/abs/2605.11640",
            "title": "Fill-Side Non-Retail Trading on Polymarket",
            "date": "2026-05-12",
            "read_scope": "Abstract",
            "relevance": "Separates fill-side behavior from unavailable wallet-level quote lifecycles; market-maker labels need caution.",
        },
        {
            "url": "https://arxiv.org/abs/2606.04217",
            "title": "Polymarket-v1 Database",
            "date": "2026-06",
            "read_scope": "Abstract",
            "relevance": "Trade direction and settlement microstructure matter for measurement.",
        },
    ]
    (ROOT / "prior_art.json").write_text(json.dumps(prior, indent=2))
    datasets = [
        {
            "name": "wzsg Polymarket V1 OrderFilled",
            "url": "https://huggingface.co/datasets/wzsg/polymarket-orderfilled-v1",
            "access": "anonymous parquet; 8 monthly shards cached",
        },
        {
            "name": "Polymarket Data API V2",
            "url": "https://data-api.polymarket.com/v2/docs",
            "access": "keyless read-only probes",
        },
        {
            "name": "Polygon dRPC",
            "url": "https://polygon.drpc.org",
            "access": "read-only JSON-RPC historical spot checks",
        },
    ]
    prefix = "explore/polymarket_experts/"
    findings = []

    def finding(id, title, line, verdict, metrics, figures, caveat):
        findings.append(
            {
                "id": id,
                "title": title,
                "one_liner": line,
                "datasets": datasets,
                "mechanism": "Historical category performance might identify informative positions; valid inference requires a complete point-in-time ledger.",
                "method": "83 preregistered tests; hard validity gates; descriptive source and transaction audits; no empirical skill test evaluated.",
                "results": metrics,
                "controls": [
                    "Temporal holdout fixed at 2025-01-01",
                    "Resolution strictly precedes expert qualification",
                    "No current leaderboard selection for research",
                    "10 matched placebo tests registered but blocked",
                    "Whole-family BH includes all 83 specifications",
                ],
                "verdict": verdict,
                "known_or_novel": "Known idea; this run contributes an access and accounting audit, not a new skill result.",
                "prior_art": [p["url"] for p in prior],
                "figures": [prefix + "figures/" + f for f in figures],
                "scripts": [
                    prefix + "scripts/" + s
                    for s in [
                        "ingest.py",
                        "ledger.py",
                        "panel.py",
                        "inference.py",
                        "publish.py",
                    ]
                ],
                "caveats": [
                    caveat,
                    "Research demonstration, not investment advice.",
                    "Code and report prepared with AI assistance.",
                ],
            }
        )

    finding(
        "P1-consensus",
        "Expert-weighted consensus remains untested",
        "83 registered tests; 0 evaluated; 83 blocked by missing verified history. No skill verdict.",
        "partial",
        [
            {
                "metric": "registered_family_size",
                "value": 83,
                "n": 83,
                "note": "Frozen before tests",
            },
            {
                "metric": "evaluated_tests",
                "value": 0,
                "n": 83,
                "note": "Not a statistical null",
            },
            {
                "metric": "Brier improvement",
                "value": None,
                "n": 0,
                "note": "Missing, not zero",
            },
        ],
        [
            "family_overview.png",
            "reliability_by_category.png",
            "brier_improvement_by_category.png",
        ],
        reason,
    )
    finding(
        "P1-fills-sufficiency",
        "Reject the fill-only inventory shortcut",
        f"{audit['negative_fill_only_wallet_token_pairs']:,} wallet–token pairs have negative fill-only balances in a {audit['fill_rows']:,}-fill audit.",
        "rejected",
        [
            {
                "metric": "negative_fill_only_wallet_token_pairs",
                "value": audit["negative_fill_only_wallet_token_pairs"],
                "n": audit["fill_rows"],
                "note": "Descriptive audit, no inferential test",
            },
            {
                "metric": "exchange_as_taker_rows",
                "value": audit["exchange_taker_rows"],
                "n": audit["fill_rows"],
                "note": "Exchange is not an independent forecasting wallet",
            },
        ],
        ["ledger_completeness.png"],
        "Rejected claim is that fills alone suffice for full positions/PnL. Does not reject expert skill; sample limited to Nov 2022–Jun 2023.",
    )
    finding(
        "P1-source-validation",
        "Bulk fill fields pass limited receipt checks",
        "Six fills match three public RPC receipts exactly; complete-ledger validation is still missing.",
        "supported",
        [
            {
                "metric": "exact_raw_fill_matches",
                "value": receipt["bulk_exact_matches"],
                "n": receipt["orderfilled_logs"],
                "note": "Three transactions, five integer data fields and two address fields checked",
            },
            {
                "metric": "same_provider_PnL_matches",
                "value": 3,
                "n": 3,
                "note": "NOT independent full-wallet reconstruction",
            },
        ],
        ["ledger_completeness.png"],
        "Small raw-event checks do not validate lifetime PnL or archive completeness.",
    )
    for id, title, line, figs in [
        (
            "P1-sports",
            "Sports advantage is untested",
            "No category has eligible paired forecasts.",
            ["brier_improvement_by_category.png"],
        ),
        (
            "P1-divergence",
            "Divergence information and drift are untested",
            "No verified expert-minus-mid divergence exists to regress or lag-search.",
            ["case_study_1.png", "case_study_2.png", "case_study_3.png"],
        ),
        (
            "P1-persistence",
            "Persistent expertise is untested",
            "Past and future category P&L cannot yet be compared without missing lifecycle accounting.",
            ["skill_persistence_deciles.png"],
        ),
        (
            "P1-economics",
            "No executable edge established",
            "No historical spread, depth and fee-adjusted effect is available.",
            ["family_overview.png"],
        ),
        (
            "P1-whales",
            "Whale-watching extras remain exploratory and unavailable",
            "Profit concentration, net expert flow, news timing, lockstep clusters and specialization are not estimated.",
            ["pnl_concentration.png"],
        ),
    ]:
        finding(
            id,
            title,
            line,
            "partial",
            [
                {
                    "metric": "eligible_observations",
                    "value": 0,
                    "n": 0,
                    "note": "Not estimable; missing estimates and MDE remain null",
                }
            ],
            figs,
            reason,
        )
    (ROOT / "findings.json").write_text(
        json.dumps(findings, indent=2, allow_nan=False) + "\n"
    )
    table = "\n".join(
        "| " + " | ".join(str(v).replace("|", "/") for v in row) + " |" for row in a
    )
    now = datetime.now(timezone.utc).isoformat()
    report = f"""# P1 — Expert-weighted consensus & whale watching

**83 tests preregistered; 0 evaluated; 83 blocked; 0 supported statistical conclusions.**
The expert-consensus hypothesis remains **untested**. This is an incomplete empirical study with a measured data-access/accounting audit, **not a clean statistical null**. All requested output paths exist, but `expert_panel.parquet` is a typed **zero-row** panel; the requested empirical charts are explicitly unavailable. It would be misleading to show expert probabilities, Brier gains, or profit concentration from these inputs.

Generated {now}. SHA256 of immutable preregistration: `{digest}`.

## Primary result and what was actually tested

The audit downloaded **{audit["fill_rows"]:,} actual V1 OrderFilled rows**, representing **{audit["transactions"]:,} transactions**, **{audit["makers"]:,} maker addresses**, and **{audit["tokens"]:,} outcome tokens**, from {audit["start"]} to {audit["end"]}. Zero duplicate event keys were found. The audit slice is the first eight monthly shards, chosen for a bounded, reproducible check of original event semantics, not for predictive performance. It is outside the registered holdout and never treated as an out-of-sample test.

**{audit["exchange_taker_rows"]:,} rows ({100 * audit["exchange_taker_rows"] / audit["fill_rows"]:.1f}%) name the Exchange as taker.** These correspond to aggregate taker-order settlement rows in this slice. Appending an opposite taker position to every maker row would double count some matched order flow. A maker-only replay, with V1 fees in the received asset, has **{audit["negative_fill_only_inventory_rows"]:,} negative inventory observations in {audit["negative_fill_only_wallet_token_pairs"]:,} wallet–token pairs**. This diagnostic identifies missing lifecycle/opening-state information or other unresolved accounting, not literal short balances. Nonnegative paths are not proof of completeness either.

Three public historical RPC receipts contain {receipt["logs"]} logs, including {receipt["ctf_logs"]} CTF logs and {receipt["orderfilled_logs"]} exchange fills. **{receipt["bulk_exact_matches"]}/{receipt["orderfilled_logs"]} fills match** five raw integer fields plus maker/taker addresses. This spot check validates those rows, not the full archive. Three pseudonymous wallets' current all-time leaderboard P&L agrees with the same provider's `realized_pnl` atom. **Independent engine-versus-leaderboard lifetime P&L reconciliation was not achieved.** The latter comparison is a consistency test, not independent validation, and these leaderboard-selected wallets never enter an expert cohort.

## Data-access evaluation

Discovery and bulk README/schema evaluation preceded any Polymarket API paging. All activity was public read-only HTTP or read-only RPC. No account, API credential, wallet connection, signature, payment, order, or order simulation was used. No address was linked to a real identity. Raw endpoint responses may carry public display fields; analytic exports retain addresses and numeric data only.

| Route | Observed access | Depth / coverage | Pagination / rate limits | Gaps |
|---|---|---|---|---|
{table}

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

The brief described the shared Gamma crawl as DONE. At inspection it was actively growing with a non-DONE cursor. A local byte snapshot retained **{audit["catalog_markets"]:,} distinct markets** ({audit["catalog_tokens"]:,} tokens) before a truncated gzip tail; malformed complete lines: {audit["gamma_malformed_lines"]}. Snapshot SHA256: `{audit["gamma_snapshot_sha256"]}`. **{audit["mapped_rows"]:,}/{audit["fill_rows"]:,} fill rows** match metadata, but only **{audit["mapped_tokens"]}/{audit["tokens"]} outcome tokens** match. The final-volume >=USD10000 source filter creates survivorship/selection bias and cannot define the confirmation sample. Heuristic categories are audit labels only, not validated historical tags. Gamma `closedTime`, scheduled end and terminal prices do not prove on-chain payout-finality time.

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
"""
    (ROOT / "REPORT.md").write_text(report)
    print(
        "Published 83 blocked test rows, typed empty panel, 9 figures and",
        len(findings),
        "findings",
    )


if __name__ == "__main__":
    main()
