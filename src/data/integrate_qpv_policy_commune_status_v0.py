from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
QPV2024_PATH = ROOT / "data" / "interim" / "policy" / "qpv_2024_communes_v0.csv"
QPV_CORRESP_PATH = ROOT / "data" / "interim" / "policy" / "qpv_correspondance_2024_2015_v0.csv"
POLICY_PATH = ROOT / "data" / "interim" / "policy" / "policy_commune_status_v0.csv"
REGISTRY_PATH = ROOT / "metadata" / "policy_layers_registry_v0.csv"
QUALITY_PATH = ROOT / "reports" / "policy_commune_status_quality_v0.json"


def main() -> None:
    with POLICY_PATH.open(encoding="utf-8", newline="") as f:
        policy_rows = list(csv.DictReader(f))

    known_keys = {(r["codgeo"], r["policy_type"], r["policy_year"], r["source_layer"], r["notes"]) for r in policy_rows}

    qpv_corr = {}
    with QPV_CORRESP_PATH.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            qpv_corr[row["qp2024"]] = row

    added = 0
    with QPV2024_PATH.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            corr = qpv_corr.get(row["code_qp"], {})
            status_2015 = corr.get("statut", "")
            notes = f"code_qp={row['code_qp']}; statut_2015={status_2015}"
            new_row = {
                "codgeo": row["insee_com"].zfill(5),
                "policy_type": "QPV",
                "policy_year": "2024",
                "policy_status": "classified",
                "policy_status_raw": row["lib_qp"],
                "source_layer": "qpv_2024_communes_v0",
                "policy_scope": "commune",
                "policy_reference_geo": "COG2024",
                "notes": notes,
            }
            key = (new_row["codgeo"], new_row["policy_type"], new_row["policy_year"], new_row["source_layer"], new_row["notes"])
            if key not in known_keys:
                policy_rows.append(new_row)
                known_keys.add(key)
                added += 1

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
    with POLICY_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(policy_rows)

    registry_rows = []
    with REGISTRY_PATH.open(encoding="utf-8", newline="") as f:
        registry_rows = list(csv.DictReader(f))

    seen_policy_types = {r["policy_type"] for r in registry_rows}
    if "QPV" not in seen_policy_types:
        registry_rows.append(
            {
                "policy_type": "QPV",
                "status_values": "classified; unknown",
                "intended_role": "policy_agent; territorial context; social priority layer",
                "current_source_status": "active",
            }
        )
    else:
        for row in registry_rows:
            if row["policy_type"] == "QPV":
                row["current_source_status"] = "active"
                row["status_values"] = "classified; unknown"

    with REGISTRY_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["policy_type", "status_values", "intended_role", "current_source_status"],
        )
        writer.writeheader()
        writer.writerows(registry_rows)

    with QUALITY_PATH.open(encoding="utf-8") as f:
        quality = json.load(f)

    quality["rows"] = len(policy_rows)
    quality["policy_types_present"] = sorted({row["policy_type"] for row in policy_rows})
    quality["years_present"] = sorted({row["policy_year"] for row in policy_rows}, key=int)
    notes = list(quality.get("notes", []))
    placeholder_note = "FRR/FRR+, QPV and ZAN remain placeholders in the registry until reliable sources are loaded."
    if placeholder_note in notes:
        notes.remove(placeholder_note)
    qpv_note = "QPV 2024 commune layer appended to canonical policy table."
    if qpv_note not in notes:
        notes.append(qpv_note)
    notes.append("FRR/FRR+ and ZAN remain pending in the registry until reliable sources are loaded.")
    quality["notes"] = list(dict.fromkeys(notes))

    with QUALITY_PATH.open("w", encoding="utf-8") as f:
        json.dump(quality, f, ensure_ascii=False, indent=2)

    print(
        json.dumps(
            {
                "policy_rows_total": len(policy_rows),
                "qpv_rows_added": added,
                "policy_types_present": quality["policy_types_present"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
