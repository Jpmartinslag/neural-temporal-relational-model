"""
DEC-063: Download NL gemeente establishment stock from CBS 81575NED.

Source: CBS OData API
Table: 81575NED — Vestigingen van bedrijven; bedrijfstak, gemeente
Metric: Vestigingen_1 (establishment stock, NOT births)
Level: gemeente (GM codes), 483 current municipalities
Period: 2007–2026

Also downloads gemeente→COROP crosswalk from 84721NED.

Evidence type: observed_stock (NOT births, NOT proxy)
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pandas as pd
import requests

REPO_ROOT = Path(__file__).parents[3]
OUT_DIR = REPO_ROOT / "data/processed/european_panel"
OUT_STOCK_CSV = OUT_DIR / "nl_gemeente_stock_panel.csv"
OUT_CROSSWALK_CSV = OUT_DIR / "nl_gemeente_corop_crosswalk.csv"
OUT_MANIFEST = OUT_DIR / "nl_gemeente_stock_manifest.json"

CBS_BASE = "https://opendata.cbs.nl/ODataApi/OData"
HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}

# Table identifiers
TABLE_STOCK = "81575NED"
TABLE_CROSSWALK = "84721NED"

# SBI section keys → A10 mapping (same convention as existing NL COROP panel)
SBI_SECTION_TO_A10 = {
    "301000": "OQ",   # A  Agriculture → OQ
    "305700": "BE",   # B  Mining
    "307500": "BE",   # C  Manufacturing
    "346600": "BE",   # D  Energy
    "348000": "BE",   # E  Water/waste
    "350000": "FZ",   # F  Construction
    "354200": "GI",   # G  Trade
    "383100": "GI",   # H  Transport
    "389100": "GI",   # I  Hospitality
    "391600": "JZ",   # J  ICT
    "396300": "KZ",   # K  Finance (present in NL, unlike PT)
    "402000": "LZ",   # L  Real estate
    "403300": "MN",   # M  Business services
    "410200": "MN",   # N  Other business services
    "417400": "OQ",   # O  Public admin
    "419000": "OQ",   # P  Education
    "422400": "OQ",   # Q  Health/welfare
    "428100": "RU",   # R  Culture/sport
    "435500": "RU",   # S  Other services
    # T (440000) and U (440900) excluded: households / extraterritorial
}

A10_SECTORS = ["BE", "FZ", "GI", "JZ", "KZ", "LZ", "MN", "OQ", "RU"]

MIN_YEAR = 2007
MAX_YEAR = 2025
SECTION_KEYS = list(SBI_SECTION_TO_A10.keys())


def _fetch_odata(url: str, params: dict | None = None, retries: int = 3) -> list[dict]:
    """Fetch all pages from CBS OData endpoint."""
    all_rows: list[dict] = []
    next_url: str | None = url
    p = dict(params or {})
    p.setdefault("$format", "json")

    while next_url:
        for attempt in range(retries):
            try:
                r = requests.get(next_url, params=p if next_url == url else None,
                                 headers=HEADERS, timeout=60)
                r.raise_for_status()
                data = r.json()
                break
            except Exception as e:
                if attempt == retries - 1:
                    raise
                time.sleep(2 ** attempt)

        rows = data.get("value", [])
        all_rows.extend(rows)
        next_url = data.get("odata.nextLink")
        p = {}   # params only on first call
        if next_url:
            time.sleep(0.3)

    return all_rows


def download_crosswalk() -> pd.DataFrame:
    """Download gemeente→COROP crosswalk from CBS 84721NED."""
    print("Downloading gemeente→COROP crosswalk from 84721NED...")
    url = f"{CBS_BASE}/{TABLE_CROSSWALK}/TypedDataSet"
    params = {
        "$select": "RegioS,Code_1,Naam_2,Code_8,Naam_9",
        "$top": 10000,
    }
    rows = _fetch_odata(url, params)
    df = pd.DataFrame(rows)
    if df.empty:
        raise RuntimeError("Crosswalk download returned 0 rows")

    df.columns = [c.strip() for c in df.columns]
    df["gm_code"] = df["RegioS"].astype(str).str.strip()
    df["gm_code_alt"] = df.get("Code_1", df["RegioS"]).astype(str).str.strip()
    df["gm_name"] = df["Naam_2"].astype(str).str.strip()
    df["cr_code"] = df["Code_8"].astype(str).str.strip()
    df["cr_name"] = df["Naam_9"].astype(str).str.strip()

    # Keep only entries with valid GM and CR codes
    result = df[
        df["gm_code"].str.startswith("GM") & df["cr_code"].str.startswith("CR")
    ][["gm_code", "gm_name", "cr_code", "cr_name"]].drop_duplicates("gm_code")

    print(f"  Crosswalk: {len(result)} GM→CR mappings")
    return result.reset_index(drop=True)


def _build_sbi_filter() -> str:
    """Build OData filter OR-chain for 19 SBI section keys (padded to 7 chars)."""
    # CBS stores SBI codes as 7-char strings (6 digits + 1 space)
    clauses = " or ".join(
        f"BedrijfstakkenBranchesSBI2008 eq '{k.ljust(7)}'"
        for k in SECTION_KEYS
    )
    return f"({clauses})"


def _fetch_by_year(year: int) -> list[dict]:
    """
    Fetch all GM stock rows for one year from 81575NED.
    Filter: GM regions × 19 section keys × 1 year = 483×19 = 9177 rows < 10k limit.
    CBS OData ignores filters that would return >10k rows, so filtering both by
    year AND SBI keeps each call safely below the limit.
    """
    period = f"{year}JJ00"
    sbi_filter = _build_sbi_filter()
    url = f"{CBS_BASE}/{TABLE_STOCK}/TypedDataSet"
    params = {
        "$select": "BedrijfstakkenBranchesSBI2008,RegioS,Perioden,Vestigingen_1",
        "$filter": f"startswith(RegioS,'GM') and Perioden eq '{period}' and {sbi_filter}",
        "$top": 10000,
    }
    for attempt in range(3):
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=60)
            if r.status_code == 500:
                print(f"    CBS 500 for year {year} — skipping")
                return []
            r.raise_for_status()
            return r.json().get("value", [])
        except Exception as e:
            if attempt == 2:
                print(f"    Failed year {year}: {e}")
                return []
            time.sleep(2 ** attempt)
    return []


def download_gemeente_stock() -> pd.DataFrame:
    """Download establishment stock from CBS 81575NED — one API call per year."""
    print(f"Downloading gemeente stock from {TABLE_STOCK} (one call per year, SBI filter embedded)...")

    all_rows: list[dict] = []
    for year in range(MIN_YEAR, MAX_YEAR + 1):
        rows = _fetch_by_year(year)
        print(f"  {year}: {len(rows)} rows")
        all_rows.extend(rows)
        time.sleep(0.5)

    print(f"  Total downloaded: {len(all_rows)} rows")

    df = pd.DataFrame(all_rows)
    if df.empty:
        raise RuntimeError("No stock data downloaded from 81575NED")

    df["sbi_key"] = df["BedrijfstakkenBranchesSBI2008"].astype(str).str.strip()
    df["gm_code"] = df["RegioS"].astype(str).str.strip()
    df["year"] = df["Perioden"].astype(str).str[:4].astype(int)
    df["stock"] = pd.to_numeric(df["Vestigingen_1"], errors="coerce")

    # Filter to section-level SBI keys and year range
    df = df[df["sbi_key"].isin(SECTION_KEYS)].copy()
    df = df[df["year"].between(MIN_YEAR, MAX_YEAR)].copy()
    df["a10"] = df["sbi_key"].map(SBI_SECTION_TO_A10)
    df = df[df["a10"].notna()].copy()

    print(f"  After filter: {len(df)} rows ({df['gm_code'].nunique()} GMs, {df['year'].nunique()} years)")
    return df


def aggregate_to_a10(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate section-level stock to A10 buckets per gemeente × year."""
    grouped = df.groupby(["gm_code", "year", "a10"], as_index=False)["stock"].sum(min_count=1)
    wide = grouped.pivot_table(
        index=["gm_code", "year"],
        columns="a10",
        values="stock",
        aggfunc="sum",
    ).reset_index()
    wide.columns.name = None

    # Ensure all A10 sectors present
    for s in A10_SECTORS:
        if s not in wide.columns:
            wide[s] = float("nan")
    wide = wide[["gm_code", "year"] + A10_SECTORS]
    wide["total_stock"] = wide[A10_SECTORS].sum(axis=1, skipna=False)
    return wide


def build_stock_panel(long_df: pd.DataFrame, crosswalk: pd.DataFrame) -> pd.DataFrame:
    """Build final gemeente stock panel with COROP crosswalk."""
    wide = aggregate_to_a10(long_df)
    panel = wide.merge(crosswalk[["gm_code", "gm_name", "cr_code", "cr_name"]],
                       on="gm_code", how="left")

    n_no_corop = panel["cr_code"].isna().sum()
    if n_no_corop > 0:
        print(f"  WARNING: {n_no_corop} rows with no COROP mapping (historical mergers)")

    panel["country"] = "NL"
    panel["region_level"] = "gemeente"
    panel["evidence_type"] = "observed_stock"
    panel["source_table"] = TABLE_STOCK

    # Rename A10 columns to sector_ prefix
    rename = {s: f"sector_{s}" for s in A10_SECTORS}
    panel = panel.rename(columns={**rename, "total_stock": "total_stock_all_sectors"})

    cols = (
        ["country", "gm_code", "gm_name", "cr_code", "cr_name",
         "region_level", "year", "evidence_type", "source_table"]
        + [f"sector_{s}" for s in A10_SECTORS]
        + ["total_stock_all_sectors"]
    )
    return panel[[c for c in cols if c in panel.columns]]


def main() -> dict:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("\nDEC-063: NL Gemeente Stock Panel Ingest")
    print("=" * 45)

    # 1. Crosswalk
    crosswalk = download_crosswalk()
    crosswalk.to_csv(OUT_CROSSWALK_CSV, index=False)
    print(f"Crosswalk saved: {OUT_CROSSWALK_CSV}")

    # 2. Stock download
    long_df = download_gemeente_stock()

    # 3. Build panel
    panel = build_stock_panel(long_df, crosswalk)

    # 4. Save
    panel.to_csv(OUT_STOCK_CSV, index=False)
    print(f"\nStock panel saved: {OUT_STOCK_CSV}")
    print(f"  {len(panel)} rows, {panel['gm_code'].nunique()} GMs, {panel['year'].nunique()} years")

    # 5. Manifest
    n_with_corop = panel["cr_code"].notna().sum()
    manifest = {
        "experiment": "DEC-063",
        "source_table": TABLE_STOCK,
        "crosswalk_table": TABLE_CROSSWALK,
        "source_url": f"{CBS_BASE}/{TABLE_STOCK}",
        "crosswalk_url": f"{CBS_BASE}/{TABLE_CROSSWALK}",
        "evidence_type": "observed_stock",
        "metric": "Vestigingen_1",
        "region_level": "gemeente",
        "n_rows": int(len(panel)),
        "n_gemeenten": int(panel["gm_code"].nunique()),
        "n_years": int(panel["year"].nunique()),
        "year_range": f"{int(panel['year'].min())}-{int(panel['year'].max())}",
        "n_with_corop_mapping": int(n_with_corop),
        "note": "Stock (vestigingen bestand) not births (oprichtingen). "
                "Used only for computing gemeent birth proxy shares, not as direct target.",
        "sbi_to_a10": SBI_SECTION_TO_A10,
        "sectors": A10_SECTORS,
    }
    with open(OUT_MANIFEST, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"Manifest saved: {OUT_MANIFEST}")

    return manifest


if __name__ == "__main__":
    main()
