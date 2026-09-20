"""Brazil ONS open data (anonymous S3): per-plant hourly generation -> monthly MWh, reservoir registry, capacity,
daily hydrology -> monthly, and subsystem energy balance -> monthly. Raw hourly files are streamed, not kept."""
import pandas as pd
import s3fs

from common import DATA

P = "ons-aws-prod-opendata/dataset/"
fs = s3fs.S3FileSystem(anon=True)
OUT = DATA / "ons"
OUT.mkdir(exist_ok=True)


def num(s):
    return pd.to_numeric(s.astype(str).str.replace(",", "."), errors="coerce")


def read(path):
    with fs.open(path) as f:
        return pd.read_parquet(f)


if not (OUT / "gen_monthly.parquet").exists():
    parts = []
    for path in sorted(x for x in fs.ls(P + "geracao_usina_2_ho") if x.endswith(".parquet")):
        d = read(path)
        d["val_geracao"] = num(d.val_geracao)  # MWmed over the hour == MWh
        d["month"] = pd.to_datetime(d.din_instante).dt.to_period("M").dt.to_timestamp()
        m = d.groupby(["month", "nom_tipousina", "id_subsistema", "nom_usina", "id_ons", "ceg"], dropna=False).agg(
            mwh=("val_geracao", "sum"), hours=("val_geracao", "count")).reset_index()
        parts.append(m)
        print(path.split("/")[-1], len(d), flush=True)
    m = pd.concat(parts).groupby(["month", "nom_tipousina", "id_subsistema", "nom_usina", "id_ons", "ceg"], dropna=False).sum().reset_index()
    m.to_parquet(OUT / "gen_monthly.parquet")

read(P + "reservatorio/RESERVATORIOS.parquet").to_parquet(OUT / "reservatorios.parquet")
read(P + "capacidade-geracao/CAPACIDADE_GERACAO.parquet").to_parquet(OUT / "capacidade.parquet")

if not (OUT / "hidro_monthly.parquet").exists():
    parts = []
    for path in sorted(x for x in fs.ls(P + "dados_hidrologicos_di") if x.endswith(".parquet")):
        d = read(path)
        cols = [c for c in d.columns if c.startswith("val_")]
        for c in cols:
            d[c] = num(d[c])
        d["month"] = pd.to_datetime(d.din_instante).dt.to_period("M").dt.to_timestamp()
        parts.append(d.groupby(["month", "nom_reservatorio"])[cols].mean().reset_index())
        print(path.split("/")[-1], flush=True)
    pd.concat(parts).to_parquet(OUT / "hidro_monthly.parquet")

if not (OUT / "balanco_monthly.parquet").exists():
    parts = []
    for path in sorted(x for x in fs.ls(P + "balanco_energia_subsistema_ho") if x.endswith(".parquet")):
        d = read(path)
        cols = [c for c in d.columns if c.startswith("val_")]
        for c in cols:
            d[c] = num(d[c])
        d["month"] = pd.to_datetime(d.din_instante).dt.to_period("M").dt.to_timestamp()
        parts.append(d.groupby(["month", "id_subsistema"])[cols].sum().reset_index())
    pd.concat(parts).groupby(["month", "id_subsistema"]).sum().reset_index().to_parquet(OUT / "balanco_monthly.parquet")
print("done")
