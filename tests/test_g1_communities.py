from __future__ import annotations

import networkx as nx
import numpy as np
import pandas as pd

from src.data.european_panel.build_g1_communities import (
    add_fdr_and_gate,
    aggregate_cogrowth_graph,
    louvain_best,
    partition_ami,
    symmetric_top_k,
)
from src.data.european_panel.build_g1_l2_cogrowth import (
    build_growth_matrix,
    permute_growth_territory,
)


def make_panel() -> pd.DataFrame:
    rows = []
    patterns = {
        "R1": [0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07],
        "R2": [0.02, 0.04, 0.06, 0.08, 0.10, 0.12, 0.14],
        "R3": [0.07, 0.06, 0.05, 0.04, 0.03, 0.02, 0.01],
        "R4": [0.14, 0.12, 0.10, 0.08, 0.06, 0.04, 0.02],
    }
    for sector in ("BE", "FZ"):
        for region, values in patterns.items():
            for year, value in zip(range(2015, 2022), values):
                rows.append(
                    {
                        "country": "XX",
                        "region_id": region,
                        "sector_a10": sector,
                        "observation_year": year,
                        "sector_growth_1y": value,
                        "mask_sector_supported": 1,
                    }
                )
    return pd.DataFrame(rows)


def sector_data() -> dict:
    panel = make_panel()
    return {
        sector: build_growth_matrix(panel, "XX", sector)
        for sector in ("BE", "FZ")
    }


def test_symmetric_top_k_has_no_self_loops_and_keeps_all_nodes() -> None:
    weights = np.array(
        [
            [np.nan, 0.9, 0.1, -0.2],
            [0.9, np.nan, 0.8, 0.2],
            [0.1, 0.8, np.nan, 0.7],
            [-0.2, 0.2, 0.7, np.nan],
        ]
    )
    graph = symmetric_top_k(weights, ["A", "B", "C", "D"], top_k=1)
    assert set(graph.nodes()) == {"A", "B", "C", "D"}
    assert nx.number_of_selfloops(graph) == 0
    assert graph.number_of_edges() <= 4


def test_aggregate_graph_is_sparse() -> None:
    graph = aggregate_cogrowth_graph(
        sector_data(),
        ["BE", "FZ"],
        eval_year=2021,
        top_k=1,
    )
    assert graph.number_of_nodes() == 4
    assert graph.number_of_edges() < 6


def test_covid_exclusion_changes_only_window_data() -> None:
    full = aggregate_cogrowth_graph(
        sector_data(),
        ["BE", "FZ"],
        eval_year=2020,
    )
    excluded = aggregate_cogrowth_graph(
        sector_data(),
        ["BE", "FZ"],
        eval_year=2020,
        exclude_years=frozenset({2020}),
    )
    assert nx.utils.graphs_equal(full, excluded)


def test_territory_null_rebuilds_data_not_only_labels() -> None:
    data = sector_data()
    original = aggregate_cogrowth_graph(data, ["BE", "FZ"], 2021, top_k=1)
    permuted_data = permute_growth_territory(
        data,
        np.random.default_rng(9),
    )
    permuted = aggregate_cogrowth_graph(
        permuted_data,
        ["BE", "FZ"],
        2021,
        top_k=1,
    )
    original_weights = sorted(
        round(edge_data["weight"], 8)
        for _, _, edge_data in original.edges(data=True)
    )
    permuted_weights = sorted(
        round(edge_data["weight"], 8)
        for _, _, edge_data in permuted.edges(data=True)
    )
    assert original_weights != permuted_weights


def test_louvain_finds_disconnected_clusters() -> None:
    graph = nx.Graph()
    graph.add_weighted_edges_from(
        [
            ("A", "B", 1.0),
            ("A", "C", 1.0),
            ("B", "C", 1.0),
            ("X", "Y", 1.0),
            ("X", "Z", 1.0),
            ("Y", "Z", 1.0),
        ]
    )
    partition, modularity = louvain_best(graph, restarts=3)
    assert partition is not None
    assert len(partition) == 2
    assert modularity > 0


def test_partition_ami_identical_is_one() -> None:
    partition = [{"A", "B"}, {"C", "D"}]
    assert partition_ami(partition, partition, ["A", "B", "C", "D"]) == 1.0


def test_gate_is_fail_closed_when_one_q_fails() -> None:
    row = {
        "mean_modularity": 0.2,
        "mean_ami_consecutive": 0.3,
        "modularity_temporal_p": 0.01,
        "modularity_territory_p": 0.01,
        "ami_temporal_p": 0.01,
        "ami_territory_p": 0.8,
    }
    result = add_fdr_and_gate([row], "country_pass")
    assert result[0]["country_pass"] is False


def test_gate_passes_only_all_four_families() -> None:
    row = {
        "mean_modularity": 0.2,
        "mean_ami_consecutive": 0.3,
        "modularity_temporal_p": 0.01,
        "modularity_territory_p": 0.01,
        "ami_temporal_p": 0.01,
        "ami_territory_p": 0.01,
    }
    result = add_fdr_and_gate([row], "country_pass")
    assert result[0]["country_pass"] is True
