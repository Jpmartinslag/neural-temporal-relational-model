"""Phase 2K latent-regime dimension audit.

Checks completeness (13 configs × 10 seeds = 130 runs), per-run artifact
integrity, predictive metrics, seed stability, paired comparisons, and
latent-dimension diagnostics including auto-mask effective_dim.

Usage:
    python3 hpc/regime/audit_herald_phase2k_latent_dim.py
    python3 hpc/regime/audit_herald_phase2k_latent_dim.py --root hpc_results/herald_regime_phase2k_latent_dim_<STAMP>_r1
    python3 hpc/regime/audit_herald_phase2k_latent_dim.py --preflight
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT_DIR = Path(__file__).resolve().parents[2]

PHASE2K_LABELS = [
    "L1_gate", "L2_gate", "L3_gate", "L4_gate", "L5_gate",
    "L1_both", "L2_both", "L3_both", "L4_both", "L5_both",
    "AUTO5_l1_001", "AUTO5_l1_005", "AUTO5_l1_010",
]
PHASE2K_SEEDS = [0, 1, 7, 13, 17, 42, 77, 99, 123, 2025]
EXPECTED_CONFIGS = len(PHASE2K_LABELS)
EXPECTED_SEEDS = len(PHASE2K_SEEDS)
EXPECTED_RUNS = EXPECTED_CONFIGS * EXPECTED_SEEDS

LABEL_TO_DIM = {
    "L1_gate": 1, "L2_gate": 2, "L3_gate": 3, "L4_gate": 4, "L5_gate": 5,
    "L1_both": 1, "L2_both": 2, "L3_both": 3, "L4_both": 4, "L5_both": 5,
    "AUTO5_l1_001": 5, "AUTO5_l1_005": 5, "AUTO5_l1_010": 5,
}
AUTO_LABELS = {"AUTO5_l1_001", "AUTO5_l1_005", "AUTO5_l1_010"}
GATE_LABELS = {"L1_gate", "L2_gate", "L3_gate", "L4_gate", "L5_gate"}
BOTH_LABELS = {"L1_both", "L2_both", "L3_both", "L4_both", "L5_both"}

EVAL_YEARS = [2021, 2022, 2023, 2024, 2025]
REFERENCE_LABEL = "L3_gate"


def tag_for_label(label):
    if label in GATE_LABELS or label in AUTO_LABELS:
        return f"regime_no_regime_learned_regime_gate_sector_enhanced_no_source_flags_{label}"
    return f"regime_no_regime_learned_regime_both_sector_enhanced_no_source_flags_{label}"


def preflight_check():
    """Check that plan produces 13 configs and all labels are present."""
    import subprocess
    result = subprocess.run(
        ["bash", "-c",
         "source hpc/regime/regime_plan_configs.sh && "
         "REGIME_PLAN=phase2k_latent_dim plan_configs | wc -l"],
        capture_output=True, text=True, cwd=str(ROOT_DIR),
    )
    n = int(result.stdout.strip())
    if n != EXPECTED_CONFIGS:
        print(f"PREFLIGHT ERROR: expected {EXPECTED_CONFIGS} configs, got {n}", file=sys.stderr)
        sys.exit(1)
    print(f"preflight: config count = {n} OK")

    # Check label presence via label column (field 4)
    result2 = subprocess.run(
        ["bash", "-c",
         "source hpc/regime/regime_plan_configs.sh && "
         "REGIME_PLAN=phase2k_latent_dim plan_configs | awk '{print $4}'"],
        capture_output=True, text=True, cwd=str(ROOT_DIR),
    )
    found = set(result2.stdout.strip().split())
    missing = set(PHASE2K_LABELS) - found
    if missing:
        print(f"PREFLIGHT ERROR: missing labels: {sorted(missing)}", file=sys.stderr)
        sys.exit(1)
    print(f"preflight: all {EXPECTED_CONFIGS} labels present OK")


def load_json_metrics(root: Path):
    """Return dict: label -> seed -> metrics_dict."""
    data = {}
    for label in PHASE2K_LABELS:
        tag = tag_for_label(label)
        data[label] = {}
        for seed in PHASE2K_SEEDS:
            jpath = root / "reports" / "per_run" / f"{tag}_seed_{seed}.json"
            if not jpath.exists():
                data[label][seed] = None
                continue
            raw = json.loads(jpath.read_text())
            run_key = f"{jpath.stem}"
            rv = raw.get(run_key, None)
            if rv is None and len(raw) == 1:
                rv = next(iter(raw.values()))
            data[label][seed] = rv
    return data


def check_completeness(root: Path):
    """Verify 130 JSON files exist and all artifacts are present."""
    errors = []
    found_runs = 0
    for label in PHASE2K_LABELS:
        tag = tag_for_label(label)
        for seed in PHASE2K_SEEDS:
            base = f"{tag}_seed_{seed}"
            json_f = root / "reports" / "per_run" / f"{base}.json"
            total_f = root / "data_processed" / f"herald_semi_v2_predictions_total_full_{base}_v1.csv"
            sector_f = root / "data_processed" / f"herald_semi_v2_predictions_sector_full_{base}_v1.csv"
            npz_f = root / "data_processed" / f"herald_semi_v2_internals_full_{base}_v1.npz"
            meta_f = root / "metadata" / f"{base}.json"
            missing = [str(f) for f in [json_f, total_f, sector_f, npz_f, meta_f] if not f.exists()]
            if not missing:
                found_runs += 1
            else:
                errors.append(f"{label} seed={seed}: MISSING {missing}")
    print(f"completeness: {found_runs}/{EXPECTED_RUNS} runs complete")
    if errors:
        for e in errors[:20]:
            print(f"  MISSING: {e}")
        if len(errors) > 20:
            print(f"  ... and {len(errors) - 20} more")
    return len(errors) == 0


def check_latent_metadata(data):
    """Verify latent_regime_dim and auto_mask fields in JSON metrics."""
    errors = []
    for label, seeds in data.items():
        expected_dim = LABEL_TO_DIM[label]
        expect_auto = label in AUTO_LABELS
        for seed, rv in seeds.items():
            if rv is None:
                continue
            actual_dim = rv.get("latent_regime_dim")
            actual_auto = rv.get("latent_dim_auto_mask", False)
            if actual_dim != expected_dim:
                errors.append(f"{label} seed={seed}: latent_regime_dim={actual_dim} expected={expected_dim}")
            if actual_auto != expect_auto:
                errors.append(f"{label} seed={seed}: auto_mask={actual_auto} expected={expect_auto}")
            if expect_auto:
                mv = rv.get("latent_dim_mask_values")
                ed = rv.get("latent_dim_effective_dim")
                if mv is None:
                    errors.append(f"{label} seed={seed}: latent_dim_mask_values missing")
                elif len(mv) != expected_dim:
                    errors.append(f"{label} seed={seed}: mask_values len={len(mv)} expected={expected_dim}")
                if ed is None:
                    errors.append(f"{label} seed={seed}: latent_dim_effective_dim missing")
    if errors:
        print(f"latent metadata: {len(errors)} errors")
        for e in errors[:10]:
            print(f"  {e}")
    else:
        print("latent metadata: OK")
    return len(errors) == 0


def compute_wmape_stats(data):
    """Return dict: label -> {mean, std, by_year_mean}."""
    stats = {}
    for label, seeds in data.items():
        per_seed_mean = []
        by_year = {y: [] for y in EVAL_YEARS}
        for seed, rv in seeds.items():
            if rv is None:
                continue
            m = rv.get("total_wmape_mean")
            if m is not None:
                per_seed_mean.append(m)
            py = rv.get("per_year_total", {})
            for y in EVAL_YEARS:
                v = py.get(str(y)) or py.get(y)
                if v is not None:
                    by_year[y].append(v)
        stats[label] = {
            "mean": round(float(np.mean(per_seed_mean)), 6) if per_seed_mean else None,
            "std":  round(float(np.std(per_seed_mean)), 6) if len(per_seed_mean) > 1 else None,
            "n_seeds": len(per_seed_mean),
            "by_year": {y: round(float(np.mean(v)), 6) if v else None for y, v in by_year.items()},
        }
    return stats


def print_summary_table(stats):
    """Print WMAPE comparison table."""
    header = f"{'Label':<20} {'N':>3} {'mean':>9} {'std':>8} {'2021':>9} {'2025':>9}"
    print("\n" + header)
    print("-" * len(header))
    for label in PHASE2K_LABELS:
        s = stats.get(label, {})
        mean = f"{s['mean']:.6f}" if s.get("mean") is not None else "    ——"
        std  = f"{s['std']:.6f}"  if s.get("std") is not None else "    ——"
        y21  = f"{s['by_year'].get(2021):.6f}" if s.get("by_year", {}).get(2021) is not None else "    ——"
        y25  = f"{s['by_year'].get(2025):.6f}" if s.get("by_year", {}).get(2025) is not None else "    ——"
        print(f"{label:<20} {s.get('n_seeds', 0):>3} {mean:>9} {std:>8} {y21:>9} {y25:>9}")


def paired_comparison(data, stats, ref_label=REFERENCE_LABEL):
    """Compare each config vs reference label by seed."""
    ref_seeds = data.get(ref_label, {})
    print(f"\nPaired comparison vs {ref_label}:")
    for label in PHASE2K_LABELS:
        if label == ref_label:
            continue
        wins = losses = ties = 0
        for seed in PHASE2K_SEEDS:
            rv = data[label].get(seed)
            ref_rv = ref_seeds.get(seed)
            if rv is None or ref_rv is None:
                continue
            m = rv.get("total_wmape_mean")
            rm = ref_rv.get("total_wmape_mean")
            if m is None or rm is None:
                continue
            if m < rm - 1e-7:
                wins += 1
            elif m > rm + 1e-7:
                losses += 1
            else:
                ties += 1
        print(f"  {label:<20} wins={wins} losses={losses} ties={ties}")


def gate_vs_both_comparison(data, stats):
    """Compare gate vs both at same dimension."""
    print("\nGate vs Both at same dim:")
    dims = [1, 2, 3, 4, 5]
    for d in dims:
        gate_label = f"L{d}_gate"
        both_label = f"L{d}_both"
        g_mean = stats.get(gate_label, {}).get("mean")
        b_mean = stats.get(both_label, {}).get("mean")
        if g_mean is None and b_mean is None:
            continue
        g_str = f"{g_mean:.6f}" if g_mean is not None else "——"
        b_str = f"{b_mean:.6f}" if b_mean is not None else "——"
        diff = f"{b_mean - g_mean:+.6f}" if (g_mean is not None and b_mean is not None) else "——"
        print(f"  dim={d}: gate={g_str}  both={b_str}  delta={diff} (both-gate)")


def auto_mask_summary(data):
    """Report effective_dim statistics for AUTO5 configs."""
    print("\nAuto-mask effective_dim summary (mask > 0.2 threshold):")
    for label in AUTO_LABELS:
        eff_dims = []
        for seed, rv in data[label].items():
            if rv is None:
                continue
            ed = rv.get("latent_dim_effective_dim")
            if ed is not None:
                eff_dims.append(ed)
        if eff_dims:
            print(f"  {label:<20} effective_dim: mean={np.mean(eff_dims):.2f} "
                  f"min={min(eff_dims)} max={max(eff_dims)} "
                  f"(over {len(eff_dims)} seeds)")
        else:
            print(f"  {label:<20} no effective_dim data")


def latent_variance_summary(root: Path):
    """Report per-dimension variance of latent_regime_values from NPZ files."""
    print("\nLatent variance per dimension (sample: seed=0, fold=last):")
    for label in PHASE2K_LABELS[:6]:  # sample, not all
        tag = tag_for_label(label)
        npz_f = root / "data_processed" / f"herald_semi_v2_internals_full_{tag}_seed_0_v1.npz"
        if not npz_f.exists():
            print(f"  {label:<20} NPZ not found")
            continue
        try:
            npz = np.load(npz_f, allow_pickle=True)
            latent = npz.get("latent_regime_values")
            if latent is None:
                print(f"  {label:<20} latent_regime_values not in NPZ")
                continue
            if hasattr(latent, "item"):
                latent = latent.item()
                # dict keyed by year; take last
                last_key = max(latent.keys())
                latent = latent[last_key]
            var_per_dim = np.var(latent, axis=0)
            print(f"  {label:<20} dim={latent.shape[-1]} "
                  f"var_per_dim={[round(float(v), 5) for v in var_per_dim]}")
        except Exception as exc:
            print(f"  {label:<20} ERROR: {exc}")


def adj_delta_summary(root: Path):
    """Compare adj_delta_by_year for gate vs both variants."""
    print("\nadj_delta_by_year comparison gate vs both (seed=0):")
    for d in [1, 3, 5]:
        for variant in ["gate", "both"]:
            label = f"L{d}_{variant}"
            if variant == "both" and d == 5:
                continue
            tag = tag_for_label(label)
            npz_f = root / "data_processed" / f"herald_semi_v2_internals_full_{tag}_seed_0_v1.npz"
            if not npz_f.exists():
                print(f"  {label:<20} NPZ not found")
                continue
            try:
                npz = np.load(npz_f, allow_pickle=True)
                adj_delta = npz.get("adj_delta_by_year")
                if adj_delta is None:
                    print(f"  {label:<20} adj_delta_by_year not in NPZ")
                    continue
                mean_delta = float(np.mean(adj_delta)) if len(adj_delta) > 0 else 0.0
                print(f"  {label:<20} mean adj_delta={mean_delta:.5f}")
            except Exception as exc:
                print(f"  {label:<20} ERROR: {exc}")


def main():
    parser = argparse.ArgumentParser(description="Phase 2K audit")
    parser.add_argument("--root", type=Path, default=None,
                        help="OUT_ROOT of completed run (required for post-run audit)")
    parser.add_argument("--preflight", action="store_true",
                        help="Preflight only: check plan configs without results")
    args = parser.parse_args()

    if args.preflight or args.root is None:
        preflight_check()
        if args.preflight:
            print("Preflight OK")
            return

    root = args.root
    if not root.exists():
        print(f"ERROR: root not found: {root}", file=sys.stderr)
        sys.exit(1)

    print(f"Auditing: {root}")
    print(f"Expected: {EXPECTED_CONFIGS} configs × {EXPECTED_SEEDS} seeds = {EXPECTED_RUNS} runs")

    complete = check_completeness(root)
    data = load_json_metrics(root)
    meta_ok = check_latent_metadata(data)
    stats = compute_wmape_stats(data)

    print_summary_table(stats)
    paired_comparison(data, stats)
    gate_vs_both_comparison(data, stats)
    auto_mask_summary(data)
    latent_variance_summary(root)
    adj_delta_summary(root)

    # Final verdict.
    print("\n--- AUDIT VERDICT ---")
    if not complete:
        print("INCOMPLETE: not all 130 runs finished")
    if not meta_ok:
        print("METADATA ERRORS: latent_regime_dim or auto_mask fields incorrect")
    if complete and meta_ok:
        print("PASS: completeness and metadata OK")
        ref_mean = stats.get(REFERENCE_LABEL, {}).get("mean")
        if ref_mean is not None:
            print(f"Reference ({REFERENCE_LABEL}) WMAPE mean = {ref_mean:.6f}")
            # Decision rule: find smallest dim matching reference
            candidates = []
            for label in ["L1_gate", "L2_gate"]:
                m = stats.get(label, {}).get("mean")
                if m is not None and m <= ref_mean + 5e-4:
                    candidates.append(label)
            if candidates:
                print(f"H1 supported: {candidates} match reference within 0.0005")
            else:
                print("H1 uncertain: smaller dims do not clearly match reference")


if __name__ == "__main__":
    main()
