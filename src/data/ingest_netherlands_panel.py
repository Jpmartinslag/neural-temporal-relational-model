"""
Netherlands Phase 4 — Data Ingestion
Downloads CBS 81578NED (stock at COROP × SBI, 2007-2026) via OData API.
Target = ΔStock(t, t-1) = proxy for net establishment flows (births − deaths).
Also downloads CBS 83631NED for validation at available granularity.

Output: netherlands_stock_panel.csv  (zone × year × stock → ΔStock as y_proxy)
        netherlands_births_validation.csv  (province × year, for proxy validation)

Preflight note point 1: target = ΔStock (net flow), not pure births.
Documents this as "acceptable proxy if deaths fraction stable (expected 15-25%)."
"""

import time
from pathlib import Path

import pandas as pd
import requests

OUT_DIR = Path(__file__).parents[2] / "data/external/netherlands"
RAW_DIR = OUT_DIR / "raw/cbs"
PROC_DIR = OUT_DIR / "processed"

CBS_ODATA = "https://opendata.cbs.nl/ODataFeed/odata/{table}/TypedDataSet"

# SBI 2008 → A10 mapping (EU-harmonized, NACE Rev.2 compatible)
SBI_TO_A10 = {
    "A": "A",
    "B": "BE", "C": "BE", "D": "BE", "E": "BE",
    "F": "F",
    "G": "G", "H": "G", "I": "G",
    "J": "J",
    "K": "K",
    "L": "L",
    "M": "MN", "N": "MN",
    "O": "OPQ", "P": "OPQ", "Q": "OPQ",
    "R": "RSU", "S": "RSU", "T": "RSU", "U": "RSU",
}


def fetch_cbs_odata(table: str, select: str = None, filter_str: str = None,
                    cache_path: Path = None) -> pd.DataFrame:
    """Paginate CBS OData API (max 10,000 rows/page)."""
    if cache_path and cache_path.exists():
        print(f"  {table} — cached: {cache_path.name}")
        return pd.read_csv(cache_path)

    base_url = CBS_ODATA.format(table=table)
    params = {"$format": "json", "$top": 9999, "$skip": 0}
    if select:
        params["$select"] = select
    if filter_str:
        params["$filter"] = filter_str

    all_rows = []
    print(f"  fetching {table}...")
    while True:
        r = requests.get(base_url, params=params, timeout=60)
        r.raise_for_status()
        data = r.json()
        rows = data.get("value", [])
        all_rows.extend(rows)
        print(f"    page @skip={params['$skip']}: {len(rows)} rows (total: {len(all_rows)})")
        if len(rows) < 9999:
            break
        params = {"$format": "json", "$top": 9999, "$skip": params["$skip"] + 9999}
        if select:
            params["$select"] = select
        if filter_str:
            params["$filter"] = filter_str
        time.sleep(0.3)

    df = pd.DataFrame(all_rows)
    if cache_path:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(cache_path, index=False)
        print(f"  saved: {cache_path.name} ({len(df)} rows)")
    return df


def parse_sbi_letter(sbi_code: str) -> str:
    """Extract A10 letter from SBI code string like 'A   ' or 'B0103'."""
    if not isinstance(sbi_code, str):
        return None
    s = sbi_code.strip()
    if not s:
        return None
    # Single letter = section level (A10 compatible)
    if len(s) == 1 and s.isalpha():
        return SBI_TO_A10.get(s.upper())
    # Try first char
    return None  # sub-section level; skip for A10 aggregate


def build_stock_panel(df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    81578NED columns expected:
    BedrijfstakkenBranchesSBI2008, RegioS, Perioden, Vestigingen_1
    Filter: RegioS starts with 'CR' (40 COROP), Perioden = 4-digit year,
    BedrijfstakkenBranchesSBI2008 = single-letter SBI section.
    """
    df = df_raw.copy()

    print("Columns:", list(df.columns))
    print("Sample row:", df.iloc[0].to_dict())

    # Filter COROP regions only (RegioS like 'CR01' through 'CR40')
    corop_mask = df["RegioS"].str.strip().str.match(r"^CR\d{2}$", na=False)
    df = df[corop_mask].copy()
    print(f"After COROP filter: {len(df)} rows, {df['RegioS'].nunique()} zones")

    # Parse year from Perioden (format '2015JJ00')
    df["target_year"] = df["Perioden"].str[:4].astype(int)
    df = df[df["target_year"].between(2007, 2026)]

    # 81578NED has only aggregate SBI codes — use Total (T001081)
    sbi_col = "BedrijfstakkenBranchesSBI2008"
    total_sbi = df[df[sbi_col].str.strip() == "T001081"].copy()
    print(f"Total SBI rows: {len(total_sbi)}")

    stock_col = "Vestigingen_1"
    total_sbi["stock"] = pd.to_numeric(total_sbi[stock_col], errors="coerce")

    total = (
        total_sbi[["RegioS", "target_year", "stock"]]
        .rename(columns={"RegioS": "zone_id", "stock": "stock_total"})
    )

    # Sort and compute ΔStock as target proxy
    total = total.sort_values(["zone_id", "target_year"])
    total["stock_lag1"] = total.groupby("zone_id")["stock_total"].shift(1)
    total["y_proxy"] = total["stock_total"] - total["stock_lag1"]
    total["growth_1y"] = total["y_proxy"] / total["stock_lag1"]

    return total


def preflight_check(panel: pd.DataFrame) -> None:
    print("\n=== PREFLIGHT CHECK — Netherlands stock ===")
    print(f"Shape: {panel.shape}")
    print(f"Years: {sorted(panel['target_year'].unique())}")
    n_zones = panel["zone_id"].nunique()
    print(f"Zones: {n_zones} (expected 40 COROP)")
    if n_zones != 40:
        print(f"  WARNING: expected 40, got {n_zones}")

    nonull = panel.dropna(subset=["y_proxy"])
    print(f"Rows with valid ΔStock: {len(nonull)}")
    print(f"NaN y_proxy years: first year per zone (expected target_year=2007 or first available)")

    # Sample: CR23 Groot-Amsterdam 2020
    cr23 = panel[(panel["zone_id"].str.startswith("CR23")) & (panel["target_year"] == 2020)]
    if not cr23.empty:
        print(f"CR23 Amsterdam stock 2020: {cr23['stock_total'].values[0]:,.0f}")
        print(f"CR23 Amsterdam ΔStock 2020: {cr23['y_proxy'].values[0]:,.0f}")
    print("=" * 44)


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROC_DIR.mkdir(parents=True, exist_ok=True)

    print("=== Netherlands establishment stock (81578NED) ===")
    df_raw = fetch_cbs_odata(
        "81578NED",
        cache_path=RAW_DIR / "81578NED_full.csv",
    )

    panel = build_stock_panel(df_raw)
    preflight_check(panel)

    out = PROC_DIR / "netherlands_stock_panel.csv"
    panel.to_csv(out, index=False)
    print(f"Saved: {out}")

    print("\n=== Netherlands births validation (83631NED — COROP level) ===")
    df_births_raw = fetch_cbs_odata(
        "83631NED",
        cache_path=RAW_DIR / "83631NED_full.csv",
    )
    print("83631NED columns:", list(df_births_raw.columns))
    print("Sample:")
    print(df_births_raw.head(5).to_string())
    out_births = PROC_DIR / "netherlands_births_validation_raw.csv"
    df_births_raw.to_csv(out_births, index=False)
    print(f"Saved: {out_births}")


if __name__ == "__main__":
    main()
