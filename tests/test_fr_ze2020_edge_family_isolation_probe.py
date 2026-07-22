import pandas as pd

from src.modeles.france_ze2020.run_fr_ze2020_edge_family_isolation_probe import (
    prefix_family_embedding,
)


def test_prefix_family_embedding_creates_collision_free_block() -> None:
    embedding = pd.DataFrame(
        {
            "node_id": ["0051_BE"],
            "decision_year": [2020],
            "relation_graph_in_count": [2.0],
            "relation_graph_out_signal_mean": [0.4],
            "relation_graph_embedding_available": [1],
        }
    )
    block = prefix_family_embedding(embedding, "cross_ze_same_sector")
    assert list(block.columns) == [
        "node_id",
        "decision_year",
        "relation_graph_cross_ze_same_sector__in_count",
        "relation_graph_cross_ze_same_sector__out_signal_mean",
    ]
    assert block.iloc[0]["relation_graph_cross_ze_same_sector__in_count"] == 2.0
