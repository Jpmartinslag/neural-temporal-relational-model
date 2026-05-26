#!/usr/bin/env python3
"""Audit HERALD Phase 2R confirmatory results."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from scipy.stats import wilcoxon
except Exception:  # pragma: no cover - optional on HPC
    wilcoxon = None


EXPECTED_LABELS = {
    "ridge_side2",
    "L3_gate",
    "L5_gate_no_auditor",
    "L5_trainopt",
    "HC5_trainopt",
    "AUD_alpha_trainopt",
    "AUD_both_trainopt",
    "L4_a10g",
    "side2_AUDboth",
    "clean_flags_side2",
    "clean_flags_side2_trainopt",
    "extended_flags_current",
    "extended_flags_current_trainopt",
}

PRIMARY_REF = "L5_gate_no_auditor"
PRIMARY_CANDIDATE = "L5_trainopt"
YEARS = [2021, 2022, 2023, 2024, 2025]


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _payload_result(path: Path) -> dict:
    payload = _read_json(path)
    if len(payload) != 1:
        raise ValueError(f"{path}: expected one run payload, got {len(payload)}")
    return next(iter(payload.values()))


def _label_from_meta(meta: dict, result: dict, path: Path) -> str:
    label = meta.get("experiment_label")
    if label:
        return str(label)
    tag = str(result.get("run_tag", path.stem))
    for known in sorted(EXPECTED_LABELS, key=len, reverse=True):
        if known in tag:
            return known
    return tag


def collect(root: Path) -> pd.DataFrame:
    rows = []
    per_run = root / "reports" / "per_run"
    metadata_dir = root / "metadata"
    for path in sorted(per_run.glob("regime_*_seed_*.json")):
        result = _payload_result(path)
        meta_path = metadata_dir / path.name
        meta = _read_json(meta_path) if meta_path.exists() else {}
        label = _label_from_meta(meta, result, path)
        row = {
            "label": label,
            "seed": int(result.get("seed")),
            "run_tag": result.get("run_tag"),
            "regime_mode": meta.get("regime_mode"),
            "v7_variant": result.get("v7_variant"),
            "feature_policy": meta.get("feature_policy"),
            "source_flags": bool(meta.get("source_flags_in_annual_features", True)),
            "manual_flags_features": bool(meta.get("manual_flags_in_annual_features", False)),
            "manual_flags_regime": bool(meta.get("manual_flags_in_regime_vector", False)),
            "mean_wmape": float(result.get("total_wmape_mean", math.nan)),
            "wmape_2025": float(result.get("total_wmape_2025", math.nan)),
            "sector_wmape_mean": float(result.get("sector_wmape_mean", math.nan)),
            "residual_shrinkage_mode": result.get("residual_shrinkage_mode", "none"),
            "auditor_mode": result.get("auditor_mode", "none"),
            "auditor_confidence_mean": float(result.get("auditor_confidence_mean", math.nan)),
            "auditor_variance": float(result.get("auditor_variance", math.nan)),
            "path": str(path),
        }
        per_year = result.get("per_year_total") or {}
        for year in YEARS:
            row[f"wmape_{year}"] = float(per_year.get(str(year), per_year.get(year, math.nan)))
        shrink_by_fold = result.get("residual_shrinkage_by_fold") or {}
        for year in YEARS:
            row[f"shrink_{year}"] = float(shrink_by_fold.get(str(year), shrink_by_fold.get(year, math.nan)))
        sector = result.get("sector_wmape") or {}
        for sec, val in sector.items():
            row[f"sector_{sec}"] = float(val)
        rows.append(row)
    return pd.DataFrame(rows)


def wilcoxon_p(delta: pd.Series) -> float:
    delta = delta.dropna()
    if len(delta) == 0 or np.allclose(delta.to_numpy(), 0.0):
        return math.nan
    if wilcoxon is None:
        return math.nan
    try:
        return float(wilcoxon(delta.to_numpy(), alternative="two-sided", zero_method="wilcox").pvalue)
    except Exception:
        return math.nan


def bootstrap_ci(delta: pd.Series, n_boot: int = 20000, seed: int = 123) -> tuple[float, float]:
    vals = delta.dropna().to_numpy(dtype=float)
    if len(vals) == 0:
        return math.nan, math.nan
    rng = np.random.default_rng(seed)
    draws = rng.choice(vals, size=(n_boot, len(vals)), replace=True).mean(axis=1)
    return tuple(np.quantile(draws, [0.025, 0.975]).tolist())


def summary_tables(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    metric_cols = ["mean_wmape", "wmape_2021", "wmape_2022", "wmape_2023", "wmape_2024", "wmape_2025", "sector_wmape_mean"]
    summary = (
        df.groupby("label")
        .agg(
            n=("seed", "count"),
            mean_wmape=("mean_wmape", "mean"),
            std_wmape=("mean_wmape", "std"),
            wmape_2021=("wmape_2021", "mean"),
            wmape_2022=("wmape_2022", "mean"),
            wmape_2023=("wmape_2023", "mean"),
            wmape_2024=("wmape_2024", "mean"),
            wmape_2025=("wmape_2025", "mean"),
            sector_wmape_mean=("sector_wmape_mean", "mean"),
            shrink_2021=("shrink_2021", "mean"),
            shrink_2025=("shrink_2025", "mean"),
            auditor_confidence_mean=("auditor_confidence_mean", "mean"),
            auditor_variance=("auditor_variance", "mean"),
        )
        .reset_index()
        .sort_values(["mean_wmape", "wmape_2021"])
    )

    paired_rows = []
    ref = df[df["label"] == PRIMARY_REF].set_index("seed")
    for label in sorted(set(df["label"]) - {PRIMARY_REF}):
        cur = df[df["label"] == label].set_index("seed")
        joined = cur.join(ref, lsuffix="_cur", rsuffix="_ref", how="inner")
        row = {"label": label, "ref": PRIMARY_REF, "n": len(joined)}
        for metric in metric_cols:
            delta = joined[f"{metric}_cur"] - joined[f"{metric}_ref"]
            lo, hi = bootstrap_ci(delta)
            row[f"{metric}_delta"] = float(delta.mean()) if len(delta) else math.nan
            row[f"{metric}_wins"] = int((delta < 0).sum()) if len(delta) else 0
            row[f"{metric}_p"] = wilcoxon_p(delta)
            row[f"{metric}_ci95_lo"] = lo
            row[f"{metric}_ci95_hi"] = hi
        paired_rows.append(row)
    paired = pd.DataFrame(paired_rows).sort_values("mean_wmape_delta")

    # Pareto: lower is better for all four headline dimensions.
    headline = ["mean_wmape", "wmape_2021", "wmape_2025", "sector_wmape_mean"]
    pareto_rows = []
    for _, a in summary.iterrows():
        dominated = False
        for _, b in summary.iterrows():
            if a["label"] == b["label"]:
                continue
            no_worse = all(float(b[m]) <= float(a[m]) + 1e-12 for m in headline)
            strictly_better = any(float(b[m]) < float(a[m]) - 1e-12 for m in headline)
            if no_worse and strictly_better:
                dominated = True
                break
        pareto_rows.append({"label": a["label"], "pareto": not dominated})
    pareto = pd.DataFrame(pareto_rows)
    return summary, paired, pareto


def write_report(root: Path, df: pd.DataFrame, summary: pd.DataFrame, paired: pd.DataFrame, pareto: pd.DataFrame, strict: bool) -> None:
    out = root / "reports" / "phase2r_confirmatory"
    out.mkdir(parents=True, exist_ok=True)
    df.to_csv(out / "phase2r_runs.csv", index=False)
    summary.to_csv(out / "phase2r_summary.csv", index=False)
    paired.to_csv(out / "phase2r_paired_vs_l5_gate.csv", index=False)
    pareto.to_csv(out / "phase2r_pareto.csv", index=False)

    counts = df.groupby("label")["seed"].nunique().to_dict()
    missing_labels = sorted(EXPECTED_LABELS - set(counts))
    expected_n = max(counts.values()) if counts else 0
    incomplete = {k: int(v) for k, v in counts.items() if v != expected_n}
    errors = []
    if missing_labels:
        errors.append(f"missing labels: {missing_labels}")
    if incomplete:
        errors.append(f"incomplete labels: {incomplete}")
    if strict and errors:
        strict_line = "STRICT FAIL: " + "; ".join(errors)
    else:
        strict_line = "STRICT PASS" if not errors else "PARTIAL: " + "; ".join(errors)

    best_mean = summary.iloc[0]
    l5 = summary[summary["label"] == PRIMARY_CANDIDATE]
    ref_pair = paired[paired["label"] == PRIMARY_CANDIDATE]
    l5_line = "L5_trainopt not found."
    if not l5.empty and not ref_pair.empty:
        p = ref_pair.iloc[0]
        l5_line = (
            f"`L5_trainopt` vs `{PRIMARY_REF}`: mean delta "
            f"{p['mean_wmape_delta']:.6f}, wins {int(p['mean_wmape_wins'])}/{int(p['n'])}, "
            f"p={p['mean_wmape_p']:.4g}, bootstrap CI95 "
            f"[{p['mean_wmape_ci95_lo']:.6f}, {p['mean_wmape_ci95_hi']:.6f}]."
        )

    pareto_labels = ", ".join(pareto[pareto["pareto"]]["label"].tolist())
    lines = [
        "# HERALD Phase 2R Confirmatory Audit",
        "",
        strict_line,
        "",
        "## Main Read",
        "",
        f"- Best mean WMAPE: `{best_mean['label']}` = {best_mean['mean_wmape']:.6f}.",
        f"- {l5_line}",
        f"- Pareto labels over mean/2021/2025/A10: {pareto_labels or 'none'}.",
        "",
        "## Summary",
        "",
        "| Label | N | Mean | Std | 2021 | 2022 | 2023 | 2024 | 2025 | A10 | shrink 2021 | shrink 2025 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary.itertuples(index=False):
        lines.append(
            f"| {row.label} | {int(row.n)} | {row.mean_wmape:.6f} | "
            f"{0.0 if pd.isna(row.std_wmape) else row.std_wmape:.6f} | "
            f"{row.wmape_2021:.6f} | {row.wmape_2022:.6f} | {row.wmape_2023:.6f} | "
            f"{row.wmape_2024:.6f} | {row.wmape_2025:.6f} | {row.sector_wmape_mean:.6f} | "
            f"{row.shrink_2021:.3f} | {row.shrink_2025:.3f} |"
        )
    lines += [
        "",
        "## Interpretation Rule",
        "",
        "- Promote `L5_trainopt` only if it keeps paired mean gain vs `L5_gate_no_auditor` and is non-inferior on 2021/A10.",
        "- Treat `HC5_trainopt` as a trade-off candidate unless it also survives 2021/A10.",
        "- Treat auditor variants as stabilizers, not proof of autonomous regime discovery.",
        "- Keep flags rows as controls; the no-flags claim must not depend on comparing against a noisy or unfair flag baseline.",
    ]
    (out / "HERALD_PHASE2R_CONFIRMATORY_AUDIT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(out / "HERALD_PHASE2R_CONFIRMATORY_AUDIT.md")
    if strict and errors:
        raise SystemExit(strict_line)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    if not args.root.exists():
        raise SystemExit(f"missing root: {args.root}")

    df = collect(args.root)
    if df.empty:
        raise SystemExit(f"no per-run JSON files found under {args.root / 'reports' / 'per_run'}")

    summary, paired, pareto = summary_tables(df)
    write_report(args.root, df, summary, paired, pareto, args.strict)


if __name__ == "__main__":
    main()
