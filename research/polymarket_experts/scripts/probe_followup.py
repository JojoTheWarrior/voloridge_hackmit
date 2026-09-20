import json
import pandas as pd
from access import ROOT, show

for route in ["v2_activity", "v2_trades"]:
    j = json.loads((ROOT / "data/access" / f"{route}.body").read_bytes())
    c = j.get("pagination", {}).get("next_cursor")
    if c:
        show(
            route + "_page2",
            "https://data-api.polymarket.com/" + route.replace("_", "/"),
            {"cursor": c},
        )
wallets = [
    x["proxyWallet"]
    for x in json.loads((ROOT / "data/access/leaderboard_probe.body").read_bytes())
]
for i, w in enumerate(wallets):
    show(
        f"v2_board_{i}",
        "https://data-api.polymarket.com/v2/leaderboard",
        {"user": w, "time_period": "all"},
    )
    show(f"v2_pnl_{i}", "https://data-api.polymarket.com/v2/user-pnl", {"user": w})
    show(
        f"v2_first_activity_{i}",
        "https://data-api.polymarket.com/v2/activity",
        {"user": w, "start": 1, "sort_direction": "ASC", "limit": 2},
    )
x = pd.read_parquet(ROOT / "data/raw/v1_nov2022.parquet")
for i, tx in enumerate(x.transaction_hash.unique()[:3]):
    tx = "0x" + tx.removeprefix("0x")
    show(
        "receipt_" + str(i),
        "https://polygon.drpc.org",
        post={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "eth_getTransactionReceipt",
            "params": [tx],
        },
    )
show(
    "ctf_abi",
    "https://raw.githubusercontent.com/Polymarket/polymarket-subgraph/main/abis/ConditionalTokens.json",
)
show(
    "v1_trading",
    "https://raw.githubusercontent.com/Polymarket/ctf-exchange/main/src/exchange/mixins/Trading.sol",
)
show(
    "v2_trading",
    "https://raw.githubusercontent.com/Polymarket/ctf-exchange-v2/main/src/exchange/mixins/Trading.sol",
)
show("edge_docs", "https://edge.goldsky.com/data/docs/")
