"""Lead-lag test engine: max-|r|-over-lags statistic, block-permutation + circular-shift null, exact circular p, year-shuffle, OOS split."""
import numpy as np, pandas as pd
N_PERM = 10_000

def _corr(X, mx, Y, my):
    """Pairwise-complete Pearson r between each row of X (S x n) and each row of Y (K x n) -> (S x K)."""
    X0, Y0 = np.where(mx, X, 0.0), np.where(my, Y, 0.0)
    mxf, myf = mx.astype(float), my.astype(float)
    n = mxf @ myf.T; sx = X0 @ myf.T; sxx = (X0 ** 2) @ myf.T; sy = mxf @ Y0.T; syy = mxf @ (Y0 ** 2).T; sxy = X0 @ Y0.T
    with np.errstate(invalid="ignore", divide="ignore"):
        r = (n * sxy - sx * sy) / np.sqrt((n * sxx - sx ** 2) * (n * syy - sy ** 2))
    r[n < 12] = np.nan
    return r, n

def surrogates(x, block, n_perm, rng):
    """Random permutation of contiguous blocks followed by a random circular shift (NaNs travel with their values)."""
    n = len(x); starts = np.arange(0, n, block); out = np.empty((n_perm, n))
    for i in range(n_perm):
        o = rng.integers(0, block)                                   # random block phase
        xr = np.roll(x, -o); blocks = [xr[s:s + block] for s in starts]
        out[i] = np.roll(np.concatenate([blocks[j] for j in rng.permutation(len(blocks))]), rng.integers(1, n))
    return out

def year_surrogates(x, idx, n_perm, rng):
    yrs = idx.year.to_numpy(); full = [y for y in np.unique(yrs) if (yrs == y).sum() == 12]
    pos = {y: np.where(yrs == y)[0] for y in full}; out = np.tile(x, (n_perm, 1))
    for i in range(n_perm):
        for a, b in zip(full, rng.permutation(full)): out[i, pos[a]] = x[pos[b]]
    return out

def frame(x, y, shifts):
    """Regular grid; column k holds y at t+shift_k aligned to the signal date t."""
    df = pd.concat([x.rename("x"), y.rename("y")], axis=1).sort_index()
    df = df.loc[max(x.first_valid_index(), y.first_valid_index()):]
    Y = np.vstack([df.y.shift(-s).to_numpy() for s in shifts])
    keep = df.x.notna().to_numpy() | np.isfinite(Y).any(axis=0)
    last = np.where(df.x.notna().to_numpy())[0].max() + 1
    return df.index[:last], df.x.to_numpy()[:last], Y[:, :last]

def stat(x, Y):
    r, n = _corr(x[None, :], np.isfinite(x)[None, :], Y, np.isfinite(Y))
    return r[0], n[0]

def null_max(xs, Y):
    r, _ = _corr(xs, np.isfinite(xs), Y, np.isfinite(Y))
    return r

def run_test(x, y, lags, latency, freq, seed=0, year_shuffle=False):
    rng = np.random.default_rng(seed); block = 6 if freq == "M" else 8
    shifts = [latency + k for k in lags]
    idx, xv, Y = frame(x.dropna(), y.dropna(), shifts)
    r, n = stat(xv, Y)
    if not np.isfinite(r).any(): return None
    b = int(np.nanargmax(np.abs(r))); out = dict(n=int(n[b]), best_lag=lags[b], r=float(r[b]), r_by_lag=[round(float(v), 4) for v in r], sample_start=str(idx[0].date()), sample_end=str(idx[-1].date()))
    m = np.isfinite(xv) & np.isfinite(Y[b]); out["beta"] = float(np.polyfit(xv[m], Y[b][m], 1)[0])
    out["spearman"] = float(pd.Series(xv[m]).corr(pd.Series(Y[b][m]), method="spearman"))
    S = surrogates(xv, block, N_PERM, rng); R = null_max(S, Y)
    out["perm_p"] = float((1 + np.sum(np.abs(R[:, b]) >= abs(r[b]))) / (1 + N_PERM))                 # single (best) lag, NOT corrected for the lag search
    out["maxstat_p"] = float((1 + np.sum(np.nanmax(np.abs(R), axis=1) >= np.nanmax(np.abs(r)))) / (1 + N_PERM))
    K = max(shifts) + 1; sh = np.arange(K, len(xv) - K)
    Rc = null_max(np.vstack([np.roll(xv, s) for s in sh]), Y)
    out["circ_p"] = float((1 + np.sum(np.nanmax(np.abs(Rc), axis=1) >= np.nanmax(np.abs(r)))) / (1 + len(sh))); out["circ_n_shifts"] = int(len(sh))
    if year_shuffle:
        Ry = null_max(year_surrogates(xv, idx, N_PERM, rng), Y)
        out["yearshuffle_p"] = float((1 + np.sum(np.nanmax(np.abs(Ry), axis=1) >= np.nanmax(np.abs(r)))) / (1 + N_PERM))
    # out-of-sample: first 60% of usable rows = train (choose lag + sign), last 40% = test
    use = np.where(np.isfinite(xv) & np.isfinite(Y).any(axis=0))[0]; cut = use[int(0.6 * len(use))]
    rt, nt = stat(xv[:cut], Y[:, :cut]); re_, ne = stat(xv[cut:], Y[:, cut:])
    if np.isfinite(rt).any():
        kb = int(np.nanargmax(np.abs(rt))); sg = np.sign(rt[kb])
        out.update(train_n=int(nt[kb]), test_n=int(ne[kb]), train_lag=lags[kb], r_train=float(rt[kb]), r_test=float(re_[kb]), split=str(idx[cut].date()))
        if np.isfinite(re_[kb]):
            Rt = null_max(surrogates(xv[cut:], block, N_PERM, rng), Y[kb:kb + 1, cut:])[:, 0]
            out["p_test"] = float((1 + np.sum(sg * Rt >= sg * re_[kb])) / (1 + N_PERM))
    return out

def bh(p):
    p = np.asarray(p, float); o = np.argsort(p); m = len(p)
    q = np.minimum.accumulate((p[o] * m / np.arange(1, m + 1))[::-1])[::-1]
    out = np.empty(m); out[o] = np.minimum(q, 1); return out

def residualise(y, F):
    d = pd.concat([y.rename("y"), F], axis=1).dropna()
    X = np.column_stack([np.ones(len(d)), d[F.columns].to_numpy()]); b = np.linalg.lstsq(X, d.y.to_numpy(), rcond=None)[0]
    return pd.Series(d.y.to_numpy() - X @ b, index=d.index)
