#!/usr/bin/env python3
"""Audit strict ex-ante battery outputs."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path


SEEDS = [0, 1, 7, 13, 17, 42, 77, 99, 123, 2025]
PANELS = ["lag_only", "no_source_flags"]
TAGS = [
    "semiv2_graph_only",
    "semiv2_graph_only_nossl",
    "v7_graph_only",
    "v7_ridge_only",
    "v6_full",
    "v6_self_only",
]


def expected_paths(root: Path) -> list[Path]:
    paths = []
    for panel in PANELS:
        for seed in SEEDS:
            for tag in TAGS:
                paths.append(root / "reports/per_run" / f"strict_{panel}_{tag}_seed_{seed}.json")
    return paths


def load_single(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception as exc:
        print(f"WARN cannot read {path}: {exc}")
        return {}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, type=Path)
    args = parser.parse_args()

    exp = expected_paths(args.root)
    print(f"expected_json={len(exp)}")
    print(f"duplicate_expected_paths={sum(c > 1 for c in Counter(exp).values())}")
    missing = [p for p in exp if not p.exists()]
    print(f"missing_json={len(missing)}")
    for p in missing[:40]:
        print(f"  MISSING {p}")

    files = sorted((args.root / "reports/per_run").glob("strict_*.json"))
    print(f"actual_json={len(files)}")
    keys = []
    by_seed = defaultdict(int)
    for path in files:
        for key, value in load_single(path).items():
            keys.append(key)
            if isinstance(value, dict) and "seed" in value:
                by_seed[int(value["seed"])] += 1
    duplicate_keys = [k for k, c in Counter(keys).items() if c > 1]
    print(f"run_keys={len(keys)} duplicate_run_keys={len(duplicate_keys)}")
    for seed in SEEDS:
        print(f"seed_{seed}_runs={by_seed.get(seed, 0)}")

    if missing or duplicate_keys:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
