from pathlib import Path

import numpy as np
import pandas as pd

from src.modeles.france_ze2020.run_fr_ze2020_relation_embedding_linear_probes import (
    BASE_FEATURE_COLUMNS,
    CLAIM_STATUS,
    VIEW_NAMES,
    build_probe_views,
    past_only_snapshot_placebo,
    random_endpoint_placebo,
    run_linear_probes,
)
from src.modeles.france_ze2020.train_fr_ze2020_dynamic_relation_encoder import (
    build_dense_graph_signal_embeddings,
)

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "src/modeles/france_ze2020/run_fr_ze2020_relation_embedding_linear_probes.py"


def _sample() -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    years = range(2015, 2022)
    for zone_idx, zone in enumerate(["0001", "0002", "0003"]):
        for sector_idx, sector in enumerate(["BE", "GI"]):
            for year in years:
                trend = year - 2015
                share = 0.10 + 0.01 * zone_idx + 0.02 * sector_idx + 0.003 * trend
                row = {
                    "node_id": f"{zone}_{sector}",
                    "ze2020": zone,
                    "ze2020_label": zone,
                    "sector_code": sector,
                    "sector_label": sector,
                    "decision_year": year,
                    "sector_count_t": 100 + 7 * zone_idx + 5 * sector_idx + 2 * trend,
                    "sector_share_t": share,
                    "sector_rank_in_ze_year_t": sector_idx + 1,
                    "sector_share_lag_1": share - 0.003,
                    "sector_growth_lag_1": 0.01 + 0.001 * zone_idx,
                    "sector_growth_lag_2": 0.008 + 0.001 * sector_idx,
                    "dominant_sector_flag_t": int(sector_idx == 0),
                    "dominant_sector_share_lag_1": 0.45 + 0.001 * trend,
                    "sector_diversity_lag_1": 0.75 + 0.002 * zone_idx,
                    "sector_concentration_hhi_lag_1": 0.20 + 0.003 * sector_idx,
                    "national_sector_share_lag_1": 0.12 + 0.002 * sector_idx,
                    "national_sector_growth_lag_1": 0.015 + 0.001 * trend,
                }
                rows.append(row)
    nodes = pd.DataFrame(rows)

    edge_rows = []
    for year in years:
        for sector in ["BE", "GI"]:
            for source, target in [("0001", "0002"), ("0002", "0003"), ("0003", "0001")]:
                edge_rows.append(
                    {
                        "source_node_id": f"{source}_{sector}",
                        "target_node_id": f"{target}_{sector}",
                        "decision_year": year,
                        "edge_type": "cross_ze_same_sector",
                        "edge_weight": 0.4 + 0.01 * (year - 2015),
                        "signal_strength": 0.5,
                        "stability_score": 0.7,
                    }
                )
    return nodes, pd.DataFrame(edge_rows)


def test_past_snapshot_placebo_never_copies_current_or_future_snapshot():
    nodes, edges = _sample()
    embeddings = build_dense_graph_signal_embeddings(nodes, edges)
    shuffled = past_only_snapshot_placebo(embeddings, seed=42)
    graph_cols = [col for col in shuffled if col.startswith("relation_graph_") and col != "relation_graph_embedding_available"]
    node_id = "0001_BE"
    original = embeddings[embeddings["node_id"] == node_id].sort_values("decision_year")
    changed = shuffled[shuffled["node_id"] == node_id].sort_values("decision_year")
    assert np.allclose(changed.iloc[0][graph_cols].to_numpy(dtype=float), 0.0)
    for position in range(1, len(changed)):
        prior = original.iloc[:position][graph_cols].to_numpy(dtype=float)
        value = changed.iloc[position][graph_cols].to_numpy(dtype=float)
        assert any(np.allclose(value, candidate) for candidate in prior)


def test_build_probe_views_returns_only_declared_controls():
    nodes, edges = _sample()
    views = build_probe_views(nodes, edges, seed=42)
    assert list(views) == VIEW_NAMES
    assert all(len(frame) == len(nodes) for frame in views.values())
    assert not any(col.startswith("relation_graph_") for col in views["node_only"])
    assert any(col.startswith("relation_graph_") for col in views["real_graph"])


def test_random_endpoint_placebo_changes_both_endpoint_assignments():
    _, edges = _sample()
    shuffled = random_endpoint_placebo(edges, seed=42)
    original = edges.loc[shuffled.index]
    assert not shuffled["source_node_id"].equals(original["source_node_id"])
    assert not shuffled["target_node_id"].equals(original["target_node_id"])
    assert not (shuffled["source_node_id"] == shuffled["target_node_id"]).any()


def test_linear_probe_smoke_produces_both_tasks_and_finite_primary_metrics():
    nodes, edges = _sample()
    metrics, summary = run_linear_probes(
        nodes,
        edges,
        eval_years=[2019, 2020, 2021],
        seeds=[42],
    )
    assert set(metrics["probe"]) == {"temporal_successor", "next_sector_share"}
    assert set(metrics["view"]) == set(VIEW_NAMES)
    assert set(metrics["claim_status"]) == {CLAIM_STATUS}
    successor = metrics[metrics["probe"] == "temporal_successor"]
    next_state = metrics[metrics["probe"] == "next_sector_share"]
    assert np.isfinite(successor[["roc_auc", "average_precision"]].to_numpy()).all()
    assert np.isfinite(next_state[["mae", "r2"]].to_numpy()).all()
    assert set(summary["view"]) == set(VIEW_NAMES)


def test_probe_uses_canonical_feature_names_and_has_no_forbidden_claim_columns():
    source = SCRIPT.read_text()
    assert all(column in source for column in BASE_FEATURE_COLUMNS)
    for term in ["recommended_action", "policy_action", "causal_effect", "causal_impact"]:
        assert term not in source
