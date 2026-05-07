"""
Prospective HERALD forecasts for 2026/2027.

This runner is intentionally separate from the walk-forward evaluation scripts:
future years have no observed target and must not be mixed into WMAPE tables.
It reuses the trained HERALD V6/V7/Semi V2 components and writes forecast-only
CSV/JSON artifacts.
"""

import argparse
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

try:
    import torch
except ModuleNotFoundError as exc:
    raise SystemExit("PyTorch required. Run inside torch environment.") from exc

import train_herald_v6 as base
import train_herald_v7 as v7
import train_herald_semi_v2 as semi


ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data/processed"
REPORTS = ROOT / "reports"


MODEL_CHOICES = [
    "v6_full",
    "v7_graph_only",
    "v7_ridge_only",
    "semiv2_graph_ssl",
    "semiv2_graph_nossl",
]


def build_train_args(args):
    common = dict(
        epochs=args.epochs,
        hidden_dim=args.hidden_dim,
        q_hidden=args.q_hidden,
        attn_dim=args.attn_dim,
        top_k=args.top_k,
        prior_strength_init=args.prior_strength_init,
        lr=args.lr,
        weight_decay=args.weight_decay,
        huber_delta=args.huber_delta,
        grad_clip=args.grad_clip,
        smooth_lambda=args.smooth_lambda,
        gate_entropy_lambda=args.gate_entropy_lambda,
        alpha_smooth_lambda=args.alpha_smooth_lambda,
        gate_bias_init=args.gate_bias_init,
        alpha_bias_init=args.alpha_bias_init,
        sector_lambda=args.sector_lambda,
        seed=args.seed,
        run_tag=args.run_tag,
    )
    if args.model == "v6_full":
        return SimpleNamespace(**common, ablation="full", contrast_lambda=args.contrast_lambda)
    if args.model == "v7_graph_only":
        return SimpleNamespace(**common, variant="graph_only")
    if args.model == "v7_ridge_only":
        return SimpleNamespace(**common, variant="ridge_only")
    if args.model == "semiv2_graph_ssl":
        return SimpleNamespace(
            **common,
            mode="full",
            v7_variant="graph_only",
            feature_mask_ratio=args.feature_mask_ratio,
            sector_mask_ratio=args.sector_mask_ratio,
            semi_warmup_epochs=args.semi_warmup_epochs,
            rank_lambda=args.rank_lambda,
        )
    if args.model == "semiv2_graph_nossl":
        return SimpleNamespace(
            **common,
            mode="full",
            v7_variant="graph_only",
            feature_mask_ratio=0.0,
            sector_mask_ratio=0.0,
            semi_warmup_epochs=0,
            rank_lambda=0.0,
        )
    raise ValueError(args.model)


def train_one(seq, adj_geo, adj_mob, args, train_args, device):
    if args.model == "v6_full":
        residual, sector_props, internals = base.train_herald_v6(
            seq, adj_geo, adj_mob, train_args, device
        )
    elif args.model in {"v7_graph_only", "v7_ridge_only"}:
        residual, sector_props, internals = v7.train_herald_v7(
            seq, adj_geo, adj_mob, train_args, device
        )
    else:
        residual, sector_props, internals = semi.train_herald_semi_v2(
            seq, adj_geo, adj_mob, train_args, device
        )
    return residual, sector_props, internals


def make_seq(args, ext_panel, cols, ext_q, ext_sec, sec_lag1, zones, years, last_obs, future_year):
    if args.model == "v6_full":
        return base.make_sequences(
            ext_panel, cols, ext_q, ext_sec,
            zones, years, last_obs, future_year,
        )
    return v7.make_sequences_v7(
        ext_panel, cols, ext_q, ext_sec, sec_lag1,
        zones, years, last_obs, future_year,
    )


def run_forecast(panel, a10_panel, cols, zones, adj_geo, adj_mob, args, device):
    train_args = build_train_args(args)
    last_obs = int(panel["target_year"].max())
    future_years = [last_obs + h for h in range(1, args.forecast_horizon + 1)]
    prev_year_preds = {}
    total_rows = []
    sector_rows = []
    internals_by_year = {}

    for future_year in future_years:
        print(f"Forecasting {future_year} with {args.model} seed={args.seed}", flush=True)
        future_df = base.build_future_panel_rows(panel, zones, [future_year], prev_year_preds)
        ext_panel = pd.concat([panel, future_df], ignore_index=True)
        years = sorted(ext_panel["target_year"].unique())

        ext_q = base.build_quarterly_tensor(zones, years)
        fy_idx = years.index(future_year)
        if ext_q[fy_idx].sum() == 0 and fy_idx > 0:
            ext_q[fy_idx] = ext_q[fy_idx - 1]

        ext_sec = base.build_sector_props_target(a10_panel, zones, years)
        sec_lag1 = v7.sector_lag1_tensor(ext_sec)
        seq = make_seq(args, ext_panel, cols, ext_q, ext_sec, sec_lag1, zones, years, last_obs, future_year)

        residual, sector_props, internals = train_one(seq, adj_geo, adj_mob, args, train_args, device)
        internals["target_year"] = future_year
        internals_by_year[future_year] = internals

        future_sorted = future_df.sort_values("ZE2020").reset_index(drop=True)
        ridge_pred = base.predict_ridge_future(panel, future_sorted)
        y_pred = np.maximum(ridge_pred + residual * seq["zone_std"], 0.0)
        prev_year_preds[future_year] = dict(zip(zones, y_pred.tolist()))

        for i, ze in enumerate(zones):
            total_rows.append({
                "model": args.model,
                "target_year": future_year,
                "ZE2020": int(ze),
                "y_pred": float(y_pred[i]),
                "ridge_pred": float(ridge_pred[i]),
                "residual_norm": float(residual[i]),
                "forecast_type": "prospective",
                "seed": args.seed,
                "panel_key": args.panel_key,
            })
            for si, sector in enumerate(base.A10_SECTORS):
                sector_rows.append({
                    "model": args.model,
                    "target_year": future_year,
                    "ZE2020": int(ze),
                    "sector": sector,
                    "y_pred_total": float(y_pred[i]),
                    "prop_pred": float(sector_props[i, si]),
                    "y_pred_sector": float(y_pred[i] * sector_props[i, si]),
                    "forecast_type": "prospective",
                    "seed": args.seed,
                    "panel_key": args.panel_key,
                })
    return total_rows, sector_rows, internals_by_year


def write_outputs(total_rows, sector_rows, internals_by_year, args):
    tag = f"_{args.run_tag}" if args.run_tag else ""
    suffix = f"{args.panel_key}_{args.model}{tag}_seed_{args.seed}"
    out_total = args.prediction_output_dir / f"herald_forecast_total_{suffix}_v1.csv"
    out_sector = args.prediction_output_dir / f"herald_forecast_sector_{suffix}_v1.csv"
    out_int = args.prediction_output_dir / f"herald_forecast_internals_{suffix}_v1.npz"

    total_df = pd.DataFrame(total_rows)
    sector_df = pd.DataFrame(sector_rows)
    total_df.to_csv(out_total, index=False)
    sector_df.to_csv(out_sector, index=False)

    last = internals_by_year[max(internals_by_year)]
    np.savez_compressed(
        out_int,
        dynamic_adj=last["dynamic_adj"],
        gate_values=last.get("gate_values"),
        alpha_values=last.get("alpha_values"),
        regime_delta_by_year=last["regime_delta_by_year"],
        adj_delta_by_year=last["adj_delta_by_year"],
        sector_proportions=last["sector_proportions"],
        gamma_geo=np.array([last["gamma_geo"]]),
        gamma_mob=np.array([last["gamma_mob"]]),
        years=np.array(last["years"]),
        node_order=np.array(last["node_order"]),
        sector_names=np.array(base.A10_SECTORS),
    )

    aggregates = []
    for year, g in total_df.groupby("target_year"):
        aggregates.append({
            "target_year": int(year),
            "national_pred": float(g["y_pred"].sum()),
            "national_ridge_pred": float(g["ridge_pred"].sum()),
            "n_zones": int(len(g)),
        })

    key = f"{args.panel_key}_{args.model}{tag}_seed_{args.seed}"
    result = {
        "model": args.model,
        "panel_key": args.panel_key,
        "seed": args.seed,
        "run_tag": args.run_tag,
        "forecast_horizon": args.forecast_horizon,
        "forecast_type": "prospective",
        "aggregates": aggregates,
        "feature_mask_ratio": args.feature_mask_ratio if args.model == "semiv2_graph_ssl" else 0.0,
        "sector_mask_ratio": args.sector_mask_ratio if args.model == "semiv2_graph_ssl" else 0.0,
        "rank_lambda": args.rank_lambda if args.model == "semiv2_graph_ssl" else 0.0,
    }
    existing = {}
    if args.metrics_path.exists():
        existing = json.loads(args.metrics_path.read_text(encoding="utf-8"))
    existing[key] = result
    args.metrics_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")

    lines = ["# HERALD prospective forecast", "", "| Run | Years | National prediction |", "|---|---:|---:|"]
    for rk, rv in sorted(existing.items()):
        years = ",".join(str(x["target_year"]) for x in rv["aggregates"])
        pred = "; ".join(f"{x['target_year']}={x['national_pred']:.0f}" for x in rv["aggregates"])
        lines.append(f"| {rk} | {years} | {pred} |")
    args.model_card_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Saved: {out_total}")
    print(f"Saved: {out_sector}")
    print(f"Saved: {out_int}")
    print(f"Saved: {args.metrics_path}")


def main():
    parser = argparse.ArgumentParser(description="HERALD prospective forecast 2026/2027")
    parser.add_argument("--model", required=True, choices=MODEL_CHOICES)
    parser.add_argument("--panel-key", required=True)
    parser.add_argument("--forecast-horizon", type=int, default=2)
    parser.add_argument("--epochs", type=int, default=800)
    parser.add_argument("--hidden-dim", type=int, default=64)
    parser.add_argument("--q-hidden", type=int, default=32)
    parser.add_argument("--attn-dim", type=int, default=16)
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--prior-strength-init", type=float, default=1.0)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--huber-delta", type=float, default=300.0)
    parser.add_argument("--grad-clip", type=float, default=5.0)
    parser.add_argument("--smooth-lambda", type=float, default=0.01)
    parser.add_argument("--contrast-lambda", type=float, default=0.0)
    parser.add_argument("--gate-entropy-lambda", type=float, default=0.001)
    parser.add_argument("--alpha-smooth-lambda", type=float, default=0.001)
    parser.add_argument("--gate-bias-init", type=float, default=2.0)
    parser.add_argument("--alpha-bias-init", type=float, default=0.0)
    parser.add_argument("--sector-lambda", type=float, default=0.1)
    parser.add_argument("--feature-mask-ratio", type=float, default=0.10)
    parser.add_argument("--sector-mask-ratio", type=float, default=0.30)
    parser.add_argument("--semi-warmup-epochs", type=int, default=100)
    parser.add_argument("--rank-lambda", type=float, default=0.02)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--panel-path", type=Path, default=base.PANEL_PATH)
    parser.add_argument("--side-a10-path", type=Path, default=base.SIDE_A10_PATH)
    parser.add_argument("--prediction-output-dir", type=Path, default=PROCESSED)
    parser.add_argument("--metrics-path", type=Path, default=REPORTS / "herald_forecast_metrics_v1.json")
    parser.add_argument("--model-card-path", type=Path, default=REPORTS / "HERALD_FORECAST_MODEL_V1.md")
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--run-tag", default="")
    args = parser.parse_args()

    base.set_seed(args.seed)
    device = torch.device(args.device)
    args.prediction_output_dir.mkdir(parents=True, exist_ok=True)
    args.metrics_path.parent.mkdir(parents=True, exist_ok=True)
    args.model_card_path.parent.mkdir(parents=True, exist_ok=True)
    base.SIDE_A10_PATH = args.side_a10_path

    panel = pd.read_csv(args.panel_path).sort_values(["target_year", "ZE2020"]).reset_index(drop=True)
    cols = base.feature_columns(panel, ablation="full")
    zones = sorted(panel["ZE2020"].unique())
    adj_geo = base.load_adjacency(base.GEO_ADJ_PATH)
    adj_mob = base.load_adjacency(base.MOB_ADJ_PATH)
    a10_panel = base.load_or_build_side_a10_panel(zones)

    print("Prospective forecast setup")
    print(f"  model:    {args.model}")
    print(f"  panel:    {args.panel_key}")
    print(f"  years:    {int(panel['target_year'].max()) + 1}-{int(panel['target_year'].max()) + args.forecast_horizon}")
    print(f"  features: {len(cols)}")
    print(f"  device:   {device}")

    total_rows, sector_rows, internals_by_year = run_forecast(
        panel, a10_panel, cols, zones, adj_geo, adj_mob, args, device
    )
    write_outputs(total_rows, sector_rows, internals_by_year, args)


if __name__ == "__main__":
    main()
