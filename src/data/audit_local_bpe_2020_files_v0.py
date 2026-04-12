#!/usr/bin/env python3
"""Audit local files for possible BPE 2020 data.

This is intentionally conservative: a file is only marked as usable BPE 2020
data if it contains observation-level identifiers such as DEPCOM/TYPEQU and a
confirmed 2020 year or BPE20 archive marker. Documentation and nomenclature
files are recorded separately because they prove the source structure but are
not usable observations.
"""

from __future__ import annotations

import csv
import json
import subprocess
import zipfile
from collections import Counter
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "reports"
METADATA = ROOT / "metadata"

SKIP_PARTS = {".git", ".venv", "__pycache__", "scan_output"}
TEXT_EXTENSIONS = {".csv", ".txt", ".tsv"}
TABLE_EXTENSIONS = {".csv", ".txt", ".tsv", ".xlsx", ".xls", ".parquet"}
PDF_EXTENSIONS = {".pdf"}
ZIP_EXTENSIONS = {".zip"}


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def should_skip(path: Path) -> bool:
    return any(part in SKIP_PARTS for part in path.parts)


def safe_size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return -1


def read_head(path: Path, nbytes: int = 65536) -> str:
    try:
        return path.read_bytes()[:nbytes].decode("utf-8", errors="ignore")
    except OSError:
        return ""


def sniff_csv(path: Path) -> dict[str, object]:
    info: dict[str, object] = {"columns": [], "years": [], "row_sampled": 0}
    try:
        sample = read_head(path)
        dialect = csv.Sniffer().sniff(sample, delimiters=";,|\t,")
        sep = dialect.delimiter
    except Exception:
        sep = ";"

    try:
        frame = pd.read_csv(path, sep=sep, nrows=5000, dtype=str, low_memory=False)
    except Exception:
        try:
            frame = pd.read_csv(path, sep=None, engine="python", nrows=5000, dtype=str)
        except Exception as exc:
            info["error"] = str(exc)
            return info

    columns = [str(c).lstrip("\ufeff") for c in frame.columns]
    info["columns"] = columns
    info["row_sampled"] = int(len(frame))

    year_values: set[str] = set()
    for col in columns:
        col_original = frame.columns[columns.index(col)]
        upper = col.upper()
        # Only true time columns are used here. Spatial zoning columns such as
        # AAV2020/UU2020 contain commune-area codes, not observation years.
        if upper in {"AN", "ANNEE", "ANNÉE", "ANNÉE ", "YEAR", "TIME_PERIOD"}:
            values = frame[col_original].dropna().astype(str).str[:4]
            year_values.update(v for v in values.unique().tolist() if v.isdigit())
    info["years"] = sorted(year_values)[:20]
    return info


def classify_table(path: Path) -> dict[str, object]:
    name = path.name.lower()
    text = read_head(path).lower()
    info: dict[str, object] = {
        "path": rel(path),
        "kind": "table",
        "size_bytes": safe_size(path),
        "classification": "not_bpe_candidate",
        "evidence": "",
    }

    if path.suffix.lower() in TEXT_EXTENSIONS:
        sniff = sniff_csv(path)
        info.update(sniff)
        columns = {str(c).lstrip("\ufeff").upper() for c in sniff.get("columns", [])}
        years = set(sniff.get("years", []))
        has_bpe_columns = {"DEPCOM", "TYPEQU"}.issubset(columns)
        has_counts = bool({"NB_EQUIP", "NB_2020", "PRES_2020"} & columns)

        if "bpe20_table_passage" in name:
            info["classification"] = "documentation_or_nomenclature_only"
            info["evidence"] = "TYPEQU/LIB_EQUIP mapping only; no DEPCOM observations."
        elif "bpe" in name or "equip" in name or has_bpe_columns:
            if has_bpe_columns and ("2020" in years or "bpe20" in name) and has_counts:
                info["classification"] = "usable_bpe_2020_data_candidate"
                info["evidence"] = "Has DEPCOM/TYPEQU/count columns and 2020 evidence."
            elif has_bpe_columns and years:
                info["classification"] = "bpe_data_wrong_year_or_not_2020"
                info["evidence"] = f"Has BPE-like columns but detected years={sorted(years)}."
            elif "2020" in name or "bpe20" in name or "nb_2020" in text or "pres_2020" in text:
                info["classification"] = "bpe_2020_related_not_observation_data"
                info["evidence"] = "Mentions BPE 2020 but lacks required observation columns."
            else:
                info["classification"] = "bpe_related_year_unclear"
                info["evidence"] = "BPE/equipment-related name or columns, but no confirmed 2020 observations."
    elif path.suffix.lower() == ".parquet":
        if "bpe24" in name:
            info["classification"] = "bpe_data_wrong_year_or_not_2020"
            info["evidence"] = "BPE24 parquet by filename."
        elif "bpe" in name or "equip" in name:
            info["classification"] = "bpe_related_year_unclear"
            info["evidence"] = "Parquet candidate by filename; not deeply read in this audit."
    elif path.suffix.lower() in {".xlsx", ".xls"}:
        text = ""
        if path.suffix.lower() == ".xls":
            try:
                result = subprocess.run(
                    ["xls2csv", str(path)],
                    cwd=ROOT,
                    check=False,
                    text=True,
                    capture_output=True,
                    timeout=60,
                )
                text = result.stdout.lower()
            except Exception:
                text = ""
        if "base permanente des équipements 2016" in text:
            info["classification"] = "bpe_derived_article_table_wrong_year"
            info["evidence"] = "Opaque XLS contains INSEE figure tables sourced from BPE 2016; not raw BPE 2020 observations."
        elif "base permanente des équipements 2012 et 2017" in text or "base permanente des équipements 2017" in text:
            info["classification"] = "bpe_derived_article_table_wrong_year"
            info["evidence"] = "Opaque XLS contains INSEE figure tables sourced from BPE 2012/2017; not raw BPE 2020 observations."
        elif "base permanente des équipements 2020" in text or "bpe 2020" in text:
            info["classification"] = "bpe_2020_related_spreadsheet_needs_manual_review"
            info["evidence"] = "Spreadsheet mentions BPE 2020; manual review required."
        elif "base permanente des équipements" in text or "typequ" in text:
            info["classification"] = "bpe_related_year_unclear"
            info["evidence"] = "Spreadsheet mentions BPE/TYPEQU, but no confirmed raw BPE 2020 observations."
        elif "bpe" in name or "equip" in name:
            info["classification"] = "bpe_related_year_unclear"
            info["evidence"] = "Spreadsheet candidate by filename; not required for known BPE20 ensemble CSV."

    return info


def classify_zip(path: Path) -> dict[str, object]:
    info: dict[str, object] = {
        "path": rel(path),
        "kind": "zip",
        "size_bytes": safe_size(path),
        "classification": "not_bpe_candidate",
        "evidence": "",
        "members": [],
    }
    name = path.name.lower()
    head = read_head(path, 256).lower()

    if not zipfile.is_zipfile(path):
        if "bpe20" in name and ("html" in head or "<!doctype" in head):
            info["classification"] = "invalid_download_html_error"
            info["evidence"] = "Filename is BPE20, but file is HTML, not a ZIP archive."
        return info

    try:
        with zipfile.ZipFile(path) as archive:
            members = archive.namelist()
    except Exception as exc:
        info["classification"] = "zip_unreadable"
        info["evidence"] = str(exc)
        return info

    info["members"] = members[:20]
    joined = " ".join(members).lower()
    if "bpe20" in name or "bpe20" in joined:
        if "ensemble" in joined and any(x in joined for x in [".csv", ".shp"]):
            info["classification"] = "usable_bpe_2020_archive_candidate"
            info["evidence"] = "Archive/member names indicate BPE20 ensemble data."
        else:
            info["classification"] = "bpe_2020_related_archive_unclear"
            info["evidence"] = "Archive references BPE20 but members do not clearly show ensemble observations."
    elif "bpe_evolution" in name or "bpe_evolution" in joined:
        info["classification"] = "official_harmonized_bpe_evolution_not_bpe2020_raw"
        info["evidence"] = "Official BPE evolution archive; useful comparable layer, but not raw BPE 2020."
    elif "bpe" in name or "bpe" in joined:
        if "bpe21" in name or "bpe21" in joined or "2021" in joined:
            info["classification"] = "bpe_data_wrong_year_or_not_2020"
            info["evidence"] = "BPE archive, but 2021 evidence."
        elif "bpe23" in name or "bpe23" in joined or "2023" in joined:
            info["classification"] = "bpe_data_wrong_year_or_not_2020"
            info["evidence"] = "BPE archive, but 2023 evidence."
        elif "bpe24" in name or "bpe24" in joined or "2024" in joined:
            info["classification"] = "bpe_data_wrong_year_or_not_2020"
            info["evidence"] = "BPE archive, but 2024 evidence."
        elif "bpe19" in name or "bpe19" in joined or "2019" in joined:
            info["classification"] = "bpe_data_wrong_year_or_not_2020"
            info["evidence"] = "BPE archive, but 2019 evidence."
        else:
            info["classification"] = "bpe_related_year_unclear"
            info["evidence"] = "BPE-related archive without confirmed 2020."
    return info


def classify_pdf(path: Path) -> dict[str, object]:
    info: dict[str, object] = {
        "path": rel(path),
        "kind": "pdf",
        "size_bytes": safe_size(path),
        "classification": "not_bpe_candidate",
        "evidence": "",
    }
    name = path.name.lower()
    if "bpe" not in name and "equip" not in name:
        return info

    try:
        result = subprocess.run(
            ["pdftotext", "-f", "1", "-l", "2", str(path), "-"],
            cwd=ROOT,
            check=False,
            text=True,
            capture_output=True,
            timeout=20,
        )
        text = result.stdout.lower()
    except Exception:
        text = ""

    if "base permanente des équipements 2020" in text or "bpe 2020" in text or "bpe20" in name:
        info["classification"] = "documentation_or_nomenclature_only"
        if "contenu du fichier" in text or "liste des variables" in text:
            info["evidence"] = "BPE 2020 content/variable documentation; not row-level observations."
        elif "liste des types" in text or "liste_equipements" in name:
            info["evidence"] = "BPE 2020 equipment list; not row-level observations."
        else:
            info["evidence"] = "BPE 2020 methodological/documentation PDF; not data."
    elif "bpe" in name or "équipement" in text or "equipement" in text:
        info["classification"] = "documentation_or_nomenclature_only"
        info["evidence"] = "BPE/equipment-related PDF documentation."
    return info


def collect_records() -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or should_skip(path):
            continue
        suffix = path.suffix.lower()
        name = path.name.lower()
        if suffix in ZIP_EXTENSIONS:
            record = classify_zip(path)
        elif suffix in PDF_EXTENSIONS:
            record = classify_pdf(path)
        elif suffix in TABLE_EXTENSIONS:
            if "bpe" not in name and "equip" not in name and suffix not in {".xls", ".xlsx"}:
                head = read_head(path, 8192).lower()
                if not any(token in head for token in ["typequ", "nb_2020", "pres_2020", "bpe 2020", "bpe20"]):
                    continue
            record = classify_table(path)
        else:
            continue

        if record["classification"] != "not_bpe_candidate":
            records.append(record)
    return records


def write_outputs(records: list[dict[str, object]]) -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    METADATA.mkdir(parents=True, exist_ok=True)

    csv_path = METADATA / "local_bpe_2020_file_audit_v0.csv"
    json_path = REPORTS / "local_bpe_2020_file_audit_v0.json"
    md_path = REPORTS / "LOCAL_BPE_2020_FILE_AUDIT_V0.md"

    fieldnames = [
        "path",
        "kind",
        "size_bytes",
        "classification",
        "evidence",
        "columns",
        "years",
        "members",
        "error",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for record in records:
            flat = dict(record)
            for key in ["columns", "years", "members"]:
                if isinstance(flat.get(key), list):
                    flat[key] = json.dumps(flat[key], ensure_ascii=False)
            writer.writerow(flat)

    summary = Counter(str(record["classification"]) for record in records)
    json_path.write_text(
        json.dumps({"summary": summary, "records": records}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    usable = [
        record
        for record in records
        if str(record["classification"]).startswith("usable_bpe_2020")
    ]
    lines = [
        "# Local BPE 2020 File Audit v0",
        "",
        "## Conclusion",
        "",
    ]
    if usable:
        lines.append("At least one local file is a usable BPE 2020 data candidate and must be manually validated before integration.")
    else:
        lines.append("No local usable BPE 2020 observation file was found. Local BPE 2020 materials are documentation, nomenclature, invalid downloads, or wrong-year datasets.")

    lines.extend(["", "## Summary", ""])
    for key, value in summary.most_common():
        lines.append(f"- `{key}`: {value}")

    lines.extend(["", "## Key Evidence", ""])
    key_records = [
        record
        for record in records
        if "bpe20" in str(record["path"]).lower()
        or "BPE20" in str(record["path"])
        or record["classification"] in {
            "usable_bpe_2020_data_candidate",
            "usable_bpe_2020_archive_candidate",
            "invalid_download_html_error",
        }
    ]
    for record in key_records:
        lines.append(
            f"- `{record['path']}`: `{record['classification']}` - {record.get('evidence', '')}"
        )

    lines.extend(["", "## Outputs", ""])
    lines.append(f"- CSV: `{rel(csv_path)}`")
    lines.append(f"- JSON: `{rel(json_path)}`")

    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    records = collect_records()
    write_outputs(records)
    summary = Counter(str(record["classification"]) for record in records)
    print("records", len(records))
    for key, value in summary.most_common():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
