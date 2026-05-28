"""
Portugal Phase 4 — NUTS3 Data Ingestion
Reaggregates municipality-level births data → 25 NUTS3 zones.
Downloads stock data (0009819) directly at NUTS3 level.

Sources:
  Births (0009702): Nascimentos Empresas × município × forma jurídica  (existing raw)
  Births by CAE (0009703): Nascimentos Empresas × município × CAE section (existing raw)
  Stock (0009819): Empresas × NUTS3 × Dimensão  (downloaded here)

NUT3 extraction: geocod[:3] for 7-char municipality codes.
Zone IDs: 'PT_' + nut3_code  (e.g. 'PT_111', 'PT_170', 'PT_300')

*** TENSOR FRAMING — READ BEFORE USE ***
  The sectoral tensor built here (portugal_qtensor_births_cae_nuts3.csv) is a
  SECTOR-BIRTHS tensor, NOT a Q7 effectifs (employment) tensor.

  - France Q7 uses: URSSAF effectifs (employee headcount) × A10 × ZE, lag-1.
  - Portugal tensor: enterprise BIRTHS × CAE→A10 × NUTS3.

  These are DIFFERENT concepts:
    · effectifs = stock of employees (labour supply signal)
    · sector births = flow of new firms by sector (entrepreneurial activity signal)

  Implications:
    · Do NOT call this tensor "Q7 effectifs" or "tensor laboral" in any report.
    · Use the label "sector_births_tensor" or "sector_births_lag1" in all
      experiment configs, paper sections, and dashboard labels.
    · This tensor can be tested as a feature in its own right, but as a
      SEPARATE VARIANT from Q7, never as a drop-in replacement.
    · Portugal Q7 equivalence (employment-based) requires GEP Quadros de Pessoal
      (employee headcount × CAE × municipality). That dataset is NOT ingested
      here. Until it is available, Portugal does NOT have a Q7-equivalent tensor.

A10 mapping from CAE sections:
  A → A
  B,C,D,E → BE   (K and O absent from enterprise births — expected)
  F → FZ
  G,H,I → GI
  J → JZ
  K → KZ  (KZ = 0 everywhere in births — finance sector does not appear in
             enterprise births; this is expected, NOT a data error)
  L → LZ
  M,N → MN
  O,P,Q → OPQ  (O absent — public admin barely appears in births)
  R,S,T,U → RSU
"""

import json
import time
from pathlib import Path

import pandas as pd
import requests

BASE = Path(__file__).parents[2]
RAW_DIR  = BASE / "data/external/portugal/raw/ine"
PROC_DIR = BASE / "data/external/portugal/processed"
PROC_DIR.mkdir(parents=True, exist_ok=True)

YEARS = list(range(2008, 2023))

CAE_TO_A10 = {
    "A": "A",
    "B": "BE", "C": "BE", "D": "BE", "E": "BE",
    "F": "FZ",
    "G": "GI", "H": "GI", "I": "GI",
    "J": "JZ",
    "K": "KZ",
    "L": "LZ",
    "M": "MN", "N": "MN",
    "O": "OPQ", "P": "OPQ", "Q": "OPQ",
    "R": "RSU", "S": "RSU", "T": "RSU", "U": "RSU",
}

ALL_A10 = ["A", "BE", "FZ", "GI", "JZ", "KZ", "LZ", "MN", "OPQ", "RSU"]


def geocod_to_nuts3(geocod: str) -> str:
    return str(geocod)[:3]


def zone_id(nuts3: str) -> str:
    return f"PT_{nuts3}"


def fetch_ine_indicator(indicator: str, year: int) -> list:
    cache = RAW_DIR / f"{indicator}_{year}.json"
    if cache.exists():
        with open(cache) as f:
            return json.load(f)
    url = (
        f"https://www.ine.pt/ine/json_indicador/pindica.jsp"
        f"?op=2&varcd={indicator}&Dim1=S7A{year}&lang=PT"
    )
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    data = r.json()
    with open(cache, "w") as f:
        json.dump(data, f)
    time.sleep(0.4)
    return data


def build_births_panel_nuts3() -> pd.DataFrame:
    """Reaggregate municipality births → NUT3."""
    births_path = PROC_DIR / "portugal_births_panel.csv"
    if not births_path.exists():
        raise FileNotFoundError(f"Run ingest_portugal_panel.py first: {births_path}")
    df = pd.read_csv(births_path, dtype={"zone_id": str})
    df["nuts3"] = df["zone_id"].apply(geocod_to_nuts3)
    df["zone_id"] = df["nuts3"].apply(zone_id)
    grouped = (
        df.groupby(["zone_id", "target_year"])["y"]
        .sum()
        .reset_index()
        .sort_values(["zone_id", "target_year"])
    )
    grouped["side_lag_1"] = grouped.groupby("zone_id")["y"].shift(1)
    grouped["growth_1y"] = (grouped["y"] - grouped["side_lag_1"]) / grouped["side_lag_1"]
    return grouped.reset_index(drop=True)


def build_qtensor_nuts3() -> pd.DataFrame:
    """Reaggregate births-by-CAE × municipality → A10 × NUT3.

    OUTPUT: sector_births_tensor — enterprise births per sector per NUTS3 zone.
    This is NOT equivalent to the Q7 effectifs (employment) tensor used in France.
    See module docstring for full framing rationale.

    Special cases:
      - KZ (finance): all zeros in births — expected, finance firms do not appear
        as enterprise births in INE 0009703. Do not treat as missing data.
    """
    cae_path = PROC_DIR / "portugal_births_cae_raw.csv"
    if not cae_path.exists():
        raise FileNotFoundError(f"Run ingest_portugal_panel.py first: {cae_path}")
    df = pd.read_csv(cae_path, dtype={"zone_id": str})
    df["nuts3"] = df["zone_id"].apply(geocod_to_nuts3)
    df["zone_id"] = df["nuts3"].apply(zone_id)
    df["a10"] = df["cae_section"].map(CAE_TO_A10)
    df = df[df["a10"].notna()].copy()
    grouped = (
        df.groupby(["zone_id", "target_year", "a10"])["births_cae"]
        .sum()
        .reset_index()
        .rename(columns={"births_cae": "births"})
        .sort_values(["zone_id", "target_year", "a10"])
    )
    # Ensure all A10 codes present (fill 0 for K, O which are absent in births)
    idx = pd.MultiIndex.from_product(
        [
            grouped["zone_id"].unique(),
            YEARS,
            ALL_A10,
        ],
        names=["zone_id", "target_year", "a10"],
    )
    full = grouped.set_index(["zone_id", "target_year", "a10"]).reindex(idx, fill_value=0).reset_index()
    return full.sort_values(["zone_id", "target_year", "a10"]).reset_index(drop=True)


def build_stock_panel_nuts3() -> pd.DataFrame:
    """Download 0009819 (Empresas × NUT3 × Dimensão) and extract Total."""
    records = []
    for yr in YEARS:
        data = fetch_ine_indicator("0009819", yr)
        if not data or not isinstance(data, list):
            print(f"  {yr}: no data")
            continue
        rows = list(data[0].get("Dados", {}).values())
        rows = rows[0] if rows else []
        for row in rows:
            geo = str(row.get("geocod", ""))
            if len(geo) != 3:
                continue
            if row.get("dim_3_t", "") != "Total":
                continue
            val = row.get("valor", "")
            try:
                val = float(str(val).replace(" ", "").replace(",", "."))
            except (ValueError, TypeError):
                val = float("nan")
            records.append({"zone_id": zone_id(geo), "target_year": yr, "stock": val})
        print(f"  {yr}: {sum(1 for r in records if r['target_year'] == yr)} zones")
    df = pd.DataFrame(records).sort_values(["zone_id", "target_year"]).reset_index(drop=True)
    return df


def preflight(births: pd.DataFrame, qtensor: pd.DataFrame, stock: pd.DataFrame) -> None:
    """Phase 4 preflight for Portugal. Validates windows, tensor framing, and
    methodological constraints. Any FAIL blocks HPC launch."""
    import sys
    failures = []
    warnings_list = []

    print("\n=== PREFLIGHT — Portugal NUTS3 (Phase 4) ===")
    print(f"  Tensor type       : sector_births (enterprise births by CAE→A10)")
    print(f"  Tensor label      : sector_births_tensor (NOT Q7 effectifs)")
    print(f"  Q7 equivalence    : NO — employment tensor requires GEP Quadros de Pessoal")
    print(f"  Main window       : 2008-2022")
    print(f"  First eval year   : 2009 (after lag)")

    # --- Births ---
    zones_b = births["zone_id"].nunique()
    years_b = sorted(births["target_year"].unique())
    exp_years_b = list(range(2008, 2023))
    print(f"\nBirths:")
    print(f"  Rows={len(births)}, zones={zones_b} (expected 25), years={years_b[0]}-{years_b[-1]}")
    if zones_b != 25:
        failures.append(f"births: expected 25 NUT3 zones, got {zones_b}")
    if sorted(years_b) != exp_years_b:
        failures.append(f"births: year range {years_b[0]}-{years_b[-1]} != expected 2008-2022")
    nan_lag = births["side_lag_1"].isna().sum()
    if nan_lag != zones_b:
        failures.append(f"births: NaN side_lag_1={nan_lag}, expected {zones_b} (one per zone, first year)")
    else:
        print(f"  NaN side_lag_1={nan_lag} ✓ (first-year lag, expected)")

    # --- Sector-births tensor ---
    zones_q = qtensor["zone_id"].nunique()
    a10_found = sorted(qtensor["a10"].unique())
    years_q = sorted(qtensor["target_year"].unique())
    exp_years_q = list(range(2008, 2023))
    print(f"\nSector-births tensor (births by CAE→A10 — NOT employment):")
    print(f"  Rows={len(qtensor)}, zones={zones_q}, A10={len(a10_found)}, years={years_q[0]}-{years_q[-1]}")
    if zones_q != 25:
        failures.append(f"sector_births_tensor: expected 25 zones, got {zones_q}")
    if sorted(years_q) != exp_years_q:
        failures.append(f"sector_births_tensor: year range {years_q[0]}-{years_q[-1]} != expected 2008-2022")
    missing = set(ALL_A10) - set(a10_found)
    if missing:
        failures.append(f"sector_births_tensor: missing A10 codes: {missing}")
    zero_a10 = qtensor.groupby("a10")["births"].sum()
    zero_codes = zero_a10[zero_a10 == 0].index.tolist()
    if zero_codes:
        for code in zero_codes:
            if code == "KZ":
                print(f"  A10={code}: all-zero births — expected (finance sector absent from enterprise births)")
            else:
                warnings_list.append(f"sector_births_tensor: A10={code} has all-zero births (unexpected for non-KZ)")
    nan_births = qtensor["births"].isna().sum()
    if nan_births > 0:
        failures.append(f"sector_births_tensor: {nan_births} NaN births values")

    # --- Stock ---
    zones_s = stock["zone_id"].nunique()
    years_s = sorted(stock["target_year"].unique())
    exp_years_s = list(range(2008, 2023))
    nan_s = stock["stock"].isna().sum()
    print(f"\nStock:")
    print(f"  Rows={len(stock)}, zones={zones_s} (expected 25), years={years_s[0]}-{years_s[-1]}, NaN={nan_s}")
    if zones_s != 25:
        failures.append(f"stock: expected 25 zones, got {zones_s}")
    if sorted(years_s) != exp_years_s:
        failures.append(f"stock: year range {years_s[0]}-{years_s[-1]} != expected 2008-2022")
    if nan_s > 0:
        failures.append(f"stock: {nan_s} NaN stock values")

    # --- Q7 equivalence guard ---
    print("\n  [Q7 GUARD] Portugal tensor is sector_births, NOT employment/effectifs.")
    print("  [Q7 GUARD] Do not label as Q7 in any paper section, config, or dashboard.")
    print("  [Q7 GUARD] For Q7 equivalence, ingest GEP Quadros de Pessoal first.")

    # --- Summary ---
    print("\n" + "=" * 36)
    if failures:
        print("PREFLIGHT RESULT: *** FAIL — DO NOT LAUNCH HPC ***")
        for f in failures:
            print(f"  FAIL: {f}")
    else:
        print("PREFLIGHT RESULT: PASS")
    for w in warnings_list:
        print(f"  WARN: {w}")
    print("=" * 36)
    if failures:
        sys.exit(1)


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    print("=== Building NUT3 births panel ===")
    births = build_births_panel_nuts3()
    out_births = PROC_DIR / "portugal_births_panel_nuts3.csv"
    births.to_csv(out_births, index=False)
    print(f"  saved: {out_births.name} ({len(births)} rows)")

    print("\n=== Building NUT3 sector-births tensor (births by CAE→A10) ===")
    print("  NOTE: This is a sector_births_tensor, NOT Q7 effectifs (employment).")
    print("  Output file: portugal_qtensor_births_cae_nuts3.csv")
    print("  Use label 'sector_births_tensor' in all experiment configs and reports.")
    qtensor = build_qtensor_nuts3()
    out_qt = PROC_DIR / "portugal_qtensor_births_cae_nuts3.csv"
    qtensor.to_csv(out_qt, index=False)
    print(f"  saved: {out_qt.name} ({len(qtensor)} rows)")

    print("\n=== Downloading NUT3 stock panel (0009819) ===")
    stock = build_stock_panel_nuts3()
    out_stock = PROC_DIR / "portugal_stock_panel_nuts3.csv"
    stock.to_csv(out_stock, index=False)
    print(f"  saved: {out_stock.name} ({len(stock)} rows)")

    preflight(births, qtensor, stock)
    print("\nDone.")


if __name__ == "__main__":
    main()
