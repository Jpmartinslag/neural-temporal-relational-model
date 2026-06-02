"""
France adapter — converts the existing Phase 3/4 France panel to the European
canonical schema.

Primary sources (already processed, local files):
  data/processed/dynamic_stgnn_feature_panel_v1.csv      — main panel (280 ZE2020, 2012-2024)
  data/processed/side_creations_a10_ze2020_v1.csv        — births by A10 sector

Target concept : establishment_creation (SIDE/SIRENE)
  France uses SIDE which counts 'créations d'établissements', not enterprises.
  flag_target_concept = 'establishment_creation'

Employment tensor: URSSAF (has_urssaf_source = 1 in original panel)
  flag_has_national_employment = 1

Sector births: SIDE A10 creations — full 9-sector breakdown, total = target
  sector_* = births by A10 sector at t-1 (lagged)
  mask_sector_a10 = 1.0 where sector data present

Notes:
  - ZE2020 codes are numeric INSEE identifiers (51, 52, ...)
  - region_id uses the ZE2020 code as-is (French national system, not NUTS3)
  - NUTS3 correspondence for ZE2020 is not 1:1; meta_nuts3_code left empty
  - node_idx from original panel (0-based integer, 0..279)
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

_BASE = Path(__file__).resolve().parents[4]  # dataset root
_PANEL_PATH = _BASE / "data/processed/dynamic_stgnn_feature_panel_v1.csv"
_A10_PATH   = _BASE / "data/processed/side_creations_a10_ze2020_v1.csv"

_SECTOR_COLS = ["BE", "FZ", "GI", "JZ", "KZ", "LZ", "MN", "OQ", "RU"]


class FranceAdapter:
    country        = "FR"
    region_level   = "ZE2020"
    meta_region_system = "ZE2020"
    meta_source_label  = "SIDE"
    flag_target_concept = "establishment_creation"

    def __init__(
        self,
        panel_path: Optional[Path] = None,
        a10_path:   Optional[Path] = None,
    ) -> None:
        self._panel_path = Path(panel_path) if panel_path else _PANEL_PATH
        self._a10_path   = Path(a10_path)   if a10_path   else _A10_PATH

    def build(
        self,
        year_min: int = 2012,
        year_max: int = 2024,
    ) -> pd.DataFrame:
        pan = pd.read_csv(self._panel_path)
        a10 = pd.read_csv(self._a10_path)

        # Filter year range
        pan = pan[(pan["target_year"] >= year_min) & (pan["target_year"] <= year_max)].copy()
        a10 = a10[(a10["target_year"] >= year_min) & (a10["target_year"] <= year_max)].copy()

        # Sector births at t-1: join A10 on (ZE2020, target_year+1)
        # A10 columns contain births for that year; we need births of t-1 as a feature for year t
        a10_shifted = a10.copy()
        a10_shifted["target_year"] = a10_shifted["target_year"] + 1  # shift: A10[t-1] → feature at year t
        a10_shifted = a10_shifted.rename(
            columns={s: f"sector_{s}" for s in _SECTOR_COLS}
        )
        a10_shifted["mask_sector_a10"] = 1.0
        a10_shifted = a10_shifted[["ZE2020", "target_year", "mask_sector_a10"]
                                   + [f"sector_{s}" for s in _SECTOR_COLS]]

        pan = pan.merge(a10_shifted, on=["ZE2020", "target_year"], how="left")

        # mask_sector_a10 = 0 when sector data not available (first year or gap)
        pan["mask_sector_a10"] = pan["mask_sector_a10"].fillna(0.0)

        # Build canonical panel
        out = pd.DataFrame()
        out["country"]       = [self.country] * len(pan)
        out["region_id"]     = pan["ZE2020"].astype(str)
        out["region_name"]   = pan.get("libze2020", pan["ZE2020"].astype(str))
        out["region_level"]  = [self.region_level] * len(pan)
        out["year"]          = pan["target_year"].astype(int)
        out["node_idx"]      = pan["node_idx"].astype(int)

        out["target_births"] = pan["side_establishment_creations_official"].astype(float)
        out["lag1_births"]   = pan["side_lag_1"].astype(float)
        out["lag2_births"]   = pan["side_lag_2"].astype(float)
        out["lag3_births"]   = pan["side_lag_3"].astype(float)
        out["growth_1y"]     = pan["growth_1y"].astype(float)
        out["growth_2y"]     = pan["growth_2y"].astype(float)
        out["stock_lag1"]    = pan["side_stock_total_t_minus_1"].astype(float)

        # Sector births (t-1 via shifted join)
        for s in _SECTOR_COLS:
            col = f"sector_{s}"
            out[col] = pan[col].astype(float) if col in pan.columns else np.nan

        out["mask_target"]      = np.where(out["target_births"].notna(), 1.0, 0.0)
        out["mask_sector_a10"]  = pan["mask_sector_a10"].astype(float)
        out["mask_employment"]  = pan.get("has_urssaf_source", pd.Series(1, index=pan.index)).astype(float)
        out["mask_tensor"]      = out["mask_employment"].astype(float)

        out["flag_target_concept"]          = [self.flag_target_concept] * len(out)
        out["flag_has_national_employment"] = pan.get("has_urssaf_source", pd.Series(1, index=pan.index)).astype(int)
        out["flag_has_eurostat_bd"]         = 0  # FR uses SIDE, not Eurostat BD as primary
        out["flag_is_covid_year"]           = pan["is_covid_year"].astype(int)
        out["flag_is_rebound_year"]         = pan["is_post_covid_rebound"].astype(int)
        out["flag_forecast_safe"]           = pan["feature_forecast_safe"].astype(int)
        out.loc[out["lag1_births"].isna(), "flag_forecast_safe"] = 0

        out["meta_nuts3_code"]    = [""] * len(out)  # ZE2020 ≠ NUTS3 (not 1:1)
        out["meta_region_system"] = [self.meta_region_system] * len(out)
        out["meta_source_label"]  = [self.meta_source_label] * len(out)

        # Optional EU signals — not yet loaded; appear as NaN
        for eu_col in [
            "eu_employment_rate_lag1", "eu_unemployment_rate_lag1",
            "eu_sts_turnover_lag1", "eu_esi_lag1", "eu_eei_lag1",
            "eu_credit_standards_lag1", "eu_gdp_growth_lag1",
        ]:
            out[eu_col] = np.nan
        out["mask_eu_signals"] = 0.0

        out = out.sort_values(["region_id", "year"]).reset_index(drop=True)
        return out

    def validate(self, df: pd.DataFrame, year_min: int = 2012, year_max: int = 2024) -> dict:
        from src.data.european_panel.validation import validate_panel
        return validate_panel(df, country=self.country,
                              expected_years=range(year_min, year_max + 1))
