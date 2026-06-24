"""
HERALD -- France ZE2020 exploratory relation examples (small, presentation-
ready table). See reports/canonical/HERALD_20_FR_ZE2020_EXPLORATORY_RELATION_SIGNALS.md.

Reads ONLY data/processed/france_ze2020/fr_ze2020_exploratory_relation_signals.csv
(read-only) and selects a small, curated set of illustrative rows per
relation_family, reformatted into a presentation-friendly schema. No new
computation: plain_language_interpretation is carried over verbatim from
that file's interpretation_label, never regenerated.

Selection rule: ranked by (stability_score desc, signal_strength desc), NOT
signal_strength alone -- the parent file shows the single highest
signal_strength rows for ze_to_ze_similarity are mostly one-off single-year
spikes (stability_score as low as 1/9); examples meant to illustrate
"stable" structure should not lead with those. Top N_EXAMPLES_PER_FAMILY
per family.

Input (read-only):
  data/processed/france_ze2020/fr_ze2020_exploratory_relation_signals.csv

Output:
  data/processed/france_ze2020/fr_ze2020_exploratory_relation_examples.csv
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
RELATION_SIGNALS_PATH = ROOT / "data/processed/france_ze2020/fr_ze2020_exploratory_relation_signals.csv"
OUT_DIR = ROOT / "data/processed/france_ze2020"
OUT_PATH = OUT_DIR / "fr_ze2020_exploratory_relation_examples.csv"

N_EXAMPLES_PER_FAMILY = 5

EXAMPLE_COLUMNS = [
    "example_id",
    "ze2020",
    "ze2020_label",
    "sector_code",
    "sector_label",
    "year",
    "main_signal",
    "related_ze2020",
    "related_ze2020_label",
    "related_sector_code",
    "related_sector_label",
    "signal_strength",
    "stability_score",
    "plain_language_interpretation",
    "caveat",
]


def load_relation_signals(path: Path = RELATION_SIGNALS_PATH) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found -- run "
            "src/data/france_ze2020/build_fr_ze2020_exploratory_relation_signals.py first."
        )
    return pd.read_csv(
        path,
        dtype={"source_id": str, "target_id": str, "sector_code": str, "target_label": str},
    )


def _row_to_example(row: pd.Series, example_id: str) -> dict:
    family = row["relation_family"]

    if family == "ze_sector_specialization":
        ze2020 = row["source_id"]
        ze2020_label = row["source_label"]
        sector_code = row["sector_code"]
        sector_label = row["sector_label"]
        related_ze2020 = ""
        related_ze2020_label = ""
        related_sector_code = ""
        related_sector_label = ""
    elif family == "ze_to_ze_similarity":
        ze2020 = row["source_id"]
        ze2020_label = row["source_label"]
        sector_code = ""
        sector_label = ""
        related_ze2020 = row["target_id"]
        related_ze2020_label = row["target_label"]
        related_sector_code = ""
        related_sector_label = ""
    elif family == "ze_to_ze_same_sector_signal":
        ze2020 = row["source_id"]
        ze2020_label = row["source_label"]
        sector_code = row["sector_code"]
        sector_label = row["sector_label"]
        related_ze2020 = row["target_id"]
        related_ze2020_label = row["target_label"]
        related_sector_code = row["sector_code"]
        related_sector_label = row["sector_label"]
    elif family == "intra_ze_sector_interaction":
        ze2020, sector_code = row["source_id"].rsplit("_", 1)
        _, related_sector_code = row["target_id"].rsplit("_", 1)
        ze2020_label = row["source_label"].split(" - ")[0]
        sector_label = row["source_label"].split(" - ", 1)[1] if " - " in row["source_label"] else ""
        related_sector_label = row["target_label"].split(" - ", 1)[1] if " - " in row["target_label"] else ""
        related_ze2020 = ze2020
        related_ze2020_label = ze2020_label
    else:
        raise ValueError(f"Unknown relation_family: {family}")

    return {
        "example_id": example_id,
        "ze2020": ze2020,
        "ze2020_label": ze2020_label,
        "sector_code": sector_code,
        "sector_label": sector_label,
        "year": int(row["year_end"]),
        "main_signal": family,
        "related_ze2020": related_ze2020,
        "related_ze2020_label": related_ze2020_label,
        "related_sector_code": related_sector_code,
        "related_sector_label": related_sector_label,
        "signal_strength": row["signal_strength"],
        "stability_score": row["stability_score"],
        "plain_language_interpretation": row["interpretation_label"],
        "caveat": row["caveat"],
    }


def build_relation_examples(
    signals: pd.DataFrame | None = None, n_per_family: int = N_EXAMPLES_PER_FAMILY
) -> pd.DataFrame:
    if signals is None:
        signals = load_relation_signals()

    selected = (
        signals.sort_values(["relation_family", "stability_score", "signal_strength"], ascending=[True, False, False])
        .groupby("relation_family", group_keys=False)
        .head(n_per_family)
    )

    rows = []
    for i, (_, row) in enumerate(selected.iterrows(), start=1):
        example_id = f"example_{i:03d}"
        rows.append(_row_to_example(row, example_id))

    examples = pd.DataFrame(rows)[EXAMPLE_COLUMNS]
    return examples


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    examples = build_relation_examples()
    examples.to_csv(OUT_PATH, index=False)

    print(f"Rows: {len(examples)}")
    print(examples[["example_id", "main_signal", "ze2020_label", "stability_score"]].to_string(index=False))
    print(f"Saved: {OUT_PATH}")


if __name__ == "__main__":
    main()
