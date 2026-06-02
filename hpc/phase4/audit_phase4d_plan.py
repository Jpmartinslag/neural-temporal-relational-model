#!/usr/bin/env python3
"""Phase 4D pre-launch audit.

Validates all graphs, configs, and scripts before HPC submission.
Run via submit scripts (--quiet) or directly for full report.

Usage:
    python3 hpc/phase4/audit_phase4d_plan.py
    python3 hpc/phase4/audit_phase4d_plan.py --country nl
    python3 hpc/phase4/audit_phase4d_plan.py --country nl --quiet
"""
import argparse
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent.parent.parent

PASS = "\033[92m✓\033[0m"
FAIL = "\033[91m✗\033[0m"

errors = []   # type: List[str]
warnings = [] # type: List[str]


def ok(msg: str, quiet: bool = False) -> None:
    if not quiet:
        print(f"  {PASS} {msg}")


def fail(msg: str) -> None:
    print(f"  {FAIL} {msg}")
    errors.append(msg)


def warn(msg: str) -> None:
    print(f"  ⚠  {msg}")
    warnings.append(msg)


def check_adj(path: Path, country: str, n_zones: int,
              label: str, expected_k: int = 0, quiet: bool = False) -> None:
    """Validate an adjacency CSV: shape, row sums, NaN, non-negative, top-k count."""
    if not path.exists():
        fail(f"{label}: MISSING {path}")
        return

    df = pd.read_csv(path)
    mat = df.drop("source_idx", axis=1).values.astype(float)
    N = mat.shape[0]

    if df.shape != (n_zones, n_zones + 1):
        fail(f"{label}: wrong shape {df.shape}, expected ({n_zones}, {n_zones+1})")
        return

    if not np.allclose(mat.sum(axis=1), 1.0, atol=1e-4):
        rs = mat.sum(axis=1)
        fail(f"{label}: row sums not ~1 [{rs.min():.5f},{rs.max():.5f}]")
        return

    if np.isnan(mat).any():
        fail(f"{label}: contains NaN")
        return

    if mat.min() < 0:
        fail(f"{label}: contains negative values")
        return

    diag = np.diag(mat)
    off = (mat > 0).sum(axis=1) - (diag > 0).astype(int)
    density = float((mat > 0).sum() - N) / (N * (N - 1))

    if expected_k > 0:
        actual_k = int(off.mean())
        if actual_k != expected_k:
            fail(f"{label}: expected top-k={expected_k}, got avg_off_neighbors={actual_k:.1f}")
            return

    ok(f"{label}: {N}×{N} density={density:.3f} diag_mean={diag.mean():.3f} "
       f"avg_off={off.mean():.1f}", quiet)


def check_permuted_not_identical(real_path: Path, perm_path: Path, label: str,
                                 quiet: bool = False) -> None:
    if not real_path.exists() or not perm_path.exists():
        return  # already caught by check_adj
    real = pd.read_csv(real_path).drop("source_idx", axis=1).values
    perm = pd.read_csv(perm_path).drop("source_idx", axis=1).values
    if np.allclose(real, perm):
        fail(f"{label}: permuted IS identical to real — no signal test possible")
    else:
        ok(f"{label}: permuted ≠ real (max_diff={np.abs(real-perm).max():.4f})", quiet)


def check_shell(script: Path, quiet: bool = False) -> None:
    r = subprocess.run(["bash", "-n", str(script)], capture_output=True)
    if r.returncode != 0:
        fail(f"bash -n {script.name}: {r.stderr.decode().strip()}")
    else:
        ok(f"bash -n {script.name}: OK", quiet)


def check_py_compile(script: Path, quiet: bool = False) -> None:
    r = subprocess.run([sys.executable, "-m", "py_compile", str(script)],
                       capture_output=True)
    if r.returncode != 0:
        fail(f"py_compile {script.name}: {r.stderr.decode().strip()}")
    else:
        ok(f"py_compile {script.name}: OK", quiet)


def get_configs(country):
    # type: (str) -> List[Tuple[str, str, str, str]]
    r = subprocess.run(
        ["bash", "-c",
         f"source hpc/phase4/phase4d_configs.sh && phase4d_configs"],
        capture_output=True, text=True, cwd=str(BASE),
        env={**__import__("os").environ, "COUNTRY": country},
    )
    configs = []
    for line in r.stdout.strip().splitlines():
        parts = line.split()
        if len(parts) >= 4:
            configs.append((parts[0], parts[1], parts[2], parts[3]))
    return configs


def audit_country(country: str, n_zones: int, quiet: bool = False) -> None:
    print(f"\n{'='*60}")
    print(f" [{country.upper()}]  ({n_zones} zones)")
    print(f"{'='*60}")

    p4 = BASE / "data/processed/phase4" / country
    p4d = BASE / "data/processed/phase4d" / country

    # ── Panel files ───────────────────────────────────────────────────────────
    print("\n  Panel files:")
    for f in ["panel_ze2020.csv", "splits.csv", "a10_ze2020.csv"]:
        if (p4 / f).exists():
            ok(f"{f}: exists", quiet)
        else:
            fail(f"{f}: MISSING")

    # Phase 4C columns in panel
    panel_path = p4 / "panel_ze2020.csv"
    if panel_path.exists():
        p = pd.read_csv(panel_path)
        missing_cols = [c for c in ["side_lag_2", "side_lag_3", "growth_2y"]
                        if c not in p.columns]
        if missing_cols:
            fail(f"Phase 4C columns missing: {missing_cols}")
        else:
            ok(f"Phase 4C columns present (side_lag_2 non-null: {p['side_lag_2'].notna().sum()}/{len(p)})", quiet)

    # ── Adjacency matrices ────────────────────────────────────────────────────
    print("\n  Adjacency matrices:")

    # Default adj_geo (Phase 4C real contiguity)
    check_adj(p4 / "adj_geo.csv", country, n_zones, "adj_geo (Phase 4C)", quiet=quiet)
    check_adj(p4 / "adj_mob.csv", country, n_zones, "adj_mob", quiet=quiet)

    # Phase 4D matrices
    check_adj(p4d / "adj_identity.csv", country, n_zones, "adj_identity (best_4a ctrl)", quiet=quiet)
    check_adj(p4d / "adj_sector_similarity.csv", country, n_zones, "adj_sector_sim (dense)", quiet=quiet)
    check_adj(p4d / "adj_sector_similarity_top5.csv", country, n_zones,
              "adj_sector_sim_top5", expected_k=5, quiet=quiet)
    check_adj(p4d / "adj_sector_similarity_top8.csv", country, n_zones,
              "adj_sector_sim_top8", expected_k=8, quiet=quiet)
    check_adj(p4d / "adj_sector_similarity_top5_perm.csv", country, n_zones,
              "adj_sector_sim_top5_perm", expected_k=5, quiet=quiet)
    check_permuted_not_identical(
        p4d / "adj_sector_similarity_top5.csv",
        p4d / "adj_sector_similarity_top5_perm.csv",
        "sector_sim_top5_perm", quiet=quiet,
    )

    if country in ("nl", "be"):
        check_adj(p4d / "adj_commuting.csv", country, n_zones, "adj_commuting (dense)", quiet=quiet)
        check_adj(p4d / "adj_commuting_top5.csv", country, n_zones,
                  "adj_commuting_top5", expected_k=5, quiet=quiet)
        check_adj(p4d / "adj_commuting_top8.csv", country, n_zones,
                  "adj_commuting_top8", expected_k=8, quiet=quiet)
        check_adj(p4d / "adj_commuting_top5_perm.csv", country, n_zones,
                  "adj_commuting_top5_perm", expected_k=5, quiet=quiet)
        check_permuted_not_identical(
            p4d / "adj_commuting_top5.csv",
            p4d / "adj_commuting_top5_perm.csv",
            "commuting_top5_perm", quiet=quiet,
        )

    # ── Configs ───────────────────────────────────────────────────────────────
    print("\n  Configs:")
    configs = get_configs(country)
    expected_n = 10 if country in ("nl", "be") else 7
    if len(configs) != expected_n:
        fail(f"Expected {expected_n} configs, got {len(configs)}")
    else:
        ok(f"{len(configs)} configs loaded", quiet)

    for label, feat, qtensor, graph_file in configs:
        # Check PT does not use effectifs_lag1 as a Q7 substitute label
        if country == "pt" and qtensor == "effectifs_lag1":
            ok(f"  {label}: qtensor=effectifs_lag1 (births proxy, OK)", quiet)
        # Check graph file exists (unless geo_default)
        if graph_file != "geo_default":
            gpath = BASE / graph_file
            if not gpath.exists():
                fail(f"  {label}: graph_file not found: {graph_file}")
            else:
                ok(f"  {label}: feat={feat} qtensor={qtensor} graph={Path(graph_file).name}", quiet)
        else:
            ok(f"  {label}: feat={feat} qtensor={qtensor} graph=geo_default", quiet)

    # ── Tensor sources ────────────────────────────────────────────────────────
    print("\n  Tensor source check:")
    if country in ("nl", "be"):
        qtensor_files = {
            "nl": BASE / "data/external/netherlands/processed/netherlands_qtensor_jobs_panel.csv",
            "be": BASE / "data/external/belgium/processed/belgium_qtensor_jobs_panel.csv",
        }
        f = qtensor_files[country]
        if f.exists():
            ok(f"Q7 effectifs tensor: {f.name}", quiet)
        else:
            fail(f"Q7 effectifs tensor MISSING: {f}")
    elif country == "pt":
        f = BASE / "data/external/portugal/processed/portugal_qtensor_births_cae_nuts3.csv"
        if f.exists():
            ok(f"PT births proxy tensor: {f.name} (⚠ proxy, NOT Q7)", quiet)
            warn("PT tensor is births proxy — label as proxy in all results")
        else:
            fail(f"PT births tensor MISSING: {f}")


def audit_scripts(quiet: bool = False) -> None:
    print(f"\n{'='*60}")
    print(f" Scripts")
    print(f"{'='*60}")
    scripts_sh = [
        BASE / "hpc/phase4/run_herald_phase4d_seed.sh",
        BASE / "hpc/phase4/phase4d_configs.sh",
        BASE / "hpc/phase4/run_herald_phase4d_array.sbatch",
        BASE / "hpc/phase4/submit_herald_phase4d_nl.sh",
        BASE / "hpc/phase4/submit_herald_phase4d_be.sh",
        BASE / "hpc/phase4/submit_herald_phase4d_pt.sh",
    ]
    scripts_py = [
        BASE / "hpc/phase4/run_herald_phase4_wrapper.py",
        BASE / "hpc/phase4/audit_phase4d_plan.py",
        BASE / "data/external/build_phase4d_commuting_graph.py",
        BASE / "data/external/build_phase4d_sector_similarity.py",
    ]
    print()
    for s in scripts_sh:
        if not s.exists():
            fail(f"{s.name}: MISSING")
        else:
            check_shell(s, quiet)
    for s in scripts_py:
        if not s.exists():
            fail(f"{s.name}: MISSING")
        else:
            check_py_compile(s, quiet)


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 4D pre-launch audit")
    parser.add_argument("--country", choices=["nl", "be", "pt", "all"], default="all")
    parser.add_argument("--quiet", action="store_true",
                        help="Suppress OK lines (only show failures and summary)")
    args = parser.parse_args()

    countries = {"nl": 40, "be": 42, "pt": 25}
    targets = countries if args.country == "all" else {args.country: countries[args.country]}

    print("HERALD Phase 4D — Pre-launch audit")
    print(f"Base: {BASE}")

    for c, n in targets.items():
        audit_country(c, n, quiet=args.quiet)

    if args.country == "all":
        audit_scripts(quiet=args.quiet)

    print(f"\n{'='*60}")
    if errors:
        print(f"  BLOCKED — {len(errors)} error(s):")
        for e in errors:
            print(f"    {FAIL} {e}")
        sys.exit(1)
    elif warnings:
        print(f"  PASS with {len(warnings)} warning(s):")
        for w in warnings:
            print(f"    ⚠  {w}")
        print("  Ready to launch (check warnings first).")
    else:
        print("  ALL CHECKS PASSED — pronto para lançar.")


if __name__ == "__main__":
    main()
