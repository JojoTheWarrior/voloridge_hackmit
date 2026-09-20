"""Preregistered paired event bootstrap and whole-family BH utilities."""

import numpy as np
from scipy.stats import norm


def bh(pvalues, family_size):
    p = np.asarray(pvalues, dtype=float)
    if len(p) != family_size:
        raise ValueError("Must supply entire registered family")
    missing = ~np.isfinite(p)
    order = np.argsort(np.where(missing, 1, p))
    ranked = np.where(missing, 1, p)[order]
    corrected = np.minimum.accumulate(
        (ranked * family_size / np.arange(1, family_size + 1))[::-1]
    )[::-1]
    out = np.empty(family_size)
    out[order] = np.clip(corrected, 0, 1)
    out[missing] = np.nan
    return out


def paired_bootstrap(event_differences, resamples=10000, seed=20260920, family_size=83):
    x = np.asarray(event_differences, dtype=float)
    x = x[np.isfinite(x)]
    if len(x) < 50:
        raise ValueError("Fewer than 50 independent event clusters")
    if resamples < 10000:
        raise ValueError("At least 10000 resamples required")
    rng = np.random.default_rng(seed)
    means = []
    for start in range(0, resamples, 200):
        idx = rng.integers(0, len(x), (min(200, resamples - start), len(x)))
        means.extend(x[idx].mean(1))
    means = np.asarray(means)
    estimate = x.mean()
    p = (1 + np.count_nonzero(np.abs(means - estimate) >= abs(estimate))) / (
        resamples + 1
    )
    lo, hi = np.quantile(means, [0.025, 0.975])
    mde = (
        (norm.ppf(1 - 0.05 / (2 * family_size)) + norm.ppf(0.8))
        * x.std(ddof=1)
        / np.sqrt(len(x))
    )
    return dict(
        estimate=float(estimate),
        ci_low=float(lo),
        ci_high=float(hi),
        p_value=float(p),
        mde_80pct=float(mde),
        n_events=len(x),
        resamples=resamples,
    )


def max_statistic(differences, resamples=10000, seed=20260920):
    """Joint event-cluster sign-flip null; requires symmetric null differences."""
    x = np.asarray(differences, dtype=float)
    if x.ndim != 2 or x.shape[0] < 50 or resamples < 10000 or not np.isfinite(x).all():
        raise ValueError("Require finite event x horizon data, n>=50, B>=10000")
    se = x.std(0, ddof=1) / np.sqrt(len(x))
    if np.any(se <= 0):
        raise ValueError("Degenerate horizon")
    observed = np.max(np.abs(x.mean(0) / se))
    rng = np.random.default_rng(seed)
    null = []
    for start in range(0, resamples, 100):
        signs = rng.choice([-1.0, 1.0], (min(100, resamples - start), len(x)))
        null.extend(np.max(np.abs((signs @ x) / len(x) / se), axis=1))
    return float((1 + np.count_nonzero(np.asarray(null) >= observed)) / (resamples + 1))


def loss_delta(y, market, expert, metric="brier"):
    y, m, e = map(lambda z: np.asarray(z, dtype=float), (y, market, expert))
    if metric == "brier":
        return (m - y) ** 2 - (e - y) ** 2
    m, e = np.clip(m, 0.001, 0.999), np.clip(e, 0.001, 0.999)
    return -(y * np.log(m) + (1 - y) * np.log1p(-m)) + (
        y * np.log(e) + (1 - y) * np.log1p(-e)
    )
