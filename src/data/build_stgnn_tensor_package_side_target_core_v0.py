from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]

FEATURE_PANEL_PATH = ROOT / "data" / "processed" / "graph_model_feature_panel_core_v0.csv"
TARGET_PANEL_PATH = ROOT / "data" / "processed" / "target_side_establishments_annual_core_v0.csv"
ADJACENCY_PATH = ROOT / "data" / "processed" / "graph_adjacency_core_v0.csv"

TENSOR_OUT = ROOT / "data" / "processed" / "stgnn_tensor_package_side_target_core_v0.npz"
FEATURE_REGISTRY_OUT = ROOT / "metadata" / "stgnn_tensor_feature_registry_side_target_core_v0.csv"
SAMPLE_INDEX_OUT = ROOT / "metadata" / "stgnn_tensor_sample_index_side_target_core_v0.csv"
QUALITY_OUT = ROOT / "reports" / "stgnn_tensor_package_side_target_core_quality_v0.json"
REPORT_OUT = ROOT / "reports" / "STGNN_TENSOR_PACKAGE_SIDE_TARGET_CORE_V0.md"

INDEX_COLS = {"feature_year", "node_idx", "ze2020", "libze2020", "reg"}
TARGET_COL = "side_establishment_creations_official"
HORIZON = 1


def build_row_normalized_adjacency(adjacency: np.ndarray) -> np.ndarray:
    adjacency_with_self = adjacency.astype(float).copy()
    np.fill_diagonal(adjacency_with_self, 1.0)
    row_sum = adjacency_with_self.sum(axis=1, keepdims=True)
    row_sum[row_sum == 0] = 1.0
    return adjacency_with_self / row_sum


def split_for_target_year(target_year: int) -> str:
    if target_year <= 2022:
        return "train"
    if target_year == 2023:
        return "validation"
    if target_year == 2024:
        return "test"
    return "forecast_holdout"


def main() -> None:
    feature_panel = pd.read_csv(FEATURE_PANEL_PATH, dtype={"ze2020": str})
    target_panel = pd.read_csv(TARGET_PANEL_PATH, dtype={"ze2020": str})
    adjacency_frame = pd.read_csv(ADJACENCY_PATH)

    feature_cols = [c for c in feature_panel.columns if c not in INDEX_COLS]
    feature_years = sorted(int(y) for y in feature_panel["feature_year"].unique())
    target_years = sorted(int(y) for y in target_panel["target_year"].unique())
    node_ids = sorted(int(n) for n in feature_panel["node_idx"].unique())

    expected_feature_rows = len(feature_years) * len(node_ids)
    if len(feature_panel) != expected_feature_rows:
        raise ValueError(
            f"Feature panel is not a complete time-node grid: {len(feature_panel)} rows, expected {expected_feature_rows}."
        )

    feature_panel = feature_panel.sort_values(["feature_year", "node_idx"]).reset_index(drop=True)
    target_panel = target_panel.sort_values(["target_year", "node_idx"]).reset_index(drop=True)

    x_raw = (
        feature_panel[feature_cols]
        .to_numpy(dtype=float)
        .reshape(len(feature_years), len(node_ids), len(feature_cols))
    )
    x_mask = np.isfinite(x_raw).astype(np.float32)

    target_values = (
        target_panel[TARGET_COL]
        .to_numpy(dtype=float)
        .reshape(len(target_years), len(node_ids))
    )
    target_year_to_position = {year: idx for idx, year in enumerate(target_years)}

    sample_rows = []
    y_rows = []
    x_positions = []
    for feature_pos, feature_year in enumerate(feature_years):
        target_year = feature_year + HORIZON
        if target_year not in target_year_to_position:
            continue
        sample_rows.append(
            {
                "sample_idx": len(sample_rows),
                "feature_year": feature_year,
                "target_year": target_year,
                "horizon_years": HORIZON,
                "split": split_for_target_year(target_year),
            }
        )
        x_positions.append(feature_pos)
        y_rows.append(target_values[target_year_to_position[target_year]])

    sample_index = pd.DataFrame(sample_rows)
    if sample_index.empty:
        raise ValueError("No aligned feature-target samples were created.")

    y_raw = np.stack(y_rows, axis=0)
    x_sample_raw = x_raw[np.array(x_positions)]
    x_sample_mask = x_mask[np.array(x_positions)]

    train_positions = sample_index.loc[sample_index["split"] == "train"].index.to_numpy()
    if len(train_positions) == 0:
        raise ValueError("No training samples available for scaling.")

    x_train = x_sample_raw[train_positions]
    train_observed_count = np.isfinite(x_train).sum(axis=(0, 1))
    feature_mean = np.zeros(len(feature_cols), dtype=float)
    feature_std = np.ones(len(feature_cols), dtype=float)
    for idx in range(len(feature_cols)):
        observed = x_train[:, :, idx][np.isfinite(x_train[:, :, idx])]
        if len(observed) == 0:
            continue
        feature_mean[idx] = float(observed.mean())
        std = float(observed.std())
        feature_std[idx] = std if std > 0 else 1.0

    x_scaled = (x_sample_raw - feature_mean.reshape(1, 1, -1)) / feature_std.reshape(1, 1, -1)
    x_scaled_imputed = np.where(np.isfinite(x_scaled), x_scaled, 0.0).astype(np.float32)

    adjacency = adjacency_frame.drop(columns=["source_idx"]).to_numpy(dtype=np.float32)
    adjacency_normalized = build_row_normalized_adjacency(adjacency).astype(np.float32)

    feature_registry = pd.DataFrame(
        {
            "feature_idx": range(len(feature_cols)),
            "feature_name": feature_cols,
            "train_mean": feature_mean,
            "train_std": feature_std,
            "train_observed_count": train_observed_count,
            "has_train_observation": train_observed_count > 0,
            "missing_rate_all_samples": np.isnan(x_sample_raw).mean(axis=(0, 1)),
            "scaling_scope": "train_samples_only",
            "imputation_after_scaling": "missing_values_set_to_zero_with_mask_preserved",
        }
    )

    split_counts = sample_index["split"].value_counts().sort_index().to_dict()
    quality = {
        "target_column": TARGET_COL,
        "target_source": str(TARGET_PANEL_PATH.relative_to(ROOT)),
        "node_count": int(len(node_ids)),
        "feature_count": int(len(feature_cols)),
        "feature_years": feature_years,
        "target_years_available": target_years,
        "aligned_feature_years": [int(y) for y in sample_index["feature_year"].to_list()],
        "aligned_target_years": [int(y) for y in sample_index["target_year"].to_list()],
        "horizon_years": HORIZON,
        "sample_count": int(len(sample_index)),
        "split_counts": {k: int(v) for k, v in split_counts.items()},
        "x_raw_shape": list(x_sample_raw.shape),
        "x_scaled_imputed_shape": list(x_scaled_imputed.shape),
        "x_mask_shape": list(x_sample_mask.shape),
        "y_raw_shape": list(y_raw.shape),
        "adjacency_shape": list(adjacency.shape),
        "raw_missing_rate": float(np.isnan(x_sample_raw).mean()),
        "features_without_train_observation": feature_registry.loc[
            ~feature_registry["has_train_observation"], "feature_name"
        ].tolist(),
        "leakage_controls": [
            "Feature scaling is fitted only on train samples.",
            "Validation and test years do not influence feature means or standard deviations.",
            "Missing values are imputed only after scaling and masks are stored explicitly.",
        ],
    }

    np.savez_compressed(
        TENSOR_OUT,
        x_raw=x_sample_raw.astype(np.float32),
        x_scaled_imputed=x_scaled_imputed,
        x_mask=x_sample_mask.astype(np.float32),
        y_raw=y_raw.astype(np.float32),
        adjacency_raw=adjacency.astype(np.float32),
        adjacency_row_normalized_self_loop=adjacency_normalized,
        feature_year=np.array(sample_index["feature_year"].to_list(), dtype=np.int16),
        target_year=np.array(sample_index["target_year"].to_list(), dtype=np.int16),
        node_idx=np.array(node_ids, dtype=np.int16),
        feature_name=np.array(feature_cols),
        feature_mean=feature_mean.astype(np.float32),
        feature_std=feature_std.astype(np.float32),
    )
    feature_registry.to_csv(FEATURE_REGISTRY_OUT, index=False)
    sample_index.to_csv(SAMPLE_INDEX_OUT, index=False)
    QUALITY_OUT.write_text(json.dumps(quality, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(quality)
    print(json.dumps(quality, ensure_ascii=False, indent=2))


def write_report(quality: dict) -> None:
    lines = [
        "# STGNN Tensor Package SIDE Target Core v0",
        "",
        "Data: 2026-04-13",
        "",
        "Objetivo:",
        "",
        "- reconstruir o pacote tensorial usando target oficial `SIDE` estabelecimentos",
        "- manter a mesma camada de features e grafo do `core_v0` para comparacao metodologica",
        "",
        "## Artefatos",
        "",
        f"- tensor: `{TENSOR_OUT.relative_to(ROOT)}`",
        f"- indice de amostras: `{SAMPLE_INDEX_OUT.relative_to(ROOT)}`",
        f"- registro de features: `{FEATURE_REGISTRY_OUT.relative_to(ROOT)}`",
        f"- qualidade: `{QUALITY_OUT.relative_to(ROOT)}`",
        "",
        "## Estrutura",
        "",
        f"- target: `{quality['target_column']}`",
        f"- nos: `{quality['node_count']}`",
        f"- features: `{quality['feature_count']}`",
        f"- horizonte: `{quality['horizon_years']}` ano",
        f"- amostras anuais: `{quality['sample_count']}`",
        f"- splits: `{quality['split_counts']}`",
        f"- anos de feature alinhados: `{quality['aligned_feature_years']}`",
        f"- anos de target alinhados: `{quality['aligned_target_years']}`",
        f"- `x_raw`: `{quality['x_raw_shape']}`",
        f"- `y_raw`: `{quality['y_raw_shape']}`",
        "",
        "## Decisoes",
        "",
        "- a normalizacao continua ajustada apenas no treino",
        "- `0` em `x_scaled_imputed` continua significando media do treino depois da padronizacao",
        "- `x_mask` continua obrigatoria para distinguir dado observado de imputacao",
        "- este pacote nao escolhe arquitetura; ele apenas troca o alvo para a fonte oficial `SIDE`",
        "",
        "## Limites",
        "",
        f"- missingness bruto das features nas amostras: `{quality['raw_missing_rate']:.3f}`",
        f"- features sem observacao no treino: `{quality['features_without_train_observation']}`",
        "- os baselines devem ser reexecutados antes de qualquer modelo complexo",
    ]
    REPORT_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
