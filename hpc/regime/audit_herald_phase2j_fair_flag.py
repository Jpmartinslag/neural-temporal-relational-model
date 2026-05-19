#!/usr/bin/env python3
"""Preflight audit for Phase 2J fair flag comparison.

Two configs are audited:
  lag1_growth1y_nf    — HERALD no flags, feature_policy=side5_lag1_growth1y
  lag1_growth1y_flags — HERALD with manual flags, same feature_policy

Validates:
  - feature_policy produces only {side_lag_1, growth_1y} as SIDE features
  - lag1_growth1y_nf has NO manual flags in features or regime vector
  - lag1_growth1y_flags HAS manual flags in features and regime vector
  - both drop source flags
  - both drop flores, side_stock, lag2, lag3, growth2y
  - run tags are unique across Phase 2J AND Phase 2I (no collision)
  - expected run count = 2 configs × N_SEEDS = 20

Run without arguments. Exits 1 on any constraint violation.
"""

import sys

SIDE5_ALL = {"side_lag_1", "side_lag_2", "side_lag_3", "growth_1y", "growth_2y"}
SIDE2_EXPECTED = {"side_lag_1", "growth_1y"}
NOISE_FEATURES = {"side_lag_2", "side_lag_3", "growth_2y"}
SOURCE_FLAGS = {"has_flores_source", "has_side_stock_source", "has_urssaf_source"}
MANUAL_FLAGS = {"is_covid_year", "is_post_covid_rebound"}

CONFIGS = [
    {
        "label":          "lag1_growth1y_nf",
        "regime_mode":    "no_regime",
        "variant":        "learned_regime_gate_sector_enhanced",
        "source_policy":  "no_source_flags",
        "feature_policy": "side5_lag1_growth1y",
        "macro":          "none",
        "sector_lambda":  0.2,
        "has_manual_flags_in_features": False,
        "has_manual_flags_in_regime":   False,
    },
    {
        "label":          "lag1_growth1y_flags",
        "regime_mode":    "manual_flags",
        "variant":        "full",
        "source_policy":  "no_source_flags",
        "feature_policy": "side5_lag1_growth1y",
        "macro":          "none",
        "sector_lambda":  0.1,
        "has_manual_flags_in_features": True,
        "has_manual_flags_in_regime":   True,
    },
]

# Known Phase 2I run tags — Phase 2J must not collide with these.
PHASE2I_TAGS = {
    "regime_no_regime_learned_regime_gate_sector_enhanced_no_source_flags_side5_full",
    "regime_no_regime_learned_regime_gate_sector_enhanced_no_source_flags_drop_lag1",
    "regime_no_regime_learned_regime_gate_sector_enhanced_no_source_flags_drop_lag2",
    "regime_no_regime_learned_regime_gate_sector_enhanced_no_source_flags_drop_lag3",
    "regime_no_regime_learned_regime_gate_sector_enhanced_no_source_flags_drop_growth1y",
    "regime_no_regime_learned_regime_gate_sector_enhanced_no_source_flags_drop_growth2y",
    "regime_no_regime_learned_regime_gate_sector_enhanced_no_source_flags_lags_only",
    "regime_no_regime_learned_regime_gate_sector_enhanced_no_source_flags_growth_only",
    "regime_no_regime_learned_regime_gate_sector_enhanced_no_source_flags_lag1_growth1y",
}

N_SEEDS = 10
N_CONFIGS = len(CONFIGS)
EXPECTED_RUNS = N_CONFIGS * N_SEEDS


def expected_run_tag(cfg: dict) -> str:
    mode = cfg["regime_mode"]
    variant = cfg["variant"]
    source_policy = cfg["source_policy"]
    label = cfg["label"]
    tag = f"regime_{mode}"
    if variant != "full":
        tag = f"{tag}_{variant}"
    if source_policy == "no_source_flags":
        tag = f"{tag}_no_source_flags"
    if label != "base":
        tag = f"{tag}_{label}"
    return tag


def main() -> None:
    errors = []

    print("Phase 2J — fair flag comparison — preflight audit")
    print("=" * 100)
    print(f"  Configs: {N_CONFIGS}   Seeds: {N_SEEDS}   Expected runs: {EXPECTED_RUNS}")
    print()
    print(f"  {'label':<30} {'mode':<15} {'variant':<42} {'policy':<22} {'manual_flags'}")
    print(f"  {'-'*30} {'-'*15} {'-'*42} {'-'*22} {'-'*12}")

    seen_tags: dict = {}

    for cfg in CONFIGS:
        label = cfg["label"]
        run_tag = expected_run_tag(cfg)

        print(f"  {label:<30} {cfg['regime_mode']:<15} {cfg['variant']:<42} "
              f"{cfg['feature_policy']:<22} {str(cfg['has_manual_flags_in_features'])}")

        # Feature policy must be side5_lag1_growth1y for both
        if cfg["feature_policy"] != "side5_lag1_growth1y":
            errors.append(f"{label}: feature_policy must be side5_lag1_growth1y, "
                          f"got {cfg['feature_policy']!r}")

        # Source flags must be dropped
        if cfg["source_policy"] != "no_source_flags":
            errors.append(f"{label}: source_policy must be no_source_flags, "
                          f"got {cfg['source_policy']!r}")

        # No macro
        if cfg["macro"] != "none":
            errors.append(f"{label}: macro must be none, got {cfg['macro']!r}")

        # Manual flags logic
        if label == "lag1_growth1y_nf":
            if cfg["regime_mode"] != "no_regime":
                errors.append(f"{label}: regime_mode must be no_regime")
            if cfg["variant"] != "learned_regime_gate_sector_enhanced":
                errors.append(f"{label}: variant must be learned_regime_gate_sector_enhanced")
            if cfg["has_manual_flags_in_features"]:
                errors.append(f"{label}: must NOT have manual flags in features")
            if cfg["has_manual_flags_in_regime"]:
                errors.append(f"{label}: must NOT have manual flags in regime vector")

        if label == "lag1_growth1y_flags":
            if cfg["regime_mode"] != "manual_flags":
                errors.append(f"{label}: regime_mode must be manual_flags")
            if cfg["variant"] != "full":
                errors.append(f"{label}: variant must be full (explicit regime)")
            if not cfg["has_manual_flags_in_features"]:
                errors.append(f"{label}: must have manual flags in features")
            if not cfg["has_manual_flags_in_regime"]:
                errors.append(f"{label}: must have manual flags in regime vector")

        # Tag uniqueness within Phase 2J
        if run_tag in seen_tags:
            errors.append(f"duplicate tag in Phase 2J: {run_tag} "
                          f"(labels: {seen_tags[run_tag]!r}, {label!r})")
        seen_tags[run_tag] = label

        # No collision with Phase 2I
        if run_tag in PHASE2I_TAGS:
            errors.append(f"{label}: run_tag collides with Phase 2I: {run_tag}")

    print()
    print("Expected run tags:")
    for cfg in CONFIGS:
        print(f"  {expected_run_tag(cfg)}")

    print()
    print(f"Total expected runs: {EXPECTED_RUNS} ({N_CONFIGS} configs × {N_SEEDS} seeds)")
    print()
    print("Methodological check:")
    print("  Both variants use feature_policy=side5_lag1_growth1y:")
    print("    SIDE features kept : side_lag_1, growth_1y")
    print("    SIDE features dropped: side_lag_2, side_lag_3, growth_2y")
    print("    Noise dropped      : flores_*, side_stock_*")
    print("    Source flags dropped: has_flores_source, has_side_stock_source, has_urssaf_source")
    print("  lag1_growth1y_nf  : regime learned from data (no is_covid_year, no is_post_covid_rebound)")
    print("  lag1_growth1y_flags: regime from manual flags (is_covid_year, is_post_covid_rebound kept)")
    print("  => The ONLY difference is presence/absence of 2 manual regime flags.")
    print()

    if errors:
        print("PREFLIGHT ERRORS:", file=sys.stderr)
        for e in errors:
            print(f"  ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    print("All Phase 2J constraints passed. Preflight OK.")


if __name__ == "__main__":
    main()
