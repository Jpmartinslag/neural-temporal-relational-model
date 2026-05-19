#!/usr/bin/env python3
"""Audit HERALD Phase 2C critical battery.

Phase 2C tests two orthogonal questions:
  1. Does symmetric smoothing change the ranking? (cand_baseline vs. cand_sym_smooth)
  2. Does the latent regime carry real signal? (falsification tests)

Decision logic:
  - If cand_sym_smooth >= cand_baseline (worse with symmetric smooth), the Phase 2A
    win was partly an artefact of the asymmetric smooth penalty — the manual control
    had structural capacity the latent model did not.
  - If falsify_* is equivalent to cand_baseline, the latent regime is not doing
    useful work (the gain comes from elsewhere in the architecture).
  - fold2021_probe reveals whether the 2021 collapse is structural or seed-variance.
"""

import argparse
import json
from pathlib import Path
from typing import Dict

import numpy as np
import pandas as pd

try:
    from scipy.stats import wilcoxon
except Exception:
    wilcoxon = None


REAL_CANDIDATES = {"ctrl_manual", "ctrl_noregime", "cand_baseline", "cand_sym_smooth"}
FALSIFICATION_LABELS = {"falsify_regime_permute", "falsify_latent_inf_zero", "falsify_latent_frozen"}
FOLD_PROBE_LABELS = {"fold2021_probe"}
EXPECTED_LABELS = REAL_CANDIDATES | FALSIFICATION_LABELS | FOLD_PROBE_LABELS


def _read_runs(root):
    # type: (Path) -> pd.DataFrame
    rows = []
    for path in sorted((root / "reports" / "per_run").glob("regime_*_seed_*.json")):
        meta_path = root / "metadata" / path.name
        meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
        payload = json.loads(path.read_text(encoding="utf-8"))
        for run_key, result in payload.items():
            label = meta.get("experiment_label") or "base"
            rows.append({
                "run_key": run_key,
                "label": label,
                "seed": int(result["seed"]),
                "regime_mode": meta.get("regime_mode", "unknown"),
                "variant": result.get("v7_variant", "unknown"),
                "source_policy": "with_source_flags" if meta.get("source_flags_in_annual_features", True) else "no_source_flags",
                "smooth_regime_source": meta.get("smooth_regime_source", "unknown"),
                "latent_train_mode": meta.get("latent_train_mode", "unknown"),
                "latent_inference_mode": meta.get("latent_inference_mode", "unknown"),
                "regime_seq_transform": meta.get("regime_seq_transform", "unknown"),
                "single_target_year": meta.get("single_target_year"),
                "is_falsification": bool(meta.get("is_falsification_test", False)),
                "comparison_is_symmetric": bool(meta.get("comparison_is_symmetric", False)),
                "mean_wmape": float(result["total_wmape_mean"]),
                "wmape_2025": float(result.get("total_wmape_2025") or float("nan")),
                "sector_wmape_mean": float(result["sector_wmape_mean"]),
                "per_year": result.get("per_year_total", {}),
                "path": str(path),
            })
    if not rows:
        raise SystemExit(f"No Phase 2C metrics found under {root}")
    return pd.DataFrame(rows)


def _paired(df, label_a, label_b, metric):
    # type: (pd.DataFrame, str, str, str) -> Dict
    a = df[df["label"] == label_a].set_index("seed")[metric]
    b = df[df["label"] == label_b].set_index("seed")[metric]
    seeds = sorted(set(a.index) & set(b.index))
    if not seeds:
        return {"n": 0, "wins_b": 0, "delta_b_minus_a": float("nan"), "p": float("nan")}
    diff = b.loc[seeds] - a.loc[seeds]
    wins_b = int((diff < 0).sum())
    p = float("nan")
    if wilcoxon is not None and len(seeds) > 1 and np.any(np.abs(diff.to_numpy()) > 0):
        p = float(wilcoxon(diff.to_numpy()).pvalue)
    return {"n": len(seeds), "wins_b": wins_b, "delta_b_minus_a": float(diff.mean()), "p": p}


def _fmt_p(p):
    return "NA" if not np.isfinite(p) else f"{p:.4f}"


def main():
    parser = argparse.ArgumentParser(description="Audit HERALD Phase 2C critical battery")
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--strict", action="store_true",
                        help="Fail if any expected label is missing or seed count != 10")
    args = parser.parse_args()

    df = _read_runs(args.root)
    out_dir = args.root / "reports" / "audit_phase2c_critical"
    out_dir.mkdir(parents=True, exist_ok=True)

    labels_found = set(df["label"].unique())
    seeds_per_label = df.groupby("label")["seed"].nunique().to_dict()
    missing = sorted(EXPECTED_LABELS - labels_found)
    bad_counts = {k: v for k, v in seeds_per_label.items() if v != 10}

    # fold2021_probe only covers one fold — mean_wmape = wmape_2021 for those runs
    full_df = df[~df["label"].isin(FOLD_PROBE_LABELS)]
    probe_df = df[df["label"].isin(FOLD_PROBE_LABELS)]

    if args.strict and (missing or bad_counts):
        raise SystemExit(
            f"Phase 2C strict audit failed: missing_labels={missing} "
            f"bad_seed_counts={bad_counts}"
        )

    # ── Main summary ─────────────────────────────────────────────────────────
    summary = (full_df.groupby(["label", "smooth_regime_source", "latent_train_mode",
                                "latent_inference_mode", "regime_seq_transform"])
               .agg(n=("seed", "count"),
                    mean_wmape=("mean_wmape", "mean"),
                    std_wmape=("mean_wmape", "std"),
                    wmape_2025=("wmape_2025", "mean"),
                    std_2025=("wmape_2025", "std"),
                    sector_wmape_mean=("sector_wmape_mean", "mean"),
                    std_sector=("sector_wmape_mean", "std"))
               .reset_index()
               .sort_values("mean_wmape"))

    # ── Per-year breakdown ────────────────────────────────────────────────────
    fold_rows = []
    for _, row in df.iterrows():
        lbl = row["label"]
        for yr_str, wm in row["per_year"].items():
            fold_rows.append({"label": lbl, "seed": row["seed"],
                              "year": int(yr_str), "wmape": float(wm)})
    fold_df = pd.DataFrame(fold_rows)
    fold_summary = (fold_df.groupby(["label", "year"])
                    .agg(wmape_mean=("wmape", "mean"), wmape_std=("wmape", "std"))
                    .reset_index())

    # ── Question 1: does symmetric smooth change ranking? ─────────────────────
    q1 = _paired(full_df, "cand_baseline", "cand_sym_smooth", "mean_wmape")
    q1_a10 = _paired(full_df, "cand_baseline", "cand_sym_smooth", "sector_wmape_mean")
    q1_2025 = _paired(full_df, "cand_baseline", "cand_sym_smooth", "wmape_2025")

    # ── Question 2: falsification checks ─────────────────────────────────────
    falsify_rows = []
    for flabel in sorted(FALSIFICATION_LABELS & labels_found):
        for metric in ("mean_wmape", "wmape_2025", "sector_wmape_mean"):
            for ref in ("cand_baseline", "cand_sym_smooth"):
                if ref not in labels_found:
                    continue
                stats = _paired(full_df, ref, flabel, metric)
                falsify_rows.append({
                    "falsification": flabel,
                    "reference": ref,
                    "metric": metric,
                    "delta_falsify_minus_ref": stats["delta_b_minus_a"],
                    "wins_falsify": stats["wins_b"],
                    "n": stats["n"],
                    "p": stats["p"],
                })
    falsify_df = pd.DataFrame(falsify_rows) if falsify_rows else pd.DataFrame()

    # ── fold2021 probe ────────────────────────────────────────────────────────
    probe_summary = pd.DataFrame()
    if not probe_df.empty:
        probe_summary = (probe_df.groupby("label")
                         .agg(n=("seed", "count"),
                              wmape_2021_mean=("mean_wmape", "mean"),
                              wmape_2021_std=("mean_wmape", "std"))
                         .reset_index())

    # ── Save artifacts ────────────────────────────────────────────────────────
    summary.to_csv(out_dir / "phase2c_summary.csv", index=False)
    fold_summary.to_csv(out_dir / "phase2c_fold_by_fold.csv", index=False)
    if not falsify_df.empty:
        falsify_df.to_csv(out_dir / "phase2c_falsification.csv", index=False)
    if not probe_summary.empty:
        probe_summary.to_csv(out_dir / "phase2c_fold2021_probe.csv", index=False)
    df.drop(columns=["per_year"]).to_csv(out_dir / "phase2c_runs.csv", index=False)

    # ── Markdown report ───────────────────────────────────────────────────────
    lines = [
        "# HERALD Phase 2C Critical Audit",
        "",
        "Two questions tested:",
        "1. Was the Phase 2A win an artefact of the asymmetric smooth penalty?",
        "2. Does the latent regime carry real signal (falsification)?",
        "",
        "## Integrity",
        "",
        f"- total runs: {len(df)}",
        f"- labels found: {sorted(labels_found)}",
        f"- missing labels: {missing or 'none'}",
        "",
        "## Main Summary (full-battery runs only)",
        "",
        "| Label | smooth_src | latent_train | N | Mean WMAPE | 2025 WMAPE | A10 WMAPE |",
        "|---|---|---|---:|---:|---:|---:|",
    ]
    for r in summary.itertuples(index=False):
        lines.append(
            f"| {r.label} | {r.smooth_regime_source} | {r.latent_train_mode} | {int(r.n)} | "
            f"{r.mean_wmape:.6f} ± {r.std_wmape:.6f} | "
            f"{r.wmape_2025:.6f} ± {r.std_2025:.6f} | "
            f"{r.sector_wmape_mean:.5f} ± {r.std_sector:.5f} |"
        )

    lines += [
        "",
        "## Fold-by-fold WMAPE",
        "",
        "| Label | 2021 | 2022 | 2023 | 2024 | 2025 |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    pivot = fold_summary[fold_summary["label"].isin(
        REAL_CANDIDATES & labels_found
    )].pivot(index="label", columns="year", values="wmape_mean")
    for lbl in sorted(pivot.index):
        row_vals = [f"{pivot.loc[lbl, yr]:.5f}" if yr in pivot.columns else "—"
                    for yr in [2021, 2022, 2023, 2024, 2025]]
        lines.append(f"| {lbl} | " + " | ".join(row_vals) + " |")

    lines += [
        "",
        "## Question 1 — Symmetric smooth effect",
        "",
        f"Comparison: cand_sym_smooth vs. cand_baseline (N={q1['n']} seed pairs)",
        "",
        f"| Metric | delta (sym − base) | wins sym | p |",
        f"|---|---:|---:|---|",
        f"| mean_wmape | {q1['delta_b_minus_a']:+.6f} | {q1['wins_b']}/{q1['n']} | {_fmt_p(q1['p'])} |",
        f"| wmape_2025 | {q1_2025['delta_b_minus_a']:+.6f} | {q1_2025['wins_b']}/{q1_2025['n']} | {_fmt_p(q1_2025['p'])} |",
        f"| A10_wmape | {q1_a10['delta_b_minus_a']:+.6f} | {q1_a10['wins_b']}/{q1_a10['n']} | {_fmt_p(q1_a10['p'])} |",
        "",
        "**Interpretation:**",
        "- `delta > 0` (sym worse): Phase 2A win was partly from structural asymmetry.",
        "- `delta ≈ 0`: the smooth source does not explain the Phase 2A result.",
        "- `delta < 0` (sym better): symmetric smooth is strictly better — Phase 2A understated the gain.",
    ]

    if not falsify_df.empty:
        lines += [
            "",
            "## Question 2 — Falsification tests",
            "",
            "**Expected:** falsifications should be worse (higher WMAPE) than real candidates.",
            "If a falsification matches or beats the candidate, the candidate's signal is spurious.",
            "",
            "| Falsification | Ref | Metric | delta (falsify − ref) | wins_falsify | p | Verdict |",
            "|---|---|---|---:|---:|---|---|",
        ]
        for r in falsify_df.itertuples(index=False):
            verdict = "⚠️ SIGNAL SPURIOUS" if r.delta_falsify_minus_ref <= 0 else "✓ as expected"
            lines.append(
                f"| {r.falsification} | {r.reference} | {r.metric} | "
                f"{r.delta_falsify_minus_ref:+.6f} | {r.wins_falsify}/{r.n} | "
                f"{_fmt_p(r.p)} | {verdict} |"
            )

    if not probe_summary.empty:
        lines += [
            "",
            "## fold2021_probe — isolated 2021 fold",
            "",
            "| Label | N | WMAPE 2021 mean | std |",
            "|---|---:|---:|---:|",
        ]
        for r in probe_summary.itertuples(index=False):
            lines.append(
                f"| {r.label} | {int(r.n)} | {r.wmape_2021_mean:.6f} | {r.wmape_2021_std:.6f} |"
            )
        ctrl_2021 = probe_summary.loc[probe_summary["label"] == "fold2021_probe", "wmape_2021_mean"].values
        if len(ctrl_2021):
            lines += ["",
                      f"2021 WMAPE for cand_baseline (from fold_by_fold): check phase2c_fold_by_fold.csv"]

    lines += [
        "",
        "## Decision Logic",
        "",
        "Proceed to Phase 3 (MoE / stronger latent) only if ALL conditions hold:",
        "",
        "1. `cand_sym_smooth` does not degrade vs. `cand_baseline` by more than 0.001 WMAPE",
        "   (meaning the Phase 2A gain survives with fair comparison)",
        "2. ALL falsification tests are worse than `cand_sym_smooth` on mean_wmape (delta > 0)",
        "   (confirming real signal, not architecture artefact)",
        "3. `cand_sym_smooth` WMAPE 2021 ≤ `ctrl_manual` WMAPE 2021 + 0.005",
        "   (the latent does not collapse on the COVID transition year)",
        "4. `cand_sym_smooth` A10 WMAPE ≤ `ctrl_manual` A10 WMAPE",
        "   (sector constraint maintained)",
        "",
        "If condition 1 fails: report that Phase 2A was a structural artefact.",
        "If condition 2 fails: the latent regime is not useful; reject the latent hypothesis.",
        "If condition 3 fails: the architecture cannot handle regime breaks without manual flags.",
        "If condition 4 fails: run Phase 2B winner for A10 guard before Phase 3.",
    ]
    (out_dir / "PHASE2C_CRITICAL_AUDIT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Audit saved to {out_dir}")
    print("\n=== Main summary ===")
    print(summary[["label", "n", "mean_wmape", "wmape_2025", "sector_wmape_mean",
                   "smooth_regime_source", "latent_train_mode"]].to_string(index=False))
    print("\n=== Q1: symmetric smooth effect ===")
    print(f"  mean_wmape:  delta={q1['delta_b_minus_a']:+.6f}  p={_fmt_p(q1['p'])}")
    print(f"  wmape_2025:  delta={q1_2025['delta_b_minus_a']:+.6f}  p={_fmt_p(q1_2025['p'])}")
    print(f"  A10_wmape:   delta={q1_a10['delta_b_minus_a']:+.6f}  p={_fmt_p(q1_a10['p'])}")
    if not falsify_df.empty:
        print("\n=== Q2: falsification ===")
        print(falsify_df[["falsification", "metric", "delta_falsify_minus_ref", "p"]].to_string(index=False))


if __name__ == "__main__":
    main()
