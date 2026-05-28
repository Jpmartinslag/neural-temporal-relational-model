"""
Netherlands Phase 4 — Data Ingestion
Target  : 83631NED  births (OprichtingenVanVestigingen) × COROP, 2015-2025
Q-tensor: 83582NED  employee jobs × SBI-A10 aggregate × COROP, 2010-2024
Stock   : 81578NED  total establishments stock × COROP, 2007-2026 (SIDE proxy)

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


def build_births_panel(df: pd.DataFrame) -> pd.DataFrame:
    """83631NED → births per COROP zone per year."""
    births_col = "OprichtingenVanVestigingen_1"
    df = df.copy()
    df = df[df["BedrijfstakkenBranchesSBI2008"].str.strip() == "T001081"].copy()
    df = df[df[births_col].notna()].copy()
    df["zone_id"]     = df["RegioS"].str.strip()
    df["target_year"] = df["Perioden"].str[:4].astype(int)
    df["y"]           = pd.to_numeric(df[births_col], errors="coerce")
    df = df[["zone_id", "target_year", "y"]].sort_values(["zone_id", "target_year"])
    df["side_lag_1"] = df.groupby("zone_id")["y"].shift(1)
    df["growth_1y"]  = (df["y"] - df["side_lag_1"]) / df["side_lag_1"]
    return df.reset_index(drop=True)


def build_stock_panel(df: pd.DataFrame) -> pd.DataFrame:
    """81578NED → total establishment stock per COROP per year."""
    df = df.copy()
    df = df[df["BedrijfstakkenBranchesSBI2008"].str.strip() == "T001081"].copy()
    df["zone_id"]     = df["RegioS"].str.strip()
    df["target_year"] = df["Perioden"].str[:4].astype(int)
    df["stock"]       = pd.to_numeric(df["Vestigingen_1"], errors="coerce")
    return df[["zone_id", "target_year", "stock"]].sort_values(["zone_id", "target_year"])


def build_qtensor(df: pd.DataFrame) -> pd.DataFrame:
    """83582NED → employee jobs × A10 × COROP × year."""
    df = df.copy()
    df["zone_id"]     = df["RegioS"].str.strip()
    df["target_year"] = df["Perioden"].str[:4].astype(int)
    df["sbi_key"]     = df["BedrijfstakkenBranchesSBI2008"].str.strip()
    df["jobs"]        = pd.to_numeric(df["BanenVanWerknemersInDecember_1"], errors="coerce")
    df["a10"]         = df["sbi_key"].map(SBI_TO_A10)
    df = df[df["a10"].notna()].copy()
    return df[["zone_id", "target_year", "a10", "jobs"]].sort_values(
        ["zone_id", "target_year", "a10"]
    ).reset_index(drop=True)


def preflight(births: pd.DataFrame, qtensor: pd.DataFrame, stock: pd.DataFrame) -> None:
    print("\n=== PREFLIGHT — Netherlands ===")
    # Births
    zones_b = births["zone_id"].nunique()
    years_b = sorted(births["target_year"].unique())
    print(f"Births: {len(births)} rows | {zones_b} zones (expected 40) | years {years_b}")
    if zones_b != 40:
        print(f"  WARNING: expected 40 COROP, got {zones_b}")
    nan_lag = births["side_lag_1"].isna().sum()
    print(f"  NaN side_lag_1: {nan_lag} (expected = n_zones for first year)")
    # Q-tensor
    a10_found = sorted(qtensor["a10"].unique())
    zones_q   = qtensor["zone_id"].nunique()
    years_q   = sorted(qtensor["target_year"].unique())
    print(f"Q-tensor: {len(qtensor)} rows | {zones_q} zones | {len(a10_found)} A10 | years {years_q}")
    print(f"  A10 codes: {a10_found}")
    missing_a10 = set(A10_SBI_CODES.keys()) - set(a10_found)
    if missing_a10:
        print(f"  WARNING: missing A10 codes: {missing_a10}")
    # Stock
    print(f"Stock: {len(stock)} rows | {stock['zone_id'].nunique()} zones | years {sorted(stock['target_year'].unique())}")
    # Cross-check CR99
    cr99_b = births[births["zone_id"] == "CR99"]
    if not cr99_b.empty:
        print(f"  Note: CR99 (aggregate) present in births, will be excluded in modelling")
    print("=" * 36)


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
