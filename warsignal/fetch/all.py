from __future__ import annotations

import argparse
from datetime import date

from warsignal.fetch import finance, gdelt_live, materials_project, noaa_isd, open_meteo, open_meteo_aq, openalex, openaq, pudl

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true")
    args = parser.parse_args()
    from warsignal.config import END, START
    start, end = (date(2026, 2, 21), date(2026, 3, 7)) if args.quick else (START, END)
    run(quick=args.quick)


def run(quick=False):
    from warsignal.config import END, START
    start, end = (date(2026, 2, 21), date(2026, 3, 7)) if quick else (START, END)
    common = {"start": start, "end": end, "quick": quick}
    for module in (gdelt_live, noaa_isd, open_meteo, open_meteo_aq, openaq, openalex, materials_project, pudl):
        module.fetch(**common)
    finance.fetch(start=date(2025, 1, 1) if not quick else start, end=end, quick=quick)

if __name__ == "__main__":
    main()
