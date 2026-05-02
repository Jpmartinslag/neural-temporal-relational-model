"""
Train forecast-safe temporal baselines for the HERALD final comparison.

Models:
  - naive_lag1: previous annual value per ZE2020.
  - arima_local: one univariate ARIMA per ZE2020, fitted only on past annual values.
  - lstm_local: global local-history LSTM, using only each zone's own lag sequence.

Outputs are isolated under:
  hpc_results/final_model_comparison_20260429/temporal_baselines/
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"
METADATA = ROOT / "metadata"
DEFAULT_OUT = ROOT / "hpc_results/final_model_comparison_20260429/temporal_baselines"

PANEL_PATH = PROCESSED / "dynamic_stgnn_feature_panel_v1.csv"
SPLITS_PATH = METADATA / "dynamic_stgnn_walk_forward_splits_v1.csv"
TARGET_COL = "side_establishment_creations_official"
LAG_COLS = ["side_lag_3", "side_lag_2", "side_lag_1"]


def wmape(y_true, y_pred):
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    denom = np.abs(y_true).sum()
    return float(np.abs(y_true - y_pred).sum() / denom) if denom > 0 else np.nan


def set_seed(seed: int):
    np.random.seed(seed)
    try:
        import torch

        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
    except ModuleNotFoundError:
        pass


def predict_naive_lag1(test: pd.DataFrame) -> np.ndarray:
    pred = test["side_lag_1"].to_numpy(float)
    fallback = np.nanmedian(pred)
    if not np.isfinite(fallback):
        fallback = 0.0
    return np.maximum(np.nan_to_num(pred, nan=fallback), 0.0)


def predict_ridge_ar(train: pd.DataFrame, test: pd.DataFrame) -> np.ndarray:
    cols = [c for c in ["side_lag_1", "side_lag_2", "side_lag_3", "growth_1y", "growth_2y"] if c in train.columns]
    tr = train.dropna(subset=[TARGET_COL]).copy()
    te = test.dropna(subset=[TARGET_COL]).copy()
    model = Pipeline(
        [
            ("imp", SimpleImputer(strategy="median")),
            ("sc", StandardScaler()),
            ("ridge", Ridge(alpha=1.0)),
        ]
    )
    model.fit(tr[cols].values.astype(float), tr[TARGET_COL].values.astype(float))
    return np.maximum(model.predict(te[cols].values.astype(float)), 0.0)


def predict_arima_local(train: pd.DataFrame, test: pd.DataFrame, orders):
    try:
        from statsmodels.tsa.arima.model import ARIMA
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "statsmodels is required for --models arima_local. "
            "Install statsmodels in the HPC environment or run without arima_local."
        ) from exc

    preds = []
    train_by_zone = {
        int(ze): group.sort_values("target_year")[TARGET_COL].dropna().to_numpy(float)
        for ze, group in train.groupby("ZE2020")
    }
    for row in test.itertuples(index=False):
        ze = int(row.ZE2020)
        series = train_by_zone.get(ze, np.asarray([], dtype=float))
        fallback = getattr(row, "side_lag_1", np.nan)
        if len(series) < 5:
            preds.append(fallback)
            continue
        pred = np.nan
        for order in orders:
            try:
                fit = ARIMA(
                    series,
                    order=order,
                    enforce_stationarity=False,
                    enforce_invertibility=False,
                ).fit()
                pred = float(fit.forecast(steps=1)[0])
                break
            except Exception:
                continue
        preds.append(fallback if not np.isfinite(pred) else pred)
    out = np.asarray(preds, dtype=float)
    fallback = np.nanmedian(out)
    if not np.isfinite(fallback):
        fallback = 0.0
    return np.maximum(np.nan_to_num(out, nan=fallback), 0.0)


def predict_lstm_local(train: pd.DataFrame, test: pd.DataFrame, args):
    try:
        import torch
        import torch.nn as nn
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "PyTorch is required for --models lstm_local. "
            "Use the same torch environment used for HERALD."
        ) from exc

    train_fit = train.dropna(subset=[TARGET_COL] + LAG_COLS).copy()
    test_fit = test.dropna(subset=[TARGET_COL] + LAG_COLS).copy()
    if train_fit.empty or test_fit.empty:
        return np.asarray([], dtype=float), test_fit

    x_scaler = StandardScaler()
    y_scaler = StandardScaler()
    x_train = x_scaler.fit_transform(train_fit[LAG_COLS].to_numpy(float)).reshape(-1, len(LAG_COLS), 1)
    y_train = y_scaler.fit_transform(train_fit[[TARGET_COL]].to_numpy(float)).ravel()
    x_test = x_scaler.transform(test_fit[LAG_COLS].to_numpy(float)).reshape(-1, len(LAG_COLS), 1)

    class LocalLSTM(nn.Module):
        def __init__(self, hidden_dim: int):
            super().__init__()
            self.lstm = nn.LSTM(input_size=1, hidden_size=hidden_dim, batch_first=True)
            self.out = nn.Linear(hidden_dim, 1)

        def forward(self, x):
            h, _ = self.lstm(x)
            return self.out(h[:, -1]).squeeze(-1)

    device_name = "cuda" if args.device == "auto" and torch.cuda.is_available() else args.device
    if device_name == "cuda" and not torch.cuda.is_available():
        device_name = "cpu"
    device = torch.device(device_name)
    model = LocalLSTM(args.hidden_dim).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    loss_fn = nn.HuberLoss(delta=args.huber_delta)
    x_t = torch.tensor(x_train, dtype=torch.float32, device=device)
    y_t = torch.tensor(y_train, dtype=torch.float32, device=device)

    model.train()
    for _ in range(args.epochs):
        opt.zero_grad()
        loss = loss_fn(model(x_t), y_t)
        loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), args.grad_clip)
        opt.step()

    model.eval()
    with torch.no_grad():
        pred_scaled = model(torch.tensor(x_test, dtype=torch.float32, device=device)).cpu().numpy()
    pred = y_scaler.inverse_transform(pred_scaled.reshape(-1, 1)).ravel()
    return np.maximum(pred, 0.0), test_fit


def evaluate(panel: pd.DataFrame, splits: pd.DataFrame, model_name: str, args) -> pd.DataFrame:
    rows = []
    arima_orders = [tuple(map(int, item.split(","))) for item in args.arima_orders]
    for split in splits.itertuples(index=False):
        target_year = int(split.target_year)
        train = panel[panel["target_year"] <= int(split.train_years_max)].copy()
        test = panel[panel["target_year"] == target_year].dropna(subset=[TARGET_COL]).copy()
        if model_name == "naive_lag1":
            pred = predict_naive_lag1(test)
            eval_test = test
        elif model_name == "ridge_ar":
            pred = predict_ridge_ar(train, test)
            eval_test = test
        elif model_name == "arima_local":
            pred = predict_arima_local(train, test, arima_orders)
            eval_test = test
        elif model_name == "lstm_local":
            pred, eval_test = predict_lstm_local(train, test, args)
        else:
            raise ValueError(f"Unknown model: {model_name}")

        for row, yp in zip(eval_test.itertuples(index=False), pred):
            rows.append(
                {
                    "model": model_name,
                    "seed": int(args.seed),
                    "target_year": target_year,
                    "ZE2020": int(row.ZE2020),
                    "y_true": float(getattr(row, TARGET_COL)),
                    "y_pred": float(yp),
                    "abs_error": float(abs(getattr(row, TARGET_COL) - yp)),
                }
            )
    return pd.DataFrame(rows)


def write_outputs(pred: pd.DataFrame, args):
    out_dir = args.out_dir
    data_dir = out_dir / "data_processed"
    reports_dir = out_dir / "reports"
    data_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    model_tag = "_".join(args.models)
    suffix = f"{model_tag}_seed_{args.seed}"
    pred_path = data_dir / f"temporal_baselines_predictions_{suffix}_v1.csv"
    pred.to_csv(pred_path, index=False)

    metrics = []
    for (model, seed, year), group in pred.groupby(["model", "seed", "target_year"]):
        metrics.append(
            {
                "model": model,
                "seed": int(seed),
                "target_year": int(year),
                "wmape": wmape(group["y_true"], group["y_pred"]),
                "n": int(len(group)),
            }
        )
    metrics_df = pd.DataFrame(metrics)
    summary = (
        metrics_df.groupby(["model", "seed"], as_index=False)["wmape"]
        .mean()
        .rename(columns={"wmape": "mean_wmape"})
    )

    json_path = reports_dir / f"temporal_baselines_metrics_{suffix}_v1.json"
    json_path.write_text(
        json.dumps(
            {
                "metrics_by_model_year": metrics_df.to_dict(orient="records"),
                "summary_mean_wmape": summary.to_dict(orient="records"),
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    combined = []
    metric_paths = list(reports_dir.glob("temporal_baselines_metrics_seed_*_v1.json"))
    metric_paths += list(reports_dir.glob("temporal_baselines_metrics_*_seed_*_v1.json"))
    for path in sorted(set(metric_paths)):
        data = json.loads(path.read_text(encoding="utf-8"))
        combined.extend(data.get("metrics_by_model_year", []))
    combined_df = pd.DataFrame(combined)
    if not combined_df.empty:
        combined_summary = (
            combined_df.groupby(["model", "seed"], as_index=False)["wmape"]
            .mean()
            .rename(columns={"wmape": "mean_wmape"})
        )
        combined_path = reports_dir / "final_temporal_baselines_metrics_v1.json"
        combined_path.write_text(
            json.dumps(
                {
                    "metrics_by_model_year": combined_df.to_dict(orient="records"),
                    "summary_mean_wmape": combined_summary.to_dict(orient="records"),
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    print(f"Saved: {pred_path}")
    print(f"Saved: {json_path}")
    if not summary.empty:
        print(summary.sort_values('mean_wmape').to_string(index=False))


def main():
    parser = argparse.ArgumentParser(description="HERALD temporal baselines")
    parser.add_argument("--models", nargs="+", default=["naive_lag1", "ridge_ar", "arima_local", "lstm_local"],
                        choices=["naive_lag1", "ridge_ar", "arima_local", "lstm_local"])
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--epochs", type=int, default=500)
    parser.add_argument("--hidden-dim", type=int, default=32)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--huber-delta", type=float, default=1.0)
    parser.add_argument("--grad-clip", type=float, default=5.0)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--arima-orders", nargs="+", default=["1,1,0", "1,0,0", "0,1,1", "0,1,0"])
    parser.add_argument("--panel-path", type=Path, default=PANEL_PATH)
    parser.add_argument("--splits-path", type=Path, default=SPLITS_PATH)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    set_seed(args.seed)
    panel = pd.read_csv(args.panel_path).sort_values(["target_year", "ZE2020"]).reset_index(drop=True)
    splits = pd.read_csv(args.splits_path)

    frames = []
    for model_name in args.models:
        print(f"Training/evaluating {model_name} seed={args.seed}")
        frames.append(evaluate(panel, splits, model_name, args))
    pred = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    write_outputs(pred, args)


if __name__ == "__main__":
    main()
