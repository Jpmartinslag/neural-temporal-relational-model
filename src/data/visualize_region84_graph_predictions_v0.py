import json
from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
from sklearn.linear_model import RidgeCV


ROOT = Path(__file__).resolve().parents[2]
TENSOR_PATH = ROOT / "data" / "processed" / "stgnn_tensor_package_extended_forecast_core_v1.npz"
PANEL_PATH = ROOT / "data" / "processed" / "panel_zones_core_v0.csv"
NODES_PATH = ROOT / "data" / "processed" / "graph_nodes_ze2020_core_v0.csv"
NODE_INDEX_PATH = ROOT / "data" / "processed" / "graph_node_index_core_v0.csv"
EDGES_PATH = ROOT / "data" / "processed" / "graph_edges_ze2020_core_v0.csv"
FIGURE_OUT = ROOT / "reports" / "REGION84_GRAPH_PREDICTIONS_V0.png"
TABLE_OUT = ROOT / "reports" / "region84_graph_predictions_v0.csv"
METADATA_OUT = ROOT / "reports" / "region84_graph_predictions_v0.json"

TARGET_YEAR = 2023
REGION_CODE = 84
LAG_ONLY_FEATURES = ["side_creations_lag_1"]
BASE_FEATURES = ["side_creations_lag_1", "nb_com"]
GEO_FEATURES = [
    "side_creations_lag_1",
    "nb_com",
    "geo_neighbor_side_creations_lag_1",
    "geo_neighbor_nb_com",
]


def normalize_rows(matrix):
    row_sums = matrix.sum(axis=1, keepdims=True)
    safe_denominator = np.where(row_sums > 0, row_sums, 1.0)
    normalized = matrix / safe_denominator
    normalized[row_sums.squeeze() == 0] = 0.0
    return normalized


def scale_and_impute_from_train(X_train_raw, X_test_raw):
    X_train_scaled = np.zeros_like(X_train_raw, dtype=float)
    X_test_scaled = np.zeros_like(X_test_raw, dtype=float)
    valid = []

    for i in range(X_train_raw.shape[1]):
        train_col = X_train_raw[:, i]
        test_col = X_test_raw[:, i]
        observed_train = train_col[np.isfinite(train_col)]
        if len(observed_train) == 0:
            valid.append(False)
            continue

        mean = observed_train.mean()
        std = observed_train.std()
        if std == 0:
            std = 1.0

        X_train_scaled[:, i] = np.where(np.isfinite(train_col), (train_col - mean) / std, 0.0)
        X_test_scaled[:, i] = np.where(np.isfinite(test_col), (test_col - mean) / std, 0.0)
        valid.append(True)

    valid = np.array(valid, dtype=bool)
    return X_train_scaled[:, valid], X_test_scaled[:, valid], valid


def fit_ridge(X_train, y_train):
    model = RidgeCV(alphas=np.logspace(-3, 5, 20))
    model.fit(X_train, y_train)
    return model


def load_tensor():
    package = np.load(TENSOR_PATH, allow_pickle=True)
    return {
        "years": package["years"].astype(int),
        "node_idx": package["node_idx"].astype(int),
        "feature_name": np.array([str(name) for name in package["feature_name"]]),
        "x_raw": package["x_raw"].astype(float),
        "y_raw": package["y_raw"].astype(float),
        "adjacency_geo": normalize_rows(package["adjacency_geo"].astype(float)),
    }


def build_baseline_features(data, pos, feature_indices):
    return data["x_raw"][pos][:, feature_indices]


def build_geo_features(data, pos, feature_indices):
    local = data["x_raw"][pos][:, feature_indices]
    spatial = data["adjacency_geo"] @ local
    return np.concatenate([local, spatial], axis=1)


def predict_for_year(data, target_year, input_features, feature_labels, feature_builder):
    years = data["years"]
    feature_names = data["feature_name"].tolist()
    feature_indices = [feature_names.index(name) for name in input_features]

    test_pos = np.where(years == target_year)[0]
    if len(test_pos) != 1:
        raise ValueError(f"Target year {target_year} not found uniquely in tensor.")
    test_pos = int(test_pos[0])
    train_pos = np.where(years < target_year)[0]
    if len(train_pos) == 0:
        raise ValueError(f"No prior years available before {target_year}.")

    y_train = data["y_raw"][train_pos].reshape(-1)
    y_test = data["y_raw"][test_pos]
    X_train_raw = np.concatenate(
        [feature_builder(data, int(pos), feature_indices) for pos in train_pos],
        axis=0,
    )
    X_test_raw = feature_builder(data, test_pos, feature_indices)

    train_valid = np.isfinite(y_train)
    test_valid = np.isfinite(y_test)
    X_train_raw = X_train_raw[train_valid]
    y_train = y_train[train_valid]
    X_test_raw = X_test_raw[test_valid]
    y_test = y_test[test_valid]
    node_idx_valid = data["node_idx"][test_valid]

    X_train, X_test, valid = scale_and_impute_from_train(X_train_raw, X_test_raw)
    used_features = [name for name, ok in zip(feature_labels, valid) if ok]
    model = fit_ridge(X_train, y_train)
    y_pred = np.clip(model.predict(X_test), a_min=0, a_max=None)

    return {
        "node_idx": node_idx_valid,
        "y_true": y_test,
        "y_pred": y_pred,
        "used_features": used_features,
        "alpha": float(model.alpha_),
        "coefficients": {name: float(value) for name, value in zip(used_features, model.coef_)},
    }


def build_region_frame(data):
    panel = pd.read_csv(PANEL_PATH, usecols=["ze2020", "libze2020", "reg", "year"]).drop_duplicates()
    panel = panel[panel["year"] == TARGET_YEAR][["ze2020", "libze2020", "reg"]].drop_duplicates()
    node_index = pd.read_csv(NODE_INDEX_PATH, usecols=["node_idx", "ze2020"])

    ridge_nbcom = predict_for_year(data, TARGET_YEAR, BASE_FEATURES, BASE_FEATURES, build_baseline_features)
    learned_geo = predict_for_year(data, TARGET_YEAR, BASE_FEATURES, GEO_FEATURES, build_geo_features)

    ridge_frame = pd.DataFrame(
        {
            "node_idx": ridge_nbcom["node_idx"],
            "y_true": ridge_nbcom["y_true"],
            "ridge_lag_nbcom_pred": ridge_nbcom["y_pred"],
        }
    ).merge(node_index, on="node_idx", how="left")
    learned_geo_frame = pd.DataFrame(
        {
            "node_idx": learned_geo["node_idx"],
            "learned_geo_pred": learned_geo["y_pred"],
        }
    ).merge(node_index, on="node_idx", how="left")

    frame = panel.merge(
        ridge_frame[["ze2020", "y_true", "ridge_lag_nbcom_pred"]],
        on="ze2020",
        how="inner",
    ).merge(
        learned_geo_frame[["ze2020", "learned_geo_pred"]],
        on="ze2020",
        how="inner",
    )

    frame["ridge_abs_error"] = np.abs(frame["y_true"] - frame["ridge_lag_nbcom_pred"])
    frame["geo_abs_error"] = np.abs(frame["y_true"] - frame["learned_geo_pred"])
    frame["geo_minus_ridge_error"] = frame["geo_abs_error"] - frame["ridge_abs_error"]

    region_frame = frame[frame["reg"] == REGION_CODE].copy()
    return region_frame, ridge_nbcom, learned_geo


def build_region_graph(region_frame):
    edges = pd.read_csv(EDGES_PATH)
    node_ids = set(region_frame["ze2020"].tolist())
    region_edges = edges[
        edges["source_ze2020"].isin(node_ids) & edges["target_ze2020"].isin(node_ids)
    ].copy()

    graph = nx.Graph()
    for _, row in region_frame.iterrows():
        graph.add_node(int(row["ze2020"]), label=row["libze2020"])
    for _, row in region_edges.iterrows():
        graph.add_edge(int(row["source_ze2020"]), int(row["target_ze2020"]))

    if graph.number_of_edges() == 0:
        raise ValueError(f"No internal regional edges found for region {REGION_CODE}.")

    return graph


def draw_panel(ax, graph, positions, value_map, title, cmap, diverging=False):
    values = np.array([value_map[node] for node in graph.nodes()], dtype=float)
    if diverging:
        vmax = np.max(np.abs(values))
        vmin = -vmax
    else:
        vmin = float(np.min(values))
        vmax = float(np.max(values))

    nx.draw_networkx_edges(graph, positions, ax=ax, alpha=0.25, width=0.8, edge_color="#777777")
    nodes = nx.draw_networkx_nodes(
        graph,
        positions,
        ax=ax,
        node_color=values,
        cmap=cmap,
        node_size=220,
        vmin=vmin,
        vmax=vmax,
        linewidths=0.4,
        edgecolors="#111111",
    )
    nx.draw_networkx_labels(
        graph,
        positions,
        ax=ax,
        labels={node: graph.nodes[node]["label"] for node in graph.nodes()},
        font_size=6,
    )
    ax.set_title(title, fontsize=10)
    ax.set_axis_off()
    return nodes


def save_visualization(region_frame):
    graph = build_region_graph(region_frame)
    positions = nx.spring_layout(graph, seed=42, k=0.55)

    value_maps = {
        "Observed SIDE creations": region_frame.set_index("ze2020")["y_true"].to_dict(),
        "Ridge lag + nb_com prediction": region_frame.set_index("ze2020")["ridge_lag_nbcom_pred"].to_dict(),
        "Geo minus ridge absolute error": region_frame.set_index("ze2020")["geo_minus_ridge_error"].to_dict(),
    }

    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    m0 = draw_panel(axes[0], graph, positions, value_maps["Observed SIDE creations"], "Observed SIDE creations", "viridis")
    m1 = draw_panel(axes[1], graph, positions, value_maps["Ridge lag + nb_com prediction"], "Ridge lag + nb_com prediction", "viridis")
    m2 = draw_panel(
        axes[2],
        graph,
        positions,
        value_maps["Geo minus ridge absolute error"],
        "Geo error minus ridge error",
        "coolwarm",
        diverging=True,
    )

    fig.colorbar(m0, ax=axes[0], fraction=0.046, pad=0.02)
    fig.colorbar(m1, ax=axes[1], fraction=0.046, pad=0.02)
    fig.colorbar(m2, ax=axes[2], fraction=0.046, pad=0.02)
    fig.suptitle(f"Region {REGION_CODE} graph snapshot for target year {TARGET_YEAR}", fontsize=12)
    fig.tight_layout()
    fig.savefig(FIGURE_OUT, dpi=180, bbox_inches="tight")
    plt.close(fig)


def main():
    data = load_tensor()
    region_frame, ridge_nbcom, learned_geo = build_region_frame(data)
    region_frame.to_csv(TABLE_OUT, index=False)
    save_visualization(region_frame)

    payload = {
        "tensor_path": str(TENSOR_PATH.relative_to(ROOT)),
        "target_year": TARGET_YEAR,
        "region_code": REGION_CODE,
        "zones_in_region": int(len(region_frame)),
        "ridge_lag_nbcom_alpha": ridge_nbcom["alpha"],
        "learned_geo_alpha": learned_geo["alpha"],
        "ridge_lag_nbcom_coefficients": ridge_nbcom["coefficients"],
        "learned_geo_coefficients": learned_geo["coefficients"],
        "figure_path": str(FIGURE_OUT.relative_to(ROOT)),
        "table_path": str(TABLE_OUT.relative_to(ROOT)),
    }
    METADATA_OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    print(f"Saved table to {TABLE_OUT}")
    print(f"Saved figure to {FIGURE_OUT}")
    print(f"Saved metadata to {METADATA_OUT}")


if __name__ == "__main__":
    main()
