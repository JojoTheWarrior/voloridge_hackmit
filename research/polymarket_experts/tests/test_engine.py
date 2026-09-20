"""Synthetic accounting fixtures test code only; never research observations."""

import sys
from pathlib import Path
from decimal import Decimal as D
import json
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from ledger import Delta, Resolution, Ledger, IncompleteLedger, decode_v1_maker
from inference import bh, paired_bootstrap, max_statistic, loss_delta
from panel import consensus, empty_panel

ROOT = Path(__file__).resolve().parents[1]


def event(t, kind, tokens, cash, condition="c", basis=None):
    return Delta(
        t,
        t,
        0,
        0,
        str(t),
        "0xABC",
        condition,
        kind,
        {k: D(str(v)) for k, v in tokens.items()},
        D(str(cash)),
        True,
        D(str(basis)) if basis is not None else None,
    )


def resolved(ledger, t=20):
    ledger.resolve(Resolution("c", "NBA", t, {"yes": D(1), "no": D(0)}, True))


def test_no_future_resolution_or_transaction():
    ledger = Ledger(True)
    ledger.add(event(10, "trade", {"yes": 100}, -40))
    resolved(ledger)
    assert ledger.snapshot(10) == {}
    assert ledger.past_pnl(20) == {}
    assert ledger.past_pnl(21)["0xabc"]["pnl"] == 60


def test_redemption_does_not_double_count_payout():
    ledger = Ledger(True)
    ledger.add(event(10, "trade", {"yes": 100}, -40))
    resolved(ledger)
    ledger.add(event(30, "redeem", {"yes": -100}, 100))
    assert (
        ledger.past_pnl(21)["0xabc"]["pnl"] == ledger.past_pnl(31)["0xabc"]["pnl"] == 60
    )


def test_split_merge_fee_roundtrip():
    ledger = Ledger(True)
    ledger.add(event(10, "split", {"yes": 100, "no": 100}, -100))
    ledger.add(event(11, "merge", {"yes": -60, "no": -60}, 60))
    ledger.add(event(12, "trade", {"yes": -40}, 23.9))
    resolved(ledger)
    assert ledger.past_pnl(21)["0xabc"]["pnl"] == D("-16.1")


def test_negative_inventory_rejected():
    ledger = Ledger(True)
    ledger.add(event(10, "trade", {"yes": -1}, 0.5))
    with pytest.raises(IncompleteLedger):
        ledger.snapshot(11)


def test_unaudited_and_duplicate_rejected():
    with pytest.raises(IncompleteLedger):
        Ledger().add(event(1, "split", {"yes": 1, "no": 1}, -1))
    ledger = Ledger(True)
    e = event(1, "split", {"yes": 1, "no": 1}, -1)
    ledger.add(e)
    with pytest.raises(IncompleteLedger):
        ledger.add(e)


def test_transfer_basis_required_and_supported():
    ledger = Ledger(True)
    with pytest.raises(IncompleteLedger):
        ledger.add(event(1, "transfer", {"yes": 10}, 0))
    ledger.add(event(1, "transfer", {"yes": 10}, 0, basis=-4))
    resolved(ledger)
    assert ledger.past_pnl(21)["0xabc"]["pnl"] == 6


def test_neg_risk_conversion_rejects_unknown_allocation():
    with pytest.raises(IncompleteLedger):
        Ledger(True).add(event(1, "neg_risk_conversion", {"yes": 10}, 0))


def test_fractional_resolution():
    ledger = Ledger(True)
    ledger.add(event(1, "trade", {"yes": 10}, -4))
    ledger.resolve(Resolution("c", "NBA", 2, {"yes": D(".5"), "no": D(".5")}, True))
    assert ledger.past_pnl(3)["0xabc"]["pnl"] == 1


def test_unverified_resolution_rejected():
    with pytest.raises(IncompleteLedger):
        Ledger(True).resolve(Resolution("c", "NBA", 1, {"yes": D(1), "no": D(0)}))


def test_v1_fee_is_in_received_asset():
    x = dict(
        maker="0xABC",
        maker_asset_id="0",
        taker_asset_id="123",
        maker_amount_filled="4000000",
        taker_amount_filled="10000000",
        fee="100000",
    )
    r = decode_v1_maker(x)
    assert r["shares"] == D("9.9") and r["cash"] == -4
    x.update(
        maker_asset_id="123",
        taker_asset_id="0",
        maker_amount_filled="10000000",
        taker_amount_filled="4000000",
    )
    r = decode_v1_maker(x)
    assert r["shares"] == -10 and r["cash"] == D("3.9")


def test_bh_full_family_and_missing():
    p = [0.001, 0.03, np.nan, 0.7]
    q = bh(p, 4)
    assert (
        q[0] == pytest.approx(0.004) and q[1] == pytest.approx(0.06) and np.isnan(q[2])
    )
    with pytest.raises(ValueError):
        bh(p, 3)


def test_bootstrap_minimum_and_behavior():
    with pytest.raises(ValueError):
        paired_bootstrap(np.arange(20))
    x = np.linspace(0.01, 0.03, 60)
    result = paired_bootstrap(x)
    assert (
        result["ci_low"] > 0
        and result["resamples"] == 10000
        and result["mde_80pct"] > 0
    )
    assert paired_bootstrap(-x)["estimate"] == pytest.approx(-result["estimate"])


def test_max_stat_null():
    x = np.tile([-0.1, 0.1], 30)
    assert max_statistic(np.column_stack([x, -x])) == 1


def test_loss_differences():
    assert loss_delta([1], [0.5], [0.9])[0] > 0
    assert np.isfinite(loss_delta([1], [0], [1], "logloss")).all()


def test_no_experts_is_missing_not_half():
    s = consensus(Ledger(True), "c", "NBA", 10, "yes", "no")
    assert s["n_experts"] == 0 and np.isnan(s["expert_prob"])
    assert empty_panel().empty


def test_three_public_wallet_pnl_definitions():
    # Cross-endpoint consistency only, NOT independent engine reconstruction.
    for i in range(3):
        b = json.loads((ROOT / f"data/access/v2_board_{i}.body").read_text())["data"]
        p = json.loads((ROOT / f"data/access/v2_pnl_{i}.body").read_text())["data"][
            "points"
        ][-1]
        assert b["pnl"] == pytest.approx(p["realized_pnl"], abs=0.02)
        assert p["realized_pnl"] == pytest.approx(
            p["realized_market_pnl"] + p["realized_lp_pnl"] + p["realized_combo_pnl"],
            abs=0.02,
        )


def test_v2_buy_fee_is_collateral():
    from ledger import decode_v2_maker

    x = dict(
        maker="0xABC",
        token_id="123",
        side=0,
        maker_amount_filled="4000000",
        taker_amount_filled="10000000",
        fee="100000",
    )
    r = decode_v2_maker(x)
    assert r["shares"] == 10 and r["cash"] == D("-4.1")


def test_real_receipts_match_bulk_fields():
    import pandas as pd

    p = ROOT / "data/receipt_audit.parquet"
    x = pd.read_parquet(p)
    matched = x[x.is_orderfilled]
    assert len(matched) == 6 and matched.bulk_match.all()
