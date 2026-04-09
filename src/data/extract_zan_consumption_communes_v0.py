from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RAW_PATH = ROOT / "data" / "raw" / "policy" / "zan" / "conso2009-2024-resultats-com.csv"
OUT_PATH = ROOT / "data" / "interim" / "policy" / "zan_consumption_communes_v0.csv"
QUALITY_PATH = ROOT / "reports" / "zan_consumption_quality_v0.json"


def main() -> None:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    with RAW_PATH.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        fieldnames = [field.strip('"') for field in (reader.fieldnames or [])]
        for raw_row in reader:
            row = {}
            for raw_key, value in raw_row.items():
                key = raw_key.strip('"')
                row[key] = value
            row["idcom"] = row["idcom"].zfill(5)
            rows.append(row)

    with OUT_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    quality = {
        "rows": len(rows),
        "columns": len(fieldnames),
        "fieldnames_head": fieldnames[:20],
        "communes_distinct": len({row["idcom"] for row in rows}),
        "years_covered_by_name": "2009-2024",
        "notes": [
            "Raw semicolon-delimited ZAN commune table normalized into canonical CSV.",
            "This layer is kept outside policy_commune_status_v0 because it carries quantitative land-use indicators rather than a binary policy status.",
        ],
    }
    with QUALITY_PATH.open("w", encoding="utf-8") as f:
        json.dump(quality, f, ensure_ascii=False, indent=2)

    print(
        json.dumps(
            {
                "out_path": str(OUT_PATH),
                "quality_path": str(QUALITY_PATH),
                "rows": len(rows),
                "columns": len(fieldnames),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
