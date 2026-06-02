"""
eu_esi_lag1 — Economic Sentiment Indicator (ESI), national, annual mean.

Source : Eurostat ei_bssi_m_r2  (EC DG ECFIN Business & Consumer Surveys)
  indic = BS-ESI-I   (Economic sentiment indicator, long-run average = 100)
  s_adj = SA         (seasonally adjusted)
Monthly series → aggregated to a calendar-year mean.  A year is kept only if at
least ``MIN_MONTHS`` of its 12 months are present, so the annual value for
reference year t-1 is a full closed-year mean before forecasting t.

Note: the Employment Expectations Indicator (EEI) is *not* published as a clean
per-country annual series in this dataset and is left NaN (mask_eu_signals).
See HERALD_PHASE4E_MISSING_DATA_SEARCH.md (status: blocked) for EEI.
"""

from __future__ import annotations

from collections import defaultdict

from .eurostat_client import fetch, parse_time_series

DATASET = "ei_bssi_m_r2"
MIN_MONTHS = 10


def get_esi(countries: list[str], since: str = "2004-01",
            refresh: bool = False) -> dict[tuple[str, int], float]:
    """Return {(country, reference_year): annual_mean_ESI}."""
    out: dict[tuple[str, int], float] = {}
    for c in countries:
        data = fetch(
            DATASET,
            {"geo": c, "indic": "BS-ESI-I", "s_adj": "SA", "freq": "M",
             "sinceTimePeriod": since},
            refresh=refresh,
        )
        monthly = parse_time_series(data)  # {"YYYY-MM": value}
        by_year: dict[int, list[float]] = defaultdict(list)
        for label, val in monthly.items():
            year = int(label[:4])
            by_year[year].append(val)
        for year, vals in by_year.items():
            if len(vals) >= MIN_MONTHS:
                out[(c, year)] = sum(vals) / len(vals)
    return out
