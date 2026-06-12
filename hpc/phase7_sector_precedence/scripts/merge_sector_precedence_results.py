"""
Merge raw task outputs and apply BH/FDR per family for Phase 7.

Family = country × scenario × window (start, end).
BH/FDR is applied only after the FULL family is collected; this is why
each task outputs raw p-values and deferral to this script is mandatory.

Outputs (in out_dir):
    all_edges.csv               — all edges from all tasks (raw p_perm + q_fdr)
    main_with_sensitivity.csv   — main-scenario edges with without_2020 column
    latest.csv                  — promoted edges (all gates passed)
    decision.json               — SECTOR_PRECEDENCE_PROTOTYPE_READY or NOT_PROMOTED
    run_manifest.json           — provenance: manifest hash, task count, etc.

Usage:
    python merge_sector_precedence_results.py --raw-dir <dir> --manifest <path> --out-dir <dir>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

# Gate constants — pre-registered, must not change after observing results
FDR_Q = 0.05
MIN_ABS_BETA = 0.10
MIN_DELTA_R2 = 0.005
MIN_SIGN_STABILITY = 0.70
MIN_SAMPLES = 60


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


def load_manifest(manifest_path: Path) -> tuple[list[dict], str]:
    text = manifest_path.read_text()
    sha = hashlib.sha256(text.encode()).hexdigest()
    return json.loads(text), sha


def load_raw_results(raw_dir: Path, manifest: list[dict]) -> pd.DataFrame:
    """Load all task JSONs, verify 1:1 correspondence with manifest."""
    rows = []
    missing = []
    for task in manifest:
        expected_file = raw_dir / task["expected_output"]
        if not expected_file.exists():
            missing.append(task["task_id"])
            continue
        try:
            result = json.loads(expected_file.read_text())
        except Exception as e:
            sys.exit(f"ERROR: could not parse {expected_file}: {e}")

        if result.get("status") != "complete":
            sys.exit(f"ERROR: task {task['task_id']} result has status={result.get('status')!r}")

        for field in ("task_id", "country", "scenario", "window_start", "window_end",
                      "source_sector", "panel_checksum", "commit_sha"):
            if result.get(field) != task[field]:
                sys.exit(
                    f"ERROR: task {task['task_id']} field {field!r} mismatch: "
                    f"manifest={task[field]!r}, result={result.get(field)!r}"
                )

        for edge in result.get("edges", []):
            rows.append({
                "task_id": result["task_id"],
                "country": result["country"],
                "scenario": result["scenario"],
                "window_start": result["window_start"],
                "window_end": result["window_end"],
                "source_sector": result["source_sector"],
                "target_sector": edge["target_sector"],
                "n_samples": edge["n_samples"],
                "beta": edge["beta"],
                "delta_r2": edge["delta_r2"],
                "p_perm": edge["p_perm"],
                "bootstrap_sign_stability": edge["bootstrap_sign_stability"],
                "panel_checksum": result["panel_checksum"],
                "commit_sha": result["commit_sha"],
                "hostname": result.get("hostname", ""),
                "runtime_seconds": result.get("runtime_seconds", None),
            })

    if missing:
        sys.exit(f"ERROR: {len(missing)} tasks missing from raw_dir. Missing task_ids: {missing[:20]}")

    df = pd.DataFrame(rows)
    for col in ("beta", "delta_r2", "p_perm", "bootstrap_sign_stability"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def apply_fdr(df: pd.DataFrame) -> pd.DataFrame:
    """Apply BH/FDR per family = country × scenario × (window_start, window_end)."""
    df = df.copy()
    df["q_fdr"] = np.nan
    for (country, scenario, ws, we), group in df.groupby(
        ["country", "scenario", "window_start", "window_end"]
    ):
        q = bh_fdr(group["p_perm"])
        df.loc[group.index, "q_fdr"] = q.values
    return df


def apply_promotion_gates(df: pd.DataFrame) -> pd.Series:
    return (
        df["q_fdr"].le(FDR_Q)
        & df["beta"].abs().ge(MIN_ABS_BETA)
        & df["delta_r2"].ge(MIN_DELTA_R2)
        & df["bootstrap_sign_stability"].ge(MIN_SIGN_STABILITY)
        & df["n_samples"].ge(MIN_SAMPLES)
    )


def covid_robust(df: pd.DataFrame) -> pd.DataFrame:
    """Promoted in BOTH main AND without_2020 AND same sign."""
    main_promoted = df[
        (df["scenario"] == "main") & df["promoted"]
    ][["country", "window_start", "window_end", "source_sector", "target_sector", "beta"]].copy()
    main_promoted = main_promoted.rename(columns={"beta": "beta_main"})

    wo20_promoted = df[
        (df["scenario"] == "without_2020") & df["promoted"]
    ][["country", "window_start", "window_end", "source_sector", "target_sector", "beta"]].copy()
    wo20_promoted = wo20_promoted.rename(columns={"beta": "beta_wo20"})

    robust = main_promoted.merge(
        wo20_promoted,
        on=["country", "window_start", "window_end", "source_sector", "target_sector"],
        how="inner",
    )
    robust = robust[np.sign(robust["beta_main"]) == np.sign(robust["beta_wo20"])].copy()
    return robust


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    manifest, manifest_sha = load_manifest(args.manifest)
    print(f"Manifest: {len(manifest)} tasks, sha256={manifest_sha[:20]}...")

    df = load_raw_results(args.raw_dir, manifest)
    print(f"Loaded {len(df)} edges from {len(manifest)} tasks")

    df = apply_fdr(df)
    df["promoted"] = apply_promotion_gates(df)

    df.to_csv(args.out_dir / "all_edges.csv", index=False)
    print(f"Wrote all_edges.csv ({len(df)} rows)")

    # main_with_sensitivity: main rows + whether the edge is also promoted in without_2020
    main_df = df[df["scenario"] == "main"].copy()
    wo20_promoted_keys = set(
        df[(df["scenario"] == "without_2020") & df["promoted"]]
        .apply(lambda r: (r.country, r.window_start, r.window_end, r.source_sector, r.target_sector), axis=1)
    )
    main_df["promoted_without_2020"] = main_df.apply(
        lambda r: (r.country, r.window_start, r.window_end, r.source_sector, r.target_sector) in wo20_promoted_keys,
        axis=1,
    )
    main_df.to_csv(args.out_dir / "main_with_sensitivity.csv", index=False)

    robust = covid_robust(df)
    promoted_main = df[(df["scenario"] == "main") & df["promoted"]].copy()
    promoted_main.to_csv(args.out_dir / "latest.csv", index=False)
    print(f"Promoted (main, all gates): {len(promoted_main)} edges")
    print(f"COVID-robust (both scenarios, same sign): {len(robust)} edges")

    # Per-country COVID-robust count
    countries_with_robust = len(robust["country"].unique()) if len(robust) > 0 else 0
    if countries_with_robust >= 2:
        verdict = "SECTOR_PRECEDENCE_PROTOTYPE_READY"
    else:
        verdict = "SECTOR_PRECEDENCE_NOT_PROMOTED"

    robust.to_csv(args.out_dir / "covid_robust_edges.csv", index=False)

    decision = {
        "verdict": verdict,
        "total_tasks": len(manifest),
        "total_edges_raw": len(df),
        "promoted_main_count": int(len(promoted_main)),
        "covid_robust_count": int(len(robust)),
        "countries_with_robust_edges": int(countries_with_robust),
        "gate_thresholds": {
            "q_fdr": FDR_Q,
            "min_abs_beta": MIN_ABS_BETA,
            "min_delta_r2": MIN_DELTA_R2,
            "min_sign_stability": MIN_SIGN_STABILITY,
            "min_samples": MIN_SAMPLES,
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    (args.out_dir / "decision.json").write_text(json.dumps(decision, indent=2) + "\n")
    print(f"Verdict: {verdict}")

    run_manifest = {
        "manifest_sha256": manifest_sha,
        "manifest_task_count": len(manifest),
        "panel_checksum": manifest[0]["panel_checksum"] if manifest else None,
        "commit_sha": manifest[0]["commit_sha"] if manifest else None,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    (args.out_dir / "run_manifest.json").write_text(json.dumps(run_manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
