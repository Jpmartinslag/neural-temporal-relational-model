"""
HERALD -- France ZE2020 sector relational features (MVP2 Category C, step 2).

Reads ONLY data/processed/france_ze2020/fr_ze2020_sector_panel.csv (the
already-audited, already-reconciled sector composition panel built by
build_fr_ze2020_sector_panel.py). Adds causal, lag-only features at three
grains, all merged onto a single ZE-to-sector-to-year long table:

  1. ZE x sector (its own history):
     sector_share_lag_1, sector_growth_lag_1, sector_growth_lag_2.
     sector_growth_lag_1 = growth ending at t-1 (uses own_lag_1, own_lag_2);
     sector_growth_lag_2 = growth ending at t-2, one step further back
     (uses own_lag_2, own_lag_3) -- mirrors the growth_1y_safe/growth_2y_safe
     causal pattern already used in fr_ze2020_model_ready_panel.csv, but
     applied to two CONSECUTIVE historical growth observations rather than
     two different reference windows.

  2. ZE x year (sector-share distribution within the zone):
     dominant_sector_lag_1, dominant_sector_share_lag_1,
     sector_diversity_lag_1 (Shannon entropy of the share distribution,
     normalized to [0, 1] by log(9)), sector_concentration_hhi_lag_1
     (Herfindahl-Hirschman index, in [1/9, 1]), commerce_share_lag_1 (GI --
     "Trade, transport and hospitality", the closest single A10 category to
     commerce), construction_share_lag_1 (FZ). All computed from the
     CONTEMPORANEOUS share distribution at year t-1, then attached to row t
     by a strict groupby-shift(1) -- never from year t's own distribution.

     services_share_lag_1 is explicitly NOT implemented: the A10 nomenclature
     has no single "services" code -- JZ/MN/OQ/RU are all services-like but
     economically heterogeneous (information, professional/admin, public
     admin/education/health, arts/other). Picking an arbitrary subset would
     be a judgment call presented as data; left out per the plan document's
     "se possível" qualifier.

  3. Sector x year (national aggregate, summed over all 280 zones):
     national_sector_share_lag_1, national_sector_growth_lag_1. Same
     compute-then-shift-by-1 pattern as (2), shifted within sector_code
     instead of within ze2020.

Every "_lag_1"/"_lag_2" column has a paired mask column. No column is ever
filled with the current year's own contemporaneous value.

Input (read-only):
  data/processed/france_ze2020/fr_ze2020_sector_panel.csv

Output:
  data/processed/france_ze2020/fr_ze2020_sector_relational_features.csv
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data.france_ze2020.build_fr_ze2020_sector_panel import OUT_PATH as SECTOR_PANEL_PATH  # noqa: E402
from src.data.france_ze2020.build_fr_ze2020_sector_panel import SECTOR_CODES  # noqa: E402

OUT_DIR = ROOT / "data/processed/france_ze2020"
OUT_PATH = OUT_DIR / "fr_ze2020_sector_relational_features.csv"

COMMERCE_SECTOR = "GI"
CONSTRUCTION_SECTOR = "FZ"

ZE_AGGREGATE_COLS = [
    "dominant_sector",
    "dominant_sector_share",
    "sector_diversity",
    "sector_concentration_hhi",
    "commerce_share",
    "construction_share",
]


def load_sector_panel(path: Path = SECTOR_PANEL_PATH) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"ze2020": str})
    df["year"] = df["year"].astype(int)
    return df


def _shannon_diversity(shares: pd.Series) -> float:
    """Normalized Shannon entropy in [0, 1]; 1 = perfectly even across all
    9 sectors, 0 = fully concentrated in a single sector."""
    positive = shares[shares > 0]
    if positive.empty:
        return float("nan")
    return float(-(positive * np.log(positive)).sum() / np.log(len(SECTOR_CODES)))


def _hhi(shares: pd.Series) -> float:
    return float((shares**2).sum())


def _build_ze_sector_own_lags(panel: pd.DataFrame) -> pd.DataFrame:
    df = panel.sort_values(["ze2020", "sector_code", "year"]).reset_index(drop=True)
    grp = df.groupby(["ze2020", "sector_code"])

    own_lag_1 = grp["sector_establishment_creations"].shift(1)
    own_lag_2 = grp["sector_establishment_creations"].shift(2)
    own_lag_3 = grp["sector_establishment_creations"].shift(3)

    df["sector_share_lag_1"] = grp["sector_share"].shift(1)
    df["sector_growth_lag_1"] = (own_lag_1 - own_lag_2) / own_lag_2
    df["sector_growth_lag_2"] = (own_lag_2 - own_lag_3) / own_lag_3

    df["mask_sector_share_lag_1_available"] = df["sector_share_lag_1"].notna().astype(int)
    df["mask_sector_growth_lag_1_available"] = df["sector_growth_lag_1"].notna().astype(int)
    df["mask_sector_growth_lag_2_available"] = df["sector_growth_lag_2"].notna().astype(int)
    return df


def _build_ze_year_aggregates_lagged(panel: pd.DataFrame) -> pd.DataFrame:
    """Contemporaneous sector-distribution stats per (ze2020, year), then
    shifted by exactly 1 year within ze2020 -- the shift happens AFTER the
    contemporaneous computation, so '_lag_1' always means 'as observed at
    year - 1', never the current row's own distribution."""
    grouped = panel.groupby(["ze2020", "year"])

    dominant_idx = grouped["sector_share"].idxmax()
    dominant = panel.loc[dominant_idx, ["ze2020", "year", "sector_code", "sector_share"]].rename(
        columns={"sector_code": "dominant_sector", "sector_share": "dominant_sector_share"}
    )

    stats = grouped["sector_share"].agg(
        sector_diversity=_shannon_diversity, sector_concentration_hhi=_hhi
    ).reset_index()

    commerce = panel.loc[
        panel["sector_code"] == COMMERCE_SECTOR, ["ze2020", "year", "sector_share"]
    ].rename(columns={"sector_share": "commerce_share"})
    construction = panel.loc[
        panel["sector_code"] == CONSTRUCTION_SECTOR, ["ze2020", "year", "sector_share"]
    ].rename(columns={"sector_share": "construction_share"})

    contemporaneous = (
        dominant.merge(stats, on=["ze2020", "year"])
        .merge(commerce, on=["ze2020", "year"])
        .merge(construction, on=["ze2020", "year"])
        .sort_values(["ze2020", "year"])
        .reset_index(drop=True)
    )

    lagged = contemporaneous.groupby("ze2020")[ZE_AGGREGATE_COLS].shift(1)
    lagged.columns = [f"{c}_lag_1" for c in ZE_AGGREGATE_COLS]

    result = pd.concat([contemporaneous[["ze2020", "year"]], lagged], axis=1)
    result["mask_ze_sector_distribution_lag_1_available"] = (
        result["dominant_sector_lag_1"].notna().astype(int)
    )
    return result


def _build_national_sector_lags(panel: pd.DataFrame) -> pd.DataFrame:
    """National total per (sector_code, year), summed over all 280 zones,
    then share/growth computed contemporaneously and shifted by 1 within
    sector_code -- same compute-then-shift pattern as the ZE aggregates."""
    national_sector = (
        panel.groupby(["sector_code", "year"])["sector_establishment_creations"]
        .sum()
        .reset_index(name="national_sector_total")
    )
    national_grand_total = (
        panel.groupby("year")["sector_establishment_creations"]
        .sum()
        .reset_index(name="national_grand_total")
    )
    national = national_sector.merge(national_grand_total, on="year")
    national["national_sector_share"] = (
        national["national_sector_total"] / national["national_grand_total"]
    )
    national = national.sort_values(["sector_code", "year"]).reset_index(drop=True)
    national["national_sector_growth"] = national.groupby("sector_code")[
        "national_sector_total"
    ].pct_change(1)

    national["national_sector_share_lag_1"] = national.groupby("sector_code")[
        "national_sector_share"
    ].shift(1)
    national["national_sector_growth_lag_1"] = national.groupby("sector_code")[
        "national_sector_growth"
    ].shift(1)

    national["mask_national_sector_share_lag_1_available"] = (
        national["national_sector_share_lag_1"].notna().astype(int)
    )
    national["mask_national_sector_growth_lag_1_available"] = (
        national["national_sector_growth_lag_1"].notna().astype(int)
    )

    return national[
        [
            "sector_code",
            "year",
            "national_sector_share_lag_1",
            "mask_national_sector_share_lag_1_available",
            "national_sector_growth_lag_1",
            "mask_national_sector_growth_lag_1_available",
        ]
    ]


def build_sector_relational_features(panel: pd.DataFrame | None = None) -> pd.DataFrame:
    if panel is None:
        panel = load_sector_panel()

    with_own_lags = _build_ze_sector_own_lags(panel)
    ze_year_lagged = _build_ze_year_aggregates_lagged(panel)
    national_lagged = _build_national_sector_lags(panel)

    result = with_own_lags[
        [
            "ze2020",
            "year",
            "sector_code",
            "sector_share_lag_1",
            "mask_sector_share_lag_1_available",
            "sector_growth_lag_1",
            "mask_sector_growth_lag_1_available",
            "sector_growth_lag_2",
            "mask_sector_growth_lag_2_available",
        ]
    ].copy()

    result = result.merge(ze_year_lagged, on=["ze2020", "year"], how="left")
    result = result.merge(national_lagged, on=["sector_code", "year"], how="left")

    col_order = [
        "ze2020",
        "year",
        "sector_code",
        "sector_share_lag_1",
        "mask_sector_share_lag_1_available",
        "sector_growth_lag_1",
        "mask_sector_growth_lag_1_available",
        "sector_growth_lag_2",
        "mask_sector_growth_lag_2_available",
        "dominant_sector_lag_1",
        "dominant_sector_share_lag_1",
        "sector_diversity_lag_1",
        "sector_concentration_hhi_lag_1",
        "commerce_share_lag_1",
        "construction_share_lag_1",
        "mask_ze_sector_distribution_lag_1_available",
        "national_sector_share_lag_1",
        "mask_national_sector_share_lag_1_available",
        "national_sector_growth_lag_1",
        "mask_national_sector_growth_lag_1_available",
    ]
    result = result[col_order].sort_values(["ze2020", "year", "sector_code"]).reset_index(drop=True)
    return result


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    features = build_sector_relational_features()
    features.to_csv(OUT_PATH, index=False)

    n_growth_available = int(features["mask_sector_growth_lag_1_available"].sum())
    n_national_available = int(features["mask_national_sector_growth_lag_1_available"].sum())
    print(f"Rows: {len(features)}")
    print(f"sector_growth_lag_1 available: {n_growth_available}/{len(features)}")
    print(f"national_sector_growth_lag_1 available: {n_national_available}/{len(features)}")
    print(f"Saved: {OUT_PATH}")


if __name__ == "__main__":
    main()
