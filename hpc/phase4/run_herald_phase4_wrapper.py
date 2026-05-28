#!/usr/bin/env python3
"""Phase 4 training wrapper — patches adjacency paths and quarterly tensor before training.

This script is NOT a modification to the training code. It patches module-level globals
in train_herald_v6 before importing the training pipeline, so the existing training code
runs on international panels without any changes.

Environment variables consumed:
  PHASE4_PANEL       — path to panel_ze2020.csv
  PHASE4_SPLITS      — path to splits.csv
  PHASE4_SIDE_A10    — path to a10_ze2020.csv
  PHASE4_GEO_ADJ     — path to adj_geo.csv
  PHASE4_MOB_ADJ     — path to adj_mob.csv
  PHASE4_QTENSOR     — path to qtensor CSV (for building international quarterly tensor)
  PHASE4_QTENSOR_COL — column name for the value: "jobs" or "births"
  PHASE4_COUNTRY     — country code: nl | be | pt

All remaining argv are forwarded to train_herald_regime_experiment.main().
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Must be done BEFORE any import of train_herald_v6/v7.
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src" / "modeles"))

import numpy as np
import pandas as pd


def _require_env(key: str) -> str:
    val = os.environ.get(key)
    if not val:
        print(f"ERROR: environment variable {key} is required", file=sys.stderr)
        sys.exit(1)
    return val


def _build_international_qtensor(
    qtensor_path: str,
    qtensor_col: str,
    mapping_path: str,
    zones_sorted: list,
    years_sorted: list,
) -> "np.ndarray":
    """Build (T, 3, N, 2) quarterly tensor from international annual employment/births data.

    Slot ty gets data from year ty (raw). The effectifs_lag1 policy applied downstream
    will shift to use ty-1 data when predicting ty.

    Channel 0: employment / births (the qtensor_col)
    Channel 1: 0 (no wage/payroll data for international countries)
    """
    qt = pd.read_csv(qtensor_path)
    mapping = pd.read_csv(mapping_path)
    zm = mapping.set_index("zone_id")["ZE2020"].to_dict()

    # Aggregate across sectors → total signal per zone per year
    qt["ze_int"] = qt["zone_id"].map(zm)
    agg = qt.groupby(["ze_int", "target_year"])[qtensor_col].sum()

    zone_to_idx = {z: i for i, z in enumerate(zones_sorted)}
    year_to_idx = {y: i for i, y in enumerate(years_sorted)}

    T, N = len(years_sorted), len(zones_sorted)
    tensor = np.zeros((T, 3, N, 2), dtype=np.float32)

    for (ze_int, yr), val in agg.items():
        if ze_int not in zone_to_idx or yr not in year_to_idx:
            continue
        zi = zone_to_idx[ze_int]
        ti = year_to_idx[yr]
        # Store in all 3 quarters so any quarter-selection logic works
        for q in range(3):
            tensor[ti, q, zi, 0] = float(val)

    return tensor


def main() -> None:
    panel_path   = _require_env("PHASE4_PANEL")
    splits_path  = _require_env("PHASE4_SPLITS")
    side_a10     = _require_env("PHASE4_SIDE_A10")
    geo_adj      = _require_env("PHASE4_GEO_ADJ")
    mob_adj      = _require_env("PHASE4_MOB_ADJ")
    qtensor_path = _require_env("PHASE4_QTENSOR")
    qtensor_col  = _require_env("PHASE4_QTENSOR_COL")
    country      = _require_env("PHASE4_COUNTRY")
    mapping_path = str(Path(panel_path).parent / "zone_mapping.csv")

    # Patch train_herald_v6 globals BEFORE the training modules import them.
    import train_herald_v6 as v6
    v6.GEO_ADJ_PATH  = Path(geo_adj)
    v6.MOB_ADJ_PATH  = Path(mob_adj)
    v6.PANEL_PATH    = Path(panel_path)
    v6.SPLITS_PATH   = Path(splits_path)
    v6.SIDE_A10_PATH = Path(side_a10)

    # Override build_quarterly_tensor with the international version.
    _original_build_qt = v6.build_quarterly_tensor

    def _intl_build_quarterly_tensor(zones_sorted, years_sorted):
        return _build_international_qtensor(
            qtensor_path, qtensor_col, mapping_path,
            zones_sorted, years_sorted,
        )

    v6.build_quarterly_tensor = _intl_build_quarterly_tensor

    # Forward remaining argv to the training script.
    import train_herald_regime_experiment as trainer
    trainer.main()


if __name__ == "__main__":
    main()
