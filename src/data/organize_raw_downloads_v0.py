#!/usr/bin/env python3
"""Organize raw downloads that were left in the repository root.

The script is deliberately conservative:
- only root-level files are moved or removed;
- processed/interim/report/code files are not touched;
- a source is removed only when the destination already has identical bytes;
- known duplicate downloads such as ``(1)`` copies are removed by hash.
"""

from __future__ import annotations

import csv
import hashlib
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "reports" / "RAW_DOWNLOAD_ORGANIZATION_2026_04_12_V0.md"
MANIFEST = ROOT / "metadata" / "raw_download_organization_2026_04_12_v0.csv"

KEEP_ROOT = {
    ".gitignore",
    "requirements.txt",
}

DUPLICATE_PREFERRED = {
    "DS_SIDE_CREA_ENT_COM_2024_CSV.zip": "DS_SIDE_CREA_ENT_COM_2024_CSV_FR.zip",
    "DS_SIDE_CREA_ETAB_COM_2024_CSV.zip": "DS_SIDE_CREA_ETAB_COM_2024_CSV_FR.zip",
    "DS_FLORES_A17_2024_CSV_FR (1).zip": "DS_FLORES_A17_2024_CSV_FR.zip",
    "DS_RP_EMPLOI_LT_PRINC_2022_CSV_FR (1).zip": "DS_RP_EMPLOI_LT_PRINC_2022_CSV_FR.zip",
    "DS_FLORES_ECONOMIC_SPHERE_2024_CSV_FR (1).zip": "DS_FLORES_ECONOMIC_SPHERE_2024_CSV_FR.zip",
    "DS_FILOSOFI_CC_2021_CSV_FR (1).zip": "DS_FILOSOFI_CC_2021_CSV_FR.zip",
    "BPE20_Liste_equipements_insee-fr (1).pdf": "BPE20_Liste_equipements_insee-fr.pdf",
    "BPE20_Liste_equipements_insee-fr (2).pdf": "BPE20_Liste_equipements_insee-fr.pdf",
    "contenu_bpe20_ensemble (1).pdf": "contenu_bpe20_ensemble.pdf",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def target_for(path: Path) -> Path | None:
    name = path.name
    lower = name.lower()

    if name in KEEP_ROOT or name.startswith("."):
        return None
    if name == "CATALOGO_INSEE_DATASETS.md":
        return ROOT / "metadata" / name
    if name == "scan_output_bundle.tar.gz":
        return ROOT / "reports" / "scan_archives" / name
    if name == "methode_constitution_ze2020.pdf":
        return ROOT / "data" / "raw" / "territorial" / "docs" / name

    if name.startswith("DS_RP_") or name.startswith("base-cc-") or name.startswith("base-flux-"):
        return ROOT / "data" / "raw" / "census" / "rp_2022" / name
    if name.startswith("DS_POPULATIONS") or name == "base-pop-historiques-1876-2023.xlsx":
        return ROOT / "data" / "raw" / "population" / name

    if name.startswith("DS_FILOSOFI") or name.startswith("indic-struct-distrib-revenu"):
        return ROOT / "data" / "raw" / "income" / "filosofi" / name

    if name.startswith("DS_FLORES") or name.startswith("TD_FLORES") or name == "table_passage_flores.zip":
        return ROOT / "data" / "raw" / "employment" / "flores" / name

    if name.startswith("DS_SIDE") or name.startswith("TAB_SIDE") or name.startswith("Listes de codes DS_SIDE"):
        return ROOT / "data" / "raw" / "business_demography" / "side" / name

    if name.startswith("DS_BTS"):
        return ROOT / "data" / "raw" / "wages" / "bts" / name

    if lower.startswith("if") and lower.endswith(".xls"):
        return ROOT / "data" / "raw" / "temporal_depth" / "bpe" / "derived_article_tables" / name

    if "bpe" in lower or "buildingref" in lower:
        if lower.endswith((".pdf", ".html")):
            return ROOT / "data" / "raw" / "temporal_depth" / "bpe" / "docs" / name
        if "buildingref" in lower:
            return ROOT / "data" / "raw" / "temporal_depth" / "bpe" / "third_party_mirrors" / name
        if "bfc" in lower:
            return ROOT / "data" / "raw" / "temporal_depth" / "bpe" / "regional_mirrors" / name
        if lower.endswith(".csv") and name in {"BPE23.csv", "BPE23-full.csv"}:
            return ROOT / "data" / "raw" / "temporal_depth" / "bpe" / "extracted_cache" / name
        if lower.endswith(".parquet"):
            return ROOT / "data" / "raw" / "temporal_depth" / "bpe" / "parquet_cache" / name
        return ROOT / "data" / "raw" / "temporal_depth" / "bpe" / name

    return ROOT / "data" / "raw" / "inbox" / name


def remove_if_duplicate(path: Path, preferred_name: str, operations: list[dict[str, str]]) -> bool:
    preferred = ROOT / preferred_name
    if not preferred.exists():
        return False
    if sha256(path) != sha256(preferred):
        return False
    path.unlink()
    operations.append(
        {
            "action": "removed_duplicate",
            "source": str(path.relative_to(ROOT)),
            "destination": preferred_name,
            "notes": "byte-identical duplicate of preferred root file",
        }
    )
    return True


def organize_file(path: Path, operations: list[dict[str, str]]) -> None:
    if path.name in DUPLICATE_PREFERRED and remove_if_duplicate(path, DUPLICATE_PREFERRED[path.name], operations):
        return

    target = target_for(path)
    if target is None:
        operations.append(
            {
                "action": "kept_root",
                "source": str(path.relative_to(ROOT)),
                "destination": "",
                "notes": "root file intentionally kept",
            }
        )
        return

    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if sha256(path) == sha256(target):
            path.unlink()
            operations.append(
                {
                    "action": "removed_duplicate",
                    "source": str(path.relative_to(ROOT)),
                    "destination": str(target.relative_to(ROOT)),
                    "notes": "destination already had identical bytes",
                }
            )
        else:
            alt = target.with_name(f"{target.stem}__root_duplicate{target.suffix}")
            counter = 1
            while alt.exists():
                alt = target.with_name(f"{target.stem}__root_duplicate_{counter}{target.suffix}")
                counter += 1
            shutil.move(str(path), str(alt))
            operations.append(
                {
                    "action": "moved_name_collision",
                    "source": str(path.relative_to(ROOT)),
                    "destination": str(alt.relative_to(ROOT)),
                    "notes": "same target name existed with different bytes",
                }
            )
    else:
        shutil.move(str(path), str(target))
        operations.append(
            {
                "action": "moved",
                "source": str(path.relative_to(ROOT)),
                "destination": str(target.relative_to(ROOT)),
                "notes": "organized root raw download",
            }
        )


def write_outputs(operations: list[dict[str, str]]) -> None:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    REPORT.parent.mkdir(parents=True, exist_ok=True)

    with MANIFEST.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["action", "source", "destination", "notes"])
        writer.writeheader()
        writer.writerows(operations)

    counts: dict[str, int] = {}
    for op in operations:
        counts[op["action"]] = counts.get(op["action"], 0) + 1

    lines = [
        "# Raw Download Organization 2026-04-12 v0",
        "",
        "## Summary",
        "",
    ]
    for action, count in sorted(counts.items()):
        lines.append(f"- `{action}`: {count}")
    lines.extend(
        [
            "",
            "## Rule",
            "",
            "Only root-level raw/download files were moved or removed. Processed, interim, report, metadata and source-code trees were not cleaned by this script.",
            "A file was removed only when an identical copy was already present at the destination or when it was a byte-identical duplicate of a preferred root file.",
            "",
            "## Manifest",
            "",
            f"- `{MANIFEST.relative_to(ROOT)}`",
        ]
    )
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    operations: list[dict[str, str]] = []
    for path in sorted(ROOT.iterdir()):
        if path.is_file():
            organize_file(path, operations)
    write_outputs(operations)
    print(f"operations={len(operations)}")
    for action in sorted({op["action"] for op in operations}):
        print(f"{action}={sum(1 for op in operations if op['action'] == action)}")
    print(f"manifest={MANIFEST.relative_to(ROOT)}")
    print(f"report={REPORT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
