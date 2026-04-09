from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ZRR_HIST_PATH = ROOT / "data" / "interim" / "policy" / "zrr_historique_communes_v0.csv"
ZRR_COG2021_PATH = ROOT / "data" / "interim" / "policy" / "zrr_cog2021_communes_v0.csv"
OUT_PATH = ROOT / "data" / "interim" / "policy" / "policy_commune_status_v0.csv"
QUALITY_PATH = ROOT / "reports" / "policy_commune_status_quality_v0.json"
REGISTRY_PATH = ROOT / "metadata" / "policy_layers_registry_v0.csv"


def normalize_zrr_status(raw: str) -> str:
    value = (raw or "").strip()
    if value.startswith("C - "):
        return "classified"
    if value.startswith("P - "):
        return "partially_classified"
    if value.startswith("NC - "):
        return "not_classified"
    return "unknown"


def main() -> None:
    rows = []

    with ZRR_HIST_PATH.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            rows.append(
                {
                    "codgeo": row["codgeo"].zfill(5),
                    "policy_type": "ZRR",
                    "policy_year": row["year"],
                    "policy_status": normalize_zrr_status(row["zrr_status"]),
                    "policy_status_raw": row["zrr_status"],
                    "source_layer": "zrr_historique_communes_v0",
                    "policy_scope": "commune",
                    "policy_reference_geo": "historical workbook geography",
                    "notes": "",
                }
            )

    with ZRR_COG2021_PATH.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            rows.append(
                {
                    "codgeo": row["codgeo"].zfill(5),
                    "policy_type": "ZRR",
                    "policy_year": "2021",
                    "policy_status": normalize_zrr_status(row["zrr_simp"]),
                    "policy_status_raw": row["zrr_simp"],
                    "source_layer": "zrr_cog2021_communes_v0",
                    "policy_scope": "commune",
                    "policy_reference_geo": "COG2021",
                    "notes": row["zonage_zrr"],
                }
            )

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "codgeo",
        "policy_type",
        "policy_year",
        "policy_status",
        "policy_status_raw",
        "source_layer",
        "policy_scope",
        "policy_reference_geo",
        "notes",
    ]
    with OUT_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    with REGISTRY_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["policy_type", "status_values", "intended_role", "current_source_status"],
        )
        writer.writeheader()
        writer.writerow(
            {
                "policy_type": "ZRR",
                "status_values": "classified; partially_classified; not_classified; unknown",
                "intended_role": "policy_agent; territorial context; future aggregation to ZE2020",
                "current_source_status": "active",
            }
        )
        writer.writerow(
            {
                "policy_type": "FRR/FRR+",
                "status_values": "pending",
                "intended_role": "policy_agent; territorial context; future aggregation to ZE2020",
                "current_source_status": "partial_source_only",
            }
        )
        writer.writerow(
            {
                "policy_type": "QPV",
                "status_values": "pending",
                "intended_role": "policy_agent; territorial context; social priority layer",
                "current_source_status": "not_loaded_yet",
            }
        )
        writer.writerow(
            {
                "policy_type": "ZAN",
                "status_values": "pending",
                "intended_role": "policy_agent; land-use constraint layer",
                "current_source_status": "not_loaded_yet",
            }
        )

    quality = {
        "rows": len(rows),
        "policy_types_present": sorted({row["policy_type"] for row in rows}),
        "years_present": sorted({row["policy_year"] for row in rows}),
        "notes": [
            "Canonical policy layer initialized with ZRR.",
            "FRR/FRR+, QPV and ZAN remain placeholders in the registry until reliable sources are loaded.",
        ],
    }
    with QUALITY_PATH.open("w", encoding="utf-8") as f:
        json.dump(quality, f, ensure_ascii=False, indent=2)

    print(
        json.dumps(
            {
                "out_path": str(OUT_PATH),
                "registry_path": str(REGISTRY_PATH),
                "quality_path": str(QUALITY_PATH),
                "quality": quality,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
