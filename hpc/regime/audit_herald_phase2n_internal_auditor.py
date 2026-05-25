#!/usr/bin/env python3
"""Audit HERALD Phase 2N internal-auditor results.

Checks the corrected methodology:
  - 11 configs x 10 seeds by default;
  - clean no-flags SIDE2 input policy in metadata;
  - paired comparisons against L5_gate_no_auditor;
  - auditor confidence is neither all-zero nor all-one.
"""

import argparse
import csv
import json
import re
from pathlib import Path
from statistics import mean, pstdev


EXPECTED_LABELS = [
    "L3_gate",
    "L5_gate_no_auditor",
    "HC5_l0_050",
    "L4_a10g",
    "AUD_lat_b001",
    "AUD_lat_b005",
    "AUD_alpha_b001",
    "AUD_alpha_b005",
    "AUD_both_b001",
    "AUD_both_b005",
    "AUD_both_b001_s010",
]
EXPECTED_SEEDS = [0, 1, 7, 13, 17, 42, 77, 99, 123, 2025]
LABEL_RE = re.compile(r"no_source_flags_(?P<label>.+)_seed_(?P<seed>\d+)\.json$")


def wilcoxon_p(xs, ys):
    try:
        from scipy.stats import wilcoxon  # type: ignore
    except Exception:
        return None
    diffs = [x - y for x, y in zip(xs, ys)]
    if not diffs or all(abs(d) < 1e-12 for d in diffs):
        return 1.0
    return float(wilcoxon(xs, ys, zero_method="wilcox").pvalue)


def read_runs(root: Path):
    rows = []
    errors = []
    for p in sorted((root / "reports/per_run").glob("*.json")):
        m = LABEL_RE.search(p.name)
        if not m:
            errors.append(f"cannot parse label/seed from {p.name}")
            continue
        label = m.group("label")
        seed = int(m.group("seed"))
        payload = json.loads(p.read_text(encoding="utf-8"))
        run_key, run = next(iter(payload.items()))
        conf = []
        for fold in (run.get("auditor_confidence_by_fold") or {}).values():
            conf.extend(float(v) for v in fold.values())
        rows.append({
            "label": label,
            "seed": seed,
            "run_key": run_key,
            "json": str(p),
            "mean": float(run["total_wmape_mean"]),
            "w2021": float(run["per_year_total"]["2021"]),
            "w2022": float(run["per_year_total"]["2022"]),
            "w2023": float(run["per_year_total"]["2023"]),
            "w2024": float(run["per_year_total"]["2024"]),
            "w2025": float(run["per_year_total"]["2025"]),
            "a10": float(run["sector_wmape_mean"]),
            "auditor_mode": run.get("auditor_mode", "none"),
            "auditor_budget_lambda": float(run.get("auditor_budget_lambda") or 0.0),
            "auditor_smooth_lambda": float(run.get("auditor_smooth_lambda") or 0.0),
            "auditor_conf_mean": mean(conf) if conf else 1.0,
            "auditor_conf_std": pstdev(conf) if len(conf) > 1 else 0.0,
            "auditor_collapsed_low": bool(conf and mean(conf) < 0.05),
            "auditor_collapsed_high": bool(conf and mean(conf) > 0.95),
            "auditor_constant": bool(len(conf) > 1 and pstdev(conf) < 1e-4),
        })
    return rows, errors


def read_metadata(root: Path):
    errors = []
    for p in sorted((root / "metadata").glob("*.json")):
        m = LABEL_RE.search(p.name)
        if not m:
            errors.append(f"cannot parse metadata label/seed from {p.name}")
            continue
        meta = json.loads(p.read_text(encoding="utf-8"))
        checks = {
            "regime_mode": meta.get("regime_mode") == "no_regime",
            "manual_flags_in_annual_features": meta.get("manual_flags_in_annual_features") is False,
            "manual_flags_in_regime_vector": meta.get("manual_flags_in_regime_vector") is False,
            "source_flags_in_annual_features": meta.get("source_flags_in_annual_features") is False,
            "feature_policy": meta.get("feature_policy") == "side5_lag1_growth1y",
            "macro_feature_set": meta.get("macro_feature_set") == "none",
            "quarterly_tensor_zeroed": meta.get("quarterly_tensor_zeroed") is False,
        }
        for k, ok in checks.items():
            if not ok:
                errors.append(f"{p.name}: bad {k}={meta.get(k)}")
    return errors


def write_csv(path: Path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k) for k in fields})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, type=Path)
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()

    rows, errors = read_runs(args.root)
    errors.extend(read_metadata(args.root))
    by = {(r["label"], r["seed"]): r for r in rows}
    for label in EXPECTED_LABELS:
        for seed in EXPECTED_SEEDS:
            if (label, seed) not in by:
                errors.append(f"missing run label={label} seed={seed}")

    out = args.root / "reports/phase2n_audit"
    labels = sorted({r["label"] for r in rows})
    summary = []
    for label in labels:
        rs = [r for r in rows if r["label"] == label]
        summary.append({
            "label": label,
            "n": len(rs),
            "mean_wmape": mean(r["mean"] for r in rs),
            "std_wmape": pstdev(r["mean"] for r in rs) if len(rs) > 1 else 0.0,
            "wmape_2021": mean(r["w2021"] for r in rs),
            "wmape_2025": mean(r["w2025"] for r in rs),
            "a10_wmape": mean(r["a10"] for r in rs),
            "auditor_mode": rs[0]["auditor_mode"] if rs else "",
            "auditor_conf_mean": mean(r["auditor_conf_mean"] for r in rs),
            "auditor_conf_std": mean(r["auditor_conf_std"] for r in rs),
            "collapsed_low": sum(r["auditor_collapsed_low"] for r in rs),
            "collapsed_high": sum(r["auditor_collapsed_high"] for r in rs),
            "constant_conf": sum(r["auditor_constant"] for r in rs),
        })

    paired = []
    ref_label = "L5_gate_no_auditor"
    for label in labels:
        if label == ref_label:
            continue
        common = [s for s in EXPECTED_SEEDS if (label, s) in by and (ref_label, s) in by]
        if not common:
            continue
        for metric in ["mean", "w2021", "w2025", "a10"]:
            xs = [by[(label, s)][metric] for s in common]
            ys = [by[(ref_label, s)][metric] for s in common]
            paired.append({
                "label": label,
                "ref": ref_label,
                "metric": metric,
                "n": len(common),
                "delta_label_minus_ref": mean(x - y for x, y in zip(xs, ys)),
                "wins": sum(x < y for x, y in zip(xs, ys)),
                "losses": sum(x > y for x, y in zip(xs, ys)),
                "wilcoxon_p": wilcoxon_p(xs, ys),
            })

    write_csv(out / "phase2n_summary.csv", summary, [
        "label", "n", "mean_wmape", "std_wmape", "wmape_2021", "wmape_2025",
        "a10_wmape", "auditor_mode", "auditor_conf_mean", "auditor_conf_std",
        "collapsed_low", "collapsed_high", "constant_conf",
    ])
    write_csv(out / "phase2n_paired_vs_l5.csv", paired, [
        "label", "ref", "metric", "n", "delta_label_minus_ref", "wins",
        "losses", "wilcoxon_p",
    ])
    write_csv(out / "phase2n_runs.csv", rows, [
        "label", "seed", "mean", "w2021", "w2022", "w2023", "w2024", "w2025",
        "a10", "auditor_mode", "auditor_budget_lambda", "auditor_smooth_lambda",
        "auditor_conf_mean", "auditor_conf_std", "auditor_collapsed_low",
        "auditor_collapsed_high", "auditor_constant",
    ])

    md = [
        "# HERALD Phase 2N Internal Auditor Audit",
        "",
        f"Root: `{args.root}`",
        f"Runs found: {len(rows)} / {len(EXPECTED_LABELS) * len(EXPECTED_SEEDS)}",
        f"Integrity errors: {len(errors)}",
        "",
        "Primary comparison is against `L5_gate_no_auditor`.",
        "An auditor config is not accepted if confidence is constant or collapsed.",
        "",
        "## Files",
        "- `phase2n_summary.csv`",
        "- `phase2n_paired_vs_l5.csv`",
        "- `phase2n_runs.csv`",
    ]
    if errors:
        md.extend(["", "## Errors"])
        md.extend(f"- {e}" for e in errors[:100])
    (out / "PHASE2N_AUDIT.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    print(f"runs={len(rows)} errors={len(errors)} out={out}")
    if args.strict and errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
