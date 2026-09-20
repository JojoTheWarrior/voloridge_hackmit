"""Brazil ONS open data (anonymous S3): daily stored energy (EAR) by subsystem, weekly marginal cost (CMO), hourly energy balance."""
import s3fs, pandas as pd
from pathlib import Path
D = Path(__file__).parent / "data" / "ons"; D.mkdir(parents=True, exist_ok=True)
fs = s3fs.S3FileSystem(anon=True); R = "ons-aws-prod-opendata/dataset/"
for k in ["ear_subsistema_di", "cmo_se", "balanco_energia_subsistema_ho", "ena_subsistema_di"]:
    for p in fs.ls(R + k + "/"):
        if p.endswith(".parquet") and not (D / p.split("/")[-1]).exists():
            fs.get(p, str(D / p.split("/")[-1])); print(p.split("/")[-1], flush=True)
