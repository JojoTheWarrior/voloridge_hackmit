"""Fetch EPA GHGRP subpart HH (municipal landfill) tables from Envirofacts (keyless REST)."""
import io, time, requests, pandas as pd
UA = {"User-Agent": "kingdom-hackathon-research/0.1"}
def table(name, step=10000):
    fr, a = [], 0
    while True:
        r = requests.get(f"https://data.epa.gov/efservice/{name}/rows/{a}:{a+step-1}/CSV", headers=UA, timeout=600)
        r.raise_for_status()
        d = pd.read_csv(io.StringIO(r.text)) if r.text.strip() else pd.DataFrame()
        fr.append(d); print(name, a, len(d), flush=True); a += step
        if len(d) < step: break
        time.sleep(1)
    out = pd.concat(fr); out.to_csv(f"data/ghgrp_{name}.csv", index=False); return out
for t in ["hh_subpart_level_information", "hh_landfill_info", "hh_gas_collection_system_detls"]:
    try: print(t, table(t).shape)
    except Exception as e: print("FAILED", t, e)
