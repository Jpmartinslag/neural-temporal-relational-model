"""Audit Phase 4E-C EU macro-signal ablation results."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

BASE = Path(__file__).resolve().parents[2]

EXPECTED_CONFIGS = {
    "fr": {"c0_winner_4e_b", "c1_gdp", "c2_labor", "c3_esi", "c4_all_eu", "c5_all_eu_perm"},
    "nl": {"c0_winner_4e_b", "c1_gdp", "c2_labor", "c3_esi", "c4_all_eu", "c5_all_eu_perm"},
    "be": {"c0_winner_4e_b", "c1_gdp", "c2_labor", "c3_esi", "c4_all_eu", "c5_all_eu_perm"},
    "pt": {"c0_winner_4e_b", "c1_gdp", "c2_labor", "c3_esi", "c4_all_eu", "c5_all_eu_perm"},
}

PHASE4E_B_BASELINES = {
    "fr": 0.1031,
    "nl": 0.1017,
    "be": 0.1488,
    "pt": 0.2286,
}


def _run_obj(data: dict) -> dict:
    if len(data) == 1 and isinstance(next(iter(data.values())), dict):
        return next(iter(data.values()))
    return data


def _label_from_tag(tag: str, country: str) -> str:
    prefix = f"phase4e_c_{country}_"
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

    print(f"\n{'=' * 80}")
    print(f"Phase 4E-C [{country.upper()}] {root.name}")
    print(f"{'=' * 80}")
    print(f"configs={len(results)} expected={len(expected)} jsons={sum(len(v) for v in results.values())}")
    if missing:
        print(f"ERROR missing configs: {missing}")
    if extra:
        print(f"WARNING extra configs: {extra}")
    if incomplete:
        print(f"ERROR incomplete seeds (expected {expected_seeds}): {incomplete}")

    c0_vals = results.get("c0_winner_4e_b", [])
    c0_mean = float(np.mean(c0_vals)) if c0_vals else None
    b4e_b = PHASE4E_B_BASELINES[country]

    rows = []
    for label in sorted(results, key=lambda x: np.mean(results[x])):
        vals = results[label]
        m = meta.get(label, {})
        mean_val = float(np.mean(vals))
        std_val = float(np.std(vals))
        delta_c0 = (mean_val - c0_mean) if c0_mean is not None else None
        is_perm = label == "c5_all_eu_perm"
        rows.append({
            "label": label,
            "mean": mean_val,
            "std": std_val,
            "n": len(vals),
            "delta_c0": delta_c0,
            "macro_set": m.get("macro_feature_set", "?"),
            "is_falsif": m.get("is_falsification_test", is_perm),
        })

    hdr = f"{'label':<22} {'mean':>10} {'std':>8} {'n':>3} {'Δc0':>8} {'macro_set':<14} {'falsif'}"
    print(hdr)
    print("-" * len(hdr))
    for r in rows:
        delta_str = f"{r['delta_c0']:+.6f}" if r["delta_c0"] is not None else "   N/A  "
        print(f"{r['label']:<22} {r['mean']:>10.6f} {r['std']:>8.6f} {r['n']:>3} {delta_str:>8} {str(r['macro_set']):<14} {r['is_falsif']}")

    # C0 vs Phase 4E-B baseline check
    if c0_mean is not None:
        delta_b = c0_mean - b4e_b
        flag = "OK" if abs(delta_b) < 0.005 else "WARN: c0 deviates >0.5% from 4E-B baseline"
        print(f"\nC0 vs Phase 4E-B baseline: {c0_mean:.6f} vs {b4e_b:.4f}  Δ={delta_b:+.6f}  [{flag}]")

    # Victory criteria
    print("\n--- Victory criteria ---")
    real_signals = [r for r in rows if not r["is_falsif"] and r["label"] != "c0_winner_4e_b"]
    perm_row = next((r for r in rows if r["label"] == "c5_all_eu_perm"), None)

    if c0_mean is not None:
        improvers = [r for r in real_signals if r["delta_c0"] is not None and r["delta_c0"] < -0.01]
        regressors = [r for r in real_signals if r["delta_c0"] is not None and r["delta_c0"] > 0.01]
        print(f"  Configs beating c0 by >1%: {[r['label'] for r in improvers]}")
        print(f"  Configs degrading c0 by >1%: {[r['label'] for r in regressors]}")

    if perm_row and c0_mean is not None:
        perm_delta = perm_row["delta_c0"]
        if perm_delta is not None:
            status = "OK" if perm_delta > -0.01 else "WARN: permuted EU beats c0 by >1% — spurious regularization"
            print(f"  C5 permuted Δc0={perm_delta:+.6f}  [{status}]")

    return {
        "country": country,
        "root": str(root),
        "missing": missing,
        "extra": extra,
        "incomplete": incomplete,
        "rows": rows,
        "c0_mean": c0_mean,
    }


def cross_country_summary(reports: list[dict]) -> None:
    print(f"\n{'=' * 80}")
    print("Cross-country EU signal summary")
    print(f"{'=' * 80}")
    signal_labels = ["c1_gdp", "c2_labor", "c3_esi", "c4_all_eu"]
    for sig in signal_labels:
        improvements = []
        for rep in reports:
            c0 = rep.get("c0_mean")
            row = next((r for r in rep["rows"] if r["label"] == sig), None)
            if row and c0 is not None and row["delta_c0"] is not None:
                improvements.append((rep["country"], row["delta_c0"]))
        countries_improving = [c for c, d in improvements if d < -0.005]
        countries_degrading = [c for c, d in improvements if d > 0.005]
        deltas_str = "  ".join(f"{c}:{d:+.4f}" for c, d in improvements)
        consistent = len(countries_improving) >= 2
        verdict = "CONSISTENT (>=2 countries)" if consistent else "NOT consistent (<2 countries)"
        print(f"\n  {sig:<14} {verdict}")
        print(f"    {deltas_str}")
        if countries_improving:
            print(f"    Improving: {countries_improving}")
        if countries_degrading:
            print(f"    Degrading: {countries_degrading}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Audit Phase 4E-C EU signals results")
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
    cross_country_summary(reports)
    failed = any(r["missing"] or r["incomplete"] for r in reports)
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
