"""Build causal France-NUTS3 tensors for the HERALD dual-graph experiment."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.data.european_panel.audit_dual_graph_targets import (
    LeakageError,
    classify_recovery,
    classify_regime,
    compute_emergence,
    compute_fold_thresholds,
    compute_log_growth,
    get_feature_rows,
    get_target_rows,
)
from src.data.european_panel.build_graph_temporal_v2 import build_adjacency_seq
from src.modeles.run_ardeco_ridge_fr import prepare_ardeco


BASE = Path(__file__).resolve().parents[3]
DEFAULT_PANEL = BASE / "data/processed/economic_graph/sector_panel_fr_nuts3.csv"
DEFAULT_ARDECO = BASE / "data/raw/european_panel/ardeco/snetz/ardeco_snetz_combined.csv"
DEFAULT_OUT = BASE / "data/processed/dual_graph_tensors"
EVAL_YEARS = [2021, 2022, 2023, 2024, 2025]
T_SEQ = 5
FEATURE_NAMES = (
    "sector_growth_1y",
    "sector_share",
    "log_sector_births",
    "log_employment",
    "employment_growth",
    "employment_share",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _ardeco_long(raw: pd.DataFrame) -> pd.DataFrame:
    wide = prepare_ardeco(raw)
    rows = []
    for sector in sorted({
        column.removeprefix("emp_")
        for column in wide.columns
        if column.startswith("emp_") and not column.startswith("emp_growth_")
    }):
        rows.append(pd.DataFrame({
            "region_id": wide["region_id"].astype(str),
            "observation_year": wide["source_year"].astype(int),
            "sector_a10": sector,
            "log_employment": wide[f"log_emp_{sector}"],
            "employment_growth": wide[f"growth_emp_{sector}"],
            "employment_share": wide[f"share_emp_{sector}"],
        }))
    return pd.concat(rows, ignore_index=True)


def _fit_scale(raw: np.ndarray, mask: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    scaled = np.zeros_like(raw, dtype=np.float32)
    means = np.zeros(raw.shape[-1], dtype=np.float32)
    stds = np.ones(raw.shape[-1], dtype=np.float32)
    for feature in range(raw.shape[-1]):
        valid = mask[..., feature].astype(bool) & np.isfinite(raw[..., feature])
        values = raw[..., feature][valid]
        if values.size:
            means[feature] = float(values.mean())
            std = float(values.std())
            stds[feature] = std if std > 1e-8 else 1.0
            scaled[..., feature][valid] = (
                raw[..., feature][valid] - means[feature]
            ) / stds[feature]
    return scaled, means, stds


def _build_sample(
    panel: pd.DataFrame,
    ardeco_long: pd.DataFrame,
    eval_year: int,
) -> dict[str, np.ndarray]:
    panel = panel.copy()
    panel["region_id"] = panel["region_id"].astype(str)
    regions = sorted(panel["region_id"].unique())
    sectors = sorted(panel["sector_a10"].unique())
    observation_years = list(range(eval_year - T_SEQ, eval_year))
    if max(observation_years) >= eval_year:
        raise LeakageError("Feature sequence reaches target year")

    region_idx = {value: index for index, value in enumerate(regions)}
    sector_idx = {value: index for index, value in enumerate(sectors)}
    shape = (T_SEQ, len(regions), len(sectors), len(FEATURE_NAMES))
    raw = np.full(shape, np.nan, dtype=np.float32)
    mask = np.zeros(shape, dtype=np.uint8)

    panel_seq = panel[panel["observation_year"].isin(observation_years)]
    ardeco_seq = ardeco_long[ardeco_long["observation_year"].isin(observation_years)]
    ardeco_lookup = ardeco_seq.set_index(
        ["region_id", "observation_year", "sector_a10"]
    )
    for row in panel_seq.itertuples(index=False):
        t = observation_years.index(int(row.observation_year))
        r = region_idx[str(row.region_id)]
        s = sector_idx[str(row.sector_a10)]
        values = (
            row.sector_growth_1y,
            row.sector_share,
            np.log1p(row.sector_births) if row.sector_births >= 0 else np.nan,
        )
        for feature, value in enumerate(values):
            if np.isfinite(value):
                raw[t, r, s, feature] = value
                mask[t, r, s, feature] = 1
        key = (str(row.region_id), int(row.observation_year), str(row.sector_a10))
        if key in ardeco_lookup.index:
            employment = ardeco_lookup.loc[key]
            for offset, column in enumerate(
                ("log_employment", "employment_growth", "employment_share"), start=3
            ):
                value = employment[column]
                if np.isfinite(value):
                    raw[t, r, s, offset] = value
                    mask[t, r, s, offset] = 1

    territory_adj = build_adjacency_seq(
        panel, "FR", sectors, regions, observation_years, eval_year
    ).astype(np.float32)

    target_rows = get_target_rows(panel, eval_year).set_index(
        ["region_id", "sector_a10"]
    )
    prior_rows = panel[panel["observation_year"] == eval_year - 1].set_index(
        ["region_id", "sector_a10"]
    )
    thresholds = compute_fold_thresholds(get_feature_rows(panel, eval_year))
    target_shape = (len(regions), len(sectors))
    target_log_growth = np.full(target_shape, np.nan, dtype=np.float32)
    target_raw_growth = np.full(target_shape, np.nan, dtype=np.float32)
    target_regime = np.full(target_shape, -1, dtype=np.int64)
    target_recovery = np.full(target_shape, -1, dtype=np.int64)
    target_emergence = np.full(target_shape, -1, dtype=np.int64)
    target_mask = np.zeros(target_shape, dtype=np.uint8)

    for region in regions:
        for sector in sectors:
            key = (region, sector)
            if key not in target_rows.index or key not in prior_rows.index:
                continue
            current = target_rows.loc[key]
            prior = prior_rows.loc[key]
            threshold = thresholds[sector]
            frame = pd.DataFrame([current])
            log_growth = float(compute_log_growth(frame).iloc[0])
            growth = float(current["sector_growth_1y"])
            prior_growth = float(prior["sector_growth_1y"])
            r, s = region_idx[region], sector_idx[sector]
            if not np.isfinite(log_growth) or not np.isfinite(growth):
                continue
            target_log_growth[r, s] = log_growth
            target_raw_growth[r, s] = growth
            target_regime[r, s] = int(classify_regime(
                pd.Series([growth]), threshold["growth_q25"], threshold["growth_q75"]
            ).iloc[0])
            target_recovery[r, s] = int(classify_recovery(
                pd.Series([growth]), pd.Series([prior_growth]),
                threshold["growth_q25"], threshold["growth_q75"]
            ).iloc[0])
            target_emergence[r, s] = int(compute_emergence(
                pd.Series([growth]), pd.Series([float(prior["sector_share"])]),
                threshold["growth_q75"], threshold["share_q25"]
            ).iloc[0])
            target_mask[r, s] = 1

    return {
        "features_seq": raw,
        "feature_mask_seq": mask,
        "territory_adj_seq": territory_adj,
        "target_log_growth": target_log_growth,
        "target_raw_growth": target_raw_growth,
        "target_regime": target_regime,
        "target_recovery": target_recovery,
        "target_emergence": target_emergence,
        "target_mask": target_mask,
        "observation_years": np.asarray(observation_years, dtype=np.int64),
        "region_ids": np.asarray(regions),
        "sector_ids": np.asarray(sectors),
    }


def build_fold(
    panel: pd.DataFrame,
    ardeco_long: pd.DataFrame,
    eval_year: int,
) -> dict[str, np.ndarray]:
    """Build historical training samples plus the final outer-evaluation sample."""
    first_target_year = int(panel["observation_year"].min()) + T_SEQ
    sample_years = list(range(first_target_year, eval_year + 1))
    if len(sample_years) < 2:
        raise ValueError(f"Need training samples before eval_year={eval_year}")
    samples = [_build_sample(panel, ardeco_long, year) for year in sample_years]

    raw = np.stack([sample["features_seq"] for sample in samples])
    masks = np.stack([sample["feature_mask_seq"] for sample in samples])
    train_raw = raw[:-1]
    train_masks = masks[:-1]
    _, means, stds = _fit_scale(train_raw, train_masks)
    features = np.zeros_like(raw, dtype=np.float32)
    for feature in range(raw.shape[-1]):
        valid = masks[..., feature].astype(bool) & np.isfinite(raw[..., feature])
        features[..., feature][valid] = (
            raw[..., feature][valid] - means[feature]
        ) / stds[feature]

    stack_keys = (
        "territory_adj_seq", "target_log_growth", "target_raw_growth",
        "target_regime", "target_recovery", "target_emergence", "target_mask",
        "observation_years",
    )
    result = {
        key: np.stack([sample[key] for sample in samples])
        for key in stack_keys
    }
    territory_adj_mask = (result["territory_adj_seq"].sum(axis=(-1, -2)) > 0).astype(
        np.uint8
    )
    result.update({
        "features_seq": features,
        "feature_mask_seq": masks,
        "territory_adj_mask": territory_adj_mask,
        "sample_years": np.asarray(sample_years, dtype=np.int64),
        "region_ids": samples[-1]["region_ids"],
        "sector_ids": samples[-1]["sector_ids"],
        "feature_means": means,
        "feature_stds": stds,
    })
    return result


def run_builder(
    panel_path: Path = DEFAULT_PANEL,
    ardeco_path: Path = DEFAULT_ARDECO,
    out_dir: Path = DEFAULT_OUT,
    eval_years: list[int] = EVAL_YEARS,
) -> dict:
    panel = pd.read_csv(panel_path, low_memory=False)
    ardeco = _ardeco_long(pd.read_csv(ardeco_path, low_memory=False))
    out_dir.mkdir(parents=True, exist_ok=True)
    folds = []
    for eval_year in eval_years:
        arrays = build_fold(panel, ardeco, eval_year)
        path = out_dir / f"fr_{eval_year}.npz"
        np.savez_compressed(path, **arrays)
        folds.append({
            "eval_year": eval_year,
            "path": str(path),
            "sha256": _sha256(path),
            "features_shape": list(arrays["features_seq"].shape),
            "adjacency_shape": list(arrays["territory_adj_seq"].shape),
            "graph_available_fraction": float(arrays["territory_adj_mask"].mean()),
            "eval_graph_complete": bool(arrays["territory_adj_mask"][-1].all()),
            "n_train_samples": int(len(arrays["sample_years"]) - 1),
            "sample_years": arrays["sample_years"].tolist(),
            "target_observed": int(arrays["target_mask"][-1].sum()),
            "max_source_year": int(arrays["observation_years"][-1].max()),
            "leakage_ok": bool(
                arrays["sample_years"][-1] == eval_year
                and arrays["observation_years"][-1].max() < eval_year
                and arrays["sample_years"][:-1].max() < eval_year
            ),
        })
    manifest = {
        "version": "1.0",
        "decision": "DUAL_GRAPH_TENSORS_READY",
        "feature_names": list(FEATURE_NAMES),
        "geography": "FR NUTS3-2021",
        "n_regions": int(panel["region_id"].nunique()),
        "n_sectors": int(panel["sector_a10"].nunique()),
        "folds": folds,
    }
    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", type=Path, default=DEFAULT_PANEL)
    parser.add_argument("--ardeco", type=Path, default=DEFAULT_ARDECO)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--eval-years", nargs="+", type=int, default=EVAL_YEARS)
    args = parser.parse_args()
    result = run_builder(args.panel, args.ardeco, args.out_dir, args.eval_years)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
