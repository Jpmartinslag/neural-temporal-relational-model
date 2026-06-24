"""
HERALD -- France ZE2020 relational + sector prototype: exploratory examples
(MVP2, Part 5). See reports/canonical/HERALD_17_FR_ZE2020_RELATIONAL_LAYER_PLAN.md,
"MVP2 Categoria C" section.

Reads ONLY data/processed/france_ze2020/fr_ze2020_relational_sector_prototype_panel.csv
(already causal, already tested) and emits a small, human-interpretable
table: observed value, the persistence baseline (predicted_baseline=lag_1,
no fitting), the ZE-to-ZE relational signal (Category A), the ZE-to-sector
signal (Category C), and a plain-language exploratory_note per row.

This is a presentation/export step, NOT a model: predicted_baseline is
literally lag_1 (the same persistence baseline already used elsewhere in
this track), not a new fit. exploratory_note is a deterministic template
sentence built from already-causal columns -- never an LLM call, never a
recommendation, always closed with an explicit non-causality caveat.

Only rows where BOTH the ZE-to-ZE relational features and the ZE-to-sector
distribution features are available are included (2017-2025 in the current
panel) -- this is a complete, reproducible export, not a hand-picked sample;
read it selectively (e.g. by ze2020) for illustration.

Input (read-only):
  data/processed/france_ze2020/fr_ze2020_relational_sector_prototype_panel.csv

Output:
  data/processed/france_ze2020/fr_ze2020_relational_prototype_examples.csv
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data.france_ze2020.build_fr_ze2020_sector_panel import SECTOR_LABELS  # noqa: E402

PROTOTYPE_PANEL_PATH = (
    ROOT / "data/processed/france_ze2020/fr_ze2020_relational_sector_prototype_panel.csv"
)
OUT_DIR = ROOT / "data/processed/france_ze2020"
OUT_PATH = OUT_DIR / "fr_ze2020_relational_prototype_examples.csv"

OUTPUT_COLUMNS = [
    "ze2020",
    "ze2020_label",
    "year",
    "observed_value",
    "lag_1",
    "predicted_baseline",
    "similar_ze_count",
    "similar_ze_lag_1_mean",
    "dominant_sector_lag_1",
    "dominant_sector_share_lag_1",
    "sector_diversity_lag_1",
    "top_sector_signal_lag_1",
    "exploratory_note",
]


def load_prototype_panel(path: Path = PROTOTYPE_PANEL_PATH) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"ze2020": str})
    df["year"] = df["year"].astype(int)
    return df


def _exploratory_note(row: pd.Series) -> str:
    sector_label = SECTOR_LABELS.get(row["dominant_sector_lag_1"])
    parts: list[str] = []

    if sector_label is not None:
        parts.append(
            f"ZE com {sector_label.lower()} como setor dominante "
            f"(share={row['dominant_sector_share_lag_1']:.0%})"
        )
    else:
        parts.append("ZE sem distribuição setorial disponível para o ano anterior")

    if pd.notna(row["similar_ze_count"]) and row["similar_ze_count"] > 0:
        direction = (
            "crescimento"
            if pd.notna(row["similar_ze_lag_1_mean"]) and row["similar_ze_lag_1_mean"] >= row["lag_1"]
            else "retração"
        )
        parts.append(
            f"trajetória similar a {int(row['similar_ze_count'])} outras ZEs "
            f"com sinal recente de {direction}"
        )
    else:
        parts.append("sem ZEs similares suficientes neste ano")

    return "; ".join(parts) + ". Relação exploratória, sem claim causal."


def build_examples(panel: pd.DataFrame | None = None) -> pd.DataFrame:
    if panel is None:
        panel = load_prototype_panel()

    complete = panel[
        (panel["relational_feature_available"] == 1)
        & (panel["mask_ze_sector_distribution_lag_1_available"] == 1)
    ].copy()

    complete["predicted_baseline"] = complete["lag_1"]
    complete["exploratory_note"] = complete.apply(_exploratory_note, axis=1)

    examples = complete[OUTPUT_COLUMNS].sort_values(["ze2020", "year"]).reset_index(drop=True)
    return examples


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    examples = build_examples()
    examples.to_csv(OUT_PATH, index=False)

    print(f"Rows: {len(examples)}")
    print("Sample:")
    print(examples.head(3)[["ze2020", "ze2020_label", "year", "exploratory_note"]].to_string(index=False))
    print(f"Saved: {OUT_PATH}")


if __name__ == "__main__":
    main()
