"""
Netherlands Phase 4 — Data Ingestion
Target  : 83631NED  births (OprichtingenVanVestigingen) × COROP, 2015-2025
Q-tensor: 83582NED  employee jobs × SBI-A10 aggregate × COROP, 2010-2024
           NOTE: 2025 data not available from CBS as of current pipeline.
           For lag-1 models predicting 2025 target, qtensor year 2024 is
           the correct input (Q7 uses qtensor[t-1]). Do NOT proxy 2025 jobs
           in the main pipeline. Proxy only allowed as a sensitivity test,
           explicitly flagged and never presented as a main result.
Stock   : 81578NED  total establishments stock × COROP, clipped to 2015-2025
           Raw CBS table extends 2007-2026. Years 2007-2014 have NaN stock
           (CBS does not publish COROP totals before 2015). Year 2026 is a
           CBS preliminary estimate and is excluded from the main panel.

NaN policy for qtensor (CBS statistical disclosure control):
  Some small-zone × sector cells are suppressed by CBS. These appear as NaN
  in the jobs column. Policy for main pipeline:
    - A 'jobs_suppressed' flag column is added (1 = suppressed, 0 = observed).
    - Suppressed cells are filled with 0 for first-pass modelling.
    - This imputation is NOT silent: this docstring and preflight() both report
      the suppressed cell count. Results using suppressed zones should be
      treated as sensitivity output, not as main results.
    - If <5% of cells per A10 are suppressed, proceed with 0-fill.
    - If >=5% of cells for any A10 are suppressed, raise a warning.

A10 mapping via CBS aggregate SBI codes (available as-is at COROP level):
  A       → 301000
  BE      → 300002  (B-E, industry+energy excl. construction)
  FZ      → 350000  (F, construction)
  GI      → 300006  (G-I, trade+transport+hospitality)
  JZ      → 391600  (J, information+communication)
  KZ      → 396300  (K, finance)
  LZ      → 402000  (L, real estate)
  MN      → 300010  (M-N, professional+business services)
  OPQ     → 300012  (O-Q, government+education+health)
  RSU     → 300014  (R-U, culture+other; T+U negligible)
"""

import time
from pathlib import Path

import pandas as pd
import requests

OUT_DIR  = Path(__file__).parents[2] / "data/external/netherlands"
RAW_DIR  = OUT_DIR / "raw/cbs"
PROC_DIR = OUT_DIR / "processed"

# A10 SBI code mapping for 83582NED
A10_SBI_CODES = {
    "A":   "301000",
    "BE":  "300002",
    "FZ":  "350000",
    "GI":  "300006",
    "JZ":  "391600",
    "KZ":  "396300",
    "LZ":  "402000",
    "MN":  "300010",
    "OPQ": "300012",
    "RSU": "300014",
}
SBI_TO_A10 = {v.strip(): k for k, v in A10_SBI_CODES.items()}


def fetch_cbs_filtered(table: str, filter_str: str, cache_path: Path) -> pd.DataFrame:
    """Download all pages of a CBS ODataFeed table with a server-side filter."""
    if cache_path.exists():
        print(f"  {table} — cached ({cache_path.name})")
        return pd.read_csv(cache_path)

    base = f"https://opendata.cbs.nl/ODataFeed/odata/{table}/TypedDataSet"
    rows_all = []
    skip = 0
    while True:
        url = f"{base}?$top=9999&$skip={skip}&$filter={filter_str}&$format=json"
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        batch = r.json().get("value", [])
        rows_all.extend(batch)
        print(f"    {table} skip={skip}: {len(batch)} rows (total {len(rows_all)})")
        if len(batch) < 9999:
            break
        skip += 9999
        time.sleep(0.3)

    df = pd.DataFrame(rows_all)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(cache_path, index=False)
    print(f"  saved {cache_path.name} ({len(df)} rows)")
    return df


# CBS includes CR98 (residual not-elsewhere-classified) and CR99 (national total).
# Both are aggregate zones, NOT functional COROP regions. They must be excluded
# from all main panels. This filter is applied in every build_* function.
_COROP_AGGREGATE_ZONES = {"CR98", "CR99"}


def build_births_panel(df: pd.DataFrame) -> pd.DataFrame:
    """83631NED → births per COROP zone per year.
    Excludes aggregate zones CR98 and CR99 (national aggregates, not COROP regions).
    """
    births_col = "OprichtingenVanVestigingen_1"
    df = df.copy()
    df = df[df["BedrijfstakkenBranchesSBI2008"].str.strip() == "T001081"].copy()
    df = df[df[births_col].notna()].copy()
    df["zone_id"]     = df["RegioS"].str.strip()
    # Exclude CBS national aggregate codes — not functional COROP regions
    df = df[~df["zone_id"].isin(_COROP_AGGREGATE_ZONES)].copy()
    df["target_year"] = df["Perioden"].str[:4].astype(int)
    df["y"]           = pd.to_numeric(df[births_col], errors="coerce")
    df = df[["zone_id", "target_year", "y"]].sort_values(["zone_id", "target_year"])
    df["side_lag_1"] = df.groupby("zone_id")["y"].shift(1)
    df["growth_1y"]  = (df["y"] - df["side_lag_1"]) / df["side_lag_1"]
    return df.reset_index(drop=True)


def build_stock_panel(df: pd.DataFrame) -> pd.DataFrame:
    """81578NED → total establishment stock per COROP per year.

    Main pipeline window: 2015-2025 only.
      - Pre-2015 rows are dropped (CBS does not publish COROP totals before 2015).
      - Year 2026 is dropped (CBS preliminary estimate, outside model scope).
    """
    df = df.copy()
    df = df[df["BedrijfstakkenBranchesSBI2008"].str.strip() == "T001081"].copy()
    df["zone_id"]     = df["RegioS"].str.strip()
    # Exclude CBS national aggregate codes — not functional COROP regions
    df = df[~df["zone_id"].isin(_COROP_AGGREGATE_ZONES)].copy()
    df["target_year"] = df["Perioden"].str[:4].astype(int)
    df["stock"]       = pd.to_numeric(df["Vestigingen_1"], errors="coerce")
    # Clip to main modelling window — DO NOT remove this filter without updating
    # the methodology note in the docstring above.
    df = df[df["target_year"].between(2015, 2025)].copy()
    return df[["zone_id", "target_year", "stock"]].sort_values(["zone_id", "target_year"])


def build_qtensor(df: pd.DataFrame) -> pd.DataFrame:
    """83582NED → employee jobs × A10 × COROP × year.

    Source window: 2010-2024 (CBS availability). 2025 is NOT available and is
    NOT filled in the main pipeline. For lag-1 models, target year 2025 uses
    qtensor year 2024 as input — no proxy needed.

    NaN policy: CBS suppresses small counts for privacy (statistical disclosure
    control). These appear as NaN in 'jobs'. This function:
      1. Adds a 'jobs_suppressed' flag (1 = CBS-suppressed, 0 = observed).
      2. Fills suppressed NaN values with 0 for first-pass modelling.
    See module docstring for the full policy rationale.
    """
    df = df.copy()
    df["zone_id"]     = df["RegioS"].str.strip()
    # Exclude CBS national aggregate codes — not functional COROP regions
    df = df[~df["zone_id"].isin(_COROP_AGGREGATE_ZONES)].copy()
    df["target_year"] = df["Perioden"].str[:4].astype(int)
    df["sbi_key"]     = df["BedrijfstakkenBranchesSBI2008"].str.strip()
    df["jobs"]        = pd.to_numeric(df["BanenVanWerknemersInDecember_1"], errors="coerce")
    df["a10"]         = df["sbi_key"].map(SBI_TO_A10)
    df = df[df["a10"].notna()].copy()
    # Flag suppressed cells before filling
    df["jobs_suppressed"] = df["jobs"].isna().astype(int)
    df["jobs"]            = df["jobs"].fillna(0)
    return df[["zone_id", "target_year", "a10", "jobs", "jobs_suppressed"]].sort_values(
        ["zone_id", "target_year", "a10"]
    ).reset_index(drop=True)


def preflight(births: pd.DataFrame, qtensor: pd.DataFrame, stock: pd.DataFrame) -> None:
    """Phase 4 preflight for Netherlands. Validates windows, NaN policy, and
    methodological constraints. Any FAIL here blocks HPC launch."""
    import sys
    failures = []
    warnings = []

    print("\n=== PREFLIGHT — Netherlands (Phase 4) ===")
    print(f"  Tensor type       : employment/effectifs (CBS employee jobs)")
    print(f"  Tensor label      : qtensor_jobs (equivalent to Q7 effectifs)")

    # --- Births ---
    zones_b = births["zone_id"].nunique()
    years_b = sorted(births["target_year"].unique())
    exp_years_b = list(range(2015, 2026))
    print(f"\nBirths:")
    print(f"  Rows={len(births)}, zones={zones_b} (expected 40), years={years_b[0]}-{years_b[-1]}")
    if zones_b != 40:
        failures.append(f"births: expected 40 COROP zones, got {zones_b}")
    if sorted(years_b) != exp_years_b:
        failures.append(f"births: year range {years_b[0]}-{years_b[-1]} != expected 2015-2025")
    nan_lag = births["side_lag_1"].isna().sum()
    if nan_lag != zones_b:
        failures.append(f"births: NaN side_lag_1={nan_lag}, expected {zones_b} (one per zone, first year)")
    else:
        print(f"  NaN side_lag_1={nan_lag} ✓ (first-year lag, expected)")
    cr99_b = births[births["zone_id"] == "CR99"]
    if not cr99_b.empty:
        warnings.append("births: CR99 (aggregate) present — exclude in modelling")

    # --- Stock ---
    zones_s = stock["zone_id"].nunique()
    years_s = sorted(stock["target_year"].unique())
    exp_years_s = list(range(2015, 2026))
    nan_stock = stock["stock"].isna().sum()
    print(f"\nStock:")
    print(f"  Rows={len(stock)}, zones={zones_s}, years={years_s[0]}-{years_s[-1]}, NaN={nan_stock}")
    if sorted(years_s) != exp_years_s:
        failures.append(f"stock: year range {years_s[0]}-{years_s[-1]} != expected 2015-2025")
    if nan_stock > 0:
        failures.append(f"stock: {nan_stock} NaN values in main window 2015-2025")

    # --- Q-tensor ---
    a10_found = sorted(qtensor["a10"].unique())
    zones_q   = qtensor["zone_id"].nunique()
    years_q   = sorted(qtensor["target_year"].unique())
    exp_years_q = list(range(2010, 2025))  # 2010-2024 from CBS availability
    suppressed_total = qtensor["jobs_suppressed"].sum() if "jobs_suppressed" in qtensor.columns else "col missing"
    print(f"\nQ-tensor (employment/effectifs — CBS 83582NED):")
    print(f"  Rows={len(qtensor)}, zones={zones_q}, A10={len(a10_found)}, years={years_q[0]}-{years_q[-1]}")
    print(f"  Source window: 2010-2024 (CBS; 2025 NOT available, NOT proxied in main pipeline)")
    print(f"  Suppressed cells (jobs_suppressed=1, filled as 0): {suppressed_total}")
    if sorted(years_q) != exp_years_q:
        failures.append(f"qtensor: year range {years_q[0]}-{years_q[-1]} != expected 2010-2024")
    missing_a10 = set(A10_SBI_CODES.keys()) - set(a10_found)
    if missing_a10:
        failures.append(f"qtensor: missing A10 codes: {missing_a10}")
    if isinstance(suppressed_total, int):
        total_cells = len(qtensor)
        sup_rate = suppressed_total / total_cells if total_cells > 0 else 0
        if sup_rate >= 0.05:
            failures.append(f"qtensor: suppressed cell rate {sup_rate:.1%} >= 5% threshold")
        else:
            print(f"  Suppressed cell rate: {sup_rate:.1%} < 5% threshold ✓")
        per_a10 = qtensor.groupby("a10")["jobs_suppressed"].sum()
        high = per_a10[per_a10 / (total_cells / len(a10_found)) >= 0.05]
        if not high.empty:
            for code, cnt in high.items():
                warnings.append(f"qtensor: A10={code} has {cnt} suppressed cells (>=5% of rows for this code)")
    else:
        failures.append("qtensor: jobs_suppressed column missing")
    print(f"  A10 codes: {a10_found}")

    # --- Proxy guard ---
    if 2025 in years_q:
        failures.append("qtensor: year 2025 present — potential proxy contamination in main panel")
    print(f"\n  [PROXY GUARD] qtensor 2025 absent: {'✓ CLEAN' if 2025 not in years_q else '✗ FAIL — remove proxy'}")

    # --- First eval year ---
    first_eval = max(min(years_b) + 1, min(years_q) + 1, min(years_s) + 1)
    print(f"  First evaluation year (after lags): {first_eval}")

    # --- Summary ---
    print("\n" + "=" * 36)
    if failures:
        print("PREFLIGHT RESULT: *** FAIL — DO NOT LAUNCH HPC ***")
        for f in failures:
            print(f"  FAIL: {f}")
    else:
        print("PREFLIGHT RESULT: PASS")
    for w in warnings:
        print(f"  WARN: {w}")
    print("=" * 36)
    if failures:
        sys.exit(1)


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROC_DIR.mkdir(parents=True, exist_ok=True)

    corop_filter = "startswith(RegioS,'CR')"

    # 1. Births — 83631NED
    print("=== 83631NED births × COROP ===")
    df_births_raw = fetch_cbs_filtered(
        "83631NED", corop_filter,
        cache_path=RAW_DIR / "83631NED_corop.csv",
    )
    births = build_births_panel(df_births_raw)
    births.to_csv(PROC_DIR / "netherlands_births_panel.csv", index=False)
    print(f"  births panel: {len(births)} rows")

    # 2. Stock — 81578NED
    print("\n=== 81578NED stock × COROP ===")
    df_stock_raw = fetch_cbs_filtered(
        "81578NED", corop_filter,
        cache_path=RAW_DIR / "81578NED_corop.csv",
    )
    stock = build_stock_panel(df_stock_raw)
    stock.to_csv(PROC_DIR / "netherlands_stock_panel.csv", index=False)
    print(f"  stock panel: {len(stock)} rows")

    # 3. Q-tensor — 83582NED employment × A10 × COROP
    # Fetch all COROP rows then filter A10 codes in Python (CBS 'in' operator not supported)
    print("\n=== 83582NED jobs × A10 × COROP ===")
    df_jobs_raw = fetch_cbs_filtered(
        "83582NED", corop_filter,
        cache_path=RAW_DIR / "83582NED_corop.csv",
    )
    # Keep only A10-compatible SBI codes
    a10_keys = set(v.strip() for v in A10_SBI_CODES.values())
    df_jobs_raw = df_jobs_raw[
        df_jobs_raw["BedrijfstakkenBranchesSBI2008"].str.strip().isin(a10_keys)
    ].copy()
    qtensor = build_qtensor(df_jobs_raw)
    qtensor.to_csv(PROC_DIR / "netherlands_qtensor_jobs_panel.csv", index=False)
    print(f"  q-tensor: {len(qtensor)} rows")

    preflight(births, qtensor, stock)
    print("\nDone.")


if __name__ == "__main__":
    main()
