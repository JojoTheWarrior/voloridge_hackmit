"""Fetch the PUDL tables used here (anonymous S3). Reuses the scout's copies via symlink when present to save disk."""
import s3fs

from common import DATA, ROOT

TABLES = ["core_eia923__monthly_generation_fuel", "core_eia__entity_plants", "core_eia860__scd_generators",
          "core_eia860__scd_plants", "core_eia930__hourly_net_generation_by_energy_source"]
SCOUT = ROOT.parent / "scout" / "data"
fs = s3fs.S3FileSystem(anon=True)
for t in TABLES:
    dst = DATA / f"{t}.parquet"
    if dst.exists():
        continue
    src = SCOUT / f"{t}.parquet"
    if src.exists():
        dst.symlink_to(src)
        print("linked", t)
    else:
        fs.get(f"pudl.catalyst.coop/nightly/{t}.parquet", str(dst))
        print("downloaded", t)
