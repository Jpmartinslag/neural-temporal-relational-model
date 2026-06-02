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


def _graph_stats(adj_path: str) -> dict:
    """Compute graph metadata from an adjacency CSV. Used for run provenance."""
    import json as _json
    df = pd.read_csv(adj_path)
    mat = df.drop("source_idx", axis=1).values.astype(np.float64)
    N = mat.shape[0]
    diag = np.diag(mat)
    off_mask = ~np.eye(N, dtype=bool)
    return {
        "graph_path": str(adj_path),
        "graph_shape": [N, N],
        "graph_density": float((mat[off_mask] > 0).sum() / (N * (N - 1))),
        "graph_diag_mean": float(diag.mean()),
        "graph_diag_min": float(diag.min()),
        "graph_diag_max": float(diag.max()),
        "graph_row_sum_min": float(mat.sum(axis=1).min()),
        "graph_row_sum_max": float(mat.sum(axis=1).max()),
        "graph_avg_off_neighbors": float((mat[off_mask] > 0).sum() / N),
    }


def _inject_graph_metadata(metadata_path: str, graph_meta: dict, graph_policy: str,
                           tensor_policy: str, feature_policy: str, country: str,
                           config_label: str) -> None:
    """Append graph/config provenance fields to the trainer's metadata JSON."""
    import json as _json
    p = Path(metadata_path)
    if not p.exists():
        return
    try:
        data = _json.loads(p.read_text())
    except Exception:
        data = {}
    data.update(graph_meta)
    data["graph_policy"] = graph_policy
    data["tensor_policy"] = tensor_policy
    data["feature_policy"] = feature_policy
    data["country"] = country
    data["config_label"] = config_label
    p.write_text(_json.dumps(data, indent=2), encoding="utf-8")


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

    # Optional provenance vars (set by phase4d seed script)
    graph_policy  = os.environ.get("PHASE4_GRAPH_POLICY", Path(geo_adj).stem)
    tensor_policy = os.environ.get("PHASE4_TENSOR_POLICY", "unknown")
    feature_policy = os.environ.get("PHASE4_FEATURE_POLICY", "unknown")
    config_label  = os.environ.get("PHASE4_CONFIG_LABEL", "unknown")

    # Compute graph stats before training (fail fast if adj path is wrong)
    graph_meta = _graph_stats(geo_adj)
    print(f"[wrapper] graph={graph_policy} path={geo_adj}")
    print(f"[wrapper] graph_density={graph_meta['graph_density']:.3f} "
          f"diag_mean={graph_meta['graph_diag_mean']:.3f} "
          f"avg_neighbors={graph_meta['graph_avg_off_neighbors']:.1f}")

    # Parse --regime-metadata-path from sys.argv so we can inject graph metadata after training
    metadata_path: str | None = None
    for i, arg in enumerate(sys.argv):
        if arg == "--regime-metadata-path" and i + 1 < len(sys.argv):
            metadata_path = sys.argv[i + 1]
            break

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

    # After training, inject graph provenance into metadata JSON
    if metadata_path:
        _inject_graph_metadata(
            metadata_path, graph_meta, graph_policy,
            tensor_policy, feature_policy, country, config_label,
        )


if __name__ == "__main__":
    main()
