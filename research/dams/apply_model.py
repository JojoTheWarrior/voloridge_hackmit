"""Apply the saved US-trained models to any set of reservoirs (no labels needed)."""
import lightgbm as lgb

from common import ROOT
from features import AREA_FEATS, CLIM_FEATS, PHASE_FEATS, STATIC_FEATS, build

FEATSETS = {"gbm_area": AREA_FEATS + PHASE_FEATS + STATIC_FEATS,
            "gbm_climate": CLIM_FEATS + PHASE_FEATS + STATIC_FEATS,
            "gbm_area+climate": AREA_FEATS + CLIM_FEATS + PHASE_FEATS + STATIC_FEATS}


def predict(panel, st, clim):
    """Returns the feature table plus pred_<model>, and pred_lo / pred_hi (10-90 % band of the full model)."""
    df = build(panel, st, clim, ref_end=None)
    df = df[df.a0.notna()].copy()
    for name, cols in FEATSETS.items():
        df[f"pred_{name}"] = lgb.Booster(model_file=str(ROOT / "models" / f"{name}.txt")).predict(df[cols])
    full = "gbm_area+climate"
    for q, c in ((10, "pred_lo"), (90, "pred_hi")):
        df[c] = lgb.Booster(model_file=str(ROOT / "models" / f"{full}_q{q}.txt")).predict(df[FEATSETS[full]])
    df["pred_lo"] = df[["pred_lo", f"pred_{full}"]].min(axis=1)
    df["pred_hi"] = df[["pred_hi", f"pred_{full}"]].max(axis=1)
    return df
