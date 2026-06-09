"""Italy adapter — Eurostat business demography (NUTS3) to canonical schema.

Source: Eurostat `bd_size_r3`, size class TOTAL, indicator V11920 (enterprise
births) and V11910 (active-enterprise stock). Ingested by
`src/data/ingest_italy_panel.py` into
`data/external/italy/processed/italy_births_panel_nuts3.csv`.

Target concept: enterprise_birth — demographic (economic) enterprise births from
the ASIA register, Eurostat-OECD aligned (2-year reactivation, births "from
scratch", excludes mergers/splits). Same concept as Portugal INE; suitable for
the harmonized enterprise_birth subpanel.

Coverage policy (no imputation):
  - Window default 2008-2020 (the bd_size_r3 published range).
  - Keep only region_ids present in EVERY year of the window (contiguous), so the
    European validator's no-year-gap rule holds. NUTS-version-transition codes
    that exist for only part of the window (e.g. Sardinia 2019 NUTS2021 changes)
    are DROPPED and listed, never merged or interpolated.
  - Suppressed/absent target cells within a kept region stay NaN and are masked
    (mask_target=0, flag_forecast_safe=0); never zero-filled.
  - Sector A10 births and the employment tensor are NOT available from this
    source at NUTS3; their columns are NaN with masks=0 (honest gap, documented).
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

_BASE = Path(__file__).resolve().parents[4]
_PANEL_PATH = _BASE / "data/external/italy/processed/italy_births_panel_nuts3.csv"

_SECTOR_COLS = ["BE", "FZ", "GI", "JZ", "KZ", "LZ", "MN", "OQ", "RU"]
_EU_COLS = [
    "eu_employment_rate_lag1", "eu_unemployment_rate_lag1", "eu_sts_turnover_lag1",
    "eu_esi_lag1", "eu_eei_lag1", "eu_credit_standards_lag1", "eu_gdp_growth_lag1",
]


class ITAdapter:
    country = "IT"
    region_level = "NUTS3"
    meta_region_system = "NUTS3"
    meta_source_label = "Eurostat-BD"  # bd_size_r3 (ISTAT/ASIA upstream)
    flag_target_concept = "enterprise_birth"

    def __init__(self, panel_path: Optional[Path] = None) -> None:
        self._panel_path = Path(panel_path) if panel_path else _PANEL_PATH
        self.dropped_regions: list[str] = []

    def build(self, year_min: int = 2008, year_max: int = 2020) -> pd.DataFrame:
        raw = pd.read_csv(self._panel_path)
        raw = raw[(raw["year"] >= year_min) & (raw["year"] <= year_max)].copy()
        years = list(range(year_min, year_max + 1))

        # Keep only regions with a NON-NULL birth in every year of the window
        # (pristine contiguous coverage). The ingest is a geo×year Cartesian, so a
        # NUTS-transition code (e.g. Sardinia NUTS2021 vs older codes) or a
        # heavily-suppressed province has NaN-filled years; those are DROPPED and
        # listed, never merged or imputed.
        nonnull = raw.dropna(subset=["births"]).groupby("region_id")["year"].nunique()
        keep = sorted(nonnull[nonnull == len(years)].index)
        all_regions = sorted(raw["region_id"].unique())
        self.dropped_regions = sorted(set(all_regions) - set(keep))
        raw = raw[raw["region_id"].isin(keep)].copy()
        raw = raw.sort_values(["region_id", "year"]).reset_index(drop=True)

        node_idx = {region: idx for idx, region in enumerate(keep)}

        # Lags/growth already causal in ingest; recompute on the kept window to be
        # safe (past-only; never future).
        raw["lag1_births"] = raw.groupby("region_id")["births"].shift(1)
        raw["lag2_births"] = raw.groupby("region_id")["births"].shift(2)
        raw["lag3_births"] = raw.groupby("region_id")["births"].shift(3)
        raw["stock_lag1"] = raw.groupby("region_id")["stock"].shift(1)
        raw["growth_1y"] = (raw["lag1_births"] - raw["lag2_births"]) / raw["lag2_births"]
        raw["growth_2y"] = (raw["lag1_births"] - raw["lag3_births"]) / raw["lag3_births"]

        out = pd.DataFrame()
        out["country"] = [self.country] * len(raw)
        out["region_id"] = raw["region_id"]
        out["region_name"] = raw["region_name"]
        out["region_level"] = [self.region_level] * len(raw)
        out["year"] = raw["year"].astype(int)
        out["node_idx"] = raw["region_id"].map(node_idx).astype(int)

        out["target_births"] = raw["births"].astype(float)
        out["lag1_births"] = raw["lag1_births"].astype(float)
        out["lag2_births"] = raw["lag2_births"].astype(float)
        out["lag3_births"] = raw["lag3_births"].astype(float)
        out["growth_1y"] = raw["growth_1y"].replace([np.inf, -np.inf], np.nan)
        out["growth_2y"] = raw["growth_2y"].replace([np.inf, -np.inf], np.nan)
        out["stock_lag1"] = raw["stock_lag1"].astype(float)

        # Sector A10 not available from bd_size_r3 at NUTS3 -> NaN + mask 0.
        for s in _SECTOR_COLS:
            out[f"sector_{s}"] = np.nan
        out["mask_sector_a10"] = 0.0

        out["mask_target"] = np.where(out["target_births"].notna(), 1.0, 0.0)
        out["mask_employment"] = 0.0  # no NUTS3 x A10 employment tensor ingested
        out["mask_tensor"] = 0.0

        out["flag_target_concept"] = [self.flag_target_concept] * len(out)
        out["flag_has_national_employment"] = 0
        out["flag_has_eurostat_bd"] = 1
        out["flag_is_covid_year"] = (out["year"] == 2020).astype(int)
        out["flag_is_rebound_year"] = (out["year"] == 2021).astype(int)
        out["flag_forecast_safe"] = np.where(
            out["target_births"].notna() & out["lag1_births"].notna(), 1, 0
        )

        out["meta_nuts3_code"] = raw["region_id"]
        out["meta_region_system"] = [self.meta_region_system] * len(out)
        out["meta_source_label"] = [self.meta_source_label] * len(out)

        # EU macro signals not overlaid for the standalone subpanel -> NaN + mask 0.
        for col in _EU_COLS:
            out[col] = np.nan
        out["mask_eu_signals"] = 0.0
        return out

    def validate(self, df: pd.DataFrame) -> dict:
        from src.data.european_panel.validation import validate_panel
        return validate_panel(df, country=self.country)
