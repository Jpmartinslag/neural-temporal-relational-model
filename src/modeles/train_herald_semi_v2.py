"""
HERALD Semi V2 — economic semi-supervised objectives on top of V7.

This script deliberately does not repeat Semi V1's raw zone masking.  It tests
semi-supervised signals that are closer to the economic problem:
  - masked economic variables: denoise annual features, not whole zones;
  - sector denoising: reconstruct A10 proportions from partially hidden sector
    priors;
  - ranking auxiliary loss: preserve territorial growth ordering;
  - temporal regime regularization: stabilize local/graph alpha in normal years.

Outputs use the herald_semi_v2_ prefix.
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
except ModuleNotFoundError as exc:
    raise SystemExit("PyTorch required. Run inside torch environment.") from exc

import train_herald_v6 as base
import train_herald_v7 as v7


ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data/processed"
REPORTS = ROOT / "reports"
OUT_JSON = REPORTS / "herald_semi_v2_metrics_v1.json"
OUT_MD = REPORTS / "HERALD_SEMI_V2_MODEL_V1.md"


def apply_feature_mask(x_ann, mask_ratio):
    if mask_ratio <= 0:
        return x_ann
    keep = (torch.rand_like(x_ann) > mask_ratio).float()
    return x_ann * keep


def apply_sector_prior_mask(sec_prior, mask_ratio):
    if mask_ratio <= 0:
        return sec_prior
    drop = (torch.rand_like(sec_prior) < mask_ratio).float()
    masked = sec_prior * (1.0 - drop)
    fallback = torch.full_like(sec_prior, 1.0 / sec_prior.shape[-1])
    row_sum = masked.sum(dim=-1, keepdim=True)
    return torch.where(row_sum > 1e-8, masked / row_sum.clamp_min(1e-8), fallback)


def ranking_loss(pred, target, mask, ridge_train=None, zone_std=None, max_pairs=4096):
    """Pairwise logistic ranking loss on territorial growth order.

    When ridge_train and zone_std are given, ranks reconstructed totals
    (ridge + resid * std), aligned with the plan's "territorial growth ranking".
    Otherwise falls back to ranking residuals.
    """
    if ridge_train is not None and zone_std is not None:
        zs = zone_std.unsqueeze(0)
        pred_full = ridge_train + pred * zs
        target_full = ridge_train + target * zs
    else:
        pred_full = pred
        target_full = target
    losses = []
    T, N = pred_full.shape
    for t in range(T):
        valid = torch.where(mask[t] > 0)[0]
        if valid.numel() < 2:
            continue
        n_pairs = min(max_pairs, valid.numel() * 2)
        i = valid[torch.randint(valid.numel(), (n_pairs,), device=pred_full.device)]
        j = valid[torch.randint(valid.numel(), (n_pairs,), device=pred_full.device)]
        sign = torch.sign(target_full[t, i] - target_full[t, j])
        keep = sign != 0
        if keep.any():
            margin = (pred_full[t, i] - pred_full[t, j]) * sign
            losses.append(F.softplus(-margin[keep]).mean())
    if not losses:
        return torch.tensor(0.0, device=pred_full.device)
    return torch.stack(losses).mean()


def train_herald_semi_v2(seq, adj_geo, adj_mob, args, device):
    N = len(seq["zones"])
    annual_dim = seq["x_ann_train"].shape[-1]
    model = v7.HERALDv7Residual(
        num_nodes=N,
        annual_dim=annual_dim,
        hidden_dim=args.hidden_dim,
        attn_dim=args.attn_dim,
        q_hidden=args.q_hidden,
        n_sectors_a10=len(base.A10_SECTORS),
        top_k=args.top_k,
        prior_strength_init=args.prior_strength_init,
        gate_bias_init=args.gate_bias_init,
        alpha_bias_init=args.alpha_bias_init,
    ).to(device)

    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    huber = nn.HuberLoss(delta=args.huber_delta, reduction="none")

    x_ann = torch.tensor(seq["x_ann_train"], device=device)
    x_q = torch.tensor(seq["q_train"], device=device)
    regime = torch.tensor(seq["regime_train"], device=device)
    sec_prior = torch.tensor(seq["sec_prior_train"], device=device)
    target = torch.tensor(seq["train_resid"], device=device)
    mask = torch.tensor(seq["mask"], device=device)
    zone_w = torch.tensor(seq["zone_weight"], device=device)
    sec_t = torch.tensor(seq["sec_train"], device=device)
    sec_m = torch.tensor(seq["sec_mask"], device=device)
    ridge_train = torch.tensor(seq["train_ridge"], device=device) if "train_ridge" in seq else None
    zone_std_t = torch.tensor(seq["zone_std"], device=device) if "zone_std" in seq else None

    adj_g = torch.tensor(adj_geo, device=device)
    adj_m_t = torch.tensor(adj_mob, device=device)
    adj_log_g = torch.log(adj_g + 1e-6)
    adj_log_m = torch.log(adj_m_t + 1e-6)

    T = x_ann.shape[0]
    model.train()
    for ep in range(args.epochs):
        opt.zero_grad()

        use_mask = ep >= args.semi_warmup_epochs
        feat_ratio = args.feature_mask_ratio if use_mask and args.mode in {
            "masked_variables", "full"
        } else 0.0
        sector_ratio = args.sector_mask_ratio if use_mask and args.mode in {
            "sector_denoise", "full"
        } else 0.0

        x_ann_aug = apply_feature_mask(x_ann, feat_ratio)
        sec_prior_aug = apply_sector_prior_mask(sec_prior, sector_ratio)

        ann_list = [x_ann_aug[t] for t in range(T)]
        q_list = [x_q[t].permute(1, 0, 2) for t in range(T)]
        reg_list = [regime[t] for t in range(T)]
        sec_prior_list = [sec_prior_aug[t] for t in range(T)]

        pred_main, pred_sector, graph_losses = model(
            ann_list, q_list, reg_list, sec_prior_list,
            adj_g, adj_m_t, adj_log_g, adj_log_m,
            variant=args.v7_variant, return_internals=False,
        )

        zone_w_bc = zone_w.unsqueeze(0).expand_as(pred_main)
        denom = torch.clamp((mask * zone_w_bc).sum(), min=1.0)
        loss_main = (huber(pred_main, target) * mask * zone_w_bc).sum() / denom

        eps = 1e-8
        kl = sec_t * (torch.log(sec_t + eps) - torch.log(pred_sector + eps))
        loss_sec = (kl.sum(-1) * sec_m).sum() / torch.clamp(sec_m.sum(), min=1.0)

        loss_rank = torch.tensor(0.0, device=device)
        if args.mode in {"ranking_aux", "full"}:
            loss_rank = ranking_loss(
                pred_main, target, mask,
                ridge_train=ridge_train, zone_std=zone_std_t,
            )

        regime_shift = torch.mean(torch.abs(regime[1:] - regime[:-1]), dim=-1) if T > 1 else None
        stable_weight = torch.tensor(1.0, device=device)
        if regime_shift is not None and args.mode in {"temporal_regime", "full"}:
            stable_weight = torch.clamp(1.0 - regime_shift.mean(), min=0.0, max=1.0)

        loss_graph = (
            args.smooth_lambda * stable_weight * graph_losses["smooth_term"]
            - args.gate_entropy_lambda * graph_losses["gate_entropy"]
            + args.alpha_smooth_lambda * graph_losses["alpha_smooth"]
        )
        loss = (
            loss_main
            + args.sector_lambda * loss_sec
            + args.rank_lambda * loss_rank
            + loss_graph
        )
        loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), args.grad_clip)
        opt.step()

    model.eval()
    with torch.no_grad():
        x_ann_f = torch.tensor(seq["x_ann_full"], device=device)
        x_q_f = torch.tensor(seq["q_full"], device=device)
        reg_f = torch.tensor(seq["regime_full"], device=device)
        sec_prior_f = torch.tensor(seq["sec_prior_full"], device=device)
        T_full = x_ann_f.shape[0]
        ann_f = [x_ann_f[t] for t in range(T_full)]
        q_f = [x_q_f[t].permute(1, 0, 2) for t in range(T_full)]
        reg_fl = [reg_f[t] for t in range(T_full)]
        sec_prior_fl = [sec_prior_f[t] for t in range(T_full)]

        pred_f, sec_f, graph_f, adj_t, gate_t, alpha_t, regime_delta_t, adj_delta_t = model(
            ann_f, q_f, reg_fl, sec_prior_fl,
            adj_g, adj_m_t, adj_log_g, adj_log_m,
            variant=args.v7_variant, return_internals=True,
        )

    internals = {
        "dynamic_adj": adj_t.cpu().numpy(),
        "gate_values": gate_t.cpu().numpy(),
        "alpha_values": alpha_t.cpu().numpy(),
        "regime_delta_by_year": regime_delta_t.cpu().numpy(),
        "adj_delta_by_year": adj_delta_t.cpu().numpy(),
        "sector_proportions": sec_f[-1].cpu().numpy(),
        "gamma_geo": float(model.gamma_geo.item()),
        "gamma_mob": float(model.gamma_mob.item()),
        "smooth_loss_inference": float(graph_f["smooth_term"].item()),
        "gate_entropy_inference": float(graph_f["gate_entropy"].item()),
        "alpha_smooth_inference": float(graph_f["alpha_smooth"].item()),
        "years": seq["years_full"],
        "node_order": seq["zones"],
    }
    return pred_f[-1].cpu().numpy(), sec_f[-1].cpu().numpy(), internals


def evaluate(panel, a10_panel, splits, cols, q_tensor, sec_props_tensor,
             sec_lag1_tensor, zones_sorted, years_sorted, adj_geo, adj_mob,
             args, device):
    total_rows, sector_rows = [], []
    internals_by_year = {}
    for _, split in splits.iterrows():
        target_year = int(split["target_year"])
        train_max = int(split["train_years_max"])
        print(f"  Fold {target_year}...", flush=True)
        seq = v7.make_sequences_v7(
            panel, cols, q_tensor, sec_props_tensor, sec_lag1_tensor,
            zones_sorted, years_sorted, train_max, target_year,
        )
        residual, sector_props, internals = train_herald_semi_v2(seq, adj_geo, adj_mob, args, device)
        internals["target_year"] = target_year
        internals_by_year[target_year] = internals

        mask_ = seq["test_mask"]
        y_true = seq["test_y"][mask_]
        ridge_p = seq["test_ridge"][mask_]
        zone_std = seq["zone_std"][mask_]
        y_pred = np.maximum(ridge_p + residual[mask_] * zone_std, 0.0)
        s_props = sector_props[mask_]
        zones_arr = np.asarray(zones_sorted)[mask_]
        a10_test = a10_panel[a10_panel["target_year"] == target_year].set_index("ZE2020")

        for i, (ze, yt, yp) in enumerate(zip(zones_arr, y_true, y_pred)):
            total_rows.append({
                "model": "herald_semi_v2",
                "mode": args.mode,
                "target_year": target_year,
                "ZE2020": int(ze),
                "y_true": float(yt),
                "y_pred": float(yp),
                "ridge_pred": float(ridge_p[i]),
                "abs_error": float(abs(yt - yp)),
            })
            for si, s in enumerate(base.A10_SECTORS):
                y_true_s = float(a10_test.loc[ze, s]) if ze in a10_test.index else np.nan
                sector_rows.append({
                    "model": "herald_semi_v2",
                    "mode": args.mode,
                    "target_year": target_year,
                    "ZE2020": int(ze),
                    "sector": s,
                    "y_true_sector": y_true_s,
                    "y_pred_sector": float(yp * s_props[i, si]),
                    "y_pred_total": float(yp),
                    "prop_pred": float(s_props[i, si]),
                })
    return total_rows, sector_rows, internals_by_year


def write_report(total_rows, sector_rows, args, internals_by_year):
    total_df = pd.DataFrame(total_rows)
    sector_df = pd.DataFrame(sector_rows)
    per_year = []
    for year, g in total_df.groupby("target_year"):
        per_year.append({"target_year": int(year), "wmape": base.wmape(g["y_true"], g["y_pred"]), "n": len(g)})
    tmdf = pd.DataFrame(per_year)
    mean_wmape = float(tmdf["wmape"].mean())
    wmape_2025 = float(tmdf.loc[tmdf["target_year"] == 2025, "wmape"].iloc[0]) if 2025 in set(tmdf["target_year"]) else np.nan

    sector_wmape = {}
    valid_sector = sector_df.dropna(subset=["y_true_sector"])
    for s in base.A10_SECTORS:
        df_s = valid_sector[valid_sector["sector"] == s]
        if len(df_s) > 0:
            sector_wmape[s] = round(base.wmape(df_s["y_true_sector"], df_s["y_pred_sector"]), 5)
    sector_wmape_mean = round(float(np.mean(list(sector_wmape.values()))), 5) if sector_wmape else np.nan

    last = internals_by_year[max(internals_by_year)]
    years_f = last["years"]
    alpha_arr = last["alpha_values"]
    alpha_by_year = {int(yr): round(float(alpha_arr[t].mean()), 5) for t, yr in enumerate(years_f)}
    tag = f"_{args.run_tag}" if args.run_tag else ""
    run_key = f"{args.mode}{tag}_seed_{args.seed}"
    result = {
        "mode": args.mode,
        "v7_variant": args.v7_variant,
        "seed": args.seed,
        "run_tag": args.run_tag,
        "total_wmape_mean": round(mean_wmape, 6),
        "total_wmape_2025": round(wmape_2025, 6) if np.isfinite(wmape_2025) else None,
        "per_year_total": {int(r.target_year): round(float(r.wmape), 6) for r in tmdf.itertuples(index=False)},
        "sector_wmape": sector_wmape,
        "sector_wmape_mean": sector_wmape_mean,
        "alpha_by_year": alpha_by_year,
        "gamma_geo": round(last["gamma_geo"], 4),
        "gamma_mob": round(last["gamma_mob"], 4),
        "feature_mask_ratio": args.feature_mask_ratio,
        "sector_mask_ratio": args.sector_mask_ratio,
        "rank_lambda": args.rank_lambda,
    }
    existing = {}
    if args.metrics_path.exists():
        existing = json.loads(args.metrics_path.read_text(encoding="utf-8"))
    existing[run_key] = result
    args.metrics_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")

    lines = [
        "# HERALD Semi V2",
        "",
        "| Run | Mean WMAPE | 2025 WMAPE | Sector WMAPE |",
        "|---|---:|---:|---:|",
    ]
    for rk, rv in sorted(existing.items()):
        lines.append(
            f"| {rk} | {rv['total_wmape_mean']:.6f} | {rv.get('total_wmape_2025')} | {rv.get('sector_wmape_mean')} |"
        )
    args.model_card_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"\n=== HERALD Semi V2 ({run_key}) ===")
    print(f"Total WMAPE:       {mean_wmape:.6f}")
    if np.isfinite(wmape_2025):
        print(f"2025 WMAPE:        {wmape_2025:.6f}")
    print(f"Sector WMAPE mean: {sector_wmape_mean:.5f}")
    print(f"alpha 2025:        {alpha_by_year.get(2025, '?')}")


def main():
    parser = argparse.ArgumentParser(description="HERALD Semi V2")
    parser.add_argument("--mode", default="full",
                        choices=["masked_variables", "sector_denoise", "ranking_aux", "temporal_regime", "full"])
    parser.add_argument("--v7-variant", default="full")
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
    parser.add_argument("--gate-entropy-lambda", type=float, default=0.001)
    parser.add_argument("--alpha-smooth-lambda", type=float, default=0.001)
    parser.add_argument("--gate-bias-init", type=float, default=2.0)
    parser.add_argument("--alpha-bias-init", type=float, default=1.5)
    parser.add_argument("--sector-lambda", type=float, default=0.1)
    parser.add_argument("--feature-mask-ratio", type=float, default=0.10)
    parser.add_argument("--sector-mask-ratio", type=float, default=0.30)
    parser.add_argument("--semi-warmup-epochs", type=int, default=100)
    parser.add_argument("--rank-lambda", type=float, default=0.02)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--panel-path", type=Path, default=base.PANEL_PATH)
    parser.add_argument("--splits-path", type=Path, default=base.SPLITS_PATH)
    parser.add_argument("--side-a10-path", type=Path, default=base.SIDE_A10_PATH)
    parser.add_argument("--prediction-output-dir", type=Path, default=PROCESSED)
    parser.add_argument("--metrics-path", type=Path, default=OUT_JSON)
    parser.add_argument("--model-card-path", type=Path, default=OUT_MD)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--run-tag", default="")
    args = parser.parse_args()

    base.set_seed(args.seed)
    device = torch.device(args.device)
    args.prediction_output_dir.mkdir(parents=True, exist_ok=True)
    args.metrics_path.parent.mkdir(parents=True, exist_ok=True)
    args.model_card_path.parent.mkdir(parents=True, exist_ok=True)
    base.SIDE_A10_PATH = args.side_a10_path

    print("Loading data...")
    panel = pd.read_csv(args.panel_path).sort_values(["target_year", "ZE2020"]).reset_index(drop=True)
    splits = pd.read_csv(args.splits_path)
    cols = base.feature_columns(panel, ablation="full")
    adj_geo = base.load_adjacency(base.GEO_ADJ_PATH)
    adj_mob = base.load_adjacency(base.MOB_ADJ_PATH)
    zones_sorted = sorted(panel["ZE2020"].unique())
    years_sorted = sorted(panel["target_year"].unique())

    print("Loading A10 sectoral panel...")
    a10_panel = base.load_or_build_side_a10_panel(zones_sorted)

    print("Building tensors...")
    q_tensor = base.build_quarterly_tensor(zones_sorted, years_sorted)
    sec_props_tensor = base.build_sector_props_target(a10_panel, zones_sorted, years_sorted)
    sec_lag1 = v7.sector_lag1_tensor(sec_props_tensor)
    print(f"  Quarterly:    {q_tensor.shape}")
    print(f"  Sector props: {sec_props_tensor.shape}")
    print(f"  Sector lag1:  {sec_lag1.shape}")
    print(f"  Features:     {len(cols)}")
    print(f"  Mode:         {args.mode}  Device: {device}")

    print(f"\nTraining HERALD Semi V2 (mode={args.mode}, seed={args.seed})...")
    total_rows, sector_rows, internals_by_year = evaluate(
        panel, a10_panel, splits, cols, q_tensor, sec_props_tensor, sec_lag1,
        zones_sorted, years_sorted, adj_geo, adj_mob, args, device,
    )

    tag = f"_{args.run_tag}" if args.run_tag else ""
    suffix = f"{args.mode}{tag}_seed_{args.seed}"
    out_total = args.prediction_output_dir / f"herald_semi_v2_predictions_total_{suffix}_v1.csv"
    out_sector = args.prediction_output_dir / f"herald_semi_v2_predictions_sector_{suffix}_v1.csv"
    out_int = args.prediction_output_dir / f"herald_semi_v2_internals_{suffix}_v1.npz"
    pd.DataFrame(total_rows).to_csv(out_total, index=False)
    pd.DataFrame(sector_rows).to_csv(out_sector, index=False)

    last = internals_by_year[max(internals_by_year)]
    np.savez_compressed(
        out_int,
        dynamic_adj=last["dynamic_adj"],
        gate_values=last["gate_values"],
        alpha_values=last["alpha_values"],
        regime_delta_by_year=last["regime_delta_by_year"],
        adj_delta_by_year=last["adj_delta_by_year"],
        sector_proportions=last["sector_proportions"],
        gamma_geo=np.array([last["gamma_geo"]]),
        gamma_mob=np.array([last["gamma_mob"]]),
        years=np.array(last["years"]),
        node_order=np.array(last["node_order"]),
        sector_names=np.array(base.A10_SECTORS),
    )
    write_report(total_rows, sector_rows, args, internals_by_year)

    print(f"\nSaved: {out_total}")
    print(f"Saved: {out_sector}")
    print(f"Saved: {out_int}")
    print(f"Saved: {args.metrics_path}")
    print(f"Saved: {args.model_card_path}")


if __name__ == "__main__":
    main()
