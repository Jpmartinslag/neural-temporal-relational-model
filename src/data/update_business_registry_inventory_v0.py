from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
INVENTORY_PATH = ROOT / "metadata" / "dataset_inventory.csv"
RAW_ROOT = ROOT / "data" / "raw" / "business_registry" / "sirene"


def infer_family(name: str) -> str:
    lower = name.lower()
    if "geolocalisation" in lower:
        return "business_registry_geoloc"
    if "unitelegale" in lower:
        return "business_registry_legal_unit"
    if "etablissementhistorique" in lower:
        return "business_registry_establishment_history"
    if "etablissement" in lower:
        return "business_registry_establishment"
    return "business_registry_other"


def main() -> None:
    with INVENTORY_PATH.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    known_paths = {row["relative_path"] for row in rows}
    for path in sorted(RAW_ROOT.rglob("*")):
        if not path.is_file():
            continue
        rel = str(path.relative_to(ROOT))
        if rel in known_paths:
            continue
        rows.append(
            {
                "relative_path": rel,
                "file_name": path.name,
                "size_bytes": str(path.stat().st_size),
                "storage_group": "business_registry_raw",
                "dataset_family": infer_family(path.name),
                "api_or_source_url": "",
                "status": "available_downloaded_pending_review",
            }
        )

    fieldnames = [
        "relative_path",
        "file_name",
        "size_bytes",
        "storage_group",
        "dataset_family",
        "api_or_source_url",
        "status",
    ]
    rows.sort(key=lambda r: r["relative_path"])
    with INVENTORY_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"inventory_rows={len(rows)}")


if __name__ == "__main__":
    main()
