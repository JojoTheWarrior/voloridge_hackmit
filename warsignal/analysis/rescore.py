"""Recompute Round 2 trade rules uniformly from published run folders.

Usage: ``python -m warsignal.analysis.rescore [--out missions/round2_trades.csv]``

Reads every ``missions/status/R2-*.json`` with a run folder, reloads ``raw_a.csv`` /
``raw_b.csv`` and ``plan.json``, and re-evaluates the rubric rule with the current
``warsignal.analysis.trade`` code so all missions are scored with the same logic
(early Round 2 children ran before the target-kind fix). Only finance targets whose
P&L is meaningful (``log_return``, ``close``, ``spread``, ``ratio``) are scored.
"""
from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path

import pandas as pd

from warsignal.analysis.stats import transform
from warsignal.analysis.trade import (
    evaluate_rule, heuristic_actionability, instrument_from_indicator, target_kind_from_indicator,
)
from warsignal.config import ROOT

TRADEABLE_KINDS = {"log_return", "level", "diff"}


def _series(path):
    df = pd.read_csv(path, parse_dates=["date"]).dropna()
    return pd.Series(df["value"].to_numpy(dtype="float64"), index=pd.DatetimeIndex(df["date"])).sort_index()


def rescore_run(folder, plan=None):
    folder = Path(folder)
    plan = plan or json.loads((folder / "plan.json").read_text())
    stats = json.loads((folder / "stats.json").read_text())
    if plan.get("mode") == "single" or not (folder / "data" / "raw_b.csv").exists():
        return None
    kind = target_kind_from_indicator(plan["indicator_b"])
    if kind not in TRADEABLE_KINDS:
        return None
    a = _series(folder / "data" / "raw_a.csv")
    b = _series(folder / "data" / "raw_b.csv")
    best_lag = (stats.get("lagged") or {}).get("best_lag")
    holding = int(best_lag) if best_lag and best_lag > 0 else 1
    sign = plan.get("expected_sign") or (1 if ((stats.get("lagged") or {}).get("best_r") or 0) >= 0 else -1)
    metrics = evaluate_rule(transform(a, plan.get("transform_a", "level")), b, expected_sign=sign,
                            holding_days=holding, target_kind=kind)
    metrics["actionability"] = heuristic_actionability(metrics)
    metrics["instrument"] = instrument_from_indicator(plan["indicator_b"])
    metrics["target_kind"] = kind
    metrics["perm_p"] = stats.get("perm_p")
    metrics["bonferroni_p"] = stats.get("bonferroni_p")
    metrics["n_obs"] = stats.get("n_obs")
    return metrics


def rescore_all(status_dir=ROOT / "missions" / "status"):
    rows = []
    for path in sorted(glob.glob(str(status_dir / "R2-*.json"))):
        st = json.loads(Path(path).read_text())
        folder = st.get("run_folder")
        if st.get("state") != "done" or not folder or not (ROOT / folder / "plan.json").exists():
            continue
        try:
            m = rescore_run(ROOT / folder)
        except Exception as exc:  # keep going; report the failure row
            rows.append({"mission_id": st["mission_id"], "error": str(exc)[:120]})
            continue
        if m is None:
            continue
        rule, al, fit, test = m["rule"], m["all"], m["fit_pre_war"], m["test_war"]
        plan_signal = json.loads((ROOT / folder / "plan.json").read_text())["indicator_a"]
        rows.append({
            "mission_id": st["mission_id"], "parent": st.get("parent_mission_id"),
            "hypothesis": st["hypothesis"], "run_folder": folder,
            "signal": plan_signal, "instrument": m["instrument"], "direction": rule["direction"],
            "holding_days": rule["holding_days"], "target_kind": m["target_kind"],
            "n_trades": al["n_trades"], "hit_rate": al["hit_rate"], "avg_return": al["avg_return"],
            "baseline_avg_return": al["baseline_avg_return"], "excess_return": al["excess_return"],
            "sharpe_like": al["sharpe_like"], "max_drawdown": al["max_drawdown"], "total_return": al["total_return"],
            "fit_n": fit["n_trades"], "fit_hit": fit["hit_rate"], "fit_avg": fit["avg_return"],
            "test_n": test["n_trades"], "test_hit": test["hit_rate"], "test_avg": test["avg_return"],
            "test_excess": test["excess_return"],
            "perm_p": m["perm_p"], "bonferroni_p": m["bonferroni_p"], "n_obs": m["n_obs"],
            "actionability": m["actionability"],
        })
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "missions" / "round2_trades.csv"))
    args = ap.parse_args()
    df = rescore_all()
    df.to_csv(args.out, index=False)
    ok = df[df.get("error").isna()] if "error" in df else df
    print(f"{len(ok)} rules rescored -> {args.out}")
    cols = ["mission_id", "instrument", "direction", "holding_days", "n_trades", "hit_rate", "excess_return",
            "sharpe_like", "test_n", "test_hit", "test_excess", "actionability"]
    print(ok.sort_values("actionability", ascending=False)[cols].head(15).to_string(index=False))


if __name__ == "__main__":
    main()
