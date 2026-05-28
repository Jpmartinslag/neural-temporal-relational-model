"""
Belgium Phase 4 — Data Ingestion
Births/Stock: Statbel TVA demography — data/external/belgium/raw/export (1).csv
              43 arrondissements × monthly 2006-2020
              births panel: main window 2007-2020 (2006 excluded — partial)
Q-tensor:     ONSS localunit publications — employees × NACE-detailed × arrondissement
              Q4 snapshot (31 Dec) downloaded per year 2007-2020
              Source: https://www.onss.be/stats/repartition-des-postes-de-travail-par-lieu-de-travail
              Archive links extracted from page HTML (data-spreadsheet attributes)

Main modelling window: 2008-2020
  - q_tensor starts 2008 because 2007 uses NACE Rev.1, incompatible with Rev.2 A10 mapping.
    The ONSS ingestion correctly skips 2007. This is NOT a data error.
  - Do NOT carry-forward 2008 qtensor values to synthesize 2007 in the main pipeline.
    Synthetic 2007 is only allowed as a clearly-flagged sensitivity test.
  - First evaluation year after lags: 2009 (needs births(2008) and qtensor(2008)).
  - Stock: raw Statbel data starts 2006. Only years 2007-2020 are written to the
    main panel (2006 row dropped). If a pre-2007 stock lag is ever needed, read
    the raw CSV directly.

Geographic mismatch NOTE:
  Births (Statbel TVA): Tournai + Mouscron as separate arrondissements, no La Louvière
  Employment (ONSS):    "Tournai - Mouscron" combined, "La Louvière" separate
  Resolution: ONSS "Tournai - Mouscron" → BE_tournai_mouscron (keep combined)
              ONSS "La Louvière" → merged into BE_soignies (pre-2002 classification)
              Then births: sum Tournai+Mouscron → BE_tournai_mouscron for joint modelling
  Handled in build_births_panel() and build_qtensor_from_onss() below.
"""

import io
import re
import time
import unicodedata
import zipfile
from pathlib import Path

import pandas as pd
import requests

RAW_FILE = Path(__file__).parents[2] / "data/external/belgium/raw/export (1).csv"
RAW_DIR  = Path(__file__).parents[2] / "data/external/belgium/raw/onss"
PROC_DIR = Path(__file__).parents[2] / "data/external/belgium/processed"

ONSS_PAGE = "https://www.onss.be/stats/repartition-des-postes-de-travail-par-lieu-de-travail"
ONSS_BASE = "https://www.onss.be/"

# Tableau 8-17 column → A10 mapping (0-indexed from col 0)
# Col 0 = region, Col 1 = arrondissement, Col 2-41 = NACE, Col 41 = Total general
COL_A10 = {
    2:  "A",   # Agriculture
    # cols 3-16 = B (extractives) + C (manufacturing sub-sectors)
    # col 17 = Total B+C (industry)
    17: "BE",  # Total B+C (use this to avoid double-counting individual sub-cols)
    18: "BE",  # D — energy production/distribution
    19: "BE",  # E — water/waste management
    20: "FZ",  # F — construction
    21: "GI",  # G — trade
    22: "GI",  # H — transport
    23: "GI",  # I — hospitality
    24: "JZ",  # J — edition/audiovisual
    25: "JZ",  # J — telecom
    26: "JZ",  # J — IT
    27: "KZ",  # K — finance
    28: "LZ",  # L — real estate
    29: "MN",  # M — legal/accounting/technical
    30: "MN",  # M — R&D
    31: "MN",  # M — advertising/specialized
    32: "MN",  # N — administrative support
    33: "OPQ", # O — public administration
    34: "OPQ", # P — education
    35: "OPQ", # Q — health
    36: "OPQ", # Q — social
    37: "RSU", # R — arts/entertainment
    38: "RSU", # S — other services
    39: "RSU", # T — household employers
    40: "RSU", # U — extraterritorial
}

# ONSS arrondissement name → zone_id (handles mismatches vs births panel)
ONSS_NAME_MAP = {
    "Bruxelles-Capitale":   "BE_bruxelles_capitale",
    "Anvers":               "BE_anvers",
    "Malines":              "BE_malines",
    "Turnhout":             "BE_turnhout",
    "Hal-Vilvorde":         "BE_hal_vilvorde",
    "Louvain":              "BE_louvain",
    "Hasselt":              "BE_hasselt",
    "Maaseik":              "BE_maaseik",
    "Tongres":              "BE_tongres",
    "Alost":                "BE_alost",
    "Termonde":             "BE_termonde",
    "Eeklo":                "BE_eeklo",
    "Gand":                 "BE_gand",
    "Audenarde":            "BE_audenarde",
    "St-Nicolas-Waas":      "BE_saint_nicolas",
    "Bruges":               "BE_bruges",
    "Dixmude":              "BE_dixmude",
    "Ypres":                "BE_ypres",
    "Courtrai":             "BE_courtrai",
    "Ostende":              "BE_ostende",
    "Roulers":              "BE_roulers",
    "Tielt":                "BE_tielt",
    "Furnes":               "BE_furnes",
    "Nivelles":             "BE_nivelles",
    "Ath":                  "BE_ath",
    "Charleroi":            "BE_charleroi",
    "Mons":                 "BE_mons",
    "Soignies":             "BE_soignies",
    "Thuin":                "BE_thuin",
    "Tournai - Mouscron":   "BE_tournai_mouscron",  # combined in ONSS (2019+)
    "Tournai":              "BE_tournai_mouscron",  # separate in ONSS 2008-2018 → merge
    "Mouscron":             "BE_tournai_mouscron",  # separate in ONSS 2008-2018 → merge
    "La Louvière":          "BE_soignies",           # merged into Soignies (pre-2002)
    "dont communes germ.":  None,                    # sub-note under Verviers, not an arrond
    "Huy":                  "BE_huy",
    "Liège":                "BE_liege",
    "Verviers":             "BE_verviers",
    "Waremme":              "BE_waremme",
    "Arlon":                "BE_arlon",
    "Bastogne":             "BE_bastogne",
    "Marche-en-Famenne":    "BE_marche_en_famenne",
    "Neufchâteau":          "BE_neufchateau",
    "Virton":               "BE_virton",
    "Dinant":               "BE_dinant",
    "Namur":                "BE_namur",
    "Philippeville":        "BE_philippeville",
}


def clean_zone_id(name: str) -> str:
    """'Arrondissement de Liège' → 'BE_liege' (for births panel)."""
    s = name.replace("’", "'").replace("‘", "'")
    s = re.sub(r"Arrondissement (de |d')", "", s)
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.lower().replace("-", "_").replace(" ", "_").replace("'", "")
    return "BE_" + s


def fetch_onss_archive_urls() -> dict[str, tuple[str, str]]:
    """Scrape ONSS page for archive download URLs. Returns {period_key: (xlsx_url, zip_url)}."""
    r = requests.get(ONSS_PAGE, timeout=15)
    r.raise_for_status()
    divs = re.findall(
        r'id="(arch_period\d+)"[^>]*data-spreadsheet="([^"]*)"[^>]*data-zip="([^"]*)"',
        r.text
    )
    result = {}
    for period, xlsx, zip_url in divs:
        if len(period) == 16:        # arch_period{YYYY}{Q}
            yr = int(period[11:15])
            q  = int(period[15])
        elif len(period) == 15:      # arch_period{YYYY} — annual (pre-2006)
            yr = int(period[11:15])
            q  = 4                   # treat as Q4
        else:
            continue
        key = (yr, q)
        result[key] = (ONSS_BASE + xlsx if xlsx else "", ONSS_BASE + zip_url if zip_url else "")
    return result


def download_onss_year(year: int, archive_urls: dict, cache_dir: Path) -> pd.DataFrame | None:
    """Download and parse ONSS Q4 localunit xlsx for one year."""
    cache_path = cache_dir / f"onss_localunit_{year}Q4.csv"
    if cache_path.exists():
        print(f"  {year}: cached")
        return pd.read_csv(cache_path)

    xlsx_url, zip_url = archive_urls.get((year, 4), ("", ""))
    if not xlsx_url and not zip_url:
        print(f"  {year}: NOT FOUND in archive")
        return None

    # Skip years with NACE Rev.1 (pre-2008) — incompatible column layout
    if year < 2008:
        print(f"  {year}: SKIP (NACE Rev.1, incompatible with Rev.2 A10 mapping)")
        return None

    print(f"  {year}: downloading...", end=" ")
    # Determine source: use xlsx_url if it's an actual Excel file, else unzip
    is_direct_excel = xlsx_url and (xlsx_url.endswith(".xlsx") or xlsx_url.endswith(".xls"))
    download_url = xlsx_url if is_direct_excel else (zip_url or xlsx_url)
    if not download_url:
        print("no URL")
        return None
    r = requests.get(download_url, timeout=60)
    r.raise_for_status()
    if is_direct_excel:
        raw = io.BytesIO(r.content)
        engine = "xlrd" if download_url.endswith(".xls") else None
        xl = pd.read_excel(raw, sheet_name="tableau 8-17", engine=engine, header=None)
    else:
        # ZIP: find the localunit val Excel inside
        z = zipfile.ZipFile(io.BytesIO(r.content))
        xlsx_name = next(
            (n for n in z.namelist() if "val" in n.lower() and n.lower().endswith((".xlsx", ".xls"))),
            None
        )
        if not xlsx_name:
            print("no xlsx in zip")
            return None
        with z.open(xlsx_name) as f:
            engine = "xlrd" if xlsx_name.endswith(".xls") else None
            xl = pd.read_excel(f, sheet_name="tableau 8-17", engine=engine, header=None)

    print(f"{xl.shape}")
    if xl.shape[1] < 41:
        print(f"    WARNING: only {xl.shape[1]} cols — unexpected format, skipping")
        return None

    # Row 5 (0-indexed) = NACE sector labels
    # Arrondissement rows: col 0 is NaN, col 1 is arrondissement name (string, length > 2)
    arr_mask = (
        xl.iloc[:, 0].isna()
        & xl.iloc[:, 1].notna()
        & xl.iloc[:, 1].apply(lambda x: isinstance(x, str) and len(str(x)) > 2)
    )
    arr_rows = xl[arr_mask].copy()

    records = []
    for _, row in arr_rows.iterrows():
        arr_name = str(row.iloc[1]).strip()
        lookup   = ONSS_NAME_MAP.get(arr_name, "UNKNOWN")
        if lookup is None:
            continue   # explicitly excluded (e.g. sub-note rows)
        if lookup == "UNKNOWN":
            # Fallback: normalize name
            s = unicodedata.normalize("NFD", arr_name)
            s = "".join(c for c in s if unicodedata.category(c) != "Mn")
            lookup = "BE_" + s.lower().replace("-", "_").replace(" ", "_").replace("'", "")
        zone_id = lookup
        for col_idx, a10 in COL_A10.items():
            val = row.iloc[col_idx]
            try:
                jobs = float(val) if pd.notna(val) else None
            except (ValueError, TypeError):
                jobs = None
            records.append({"zone_id": zone_id, "target_year": year, "a10": a10, "jobs": jobs})

    df = pd.DataFrame(records)
    # Aggregate (some A10 codes appear multiple times due to multi-col mapping)
    df = df.groupby(["zone_id", "target_year", "a10"])["jobs"].sum().reset_index()
    df.to_csv(cache_path, index=False)
    return df


def build_births_panel(df: pd.DataFrame) -> pd.DataFrame:
    """Primo-assujetissements summed per arrondissement per year.

    Main pipeline window: 2007-2020.
      - 2006 is excluded (partial year, beSTAT series starts fully in 2007).
      - Full modelling window used in main results: 2008-2020 (aligns with qtensor).
        2007 is retained in the panel for lag computation (side_lag_1 of 2008
        uses births[2007]) but 2007 itself is not a modelling target year.
    Combines Tournai+Mouscron → BE_tournai_mouscron to match ONSS geography.
    """
    df = df.copy()
    df["zone_id"]     = df["Arrondissement"].map(clean_zone_id)
    # Merge Tournai + Mouscron → combined zone matching ONSS
    df["zone_id"]     = df["zone_id"].replace({
        "BE_tournai": "BE_tournai_mouscron",
        "BE_mouscron": "BE_tournai_mouscron",
    })
    df["target_year"] = df["Année"].astype(int)
    df["y"]           = pd.to_numeric(df["Primo-assujetissements"], errors="coerce")
    df = df[df["target_year"] >= 2007].copy()
    births = (
        df.groupby(["zone_id", "target_year"])["y"]
        .sum()
        .reset_index()
        .sort_values(["zone_id", "target_year"])
    )
    births["side_lag_1"] = births.groupby("zone_id")["y"].shift(1)
    births["growth_1y"]  = (births["y"] - births["side_lag_1"]) / births["side_lag_1"]
    return births.reset_index(drop=True)


def build_stock_panel(df: pd.DataFrame) -> pd.DataFrame:
    """December year-end stock (Entreprises Act. Fin T).

    Main pipeline window: 2007-2020.
      - Raw Statbel data includes 2006 (first full December snapshot).
      - 2006 is excluded from the main panel (outside target window 2007-2020).
        If a pre-2007 stock value is ever needed as a lag feature, read the
        raw CSV directly; do not add 2006 back to this panel without a
        methodology note in the paper.
    """
    df = df.copy()
    df_dec = df[df["Mois"] == "décembre"].copy()
    df_dec["zone_id"]     = df_dec["Arrondissement"].map(clean_zone_id)
    df_dec["zone_id"]     = df_dec["zone_id"].replace({
        "BE_tournai": "BE_tournai_mouscron",
        "BE_mouscron": "BE_tournai_mouscron",
    })
    df_dec["target_year"] = df_dec["Année"].astype(int)
    df_dec["stock"]       = pd.to_numeric(df_dec["Entreprises Act. Fin T"], errors="coerce")
    # Clip to main modelling window — 2006 dropped intentionally
    df_dec = df_dec[df_dec["target_year"] >= 2007].copy()
    # Sum Tournai+Mouscron for merged zone
    stock = (
        df_dec.groupby(["zone_id", "target_year"])["stock"]
        .sum()
        .reset_index()
        .sort_values(["zone_id", "target_year"])
    )
    return stock.reset_index(drop=True)


def preflight(births: pd.DataFrame, stock: pd.DataFrame, qtensor: pd.DataFrame | None) -> None:
    """Phase 4 preflight for Belgium. Validates windows, methodology constraints,
    and proxy guard. Any FAIL blocks HPC launch."""
    import sys
    failures = []
    warnings_list = []

    print("\n=== PREFLIGHT — Belgium (Phase 4) ===")
    print(f"  Tensor type       : employment/effectifs (ONSS employee jobs)")
    print(f"  Tensor label      : qtensor_jobs (equivalent to Q7 effectifs)")
    print(f"  Main modelling window: 2008-2020")
    print(f"  First evaluation year: 2009 (after lag)")

    # --- Births ---
    zones_b = births["zone_id"].nunique()
    years_b = sorted(births["target_year"].unique())
    exp_years_b = list(range(2007, 2021))  # 2007 retained for lag, main targets 2008-2020
    print(f"\nBirths:")
    print(f"  Rows={len(births)}, zones={zones_b} (expected 42), years={years_b[0]}-{years_b[-1]}")
    print(f"  NaN y={births['y'].isna().sum()} | NaN side_lag_1={births['side_lag_1'].isna().sum()}")
    if zones_b != 42:
        failures.append(f"births: expected 42 arrondissements, got {zones_b}")
    if sorted(years_b) != exp_years_b:
        failures.append(f"births: year range {years_b[0]}-{years_b[-1]} != expected 2007-2020")
    total_2020 = births[births["target_year"] == 2020]["y"].sum()
    print(f"  Total BE 2020 births: {total_2020:.0f}")

    # --- Stock ---
    zones_s = stock["zone_id"].nunique()
    years_s = sorted(stock["target_year"].unique())
    exp_years_s = list(range(2007, 2021))  # 2006 dropped
    print(f"\nStock:")
    print(f"  Rows={len(stock)}, zones={zones_s}, years={years_s[0]}-{years_s[-1]}")
    if sorted(years_s) != exp_years_s:
        failures.append(f"stock: year range {years_s[0]}-{years_s[-1]} != expected 2007-2020 (2006 must be excluded)")
    nan_s = stock["stock"].isna().sum()
    if nan_s > 0:
        failures.append(f"stock: {nan_s} NaN values")

    # --- Q-tensor ---
    if qtensor is not None:
        zones_q = qtensor["zone_id"].nunique()
        a10_found = sorted(qtensor["a10"].unique())
        years_q = sorted(qtensor["target_year"].unique())
        exp_years_q = list(range(2008, 2021))  # 2007 skipped: NACE Rev.1
        print(f"\nQ-tensor (employment/effectifs — ONSS):")
        print(f"  Rows={len(qtensor)}, zones={zones_q}, A10={len(a10_found)}, years={years_q[0]}-{years_q[-1]}")
        print(f"  2007 ABSENT: NACE Rev.1 incompatible with A10 Rev.2 — correct by design")
        print(f"  Synthetic 2007 NOT present in main pipeline: ", end="")
        if 2007 in years_q:
            print("*** FAIL — synthetic 2007 detected ***")
            failures.append("qtensor: year 2007 present — NACE Rev.1 incompatibility; remove synthetic 2007")
        else:
            print("✓ CLEAN")
        if sorted(years_q) != exp_years_q:
            failures.append(f"qtensor: year range {years_q[0]}-{years_q[-1]} != expected 2008-2020")
        missing_a10 = set(["A","BE","FZ","GI","JZ","KZ","LZ","MN","OPQ","RSU"]) - set(a10_found)
        if missing_a10:
            failures.append(f"qtensor: missing A10 codes: {missing_a10}")
        print(f"  NaN jobs: {qtensor['jobs'].isna().sum()}")
        if qtensor["jobs"].isna().sum() > 0:
            failures.append(f"qtensor: {qtensor['jobs'].isna().sum()} NaN jobs values")
    else:
        failures.append("qtensor: NOT BUILT")

    print("\nNOTE: Tournai+Mouscron merged → BE_tournai_mouscron; La Louvière → BE_soignies")
    print("NOTE: Primo-assujetissements = TVA enterprise births (≠ establishment)")
    print("NOTE: Methodology break 2018 — flag in modelling")

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
    PROC_DIR.mkdir(parents=True, exist_ok=True)

    # Births + Stock from TVA CSV
    print("=== Belgium TVA births × arrondissement ===")
    df_raw = pd.read_csv(RAW_FILE)
    births = build_births_panel(df_raw)
    births.to_csv(PROC_DIR / "belgium_births_panel.csv", index=False)
    print(f"  births: {len(births)} rows")

    stock = build_stock_panel(df_raw)
    stock.to_csv(PROC_DIR / "belgium_stock_panel.csv", index=False)
    print(f"  stock: {len(stock)} rows")

    # Q-tensor from ONSS
    print("\n=== ONSS employment Q-tensor (Q4 2007-2020) ===")
    print("  Fetching archive URLs...")
    archive_urls = fetch_onss_archive_urls()
    print(f"  Found {len(archive_urls)} archive periods")

    yearly_frames = []
    for year in range(2007, 2021):
        df_year = download_onss_year(year, archive_urls, RAW_DIR)
        if df_year is not None:
            yearly_frames.append(df_year)
        time.sleep(0.5)

    if yearly_frames:
        qtensor = pd.concat(yearly_frames, ignore_index=True)
        qtensor = qtensor.sort_values(["zone_id", "target_year", "a10"]).reset_index(drop=True)
        qtensor.to_csv(PROC_DIR / "belgium_qtensor_jobs_panel.csv", index=False)
        print(f"  q-tensor: {len(qtensor)} rows")
    else:
        qtensor = None
        print("  Q-tensor: no data downloaded")

    preflight(births, stock, qtensor)
    print("\nDone.")


if __name__ == "__main__":
    main()
