import numpy as np
import pandas as pd

from warsignal.analysis.stats import align, event_study, lagged_correlation, permutation_pvalue, transform


def test_lag_and_align():
    idx = pd.date_range("2025-01-01", periods=40)
    a = pd.Series(np.sin(np.arange(40)), index=idx)
    b = a.shift(3).fillna(0)
    assert abs(lagged_correlation(a, b, 5)["best_lag"]) == 3
    assert len(align(a, b)) == 40


def test_permutation_and_anomaly():
    idx = pd.date_range("2025-01-01", periods=100)
    a = pd.Series(np.arange(100), index=idx)
    assert permutation_pvalue(a, a, n_perm=30) < 0.2
    assert transform(pd.Series([1, 2, 1, 2], index=pd.date_range("2025-01-01", periods=4)), "anomaly").abs().sum() >= 0


def test_event_study_step():
    idx = pd.date_range("2025-01-01", periods=20)
    series = pd.Series([0] * 10 + [1] * 10, index=idx)
    result = event_study(series, [idx[10]], window=3)
    assert result["mean_change"] == 1


def test_daily_and_weekly_alignment_uses_weekly_steps():
    daily_idx = pd.date_range("2025-03-01", periods=560, freq="D")
    weekly_idx = pd.date_range("2025-03-03", periods=80, freq="W-MON")
    daily = pd.Series(np.arange(len(daily_idx)), index=daily_idx)
    weekly = pd.Series(np.arange(len(weekly_idx)), index=weekly_idx)
    frame = align(daily, weekly)
    assert 75 <= len(frame) <= 81
