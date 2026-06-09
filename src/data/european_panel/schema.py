"""
HERALD European Panel — canonical data contract.

Every country adapter must produce a DataFrame conforming to REQUIRED_FIELDS.
OPTIONAL_FIELDS are included when the source exists; absent columns must appear
as NaN (not dropped), so the validation layer can report coverage systematically.

Field naming convention
-----------------------
  target_*      : quantity being forecast (observable at year end)
  lag1_*        : value of * at t-1 (available when forecasting t)
  growth_*      : year-on-year log-ratio or pct-change, computed at t-1
  sector_*      : A10 sector breakdown of the target
  eu_*          : harmonised Eurostat / ECB signal, usually NUTS2 or national
  mask_*        : 0/1 or float in [0,1]; 1 = fully observed, 0 = unobserved
  flag_*        : binary quality / provenance indicator
  meta_*        : non-predictive metadata (region name, source label, ...)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Field catalogue
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FieldSpec:
    name: str
    dtype: str          # "float64" | "int64" | "str" | "object"
    required: bool
    temporal_role: str  # "id" | "target" | "feature_t1" | "feature_static" | "mask" | "flag" | "meta"
    description: str
    source_hint: str    # which Eurostat/national source typically fills this


FIELD_CATALOGUE: list[FieldSpec] = [

    # ── Identifiers ────────────────────────────────────────────────────────
    FieldSpec("country",      "str",     True,  "id",
              "ISO 3166-1 alpha-2 (FR, NL, BE, PT, …)",
              "dataset config"),
    FieldSpec("region_id",    "str",     True,  "id",
              "Canonical NUTS3-2021 code (e.g. NL310, BE100, PT111). "
              "Use national identifier when NUTS3 not available; document in meta_region_system.",
              "national + Eurostat NUTS correspondence table"),
    FieldSpec("region_name",  "str",     True,  "meta",
              "Human-readable region label (original language).",
              "national statistical office"),
    FieldSpec("region_level", "str",     True,  "meta",
              "Administrative level: NUTS3 | NUTS2 | LAU2 | COROP | arrondissement | ZE2020 | …",
              "dataset config"),
    FieldSpec("year",         "int64",   True,  "id",
              "Calendar year of the observation (target year t).",
              "dataset config"),
    FieldSpec("node_idx",     "int64",   True,  "id",
              "Integer index (0-based, stable within a country run). "
              "Must be consistent with adjacency matrix row/column order.",
              "adapter"),

    # ── Target ─────────────────────────────────────────────────────────────
    FieldSpec("target_births", "float64", True, "target",
              "Number of enterprise / establishment births in year t. "
              "Concept must be consistent within a country across years; "
              "cross-country comparisons require source_quality_flags.",
              "Eurostat BD (bd_hgnace_r) or national (SIDE/CBS/StatBel/INE)"),

    # ── Lagged target features (available at forecast time) ────────────────
    FieldSpec("lag1_births",   "float64", True,  "feature_t1",
              "target_births at t-1.",
              "derived from target_births"),
    FieldSpec("lag2_births",   "float64", False, "feature_t1",
              "target_births at t-2.",
              "derived from target_births"),
    FieldSpec("lag3_births",   "float64", False, "feature_t1",
              "target_births at t-3.",
              "derived from target_births"),
    FieldSpec("growth_1y",     "float64", True,  "feature_t1",
              "Percent change (target_births_t-1 - target_births_t-2) / target_births_t-2. NaN if either is missing.",
              "derived"),
    FieldSpec("growth_2y",     "float64", False, "feature_t1",
              "Percent change (target_births_t-1 - target_births_t-3) / target_births_t-3.",
              "derived"),
    FieldSpec("stock_lag1",    "float64", False, "feature_t1",
              "Total active enterprise stock at end of t-1.",
              "Eurostat BD (bd_hgnace_r active_ent) or national"),

    # ── Sector breakdown of target (A10 mapping) ───────────────────────────
    FieldSpec("sector_BE",  "float64", False, "feature_t1",
              "A10 sector BE births at t-1 (Manufacture intensive energy / heavy industry proxy).",
              "Eurostat BD or national sector tables"),
    FieldSpec("sector_FZ",  "float64", False, "feature_t1",
              "A10 sector FZ births at t-1 (Construction).",
              "Eurostat BD or national sector tables"),
    FieldSpec("sector_GI",  "float64", False, "feature_t1",
              "A10 sector GI births at t-1 (Trade, transport, accommodation).",
              "Eurostat BD or national sector tables"),
    FieldSpec("sector_JZ",  "float64", False, "feature_t1",
              "A10 sector JZ births at t-1 (Information & communication).",
              "Eurostat BD or national sector tables"),
    FieldSpec("sector_KZ",  "float64", False, "feature_t1",
              "A10 sector KZ births at t-1 (Finance & insurance).",
              "Eurostat BD or national sector tables"),
    FieldSpec("sector_LZ",  "float64", False, "feature_t1",
              "A10 sector LZ births at t-1 (Real estate).",
              "Eurostat BD or national sector tables"),
    FieldSpec("sector_MN",  "float64", False, "feature_t1",
              "A10 sector MN births at t-1 (Professional / scientific / technical + support).",
              "Eurostat BD or national sector tables"),
    FieldSpec("sector_OQ",  "float64", False, "feature_t1",
              "A10 sector OQ births at t-1 (Public admin, education, health + other services).",
              "Eurostat BD or national sector tables"),
    FieldSpec("sector_RU",  "float64", False, "feature_t1",
              "A10 sector RU births at t-1 (Arts, entertainment, other personal services).",
              "Eurostat BD or national sector tables"),

    # ── European common signals (NUTS2 or national, lag-1 safe) ───────────
    FieldSpec("eu_employment_rate_lag1", "float64", False, "feature_t1",
              "Employment rate (%) at NUTS2 or national level, year t-1. "
              "Source: Eurostat LFS (lfst_r_lfe2emprt). "
              "Temporal causal: published ~6 months after reference year.",
              "Eurostat LFS"),
    FieldSpec("eu_unemployment_rate_lag1", "float64", False, "feature_t1",
              "Unemployment rate (%) at NUTS2 or national level, year t-1.",
              "Eurostat LFS (lfst_r_lfu3rt)"),
    FieldSpec("eu_sts_turnover_lag1", "float64", False, "feature_t1",
              "Short-term business statistics: turnover index (base 100), "
              "national, annual average of monthly indices at t-1. "
              "Source: Eurostat STS (sts_trtu_a). Covers B-N sectors.",
              "Eurostat STS"),
    FieldSpec("eu_esi_lag1", "float64", False, "feature_t1",
              "Economic Sentiment Indicator (ESI), annual average, national, t-1. "
              "Source: Eurostat/EC Business and Consumer Surveys. "
              "Published monthly; annual average available before end of year.",
              "Eurostat / EC DG ECFIN"),
    FieldSpec("eu_eei_lag1", "float64", False, "feature_t1",
              "Employment Expectations Indicator (EEI), annual average, national, t-1. "
              "Source: EC Business and Consumer Surveys.",
              "EC DG ECFIN"),
    FieldSpec("eu_credit_standards_lag1", "float64", False, "feature_t1",
              "ECB Bank Lending Survey: net % of banks tightening credit standards "
              "for SME loans, annual average, t-1. Negative = easing. "
              "Coverage: Euro Area members only (FR, NL, BE, PT covered). "
              "Published quarterly; annual aggregation is safe.",
              "ECB BLS"),
    FieldSpec("eu_gdp_growth_lag1", "float64", False, "feature_t1",
              "Real GDP growth rate (%), national, t-1. "
              "Source: Eurostat nama_10_gdp. Widely available, high quality.",
              "Eurostat / Eurostat nama_10_gdp"),

    # ── Coverage masks ─────────────────────────────────────────────────────
    FieldSpec("mask_target",         "float64", True, "mask",
              "1.0 if target_births is observed, 0.0 if imputed or structurally absent. "
              "Loss function must be scaled by this mask.",
              "adapter"),
    FieldSpec("mask_sector_a10",     "float64", False, "mask",
              "Fraction of A10 sectors observed in this region-year (0–1). "
              "1.0 = all 9 sectors present; 0.0 = no sector breakdown available.",
              "adapter"),
    FieldSpec("mask_employment",     "float64", False, "mask",
              "1.0 if eu_employment_rate_lag1 is observed at NUTS3/NUTS2, "
              "0.5 if national proxy used, 0.0 if absent.",
              "adapter"),
    FieldSpec("mask_tensor",         "float64", False, "mask",
              "Quality/availability of the country-specific tensor for target year t. "
              "1.0 = genuine employment tensor available causally, 0.5 = useful proxy "
              "(for example births-by-sector), 0.0 = no tensor signal.",
              "adapter"),
    FieldSpec("mask_eu_signals",     "float64", False, "mask",
              "Proportion of eu_* fields that are non-NaN for this row (0–1).",
              "derived in validation"),

    # ── Source quality flags ───────────────────────────────────────────────
    FieldSpec("flag_target_concept",    "str",   True,  "flag",
              "Target concept identifier: 'establishment_creation' | 'enterprise_birth' | "
              "'enterprise_creation' | 'self_employment_entry' | 'mixed'. "
              "Cross-country comparison is only valid when concepts match.",
              "adapter"),
    FieldSpec("flag_has_national_employment", "int64", False, "flag",
              "1 if country-specific employment tensor available at zone×sector×year.",
              "adapter"),
    FieldSpec("flag_has_eurostat_bd",  "int64", False, "flag",
              "1 if Eurostat Business Demography is the primary target source.",
              "adapter"),
    FieldSpec("flag_is_covid_year",    "int64", True,  "flag",
              "1 for 2020 (primary disruption year). Country-specific if different.",
              "adapter"),
    FieldSpec("flag_is_rebound_year",  "int64", True,  "flag",
              "1 for 2021 (post-COVID rebound).",
              "adapter"),
    FieldSpec("flag_forecast_safe",    "int64", True,  "flag",
              "1 if all required lag-1 features are available (no lookahead risk). "
              "Rows with 0 must be excluded from model training and evaluation.",
              "adapter"),

    # ── Country metadata ───────────────────────────────────────────────────
    FieldSpec("meta_nuts3_code",     "str",   False, "meta",
              "NUTS3-2021 code. May differ from region_id if national system is used.",
              "Eurostat NUTS correspondence"),
    FieldSpec("meta_region_system",  "str",   True,  "meta",
              "Regional system used: NUTS3 | COROP | arrondissement | ZE2020 | commune | …",
              "adapter"),
    FieldSpec("meta_source_label",   "str",   True,  "meta",
              "Short label for primary target data source: "
              "SIDE | CBS | StatBel | INE | Eurostat-BD | …",
              "adapter"),
]

# ---------------------------------------------------------------------------
# Derived sets for quick lookup
# ---------------------------------------------------------------------------

REQUIRED_FIELDS: list[str] = [f.name for f in FIELD_CATALOGUE if f.required]
OPTIONAL_FIELDS: list[str] = [f.name for f in FIELD_CATALOGUE if not f.required]
ALL_FIELDS:      list[str] = [f.name for f in FIELD_CATALOGUE]
FIELD_BY_NAME:   dict[str, FieldSpec] = {f.name: f for f in FIELD_CATALOGUE}

SECTOR_FIELDS:    list[str] = [f.name for f in FIELD_CATALOGUE if f.name.startswith("sector_")]
EU_SIGNAL_FIELDS: list[str] = [f.name for f in FIELD_CATALOGUE if f.name.startswith("eu_")]
MASK_FIELDS:      list[str] = [f.name for f in FIELD_CATALOGUE if f.name.startswith("mask_")]
FLAG_FIELDS:      list[str] = [f.name for f in FIELD_CATALOGUE if f.name.startswith("flag_")]
ID_FIELDS:        list[str] = [f.name for f in FIELD_CATALOGUE if f.temporal_role == "id"]

# ---------------------------------------------------------------------------
# Fields that MUST NOT enter any predictive input (x_ann, q_tensor, regime
# vector, graph features, etc.).  Loaders and trainers must explicitly
# exclude these before assembling feature tensors.
# ---------------------------------------------------------------------------

# Manually-labelled historical events.  These flags encode researcher knowledge
# about specific calendar years (2020, 2021) and therefore constitute look-ahead
# information when used as features for future forecasts.  They are valid only
# as metadata for post-hoc analysis and as regime signals in audit-only mode
# (cf. herald_regime_modes.py "manual_flags" — explicitly documented as
# non-generalisable).
NON_PREDICTIVE_FIELDS: list[str] = [
    "flag_is_covid_year",    # 1 if year==2020; must not enter x_ann or regime
    "flag_is_rebound_year",  # 1 if year==2021; must not enter x_ann or regime
]

# Fields that are purely administrative / provenance / audit.
# These must never enter any model input regardless of ablation mode.
METADATA_FIELDS: list[str] = [f.name for f in FIELD_CATALOGUE if f.temporal_role == "meta"] + [
    "country",           # identifier, not a learnable feature
    "region_id",         # identifier
    "region_name",       # identifier
    "region_level",      # identifier
    "node_idx",          # structural index, not a feature
    "year",              # structural index, not a feature
    "flag_forecast_safe",     # row selector, not a feature
    "flag_target_concept",    # metadata
    "flag_has_national_employment",  # provenance flag
    "flag_has_eurostat_bd",          # provenance flag
    "mask_target",        # loss weight, not a feature
    "mask_sector_a10",    # loss weight, not a feature
    "mask_employment",    # availability/quality weight, not a feature
    "mask_tensor",        # availability/quality weight, not a feature
    "mask_eu_signals",    # availability/quality weight, not a feature
]

# Safe annual features for Phase 4E-A baseline (no EU signals, no sector).
# Structurally equivalent to Phase 4A "no_qtensor_control" feature set,
# but with growth_1y computed causally: (y[t-1]-y[t-2])/y[t-2].
# Phase 4A growth_1y was leaky — do not compare WMAPEs directly.
BASELINE_ANNUAL_FEATURES: list[str] = [
    "lag1_births",
    "lag2_births",
    "lag3_births",
    "growth_1y",
    "growth_2y",
]

# ---------------------------------------------------------------------------
# Schema completeness notes (to keep documentation accurate)
# ---------------------------------------------------------------------------
# Total fields catalogued in FIELD_CATALOGUE : 43
# Current adapters export all catalogue fields.  EU signal columns remain NaN
# until Phase 4E-C/D loaders are implemented, and mask_eu_signals is therefore
# 0.0 for now.

# ---------------------------------------------------------------------------
# Canonical empty panel (for adapter scaffolding)
# ---------------------------------------------------------------------------

def empty_panel() -> pd.DataFrame:
    """Return a zero-row DataFrame with all canonical columns and correct dtypes."""
    dtypes = {f.name: f.dtype for f in FIELD_CATALOGUE}
    df = pd.DataFrame({name: pd.Series(dtype=dtype) for name, dtype in dtypes.items()})
    return df


def validate_dtypes(df: pd.DataFrame) -> list[str]:
    """Return list of dtype mismatch warnings (non-fatal)."""
    issues = []
    for f in FIELD_CATALOGUE:
        if f.name not in df.columns:
            continue
        col = df[f.name]
        if f.dtype == "float64" and not pd.api.types.is_float_dtype(col):
            issues.append(f"{f.name}: expected float64, got {col.dtype}")
        elif f.dtype == "int64" and not pd.api.types.is_integer_dtype(col):
            issues.append(f"{f.name}: expected int64, got {col.dtype}")
    return issues
