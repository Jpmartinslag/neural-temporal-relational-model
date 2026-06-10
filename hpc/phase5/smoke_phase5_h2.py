"""Phase 5 smoke test: NL, 3 eval years, seed=42, all hypotheses.

Runtime target: < 5 minutes on a laptop. No GPU required.
Outputs JSON summary + per-year WMAPE table to stdout.
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
    gate_h2_vs_controls,
    HYPOTHESES_LOCAL,
)

import pandas as pd

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
PANEL_PATH = BASE / "data/processed/economic_graph/sector_panel_fr_nl_pt.csv"
COUNTRY = "NL"
EVAL_YEARS = [2021, 2022, 2023]
SEED = 42
HYPOTHESES = HYPOTHESES_LOCAL  # H0, H0b, H1, H2, PC-temporal, PC-territory
WMAPE_GATE_THRESHOLD = 0.01


def main() -> None:
    t0 = time.time()

    print("=== Phase 5 Smoke Test: NL ===")
    print(f"Eval years: {EVAL_YEARS}  |  Seed: {SEED}")
    print()

    # 1. Manifest check
    print("[1/4] Verifying L2 artifact checksums...")
    try:
        ok = verify_manifest(strict=False)
        for rel, passed in ok.items():
            status = "OK" if passed else "MISMATCH"
            print(f"  {status}  {rel}")
        if not all(ok.values()):
            print("  WARNING: checksum mismatches detected — results may not match HPC artifacts")
    except Exception as e:
        print(f"  ERROR: {e}")
    print()

    # 2. Load panel
    print("[2/4] Loading sector panel...")
    panel = pd.read_csv(PANEL_PATH)
    nl_panel = panel[panel["country"].eq(COUNTRY)].copy()
    print(f"  NL rows: {len(nl_panel):,}  |  regions: {nl_panel['region_id'].nunique()}")
    print(f"  years in panel: {sorted(nl_panel['available_for_forecast_year'].unique())}")
    print()

    # 3. Run rolling-origin evaluation
    print("[3/4] Running rolling-origin evaluation...")
    results = run_country(
        panel=panel,
        country=COUNTRY,
        eval_years=EVAL_YEARS,
        hypotheses=HYPOTHESES,
        seed=SEED,
    )
    elapsed = time.time() - t0
    print(f"  Done in {elapsed:.1f}s  |  {len(results)} result rows")
    print()

    # 4. Summarise and gate
    print("[4/4] Results summary")
    summary = summarise(results)
    gate = gate_h2_vs_controls(summary, COUNTRY, WMAPE_GATE_THRESHOLD)

    # Per-hypothesis table
    header = f"{'Hypothesis':<14} {'MeanWMAPE':>10} {'StdWMAPE':>9} {'AlphaRatio':>11} {'NaN':>4} {'Inf':>4} {'Leakage':>8}"
    print(header)
    print("-" * len(header))
    for hyp in HYPOTHESES:
        if hyp not in summary:
            print(f"  {hyp}: not computed")
            continue
        s = summary[hyp]
        print(
            f"{hyp:<14}"
            f"{s['mean_wmape']:>10.4f}"
            f"{s['std_wmape']:>9.4f}"
            f"{s['mean_alpha_ratio']:>11.4f}"
            f"{'Y' if s['any_nan_any_year'] else 'N':>4}"
            f"{'Y' if s['any_inf_any_year'] else 'N':>4}"
            f"{'OK' if s['all_leakage_ok'] else 'FAIL':>8}"
        )
    print()

    # Per-year breakdown
    print("WMAPE by year:")
    hyp_header = f"{'Year':>6}" + "".join(f"{h:>14}" for h in HYPOTHESES)
    print(hyp_header)
    print("-" * len(hyp_header))
    for yr in EVAL_YEARS:
        row = f"{yr:>6}"
        for hyp in HYPOTHESES:
            if hyp not in summary:
                row += f"{'N/A':>14}"
                continue
            val = summary[hyp]["wmape_by_year"].get(yr, float("nan"))
            row += f"{val:>14.4f}"
        print(row)
    print()

    # Gate
    gate_status = "PROMOTED" if gate["gate_passed"] else "NOT_PROMOTED"
    print(f"H2 gate ({WMAPE_GATE_THRESHOLD:.0%} threshold): {gate_status}")
    for ctrl, info in gate.get("controls", {}).items():
        if isinstance(info, dict) and "gain" in info:
            beats = "✓" if info["beats"] else "✗"
            print(f"  H2 vs {ctrl:<14}: gain={info['gain']:+.4f}  {beats}")
    print()

    # Leakage summary
    print("Leakage audit:")
    all_ok = all(r.leakage_ok for r in results)
    print(f"  All leakage checks OK: {all_ok}")
    if not all_ok:
        bad = [(r.hypothesis, r.eval_year) for r in results if not r.leakage_ok]
        print(f"  VIOLATIONS: {bad}")
    print()

    total_elapsed = time.time() - t0
    print(f"Total runtime: {total_elapsed:.1f}s")

    # Save JSON
    out = {
        "smoke_test": {
            "country": COUNTRY,
            "eval_years": EVAL_YEARS,
            "seed": SEED,
            "runtime_seconds": round(total_elapsed, 2),
        },
        "summary": summary,
        "gate": gate,
        "leakage_ok": all_ok,
    }

    out_path = BASE / "data/processed/phase5/smoke_nl_results.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"Results saved: {out_path}")


if __name__ == "__main__":
    main()
