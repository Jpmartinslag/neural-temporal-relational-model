from __future__ import annotations

import csv
import json
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[2]
XLSX_PATH = ROOT / "base-pop-historiques-1876-2023.xlsx"
OUT_DIR = ROOT / "data" / "interim" / "population_history"
OUT_PATH = OUT_DIR / "population_history_communes_v0.csv"
QUALITY_PATH = ROOT / "reports" / "population_history_quality_v0.json"

NS = {
    "a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}


def load_parts(path: Path):
    z = zipfile.ZipFile(path)
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    relmap = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rels}
    sstrings = []
    ss = ET.fromstring(z.read("xl/sharedStrings.xml"))
    for si in ss.findall("a:si", NS):
        sstrings.append("".join(t.text or "" for t in si.iterfind(".//a:t", NS)))
    sheets = {}
    for s in wb.find("a:sheets", NS):
        sheets[s.attrib["name"]] = "xl/" + relmap[s.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]]
    return z, sheets, sstrings


def sheet_rows(zf: zipfile.ZipFile, target: str, shared_strings: list[str]):
    root = ET.fromstring(zf.read(target))
    for row in root.findall(".//a:sheetData/a:row", NS):
        rownum = int(row.attrib["r"])
        values = {}
        for cell in row.findall("a:c", NS):
            ref = cell.attrib.get("r", "")
            col = "".join(ch for ch in ref if ch.isalpha())
            t = cell.attrib.get("t")
            v = cell.find("a:v", NS)
            val = ""
            if v is not None and v.text is not None:
                val = shared_strings[int(v.text)] if t == "s" else v.text
            values[col] = val
        yield rownum, values


def main() -> None:
    zf, sheets, sstrings = load_parts(XLSX_PATH)
    target = sheets["pop_1876_2023"]

    header_long = {}
    header_short = {}
    rows = []
    years_detected = []

    for rownum, vals in sheet_rows(zf, target, sstrings):
        if rownum == 5:
            header_long = vals
            continue
        if rownum == 6:
            header_short = vals
            for col, short_name in vals.items():
                if col >= "E":
                    years_detected.append(short_name)
            continue
        if rownum <= 6:
            continue
        codgeo = vals.get("A", "").strip()
        if not codgeo:
            continue
        row = {
            "codgeo": codgeo.zfill(5),
            "reg": vals.get("B", "").strip(),
            "dep": vals.get("C", "").strip(),
            "libgeo": vals.get("D", "").strip(),
        }
        for col, short_name in header_short.items():
            if col in {"A", "B", "C", "D"}:
                continue
            row[short_name] = vals.get(col, "").strip()
        rows.append(row)

    zf.close()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys())
    with OUT_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    quality = {
        "rows": len(rows),
        "geography": "Communes, France hors Mayotte, geography at 01/01/2025",
        "publication_note": "Mise en ligne : décembre 2025",
        "latest_year_variable": "PMUN2023",
        "time_columns_count": len(fieldnames) - 4,
        "time_columns": fieldnames[4:],
    }
    with QUALITY_PATH.open("w", encoding="utf-8") as f:
        json.dump(quality, f, ensure_ascii=False, indent=2)

    print(
        json.dumps(
            {
                "out_path": str(OUT_PATH),
                "quality_path": str(QUALITY_PATH),
                "quality": quality,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
