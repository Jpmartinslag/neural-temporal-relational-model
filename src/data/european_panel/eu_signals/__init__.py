"""
HERALD European Panel — EU common signal loaders (Phase 4E-C).

These loaders fetch harmonised macro signals from official sources (Eurostat,
EC DG ECFIN, ECB) and expose them as **annual, national, lag-1-safe** series.

Causality contract (enforced by assemble.attach_eu_signals)
-----------------------------------------------------------
A feature on panel row with target year ``t`` may only use information from the
*closed* reference year ``t-1``.  Each loader therefore returns a mapping

    {(country, reference_year): value}

and the assembler writes ``eu_<x>_lag1`` at panel year ``t`` from reference year
``t-1``.  Quarterly/monthly series are aggregated to a full calendar-year mean
*before* lagging, so every month used is closed before year ``t`` begins.

Rules (see reports/HERALD_PHASE4E_MISSING_DATA_SEARCH.md):
  * Never use year-t data to predict t.
  * Missing values stay NaN — never imputed as 0.
  * National coverage is repeated across a country's regions and documented as a
    national-level signal (meta_source_label unchanged; signals are national).
"""

from .assemble import attach_eu_signals, EU_SIGNAL_SPECS  # noqa: F401
