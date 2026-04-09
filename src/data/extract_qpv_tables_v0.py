from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
QPV2024_PATH = ROOT / "data" / "raw" / "policy" / "qpv" / "listeqp2024-cog2024.csv"
QPV_CORRESP_PATH = ROOT / "data" / "raw" / "policy" / "qpv" / "liste-correspondance-qp2024-qp2015.csv"
OUT_DIR = ROOT / "data" / "interim" / "policy"
QPV2024_OUT = OUT_DIR / "qpv_2024_communes_v0.csv"
QPV_CORRESP_OUT = OUT_DIR / "qpv_correspondance_2024_2015_v0.csv"
QUALITY_OUT = ROOT / "reports" / "qpv_tables_quality_v0.json"

def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    qpv2024_rows = []
    with QPV2024_PATH.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            if not row.get("code_qp"):
                continue
            insee_com_raw = (row.get("insee_com") or "").strip().strip('"')
            if len(insee_com_raw) != 5 or not insee_com_raw.isdigit():
                # Multi-commune QPV rows are kept out of the commune table until a dedicated explode rule is defined.
                continue
            insee_dep_raw = (row.get("insee_dep") or "").strip().strip('"')
            insee_reg_raw = (row.get("insee_reg") or "").strip().strip('"')
            siren_epci_raw = (row.get("siren_epci") or "").strip().strip('"')
            qpv2024_rows.append(
                {
                    "code_qp": (row.get("code_qp") or "").strip().strip('"'),
                    "lib_qp": (row.get("lib_qp") or "").strip().strip('"'),
                    "insee_reg": insee_reg_raw.zfill(2) if insee_reg_raw else "",
                    "lib_reg": (row.get("lib_reg") or "").strip().strip('"'),
                    "insee_dep": insee_dep_raw.zfill(2) if insee_dep_raw else "",
                    "lib_dep": (row.get("lib_dep") or "").strip().strip('"'),
                    "insee_com": insee_com_raw.zfill(5),
                    "lib_com": (row.get("lib_com") or "").strip().strip('"'),
                    "siren_epci": siren_epci_raw,
                    "lib_epci": (row.get("lib_epci") or "").strip().strip('"'),
                }
            )

    with QPV2024_OUT.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "code_qp",
                "lib_qp",
                "insee_reg",
                "lib_reg",
                "insee_dep",
                "lib_dep",
                "insee_com",
                "lib_com",
                "siren_epci",
                "lib_epci",
            ],
        )
        writer.writeheader()
        writer.writerows(qpv2024_rows)

    corr_rows = []
    with QPV_CORRESP_PATH.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        if reader.fieldnames:
            reader.fieldnames = [field.strip() for field in reader.fieldnames]
        for row in reader:
            if not row.get("QP2024"):
                continue
            corr_rows.append(
                {
                    "qp2024": (row.get("QP2024") or "").strip().strip('"'),
                    "label_qp2024": (row.get("Label_QP2024") or "").strip().strip('"'),
                    "statut": (row.get("Statut") or "").strip().strip('"'),
                    "qp2015_1": (row.get("QP2015_1") or "").strip().strip('"'),
                    "label_qp2015_1": (row.get("Label_QP2015_1") or "").strip().strip('"'),
                    "qp2015_2": (row.get("QP2015_2") or "").strip().strip('"'),
                    "label_qp2015_2": (row.get("Label_QP2015_2") or "").strip().strip('"'),
                    "qp2015_3": (row.get("QP2015_3") or "").strip().strip('"'),
                    "label_qp2015_3": (row.get("Label_QP2015_3") or "").strip().strip('"'),
                }
            )

    with QPV_CORRESP_OUT.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "qp2024",
                "label_qp2024",
                "statut",
                "qp2015_1",
                "label_qp2015_1",
                "qp2015_2",
                "label_qp2015_2",
                "qp2015_3",
                "label_qp2015_3",
            ],
        )
        writer.writeheader()
        writer.writerows(corr_rows)

    quality = {
        "qpv_2024_rows": len(qpv2024_rows),
        "qpv_correspondance_rows": len(corr_rows),
        "notes": [
            "QPV 2024 commune list extracted from semicolon-separated source file.",
            "Rows with multi-commune coding in the raw file were excluded from the commune table until a dedicated explode rule is defined.",
            "Correspondence file links QP2024 units to QP2015 units with status change.",
        ],
    }
    with QUALITY_OUT.open("w", encoding="utf-8") as f:
        json.dump(quality, f, ensure_ascii=False, indent=2)

    print(
        json.dumps(
            {
                "qpv2024_out": str(QPV2024_OUT),
                "qpv_correspondance_out": str(QPV_CORRESP_OUT),
                "quality_out": str(QUALITY_OUT),
                "quality": quality,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
