"""Round 2 trade rubric: turn an aligned (signal, target) pair into a repeatable rule.

Rule: signal_z = rolling z-score of the signal series over ``zscore_window`` days;
enter when ``signal_z`` crosses ``threshold`` (direction = expected sign), hold the
target security for ``holding_days`` (the mission's best lead lag, clipped to
1..10) using only information available at the close of the signal day.
See missions/ROUND2_RUBRIC.md.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from warsignal.config import WAR_START

MIN_TRADES = 5
MAX_HOLD = 10


def rolling_zscore(series, window=20):
    s = pd.Series(series, dtype="float64").sort_index()
    mean = s.rolling(window, min_periods=max(5, window // 2)).mean()
    std = s.rolling(window, min_periods=max(5, window // 2)).std(ddof=0)
    return ((s - mean) / std).replace([np.inf, -np.inf], np.nan)


def _returns(target, target_kind):
    """Target as per-period simple returns. ``log_return`` is exponentiated; ``level``
    (prices, spreads, ratios) becomes pct change; anything else is used as-is."""
    t = pd.Series(target, dtype="float64").sort_index()
    if target_kind == "log_return":
        return np.exp(t) - 1.0
    if target_kind == "level":
        return t.pct_change().replace([np.inf, -np.inf], np.nan)
    if target_kind == "diff":  # spreads can cross zero: use point changes as the P&L unit
        return t.diff()
    return t


def forward_return(returns, holding_days, additive=False):
    """Return earned from the close of day t over the next ``holding_days`` periods
    (compounded, or summed for point-change targets such as spreads)."""
    if additive:
        cum = returns.fillna(0.0).cumsum()
        fwd = cum.shift(-holding_days) - cum
    else:
        growth = (1.0 + returns.fillna(0.0)).cumprod()
        fwd = growth.shift(-holding_days) / growth - 1.0
    fwd[returns.shift(-holding_days).isna()] = np.nan  # no look-ahead past the last observation
    return fwd


def _max_drawdown(trade_returns):
    if len(trade_returns) == 0:
        return 0.0
    equity = (1.0 + pd.Series(trade_returns, dtype="float64")).cumprod()
    peak = equity.cummax()
    return float(((equity / peak) - 1.0).min())


def _summary(trade_returns, baseline_returns):
    n = int(len(trade_returns))
    if n == 0:
        return {"n_trades": 0, "hit_rate": None, "avg_return": None, "baseline_avg_return": None,
                "excess_return": None, "sharpe_like": None, "max_drawdown": None, "total_return": None}
    tr = np.asarray(trade_returns, dtype="float64")
    avg = float(tr.mean())
    base = float(np.nanmean(baseline_returns)) if len(baseline_returns) else 0.0
    std = float(tr.std(ddof=0))
    sharpe = float(avg / std * math.sqrt(n)) if std > 0 and n > 1 else None
    return {
        "n_trades": n,
        "hit_rate": float((tr > 0).mean()),
        "avg_return": avg,
        "baseline_avg_return": base,
        "excess_return": avg - base,
        "sharpe_like": sharpe,
        "max_drawdown": _max_drawdown(tr),
        "total_return": float(np.prod(1.0 + tr) - 1.0),
    }


def evaluate_rule(signal, target, expected_sign=1, holding_days=1, threshold=1.0, zscore_window=20,
                  target_kind="log_return", split_date=WAR_START):
    """Backtest one rule on two date-indexed series and return metrics (JSON-safe dict).

    ``expected_sign`` +1 -> long the target when signal_z > threshold; -1 -> short.
    Entries are non-overlapping (no new trade while a position is open).
    """
    holding_days = int(max(1, min(MAX_HOLD, holding_days or 1)))
    direction = -1 if expected_sign is not None and expected_sign < 0 else 1
    frame = pd.concat(
        [rolling_zscore(signal, zscore_window).rename("z"),
         forward_return(_returns(target, target_kind), holding_days, additive=target_kind == "diff").rename("fwd")],
        axis=1, join="inner",
    )
    frame = frame[frame["z"].notna()]
    entries = frame.index[frame["z"] > threshold]
    taken, last_exit = [], None
    for ts in entries:
        if last_exit is not None and ts <= last_exit:
            continue
        if pd.isna(frame.at[ts, "fwd"]):
            continue
        taken.append(ts)
        pos = frame.index.get_loc(ts)
        exit_pos = min(pos + holding_days, len(frame.index) - 1)
        last_exit = frame.index[exit_pos]
    trades = pd.Series([direction * frame.at[ts, "fwd"] for ts in taken], index=pd.DatetimeIndex(taken), dtype="float64")
    baseline = direction * frame["fwd"].dropna()
    split = pd.Timestamp(split_date)
    fit_mask, test_mask = trades.index < split, trades.index >= split
    return {
        "rule": {
            "signal_transform": f"rolling_zscore_{zscore_window}d",
            "threshold": float(threshold),
            "direction": "long" if direction > 0 else "short",
            "holding_days": holding_days,
            "target_kind": target_kind,
        },
        "all": _summary(trades.to_numpy(), baseline.to_numpy()),
        "fit_pre_war": _summary(trades[fit_mask].to_numpy(), baseline[baseline.index < split].to_numpy()),
        "test_war": _summary(trades[test_mask].to_numpy(), baseline[baseline.index >= split].to_numpy()),
        "trade_dates": [ts.strftime("%Y-%m-%d") for ts in trades.index],
        "trade_returns": [float(v) for v in trades.to_numpy()],
        "n_signal_days": int(len(frame)),
    }


def heuristic_actionability(metrics):
    """0-10 score: enough trades, positive OOS edge, decent hit rate, controlled drawdown."""
    if not metrics:
        return 0.0
    overall, test = metrics.get("all") or {}, metrics.get("test_war") or {}
    n = overall.get("n_trades") or 0
    if n < MIN_TRADES:
        return round(min(2.0, 0.4 * n), 2)
    score = 2.0
    score += min(2.0, 2.0 * math.log10(n / MIN_TRADES + 1))
    hit = overall.get("hit_rate") or 0.0
    score += max(-2.0, min(2.0, (hit - 0.5) * 10))
    excess = overall.get("excess_return") or 0.0
    score += 1.0 if excess > 0 else -1.0
    sharpe = overall.get("sharpe_like") or 0.0
    score += max(0.0, min(2.0, sharpe / 1.5))
    if (test.get("n_trades") or 0) >= 3:
        score += 1.5 if (test.get("excess_return") or 0.0) > 0 else -1.5
    dd = overall.get("max_drawdown") or 0.0
    if dd < -0.15:
        score -= 1.0
    return round(max(0.0, min(10.0, score)), 2)


def trade_idea_from_metrics(metrics, instrument, signal_name, actionability=None, caveats=""):
    """Render metrics as the SCHEMA.md ``trade_idea`` object."""
    rule, overall = metrics.get("rule") or {}, metrics.get("all") or {}
    test = metrics.get("test_war") or {}
    return {
        "instrument": instrument,
        "direction": rule.get("direction", "long"),
        "entry_rule": (f"{signal_name} {rule.get('signal_transform', 'zscore')} > {rule.get('threshold', 1.0):g} "
                       f"at close -> {rule.get('direction', 'long')} {instrument} next session"),
        "exit_rule": f"close after {rule.get('holding_days', 1)} trading days (no overlapping entries)",
        "holding_days": rule.get("holding_days"),
        "hit_rate": overall.get("hit_rate"),
        "avg_return": overall.get("avg_return"),
        "excess_return": overall.get("excess_return"),
        "n_trades": overall.get("n_trades"),
        "sharpe_like": overall.get("sharpe_like"),
        "max_drawdown": overall.get("max_drawdown"),
        "oos_n_trades": test.get("n_trades"),
        "oos_avg_return": test.get("avg_return"),
        "oos_hit_rate": test.get("hit_rate"),
        "actionability": actionability if actionability is not None else heuristic_actionability(metrics),
        "caveats": caveats or ("Backtest on daily closes, no costs/slippage; few independent regimes; "
                               "signal and target may share the war as common cause."),
    }


def instrument_from_indicator(name):
    """finance.FRO.log_return -> FRO; finance.spread.brent_wti -> spread:brent_wti; else the name."""
    parts = str(name).split(".")
    if len(parts) >= 3 and parts[0] == "finance":
        if parts[1] in {"spread", "ratio", "fred"}:
            return f"{parts[1]}:{parts[2]}"
        return parts[1]
    return str(name)


def target_kind_from_indicator(name, transform="level"):
    if str(name).endswith(".log_return") or transform == "log_return":
        return "log_return"
    parts = str(name).split(".")
    if parts[0] == "finance" and parts[1] == "spread":
        return "diff"
    if parts[0] == "finance" and (name.endswith(".close") or parts[1] in {"ratio", "fred"}):
        return "level"
    return "return"
