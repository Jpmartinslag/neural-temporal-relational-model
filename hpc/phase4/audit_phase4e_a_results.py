"""Audit Phase 4E-A results.

Usage:
    python3 hpc/phase4/audit_phase4e_a_results.py \\
        --root hpc_results/herald_phase4e_a_nl_20260601_r1 \\
        --country nl \\
        --phase4a-wmape 0.058184

    # All countries in one pass (one --root per country):
    python3 hpc/phase4/audit_phase4e_a_results.py \\
        --root-nl hpc_results/herald_phase4e_a_nl_20260601_r1 \\
        --root-be hpc_results/herald_phase4e_a_be_20260601_r1 \\
        --root-pt hpc_results/herald_phase4e_a_pt_20260601_r1 \\
        --root-fr hpc_results/herald_phase4e_a_fr_20260601_r1

Acceptance criteria (Phase 4E-A sanity check):
  - WMAPE within 2% of Phase 4A for NL/BE/PT (small regression acceptable)
  - Small differences explained by:
      * flag_forecast_safe corrected (first year now excluded)
      * NON_PREDICTIVE_FIELDS excluded (COVID flags not in x_ann)
      * Identity graph (same as Phase 4A)
  - Seed stability: σ < 0.008
  - If regression > 2%: must be investigated before Phase 4E-B/C/D
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[2]

PHASE4A_WMAPE = {
    "fr": None,       # Phase 4A FR used different pipeline (V6/V7); not directly comparable
    "nl": 0.058184,
    "be": 0.070900,
    "pt": 0.169900,
}


def load_results(run_root: Path, country: str) -> dict:
    jsons = list((run_root / "reports" / "per_run").glob("*.json"))
    configs = {}  # label → [wmape, ...]
    prefix = f"phase4e_a_{country}_"
    for jpath in jsons:
        data = json.loads(jpath.read_text())
        for _tag, rd in data.items():
            tag   = rd.get("run_tag", "")
            label = tag.replace(prefix, "")
            wmape = rd.get("total_wmape_mean") or rd.get("wmape_mean")
            if wmape is None:
                continue
            configs.setdefault(label, []).append(float(wmape))
    return {k: sorted(v) for k, v in configs.items()}


def load_metadata(run_root: Path, country: str) -> dict:
    meta_dir = run_root / "metadata"
    prefix   = f"phase4e_a_{country}_"
    result   = {}
    for mf in meta_dir.glob("*.json"):
        try:
            d = json.loads(mf.read_text())
        except Exception:
            continue
        label = d.get("config_label", mf.stem.replace(prefix, "").rsplit("_seed_", 1)[0])
        if label not in result:
            result[label] = {
                "features":           d.get("baseline_annual_features", []),
                "excluded":           d.get("non_predictive_fields_excluded", []),
                "tensor_policy":      d.get("tensor_policy", "?"),
                "graph_policy":       d.get("graph_policy", "?"),
                "feature_policy":     d.get("feature_policy", "?"),
            }
    return result


def audit_country(run_root, country, phase4a_wmape=None):
    # type: (Path, str, object) -> dict
    if not run_root.exists():
        print(f"  [{country.upper()}] ERROR: {run_root} does not exist")
        return {}

    configs  = load_results(run_root, country)
    meta     = load_metadata(run_root, country)
    n_seeds  = max((len(v) for v in configs.values()), default=0)
    n_total  = sum(len(v) for v in configs.values())
    expected = 10  # 1 config × 10 seeds

    print(f"\n{'='*60}")
    print(f"  Phase 4E-A [{country.upper()}]  {n_total} runs  {run_root.name}")
    print(f"{'='*60}")

    if n_total < expected:
        print(f"  WARNING: expected {expected} runs, got {n_total}")

    if not configs:
        print(f"  No results found.")
        return {}

    # Feature verification from metadata
    m = meta.get("baseline_annual", {})
    if m:
        print(f"\n  Feature verification:")
        print(f"    Features in x_ann : {m.get('features', '?')}")
        print(f"    Excluded (non-pred): {m.get('excluded', '?')}")
        print(f"    Tensor policy      : {m.get('tensor_policy', '?')}")
        print(f"    Graph policy       : {m.get('graph_policy', '?')}")
        # Hard check
        excluded = m.get("excluded", [])
        if "is_covid_year" in excluded and "is_post_covid_rebound" in excluded:
            print(f"    NON_PREDICTIVE_FIELDS exclusion: ✓")
        else:
            print(f"    NON_PREDICTIVE_FIELDS exclusion: ✗ CHECK METADATA")

    # Results table
    print(f"\n  {'Config':<30} {'N':>4} {'WMAPE mean':>12} {'±std':>8}")
    print(f"  {'-'*56}")
    results_out = {}
    for label, wmapes in sorted(configs.items()):
        mean = np.mean(wmapes)
        std  = np.std(wmapes)
        print(f"  {label:<30} {len(wmapes):>4}  {mean:>12.6f}  {std:>8.6f}")
        results_out[label] = {"mean": mean, "std": std, "n": len(wmapes), "wmapes": wmapes}

    # Acceptance criteria
    if configs and phase4a_wmape is not None:
        best_label  = min(configs, key=lambda k: np.mean(configs[k]))
        best_mean   = np.mean(configs[best_label])
        best_std    = np.std(configs[best_label])
        delta_pct   = (best_mean - phase4a_wmape) / phase4a_wmape * 100

        print(f"\n  Acceptance criteria vs Phase 4A (WMAPE={phase4a_wmape:.6f}):")
        print(f"  {'─'*50}")

        def chk(ok, msg):
            print(f"  {'✓' if ok else '✗'} {msg}")

        chk(abs(delta_pct) <= 2.0,
            f"Within 2% of Phase 4A: {best_mean:.6f} [{delta_pct:+.2f}%]")
        chk(best_std < 0.008,
            f"Seed stability σ < 0.008: σ={best_std:.6f}")
        chk(delta_pct <= 0.0,
            f"No regression (≤0%): {delta_pct:+.2f}%")

        if delta_pct > 2.0:
            print(f"\n  ⚠  REGRESSION > 2% — investigate before Phase 4E-B/C/D")
            print(f"     Possible causes:")
            print(f"     1. flag_forecast_safe corrected (−1 row/region) — expect tiny effect")
            print(f"     2. NON_PREDICTIVE_FIELDS excluded — COVID/rebound flags removed from x_ann")
            print(f"     3. Different Panel: European canonical vs Phase 4 original")
            print(f"     4. Splits changed (FR: eval_start=2016 vs original)")

        if country == "be" and n_seeds < 10:
            print(f"\n  ⚠  BE: {n_seeds} seeds completed, expected 10")

        results_out["_summary"] = {
            "best_label": best_label, "best_mean": best_mean,
            "best_std": best_std, "delta_pct": delta_pct,
            "phase4a_ref": phase4a_wmape, "n_total": n_total,
        }

    if country == "be":
        be_panel = BASE / "data/processed/phase4e/be/panel_ze2020.csv"
        if be_panel.exists():
            yr_max = pd.read_csv(be_panel)["target_year"].max()
            if yr_max < 2023:
                print(f"\n  ⚠  BE panel ends at {yr_max}. Cannot compare with NL ({{}}) or PT (2022). "
                      "Phase 4E-A sanity check valid; cross-country comparison requires BE extension.")

    if country == "fr":
        print(f"\n  Note: FR Phase 4E-A uses train_herald_semi_v2 (international pipeline).")
        print(f"  Phase 4A/V6/V7 reference WMAPE (0.020398) is from a different pipeline.")
        print(f"  For FR: compare Phase 4E-A vs Phase 4E-A only (seed stability).")

    return results_out


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit Phase 4E-A results")
    parser.add_argument("--root",    type=Path, help="Result root for single-country run")
    parser.add_argument("--country", choices=["fr","nl","be","pt"],
                        help="Country (required when using --root)")
    parser.add_argument("--root-fr", type=Path, default=None)
    parser.add_argument("--root-nl", type=Path, default=None)
    parser.add_argument("--root-be", type=Path, default=None)
    parser.add_argument("--root-pt", type=Path, default=None)
    parser.add_argument("--phase4a-wmape", type=float, default=None,
                        help="Phase 4A reference WMAPE for the country (overrides built-in default)")
    args = parser.parse_args()

    runs = {}
    if args.root:
        if not args.country:
            parser.error("--country required when using --root")
        runs[args.country] = args.root
    for c in ("fr","nl","be","pt"):
        r = getattr(args, f"root_{c}", None)
        if r:
            runs[c] = r

    if not runs:
        parser.error("Provide --root + --country, or --root-nl / --root-be / --root-pt / --root-fr")

    all_results = {}
    for c, root in runs.items():
        ref = args.phase4a_wmape if args.phase4a_wmape else PHASE4A_WMAPE.get(c)
        root_abs = BASE / root if not root.is_absolute() else root
        all_results[c] = audit_country(root_abs, c, ref)

    # Cross-country summary if multiple countries
    if len(all_results) > 1:
        print(f"\n{'='*60}")
        print(f"  Phase 4E-A Cross-country summary")
        print(f"{'='*60}")
        print(f"  {'Country':<8} {'WMAPE 4E-A':>12} {'vs 4A':>10} {'σ':>8} {'N':>4} {'Status':>10}")
        print(f"  {'─'*56}")
        for c, res in all_results.items():
            s = res.get("_summary", {})
            if not s:
                print(f"  {c.upper():<8} {'no data':>32}")
                continue
            delta = s["delta_pct"]
            status = "✓ OK" if abs(delta) <= 2.0 else "⚠ REGRESS" if delta > 2.0 else "✓ IMPROVE"
            ref_str = f"{s['phase4a_ref']:.4f}" if s["phase4a_ref"] else "—"
            print(f"  {c.upper():<8} {s['best_mean']:>12.6f} {delta:>+9.2f}% {s['best_std']:>8.6f} "
                  f"{s['n_total']:>4}   {status}")

    print()


if __name__ == "__main__":
    main()
