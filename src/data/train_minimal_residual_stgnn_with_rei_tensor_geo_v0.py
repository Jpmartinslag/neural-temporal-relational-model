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
METRICS_OUT = ROOT / "reports" / "minimal_residual_stgnn_with_rei_tensor_geo_metrics_v0.json"
REPORT_OUT = ROOT / "reports" / "MINIMAL_RESIDUAL_STGNN_WITH_REI_TENSOR_GEO_V0.md"
PRED_OUT = ROOT / "data" / "processed" / "minimal_residual_stgnn_with_rei_tensor_geo_predictions_v0.csv"

TARGET_YEARS = [2021, 2022, 2023, 2024]
BASE_FEATURES = ["side_creations_lag_1", "nb_com", "rei_cfe_microentrepreneurs_created_n_1_lag_1"]
HIDDEN_DIM = 16
EPOCHS = 500
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


def load_tensor():
    package = np.load(TENSOR_PATH, allow_pickle=True)
    feature_names = [str(x) for x in package["feature_name"]]
    feature_idx = [feature_names.index(name) for name in BASE_FEATURES]
    node_index = pd.read_csv(NODE_INDEX_PATH, usecols=["node_idx", "ze2020", "libze2020"])
    return {
        "years": package["years"].astype(int),
        "node_idx": package["node_idx"].astype(int),
        "x_raw": package["x_raw"][:, :, feature_idx].astype(float),
        "y_raw": package["y_raw"].astype(float),
        "adjacency_geo": package["adjacency_geo"].astype(np.float32),
        "node_index": node_index,
    }


class MinimalResidualSTGNN(nn.Module):
    def __init__(self, in_dim, hidden_dim):
        super().__init__()
        self.graph_in = nn.Linear(in_dim, hidden_dim)
        self.gru_cell = nn.GRUCell(hidden_dim, hidden_dim)
        self.out = nn.Linear(hidden_dim, 1)

    def forward(self, x_seq, adj):
        t_steps, n_nodes, _ = x_seq.shape
        hidden = torch.zeros(n_nodes, self.graph_in.out_features, device=x_seq.device)
        outputs = []
        for t in range(t_steps):
            g = torch.matmul(adj, x_seq[t])
            g = torch.relu(self.graph_in(g))
            hidden = self.gru_cell(g, hidden)
            outputs.append(self.out(hidden).squeeze(-1))
        return torch.stack(outputs, dim=0)


def fit_residual_stgnn(train_x_seq, train_resid_seq, full_x_seq, adj):
    set_seed()
    device = torch.device("cpu")
    adj_t = torch.tensor(adj, dtype=torch.float32, device=device)
    x_train = torch.tensor(train_x_seq, dtype=torch.float32, device=device)
    y_train = torch.tensor(train_resid_seq, dtype=torch.float32, device=device)
    x_full = torch.tensor(full_x_seq, dtype=torch.float32, device=device)

    model = MinimalResidualSTGNN(in_dim=train_x_seq.shape[-1], hidden_dim=HIDDEN_DIM).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=LR, weight_decay=WEIGHT_DECAY)
    loss_fn = nn.HuberLoss(delta=1.0)

    model.train()
    for _ in range(EPOCHS):
        opt.zero_grad()
        pred = model(x_train, adj_t)
        loss = loss_fn(pred, y_train)
        loss.backward()
        opt.step()

    model.eval()
    with torch.no_grad():
        pred_full = model(x_full, adj_t).cpu().numpy()
    return pred_full


def evaluate(data):
    years = data["years"]
    node_ids = data["node_idx"]
    x_raw = data["x_raw"]
    y_raw = data["y_raw"]
    adj = data["adjacency_geo"]
    node_index = data["node_index"]

    pred_rows = []
    rows = []

    for target_year in TARGET_YEARS:
        test_pos = int(np.where(years == target_year)[0][0])
        train_pos = np.where(years < target_year)[0]

        X_train_seq_raw = x_raw[train_pos]
        X_test_seq_raw = x_raw[[test_pos]]
        X_train_seq, X_test_seq, valid = scale_and_impute_from_train(X_train_seq_raw, X_test_seq_raw)
        kept_features = [f for f, ok in zip(BASE_FEATURES, valid) if ok]

        X_train_flat = X_train_seq.reshape(-1, len(kept_features))
        y_train_flat = y_raw[train_pos].reshape(-1)
        X_test_flat = X_test_seq.reshape(-1, len(kept_features))
        y_test = y_raw[test_pos]

        ridge = fit_ridge(X_train_flat, y_train_flat)
        ridge_train_pred = np.clip(ridge.predict(X_train_flat), a_min=0, a_max=None).reshape(len(train_pos), len(node_ids))
        ridge_test_pred = np.clip(ridge.predict(X_test_flat), a_min=0, a_max=None)

        resid_train = y_raw[train_pos] - ridge_train_pred
        resid_mean = float(np.mean(resid_train))
        resid_std = float(np.std(resid_train))
        if resid_std == 0:
            resid_std = 1.0
        resid_train_scaled = (resid_train - resid_mean) / resid_std

        X_full_seq = np.concatenate([X_train_seq, X_test_seq], axis=0)
        pred_resid_scaled_full = fit_residual_stgnn(X_train_seq, resid_train_scaled, X_full_seq, adj)
        pred_resid_full = pred_resid_scaled_full * resid_std + resid_mean
        pred_test = np.clip(ridge_test_pred + pred_resid_full[-1], a_min=0, a_max=None)

        out = (
            node_index.copy()
            .assign(
                target_year=target_year,
                y_true=y_test,
                baseline_pred=ridge_test_pred,
                predicted_residual=pred_resid_full[-1],
                prediction=pred_test,
                features_used=",".join(kept_features),
            )
        )
        pred_rows.append(out[["target_year", "node_idx", "ze2020", "libze2020", "y_true", "baseline_pred", "predicted_residual", "prediction", "features_used"]])

        rows.append(
            {
                "target_year": int(target_year),
                "features": kept_features,
                "baseline_wmape": wmape(y_test, ridge_test_pred),
                "minimal_residual_stgnn_wmape": wmape(y_test, pred_test),
            }
        )

    return pd.concat(pred_rows, ignore_index=True), rows


def main():
    data = load_tensor()
    pred_df, rows = evaluate(data)
    pred_df.to_csv(PRED_OUT, index=False)

    baseline_mean = float(np.mean([r["baseline_wmape"] for r in rows]))
    candidate_mean = float(np.mean([r["minimal_residual_stgnn_wmape"] for r in rows]))
    payload = {
        "tensor_path": str(TENSOR_PATH.relative_to(ROOT)),
        "model": "minimal_residual_stgnn_with_rei_tensor_geo",
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
                str(r["target_year"]): float(r["minimal_residual_stgnn_wmape"] - r["baseline_wmape"]) for r in rows
            },
            "worsened_years": [int(r["target_year"]) for r in rows if r["minimal_residual_stgnn_wmape"] - r["baseline_wmape"] > 1e-6],
            "strictly_better_with_tolerance": bool(
                candidate_mean < baseline_mean and all(r["minimal_residual_stgnn_wmape"] - r["baseline_wmape"] <= 1e-6 for r in rows)
            ),
        },
        "prediction_output": str(PRED_OUT.relative_to(ROOT)),
    }
    METRICS_OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    cmp = payload["comparison_vs_rei_created_baseline"]
    lines = [
        "# Minimal Residual STGNN With REI Tensor Geo v0",
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
