#!/usr/bin/env python3
"""Preflight audit for Phase 2I SIDE5 feature audit.

Prints the expected feature table for all 9 variants and validates constraints.
Run without arguments; set REGIME_PLAN env var if needed.

Fails (exit 1) if:
  - side5_full does not have exactly 5 features
  - any drop_* variant still contains the dropped feature
  - lags_only contains growth_1y or growth_2y
  - growth_only contains any side_lag
  - lag1_growth1y contains anything beyond side_lag_1 and growth_1y
  - any run_tag is duplicated
  - manual or source flags appear in expected annual features
"""

import sys

SIDE5_ALL = ["side_lag_1", "side_lag_2", "side_lag_3", "growth_1y", "growth_2y"]
SIDE5_ALL_SET = set(SIDE5_ALL)

MANUAL_FLAGS = {"is_covid_year", "is_post_covid_rebound"}
SOURCE_FLAGS = {"has_flores_source", "has_side_stock_source", "has_urssaf_source"}

# (label, feature_policy, expected_side5_features)
CONFIGS = [
    ("side5_full",    "side5_full",          ["side_lag_1", "side_lag_2", "side_lag_3", "growth_1y", "growth_2y"]),
    ("drop_lag1",     "side5_drop_lag1",     ["side_lag_2", "side_lag_3", "growth_1y", "growth_2y"]),
    ("drop_lag2",     "side5_drop_lag2",     ["side_lag_1", "side_lag_3", "growth_1y", "growth_2y"]),
    ("drop_lag3",     "side5_drop_lag3",     ["side_lag_1", "side_lag_2", "growth_1y", "growth_2y"]),
    ("drop_growth1y", "side5_drop_growth1y", ["side_lag_1", "side_lag_2", "side_lag_3", "growth_2y"]),
    ("drop_growth2y", "side5_drop_growth2y", ["side_lag_1", "side_lag_2", "side_lag_3", "growth_1y"]),
    ("lags_only",     "side5_lags_only",     ["side_lag_1", "side_lag_2", "side_lag_3"]),
    ("growth_only",   "side5_growth_only",   ["growth_1y", "growth_2y"]),
    ("lag1_growth1y", "side5_lag1_growth1y", ["side_lag_1", "growth_1y"]),
]

MODE = "no_regime"
VARIANT = "learned_regime_gate_sector_enhanced"
SOURCE_POLICY = "no_source_flags"


def expected_run_tag(label: str) -> str:
    tag = f"regime_{MODE}"
    if VARIANT != "full":
        tag = f"{tag}_{VARIANT}"
    if SOURCE_POLICY == "no_source_flags":
        tag = f"{tag}_no_source_flags"
    if label != "base":
        tag = f"{tag}_{label}"
    return tag


def main() -> None:
    errors = []

    col_label = 20
    col_policy = 25
    col_features = 55
    col_n = 3

    print("Phase 2I — SIDE5 feature audit — preflight")
    print("=" * 120)
    print(
        f"{'label':<{col_label}} {'feature_policy':<{col_policy}} "
        f"{'annual_features (SIDE5)':<{col_features}} {'n':<{col_n}} {'dropped':<35} run_tag"
    )
    print("-" * 120)

    seen_tags: dict = {}

    for label, policy, expected_features in CONFIGS:
        expected_set = set(expected_features)
        dropped = sorted(SIDE5_ALL_SET - expected_set)
        run_tag = expected_run_tag(label)

        print(
            f"{label:<{col_label}} {policy:<{col_policy}} "
            f"{', '.join(sorted(expected_set)):<{col_features}} {len(expected_set):<{col_n}} "
            f"{str(dropped):<35} {run_tag}"
        )

        # Manual and source flag checks
        if expected_set & MANUAL_FLAGS:
            errors.append(f"{label}: manual flags in features: {expected_set & MANUAL_FLAGS}")
        if expected_set & SOURCE_FLAGS:
            errors.append(f"{label}: source flags in features: {expected_set & SOURCE_FLAGS}")

        # Label-specific constraints
        if label == "side5_full":
            if len(expected_features) != 5:
                errors.append(f"side5_full: must have exactly 5 features, got {len(expected_features)}")
            if expected_set != SIDE5_ALL_SET:
                errors.append(f"side5_full: features must equal SIDE5_ALL, got {expected_set}")
        if label == "drop_lag1" and "side_lag_1" in expected_set:
            errors.append("drop_lag1: still contains side_lag_1")
        if label == "drop_lag2" and "side_lag_2" in expected_set:
            errors.append("drop_lag2: still contains side_lag_2")
        if label == "drop_lag3" and "side_lag_3" in expected_set:
            errors.append("drop_lag3: still contains side_lag_3")
        if label == "drop_growth1y" and "growth_1y" in expected_set:
            errors.append("drop_growth1y: still contains growth_1y")
        if label == "drop_growth2y" and "growth_2y" in expected_set:
            errors.append("drop_growth2y: still contains growth_2y")
        if label == "lags_only":
            if "growth_1y" in expected_set or "growth_2y" in expected_set:
                errors.append("lags_only: contains growth features")
        if label == "growth_only":
            lag_contamination = expected_set & {"side_lag_1", "side_lag_2", "side_lag_3"}
            if lag_contamination:
                errors.append(f"growth_only: contains lag features: {lag_contamination}")
        if label == "lag1_growth1y":
            if expected_set != {"side_lag_1", "growth_1y"}:
                errors.append(f"lag1_growth1y: must have exactly side_lag_1 and growth_1y, got {expected_set}")

        # Run tag uniqueness
        if run_tag in seen_tags:
            errors.append(f"duplicate run_tag: {run_tag} (labels: {seen_tags[run_tag]!r}, {label!r})")
        seen_tags[run_tag] = label

    print("-" * 120)
    print(f"Total configs: {len(CONFIGS)}")
    print()

    if errors:
        print("PREFLIGHT ERRORS:", file=sys.stderr)
        for e in errors:
            print(f"  ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    print("All constraints passed. Phase 2I preflight OK.")
    print()
    print("Expected run tags:")
    for label, _, _ in CONFIGS:
        print(f"  {expected_run_tag(label)}")


if __name__ == "__main__":
    main()
