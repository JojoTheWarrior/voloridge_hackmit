"""Small read-only historical log probes for both exchanges and CTF finality."""

import json
from access import ROOT, show
from Crypto.Hash import keccak

abi = json.loads((ROOT / "data/access/ctf_abi.body").read_text())["abi"]
topics = {}
for item in abi:
    if item["type"] != "event":
        continue
    signature = item["name"] + "(" + ",".join(x["type"] for x in item["inputs"]) + ")"
    k = keccak.new(digest_bits=256)
    k.update(signature.encode())
    topics["0x" + k.hexdigest()] = item["name"]
(ROOT / "data/ctf_event_topics.json").write_text(json.dumps(topics, indent=2))
for label, address in [
    ("ctf_exchange_v1", "0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E"),
    ("negrisk_exchange_v1", "0xC5d563A36AE78145C45a50134d48A1215220f80a"),
]:
    show(
        "rpc_" + label,
        "https://polygon.drpc.org",
        post={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "eth_getLogs",
            "params": [
                {
                    "address": address,
                    "fromBlock": hex(70000000),
                    "toBlock": hex(70000010),
                }
            ],
        },
    )
# This is a bounded historical sample, not a finality crawler.
show(
    "rpc_payout_sample",
    "https://polygon.drpc.org",
    post={
        "jsonrpc": "2.0",
        "id": 2,
        "method": "eth_getLogs",
        "params": [
            {
                "address": "0x4D97DCd97eC945f40cF65F87097ACe5EA0476045",
                "topics": [
                    [k for k, v in topics.items() if v == "ConditionResolution"][0]
                ],
                "fromBlock": hex(70000000),
                "toBlock": hex(70001000),
            }
        ],
    },
)
