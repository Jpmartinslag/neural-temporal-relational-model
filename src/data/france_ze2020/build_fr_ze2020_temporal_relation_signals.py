"""Build leakage-safe as-of-time ZE2020 x sector relation snapshots.

The exploratory relation export is a retrospective presentation artifact and
must not be used as model input.  This builder reconstructs annual relation
snapshots directly from causal lag features.  Every row for decision year ``t``
uses observations strictly before or available at ``t``; recurrence and
stability denominators are also truncated at ``t``.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data.france_ze2020.build_fr_ze2020_relational_model_ready_panel import (  # noqa: E402
    MODEL_READY_PANEL_PATH,
    similarity_matrix_for_year,
)
from src.modeles.france_ze2020.train_fr_ze2020_sector_graph_prototype import (  # noqa: E402
    add_cross_ze_messages,
    build_node_table,
    intra_ze_relation_signals,
)

OUT_DIR = ROOT / "data/processed/france_ze2020"
OUT_PATH = OUT_DIR / "fr_ze2020_temporal_relation_signals.csv.gz"

ZE_TOP_K = 5
ZE_MIN_HISTORY_YEARS = 3
CLAIM_STATUS = "temporal_relation_snapshot_exploratory_not_causal"

OUTPUT_COLUMNS = [
    "relation_snapshot_id",
    "relation_id",
    "source_node_id",
    "target_node_id",
    "decision_year",
    "relation_family",
    "relation_direction",
    "sector_code",
    "signal_strength",
    "recurrence_count_to_t",
    "available_relation_years_to_t",
    "stability_score",
    "evidence_source",
    "claim_status",
]


def load_model_ready_panel(path: Path = MODEL_READY_PANEL_PATH) -> pd.DataFrame:
    panel = pd.read_csv(path, dtype={"ze2020": str})
    panel["ze2020"] = panel["ze2020"].str.zfill(4)
    panel["year"] = panel["year"].astype(int)
    return panel


def _node_id(ze2020: str, sector_code: str) -> str:
    return f"{str(ze2020).zfill(4)}_{sector_code}"


def _ze_similarity_rows(panel: pd.DataFrame, sector_codes: list[str]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for year in sorted(int(value) for value in panel["year"].unique()):
        corr = similarity_matrix_for_year(panel, year, ZE_MIN_HISTORY_YEARS)
        if corr is None:
            continue
        for source_ze in corr.index:
            candidates = corr.loc[source_ze].drop(labels=[source_ze], errors="ignore").dropna()
            candidates = candidates[candidates > 0].sort_values(ascending=False).head(ZE_TOP_K)
            for target_ze, strength in candidates.items():
                for sector_code in sector_codes:
                    rows.append(
                        {
                            "source_node_id": _node_id(source_ze, sector_code),
                            "target_node_id": _node_id(target_ze, sector_code),
                            "decision_year": year,
                            "relation_family": "ze_similarity",
                            "relation_direction": "directed",
                            "sector_code": sector_code,
                            "signal_strength": float(strength),
                            "evidence_source": "causal_prior_growth_ze_similarity",
                        }
                    )
    return rows


def _sector_relation_rows(nodes: pd.DataFrame) -> list[dict[str, object]]:
    years = sorted(int(value) for value in nodes["year"].unique())
    _, cross_edges = add_cross_ze_messages(nodes, target_years=years)
    intra_edges = intra_ze_relation_signals(nodes, years)
    rows: list[dict[str, object]] = []

    for edge in cross_edges.itertuples(index=False):
        rows.append(
            {
                "source_node_id": str(edge.source_node),
                "target_node_id": str(edge.target_node),
                "decision_year": int(edge.year),
                "relation_family": "cross_ze_same_sector",
                "relation_direction": "directed",
                "sector_code": str(edge.source_node).rsplit("_", 1)[1],
                "signal_strength": float(edge.signal_strength),
                "evidence_source": "causal_prior_sector_growth_cross_ze_similarity",
            }
        )

    for edge in intra_edges.itertuples(index=False):
        source = str(edge.source_node)
        target = str(edge.target_node)
        source, target = sorted([source, target])
        rows.append(
            {
                "source_node_id": source,
                "target_node_id": target,
                "decision_year": int(edge.year),
                "relation_family": "intra_ze_sector",
                "relation_direction": "undirected",
                "sector_code": "",
                "signal_strength": float(edge.signal_strength),
                "evidence_source": "causal_prior_growth_intra_ze_sector_correlation",
            }
        )
    return rows


def _add_asof_recurrence(signals: pd.DataFrame) -> pd.DataFrame:
    out = signals.sort_values(["relation_family", "relation_id", "decision_year"]).copy()
    out["recurrence_count_to_t"] = out.groupby("relation_id").cumcount() + 1

    family_years = {
        family: sorted(int(year) for year in frame["decision_year"].unique())
        for family, frame in out.groupby("relation_family")
    }
    year_positions = {
        (family, year): position + 1
        for family, years in family_years.items()
        for position, year in enumerate(years)
    }
    out["available_relation_years_to_t"] = [
        year_positions[(family, int(year))]
        for family, year in zip(out["relation_family"], out["decision_year"])
    ]
    out["stability_score"] = (
        out["recurrence_count_to_t"] / out["available_relation_years_to_t"]
    )
    return out


def build_temporal_relation_signals(
    model_ready_panel: pd.DataFrame | None = None,
    sector_nodes: pd.DataFrame | None = None,
) -> pd.DataFrame:
    if model_ready_panel is None:
        model_ready_panel = load_model_ready_panel()
    if sector_nodes is None:
        sector_nodes = build_node_table()

    sector_codes = sorted(str(value) for value in sector_nodes["sector_code"].unique())
    rows = _ze_similarity_rows(model_ready_panel, sector_codes)
    rows.extend(_sector_relation_rows(sector_nodes))
    if not rows:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    signals = pd.DataFrame(rows)
    signals = signals[np.isfinite(signals["signal_strength"].to_numpy(dtype=float))].copy()
    signals = signals[signals["source_node_id"] != signals["target_node_id"]].copy()
    signals["relation_id"] = (
        signals["relation_family"]
        + "__"
        + signals["source_node_id"]
        + "__"
        + signals["target_node_id"]
    )
    signals = signals.drop_duplicates(["relation_id", "decision_year"])
    signals = _add_asof_recurrence(signals)
    signals["relation_snapshot_id"] = (
        signals["relation_id"] + "__" + signals["decision_year"].astype(str)
    )
    signals["claim_status"] = CLAIM_STATUS
    signals = signals[OUTPUT_COLUMNS].sort_values(
        ["decision_year", "relation_family", "source_node_id", "target_node_id"]
    )
    return signals.reset_index(drop=True)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    signals = build_temporal_relation_signals()
    signals.to_csv(OUT_PATH, index=False, compression="gzip")
    print(f"Rows: {len(signals)}")
    print(f"Years: {signals['decision_year'].min()}-{signals['decision_year'].max()}")
    print(f"Families: {signals['relation_family'].value_counts().to_dict()}")
    print(f"Saved: {OUT_PATH}")


if __name__ == "__main__":
    main()
