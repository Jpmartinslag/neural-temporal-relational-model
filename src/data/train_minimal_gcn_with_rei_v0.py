import json
from pathlib import Path

import numpy as np
import pandas as pd

try:
    import torch
    import torch.nn as nn
except ModuleNotFoundError as exc:  # pragma: no cover
    raise SystemExit(
        "This script requires PyTorch on the target machine. "
        "Install torch there and rerun."
    ) from exc


ROOT = Path(__file__).resolve().parents[2]
TENSOR_PATH = ROOT / "data" / "processed" / "stgnn_tensor_package_extended_forecast_core_v1.npz"
NODE_INDEX_PATH = ROOT / "data" / "processed" / "graph_node_index_core_v0.csv"
REI_PATH = ROOT / "data" / "interim" / "tables" / "rei_cfe_ze2020_v0.csv"
METRICS_OUT = ROOT / "reports" / "minimal_gcn_with_rei_metrics_v0.json"
REPORT_OUT = ROOT / "reports" / "MINIMAL_GCN_WITH_REI_V0.md"
PRED_OUT = ROOT / "data" / "processed" / "minimal_gcn_with_rei_predictions_v0.csv"

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


def row_standardize(train_mat, test_mat):
    train_scaled = np.zeros_like(train_mat, dtype=float)
    test_scaled = np.zeros_like(test_mat, dtype=float)
    keep = []
    for i in range(train_mat.shape[2]):
        tr = train_mat[:, :, i]
        te = test_mat[:, :, i]
        obs = tr[np.isfinite(tr)]
        if len(obs) == 0:
            keep.append(False)
            continue
        mean = obs.mean()
        std = obs.std()
        if std == 0:
            std = 1.0
        train_scaled[:, :, i] = np.where(np.isfinite(tr), (tr - mean) / std, 0.0)
        test_scaled[:, :, i] = np.where(np.isfinite(te), (te - mean) / std, 0.0)
        keep.append(True)
    keep = np.array(keep, dtype=bool)
    return train_scaled[:, :, keep], test_scaled[:, :, keep], keep


def load_frame():
    package = np.load(TENSOR_PATH, allow_pickle=True)
    feature_names = [str(x) for x in package["feature_name"]]
    idx_side = feature_names.index("side_creations_lag_1")
    idx_nb = feature_names.index("nb_com")

    node_index = pd.read_csv(NODE_INDEX_PATH, usecols=["node_idx", "ze2020", "libze2020"])
    rei = pd.read_csv(REI_PATH).rename(columns={"ZE2020": "ze2020"}).sort_values(["ze2020", "year"])
    rei["rei_cfe_microentrepreneurs_created_n_1_lag_1"] = rei.groupby("ze2020")["rei_cfe_microentrepreneurs_created_n_1"].shift(1)
    rei = rei[["ze2020", "year", "rei_cfe_microentrepreneurs_created_n_1_lag_1"]]

    frames = []
    for pos, year in enumerate(package["years"].astype(int)):
        frames.append(
            pd.DataFrame(
                {
                    "node_idx": package["node_idx"].astype(int),
                    "target_year": int(year),
                    "y_true": package["y_raw"][pos].astype(float),
                    "side_creations_lag_1": package["x_raw"][pos][:, idx_side].astype(float),
                    "nb_com": package["x_raw"][pos][:, idx_nb].astype(float),
                }
            )
        )
    df = pd.concat(frames, ignore_index=True)
    df = df.merge(node_index, on="node_idx", how="left")
    df = df.merge(rei, left_on=["ze2020", "target_year"], right_on=["ze2020", "year"], how="left").drop(columns=["year"])
    return df, package["adjacency_geo"].astype(np.float32)


class MinimalGCN(nn.Module):
    def __init__(self, in_dim, hidden_dim):
        super().__init__()
        self.lin1 = nn.Linear(in_dim, hidden_dim)
        self.lin2 = nn.Linear(hidden_dim, 1)

    def forward(self, x, adj):
        h = torch.matmul(adj, x)
        h = torch.relu(self.lin1(h))
        h = torch.matmul(adj, h)
        out = self.lin2(h).squeeze(-1)
        return out


def fit_predict(train_x, train_y, test_x, adj):
    set_seed()
    device = torch.device("cpu")
    adj_t = torch.tensor(adj, dtype=torch.float32, device=device)
    x_train = torch.tensor(train_x, dtype=torch.float32, device=device)
    y_train = torch.tensor(train_y, dtype=torch.float32, device=device)
    x_test = torch.tensor(test_x, dtype=torch.float32, device=device)

    model = MinimalGCN(in_dim=train_x.shape[2], hidden_dim=HIDDEN_DIM).to(device)
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
        pred_test = model(x_test, adj_t).cpu().numpy()
    return np.clip(pred_test, a_min=0, a_max=None)


def evaluate(df, adj):
    pred_rows = []
    rows = []

    for target_year in TARGET_YEARS:
        train_df = df[df["target_year"] < target_year].copy()
        test_df = df[df["target_year"] == target_year].copy()

        train_pivot_x = (
            train_df.pivot(index="target_year", columns="node_idx", values=BASE_FEATURES)
            .sort_index(axis=0)
            .sort_index(axis=1)
        )
        test_pivot_x = (
            test_df.pivot(index="target_year", columns="node_idx", values=BASE_FEATURES)
            .sort_index(axis=0)
            .sort_index(axis=1)
        )
        train_pivot_y = (
            train_df.pivot(index="target_year", columns="node_idx", values="y_true")
            .sort_index(axis=0)
            .sort_index(axis=1)
        )
        test_pivot_y = (
            test_df.pivot(index="target_year", columns="node_idx", values="y_true")
            .sort_index(axis=0)
            .sort_index(axis=1)
        )

        train_x = train_pivot_x.to_numpy(dtype=float).reshape(len(train_pivot_x.index), len(train_pivot_y.columns), len(BASE_FEATURES))
        test_x = test_pivot_x.to_numpy(dtype=float).reshape(len(test_pivot_x.index), len(test_pivot_y.columns), len(BASE_FEATURES))
        train_y = train_pivot_y.to_numpy(dtype=float)
        test_y = test_pivot_y.to_numpy(dtype=float)

        train_x, test_x, keep = row_standardize(train_x, test_x)
        kept_features = [f for f, ok in zip(BASE_FEATURES, keep) if ok]
        pred = fit_predict(train_x, train_y, test_x, adj)[0]
        y_true = test_y[0]

        out = test_df[["target_year", "node_idx", "ze2020", "libze2020", "y_true"]].copy()
        out["features_used"] = ",".join(kept_features)
        out["prediction"] = pred[out["node_idx"].to_numpy(dtype=int)]
        pred_rows.append(out)
        rows.append(
            {
                "target_year": int(target_year),
                "features": kept_features,
                "wmape": wmape(y_true, pred),
            }
        )

    pred_df = pd.concat(pred_rows, ignore_index=True)
    return pred_df, rows


def summarize(rows):
    return {
        "mean_wmape": float(np.mean([r["wmape"] for r in rows])),
        "max_wmape": float(np.max([r["wmape"] for r in rows])),
        "per_year_wmape": {str(r["target_year"]): float(r["wmape"]) for r in rows},
    }


def compare(candidate, baseline):
    deltas = {}
    worsened = []
    for year, base_val in baseline["per_year_wmape"].items():
        cand_val = candidate["per_year_wmape"][year]
        delta = cand_val - base_val
        deltas[year] = float(delta)
        if delta > 1e-6:
            worsened.append(int(year))
    return {
        "mean_delta": float(candidate["mean_wmape"] - baseline["mean_wmape"]),
        "per_year_delta": deltas,
        "worsened_years": worsened,
        "strictly_better_with_tolerance": bool(candidate["mean_wmape"] < baseline["mean_wmape"] and len(worsened) == 0),
    }


def main():
    df, adj = load_frame()
    pred_df, gcn_rows = evaluate(df, adj)
    pred_df.to_csv(PRED_OUT, index=False)

    baseline = json.loads((ROOT / "reports" / "rei_created_baseline_metrics_v0.json").read_text())["rei_created_baseline"]["summary"]
    candidate = summarize(gcn_rows)
    payload = {
        "model": "minimal_gcn_with_rei_geo",
        "feature_set": BASE_FEATURES,
        "hyperparameters": {
            "hidden_dim": HIDDEN_DIM,
            "epochs": EPOCHS,
            "lr": LR,
            "weight_decay": WEIGHT_DECAY,
            "seed": SEED,
        },
        "summary": candidate,
        "rows": gcn_rows,
        "comparison_vs_rei_created_baseline": compare(candidate, baseline),
        "prediction_output": str(PRED_OUT.relative_to(ROOT)),
    }
    METRICS_OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    cmp = payload["comparison_vs_rei_created_baseline"]
    lines = [
        "# Minimal GCN With REI v0",
        "",
        "First heavy structural candidate prepared for an external machine with PyTorch.",
        "",
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
