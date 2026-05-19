#!/usr/bin/env python3
"""Aggregate HERALD regime discovery per-run metrics."""

import argparse
import json
from pathlib import Path

import pandas as pd


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()

    per_run = args.root / "reports" / "per_run"
    rows = []
    for path in sorted(per_run.glob("regime_*_seed_*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        meta_path = args.root / "metadata" / path.name
        metadata = {}
        if meta_path.exists():
            metadata = json.loads(meta_path.read_text(encoding="utf-8"))
        for run_key, result in payload.items():
            tag = str(result.get("run_tag", ""))
            regime_mode = tag.replace("regime_", "", 1) if tag.startswith("regime_") else "unknown"
            source_policy = "with_source_flags"
            experiment_label = str(metadata.get("experiment_label") or "base")
            if metadata:
                regime_mode = str(metadata.get("regime_mode", regime_mode))
                source_policy = "with_source_flags" if metadata.get("source_flags_in_annual_features", True) else "no_source_flags"
            elif "_no_source_flags" in regime_mode:
                regime_mode = regime_mode.replace("_no_source_flags", "")
                source_policy = "no_source_flags"
            learned_variant = str(result.get("v7_variant") or "none")
            if learned_variant == "full":
                learned_variant = "none"
            rows.append({
                "run_key": run_key,
                "regime_mode": regime_mode,
                "learned_variant": learned_variant,
                "experiment_label": experiment_label,
                "source_policy": source_policy,
                "seed": result.get("seed"),
                "mean_wmape": result.get("total_wmape_mean"),
                "wmape_2025": result.get("total_wmape_2025"),
                "sector_wmape_mean": result.get("sector_wmape_mean"),
                "sector_lambda": result.get("sector_lambda"),
                "smooth_lambda": result.get("smooth_lambda"),
                "alpha_smooth_lambda": result.get("alpha_smooth_lambda"),
                "gamma_geo": result.get("gamma_geo"),
                "gamma_mob": result.get("gamma_mob"),
                "alpha_2025": (result.get("alpha_by_year") or {}).get("2025")
                    or (result.get("alpha_by_year") or {}).get(2025),
                "path": str(path),
            })
    if not rows:
        raise SystemExit(f"No regime metrics found under {per_run}")

    df = pd.DataFrame(rows)
    out_csv = args.root / "reports" / "herald_regime_discovery_runs.csv"
    out_summary = args.root / "reports" / "herald_regime_discovery_summary.csv"
    out_md = args.root / "reports" / "HERALD_REGIME_DISCOVERY_SUMMARY.md"
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_csv, index=False)

    summary = (df.groupby(["regime_mode", "learned_variant", "experiment_label", "source_policy"])
               .agg(n=("seed", "count"),
                    mean_wmape=("mean_wmape", "mean"),
                    std_wmape=("mean_wmape", "std"),
                    wmape_2025=("wmape_2025", "mean"),
                    sector_wmape_mean=("sector_wmape_mean", "mean"),
                    sector_lambda=("sector_lambda", "mean"),
                    smooth_lambda=("smooth_lambda", "mean"),
                    alpha_smooth_lambda=("alpha_smooth_lambda", "mean"),
                    gamma_geo=("gamma_geo", "mean"),
                    gamma_mob=("gamma_mob", "mean"),
                    alpha_2025=("alpha_2025", "mean"))
               .reset_index()
               .sort_values("mean_wmape"))
    summary.to_csv(out_summary, index=False)

    lines = [
        "# HERALD Regime Discovery Summary",
        "",
        "Experimental battery: manual regime flags vs latent/inferred regimes.",
        "",
        "| Regime mode | Variant | Label | Source flags | N | Mean WMAPE | Std | 2025 WMAPE | A10 WMAPE | sector λ | alpha smooth | graph smooth | gamma_mob/gamma_geo | alpha 2025 |",
        "|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary.itertuples(index=False):
        ratio = row.gamma_mob / row.gamma_geo if row.gamma_geo and row.gamma_geo != 0 else float("nan")
        lines.append(
            f"| {row.regime_mode} | {row.learned_variant} | {row.experiment_label} | {row.source_policy} | {int(row.n)} | {row.mean_wmape:.6f} | "
            f"{row.std_wmape if pd.notna(row.std_wmape) else 0.0:.6f} | "
            f"{row.wmape_2025:.6f} | {row.sector_wmape_mean:.5f} | "
            f"{row.sector_lambda if pd.notna(row.sector_lambda) else 0.0:.3f} | "
            f"{row.alpha_smooth_lambda if pd.notna(row.alpha_smooth_lambda) else 0.0:.4f} | "
            f"{row.smooth_lambda if pd.notna(row.smooth_lambda) else 0.0:.4f} | "
            f"{ratio:.3f} | {row.alpha_2025:.5f} |"
        )
    lines += [
        "",
        "Interpretation rule:",
        "",
        "- `manual_flags` is the current researcher-labelled control.",
        "- Any non-manual mode that matches or beats `manual_flags` supports the claim that HERALD can infer crisis regimes without explicit COVID/rebound labels.",
        "- If `no_regime` is equivalent to all regime modes, the regime mechanism is not empirically necessary.",
        "- `learned_regime_*` rows are the strongest test: HERALD creates a latent regime internally without manual flags.",
    ]
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Saved: {out_csv}")
    print(f"Saved: {out_summary}")
    print(f"Saved: {out_md}")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
