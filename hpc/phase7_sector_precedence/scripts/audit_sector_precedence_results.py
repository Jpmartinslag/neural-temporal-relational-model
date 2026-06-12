"""
Scientific audit of Phase 7 sector precedence merged results.

Independently recomputes BH/FDR and promotion gates. Validates completeness
against manifest and numeric integrity. Zero promoted edges is a valid result.

Outputs:
    audit_report.json   — machine-readable audit findings
    audit_report.md     — human-readable summary

Usage:
    python audit_sector_precedence_results.py \
        --all-edges <path/all_edges.csv> \
        --manifest <path/task_manifest.json> \
        --out-dir <dir>
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

FDR_Q = 0.05
MIN_ABS_BETA = 0.10
MIN_DELTA_R2 = 0.005
MIN_SIGN_STABILITY = 0.70
MIN_SAMPLES = 60

REQUIRED_COLS = {
    "task_id", "country", "scenario", "window_start", "window_end",
    "source_sector", "target_sector", "n_samples", "beta", "delta_r2",
    "p_perm", "bootstrap_sign_stability", "q_fdr",
}


def bh_fdr(pvalues: pd.Series) -> pd.Series:
    values = pvalues.to_numpy(dtype=float)
    result = np.full(len(values), np.nan)
    valid = np.flatnonzero(np.isfinite(values))
    if not len(valid):
        return pd.Series(result, index=pvalues.index)
    order = valid[np.argsort(values[valid])]
    ranked = values[order] * len(order) / np.arange(1, len(order) + 1)
    ranked = np.minimum.accumulate(ranked[::-1])[::-1]
    result[order] = np.minimum(ranked, 1.0)
    return pd.Series(result, index=pvalues.index)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--all-edges", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    findings: list[dict] = []
    errors = 0

    def record(level: str, code: str, message: str) -> None:
        nonlocal errors
        findings.append({"level": level, "code": code, "message": message})
        if level == "ERROR":
            errors += 1
            print(f"ERROR [{code}]: {message}", file=sys.stderr)
        else:
            print(f"{level} [{code}]: {message}")

    # Load manifest
    manifest = json.loads(args.manifest.read_text())
    expected_task_ids = {t["task_id"] for t in manifest}

    # Load all_edges
    if not args.all_edges.is_file():
        record("ERROR", "MISSING_FILE", f"all_edges.csv not found: {args.all_edges}")
        sys.exit(1)
    df = pd.read_csv(args.all_edges)

    # 1. Schema
    missing_cols = REQUIRED_COLS - set(df.columns)
    if missing_cols:
        record("ERROR", "MISSING_COLS", f"Missing columns: {sorted(missing_cols)}")
    else:
        record("INFO", "SCHEMA_OK", f"All required columns present ({len(df.columns)} total)")

    # 2. Completeness — all tasks must appear in edges
    if "task_id" in df.columns:
        actual_task_ids = set(df["task_id"].unique())
        missing_tasks = expected_task_ids - actual_task_ids
        extra_tasks = actual_task_ids - expected_task_ids
        if missing_tasks:
            record("ERROR", "MISSING_TASKS", f"{len(missing_tasks)} tasks absent from all_edges: {sorted(missing_tasks)[:10]}")
        else:
            record("INFO", "TASKS_COMPLETE", f"All {len(expected_task_ids)} tasks represented")
        if extra_tasks:
            record("ERROR", "EXTRA_TASKS", f"{len(extra_tasks)} extra task_ids not in manifest")

    # 3. Numeric integrity
    numeric_cols = ["beta", "delta_r2", "p_perm", "bootstrap_sign_stability", "q_fdr"]
    eligible_cols = [c for c in numeric_cols if c in df.columns]
    n_nan = df[eligible_cols].isnull().sum().sum()
    numeric_eligible = df[eligible_cols].select_dtypes(include="number")
    n_inf = np.isinf(numeric_eligible).sum().sum()

    # NaN is expected for edges with too few samples; count those
    n_total = len(df)
    n_with_nan = df[eligible_cols].isnull().any(axis=1).sum()
    if n_with_nan > 0:
        record("INFO", "NAN_PRESENT", f"{n_with_nan}/{n_total} edges have NaN (expected for low-sample edges)")
    if n_inf > 0:
        record("ERROR", "INF_PRESENT", f"{n_inf} Inf values in numeric columns")
    else:
        record("INFO", "NO_INF", "No Inf values in numeric columns")

    # 4. p_perm range check
    if "p_perm" in df.columns:
        valid_p = df["p_perm"].dropna()
        if len(valid_p) > 0:
            if (valid_p <= 0).any():
                record("ERROR", "P_ZERO", f"{(valid_p <= 0).sum()} p_perm values <= 0 (empirical p is always > 0)")
            if (valid_p > 1).any():
                record("ERROR", "P_ABOVE_ONE", f"{(valid_p > 1).sum()} p_perm values > 1")
            if not any(["P_ZERO", "P_ABOVE_ONE"] == f["code"] for f in findings):
                record("INFO", "P_RANGE_OK", f"p_perm in (0, 1] for all {len(valid_p)} non-NaN edges")

    # 5. Independently recompute BH/FDR and compare
    if {"p_perm", "q_fdr"}.issubset(df.columns):
        df_check = df.copy()
        df_check["q_fdr_recomputed"] = np.nan
        for (country, scenario, ws, we), group in df_check.groupby(
            ["country", "scenario", "window_start", "window_end"]
        ):
            q = bh_fdr(group["p_perm"])
            df_check.loc[group.index, "q_fdr_recomputed"] = q.values

        # Compare where both are finite
        both_finite = df_check["q_fdr"].notna() & df_check["q_fdr_recomputed"].notna()
        if both_finite.any():
            max_diff = (df_check.loc[both_finite, "q_fdr"] - df_check.loc[both_finite, "q_fdr_recomputed"]).abs().max()
            if max_diff > 1e-9:
                record("ERROR", "FDR_MISMATCH", f"Max q_fdr discrepancy: {max_diff:.2e} — merge script FDR may be wrong")
            else:
                record("INFO", "FDR_VERIFIED", f"BH/FDR recomputed matches merged (max diff={max_diff:.2e})")

    # 6. Promotion counts (not an error if zero)
    promotion_mask = (
        df["q_fdr"].le(FDR_Q)
        & df["beta"].abs().ge(MIN_ABS_BETA)
        & df["delta_r2"].ge(MIN_DELTA_R2)
        & df["bootstrap_sign_stability"].ge(MIN_SIGN_STABILITY)
        & df["n_samples"].ge(MIN_SAMPLES)
    ) if REQUIRED_COLS.issubset(set(df.columns)) else pd.Series(False, index=df.index)

    n_promoted_main = int(promotion_mask[df["scenario"].eq("main")].sum()) if "scenario" in df.columns else 0
    n_promoted_wo20 = int(promotion_mask[df["scenario"].eq("without_2020")].sum()) if "scenario" in df.columns else 0
    record("INFO", "PROMOTION_MAIN", f"Promoted edges (main): {n_promoted_main}")
    record("INFO", "PROMOTION_WO20", f"Promoted edges (without_2020): {n_promoted_wo20}")

    # 7. COVID robustness
    if "scenario" in df.columns:
        main_prom = df[(df["scenario"] == "main") & promotion_mask]
        wo20_prom = df[(df["scenario"] == "without_2020") & promotion_mask]
        key_cols = ["country", "window_start", "window_end", "source_sector", "target_sector"]
        if not main_prom.empty and not wo20_prom.empty:
            robust = main_prom[key_cols + ["beta"]].merge(
                wo20_prom[key_cols + ["beta"]].rename(columns={"beta": "beta_wo20"}),
                on=key_cols, how="inner",
            )
            robust = robust[np.sign(robust["beta"]) == np.sign(robust["beta_wo20"])]
            countries_robust = len(robust["country"].unique()) if len(robust) > 0 else 0
            record("INFO", "COVID_ROBUST", f"COVID-robust edges: {len(robust)} ({countries_robust} countries)")
        else:
            record("INFO", "COVID_ROBUST", "COVID-robust edges: 0 (one or both scenarios have no promoted edges)")

    audit_result = "PASS" if errors == 0 else f"FAIL ({errors} errors)"
    record("INFO", "SUMMARY", f"Audit result: {audit_result} — {len(findings)} findings")

    report = {
        "audit_result": audit_result,
        "errors": errors,
        "total_edges": len(df),
        "manifest_tasks": len(manifest),
        "findings": findings,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    (args.out_dir / "audit_report.json").write_text(json.dumps(report, indent=2) + "\n")

    # Markdown report
    md_lines = [
        "# Phase 7 Sector Precedence — Audit Report",
        "",
        f"**Result: {audit_result}**  ",
        f"Generated: {report['generated_at']}",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total edges | {len(df)} |",
        f"| Manifest tasks | {len(manifest)} |",
        f"| Promoted (main) | {n_promoted_main} |",
        f"| Promoted (without_2020) | {n_promoted_wo20} |",
        "",
        "## Findings",
        "",
    ]
    for f in findings:
        md_lines.append(f"- **{f['level']}** `{f['code']}`: {f['message']}")
    md_lines.append("")
    (args.out_dir / "audit_report.md").write_text("\n".join(md_lines))
    print(f"Audit complete: {audit_result} — see {args.out_dir}/audit_report.json")
    sys.exit(0 if errors == 0 else 1)


if __name__ == "__main__":
    main()
