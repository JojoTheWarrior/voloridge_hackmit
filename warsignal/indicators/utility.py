from __future__ import annotations

import pandas as pd

from warsignal.config import DATA_RAW
from .base import IndicatorSpec, register


def _load(name):
    path = DATA_RAW / "pudl" / f"{name}.parquet"
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_parquet(path)


def _demand(group=None, peak=False):
    frame = _load("out_eia930__hourly_aggregated_demand")
    if group and "aggregation_group" in frame:
        frame = frame[frame.aggregation_group.str.lower() == group.lower()]
    frame["date"] = pd.to_datetime(frame.datetime_utc).dt.floor("D")
    col = "demand_imputed_pudl_mwh"
    return frame.groupby("date")[col].max() if peak else frame.groupby("date")[col].sum()


register(IndicatorSpec("utility.us.demand_mwh", "utility", "US electricity demand", "MWh", "D"), lambda: _demand())
register(IndicatorSpec("utility.us.demand_peak_mwh", "utility", "US demand peak", "MWh", "D"), lambda: _demand(peak=True))
register(IndicatorSpec("utility.us.demand_anomaly", "utility", "US demand same-weekday 2025 anomaly", "MWh", "D"),
         lambda: _demand() - _demand().loc[lambda s: s.index.year == 2025].groupby(lambda d: d.dayofyear).transform("mean").reindex(_demand().index, method="nearest"))
for ba in ("ERCO", "PJM", "MISO", "CISO", "NYIS", "ISNE", "SWPP"):
    register(IndicatorSpec(f"utility.{ba}.demand_mwh", "utility", f"{ba} demand", "MWh", "D"), lambda ba=ba: _demand(ba.lower()))


def _fuel(fuel):
    frame = _load("out_eia923__monthly_fuel_receipts_costs")
    frame = frame[frame.fuel_type_code_pudl.astype(str).str.lower().str.contains(fuel)]
    weighted = frame["fuel_cost_per_mmbtu"] * frame["fuel_received_mmbtu"]
    return weighted.groupby(frame["report_date"]).sum().divide(
        frame["fuel_received_mmbtu"].groupby(frame["report_date"]).sum()
    )


for fuel in ("gas", "coal", "oil"):
    register(IndicatorSpec(f"utility.fuel_cost.{fuel}_per_mmbtu", "utility", f"{fuel} delivered fuel cost", "USD/MMBtu", "M"),
             lambda fuel=fuel: _fuel(fuel))


def _generation(fuel):
    frame = _load("out_eia923__monthly_generation_fuel_combined")
    frame = frame[frame.fuel_type_code_pudl.astype(str).str.lower().str.contains(fuel)]
    return frame.groupby("report_date").net_generation_mwh.sum()


for fuel in ("coal", "gas", "oil", "nuclear", "solar", "wind", "hydro"):
    register(IndicatorSpec(f"utility.generation.{fuel}_mwh", "utility", f"{fuel} generation", "MWh", "M"),
             lambda fuel=fuel: _generation(fuel))


def _share(fuel):
    frame = _load("out_eia923__monthly_generation_fuel_combined")
    total = frame.groupby("report_date").net_generation_mwh.sum()
    return _generation(fuel).divide(total)


for fuel in ("coal", "gas", "oil"):
    register(IndicatorSpec(f"utility.generation.{fuel}_share", "utility", f"{fuel} generation share", "share", "M"),
             lambda fuel=fuel: _share(fuel))


def _capacity(kind):
    frame = _load("core_eia860m__changelog_generators")
    date_col = "generator_operating_date" if kind == "new" else "generator_retirement_date"
    frame[date_col] = pd.to_datetime(frame[date_col], errors="coerce")
    return frame.dropna(subset=[date_col]).groupby(frame[date_col].dt.to_period("M").dt.to_timestamp()).capacity_mw.sum()


register(IndicatorSpec("utility.generators.new_capacity_mw", "utility", "New generator capacity", "MW", "M"), lambda: _capacity("new"))
register(IndicatorSpec("utility.generators.retired_capacity_mw", "utility", "Retired generator capacity", "MW", "M"), lambda: _capacity("retired"))
