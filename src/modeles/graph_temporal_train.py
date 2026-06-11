"""Causal rolling-origin training for HERALD graph-temporal models.

For an evaluation year ``t``:
- folds with year < t are eligible for training;
- the latest eligible fold is reserved for causal validation;
- the evaluation fold t is never used by the optimizer or early stopping.

The module intentionally contains no S1 orchestration or graph-null rebuilding.
Those belong to the later experiment runner.
"""
from __future__ import annotations

import copy
import hashlib
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import torch
from torch import nn

from src.modeles.graph_temporal_models import (
    A0Neural,
    build_model,
    count_parameters,
    masked_wmape,
)


DEFAULT_FOLDS_DIR = Path("data/processed/graph_temporal_v2")


class TrainingContractError(RuntimeError):
    """Raised when a fold or training split violates the causal contract."""


@dataclass(frozen=True)
class TrainConfig:
    learning_rate: float = 1e-3
    weight_decay: float = 1e-4
    max_epochs: int = 200
    patience: int = 20
    min_delta: float = 1e-5
    grad_clip_norm: float = 1.0
    hidden_dim: int = 4
    sector_embed_dim: int = 4
    dropout: float = 0.3
    clamp_frac: float = 0.15
    seed: int = 42
    device: str = "cpu"

    def validate(self) -> None:
        if self.learning_rate <= 0:
            raise ValueError("learning_rate must be positive")
        if self.max_epochs < 1 or self.patience < 1:
            raise ValueError("max_epochs and patience must be positive")
        if self.hidden_dim not in {4, 8}:
            raise ValueError("hidden_dim must be 4 or 8")
        if self.sector_embed_dim not in {4, 8}:
            raise ValueError("sector_embed_dim must be 4 or 8")
        if self.dropout < 0.3:
            raise ValueError("dropout must be >= 0.3")
        if self.clamp_frac not in {0.10, 0.15}:
            raise ValueError("clamp_frac must be 0.10 or 0.15")


@dataclass
class FoldBatch:
    country: str
    eval_year: int
    observation_years: np.ndarray
    features_seq: torch.Tensor
    feature_mask_seq: torch.Tensor
    struct_mask: torch.Tensor
    adjacency_seq: torch.Tensor
    y_true: torch.Tensor
    y_ridge_canonical: torch.Tensor
    target_mask: torch.Tensor


@dataclass(frozen=True)
class TrainingResult:
    model_name: str
    country: str
    eval_year: int
    seed: int
    train_years: tuple[int, ...]
    validation_year: int
    best_epoch: int
    epochs_ran: int
    best_validation_wmape: float
    evaluation_wmape: float
    ridge_wmape: float
    n_parameters: int
    n_train_targets: int
    n_validation_targets: int
    n_evaluation_targets: int
    state_checksum: str
    leakage_ok: bool

    def to_dict(self) -> dict:
        return asdict(self)


def set_deterministic_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.use_deterministic_algorithms(True, warn_only=True)


def available_fold_years(country: str, folds_dir: Path = DEFAULT_FOLDS_DIR) -> list[int]:
    country_dir = Path(folds_dir) / country
    if not country_dir.exists():
        raise FileNotFoundError(f"Country fold directory not found: {country_dir}")
    years = sorted(
        int(p.name)
        for p in country_dir.iterdir()
        if p.is_dir() and p.name.isdigit() and (p / "fold_v2.npz").exists()
    )
    if not years:
        raise FileNotFoundError(f"No schema 2.0 folds found under {country_dir}")
    return years


def causal_split(
    available_years: Iterable[int],
    eval_year: int,
) -> tuple[list[int], int]:
    """Return fit years and the latest prior year used for validation."""
    prior = sorted({int(y) for y in available_years if int(y) < int(eval_year)})
    if len(prior) < 2:
        raise TrainingContractError(
            f"Need at least two prior folds before {eval_year}; found {prior}"
        )
    return prior[:-1], prior[-1]


def _as_batch(array: np.ndarray, *, dtype: torch.dtype, device: torch.device) -> torch.Tensor:
    return torch.as_tensor(array, dtype=dtype, device=device).unsqueeze(0)


def load_fold_batch(
    country: str,
    eval_year: int,
    folds_dir: Path = DEFAULT_FOLDS_DIR,
    device: str | torch.device = "cpu",
) -> FoldBatch:
    path = Path(folds_dir) / country / str(eval_year) / "fold_v2.npz"
    if not path.exists():
        raise FileNotFoundError(f"Fold not found: {path}")

    with np.load(path, allow_pickle=False) as data:
        required = {
            "features_seq", "feature_mask_seq", "struct_mask", "adjacency_seq",
            "observation_years", "y_true", "y_ridge_canonical", "target_mask",
            "eval_year",
        }
        missing = required.difference(data.files)
        if missing:
            raise TrainingContractError(f"{path}: missing arrays {sorted(missing)}")

        stored_year = int(data["eval_year"][0])
        observation_years = np.asarray(data["observation_years"], dtype=np.int64)
        if stored_year != int(eval_year):
            raise TrainingContractError(
                f"{path}: stored eval_year={stored_year}, expected {eval_year}"
            )
        if observation_years.size == 0 or np.any(observation_years >= eval_year):
            raise TrainingContractError(
                f"{path}: non-causal observation years {observation_years.tolist()}"
            )
        if np.any(np.diff(observation_years) <= 0):
            raise TrainingContractError(f"{path}: observation years are not increasing")

        features = np.asarray(data["features_seq"])
        feature_mask = np.asarray(data["feature_mask_seq"])
        struct_mask = np.asarray(data["struct_mask"])
        adjacency = np.asarray(data["adjacency_seq"])
        y_true = np.asarray(data["y_true"])
        y_ridge = np.asarray(data["y_ridge_canonical"])
        target_mask = np.asarray(data["target_mask"])

    if features.ndim != 4:
        raise TrainingContractError(f"{path}: features_seq must be (T,R,S,F)")
    t, r, s, _ = features.shape
    expected = {
        "feature_mask_seq": (t, r, s, features.shape[-1]),
        "struct_mask": (r, s),
        "adjacency_seq": (t, s, r, r),
        "y_true": (r,),
        "y_ridge_canonical": (r,),
        "target_mask": (r,),
    }
    actual = {
        "feature_mask_seq": feature_mask.shape,
        "struct_mask": struct_mask.shape,
        "adjacency_seq": adjacency.shape,
        "y_true": y_true.shape,
        "y_ridge_canonical": y_ridge.shape,
        "target_mask": target_mask.shape,
    }
    bad = {name: (actual[name], shape) for name, shape in expected.items() if actual[name] != shape}
    if bad:
        raise TrainingContractError(f"{path}: incompatible shapes {bad}")

    valid_feature = feature_mask.astype(bool)
    if not np.isfinite(features[valid_feature]).all():
        raise TrainingContractError(f"{path}: non-finite value marked as observed")
    if np.any(adjacency < 0) or not np.isfinite(adjacency).all():
        raise TrainingContractError(f"{path}: adjacency must be finite and non-negative")
    if not np.allclose(adjacency, adjacency.swapaxes(-1, -2), atol=1e-6):
        raise TrainingContractError(f"{path}: adjacency is not symmetric")

    dev = torch.device(device)
    return FoldBatch(
        country=country,
        eval_year=eval_year,
        observation_years=observation_years,
        features_seq=_as_batch(features, dtype=torch.float32, device=dev),
        feature_mask_seq=_as_batch(feature_mask, dtype=torch.bool, device=dev),
        struct_mask=_as_batch(struct_mask, dtype=torch.bool, device=dev),
        adjacency_seq=_as_batch(adjacency, dtype=torch.float32, device=dev),
        y_true=_as_batch(y_true, dtype=torch.float32, device=dev),
        y_ridge_canonical=_as_batch(y_ridge, dtype=torch.float32, device=dev),
        target_mask=_as_batch(target_mask, dtype=torch.bool, device=dev),
    )


def _forward(model: nn.Module, fold: FoldBatch) -> dict[str, torch.Tensor]:
    args = (
        fold.features_seq,
        fold.feature_mask_seq,
        fold.struct_mask,
        fold.y_ridge_canonical,
    )
    if isinstance(model, A0Neural):
        return model(*args)
    return model(*args, adjacency_seq=fold.adjacency_seq)


def _fold_loss(model: nn.Module, fold: FoldBatch) -> torch.Tensor:
    out = _forward(model, fold)
    loss = masked_wmape(out["y_hat"], fold.y_true, fold.target_mask)
    if not torch.isfinite(loss):
        raise TrainingContractError(
            f"{fold.country}/{fold.eval_year}: non-finite masked WMAPE"
        )
    return loss


def _target_count(fold: FoldBatch) -> int:
    valid = (
        fold.target_mask.bool()
        & torch.isfinite(fold.y_true)
        & torch.isfinite(fold.y_ridge_canonical)
    )
    return int(valid.sum().item())


def state_checksum(model: nn.Module) -> str:
    digest = hashlib.sha256()
    for name, tensor in sorted(model.state_dict().items()):
        digest.update(name.encode("utf-8"))
        digest.update(tensor.detach().cpu().contiguous().numpy().tobytes())
    return digest.hexdigest()


def train_rolling_origin(
    model_name: str,
    country: str,
    eval_year: int,
    *,
    config: TrainConfig = TrainConfig(),
    folds_dir: Path = DEFAULT_FOLDS_DIR,
) -> tuple[nn.Module, TrainingResult]:
    """Train one model causally and evaluate once on ``eval_year``."""
    config.validate()
    set_deterministic_seed(config.seed)
    device = torch.device(config.device)

    years = available_fold_years(country, folds_dir)
    if eval_year not in years:
        raise TrainingContractError(
            f"Evaluation fold {country}/{eval_year} is not available"
        )
    train_years, validation_year = causal_split(years, eval_year)
    if max(train_years) >= validation_year or validation_year >= eval_year:
        raise TrainingContractError("Non-causal train/validation/evaluation ordering")

    train_folds = [
        load_fold_batch(country, year, folds_dir, device) for year in train_years
    ]
    validation_fold = load_fold_batch(country, validation_year, folds_dir, device)
    evaluation_fold = load_fold_batch(country, eval_year, folds_dir, device)

    sample = evaluation_fold.features_seq
    n_sectors = sample.shape[3]
    n_features = sample.shape[4]
    model = build_model(
        model_name,
        n_sectors=n_sectors,
        n_features=n_features,
        hidden_dim=config.hidden_dim,
        sector_embed_dim=config.sector_embed_dim,
        dropout=config.dropout,
        clamp_frac=config.clamp_frac,
    ).to(device)
    n_parameters = count_parameters(model)
    if n_parameters > 5000:
        raise TrainingContractError(f"Too many trainable parameters: {n_parameters}")

    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=config.learning_rate,
        weight_decay=config.weight_decay,
    )

    best_state = copy.deepcopy(model.state_dict())
    best_validation = float("inf")
    best_epoch = 0
    epochs_without_improvement = 0
    epochs_ran = 0

    for epoch in range(1, config.max_epochs + 1):
        model.train()
        optimizer.zero_grad(set_to_none=True)
        train_losses = [_fold_loss(model, fold) for fold in train_folds]
        train_loss = torch.stack(train_losses).mean()
        train_loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), config.grad_clip_norm)
        optimizer.step()

        model.eval()
        with torch.no_grad():
            validation_loss = float(_fold_loss(model, validation_fold).item())
        epochs_ran = epoch

        if validation_loss < best_validation - config.min_delta:
            best_validation = validation_loss
            best_epoch = epoch
            best_state = copy.deepcopy(model.state_dict())
            epochs_without_improvement = 0
        else:
            epochs_without_improvement += 1
            if epochs_without_improvement >= config.patience:
                break

    model.load_state_dict(best_state)
    model.eval()
    with torch.no_grad():
        evaluation_wmape = float(_fold_loss(model, evaluation_fold).item())
        ridge_wmape = float(
            masked_wmape(
                evaluation_fold.y_ridge_canonical,
                evaluation_fold.y_true,
                evaluation_fold.target_mask,
            ).item()
        )

    result = TrainingResult(
        model_name=model_name,
        country=country,
        eval_year=eval_year,
        seed=config.seed,
        train_years=tuple(train_years),
        validation_year=validation_year,
        best_epoch=best_epoch,
        epochs_ran=epochs_ran,
        best_validation_wmape=best_validation,
        evaluation_wmape=evaluation_wmape,
        ridge_wmape=ridge_wmape,
        n_parameters=n_parameters,
        n_train_targets=sum(_target_count(fold) for fold in train_folds),
        n_validation_targets=_target_count(validation_fold),
        n_evaluation_targets=_target_count(evaluation_fold),
        state_checksum=state_checksum(model),
        leakage_ok=bool(
            all(fold.observation_years.max() < fold.eval_year for fold in train_folds)
            and validation_fold.observation_years.max() < validation_year
            and evaluation_fold.observation_years.max() < eval_year
            and max(train_years) < validation_year < eval_year
        ),
    )
    return model, result

