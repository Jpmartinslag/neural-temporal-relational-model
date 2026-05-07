#!/usr/bin/env python3
"""Prepare strict ex-ante HERALD panels for leakage checks.

The original geo2025 panel is already lag-oriented, but this script creates
auditable variants with narrower feature availability assumptions:

1. strict_lag_only:
   keeps only SIDE lag/growth features used by Ridge AR plus calendar regime
   flags required by HERALD's regime vector.
2. strict_no_source_flags:
   keeps all t_minus_1 variables and SIDE lag/growth features, but removes
   source-availability flags and calendar regime flags from the panel.

Both variants use only 2024/2025 validation folds. They are intentionally
saved as new files and never overwrite the production panel/splits.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


TARGET_COL = "side_establishment_creations_official"
ID_COLS = [
    "target_year",
    "ZE2020",
    "node_idx",
    "libze2020",
    "side_enterprise_creations_official",
    TARGET_COL,
    "communes_count",
]
RIDGE_LAGS = ["side_lag_1", "side_lag_2", "side_lag_3", "growth_1y", "growth_2y"]
REGIME_FLAGS = ["is_covid_year", "is_post_covid_rebound"]
SOURCE_FLAGS = ["has_flores_source", "has_side_stock_source", "has_urssaf_source"]


def existing(df: pd.DataFrame, cols: list[str]) -> list[str]:
    return [c for c in cols if c in df.columns]


def write_panel(df: pd.DataFrame, cols: list[str], path: Path) -> None:
    out = df[existing(df, cols)].copy()
    out = out.sort_values(["target_year", "ZE2020"]).reset_index(drop=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(path, index=False)
    print(f"wrote {path} rows={len(out)} cols={len(out.columns)}")
    print("columns:")
    for c in out.columns:
        print(f"  {c}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--panel-path",
        type=Path,
        default=Path("data/processed/dynamic_stgnn_feature_panel_through_2025_v1.csv"),
    )
    parser.add_argument(
        "--splits-path",
        type=Path,
        default=Path("metadata/dynamic_stgnn_walk_forward_splits_through_2025_v1.csv"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/processed/strict_exante_20260506"),
    )
    args = parser.parse_args()

    panel = pd.read_csv(args.panel_path)
    splits = pd.read_csv(args.splits_path)

    # Extremal conservative panel: only autoregressive establishment signals.
    lag_only_cols = ID_COLS + RIDGE_LAGS + REGIME_FLAGS
    write_panel(
        panel,
        lag_only_cols,
        args.output_dir / "dynamic_stgnn_feature_panel_strict_lag_only_through_2025_v1.csv",
    )

    # Broader strict panel: only lagged covariates, no availability/calendar flags.
    lagged_covariates = [
        c
        for c in panel.columns
        if (
            c.endswith("_t_minus_1")
            or c in RIDGE_LAGS
            or c in ID_COLS
            or c in REGIME_FLAGS
        )
        and c not in SOURCE_FLAGS
    ]
    write_panel(
        panel,
        lagged_covariates,
        args.output_dir / "dynamic_stgnn_feature_panel_strict_no_source_flags_through_2025_v1.csv",
    )

    strict_splits = splits[splits["target_year"].isin([2024, 2025])].copy()
    strict_splits.to_csv(
        args.output_dir / "dynamic_stgnn_walk_forward_splits_strict_2024_2025_v1.csv",
        index=False,
    )
    print(
        "wrote",
        args.output_dir / "dynamic_stgnn_walk_forward_splits_strict_2024_2025_v1.csv",
        f"rows={len(strict_splits)}",
    )


if __name__ == "__main__":
    main()
