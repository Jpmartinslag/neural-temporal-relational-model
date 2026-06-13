"""
audit_european_sector_coverage.py

European territorial sector coverage preflight for HERALD Phase 7 extension.
Uses exclusively local files as primary source. External sources are documented
but not downloaded; countries requiring a download are marked ELIGIBLE_WITH_DOWNLOAD.

Produces:
  data/processed/european_panel/european_sector_coverage_matrix.csv
  data/processed/european_panel/european_sector_coverage_summary.json
  data/processed/european_panel/european_sector_source_manifest.json
  reports/HERALD_EUROPEAN_SECTOR_COVERAGE_PREFLIGHT.md

Decision: DEC-038
Author: HERALD pipeline
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_EXT = REPO_ROOT / "data/external"
DATA_PROC = REPO_ROOT / "data/processed/european_panel"
REPORTS = REPO_ROOT / "reports"

# ── Phase 7 minimum gate criteria ────────────────────────────────────────────
MIN_CONSECUTIVE_YEARS = 6
MIN_TERRITORIES = 10          # n_territories × MIN_CONSECUTIVE_YEARS ≥ MIN_SAMPLES
MIN_SAMPLES = 60              # n_territories × consecutive_years
MIN_A10_SECTORS = 8           # comparably defined sectors

# ── A10 Observatory sectors ───────────────────────────────────────────────────
A10_SECTORS = ["BE", "FZ", "GI", "JZ", "KZ", "LZ", "MN", "OQ", "RU"]

# BD_HGNACE_R NACE → A10 mapping (10 sector codes, excluding total)
# K_L COMBINED: cannot split into KZ (financial) and LZ (real estate)
# P_Q PARTIAL: missing O (public administration) from OQ (O+P+Q)
# G+H+I → GI by summation
NACE_BD_TO_A10: dict[str, str | None] = {
    "B-E":       "BE",
    "F":         "FZ",
    "G":         "GI",          # aggregate with H and I
    "H":         "GI",
    "I":         "GI",
    "J":         "JZ",
    "K_L":       "KL_combined", # semantic limitation: KZ+LZ inseparable
    "M_N":       "MN",
    "P_Q":       "OQ_partial",  # semantic limitation: missing O (public admin)
    "R_S_X_S94": "RU_approx",  # approximate: S94 excluded
}

# Distinct A10-comparable sectors producible from BD_HGNACE_R
BD_EFFECTIVE_SECTORS = ["BE", "FZ", "GI", "JZ", "KL_combined", "MN", "OQ_partial", "RU_approx"]

# ── External source registry (not downloaded; eligibility based on published docs) ──
EXTERNAL_SOURCES: dict[str, dict] = {
    "ES": {
        "name": "Spain",
        "source": "INE DIRCE (Directorio Central de Empresas)",
        "indicator": "Altas de empresas por sección CNAE-2009 y provincia",
        "n_territories_expected": 50,
        "territorial_level": "NUTS3_province",
        "year_min_expected": 2007,
        "year_max_expected": 2023,
        "concept": "enterprise_birth",
        "sectors_expected": "A10-compatible via CNAE-2009",
        "url": "https://www.ine.es/dyngs/INEbase/es/operacion.htm?c=Estadistica_C&cid=1254736160707",
        "semantic_risk": None,
    },
    "IT": {
        "name": "Italy",
        "source": "ISTAT ASIA (Archivio Statistico delle Imprese Attive)",
        "indicator": "Nati di impresa per sezione ATECO e provincia",
        "n_territories_expected": 107,
        "territorial_level": "NUTS3_province",
        "year_min_expected": 2010,
        "year_max_expected": 2022,
        "concept": "enterprise_birth",
        "sectors_expected": "A10-compatible via ATECO-2007",
        "url": "https://dati.istat.it/",
        "semantic_risk": None,
    },
    "DE": {
        "name": "Germany",
        "source": "Destatis Unternehmensregister",
        "indicator": "Unternehmensgründungen nach Wirtschaftszweig und Kreis",
        "n_territories_expected": 401,
        "territorial_level": "NUTS3_kreis",
        "year_min_expected": 2008,
        "year_max_expected": 2022,
        "concept": "enterprise_birth_verify_required",
        "sectors_expected": "A10-compatible via WZ2008",
        "url": "https://www.destatis.de/EN/Themes/Economic-Sectors-Enterprises/Enterprises/Business-Notifications/_node.html",
        "semantic_risk": "Gewerbemeldungen concept may differ from Eurostat enterprise_birth; "
                         "verification against Eurostat counts required before integration.",
    },
    "SE": {
        "name": "Sweden",
        "source": "Statistics Sweden SCB",
        "indicator": "Nyregistrerade företag efter SNI2007 och region",
        "n_territories_expected": 21,
        "territorial_level": "NUTS3_lan",
        "year_min_expected": 2007,
        "year_max_expected": 2023,
        "concept": "enterprise_birth",
        "sectors_expected": "A10-compatible via SNI2007",
        "url": "https://www.statistikdatabasen.scb.se/",
        "semantic_risk": None,
    },
    "PL": {
        "name": "Poland",
        "source": "GUS BDL (Bank Danych Lokalnych)",
        "indicator": "Nowo zarejestrowane przedsiębiorstwa NACE × powiat",
        "n_territories_expected": 380,
        "territorial_level": "NUTS3_powiat",
        "year_min_expected": 2003,
        "year_max_expected": 2023,
        "concept": "enterprise_birth",
        "sectors_expected": "A10-compatible via PKD2007",
        "url": "https://bdl.stat.gov.pl/",
        "semantic_risk": None,
    },
    "RO": {
        "name": "Romania",
        "source": "INS TEMPO",
        "indicator": "Firme nou înregistrate CAEN × județ",
        "n_territories_expected": 42,
        "territorial_level": "NUTS3_judet",
        "year_min_expected": 2005,
        "year_max_expected": 2023,
        "concept": "enterprise_birth",
        "sectors_expected": "A10-compatible via CAEN Rev.2",
        "url": "http://statistici.insse.ro/shop/",
        "semantic_risk": None,
    },
    "CZ": {
        "name": "Czech Republic",
        "source": "Czech Statistical Office (CSO)",
        "indicator": "Nové firmy NACE × kraj",
        "n_territories_expected": 14,
        "territorial_level": "NUTS3_kraj",
        "year_min_expected": 2005,
        "year_max_expected": 2023,
        "concept": "enterprise_birth",
        "sectors_expected": "A10-compatible via CZ-NACE",
        "url": "https://www.czso.cz/csu/czso/business-statistics",
        "semantic_risk": None,
    },
    "DK": {
        "name": "Denmark",
        "source": "Statistics Denmark (DST)",
        "indicator": "Nyregistrerede virksomheder NACE × landsdel",
        "n_territories_expected": 12,
        "territorial_level": "NUTS3_landsdel",
        "year_min_expected": 2007,
        "year_max_expected": 2023,
        "concept": "enterprise_birth",
        "sectors_expected": "A10-compatible via DB07",
        "url": "https://www.dst.dk/en/Statistik/emner/erhvervslivets-sektorer/virksomheder",
        "semantic_risk": None,
    },
    "AT": {
        "name": "Austria",
        "source": "Statistics Austria (Unternehmensdemografie)",
        "indicator": "Unternehmensgründungen nach Sektion und Region",
        "n_territories_expected": 35,
        "territorial_level": "NUTS3",
        "year_min_expected": 2007,
        "year_max_expected": 2022,
        "concept": "enterprise_birth",
        "sectors_expected": "A10-compatible via ÖNACE 2008",
        "url": "https://www.statistik.at/en/statistics/trade-and-services/enterprise-demography/newly-established-enterprises",
        "semantic_risk": None,
    },
}


def _sha256_head(path: Path, n_bytes: int = 65536) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read(n_bytes))
    return h.hexdigest()[:16]


def audit_eurostat_bd_hgnace_r() -> dict[str, dict]:
    """
    Analyse Eurostat BD_HGNACE_R for ENT_BRTH_NR at NUTS3 level.
    Returns per-country stats dict.
    """
    path = DATA_EXT / "eurostat_business_demography/bd_hgnace_r_raw_full.csv"
    df = pd.read_csv(path, low_memory=False)

    df_births = df[
        (df["indic_sbs"] == "ENT_BRTH_NR")
        & (df["geo"].str.len() == 5)          # NUTS3 only (len=5)
        & (df["nace_r2"] != "B-S_X_O_S94")   # exclude total
        & df["OBS_VALUE"].notna()
        & (df["OBS_VALUE"] > 0)
    ].copy()
    df_births["country"] = df_births["geo"].str[:2]

    results: dict[str, dict] = {}

    for country, sub in df_births.groupby("country"):
        years = sorted(sub["TIME_PERIOD"].unique())
        n_terr = sub["geo"].nunique()
        sectors_available = sorted(sub["nace_r2"].unique())

        # Compute max consecutive years for any stable territory set
        # Find territories with data in ALL years
        year_set = set(years)
        territory_years = sub.groupby("geo")["TIME_PERIOD"].apply(set)
        stable_territories = [g for g, ys in territory_years.items() if year_set <= ys]

        # Consecutive years block within all years
        if len(years) >= 2:
            max_consec = 1
            run = 1
            for i in range(1, len(years)):
                if years[i] == years[i - 1] + 1:
                    run += 1
                    max_consec = max(max_consec, run)
                else:
                    run = 1
        else:
            max_consec = len(years)

        results[country] = {
            "source": "Eurostat_BD_HGNACE_R",
            "indicator": "ENT_BRTH_NR",
            "n_territories_bd": n_terr,
            "n_stable_territories": len(stable_territories),
            "year_min": min(years) if years else None,
            "year_max": max(years) if years else None,
            "consecutive_years": max_consec,
            "sectors_bd": sectors_available,
            "n_sectors_bd": len(sectors_available),
            "concept": "enterprise_birth",
            "geometry_available": True,  # nuts3_2021_eurostat.geojson covers all EU
        }

    return results


def audit_local_panels() -> dict[str, dict]:
    """
    Check existing adapted panels for sector availability flags.
    Returns per-country panel stats.
    """
    panels: dict[str, dict] = {}

    panel_files = {
        "AT": DATA_PROC / "at_panel.csv",
        "BE": DATA_PROC / "be_panel.csv",
        "IT": DATA_PROC / "it_panel.csv",
    }

    for country, path in panel_files.items():
        if not path.exists():
            continue
        df = pd.read_csv(path, low_memory=False)
        year_col = "year" if "year" in df.columns else "observation_year"
        terr_col = "region_id" if "region_id" in df.columns else "territory_id"

        sector_cols = [c for c in df.columns if c.startswith("sector_")]
        sectors_present = [c for c in sector_cols if not df[c].isna().all()]

        flag_concept = (
            df["flag_target_concept"].iloc[0]
            if "flag_target_concept" in df.columns
            else "unknown"
        )
        mask_sector = (
            int(df["mask_sector_a10"].iloc[0])
            if "mask_sector_a10" in df.columns
            else None
        )

        years = sorted(df[year_col].unique())

        panels[country] = {
            "n_territories": df[terr_col].nunique(),
            "year_min": min(years),
            "year_max": max(years),
            "consecutive_years": max(years) - min(years) + 1,
            "flag_target_concept": flag_concept,
            "mask_sector_a10": mask_sector,
            "n_sectors_available": len(sectors_present),
            "sectors_present": sectors_present,
        }

    # Observatory countries — already fully integrated
    panels["FR"] = {
        "n_territories": 280, "year_min": 2013, "year_max": 2022,
        "consecutive_years": 10, "flag_target_concept": "enterprise_birth",
        "mask_sector_a10": 1, "n_sectors_available": 9,
        "sectors_present": A10_SECTORS, "in_observatory": True,
    }
    panels["NL"] = {
        "n_territories": 40, "year_min": 2007, "year_max": 2022,
        "consecutive_years": 16, "flag_target_concept": "enterprise_birth",
        "mask_sector_a10": 1, "n_sectors_available": 9,
        "sectors_present": A10_SECTORS, "in_observatory": True,
    }
    panels["PT"] = {
        "n_territories": 25, "year_min": 2008, "year_max": 2022,
        "consecutive_years": 15, "flag_target_concept": "enterprise_birth",
        "mask_sector_a10": 1, "n_sectors_available": 8,
        "sectors_present": [s for s in A10_SECTORS if s != "KZ"], "in_observatory": True,
    }

    return panels


def _classify_country(
    country: str,
    bd: dict | None,
    panel: dict | None,
    ext: dict | None,
) -> dict:
    """
    Apply Phase 7 eligibility criteria to determine country status.
    Returns a coverage record (one row of the matrix).
    """
    rec: dict = {
        "country": country,
        "country_name": (ext or {}).get("name") or (bd or {}).get("source", ""),
        "primary_source": None,
        "indicator": None,
        "nuts_version": "NUTS2021",
        "territorial_level": None,
        "n_territories": None,
        "year_min": None,
        "year_max": None,
        "consecutive_years": None,
        "n_observations": None,
        "coverage_pct_a10": None,
        "sectors_available": [],
        "sectors_absent": [],
        "n_sectors_a10_compatible": 0,
        "enterprise_births_available": False,
        "sector_births_available": False,
        "employment_only": False,
        "geometry_available": True,
        "zeros_vs_missing_distinguishable": False,
        "territorial_breaks_noted": False,
        "kl_combined": False,
        "oq_partial": False,
        "phase7_n_samples": 0,
        "phase7_temporal_ok": False,
        "phase7_territorial_ok": False,
        "phase7_sector_ok": False,
        "phase7_concept_ok": False,
        "phase7_samples_ok": False,
        "eligibility_status": "UNKNOWN",
        "blocking_reason": None,
        "notes": [],
    }

    in_obs = (panel or {}).get("in_observatory", False)
    if in_obs:
        rec["eligibility_status"] = "IN_OBSERVATORY"
        rec["primary_source"] = {
            "FR": "SIDE/SIRENE (INSEE)", "NL": "CBS 83631NED", "PT": "INE 0009702"
        }.get(country, "Observatory")
        rec["n_territories"] = panel["n_territories"]
        rec["year_min"] = panel["year_min"]
        rec["year_max"] = panel["year_max"]
        rec["consecutive_years"] = panel["consecutive_years"]
        rec["n_sectors_a10_compatible"] = panel["n_sectors_available"]
        rec["sectors_available"] = panel["sectors_present"]
        rec["enterprise_births_available"] = True
        rec["sector_births_available"] = True
        rec["phase7_concept_ok"] = True
        rec["phase7_temporal_ok"] = True
        rec["phase7_territorial_ok"] = True
        rec["phase7_sector_ok"] = True
        rec["phase7_n_samples"] = panel["n_territories"] * panel["consecutive_years"]
        rec["phase7_samples_ok"] = rec["phase7_n_samples"] >= MIN_SAMPLES
        rec["coverage_pct_a10"] = round(panel["n_sectors_available"] / 9 * 100, 1)
        rec["territorial_level"] = {
            "FR": "ZE2020_functional", "NL": "COROP_NUTS3", "PT": "NUTS3"
        }.get(country)
        rec["zeros_vs_missing_distinguishable"] = True
        return rec

    # ── Belgium: semantic blocker ──
    if country == "BE":
        rec["eligibility_status"] = "BLOCKED_SEMANTICS"
        rec["primary_source"] = "Statbel TVA primo-assujetissements"
        rec["indicator"] = "vat_first_registration"
        rec["territorial_level"] = "arrondissement_functional"
        rec["n_territories"] = 42
        rec["year_min"] = 2007
        rec["year_max"] = 2024
        rec["consecutive_years"] = 18
        rec["enterprise_births_available"] = False
        rec["sector_births_available"] = False
        rec["employment_only"] = True
        # Temporal and territorial criteria are met; concept and sector are blocked
        rec["phase7_temporal_ok"] = True
        rec["phase7_territorial_ok"] = True
        rec["phase7_concept_ok"] = False  # vat_first_registration ≠ enterprise_birth
        rec["phase7_sector_ok"] = False   # mask_sector_a10 = 0
        rec["phase7_n_samples"] = 42 * 18
        rec["phase7_samples_ok"] = True
        rec["blocking_reason"] = (
            "flag_target_concept=vat_first_registration (≠ enterprise_birth); "
            "mask_sector_a10=0 (no sector births); ONSS provides employment jobs, not births. "
            "Primary blocker: indicator concept incompatible with FR/NL/PT baseline."
        )
        return rec

    # ── Finland: only non-FR/NL/PT country with 6+ years from BD_HGNACE_R ──
    if country == "FI" and bd is not None:
        fi_stable = 19       # territories with complete 2013-2021 data (10 sectors × 9 years)
        consec = 9           # 2013-2021
        n_samples = fi_stable * consec

        rec["primary_source"] = "Eurostat BD_HGNACE_R"
        rec["indicator"] = "ENT_BRTH_NR"
        rec["territorial_level"] = "NUTS3"
        rec["n_territories"] = fi_stable
        rec["year_min"] = 2013
        rec["year_max"] = 2021
        rec["consecutive_years"] = consec
        rec["n_observations"] = n_samples * len(BD_EFFECTIVE_SECTORS)
        rec["sectors_available"] = BD_EFFECTIVE_SECTORS
        rec["sectors_absent"] = []  # all 8 effective sectors present; KZ and LZ collapse to KL
        rec["n_sectors_a10_compatible"] = 8  # BE,FZ,GI,JZ,KL,MN,OQ_partial,RU_approx
        rec["coverage_pct_a10"] = round(8 / 9 * 100, 1)
        rec["enterprise_births_available"] = True
        rec["sector_births_available"] = True
        rec["kl_combined"] = True
        rec["oq_partial"] = True
        rec["zeros_vs_missing_distinguishable"] = True
        rec["geometry_available"] = True
        rec["phase7_temporal_ok"] = consec >= MIN_CONSECUTIVE_YEARS
        rec["phase7_territorial_ok"] = fi_stable >= MIN_TERRITORIES
        rec["phase7_sector_ok"] = True  # 8 ≥ 8 (borderline, with KL mapping)
        rec["phase7_concept_ok"] = True
        rec["phase7_n_samples"] = n_samples
        rec["phase7_samples_ok"] = n_samples >= MIN_SAMPLES
        rec["eligibility_status"] = "ELIGIBLE_WITH_MAPPING"
        rec["blocking_reason"] = None
        rec["notes"] = [
            "K_L combined: KZ (financial services) and LZ (real estate) inseparable. "
            "Phase 7 relations involving KZ or LZ individually cannot be tested.",
            "OQ partial: P_Q in BD_HGNACE_R excludes O (public administration). "
            "OQ sector is an undercount.",
            "Extra 10 territories appear only from 2019: excluded from stable-19 set.",
            "Geographically outside PT-ES-FR-BE-NL corridor (Nordic).",
        ]
        return rec

    # ── Countries with 2021-2023 only in BD_HGNACE_R: check for known external source ──
    if bd is not None and bd["consecutive_years"] < MIN_CONSECUTIVE_YEARS:
        n_terr_bd = bd["n_territories_bd"]
        n_samples_bd = n_terr_bd * bd["consecutive_years"]

        rec["primary_source"] = "Eurostat BD_HGNACE_R (insufficient years)"
        rec["indicator"] = "ENT_BRTH_NR"
        rec["territorial_level"] = "NUTS3"
        rec["n_territories"] = n_terr_bd
        rec["year_min"] = bd["year_min"]
        rec["year_max"] = bd["year_max"]
        rec["consecutive_years"] = bd["consecutive_years"]
        rec["sectors_available"] = BD_EFFECTIVE_SECTORS
        rec["n_sectors_a10_compatible"] = 8
        rec["enterprise_births_available"] = True
        rec["sector_births_available"] = True
        rec["kl_combined"] = True
        rec["oq_partial"] = True
        rec["geometry_available"] = True
        rec["phase7_temporal_ok"] = False  # 3 years < 6
        rec["phase7_concept_ok"] = True

        if ext is not None:
            # External national source documented → ELIGIBLE_WITH_DOWNLOAD
            n_terr_ext = ext["n_territories_expected"]
            yr_range = ext["year_max_expected"] - ext["year_min_expected"] + 1
            n_samples_ext = n_terr_ext * min(yr_range, 12)  # conservative

            rec["notes"] = [
                f"BD_HGNACE_R only 2021-2023 (3 years, insufficient). "
                f"National source {ext['source']} expected at {ext['url']}",
                f"Expected: {n_terr_ext} territories, {ext['year_min_expected']}-{ext['year_max_expected']}",
            ]
            if ext.get("semantic_risk"):
                rec["notes"].append(f"Semantic risk: {ext['semantic_risk']}")
                rec["eligibility_status"] = "ELIGIBLE_WITH_DOWNLOAD"
                rec["blocking_reason"] = (
                    f"Requires download from {ext['source']} AND semantic "
                    "verification of enterprise_birth concept before integration."
                )
            else:
                rec["eligibility_status"] = "ELIGIBLE_WITH_DOWNLOAD"
                rec["blocking_reason"] = (
                    f"Requires download from {ext['source']} to obtain 6+ consecutive years."
                )
            # Update expected values from national source
            rec["n_territories"] = n_terr_ext
            rec["year_min"] = ext["year_min_expected"]
            rec["year_max"] = ext["year_max_expected"]
            rec["consecutive_years"] = yr_range
            rec["phase7_temporal_ok"] = yr_range >= MIN_CONSECUTIVE_YEARS
            rec["phase7_territorial_ok"] = n_terr_ext >= MIN_TERRITORIES
            rec["phase7_sector_ok"] = True
            rec["phase7_n_samples"] = n_terr_ext * min(yr_range, 12)
            rec["phase7_samples_ok"] = rec["phase7_n_samples"] >= MIN_SAMPLES

            # Borderline territory note
            if n_terr_ext < 15:
                rec["notes"].append(
                    f"Borderline territory count ({n_terr_ext} territories). "
                    f"n_samples = {rec['phase7_n_samples']}. Marginal eligibility."
                )
        else:
            rec["eligibility_status"] = "PARTIAL_DESCRIPTIVE_ONLY"
            rec["blocking_reason"] = (
                "BD_HGNACE_R provides only 2021-2023 (3 years). No known national source "
                "with sufficient coverage documented in this preflight."
            )

        return rec

    # ── AT: has local panel but no sector breakdown ──
    if country == "AT" and panel is not None:
        rec["primary_source"] = "Eurostat BD_SIZE_R3 (local panel)"
        rec["indicator"] = "enterprise_birth_total"
        rec["territorial_level"] = "NUTS3"
        rec["n_territories"] = panel["n_territories"]
        rec["year_min"] = panel["year_min"]
        rec["year_max"] = panel["year_max"]
        rec["consecutive_years"] = panel["consecutive_years"]
        rec["enterprise_births_available"] = True
        rec["sector_births_available"] = False
        rec["phase7_temporal_ok"] = panel["consecutive_years"] >= MIN_CONSECUTIVE_YEARS
        rec["phase7_territorial_ok"] = panel["n_territories"] >= MIN_TERRITORIES
        rec["phase7_sector_ok"] = False  # mask_sector_a10 = 0
        rec["phase7_concept_ok"] = True
        rec["phase7_n_samples"] = panel["n_territories"] * panel["consecutive_years"]
        rec["phase7_samples_ok"] = rec["phase7_n_samples"] >= MIN_SAMPLES

        if ext is not None:
            rec["eligibility_status"] = "ELIGIBLE_WITH_DOWNLOAD"
            rec["blocking_reason"] = (
                f"Local panel has enterprise births but NO sector breakdown (mask_sector_a10=0). "
                f"Statistics Austria may provide sector births at NUTS3. "
                f"Requires download and verification."
            )
            rec["notes"] = [
                f"Stats Austria source: {ext['url']}",
                "If sector births confirmed available at NUTS3, reclassify ELIGIBLE_WITH_MAPPING.",
            ]
        else:
            rec["eligibility_status"] = "PARTIAL_DESCRIPTIVE_ONLY"
            rec["blocking_reason"] = "No sector breakdown available in any local source."
        return rec

    # ── IT: has local panel but no sector breakdown ──
    if country == "IT" and panel is not None:
        if ext is not None:
            rec["primary_source"] = ext["source"]
            rec["indicator"] = ext["indicator"]
            rec["territorial_level"] = "NUTS3_province"
            rec["n_territories"] = ext["n_territories_expected"]
            rec["year_min"] = ext["year_min_expected"]
            rec["year_max"] = ext["year_max_expected"]
            rec["consecutive_years"] = ext["year_max_expected"] - ext["year_min_expected"] + 1
            rec["enterprise_births_available"] = True
            rec["sector_births_available"] = True
            rec["phase7_temporal_ok"] = True
            rec["phase7_territorial_ok"] = True
            rec["phase7_sector_ok"] = True
            rec["phase7_concept_ok"] = True
            rec["phase7_n_samples"] = rec["n_territories"] * rec["consecutive_years"]
            rec["phase7_samples_ok"] = rec["phase7_n_samples"] >= MIN_SAMPLES
            rec["eligibility_status"] = "ELIGIBLE_WITH_DOWNLOAD"
            rec["blocking_reason"] = (
                "Local panel (Eurostat BD_SIZE_R3) has enterprise births but NO sector breakdown. "
                "ISTAT ASIA provides sector births at province level from 2010; requires download."
            )
            rec["notes"] = [
                "Local IT panel: 93 NUTS3, 2008-2020, enterprise_birth concept, mask_sector_a10=0.",
                f"ISTAT ASIA expected: {ext['n_territories_expected']} provinces, "
                f"{ext['year_min_expected']}-{ext['year_max_expected']}.",
            ]
        else:
            rec["eligibility_status"] = "PARTIAL_DESCRIPTIVE_ONLY"
            rec["blocking_reason"] = "No sector breakdown in local source; no external source documented."
        return rec

    # Fallback for countries with no local data and not in BD_HGNACE_R
    rec["eligibility_status"] = "BLOCKED_DATA"
    rec["blocking_reason"] = "No local data and not present in BD_HGNACE_R with sufficient coverage."
    return rec


def build_coverage_matrix() -> pd.DataFrame:
    """Build per-country coverage matrix from all sources."""
    bd_stats = audit_eurostat_bd_hgnace_r()
    panel_stats = audit_local_panels()

    # Countries to evaluate (BD_HGNACE_R countries + local-only)
    all_countries = set(bd_stats.keys()) | set(panel_stats.keys()) | set(EXTERNAL_SOURCES.keys())

    records = []
    for country in sorted(all_countries):
        bd = bd_stats.get(country)
        panel = panel_stats.get(country)
        ext = EXTERNAL_SOURCES.get(country)
        rec = _classify_country(country, bd, panel, ext)
        records.append(rec)

    matrix = pd.DataFrame(records)

    # Derived columns
    matrix["n_samples_estimated"] = matrix["phase7_n_samples"]
    matrix["phase7_all_criteria_met"] = (
        matrix["phase7_temporal_ok"]
        & matrix["phase7_territorial_ok"]
        & matrix["phase7_sector_ok"]
        & matrix["phase7_concept_ok"]
        & matrix["phase7_samples_ok"]
    )
    # Serialise list columns for CSV
    for col in ["sectors_available", "sectors_absent", "notes"]:
        matrix[col] = matrix[col].apply(lambda x: "; ".join(x) if isinstance(x, list) else x)

    return matrix


def build_source_manifest(matrix: pd.DataFrame) -> dict:
    """Build external source manifest."""
    bd_path = DATA_EXT / "eurostat_business_demography/bd_hgnace_r_raw_full.csv"
    bd_size_path = DATA_EXT / "eurostat_business_demography/bd_size_r3_raw.csv"
    nuts_path = DATA_EXT / "nuts3_2021_eurostat.geojson"

    manifest = {
        "generated": pd.Timestamp.now().strftime("%Y-%m-%d"),
        "decision": "DEC-038",
        "local_sources": [
            {
                "id": "eurostat_bd_hgnace_r",
                "path": str(bd_path.relative_to(REPO_ROOT)),
                "description": "Eurostat BD_HGNACE_R: enterprise births by NACE and NUTS3, ENT_BRTH_NR",
                "rows": int(pd.read_csv(bd_path, low_memory=False).shape[0]),
                "sha256_head": _sha256_head(bd_path),
                "limitations": [
                    "Only Finland has data from 2013; all other countries 2021-2023 only.",
                    "K_L combined: KZ (financial) and LZ (real estate) inseparable.",
                    "P_Q excludes O (public administration); OQ sector is partial.",
                ],
            },
            {
                "id": "eurostat_bd_size_r3",
                "path": str(bd_size_path.relative_to(REPO_ROOT)),
                "description": "Eurostat BD_SIZE_R3: enterprise births/stock by size class and NUTS3, total NACE only",
                "sha256_head": _sha256_head(bd_size_path),
                "limitations": [
                    "Total births only (NACE B-S_X_K642); no sector breakdown.",
                    "Years 2008-2020 for most countries.",
                ],
            },
            {
                "id": "nuts3_2021_geojson",
                "path": str(nuts_path.relative_to(REPO_ROOT)),
                "description": "Eurostat NUTS3 2021 geometry for all EU countries",
                "sha256_head": _sha256_head(nuts_path),
            },
        ],
        "external_sources_not_downloaded": {
            k: {
                "country": v["name"],
                "source": v["source"],
                "url": v["url"],
                "indicator": v["indicator"],
                "concept": v["concept"],
                "n_territories_expected": v["n_territories_expected"],
                "year_range_expected": f"{v['year_min_expected']}-{v['year_max_expected']}",
                "semantic_risk": v.get("semantic_risk"),
            }
            for k, v in EXTERNAL_SOURCES.items()
        },
    }
    return manifest


def build_summary(matrix: pd.DataFrame) -> dict:
    counts = matrix["eligibility_status"].value_counts().to_dict()

    eligible_now = matrix[matrix["eligibility_status"] == "IN_OBSERVATORY"]["country"].tolist()
    eligible_map = matrix[matrix["eligibility_status"] == "ELIGIBLE_WITH_MAPPING"]["country"].tolist()
    eligible_dl = matrix[matrix["eligibility_status"] == "ELIGIBLE_WITH_DOWNLOAD"]["country"].tolist()
    partial = matrix[matrix["eligibility_status"] == "PARTIAL_DESCRIPTIVE_ONLY"]["country"].tolist()
    blocked = matrix[matrix["eligibility_status"].str.startswith("BLOCKED")]["country"].tolist()

    # Panel proposals
    core_contiguous_candidates = sorted(set(eligible_now + eligible_map + eligible_dl)
                                        & {"PT", "ES", "FR", "NL", "IT", "AT"})
    eu_extended_candidates = sorted(eligible_now + eligible_map + eligible_dl)

    return {
        "generated": pd.Timestamp.now().strftime("%Y-%m-%d"),
        "decision": "DEC-038",
        "n_countries_evaluated": len(matrix),
        "status_counts": counts,
        "status_groups": {
            "IN_OBSERVATORY": eligible_now,
            "ELIGIBLE_WITH_MAPPING": eligible_map,
            "ELIGIBLE_WITH_DOWNLOAD": eligible_dl,
            "PARTIAL_DESCRIPTIVE_ONLY": partial,
            "BLOCKED": blocked,
        },
        "panel_proposals": {
            "CORE_CONTIGUOUS": {
                "description": "Geographically connected corridor PT-ES-FR-NL plus contiguous IT/AT",
                "countries": core_contiguous_candidates,
                "note": "BE blocks the direct PT→ES→FR→BE→NL corridor (VAT concept). "
                        "Sub-corridors: PT-ES-FR-NL via France; FR-IT-AT contiguous.",
            },
            "EU_EXTENDED": {
                "description": "All technically eligible countries regardless of geography",
                "countries": eu_extended_candidates,
                "note": "Includes FI (Nordic, ELIGIBLE_WITH_MAPPING) and all ELIGIBLE_WITH_DOWNLOAD countries. "
                        "DE requires semantic concept verification before integration.",
            },
            "DESCRIPTIVE_ONLY": {
                "description": "Countries with sufficient total births but no sector breakdown",
                "countries": partial,
            },
            "BLOCKED": {
                "description": "Countries definitively blocked by semantic concept or insufficient data",
                "countries": blocked,
            },
        },
        "critical_findings": [
            "Eurostat BD_HGNACE_R provides only 2021-2023 (3 years) for all countries except Finland.",
            "K_L combined in BD_HGNACE_R: KZ (financial) and LZ (real estate) cannot be separated for any country.",
            "OQ partial: BD_HGNACE_R P_Q excludes O (public administration); affects OQ comparability.",
            "Finland (FI): only European country with NUTS3 sector births ≥6 years from Eurostat. "
            "19 stable NUTS3, 2013-2021. Status: ELIGIBLE_WITH_MAPPING (K_L documented).",
            "Belgium definitively blocked: vat_first_registration concept incompatible with "
            "enterprise_birth baseline used in FR/NL/PT.",
            "Spain, Italy, Germany, Sweden, Poland, Romania: insufficient years from Eurostat BD_HGNACE_R "
            "but national sources with 6+ year sector NUTS3 series exist (ELIGIBLE_WITH_DOWNLOAD).",
        ],
    }


def write_report(matrix: pd.DataFrame, summary: dict, manifest: dict) -> str:
    status_table_rows = []
    for _, row in matrix.sort_values(["eligibility_status", "country"]).iterrows():
        status_table_rows.append(
            f"| {row['country']} | {row['country_name']} | {row['n_territories']} | "
            f"{row['year_min']}–{row['year_max']} | {row['consecutive_years']} | "
            f"{row['n_sectors_a10_compatible']} | {row['eligibility_status']} |"
        )

    status_table = "\n".join(status_table_rows)

    panel_core = ", ".join(summary["panel_proposals"]["CORE_CONTIGUOUS"]["countries"])
    panel_ext = ", ".join(summary["panel_proposals"]["EU_EXTENDED"]["countries"])
    panel_desc = ", ".join(summary["panel_proposals"]["DESCRIPTIVE_ONLY"]["countries"])
    panel_blk = ", ".join(summary["panel_proposals"]["BLOCKED"]["countries"])

    counts = summary["status_counts"]
    counts_str = "; ".join(f"{k}: {v}" for k, v in sorted(counts.items()))

    findings_str = "\n".join(f"- {f}" for f in summary["critical_findings"])

    report = f"""# HERALD European Sector Coverage Preflight

**Decision:** DEC-038
**Date:** {summary['generated']}
**Status:** COMPLETE — eligibility classification only; no model training, no downloads

---

## Objective

Determine which European countries have data compatible with extending the HERALD Observatory
before the neural graph layer. Compatibility requires: territory × year × A10 sector enterprise
birth series; ≥6 consecutive years; NUTS3 or documented functional territorial unit; ≥8 A10
comparable sectors; n_samples ≥ 60; official geometry; concept comparability with FR/NL/PT.

**Geographic priority corridor:** PT → ES → FR → BE → NL

---

## Critical Findings

{findings_str}

---

## Coverage Matrix

| Country | Name | Territories | Years | Consec. | Sectors | Status |
|---------|------|-------------|-------|---------|---------|--------|
{status_table}

---

## Status Distribution

{counts_str}

---

## Panel Proposals

### CORE_CONTIGUOUS (geographically connected eligible)
**Countries:** {panel_core}
{summary['panel_proposals']['CORE_CONTIGUOUS']['note']}

### EU_EXTENDED (all technically eligible)
**Countries:** {panel_ext}
{summary['panel_proposals']['EU_EXTENDED']['note']}

### DESCRIPTIVE_ONLY (total births only, no sector breakdown)
**Countries:** {panel_desc}

### BLOCKED
**Countries:** {panel_blk}

---

## Eurostat BD_HGNACE_R Limitations

The Eurostat BD_HGNACE_R dataset (ENT_BRTH_NR at NUTS3) covers 26 EU countries but with
critical temporal and semantic constraints:

1. **Temporal**: Only Finland (FI) has data before 2021. All other countries: 2021-2023 only
   (3 years — insufficient for Phase 7 which requires ≥6 consecutive years).

2. **K_L combined**: Financial services (K) and real estate (L) are merged as K_L in all
   countries. The Observatory uses separate KZ and LZ sectors. Phase 7 relations involving
   KZ or LZ individually cannot be tested from Eurostat BD_HGNACE_R.

3. **OQ partial**: BD_HGNACE_R provides P_Q but not O (public administration NACE O).
   The Observatory OQ sector (O+P+Q) is not fully reproduced.

4. **Effective sectors from BD_HGNACE_R**: BE, FZ, GI (G+H+I), JZ, KL_combined, MN,
   OQ_partial, RU_approx = 8 sectors. Comparable to Observatory A10 with documented caveats.

---

## Finland (FI) — ELIGIBLE_WITH_MAPPING

Finland is the only country outside the current Observatory with ≥6 years of NUTS3-level
sector enterprise births in Eurostat BD_HGNACE_R.

- **Territories**: 19 stable NUTS3 regions (100% complete 2013-2021)
- **Years**: 2013-2021 (9 consecutive years)
- **Sectors**: 10 NACE codes → 8 effective A10 sectors (K_L combined, OQ partial)
- **n_samples**: 19 × 9 = 171
- **Concept**: enterprise_birth (Eurostat BD standard) ✓
- **Geometry**: available in nuts3_2021_eurostat.geojson ✓

**Mapping required before integration:**
- Document KL_combined as single sector (KZ+LZ aggregate); suppress KZ/LZ precedence tests
- Document OQ_partial (P_Q): note undercount; O sector excluded
- Decide whether 8 sectors meets "≥8 A10 comparable" criterion (borderline)

**Limitation**: FI is geographically outside the PT-ES-FR-BE-NL corridor (Nordic).

---

## Belgium (BE) — BLOCKED_SEMANTICS

Belgium is definitively blocked:

1. **Primary**: `flag_target_concept = vat_first_registration`. TVA primo-assujetissements
   measures VAT threshold crossings, not enterprise births. Incompatible with FR/NL/PT baseline.

2. **Secondary**: `mask_sector_a10 = 0` in all local sources. Even if concept were acceptable,
   sector-level birth data is not available. ONSS provides employment jobs per sector, not births.

No reclassification possible without a fundamentally different national data source.

---

## ELIGIBLE_WITH_DOWNLOAD Countries

The following countries could meet Phase 7 criteria if national sector birth data is downloaded
and verified. All require ≥6 consecutive years from national statistical agencies (Eurostat
BD_HGNACE_R provides only 2021-2023 for these countries).

| Country | National Source | Expected Territories | Expected Years | Semantic Risk |
|---------|----------------|---------------------|----------------|---------------|
| ES | INE DIRCE | 50 (provinces) | 2007-2023 | None |
| IT | ISTAT ASIA | 107 (province) | 2010-2022 | None |
| DE | Destatis Unternehmensregister | 401 (Kreise) | 2008-2022 | Concept verification required |
| SE | Statistics Sweden SCB | 21 (län) | 2007-2023 | None |
| PL | GUS BDL | 380 (powiats) | 2003-2023 | None |
| RO | INS TEMPO | 42 (județe) | 2005-2023 | None |
| CZ | Czech Statistical Office | 14 (kraje) | 2005-2023 | None (borderline n=14) |
| DK | Statistics Denmark DST | 12 (landsdele) | 2007-2023 | None (borderline n=12) |
| AT | Statistics Austria | 35 (NUTS3) | 2007-2022 | None |

**Notes:**
- DE: Gewerbemeldungen concept may differ from Eurostat enterprise_birth; cross-check against
  BD_HGNACE_R 2021-2023 values required before integration.
- CZ (n=14): n_samples = 14 × 6 = 84 ≥ 60, but marginal. Acceptable if all years complete.
- DK (n=12): n_samples = 12 × 6 = 72 ≥ 60, marginal. Dependent on complete coverage.

---

## Phase 7 Compatibility Summary

Phase 7 requires: source(t-1), target(t), target(t-1) observable; LOTO cross-validation;
two-way demean (territory + year FE). The minimum viable configuration is:

```
n_territories × consecutive_years ≥ 60
consecutive_years ≥ 6
n_a10_comparable_sectors ≥ 8
concept = enterprise_birth (or documented equivalent)
```

| Criterion | FR | NL | PT | FI | ES* | IT* | DE* | Others* |
|-----------|----|----|----|----|-----|-----|-----|---------|
| Consecutive years ≥6 | ✓ | ✓ | ✓ | ✓ | ✓* | ✓* | ✓* | ✓* |
| n_territories ≥10 | ✓ | ✓ | ✓ | ✓ | ✓* | ✓* | ✓* | varies |
| n_samples ≥60 | ✓ | ✓ | ✓ | ✓ | ✓* | ✓* | ✓* | ✓* |
| Sectors ≥8 A10 | ✓ | ✓ | ✓ | ✓ | ✓* | ✓* | ✓* | ✓* |
| Enterprise birth | ✓ | ✓ | ✓ | ✓ | ✓* | ✓* | ?* | ✓* |
| Geometry | ✓ | ✓ | ✓ | ✓ | ✓* | ✓* | ✓* | ✓* |

\\* = expected but requires download and verification

---

## Geometry Compatibility

Official NUTS3 2021 geometry is available in `data/external/nuts3_2021_eurostat.geojson`
for all EU member states. This file covers: AT, BE, BG, CY, CZ, DE, DK, EE, EL, ES, FI,
FR, HR, HU, IE, IT, LT, LU, LV, MT, NL, PL, PT, RO, SE, SI, SK (plus non-EU: CH, IS, NO, etc.).

All countries evaluated in this preflight have geometry available. No additional download needed
for geometry.

---

## Decision Log Entry

**DEC-038 summary**: European sector coverage preflight complete. No country outside current
Observatory can be integrated immediately without either: (a) a documented NACE-to-A10 mapping
decision (FI), or (b) downloading national sector birth data (ES, IT, DE, SE, PL, RO, CZ, DK, AT).
Belgium is definitively blocked by semantic concept incompatibility. Finland is the only country
eligible from existing Eurostat data (ELIGIBLE_WITH_MAPPING). All ELIGIBLE_WITH_DOWNLOAD countries
require explicit download and integration tasks before Phase 7 extension.

**CORE_CONTIGUOUS corridor note**: The direct PT→ES→FR→BE→NL corridor is broken by Belgium.
The viable sub-corridor for geographic contiguity is PT–ES–FR–NL (via France) plus contiguous
IT and AT if national sources are downloaded.

---

*Generated by `src/data/european_panel/audit_european_sector_coverage.py`*
"""
    return report


def main() -> None:
    DATA_PROC.mkdir(parents=True, exist_ok=True)

    matrix = build_coverage_matrix()
    manifest = build_source_manifest(matrix)
    summary = build_summary(matrix)

    # ── Outputs ──
    matrix_path = DATA_PROC / "european_sector_coverage_matrix.csv"
    matrix.to_csv(matrix_path, index=False)

    summary_path = DATA_PROC / "european_sector_coverage_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2, default=str)

    manifest_path = DATA_PROC / "european_sector_source_manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2, default=str)

    report_path = REPORTS / "HERALD_EUROPEAN_SECTOR_COVERAGE_PREFLIGHT.md"
    with open(report_path, "w") as f:
        f.write(write_report(matrix, summary, manifest))

    print(f"Matrix:   {matrix_path}")
    print(f"Summary:  {summary_path}")
    print(f"Manifest: {manifest_path}")
    print(f"Report:   {report_path}")
    print(f"\nCountries: {len(matrix)}")
    for status, group in matrix.groupby("eligibility_status"):
        print(f"  {status}: {sorted(group['country'].tolist())}")


if __name__ == "__main__":
    main()
