"""Phase 5 smoke test: NL, eval_years=[2021,2022,2023], seeds=[42,43,44].

Runs all hypotheses:
  Linear (Ridge): H0, H0b, H1-linear, H2-linear, PC-temporal-linear, PC-territory-linear
  Neural (MLP):   H1-neural, H2-neural, PC-temporal-neural, PC-territory-neural

Naming: H1/H2-linear = Ridge on pooled 1D graph features (NOT neural).
        H1/H2-neural = sklearn MLPRegressor on 9D per-sector features.

Runtime target: < 10 min on laptop. Outputs JSON and stdout table.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from src.modeles.phase5.manifest import verify_manifest
from src.modeles.phase5.rolling_origin import (
    run_country,
    summarise,
    gate_h2_neural,
    gate_h2_vs_controls,
    HYPOTHESES_LINEAR,
    HYPOTHESES_NEURAL,
)

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
PANEL_PATH = BASE / "data/processed/economic_graph/sector_panel_fr_nl_pt.csv"
COUNTRY = "NL"
EVAL_YEARS = [2021, 2022, 2023]
SEEDS = [42, 43, 44]
HYPOTHESES = HYPOTHESES_LINEAR + HYPOTHESES_NEURAL
WMAPE_GATE_THRESHOLD = 0.01
NO_REGRESSION_VS_H0B = 0.10


def _fmt(v: float) -> str:
    return f"{v:.4f}" if np.isfinite(v) else "  nan "


def main() -> None:
    t0 = time.time()
    print("=== Phase 5 Smoke Test: NL ===")
    print(f"Eval years: {EVAL_YEARS}  |  Seeds: {SEEDS}")
    print(f"Hypotheses: {list(HYPOTHESES)}")
    print()

    # 1. Manifest
    print("[1/5] Verifying L2 artifact checksums...")
    ok = verify_manifest(strict=False)
    for rel, passed in ok.items():
        print(f"  {'OK  ' if passed else 'MISMATCH'} {rel}")
    if not all(ok.values()):
        print("  WARNING: checksum mismatches — results may differ from frozen artifacts")
    print()

    # 2. Load panel
    print("[2/5] Loading sector panel...")
    panel = pd.read_csv(PANEL_PATH, low_memory=False)
    nl = panel[panel["country"].eq(COUNTRY)]
    print(f"  NL rows: {len(nl):,}  |  regions: {nl['region_id'].nunique()}")
    print()

    # 3. Run per seed
    print("[3/5] Rolling-origin evaluation (all seeds)...")
    all_results = []
    seed_summaries = {}
    for seed in SEEDS:
        t_seed = time.time()
        results = run_country(
            panel=panel, country=COUNTRY,
            eval_years=EVAL_YEARS,
            hypotheses=HYPOTHESES,
            seed=seed,
        )
        elapsed = time.time() - t_seed
        all_results.extend(results)
        seed_summaries[seed] = summarise(results)
        n_ok = sum(1 for r in results if np.isfinite(r.wmape))
        print(f"  seed={seed}: {n_ok}/{len(results)} results OK  ({elapsed:.1f}s)")
    print()

    # 4. Aggregate across seeds
    print("[4/5] Aggregated summary (mean over seeds)")
    import pandas as pd_
    df = pd_.DataFrame([
        {"hypothesis": r.hypothesis, "eval_year": r.eval_year,
         "wmape": r.wmape, "alpha_ratio": r.alpha_ratio,
         "any_nan": r.any_nan, "any_inf": r.any_inf, "leakage_ok": r.leakage_ok}
        for r in all_results
    ])

    agg = {}
    for hyp in HYPOTHESES:
        sub = df[df["hypothesis"] == hyp]
        if len(sub) == 0:
            agg[hyp] = {"mean_wmape": float("nan")}
            continue
        agg[hyp] = {
            "mean_wmape": float(sub["wmape"].mean()),
            "std_wmape": float(sub["wmape"].std()),
            "mean_alpha_ratio": float(sub["alpha_ratio"].mean()),
            "any_nan": bool(sub["any_nan"].any()),
            "any_inf": bool(sub["any_inf"].any()),
            "all_leakage_ok": bool(sub["leakage_ok"].all()),
            "n_eval_seeds": int(len(sub)),
            "wmape_by_year": {
                int(y): float(sub[sub["eval_year"] == y]["wmape"].mean())
                for y in EVAL_YEARS
            },
        }

    # Print table
    header = f"{'Hypothesis':<22} {'MeanWMAPE':>10} {'StdWMAPE':>9} {'AlphaRatio':>11} {'NaN':>4} {'Inf':>4} {'Leak':>6}"
    print(header)
    print("-" * len(header))
    for hyp in HYPOTHESES:
        s = agg.get(hyp, {})
        if not s or np.isnan(s.get("mean_wmape", float("nan"))):
            print(f"{hyp:<22}   N/A")
            continue
        print(
            f"{hyp:<22}"
            f"{s['mean_wmape']:>10.4f}"
            f"{s['std_wmape']:>9.4f}"
            f"{s['mean_alpha_ratio']:>11.4f}"
            f"{'Y' if s['any_nan'] else 'N':>4}"
            f"{'Y' if s['any_inf'] else 'N':>4}"
            f"{'OK' if s['all_leakage_ok'] else 'FAIL':>6}"
        )
    print()

    # Per-year WMAPE
    print("WMAPE by year (mean over seeds):")
    yr_header = f"{'Year':>6}" + "".join(f"{h:>14}" for h in HYPOTHESES)
    print(yr_header)
    print("-" * len(yr_header))
    for yr in EVAL_YEARS:
        row = f"{yr:>6}"
        for hyp in HYPOTHESES:
            val = agg.get(hyp, {}).get("wmape_by_year", {}).get(yr, float("nan"))
            row += f"{val:>14.4f}"
        print(row)
    print()

    # Correction norms per hypothesis
    print("Correction amplitude (mean |correction| / mean |baseline| per region-year):")
    for hyp in HYPOTHESES_NEURAL + ("H1-linear", "H2-linear"):
        s = agg.get(hyp, {})
        ar = s.get("mean_alpha_ratio", float("nan"))
        print(f"  {hyp:<24}: alpha_ratio={ar:.4f}")
    print()

    # 5. Gate
    print("[5/5] Gate checks")
    gate_n = gate_h2_neural(agg, COUNTRY, WMAPE_GATE_THRESHOLD, NO_REGRESSION_VS_H0B)
    gate_l = gate_h2_vs_controls(agg, COUNTRY, WMAPE_GATE_THRESHOLD)

    print(f"\nNeural gate (H2-neural): {gate_n['note']}")
    for ctrl, info in gate_n.get("controls", {}).items():
        if isinstance(info, dict) and "beats" in info:
            sym = "✓" if info["beats"] else "✗"
            gain_str = f"gain={info.get('gain', float('nan')):+.4f}" if "gain" in info else str(info)
            print(f"  {sym} {ctrl:<28}: {gain_str}")

    print(f"\nLinear gate (H2-linear): {gate_l.get('note','?')}")
    for ctrl, info in gate_l.get("controls", {}).items():
        if isinstance(info, dict) and "beats" in info:
            sym = "✓" if info["beats"] else "✗"
            gain_str = f"gain={info.get('gain', float('nan')):+.4f}" if "gain" in info else str(info)
            print(f"  {sym} {ctrl:<28}: {gain_str}")

    print()
    all_leakage_ok = all(r.leakage_ok for r in all_results)
    any_nan = any(r.any_nan for r in all_results)
    any_inf = any(r.any_inf for r in all_results)
    print(f"Leakage: {'OK' if all_leakage_ok else 'FAIL'}  |  NaN: {'YES' if any_nan else 'no'}  |  Inf: {'YES' if any_inf else 'no'}")

    total = time.time() - t0
    print(f"\nTotal runtime: {total:.1f}s")

    # Save JSON
    out = {
        "smoke_test": {
            "country": COUNTRY, "eval_years": EVAL_YEARS, "seeds": SEEDS,
            "hypotheses": list(HYPOTHESES), "runtime_seconds": round(total, 2),
        },
        "aggregated_summary": {
            h: {k: (v if not isinstance(v, dict) else {str(k2): v2 for k2, v2 in v.items()})
                for k, v in s.items()}
            for h, s in agg.items()
        },
        "gate_neural": gate_n,
        "gate_linear": gate_l,
        "leakage_ok": all_leakage_ok,
        "any_nan": any_nan,
        "any_inf": any_inf,
    }
    out_path = BASE / "data/processed/phase5/smoke_nl_results.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"Results saved: {out_path}")

    # HPC decision
    decision = "HPC_READY" if gate_n["gate_passed"] else "HPC_BLOCKED"
    print(f"\n{'='*50}")
    print(f"DECISION: {decision}")
    if decision == "HPC_READY":
        print("Smoke gate cleared. Await supervisor confirmation before rsync+submit.")
    else:
        print("Smoke gate NOT cleared. Do not submit to HPC.")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
