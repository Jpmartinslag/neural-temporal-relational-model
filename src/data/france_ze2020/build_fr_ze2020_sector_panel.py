"""Build the canonical France ZE2020 A10 establishment-creation panel.

The official INSEE SIDE 2025 release is streamed directly from its ZIP. The
builder selects annual establishment creations at ZE2020 level, all legal
forms, and the nine published A10 sectors used by the project. The resulting
sector totals must reconcile exactly with the canonical clean-panel total for
every ZE-year; otherwise the build fails.

Input:
  data/raw/business_demography/side/DS_SIDE_CREA_ETAB_COM_2025_CSV.zip
  data/processed/france_ze2020/fr_ze2020_clean_panel.csv

Outputs:
  data/processed/france_ze2020/fr_ze2020_sector_panel.csv
  data/processed/france_ze2020/fr_ze2020_sector_panel_source_summary.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
SIDE_ZIP_PATH = (
    ROOT / "data/raw/business_demography/side/DS_SIDE_CREA_ETAB_COM_2025_CSV.zip"
)
SIDE_DATA_MEMBER = "DS_SIDE_CREA_ETAB_COM_2025_data.csv"
SIDE_ZIP_SHA256 = "1c42a050d971932eaf9ad2d25292c9ab586d28d7ee171826586cfb53ace2ba14"
CLEAN_PANEL_PATH = ROOT / "data/processed/france_ze2020/fr_ze2020_clean_panel.csv"
OUT_DIR = ROOT / "data/processed/france_ze2020"
OUT_PATH = OUT_DIR / "fr_ze2020_sector_panel.csv"
SOURCE_SUMMARY_PATH = OUT_DIR / "fr_ze2020_sector_panel_source_summary.json"

SECTOR_LABELS = {
    "BE": "Industry and energy",
    "FZ": "Construction",
    "GI": "Trade, transport and hospitality",
    "JZ": "Information and communication",
    "KZ": "Financial and insurance activities",
    "LZ": "Real estate activities",
    "MN": "Professional and administrative services",
    "OQ": "Public administration, education and health",
    "RU": "Arts and other services",
}
SECTOR_CODES = list(SECTOR_LABELS)
RECONCILIATION_TOLERANCE = 1e-6
SOURCE_FILTER = {
    "GEO_OBJECT": "ZE2020",
    "LEGAL_FORM": "_T",
    "SIDE_MEASURE": "UNIT_LOC_BURE",
    "OBS_STATUS": "A",
    "FREQ": "A",
}


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_clean_panel(path: Path = CLEAN_PANEL_PATH) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"ze2020": str})
    df["ze2020"] = df["ze2020"].str.zfill(4)
    df["year"] = df["year"].astype(int)
    return df[["ze2020", "ze2020_label", "year", "establishment_creations"]]


def load_a10_source(
    path: Path = SIDE_ZIP_PATH,
    *,
    allowed_zones: set[str] | None = None,
    verify_checksum: bool = True,
) -> pd.DataFrame:
    """Stream and pivot official SIDE A10 rows for the canonical ZE scope."""
    if verify_checksum:
        observed_hash = file_sha256(path)
        if observed_hash != SIDE_ZIP_SHA256:
            raise ValueError(
                f"SIDE ZIP checksum mismatch: {observed_hash} != {SIDE_ZIP_SHA256}"
            )
    if allowed_zones is None:
        allowed_zones = set(load_clean_panel()["ze2020"])

    usecols = [
        "ACTIVITY",
        "GEO_OBJECT",
        "GEO",
        "LEGAL_FORM",
        "SIDE_MEASURE",
        "OBS_STATUS",
        "FREQ",
        "TIME_PERIOD",
        "OBS_VALUE",
    ]
    parts: list[pd.DataFrame] = []
    with zipfile.ZipFile(path) as archive:
        if SIDE_DATA_MEMBER not in archive.namelist():
            raise ValueError(f"SIDE member missing: {SIDE_DATA_MEMBER}")
        with archive.open(SIDE_DATA_MEMBER) as raw:
            for chunk in pd.read_csv(
                raw,
                sep=";",
                usecols=usecols,
                dtype={
                    "ACTIVITY": str,
                    "GEO_OBJECT": str,
                    "GEO": str,
                    "LEGAL_FORM": str,
                    "SIDE_MEASURE": str,
                    "OBS_STATUS": str,
                    "FREQ": str,
                },
                chunksize=500_000,
                low_memory=False,
            ):
                selected = chunk[
                    chunk["GEO_OBJECT"].eq(SOURCE_FILTER["GEO_OBJECT"])
                    & chunk["LEGAL_FORM"].eq(SOURCE_FILTER["LEGAL_FORM"])
                    & chunk["SIDE_MEASURE"].eq(SOURCE_FILTER["SIDE_MEASURE"])
                    & chunk["OBS_STATUS"].eq(SOURCE_FILTER["OBS_STATUS"])
                    & chunk["FREQ"].eq(SOURCE_FILTER["FREQ"])
                    & chunk["ACTIVITY"].isin(SECTOR_CODES)
                ][["GEO", "TIME_PERIOD", "ACTIVITY", "OBS_VALUE"]].copy()
                if not selected.empty:
                    parts.append(selected)
    if not parts:
        raise ValueError("Official SIDE source produced no eligible A10 rows")

    long = pd.concat(parts, ignore_index=True)
    long["ze2020"] = long["GEO"].astype(str).str.zfill(4)
    long["year"] = pd.to_numeric(long["TIME_PERIOD"], errors="raise").astype(int)
    long["value"] = pd.to_numeric(long["OBS_VALUE"], errors="coerce")
    long = long[long["ze2020"].isin(allowed_zones)].copy()
    if long["value"].isna().any():
        raise ValueError("Eligible SIDE A10 rows contain missing/non-numeric values")
    if (long["value"] < 0).any():
        raise ValueError("Eligible SIDE A10 rows contain negative values")
    key = ["ze2020", "year", "ACTIVITY"]
    if long.duplicated(key).any():
        raise ValueError("Official SIDE source has duplicate ZE-year-sector rows")

    pivot = long.pivot(index=["ze2020", "year"], columns="ACTIVITY", values="value")
    missing_sectors = set(SECTOR_CODES) - set(pivot.columns)
    if missing_sectors:
        raise ValueError(f"SIDE source missing A10 sectors: {sorted(missing_sectors)}")
    missing_sector_cells = int(pivot[SECTOR_CODES].isna().sum().sum())
    # SIDE is sparse for zero counts. A missing sector cell is completed as
    # zero only before the independent nine-sector/official-total identity is
    # checked in build_sector_panel; any incorrect completion therefore fails.
    pivot[SECTOR_CODES] = pivot[SECTOR_CODES].fillna(0.0)
    pivot = pivot.reset_index()
    pivot["a10_total"] = pivot[SECTOR_CODES].sum(axis=1)
    result = pivot[["ze2020", "year", *SECTOR_CODES, "a10_total"]].copy()
    result = result.sort_values(["ze2020", "year"]).reset_index(drop=True)
    result.attrs["source_missing_sector_cells_completed_as_zero"] = (
        missing_sector_cells
    )
    return result


def build_sector_panel(
    a10: pd.DataFrame | None = None,
    clean: pd.DataFrame | None = None,
) -> pd.DataFrame:
    if clean is None:
        clean = load_clean_panel()
    if a10 is None:
        a10 = load_a10_source(allowed_zones=set(clean["ze2020"]))

    merged = a10.merge(clean, on=["ze2020", "year"], how="inner", validate="one_to_one")
    if len(merged) != len(a10) or len(merged) != len(clean):
        raise ValueError(
            "SIDE A10 and clean panel do not have identical canonical ZE-year coverage"
        )
    reconciliation_diff = (merged["a10_total"] - merged["establishment_creations"]).abs()
    if (reconciliation_diff > RECONCILIATION_TOLERANCE).any():
        raise ValueError(
            "SIDE A10 total does not reconcile with canonical establishment_creations "
            f"(max abs diff={reconciliation_diff.max()})"
        )

    long_rows = []
    for sector in SECTOR_CODES:
        sub = merged[
            ["ze2020", "ze2020_label", "year", "establishment_creations", sector]
        ].copy()
        sub = sub.rename(
            columns={
                "establishment_creations": "total_establishment_creations",
                sector: "sector_establishment_creations",
            }
        )
        sub["sector_code"] = sector
        sub["sector_label"] = SECTOR_LABELS[sector]
        long_rows.append(sub)

    panel = pd.concat(long_rows, ignore_index=True)
    panel["sector_establishment_creations"] = panel[
        "sector_establishment_creations"
    ].astype(float)
    panel["mask_sector_available"] = panel[
        "sector_establishment_creations"
    ].notna().astype(int)
    panel["sector_share"] = (
        panel["sector_establishment_creations"]
        / panel["total_establishment_creations"]
    )
    panel["sector_rank_in_ze_year"] = (
        panel.groupby(["ze2020", "year"])["sector_share"]
        .rank(ascending=False, method="min")
        .astype(int)
    )
    columns = [
        "ze2020",
        "ze2020_label",
        "year",
        "sector_code",
        "sector_label",
        "sector_establishment_creations",
        "total_establishment_creations",
        "sector_share",
        "sector_rank_in_ze_year",
        "mask_sector_available",
    ]
    return panel[columns].sort_values(["ze2020", "year", "sector_code"]).reset_index(drop=True)


def source_summary(
    panel: pd.DataFrame,
    source_path: Path,
    *,
    source_missing_sector_cells_completed_as_zero: int,
) -> dict[str, object]:
    return {
        "source_path": str(source_path.relative_to(ROOT)),
        "source_member": SIDE_DATA_MEMBER,
        "source_sha256": file_sha256(source_path),
        "source_filter": SOURCE_FILTER,
        "sector_codes": SECTOR_CODES,
        "zones": int(panel["ze2020"].nunique()),
        "years": sorted(int(year) for year in panel["year"].unique()),
        "rows": int(len(panel)),
        "source_missing_sector_cells_completed_as_zero": int(
            source_missing_sector_cells_completed_as_zero
        ),
        "zero_completion_validation": (
            "accepted_only_after_exact_nine_sector_to_official_total_reconciliation"
        ),
        "max_total_reconciliation_abs_diff": 0.0,
        "claim_status": "official_observed_sector_composition_not_causal_claim",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=SIDE_ZIP_PATH)
    parser.add_argument("--output", type=Path, default=OUT_PATH)
    parser.add_argument("--summary-output", type=Path, default=SOURCE_SUMMARY_PATH)
    args = parser.parse_args()

    clean = load_clean_panel()
    a10 = load_a10_source(args.source, allowed_zones=set(clean["ze2020"]))
    panel = build_sector_panel(a10, clean)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    panel.to_csv(args.output, index=False)
    args.summary_output.parent.mkdir(parents=True, exist_ok=True)
    args.summary_output.write_text(
        json.dumps(
            source_summary(
                panel,
                args.source,
                source_missing_sector_cells_completed_as_zero=a10.attrs.get(
                    "source_missing_sector_cells_completed_as_zero", 0
                ),
            ),
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    print(f"Saved {len(panel)} rows to {args.output}")


if __name__ == "__main__":
    main()
