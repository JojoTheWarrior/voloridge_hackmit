"""Shared change-detection machinery: per-pixel placebo-calibrated z-scores and blob extraction."""
import numpy as np
from scipy import ndimage as ndi

S8 = np.ones((3, 3), bool)


def robust_sigma(diffs, floor_q=50):
    """Per-pixel robust sigma over placebo differences [n,y,x], floored at the site-wide median sigma so
    that pixels which happened to be quiet in a handful of placebo pairs cannot produce huge z."""
    med = np.nanmedian(diffs, 0)
    sig = 1.4826 * np.nanmedian(np.abs(diffs - med), 0)
    floor = np.nanpercentile(sig, floor_q)
    return np.maximum(sig, floor)


def blobs(score, signed, valid, thr, min_px):
    """Connected components of score>thr inside valid, >= min_px. List of dicts sorted by area (desc)."""
    lab, n = ndi.label((score > thr) & valid, S8)
    if n == 0:
        return []
    ids = np.arange(1, n + 1)
    area = ndi.sum_labels(np.ones(score.shape, "float32"), lab, ids)
    ids = ids[area >= min_px]
    if len(ids) == 0:
        return []
    com = ndi.center_of_mass(np.ones(score.shape, "float32"), lab, ids)
    peak = ndi.maximum(score, lab, ids)
    mean = ndi.mean(np.nan_to_num(signed), lab, ids)
    out = [dict(npix=int(a), row=float(c[0]), col=float(c[1]), peak=float(p), mean_signed=float(m))
           for a, c, p, m in zip(area[area >= min_px], com, peak, mean)]
    return sorted(out, key=lambda b: -b["npix"])
