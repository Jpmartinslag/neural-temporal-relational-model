"""
HERALD -- France ZE2020 relational + sector prototype panel (MVP2, integration
step). See reports/canonical/HERALD_17_FR_ZE2020_RELATIONAL_LAYER_PLAN.md,
"MVP2 Categoria C" section.

Joins, WITHOUT modifying either input:
  data/processed/france_ze2020/fr_ze2020_relational_model_ready_panel.csv
    (time + ZE-to-ZE trajectory similarity, Category A, 280 zones x 14 years)
  data/processed/france_ze2020/fr_ze2020_sector_relational_features.csv
    (ZE x sector causal features, Category C) -- only the ZE x year grain
    columns (the sector-distribution aggregates, already identical across a
    zone's 9 sector rows) are pulled in here, plus one extra derived column:
    top_sector_signal_lag_1 = the dominant sector's OWN sector_growth_lag_1,
    looked up by matching sector_code == dominant_sector_lag_1 for the same
    (ze2020, year) -- i.e. "how is the zone's currently-dominant sector
    trending", itself already a lag-only, causal-safe value.

This represents time + ZE-to-ZE + ZE-x-sector in a single row per
(ze2020, year) -- the tabular base for a future graph/neural candidate, NOT
a graph and NOT a trained model. No row count changes (left join on the
relational panel, which already has exactly one row per zone-year); no
input file is modified.

Input (read-only):
  data/processed/france_ze2020/fr_ze2020_relational_model_ready_panel.csv
  data/processed/france_ze2020/fr_ze2020_sector_relational_features.csv

Output:
  data/processed/france_ze2020/fr_ze2020_relational_sector_prototype_panel.csv
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
RELATIONAL_PANEL_PATH = (
    ROOT / "data/processed/france_ze2020/fr_ze2020_relational_model_ready_panel.csv"
)
SECTOR_FEATURES_PATH = ROOT / "data/processed/france_ze2020/fr_ze2020_sector_relational_features.csv"
OUT_DIR = ROOT / "data/processed/france_ze2020"
OUT_PATH = OUT_DIR / "fr_ze2020_relational_sector_prototype_panel.csv"

ZE_YEAR_SECTOR_AGGREGATE_COLS = [
    "dominant_sector_lag_1",
    "dominant_sector_share_lag_1",
    "sector_diversity_lag_1",
    "sector_concentration_hhi_lag_1",
    "commerce_share_lag_1",
    "construction_share_lag_1",
    "mask_ze_sector_distribution_lag_1_available",
]


def load_relational_panel(path: Path = RELATIONAL_PANEL_PATH) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"ze2020": str})
    df["year"] = df["year"].astype(int)
    return df


def load_sector_features(path: Path = SECTOR_FEATURES_PATH) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"ze2020": str})
    df["year"] = df["year"].astype(int)
    return df


def build_prototype_panel(
    relational: pd.DataFrame | None = None, sector_features: pd.DataFrame | None = None
) -> pd.DataFrame:
    if relational is None:
        relational = load_relational_panel()
    if sector_features is None:
        sector_features = load_sector_features()

    ze_year_aggregates = sector_features.drop_duplicates(subset=["ze2020", "year"])[
        ["ze2020", "year"] + ZE_YEAR_SECTOR_AGGREGATE_COLS
    ]

    prototype = relational.merge(ze_year_aggregates, on=["ze2020", "year"], how="left")
    assert len(prototype) == len(relational), "Integration step must not change row count"

    top_sector_signal = sector_features[["ze2020", "year", "sector_code", "sector_growth_lag_1"]].rename(
        columns={"sector_code": "dominant_sector_lag_1", "sector_growth_lag_1": "top_sector_signal_lag_1"}
    )
    prototype = prototype.merge(
        top_sector_signal, on=["ze2020", "year", "dominant_sector_lag_1"], how="left"
    )
    assert len(prototype) == len(relational), "top_sector_signal_lag_1 lookup must not fan out rows"

    relational_cols = list(relational.columns)
    new_cols = ZE_YEAR_SECTOR_AGGREGATE_COLS + ["top_sector_signal_lag_1"]
    col_order = relational_cols + new_cols
    prototype = prototype[col_order].sort_values(["ze2020", "year"]).reset_index(drop=True)
    return prototype


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    panel = build_prototype_panel()
    panel.to_csv(OUT_PATH, index=False)

    n_sector_available = int(panel["mask_ze_sector_distribution_lag_1_available"].sum())
    n_both_available = int(
        ((panel["relational_feature_available"] == 1) & (panel["mask_ze_sector_distribution_lag_1_available"] == 1)).sum()
    )
    print(f"Rows: {len(panel)}")
    print(f"Sector distribution available: {n_sector_available}/{len(panel)}")
    print(f"Both ZE->ZE and ZE x sector available: {n_both_available}/{len(panel)}")
    print(f"Saved: {OUT_PATH}")


if __name__ == "__main__":
    main()
