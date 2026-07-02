"""
HERALD -- France ZE2020 dynamic graph input builder.

Builds the first dynamic graph input tables specified in HERALD_25.
This is a construction layer, not a trained model and not an operational
recommendation artifact.

Reads only audited France ZE2020 inputs:
  data/processed/france_ze2020/fr_ze2020_sector_ranking_panel.csv
  data/processed/france_ze2020/fr_ze2020_exploratory_relation_signals.csv

Outputs:
  data/processed/france_ze2020/fr_ze2020_dynamic_graph_nodes.csv
  data/processed/france_ze2020/fr_ze2020_dynamic_graph_edges.csv
  data/processed/france_ze2020/fr_ze2020_dynamic_graph_edges_expanding.csv.gz
  data/processed/france_ze2020/fr_ze2020_dynamic_graph_splits.csv
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
OUT_DIR = ROOT / "data/processed/france_ze2020"
RANKING_PANEL_PATH = OUT_DIR / "fr_ze2020_sector_ranking_panel.csv"
RELATION_SIGNALS_PATH = OUT_DIR / "fr_ze2020_exploratory_relation_signals.csv"
NODES_OUT_PATH = OUT_DIR / "fr_ze2020_dynamic_graph_nodes.csv"
EDGES_OUT_PATH = OUT_DIR / "fr_ze2020_dynamic_graph_edges.csv"
EXPANDING_EDGES_OUT_PATH = OUT_DIR / "fr_ze2020_dynamic_graph_edges_expanding.csv.gz"
SPLITS_OUT_PATH = OUT_DIR / "fr_ze2020_dynamic_graph_splits.csv"

FORBIDDEN_INPUT_STEMS = (
    "dynamic_stgnn_feature_panel",
    "graph_adjacency_core_v0",
    "graph_adjacency_mobility_v0",
)

NODE_FEATURE_COLUMNS = [
    "sector_count_t",
    "sector_share_t",
    "sector_rank_in_ze_year_t",
    "sector_share_lag_1",
    "sector_growth_lag_1",
    "sector_growth_lag_2",
    "dominant_sector_flag_t",
    "dominant_sector_share_lag_1",
    "sector_diversity_lag_1",
    "sector_concentration_hhi_lag_1",
    "commerce_share_lag_1",
    "construction_share_lag_1",
    "national_sector_share_lag_1",
    "national_sector_growth_lag_1",
    "relation_signal_strength_mean_to_t",
    "relation_signal_strength_max_to_t",
    "relation_stability_mean_to_t",
    "relation_count_to_t",
]

NODE_MASK_COLUMNS = [
    "mask_sector_share_lag_1_available",
    "mask_sector_growth_lag_1_available",
    "mask_sector_growth_lag_2_available",
    "mask_ze_sector_distribution_lag_1_available",
    "mask_national_sector_share_lag_1_available",
    "mask_national_sector_growth_lag_1_available",
    "mask_future_growth_1y_available",
    "mask_future_growth_3y_available",
]

LABEL_COLUMNS = [
    "future_growth_1y",
    "future_growth_3y",
    "future_top3_growth_3y_label",
]


def _assert_no_forbidden_paths() -> None:
    joined = "\n".join(str(p) for p in [RANKING_PANEL_PATH, RELATION_SIGNALS_PATH])
    for stem in FORBIDDEN_INPUT_STEMS:
        if stem in joined:
            raise ValueError(f"Forbidden legacy input referenced: {stem}")


def load_ranking_panel(path: Path = RANKING_PANEL_PATH) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"ze2020": str, "sector_code": str})
    df["ze2020"] = df["ze2020"].str.zfill(4)
    df["decision_year"] = df["decision_year"].astype(int)
    return df


def load_relation_signals(path: Path = RELATION_SIGNALS_PATH) -> pd.DataFrame:
    return pd.read_csv(path, dtype={"source_id": str, "target_id": str, "sector_code": str})


def _node_id(ze2020: str, sector_code: str) -> str:
    return f"{str(ze2020).zfill(4)}_{sector_code}"


def build_dynamic_graph_nodes(ranking_panel: pd.DataFrame | None = None) -> pd.DataFrame:
    _assert_no_forbidden_paths()
    if ranking_panel is None:
        ranking_panel = load_ranking_panel()

    required = {
        "ze2020",
        "ze2020_label",
        "sector_code",
        "sector_label",
        "decision_year",
        *NODE_FEATURE_COLUMNS,
        *NODE_MASK_COLUMNS,
        *LABEL_COLUMNS,
        "ranking_feature_complete",
    }
    missing = required.difference(ranking_panel.columns)
    if missing:
        raise ValueError(f"Ranking panel missing required columns: {sorted(missing)}")

    nodes = ranking_panel[
        [
            "ze2020",
            "ze2020_label",
            "sector_code",
            "sector_label",
            "decision_year",
            *NODE_FEATURE_COLUMNS,
            *NODE_MASK_COLUMNS,
            *LABEL_COLUMNS,
            "ranking_feature_complete",
        ]
    ].copy()
    nodes["node_id"] = [
        _node_id(ze, sector) for ze, sector in zip(nodes["ze2020"], nodes["sector_code"])
    ]
    nodes["feature_complete"] = nodes["ranking_feature_complete"].astype(int)
    nodes["claim_status"] = "dynamic_graph_input_exploratory_not_recommendation"

    col_order = [
        "node_id",
        "ze2020",
        "ze2020_label",
        "sector_code",
        "sector_label",
        "decision_year",
        *NODE_FEATURE_COLUMNS,
        *NODE_MASK_COLUMNS,
        *LABEL_COLUMNS,
        "feature_complete",
        "claim_status",
    ]
    return nodes[col_order].sort_values(["decision_year", "ze2020", "sector_code"]).reset_index(drop=True)


def _valid_node_lookup(nodes: pd.DataFrame) -> set[tuple[str, int]]:
    return set(zip(nodes["node_id"], nodes["decision_year"].astype(int)))


def _base_edge_row(
    *,
    source_node_id: str,
    target_node_id: str,
    decision_year: int,
    edge_type: str,
    edge_weight: float,
    signal_strength: float,
    stability_score: float,
    source_basis: str,
    relation_id: str,
    source_relation_year_end: int | None = None,
    edge_age: int = 0,
    edge_memory_mode: str = "instant",
) -> dict[str, object]:
    if edge_memory_mode == "instant":
        edge_id = f"{edge_type}__{decision_year}__{source_node_id}__{target_node_id}__{relation_id}"
    else:
        edge_id = (
            f"{edge_type}__{edge_memory_mode}__{decision_year}__{source_node_id}__"
            f"{target_node_id}__{relation_id}"
        )
    return {
        "edge_id": edge_id,
        "source_node_id": source_node_id,
        "target_node_id": target_node_id,
        "decision_year": int(decision_year),
        "edge_type": edge_type,
        "edge_weight": float(edge_weight),
        "signal_strength": float(signal_strength),
        "stability_score": float(stability_score),
        "source_basis": source_basis,
        "source_relation_id": relation_id,
        "source_relation_year_end": int(source_relation_year_end if source_relation_year_end is not None else decision_year),
        "edge_age": int(edge_age),
        "edge_memory_mode": edge_memory_mode,
        "claim_status": "dynamic_graph_edge_exploratory_not_causal",
    }


def build_dynamic_graph_edges(
    nodes: pd.DataFrame | None = None,
    relation_signals: pd.DataFrame | None = None,
) -> pd.DataFrame:
    _assert_no_forbidden_paths()
    if nodes is None:
        nodes = build_dynamic_graph_nodes()
    if relation_signals is None:
        relation_signals = load_relation_signals()

    node_lookup = _valid_node_lookup(nodes)
    sector_codes = sorted(nodes["sector_code"].dropna().unique())
    rows: list[dict[str, object]] = []

    for row in relation_signals.itertuples(index=False):
        family = getattr(row, "relation_family")
        decision_year = int(getattr(row, "year_end"))
        strength = float(getattr(row, "signal_strength"))
        stability = float(getattr(row, "stability_score"))
        relation_id = str(getattr(row, "relation_id"))
        source_basis = str(getattr(row, "evidence_source"))

        if family == "intra_ze_sector_interaction":
            source_node_id = str(getattr(row, "source_id"))
            target_node_id = str(getattr(row, "target_id"))
            if (source_node_id, decision_year) in node_lookup and (target_node_id, decision_year) in node_lookup:
                rows.append(
                    _base_edge_row(
                        source_node_id=source_node_id,
                        target_node_id=target_node_id,
                        decision_year=decision_year,
                        edge_type="intra_ze_sector",
                        edge_weight=strength,
                        signal_strength=strength,
                        stability_score=stability,
                        source_basis=source_basis,
                        relation_id=relation_id,
                        source_relation_year_end=decision_year,
                        edge_age=0,
                        edge_memory_mode="instant",
                    )
                )

        elif family == "ze_to_ze_same_sector_signal":
            sector_code = str(getattr(row, "sector_code"))
            source_node_id = _node_id(str(getattr(row, "source_id")), sector_code)
            target_node_id = _node_id(str(getattr(row, "target_id")), sector_code)
            if (source_node_id, decision_year) in node_lookup and (target_node_id, decision_year) in node_lookup:
                rows.append(
                    _base_edge_row(
                        source_node_id=source_node_id,
                        target_node_id=target_node_id,
                        decision_year=decision_year,
                        edge_type="cross_ze_same_sector",
                        edge_weight=strength,
                        signal_strength=strength,
                        stability_score=stability,
                        source_basis=source_basis,
                        relation_id=relation_id,
                        source_relation_year_end=decision_year,
                        edge_age=0,
                        edge_memory_mode="instant",
                    )
                )

        elif family == "ze_to_ze_similarity":
            for sector_code in sector_codes:
                source_node_id = _node_id(str(getattr(row, "source_id")), sector_code)
                target_node_id = _node_id(str(getattr(row, "target_id")), sector_code)
                if (source_node_id, decision_year) not in node_lookup:
                    continue
                if (target_node_id, decision_year) not in node_lookup:
                    continue
                rows.append(
                    _base_edge_row(
                        source_node_id=source_node_id,
                        target_node_id=target_node_id,
                        decision_year=decision_year,
                        edge_type="ze_similarity",
                        edge_weight=strength,
                        signal_strength=strength,
                        stability_score=stability,
                        source_basis=source_basis,
                        relation_id=relation_id,
                        source_relation_year_end=decision_year,
                        edge_age=0,
                        edge_memory_mode="instant",
                    )
                )

        elif family == "ze_sector_specialization":
            # Specialization is a node attribute candidate, not an edge.
            continue

    if not rows:
        columns = [
            "edge_id",
            "source_node_id",
            "target_node_id",
            "decision_year",
            "edge_type",
            "edge_weight",
            "signal_strength",
            "stability_score",
            "source_basis",
            "source_relation_id",
            "claim_status",
        ]
        return pd.DataFrame(columns=columns)

    edges = pd.DataFrame(rows).drop_duplicates("edge_id")
    edges = edges[np.isfinite(edges["edge_weight"].astype(float))]
    edges = edges[edges["source_node_id"] != edges["target_node_id"]]
    columns = [
        "edge_id",
        "source_node_id",
        "target_node_id",
        "decision_year",
        "edge_type",
        "edge_weight",
        "signal_strength",
        "stability_score",
        "source_basis",
        "source_relation_id",
        "claim_status",
    ]
    return (
        edges[columns]
        .sort_values(["decision_year", "edge_type", "source_node_id", "target_node_id"])
        .reset_index(drop=True)
    )


def _memory_weight(signal_strength: float, stability_score: float, edge_age: int) -> float:
    return float(signal_strength) * float(stability_score) / float(1 + edge_age)


def build_dynamic_graph_edges_expanding(
    nodes: pd.DataFrame | None = None,
    relation_signals: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Build causal edge-memory snapshots.

    A relation observed with year_end=s can be used for every decision_year t >= s.
    The edge weight is damped by stability and recency:

        signal_strength * stability_score / (1 + t - s)

    This keeps historical signals available without pretending that a one-year spike is
    as reliable as a recurrent relation.
    """
    _assert_no_forbidden_paths()
    if nodes is None:
        nodes = build_dynamic_graph_nodes()
    if relation_signals is None:
        relation_signals = load_relation_signals()

    node_lookup = _valid_node_lookup(nodes)
    sector_codes = sorted(nodes["sector_code"].dropna().unique())
    years = sorted(nodes["decision_year"].astype(int).unique())
    rows: list[dict[str, object]] = []

    for row in relation_signals.itertuples(index=False):
        family = getattr(row, "relation_family")
        source_year = int(getattr(row, "year_end"))
        strength = float(getattr(row, "signal_strength"))
        stability = float(getattr(row, "stability_score"))
        relation_id = str(getattr(row, "relation_id"))
        source_basis = str(getattr(row, "evidence_source"))
        decision_years = [year for year in years if year >= source_year]

        for decision_year in decision_years:
            edge_age = decision_year - source_year
            edge_weight = _memory_weight(strength, stability, edge_age)

            if family == "intra_ze_sector_interaction":
                source_node_id = str(getattr(row, "source_id"))
                target_node_id = str(getattr(row, "target_id"))
                if (source_node_id, decision_year) in node_lookup and (target_node_id, decision_year) in node_lookup:
                    rows.append(
                        _base_edge_row(
                            source_node_id=source_node_id,
                            target_node_id=target_node_id,
                            decision_year=decision_year,
                            edge_type="intra_ze_sector",
                            edge_weight=edge_weight,
                            signal_strength=strength,
                            stability_score=stability,
                            source_basis=source_basis,
                            relation_id=relation_id,
                            source_relation_year_end=source_year,
                            edge_age=edge_age,
                            edge_memory_mode="expanding_stability_decay",
                        )
                    )

            elif family == "ze_to_ze_same_sector_signal":
                sector_code = str(getattr(row, "sector_code"))
                source_node_id = _node_id(str(getattr(row, "source_id")), sector_code)
                target_node_id = _node_id(str(getattr(row, "target_id")), sector_code)
                if (source_node_id, decision_year) in node_lookup and (target_node_id, decision_year) in node_lookup:
                    rows.append(
                        _base_edge_row(
                            source_node_id=source_node_id,
                            target_node_id=target_node_id,
                            decision_year=decision_year,
                            edge_type="cross_ze_same_sector",
                            edge_weight=edge_weight,
                            signal_strength=strength,
                            stability_score=stability,
                            source_basis=source_basis,
                            relation_id=relation_id,
                            source_relation_year_end=source_year,
                            edge_age=edge_age,
                            edge_memory_mode="expanding_stability_decay",
                        )
                    )

            elif family == "ze_to_ze_similarity":
                for sector_code in sector_codes:
                    source_node_id = _node_id(str(getattr(row, "source_id")), sector_code)
                    target_node_id = _node_id(str(getattr(row, "target_id")), sector_code)
                    if (source_node_id, decision_year) not in node_lookup:
                        continue
                    if (target_node_id, decision_year) not in node_lookup:
                        continue
                    rows.append(
                        _base_edge_row(
                            source_node_id=source_node_id,
                            target_node_id=target_node_id,
                            decision_year=decision_year,
                            edge_type="ze_similarity",
                            edge_weight=edge_weight,
                            signal_strength=strength,
                            stability_score=stability,
                            source_basis=source_basis,
                            relation_id=relation_id,
                            source_relation_year_end=source_year,
                            edge_age=edge_age,
                            edge_memory_mode="expanding_stability_decay",
                        )
                    )

            elif family == "ze_sector_specialization":
                continue

    if not rows:
        columns = [
            "edge_id",
            "source_node_id",
            "target_node_id",
            "decision_year",
            "edge_type",
            "edge_weight",
            "signal_strength",
            "stability_score",
            "source_basis",
            "source_relation_id",
            "source_relation_year_end",
            "edge_age",
            "edge_memory_mode",
            "claim_status",
        ]
        return pd.DataFrame(columns=columns)

    edges = pd.DataFrame(rows).drop_duplicates("edge_id")
    edges = edges[np.isfinite(edges["edge_weight"].astype(float))]
    edges = edges[edges["source_node_id"] != edges["target_node_id"]]
    return edges.sort_values(
        ["decision_year", "edge_type", "source_node_id", "target_node_id", "source_relation_year_end"]
    ).reset_index(drop=True)


def build_dynamic_graph_splits(nodes: pd.DataFrame | None = None) -> pd.DataFrame:
    if nodes is None:
        nodes = build_dynamic_graph_nodes()
    years = sorted(nodes["decision_year"].unique())
    rows = []
    for year in years:
        if year <= 2018:
            split = "warmup_or_train"
        elif year <= 2022:
            split = "rolling_eval_3y"
        elif year <= 2024:
            split = "rolling_eval_1y"
        else:
            split = "label_incomplete_holdout"
        rows.append(
            {
                "decision_year": int(year),
                "split_role": split,
                "node_count": int((nodes["decision_year"] == year).sum()),
                "claim_status": "dynamic_graph_split_exploratory_not_recommendation",
            }
        )
    return pd.DataFrame(rows)


def build_dynamic_graph_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    nodes = build_dynamic_graph_nodes()
    edges = build_dynamic_graph_edges(nodes=nodes)
    expanding_edges = build_dynamic_graph_edges_expanding(nodes=nodes)
    splits = build_dynamic_graph_splits(nodes=nodes)
    return nodes, edges, expanding_edges, splits


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    nodes, edges, expanding_edges, splits = build_dynamic_graph_inputs()
    nodes.to_csv(NODES_OUT_PATH, index=False)
    edges.to_csv(EDGES_OUT_PATH, index=False)
    expanding_edges.to_csv(EXPANDING_EDGES_OUT_PATH, index=False)
    splits.to_csv(SPLITS_OUT_PATH, index=False)
    print(f"Nodes: {len(nodes)} -> {NODES_OUT_PATH}")
    print(f"Edges: {len(edges)} -> {EDGES_OUT_PATH}")
    print(f"Expanding edges: {len(expanding_edges)} -> {EXPANDING_EDGES_OUT_PATH}")
    print(f"Splits: {len(splits)} -> {SPLITS_OUT_PATH}")
    print(f"Years: {nodes['decision_year'].min()}-{nodes['decision_year'].max()}")
    print(f"Edge types: {', '.join(sorted(edges['edge_type'].unique())) if len(edges) else 'none'}")


if __name__ == "__main__":
    main()
