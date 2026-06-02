"""
Netherlands adapter — converts Phase 4 NL panel to the European canonical schema.

Primary sources (already processed, local files):
  data/processed/phase4/nl/panel_ze2020.csv       — main panel (40 COROP, 2015-2025)
  data/processed/phase4/nl/a10_ze2020.csv         — employment Q-tensor (jobs, NOT births by sector)
  data/processed/phase4/nl/zone_mapping.csv        — zone_id (CR01..CR40) → node index
  data/external/netherlands/processed/
    netherlands_births_panel.csv                   — raw births with growth/lag
    netherlands_stock_panel.csv                    — enterprise stock
    netherlands_qtensor_jobs_panel.csv             — employment by A10 × COROP × year
    netherlands_sector_births_cbs_83631NED_corop_a10.csv
                                                    — births by HERALD A10 × COROP × year

Target concept: enterprise_birth (CBS OprichtingenVanVestigingen)
  NL CBS counts enterprise births (vestigingen), not legal entities.
  flag_target_concept = 'enterprise_birth'

Sector births: available from CBS 83631NED at COROP × SBI aggregate level.
  sector_* = births by HERALD A10 at t-1; mask_sector_a10 = 1 where present.
  flag_has_national_employment = 1 (employment tensor IS available)

Employment tensor: CBS 83582NED (jobs by SBI-A10 × COROP)
  Used at training time as Q-tensor feature, not embedded in this panel.

Notes:
  - COROP codes CR01..CR40 are Dutch national codes (not NUTS3)
  - node_idx from zone_mapping (0-based, stable)
  - 2025 target is available; qtensor stops at 2024 (no CBS jobs for 2025)
  - has_urssaf_source = 0 (no URSSAF equivalent; ONSS/CBS not included here)
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

_BASE = Path(__file__).resolve().parents[4]
_PANEL_PATH   = _BASE / "data/processed/phase4/nl/panel_ze2020.csv"
_ZONE_PATH    = _BASE / "data/processed/phase4/nl/zone_mapping.csv"
_BIRTHS_PATH  = _BASE / "data/external/netherlands/processed/netherlands_births_panel.csv"
_STOCK_PATH   = _BASE / "data/external/netherlands/processed/netherlands_stock_panel.csv"
_SECTOR_BIRTHS_PATH = _BASE / "data/external/netherlands/processed/netherlands_sector_births_cbs_83631NED_corop_a10.csv"

# Canonical COROP region names (source: CBS, 2021 classification, 40 regions)
_NL_COROP_NAMES = {
    "CR01": "Oost-Groningen",              "CR02": "Delfzijl en omgeving",
    "CR03": "Overig Groningen",            "CR04": "Noord-Friesland",
    "CR05": "Zuidwest-Friesland",          "CR06": "Zuidoost-Friesland",
    "CR07": "Noord-Drenthe",              "CR08": "Zuidoost-Drenthe",
    "CR09": "Zuidwest-Drenthe",           "CR10": "Noord-Overijssel",
    "CR11": "Zuidwest-Overijssel",        "CR12": "Twente",
    "CR13": "Veluwe",                     "CR14": "Achterhoek",
    "CR15": "Arnhem/Nijmegen",            "CR16": "Zuidwest-Gelderland",
    "CR17": "Utrecht",                    "CR18": "Kop van Noord-Holland",
    "CR19": "Alkmaar en omgeving",        "CR20": "IJmond",
    "CR21": "Agglomeratie Haarlem",       "CR22": "Zaanstreek",
    "CR23": "Groot-Amsterdam",            "CR24": "Het Gooi en Vechtstreek",
    "CR25": "Agglomeratie Leiden en Bollenstreek",
    "CR26": "Agglomeratie 's-Gravenhage", "CR27": "Delft en Westland",
    "CR28": "Oost-Zuid-Holland",          "CR29": "Groot-Rijnmond",
    "CR30": "Zuidoost-Zuid-Holland",      "CR31": "Zeeuwsch-Vlaanderen",
    "CR32": "Overig Zeeland",             "CR33": "West-Noord-Brabant",
    "CR34": "Midden-Noord-Brabant",       "CR35": "Noordoost-Noord-Brabant",
    "CR36": "Zuidoost-Noord-Brabant",     "CR37": "Noord-Limburg",
    "CR38": "Midden-Limburg",             "CR39": "Zuid-Limburg",
    "CR40": "Flevoland",
}

_SECTOR_COLS = ["BE", "FZ", "GI", "JZ", "KZ", "LZ", "MN", "OQ", "RU"]


class NLAdapter:
    country        = "NL"
    region_level   = "COROP"
    meta_region_system = "COROP"
    meta_source_label  = "CBS"
    flag_target_concept = "enterprise_birth"

    def __init__(self, panel_path: Optional[Path] = None) -> None:
        self._panel_path = Path(panel_path) if panel_path else _PANEL_PATH

    def build(
        self,
        year_min: int = 2015,
        year_max: int = 2025,
    ) -> pd.DataFrame:
        pan   = pd.read_csv(self._panel_path)
        zm    = pd.read_csv(_ZONE_PATH)
        stock = pd.read_csv(_STOCK_PATH)

        pan = pan[(pan["target_year"] >= year_min) & (pan["target_year"] <= year_max)].copy()

        # Attach zone_id (CR01..CR40) via zone_mapping (ZE2020 = node idx 1-based → zone_id)
        zm_map = dict(zip(zm["ZE2020"], zm["zone_id"]))
        pan["zone_id"] = pan["ZE2020"].map(zm_map)

        # Stock lag-1: stock at t-1 (CBS stock is year-end; we join t-1)
        stock_lag = stock.copy()
        stock_lag["target_year"] = stock_lag["target_year"] + 1  # shift: stock[t-1] → year t
        stock_lag = stock_lag.rename(columns={"stock": "stock_lag1"})
        pan = pan.merge(stock_lag[["zone_id", "target_year", "stock_lag1"]],
                        on=["zone_id", "target_year"], how="left")

        if _SECTOR_BIRTHS_PATH.exists():
            sector = pd.read_csv(_SECTOR_BIRTHS_PATH)
            sector = sector[["zone_id", "target_year"] + _SECTOR_COLS].copy()
            sector["target_year"] = sector["target_year"] + 1
            sector = sector.rename(columns={s: f"sector_{s}" for s in _SECTOR_COLS})
            sector["mask_sector_a10"] = 1.0
            pan = pan.merge(
                sector[["zone_id", "target_year", "mask_sector_a10"] + [f"sector_{s}" for s in _SECTOR_COLS]],
                on=["zone_id", "target_year"],
                how="left",
            )
        else:
            pan["mask_sector_a10"] = 0.0

        out = pd.DataFrame()
        out["country"]      = [self.country] * len(pan)
        out["region_id"]    = pan["zone_id"]
        out["region_name"]  = pan["zone_id"].map(_NL_COROP_NAMES).fillna(pan["zone_id"])
        out["region_level"] = [self.region_level] * len(pan)
        out["year"]         = pan["target_year"].astype(int)
        out["node_idx"]     = (pan["ZE2020"] - 1).astype(int)  # ZE2020 is 1-based → 0-based

        out["target_births"] = pan["side_establishment_creations_official"].astype(float)
        out["lag1_births"]   = pan["side_lag_1"].astype(float)
        out["lag2_births"]   = pan["side_lag_2"].astype(float)
        out["lag3_births"]   = pan["side_lag_3"].astype(float)
        out["growth_1y"]     = pan["growth_1y"].astype(float)
        out["growth_2y"]     = pan["growth_2y"].astype(float)
        out["stock_lag1"]    = pan["stock_lag1"].astype(float)

        for s in _SECTOR_COLS:
            col = f"sector_{s}"
            out[col] = pan[col].astype(float) if col in pan.columns else np.nan
        out["mask_sector_a10"] = pan["mask_sector_a10"].fillna(0.0).astype(float)

        out["mask_target"]   = np.where(out["target_births"].notna(), 1.0, 0.0)
        out["mask_employment"] = 1.0
        out["mask_tensor"] = 1.0

        out["flag_target_concept"]          = [self.flag_target_concept] * len(out)
        # CBS Q-tensor (83582NED) available through 2024.
        # Semantics: flag=1 when employment data for t-1 is available to use as a feature.
        # Under effectifs_lag1 policy (q_lag[t] = q[t-1]):
        #   - NL 2025 needs employment[2024] → CBS has 2024 → flag=1 ✓
        #   - NL 2026 would need employment[2025] → CBS does not have 2025 → flag=0
        # The current panel ends at 2025, so all rows are flag=1.
        out["flag_has_national_employment"] = 1
        out["flag_has_eurostat_bd"]         = 1  # Eurostat BD covers NL
        out["flag_is_covid_year"]           = pan["is_covid_year"].astype(int)
        out["flag_is_rebound_year"]         = pan["is_post_covid_rebound"].astype(int)
        out["flag_forecast_safe"]           = pan["feature_forecast_safe"].astype(int)
        out.loc[out["lag1_births"].isna(), "flag_forecast_safe"] = 0

        out["meta_nuts3_code"]    = [""] * len(out)  # COROP ≠ NUTS3 (aggregation differs)
        out["meta_region_system"] = [self.meta_region_system] * len(out)
        out["meta_source_label"]  = [self.meta_source_label] * len(out)

        for eu_col in [
            "eu_employment_rate_lag1", "eu_unemployment_rate_lag1",
            "eu_sts_turnover_lag1", "eu_esi_lag1", "eu_eei_lag1",
            "eu_credit_standards_lag1", "eu_gdp_growth_lag1",
        ]:
            out[eu_col] = np.nan
        out["mask_eu_signals"] = 0.0

        out = out.sort_values(["region_id", "year"]).reset_index(drop=True)
        return out

    def validate(self, df: pd.DataFrame, year_min: int = 2015, year_max: int = 2025) -> dict:
        from src.data.european_panel.validation import validate_panel
        return validate_panel(df, country=self.country,
                              expected_years=range(year_min, year_max + 1))
