"""Tests for causal graph-temporal rolling-origin training."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from src.modeles.graph_temporal_train import (
    TrainConfig,
    TrainingContractError,
    causal_split,
    load_fold_batch,
    train_rolling_origin,
)


def _write_fold(root: Path, year: int, *, target_shift: float = 0.0) -> None:
    rng = np.random.default_rng(year)
    t, r, s, f = 5, 6, 3, 3
    features = rng.normal(size=(t, r, s, f)).astype(np.float32)
    feature_mask = np.ones_like(features, dtype=np.int8)
    struct_mask = np.ones((r, s), dtype=np.int8)
    adjacency = np.zeros((t, s, r, r), dtype=np.float32)
    for ti in range(t):
        for si in range(s):
            adjacency[ti, si] = np.eye(r, k=1) + np.eye(r, k=-1)
            adjacency[ti, si] = np.maximum(adjacency[ti, si], adjacency[ti, si].T)
    ridge = np.full(r, 100.0 + year % 5, dtype=np.float32)
    y_true = ridge + target_shift + rng.normal(scale=2.0, size=r).astype(np.float32)
    target_mask = np.ones(r, dtype=np.int8)

    out = root / "XX" / str(year)
    out.mkdir(parents=True)
    np.savez_compressed(
        out / "fold_v2.npz",
        features_seq=features,
        feature_mask_seq=feature_mask,
        struct_mask=struct_mask,
        adjacency_seq=adjacency,
        observation_years=np.arange(year - t, year, dtype=np.int32),
        y_true=y_true,
        y_ridge_canonical=ridge,
        residual=y_true - ridge,
        target_mask=target_mask,
        eval_year=np.array([year], dtype=np.int32),
    )


@pytest.fixture()
def fold_root(tmp_path: Path) -> Path:
    for year in [2019, 2020, 2021, 2022]:
        _write_fold(tmp_path, year)
    return tmp_path


def test_causal_split_reserves_latest_prior_fold():
    train, validation = causal_split([2019, 2020, 2021, 2022], 2022)
    assert train == [2019, 2020]
    assert validation == 2021


def test_causal_split_fails_with_insufficient_history():
    with pytest.raises(TrainingContractError):
        causal_split([2021, 2022], 2022)


def test_load_fold_rejects_future_observation(tmp_path: Path):
    _write_fold(tmp_path, 2022)
    path = tmp_path / "XX" / "2022" / "fold_v2.npz"
    with np.load(path) as data:
        payload = {name: data[name] for name in data.files}
    payload["observation_years"][-1] = 2022
    np.savez_compressed(path, **payload)
    with pytest.raises(TrainingContractError):
        load_fold_batch("XX", 2022, tmp_path)


@pytest.mark.parametrize("model_name", ["A0Neural", "GConvGRU", "EvolveGCNH"])
def test_training_is_finite_causal_and_within_budget(fold_root: Path, model_name: str):
    config = TrainConfig(max_epochs=4, patience=2, hidden_dim=4, seed=42)
    _, result = train_rolling_origin(
        model_name, "XX", 2022, config=config, folds_dir=fold_root
    )
    assert np.isfinite(result.evaluation_wmape)
    assert np.isfinite(result.ridge_wmape)
    assert result.train_years == (2019, 2020)
    assert result.validation_year == 2021
    assert result.n_parameters <= 5000
    assert result.leakage_ok


def test_eval_target_does_not_change_trained_state(fold_root: Path):
    config = TrainConfig(max_epochs=5, patience=2, hidden_dim=4, seed=43)
    _, first = train_rolling_origin(
        "GConvGRU", "XX", 2022, config=config, folds_dir=fold_root
    )

    eval_path = fold_root / "XX" / "2022" / "fold_v2.npz"
    with np.load(eval_path) as data:
        payload = {name: data[name] for name in data.files}
    payload["y_true"] = payload["y_true"] + 10000.0
    payload["residual"] = payload["y_true"] - payload["y_ridge_canonical"]
    np.savez_compressed(eval_path, **payload)

    _, second = train_rolling_origin(
        "GConvGRU", "XX", 2022, config=config, folds_dir=fold_root
    )
    assert first.state_checksum == second.state_checksum
    assert first.evaluation_wmape != second.evaluation_wmape


def test_same_seed_is_deterministic(fold_root: Path):
    config = TrainConfig(max_epochs=5, patience=2, hidden_dim=4, seed=44)
    _, first = train_rolling_origin(
        "A0Neural", "XX", 2022, config=config, folds_dir=fold_root
    )
    _, second = train_rolling_origin(
        "A0Neural", "XX", 2022, config=config, folds_dir=fold_root
    )
    assert first.state_checksum == second.state_checksum
    assert first.evaluation_wmape == second.evaluation_wmape

