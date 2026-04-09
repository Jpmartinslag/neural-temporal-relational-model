from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HIST_PATH = ROOT / "data" / "interim" / "policy" / "zrr_historique_communes_v0.csv"
QUALITY_PATH = ROOT / "reports" / "zrr_tables_quality_v0.json"


def main() -> None:
    with HIST_PATH.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    cleaned = []
    removed = 0
    for row in rows:
        codgeo = (row.get("codgeo") or "").strip()
        if len(codgeo) == 5 and codgeo.isdigit():
            cleaned.append(row)
        else:
            removed += 1

    with HIST_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["year", "codgeo", "libgeo", "zrr_status"])
        writer.writeheader()
        writer.writerows(cleaned)

    quality = {}
    if QUALITY_PATH.exists():
        with QUALITY_PATH.open(encoding="utf-8") as f:
            quality = json.load(f)
    quality["historical_rows"] = len(cleaned)
    notes = list(quality.get("notes", []))
    note = "Legend rows with non-communal labels were removed from zrr_historique_communes_v0.csv."
    if note not in notes:
        notes.append(note)
    quality["notes"] = notes
    with QUALITY_PATH.open("w", encoding="utf-8") as f:
        json.dump(quality, f, ensure_ascii=False, indent=2)

    print(
        json.dumps(
            {
                "historical_rows_cleaned": len(cleaned),
                "rows_removed": removed,
                "quality_path": str(QUALITY_PATH),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
