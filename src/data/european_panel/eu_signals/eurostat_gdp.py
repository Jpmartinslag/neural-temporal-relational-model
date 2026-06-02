"""
eu_gdp_growth_lag1 — real GDP growth, national, annual.

Source : Eurostat nama_10_gdp
  na_item = B1GQ   (Gross domestic product at market prices)
  unit    = CLV_PCH_PRE  (chain-linked volumes, % change on previous year)
Concept: real GDP volume growth rate (%).  Annual, national.
Publication lag: t-1 first estimate ~Feb of year t; final ~Sep.  Annual value
for reference year t-1 is therefore closed and available before forecasting t.
"""

from __future__ import annotations

from .eurostat_client import fetch, parse_time_series

DATASET = "nama_10_gdp"


def get_gdp_growth(countries: list[str], refresh: bool = False) -> dict[tuple[str, int], float]:
    """Return {(country, reference_year): real_gdp_growth_pct}."""
    out: dict[tuple[str, int], float] = {}
    for c in countries:
        data = fetch(
            DATASET,
            {"geo": c, "na_item": "B1GQ", "unit": "CLV_PCH_PRE", "freq": "A"},
            refresh=refresh,
        )
        for year_label, val in parse_time_series(data).items():
            out[(c, int(year_label))] = val
    return out
