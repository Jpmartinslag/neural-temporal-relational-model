import hashlib
import json
import os
import tempfile
import zipfile
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw" / "external" / "rei"
OUTPUT_DIR = ROOT / "data" / "interim" / "tables" / "rei_converted_csv_v0"
QUALITY_PATH = ROOT / "reports" / "archive" / "diagnostics" / "rei_xlsx_conversion_quality_v0.json"

DEFAULT_YEARS = [2018, 2019, 2020, 2021, 2022]


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def find_rei_workbook(zip_path):
    with zipfile.ZipFile(zip_path) as z:
        candidates = []
        for name in z.namelist():
            lower = name.lower()
            if not lower.endswith(".xlsx"):
                continue
            basename = Path(name).name.lower()
            if "trace" in basename:
                continue
            if "rei" not in basename:
                continue
            candidates.append(name)

        if len(candidates) != 1:
            raise RuntimeError(f"Expected exactly one REI workbook in {zip_path.name}, found {candidates}.")
        return candidates[0]


def convert_year(year):
    zip_path = RAW_DIR / f"REI-{year}-fichier-notice-trace.zip"
    if not zip_path.exists():
        raise FileNotFoundError(f"Missing expected REI zip: {zip_path}")

    member = find_rei_workbook(zip_path)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"rei_{year}.csv"

    with tempfile.TemporaryDirectory(prefix=f"rei_{year}_") as tmp:
        tmp_path = Path(tmp)
        with zipfile.ZipFile(zip_path) as z:
            z.extract(member, tmp_path)

        workbook_path = tmp_path / member
        if not workbook_path.exists():
            # Handles nested zip members such as REI-2021-fichier-notice-trace/REI_2021.xlsx.
            matches = list(tmp_path.rglob(Path(member).name))
            if not matches:
                raise FileNotFoundError(f"Extracted workbook not found for {member}")
            workbook_path = matches[0]

        try:
            frame = pd.read_excel(workbook_path, sheet_name=0, dtype=str, engine="calamine")
        except ImportError as exc:
            raise RuntimeError(
                "python-calamine is required for fast REI XLSX conversion. "
                "Install it with: pip install python-calamine"
            ) from exc

    frame.to_csv(output_path, sep=";", index=False)

    return {
        "year": int(year),
        "source_zip": str(zip_path.relative_to(ROOT)),
        "source_member": member,
        "output_csv": str(output_path.relative_to(ROOT)),
        "rows": int(len(frame)),
        "columns": list(frame.columns),
        "output_size_bytes": int(output_path.stat().st_size),
        "output_sha256": sha256_file(output_path),
    }


def convert_rei_xlsx(years=None):
    years = years or DEFAULT_YEARS
    converted = []
    errors = []

    for year in years:
        try:
            result = convert_year(year)
            converted.append(result)
            print(f"Converted REI {year}: {result['rows']} rows -> {result['output_csv']}")
        except Exception as exc:
            errors.append({"year": int(year), "error": str(exc)})
            print(f"ERROR converting REI {year}: {exc}")

    quality = {
        "years_requested": [int(y) for y in years],
        "converted": converted,
        "errors": errors,
        "methodological_status": "intermediate conversion only; converted CSVs are not canonical until aggregated and causally evaluated",
    }
    QUALITY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(QUALITY_PATH, "w") as f:
        json.dump(quality, f, indent=2)

    if errors:
        raise RuntimeError(f"REI conversion completed with {len(errors)} error(s). See {QUALITY_PATH}")

    print(f"Saved conversion quality report to {QUALITY_PATH}")


if __name__ == "__main__":
    convert_rei_xlsx()
