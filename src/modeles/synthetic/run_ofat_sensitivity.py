"""
run_ofat_sensitivity.py — OFAT signal sensitivity diagnostic (DEC-044 addendum)

One-Factor-At-a-Time design. 8 configurations × 2 scenarios × 3 seeds = 48 tasks.
Each task runs 7 models on 2 masks (MCAR 30% + block 30%).
Produces full per-seed/per-mask metric tables; no global-mean-only summaries.

NOT a substitute for Phase 10 (PHASE10_PARTIAL_CONFIRMED unchanged).
NOT the 324-task factorial (use run_signal_sensitivity.py with authorization flag).

Design:
  reference  : cs=original, ar=original, noise=original, lag=mixed
  A_low      : cs=low      (only cs varies)
  A_high     : cs=high     (only cs varies)
  B_low      : ar=low      (only ar varies)
  B_high     : ar=high     (only ar varies)
  C_low      : noise=low   (only noise varies)
  D_lag1     : lag=lag1    (only lag varies)
  D_lag2     : lag=lag2    (only lag varies)

Total: 8 × 2 scenarios × 3 seeds = 48 tasks

Gates O1-O8 frozen in gates_ofat.py BEFORE execution.

Usage:
    # Dry run
    python -m src.modeles.synthetic.run_ofat_sensitivity --dry-run

    # Full local run (all 48 tasks, 200 epochs, ~10-15 min)
    python -m src.modeles.synthetic.run_ofat_sensitivity --run-all \\
        --output-dir data/processed/synthetic_benchmark/ofat

    # Single task
    python -m src.modeles.synthetic.run_ofat_sensitivity \\
        --task-id 0 --output-dir data/processed/synthetic_benchmark/ofat

    # Linear-only first pass (24 tasks)
    python -m src.modeles.synthetic.run_ofat_sensitivity --run-all \\
        --scenarios linear --output-dir data/processed/synthetic_benchmark/ofat
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
from sklearn.metrics import average_precision_score

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

# ── OFAT manifest version and constants ──────────────────────────────────────

OFAT_VERSION = "ofat_v1"
OFAT_HIDDEN_DIM = 64
OFAT_SCENARIOS = ["linear", "nonlinear_heavy"]
OFAT_SEEDS = [42, 123, 456]
OFAT_MASKS = [("mcar", 30), ("block", 30)]

# ── OFAT axis definitions ─────────────────────────────────────────────────────
# Each entry: (axis_label, changed_key, changed_value_name, param_overrides)
# "reference" means no override (all original values).
# One axis changes per row; all others remain at original.

OFAT_CONFIGS: list[dict] = [
    # Reference — all original
    {
        "ofat_label": "reference",
        "axis": "none",
        "cs": "original",
        "ar": "original",
        "noise": "original",
        "lag": "mixed",
        "overrides": {},
    },
    # Axis A — cross-sector force
    {
        "ofat_label": "A_low",
        "axis": "A_cs",
        "cs": "low",
        "ar": "original",
        "noise": "original",
        "lag": "mixed",
        "overrides": {"weight_range": (0.1, 0.3)},
    },
    {
        "ofat_label": "A_high",
        "axis": "A_cs",
        "cs": "high",
        "ar": "original",
        "noise": "original",
        "lag": "mixed",
        "overrides": {"weight_range": (0.8, 1.2)},
    },
    # Axis B — AR strength
    {
        "ofat_label": "B_low",
        "axis": "B_ar",
        "cs": "original",
        "ar": "low",
        "noise": "original",
        "lag": "mixed",
        "overrides": {"ar_coef_range": (0.1, 0.3)},
    },
    {
        "ofat_label": "B_high",
        "axis": "B_ar",
        "cs": "original",
        "ar": "high",
        "noise": "original",
        "lag": "mixed",
        "overrides": {"ar_coef_range": (0.5, 0.8)},
    },
    # Axis C — noise
    {
        "ofat_label": "C_low",
        "axis": "C_noise",
        "cs": "original",
        "ar": "original",
        "noise": "low",
        "lag": "mixed",
        "overrides": {"noise_sigma_range": (0.05, 0.10)},
    },
    # Axis D — lag structure
    {
        "ofat_label": "D_lag1",
        "axis": "D_lag",
        "cs": "original",
        "ar": "original",
        "noise": "original",
        "lag": "lag1",
        "overrides": {"forced_lag": 1},
    },
    {
        "ofat_label": "D_lag2",
        "axis": "D_lag",
        "cs": "original",
        "ar": "original",
        "noise": "original",
        "lag": "lag2",
        "overrides": {"forced_lag": 2},
    },
]

# Sanity: reference appears exactly once and no config mixes high-cs + low-ar + low-noise
_REF_LABELS = [c["ofat_label"] for c in OFAT_CONFIGS if c["ofat_label"] == "reference"]
assert len(_REF_LABELS) == 1, "Reference must appear exactly once"
for _c in OFAT_CONFIGS:
    assert not (_c["cs"] == "high" and _c["ar"] == "low" and _c["noise"] == "low"), (
        f"Confounded config not allowed: {_c['ofat_label']}"
    )


def _build_config(base_scenario: str, ofat_cfg: dict, seed: int) -> SyntheticConfig:
    base = BENCHMARK_SCENARIOS[base_scenario]
    overrides = {**ofat_cfg["overrides"], "seed": seed}
    return dataclasses.replace(base, **overrides)


def build_manifest(scenarios: list[str] | None = None, seeds: list[int] | None = None) -> list[dict]:
    scenarios = scenarios or OFAT_SCENARIOS
    seeds = seeds or OFAT_SEEDS
    tasks = []
    for ofat_cfg in OFAT_CONFIGS:
        for scenario in sorted(scenarios):
            for seed in sorted(seeds):
                label = ofat_cfg["ofat_label"]
                tasks.append({
                    "task_id": len(tasks),
                    "ofat_label": label,
                    "axis": ofat_cfg["axis"],
                    "cs": ofat_cfg["cs"],
                    "ar": ofat_cfg["ar"],
                    "noise": ofat_cfg["noise"],
                    "lag": ofat_cfg["lag"],
                    "scenario": scenario,
                    "seed": seed,
                    "manifest_version": OFAT_VERSION,
                    "output_file": f"ofat_{label}_{scenario}_seed{seed:05d}.json",
                })
    return tasks


# ── I/O ───────────────────────────────────────────────────────────────────────

def _json_default(obj):
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    return str(obj)


def write_atomic(data: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2, default=_json_default)
    os.rename(tmp, path)


def is_valid_result(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        d = json.loads(path.read_text())
        return (
            d.get("manifest_version") == OFAT_VERSION
            and "mask_results" in d
            and "leakage_check" in d
        )
    except Exception:
        return False


# ── AUPRC helper (same off-diagonal convention as compute_edge_recovery_metrics) ──

def _compute_auprc(true_rels, n_sectors: int, learned_attn: np.ndarray) -> tuple[float, float]:
    """Returns (auprc, prevalence). Convention: learned_attn[target, source]."""
    true_adj = np.zeros((n_sectors, n_sectors))
    for rel in true_rels:
        if rel.source_sector < n_sectors and rel.target_sector < n_sectors:
            true_adj[rel.source_sector, rel.target_sector] = 1
    rows, cols = np.where(~np.eye(n_sectors, dtype=bool))
    y_true = true_adj[rows, cols]
    y_score = learned_attn[cols, rows]  # attn[target, source]
    n_true = int(y_true.sum())
    prevalence = n_true / len(y_true) if len(y_true) > 0 else 0.0
    if n_true == 0 or n_true == len(y_true):
        return float("nan"), prevalence
    try:
        auprc = float(average_precision_score(y_true, y_score))
    except Exception:
        auprc = float("nan")
    return auprc, prevalence


# ── Metric helpers ────────────────────────────────────────────────────────────

def _mdict(m) -> dict:
    return {
        "mae": float(m.mae),
        "rmse": float(m.rmse),
        "pearson_r": float(m.pearson_r) if m.pearson_r == m.pearson_r else float("nan"),
        "n_evaluated": int(m.n_evaluated),
    }


def _edict(e, true_rels, n_sectors, attn) -> dict:
    lag_acc = float(e.lag_accuracy) if (e.lag_accuracy is not None and e.lag_accuracy == e.lag_accuracy) else float("nan")
    auprc, prevalence = _compute_auprc(true_rels, n_sectors, attn)
    return {
        "edge_auc": float(e.auc) if e.auc == e.auc else float("nan"),
        "edge_auprc": auprc,
        "edge_prevalence": prevalence,
        "edge_f1": float(e.f1_at_k),
        "edge_precision": float(e.precision_at_k),
        "edge_recall": float(e.recall_at_k),
        "edge_fpr": float(e.false_positive_rate),
        "edge_sign_acc": float(e.sign_accuracy) if e.sign_accuracy == e.sign_accuracy else float("nan"),
        "edge_lag_acc": lag_acc,
        "n_true_edges": int(e.n_true_edges),
    }


# ── Per-mask runner ───────────────────────────────────────────────────────────

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
    t0 = time.time()
    pred = ForwardFillImputer().fit_transform(obs, mask)
    m = compute_imputation_metrics(panel, pred, mask)
    results["ffill"] = {**_mdict(m), "train_s": round(time.time() - t0, 2)}

    # 2. ridge
    t0 = time.time()
    pred = RidgeImputer(alpha=1.0).fit_transform(obs, mask)
    m = compute_imputation_metrics(panel, pred, mask)
    results["ridge"] = {**_mdict(m), "train_s": round(time.time() - t0, 2)}

    # 3. no_graph
    t0 = time.time()
    torch.manual_seed(torch_seed)
    m_ng = HERALDGraphImputer(n_sectors, n_territories, hidden_dim=OFAT_HIDDEN_DIM)
    train_herald_imputer(m_ng, obs, mask, identity_s, identity_t, n_epochs=n_epochs)
    pred = impute_deterministic(m_ng, obs, mask, identity_s, identity_t)
    m = compute_imputation_metrics(panel, pred, mask)
    results["no_graph"] = {**_mdict(m), "train_s": round(time.time() - t0, 2)}

    # 4. herald_contemp
    t0 = time.time()
    torch.manual_seed(torch_seed + 1)
    m_hc = HERALDGraphImputer(n_sectors, n_territories, hidden_dim=OFAT_HIDDEN_DIM)
    train_herald_imputer(m_hc, obs, mask, adj_s, adj_t, n_epochs=n_epochs)
    pred = impute_deterministic(m_hc, obs, mask, adj_s, adj_t)
    m = compute_imputation_metrics(panel, pred, mask)
    attn_hc = m_hc.get_sector_attention()
    e = compute_edge_recovery_metrics(true_rels, n_sectors, attn_hc)
    results["herald_contemp"] = {**_mdict(m), **_edict(e, true_rels, n_sectors, attn_hc),
                                  "train_s": round(time.time() - t0, 2)}

    # 5. herald_lagged
    t0 = time.time()
    torch.manual_seed(torch_seed + 10)
    m_hl = HERALDGraphImputerLagged(n_sectors, n_territories, hidden_dim=OFAT_HIDDEN_DIM)
    train_herald_lagged(m_hl, obs, mask, adj_s, adj_t, n_epochs=n_epochs)
    pred = impute_deterministic_lagged(m_hl, obs, mask, adj_s, adj_t)
    m = compute_imputation_metrics(panel, pred, mask)
    attn_hl = m_hl.get_sector_attention()
    e = compute_edge_recovery_metrics(true_rels, n_sectors, attn_hl)
    results["herald_lagged"] = {**_mdict(m), **_edict(e, true_rels, n_sectors, attn_hl),
                                 "train_s": round(time.time() - t0, 2)}
    if verbose:
        print(f"      herald_lagged  MAE={m.mae:.4f}  AUC={results['herald_lagged']['edge_auc']:.3f}"
              f"  AUPRC={results['herald_lagged']['edge_auprc']:.3f}")

    # 6. herald_lagged_permuted
    t0 = time.time()
    torch.manual_seed(torch_seed + 11)
    perm_rng = np.random.default_rng(seed + 99999)
    adj_s_perm, adj_t_perm, _, _ = build_permuted_adj(adj_s, adj_t, perm_rng)
    m_hlp = HERALDGraphImputerLagged(n_sectors, n_territories, hidden_dim=OFAT_HIDDEN_DIM)
    train_herald_lagged(m_hlp, obs, mask, adj_s_perm, adj_t_perm, n_epochs=n_epochs)
    pred = impute_deterministic_lagged(m_hlp, obs, mask, adj_s_perm, adj_t_perm)
    m = compute_imputation_metrics(panel, pred, mask)
    results["herald_lagged_permuted"] = {**_mdict(m), "train_s": round(time.time() - t0, 2)}

    # 7. oracle_lagged
    t0 = time.time()
    torch.manual_seed(torch_seed + 12)
    m_ol = HERALDGraphImputerLagged(n_sectors, n_territories, hidden_dim=OFAT_HIDDEN_DIM)
    build_directed_oracle_lagged(m_ol, true_rels, n_sectors)
    train_herald_lagged(m_ol, obs, mask, n_epochs=n_epochs)
    pred = impute_deterministic_lagged(m_ol, obs, mask)
    m = compute_imputation_metrics(panel, pred, mask)
    attn_ol = m_ol.get_sector_attention()
    e = compute_edge_recovery_metrics(true_rels, n_sectors, attn_ol)
    results["oracle_lagged"] = {**_mdict(m), **_edict(e, true_rels, n_sectors, attn_ol),
                                 "note": "directed_oracle_frozen",
                                 "train_s": round(time.time() - t0, 2)}
    if verbose:
        print(f"      oracle_lagged  MAE={m.mae:.4f}  AUC={results['oracle_lagged']['edge_auc']:.3f}")

    return results


# ── Task runner ───────────────────────────────────────────────────────────────

def run_task(task: dict, output_dir: Path, n_epochs: int, verbose=False, resume=True) -> Path:
    out_path = output_dir / task["output_file"]
    if resume and is_valid_result(out_path):
        print(f"  [skip] {task['output_file']}")
        return out_path

    ofat_cfg = next(c for c in OFAT_CONFIGS if c["ofat_label"] == task["ofat_label"])
    cfg = _build_config(task["scenario"], ofat_cfg, task["seed"])

    print(f"  [{task['task_id']:2d}] {task['ofat_label']:12s} | {task['scenario']:15s} | seed={task['seed']}")

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
    for mtype, level in OFAT_MASKS:
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
            mask_results[mkey] = {"error": str(exc), "traceback": traceback.format_exc()[-500:]}

    elapsed = round(time.time() - t_task, 1)
    output = {
        **{k: task[k] for k in ["task_id", "ofat_label", "axis", "cs", "ar", "noise", "lag",
                                  "scenario", "seed", "manifest_version"]},
        "n_sectors": n_sectors,
        "n_territories": n_territories,
        "n_true_relations": len(true_rels),
        "leakage_check": lk,
        "elapsed_seconds": elapsed,
        "mask_results": mask_results,
    }
    write_atomic(output, out_path)
    print(f"         done: {elapsed}s → {out_path.name}")
    return out_path


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="OFAT sensitivity diagnostic — 48 tasks")
    ap.add_argument("--task-id", type=int, default=None)
    ap.add_argument("--output-dir", type=Path, default=Path("data/processed/synthetic_benchmark/ofat"))
    ap.add_argument("--n-epochs", type=int, default=200)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--run-all", action="store_true", help="Run all 48 OFAT tasks locally")
    ap.add_argument("--scenarios", nargs="+", choices=OFAT_SCENARIOS, default=None)
    ap.add_argument("--no-resume", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    tasks = build_manifest(scenarios=args.scenarios)
    print(f"OFAT  tasks={len(tasks)}  epochs={args.n_epochs}  out={args.output_dir}")

    if args.dry_run:
        for t in tasks:
            print(f"  [{t['task_id']:2d}] {t['ofat_label']:12s} {t['scenario']:15s} seed={t['seed']}")
        return

    if args.task_id is not None:
        if args.task_id >= len(tasks):
            print(f"ERROR: task_id={args.task_id} >= n_tasks={len(tasks)}", file=sys.stderr)
            sys.exit(1)
        run_task(tasks[args.task_id], args.output_dir, args.n_epochs,
                 verbose=args.verbose, resume=not args.no_resume)
    elif args.run_all:
        t0_total = time.time()
        for task in tasks:
            run_task(task, args.output_dir, args.n_epochs,
                     verbose=args.verbose, resume=not args.no_resume)
        total = round(time.time() - t0_total, 1)
        print(f"\nAll {len(tasks)} OFAT tasks done in {total}s ({total/60:.1f} min)")
    else:
        print("Specify --task-id N or --run-all", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
