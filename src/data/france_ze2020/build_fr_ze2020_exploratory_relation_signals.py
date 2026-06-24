"""
HERALD -- France ZE2020 exploratory relation signals (analysis layer, not
a model). See reports/canonical/HERALD_20_FR_ZE2020_EXPLORATORY_RELATION_SIGNALS.md.

This is a REORIENTATION, not a new model: previous passes (HERALD_17/18/19)
already established that the relational/neural/graph candidates do not
beat their predictive baselines (HPC job 7498752, 5 seeds, G3 FAIL for all
3 candidates). That negative predictive result does NOT invalidate the
relational signals themselves -- it means this layer should be read as
exploratory territorial/sectoral structure, not as a forecast improvement.
This script extracts, organizes, and consolidates relation signals ALREADY
COMPUTED by existing scripts (no new training, no new model) into one
interpretable table.

Four relation families are populated, all reusing existing computation:
  1. ze_to_ze_similarity        -- reconstructed from the SAME
     similarity_matrix_for_year() already used by
     build_fr_ze2020_relational_model_ready_panel.py (Category A), exposed
     here as an explicit edge list (that builder only ever exported
     AGGREGATED neighbor means, never the edges themselves).
  2. ze_to_ze_same_sector_signal -- read directly from the existing
     fr_ze2020_sector_graph_relation_signals_v1.csv (cross_ze_same_sector
     rows), produced by train_fr_ze2020_sector_graph_prototype.py.
  3. intra_ze_sector_interaction -- same source file, intra_ze_composition
     rows.
  4. ze_sector_specialization    -- read from fr_ze2020_sector_relational_features.csv
     (dominant_sector_lag_1 / dominant_sector_share_lag_1), reduced to one
     row per zone (its modal dominant sector across the panel).

Two families from the plan are explicitly NOT populated here -- documented
gaps, not silent omissions:
  - sector_to_sector_comovement: the only existing sector-to-sector
    evidence in this repository is the country-aggregate Phase 7 sector
    precedence layer (different grain -- national, not per-ZE; see
    HERALD_17 section 1, items 7-8). Mixing that grain into a ZE-level
    table without a grain-reconciliation decision would be misleading.
  - temporal_precedence_signal: no signed lag-1 precedence test exists yet
    at ZE grain in this track (Phase 7's bootstrap/permutation/FDR method
    has not been run at this grain).

"stability_score" here means YEAR-RECURRENCE (does the same edge/zone-sector
pairing reappear across multiple evaluation years), not seed-to-seed model
stability. All 4 families above are deterministic given the input data
(no MLP/random component) -- the HPC run's seed-stability finding (G4,
mean_overlap=1.0 across 5 seeds, job 7498752) is consistent with this:
these specific signals do not depend on the neural model's random seed at
all, only on the input panels. That is stated explicitly here so the
"stable across seeds" finding is not misread as a stronger result than it
is.

Never reads dynamic_stgnn_feature_panel* or graph_adjacency_core_v0.csv/
graph_adjacency_mobility_v0.csv.

Input (read-only):
  data/processed/france_ze2020/fr_ze2020_model_ready_panel.csv
  data/processed/france_ze2020/fr_ze2020_sector_graph_relation_signals_v1.csv
  data/processed/france_ze2020/fr_ze2020_sector_relational_features.csv

Output:
  data/processed/france_ze2020/fr_ze2020_exploratory_relation_signals.csv
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
    MIN_HISTORY_YEARS as ZE_MIN_HISTORY_YEARS,
)
from src.data.france_ze2020.build_fr_ze2020_relational_model_ready_panel import (  # noqa: E402
    TOP_K as ZE_TOP_K,
)
from src.data.france_ze2020.build_fr_ze2020_relational_model_ready_panel import (  # noqa: E402
    load_model_ready_panel,
    similarity_matrix_for_year,
)
from src.data.france_ze2020.build_fr_ze2020_sector_panel import SECTOR_LABELS  # noqa: E402

MODEL_READY_PANEL_PATH = ROOT / "data/processed/france_ze2020/fr_ze2020_model_ready_panel.csv"
SECTOR_GRAPH_SIGNALS_PATH = (
    ROOT / "data/processed/france_ze2020/fr_ze2020_sector_graph_relation_signals_v1.csv"
)
SECTOR_FEATURES_PATH = ROOT / "data/processed/france_ze2020/fr_ze2020_sector_relational_features.csv"
OUT_DIR = ROOT / "data/processed/france_ze2020"
OUT_PATH = OUT_DIR / "fr_ze2020_exploratory_relation_signals.csv"

CLAIM_STATUS = "exploratory_association_not_causal"
CAVEAT = (
    "Associação exploratória observada nos dados; não estabelece causalidade, "
    "não constitui recomendação automática, e deve ser interpretada por um "
    "especialista antes de qualquer uso."
)

RELATION_COLUMNS = [
    "relation_id",
    "source_type",
    "source_id",
    "source_label",
    "target_type",
    "target_id",
    "target_label",
    "relation_family",
    "relation_direction",
    "sector_code",
    "sector_label",
    "year_start",
    "year_end",
    "signal_strength",
    "stability_score",
    "rank_within_family",
    "evidence_source",
    "interpretation_label",
    "claim_status",
    "caveat",
]


def _zone_labels(panel: pd.DataFrame) -> pd.Series:
    return panel[["ze2020", "ze2020_label"]].drop_duplicates().set_index("ze2020")["ze2020_label"]


def build_ze_to_ze_similarity_signals(
    panel: pd.DataFrame | None = None, top_k: int = ZE_TOP_K, min_history_years: int = ZE_MIN_HISTORY_YEARS
) -> pd.DataFrame:
    """Category A (ZE<->ZE trajectory similarity), reconstructed as an
    explicit edge list -- the original builder only ever exported
    aggregated neighbor means."""
    if panel is None:
        panel = load_model_ready_panel()
    labels = _zone_labels(panel)
    years = sorted(panel["year"].unique())

    edge_rows = []
    for year in years:
        corr = similarity_matrix_for_year(panel, year, min_history_years)
        if corr is None:
            continue
        for zone in corr.index:
            candidates = corr.loc[zone].drop(labels=[zone], errors="ignore").dropna()
            candidates = candidates[candidates > 0].sort_values(ascending=False).head(top_k)
            for target_zone, weight in candidates.items():
                edge_rows.append(
                    {"source_id": zone, "target_id": target_zone, "year": year, "weight": float(weight)}
                )

    if not edge_rows:
        return pd.DataFrame(columns=RELATION_COLUMNS)

    edges = pd.DataFrame(edge_rows)
    total_years = edges["year"].nunique()
    agg = (
        edges.groupby(["source_id", "target_id"])
        .agg(signal_strength=("weight", "mean"), year_start=("year", "min"), year_end=("year", "max"), n_years=("year", "nunique"))
        .reset_index()
    )
    agg["stability_score"] = agg["n_years"] / total_years

    rows = []
    for _, row in agg.iterrows():
        source_label = labels.get(row["source_id"], "")
        target_label = labels.get(row["target_id"], "")
        rows.append(
            {
                "source_type": "ZE2020",
                "source_id": row["source_id"],
                "source_label": source_label,
                "target_type": "ZE2020",
                "target_id": row["target_id"],
                "target_label": target_label,
                "relation_family": "ze_to_ze_similarity",
                "relation_direction": "directed",
                "sector_code": "",
                "sector_label": "",
                "year_start": int(row["year_start"]),
                "year_end": int(row["year_end"]),
                "signal_strength": float(row["signal_strength"]),
                "stability_score": float(row["stability_score"]),
                "evidence_source": (
                    "build_fr_ze2020_relational_model_ready_panel.py::similarity_matrix_for_year "
                    "(reconstructed edge list, Category A)"
                ),
                "interpretation_label": (
                    f"ZE {row['source_id']} ({source_label}) tem trajetória de criação de "
                    f"estabelecimentos historicamente parecida com ZE {row['target_id']} ({target_label})."
                ),
            }
        )
    return pd.DataFrame(rows)


def _split_node_id(node_id: str) -> tuple[str, str]:
    ze2020, sector_code = node_id.rsplit("_", 1)
    return ze2020, sector_code


def _load_sector_graph_signals(path: Path = SECTOR_GRAPH_SIGNALS_PATH) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found -- run src/modeles/france_ze2020/train_fr_ze2020_sector_graph_prototype.py first."
        )
    return pd.read_csv(path)


def build_ze_to_ze_same_sector_signals(signals: pd.DataFrame | None = None, panel: pd.DataFrame | None = None) -> pd.DataFrame:
    if signals is None:
        signals = _load_sector_graph_signals()
    if panel is None:
        panel = load_model_ready_panel()
    labels = _zone_labels(panel)

    cross = signals[signals["relation_type"] == "cross_ze_same_sector"].copy()
    if cross.empty:
        return pd.DataFrame(columns=RELATION_COLUMNS)

    cross[["source_ze", "sector_code"]] = cross["source_node"].apply(lambda x: pd.Series(_split_node_id(x)))
    cross[["target_ze", "_sector_check"]] = cross["target_node"].apply(lambda x: pd.Series(_split_node_id(x)))

    total_years = cross["year"].nunique()
    agg = (
        cross.groupby(["source_ze", "target_ze", "sector_code"])
        .agg(signal_strength=("signal_strength", "mean"), year_start=("year", "min"), year_end=("year", "max"), n_years=("year", "nunique"))
        .reset_index()
    )
    agg["stability_score"] = agg["n_years"] / total_years

    rows = []
    for _, row in agg.iterrows():
        source_label = labels.get(row["source_ze"], "")
        target_label = labels.get(row["target_ze"], "")
        sector_label = SECTOR_LABELS.get(row["sector_code"], row["sector_code"])
        rows.append(
            {
                "source_type": "ZE2020",
                "source_id": row["source_ze"],
                "source_label": source_label,
                "target_type": "ZE2020",
                "target_id": row["target_ze"],
                "target_label": target_label,
                "relation_family": "ze_to_ze_same_sector_signal",
                "relation_direction": "directed",
                "sector_code": row["sector_code"],
                "sector_label": sector_label,
                "year_start": int(row["year_start"]),
                "year_end": int(row["year_end"]),
                "signal_strength": float(row["signal_strength"]),
                "stability_score": float(row["stability_score"]),
                "evidence_source": (
                    "train_fr_ze2020_sector_graph_prototype.py "
                    "(fr_ze2020_sector_graph_relation_signals_v1.csv, cross_ze_same_sector rows)"
                ),
                "interpretation_label": (
                    f"No setor {sector_label.lower()}, ZE {row['source_ze']} ({source_label}) e "
                    f"ZE {row['target_ze']} ({target_label}) mostram trajetórias parecidas."
                ),
            }
        )
    return pd.DataFrame(rows)


def build_intra_ze_sector_interaction_signals(signals: pd.DataFrame | None = None, panel: pd.DataFrame | None = None) -> pd.DataFrame:
    if signals is None:
        signals = _load_sector_graph_signals()
    if panel is None:
        panel = load_model_ready_panel()
    labels = _zone_labels(panel)

    intra = signals[signals["relation_type"] == "intra_ze_composition"].copy()
    if intra.empty:
        return pd.DataFrame(columns=RELATION_COLUMNS)

    intra[["ze2020", "sector_a"]] = intra["source_node"].apply(lambda x: pd.Series(_split_node_id(x)))
    intra[["_ze_check", "sector_b"]] = intra["target_node"].apply(lambda x: pd.Series(_split_node_id(x)))

    total_years = intra["year"].nunique()
    agg = (
        intra.groupby(["ze2020", "sector_a", "sector_b"])
        .agg(signal_strength=("signal_strength", "mean"), year_start=("year", "min"), year_end=("year", "max"), n_years=("year", "nunique"))
        .reset_index()
    )
    agg["stability_score"] = agg["n_years"] / total_years

    rows = []
    for _, row in agg.iterrows():
        ze_label = labels.get(row["ze2020"], "")
        sector_a_label = SECTOR_LABELS.get(row["sector_a"], row["sector_a"])
        sector_b_label = SECTOR_LABELS.get(row["sector_b"], row["sector_b"])
        rows.append(
            {
                "source_type": "ZE2020xSetor",
                "source_id": f"{row['ze2020']}_{row['sector_a']}",
                "source_label": f"{ze_label} - {sector_a_label}",
                "target_type": "ZE2020xSetor",
                "target_id": f"{row['ze2020']}_{row['sector_b']}",
                "target_label": f"{ze_label} - {sector_b_label}",
                "relation_family": "intra_ze_sector_interaction",
                "relation_direction": "undirected",
                "sector_code": "",
                "sector_label": "",
                "year_start": int(row["year_start"]),
                "year_end": int(row["year_end"]),
                "signal_strength": float(row["signal_strength"]),
                "stability_score": float(row["stability_score"]),
                "evidence_source": (
                    "train_fr_ze2020_sector_graph_prototype.py "
                    "(fr_ze2020_sector_graph_relation_signals_v1.csv, intra_ze_composition rows)"
                ),
                "interpretation_label": (
                    f"Na ZE {row['ze2020']} ({ze_label}), os setores {sector_a_label.lower()} e "
                    f"{sector_b_label.lower()} -- os dois com maior participação na zona -- "
                    "têm trajetórias de crescimento associadas."
                ),
            }
        )
    return pd.DataFrame(rows)


def build_ze_sector_specialization_signals(
    sector_features: pd.DataFrame | None = None, panel: pd.DataFrame | None = None
) -> pd.DataFrame:
    if sector_features is None:
        if not SECTOR_FEATURES_PATH.exists():
            raise FileNotFoundError(f"{SECTOR_FEATURES_PATH} not found.")
        sector_features = pd.read_csv(SECTOR_FEATURES_PATH, dtype={"ze2020": str})
    if panel is None:
        panel = load_model_ready_panel()
    labels = _zone_labels(panel)

    valid = sector_features.dropna(subset=["dominant_sector_lag_1"])
    rows = []
    for ze2020, group in valid.drop_duplicates(subset=["ze2020", "year"]).groupby("ze2020"):
        mode_sector = group["dominant_sector_lag_1"].mode().iloc[0]
        matching = group[group["dominant_sector_lag_1"] == mode_sector]
        stability_score = len(matching) / group["year"].nunique()
        mean_share = float(matching["dominant_sector_share_lag_1"].mean())
        sector_label = SECTOR_LABELS.get(mode_sector, mode_sector)
        ze_label = labels.get(ze2020, "")
        rows.append(
            {
                "source_type": "ZE2020",
                "source_id": ze2020,
                "source_label": ze_label,
                "target_type": "Setor",
                "target_id": mode_sector,
                "target_label": sector_label,
                "relation_family": "ze_sector_specialization",
                "relation_direction": "ze_to_sector",
                "sector_code": mode_sector,
                "sector_label": sector_label,
                "year_start": int(group["year"].min()),
                "year_end": int(group["year"].max()),
                "signal_strength": mean_share,
                "stability_score": float(stability_score),
                "evidence_source": (
                    "fr_ze2020_sector_relational_features.csv "
                    "(dominant_sector_lag_1 / dominant_sector_share_lag_1, modal sector across the panel)"
                ),
                "interpretation_label": (
                    f"ZE {ze2020} ({ze_label}) é historicamente especializada no setor "
                    f"{sector_label.lower()} (setor dominante em {stability_score:.0%} dos anos observados)."
                ),
            }
        )
    return pd.DataFrame(rows)


def assemble_relation_table(frames: list[pd.DataFrame]) -> pd.DataFrame:
    non_empty = [f for f in frames if not f.empty]
    if not non_empty:
        return pd.DataFrame(columns=RELATION_COLUMNS)
    table = pd.concat(non_empty, ignore_index=True)

    table["rank_within_family"] = (
        table.groupby("relation_family")["signal_strength"]
        .rank(ascending=False, method="first")
        .astype(int)
    )
    table["claim_status"] = CLAIM_STATUS
    table["caveat"] = CAVEAT
    table["relation_id"] = (
        table["relation_family"]
        + "__"
        + table["source_id"].astype(str)
        + "__"
        + table["target_id"].astype(str)
        + "__"
        + table["sector_code"].astype(str)
    )
    assert table["relation_id"].is_unique, "relation_id must be unique"

    table = table[RELATION_COLUMNS].sort_values(["relation_family", "rank_within_family"]).reset_index(drop=True)
    return table


def build_exploratory_relation_signals() -> pd.DataFrame:
    panel = load_model_ready_panel()
    sector_graph_signals = _load_sector_graph_signals()
    sector_features = pd.read_csv(SECTOR_FEATURES_PATH, dtype={"ze2020": str})

    frames = [
        build_ze_to_ze_similarity_signals(panel),
        build_ze_to_ze_same_sector_signals(sector_graph_signals, panel),
        build_intra_ze_sector_interaction_signals(sector_graph_signals, panel),
        build_ze_sector_specialization_signals(sector_features, panel),
    ]
    return assemble_relation_table(frames)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    table = build_exploratory_relation_signals()
    table.to_csv(OUT_PATH, index=False)

    print(f"Rows: {len(table)}")
    print(table["relation_family"].value_counts())
    print(f"Saved: {OUT_PATH}")


if __name__ == "__main__":
    main()
