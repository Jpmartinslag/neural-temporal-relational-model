"""
run_phase10_benchmark.py — DEC-043 / Phase 10

Phase 10 benchmark runner: contemporaneous (Phase 9) + lagged (Phase 10) architectures.

15 models total:
  Baselines (7): mean, median, ffill, temporal_interp, knn, ridge, graph_ridge
  Neural — contemp (5): neural_no_graph, herald_contemp, herald_contemp_permuted,
                         herald_contemp_random, oracle_contemp
  Neural — lagged (3):  herald_lagged, herald_lagged_permuted, oracle_lagged  [NEW]

Usage:
    # Dry run — show task count
    python run_phase10_benchmark.py --dry-run

    # Local pilot (linear+nonlinear, seeds 42/123/456, mcar/mar/block at 10/30%, 200 epochs)
    python run_phase10_benchmark.py --local-pilot \\
        --output-dir data/processed/synthetic_benchmark/phase10_pilot

    # HPC array task
    python run_phase10_benchmark.py --task-id $SLURM_ARRAY_TASK_ID \\
        --output-dir hpc_results/phase10_synthetic_lagged --n-epochs 500

    # Full local run
    python run_phase10_benchmark.py --confirm-full-run \\
        --output-dir data/processed/synthetic_benchmark/phase10_full
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

import torch

from src.data.synthetic.generate_herald_synthetic import (
    BENCHMARK_SCENARIOS,
    BENCHMARK_SEEDS,
    BENCHMARK_MASK_TYPES,
    BENCHMARK_MASK_LEVELS,
    generate_dataset,
    mask_panel,
)
from src.modeles.synthetic.imputation_baselines import (
    MeanImputer,
    MedianImputer,
    ForwardFillImputer,
    TemporalInterpolationImputer,
    KNNPanelImputer,
    RidgeImputer,
    GraphRidgeImputer,
)
from src.modeles.synthetic.herald_graph_imputer import (
    HERALDGraphImputer,
    build_permuted_adj,
    build_random_adj,
    train_herald_imputer,
    impute_deterministic,
)
from src.modeles.synthetic.herald_graph_imputer_lagged import (
    HERALDGraphImputerLagged,
    build_directed_oracle_lagged,
    train_herald_lagged,
    impute_deterministic_lagged,
)
from src.modeles.synthetic.evaluate_imputation import (
    compute_imputation_metrics,
    compute_edge_recovery_metrics,
    check_no_leakage,
)

# ── Constants ──────────────────────────────────────────────────────────────────

DEFAULT_N_EPOCHS = 500
PILOT_N_EPOCHS = 200
HERALD_HIDDEN_DIM = 64

PILOT_SCENARIO_NAMES = ["linear", "nonlinear_heavy"]
PILOT_SEEDS_P10 = [42, 123, 456]
PILOT_MASK_TYPES = ["mcar", "mar", "block"]
PILOT_MASK_LEVELS = [10, 30]

PHASE10_MANIFEST_VERSION = "phase10_v1"


# ── Manifest ──────────────────────────────────────────────────────────────────

def build_manifest(scenario_names: list[str], seeds: list[int]) -> list[dict]:
    tasks = []
    for scenario in sorted(scenario_names):
        for seed in sorted(seeds):
            tasks.append({
                "task_id": len(tasks),
                "scenario": scenario,
                "seed": seed,
                "output_file": f"{scenario}_seed{seed:05d}.json",
                "manifest_version": PHASE10_MANIFEST_VERSION,
            })
    return tasks


def full_manifest() -> list[dict]:
    return build_manifest(list(BENCHMARK_SCENARIOS.keys()), BENCHMARK_SEEDS)


def pilot_manifest() -> list[dict]:
    return build_manifest(PILOT_SCENARIO_NAMES, PILOT_SEEDS_P10)


# ── I/O ───────────────────────────────────────────────────────────────────────

def write_atomic(data: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2, default=_json_default)
    os.rename(tmp, path)


def _json_default(obj):
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    return str(obj)


def is_valid_result(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        with open(path) as f:
            d = json.load(f)
        return (
            "mask_results" in d
            and "leakage_check" in d
            and d.get("manifest_version") == PHASE10_MANIFEST_VERSION
        )
    except Exception:
        return False


# ── Metric helpers ────────────────────────────────────────────────────────────

def _mdict(m) -> dict:
    return {
        "mae": float(m.mae),
        "rmse": float(m.rmse),
        "pearson_r": float(m.pearson_r),
        "spearman_r": float(m.spearman_r),
        "sign_accuracy": float(m.sign_accuracy),
        "n_evaluated": int(m.n_evaluated),
    }


def _edge_dict(e) -> dict:
    lag_acc = float(e.lag_accuracy) if (e.lag_accuracy is not None and e.lag_accuracy == e.lag_accuracy) else float("nan")
    return {
        "edge_auc": float(e.auc) if (e.auc == e.auc) else float("nan"),
        "edge_f1": float(e.f1_at_k),
        "edge_precision": float(e.precision_at_k),
        "edge_recall": float(e.recall_at_k),
        "edge_fpr": float(e.false_positive_rate),
        "edge_sign_acc": float(e.sign_accuracy) if (e.sign_accuracy == e.sign_accuracy) else float("nan"),
        "edge_lag_acc": lag_acc,
    }


# ── Per-mask runner ───────────────────────────────────────────────────────────

def run_one_mask(
    panel: np.ndarray,           # (n_T, n_S, n_Y) true values
    mask: np.ndarray,            # (n_T, n_S, n_Y) 1=observed 0=missing
    true_rels: list,
    adj_s: np.ndarray,           # (n_S, n_S) sector adjacency
    adj_t: np.ndarray,           # (n_T, n_T) territory adjacency
    n_sectors: int,
    n_territories: int,
    n_epochs: int,
    seed: int,
    mask_key: str,
    verbose: bool = False,
) -> dict:
    """Run all 15 Phase 10 models on one (panel, mask) pair."""
    obs = mask_panel(panel, mask)   # NaN at missing positions
    n_hid = int((mask == 0).sum())
    if verbose:
        pct = 100 * n_hid / mask.size
        print(f"    {mask_key}: hidden={n_hid} ({pct:.1f}%)")

    results: dict[str, dict] = {}
    torch_seed = seed * 10000 + abs(hash(mask_key)) % 10000
    identity_s = np.eye(n_sectors)
    identity_t = np.eye(n_territories)

    # ── Non-neural baselines (7) ──────────────────────────────────────────────
    for bname, imp in [
        ("mean", MeanImputer()),
        ("median", MedianImputer()),
        ("ffill", ForwardFillImputer()),
        ("temporal_interp", TemporalInterpolationImputer()),
        ("knn", KNNPanelImputer(k=5)),
        ("ridge", RidgeImputer(alpha=1.0)),
        ("graph_ridge", GraphRidgeImputer(adj_s, adj_t, alpha=1.0)),
    ]:
        pred = imp.fit_transform(obs, mask)
        m = compute_imputation_metrics(panel, pred, mask)
        results[bname] = _mdict(m)
        if verbose:
            print(f"      {bname:28s}  MAE={m.mae:.4f}")

    # ── Neural — contemporaneous (5) ──────────────────────────────────────────

    # C1: neural_no_graph
    t0 = time.time()
    torch.manual_seed(torch_seed)
    m_ng = HERALDGraphImputer(n_sectors, n_territories, hidden_dim=HERALD_HIDDEN_DIM)
    train_herald_imputer(m_ng, obs, mask, identity_s, identity_t, n_epochs=n_epochs)
    pred = impute_deterministic(m_ng, obs, mask, identity_s, identity_t)
    m = compute_imputation_metrics(panel, pred, mask)
    results["neural_no_graph"] = {**_mdict(m), "train_s": round(time.time() - t0, 1)}
    if verbose:
        print(f"      {'neural_no_graph':28s}  MAE={m.mae:.4f}  ({results['neural_no_graph']['train_s']}s)")

    # C2: herald_contemp
    t0 = time.time()
    torch.manual_seed(torch_seed + 1)
    m_hc = HERALDGraphImputer(n_sectors, n_territories, hidden_dim=HERALD_HIDDEN_DIM)
    train_herald_imputer(m_hc, obs, mask, adj_s, adj_t, n_epochs=n_epochs)
    pred = impute_deterministic(m_hc, obs, mask, adj_s, adj_t)
    m = compute_imputation_metrics(panel, pred, mask)
    e = compute_edge_recovery_metrics(true_rels, n_sectors, m_hc.get_sector_attention())
    results["herald_contemp"] = {**_mdict(m), **_edge_dict(e), "train_s": round(time.time() - t0, 1)}
    if verbose:
        print(f"      {'herald_contemp':28s}  MAE={m.mae:.4f}  AUC={e.auc:.3f}  ({results['herald_contemp']['train_s']}s)")

    # C3: herald_contemp_permuted
    t0 = time.time()
    perm_rng = np.random.default_rng(seed + 77777)
    adj_s_perm, adj_t_perm, perm_s, perm_t = build_permuted_adj(adj_s, adj_t, perm_rng)
    torch.manual_seed(torch_seed + 2)
    m_cp = HERALDGraphImputer(n_sectors, n_territories, hidden_dim=HERALD_HIDDEN_DIM)
    train_herald_imputer(m_cp, obs, mask, adj_s_perm, adj_t_perm, n_epochs=n_epochs)
    pred = impute_deterministic(m_cp, obs, mask, adj_s_perm, adj_t_perm)
    m = compute_imputation_metrics(panel, pred, mask)
    results["herald_contemp_permuted"] = {
        **_mdict(m), "perm_s": perm_s.tolist(), "train_s": round(time.time() - t0, 1)
    }

    # C4: herald_contemp_random
    t0 = time.time()
    rand_rng = np.random.default_rng(seed + 88888)
    adj_s_rand, adj_t_rand = build_random_adj(adj_s, adj_t, rand_rng)
    torch.manual_seed(torch_seed + 3)
    m_cr = HERALDGraphImputer(n_sectors, n_territories, hidden_dim=HERALD_HIDDEN_DIM)
    train_herald_imputer(m_cr, obs, mask, adj_s_rand, adj_t_rand, n_epochs=n_epochs)
    pred = impute_deterministic(m_cr, obs, mask, adj_s_rand, adj_t_rand)
    m = compute_imputation_metrics(panel, pred, mask)
    results["herald_contemp_random"] = {**_mdict(m), "train_s": round(time.time() - t0, 1)}

    # C5: oracle_contemp (symmetric adj frozen, MLP trained)
    t0 = time.time()
    torch.manual_seed(torch_seed + 4)
    m_oc = HERALDGraphImputer(n_sectors, n_territories, hidden_dim=HERALD_HIDDEN_DIM)
    with torch.no_grad():
        oracle_log = torch.log(torch.from_numpy(adj_s.astype(np.float32).clip(min=1e-6)))
        m_oc.log_sect_attn.data = oracle_log
    m_oc.log_sect_attn.requires_grad_(False)
    train_herald_imputer(m_oc, obs, mask, adj_s, adj_t, n_epochs=n_epochs)
    pred = impute_deterministic(m_oc, obs, mask, adj_s, adj_t)
    m = compute_imputation_metrics(panel, pred, mask)
    results["oracle_contemp"] = {
        **_mdict(m), "note": "contemp_oracle_symmetric_frozen", "train_s": round(time.time() - t0, 1)
    }
    if verbose:
        print(f"      {'oracle_contemp':28s}  MAE={m.mae:.4f}  ({results['oracle_contemp']['train_s']}s)")

    # ── Neural — lagged (3, Phase 10 NEW) ────────────────────────────────────

    # L1: herald_lagged
    t0 = time.time()
    torch.manual_seed(torch_seed + 10)
    m_hl = HERALDGraphImputerLagged(n_sectors, n_territories, hidden_dim=HERALD_HIDDEN_DIM)
    train_herald_lagged(m_hl, obs, mask, adj_s, adj_t, n_epochs=n_epochs)
    pred = impute_deterministic_lagged(m_hl, obs, mask, adj_s, adj_t)
    m = compute_imputation_metrics(panel, pred, mask)
    e = compute_edge_recovery_metrics(true_rels, n_sectors, m_hl.get_sector_attention())
    results["herald_lagged"] = {**_mdict(m), **_edge_dict(e), "train_s": round(time.time() - t0, 1)}
    if verbose:
        print(f"      {'herald_lagged':28s}  MAE={m.mae:.4f}  AUC={e.auc:.3f}  ({results['herald_lagged']['train_s']}s)")

    # L2: herald_lagged_permuted
    t0 = time.time()
    perm_rng2 = np.random.default_rng(seed + 99999)
    adj_s_perm2, adj_t_perm2, perm_s2, _ = build_permuted_adj(adj_s, adj_t, perm_rng2)
    torch.manual_seed(torch_seed + 11)
    m_hlp = HERALDGraphImputerLagged(n_sectors, n_territories, hidden_dim=HERALD_HIDDEN_DIM)
    train_herald_lagged(m_hlp, obs, mask, adj_s_perm2, adj_t_perm2, n_epochs=n_epochs)
    pred = impute_deterministic_lagged(m_hlp, obs, mask, adj_s_perm2, adj_t_perm2)
    m = compute_imputation_metrics(panel, pred, mask)
    results["herald_lagged_permuted"] = {
        **_mdict(m), "perm_s": perm_s2.tolist(), "train_s": round(time.time() - t0, 1)
    }

    # L3: oracle_lagged (directed adj frozen per lag, MLP trained)
    t0 = time.time()
    torch.manual_seed(torch_seed + 12)
    m_ol = HERALDGraphImputerLagged(n_sectors, n_territories, hidden_dim=HERALD_HIDDEN_DIM)
    build_directed_oracle_lagged(m_ol, true_rels, n_sectors)
    train_herald_lagged(m_ol, obs, mask, n_epochs=n_epochs)
    pred = impute_deterministic_lagged(m_ol, obs, mask)
    m = compute_imputation_metrics(panel, pred, mask)
    e = compute_edge_recovery_metrics(true_rels, n_sectors, m_ol.get_sector_attention())
    results["oracle_lagged"] = {
        **_mdict(m), **_edge_dict(e),
        "note": "directed_oracle_lag1_lag2_frozen",
        "train_s": round(time.time() - t0, 1),
    }
    if verbose:
        print(f"      {'oracle_lagged':28s}  MAE={m.mae:.4f}  AUC={e.auc:.3f}  ({results['oracle_lagged']['train_s']}s)")

    return results


# ── Task runner ───────────────────────────────────────────────────────────────

def run_task(
    task: dict,
    output_dir: Path,
    n_epochs: int,
    mask_types: list[str],
    mask_levels: list[int],
    verbose: bool = False,
    resume: bool = True,
) -> Path:
    out_path = output_dir / task["output_file"]
    if resume and is_valid_result(out_path):
        print(f"  [skip] {task['output_file']} already complete")
        return out_path

    scenario_name = task["scenario"]
    seed = task["seed"]
    base_cfg = BENCHMARK_SCENARIOS[scenario_name]
    config = dataclasses.replace(base_cfg, seed=seed)
    print(f"\n  [{task['task_id']}] {scenario_name}  seed={seed}  "
          f"({config.n_territories}T × {config.n_sectors}S × {config.n_years}Y)")

    ds = generate_dataset(config)
    panel = ds["panel"]
    adj_s = ds["sector_adj"]
    adj_t = ds["territory_adj"]
    true_rels = ds["true_relations"]
    n_sectors = config.n_sectors
    n_territories = config.n_territories

    lk = check_no_leakage(panel, ds["masks"]["mcar_10"])
    if not lk["passed"]:
        raise RuntimeError(f"LEAKAGE in {scenario_name} seed={seed}: {lk}")

    t_task = time.time()
    mask_results: dict[str, dict] = {}
    for mtype in mask_types:
        for level in mask_levels:
            mkey = f"{mtype}_{level:02d}"
            if mkey not in ds["masks"]:
                continue
            mask = ds["masks"][mkey].astype(np.float32)
            try:
                mask_results[mkey] = run_one_mask(
                    panel, mask, true_rels, adj_s, adj_t,
                    n_sectors, n_territories, n_epochs, seed, mkey, verbose=verbose,
                )
                mask_results[mkey]["mask_type"] = mtype
                mask_results[mkey]["mask_level_pct"] = level
            except Exception as exc:
                import traceback
                print(f"    ERROR in {mkey}: {exc}", file=sys.stderr)
                mask_results[mkey] = {"error": str(exc), "traceback": traceback.format_exc()[-400:]}

    elapsed = round(time.time() - t_task, 1)
    print(f"  task elapsed: {elapsed}s")

    output = {
        "task_id": task["task_id"],
        "scenario": scenario_name,
        "seed": seed,
        "manifest_version": PHASE10_MANIFEST_VERSION,
        "n_epochs": n_epochs,
        "n_true_relations": len(true_rels),
        "n_sectors": n_sectors,
        "n_territories": n_territories,
        "true_relations": [
            {"src": r.source_sector, "tgt": r.target_sector,
             "lag": r.lag, "weight": float(r.weight), "nonlinear": r.nonlinear}
            for r in true_rels
        ],
        "leakage_check": lk,
        "elapsed_seconds": elapsed,
        "mask_results": mask_results,
    }
    write_atomic(output, out_path)
    print(f"  [done] {out_path}")
    return out_path


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--task-id", type=int, default=None)
    ap.add_argument("--local-pilot", action="store_true")
    ap.add_argument("--confirm-full-run", action="store_true")
    ap.add_argument("--smoke", action="store_true", help="1 task, 50 epochs, mcar_10 only")
    ap.add_argument("--output-dir", default="data/processed/synthetic_benchmark/phase10_pilot")
    ap.add_argument("--n-epochs", type=int, default=None)
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--no-resume", action="store_true")
    args = ap.parse_args()

    output_dir = Path(args.output_dir)
    resume = not args.no_resume

    if args.dry_run:
        m = full_manifest()
        print(f"Phase 10 full manifest: {len(m)} tasks")
        print(f"Pilot manifest: {len(pilot_manifest())} tasks")
        for t in m[:4]:
            print(f"  {t['task_id']}: {t['scenario']} seed={t['seed']}")
        if len(m) > 4:
            print(f"  ... ({len(m)-4} more)")
        return

    if args.smoke:
        manifest = pilot_manifest()[:1]
        n_epochs = args.n_epochs or 50
        mask_types = ["mcar"]
        mask_levels = [10]
    elif args.local_pilot:
        manifest = pilot_manifest()
        n_epochs = args.n_epochs or PILOT_N_EPOCHS
        mask_types = PILOT_MASK_TYPES
        mask_levels = PILOT_MASK_LEVELS
    elif args.confirm_full_run:
        manifest = full_manifest()
        n_epochs = args.n_epochs or DEFAULT_N_EPOCHS
        mask_types = BENCHMARK_MASK_TYPES
        mask_levels = BENCHMARK_MASK_LEVELS
    elif args.task_id is not None:
        manifest = full_manifest()
        if args.task_id >= len(manifest):
            print(f"ERROR: task_id {args.task_id} >= {len(manifest)}", file=sys.stderr)
            sys.exit(1)
        manifest = [manifest[args.task_id]]
        n_epochs = args.n_epochs or DEFAULT_N_EPOCHS
        mask_types = BENCHMARK_MASK_TYPES
        mask_levels = BENCHMARK_MASK_LEVELS
    else:
        print("Specify --dry-run, --local-pilot, --smoke, --task-id N, or --confirm-full-run")
        sys.exit(1)

    print(f"Phase 10: {len(manifest)} task(s), {n_epochs} epochs, mask={mask_types}@{mask_levels}% → {output_dir}")

    for task in manifest:
        run_task(task, output_dir, n_epochs, mask_types, mask_levels,
                 verbose=args.verbose, resume=resume)

    print("Done.")


if __name__ == "__main__":
    main()
