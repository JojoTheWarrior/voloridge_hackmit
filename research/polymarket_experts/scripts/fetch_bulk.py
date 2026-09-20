"""Read-only bounded bulk download; no API pagination and no credentials.

Fetch the registered audit slice from the cached immutable HF revision. To
extend coverage, choose explicit months; new research tests need a new labelled
exploratory plan, not modifications to prereg.json.
"""

import argparse
import json
from access import ROOT, show


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--months",
        nargs="+",
        default=[
            "2022-11",
            "2022-12",
            "2023-01",
            "2023-02",
            "2023-03",
            "2023-04",
            "2023-05",
            "2023-06",
        ],
    )
    args = parser.parse_args()
    info = ROOT / "data/access/hf_v1_info.body"
    if not info.exists():
        show(
            "hf_v1_info",
            "https://huggingface.co/api/datasets/wzsg/polymarket-orderfilled-v1",
        )
    revision = json.loads(info.read_text())["sha"]
    for month in args.months:
        if month not in [
            "2022-11",
            "2022-12",
            "2023-01",
            "2023-02",
            "2023-03",
            "2023-04",
            "2023-05",
            "2023-06",
        ]:
            raise ValueError(
                "This bounded fetcher downloads only the documented one-shard audit months"
            )
        dest = ROOT / "data/raw" / ("v1_" + month + ".parquet")
        if (
            dest.exists()
            or (month == "2022-11" and (ROOT / "data/raw/v1_nov2022.parquet").exists())
            or (month == "2022-12" and (ROOT / "data/raw/v1_dec2022.parquet").exists())
        ):
            continue
        b = show(
            "pinned_v1_" + month,
            f"https://huggingface.co/datasets/wzsg/polymarket-orderfilled-v1/resolve/{revision}/event_month={month}/data_0.parquet",
        )
        if b[:4] != b"PAR1":
            raise ValueError("Download is not a parquet file")
        dest.write_bytes(b)


if __name__ == "__main__":
    main()
