"""
Portugal Phase 4 — Data Ingestion
Downloads INE births data for all years 2008-2024
at municipality level (308 municípios).
Outputs: portugal_births_panel.parquet (zone × year × births)
         portugal_births_cae_panel.parquet (zone × year × A10 sector × births)

Territory: 308 municípios (confirmed available via INE API).
Alternative: 23 zonas de emprego INE — blocked pending boundary verification.
"""

import json
import time
from pathlib import Path

import pandas as pd
import requests

OUT_DIR = Path(__file__).parents[2] / "data/external/portugal"
RAW_DIR = OUT_DIR / "raw/ine"
PROC_DIR = OUT_DIR / "processed"

YEARS = list(range(2008, 2025))
INE_BASE = "https://www.ine.pt/ine/json_indicador/pindica.jsp"

# INE indicator codes
IND_BIRTHS_TOTAL_OLD = "0009702"   # NUTS 2013, valid through 2022
IND_BIRTHS_CAE_OLD   = "0009703"   # NUTS 2013, valid through 2022
IND_BIRTHS_TOTAL_NEW = "0014098"   # NUTS 2024, 2023+
IND_BIRTHS_CAE_NEW   = "0014099"   # NUTS 2024, 2023+


def total_indicator_for_year(year: int) -> str:
    return IND_BIRTHS_TOTAL_NEW if year >= 2023 else IND_BIRTHS_TOTAL_OLD


def cae_indicator_for_year(year: int) -> str:
    return IND_BIRTHS_CAE_NEW if year >= 2023 else IND_BIRTHS_CAE_OLD

# A10 sector mapping from CAE/NACE section letters
# INE 0009703 uses NACE section letters directly
CAE_SECTION_TO_A10 = {
    "A": "A",                           # Agriculture
    "B": "BE", "C": "BE", "D": "BE", "E": "BE",  # Industry (BCDE)
    "F": "F",                           # Construction
    "G": "G", "H": "G", "I": "G",      # Trade/transport/accom (GHI)
    "J": "J",                           # Information/communication
    "K": "K",                           # Finance/insurance
    "L": "L",                           # Real estate
    "M": "MN", "N": "MN",              # Professional/admin services
    "O": "OPQ", "P": "OPQ", "Q": "OPQ",  # Public/education/health
    "R": "RSU", "S": "RSU", "T": "RSU", "U": "RSU",  # Arts/other
}

# Sections reported by INE 0009703 (verify from first download)
ALL_CAE_SECTIONS = list("ABCDEFGHIJKLMNOPQRSTU")


def fetch_ine_indicator(indicator: str, year: int, retries: int = 3) -> list:
    params = {
        "op": "2",
        "varcd": indicator,
        "Dim1": f"S7A{year}",
        "lang": "PT",
    }
    for attempt in range(retries):
        try:
            r = requests.get(INE_BASE, params=params, timeout=30)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            if attempt == retries - 1:
                raise
            print(f"  retry {attempt+1} for {indicator} {year}: {e}")
            time.sleep(2)


def parse_births_total(data: list, year: int) -> pd.DataFrame:
    """Parse 0009702 response → (geocod, year, births).
    Response is a list of one dict; Dados[year] is a list of entries.
    Filter: geocod length 7 (municipality) + dim_3='T' (Total across legal forms).
    """
    rows = []
    dados = data[0]["Dados"].get(str(year), [])
    for entry in dados:
        geocod = entry.get("geocod", "")
        if len(geocod) != 7:
            continue
        if entry.get("dim_3") != "T":
            continue
        val = entry.get("valor", "")
        if val in ("", None):
            continue
        try:
            births = float(val)
        except ValueError:
            continue
        rows.append({"zone_id": geocod, "target_year": year, "y_total": births})
    return pd.DataFrame(rows)


def parse_births_cae(data: list, year: int) -> pd.DataFrame:
    """Parse 0009703 response → (geocod, year, cae_section, births).
    dim_3 = CAE section letter (A-S) or 'TOT'. Filter: len(geocod)==7, dim_3 != 'TOT'.
    """
    rows = []
    dados = data[0]["Dados"].get(str(year), [])
    for entry in dados:
        geocod = entry.get("geocod", "")
        if len(geocod) != 7:
            continue
        cae = entry.get("dim_3", "")
        if cae == "TOT":
            continue
        val = entry.get("valor", "")
        if val in ("", None):
            continue
        try:
            births = float(val)
        except ValueError:
            continue
        rows.append({
            "zone_id": geocod,
            "target_year": year,
            "cae_section": cae,
            "births_cae": births,
        })
    return pd.DataFrame(rows)


def download_all(kind: str, years: list, raw_dir: Path) -> list[pd.DataFrame]:
    dfs = []
    for year in years:
        indicator = total_indicator_for_year(year) if kind == "total" else cae_indicator_for_year(year)
        cache_path = raw_dir / f"{indicator}_{year}.json"
        if cache_path.exists():
            print(f"  {indicator} {year} — cached")
            with open(cache_path) as f:
                data = json.load(f)
        else:
            print(f"  {indicator} {year} — downloading...")
            data = fetch_ine_indicator(indicator, year)
            with open(cache_path, "w") as f:
                json.dump(data, f)
            time.sleep(0.3)  # be polite to INE API

        if kind == "total":
            df = parse_births_total(data, year)
        else:
            df = parse_births_cae(data, year)

        if df.empty:
            print(f"  WARNING: {indicator} {year} returned empty data")
        else:
            print(f"  {indicator} {year} → {len(df)} rows")
        dfs.append(df)
    return dfs


def build_total_panel(dfs: list[pd.DataFrame]) -> pd.DataFrame:
    panel = pd.concat([d for d in dfs if not d.empty], ignore_index=True)
    panel = panel.sort_values(["zone_id", "target_year"]).reset_index(drop=True)

    # Derive lag1 and growth_1y
    panel = panel.sort_values(["zone_id", "target_year"])
    panel["side_lag_1"] = panel.groupby("zone_id")["y_total"].shift(1)
    panel["growth_1y"] = (panel["y_total"] - panel["side_lag_1"]) / panel["side_lag_1"]

    # Rename to match France schema
    panel = panel.rename(columns={"y_total": "y"})
    return panel


def build_cae_panel(dfs: list[pd.DataFrame]) -> pd.DataFrame:
    if not any(not d.empty for d in dfs):
        return pd.DataFrame()
    panel = pd.concat([d for d in dfs if not d.empty], ignore_index=True)

    # Apply A10 mapping
    panel["a10"] = panel["cae_section"].map(CAE_SECTION_TO_A10)
    unmapped = panel[panel["a10"].isna()]["cae_section"].unique()
    if len(unmapped) > 0:
        print(f"WARNING: unmapped CAE sections: {unmapped}")

    return panel.sort_values(["zone_id", "target_year", "cae_section"]).reset_index(drop=True)


def preflight_check(panel: pd.DataFrame) -> None:
    print("\n=== PREFLIGHT CHECK — Portugal births ===")
    print(f"Shape: {panel.shape}")
    print(f"Years: {sorted(panel['target_year'].unique())}")
    n_zones = panel["zone_id"].nunique()
    print(f"Zones: {n_zones} (expected 308 municípios)")
    if n_zones != 308:
        print(f"  WARNING: expected 308, got {n_zones}")

    y2020 = panel[panel["target_year"] == 2020]["y"].sum()
    print(f"Total births 2020: {y2020:,.0f} (expected ~153,290 municipal level)")

    lisboa = panel[(panel["zone_id"] == "1701106") & (panel["target_year"] == 2020)]["y"]
    if len(lisboa) > 0:
        print(f"Lisboa 2020: {lisboa.values[0]:,.0f} (expected ~14,054)")
    else:
        print("WARNING: Lisboa geocod 1701106 not found")

    missing = panel[panel["side_lag_1"].isna()]["target_year"].unique()
    print(f"NaN lag1 years: {sorted(missing)} (expected [2008] only)")
    print("=" * 42)


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROC_DIR.mkdir(parents=True, exist_ok=True)

    print("=== Portugal births (0009702) — total ===")
    total_dfs = download_all("total", YEARS, RAW_DIR)
    panel_total = build_total_panel(total_dfs)
    preflight_check(panel_total)
    out_total = PROC_DIR / "portugal_births_panel.csv"
    panel_total.to_csv(out_total, index=False)
    print(f"Saved: {out_total}")

    print("\n=== Portugal births × CAE section (0009703) ===")
    cae_dfs = download_all("cae", YEARS, RAW_DIR)
    panel_cae = build_cae_panel(cae_dfs)
    if not panel_cae.empty:
        out_cae = PROC_DIR / "portugal_births_cae_raw.csv"
        panel_cae.to_csv(out_cae, index=False)
        print(f"Saved: {out_cae}")
        print(f"\nCAE sections present: {sorted(panel_cae['cae_section'].unique())}")
        print("A10 mapping applied. Check 'a10' column — NaN = unmapped section.")
    else:
        print("WARNING: CAE panel empty — check INE 0009703 response format.")


if __name__ == "__main__":
    main()
