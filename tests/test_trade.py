import numpy as np
import pandas as pd

from warsignal.analysis.trade import (
    evaluate_rule, forward_return, heuristic_actionability, instrument_from_indicator,
    rolling_zscore, target_kind_from_indicator, trade_idea_from_metrics,
)


def _index(n, start="2025-06-02"):
    return pd.bdate_range(start, periods=n)


def test_forward_return_compounds_without_lookahead():
    idx = _index(5)
    r = pd.Series([0.0, 0.1, 0.1, -0.05, 0.02], index=idx)
    fwd = forward_return(r, 2)
    assert np.isclose(fwd.iloc[0], 1.1 * 1.1 - 1)
    assert np.isclose(fwd.iloc[2], 0.95 * 1.02 - 1)
    assert fwd.iloc[-2:].isna().all()


def test_rolling_zscore_is_causal():
    idx = _index(40)
    s = pd.Series(np.arange(40, dtype=float), index=idx)
    z = rolling_zscore(s, 20)
    assert z.iloc[:9].isna().all()
    s2 = s.copy()
    s2.iloc[-1] = 1e6
    assert np.allclose(rolling_zscore(s2, 20).iloc[:-1].dropna(), z.iloc[:-1].dropna())


def test_evaluate_rule_finds_planted_edge():
    rng = np.random.default_rng(0)
    idx = _index(400, start="2025-03-03")
    signal = pd.Series(rng.normal(size=400), index=idx)
    spikes = signal > 1.5
    target = pd.Series(rng.normal(scale=0.005, size=400), index=idx)
    target[spikes.shift(1, fill_value=False)] += 0.03
    metrics = evaluate_rule(signal, target, expected_sign=1, holding_days=1, threshold=1.0, target_kind="return")
    overall = metrics["all"]
    assert overall["n_trades"] >= 5
    assert overall["hit_rate"] > 0.6
    assert overall["excess_return"] > 0
    assert overall["sharpe_like"] > 0
    assert -1.0 <= overall["max_drawdown"] <= 0.0
    assert metrics["fit_pre_war"]["n_trades"] + metrics["test_war"]["n_trades"] == overall["n_trades"]
    assert metrics["rule"]["direction"] == "long"
    assert len(metrics["trade_dates"]) == overall["n_trades"]
    idea = trade_idea_from_metrics(metrics, "FRO", "gdelt.gkg.hormuz_share")
    for key in ("instrument", "direction", "entry_rule", "exit_rule", "holding_days", "hit_rate",
                "avg_return", "n_trades", "sharpe_like", "caveats", "actionability"):
        assert key in idea
    assert idea["actionability"] >= 5


def test_evaluate_rule_short_and_no_overlap():
    idx = _index(120)
    signal = pd.Series(0.0, index=idx)
    signal.iloc[50:56] = 5.0  # six consecutive trigger days -> at most 2 trades with 3-day hold
    target = pd.Series(-0.01, index=idx)
    metrics = evaluate_rule(signal, target, expected_sign=-1, holding_days=3, target_kind="return")
    assert metrics["rule"]["direction"] == "short"
    assert metrics["all"]["n_trades"] == 2
    assert metrics["all"]["avg_return"] > 0


def test_evaluate_rule_handles_empty_and_nans():
    idx = _index(30)
    signal = pd.Series(np.nan, index=idx)
    target = pd.Series(np.nan, index=idx)
    metrics = evaluate_rule(signal, target)
    assert metrics["all"]["n_trades"] == 0
    assert heuristic_actionability(metrics) == 0.0
    assert heuristic_actionability(None) == 0.0


def test_indicator_helpers():
    assert instrument_from_indicator("finance.FRO.log_return") == "FRO"
    assert instrument_from_indicator("finance.spread.brent_wti") == "spread:brent_wti"
    assert instrument_from_indicator("gdelt.gkg.oil_share") == "gdelt.gkg.oil_share"
    assert target_kind_from_indicator("finance.FRO.log_return") == "log_return"
    assert target_kind_from_indicator("finance.FRO.close") == "level"
    assert target_kind_from_indicator("finance.ratio.jets_spy") == "level"
    assert target_kind_from_indicator("finance.spread.brent_wti") == "diff"
    assert target_kind_from_indicator("weather.doha.temp_mean") == "return"


def test_actionability_in_jev_questions_and_result_row():
    from warsignal.ai.prompts import JEV_QUESTIONS
    from warsignal.mission.model import MissionPlan, MissionResult

    assert JEV_QUESTIONS["actionability"]["type"] == "score"
    assert len(JEV_QUESTIONS["actionability"]["criteria"]) == len(JEV_QUESTIONS["validity"]["criteria"])
    result = MissionResult("M1", "now", "h", MissionPlan("a.x", "finance.FRO.log_return"),
                           scores={"actionability": 7.0}, trade_idea={"instrument": "FRO", "n_trades": 9})
    row = result.to_row()
    assert row["actionability"] == 7.0
    assert row["trade_instrument"] == "FRO" and row["trade_n"] == 9
