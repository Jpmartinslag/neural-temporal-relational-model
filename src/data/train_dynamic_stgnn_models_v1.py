"""
Train neural residual models for the Dynamic STGNN phase.

Models:
  - dcrnn_residual: diffusion-GRU style comparator.
  - graph_wavenet_residual: temporal convolution + adaptive graph comparator.
  - dynamic_stgnn_residual: project model with static geo/mobility + adaptive graph.

All neural models predict a residual over the Ridge_AR baseline:
    final_prediction = ridge_ar_prediction + residual_prediction

Outputs:
  data/processed/dynamic_stgnn_model_predictions_v1.csv
  reports/dynamic_stgnn_model_metrics_v1.json
  reports/DYNAMIC_STGNN_MODEL_TRAINING_V1.md

Run inside an environment with PyTorch installed.
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, StandardScaler

try:
    import torch
    import torch.nn as nn
except ModuleNotFoundError as exc:  # pragma: no cover
    raise SystemExit(
        "PyTorch is required. Run this script inside your conda torch environment."
    ) from exc


ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"
REPORTS = ROOT / "reports"
METADATA = ROOT / "metadata"

PANEL_PATH = PROCESSED / "dynamic_stgnn_feature_panel_v1.csv"
SPLITS_PATH = METADATA / "dynamic_stgnn_walk_forward_splits_v1.csv"
GEO_ADJ_PATH = PROCESSED / "graph_adjacency_core_v0.csv"
MOB_ADJ_PATH = PROCESSED / "graph_adjacency_mobility_v0.csv"

OUT_PRED = PROCESSED / "dynamic_stgnn_model_predictions_v1.csv"
OUT_JSON = REPORTS / "dynamic_stgnn_model_metrics_v1.json"
OUT_MD = REPORTS / "DYNAMIC_STGNN_MODEL_TRAINING_V1.md"

TARGET_COL = "side_establishment_creations_official"
TARGET_YEARS = [2021, 2022, 2023, 2024]


def wmape(y_true, y_pred):
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    denom = np.sum(np.abs(y_true))
    if denom == 0:
        return np.nan
    return float(np.sum(np.abs(y_true - y_pred)) / denom)


def set_seed(seed):
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def load_adjacency(path):
    frame = pd.read_csv(path)
    if "source_idx" in frame.columns:
        frame = frame.drop(columns=["source_idx"])
    adj = frame.to_numpy(dtype=np.float32)
    return row_normalize(adj)


def row_normalize(adj):
    adj = np.asarray(adj, dtype=np.float32)
    row_sum = adj.sum(axis=1, keepdims=True)
    return np.divide(adj, row_sum, out=np.zeros_like(adj), where=row_sum > 0)


def feature_columns(panel):
    base = ["side_lag_1", "side_lag_2", "side_lag_3", "growth_1y", "growth_2y"]
    flores = [c for c in panel.columns if c.startswith("flores_") and c.endswith("_t_minus_1")]
    side = [c for c in panel.columns if c.startswith("side_stock_") and c.endswith("_t_minus_1")]
    urssaf = [c for c in panel.columns if c.startswith("urssaf_") and c.endswith("_t_minus_1")]
    flags = [
        "has_flores_source",
        "has_side_stock_source",
        "has_urssaf_source",
        "is_covid_year",
        "is_post_covid_rebound",
    ]
    cols = base + flores + side + urssaf + flags
    return [c for c in cols if c in panel.columns]


def fit_ridge_ar(train, test):
    cols = [c for c in ["side_lag_1", "side_lag_2", "side_lag_3", "growth_1y", "growth_2y"] if c in train.columns]
    train = train.dropna(subset=[TARGET_COL])
    test = test.dropna(subset=[TARGET_COL])

    def log_transform(x):
        return x.astype(float)

    model = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("identity", FunctionTransformer(log_transform)),
            ("scaler", StandardScaler()),
            ("ridge", Ridge(alpha=1.0)),
        ]
    )
    model.fit(train[cols].to_numpy(float), train[TARGET_COL].to_numpy(float))
    pred = np.maximum(model.predict(test[cols].to_numpy(float)), 0.0)
    return pred


def fit_ridge_ar_out_of_year(train, pred_year):
    """Predict one training year using Ridge fitted on the other training years.

    Neural residual training must see out-of-sample Ridge residuals. If the Ridge
    prediction is fitted and evaluated on the same year, the residual scale is not
    comparable with the target-year residual that the neural model sees at test
    time.
    """
    holdout = train[train["target_year"] == pred_year].copy()
    fit = train[train["target_year"] != pred_year].copy()
    if len(fit) < 10 or len(holdout) == 0:
        return holdout, np.full(len(holdout), np.nan, dtype=float)
    return holdout, fit_ridge_ar(fit, holdout)


def make_sequences(panel, cols, train_max, target_year):
    years = sorted(panel["target_year"].unique())
    zones = sorted(panel["ZE2020"].unique())
    zone_to_idx = {z: i for i, z in enumerate(zones)}
    year_to_idx = {y: i for i, y in enumerate(years)}
    t_train_idx = [year_to_idx[y] for y in years if y <= train_max]
    t_full_idx = [year_to_idx[y] for y in years if y <= target_year]
    test_idx = year_to_idx[target_year]

    x = np.zeros((len(years), len(zones), len(cols)), dtype=np.float32)
    y = np.full((len(years), len(zones)), np.nan, dtype=np.float32)
    ridge = np.full((len(years), len(zones)), np.nan, dtype=np.float32)

    train_df = panel[panel["target_year"] <= train_max].copy()
    test_df = panel[panel["target_year"] == target_year].copy()
    ridge_test = fit_ridge_ar(train_df, test_df)

    ridge_map = {}
    for pred_year in sorted(train_df["target_year"].unique()):
        holdout, ridge_holdout = fit_ridge_ar_out_of_year(train_df, int(pred_year))
        for row, pred in zip(holdout.itertuples(index=False), ridge_holdout):
            if np.isfinite(pred):
                ridge_map[(int(row.target_year), int(row.ZE2020))] = float(pred)
    for row, pred in zip(test_df.itertuples(index=False), ridge_test):
        ridge_map[(int(row.target_year), int(row.ZE2020))] = float(pred)

    for row in panel.itertuples(index=False):
        year = int(row.target_year)
        zone = int(row.ZE2020)
        ti = year_to_idx[year]
        zi = zone_to_idx[zone]
        values = [getattr(row, c) for c in cols]
        x[ti, zi, :] = np.asarray(values, dtype=np.float32)
        y[ti, zi] = float(getattr(row, TARGET_COL))
        ridge[ti, zi] = ridge_map.get((year, zone), np.nan)

    train_x_raw = x[t_train_idx]
    full_x_raw = x[t_full_idx]
    scaler = SimpleImputer(strategy="median")
    flat_train = train_x_raw.reshape(-1, train_x_raw.shape[-1])
    scaler.fit(flat_train)
    train_x = scaler.transform(flat_train).reshape(train_x_raw.shape)
    full_x = scaler.transform(full_x_raw.reshape(-1, full_x_raw.shape[-1])).reshape(full_x_raw.shape)
    mean = np.nanmean(train_x, axis=(0, 1), keepdims=True)
    std = np.nanstd(train_x, axis=(0, 1), keepdims=True)
    std = np.where(std == 0, 1.0, std)
    train_x = (train_x - mean) / std
    full_x = (full_x - mean) / std

    train_y = y[t_train_idx]
    train_ridge = ridge[t_train_idx]
    train_resid = train_y - train_ridge
    mask = np.isfinite(train_resid).astype(np.float32)
    train_resid = np.nan_to_num(train_resid, nan=0.0).astype(np.float32)

    test_y = y[test_idx]
    test_ridge = ridge[test_idx]
    test_mask = np.isfinite(test_y) & np.isfinite(test_ridge)

    return {
        "years": years,
        "zones": zones,
        "train_x": train_x.astype(np.float32),
        "full_x": full_x.astype(np.float32),
        "train_resid": train_resid,
        "mask": mask,
        "test_y": test_y,
        "test_ridge": test_ridge,
        "test_mask": test_mask,
        "target_year": target_year,
    }


class DiffusionGRUResidual(nn.Module):
    def __init__(self, in_dim, hidden_dim, diffusion_steps=2):
        super().__init__()
        self.diffusion_steps = diffusion_steps
        self.in_proj = nn.Linear(in_dim * (diffusion_steps + 1) * 2, hidden_dim)
        self.gru = nn.GRU(hidden_dim, hidden_dim)
        self.out = nn.Linear(hidden_dim, 1)

    def diffuse(self, x, adj):
        outs = [x]
        cur = x
        for _ in range(self.diffusion_steps):
            cur = torch.matmul(adj, cur)
            outs.append(cur)
        return outs

    def forward(self, x_seq, adj_geo, adj_mob):
        steps = []
        for x in x_seq:
            terms = self.diffuse(x, adj_geo) + self.diffuse(x, adj_mob)
            steps.append(torch.relu(self.in_proj(torch.cat(terms, dim=-1))))
        seq = torch.stack(steps, dim=0)
        h, _ = self.gru(seq)
        return self.out(h).squeeze(-1)


class GraphWaveNetResidual(nn.Module):
    def __init__(self, num_nodes, in_dim, hidden_dim, embed_dim=8):
        super().__init__()
        self.node_emb_1 = nn.Parameter(torch.randn(num_nodes, embed_dim) * 0.1)
        self.node_emb_2 = nn.Parameter(torch.randn(embed_dim, num_nodes) * 0.1)
        self.input_proj = nn.Linear(in_dim * 2, hidden_dim)
        self.conv1 = nn.Conv1d(hidden_dim, hidden_dim, kernel_size=2, dilation=1, padding=1)
        self.conv2 = nn.Conv1d(hidden_dim, hidden_dim, kernel_size=2, dilation=2, padding=2)
        self.out = nn.Linear(hidden_dim, 1)

    def adaptive_adj(self):
        return torch.softmax(torch.relu(self.node_emb_1 @ self.node_emb_2), dim=1)

    def forward(self, x_seq, adj_geo, adj_mob):
        adj = self.adaptive_adj()
        steps = []
        for x in x_seq:
            ax = torch.matmul(adj, x)
            steps.append(torch.relu(self.input_proj(torch.cat([x, ax], dim=-1))))
        h = torch.stack(steps, dim=0).permute(1, 2, 0)
        # GraphWaveNet comparator intentionally uses only learned adaptive
        # adjacency here. Static geo/mobility priors are reserved for the
        # project DynamicSTGNN model.
        seq_len = len(x_seq)
        h = torch.relu(self.conv1(h))[..., :seq_len]
        h = torch.relu(self.conv2(h))[..., :seq_len]
        h = h.permute(2, 0, 1)
        return self.out(h).squeeze(-1)


class DynamicSTGNNResidual(nn.Module):
    def __init__(self, num_nodes, in_dim, hidden_dim, embed_dim=8):
        super().__init__()
        self.node_emb_1 = nn.Parameter(torch.randn(num_nodes, embed_dim) * 0.1)
        self.node_emb_2 = nn.Parameter(torch.randn(embed_dim, num_nodes) * 0.1)
        self.self_proj = nn.Linear(in_dim, hidden_dim)
        self.geo_proj = nn.Linear(in_dim, hidden_dim)
        self.mob_proj = nn.Linear(in_dim, hidden_dim)
        self.adapt_proj = nn.Linear(in_dim, hidden_dim)
        self.context_gate = nn.Sequential(nn.Linear(in_dim, hidden_dim), nn.ReLU(), nn.Linear(hidden_dim, 4))
        self.gru = nn.GRU(hidden_dim, hidden_dim)
        self.out = nn.Linear(hidden_dim, 1)

    def adaptive_adj(self):
        return torch.softmax(torch.relu(self.node_emb_1 @ self.node_emb_2), dim=1)

    def forward(self, x_seq, adj_geo, adj_mob):
        adj_adapt = self.adaptive_adj()
        steps = []
        for x in x_seq:
            # This gate is year-context dynamic but spatially global: every zone
            # receives the same self/geo/mobility/adaptive mixing weights within
            # a year. That is an intentional V1 simplification, not a per-zone
            # dynamic graph attention mechanism.
            context = x.mean(dim=0, keepdim=True)
            weights = torch.softmax(self.context_gate(context), dim=-1).squeeze(0)
            mixed = (
                weights[0] * self.self_proj(x)
                + weights[1] * self.geo_proj(torch.matmul(adj_geo, x))
                + weights[2] * self.mob_proj(torch.matmul(adj_mob, x))
                + weights[3] * self.adapt_proj(torch.matmul(adj_adapt, x))
            )
            steps.append(torch.relu(mixed))
        seq = torch.stack(steps, dim=0)
        h, _ = self.gru(seq)
        return self.out(h).squeeze(-1)


def make_model(name, num_nodes, in_dim, hidden_dim):
    if name == "dcrnn_residual":
        return DiffusionGRUResidual(in_dim, hidden_dim)
    if name == "graph_wavenet_residual":
        return GraphWaveNetResidual(num_nodes, in_dim, hidden_dim)
    if name == "dynamic_stgnn_residual":
        return DynamicSTGNNResidual(num_nodes, in_dim, hidden_dim)
    raise ValueError(f"Unknown model: {name}")


def train_one(seq, model_name, adj_geo, adj_mob, args, device):
    model = make_model(model_name, len(seq["zones"]), seq["train_x"].shape[-1], args.hidden_dim).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    loss_fn = nn.HuberLoss(delta=args.huber_delta, reduction="none")

    train_x = torch.tensor(seq["train_x"], dtype=torch.float32, device=device)
    full_x = torch.tensor(seq["full_x"], dtype=torch.float32, device=device)
    target = torch.tensor(seq["train_resid"], dtype=torch.float32, device=device)
    mask = torch.tensor(seq["mask"], dtype=torch.float32, device=device)
    adj_geo_t = torch.tensor(adj_geo, dtype=torch.float32, device=device)
    adj_mob_t = torch.tensor(adj_mob, dtype=torch.float32, device=device)

    model.train()
    for _ in range(args.epochs):
        opt.zero_grad()
        pred = model(train_x, adj_geo_t, adj_mob_t)
        loss = (loss_fn(pred, target) * mask).sum() / torch.clamp(mask.sum(), min=1.0)
        loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), args.grad_clip)
        opt.step()

    model.eval()
    with torch.no_grad():
        pred_full = model(full_x, adj_geo_t, adj_mob_t).detach().cpu().numpy()
    return pred_full[-1]


def evaluate_model(panel, splits, cols, adj_geo, adj_mob, model_name, args, device):
    rows = []
    for _, split in splits.iterrows():
        target_year = int(split["target_year"])
        seq = make_sequences(panel, cols, int(split["train_years_max"]), target_year)
        residual = train_one(seq, model_name, adj_geo, adj_mob, args, device)
        mask = seq["test_mask"]
        y_true = seq["test_y"][mask]
        ridge = seq["test_ridge"][mask]
        y_pred = np.maximum(ridge + residual[mask], 0.0)
        zones = np.asarray(seq["zones"])[mask]
        for ze, yt, yp in zip(zones, y_true, y_pred):
            rows.append(
                {
                    "model": model_name,
                    "target_year": target_year,
                    "ZE2020": int(ze),
                    "y_true": float(yt),
                    "y_pred": float(yp),
                    "abs_error": float(abs(yt - yp)),
                }
            )
    return rows


def write_report(pred):
    metrics = []
    for (model, year), group in pred.groupby(["model", "target_year"]):
        metrics.append(
            {
                "model": model,
                "target_year": int(year),
                "wmape": wmape(group["y_true"], group["y_pred"]),
                "n": int(len(group)),
            }
        )
    metrics_df = pd.DataFrame(metrics)
    summary = metrics_df.groupby("model", as_index=False)["wmape"].mean().sort_values("wmape")

    OUT_JSON.write_text(
        json.dumps(
            {
                "metrics_by_model_year": metrics_df.to_dict(orient="records"),
                "summary_mean_wmape": summary.to_dict(orient="records"),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    lines = [
        "# Dynamic STGNN Model Training — V1",
        "",
        "## Methodological Notes",
        "",
        "- All neural models predict residuals over `Ridge_AR`.",
        "- Training residuals use leave-one-year-out Ridge predictions inside the training window.",
        "- Default Huber delta is 500 to match the observed residual scale.",
        "- `graph_wavenet_residual` uses only learned adaptive adjacency by design.",
        "- `dynamic_stgnn_residual` mixes self, geo, mobility, and adaptive graphs with a year-context global gate.",
        "- The V1 gate is dynamic over time but not zone-specific; this is an intentional simplification.",
        "",
        "## Mean WMAPE",
        "",
    ]
    lines += ["| model | mean_wmape |", "|---|---|"]
    for row in summary.itertuples(index=False):
        lines.append(f"| {row.model} | {row.wmape:.6f} |")
    lines += ["", "## Per-Year WMAPE", "", "| model | target_year | wmape | n |", "|---|---:|---:|---:|"]
    for row in metrics_df.sort_values(["model", "target_year"]).itertuples(index=False):
        lines.append(f"| {row.model} | {row.target_year} | {row.wmape:.6f} | {row.n} |")
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--models",
        nargs="+",
        default=["dcrnn_residual", "graph_wavenet_residual", "dynamic_stgnn_residual"],
        choices=["dcrnn_residual", "graph_wavenet_residual", "dynamic_stgnn_residual"],
    )
    parser.add_argument("--epochs", type=int, default=800)
    parser.add_argument("--hidden-dim", type=int, default=32)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--huber-delta", type=float, default=500.0)
    parser.add_argument("--grad-clip", type=float, default=5.0)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    args = parser.parse_args()

    set_seed(args.seed)
    device = torch.device(args.device)
    panel = pd.read_csv(PANEL_PATH).sort_values(["target_year", "ZE2020"]).reset_index(drop=True)
    splits = pd.read_csv(SPLITS_PATH)
    cols = feature_columns(panel)
    adj_geo = load_adjacency(GEO_ADJ_PATH)
    adj_mob = load_adjacency(MOB_ADJ_PATH)

    all_rows = []
    for model_name in args.models:
        all_rows.extend(evaluate_model(panel, splits, cols, adj_geo, adj_mob, model_name, args, device))

    pred = pd.DataFrame(all_rows)
    pred.to_csv(OUT_PRED, index=False)
    write_report(pred)
    print(f"Saved {OUT_PRED}")
    print(f"Saved {OUT_JSON}")
    print(f"Saved {OUT_MD}")


if __name__ == "__main__":
    main()
