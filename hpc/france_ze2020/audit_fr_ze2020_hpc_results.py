"""
HERALD -- France ZE2020 HPC results audit (post-collection, descriptive only).

See reports/canonical/HERALD_19_FR_ZE2020_HPC_SPEC.md sections 6/8. Run
AFTER rsync-ing hpc_results/fr_ze2020_hpc_<RUN_ID>/ back from meso. Computes
the 5 pre-registered gates (G1-G5) as DESCRIPTIVE numbers only -- this
script does not promote, recommend, or declare a final result. Whether to
act on the gate numbers is a human decision (HERALD_19 section 6).

Expects, per seed subdirectory hpc_results/fr_ze2020_hpc_<RUN_ID>/seed_<N>/:
  fr_ze2020_baseline_metrics_v1.csv
  fr_ze2020_relational_baseline_metrics_v1.csv
  fr_ze2020_neural_relational_metrics_v1.csv
  fr_ze2020_neural_relational_feature_signals_v1.csv
  fr_ze2020_sector_graph_metrics_v1.csv
  fr_ze2020_sector_graph_relation_signals_v1.csv

Output: a JSON report with G1-G5 descriptive results, never a
"PASS -> promote" instruction.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

FORBIDDEN_COLUMNS = {"recommendation", "recommended_action", "policy_action"}

BASELINE_FOR = {
    "ridge_relational": "ridge_temporal",
    "mlp_relational": "ridge_relational",
    "graph_mlp": "persistence_sector",
}

METRIC_FILES = [
    "fr_ze2020_baseline_metrics_v1.csv",
    "fr_ze2020_relational_baseline_metrics_v1.csv",
    "fr_ze2020_neural_relational_metrics_v1.csv",
    "fr_ze2020_sector_graph_metrics_v1.csv",
]
SIGNAL_FILES = [
    "fr_ze2020_neural_relational_feature_signals_v1.csv",
    "fr_ze2020_sector_graph_relation_signals_v1.csv",
]


def find_seed_dirs(results_dir: Path) -> dict[int, Path]:
    seed_dirs = {}
    for path in sorted(results_dir.glob("seed_*")):
        if path.is_dir():
            try:
                seed = int(path.name.replace("seed_", ""))
            except ValueError:
                continue
            seed_dirs[seed] = path
    return seed_dirs


def load_all_metrics(seed_dirs: dict[int, Path]) -> pd.DataFrame:
    frames = []
    for seed, seed_dir in seed_dirs.items():
        for fname in METRIC_FILES:
            fpath = seed_dir / fname
            if not fpath.exists():
                continue
            df = pd.read_csv(fpath)
            df["seed"] = seed
            df["source_file"] = fname
            frames.append(df)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def gate_g1_no_errors(seed_dirs: dict[int, Path], expected_seeds: list[int]) -> dict:
    """NaN is not flagged here: n_train_years is legitimately None/NaN for
    the persistence model (it never fits anything -- already correct,
    tested behavior in each script's own suite). Only +-Inf is checked,
    which would indicate a real bug (e.g. the division-by-zero edge case
    documented in HERALD_17 section 12). Same false-positive found and
    fixed in smoke_test_fr_ze2020_hpc.sh applies here -- this function had
    the identical np.isfinite() bug, caught when auditing the first real
    array run (job 7498752, 2026-06-24)."""
    missing_seeds = [s for s in expected_seeds if s not in seed_dirs]
    missing_files = []
    infinite_files = []
    for seed, seed_dir in seed_dirs.items():
        for fname in METRIC_FILES + SIGNAL_FILES:
            fpath = seed_dir / fname
            if not fpath.exists():
                missing_files.append(str(fpath))
                continue
            df = pd.read_csv(fpath)
            numeric = df.select_dtypes(include=[np.number])
            if not numeric.empty and np.isinf(numeric.to_numpy(dtype=float)).any():
                infinite_files.append(str(fpath))
    passed = not missing_seeds and not missing_files and not infinite_files
    return {
        "passed": passed,
        "missing_seeds": missing_seeds,
        "missing_files": missing_files,
        "infinite_files": infinite_files,
    }


def gate_g2_wmape_stability(all_metrics: pd.DataFrame) -> dict:
    if all_metrics.empty:
        return {"passed": False, "reason": "no metrics found", "per_model": {}}
    per_model = {}
    for model, group in all_metrics.groupby("model"):
        seed_means = group.groupby("seed")["wmape"].mean()
        mean_wmape = float(seed_means.mean())
        std_wmape = float(seed_means.std()) if len(seed_means) > 1 else 0.0
        relative_std = std_wmape / mean_wmape if mean_wmape else float("nan")
        per_model[model] = {
            "mean_wmape": mean_wmape,
            "std_wmape": std_wmape,
            "relative_std": relative_std,
            "n_seeds": int(seed_means.shape[0]),
        }
    threshold = 0.20
    passed = all(
        m["relative_std"] <= threshold for m in per_model.values() if not np.isnan(m["relative_std"])
    )
    return {"passed": passed, "threshold_relative_std": threshold, "per_model": per_model}


def gate_g3_beats_baseline(all_metrics: pd.DataFrame) -> dict:
    if all_metrics.empty:
        return {"passed": False, "reason": "no metrics found", "per_candidate": {}}
    per_candidate = {}
    overall_passed = False
    for candidate, baseline in BASELINE_FOR.items():
        cand_rows = all_metrics[all_metrics["model"] == candidate]
        base_rows = all_metrics[all_metrics["model"] == baseline]
        if cand_rows.empty or base_rows.empty:
            continue
        wins = 0
        n_compared = 0
        for seed in sorted(cand_rows["seed"].unique()):
            cand_wmape = cand_rows[cand_rows["seed"] == seed]["wmape"].mean()
            base_wmape = base_rows[base_rows["seed"] == seed]["wmape"].mean()
            if pd.isna(cand_wmape) or pd.isna(base_wmape):
                continue
            n_compared += 1
            if cand_wmape < base_wmape:
                wins += 1
        candidate_passed = n_compared > 0 and wins >= 3
        overall_passed = overall_passed or candidate_passed
        per_candidate[candidate] = {
            "baseline": baseline,
            "wins": wins,
            "n_compared": n_compared,
            "passed": candidate_passed,
        }
    return {"passed": overall_passed, "rule": "wins>=3 of compared seeds", "per_candidate": per_candidate}


def gate_g4_signal_stability(seed_dirs: dict[int, Path]) -> dict:
    relation_overlaps = []
    seeds = sorted(seed_dirs.keys())
    edge_sets = {}
    for seed, seed_dir in seed_dirs.items():
        fpath = seed_dir / "fr_ze2020_sector_graph_relation_signals_v1.csv"
        if not fpath.exists():
            continue
        df = pd.read_csv(fpath)
        if df.empty:
            continue
        pairs = set(zip(df["source_node"], df["target_node"]))
        edge_sets[seed] = pairs

    for i in range(len(seeds)):
        for j in range(i + 1, len(seeds)):
            a, b = seeds[i], seeds[j]
            if a not in edge_sets or b not in edge_sets or not edge_sets[a] or not edge_sets[b]:
                continue
            overlap = len(edge_sets[a] & edge_sets[b]) / max(len(edge_sets[a] | edge_sets[b]), 1)
            relation_overlaps.append(overlap)

    if not relation_overlaps:
        return {"passed": False, "reason": "no comparable relation_signals across seed pairs", "mean_overlap": None}

    mean_overlap = float(np.mean(relation_overlaps))
    return {"passed": mean_overlap >= 0.5, "threshold": 0.5, "mean_overlap": mean_overlap, "n_seed_pairs": len(relation_overlaps)}


def gate_g5_output_separation(seed_dirs: dict[int, Path]) -> dict:
    violations = []
    for seed, seed_dir in seed_dirs.items():
        for fname in METRIC_FILES + SIGNAL_FILES:
            fpath = seed_dir / fname
            if not fpath.exists():
                continue
            cols = {c.lower() for c in pd.read_csv(fpath, nrows=0).columns}
            if cols & FORBIDDEN_COLUMNS:
                violations.append(str(fpath))
    return {"passed": not violations, "violations": violations}


def build_report(results_dir: Path, expected_seeds: list[int]) -> dict:
    seed_dirs = find_seed_dirs(results_dir)
    all_metrics = load_all_metrics(seed_dirs)

    report = {
        "results_dir": str(results_dir),
        "seeds_found": sorted(seed_dirs.keys()),
        "expected_seeds": expected_seeds,
        "gates": {
            "G1_no_errors": gate_g1_no_errors(seed_dirs, expected_seeds),
            "G2_wmape_stability": gate_g2_wmape_stability(all_metrics),
            "G3_beats_baseline": gate_g3_beats_baseline(all_metrics),
            "G4_signal_stability": gate_g4_signal_stability(seed_dirs),
            "G5_output_separation": gate_g5_output_separation(seed_dirs),
        },
        "caveat": (
            "Descriptive gate computation only. No causal claim. No automatic "
            "recommendation. Whether to act on any gate result (e.g. promote a "
            "candidate, request more seeds, or close the hypothesis) is a human "
            "decision -- see HERALD_19_FR_ZE2020_HPC_SPEC.md section 6."
        ),
        "claim_status": "hpc_gate_audit_descriptive_only",
    }
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit FR ZE2020 HPC results (descriptive gates only).")
    parser.add_argument("results_dir", type=Path)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--expected-seeds", type=int, nargs="+", default=[42, 43, 44, 45, 46])
    args = parser.parse_args()

    report = build_report(args.results_dir, args.expected_seeds)

    print(json.dumps(report, indent=2))
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2))
        print(f"Saved: {args.out}")


if __name__ == "__main__":
    main()
