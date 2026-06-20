"""Preflight gate for adding ARDECO regional features to the France experiment.

This module does not download data and does not train a model.  It verifies
whether the current France panel and a local ARDECO extract can be joined
without silently mixing ZE2020 and NUTS3 geographies.

The preferred integration path is a France NUTS3 rebuild from commune-level
SIDE inputs.  A synthetic NUTS3 -> ZE2020 allocation is explicitly rejected.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd


BASE = Path(__file__).resolve().parents[3]
DEFAULT_FR_PANEL = BASE / "data/processed/european_panel/france_panel.csv"
DEFAULT_ARDECO = (
    BASE / "data/raw/european_panel/ardeco/snetz/ardeco_snetz_combined.csv"
)
DEFAULT_COMMUNE_ZE = BASE / "data/interim/mappings/commune_to_ze2020_2026.csv"
DEFAULT_OUTPUT = (
    BASE / "data/processed/ardeco_extension/ardeco_fr_preflight.json"
)

MIN_HISTORY_YEARS = 8
MIN_SECTORS = 9


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _require_columns(frame: pd.DataFrame, columns: set[str], label: str) -> None:
    missing = sorted(columns.difference(frame.columns))
    if missing:
        raise ValueError(f"{label} missing columns: {missing}")


def audit_frames(
    france_panel: pd.DataFrame,
    ardeco: pd.DataFrame,
    commune_ze: pd.DataFrame,
) -> dict[str, Any]:
    """Return a fail-closed compatibility decision from already loaded frames."""
    _require_columns(
        france_panel,
        {"region_id", "region_level", "year", "meta_nuts3_code"},
        "France panel",
    )
    _require_columns(
        ardeco,
        {"TERRITORY_ID", "YEAR", "SECTOR", "VALUE", "COUNTRY_REQUEST"},
        "ARDECO",
    )
    _require_columns(commune_ze, {"CODGEO", "ZE2020"}, "commune-to-ZE mapping")

    fr = france_panel.copy()
    fr["region_id"] = fr["region_id"].astype(str)
    fr_ardeco = ardeco[ardeco["COUNTRY_REQUEST"].astype(str).eq("FR")].copy()
    fr_ardeco["TERRITORY_ID"] = fr_ardeco["TERRITORY_ID"].astype(str)

    panel_regions = set(fr["region_id"].dropna().unique())
    ardeco_regions = set(fr_ardeco["TERRITORY_ID"].dropna().unique())
    direct_overlap = panel_regions.intersection(ardeco_regions)

    ardeco_years = [
        int(year)
        for year in sorted(
            pd.to_numeric(fr_ardeco["YEAR"], errors="coerce")
            .dropna()
            .astype(int)
            .unique()
        )
    ]
    ardeco_sectors = [
        str(sector)
        for sector in sorted(fr_ardeco["SECTOR"].dropna().astype(str).unique())
    ]
    panel_nuts_codes = (
        fr["meta_nuts3_code"].replace("", pd.NA).dropna().astype(str).unique()
    )

    checks = {
        "c1_local_ardeco_fr_present": not fr_ardeco.empty,
        "c2_ardeco_history_at_least_8_years": len(ardeco_years) >= MIN_HISTORY_YEARS,
        "c3_ardeco_has_at_least_9_sectors": len(ardeco_sectors) >= MIN_SECTORS,
        "c4_france_panel_is_nuts3": set(fr["region_level"].dropna()) == {"NUTS3"},
        "c5_france_panel_has_nuts3_codes": len(panel_nuts_codes) > 0,
        "c6_direct_region_overlap_at_least_95pct": (
            len(direct_overlap) / max(len(panel_regions), 1) >= 0.95
        ),
        "c7_commune_to_ze_mapping_present": not commune_ze.empty,
    }

    # c7 is evidence that ZE2020 can be rebuilt from communes.  It is not a
    # NUTS3 crosswalk and therefore cannot authorize an ARDECO join.
    authorization_checks = [f"c{i}_" for i in range(1, 7)]
    authorized = all(
        value
        for key, value in checks.items()
        if any(key.startswith(prefix) for prefix in authorization_checks)
    )

    return {
        "decision": (
            "ARDECO_FR_EXTENSION_READY"
            if authorized
            else "ARDECO_FR_EXTENSION_BLOCKED_PRETRAIN"
        ),
        "checks": checks,
        "inventory": {
            "france_panel_rows": int(len(fr)),
            "france_panel_regions": int(len(panel_regions)),
            "france_panel_region_levels": sorted(
                fr["region_level"].dropna().astype(str).unique()
            ),
            "france_panel_nuts3_codes": int(len(panel_nuts_codes)),
            "ardeco_fr_rows": int(len(fr_ardeco)),
            "ardeco_fr_regions": int(len(ardeco_regions)),
            "ardeco_years": ardeco_years,
            "ardeco_sectors": ardeco_sectors,
            "direct_region_overlap": int(len(direct_overlap)),
            "commune_to_ze_rows": int(len(commune_ze)),
        },
        "methodological_decision": {
            "forbidden": [
                "Direct join of ARDECO NUTS3 values to ZE2020 region_id",
                "Unweighted or area-only allocation of NUTS3 totals to ZE2020",
                "Graph or neural retraining before the Ridge enrichment gate",
            ],
            "required_path": [
                "Download a causal historical ARDECO SNETZ extract",
                "Map communes to departments and official NUTS3-2021 codes",
                "Rebuild the French target and A10 sector panel at NUTS3 from commune-level SIDE",
                "Validate target totals and sector totals against the ZE2020 reference",
                "Compare canonical Ridge against Ridge plus ARDECO features",
                "Reopen graph-temporal training only if ARDECO improves Ridge under the frozen gate",
            ],
        },
    }


def run_audit(
    france_panel_path: Path = DEFAULT_FR_PANEL,
    ardeco_path: Path = DEFAULT_ARDECO,
    commune_ze_path: Path = DEFAULT_COMMUNE_ZE,
    output_path: Path = DEFAULT_OUTPUT,
) -> dict[str, Any]:
    for path in (france_panel_path, ardeco_path, commune_ze_path):
        if not path.exists():
            raise FileNotFoundError(path)

    result = audit_frames(
        pd.read_csv(france_panel_path, low_memory=False),
        pd.read_csv(ardeco_path, low_memory=False),
        pd.read_csv(commune_ze_path, low_memory=False, dtype=str),
    )
    result["sources"] = {
        "france_panel": str(france_panel_path),
        "france_panel_sha256": file_sha256(france_panel_path),
        "ardeco": str(ardeco_path),
        "ardeco_sha256": file_sha256(ardeco_path),
        "commune_to_ze": str(commune_ze_path),
        "commune_to_ze_sha256": file_sha256(commune_ze_path),
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--france-panel", type=Path, default=DEFAULT_FR_PANEL)
    parser.add_argument("--ardeco", type=Path, default=DEFAULT_ARDECO)
    parser.add_argument("--commune-ze", type=Path, default=DEFAULT_COMMUNE_ZE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    result = run_audit(
        france_panel_path=args.france_panel,
        ardeco_path=args.ardeco,
        commune_ze_path=args.commune_ze,
        output_path=args.output,
    )
    print(json.dumps(result, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
