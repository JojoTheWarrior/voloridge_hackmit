"""Causal expert consensus from complete audited ledgers and historical quotes."""

from decimal import Decimal
import numpy as np
import pandas as pd
from ledger import IncompleteLedger

VARIANTS = ["equal", "pnl", "size", "pnl_size", "roi_shrunk", "hit_rate_shrunk"]
PANEL_TYPES = {
    "market": "string",
    "event_id": "string",
    "category": "string",
    "horizon": "string",
    "signal_timestamp": "int64",
    "resolution_timestamp": "int64",
    "market_price": "float64",
    **{"expert_prob_" + v: "float64" for v in VARIANTS},
    "expert_prob": "float64",
    "blend_prob": "float64",
    "n_experts": "int64",
    "total_expert_exposure": "float64",
    "divergence": "float64",
    "outcome": "float64",
    "quality_status": "string",
}


def empty_panel():
    return pd.DataFrame({k: pd.Series(dtype=v) for k, v in PANEL_TYPES.items()})


def consensus(
    ledger,
    condition,
    category,
    t,
    yes,
    no,
    threshold=10000,
    minpast=10,
    minimum_experts=3,
):
    past = ledger.past_pnl(t, category)
    snap = ledger.snapshot(t)
    views = []
    weights = {v: [] for v in VARIANTS}
    gross = 0
    for (wallet, c), a in snap.items():
        if c != condition:
            continue
        p = past.get(wallet)
        if p is None or p["pnl"] <= threshold or p["n_markets"] < minpast:
            continue
        y, n = float(a.tokens.get(yes, Decimal(0))), float(a.tokens.get(no, Decimal(0)))
        size = y + n
        if min(y, n) < 0:
            raise IncompleteLedger("Negative held balance")
        if size <= 0:
            continue
        views.append(y / size)
        gross += size
        pnl, cost = float(p["pnl"]), float(p["cost"])
        for k, w in {
            "equal": 1,
            "pnl": pnl,
            "size": size,
            "pnl_size": pnl * size,
            "roi_shrunk": max(pnl / (cost + 1000), 0),
            "hit_rate_shrunk": (p["wins"] + 5) / (p["n_markets"] + 10),
        }.items():
            weights[k].append(w)
    result = {"n_experts": len(views), "total_expert_exposure": gross}
    for v in VARIANTS:
        result["expert_prob_" + v] = (
            float(np.average(views, weights=weights[v]))
            if len(views) >= minimum_experts and sum(weights[v]) > 0
            else np.nan
        )
    result["expert_prob"] = result["expert_prob_pnl_size"]
    return result


def build_panel(ledger, markets, quotes):
    """Markets require verified finality and opening times, quotes require as-of bid/ask.

    Quotes contain market,timestamp,bid,ask,verified_history. No future nearest
    neighbor matching. Require quote <=t, no more than 5 minutes stale (strict
    operational gate, no post-hoc tuning). Multi-outcome events are represented
    as separate binary CTF conditions and share an event_id for inference.
    """
    rows = []
    for m in markets:
        if not m.get("verified_onchain_resolution"):
            continue
        for h in [24, 6, 1, "open_plus_6"]:
            t = (
                m["created_timestamp"] + 21600
                if isinstance(h, str)
                else m["resolution_timestamp"] - h * 3600
            )
            if t <= m["created_timestamp"] or t >= m["resolution_timestamp"]:
                continue
            q = quotes[
                (quotes.market == m["market"])
                & (quotes.timestamp <= t)
                & (quotes.timestamp >= t - 300)
                & quotes.verified_history
            ]
            if q.empty:
                continue
            q = q.sort_values("timestamp").iloc[-1]
            if not (0 <= q.bid <= q.ask <= 1):
                continue
            signal = consensus(
                ledger, m["condition"], m["category"], t, m["yes_token"], m["no_token"]
            )
            if signal["n_experts"] < 3:
                continue
            mid = (q.bid + q.ask) / 2
            rows.append(
                {
                    "market": m["market"],
                    "event_id": m["event_id"],
                    "category": m["category"],
                    "horizon": str(h),
                    "signal_timestamp": t,
                    "resolution_timestamp": m["resolution_timestamp"],
                    "market_price": mid,
                    **signal,
                    "blend_prob": 0.5 * (mid + signal["expert_prob"]),
                    "divergence": signal["expert_prob"] - mid,
                    "outcome": m["outcome"],
                    "quality_status": "verified",
                }
            )
    return pd.DataFrame(rows).astype(PANEL_TYPES) if rows else empty_panel()
