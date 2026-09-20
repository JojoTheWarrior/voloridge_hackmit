"""Conservative ledger for audited transaction-level cash/token changes.

Raw fills are NOT a ledger. Inputs must coalesce settlement transfers and fills
once per transaction/account/condition; lifecycle burns/mints must not be counted
again as generic transfers. Decimal amounts are in collateral/share units.
No inference of proxy ownership, missing basis, neg-risk conversion allocation,
or opening balances. Unknown economics invalidate affected accounts.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal

D = Decimal


class IncompleteLedger(ValueError):
    pass


@dataclass(frozen=True)
class Delta:
    timestamp: int
    block: int
    tx_index: int
    log_index: int
    tx_hash: str
    wallet: str
    condition: str
    kind: str
    tokens: dict[str, Decimal]
    cash: Decimal
    audited: bool = False
    basis_adjustment: Decimal | None = None


@dataclass(frozen=True)
class Resolution:
    condition: str
    category: str
    timestamp: int
    payouts: dict[str, Decimal]
    verified_onchain: bool = False


@dataclass
class Account:
    tokens: dict = field(default_factory=lambda: defaultdict(D))
    cash: Decimal = D(0)
    cost: Decimal = D(0)


class Ledger:
    def __init__(self, opening_state_verified=False):
        self.opening_state_verified = opening_state_verified
        self.events = []
        self.ids = set()
        self.resolutions = {}

    def add(self, e):
        if not self.opening_state_verified or not e.audited:
            raise IncompleteLedger(
                "Opening state and transaction deltas must be audited"
            )
        if e.kind not in {
            "trade",
            "split",
            "merge",
            "redeem",
            "transfer",
            "neg_risk_conversion",
            "fee",
            "rebate",
        }:
            raise IncompleteLedger("Unknown lifecycle event")
        if e.kind in {"transfer", "neg_risk_conversion"} and e.basis_adjustment is None:
            raise IncompleteLedger(
                "Unknown transferred basis or cross-condition allocation"
            )
        key = (e.tx_hash.lower(), e.wallet.lower(), e.condition)
        if key in self.ids:
            raise IncompleteLedger(
                "Duplicate transaction/account/condition; coalesce first"
            )
        self.ids.add(key)
        self.events.append(e)

    def resolve(self, r):
        if not r.verified_onchain:
            raise IncompleteLedger(
                "Scheduled end and Gamma closedTime are not payout finality"
            )
        if (
            not r.payouts
            or any(p < 0 or p > 1 for p in r.payouts.values())
            or sum(r.payouts.values()) != 1
        ):
            raise IncompleteLedger("Invalid complete outcome payout vector")
        self.resolutions[r.condition] = r

    def snapshot(self, t):
        accounts = defaultdict(Account)
        for e in sorted(
            self.events, key=lambda x: (x.timestamp, x.block, x.tx_index, x.log_index)
        ):
            if e.timestamp >= t:
                continue
            a = accounts[(e.wallet.lower(), e.condition)]
            for token, delta in e.tokens.items():
                a.tokens[token] += delta
                if a.tokens[token] < 0:
                    raise IncompleteLedger(
                        "Negative inventory: missing event/opening balance"
                    )
            flow = e.cash + (e.basis_adjustment or D(0))
            a.cash += flow
            if flow < 0:
                a.cost -= flow
        return accounts

    def past_pnl(self, t, category=None):
        """Resolution-accrual PnL, only markets finalized strictly before t.

        Include unredeemed payout entitlement exactly once. Later redemption
        replaces token entitlement by cash and leaves PnL unchanged. This differs
        from a provider's sale-realized PnL on still-open markets.
        """
        out = defaultdict(
            lambda: {"pnl": D(0), "cost": D(0), "n_markets": 0, "wins": 0}
        )
        for (w, c), a in self.snapshot(t).items():
            r = self.resolutions.get(c)
            if r is None or r.timestamp >= t or (category and r.category != category):
                continue
            if any(token not in r.payouts for token in a.tokens):
                raise IncompleteLedger("Unmapped outcome token")
            pnl = a.cash + sum(q * r.payouts[token] for token, q in a.tokens.items())
            out[w]["pnl"] += pnl
            out[w]["cost"] += a.cost
            out[w]["n_markets"] += 1
            out[w]["wins"] += int(pnl > 0)
        return dict(out)


def decode_v1_maker(row):
    """Only maker perspective; V1 fee is denominated in received asset.

    For matched taker orders a separate OrderFilled maker row already exists.
    Do not append a synthetic opposite taker row. This is a fill audit adapter,
    not a claim to complete inventory or basis.
    """
    ma, ta = str(row["maker_asset_id"]), str(row["taker_asset_id"])
    making, taking, fee = (
        D(str(row[k])) / D(10**6)
        for k in ["maker_amount_filled", "taker_amount_filled", "fee"]
    )
    if ma == "0" and ta != "0":
        return {
            "wallet": row["maker"].lower(),
            "token": ta,
            "shares": taking - fee,
            "cash": -making,
            "side": "BUY",
            "price": making / taking if taking else None,
        }
    if ta == "0" and ma != "0":
        return {
            "wallet": row["maker"].lower(),
            "token": ma,
            "shares": -making,
            "cash": taking - fee,
            "side": "SELL",
            "price": taking / making if making else None,
        }
    raise IncompleteLedger(
        "Non collateral/token fill needs explicit cross-token decoding"
    )


def decode_v2_maker(row):
    """V2 fees use collateral for both sides, unlike V1 BUY share fees."""
    making, taking, fee = (
        D(str(row[k])) / D(10**6)
        for k in ["maker_amount_filled", "taker_amount_filled", "fee"]
    )
    side = int(row["side"])
    if side == 0:
        return {
            "wallet": row["maker"].lower(),
            "token": str(row["token_id"]),
            "shares": taking,
            "cash": -making - fee,
            "side": "BUY",
            "price": making / taking if taking else None,
        }
    if side == 1:
        return {
            "wallet": row["maker"].lower(),
            "token": str(row["token_id"]),
            "shares": -making,
            "cash": taking - fee,
            "side": "SELL",
            "price": taking / making if making else None,
        }
    raise IncompleteLedger("Unknown V2 side")
