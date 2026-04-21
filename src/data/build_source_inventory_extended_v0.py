import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
RAW_ROOT = ROOT / "data" / "raw"
INTERIM_ROOT = ROOT / "data" / "interim"
PROCESSED_ROOT = ROOT / "data" / "processed"
OUT_JSON = ROOT / "reports" / "source_inventory_extended_v0.json"
OUT_MD = ROOT / "reports" / "SOURCE_INVENTORY_EXTENDED_V0.md"


KEYWORDS = {
    "energy": ["energy", "electric", "gaz", "consommation"],
    "rei_cfe": ["rei", "cfe", "microentre"],
    "sitadel": ["sitadel", "permis", "autorisations"],
    "flores": ["flores"],
    "filosofi": ["filosofi"],
    "population": ["population", "pop"],
    "rp_employment": ["emploi", "rp_", "active_lr", "jobs_lt"],
    "bpe": ["bpe"],
    "zan": ["zan", "conso"],
    "sirene": ["sirene", "etablissement", "unitelegale"],
}


def classify(path_str):
    low = path_str.lower()
    for label, keys in KEYWORDS.items():
        if any(k in low for k in keys):
            return label
    return "other"


def scan_tree(base):
    rows = []
    for path in base.rglob("*"):
        if path.is_file():
            rel = path.relative_to(ROOT)
            rows.append(
                {
                    "path": str(rel),
                    "root": rel.parts[1] if len(rel.parts) > 1 else rel.parts[0],
                    "family": classify(str(rel)),
                    "size_mb": round(path.stat().st_size / (1024 * 1024), 3),
                    "extension": path.suffix.lower().lstrip("."),
                }
            )
    return rows


def main():
    rows = scan_tree(RAW_ROOT) + scan_tree(INTERIM_ROOT) + scan_tree(PROCESSED_ROOT)
    df = pd.DataFrame(rows)

    summary = (
        df.groupby(["root", "family"], as_index=False)
        .agg(files=("path", "count"), size_mb=("size_mb", "sum"))
        .sort_values(["root", "files"], ascending=[True, False])
    )

    spotlight = (
        df[df["family"] != "other"]
        .groupby("family", as_index=False)
        .agg(files=("path", "count"), size_mb=("size_mb", "sum"))
        .sort_values("files", ascending=False)
    )

    payload = {
        "roots_scanned": ["data/raw", "data/interim", "data/processed"],
        "summary_by_root_and_family": summary.to_dict(orient="records"),
        "spotlight_families": spotlight.to_dict(orient="records"),
        "sample_paths": (
            df[df["family"] != "other"]
            .sort_values(["family", "path"])
            .groupby("family")
            .head(8)[["family", "path"]]
            .to_dict(orient="records")
        ),
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# Source Inventory Extended v0",
        "",
        "| root | family | files | size_mb |",
        "| :--- | :--- | ---: | ---: |",
    ]
    for row in payload["summary_by_root_and_family"]:
        lines.append(f"| {row['root']} | {row['family']} | {row['files']} | {row['size_mb']:.3f} |")
    lines.extend(["", "## Spotlight", "", "| family | files | size_mb |", "| :--- | ---: | ---: |"])
    for row in payload["spotlight_families"]:
        lines.append(f"| {row['family']} | {row['files']} | {row['size_mb']:.3f} |")
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps(payload, indent=2, ensure_ascii=False))
    print(f"Saved metrics to {OUT_JSON}")
    print(f"Saved report to {OUT_MD}")


if __name__ == "__main__":
    main()
