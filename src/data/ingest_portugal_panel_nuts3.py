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

A10 mapping from CAE sections:
  A → A
  B,C,D,E → BE   (K and O absent from enterprise births — expected)
  F → FZ
  G,H,I → GI
  J → JZ
  L → LZ
  M,N → MN
  P,Q → OPQ  (O absent — public admin barely appears in births)
  R,S → RSU  (T,U negligible)
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
    """Reaggregate births-by-CAE × municipality → A10 × NUT3."""
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
    print("\n=== PREFLIGHT — Portugal NUTS3 ===")
    zones_b = births["zone_id"].nunique()
    years_b = sorted(births["target_year"].unique())
    print(f"Births: {len(births)} rows | {zones_b} zones (expected 25) | years {years_b}")
    if zones_b != 25:
        print(f"  WARNING: expected 25 NUT3, got {zones_b}")
    nan_lag = births["side_lag_1"].isna().sum()
    print(f"  NaN side_lag_1: {nan_lag} (expected 25 = first year per zone)")

    zones_q = qtensor["zone_id"].nunique()
    a10_found = sorted(qtensor["a10"].unique())
    years_q = sorted(qtensor["target_year"].unique())
    print(f"Q-tensor: {len(qtensor)} rows | {zones_q} zones | {len(a10_found)} A10 | years {years_q}")
    print(f"  A10 codes: {a10_found}")
    missing = set(ALL_A10) - set(a10_found)
    if missing:
        print(f"  WARNING: missing A10: {missing}")
    zero_a10 = qtensor.groupby("a10")["births"].sum()
    zero_codes = zero_a10[zero_a10 == 0].index.tolist()
    if zero_codes:
        print(f"  Note: A10 codes with zero births (K/O expected): {zero_codes}")

    zones_s = stock["zone_id"].nunique()
    years_s = sorted(stock["target_year"].unique())
    nan_s = stock["stock"].isna().sum()
    print(f"Stock: {len(stock)} rows | {zones_s} zones (expected 25) | years {years_s} | NaN={nan_s}")
    print("=" * 36)


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    print("=== Building NUT3 births panel ===")
    births = build_births_panel_nuts3()
    out_births = PROC_DIR / "portugal_births_panel_nuts3.csv"
    births.to_csv(out_births, index=False)
    print(f"  saved: {out_births.name} ({len(births)} rows)")

    print("\n=== Building NUT3 q-tensor (births by CAE) ===")
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
