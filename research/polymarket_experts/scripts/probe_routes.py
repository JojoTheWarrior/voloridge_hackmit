"""Bounded route probes, after bulk-mirror evaluation; never a full API crawl."""

import json
import re
from access import show, ROOT


def main():
    show("blockchain_docs", "https://docs.polymarket.com/resources/blockchain-data.md")
    show("rates_docs", "https://docs.polymarket.com/api-reference/rate-limits.md")
    for kind in ["trades", "positions", "activity", "holders", "leaderboard"]:
        show(
            "v2_docs_" + kind, "https://data-api.polymarket.com/v2/docs"
        ) if kind == "trades" else None
    show(
        "kaggle_orderfilled",
        "https://www.kaggle.com/api/v1/datasets/list",
        {"search": "polymarket OrderFilled"},
    )
    show("pmxt_archive", "https://archive.pmxt.dev/Polymarket")
    show(
        "gamma_probe",
        "https://gamma-api.polymarket.com/markets",
        {"limit": 2, "closed": "true"},
    )
    b = show(
        "leaderboard_probe",
        "https://data-api.polymarket.com/v1/leaderboard",
        {"category": "OVERALL", "timePeriod": "ALL", "orderBy": "PNL", "limit": 3},
    )
    try:
        wallets = [x["proxyWallet"] for x in json.loads(b)]
    except (ValueError, KeyError, TypeError):
        wallets = []
    # Names and biographies must never flow into analytic tables or displayed outputs.
    for i, w in enumerate(wallets):
        for route in ["positions", "closed-positions", "activity", "trades"]:
            show(
                f"{route}_{i}",
                "https://data-api.polymarket.com/" + route,
                {"user": w, "limit": 5},
            )
        show(
            f"leaderboard_wallet_{i}",
            "https://data-api.polymarket.com/v1/leaderboard",
            {"user": w, "timePeriod": "ALL", "limit": 1},
        )
    show(
        "trades_depth",
        "https://data-api.polymarket.com/trades",
        {"limit": 1, "offset": 10001},
    )
    if wallets:
        show(
            "activity_depth",
            "https://data-api.polymarket.com/activity",
            {"user": wallets[0], "limit": 1, "offset": 10001},
        )
        show(
            "v2_trades",
            "https://data-api.polymarket.com/v2/trades",
            {"user": wallets[0], "limit": 2},
        )
        show(
            "v2_activity",
            "https://data-api.polymarket.com/v2/activity",
            {"user": wallets[0], "limit": 2},
        )
        show(
            "v2_positions",
            "https://data-api.polymarket.com/v2/positions",
            {"user": wallets[0], "limit": 2},
        )
    markets = json.loads((ROOT / "data/access/gamma_probe.body").read_bytes())
    if markets:
        m = markets[0]
        tokens = m.get("clobTokenIds", "[]")
        tokens = json.loads(tokens) if isinstance(tokens, str) else tokens
        if tokens:
            show(
                "clob_history_old",
                "https://clob.polymarket.com/prices-history",
                {"market": tokens[0], "interval": "max", "fidelity": 60},
            )
        show(
            "holders_probe",
            "https://data-api.polymarket.com/holders",
            {"market": m["conditionId"], "limit": 5},
        )
    docs = (ROOT / "data/access/blockchain_docs.body").read_text()
    urls = list(
        dict.fromkeys(re.findall(r'https://api\.goldsky\.com/[^\s\)"<>]+', docs))
    )
    (ROOT / "data/access/goldsky_urls.json").write_text(json.dumps(urls, indent=2))
    for i, u in enumerate(urls):
        show(
            "goldsky_" + str(i),
            u,
            {
                "query": "{ _meta { block { number } hasIndexingErrors } __schema { queryType { fields { name } } } }"
            },
        )
    for i, u in enumerate(
        [
            "https://polygon-bor-rpc.publicnode.com",
            "https://polygon.drpc.org",
            "https://polygon-rpc.com",
        ]
    ):
        b = show(
            "rpc_head_" + str(i),
            u,
            post={"jsonrpc": "2.0", "id": 1, "method": "eth_blockNumber", "params": []},
        )
        try:
            head = int(json.loads(b)["result"], 16)
        except (ValueError, KeyError, TypeError):
            continue
        ctf = "0x4D97DCd97eC945f40cF65F87097ACe5EA0476045"
        show(
            "rpc_ctf_logs_" + str(i),
            u,
            post={
                "jsonrpc": "2.0",
                "id": 2,
                "method": "eth_getLogs",
                "params": [
                    {"address": ctf, "fromBlock": hex(head - 10), "toBlock": hex(head)}
                ],
            },
        )
        show(
            "rpc_early_ctf_" + str(i),
            u,
            post={
                "jsonrpc": "2.0",
                "id": 3,
                "method": "eth_getLogs",
                "params": [
                    {
                        "address": ctf,
                        "fromBlock": hex(35896869),
                        "toBlock": hex(35896969),
                    }
                ],
            },
        )


if __name__ == "__main__":
    main()
