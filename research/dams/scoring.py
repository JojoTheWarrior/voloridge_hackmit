"""Skill metrics on generation anomalies, shared by the US validation and the transfer tests."""
import numpy as np

RNG = np.random.default_rng(0)


def metrics(te, pred, label):
    rows = []
    d = te[["gww_id", "month", "y", "gen_clim", "gen_mean", "mwh"]].copy()
    for name in pred.columns:
        d["p"] = pred[name].values
        ok = d.dropna(subset=["p"])
        sse = lambda x: ((x.y - x.p) ** 2).sum()
        skill = 1 - sse(ok) / (ok.y ** 2).sum()
        per = ok.groupby("gww_id").apply(lambda x: np.corrcoef(x.y, x.p)[0, 1] if len(x) >= 24 and x.p.std() > 0 and x.y.std() > 0 else np.nan)
        ann = ok.assign(yr=ok.month.dt.year).groupby(["gww_id", "yr"]).agg(y=("y", "mean"), p=("p", "mean"), n=("y", "size")).query("n>=10")
        # cluster bootstrap over dams for the skill score
        by = {g: x for g, x in ok.groupby("gww_id")}
        keys = list(by)
        num = np.array([sse(by[g]) for g in keys])
        den = np.array([(by[g].y ** 2).sum() for g in keys])
        bs = []
        for _ in range(400):
            i = RNG.integers(0, len(keys), len(keys))
            bs.append(1 - num[i].sum() / den[i].sum())
        lvl = ok.assign(obs=ok.mwh / ok.gen_mean, hat=(ok.gen_clim + ok.p * ok.gen_mean) / ok.gen_mean)
        lvl = lvl.assign(obs_c=lvl.obs - lvl.groupby("gww_id").obs.transform("mean"), hat_c=lvl.hat - lvl.groupby("gww_id").obs.transform("mean"))
        r2_level = 1 - ((lvl.obs_c - lvl.hat_c) ** 2).sum() / (lvl.obs_c ** 2).sum()
        rows.append({"design": label, "model": name, "n_dams": ok.gww_id.nunique(), "n_dam_months": len(ok),
                     "anom_skill_vs_clim": skill, "skill_ci_lo": np.percentile(bs, 2.5), "skill_ci_hi": np.percentile(bs, 97.5),
                     "anom_r_pooled": np.corrcoef(ok.y, ok.p)[0, 1] if ok.p.std() > 0 else np.nan,
                     "anom_r_median_per_dam": per.median(), "share_dams_r_gt_0.3": (per > 0.3).mean(),
                     "annual_anom_r": np.corrcoef(ann.y, ann.p)[0, 1] if ann.p.std() > 0 else np.nan,
                     "level_r2_within_dam": r2_level})
    return rows
