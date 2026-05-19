#!/usr/bin/env python3
"""Preflight audit for the HERALD regime discovery battery."""

import argparse
from pathlib import Path
from typing import List


PLANS = {
    "discovery": [
        ("manual_flags", "full", "with_source_flags"),
        ("no_regime", "full", "with_source_flags"),
        ("change_point", "full", "with_source_flags"),
        ("no_regime", "learned_regime_both", "with_source_flags"),
    ],
    "latent_gate_phase2a": [
        ("manual_flags", "full", "with_source_flags"),
        ("manual_flags", "full", "no_source_flags"),
        ("no_regime", "full", "with_source_flags"),
        ("no_regime", "full", "no_source_flags"),
        ("no_regime", "learned_regime_gate", "with_source_flags"),
        ("no_regime", "learned_regime_gate", "no_source_flags"),
        ("change_point", "learned_regime_gate", "with_source_flags"),
        ("change_point", "learned_regime_gate", "no_source_flags"),
    ],
    "phase2b_a10_guard": [
        ("manual_flags", "full", "no_source_flags", "ctrl"),
        ("no_regime", "learned_regime_gate", "no_source_flags", "candidate"),
        ("no_regime", "learned_regime_gate", "no_source_flags", "sec02"),
        ("no_regime", "learned_regime_gate", "no_source_flags", "sec03"),
        ("no_regime", "learned_regime_gate", "no_source_flags", "sec05"),
        ("no_regime", "learned_regime_gate_sector_enhanced", "no_source_flags", "secenh"),
        ("no_regime", "learned_regime_gate", "no_source_flags", "alpha005"),
        ("no_regime", "learned_regime_gate", "no_source_flags", "smooth003"),
        ("change_point", "learned_regime_gate", "no_source_flags", "cp_sec02"),
        ("no_regime", "learned_regime_both", "no_source_flags", "both_sec02"),
    ],
    "phase2c_critical": [
        ("manual_flags", "full", "no_source_flags", "ctrl_manual"),
        ("no_regime", "full", "no_source_flags", "ctrl_noregime"),
        ("no_regime", "learned_regime_gate_sector_enhanced", "no_source_flags", "cand_baseline"),
        ("no_regime", "learned_regime_gate_sector_enhanced", "no_source_flags", "cand_sym_smooth"),
        ("change_point", "learned_regime_gate_sector_enhanced", "no_source_flags", "falsify_regime_permute"),
        ("no_regime", "learned_regime_gate_sector_enhanced", "no_source_flags", "falsify_latent_inf_zero"),
        ("no_regime", "learned_regime_gate_sector_enhanced", "no_source_flags", "falsify_latent_frozen"),
        ("no_regime", "learned_regime_gate_sector_enhanced", "no_source_flags", "fold2021_probe"),
    ],
}


def artifact_paths(root: Path, seed: str, mode: str, variant: str, source_policy: str, label: str = "base") -> List[Path]:
    tag = f"regime_{mode}"
    if variant != "full":
        tag = f"{tag}_{variant}"
    if source_policy == "no_source_flags":
        tag = f"{tag}_no_source_flags"
    if label != "base":
        tag = f"{tag}_{label}"
    suffix = f"full_{tag}_seed_{seed}"
    return [
        root / "reports" / "per_run" / f"{tag}_seed_{seed}.json",
        root / "reports" / "per_run" / f"{tag}_seed_{seed}.md",
        root / "metadata" / f"{tag}_seed_{seed}.json",
        root / "data_processed" / f"herald_semi_v2_predictions_total_{suffix}_v1.csv",
        root / "data_processed" / f"herald_semi_v2_predictions_sector_{suffix}_v1.csv",
        root / "data_processed" / f"herald_semi_v2_internals_{suffix}_v1.npz",
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--seeds", required=True)
    parser.add_argument("--plan", choices=sorted(PLANS), default="discovery")
    parser.add_argument("--allow-existing", action="store_true")
    args = parser.parse_args()

    seeds = args.seeds.split()
    planned = []  # type: List[Path]
    for seed in seeds:
        for config in PLANS[args.plan]:
            mode, variant, source_policy, *rest = config
            label = rest[0] if rest else "base"
            planned.extend(artifact_paths(args.root, seed, mode, variant, source_policy, label))

    duplicates = sorted({p for p in planned if planned.count(p) > 1})
    existing = [p for p in planned if p.exists()]
    if duplicates:
        print("Duplicate planned artifact paths:")
        for p in duplicates:
            print(f"  {p}")
        raise SystemExit(1)
    if existing and not args.allow_existing:
        print("Existing artifacts would be overwritten:")
        for p in existing[:50]:
            print(f"  {p}")
        if len(existing) > 50:
            print(f"  ... {len(existing) - 50} more")
        raise SystemExit(1)

    print(f"Regime plan OK: plan={args.plan} seeds={len(seeds)} configs={len(PLANS[args.plan])} artifacts={len(planned)}")
    print(f"Root: {args.root}")


if __name__ == "__main__":
    main()
