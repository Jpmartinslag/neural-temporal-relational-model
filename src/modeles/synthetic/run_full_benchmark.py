"""
run_full_benchmark.py

Full-scale runner for HERALD Phase 9 synthetic benchmark (DEC-040).

Execution modes:
    --dry-run                Show manifest only, no computation
    --task-id N              Run one task (for HPC array: SLURM_ARRAY_TASK_ID)
    --local-pilot            Run reduced pilot (3 seeds, 2 scenarios, fewer epochs)
    --confirm-full-run       Run all tasks sequentially (local only, slow)
    --output-dir PATH        Where to write result JSONs
    --n-epochs N             Override epoch count (default: 500 full, 200 pilot)
    --config-json PATH       Load frozen config instead of built-in defaults

Design:
    One task = (scenario_name, seed).
    Each task evaluates ALL models on ALL mask_type × mask_level combos.
    Results written atomically: write to .tmp then rename.
    Resume: skip task if output file already exists and is valid JSON.
    Manifest: deterministic ordering; task_id is stable index into manifest.

Usage:
    # Dry run — show task count and manifest
    python run_full_benchmark.py --dry-run

    # HPC: one job per task
    python run_full_benchmark.py --task-id $SLURM_ARRAY_TASK_ID \\
        --output-dir /path/to/results --n-epochs 500

    # Local pilot
    python run_full_benchmark.py --local-pilot --output-dir data/processed/synthetic_benchmark/pilot

    # Full local run (slow)
    python run_full_benchmark.py --confirm-full-run --output-dir data/processed/synthetic_benchmark/full
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

from src.data.synthetic.generate_herald_synthetic import (
    BENCHMARK_SCENARIOS,
    BENCHMARK_SEEDS,
    BENCHMARK_MASK_LEVELS,
    BENCHMARK_MASK_TYPES,
    PILOT_SCENARIOS,
    PILOT_SEEDS,
    SyntheticConfig,
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
    impute_with_uncertainty,
)
from src.modeles.synthetic.evaluate_imputation import (
    compute_imputation_metrics,
    compute_edge_recovery_metrics,
    compute_calibration_metrics,
    compute_state_metrics,
    compute_breakdown_metrics,
    check_no_leakage,
)
from src.modeles.synthetic.gates import evaluate_gates

# ── Constants ──────────────────────────────────────────────────────────────────
DEFAULT_N_EPOCHS = 500
PILOT_N_EPOCHS = 200
HERALD_HIDDEN_DIM = 64
HERALD_N_MC = 50

PILOT_MASK_LEVELS = [10, 30]
PILOT_MASK_TYPES = ["mcar", "mar", "block"]
PILOT_SCENARIO_NAMES = ["linear", "nonlinear_heavy"]


# ── Manifest ──────────────────────────────────────────────────────────────────

def build_manifest(
    scenario_names: list[str],
    seeds: list[int],
) -> list[dict]:
    """
    Returns deterministic ordered list of task descriptors.
    task_id is the stable index into this list.
    """
    tasks = []
    for scenario in sorted(scenario_names):
        for seed in sorted(seeds):
            fname = f"{scenario}_seed{seed:05d}.json"
            tasks.append({
                "task_id": len(tasks),
                "scenario": scenario,
                "seed": seed,
                "output_file": fname,
            })
    return tasks


def full_manifest() -> list[dict]:
    return build_manifest(list(BENCHMARK_SCENARIOS.keys()), BENCHMARK_SEEDS)


def pilot_manifest() -> list[dict]:
    return build_manifest(PILOT_SCENARIO_NAMES, PILOT_SEEDS)


# ── Atomic write ──────────────────────────────────────────────────────────────

def write_atomic(data: dict, path: Path) -> None:
    """Write JSON to a .tmp file then rename — safe against partial writes."""
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
    """Return True if path exists and contains valid JSON with expected keys."""
    if not path.exists():
        return False
    try:
        with open(path) as f:
            d = json.load(f)
        return "baselines" in d and "leakage_check" in d
    except Exception:
        return False


# ── Model runner ──────────────────────────────────────────────────────────────

def _metrics_dict(m) -> dict:
    return {
        "mae": float(m.mae),
        "rmse": float(m.rmse),
        "pearson_r": float(m.pearson_r),
        "spearman_r": float(m.spearman_r),
        "sign_accuracy": float(m.sign_accuracy),
        "n_evaluated": int(m.n_evaluated),
    }


def run_one_mask(
    panel: np.ndarray,
    mask: np.ndarray,
    true_rels: list,
    adj_s: np.ndarray,
    adj_t: np.ndarray,
    regimes: np.ndarray,
    n_sectors: int,
    n_territories: int,
    n_epochs: int,
    seed: int,
    mask_key: str,
    verbose: bool = False,
) -> dict:
    """Run all models on one (panel, mask) combination. Returns metrics dict."""
    obs = mask_panel(panel, mask)
    n_hid = int((mask == 0).sum())
    if verbose:
        print(f"    {mask_key}: hidden={n_hid} ({100*n_hid/mask.size:.1f}%)")

    results: dict[str, dict] = {}

    # ── Non-neural baselines ──────────────────────────────────────────────────
    for name, imp in [
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
        results[name] = _metrics_dict(m)
        if verbose:
            print(f"      {name:16s}  MAE={m.mae:.4f}")

    # ── Neural baselines ──────────────────────────────────────────────────────
    identity_s = np.eye(n_sectors)
    identity_t = np.eye(n_territories)

    # B6: neural no graph
    t0 = time.time()
    torch_seed = seed * 10000 + abs(hash(mask_key)) % 10000
    import torch
    torch.manual_seed(torch_seed)
    m_ng = HERALDGraphImputer(n_sectors, n_territories, hidden_dim=HERALD_HIDDEN_DIM)
    train_herald_imputer(m_ng, obs, mask, identity_s, identity_t, n_epochs=n_epochs)
    pred_ng = impute_deterministic(m_ng, obs, mask, identity_s, identity_t)
    m = compute_imputation_metrics(panel, pred_ng, mask)
    results["neural_no_graph"] = {**_metrics_dict(m), "train_s": round(time.time() - t0, 1)}
    if verbose:
        print(f"      neural_no_graph      MAE={m.mae:.4f}  ({results['neural_no_graph']['train_s']}s)")

    # B7: HERALD with true graph
    t0 = time.time()
    torch.manual_seed(torch_seed + 1)
    m_g = HERALDGraphImputer(n_sectors, n_territories, hidden_dim=HERALD_HIDDEN_DIM)
    train_herald_imputer(m_g, obs, mask, adj_s, adj_t, n_epochs=n_epochs)
    pred_g = impute_deterministic(m_g, obs, mask, adj_s, adj_t)
    pred_mean, pred_std = impute_with_uncertainty(m_g, obs, mask, adj_s, adj_t, n_mc=HERALD_N_MC)
    m = compute_imputation_metrics(panel, pred_g, mask)
    e = compute_edge_recovery_metrics(true_rels, n_sectors, m_g.get_sector_attention())
    cal = compute_calibration_metrics(panel, pred_mean, pred_std, mask)
    state = compute_state_metrics(panel, pred_g, mask, regimes)
    results["herald_graph"] = {
        **_metrics_dict(m),
        "edge_auc": float(e.auc),
        "edge_f1": float(e.f1_at_k),
        "edge_precision": float(e.precision_at_k),
        "edge_recall": float(e.recall_at_k),
        "edge_fpr": float(e.false_positive_rate),
        "edge_sign_acc": float(e.sign_accuracy),
        "calibration_50": float(cal.coverage_50),
        "calibration_80": float(cal.coverage_80),
        "calibration_90": float(cal.coverage_90),
        "interval_width_90": float(cal.mean_width_90),
        "state_macro_f1": float(state.macro_f1),
        "state_balanced_acc": float(state.balanced_accuracy),
        "train_s": round(time.time() - t0, 1),
    }
    if verbose:
        print(f"      herald_graph         MAE={m.mae:.4f}  AUC={e.auc:.3f}  Cal90={cal.coverage_90:.2f}  ({results['herald_graph']['train_s']}s)")

    # B8: HERALD permuted (node relabeling null)
    t0 = time.time()
    perm_rng = np.random.default_rng(seed + 77777)
    adj_s_perm, adj_t_perm, perm_s, perm_t = build_permuted_adj(adj_s, adj_t, perm_rng)
    torch.manual_seed(torch_seed + 2)
    m_perm = HERALDGraphImputer(n_sectors, n_territories, hidden_dim=HERALD_HIDDEN_DIM)
    train_herald_imputer(m_perm, obs, mask, adj_s_perm, adj_t_perm, n_epochs=n_epochs)
    pred_perm = impute_deterministic(m_perm, obs, mask, adj_s_perm, adj_t_perm)
    m = compute_imputation_metrics(panel, pred_perm, mask)
    results["herald_permuted"] = {
        **_metrics_dict(m),
        "perm_s": perm_s.tolist(),
        "perm_t": perm_t.tolist(),
        "train_s": round(time.time() - t0, 1),
    }
    if verbose:
        print(f"      herald_permuted      MAE={m.mae:.4f}  ({results['herald_permuted']['train_s']}s)")

    # B9: HERALD random graph (density-preserving Erdős-Rényi null)
    t0 = time.time()
    rand_rng = np.random.default_rng(seed + 88888)
    adj_s_rand, adj_t_rand = build_random_adj(adj_s, adj_t, rand_rng)
    torch.manual_seed(torch_seed + 3)
    m_rand = HERALDGraphImputer(n_sectors, n_territories, hidden_dim=HERALD_HIDDEN_DIM)
    train_herald_imputer(m_rand, obs, mask, adj_s_rand, adj_t_rand, n_epochs=n_epochs)
    pred_rand = impute_deterministic(m_rand, obs, mask, adj_s_rand, adj_t_rand)
    m = compute_imputation_metrics(panel, pred_rand, mask)
    results["herald_random_graph"] = {
        **_metrics_dict(m),
        "train_s": round(time.time() - t0, 1),
    }
    if verbose:
        print(f"      herald_random_graph  MAE={m.mae:.4f}  ({results['herald_random_graph']['train_s']}s)")

    # Oracle: HERALD with identity adj + true adj as fixed bias (non-learned upper bound)
    # "Oracle" means: adjacency is initialized from true adj and NOT optimized further.
    # This is an experimental ceiling, NOT a baseline for claim purposes.
    t0 = time.time()
    torch.manual_seed(torch_seed + 4)
    m_oracle = HERALDGraphImputer(n_sectors, n_territories, hidden_dim=HERALD_HIDDEN_DIM)
    # Fix log_sect_attn to log(true_adj + eps) to anchor the oracle
    import torch as _th
    with _th.no_grad():
        oracle_log = _th.log(_th.from_numpy(adj_s.astype(np.float32).clip(min=1e-6)))
        m_oracle.log_sect_attn.data = oracle_log
    # Freeze sector attention, train rest
    for name_p, param in m_oracle.named_parameters():
        if "log_sect_attn" in name_p:
            param.requires_grad = False
    train_herald_imputer(m_oracle, obs, mask, adj_s, adj_t, n_epochs=n_epochs)
    pred_oracle = impute_deterministic(m_oracle, obs, mask, adj_s, adj_t)
    m = compute_imputation_metrics(panel, pred_oracle, mask)
    results["oracle_graph"] = {
        **_metrics_dict(m),
        "note": "experimental_ceiling_only",
        "train_s": round(time.time() - t0, 1),
    }
    if verbose:
        print(f"      oracle_graph         MAE={m.mae:.4f}  ({results['oracle_graph']['train_s']}s)")

    return results


def run_task(
    task: dict,
    output_dir: Path,
    n_epochs: int,
    scenario_registry: dict,
    mask_types: list[str],
    mask_levels: list[int],
    verbose: bool = True,
    resume: bool = True,
) -> Path:
    """Run one (scenario, seed) task — all mask combos, all models."""
    out_path = output_dir / task["output_file"]

    if resume and is_valid_result(out_path):
        if verbose:
            print(f"  [SKIP] {task['scenario']} seed={task['seed']} — already done: {out_path}")
        return out_path

    scenario_name = task["scenario"]
    seed = task["seed"]
    base_cfg = scenario_registry[scenario_name]
    config = dataclasses.replace(base_cfg, seed=seed)

    if verbose:
        print(f"\n  [{task['task_id']}] {scenario_name}  seed={seed}  "
              f"({config.n_territories}T × {config.n_sectors}S × {config.n_years}Y)")

    ds = generate_dataset(config)
    panel = ds["panel"]
    regimes = ds["regimes"]
    adj_s = ds["sector_adj"]
    adj_t = ds["territory_adj"]
    true_rels = ds["true_relations"]

    lk = check_no_leakage(panel, ds["masks"]["mcar_10"])
    if not lk["passed"]:
        raise RuntimeError(f"LEAKAGE DETECTED in {scenario_name} seed={seed}: {lk}")

    mask_results: dict[str, dict] = {}
    t_task = time.time()

    for mtype in mask_types:
        for level in mask_levels:
            mask_key = f"{mtype}_{level:02d}"
            if mask_key not in ds["masks"]:
                continue
            mask = ds["masks"][mask_key]
            try:
                mask_results[mask_key] = run_one_mask(
                    panel, mask, true_rels, adj_s, adj_t, regimes,
                    config.n_sectors, config.n_territories, n_epochs,
                    seed, mask_key, verbose=verbose,
                )
                mask_results[mask_key]["mask_type"] = mtype
                mask_results[mask_key]["mask_level_pct"] = level
            except Exception as exc:
                print(f"    ERROR in {mask_key}: {exc}", file=sys.stderr)
                mask_results[mask_key] = {"error": str(exc)}

    elapsed = round(time.time() - t_task, 1)
    if verbose:
        print(f"  task elapsed: {elapsed}s")

    # Aggregate across mask types for gate evaluation
    per_seed_for_gates = []
    for mk, bl_dict in mask_results.items():
        if "error" in bl_dict:
            continue
        # Extract per-baseline metrics and flatten
        flat = {
            "seed": seed,
            "mask_type": bl_dict.get("mask_type", "unknown"),
            "mask_level_pct": bl_dict.get("mask_level_pct", 0),
            "leakage_check": lk,
            "baselines": {},
        }
        for bl_name in ["mean", "median", "ffill", "temporal_interp", "knn", "ridge",
                        "graph_ridge", "neural_no_graph", "herald_graph", "herald_permuted",
                        "herald_random_graph", "oracle_graph"]:
            if bl_name in bl_dict:
                flat["baselines"][bl_name] = bl_dict[bl_name]
        per_seed_for_gates.append(flat)

    verdict = evaluate_gates(per_seed_for_gates, scenario=scenario_name) if per_seed_for_gates else None

    output = {
        "scenario": scenario_name,
        "seed": seed,
        "config": dataclasses.asdict(config),
        "n_true_relations": len(true_rels),
        "true_relations": [
            {"src": r.source_sector, "tgt": r.target_sector,
             "lag": r.lag, "weight": r.weight, "nonlinear": r.nonlinear}
            for r in true_rels
        ],
        "leakage_check": lk,
        "n_epochs": n_epochs,
        "elapsed_seconds": elapsed,
        "baselines": mask_results,
        "gate_preview": {g.gate: g.passed for g in verdict.gates} if verdict else None,
    }

    write_atomic(output, out_path)
    if verbose:
        print(f"  Saved → {out_path}")
    return out_path


# ── Pilot ─────────────────────────────────────────────────────────────────────

def run_pilot(output_dir: Path, n_epochs: int = PILOT_N_EPOCHS, verbose: bool = True) -> None:
    manifest = pilot_manifest()
    print(f"\n{'='*60}")
    print(f"HERALD Phase 9 — Local Pilot")
    print(f"Tasks: {len(manifest)}  Epochs: {n_epochs}")
    print(f"Scenarios: {PILOT_SCENARIO_NAMES}  Seeds: {PILOT_SEEDS}")
    print(f"Masks: {PILOT_MASK_TYPES} × levels {PILOT_MASK_LEVELS}%")
    print(f"{'='*60}")

    t0 = time.time()
    success, failed = 0, 0
    for task in manifest:
        try:
            run_task(task, output_dir, n_epochs, PILOT_SCENARIOS,
                     PILOT_MASK_TYPES, PILOT_MASK_LEVELS, verbose=verbose)
            success += 1
        except Exception as exc:
            print(f"  TASK FAILED: {task} — {exc}", file=sys.stderr)
            failed += 1

    elapsed = time.time() - t0
    print(f"\n{'='*60}")
    print(f"Pilot complete: {success}/{len(manifest)} tasks OK, {failed} failed")
    print(f"Total elapsed: {elapsed:.1f}s ({elapsed/60:.1f} min)")

    # Aggregate pilot results and print gate preview
    _print_pilot_summary(output_dir, manifest)


def _print_pilot_summary(output_dir: Path, manifest: list[dict]) -> None:
    print("\n── Pilot gate summary ──────────────────────────────────────────")
    all_results = []
    for task in manifest:
        path = output_dir / task["output_file"]
        if not is_valid_result(path):
            continue
        with open(path) as f:
            d = json.load(f)
        for mk, bl_dict in d.get("baselines", {}).items():
            if "error" in bl_dict:
                continue
            all_results.append({
                "seed": d["seed"],
                "mask_type": bl_dict.get("mask_type", "mcar"),
                "leakage_check": d.get("leakage_check", {"passed": True}),
                "baselines": {k: v for k, v in bl_dict.items()
                              if isinstance(v, dict) and "mae" in v},
            })

    if not all_results:
        print("  No valid results found.")
        return

    # Show MAE table across baselines
    baseline_names = ["mean", "ridge", "neural_no_graph", "herald_graph", "herald_permuted",
                      "herald_random_graph", "oracle_graph"]
    print(f"  {'baseline':22s}  mean_MAE  ± std_MAE")
    for bl in baseline_names:
        maes = [r["baselines"].get(bl, {}).get("mae", float("nan")) for r in all_results]
        maes = [v for v in maes if not __import__("math").isnan(v)]
        if maes:
            print(f"  {bl:22s}  {__import__('numpy').mean(maes):.4f}  ± {__import__('numpy').std(maes):.4f}")


# ── Main ──────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="HERALD Phase 9 synthetic benchmark runner")
    p.add_argument("--dry-run", action="store_true", help="Show manifest only")
    p.add_argument("--task-id", type=int, default=None, help="Run single task by id")
    p.add_argument("--local-pilot", action="store_true", help="Run pilot (reduced)")
    p.add_argument("--confirm-full-run", action="store_true", help="Run all tasks sequentially")
    p.add_argument("--output-dir", type=str,
                   default=str(REPO_ROOT / "data/processed/synthetic_benchmark/full"),
                   help="Output directory for result JSONs")
    p.add_argument("--n-epochs", type=int, default=None, help="Override epoch count")
    p.add_argument("--config-json", type=str, default=None, help="Frozen config JSON path")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)

    # ── Dry run ───────────────────────────────────────────────────────────────
    if args.dry_run:
        manifest = full_manifest()
        print(f"\nFull benchmark manifest: {len(manifest)} tasks")
        print(f"Scenarios: {sorted(BENCHMARK_SCENARIOS)}")
        print(f"Seeds: {BENCHMARK_SEEDS}")
        print(f"Mask types: {BENCHMARK_MASK_TYPES}  Levels: {BENCHMARK_MASK_LEVELS}%")
        print(f"Models per task: mean, median, ffill, temporal_interp, knn, ridge, graph_ridge,")
        print(f"                 neural_no_graph, herald_graph, herald_permuted,")
        print(f"                 herald_random_graph, oracle_graph")
        print(f"\nPilot manifest: {len(pilot_manifest())} tasks")
        print(f"\nEstimated runtime (full, 500 epochs, CPU):")
        n_tasks = len(manifest)
        print(f"  ~5-8 min/task × {n_tasks} tasks = {n_tasks*6//60}-{n_tasks*8//60} CPU-hours")
        print(f"  HPC: {n_tasks} array jobs  (1 CPU, ~6 GB RAM each)")
        print(f"\n  SLURM command (after pilot PASS):")
        print(f"  sbatch --array=0-{n_tasks-1} hpc/phase9_synthetic_generalization/run_phase9.slurm")
        return

    # ── Single task ───────────────────────────────────────────────────────────
    if args.task_id is not None:
        manifest = full_manifest()
        if args.task_id >= len(manifest):
            print(f"ERROR: task_id={args.task_id} out of range (manifest has {len(manifest)} tasks)",
                  file=sys.stderr)
            sys.exit(1)
        task = manifest[args.task_id]
        n_epochs = args.n_epochs or DEFAULT_N_EPOCHS
        run_task(task, output_dir, n_epochs, BENCHMARK_SCENARIOS,
                 BENCHMARK_MASK_TYPES, BENCHMARK_MASK_LEVELS, verbose=True)
        return

    # ── Local pilot ───────────────────────────────────────────────────────────
    if args.local_pilot:
        n_epochs = args.n_epochs or PILOT_N_EPOCHS
        run_pilot(output_dir, n_epochs=n_epochs, verbose=True)
        return

    # ── Full run ──────────────────────────────────────────────────────────────
    if args.confirm_full_run:
        manifest = full_manifest()
        n_epochs = args.n_epochs or DEFAULT_N_EPOCHS
        print(f"\nFull run: {len(manifest)} tasks, {n_epochs} epochs each")
        print("WARNING: this may take many hours on a single CPU.")
        t0 = time.time()
        success, failed = 0, 0
        for task in manifest:
            try:
                run_task(task, output_dir, n_epochs, BENCHMARK_SCENARIOS,
                         BENCHMARK_MASK_TYPES, BENCHMARK_MASK_LEVELS, verbose=True)
                success += 1
            except Exception as exc:
                print(f"  TASK FAILED: {task} — {exc}", file=sys.stderr)
                failed += 1
        elapsed = time.time() - t0
        print(f"\nDone: {success}/{len(manifest)} tasks OK, {failed} failed  ({elapsed/3600:.1f}h)")
        return

    print("ERROR: specify --dry-run, --task-id N, --local-pilot, or --confirm-full-run",
          file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
