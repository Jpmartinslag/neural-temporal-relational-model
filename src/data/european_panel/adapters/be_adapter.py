"""
Belgium adapter — converts Phase 4 BE panel to the European canonical schema.

Primary sources (already processed, local files):
  data/processed/phase4/be/panel_ze2020.csv       — legacy panel (42 arrondissements, 2007-2020)
  data/processed/phase4/be/a10_ze2020.csv         — employment Q-tensor (StatBel ONSS jobs)
  data/processed/phase4/be/zone_mapping.csv        — zone_id → node index
  data/external/belgium/processed/
    belgium_births_panel.csv                       — raw births with growth/lag
    belgium_stock_panel.csv                        — enterprise stock
    belgium_qtensor_jobs_panel.csv                 — employment by A10 × arrondissement × year
    belgium_births_stock_extension_2021_2024_42zones.csv
                                                    — StatBel TVA extension, harmonised to 42 zones

Target concept: vat_first_registration (StatBel — assujettis à la TVA)
  Belgium StatBel counts first VAT registrations (primo-assujettissements), a
  fiscal-administrative event, NOT a demographic enterprise birth. StatBel
  documents a methodological break in the health sector in January 2022 from a
  VAT-exemption change. This is the strongest semantic incompatibility of the four.
  flag_target_concept = 'vat_first_registration'
  Migration note (Phase 4J, 2026-06-09): previously labelled 'enterprise_birth';
  corrected after the semantic target audit. Passthrough metadata only (no model
  consumes the string), so no retraining is required — rebuild to propagate.
  See reports/HERALD_PHASE4J_TARGET_EQUIVALENCE_TABLE.md.

Sector births: NOT available from StatBel at arrondissement × sector level.
  BE A10 (StatBel ONSS) provides employment counts (jobs), not births by sector.
  Eurostat BD does NOT cover Belgium (confirmed: absent from bd_hgnace_r).
  sector_* = NaN for all BE rows; mask_sector_a10 = 0.0

Employment tensor: StatBel ONSS (jobs by NACE-BEL A10 × arrondissement)
  flag_has_national_employment = 1

Notes:
  - Zone IDs: BE_alost, BE_anvers, etc. (StatBel arrondissement names)
  - 43 NIS arrondissement codes → 42 arrondissements (Tournai + Mouscron merged)
  - Years: 2007-2024 for target/stock. 2021-2024 comes from manual be.STAT export.
  - Eurostat BD absent for BE — flag_has_eurostat_bd = 0
  - ECB BLS covers BE (Zona Euro member since 1999)
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

_BASE = Path(__file__).resolve().parents[4]
_PANEL_PATH  = _BASE / "data/processed/phase4/be/panel_ze2020.csv"
_ZONE_PATH   = _BASE / "data/processed/phase4/be/zone_mapping.csv"
_STOCK_PATH  = _BASE / "data/external/belgium/processed/belgium_stock_panel.csv"
_EXT_PATH    = _BASE / "data/external/belgium/processed/belgium_births_stock_extension_2021_2024_42zones.csv"

# StatBel arrondissement names (French/Dutch bilingual label → French used here)
_BE_ZONE_NAMES = {
    "BE_alost":             "Alost",
    "BE_anvers":            "Anvers",
    "BE_arlon":             "Arlon",
    "BE_ath":               "Ath",
    "BE_audenarde":         "Audenarde",
    "BE_bastogne":          "Bastogne",
    "BE_bruges":            "Bruges",
    "BE_bruxelles_capitale": "Bruxelles-Capitale",
    "BE_charleroi":         "Charleroi",
    "BE_courtrai":          "Courtrai",
    "BE_dinant":            "Dinant",
    "BE_dixmude":           "Dixmude",
    "BE_eeklo":             "Eeklo",
    "BE_furnes":            "Furnes",
    "BE_gand":              "Gand",
    "BE_hal_vilvorde":      "Hal-Vilvorde",
    "BE_hasselt":           "Hasselt",
    "BE_huy":               "Huy",
    "BE_liege":             "Liège",
    "BE_louvain":           "Louvain",
    "BE_maaseik":           "Maaseik",
    "BE_malines":           "Malines",
    "BE_marche_en_famenne": "Marche-en-Famenne",
    "BE_mons":              "Mons",
    "BE_namur":             "Namur",
    "BE_neufchateau":       "Neufchâteau",
    "BE_nivelles":          "Nivelles",
    "BE_ostende":           "Ostende",
    "BE_philippeville":     "Philippeville",
    "BE_roulers":           "Roulers",
    "BE_saint_nicolas":     "Saint-Nicolas",
    "BE_soignies":          "Soignies",
    "BE_termonde":          "Termonde",
    "BE_thuin":             "Thuin",
    "BE_tielt":             "Tielt",
    "BE_tongres":           "Tongres",
    "BE_tournai_mouscron":  "Tournai-Mouscron (merged)",
    "BE_turnhout":          "Turnhout",
    "BE_verviers":          "Verviers",
    "BE_virton":            "Virton",
    "BE_waremme":           "Waremme",
    "BE_ypres":             "Ypres",
}

_SECTOR_COLS = ["BE", "FZ", "GI", "JZ", "KZ", "LZ", "MN", "OQ", "RU"]


class BEAdapter:
    country        = "BE"
    region_level   = "arrondissement"
    meta_region_system = "arrondissement"
    meta_source_label  = "StatBel"
    flag_target_concept = "vat_first_registration"  # was 'enterprise_birth' (Phase 4J)

    def __init__(self, panel_path: Optional[Path] = None) -> None:
        self._panel_path = Path(panel_path) if panel_path else _PANEL_PATH

    def build(
        self,
        year_min: int = 2007,
        year_max: int = 2024,
    ) -> pd.DataFrame:
        pan = pd.read_csv(self._panel_path)
        zm = pd.read_csv(_ZONE_PATH)
        zm_map = dict(zip(zm["ZE2020"], zm["zone_id"]))
        rev_zm_map = {v: k for k, v in zm_map.items()}

        legacy = pan[["ZE2020", "target_year", "side_establishment_creations_official"]].copy()
        legacy["zone_id"] = legacy["ZE2020"].map(zm_map)
        legacy = legacy.rename(columns={"side_establishment_creations_official": "target_births"})

        frames = [legacy[["zone_id", "target_year", "target_births"]]]
        stock_frames = [pd.read_csv(_STOCK_PATH)]

        if _EXT_PATH.exists():
            ext = pd.read_csv(_EXT_PATH)
            ext_births = ext.rename(columns={"y": "target_births"})[["zone_id", "target_year", "target_births"]]
            frames.append(ext_births)
            stock_frames.append(ext[["zone_id", "target_year", "stock"]])

        births = (
            pd.concat(frames, ignore_index=True)
            .drop_duplicates(["zone_id", "target_year"], keep="last")
            .sort_values(["zone_id", "target_year"])
            .reset_index(drop=True)
        )
        births = births[(births["target_year"] >= year_min) & (births["target_year"] <= year_max)].copy()
        births["ZE2020"] = births["zone_id"].map(rev_zm_map)
        births["node_idx"] = births["ZE2020"].astype(int) - 1

        births["lag1_births"] = births.groupby("zone_id")["target_births"].shift(1)
        births["lag2_births"] = births.groupby("zone_id")["target_births"].shift(2)
        births["lag3_births"] = births.groupby("zone_id")["target_births"].shift(3)
        births["growth_1y"] = (births["target_births"] - births["lag1_births"]) / births["lag1_births"]
        births["growth_2y"] = (births["target_births"] - births["lag2_births"]) / births["lag2_births"]

        stock = (
            pd.concat(stock_frames, ignore_index=True)
            .drop_duplicates(["zone_id", "target_year"], keep="last")
            .sort_values(["zone_id", "target_year"])
            .reset_index(drop=True)
        )
        # Stock lag-1: join stock[t-1] as feature at year t.
        stock_lag = stock.copy()
        stock_lag["target_year"] = stock_lag["target_year"] + 1
        stock_lag = stock_lag.rename(columns={"stock": "stock_lag1"})
        births = births.merge(stock_lag[["zone_id", "target_year", "stock_lag1"]],
                              on=["zone_id", "target_year"], how="left")

        out = pd.DataFrame()
        out["country"]      = [self.country] * len(births)
        out["region_id"]    = births["zone_id"]
        out["region_name"]  = births["zone_id"].map(_BE_ZONE_NAMES).fillna(births["zone_id"])
        out["region_level"] = [self.region_level] * len(births)
        out["year"]         = births["target_year"].astype(int)
        out["node_idx"]     = births["node_idx"].astype(int)

        out["target_births"] = births["target_births"].astype(float)
        out["lag1_births"]   = births["lag1_births"].astype(float)
        out["lag2_births"]   = births["lag2_births"].astype(float)
        out["lag3_births"]   = births["lag3_births"].astype(float)
        out["growth_1y"]     = births["growth_1y"].astype(float)
        out["growth_2y"]     = births["growth_2y"].astype(float)
        out["stock_lag1"]    = births["stock_lag1"].astype(float)

        # Sector births: not available from StatBel at arrondissement level
        for s in _SECTOR_COLS:
            out[f"sector_{s}"] = np.nan
        out["mask_sector_a10"] = 0.0

        out["mask_target"] = np.where(out["target_births"].notna(), 1.0, 0.0)
        out["mask_employment"] = 1.0
        out["mask_tensor"] = 1.0

        out["flag_target_concept"]          = [self.flag_target_concept] * len(out)
        out["flag_has_national_employment"] = 1  # StatBel ONSS Q-tensor available
        out["flag_has_eurostat_bd"]         = 0  # BE absent from Eurostat BD
        out["flag_is_covid_year"]           = (out["year"] == 2020).astype(int)
        out["flag_is_rebound_year"]         = (out["year"] == 2021).astype(int)
        out["flag_forecast_safe"]           = np.where(out["lag1_births"].notna(), 1, 0)
        out.loc[out["lag1_births"].isna(), "flag_forecast_safe"] = 0

        out["meta_nuts3_code"]    = [""] * len(out)  # arrondissement ≠ NUTS3 (different aggregation)
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

    def validate(self, df: pd.DataFrame, year_min: int = 2007, year_max: int = 2024) -> dict:
        from src.data.european_panel.validation import validate_panel
        return validate_panel(df, country=self.country,
                              expected_years=range(year_min, year_max + 1))
