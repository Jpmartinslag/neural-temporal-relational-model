"""
Assemble EU common signals onto a country panel (lag-1 safe overlay).

This is a *post-processing* step applied after a country adapter has built its
panel.  It does not touch the adapter or the model core: it only fills the
``eu_*_lag1`` columns (already present as NaN) and recomputes
``mask_eu_signals``.

Causality
---------
Panel row with target year ``t`` receives the signal's value for reference year
``t-1``.  Annual sources are used directly; monthly/quarterly sources are
aggregated to a full closed calendar year inside their loader before lagging.

Robustness
----------
If a source cannot be fetched (no network *and* no on-disk cache), the
corresponding column is left NaN and a warning is printed — the build never
crashes on a missing optional signal.  Once raw JSON is cached under
``data/raw/european_panel/eurostat/`` the overlay is fully offline/reproducible.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..schema import EU_SIGNAL_FIELDS
from . import eurostat_gdp, eurostat_lfs, ec_bcs, ecb_bls

# schema field  ->  (human concept, getter callable returning {(country, ref_year): value})
EU_SIGNAL_SPECS: dict[str, tuple[str, object]] = {
    "eu_gdp_growth_lag1":        ("Eurostat nama_10_gdp real GDP growth %",        eurostat_gdp.get_gdp_growth),
    "eu_employment_rate_lag1":   ("Eurostat lfsi_emp_a employment rate 20-64 %",   eurostat_lfs.get_employment_rate),
    "eu_unemployment_rate_lag1": ("Eurostat une_rt_a unemployment rate 15-74 %",   eurostat_lfs.get_unemployment_rate),
    "eu_esi_lag1":               ("Eurostat ei_bssi_m_r2 ESI annual mean",         ec_bcs.get_esi),
    "eu_credit_standards_lag1":  ("ECB BLS SME credit standards diffusion index",  ecb_bls.get_credit_standards),
}

# Signals intentionally left NaN for now (documented in the search report).
# eu_sts_turnover_lag1   : Eurostat sts_trtu_a is trade-only, sector-inconsistent
# eu_eei_lag1            : no clean per-country annual EEI series


def attach_eu_signals(df: pd.DataFrame, country: str,
                      refresh: bool = False, verbose: bool = True) -> pd.DataFrame:
    """
    Overlay eu_*_lag1 columns onto ``df`` (in place on a copy) and recompute
    ``mask_eu_signals``.  ``country`` is the ISO-2 geo code (FR/NL/BE/PT).
    """
    df = df.copy()
    filled: list[str] = []

    for field, (concept, getter) in EU_SIGNAL_SPECS.items():
        try:
            series = getter([country], refresh=refresh)  # {(country, ref_year): value}
        except Exception as exc:  # noqa: BLE001 — degrade gracefully, never crash build
            if verbose:
                print(f"      ⚠  EU signal {field} unavailable ({type(exc).__name__}: {exc}). Left NaN.")
            continue

        # feature at target year t uses reference year t-1
        values = df["year"].map(lambda t: series.get((country, int(t) - 1), np.nan))
        n_ok = int(values.notna().sum())
        if n_ok > 0:
            df[field] = values.astype(float)
            filled.append(f"{field}={n_ok}")

    # mask_eu_signals = fraction of the 7 canonical eu_* fields observed per row
    eu_cols = [c for c in EU_SIGNAL_FIELDS if c in df.columns]
    if eu_cols:
        df["mask_eu_signals"] = df[eu_cols].notna().mean(axis=1).astype(float)

    if verbose:
        cov = df["mask_eu_signals"].mean() if "mask_eu_signals" in df else 0.0
        print(f"      EU signals [{country}]: {', '.join(filled) if filled else 'none'} "
              f"| mean mask_eu_signals={cov:.3f}")
    return df
