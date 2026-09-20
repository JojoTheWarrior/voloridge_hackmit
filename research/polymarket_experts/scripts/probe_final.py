import json
from access import ROOT, show

j = json.loads((ROOT / "data/access/v2_activity.body").read_bytes())
w = json.loads((ROOT / "data/access/leaderboard_probe.body").read_bytes())[0][
    "proxyWallet"
]
c = j.get("pagination", {}).get("next_cursor")
if c:
    show(
        "v2_activity_page2_user",
        "https://data-api.polymarket.com/v2/activity",
        {"user": w, "cursor": c},
    )
show("edge_initializer", "https://edge.goldsky.com/data/docs/swagger-initializer.js")
show("pmxt_v2", "https://archive.pmxt.dev/Polymarket/v2")
# Fetch official CTF source to identify actual lifecycle events in receipts.
show(
    "ctf_source",
    "https://raw.githubusercontent.com/gnosis/conditional-tokens-contracts/master/contracts/ConditionalTokens.sol",
)
show(
    "kaggle_view",
    "https://www.kaggle.com/api/v1/datasets/view/ethanbensadoun/polymarket-dataset",
)
show(
    "mirror_issue",
    "https://huggingface.co/api/discussions/SII-WANGZJ/Polymarket_data/4",
)
