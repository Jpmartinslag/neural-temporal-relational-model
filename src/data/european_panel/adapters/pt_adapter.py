"""
Portugal adapter — converts processed Portugal NUTS3 files to the European canonical schema.

Primary sources (already processed, local files):
  data/external/portugal/processed/
    portugal_births_panel_nuts3.csv                    — raw births
    portugal_stock_panel_nuts3.csv                     — enterprise stock
    portugal_qtensor_births_cae_nuts3.csv              — births by CAE×NUTS3 (proxy tensor)
    portugal_qtensor_employment_eurostat_nuts3.csv     — Eurostat employment × NACE×NUTS3

Target concept: enterprise_birth (INE/GEP)
  Portugal GEP Quadros de Pessoal counts enterprise entries (NUTS3 × year).
  flag_target_concept = 'enterprise_birth'

Sector births: AVAILABLE from GEP CAE → A10 mapping.
  PT A10 total == target_births (max_diff = 0).
  sector_* = births by A10 sector at t-1 (lagged).
  mask_sector_a10 = 1.0 where sector data present.

Employment tensor:
  Phase 4D used GEP births-by-CAE as a proxy tensor.
  Phase 4E can use Eurostat nama_10r_3empers regional employment by NACE,
  mapped back to the 25-region HERALD Portugal panel.
  flag_has_national_employment = 1 when that Eurostat tensor is present.

NUTS3 codes: PT_111..PT_300 correspond to the INE/GEP 25-region panel.
  PT_111 → PT111 (Minho-Lima), etc. Underscore notation used in pipeline.

Notes:
  - Zone IDs: PT_111..PT_300 (NUTS3 with underscore separator)
  - NUTS3 code = zone_id with underscore removed (PT_111 → PT111)
  - Eurostat BD covers PT (unlike BE)
  - ECB BLS covers PT (Zona Euro member since 1999)
  - 2024 is available through INE NUTS 2024 indicators, mapped back to the
    25-region HERALD Portugal panel
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

_BASE = Path(__file__).resolve().parents[4]
_BIRTHS_PATH = _BASE / "data/external/portugal/processed/portugal_births_panel_nuts3.csv"
_A10_PATH    = _BASE / "data/external/portugal/processed/portugal_qtensor_births_cae_nuts3.csv"
_STOCK_PATH  = _BASE / "data/external/portugal/processed/portugal_stock_panel_nuts3.csv"
_EMP_TENSOR_PATH = _BASE / "data/external/portugal/processed/portugal_qtensor_employment_eurostat_nuts3.csv"

# NUTS3 2021 names for Portugal (25 regions used in HERALD pipeline)
_PT_NUTS3_NAMES = {
    "PT_111": "Alto Minho",
    "PT_112": "Cávado",
    "PT_119": "Ave",
    "PT_11A": "Área Metropolitana do Porto",
    "PT_11B": "Alto Tâmega e Barroso",
    "PT_11C": "Tâmega e Sousa",
    "PT_11D": "Douro",
    "PT_11E": "Terras de Trás-os-Montes",
    "PT_150": "Algarve",
    "PT_16B": "Oeste",
    "PT_16D": "Região de Aveiro",
    "PT_16E": "Região de Coimbra",
    "PT_16F": "Região de Leiria",
    "PT_16G": "Viseu Dão Lafões",
    "PT_16H": "Beira Baixa",
    "PT_16I": "Médio Tejo",
    "PT_16J": "Beiras e Serra da Estrela",
    "PT_170": "Área Metropolitana de Lisboa",
    "PT_181": "Alentejo Litoral",
    "PT_184": "Baixo Alentejo",
    "PT_185": "Lezíria do Tejo",
    "PT_186": "Alto Alentejo",
    "PT_187": "Alentejo Central",
    "PT_200": "Região Autónoma dos Açores",
    "PT_300": "Região Autónoma da Madeira",
}

_SECTOR_COLS = ["BE", "FZ", "GI", "JZ", "KZ", "LZ", "MN", "OQ", "RU"]


class PTAdapter:
    country        = "PT"
    region_level   = "NUTS3"
    meta_region_system = "NUTS3"
    meta_source_label  = "INE-GEP"
    flag_target_concept = "enterprise_birth"

    def __init__(self, panel_path: Optional[Path] = None) -> None:
        self._panel_path = Path(panel_path) if panel_path else _BIRTHS_PATH

    def build(
        self,
        year_min: int = 2008,
        year_max: int = 2024,
    ) -> pd.DataFrame:
        pan   = pd.read_csv(self._panel_path)
        a10   = pd.read_csv(_A10_PATH)
        stock = pd.read_csv(_STOCK_PATH)

        pan = pan[(pan["target_year"] >= year_min) & (pan["target_year"] <= year_max)].copy()
        a10 = a10[(a10["target_year"] >= year_min) & (a10["target_year"] <= year_max)].copy()
        has_real_employment_tensor = _EMP_TENSOR_PATH.exists()

        zones = sorted(pan["zone_id"].unique())
        node_idx = {zone: idx for idx, zone in enumerate(zones)}
        pan = pan.sort_values(["zone_id", "target_year"]).reset_index(drop=True)
        pan["side_lag_1"] = pan.groupby("zone_id")["y"].shift(1)
        pan["side_lag_2"] = pan.groupby("zone_id")["y"].shift(2)
        pan["side_lag_3"] = pan.groupby("zone_id")["y"].shift(3)
        pan["growth_1y"] = (pan["y"] - pan["side_lag_1"]) / pan["side_lag_1"]
        pan["growth_2y"] = (pan["y"] - pan["side_lag_2"]) / pan["side_lag_2"]

        # Sector births at t-1: shift A10 by +1 year so A10[t-1] becomes feature for year t
        a10_map = {"A": "OQ", "OPQ": "OQ", "RSU": "RU"}
        a10["sector"] = a10["a10"].replace(a10_map)
        a10 = (
            a10.groupby(["zone_id", "target_year", "sector"], as_index=False)["births"]
            .sum()
        )
        a10 = a10.pivot_table(
            index=["zone_id", "target_year"],
            columns="sector",
            values="births",
            aggfunc="sum",
            fill_value=0.0,
        ).reset_index()
        a10_shifted = a10.copy()
        a10_shifted["target_year"] = a10_shifted["target_year"] + 1
        a10_shifted = a10_shifted.rename(columns={s: f"sector_{s}" for s in _SECTOR_COLS})
        a10_shifted["mask_sector_a10"] = 1.0
        a10_cols = ["zone_id", "target_year", "mask_sector_a10"] + [f"sector_{s}" for s in _SECTOR_COLS]
        pan = pan.merge(a10_shifted[a10_cols], on=["zone_id", "target_year"], how="left")
        pan["mask_sector_a10"] = pan["mask_sector_a10"].fillna(0.0)

        # Stock lag-1
        stock_lag = stock.copy()
        stock_lag["target_year"] = stock_lag["target_year"] + 1
        stock_lag = stock_lag.rename(columns={"stock": "stock_lag1"})
        pan = pan.merge(stock_lag[["zone_id", "target_year", "stock_lag1"]],
                        on=["zone_id", "target_year"], how="left")

        out = pd.DataFrame()
        out["country"]      = [self.country] * len(pan)
        out["region_id"]    = pan["zone_id"]
        out["region_name"]  = pan["zone_id"].map(_PT_NUTS3_NAMES).fillna(pan["zone_id"])
        out["region_level"] = [self.region_level] * len(pan)
        out["year"]         = pan["target_year"].astype(int)
        out["node_idx"]     = pan["zone_id"].map(node_idx).astype(int)

        out["target_births"] = pan["y"].astype(float)
        out["lag1_births"]   = pan["side_lag_1"].astype(float)
        out["lag2_births"]   = pan["side_lag_2"].astype(float)
        out["lag3_births"]   = pan["side_lag_3"].astype(float)
        out["growth_1y"]     = pan["growth_1y"].astype(float)
        out["growth_2y"]     = pan["growth_2y"].astype(float)
        out["stock_lag1"]    = pan["stock_lag1"].astype(float)

        # Sector births (A10 from GEP CAE, same concept as target)
        for s in _SECTOR_COLS:
            col = f"sector_{s}"
            out[col] = pan[col].astype(float) if col in pan.columns else np.nan
        out["mask_sector_a10"] = pan["mask_sector_a10"].astype(float)

        out["mask_target"] = np.where(out["target_births"].notna(), 1.0, 0.0)
        out["mask_employment"] = 1.0 if has_real_employment_tensor else 0.0
        out["mask_tensor"] = 1.0 if has_real_employment_tensor else np.where(out["mask_sector_a10"] > 0, 0.5, 0.0)

        out["flag_target_concept"] = [self.flag_target_concept] * len(out)
        out["flag_has_national_employment"] = 1 if has_real_employment_tensor else 0
        out["flag_has_eurostat_bd"]         = 1  # Eurostat BD covers PT
        out["flag_is_covid_year"]           = (out["year"] == 2020).astype(int)
        out["flag_is_rebound_year"]         = (out["year"] == 2021).astype(int)
        out["flag_forecast_safe"]           = np.where(out["lag1_births"].notna(), 1, 0)
        out.loc[out["lag1_births"].isna(), "flag_forecast_safe"] = 0

        # NUTS3 code: remove underscore (PT_111 → PT111)
        out["meta_nuts3_code"]    = pan["zone_id"].str.replace("_", "", n=1)
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

    def validate(self, df: pd.DataFrame, year_min: int = 2008, year_max: int = 2024) -> dict:
        from src.data.european_panel.validation import validate_panel
        return validate_panel(df, country=self.country,
                              expected_years=range(year_min, year_max + 1))
