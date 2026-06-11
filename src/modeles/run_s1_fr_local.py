"""Pre-registered local S1-FR graph-temporal experiment.

Runs A0-neural, GConvGRU and EvolveGCN-H on five FR evaluation years and
five seeds. Temporal and territory null controls rebuild L2 adjacency from
permuted source growth series. No hyperparameter search is performed.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
import traceback
from pathlib import Path

import numpy as np
import pandas as pd

from src.data.european_panel.build_graph_temporal_v2 import (
    DEFAULT_SECTOR_PANEL,
    export_v2,
)
from src.modeles.graph_temporal_train import TrainConfig, train_rolling_origin


COUNTRY = "FR"
FOLD_YEARS = list(range(2017, 2026))
EVAL_YEARS = [2021, 2022, 2023, 2024, 2025]
SEEDS = [42, 43, 44, 45, 46]
GRAPH_MODELS = ("GConvGRU", "EvolveGCNH")
OUTPUT_PATH = Path("data/processed/graph_temporal_s1/s1_fr_results.json")
CHECKPOINT_PATH = Path("data/processed/graph_temporal_s1/s1_fr_checkpoint.json")
OBSERVED_FOLDS = Path("data/processed/graph_temporal_s1/folds_observed")
N_SIGN_FLIPS = 9999


def progress(message: str, started: float) -> None:
    elapsed = time.perf_counter() - started
    print(f"[S1 +{elapsed:8.1f}s] {message}", flush=True)


def _write_json_atomic(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".tmp.{os.getpid()}")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    tmp.replace(path)


def _checkpoint(
    path: Path,
    *,
    stage: str,
    observed_rows: list[dict],
    temporal_rows: list[dict],
    territory_rows: list[dict],
    covid_rows: list[dict],
    started: float,
) -> None:
    _write_json_atomic(path, {
        "status": "RUNNING",
        "stage": stage,
        "elapsed_seconds": time.perf_counter() - started,
        "counts": {
            "observed": len(observed_rows),
            "temporal_null": len(temporal_rows),
            "territory_null": len(territory_rows),
            "covid_excluded": len(covid_rows),
        },
        "rows": {
            "observed": observed_rows,
            "temporal_null": temporal_rows,
            "territory_null": territory_rows,
            "covid_excluded": covid_rows,
        },
    })


def permute_growth_source(
    panel: pd.DataFrame,
    country: str,
    mode: str,
    seed: int,
) -> pd.DataFrame:
    """Permute source growth values while preserving missing-value positions."""
    if mode not in {"temporal", "territory"}:
        raise ValueError(f"Unknown permutation mode: {mode}")
    out = panel.copy()
    rng = np.random.default_rng(seed)
    country_mask = out["country"].eq(country)
    if mode == "temporal":
        group_cols = ["country", "sector_a10", "region_id"]
    else:
        group_cols = ["country", "sector_a10", "observation_year"]

    subset = out.loc[country_mask]
    for _, group in subset.groupby(group_cols, sort=True, dropna=False):
        idx = group.index.to_numpy()
        values = pd.to_numeric(out.loc[idx, "sector_growth_1y"], errors="coerce").to_numpy()
        finite = np.isfinite(values)
        values[finite] = rng.permutation(values[finite])
        out.loc[idx, "sector_growth_1y"] = values
    return out


def paired_sign_flip_pvalue(
    observed: np.ndarray,
    control: np.ndarray,
    *,
    seed: int,
    n_permutations: int = N_SIGN_FLIPS,
) -> float:
    """One-sided paired randomization test: H1 observed WMAPE < control."""
    observed = np.asarray(observed, dtype=float)
    control = np.asarray(control, dtype=float)
    valid = np.isfinite(observed) & np.isfinite(control)
    differences = control[valid] - observed[valid]
    if differences.size == 0:
        return float("nan")
    statistic = float(differences.mean())
    if statistic <= 0:
        return 1.0
    rng = np.random.default_rng(seed)
    count = 0
    for _ in range(n_permutations):
        signs = rng.choice(np.array([-1.0, 1.0]), size=differences.size)
        if float((differences * signs).mean()) >= statistic:
            count += 1
    return (count + 1) / (n_permutations + 1)


def _export_folds(
    panel: pd.DataFrame,
    out_dir: Path,
    *,
    exclude_adjacency_years: frozenset[int] = frozenset(),
) -> None:
    export_v2(
        countries=[COUNTRY],
        eval_years_by_country={COUNTRY: FOLD_YEARS},
        sector_panel_path=None,
        out_dir=out_dir,
        run_adjacency_audit=False,
        exclude_adjacency_years=exclude_adjacency_years,
        _sector_panel_override=panel,
    )


def _run_configuration(
    model_name: str,
    folds_dir: Path,
    seed: int,
    *,
    max_epochs: int,
    patience: int,
    started: float | None = None,
    label: str = "",
    eval_years: list[int] | None = None,
) -> list[dict]:
    config = TrainConfig(
        max_epochs=max_epochs,
        patience=patience,
        hidden_dim=4,
        sector_embed_dim=4,
        dropout=0.3,
        clamp_frac=0.15,
        seed=seed,
    )
    rows = []
    for eval_year in EVAL_YEARS if eval_years is None else eval_years:
        if started is not None:
            progress(
                f"START {label} model={model_name} seed={seed} eval_year={eval_year}",
                started,
            )
        _, result = train_rolling_origin(
            model_name,
            COUNTRY,
            eval_year,
            config=config,
            folds_dir=folds_dir,
        )
        rows.append(result.to_dict())
        if started is not None:
            progress(
                f"DONE  {label} model={model_name} seed={seed} "
                f"eval_year={eval_year} wmape={result.evaluation_wmape:.6f} "
                f"epochs={result.epochs_ran}",
                started,
            )
    return rows


def _missing_years(rows: list[dict], model_name: str, seed: int) -> list[int]:
    completed = {
        int(row["eval_year"])
        for row in rows
        if row["model_name"] == model_name and int(row["seed"]) == seed
    }
    return [year for year in EVAL_YEARS if year not in completed]


def _load_checkpoint_rows(path: Path) -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    if not path.exists():
        return [], [], [], []
    payload = json.loads(path.read_text())
    if payload.get("status") != "RUNNING":
        return [], [], [], []
    rows = payload.get("rows", {})
    return (
        list(rows.get("observed", [])),
        list(rows.get("temporal_null", [])),
        list(rows.get("territory_null", [])),
        list(rows.get("covid_excluded", [])),
    )


def _vector(rows: list[dict], model_name: str) -> np.ndarray:
    selected = [
        row for row in rows
        if row["model_name"] == model_name
    ]
    selected.sort(key=lambda row: (row["seed"], row["eval_year"]))
    return np.array([row["evaluation_wmape"] for row in selected], dtype=float)


def _gate_model(
    model_name: str,
    observed_rows: list[dict],
    temporal_rows: list[dict],
    territory_rows: list[dict],
) -> dict:
    rows = [row for row in observed_rows if row["model_name"] == model_name]
    a0_rows = [row for row in observed_rows if row["model_name"] == "A0Neural"]
    obs = _vector(observed_rows, model_name)
    a0 = _vector(observed_rows, "A0Neural")
    ridge = np.array([
        row["ridge_wmape"]
        for row in sorted(rows, key=lambda r: (r["seed"], r["eval_year"]))
    ])
    temporal = _vector(temporal_rows, model_name)
    territory = _vector(territory_rows, model_name)

    by_year = {}
    for year in EVAL_YEARS:
        y_rows = [row for row in rows if row["eval_year"] == year]
        model_mean = float(np.mean([row["evaluation_wmape"] for row in y_rows]))
        ridge_mean = float(np.mean([row["ridge_wmape"] for row in y_rows]))
        by_year[str(year)] = {
            "model_wmape": model_mean,
            "ridge_wmape": ridge_mean,
            "relative_vs_ridge": (ridge_mean - model_mean) / ridge_mean,
        }

    per_seed_means = [
        np.mean([row["evaluation_wmape"] for row in rows if row["seed"] == seed])
        for seed in SEEDS
    ]
    improvement_ridge = (ridge.mean() - obs.mean()) / ridge.mean()
    improvement_a0 = (a0.mean() - obs.mean()) / a0.mean()
    wins = sum(v["model_wmape"] < v["ridge_wmape"] for v in by_year.values())
    no_bad_year = all(
        v["model_wmape"] <= 1.10 * v["ridge_wmape"] for v in by_year.values()
    )
    p_temporal = paired_sign_flip_pvalue(
        obs, temporal, seed=1701 + sum(map(ord, model_name))
    )
    p_territory = paired_sign_flip_pvalue(
        obs, territory, seed=2701 + sum(map(ord, model_name))
    )
    checks = {
        "improves_ridge_at_least_1pct": bool(improvement_ridge >= 0.01),
        "improves_a0_at_least_1pct": bool(improvement_a0 >= 0.01),
        "wins_at_least_half_years": bool(wins >= 3),
        "no_year_over_10pct_worse": bool(no_bad_year),
        "beats_temporal_null_p_le_005": bool(p_temporal <= 0.05 and obs.mean() < temporal.mean()),
        "beats_territory_null_p_le_005": bool(p_territory <= 0.05 and obs.mean() < territory.mean()),
        "seed_std_le_0005": bool(float(np.std(per_seed_means, ddof=1)) <= 0.005),
        "all_leakage_checks_pass": bool(all(row["leakage_ok"] for row in rows)),
    }
    return {
        "decision": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "mean_wmape": float(obs.mean()),
        "ridge_mean_wmape": float(ridge.mean()),
        "a0_mean_wmape": float(a0.mean()),
        "temporal_null_mean_wmape": float(temporal.mean()),
        "territory_null_mean_wmape": float(territory.mean()),
        "relative_improvement_vs_ridge": float(improvement_ridge),
        "relative_improvement_vs_a0": float(improvement_a0),
        "winning_years_vs_ridge": int(wins),
        "seed_mean_wmape_std": float(np.std(per_seed_means, ddof=1)),
        "p_temporal": float(p_temporal),
        "p_territory": float(p_territory),
        "by_year": by_year,
    }


def run_s1(
    *,
    sector_panel_path: Path = DEFAULT_SECTOR_PANEL,
    output_path: Path = OUTPUT_PATH,
    observed_folds: Path = OBSERVED_FOLDS,
    checkpoint_path: Path = CHECKPOINT_PATH,
    max_epochs: int = 200,
    patience: int = 20,
    resume: bool = False,
) -> dict:
    started = time.perf_counter()
    progress("loading sector panel", started)
    panel = pd.read_csv(sector_panel_path, low_memory=False)
    panel["region_id"] = panel["region_id"].astype(str)

    progress(f"exporting observed folds {FOLD_YEARS}", started)
    _export_folds(panel, observed_folds)
    progress("observed folds ready", started)
    if resume:
        observed_rows, temporal_rows, territory_rows, covid_rows = (
            _load_checkpoint_rows(checkpoint_path)
        )
        progress(
            "resuming checkpoint counts="
            f"{len(observed_rows)}/{len(temporal_rows)}/"
            f"{len(territory_rows)}/{len(covid_rows)}",
            started,
        )
    else:
        observed_rows, temporal_rows, territory_rows, covid_rows = [], [], [], []
    for seed in SEEDS:
        missing = _missing_years(observed_rows, "A0Neural", seed)
        if missing:
            observed_rows += _run_configuration(
                "A0Neural", observed_folds, seed,
                max_epochs=max_epochs, patience=patience,
                started=started, label="observed", eval_years=missing,
            )
        _checkpoint(
            checkpoint_path, stage=f"observed/A0Neural/{seed}",
            observed_rows=observed_rows, temporal_rows=temporal_rows,
            territory_rows=territory_rows, covid_rows=covid_rows, started=started,
        )
        for model_name in GRAPH_MODELS:
            missing = _missing_years(observed_rows, model_name, seed)
            if missing:
                observed_rows += _run_configuration(
                    model_name, observed_folds, seed,
                    max_epochs=max_epochs, patience=patience,
                    started=started, label="observed", eval_years=missing,
                )
            _checkpoint(
                checkpoint_path, stage=f"observed/{model_name}/{seed}",
                observed_rows=observed_rows, temporal_rows=temporal_rows,
                territory_rows=territory_rows, covid_rows=covid_rows, started=started,
            )

    with tempfile.TemporaryDirectory(prefix="herald_s1_") as tmp:
        tmp_root = Path(tmp)
        for seed in SEEDS:
            for mode, collector in (
                ("temporal", temporal_rows),
                ("territory", territory_rows),
            ):
                progress(f"rebuilding {mode} null folds seed={seed}", started)
                null_panel = permute_growth_source(panel, COUNTRY, mode, seed)
                null_dir = tmp_root / f"{mode}_{seed}"
                _export_folds(null_panel, null_dir)
                for model_name in GRAPH_MODELS:
                    missing = _missing_years(collector, model_name, seed)
                    if missing:
                        collector += _run_configuration(
                            model_name, null_dir, seed,
                            max_epochs=max_epochs, patience=patience,
                            started=started, label=f"{mode}_null",
                            eval_years=missing,
                        )
                    _checkpoint(
                        checkpoint_path, stage=f"{mode}/{model_name}/{seed}",
                        observed_rows=observed_rows, temporal_rows=temporal_rows,
                        territory_rows=territory_rows, covid_rows=covid_rows,
                        started=started,
                    )

        covid_dir = tmp_root / "covid_excluded"
        progress("rebuilding COVID-excluded adjacency folds", started)
        _export_folds(
            panel, covid_dir, exclude_adjacency_years=frozenset({2020})
        )
        for seed in SEEDS:
            for model_name in GRAPH_MODELS:
                missing = _missing_years(covid_rows, model_name, seed)
                if missing:
                    covid_rows += _run_configuration(
                        model_name, covid_dir, seed,
                        max_epochs=max_epochs, patience=patience,
                        started=started, label="covid_excluded",
                        eval_years=missing,
                    )
                _checkpoint(
                    checkpoint_path, stage=f"covid/{model_name}/{seed}",
                    observed_rows=observed_rows, temporal_rows=temporal_rows,
                    territory_rows=territory_rows, covid_rows=covid_rows,
                    started=started,
                )

    gates = {
        model_name: _gate_model(
            model_name, observed_rows, temporal_rows, territory_rows
        )
        for model_name in GRAPH_MODELS
    }
    decision = (
        "S1_FR_PASS"
        if any(gate["decision"] == "PASS" for gate in gates.values())
        else "S1_FR_FAIL"
    )
    payload = {
        "decision": decision,
        "country": COUNTRY,
        "eval_years": EVAL_YEARS,
        "fold_years": FOLD_YEARS,
        "seeds": SEEDS,
        "config": {
            "hidden_dim": 4,
            "sector_embed_dim": 4,
            "dropout": 0.3,
            "clamp_frac": 0.15,
            "max_epochs": max_epochs,
            "patience": patience,
            "sign_flip_permutations": N_SIGN_FLIPS,
        },
        "gates": gates,
        "zero_adjacency_control": "exactly_y_ridge_canonical_by_contract",
        "covid_sensitivity": {
            model_name: {
                "main_mean_wmape": float(_vector(observed_rows, model_name).mean()),
                "exclude_2020_adjacency_mean_wmape": float(
                    _vector(covid_rows, model_name).mean()
                ),
            }
            for model_name in GRAPH_MODELS
        },
        "rows": {
            "observed": observed_rows,
            "temporal_null": temporal_rows,
            "territory_null": territory_rows,
            "covid_excluded": covid_rows,
        },
        "runtime_seconds": time.perf_counter() - started,
    }
    _write_json_atomic(output_path, payload)
    _write_json_atomic(checkpoint_path, {
        "status": "COMPLETED",
        "decision": decision,
        "elapsed_seconds": payload["runtime_seconds"],
        "result_path": str(output_path),
    })
    progress(f"COMPLETED decision={decision} result={output_path}", started)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sector-panel", type=Path, default=DEFAULT_SECTOR_PANEL)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    parser.add_argument("--observed-folds", type=Path, default=OBSERVED_FOLDS)
    parser.add_argument("--checkpoint", type=Path, default=CHECKPOINT_PATH)
    parser.add_argument("--max-epochs", type=int, default=200)
    parser.add_argument("--patience", type=int, default=20)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    try:
        payload = run_s1(
            sector_panel_path=args.sector_panel,
            output_path=args.output,
            observed_folds=args.observed_folds,
            checkpoint_path=args.checkpoint,
            max_epochs=args.max_epochs,
            patience=args.patience,
            resume=args.resume,
        )
    except BaseException as exc:
        failure = {
            "status": "FAILED",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "traceback": traceback.format_exc(),
        }
        _write_json_atomic(args.checkpoint, failure)
        print(f"[S1 FAILED] {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
        traceback.print_exc()
        return 1
    summary = {
        "decision": payload["decision"],
        "runtime_seconds": payload["runtime_seconds"],
        "gates": payload["gates"],
        "covid_sensitivity": payload["covid_sensitivity"],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
