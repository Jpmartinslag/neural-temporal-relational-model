from __future__ import annotations

import csv
import io
import json
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[2]
HIST_XLSX = Path("/tmp/zrr_inspect/diffusion-zonages-historique-zrr-2019.xlsx")
COG2021_XLSX = Path("/tmp/zrr_inspect/diffusion-zonages-zrr-cog2021.xlsx")
OUT_DIR = ROOT / "data" / "interim" / "policy"
HIST_OUT = OUT_DIR / "zrr_historique_communes_v0.csv"
COG2021_OUT = OUT_DIR / "zrr_cog2021_communes_v0.csv"
QUALITY_OUT = ROOT / "reports" / "zrr_tables_quality_v0.json"

NS = {
    "a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}


def load_workbook_parts(path: Path):
    z = zipfile.ZipFile(path)
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    relmap = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rels}
    sstrings = []
    if "xl/sharedStrings.xml" in z.namelist():
        ss = ET.fromstring(z.read("xl/sharedStrings.xml"))
        for si in ss.findall("a:si", NS):
            sstrings.append("".join(t.text or "" for t in si.iterfind(".//a:t", NS)))
    sheets = {}
    for s in wb.find("a:sheets", NS):
        name = s.attrib["name"]
        rid = s.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]
        sheets[name] = "xl/" + relmap[rid]
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


def extract_historical() -> tuple[list[dict[str, str]], list[str]]:
    zf, sheets, sstrings = load_workbook_parts(HIST_XLSX)
    rows = []
    years = []
    for sheet_name, target in sheets.items():
        if not sheet_name.isdigit():
            continue
        years.append(sheet_name)
        for rownum, vals in sheet_rows(zf, target, sstrings):
            if rownum <= 6:
                continue
            codgeo = vals.get("A", "").strip()
            libgeo = vals.get("B", "").strip()
            status = vals.get("C", "").strip()
            if not codgeo or not codgeo.isdigit():
                continue
            rows.append(
                {
                    "year": sheet_name,
                    "codgeo": codgeo.zfill(5),
                    "libgeo": libgeo,
                    "zrr_status": status,
                }
            )
    zf.close()
    return rows, years


def extract_cog2021() -> list[dict[str, str]]:
    zf, sheets, sstrings = load_workbook_parts(COG2021_XLSX)
    target = sheets["Classement ZRR (COG 2021)"]
    rows = []
    for rownum, vals in sheet_rows(zf, target, sstrings):
        if rownum <= 6:
            continue
        codgeo = vals.get("A", "").strip()
        libgeo = vals.get("B", "").strip()
        zrr_simp = vals.get("C", "").strip()
        zonage_zrr = vals.get("D", "").strip()
        if not codgeo:
            continue
        rows.append(
            {
                "codgeo": codgeo.zfill(5),
                "libgeo": libgeo,
                "zrr_simp": zrr_simp,
                "zonage_zrr": zonage_zrr,
            }
        )
    zf.close()
    return rows


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    hist_rows, hist_years = extract_historical()
    cog2021_rows = extract_cog2021()

    with HIST_OUT.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["year", "codgeo", "libgeo", "zrr_status"])
        writer.writeheader()
        writer.writerows(hist_rows)

    with COG2021_OUT.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["codgeo", "libgeo", "zrr_simp", "zonage_zrr"])
        writer.writeheader()
        writer.writerows(cog2021_rows)

    quality = {
        "historical_years_found": sorted(hist_years),
        "historical_rows": len(hist_rows),
        "cog2021_rows": len(cog2021_rows),
        "notes": [
            "Historical workbook stores one sheet per reference year.",
            "COG2021 workbook provides commune-level ZRR status aligned to COG 2021.",
        ],
    }
    with QUALITY_OUT.open("w", encoding="utf-8") as f:
        json.dump(quality, f, ensure_ascii=False, indent=2)

    print(
        json.dumps(
            {
                "historical_out": str(HIST_OUT),
                "cog2021_out": str(COG2021_OUT),
                "quality_out": str(QUALITY_OUT),
                "quality": quality,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
