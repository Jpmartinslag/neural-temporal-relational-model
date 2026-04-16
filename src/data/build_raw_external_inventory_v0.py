import csv
import json
import os
import zipfile
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
RAW_ROOT = ROOT / "data" / "raw" / "external"
OUTPUT_CSV = ROOT / "metadata" / "raw_external_inventory_v0.csv"
OUTPUT_REPORT = ROOT / "reports" / "RAW_EXTERNAL_INVENTORY_V0.md"


PROCESSED_OUTPUTS = {
    "sitadel_annual_communal": ROOT / "data" / "interim" / "tables" / "sitadel_surface_ze2020_v0.csv",
    "energy_iris_2018_2024": ROOT / "data" / "interim" / "tables" / "energy_consumption_ze2020_v0.csv",
    "rei_cfe_csv_2023_2024": ROOT / "data" / "interim" / "tables" / "rei_cfe_ze2020_v0.csv",
}


def mb(size):
    return round(size / (1024 * 1024), 2)


def family(path):
    rel = path.relative_to(RAW_ROOT)
    return rel.parts[0] if rel.parts else "unknown"


def infer_content(path):
    name = path.name.lower()
    fam = family(path)
    if fam == "sitadel" and "epci" in name:
        return "sitadel_epci"
    if fam == "sitadel" and "regionales" in name:
        return "sitadel_regional"
    if fam == "sitadel" and "departementales" in name:
        return "sitadel_departmental"
    if "mensuelles-communales-locaux" in name:
        return "sitadel_monthly_communal_nonres"
    if "annuelles-communales-locaux" in name:
        return "sitadel_annual_communal_nonres"
    if "autorisations" in name or "permis" in name:
        return "sitadel_event_level_permissions"
    if name.startswith("rei-"):
        return "rei_fiscality"
    if fam == "energy" and "iris" in name:
        return "energy_iris"
    if "iris" in name and "electricit" in name:
        return "energy_iris"
    if "periode-2008-2017" in name or "2008-2017" in name:
        return "energy_historical_2008_2017"
    if "epci" in name:
        return "energy_epci"
    if "region" in name:
        return "energy_region"
    if "petro" in name:
        return "energy_petroleum"
    if "chaleur" in name:
        return "energy_heat_cold"
    return "external_other"


def inspect_zip(path):
    if path.suffix.lower() != ".zip":
        return 0, "", ""
    try:
        with zipfile.ZipFile(path) as z:
            infos = z.infolist()
            names = [info.filename for info in infos]
            total_uncompressed = sum(info.file_size for info in infos)
            suffixes = sorted({Path(name).suffix.lower().lstrip(".") for name in names if Path(name).suffix})
            return len(infos), ",".join(suffixes), str(total_uncompressed)
    except zipfile.BadZipFile:
        return 0, "", ""


def status_and_priority(path, content, size_bytes):
    status = "not_processed"
    priority = "low"
    reason = "not selected yet"

    if content == "sitadel_annual_communal_nonres":
        status = "processed"
        priority = "done"
        reason = "used to build lagged SITADEL ZE2020 features"
    elif content == "energy_iris":
        status = "processed_subset"
        priority = "done"
        reason = "electricity/gas non-residential processed; heat/cold skipped"
    elif content == "rei_fiscality" and path.name in {
        "REI-2023-fichier-notice-trace.zip",
        "REI-2024-fichier-notice-trace.zip",
    }:
        status = "processed_subset"
        priority = "medium"
        reason = "CSV years processed; historical XLSX years pending"
    elif content == "sitadel_monthly_communal_nonres":
        status = "too_heavy_pending"
        priority = "high"
        reason = "3GB monthly communal data may provide stronger temporal signals"
    elif content == "sitadel_event_level_permissions":
        status = "too_heavy_pending" if size_bytes > 100_000_000 else "not_processed"
        priority = "medium"
        reason = "event-level permits may help but require aggregation design"
    elif content == "rei_fiscality":
        status = "not_processed_xlsx_or_legacy"
        priority = "high" if "2018" in path.name or "2019" in path.name or "2020" in path.name or "2021" in path.name or "2022" in path.name else "medium"
        reason = "requires controlled conversion/extraction before REI can be evaluated over time"
    elif content == "energy_historical_2008_2017":
        status = "not_processed"
        priority = "high"
        reason = "can extend energy temporal depth before 2018"
    elif content in {"energy_epci", "energy_region", "energy_petroleum", "energy_heat_cold", "sitadel_epci", "sitadel_regional", "sitadel_departmental"}:
        status = "not_processed"
        priority = "low"
        reason = "coarser geography or less direct match to ZE2020 target"

    return status, priority, reason


def build_inventory():
    rows = []
    for path in sorted(RAW_ROOT.rglob("*")):
        if not path.is_file():
            continue
        size = path.stat().st_size
        content = infer_content(path)
        zip_members, zip_suffixes, uncompressed = inspect_zip(path)
        status, priority, reason = status_and_priority(path, content, size)
        rows.append(
            {
                "family": family(path),
                "content_type": content,
                "path": str(path.relative_to(ROOT)),
                "size_bytes": size,
                "size_mb": mb(size),
                "extension": path.suffix.lower().lstrip("."),
                "zip_members": zip_members,
                "zip_member_suffixes": zip_suffixes,
                "zip_uncompressed_bytes": uncompressed,
                "processing_status": status,
                "priority": priority,
                "decision_reason": reason,
            }
        )

    frame = pd.DataFrame(rows).sort_values(["priority", "size_bytes"], ascending=[True, False])
    os.makedirs(OUTPUT_CSV.parent, exist_ok=True)
    frame.to_csv(OUTPUT_CSV, index=False)

    summary = (
        frame.groupby(["family", "processing_status"])
        .agg(files=("path", "count"), size_mb=("size_mb", "sum"))
        .reset_index()
        .sort_values(["family", "processing_status"])
    )

    high = frame[frame["priority"].isin(["high", "medium"])].sort_values(["priority", "size_bytes"], ascending=[True, False])

    lines = [
        "# Raw External Inventory v0",
        "",
        "Data: 2026-04-16",
        "",
        "## Purpose",
        "",
        "Track which external raw files have actually been processed, partially processed, or left pending.",
        "This prevents overstating conclusions from only a subset of downloaded data.",
        "",
        "## Summary",
        "",
        "| Family | Status | Files | Size MB |",
        "| :--- | :--- | ---: | ---: |",
    ]
    for _, row in summary.iterrows():
        lines.append(f"| `{row['family']}` | `{row['processing_status']}` | {int(row['files'])} | {row['size_mb']:.2f} |")

    lines.extend(
        [
            "",
            "## Priority Queue",
            "",
            "| Priority | Status | Size MB | File | Reason |",
            "| :--- | :--- | ---: | :--- | :--- |",
        ]
    )
    for _, row in high.head(30).iterrows():
        lines.append(
            f"| `{row['priority']}` | `{row['processing_status']}` | {row['size_mb']:.2f} | `{row['path']}` | {row['decision_reason']} |"
        )

    lines.extend(
        [
            "",
            "## Current Interpretation",
            "",
            "- Current negative results for SITADEL, REI, and Energy apply only to processed subsets and raw lagged-level forms.",
            "- The largest unprocessed item is the SITADEL monthly communal file, which may contain stronger short-term dynamics.",
            "- REI is mostly unprocessed historically because older files require controlled XLSX extraction/conversion.",
            "- Energy pre-2018 is unprocessed and may matter for temporal depth.",
        ]
    )

    os.makedirs(OUTPUT_REPORT.parent, exist_ok=True)
    OUTPUT_REPORT.write_text("\n".join(lines) + "\n")

    print(f"Saved inventory to {OUTPUT_CSV}")
    print(f"Saved report to {OUTPUT_REPORT}")
    print(json.dumps({"files": len(frame), "total_size_mb": round(frame["size_mb"].sum(), 2)}, indent=2))


if __name__ == "__main__":
    build_inventory()
