import json
from access import ROOT, show

base = "https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw/subgraphs/"
for name, version in [
    ("orderbook", "0.0.1"),
    ("positions", "0.0.7"),
    ("activity", "0.0.4"),
    ("pnl", "0.0.14"),
]:
    u = base + name + "-subgraph/" + version + "/gn"
    show(
        "goldsky_" + name,
        u,
        post={
            "query": "{ _meta { block { number } hasIndexingErrors } __schema { queryType { fields { name } } } }"
        },
    )
    show(
        "schema_" + name,
        "https://raw.githubusercontent.com/Polymarket/polymarket-subgraph/main/"
        + name
        + "-subgraph/schema.graphql",
    )
show("goldsky_docs", "https://docs.goldsky.com/chains/polymarket")
show("cryptohouse", "https://crypto.clickhouse.com")
for month in ["2023-01", "2023-02", "2023-03", "2023-04", "2023-05", "2023-06"]:
    b = show(
        "v1_" + month,
        "https://huggingface.co/datasets/wzsg/polymarket-orderfilled-v1/resolve/main/event_month="
        + month
        + "/data_0.parquet",
    )
    if b[:4] == b"PAR1":
        (ROOT / "data/raw" / ("v1_" + month + ".parquet")).write_bytes(b)
# Kaggle metadata query is a public GET, not a login or terms acceptance.
try:
    j = json.loads((ROOT / "data/access/kaggle_orderfilled.body").read_bytes())
    for i, x in enumerate(j[:3]):
        ref = x.get("ref")
        if ref:
            show(
                "kaggle_detail_" + str(i),
                "https://www.kaggle.com/api/v1/datasets/list/" + ref,
            )
except (ValueError, TypeError):
    pass
