#!/usr/bin/env python3
"""Audit HERALD Phase 2B A10-guard regime results.

The decision is not "lowest WMAPE only".  Phase 2B checks whether the
learned-regime candidate can keep its recent-year gain while reducing the A10
degradation observed in Phase 2A.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from scipy.stats import wilcoxon
except Exception:  # pragma: no cover - cluster env should have scipy
    wilcoxon = None


EXPECTED_LABELS = {
    "ctrl",
    "candidate",
    "sec02",
    "sec03",
    "sec05",
    "secenh",
    "alpha005",
    "smooth003",
    "cp_sec02",
    "both_sec02",
}


def _read_runs(root: Path) -> pd.DataFrame:
    rows = []
    for path in sorted((root / "reports" / "per_run").glob("regime_*_seed_*.json")):
        metadata_path = root / "metadata" / path.name
        metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.exists() else {}
        payload = json.loads(path.read_text(encoding="utf-8"))
        for run_key, result in payload.items():
            label = metadata.get("experiment_label") or "base"
            rows.append({
                "run_key": run_key,
                "label": label,
                "seed": int(result["seed"]),
                "regime_mode": metadata.get("regime_mode", "unknown"),
                "variant": result.get("v7_variant", "unknown"),
                "source_policy": "with_source_flags" if metadata.get("source_flags_in_annual_features", True) else "no_source_flags",
                "mean_wmape": float(result["total_wmape_mean"]),
                "wmape_2025": float(result["total_wmape_2025"]),
                "sector_wmape_mean": float(result["sector_wmape_mean"]),
                "sector_lambda": float(result.get("sector_lambda", np.nan)),
                "smooth_lambda": float(result.get("smooth_lambda", np.nan)),
                "alpha_smooth_lambda": float(result.get("alpha_smooth_lambda", np.nan)),
                "path": str(path),
            })
    if not rows:
        raise SystemExit(f"No Phase 2B metrics found under {root}")
    return pd.DataFrame(rows)


def _paired_stats(df: pd.DataFrame, label: str, metric: str) -> dict:
    ctrl = df[df["label"] == "ctrl"].set_index("seed")[metric]
    cand = df[df["label"] == label].set_index("seed")[metric]
    seeds = sorted(set(ctrl.index) & set(cand.index))
    if not seeds:
        return {"wins": 0, "n": 0, "delta": np.nan, "p": np.nan}
    diff = cand.loc[seeds] - ctrl.loc[seeds]
    wins = int((diff < 0).sum())
    p_value = np.nan
    if wilcoxon is not None and len(seeds) > 1 and np.any(np.abs(diff.to_numpy()) > 0):
        p_value = float(wilcoxon(diff.to_numpy()).pvalue)
    return {
        "wins": wins,
        "n": len(seeds),
        "delta": float(diff.mean()),
        "p": p_value,
    }


def _fmt_p(p: float) -> str:
    return "NA" if not np.isfinite(p) else f"{p:.4f}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    df = _read_runs(args.root)
    out_dir = args.root / "reports" / "audit_phase2b_a10_guard"
    out_dir.mkdir(parents=True, exist_ok=True)

    labels = set(df["label"])
    seeds_by_label = df.groupby("label")["seed"].nunique().to_dict()
    missing_labels = sorted(EXPECTED_LABELS - labels)
    bad_seed_counts = {k: v for k, v in seeds_by_label.items() if v != 10}
    bad_source = df[df["source_policy"] != "no_source_flags"]

    if args.strict and (missing_labels or bad_seed_counts or not bad_source.empty):
        raise SystemExit(
            "Phase 2B strict audit failed: "
            f"missing_labels={missing_labels} bad_seed_counts={bad_seed_counts} "
            f"with_source_rows={len(bad_source)}"
        )

    summary = (df.groupby(["label", "regime_mode", "variant", "source_policy"])
               .agg(n=("seed", "count"),
                    mean_wmape=("mean_wmape", "mean"),
                    std_wmape=("mean_wmape", "std"),
                    wmape_2025=("wmape_2025", "mean"),
                    std_2025=("wmape_2025", "std"),
                    sector_wmape_mean=("sector_wmape_mean", "mean"),
                    std_sector=("sector_wmape_mean", "std"),
                    sector_lambda=("sector_lambda", "mean"),
                    smooth_lambda=("smooth_lambda", "mean"),
                    alpha_smooth_lambda=("alpha_smooth_lambda", "mean"))
               .reset_index())
    summary["pareto_rank_hint"] = (
        summary["mean_wmape"].rank(method="min")
        + summary["wmape_2025"].rank(method="min")
        + summary["sector_wmape_mean"].rank(method="min")
    )
    summary = summary.sort_values(["pareto_rank_hint", "mean_wmape"])

    paired_rows = []
    for label in sorted(labels - {"ctrl"}):
        row = {"label": label}
        for metric in ("mean_wmape", "wmape_2025", "sector_wmape_mean"):
            stats = _paired_stats(df, label, metric)
            row[f"{metric}_wins"] = f"{stats['wins']}/{stats['n']}"
            row[f"{metric}_delta"] = stats["delta"]
            row[f"{metric}_p"] = stats["p"]
        paired_rows.append(row)
    paired = pd.DataFrame(paired_rows).sort_values("mean_wmape_delta")

    summary.to_csv(out_dir / "phase2b_summary.csv", index=False)
    paired.to_csv(out_dir / "phase2b_paired_vs_ctrl.csv", index=False)
    df.to_csv(out_dir / "phase2b_runs.csv", index=False)

    lines = [
        "# HERALD Phase 2B A10 Guard Audit",
        "",
        "Decision rule: choose a candidate only if it preserves recent-year gain and does not degrade A10.",
        "",
        "## Integrity",
        "",
        f"- runs: {len(df)}",
        f"- labels found: {', '.join(sorted(labels))}",
        f"- missing labels: {missing_labels or 'none'}",
        f"- non no-source rows: {len(bad_source)}",
        "",
        "## Main Summary",
        "",
        "| Label | N | Mean WMAPE | 2025 WMAPE | A10 WMAPE | sector lambda | Pareto hint |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for r in summary.itertuples(index=False):
        lines.append(
            f"| {r.label} | {int(r.n)} | {r.mean_wmape:.6f} | {r.wmape_2025:.6f} | "
            f"{r.sector_wmape_mean:.5f} | {r.sector_lambda:.3f} | {r.pareto_rank_hint:.0f} |"
        )
    lines += [
        "",
        "## Paired vs ctrl",
        "",
        "| Label | Mean wins | Mean delta | p | 2025 wins | 2025 delta | p | A10 wins | A10 delta | p |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in paired.itertuples(index=False):
        lines.append(
            f"| {r.label} | {r.mean_wmape_wins} | {r.mean_wmape_delta:.6f} | {_fmt_p(r.mean_wmape_p)} | "
            f"{r.wmape_2025_wins} | {r.wmape_2025_delta:.6f} | {_fmt_p(r.wmape_2025_p)} | "
            f"{r.sector_wmape_mean_wins} | {r.sector_wmape_mean_delta:.6f} | {_fmt_p(r.sector_wmape_mean_p)} |"
        )
    lines += [
        "",
        "## Interpretation Guard",
        "",
        "- A lower mean WMAPE alone is insufficient.",
        "- A candidate that improves 2025 but worsens A10 remains experimental.",
        "- If `secenh` improves A10 without losing total WMAPE, it becomes the first candidate for the next full validation.",
    ]
    (out_dir / "PHASE2B_A10_GUARD_AUDIT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Saved audit under {out_dir}")
    print(summary[["label", "n", "mean_wmape", "wmape_2025", "sector_wmape_mean", "pareto_rank_hint"]].to_string(index=False))


if __name__ == "__main__":
    main()
