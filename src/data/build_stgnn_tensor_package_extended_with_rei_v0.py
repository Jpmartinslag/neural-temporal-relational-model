import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
PANEL_PATH = ROOT / "data" / "processed" / "extended_panel_core_v0.csv"
REI_PATH = ROOT / "data" / "interim" / "tables" / "rei_cfe_ze2020_v0.csv"
ADJ_GEO_PATH = ROOT / "data" / "processed" / "graph_adjacency_core_v0.csv"
ADJ_MOB_PATH = ROOT / "data" / "processed" / "graph_adjacency_mobility_v0.csv"
TENSOR_OUT = ROOT / "data" / "processed" / "stgnn_tensor_package_extended_forecast_with_rei_core_v0.npz"
QUALITY_OUT = ROOT / "reports" / "stgnn_tensor_package_extended_forecast_with_rei_core_quality_v0.json"

INDEX_COLS = ["year", "node_idx", "ze2020", "libze2020", "reg"]
TARGET_COL = "side_establishment_creations_official"
REI_FEATURE = "rei_cfe_microentrepreneurs_created_n_1_lag_1"


def build_feature_list(panel):
    weights = [c for c in panel.columns if c.startswith("weight_a17_")]
    return [
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
        REI_FEATURE,
    ] + weights


def load_panel_with_rei():
    df = pd.read_csv(PANEL_PATH, dtype={"ze2020": str})
    rei = pd.read_csv(REI_PATH, dtype={"ZE2020": str}).rename(columns={"ZE2020": "ze2020"})
    rei = rei.sort_values(["ze2020", "year"]).copy()
    rei[REI_FEATURE] = rei.groupby("ze2020")["rei_cfe_microentrepreneurs_created_n_1"].shift(1)
    rei = rei[["ze2020", "year", REI_FEATURE]]

    df = df.merge(rei, on=["ze2020", "year"], how="left")
    return df.sort_values(["year", "node_idx"]).reset_index(drop=True)


def build_tensor():
    df = load_panel_with_rei()
    feature_subset = build_feature_list(df)

    years = sorted(df["year"].unique())
    node_ids = sorted(df["node_idx"].unique())

    x_raw = df[feature_subset].to_numpy(dtype=float).reshape(len(years), len(node_ids), len(feature_subset))
    y_raw = df[TARGET_COL].to_numpy(dtype=float).reshape(len(years), len(node_ids))
    x_mask = np.isfinite(x_raw).astype(np.float32)

    train_years = [y for y in years if y <= 2022]
    train_yr_indices = [i for i, y in enumerate(years) if y in train_years]
    x_train = x_raw[train_yr_indices]
    feature_mean = np.nanmean(x_train, axis=(0, 1))
    feature_std = np.nanstd(x_train, axis=(0, 1))
    feature_std[feature_std == 0] = 1.0

    x_scaled = (x_raw - feature_mean.reshape(1, 1, -1)) / feature_std.reshape(1, 1, -1)
    x_scaled_imputed = np.where(np.isfinite(x_scaled), x_scaled, 0.0).astype(np.float32)

    adj_geo = pd.read_csv(ADJ_GEO_PATH).set_index("source_idx").to_numpy(dtype=np.float32)
    adj_mob = pd.read_csv(ADJ_MOB_PATH).set_index("source_idx").to_numpy(dtype=np.float32)
    expected_shape = (len(node_ids), len(node_ids))
    if adj_geo.shape != expected_shape or adj_mob.shape != expected_shape:
        raise ValueError(f"Adjacency shape mismatch: geo={adj_geo.shape}, mob={adj_mob.shape}, expected={expected_shape}")

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
        feature_std=feature_std.astype(np.float32),
    )

    quality = {
        "name": "extended_forecast_with_rei_core_v0",
        "years": [int(y) for y in years],
        "nodes": int(len(node_ids)),
        "features": list(feature_subset),
        "x_shape": [int(s) for s in x_scaled_imputed.shape],
        "y_shape": [int(s) for s in y_raw.shape],
        "adjacency_geo_shape": [int(s) for s in adj_geo.shape],
        "adjacency_mobility_shape": [int(s) for s in adj_mob.shape],
        "train_years_count": int(len(train_years)),
        "rei_feature": REI_FEATURE,
        "rei_missing_share": float(np.isnan(df[REI_FEATURE].to_numpy(dtype=float)).mean()),
    }
    QUALITY_OUT.write_text(json.dumps(quality, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(quality, indent=2, ensure_ascii=False))
    print(f"Saved tensor to {TENSOR_OUT}")
    print(f"Saved quality report to {QUALITY_OUT}")


if __name__ == "__main__":
    build_tensor()
