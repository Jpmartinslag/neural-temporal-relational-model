"""Audit Phase 4E-B causal feature-policy ablation results."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

BASE = Path(__file__).resolve().parents[2]

EXPECTED_CONFIGS = {
    "fr": {"b0_baseline_annual", "b1_side5_full_zero", "b2_side2_zero", "b3_current_clean_zero"},
    "nl": {"b0_baseline_annual", "b1_side5_full_zero", "b2_side2_zero", "b3_current_clean_zero"},
    "be": {"b0_baseline_annual", "b1_side5_full_zero", "b2_side2_zero", "b3_current_clean_zero"},
    "pt": {
        "b0_baseline_annual",
        "b1_side5_full_zero",
        "b2_side2_zero",
        "b3_current_clean_zero",
        "b4_side2_births_lag1",
        "b5_side2_emp_lag1",
    },
}


def _run_obj(data: dict) -> dict:
    if len(data) == 1 and isinstance(next(iter(data.values())), dict):
        return next(iter(data.values()))
    return data


def _label_from_tag(tag: str, country: str) -> str:
    prefix = f"phase4e_b_{country}_"
    if tag.startswith(prefix):
        return tag[len(prefix):]
    return tag.rsplit("_seed_", 1)[0]


def audit_country(country: str, root: Path, expected_seeds: int = 10) -> dict:
    root = BASE / root if not root.is_absolute() else root
    per_run = root / "reports" / "per_run"
    meta_dir = root / "metadata"
    results: dict[str, list[float]] = {}
    meta: dict[str, dict] = {}

    for p in sorted(per_run.glob("*.json")):
        rd = _run_obj(json.loads(p.read_text()))
        tag = rd.get("run_tag", p.stem)
        label = _label_from_tag(tag, country)
        wmape = rd.get("total_wmape_mean") or rd.get("wmape_mean")
        if wmape is not None:
            results.setdefault(label, []).append(float(wmape))

    for p in sorted(meta_dir.glob("*.json")):
        try:
            d = json.loads(p.read_text())
        except Exception:
            continue
        label = d.get("config_label", _label_from_tag(p.stem, country))
        meta.setdefault(label, d)

    expected = EXPECTED_CONFIGS[country]
    missing = sorted(expected - set(results))
    extra = sorted(set(results) - expected)
    incomplete = {k: len(v) for k, v in results.items() if len(v) != expected_seeds}

    print(f"\n{'=' * 72}")
    print(f"Phase 4E-B [{country.upper()}] {root.name}")
    print(f"{'=' * 72}")
    print(f"configs={len(results)} expected={len(expected)} jsons={sum(len(v) for v in results.values())}")
    if missing:
        print(f"ERROR missing configs: {missing}")
    if extra:
        print(f"WARNING extra configs: {extra}")
    if incomplete:
        print(f"ERROR incomplete seeds (expected {expected_seeds}): {incomplete}")

    rows = []
    for label in sorted(results, key=lambda x: np.mean(results[x])):
        vals = results[label]
        m = meta.get(label, {})
        rows.append((label, np.mean(vals), np.std(vals), len(vals), m.get("feature_policy"), m.get("tensor_policy")))

    print(f"{'label':<28} {'mean':>10} {'std':>10} {'n':>3} {'features':<22} {'tensor'}")
    print("-" * 90)
    for label, mean, std, n, feat, tensor in rows:
        print(f"{label:<28} {mean:>10.6f} {std:>10.6f} {n:>3} {str(feat):<22} {tensor}")

    best = rows[0] if rows else None
    b0 = results.get("b0_baseline_annual")
    if best and b0:
        b0_mean = float(np.mean(b0))
        print(f"\nBest: {best[0]} ({best[1]:.6f}); delta vs b0={best[1] - b0_mean:+.6f}")

    return {
        "country": country,
        "root": str(root),
        "missing": missing,
        "extra": extra,
        "incomplete": incomplete,
        "rows": rows,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Audit Phase 4E-B results")
    ap.add_argument("--root-fr", type=Path)
    ap.add_argument("--root-nl", type=Path)
    ap.add_argument("--root-be", type=Path)
    ap.add_argument("--root-pt", type=Path)
    ap.add_argument("--expected-seeds", type=int, default=10)
    args = ap.parse_args()

    roots = {c: getattr(args, f"root_{c}") for c in ("fr", "nl", "be", "pt")}
    roots = {c: r for c, r in roots.items() if r is not None}
    if not roots:
        ap.error("Provide at least one --root-fr/--root-nl/--root-be/--root-pt")

    reports = [audit_country(c, r, expected_seeds=args.expected_seeds) for c, r in roots.items()]
    failed = any(r["missing"] or r["incomplete"] for r in reports)
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
