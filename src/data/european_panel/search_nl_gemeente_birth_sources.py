"""
DEC-062 Part C: Search NL CBS catalog for gemeente × births × SBI sources.

Queries CBS OData API catalog for tables with:
- gemeente / GM code (geographic level)
- births / openings / oprichtingen (concept)
- sector / SBI / bedrijfstak (sector classification)
- ≥6 years coverage

DEC-061 already confirmed NL_GEMEENTE_BIRTHS_BLOCKED_VIA_CBS_OPEN_DATA.
This script performs a more systematic catalog search to document all
candidate tables and their rejection reasons.

No HPC. No raw large downloads. No causal claims.
"""

from __future__ import annotations
import json
import time
from pathlib import Path
from urllib.parse import urljoin

import requests

REPO_ROOT = Path(__file__).parents[3]
OUT_DIR = REPO_ROOT / "data/processed/granular_phase7_preflight"
OUT_CANDIDATES_CSV = OUT_DIR / "nl_gemeente_source_candidates.csv"
OUT_SEARCH_JSON = OUT_DIR / "nl_gemeente_source_search.json"

CBS_CATALOG_BASE = "https://opendata.cbs.nl/ODataCatalog/Tables"
CBS_ODATA_BASE = "https://opendata.cbs.nl/ODataFeed/OData/"

HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)", "Accept": "application/json"}

# Known tables from DEC-061 + additional candidates
KNOWN_TABLES = {
    "83631NED": {
        "title": "Vestigingen en oprichtingen van bedrijven; bedrijfstak, regio",
        "concept_nl": "oprichtingen (births/openings)",
        "geographic_levels": ["national", "province", "COROP"],
        "has_gemeente": False,
        "has_sector_sbi": True,
        "is_births": True,
        "period": "2007-2025",
        "verdict": "COROP_ONLY",
        "rejection_reason": "No gemeente level — only COROP (40 regions), province, and national",
    },
    "81575NED": {
        "title": "Vestigingen van bedrijven; bedrijfstak, gemeente",
        "concept_nl": "vestigingen (stock/bestand)",
        "geographic_levels": ["gemeente"],
        "has_gemeente": True,
        "has_sector_sbi": True,
        "is_births": False,
        "period": "2007-2026",
        "verdict": "STOCK_ONLY_NOT_ACCEPTABLE",
        "rejection_reason": "Establishment stock (bestand), not births/openings. Stock ≠ births without closure data.",
    },
    "81841NED": {
        "title": "Oprichtingen en opheffingen; bedrijfstak, regio",
        "concept_nl": "oprichtingen+opheffingen (births+closures)",
        "geographic_levels": ["national", "province", "COROP"],
        "has_gemeente": False,
        "has_sector_sbi": True,
        "is_births": True,
        "period": "2007-2013",
        "verdict": "COROP_ONLY",
        "rejection_reason": "No gemeente level; short period (2007-2013 only).",
    },
    "80234ned": {
        "title": "Vestigingen van bedrijven; SBI, gemeenten 2006-2010",
        "concept_nl": "vestigingen (stock)",
        "geographic_levels": ["gemeente"],
        "has_gemeente": True,
        "has_sector_sbi": True,
        "is_births": False,
        "period": "2006-2010",
        "verdict": "STOCK_ONLY_NOT_ACCEPTABLE",
        "rejection_reason": "Stock data, not births. Period too short and old (2006-2010).",
    },
}

# Search terms to probe CBS catalog
SEARCH_TERMS = [
    "oprichtingen gemeente",
    "oprichtingen bedrijfstak",
    "vestigingen oprichtingen",
    "bedrijfsdemografie gemeente",
    "bedrijven gemeente SBI",
    "bedrijfsvestigingen gemeente",
    "nieuwe bedrijven gemeente",
    "bedrijvendynamiek gemeente",
]

CLASSIFICATION_LABELS = {
    "ACCEPTABLE_OPEN_DATA": "Gemeente × births × SBI × ≥6 years — suitable for HERALD",
    "STOCK_ONLY_NOT_ACCEPTABLE": "Stock data, not births",
    "COROP_ONLY": "Only COROP/province level, not gemeente",
    "NO_SECTOR": "Gemeente and births but no sector breakdown",
    "NO_YEAR": "No time dimension",
    "WRONG_CONCEPT": "Wrong enterprise concept (e.g. number of enterprises not births)",
    "MICRODATA_REQUIRED": "Data exists but requires CBS Microdata access (ABR)",
    "UNKNOWN_NEEDS_MANUAL_REVIEW": "Cannot classify from metadata alone",
}


def fetch_cbs_catalog_page(skip: int = 0, top: int = 100) -> dict:
    """Fetch a page of CBS catalog entries."""
    params = {
        "$format": "json",
        "$top": top,
        "$skip": skip,
        "$select": "Identifier,Title,ShortTitle,Summary,Period,Size",
    }
    try:
        r = requests.get(CBS_CATALOG_BASE, params=params, headers=HEADERS, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"value": [], "error": str(e)}


def probe_table_dimensions(table_id: str) -> dict:
    """Get dimension names from CBS OData to check for gemeente/SBI/year."""
    url = f"{CBS_ODATA_BASE}{table_id}/TableInfos"
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        if r.status_code != 200:
            return {"error": f"HTTP {r.status_code}"}
        # Parse dimensions from Atom XML
        text = r.text
        has_gemeente = any(t in text.lower() for t in ["gemeente", "gm code", "wijk", "municipality"])
        has_births = any(t in text.lower() for t in ["oprichting", "orichting", "birth", "opening", "start"])
        has_sbi = any(t in text.lower() for t in ["sbi", "bedrijfstak", "sector", "nace"])
        has_year = any(t in text.lower() for t in ["jaar", "year", "perioden"])
        return {
            "has_gemeente": has_gemeente,
            "has_births_concept": has_births,
            "has_sbi": has_sbi,
            "has_year": has_year,
        }
    except Exception as e:
        return {"error": str(e)}


def classify_table(table_info: dict, dim_info: dict) -> tuple[str, str]:
    """Return (verdict, rejection_reason) for a CBS table."""
    # First check known tables
    table_id = table_info.get("Identifier", "")
    if table_id in KNOWN_TABLES:
        kt = KNOWN_TABLES[table_id]
        return kt["verdict"], kt["rejection_reason"]

    has_gemeente = dim_info.get("has_gemeente", False)
    has_births = dim_info.get("has_births_concept", False)
    has_sbi = dim_info.get("has_sbi", False)
    has_year = dim_info.get("has_year", False)

    if has_gemeente and has_births and has_sbi and has_year:
        return "ACCEPTABLE_OPEN_DATA", "Passes all criteria — needs verification"

    if not has_gemeente:
        return "COROP_ONLY", "No gemeente dimension detected"
    if not has_births:
        title = (table_info.get("Title", "") + table_info.get("Summary", "")).lower()
        if any(t in title for t in ["bestand", "stock", "vestiging"]):
            return "STOCK_ONLY_NOT_ACCEPTABLE", "Stock data (vestigingen bestand), not births"
        return "WRONG_CONCEPT", "No births/openings concept detected"
    if not has_sbi:
        return "NO_SECTOR", "No SBI/bedrijfstak dimension"
    if not has_year:
        return "NO_YEAR", "No year/period dimension"

    return "UNKNOWN_NEEDS_MANUAL_REVIEW", "Cannot classify from metadata"


def search_catalog_by_terms(terms: list[str], max_pages: int = 5) -> list[dict]:
    """Search CBS catalog for tables matching birth/gemeente terms."""
    found = {}

    for term in terms:
        # CBS catalog doesn't support keyword search via OData filter easily
        # Instead, scan through pages and filter by title/summary
        for page in range(max_pages):
            result = fetch_cbs_catalog_page(skip=page * 100, top=100)
            entries = result.get("value", [])
            if not entries:
                break

            term_parts = term.lower().split()
            for entry in entries:
                title_summary = (
                    entry.get("Title", "") + " " + entry.get("Summary", "")
                ).lower()
                if all(part in title_summary for part in term_parts):
                    table_id = entry.get("Identifier", "")
                    if table_id and table_id not in found:
                        found[table_id] = entry

            time.sleep(0.2)

    return list(found.values())


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("\nDEC-062 Part C: NL Gemeente Birth Source Search")
    print("=" * 55)

    # 1. Start with known tables from DEC-061
    candidates = []
    for table_id, info in KNOWN_TABLES.items():
        candidates.append({
            "table_id": table_id,
            "title": info["title"],
            "concept": info["concept_nl"],
            "has_gemeente": info["has_gemeente"],
            "has_sector_sbi": info["has_sector_sbi"],
            "is_births": info["is_births"],
            "period": info["period"],
            "verdict": info["verdict"],
            "rejection_reason": info["rejection_reason"],
            "source": "DEC-061",
        })

    # 2. Scan catalog for additional candidates
    print("\nScanning CBS catalog for additional candidates...")
    additional = search_catalog_by_terms(SEARCH_TERMS, max_pages=10)
    print(f"  Found {len(additional)} additional table matches from catalog scan")

    for entry in additional:
        table_id = entry.get("Identifier", "")
        if table_id in KNOWN_TABLES:
            continue  # already included

        print(f"  Probing table {table_id}...", end=" ")
        dim_info = probe_table_dimensions(table_id)
        verdict, reason = classify_table(entry, dim_info)
        print(f"{verdict}")

        candidates.append({
            "table_id": table_id,
            "title": entry.get("Title", ""),
            "concept": entry.get("Summary", "")[:100],
            "has_gemeente": dim_info.get("has_gemeente", False),
            "has_sector_sbi": dim_info.get("has_sbi", False),
            "is_births": dim_info.get("has_births_concept", False),
            "period": entry.get("Period", ""),
            "verdict": verdict,
            "rejection_reason": reason,
            "source": "catalog_search",
        })
        time.sleep(0.5)

    # 3. Save CSV
    import pandas as pd
    df = pd.DataFrame(candidates)
    df.to_csv(OUT_CANDIDATES_CSV, index=False)
    print(f"\nSaved: {OUT_CANDIDATES_CSV}")

    # 4. Determine overall NL decision
    acceptable = [c for c in candidates if c["verdict"] == "ACCEPTABLE_OPEN_DATA"]
    n_acceptable = len(acceptable)

    if n_acceptable > 0:
        nl_decision = "PT_PANEL_READY_NL_SOURCE_FOUND"
        nl_note = f"{n_acceptable} acceptable open-data source(s) found — verification required"
    else:
        nl_decision = "NL_GEMEENTE_OPEN_DATA_BLOCKED"
        nl_note = (
            "No open-data table with gemeente × births × SBI × ≥6 years found. "
            "Paths: CBS Microdata (ABR) via Research Data Center or maintain NL at COROP level."
        )

    print(f"\nNL Decision: {nl_decision}")
    print(f"  {nl_note}")
    print(f"\nVerdicts:")
    verdict_counts = {}
    for c in candidates:
        v = c["verdict"]
        verdict_counts[v] = verdict_counts.get(v, 0) + 1
    for v, n in sorted(verdict_counts.items()):
        print(f"  {v}: {n}")

    # 5. Save JSON
    search_result = {
        "experiment": "DEC-062",
        "dec061_finding": "NL_GEMEENTE_BIRTHS_BLOCKED_VIA_CBS_OPEN_DATA",
        "nl_decision": nl_decision,
        "nl_note": nl_note,
        "n_tables_evaluated": len(candidates),
        "n_acceptable": n_acceptable,
        "acceptable_tables": acceptable,
        "verdict_counts": verdict_counts,
        "search_terms": SEARCH_TERMS,
        "known_tables_dec061": list(KNOWN_TABLES.keys()),
        "candidates": candidates,
        "formal_path_if_blocked": [
            "CBS Microdata (ABR) — gemeente × SBI × oprichtingen, restricted access via Research Data Center",
            "Research Data Center application via affiliated academic institution",
            "Alternatively: maintain NL at COROP (40 regions) as separate, lower-granularity layer",
        ],
        "classification_labels": CLASSIFICATION_LABELS,
    }

    with open(OUT_SEARCH_JSON, "w", encoding="utf-8") as f:
        json.dump(search_result, f, indent=2, ensure_ascii=False)
    print(f"\nSaved: {OUT_SEARCH_JSON}")

    return search_result


if __name__ == "__main__":
    main()
