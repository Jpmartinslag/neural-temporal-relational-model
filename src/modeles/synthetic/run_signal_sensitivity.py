from __future__ import annotations

"""
run_signal_sensitivity.py — PHASE10_SIGNAL_SENSITIVITY factorial runner (DEC-044)

STATUS: NOT_AUTHORIZED
  The full 324-task factorial grid is NOT authorized for execution.
  Use run_ofat_sensitivity.py (OFAT design, 48 tasks) instead.

  Launching the full factorial requires the explicit flag:
      --i-understand-this-is-the-324-task-factorial

  Without this flag, any --task-id or full-grid run will be blocked.
  --smoke-test and --local-pilot remain allowed for wiring checks.

Grid (NOT AUTHORIZED):
  cross_sector_force × AR × noise × lag × scenario × seed
  3        × 3  × 2     × 3   × 2        × 3
  = 324 tasks, each running 7 models on 2 masks

Authorized alternative:
  python -m src.modeles.synthetic.run_ofat_sensitivity --run-all

Gates S1-S7 frozen in gates_sensitivity.py BEFORE execution.

Usage:
    # Smoke test (1 task, 50 epochs) — ALLOWED
    python -m src.modeles.synthetic.run_signal_sensitivity --smoke-test

    # Local pilot (original config only, 2 seeds, 100 epochs) — ALLOWED
    python -m src.modeles.synthetic.run_signal_sensitivity --local-pilot \\
        --output-dir data/processed/synthetic_benchmark/sensitivity_pilot

    # Dry run — ALLOWED
    python -m src.modeles.synthetic.run_signal_sensitivity --dry-run

    # Full factorial — BLOCKED unless explicit authorization flag provided
    # python -m src.modeles.synthetic.run_signal_sensitivity \\
    #     --task-id $SLURM_ARRAY_TASK_ID \\
    #     --i-understand-this-is-the-324-task-factorial \\
    #     --output-dir data/processed/synthetic_benchmark/sensitivity_full
"""

_FACTORIAL_NOT_AUTHORIZED_MSG = """
ERROR: Full 324-task factorial grid is NOT AUTHORIZED.

Use the OFAT runner instead:
    python -m src.modeles.synthetic.run_ofat_sensitivity --run-all

If you have explicit authorization to run the full factorial, pass:
    --i-understand-this-is-the-324-task-factorial

This flag must be explicitly provided; it is never set by default.
"""

import argparse
import dataclasses
import itertools
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
    SyntheticConfig,
    BENCHMARK_SCENARIOS,
    generate_dataset,
    mask_panel,
)
from src.modeles.synthetic.imputation_baselines import (
    ForwardFillImputer,
    RidgeImputer,
)
from src.modeles.synthetic.herald_graph_imputer import (
    HERALDGraphImputer,
    build_permuted_adj,
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

# ── Sensitivity grid axes ─────────────────────────────────────────────────────

SENSITIVITY_VERSION = "sensitivity_v1"
SENSITIVITY_HIDDEN_DIM = 64

SENSITIVITY_CS_FORCE = {
    "low":      {"weight_range": (0.1, 0.3)},
    "original": {"weight_range": (0.4, 0.8)},
    "high":     {"weight_range": (0.8, 1.2)},
}

SENSITIVITY_AR = {
    "low":      {"ar_coef_range": (0.1, 0.3)},
    "original": {"ar_coef_range": (0.3, 0.6)},
    "high":     {"ar_coef_range": (0.5, 0.8)},
}

SENSITIVITY_NOISE = {
    "low":      {"noise_sigma_range": (0.05, 0.10)},
    "original": {"noise_sigma_range": (0.08, 0.18)},
}

SENSITIVITY_LAG = {
    "lag1":  {"forced_lag": 1},
    "lag2":  {"forced_lag": 2},
    "mixed": {"forced_lag": None},
}

SENSITIVITY_SCENARIOS = ["linear", "nonlinear_heavy"]
SENSITIVITY_SEEDS = [42, 123, 456]
SENSITIVITY_MASKS = [("mcar", 30), ("block", 30)]

PILOT_SEEDS = [42, 123]
PILOT_CS = ["original"]
PILOT_AR = ["original"]
PILOT_NOISE = ["original"]
PILOT_LAG = ["mixed"]
PILOT_EPOCHS = 100


def _build_config(base_scenario: str, cs: str, ar: str, noise: str, lag: str) -> SyntheticConfig:
    base = BENCHMARK_SCENARIOS[base_scenario]
    overrides = {
        **SENSITIVITY_CS_FORCE[cs],
        **SENSITIVITY_AR[ar],
        **SENSITIVITY_NOISE[noise],
        **SENSITIVITY_LAG[lag],
    }
    return dataclasses.replace(base, seed=0, **overrides)


def build_manifest(
    cs_keys=None, ar_keys=None, noise_keys=None, lag_keys=None,
    scenarios=None, seeds=None,
) -> list[dict]:
    cs_keys = cs_keys or list(SENSITIVITY_CS_FORCE)
    ar_keys = ar_keys or list(SENSITIVITY_AR)
    noise_keys = noise_keys or list(SENSITIVITY_NOISE)
    lag_keys = lag_keys or list(SENSITIVITY_LAG)
    scenarios = scenarios or SENSITIVITY_SCENARIOS
    seeds = seeds or SENSITIVITY_SEEDS

    tasks = []
    for cs, ar, noise, lag, scenario, seed in itertools.product(
        cs_keys, ar_keys, noise_keys, lag_keys, sorted(scenarios), sorted(seeds)
    ):
        tasks.append({
            "task_id": len(tasks),
            "scenario": scenario,
            "seed": seed,
            "cs": cs,
            "ar": ar,
            "noise": noise,
            "lag": lag,
            "manifest_version": SENSITIVITY_VERSION,
            "output_file": f"sensitivity_{scenario}_{cs}_ar{ar}_noise{noise}_{lag}_seed{seed:05d}.json",
        })
    return tasks


def full_manifest() -> list[dict]:
    return build_manifest()


def pilot_manifest() -> list[dict]:
    return build_manifest(
        cs_keys=PILOT_CS, ar_keys=PILOT_AR, noise_keys=PILOT_NOISE,
        lag_keys=PILOT_LAG, seeds=PILOT_SEEDS,
    )


def smoke_manifest() -> list[dict]:
    return build_manifest(
        cs_keys=["original"], ar_keys=["original"], noise_keys=["original"],
        lag_keys=["mixed"], scenarios=["linear"], seeds=[42],
    )


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
        d = json.loads(path.read_text())
        return (
            d.get("manifest_version") == SENSITIVITY_VERSION
            and "mask_results" in d
            and "leakage_check" in d
        )
    except Exception:
        return False


# ── Per-mask runner ───────────────────────────────────────────────────────────

def _mdict(m) -> dict:
    return {
        "mae": float(m.mae),
        "rmse": float(m.rmse),
        "pearson_r": float(m.pearson_r),
        "n_evaluated": int(m.n_evaluated),
    }


def _edict(e) -> dict:
    lag_acc = float(e.lag_accuracy) if (e.lag_accuracy is not None and e.lag_accuracy == e.lag_accuracy) else float("nan")
    return {
        "edge_auc": float(e.auc) if e.auc == e.auc else float("nan"),
        "edge_f1": float(e.f1_at_k),
        "edge_precision": float(e.precision_at_k),
        "edge_recall": float(e.recall_at_k),
        "edge_fpr": float(e.false_positive_rate),
        "edge_sign_acc": float(e.sign_accuracy) if e.sign_accuracy == e.sign_accuracy else float("nan"),
        "edge_lag_acc": lag_acc,
        "n_true_edges": int(e.n_true_edges),
    }


def run_one_mask(
    panel, mask, true_rels, adj_s, adj_t,
    n_sectors, n_territories, n_epochs, seed, mask_key, verbose=False,
) -> dict:
    obs = mask_panel(panel, mask)
    torch_seed = seed * 10000 + abs(hash(mask_key)) % 10000
    identity_s = np.eye(n_sectors)
    identity_t = np.eye(n_territories)
    results: dict[str, dict] = {}

    # 1. ffill
    pred = ForwardFillImputer().fit_transform(obs, mask)
    m = compute_imputation_metrics(panel, pred, mask)
    results["ffill"] = _mdict(m)

    # 2. ridge
    pred = RidgeImputer(alpha=1.0).fit_transform(obs, mask)
    m = compute_imputation_metrics(panel, pred, mask)
    results["ridge"] = _mdict(m)

    # 3. no_graph
    torch.manual_seed(torch_seed)
    m_ng = HERALDGraphImputer(n_sectors, n_territories, hidden_dim=SENSITIVITY_HIDDEN_DIM)
    train_herald_imputer(m_ng, obs, mask, identity_s, identity_t, n_epochs=n_epochs)
    pred = impute_deterministic(m_ng, obs, mask, identity_s, identity_t)
    m = compute_imputation_metrics(panel, pred, mask)
    results["no_graph"] = _mdict(m)

    # 4. herald_contemp
    torch.manual_seed(torch_seed + 1)
    m_hc = HERALDGraphImputer(n_sectors, n_territories, hidden_dim=SENSITIVITY_HIDDEN_DIM)
    train_herald_imputer(m_hc, obs, mask, adj_s, adj_t, n_epochs=n_epochs)
    pred = impute_deterministic(m_hc, obs, mask, adj_s, adj_t)
    m = compute_imputation_metrics(panel, pred, mask)
    e = compute_edge_recovery_metrics(true_rels, n_sectors, m_hc.get_sector_attention())
    results["herald_contemp"] = {**_mdict(m), **_edict(e)}

    # 5. herald_lagged
    torch.manual_seed(torch_seed + 10)
    m_hl = HERALDGraphImputerLagged(n_sectors, n_territories, hidden_dim=SENSITIVITY_HIDDEN_DIM)
    train_herald_lagged(m_hl, obs, mask, adj_s, adj_t, n_epochs=n_epochs)
    pred = impute_deterministic_lagged(m_hl, obs, mask, adj_s, adj_t)
    m = compute_imputation_metrics(panel, pred, mask)
    e = compute_edge_recovery_metrics(true_rels, n_sectors, m_hl.get_sector_attention())
    results["herald_lagged"] = {**_mdict(m), **_edict(e)}
    if verbose:
        print(f"      herald_lagged MAE={m.mae:.4f}  AUC={results['herald_lagged']['edge_auc']:.3f}")

    # 6. herald_lagged_permuted
    torch.manual_seed(torch_seed + 11)
    perm_rng = np.random.default_rng(seed + 99999)
    adj_s_perm, adj_t_perm, _, _ = build_permuted_adj(adj_s, adj_t, perm_rng)
    m_hlp = HERALDGraphImputerLagged(n_sectors, n_territories, hidden_dim=SENSITIVITY_HIDDEN_DIM)
    train_herald_lagged(m_hlp, obs, mask, adj_s_perm, adj_t_perm, n_epochs=n_epochs)
    pred = impute_deterministic_lagged(m_hlp, obs, mask, adj_s_perm, adj_t_perm)
    m = compute_imputation_metrics(panel, pred, mask)
    results["herald_lagged_permuted"] = _mdict(m)

    # 7. oracle_lagged
    torch.manual_seed(torch_seed + 12)
    m_ol = HERALDGraphImputerLagged(n_sectors, n_territories, hidden_dim=SENSITIVITY_HIDDEN_DIM)
    build_directed_oracle_lagged(m_ol, true_rels, n_sectors)
    train_herald_lagged(m_ol, obs, mask, n_epochs=n_epochs)
    pred = impute_deterministic_lagged(m_ol, obs, mask)
    m = compute_imputation_metrics(panel, pred, mask)
    e = compute_edge_recovery_metrics(true_rels, n_sectors, m_ol.get_sector_attention())
    results["oracle_lagged"] = {**_mdict(m), **_edict(e)}

    return results


# ── Task runner ───────────────────────────────────────────────────────────────

def run_task(task: dict, output_dir: Path, n_epochs: int, verbose=False, resume=True) -> Path:
    out_path = output_dir / task["output_file"]
    if resume and is_valid_result(out_path):
        print(f"  [skip] {task['output_file']}")
        return out_path

    cfg = _build_config(task["scenario"], task["cs"], task["ar"], task["noise"], task["lag"])
    cfg = dataclasses.replace(cfg, seed=task["seed"])

    print(f"  [{task['task_id']}] {task['scenario']} cs={task['cs']} ar={task['ar']} "
          f"noise={task['noise']} lag={task['lag']} seed={task['seed']}")

    ds = generate_dataset(cfg)
    panel = ds["panel"]
    adj_s = ds["sector_adj"]
    adj_t = ds["territory_adj"]
    true_rels = ds["true_relations"]
    n_sectors = cfg.n_sectors
    n_territories = cfg.n_territories

    lk = check_no_leakage(panel, ds["masks"]["mcar_10"])
    if not lk["passed"]:
        raise RuntimeError(f"LEAKAGE: {lk}")

    t_task = time.time()
    mask_results: dict[str, dict] = {}
    for mtype, level in SENSITIVITY_MASKS:
        mkey = f"{mtype}_{level:02d}"
        if mkey not in ds["masks"]:
            if verbose:
                print(f"    warning: {mkey} not in masks (skipped)")
            continue
        mask = ds["masks"][mkey].astype(np.float32)
        try:
            mr = run_one_mask(
                panel, mask, true_rels, adj_s, adj_t,
                n_sectors, n_territories, n_epochs, task["seed"], mkey, verbose=verbose,
            )
            mr["mask_type"] = mtype
            mr["mask_level_pct"] = level
            mask_results[mkey] = mr
        except Exception as exc:
            import traceback
            mask_results[mkey] = {"error": str(exc), "traceback": traceback.format_exc()[-400:]}

    elapsed = round(time.time() - t_task, 1)
    output = {
        **{k: task[k] for k in ["task_id", "scenario", "seed", "cs", "ar", "noise", "lag", "manifest_version"]},
        "n_sectors": n_sectors,
        "n_territories": n_territories,
        "n_true_relations": len(ds["true_relations"]),
        "leakage_check": lk,
        "elapsed_seconds": elapsed,
        "mask_results": mask_results,
    }
    write_atomic(output, out_path)
    print(f"  done: {elapsed}s → {out_path.name}")
    return out_path


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="PHASE10_SIGNAL_SENSITIVITY factorial runner [NOT_AUTHORIZED]")
    ap.add_argument("--task-id", type=int, default=None)
    ap.add_argument("--output-dir", type=Path, default=Path("data/processed/synthetic_benchmark/sensitivity_full"))
    ap.add_argument("--n-epochs", type=int, default=200)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--smoke-test", action="store_true")
    ap.add_argument("--local-pilot", action="store_true")
    ap.add_argument("--no-resume", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    # Authorization flag — must be explicitly provided to run the full factorial
    ap.add_argument(
        "--i-understand-this-is-the-324-task-factorial",
        dest="factorial_authorized",
        action="store_true",
        default=False,
    )
    args = ap.parse_args()

    if args.smoke_test:
        tasks = smoke_manifest()
        n_epochs = 50
        out_dir = Path("data/processed/synthetic_benchmark/sensitivity_smoke")
    elif args.local_pilot:
        tasks = pilot_manifest()
        n_epochs = args.n_epochs or PILOT_EPOCHS
        out_dir = args.output_dir
    elif args.dry_run:
        # dry-run: show full manifest without authorization
        tasks = full_manifest()
        n_epochs = args.n_epochs
        out_dir = args.output_dir
    else:
        # Full factorial — require explicit authorization
        if not args.factorial_authorized:
            print(_FACTORIAL_NOT_AUTHORIZED_MSG, file=sys.stderr)
            sys.exit(2)
        tasks = full_manifest()
        n_epochs = args.n_epochs
        out_dir = args.output_dir

    print(f"PHASE10_SIGNAL_SENSITIVITY  tasks={len(tasks)}  epochs={n_epochs}  out={out_dir}")

    if args.dry_run:
        for t in tasks[:5]:
            print(f"  [{t['task_id']}] {t['output_file']}")
        if len(tasks) > 5:
            print(f"  ... and {len(tasks)-5} more")
        return

    if args.task_id is not None:
        if not args.factorial_authorized:
            print(_FACTORIAL_NOT_AUTHORIZED_MSG, file=sys.stderr)
            sys.exit(2)
        if args.task_id >= len(tasks):
            print(f"ERROR: task_id={args.task_id} >= n_tasks={len(tasks)}", file=sys.stderr)
            sys.exit(1)
        run_task(tasks[args.task_id], out_dir, n_epochs, verbose=args.verbose, resume=not args.no_resume)
    elif args.smoke_test or args.local_pilot:
        for task in tasks:
            run_task(task, out_dir, n_epochs, verbose=args.verbose, resume=not args.no_resume)
    else:
        print("Specify --task-id N, --smoke-test, or --local-pilot", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
