from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

from warsignal.config import WAR_START


def transform(s, kind, baseline_year=2025):
    s = pd.Series(s, dtype="float64").sort_index()
    if kind == "level":
        return s
    if kind == "diff":
        return s.diff()
    if kind in {"pct_change", "log_return"}:
        result = s.pct_change() if kind == "pct_change" else np.log(s.where(s > 0)).diff()
        return result.replace([np.inf, -np.inf], np.nan)
    if kind == "zscore":
        return (s - s.mean()) / s.std(ddof=0)
    if kind == "anomaly":
        index = pd.DatetimeIndex(s.index)
        baseline = s[index.year == baseline_year]
        if baseline.empty:
            return s - s.mean()
        means = baseline.groupby(index[index.year == baseline_year].isocalendar().week.to_numpy()).mean()
        return pd.Series([value - means.get(ts.isocalendar().week, baseline.mean()) for ts, value in s.items()], index=s.index, name=s.name)
    raise ValueError(f"unknown transform {kind}")


def _step(s):
    s = pd.Series(s)
    return s.index.to_series().diff().median() if len(s.index) > 1 else pd.Timedelta(days=1)


def _coarsest_step(a, b):
    return max(_step(a), _step(b))


def align(a, b):
    a, b = pd.Series(a), pd.Series(b)
    coarsest = _coarsest_step(a, b)
    if coarsest > pd.Timedelta(days=20):
        a, b = a.resample("MS").mean(), b.resample("MS").mean()
    elif coarsest > pd.Timedelta(days=3):
        a, b = a.resample("W-MON", label="left", closed="left").mean(), b.resample("W-MON", label="left", closed="left").mean()
    return pd.concat([a.rename("a"), b.rename("b")], axis=1, join="inner").dropna()


def correlation_summary(a, b):
    frame = align(a, b)
    if len(frame) < 3:
        return {"n": int(len(frame)), "pearson_r": None, "pearson_p": None, "spearman_r": None, "spearman_p": None}
    p = stats.pearsonr(frame.a, frame.b)
    s = stats.spearmanr(frame.a, frame.b)
    return {"n": int(len(frame)), "pearson_r": float(p.statistic), "pearson_p": float(p.pvalue),
            "spearman_r": float(s.statistic), "spearman_p": float(s.pvalue)}


def lagged_correlation(a, b, max_lag):
    frame = align(a, b)
    lags, values = [], []
    for lag in range(-max_lag, max_lag + 1):
        shifted = frame.a.shift(lag)
        pair = pd.concat([shifted, frame.b], axis=1).dropna()
        lags.append(lag)
        values.append(float(pair.iloc[:, 0].corr(pair.iloc[:, 1])) if len(pair) >= 3 else float("nan"))
    valid = [(abs(v), lag, v) for lag, v in zip(lags, values) if np.isfinite(v)]
    if not valid:
        return {"lags": lags, "r": values, "best_lag": None, "best_r": None}
    _, lag, value = max(valid)
    return {"lags": lags, "r": values, "best_lag": int(lag), "best_r": float(value)}


def permutation_pvalue(a, b, n_perm=500, seed=0, max_lag=3):
    frame = align(a, b)
    if len(frame) < 4:
        return float("nan")
    max_lag = min(max_lag, max(1, len(frame) // 10))
    def best(x, y):
        values = []
        for lag in range(-max_lag, max_lag + 1):
            if lag > 0:
                left, right = x[:-lag], y[lag:]
            elif lag < 0:
                left, right = x[-lag:], y[:lag]
            else:
                left, right = x, y
            values.append(np.corrcoef(left, right)[0, 1] if len(left) >= 3 else np.nan)
        return np.nanmax(np.abs(values)) * (1 if values[int(np.nanargmax(np.abs(values)))] >= 0 else -1)
    observed = best(frame.a.to_numpy(), frame.b.to_numpy())
    if not np.isfinite(observed):
        return float("nan")
    rng = np.random.default_rng(seed)
    values = []
    b_values = frame.b.to_numpy()
    for _ in range(n_perm):
        shifted = np.roll(b_values, int(rng.integers(1, len(b_values))))
        values.append(best(frame.a.to_numpy(), shifted))
    return float((1 + sum(abs(x) >= abs(observed) for x in values if np.isfinite(x))) / (1 + len(values)))


def pre_post_comparison(a, b, war_start):
    a, b = pd.Series(a), pd.Series(b)
    pre = correlation_summary(a[a.index < pd.Timestamp(war_start)], b[b.index < pd.Timestamp(war_start)])
    post = correlation_summary(a[a.index >= pd.Timestamp(war_start)], b[b.index >= pd.Timestamp(war_start)])
    change = None if pre["pearson_r"] is None or post["pearson_r"] is None else post["pearson_r"] - pre["pearson_r"]
    fisher_p = None
    if change is not None and pre["n"] > 3 and post["n"] > 3:
        r1, r2 = np.clip(pre["pearson_r"], -0.9999, 0.9999), np.clip(post["pearson_r"], -0.9999, 0.9999)
        z = (np.arctanh(r1) - np.arctanh(r2)) / math.sqrt(1 / (pre["n"] - 3) + 1 / (post["n"] - 3))
        fisher_p = float(2 * stats.norm.sf(abs(z)))
    return {"pre": pre, "post": post, "r_change": change, "fisher_z_p": fisher_p}


def event_study(series, event_dates, window=5):
    s = pd.Series(series).sort_index()
    records = []
    for event in event_dates:
        day = pd.Timestamp(event)
        pre = s[(s.index >= day - pd.Timedelta(days=window)) & (s.index < day)].mean()
        post = s[(s.index >= day) & (s.index <= day + pd.Timedelta(days=window))].mean()
        records.append({"date": day.date().isoformat(), "pre": pre, "post": post, "change": post - pre})
    changes = pd.Series([r["change"] for r in records], dtype="float64").dropna()
    t = stats.ttest_1samp(changes, 0) if len(changes) > 1 else None
    pre_values = [r["pre"] for r in records if pd.notna(r["pre"])]
    post_values = [r["post"] for r in records if pd.notna(r["post"])]
    return {"n_events": len(records), "mean_pre": float(np.mean(pre_values)) if pre_values else None,
            "mean_post": float(np.mean(post_values)) if post_values else None,
            "mean_change": float(changes.mean()) if len(changes) else None,
            "t_stat": float(t.statistic) if t else None, "p": float(t.pvalue) if t else None, "per_event": records}


def apply_window(s, window):
    s = pd.Series(s)
    start = pd.Timestamp(WAR_START)
    if window == "pre_war":
        return s[s.index < start]
    if window == "war":
        return s[s.index >= start]
    return s


def run_all(plan, a, b, timeline):
    ta, tb = transform(a, plan.transform_a), transform(b, plan.transform_b)
    ta, tb = apply_window(ta, plan.window), apply_window(tb, plan.window)
    frame = align(ta, tb)
    lag = lagged_correlation(ta, tb, plan.max_lag_days)
    perm = permutation_pvalue(ta, tb, max_lag=plan.max_lag_days)
    result = {"n_obs": int(len(frame)), "coverage_start": frame.index.min().date().isoformat() if len(frame) else None,
              "coverage_end": frame.index.max().date().isoformat() if len(frame) else None,
              "correlation": correlation_summary(ta, tb), "lagged": lag,
              "perm_p": perm, "n_lags_tested": len(lag["lags"]),
              "bonferroni_p": min(1.0, perm * len(lag["lags"])) if np.isfinite(perm) else None}
    if plan.window == "compare_pre_post":
        result["pre_post"] = pre_post_comparison(ta, tb, WAR_START)
    else:
        result["pre_post"] = None
    event_dates = []
    if plan.event_category and timeline is not None:
        event_dates = timeline.loc[timeline["category"] == plan.event_category, "date"].tolist()
    result["event_study"] = event_study(ta, event_dates) if event_dates else None
    result["event_study_b"] = event_study(tb, event_dates) if event_dates else None
    result["window"] = plan.window
    coarsest = _coarsest_step(ta, tb)
    if coarsest > pd.Timedelta(days=20):
        lag_unit = "months"
    elif coarsest > pd.Timedelta(days=3):
        lag_unit = "weeks"
    else:
        lag_unit = "days"
    result["lag_unit"] = lag_unit
    expected = plan.expected_sign
    result["sign_matches_expectation"] = expected == 0 or (
        lag["best_r"] is not None and np.isfinite(lag["best_r"]) and np.sign(lag["best_r"]) == expected
    )
    return result
