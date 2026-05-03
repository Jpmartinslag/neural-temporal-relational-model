#!/usr/bin/env python3
"""Summarize HERALD semi total battery outputs.

Usage:
  python3 scripts/summarize_herald_semi_total.py hpc_results/herald_semi_total_geo2025_...
"""

from __future__ import annotations

import argparse
import json
import math
import statistics as stats
from pathlib import Path


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def mean(values):
    return sum(values) / len(values) if values else math.nan


def stdev(values):
    return stats.stdev(values) if len(values) > 1 else 0.0


def collect_runs(root: Path):
    reports = root / "reports"
    sources = {
        "v3": (
            load_json(reports / "herald_v3_total_metrics_v1.json")
            or load_json(reports / "herald_v3_metrics_v1.json")
        ),
        "v6": (
            load_json(reports / "herald_v6_total_metrics_v1.json")
            or load_json(reports / "herald_v6_metrics_v1.json")
        ),
        "semi": (
            load_json(reports / "herald_semi_total_metrics_v1.json")
            or load_json(reports / "herald_semi_metrics_v1.json")
        ),
        "semi_precovid": (
            load_json(reports / "herald_semi_total_precovid_metrics_v1.json")
            or load_json(reports / "herald_semi_precovid_metrics_v1.json")
        ),
    }

    rows = []
    by_tag_seed = {}
    for family, data in sources.items():
        for run_key, run in data.items():
            tag = run.get("run_tag") or run_key.rsplit("_seed_", 1)[0]
            seed = int(run["seed"])
            wmape = float(run.get("mean_wmape", run.get("total_wmape_mean")))
            gamma_geo = run.get("gamma_geo")
            gamma_mob = run.get("gamma_mob")
            rows.append({
                "family": family,
                "run_tag": tag,
                "seed": seed,
                "wmape": wmape,
                "sector_wmape_mean": run.get("sector_wmape_mean"),
                "gamma_mob_gt_geo": (
                    gamma_mob is not None and gamma_geo is not None and gamma_mob > gamma_geo
                ),
            })
            by_tag_seed[(tag, seed)] = wmape

    temporal = load_json(root / "temporal_baselines" / "reports" / "final_temporal_baselines_metrics_v1.json")
    for run in temporal.get("summary_mean_wmape", []):
        tag = run["model"]
        seed = int(run.get("seed", 0))
        wmape = float(run["mean_wmape"])
        rows.append({
            "family": "baseline_temporal",
            "run_tag": tag,
            "seed": seed,
            "wmape": wmape,
            "sector_wmape_mean": None,
            "gamma_mob_gt_geo": False,
        })
        by_tag_seed[(tag, seed)] = wmape

    for path in sorted((root / "stgnn_reports").glob("dynamic_stgnn_model_metrics_seed_*_v1.json")):
        data = load_json(path)
        per_model = {}
        for run in data.get("metrics_by_model_year", []):
            per_model.setdefault(run["model"], []).append(float(run["wmape"]))
        seed = int(path.stem.split("_seed_")[1].split("_")[0])
        for tag, values in per_model.items():
            wmape = mean(values)
            rows.append({
                "family": "baseline_stgnn",
                "run_tag": tag,
                "seed": seed,
                "wmape": wmape,
                "sector_wmape_mean": None,
                "gamma_mob_gt_geo": False,
            })
            by_tag_seed[(tag, seed)] = wmape
    return rows, by_tag_seed


def summarize(rows):
    grouped = {}
    for row in rows:
        grouped.setdefault(row["run_tag"], []).append(row)

    out = []
    for tag, vals in grouped.items():
        w = [v["wmape"] for v in vals]
        sector = [v["sector_wmape_mean"] for v in vals if v["sector_wmape_mean"] is not None]
        out.append({
            "run_tag": tag,
            "family": vals[0]["family"],
            "n": len(vals),
            "mean": mean(w),
            "std": stdev(w),
            "min": min(w),
            "max": max(w),
            "sector_mean": mean(sector) if sector else math.nan,
            "gamma_mob_gt_geo": sum(v["gamma_mob_gt_geo"] for v in vals),
        })
    return sorted(out, key=lambda r: r["mean"])


def paired_table(rows, by_tag_seed):
    tags = {r["run_tag"] for r in rows}
    refs = [
        "total_geo2025",
        "total_h32_no_semi",
        "total_h64_no_semi",
    ]
    existing_refs = [r for r in refs if any(t == r for t in tags)]
    lines = []
    for tag in sorted(tags):
        for ref in existing_refs:
            if tag == ref:
                continue
            diffs = []
            wins = 0
            seeds = sorted({
                seed for (candidate_tag, seed) in by_tag_seed
                if candidate_tag in (tag, ref)
            })
            for seed in seeds:
                if (tag, seed) in by_tag_seed and (ref, seed) in by_tag_seed:
                    diff = by_tag_seed[(tag, seed)] - by_tag_seed[(ref, seed)]
                    diffs.append(diff)
                    wins += diff < 0
            if diffs:
                lines.append({
                    "run_tag": tag,
                    "ref": ref,
                    "n": len(diffs),
                    "wins": wins,
                    "mean_diff": mean(diffs),
                })
    return lines


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    rows, by_tag_seed = collect_runs(args.root)
    summary = summarize(rows)
    paired = paired_table(rows, by_tag_seed)

    lines = ["# HERALD Semi Total Summary", ""]
    lines += ["## Ranking", ""]
    lines.append("| Rank | Run tag | Family | N | Mean WMAPE | Std | Min | Max | Sector | gamma_mob>geo |")
    lines.append("|---:|---|---|---:|---:|---:|---:|---:|---:|---:|")
    for i, r in enumerate(summary, 1):
        lines.append(
            f"| {i} | `{r['run_tag']}` | {r['family']} | {r['n']} | "
            f"{r['mean']:.6f} | {r['std']:.6f} | {r['min']:.6f} | {r['max']:.6f} | "
            f"{r['sector_mean']:.6f} | {r['gamma_mob_gt_geo']}/{r['n']} |"
        )

    lines += ["", "## Paired Diffs", ""]
    lines.append("Negative mean_diff means the run tag beats the reference.")
    lines.append("")
    lines.append("| Run tag | Reference | N | Wins | Mean diff |")
    lines.append("|---|---|---:|---:|---:|")
    for r in sorted(paired, key=lambda x: (x["ref"], x["mean_diff"])):
        lines.append(
            f"| `{r['run_tag']}` | `{r['ref']}` | {r['n']} | "
            f"{r['wins']}/{r['n']} | {r['mean_diff']:.6f} |"
        )

    text = "\n".join(lines) + "\n"
    out = args.out or (args.root / "reports" / "HERALD_SEMI_TOTAL_SUMMARY.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(text)
    print(f"Saved: {out}")


if __name__ == "__main__":
    main()
