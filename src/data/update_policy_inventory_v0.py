from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
INVENTORY_PATH = ROOT / "metadata" / "dataset_inventory.csv"
POLICY_ROOT = ROOT / "data" / "raw" / "policy"


FAMILY_BY_DIR = {
    "zrr": "policy_zrr",
    "frr": "policy_frr",
    "qpv": "policy_qpv",
    "zan": "policy_zan",
    "ocs_ge": "policy_zan",
    "pnb_action7": "policy_zan",
    "legal": "policy_legal",
}


def main() -> None:
    with INVENTORY_PATH.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    known_paths = {row["relative_path"] for row in rows}

    for path in sorted(POLICY_ROOT.rglob("*")):
        if not path.is_file():
            continue
        rel = str(path.relative_to(ROOT))
        if rel in known_paths:
            continue
        family_dir = path.parent.name
        rows.append(
            {
                "relative_path": rel,
                "file_name": path.name,
                "size_bytes": str(path.stat().st_size),
                "storage_group": "policy_raw",
                "dataset_family": FAMILY_BY_DIR.get(family_dir, "policy_other"),
                "api_or_source_url": "",
                "status": "available_downloaded_pending_review",
            }
        )

    for row in rows:
        rel = row["relative_path"]
        if rel.startswith("data/raw/policy/zan/ocs_ge/") or rel.startswith("data/raw/policy/zan/pnb_action7/"):
            row["dataset_family"] = "policy_zan"

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
