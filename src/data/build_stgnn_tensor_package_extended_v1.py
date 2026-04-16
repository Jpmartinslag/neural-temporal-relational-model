import numpy as np
import pandas as pd
from pathlib import Path
import json
import os

ROOT = Path(__file__).resolve().parents[2]
PANEL_PATH = ROOT / "data" / "processed" / "extended_panel_core_v0.csv"
ADJ_GEO_PATH = ROOT / "data" / "processed" / "graph_adjacency_core_v0.csv"
ADJ_MOB_PATH = ROOT / "data" / "processed" / "graph_adjacency_mobility_v0.csv"

def build_tensor(name, feature_subset):
    TENSOR_OUT = ROOT / "data" / "processed" / f"stgnn_tensor_package_{name}_v1.npz"
    QUALITY_OUT = ROOT / "reports" / f"stgnn_tensor_package_{name}_quality_v1.json"

    INDEX_COLS = ["year", "node_idx", "ze2020", "libze2020", "reg"]
    TARGET_COL = "side_establishment_creations_official"

    # 1. Load Data
    df = pd.read_csv(PANEL_PATH, dtype={"ze2020": str})

    # 2. Sort
    df = df.sort_values(["year", "node_idx"]).reset_index(drop=True)

    # 3. Setup Dimensions
    years = sorted(df["year"].unique())
    node_ids = sorted(df["node_idx"].unique())

    print(f"Building tensor {name} with {len(years)} years, {len(node_ids)} nodes, and {len(feature_subset)} features.")

    # 4. Build X, Y, Mask
    x_raw = df[feature_subset].to_numpy(dtype=float).reshape(len(years), len(node_ids), len(feature_subset))
    y_raw = df[TARGET_COL].to_numpy(dtype=float).reshape(len(years), len(node_ids))
    x_mask = np.isfinite(x_raw).astype(np.float32)

    # 5. Scaling (on train years <= 2022)
    train_years = [y for y in years if y <= 2022]
    train_yr_indices = [i for i, y in enumerate(years) if y in train_years]

    x_train = x_raw[train_yr_indices]
    feature_mean = np.nanmean(x_train, axis=(0, 1))
    feature_std = np.nanstd(x_train, axis=(0, 1))
    feature_std[feature_std == 0] = 1.0

    x_scaled = (x_raw - feature_mean.reshape(1, 1, -1)) / feature_std.reshape(1, 1, -1)
    x_scaled_imputed = np.where(np.isfinite(x_scaled), x_scaled, 0.0).astype(np.float32)

    # 6. Adjacencies
    adj_geo = pd.read_csv(ADJ_GEO_PATH).set_index("source_idx").to_numpy(dtype=np.float32)
    adj_mob = pd.read_csv(ADJ_MOB_PATH).set_index("source_idx").to_numpy(dtype=np.float32)
    expected_shape = (len(node_ids), len(node_ids))
    if adj_geo.shape != expected_shape:
        raise ValueError(f"Geographic adjacency has shape {adj_geo.shape}, expected {expected_shape}.")
    if adj_mob.shape != expected_shape:
        raise ValueError(f"Mobility adjacency has shape {adj_mob.shape}, expected {expected_shape}.")

    # 7. Save
    np.savez_compressed(
        TENSOR_OUT,
        x_raw=x_raw.astype(np.float32),
        x_scaled_imputed=x_scaled_imputed,
        x_mask=x_mask,
        y_raw=y_raw.astype(np.float32),
        adjacency_geo=adj_geo,
        adjacency_mobility=adj_mob,
        years=np.array(years, dtype=np.int16),
        node_idx=np.array(node_ids, dtype=np.int16),
        feature_name=np.array(feature_subset),
        feature_mean=feature_mean.astype(np.float32),
        feature_std=feature_std.astype(np.float32)
    )

    quality = {
        "name": name,
        "years": [int(y) for y in years],
        "nodes": int(len(node_ids)),
        "features": list(feature_subset),
        "x_shape": [int(s) for s in x_scaled_imputed.shape],
        "y_shape": [int(s) for s in y_raw.shape],
        "adjacency_geo_shape": [int(s) for s in adj_geo.shape],
        "adjacency_mobility_shape": [int(s) for s in adj_mob.shape],
        "train_years_count": int(len(train_years))
    }

    with open(QUALITY_OUT, 'w') as f:
        json.dump(quality, f, indent=4)
    print(f"Tensor {name} saved to {TENSOR_OUT}")

if __name__ == "__main__":
    panel = pd.read_csv(PANEL_PATH, nrows=1)
    weights = [c for c in panel.columns if c.startswith("weight_a17_")]

    forecast_features = [
        "nb_com",
        "total_establishments",
        "stock_lag_1",
        "side_creations_lag_1",
        "side_creations_spatial_lag_1",
        "side_creations_mobility_lag_1",
        "pop_lag_1",
        "pop_lag_2",
        "regime_signal_lag_1",
        "sitadel_surface_autorisee_lag_1",
        "sitadel_surface_commencee_lag_1",
    ] + weights

    nowcast_q1_features = forecast_features + ["regime_signal_jan_mar"]
    diagnostic_features = nowcast_q1_features + [
        "regime_signal_jan_jun",
        "regime_signal_jan_sep",
        "regime_signal_jan_dec",
    ]

    build_tensor("extended_forecast_core", forecast_features)
    build_tensor("extended_nowcast_q1_core", nowcast_q1_features)
    build_tensor("extended_diagnostic_core", diagnostic_features)
