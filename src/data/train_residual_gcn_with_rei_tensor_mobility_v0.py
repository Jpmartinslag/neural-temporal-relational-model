import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import RidgeCV

try:
    import torch
    import torch.nn as nn
except ModuleNotFoundError as exc:  # pragma: no cover
    raise SystemExit(
        "This script requires PyTorch on the target machine. Install torch there and rerun."
    ) from exc


ROOT = Path(__file__).resolve().parents[2]
TENSOR_PATH = ROOT / "data" / "processed" / "stgnn_tensor_package_extended_forecast_with_rei_core_v0.npz"
NODE_INDEX_PATH = ROOT / "data" / "processed" / "graph_node_index_core_v0.csv"
METRICS_OUT = ROOT / "reports" / "residual_gcn_with_rei_tensor_mobility_metrics_v0.json"
REPORT_OUT = ROOT / "reports" / "RESIDUAL_GCN_WITH_REI_TENSOR_MOBILITY_V0.md"
PRED_OUT = ROOT / "data" / "processed" / "residual_gcn_with_rei_tensor_mobility_predictions_v0.csv"

TARGET_YEARS = [2021, 2022, 2023, 2024]
BASE_FEATURES = ["side_creations_lag_1", "nb_com", "rei_cfe_microentrepreneurs_created_n_1_lag_1"]
HIDDEN_DIM = 16
EPOCHS = 400
LR = 1e-2
WEIGHT_DECAY = 1e-4
SEED = 0


def wmape(y_true, y_pred):
    denom = np.sum(np.abs(y_true))
    if denom == 0:
        return np.nan
    return float(np.sum(np.abs(y_true - y_pred)) / denom * 100.0)


def set_seed():
    np.random.seed(SEED)
    torch.manual_seed(SEED)


def scale_and_impute_from_train(X_train_raw, X_test_raw):
    X_train_scaled = np.zeros_like(X_train_raw, dtype=float)
    X_test_scaled = np.zeros_like(X_test_raw, dtype=float)
    valid = []
    for i in range(X_train_raw.shape[-1]):
        train_col = X_train_raw[..., i]
        test_col = X_test_raw[..., i]
        observed_train = train_col[np.isfinite(train_col)]
        if len(observed_train) == 0:
            valid.append(False)
            continue
        mean = observed_train.mean()
        std = observed_train.std()
        if std == 0:
            std = 1.0
        X_train_scaled[..., i] = np.where(np.isfinite(train_col), (train_col - mean) / std, 0.0)
        X_test_scaled[..., i] = np.where(np.isfinite(test_col), (test_col - mean) / std, 0.0)
        valid.append(True)
    valid = np.array(valid, dtype=bool)
    return X_train_scaled[..., valid], X_test_scaled[..., valid], valid


def fit_ridge(X_train, y_train):
    model = RidgeCV(alphas=np.logspace(-3, 5, 20))
    model.fit(X_train, y_train)
    return model


def load_frame():
    package = np.load(TENSOR_PATH, allow_pickle=True)
    feature_names = [str(x) for x in package["feature_name"]]
    feature_idx = [feature_names.index(name) for name in BASE_FEATURES]
    node_index = pd.read_csv(NODE_INDEX_PATH, usecols=["node_idx", "ze2020", "libze2020"])

    frames = []
    for pos, year in enumerate(package["years"].astype(int)):
        chunk = pd.DataFrame(
            {
                "node_idx": package["node_idx"].astype(int),
                "target_year": int(year),
                "y_true": package["y_raw"][pos].astype(float),
            }
        )
        for feat, idx in zip(BASE_FEATURES, feature_idx):
            chunk[feat] = package["x_raw"][pos][:, idx].astype(float)
        frames.append(chunk)

    df = pd.concat(frames, ignore_index=True)
    df = df.merge(node_index, on="node_idx", how="left")
    return df, package["adjacency_mobility"].astype(np.float32)


class ResidualGCN(nn.Module):
    def __init__(self, in_dim, hidden_dim):
        super().__init__()
        self.lin1 = nn.Linear(in_dim, hidden_dim)
        self.lin2 = nn.Linear(hidden_dim, 1)

    def forward(self, x, adj):
        h = torch.matmul(adj, x)
        h = torch.relu(self.lin1(h))
        h = torch.matmul(adj, h)
        return self.lin2(h).squeeze(-1)


def fit_residual_gcn(train_x, train_resid, test_x, adj):
    set_seed()
    device = torch.device("cpu")
    adj_t = torch.tensor(adj, dtype=torch.float32, device=device)
    x_train = torch.tensor(train_x, dtype=torch.float32, device=device)
    r_train = torch.tensor(train_resid, dtype=torch.float32, device=device)
    x_test = torch.tensor(test_x, dtype=torch.float32, device=device)

    model = ResidualGCN(train_x.shape[-1], HIDDEN_DIM).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=LR, weight_decay=WEIGHT_DECAY)
    loss_fn = nn.HuberLoss(delta=1.0)

    model.train()
    for _ in range(EPOCHS):
        opt.zero_grad()
        pred_resid = model(x_train, adj_t)
        loss = loss_fn(pred_resid, r_train)
        loss.backward()
        opt.step()

    model.eval()
    with torch.no_grad():
        pred_test = model(x_test, adj_t).cpu().numpy()
    return pred_test


def evaluate(df, adj):
    pred_rows = []
    rows = []

    for target_year in TARGET_YEARS:
        train_df = df[df["target_year"] < target_year].copy()
        test_df = df[df["target_year"] == target_year].copy()
        train_df = train_df[np.isfinite(train_df["y_true"])]
        test_df = test_df[np.isfinite(test_df["y_true"]) & np.isfinite(test_df["side_creations_lag_1"])]

        X_train_flat_raw = train_df[BASE_FEATURES].to_numpy(dtype=float)
        y_train_flat = train_df["y_true"].to_numpy(dtype=float)
        X_test_flat_raw = test_df[BASE_FEATURES].to_numpy(dtype=float)
        y_test_flat = test_df["y_true"].to_numpy(dtype=float)

        X_train_flat, X_test_flat, valid = scale_and_impute_from_train(X_train_flat_raw, X_test_flat_raw)
        kept_features = [f for f, ok in zip(BASE_FEATURES, valid) if ok]

        ridge = fit_ridge(X_train_flat, y_train_flat)
        ridge_train_pred = np.clip(ridge.predict(X_train_flat), a_min=0, a_max=None)
        ridge_test_pred = np.clip(ridge.predict(X_test_flat), a_min=0, a_max=None)

        train_df = train_df.copy()
        test_df = test_df.copy()
        for j, feat in enumerate(kept_features):
            train_df[feat] = X_train_flat[:, j]
            test_df[feat] = X_test_flat[:, j]
        train_df["baseline_pred"] = ridge_train_pred
        test_df["baseline_pred"] = ridge_test_pred
        train_df["residual_target"] = train_df["y_true"] - train_df["baseline_pred"]

        train_pivot_x = train_df.pivot(index="target_year", columns="node_idx", values=kept_features).sort_index(axis=0).sort_index(axis=1)
        test_pivot_x = test_df.pivot(index="target_year", columns="node_idx", values=kept_features).sort_index(axis=0).sort_index(axis=1)
        train_pivot_r = train_df.pivot(index="target_year", columns="node_idx", values="residual_target").sort_index(axis=0).sort_index(axis=1)

        train_x = train_pivot_x.to_numpy(dtype=float).reshape(len(train_pivot_x.index), len(train_pivot_r.columns), len(kept_features))
        test_x = test_pivot_x.to_numpy(dtype=float).reshape(1, len(test_df["node_idx"].unique()), len(kept_features))
        train_resid = train_pivot_r.to_numpy(dtype=float)

        pred_resid = fit_residual_gcn(train_x, train_resid, test_x, adj)[0]
        test_nodes = np.sort(test_df["node_idx"].unique())
        correction_map = dict(zip(test_nodes.tolist(), pred_resid.tolist()))

        out = test_df[["target_year", "node_idx", "ze2020", "libze2020", "y_true", "baseline_pred"]].copy()
        out["predicted_residual"] = out["node_idx"].map(correction_map).astype(float)
        out["prediction"] = np.clip(out["baseline_pred"] + out["predicted_residual"], a_min=0, a_max=None)
        pred_rows.append(out)

        rows.append(
            {
                "target_year": int(target_year),
                "features": kept_features,
                "baseline_wmape": wmape(y_test_flat, ridge_test_pred),
                "residual_gcn_wmape": wmape(out["y_true"].to_numpy(float), out["prediction"].to_numpy(float)),
            }
        )

    return pd.concat(pred_rows, ignore_index=True), rows


def main():
    df, adj = load_frame()
    pred_df, rows = evaluate(df, adj)
    pred_df.to_csv(PRED_OUT, index=False)

    baseline_mean = float(np.mean([r["baseline_wmape"] for r in rows]))
    candidate_mean = float(np.mean([r["residual_gcn_wmape"] for r in rows]))
    payload = {
        "tensor_path": str(TENSOR_PATH.relative_to(ROOT)),
        "model": "residual_gcn_with_rei_tensor_mobility",
        "feature_set": BASE_FEATURES,
        "hyperparameters": {
            "hidden_dim": HIDDEN_DIM,
            "epochs": EPOCHS,
            "lr": LR,
            "weight_decay": WEIGHT_DECAY,
            "seed": SEED,
        },
        "summary_by_year": rows,
        "comparison_vs_rei_created_baseline": {
            "mean_delta": float(candidate_mean - baseline_mean),
            "per_year_delta": {
                str(r["target_year"]): float(r["residual_gcn_wmape"] - r["baseline_wmape"]) for r in rows
            },
            "worsened_years": [int(r["target_year"]) for r in rows if r["residual_gcn_wmape"] - r["baseline_wmape"] > 1e-6],
            "strictly_better_with_tolerance": bool(
                candidate_mean < baseline_mean and all(r["residual_gcn_wmape"] - r["baseline_wmape"] <= 1e-6 for r in rows)
            ),
        },
        "prediction_output": str(PRED_OUT.relative_to(ROOT)),
    }
    METRICS_OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    cmp = payload["comparison_vs_rei_created_baseline"]
    lines = [
        "# Residual GCN With REI Tensor Mobility v0",
        "",
        f"- tensor_path: `{payload['tensor_path']}`",
        f"- feature_set: `{BASE_FEATURES}`",
        f"- hidden_dim: `{HIDDEN_DIM}`",
        f"- epochs: `{EPOCHS}`",
        f"- mean_delta vs rei_created_baseline: `{cmp['mean_delta']:.3f}`",
        f"- worsened_years: `{cmp['worsened_years']}`",
        f"- strictly_better_with_tolerance: `{cmp['strictly_better_with_tolerance']}`",
        f"- prediction_output: `{payload['prediction_output']}`",
    ]
    REPORT_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps(payload, indent=2, ensure_ascii=False))
    print(f"Saved predictions to {PRED_OUT}")
    print(f"Saved metrics to {METRICS_OUT}")
    print(f"Saved report to {REPORT_OUT}")


if __name__ == "__main__":
    main()
