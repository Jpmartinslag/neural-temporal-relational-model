#!/usr/bin/env python3
"""Prepare target-shuffle panels for leakage stress testing.

The test keeps all features unchanged and shuffles only the observed 2025 target
columns across zones. A model with no direct target leakage should produce the
same 2025 predictions as the original strict panel for the same seed/config;
only the reported y_true/WMAPE should change.
"""

import argparse
from pathlib import Path

import pandas as pd


TARGET_COLS = [
    "side_establishment_creations_official",
    "side_enterprise_creations_official",
]


def shuffle_2025_targets(src: Path, dst: Path, seed: int):
    df = pd.read_csv(src)
    mask = df["target_year"].astype(int) == 2025
    if mask.sum() == 0:
        raise SystemExit(f"No target_year=2025 in {src}")

    out = df.copy()
    for col in TARGET_COLS:
        if col not in out.columns:
            continue
        vals = out.loc[mask, col].sample(frac=1.0, random_state=seed).to_numpy()
        out.loc[mask, col] = vals

    # Sanity: features must be identical; targets must remain same aggregate.
    for col in TARGET_COLS:
        if col in out.columns:
            before = float(df.loc[mask, col].sum())
            after = float(out.loc[mask, col].sum())
            if abs(before - after) > 1e-6:
                raise SystemExit(f"Target sum changed for {col}: {before} vs {after}")

    dst.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(dst, index=False)
    print(f"saved {dst} rows={len(out)} shuffled_2025={int(mask.sum())}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict-dir", type=Path, default=Path("data/processed/strict_exante_20260506"))
    parser.add_argument("--out-dir", type=Path, default=Path("data/processed/leak_stress_20260507"))
    parser.add_argument("--seed", type=int, default=8675309)
    args = parser.parse_args()

    panels = [
        "dynamic_stgnn_feature_panel_strict_lag_only_through_2025_v1.csv",
        "dynamic_stgnn_feature_panel_strict_no_source_flags_through_2025_v1.csv",
    ]
    for name in panels:
        shuffle_2025_targets(args.strict_dir / name, args.out_dir / name, args.seed)

    split_src = args.strict_dir / "dynamic_stgnn_walk_forward_splits_strict_2024_2025_v1.csv"
    split_dst = args.out_dir / split_src.name
    split_dst.write_text(split_src.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"saved {split_dst}")


if __name__ == "__main__":
    main()
