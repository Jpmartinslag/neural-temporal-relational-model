#!/usr/bin/env python3
"""Audit the HERALD Semi V2 validation battery before/after launch."""

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path


SEEDS_DEFAULT = "0 1 7 13 17 42 77 99 123 2025"

V6 = [
    "full_h64_gate2",
    "self_only_h64_gate2",
    "fixed_geo_mob_h64_gate2",
    "static_adaptive_h64_gate2",
    "no_regime_graph_h64_gate2",
    "no_sector_head_h64_gate2",
    "no_quarterly_h64_gate2",
]
V7 = [
    "full",
    "fixed_alpha_0.5",
    "fixed_graph",
    "ridge_only",
    "graph_only",
    "sector_enhanced",
    "sector_lag1_only",
]
SEMIV2 = [
    "full_f0.10_s0.30_r0.02",
    "masked_variables_f0.10",
    "sector_denoise_s0.30",
    "ranking_aux_r0.02",
    "temporal_regime",
    "full_f0.00_s0.30_r0.02",
    "full_f0.10_s0.00_r0.02",
    "full_f0.10_s0.30_r0.00",
    "full_f0.00_s0.00_r0.00",
    "full_fixed_graph_f0.10_s0.30_r0.02",
    "full_graph_only_f0.10_s0.30_r0.02",
    "full_ridge_only_f0.10_s0.30_r0.02",
]


def expected_json_paths(root, seeds):
    out = []
    for seed in seeds:
        out.extend(root / "reports/per_run" / f"v6ctrl_{tag}_seed_{seed}.json" for tag in V6)
        out.extend(root / "reports/per_run" / f"v7_{tag}_seed_{seed}.json" for tag in V7)
        out.extend(root / "reports/per_run" / f"semiv2_{tag}_seed_{seed}.json" for tag in SEMIV2)
    out.append(root / "reports/per_run/sector_baselines_seed_0.json")
    return out


def audit_expected(root, seeds):
    expected = expected_json_paths(root, seeds)
    dup = [p for p, c in Counter(expected).items() if c > 1]
    print(f"seeds={seeds}")
    print(f"expected_per_run_json={len(expected)}")
    print(f"duplicate_expected_paths={len(dup)}")
    if dup:
        for p in dup[:20]:
            print(f"  DUP {p}")
        return 1
    print("expected_paths_unique=OK")
    print("expected_by_family:")
    print(f"  V6      {len(seeds) * len(V6)}")
    print(f"  V7      {len(seeds) * len(V7)}")
    print(f"  SemiV2  {len(seeds) * len(SEMIV2)}")
    print("  Sector  1")
    print("temporal/STGNN outputs are stored outside reports/per_run by their own scripts.")
    return 0


def load_single(path):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"WARN cannot read {path}: {exc}")
        return {}
    return data if isinstance(data, dict) else {}


def audit_results(root, seeds):
    rc = audit_expected(root, seeds)
    per_run = root / "reports/per_run"
    if not per_run.exists():
        print(f"results_missing={per_run}")
        return rc

    files = sorted(per_run.glob("*.json"))
    print(f"actual_per_run_json={len(files)}")
    missing = [p for p in expected_json_paths(root, seeds) if not p.exists()]
    print(f"missing_expected_json={len(missing)}")
    for p in missing[:30]:
        print(f"  MISSING {p}")

    run_keys = []
    by_seed = defaultdict(int)
    for path in files:
        data = load_single(path)
        for key, val in data.items():
            run_keys.append(key)
            if isinstance(val, dict) and "seed" in val:
                by_seed[str(val["seed"])] += 1
    dup_keys = [k for k, c in Counter(run_keys).items() if c > 1]
    print(f"run_keys={len(run_keys)} duplicate_run_keys={len(dup_keys)}")
    for key in dup_keys[:20]:
        print(f"  DUP_KEY {key}")
    print("runs_by_seed:")
    for seed in seeds:
        print(f"  {seed}: {by_seed.get(seed, 0)}")

    if missing or dup_keys:
        return 1
    return rc


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--seeds", default=SEEDS_DEFAULT)
    parser.add_argument("--mode", choices=["expected", "results"], default="expected")
    args = parser.parse_args()
    seeds = args.seeds.split()
    if len(seeds) != len(set(seeds)):
        raise SystemExit("Duplicate seeds in --seeds")
    if args.mode == "expected":
        raise SystemExit(audit_expected(args.root, seeds))
    raise SystemExit(audit_results(args.root, seeds))


if __name__ == "__main__":
    main()
