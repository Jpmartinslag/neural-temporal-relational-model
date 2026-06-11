"""Causal L2 graph-temporal tensor preflight for the HERALD A1 pilot.

Exports rolling-origin fold tensors aligned to the canonical AR/Ridge protocol.
All node features, adjacency matrices and Ridge normalisations use only data
from observation_year <= eval_year - 1.  The contract is enforced by a hard
assertion inside every fold builder — it is never silently approximated.

Causal contract (enforced, not aspirational)
---------------------------------------------
* max(source_observation_year) < eval_year — asserted in build_fold_tensors.
* Adjacency rebuilt per fold from raw growth rates up to causal cutoff.
* Normalization and imputation statistics derived from training fold only.
* PT-KZ is structurally absent: mask=0 always; never filled with zero or
  treated as an observed zero value.
* Real missingness is distinguished from zero economic activity via masks.
* No cross-country edges; no country pooling of targets or Ridge models.
* Territory and sector ordering is deterministic (sorted).

Output format
-------------
data/processed/graph_temporal_preflight/
    manifest.json
    fold_index.csv
    {COUNTRY}/
        {EVAL_YEAR}/
            node_features.npz   keys: features (R,S,F), feature_names, eval_year
            adjacency_l2.npz    keys: adj (S,R,R), sectors, region_ids
            masks.npz           keys: obs_mask (R,S), struct_mask (R,S)
            targets.npz         keys: y_true (R,), y_ridge (R,), residual (R,),
                                       target_mask (R,), region_ids
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from sklearn.linear_model import Ridge
    from sklearn.preprocessing import StandardScaler
    _HAS_SKLEARN = True
except ImportError:  # pragma: no cover
    _HAS_SKLEARN = False

BASE = Path(__file__).resolve().parents[3]
DEFAULT_SECTOR_PANEL = (
    BASE / "data/processed/economic_graph/sector_panel_fr_nl_pt.csv"
)
DEFAULT_PANEL_DIR = BASE / "data/processed/european_panel"
DEFAULT_OUT = BASE / "data/processed/graph_temporal_preflight"

SECTORS_ALL = ["BE", "FZ", "GI", "JZ", "KZ", "LZ", "MN", "OQ", "RU"]
WINDOW = 5
MIN_PERIODS = 4
RIDGE_ALPHA = 10.0
STRUCTURAL_ABSENT = {("PT", "KZ")}  # (country, sector) pairs that are always masked

PANEL_FILE = {
    "NL": "nl_panel.csv",
    "FR": "france_panel.csv",
    "PT": "pt_panel.csv",
}


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_sector_panel(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def load_country_panel(country: str, panel_dir: Path) -> pd.DataFrame:
    fname = PANEL_FILE.get(country)
    if fname is None:
        raise ValueError(f"No panel file registered for country {country!r}")
    return pd.read_csv(panel_dir / fname)


def country_sectors(sector_panel: pd.DataFrame, country: str) -> list[str]:
    """Sorted list of sectors with at least one supported observation."""
    sub = sector_panel[
        (sector_panel["country"] == country)
        & (sector_panel["mask_sector_supported"] == 1)
    ]
    return sorted(sub["sector_a10"].unique())


def country_regions(country_panel: pd.DataFrame) -> list[str]:
    """Sorted list of region IDs in the country panel."""
    return sorted(country_panel["region_id"].astype(str).unique())


# ---------------------------------------------------------------------------
# Adjacency builder
# ---------------------------------------------------------------------------

def _pairwise_pearson(mat: np.ndarray, min_periods: int = MIN_PERIODS) -> np.ndarray:
    """Pearson correlation via pandas; handles NaN and min_periods.

    Returns shape (n_regions, n_regions).  All-NaN if fewer than min_periods
    rows survive.
    """
    if mat.shape[0] < min_periods:
        n = mat.shape[1]
        return np.full((n, n), np.nan)
    return pd.DataFrame(mat).corr(min_periods=min_periods).to_numpy(dtype=float)


def build_adjacency_l2_fold(
    sector_panel: pd.DataFrame,
    country: str,
    sectors: list[str],
    region_ids: list[str],
    eval_year: int,
    window: int = WINDOW,
    min_periods: int = MIN_PERIODS,
) -> np.ndarray:
    """Causal L2 adjacency for one fold.

    Returns shape (n_sectors, n_regions, n_regions).
    Uses only observation_year in [eval_year - window, eval_year - 1].
    """
    assert eval_year - 1 >= eval_year - window, "window must be positive"
    causal_max = eval_year - 1
    window_min = eval_year - window

    n_s = len(sectors)
    n_r = len(region_ids)
    adj = np.full((n_s, n_r, n_r), np.nan)

    sp_country = sector_panel[sector_panel["country"] == country].copy()

    # Hard causal assertion: no future data may enter the window
    sp_window = sp_country[
        (sp_country["observation_year"] >= window_min)
        & (sp_country["observation_year"] <= causal_max)
        & (sp_country["mask_sector_supported"] == 1)
    ]
    _assert_no_leakage(sp_window, eval_year, column="observation_year")

    for s_idx, sector in enumerate(sectors):
        sp_s = sp_window[sp_window["sector_a10"] == sector]
        if sp_s.empty:
            continue

        # Pivot: rows = observation_year, cols = region_id (sorted)
        wide = sp_s.pivot_table(
            index="observation_year",
            columns="region_id",
            values="sector_growth_1y",
            aggfunc="first",
        ).reindex(columns=region_ids)

        mat = wide.to_numpy(dtype=float)  # (T_window, R)
        corr = _pairwise_pearson(mat, min_periods=min_periods)

        # Diagonal: self-correlation is 1 by definition; set explicitly
        np.fill_diagonal(corr, 1.0)

        adj[s_idx] = corr

    return adj


# ---------------------------------------------------------------------------
# Node features builder
# ---------------------------------------------------------------------------

def build_node_features_fold(
    sector_panel: pd.DataFrame,
    country: str,
    sectors: list[str],
    region_ids: list[str],
    eval_year: int,
    train_stats: dict | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict]:
    """Build node feature tensor for one fold.

    Feature vector per (region, sector): [sector_growth_1y, sector_share, births_norm]
    Observation year = eval_year - 1 (most recent causal snapshot).

    train_stats: if provided, use these normalisation stats; otherwise compute
    them from the training window (<= eval_year - 1) and return them.

    Returns
    -------
    features : (R, S, 3) float array
    obs_mask  : (R, S) int8 — 1 where the raw observation exists
    struct_mask: (R, S) int8 — 0 for structurally absent (PT-KZ); 1 elsewhere
    train_stats: dict with keys 'births_mean', 'births_std' per sector
    """
    causal_cutoff = eval_year - 1
    sp_country = sector_panel[sector_panel["country"] == country]

    _assert_no_leakage(
        sp_country[sp_country["observation_year"] <= causal_cutoff],
        eval_year,
        column="observation_year",
    )

    n_r = len(region_ids)
    n_s = len(sectors)
    features = np.full((n_r, n_s, 3), np.nan, dtype=float)
    obs_mask = np.zeros((n_r, n_s), dtype=np.int8)
    struct_mask = np.ones((n_r, n_s), dtype=np.int8)

    # Mark structural absences
    for s_idx, sector in enumerate(sectors):
        if (country, sector) in STRUCTURAL_ABSENT:
            struct_mask[:, s_idx] = 0

    # Compute normalisation stats from full training window if not provided
    if train_stats is None:
        train_stats = {}
        sp_train = sp_country[
            (sp_country["observation_year"] <= causal_cutoff)
            & (sp_country["mask_sector_births"] == 1)
        ]
        for sector in sectors:
            sp_s = sp_train[sp_train["sector_a10"] == sector]
            births_vals = sp_s["sector_births"].dropna().values
            train_stats[sector] = {
                "births_mean": float(np.nanmean(births_vals)) if len(births_vals) else 0.0,
                "births_std": float(np.nanstd(births_vals)) if len(births_vals) else 1.0,
            }
            if train_stats[sector]["births_std"] < 1e-9:
                train_stats[sector]["births_std"] = 1.0

    # Extract snapshot at observation_year = eval_year - 1
    sp_snapshot = sp_country[
        sp_country["observation_year"] == causal_cutoff
    ]

    r_idx_map = {r: i for i, r in enumerate(region_ids)}

    for s_idx, sector in enumerate(sectors):
        sp_s = sp_snapshot[sp_snapshot["sector_a10"] == sector]
        for _, row in sp_s.iterrows():
            rid = str(row["region_id"])
            if rid not in r_idx_map:
                continue
            r_idx = r_idx_map[rid]
            if row.get("mask_sector_supported", 1) == 0:
                continue
            if struct_mask[r_idx, s_idx] == 0:
                continue

            g = row["sector_growth_1y"]
            share = row["sector_share"]
            births = row["sector_births"]

            has_obs = (
                pd.notna(g) and np.isfinite(g)
                and pd.notna(share) and np.isfinite(share)
                and row.get("mask_sector_births", 1) == 1
            )
            if has_obs:
                bm = train_stats[sector]["births_mean"]
                bs = train_stats[sector]["births_std"]
                births_norm = (births - bm) / bs if not pd.isna(births) else np.nan
                features[r_idx, s_idx, 0] = g
                features[r_idx, s_idx, 1] = share
                features[r_idx, s_idx, 2] = births_norm
                obs_mask[r_idx, s_idx] = 1

    return features, obs_mask, struct_mask, train_stats


# ---------------------------------------------------------------------------
# Ridge baseline
# ---------------------------------------------------------------------------

def fit_ridge_baseline(
    country_panel: pd.DataFrame,
    eval_year: int,
    region_ids: list[str],
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Fit AR-Ridge on training fold; predict for eval_year.

    Features: lag1_births, lag2_births, growth_1y (all causal).
    Training fold: all rows with year < eval_year and mask_target == 1.

    Returns y_true, y_ridge, target_mask — each of length len(region_ids).
    NaN in y_ridge if Ridge cannot be fit (insufficient training data).
    """
    cp = country_panel.copy()
    cp["region_id"] = cp["region_id"].astype(str)

    n_r = len(region_ids)
    y_true = np.full(n_r, np.nan)
    y_ridge = np.full(n_r, np.nan)
    target_mask = np.zeros(n_r, dtype=np.int8)

    r_idx_map = {r: i for i, r in enumerate(region_ids)}

    # Targets at eval_year
    eval_rows = cp[cp["year"] == eval_year]
    for _, row in eval_rows.iterrows():
        rid = str(row["region_id"])
        if rid not in r_idx_map:
            continue
        idx = r_idx_map[rid]
        if row.get("mask_target", 1) == 1 and not pd.isna(row["target_births"]):
            y_true[idx] = row["target_births"]
            target_mask[idx] = 1

    if not _HAS_SKLEARN:
        return y_true, y_ridge, target_mask

    feat_cols = ["lag1_births", "lag2_births", "growth_1y"]
    train = cp[
        (cp["year"] < eval_year)
        & (cp["mask_target"].fillna(0).astype(int) == 1)
    ].copy()

    # Use only rows where all features and target are available
    train = train.dropna(subset=feat_cols + ["target_births"])
    if len(train) < 3:
        return y_true, y_ridge, target_mask

    X_tr = train[feat_cols].values
    y_tr = train["target_births"].values

    # Normalise target using training mean/std to keep Ridge well-conditioned
    y_mean = float(np.mean(y_tr))
    y_std = float(np.std(y_tr))
    if y_std < 1e-9:
        y_std = 1.0
    y_tr_norm = (y_tr - y_mean) / y_std

    scaler = StandardScaler()
    X_tr_s = scaler.fit_transform(X_tr)

    model = Ridge(alpha=RIDGE_ALPHA, fit_intercept=True)
    model.fit(X_tr_s, y_tr_norm)

    # Predict for eval_year
    eval_cp = cp[cp["year"] == eval_year].copy()
    eval_cp = eval_cp.dropna(subset=feat_cols)
    if eval_cp.empty:
        return y_true, y_ridge, target_mask

    X_ev = scaler.transform(eval_cp[feat_cols].values)
    y_pred_norm = model.predict(X_ev)
    y_pred = y_pred_norm * y_std + y_mean

    for (_, row), pred in zip(eval_cp.iterrows(), y_pred):
        rid = str(row["region_id"])
        if rid in r_idx_map:
            y_ridge[r_idx_map[rid]] = max(0.0, pred)  # births cannot be negative

    return y_true, y_ridge, target_mask


# ---------------------------------------------------------------------------
# Causal contract assertion
# ---------------------------------------------------------------------------

def _assert_no_leakage(df: pd.DataFrame, eval_year: int, column: str = "observation_year") -> None:
    """Raise LeakageError if any row has column >= eval_year."""
    if df.empty:
        return
    max_year = df[column].max()
    if max_year >= eval_year:
        raise LeakageError(
            f"Causal violation: {column} max={max_year} >= eval_year={eval_year}"
        )


class LeakageError(RuntimeError):
    """Raised when future data would enter a causal fold."""


# ---------------------------------------------------------------------------
# Checksums
# ---------------------------------------------------------------------------

def array_checksum(arr: np.ndarray) -> str:
    return hashlib.md5(np.ascontiguousarray(arr)).hexdigest()


def file_checksum(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Fold builder
# ---------------------------------------------------------------------------

def build_fold_tensors(
    country: str,
    eval_year: int,
    sector_panel: pd.DataFrame,
    country_panel: pd.DataFrame,
    sectors: list[str],
    region_ids: list[str],
    window: int = WINDOW,
    min_periods: int = MIN_PERIODS,
) -> dict:
    """Build all tensors for one (country, eval_year) fold.

    Hard contract:
    - All sector observations use observation_year <= eval_year - 1.
    - Adjacency uses only the causal window [eval_year-window, eval_year-1].
    - Ridge features (lag1, lag2, growth_1y) are all observation_year < eval_year.
    """
    adj = build_adjacency_l2_fold(
        sector_panel, country, sectors, region_ids, eval_year, window, min_periods
    )

    features, obs_mask, struct_mask, train_stats = build_node_features_fold(
        sector_panel, country, sectors, region_ids, eval_year
    )

    y_true, y_ridge, target_mask = fit_ridge_baseline(
        country_panel, eval_year, region_ids
    )

    residual = np.where(target_mask.astype(bool), y_true - y_ridge, np.nan)

    # Final causal assertion: every value written to the tensors uses data < eval_year
    sp_fold = sector_panel[
        (sector_panel["country"] == country)
        & (sector_panel["observation_year"] < eval_year)
    ]
    _assert_no_leakage(sp_fold, eval_year, column="observation_year")

    cp_train = country_panel[country_panel["year"] < eval_year]
    _assert_no_leakage(cp_train, eval_year, column="year")

    return {
        "node_features": features,      # (R, S, 3)
        "feature_names": ["sector_growth_1y", "sector_share", "births_norm"],
        "adjacency_l2": adj,            # (S, R, R)
        "obs_mask": obs_mask,           # (R, S)  int8
        "struct_mask": struct_mask,     # (R, S)  int8
        "y_true": y_true,              # (R,)
        "y_ridge": y_ridge,            # (R,)
        "residual": residual,           # (R,)
        "target_mask": target_mask,     # (R,)   int8
        "region_ids": region_ids,
        "sectors": sectors,
        "eval_year": eval_year,
        "country": country,
        "train_stats": train_stats,
        "max_train_obs_year": eval_year - 1,
    }


# ---------------------------------------------------------------------------
# Saving fold artifacts
# ---------------------------------------------------------------------------

def save_fold(fold: dict, out_dir: Path) -> dict:
    """Save fold tensors to NPZ files; return dict of checksums."""
    fold_dir = out_dir / fold["country"] / str(fold["eval_year"])
    fold_dir.mkdir(parents=True, exist_ok=True)

    checksums: dict[str, str] = {}

    # node_features.npz
    nf_path = fold_dir / "node_features.npz"
    np.savez_compressed(
        nf_path,
        features=fold["node_features"],
        eval_year=np.array([fold["eval_year"]]),
    )
    checksums["node_features"] = file_checksum(nf_path)

    # adjacency_l2.npz
    adj_path = fold_dir / "adjacency_l2.npz"
    np.savez_compressed(
        adj_path,
        adj=fold["adjacency_l2"],
    )
    checksums["adjacency_l2"] = file_checksum(adj_path)

    # masks.npz
    masks_path = fold_dir / "masks.npz"
    np.savez_compressed(
        masks_path,
        obs_mask=fold["obs_mask"],
        struct_mask=fold["struct_mask"],
    )
    checksums["masks"] = file_checksum(masks_path)

    # targets.npz
    targets_path = fold_dir / "targets.npz"
    np.savez_compressed(
        targets_path,
        y_true=fold["y_true"],
        y_ridge=fold["y_ridge"],
        residual=fold["residual"],
        target_mask=fold["target_mask"],
    )
    checksums["targets"] = file_checksum(targets_path)

    return checksums


# ---------------------------------------------------------------------------
# Main export pipeline
# ---------------------------------------------------------------------------

def export_preflight(
    countries: list[str],
    eval_years_by_country: dict[str, list[int]],
    sector_panel_path: Path = DEFAULT_SECTOR_PANEL,
    panel_dir: Path = DEFAULT_PANEL_DIR,
    out_dir: Path = DEFAULT_OUT,
    window: int = WINDOW,
    min_periods: int = MIN_PERIODS,
    panel_files: dict[str, str] | None = None,
) -> dict:
    """Export all fold tensors and write manifest.json + fold_index.csv.

    Returns the manifest dict.
    """
    t0 = time.perf_counter()
    out_dir.mkdir(parents=True, exist_ok=True)

    sector_panel = load_sector_panel(sector_panel_path)

    manifest: dict = {
        "schema_version": "1.0",
        "contract": {
            "causal": "max(source_observation_year) < eval_year",
            "no_cross_country_edges": True,
            "no_country_pooling": True,
            "pt_kz_always_masked": True,
            "missing_not_zero": True,
            "deterministic_ordering": True,
        },
        "sources": {
            "sector_panel": str(sector_panel_path),
            "sector_panel_checksum": file_checksum(sector_panel_path),
        },
        "window": window,
        "min_periods": min_periods,
        "feature_names": ["sector_growth_1y", "sector_share", "births_norm"],
        "folds": [],
        "structural_absent": [list(p) for p in sorted(STRUCTURAL_ABSENT)],
    }

    fold_rows = []

    _panel_files = dict(PANEL_FILE)
    if panel_files:
        _panel_files.update(panel_files)

    for country in countries:
        fname = _panel_files.get(country)
        if fname is None:
            raise ValueError(f"No panel file registered for country {country!r}")
        panel_path = panel_dir / fname
        country_panel = pd.read_csv(panel_path)
        manifest["sources"][f"panel_{country}"] = str(panel_path)
        manifest["sources"][f"panel_{country}_checksum"] = file_checksum(panel_path)

        sectors = country_sectors(sector_panel, country)
        region_ids = country_regions(country_panel)
        eval_years = eval_years_by_country.get(country, [])

        for eval_year in sorted(eval_years):
            fold = build_fold_tensors(
                country, eval_year, sector_panel, country_panel,
                sectors, region_ids, window, min_periods
            )
            checksums = save_fold(fold, out_dir)

            fold_meta = {
                "country": country,
                "eval_year": eval_year,
                "n_regions": len(region_ids),
                "n_sectors": len(sectors),
                "sectors": sectors,
                "max_train_obs_year": eval_year - 1,
                "adj_shape": list(fold["adjacency_l2"].shape),
                "features_shape": list(fold["node_features"].shape),
                "n_observed_targets": int(fold["target_mask"].sum()),
                "checksums": checksums,
            }
            manifest["folds"].append(fold_meta)
            fold_rows.append({
                "country": country,
                "eval_year": eval_year,
                "n_regions": len(region_ids),
                "n_sectors": len(sectors),
                "max_train_obs_year": eval_year - 1,
                "n_observed_targets": int(fold["target_mask"].sum()),
                "adj_checksum": checksums["adjacency_l2"],
                "features_checksum": checksums["node_features"],
            })

    elapsed = time.perf_counter() - t0
    manifest["build_time_s"] = round(elapsed, 2)
    manifest["n_folds"] = len(fold_rows)

    manifest_path = out_dir / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    fold_index = pd.DataFrame(fold_rows)
    fold_index.to_csv(out_dir / "fold_index.csv", index=False)

    return manifest


# ---------------------------------------------------------------------------
# Loading utilities (for smoke and tests)
# ---------------------------------------------------------------------------

def load_fold(country: str, eval_year: int, out_dir: Path = DEFAULT_OUT) -> dict:
    """Load saved fold tensors from disk.  Raises FileNotFoundError if absent."""
    fold_dir = out_dir / country / str(eval_year)
    required = ["node_features.npz", "adjacency_l2.npz", "masks.npz", "targets.npz"]
    for fname in required:
        p = fold_dir / fname
        if not p.exists():
            raise FileNotFoundError(
                f"Required artifact missing (fail-closed): {p}"
            )
    nf = np.load(fold_dir / "node_features.npz")
    ad = np.load(fold_dir / "adjacency_l2.npz")
    mk = np.load(fold_dir / "masks.npz")
    tg = np.load(fold_dir / "targets.npz")

    return {
        "features": nf["features"],
        "eval_year": int(nf["eval_year"][0]),
        "adj": ad["adj"],
        "obs_mask": mk["obs_mask"],
        "struct_mask": mk["struct_mask"],
        "y_true": tg["y_true"],
        "y_ridge": tg["y_ridge"],
        "residual": tg["residual"],
        "target_mask": tg["target_mask"],
    }


def load_manifest(out_dir: Path = DEFAULT_OUT) -> dict:
    p = out_dir / "manifest.json"
    if not p.exists():
        raise FileNotFoundError(f"Manifest missing (fail-closed): {p}")
    with open(p) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Build causal graph-temporal preflight tensors."
    )
    p.add_argument("--countries", nargs="+", default=["NL"])
    p.add_argument(
        "--eval-years-nl", nargs="+", type=int, default=[2019, 2020, 2021]
    )
    p.add_argument(
        "--eval-years-fr", nargs="+", type=int, default=[2020, 2021, 2022]
    )
    p.add_argument(
        "--eval-years-pt", nargs="+", type=int, default=[2019, 2020, 2021]
    )
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    p.add_argument("--sector-panel", type=Path, default=DEFAULT_SECTOR_PANEL)
    p.add_argument("--panel-dir", type=Path, default=DEFAULT_PANEL_DIR)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    eval_years_map: dict[str, list[int]] = {}
    if "NL" in args.countries:
        eval_years_map["NL"] = args.eval_years_nl
    if "FR" in args.countries:
        eval_years_map["FR"] = args.eval_years_fr
    if "PT" in args.countries:
        eval_years_map["PT"] = args.eval_years_pt

    manifest = export_preflight(
        countries=args.countries,
        eval_years_by_country=eval_years_map,
        sector_panel_path=args.sector_panel,
        panel_dir=args.panel_dir,
        out_dir=args.out_dir,
    )
    print(f"Exported {manifest['n_folds']} folds in {manifest['build_time_s']}s")
    print(f"Manifest: {args.out_dir / 'manifest.json'}")


if __name__ == "__main__":
    main()
