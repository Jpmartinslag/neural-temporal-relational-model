"""
Phase 4 International Preflight — HERALD
Validates all three country panels before HPC launch.

Usage:
    python3 src/data/phase4_preflight.py

Exits with code 1 if ANY country panel fails validation.
Exits with code 0 if all panels pass.

Methodology rules enforced here:
  1. No invented years in main pipeline.
  2. No mixing of main result and sensitivity.
  3. No nowcast labelled as forecast.
  4. Portugal sector_births_tensor != Q7 effectifs.
  5. NL qtensor 2025 must NOT exist (no proxy in main panel).
  6. BE qtensor 2007 must NOT exist (NACE Rev.1 incompatible).
"""

import sys
import traceback
from pathlib import Path

import pandas as pd

BASE = Path(__file__).parents[2]

# ── Country configuration ────────────────────────────────────────────────────

COUNTRIES = {
    "NL": {
        "label": "Netherlands (COROP)",
        "tensor_type": "employment/effectifs",
        "tensor_equiv_q7": True,
        "births_path": BASE / "data/external/netherlands/processed/netherlands_births_panel.csv",
        "stock_path":  BASE / "data/external/netherlands/processed/netherlands_stock_panel.csv",
        "qtensor_path": BASE / "data/external/netherlands/processed/netherlands_qtensor_jobs_panel.csv",
        "qtensor_value_col": "jobs",
        "exp_zones_births": 40,
        "exp_zones_stock":  40,
        "exp_zones_qtensor": 40,
        "exp_years_births":  list(range(2015, 2026)),   # 2015-2025
        "exp_years_stock":   list(range(2015, 2026)),   # 2015-2025 (clipped)
        "exp_years_qtensor": list(range(2010, 2025)),   # 2010-2024 (CBS availability)
        "first_eval_year": 2016,
        # Proxy guards: these years MUST NOT appear in qtensor main panel
        "qtensor_forbidden_years": [2025],
        # NaN policy for qtensor
        "qtensor_nan_col": "jobs_suppressed",           # expected flag column
        "qtensor_nan_fill_policy": "suppressed cells filled as 0 (CBS disclosure control)",
    },
    "BE": {
        "label": "Belgium (arrondissements)",
        "tensor_type": "employment/effectifs",
        "tensor_equiv_q7": True,
        "births_path": BASE / "data/external/belgium/processed/belgium_births_panel.csv",
        "stock_path":  BASE / "data/external/belgium/processed/belgium_stock_panel.csv",
        "qtensor_path": BASE / "data/external/belgium/processed/belgium_qtensor_jobs_panel.csv",
        "qtensor_value_col": "jobs",
        "exp_zones_births": 42,
        "exp_zones_stock":  42,
        "exp_zones_qtensor": 42,
        "exp_years_births":  list(range(2007, 2021)),   # 2007-2020 (2007 kept for lag)
        "exp_years_stock":   list(range(2007, 2021)),   # 2007-2020 (2006 dropped)
        "exp_years_qtensor": list(range(2008, 2021)),   # 2008-2020 (NACE Rev.1 gap)
        "first_eval_year": 2009,  # main modelling window 2008-2020; first eval after lag
        # Proxy guards: 2007 MUST NOT appear in qtensor (NACE Rev.1 incompatible)
        "qtensor_forbidden_years": [2007],
        "qtensor_nan_col": None,
        "qtensor_nan_fill_policy": None,
    },
    "PT": {
        "label": "Portugal (NUTS3)",
        "tensor_type": "sector_births",           # NOT employment
        "tensor_equiv_q7": False,                 # CRITICAL: not Q7-equivalent
        "births_path": BASE / "data/external/portugal/processed/portugal_births_panel_nuts3.csv",
        "stock_path":  BASE / "data/external/portugal/processed/portugal_stock_panel_nuts3.csv",
        "qtensor_path": BASE / "data/external/portugal/processed/portugal_qtensor_births_cae_nuts3.csv",
        "qtensor_value_col": "births",
        "exp_zones_births": 25,
        "exp_zones_stock":  25,
        "exp_zones_qtensor": 25,
        "exp_years_births":  list(range(2008, 2023)),   # 2008-2022
        "exp_years_stock":   list(range(2008, 2023)),   # 2008-2022
        "exp_years_qtensor": list(range(2008, 2023)),   # 2008-2022
        "first_eval_year": 2009,
        "qtensor_forbidden_years": [],
        "qtensor_nan_col": None,
        "qtensor_nan_fill_policy": None,
    },
}

EXPECTED_A10 = {"A", "BE", "FZ", "GI", "JZ", "KZ", "LZ", "MN", "OPQ", "RSU"}


# ── Validation helpers ───────────────────────────────────────────────────────

def load(path: Path):
    if not path.exists():
        return None, f"FILE NOT FOUND: {path}"
    try:
        df = pd.read_csv(path, low_memory=False)
        return df, None
    except Exception as e:
        return None, f"READ ERROR: {e}"


def check_years(actual: list, expected: list, label: str, failures: list):
    missing = sorted(set(expected) - set(actual))
    extra = sorted(set(actual) - set(expected))
    if not missing and not extra:
        print(f"    years {actual[0]}-{actual[-1]} ✓")
        return True
    msg = f"{label}: year mismatch"
    if missing:
        msg += f" | missing={missing}"
    if extra:
        msg += f" | extra={extra}"
    failures.append(msg)
    return False


def validate_country(country: str, cfg: dict) -> bool:
    failures = []
    warnings_list = []

    print(f"\n{'='*62}")
    print(f"  {cfg['label']}")
    print(f"{'='*62}")
    print(f"  Tensor type     : {cfg['tensor_type']}")
    print(f"  Q7 equivalent   : {'YES (employment/effectifs)' if cfg['tensor_equiv_q7'] else 'NO — sector_births only (NOT employment)'}")
    print(f"  Main window     : births {cfg['exp_years_births'][0]}-{cfg['exp_years_births'][-1]}, "
          f"qtensor {cfg['exp_years_qtensor'][0]}-{cfg['exp_years_qtensor'][-1]}")
    print(f"  First eval year : {cfg['first_eval_year']}")

    # ── Load panels ──────────────────────────────────────────────────────────
    b, b_err = load(cfg["births_path"])
    s, s_err = load(cfg["stock_path"])
    q, q_err = load(cfg["qtensor_path"])

    for name, err in [("births", b_err), ("stock", s_err), ("qtensor/tensor", q_err)]:
        if err:
            failures.append(f"{name}: {err}")

    # ── Births ───────────────────────────────────────────────────────────────
    if b is not None:
        print(f"\n  [births]")
        n_zones_b = b["zone_id"].nunique()
        years_b = sorted(b["target_year"].unique().tolist())
        print(f"    rows={len(b)}, zones={n_zones_b} (exp {cfg['exp_zones_births']}), "
              f"years={years_b[0]}-{years_b[-1]}")
        if n_zones_b != cfg["exp_zones_births"]:
            failures.append(f"births: expected {cfg['exp_zones_births']} zones, got {n_zones_b}")
        check_years(years_b, cfg["exp_years_births"], "births", failures)
        nan_y = b["y"].isna().sum()
        nan_lag = b["side_lag_1"].isna().sum() if "side_lag_1" in b.columns else "MISSING_COL"
        nan_grow = b["growth_1y"].isna().sum() if "growth_1y" in b.columns else "MISSING_COL"
        if nan_y > 0:
            failures.append(f"births: NaN in y={nan_y} (must be 0)")
        else:
            print(f"    NaN in y=0 ✓")
        if nan_lag == "MISSING_COL":
            failures.append("births: column 'side_lag_1' missing")
        elif nan_lag != n_zones_b:
            failures.append(f"births: NaN side_lag_1={nan_lag}, expected {n_zones_b}")
        else:
            print(f"    NaN side_lag_1={nan_lag} ✓ (first-year lag)")
        neg_y = (b["y"] < 0).sum()
        if neg_y > 0:
            failures.append(f"births: {neg_y} negative y values")

    # ── Stock ────────────────────────────────────────────────────────────────
    if s is not None:
        print(f"\n  [stock]")
        n_zones_s = s["zone_id"].nunique()
        years_s = sorted(s["target_year"].unique().tolist())
        nan_s = s["stock"].isna().sum() if "stock" in s.columns else "MISSING_COL"
        print(f"    rows={len(s)}, zones={n_zones_s} (exp {cfg['exp_zones_stock']}), "
              f"years={years_s[0]}-{years_s[-1]}, NaN={nan_s}")
        if n_zones_s != cfg["exp_zones_stock"]:
            failures.append(f"stock: expected {cfg['exp_zones_stock']} zones, got {n_zones_s}")
        check_years(years_s, cfg["exp_years_stock"], "stock", failures)
        if nan_s == "MISSING_COL":
            failures.append("stock: column 'stock' missing")
        elif nan_s > 0:
            failures.append(f"stock: {nan_s} NaN values in main window")

    # ── Q-tensor / Sector-births tensor ──────────────────────────────────────
    if q is not None:
        val_col = cfg["qtensor_value_col"]
        tensor_label = "sector_births_tensor" if not cfg["tensor_equiv_q7"] else "qtensor_jobs"
        print(f"\n  [{tensor_label}]")
        n_zones_q = q["zone_id"].nunique()
        years_q = sorted(q["target_year"].unique().tolist())
        print(f"    rows={len(q)}, zones={n_zones_q} (exp {cfg['exp_zones_qtensor']}), "
              f"years={years_q[0]}-{years_q[-1]}")
        if n_zones_q != cfg["exp_zones_qtensor"]:
            failures.append(f"{tensor_label}: expected {cfg['exp_zones_qtensor']} zones, got {n_zones_q}")
        check_years(years_q, cfg["exp_years_qtensor"], tensor_label, failures)

        # A10 codes
        if "a10" in q.columns:
            codes = set(q["a10"].unique())
            missing_codes = EXPECTED_A10 - codes
            extra_codes = codes - EXPECTED_A10
            if not missing_codes and not extra_codes:
                print(f"    A10 codes: all 10 present ✓")
            else:
                failures.append(f"{tensor_label}: A10 mismatch — missing={missing_codes}, extra={extra_codes}")
        else:
            failures.append(f"{tensor_label}: 'a10' column missing")

        # Value column NaN
        if val_col in q.columns:
            nan_val = q[val_col].isna().sum()
            neg_val = (q[val_col] < 0).sum()
            sup_flag = cfg.get("qtensor_nan_col")
            if nan_val > 0 and sup_flag and sup_flag in q.columns:
                # NaN already handled by suppression flag policy
                print(f"    NaN in {val_col}: {nan_val} — already handled by {sup_flag} flag ✓")
            elif nan_val > 0:
                failures.append(f"{tensor_label}: {nan_val} NaN in '{val_col}' — no suppression flag column found")
            else:
                print(f"    NaN in {val_col}=0 ✓")
            if neg_val > 0:
                failures.append(f"{tensor_label}: {neg_val} negative values in '{val_col}'")

            # Suppression flag report (NL only)
            if sup_flag and sup_flag in q.columns:
                sup_total = int(q[sup_flag].sum())
                sup_rate = sup_total / len(q)
                print(f"    Suppressed cells (filled as 0): {sup_total} ({sup_rate:.1%})")
                if sup_rate >= 0.05:
                    failures.append(f"{tensor_label}: suppressed cell rate {sup_rate:.1%} >= 5% threshold")
                else:
                    print(f"    Suppressed cell rate < 5% threshold ✓")
                print(f"    NaN policy: {cfg['qtensor_nan_fill_policy']}")
        else:
            failures.append(f"{tensor_label}: value column '{val_col}' not found")

        # PT-specific: KZ all-zero expected
        if country == "PT" and "a10" in q.columns and val_col in q.columns:
            kz = q[q["a10"] == "KZ"][val_col]
            if len(kz) > 0 and (kz == 0).all():
                print(f"    KZ all-zero ✓ (finance absent from enterprise births — expected)")
            elif (kz > 0).any():
                warnings_list.append("PT sector_births_tensor: KZ has non-zero values (unexpected)")

        # Proxy guard
        for forbidden_yr in cfg["qtensor_forbidden_years"]:
            if forbidden_yr in years_q:
                failures.append(
                    f"{tensor_label}: PROXY GUARD FAIL — year {forbidden_yr} present "
                    f"in main panel (must not exist in main pipeline)"
                )
            else:
                print(f"    [PROXY GUARD] year {forbidden_yr} absent ✓ CLEAN")

        # Q7 guard for Portugal
        if not cfg["tensor_equiv_q7"]:
            print(f"    [Q7 GUARD] This tensor is '{cfg['tensor_type']}', NOT Q7 effectifs.")
            print(f"    [Q7 GUARD] Do NOT label as Q7 in any config, paper, or dashboard.")

    # ── Cross-panel zone consistency ──────────────────────────────────────────
    print(f"\n  [cross-panel zones]")
    zone_sets = {}
    for name, df in [("births", b), ("stock", s), ("qtensor", q)]:
        if df is not None and "zone_id" in df.columns:
            zone_sets[name] = set(df["zone_id"].unique())
    panels = list(zone_sets.keys())
    for i in range(len(panels)):
        for j in range(i + 1, len(panels)):
            p1, p2 = panels[i], panels[j]
            sym = zone_sets[p1].symmetric_difference(zone_sets[p2])
            if not sym:
                print(f"    {p1} ∩ {p2}: identical zone_ids ✓")
            else:
                failures.append(f"zone mismatch {p1}↔{p2}: symmetric_diff={sorted(sym)}")

    # ── Result ────────────────────────────────────────────────────────────────
    print(f"\n  {'─'*58}")
    if failures:
        print(f"  PREFLIGHT RESULT: *** FAIL — DO NOT LAUNCH HPC ***")
        for f in failures:
            print(f"    ✗ {f}")
    else:
        print(f"  PREFLIGHT RESULT: PASS ✓")
    for w in warnings_list:
        print(f"    ⚠ {w}")

    return len(failures) == 0


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("\n" + "=" * 62)
    print("  HERALD Phase 4 — International Panel Preflight")
    print("=" * 62)

    results = {}
    for country, cfg in COUNTRIES.items():
        try:
            results[country] = validate_country(country, cfg)
        except Exception as e:
            print(f"\n  ERROR during {country} validation: {e}")
            traceback.print_exc()
            results[country] = False

    # ── Summary table ─────────────────────────────────────────────────────────
    print("\n\n" + "=" * 62)
    print("  SUMMARY")
    print("=" * 62)
    header = f"{'Country':<12} {'Tensor type':<22} {'Q7-equiv':<10} {'HPC ready':<10}"
    print(header)
    print("─" * 62)
    all_pass = True
    for country, cfg in COUNTRIES.items():
        passed = results.get(country, False)
        all_pass = all_pass and passed
        q7 = "YES" if cfg["tensor_equiv_q7"] else "NO (sector_births)"
        ready = "✓ YES" if passed else "✗ NO"
        print(f"  {country:<10} {cfg['tensor_type']:<22} {q7:<20} {ready}")

    print("─" * 62)
    if all_pass:
        print("\n  OVERALL: ALL PASS — Phase 4A panels ready for HPC preparation.")
    else:
        print("\n  OVERALL: *** FAIL — Resolve issues above before launching HPC. ***")
    print("=" * 62 + "\n")

    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
