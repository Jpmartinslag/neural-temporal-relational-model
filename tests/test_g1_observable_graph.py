from __future__ import annotations

import numpy as np

from src.data.european_panel.build_g1_observable_graph import (
    bh_fdr,
    cosine_similarity,
    empirical_p,
    leave_one_year_mean,
    top_k_edges,
)


def test_cosine_similarity_identity_and_symmetry() -> None:
    matrix = np.eye(3)
    similarity = cosine_similarity(matrix)
    assert np.allclose(similarity, np.eye(3))
    assert np.allclose(similarity, similarity.T)


def test_top_k_edges_has_no_self_edges() -> None:
    matrix = np.array(
        [
            [1.0, 0.9, 0.2],
            [0.9, 1.0, 0.3],
            [0.2, 0.3, 1.0],
        ]
    )
    edges = top_k_edges(matrix, ["A", "B", "C"], k=1)
    assert all(source != target for source, target in edges)
    assert ("A", "B") in edges


def test_empirical_p_never_zero() -> None:
    assert empirical_p(10.0, [0.0, 1.0, 2.0]) == 0.25


def test_bh_fdr_is_monotone_in_ranked_order() -> None:
    adjusted = bh_fdr([0.01, 0.04, 0.03])
    assert all(0.0 <= value <= 1.0 for value in adjusted)
    ranked = sorted(zip([0.01, 0.04, 0.03], adjusted))
    assert ranked[0][1] <= ranked[1][1] <= ranked[2][1]


def test_leave_one_year_does_not_bridge_gap() -> None:
    pair_values = [0.1, 0.2, 0.9, 0.4]
    assert leave_one_year_mean(pair_values, omitted_year_index=2) == 0.25
