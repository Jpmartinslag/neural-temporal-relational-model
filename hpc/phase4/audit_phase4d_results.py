#!/usr/bin/env python3
"""Audit Phase 4D HPC results after a battery completes.

Usage:
    python3 hpc/phase4/audit_phase4d_results.py \
        --root hpc_results/herald_phase4d_nl_20260601_120000_r1 \
        --phase4a-wmape 0.058184 \
        --phase4c-wmape 0.060751

Reads per_run JSONs. Strips the phase4d_{country}_ prefix from run tags to get
clean config labels. Prints a summary table and victory criteria evaluation.

Victory criteria:
  - graph_real beats graph_perm_control       (spatial signal present)
  - best functional graph beats geo_4c        (commuting/sector > geography)
  - best functional graph not >1% worse than best_4a (no regression)
  - strong win if ≥3% WMAPE improvement over geo_4c in ≥2 countries
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent.parent.parent


def load_results(run_root, country):
    jsons = list((run_root / "reports" / "per_run").glob("*.json"))
    configs = {}  # type: dict
    prefix = f"phase4d_{country}_"
    for jpath in jsons:
        data = json.loads(jpath.read_text())
        for _tag, rd in data.items():
            tag = rd.get("run_tag", "")
            label = tag.replace(prefix, "")
            wmape = rd.get("total_wmape_mean") or rd.get("wmape_mean")
            if wmape is None:
                continue
            configs.setdefault(label, []).append(float(wmape))
    return {k: sorted(v) for k, v in configs.items()}


def load_graph_meta(run_root: Path, country: str) -> dict[str, dict]:
    meta_dir = run_root / "metadata"
    result: dict[str, dict] = {}
    prefix = f"phase4d_{country}_"
    for mf in meta_dir.glob("*.json"):
        try:
            data = json.loads(mf.read_text())
        except Exception:
            continue
        label = data.get("config_label") or mf.stem.replace(prefix, "").rsplit("_seed_", 1)[0]
        if label not in result:
            result[label] = {
                "graph_policy": data.get("graph_policy", "?"),
                "graph_path": Path(data.get("graph_path", "?")).name,
                "graph_density": data.get("graph_density", float("nan")),
                "graph_diag_mean": data.get("graph_diag_mean", float("nan")),
                "tensor_policy": data.get("tensor_policy", "?"),
            }
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--phase4a-wmape", type=float, default=None,
                        help="Best Phase 4A WMAPE for this country (reference)")
    parser.add_argument("--phase4c-wmape", type=float, default=None,
                        help="Best Phase 4C WMAPE for this country (reference)")
    parser.add_argument("--france-wmape", type=float, default=0.020398)
    args = parser.parse_args()

    run_root = BASE / args.root if not args.root.is_absolute() else args.root
    if not run_root.exists():
        print(f"ERROR: {run_root} does not exist"); return

    # Detect country from dir name
    name = run_root.name
    country = "?"
    for c in ("nl", "be", "pt"):
        if f"_{c}_" in name:
            country = c; break

    configs = load_results(run_root, country)
    meta = load_graph_meta(run_root, country)

    if not configs:
        print(f"No results found in {run_root}"); return

    # Expected counts
    n_seeds = len(next(iter(configs.values())))
    expected = 200 if country in ("nl", "be") else 140  # 10 or 7 configs × 20 seeds
    total_runs = sum(len(v) for v in configs.values())
    print(f"\n[{country.upper()}] Loaded {total_runs} runs from {run_root.name}")
    if total_runs < expected:
        print(f"  WARNING: expected {expected} runs, got {total_runs}")

    # Build summary table
    rows = []
    for label, wmapes in sorted(configs.items(), key=lambda x: np.mean(x[1])):
        m = meta.get(label, {})
        rows.append({
            "label": label,
            "n": len(wmapes),
            "mean": np.mean(wmapes),
            "std": np.std(wmapes),
            "graph": m.get("graph_path", "?"),
            "density": m.get("graph_density", float("nan")),
            "tensor": m.get("tensor_policy", "?"),
        })

    df = pd.DataFrame(rows)
    print(f"\n{'Config':<30} {'N':>4} {'WMAPE mean':>12} {'±std':>8}  {'Graph':>35} {'Density':>8} {'Tensor':>15}")
    print("-" * 120)
    for _, r in df.iterrows():
        ref_4a = f"  {(r['mean']/args.phase4a_wmape - 1)*100:+.1f}% vs 4A" if args.phase4a_wmape else ""
        print(f"  {r['label']:<28} {r['n']:>4}  {r['mean']:>12.6f}  {r['std']:>8.6f}  {r['graph']:>35} {r['density']:>8.3f} {r['tensor']:>15}{ref_4a}")

    # ── Victory criteria ─────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f" Victory criteria [{country.upper()}]")
    print(f"{'='*60}")

    means = {r["label"]: r["mean"] for _, r in df.iterrows()}
    perm  = means.get("graph_perm_control")
    geo4c = means.get("geo_4c") or args.phase4c_wmape
    best4a = means.get("best_4a") or args.phase4a_wmape

    functional = {k: v for k, v in means.items()
                  if k not in ("best_4a", "geo_4c", "graph_perm_control")}
    best_func_label = min(functional, key=functional.__getitem__) if functional else None
    best_func = functional[best_func_label] if best_func_label else None

    def check(cond: bool, msg: str) -> None:
        sym = "✓" if cond else "✗"
        print(f"  {sym} {msg}")

    if perm and best_func:
        check(best_func < perm, f"Functional graph ({best_func:.6f}) < perm control ({perm:.6f})")
    if geo4c and best_func:
        delta = (best_func - geo4c) / geo4c * 100
        check(best_func < geo4c, f"Best functional ({best_func_label}: {best_func:.6f}) < geo_4c ({geo4c:.6f})  [{delta:+.1f}%]")
    if best4a and best_func:
        regress = (best_func - best4a) / best4a * 100
        check(regress <= 1.0, f"No regression vs best_4a ({best_func:.6f} vs {best4a:.6f})  [{regress:+.1f}%]")
    if geo4c and best_func:
        strong = (geo4c - best_func) / geo4c * 100
        check(strong >= 3.0, f"Strong win: ≥3% vs geo_4c → {strong:.1f}% improvement")

    print(f"\n  Reference: France WMAPE = {args.france_wmape:.6f}")
    best_overall = df["mean"].min()
    print(f"  Best this battery: {df.loc[df['mean'].idxmin(), 'label']} = {best_overall:.6f}")
    if args.phase4c_wmape:
        print(f"  Phase 4C best: {args.phase4c_wmape:.6f}")
    if args.phase4a_wmape:
        print(f"  Phase 4A best: {args.phase4a_wmape:.6f}")


if __name__ == "__main__":
    main()
