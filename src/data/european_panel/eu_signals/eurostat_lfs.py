"""
eu_employment_rate_lag1 and eu_unemployment_rate_lag1 — national, annual (LFS).

Sources (Eurostat, annual, national):
  Employment rate   : lfsi_emp_a  indic_em=EMP_LFS, unit=PC_POP, age=Y20-64, sex=T
                      → employment rate of the 20-64 population (%).
  Unemployment rate : une_rt_a    age=Y15-74, unit=PC_ACT, sex=T
                      → unemployed as % of the active population (%).

Both are annual averages of the EU Labour Force Survey, published ~6 months
after the reference year.  Reference year t-1 is closed before forecasting t.

National coverage: these national values are repeated across the country's
regions by the assembler and documented as national-level signals.  Regional
NUTS2 variants (lfst_r_lfe2emprt / lfst_r_lfu3rt) exist and can replace the
national series later without changing the schema field name.
"""

from __future__ import annotations

from .eurostat_client import fetch, parse_time_series

EMP_DATASET = "lfsi_emp_a"
UNEMP_DATASET = "une_rt_a"


def get_employment_rate(countries: list[str], refresh: bool = False) -> dict[tuple[str, int], float]:
    """Return {(country, reference_year): employment_rate_20_64_pct}."""
    out: dict[tuple[str, int], float] = {}
    for c in countries:
        data = fetch(
            EMP_DATASET,
            {"geo": c, "indic_em": "EMP_LFS", "unit": "PC_POP",
             "age": "Y20-64", "sex": "T", "freq": "A"},
            refresh=refresh,
        )
        for year_label, val in parse_time_series(data).items():
            out[(c, int(year_label))] = val
    return out


def get_unemployment_rate(countries: list[str], refresh: bool = False) -> dict[tuple[str, int], float]:
    """Return {(country, reference_year): unemployment_rate_15_74_pct}."""
    out: dict[tuple[str, int], float] = {}
    for c in countries:
        data = fetch(
            UNEMP_DATASET,
            {"geo": c, "age": "Y15-74", "unit": "PC_ACT", "sex": "T", "freq": "A"},
            refresh=refresh,
        )
        for year_label, val in parse_time_series(data).items():
            out[(c, int(year_label))] = val
    return out
