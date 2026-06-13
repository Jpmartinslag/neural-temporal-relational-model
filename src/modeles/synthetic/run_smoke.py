"""
run_smoke.py

Smoke test for HERALD synthetic benchmark (DEC-039).

Config: 10 territories × 5 sectors × 12 years, 2 seeds, MCAR 20% only.
Runs 6 baselines: B1 (mean), B3 (ffill), B5 (Ridge), B6 (neural-no-graph),
                  B7 (HERALD-graph), B8 (HERALD-permuted).

Expected runtime: < 3 minutes CPU.
PASS: all baselines produce valid (non-NaN) output; leakage test passes.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from src.data.synthetic.generate_herald_synthetic import SyntheticConfig, generate_dataset, mask_panel
from src.modeles.synthetic.imputation_baselines import (
    MeanImputer,
    ForwardFillImputer,
    RidgeImputer,
    GraphRidgeImputer,
)
from src.modeles.synthetic.herald_graph_imputer import (
    HERALDGraphImputer,
    build_permuted_adj,
    train_herald_imputer,
    impute_deterministic,
    impute_with_uncertainty,
)
from src.modeles.synthetic.evaluate_imputation import (
    compute_imputation_metrics,
    compute_edge_recovery_metrics,
    compute_calibration_metrics,
    check_no_leakage,
)

SMOKE_CONFIG = SyntheticConfig(
    n_territories=10,
    n_sectors=5,
    n_years=12,
    n_true_relations=4,
    seed=42,
)
SMOKE_SEEDS = [42, 123]
SMOKE_MASK_KEY = "mcar_20"
SMOKE_EPOCHS = 100
OUTPUT_PATH = REPO_ROOT / "data/processed/synthetic_benchmark/smoke_results.json"


def run_one_seed(seed: int, verbose: bool = True) -> dict:
    config = SyntheticConfig(**{**SMOKE_CONFIG.__dict__, "seed": seed})
    ds = generate_dataset(config)

    panel = ds["panel"]
    mask = ds["masks"][SMOKE_MASK_KEY]
    true_rels = ds["true_relations"]
    adj_s = ds["sector_adj"]
    adj_t = ds["territory_adj"]

    obs_panel = mask_panel(panel, mask)
    n_hidden = int((mask == 0).sum())

    if verbose:
        print(f"\n  seed={seed}: panel {panel.shape}, hidden={n_hidden}")
        print(f"  true_relations={len(true_rels)}: {[(r.source_sector, r.target_sector, r.lag) for r in true_rels]}")

    results = {"seed": seed, "n_hidden": n_hidden, "baselines": {}}

    # ── Leakage check ──────────────────────────────────────────────────────────
    leakage = check_no_leakage(panel, mask)
    results["leakage_check"] = leakage
    if not leakage["passed"]:
        print("  !! LEAKAGE CHECK FAILED")

    # ── B1: Mean ───────────────────────────────────────────────────────────────
    imp = MeanImputer().fit(obs_panel, mask)
    pred = imp.transform(obs_panel, mask)
    m = compute_imputation_metrics(panel, pred, mask)
    results["baselines"]["mean"] = {
        "mae": m.mae, "rmse": m.rmse, "pearson_r": m.pearson_r, "sign_acc": m.sign_accuracy,
    }
    if verbose:
        print(f"  B1 Mean:     MAE={m.mae:.4f}  RMSE={m.rmse:.4f}")

    # ── B3: ForwardFill ────────────────────────────────────────────────────────
    imp = ForwardFillImputer().fit(obs_panel, mask)
    pred = imp.transform(obs_panel, mask)
    m = compute_imputation_metrics(panel, pred, mask)
    results["baselines"]["ffill"] = {
        "mae": m.mae, "rmse": m.rmse, "pearson_r": m.pearson_r, "sign_acc": m.sign_accuracy,
    }
    if verbose:
        print(f"  B3 ForwardFill: MAE={m.mae:.4f}  RMSE={m.rmse:.4f}")

    # ── B5: Ridge (temporal only) ──────────────────────────────────────────────
    imp = RidgeImputer(alpha=1.0).fit(obs_panel, mask)
    pred = imp.transform(obs_panel, mask)
    m = compute_imputation_metrics(panel, pred, mask)
    results["baselines"]["ridge"] = {
        "mae": m.mae, "rmse": m.rmse, "pearson_r": m.pearson_r, "sign_acc": m.sign_accuracy,
    }
    if verbose:
        print(f"  B5 Ridge:    MAE={m.mae:.4f}  RMSE={m.rmse:.4f}")

    # ── B6: Neural no graph ────────────────────────────────────────────────────
    t0 = time.time()
    identity_s = np.eye(config.n_sectors)
    identity_t = np.eye(config.n_territories)
    model_ng = HERALDGraphImputer(config.n_sectors, config.n_territories, hidden_dim=32)
    train_herald_imputer(model_ng, obs_panel, mask, identity_s, identity_t, n_epochs=SMOKE_EPOCHS)
    pred_ng = impute_deterministic(model_ng, obs_panel, mask, identity_s, identity_t)
    m = compute_imputation_metrics(panel, pred_ng, mask)
    results["baselines"]["neural_no_graph"] = {
        "mae": m.mae, "rmse": m.rmse, "pearson_r": m.pearson_r, "sign_acc": m.sign_accuracy,
        "train_seconds": round(time.time() - t0, 2),
    }
    if verbose:
        print(f"  B6 Neural-noGraph: MAE={m.mae:.4f}  RMSE={m.rmse:.4f}  ({time.time()-t0:.1f}s)")

    # ── B7: HERALD with graph ──────────────────────────────────────────────────
    t0 = time.time()
    model_g = HERALDGraphImputer(config.n_sectors, config.n_territories, hidden_dim=32)
    train_herald_imputer(model_g, obs_panel, mask, adj_s, adj_t, n_epochs=SMOKE_EPOCHS)
    pred_g = impute_deterministic(model_g, obs_panel, mask, adj_s, adj_t)
    pred_mean, pred_std = impute_with_uncertainty(model_g, obs_panel, mask, adj_s, adj_t, n_mc=30)
    m = compute_imputation_metrics(panel, pred_g, mask)
    e = compute_edge_recovery_metrics(true_rels, config.n_sectors, model_g.get_sector_attention())
    cal = compute_calibration_metrics(panel, pred_mean, pred_std, mask)
    results["baselines"]["herald_graph"] = {
        "mae": m.mae, "rmse": m.rmse, "pearson_r": m.pearson_r, "sign_acc": m.sign_accuracy,
        "edge_auc": e.auc, "edge_f1_at_k": e.f1_at_k, "edge_precision": e.precision_at_k,
        "calibration_90": cal.coverage_90,
        "train_seconds": round(time.time() - t0, 2),
    }
    if verbose:
        print(f"  B7 HERALD-Graph: MAE={m.mae:.4f}  RMSE={m.rmse:.4f}  AUC={e.auc:.3f}  Cal90={cal.coverage_90:.2f}  ({time.time()-t0:.1f}s)")

    # ── B8: HERALD permuted graph ──────────────────────────────────────────────
    t0 = time.time()
    perm_rng = np.random.default_rng(seed + 999)
    adj_s_perm, adj_t_perm, _, _ = build_permuted_adj(adj_s, adj_t, perm_rng)
    model_perm = HERALDGraphImputer(config.n_sectors, config.n_territories, hidden_dim=32)
    train_herald_imputer(model_perm, obs_panel, mask, adj_s_perm, adj_t_perm, n_epochs=SMOKE_EPOCHS)
    pred_perm = impute_deterministic(model_perm, obs_panel, mask, adj_s_perm, adj_t_perm)
    m = compute_imputation_metrics(panel, pred_perm, mask)
    results["baselines"]["herald_permuted"] = {
        "mae": m.mae, "rmse": m.rmse, "pearson_r": m.pearson_r, "sign_acc": m.sign_accuracy,
        "train_seconds": round(time.time() - t0, 2),
    }
    if verbose:
        print(f"  B8 HERALD-Perm: MAE={m.mae:.4f}  RMSE={m.rmse:.4f}  ({time.time()-t0:.1f}s)")

    return results


def check_no_nans(results: list[dict]) -> bool:
    """Smoke PASS: all MAE values are finite."""
    for r in results:
        for name, vals in r["baselines"].items():
            mae = vals.get("mae", float("nan"))
            if not np.isfinite(mae):
                print(f"  NaN MAE in {name}, seed={r['seed']}")
                return False
    return True


def main() -> None:
    print("=" * 60)
    print("HERALD Synthetic Benchmark — Smoke Test (DEC-039)")
    print(f"Config: {SMOKE_CONFIG.n_territories}T × {SMOKE_CONFIG.n_sectors}S × {SMOKE_CONFIG.n_years}Y")
    print(f"Mask: {SMOKE_MASK_KEY}, Seeds: {SMOKE_SEEDS}")
    print("=" * 60)

    t_start = time.time()
    all_results = []
    for seed in SMOKE_SEEDS:
        seed_result = run_one_seed(seed, verbose=True)
        all_results.append(seed_result)

    elapsed = time.time() - t_start

    # ── Aggregate across seeds ────────────────────────────────────────────────
    baselines = list(all_results[0]["baselines"].keys())
    agg = {}
    for bl in baselines:
        maes = [r["baselines"][bl]["mae"] for r in all_results]
        rmses = [r["baselines"][bl]["rmse"] for r in all_results]
        agg[bl] = {
            "mean_mae": float(np.mean(maes)),
            "std_mae": float(np.std(maes)),
            "mean_rmse": float(np.mean(rmses)),
        }

    print("\n── Aggregated results ──────────────────────────────────────")
    best_bl_mae = min(agg, key=lambda k: agg[k]["mean_mae"])
    for bl, vals in agg.items():
        tag = " ← best non-neural" if bl == best_bl_mae and "herald" not in bl else ""
        print(f"  {bl:22s}  MAE={vals['mean_mae']:.4f} ± {vals['std_mae']:.4f}{tag}")

    herald_mae = agg.get("herald_graph", {}).get("mean_mae", float("nan"))
    perm_mae = agg.get("herald_permuted", {}).get("mean_mae", float("nan"))
    ridge_mae = agg.get("ridge", {}).get("mean_mae", float("nan"))

    # ── Gate checks ───────────────────────────────────────────────────────────
    no_nan_pass = check_no_nans(all_results)
    leakage_pass = all(r["leakage_check"]["passed"] for r in all_results)

    print(f"\n── Smoke gate results ──────────────────────────────────────")
    print(f"  No-NaN:         {'PASS' if no_nan_pass else 'FAIL'}")
    print(f"  Leakage check:  {'PASS' if leakage_pass else 'FAIL'}")
    print(f"  Total elapsed:  {elapsed:.1f}s")

    # G1 preview (smoke is too small to be conclusive for G1-G4)
    g1_preview = herald_mae < ridge_mae * 0.95 if np.isfinite(herald_mae) and np.isfinite(ridge_mae) else None
    g3_preview = perm_mae >= herald_mae if np.isfinite(perm_mae) and np.isfinite(herald_mae) else None
    print(f"\n  G1 preview (HERALD < Ridge×0.95): {g1_preview} (not conclusive at smoke scale)")
    print(f"  G3 preview (permuted ≥ HERALD):   {g3_preview} (not conclusive at smoke scale)")
    print(f"  Note: G1–G4 require full HPC run (n_seeds=10, all mask mechanisms)")

    smoke_pass = no_nan_pass and leakage_pass
    print(f"\n  SMOKE {'PASS' if smoke_pass else 'FAIL'}")

    # ── Save ──────────────────────────────────────────────────────────────────
    output = {
        "smoke_config": {
            "n_territories": SMOKE_CONFIG.n_territories,
            "n_sectors": SMOKE_CONFIG.n_sectors,
            "n_years": SMOKE_CONFIG.n_years,
            "mask": SMOKE_MASK_KEY,
            "seeds": SMOKE_SEEDS,
            "epochs": SMOKE_EPOCHS,
        },
        "elapsed_seconds": round(elapsed, 1),
        "smoke_pass": smoke_pass,
        "gates": {
            "no_nan": no_nan_pass,
            "leakage": leakage_pass,
            "g1_preview": g1_preview,
            "g3_preview": g3_preview,
        },
        "aggregated": agg,
        "per_seed": all_results,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\n  Saved → {OUTPUT_PATH}")

    sys.exit(0 if smoke_pass else 1)


if __name__ == "__main__":
    main()
