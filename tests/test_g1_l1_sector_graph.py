from __future__ import annotations

import numpy as np
import pandas as pd

from src.data.european_panel.build_g1_l1_sector_graph import (
    configuration_null,
    proximity_matrix,
    rca_matrix,
)


def test_proximity_is_symmetric_and_bounded() -> None:
    specialized = np.array(
        [
            [1, 1, 0],
            [1, 1, 1],
            [0, 1, 1],
        ],
        dtype=bool,
    )
    proximity = proximity_matrix(specialized)
    assert np.allclose(proximity, proximity.T)
    assert np.all((proximity >= 0) & (proximity <= 1))
    assert np.allclose(np.diag(proximity), 1)


def test_product_space_minimum_conditional_probability() -> None:
    specialized = np.array(
        [
            [1, 1],
            [1, 0],
            [0, 1],
            [0, 1],
        ],
        dtype=bool,
    )
    proximity = proximity_matrix(specialized)
    assert proximity[0, 1] == 1 / 3


def test_rca_detects_relative_specialization() -> None:
    frame = pd.DataFrame(
        {
            "region_id": ["A", "A", "B", "B"],
            "sector_a10": ["BE", "FZ", "BE", "FZ"],
            "sector_births": [80.0, 20.0, 20.0, 80.0],
        }
    )
    rca = rca_matrix(frame)
    assert rca.loc["A", "BE"] > 1
    assert rca.loc["A", "FZ"] < 1
    assert rca.loc["B", "FZ"] > 1


def test_configuration_null_preserves_sector_prevalence() -> None:
    tensor = np.array(
        [
            [[1, 0], [1, 1], [0, 1]],
            [[0, 1], [1, 0], [1, 1]],
        ],
        dtype=bool,
    )
    permuted = configuration_null(tensor, np.random.default_rng(7))
    assert np.array_equal(tensor.sum(axis=1), permuted.sum(axis=1))
