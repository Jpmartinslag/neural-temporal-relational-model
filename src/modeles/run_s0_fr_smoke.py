"""Technical S0 smoke for FR graph-temporal training.

S0 is an engineering gate, not a scientific comparison. It runs one FR
evaluation year and one seed twice to verify causal training, determinism,
finite metrics, parameter budget, runtime and memory.
"""
from __future__ import annotations

import argparse
import json
import resource
import sys
import time
from pathlib import Path

from src.modeles.graph_temporal_train import TrainConfig, train_rolling_origin


MODELS = ("A0Neural", "GConvGRU", "EvolveGCNH")
DEFAULT_OUTPUT = Path("data/processed/graph_temporal_s0/s0_fr_results.json")
RUNTIME_LIMIT_SECONDS = 600.0
RSS_DELTA_LIMIT_GB = 4.0


def _rss_gb() -> float:
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return rss / (1024 ** 3 if sys.platform == "darwin" else 1024 ** 2)


def run_s0(
    *,
    eval_year: int = 2025,
    seed: int = 42,
    output_path: Path = DEFAULT_OUTPUT,
    max_epochs: int = 200,
    patience: int = 20,
) -> dict:
    started = time.perf_counter()
    rss_before = _rss_gb()
    config = TrainConfig(
        max_epochs=max_epochs,
        patience=patience,
        hidden_dim=4,
        sector_embed_dim=4,
        dropout=0.3,
        clamp_frac=0.15,
        seed=seed,
    )

    first = {}
    second = {}
    for model_name in MODELS:
        _, result = train_rolling_origin(
            model_name, "FR", eval_year, config=config
        )
        first[model_name] = result.to_dict()
    for model_name in MODELS:
        _, result = train_rolling_origin(
            model_name, "FR", eval_year, config=config
        )
        second[model_name] = result.to_dict()

    runtime = time.perf_counter() - started
    rss_delta = max(0.0, _rss_gb() - rss_before)

    checks = {
        "all_metrics_finite": all(
            result["evaluation_wmape"] == result["evaluation_wmape"]
            and result["ridge_wmape"] == result["ridge_wmape"]
            for result in first.values()
        ),
        "all_leakage_checks_pass": all(
            result["leakage_ok"] for result in first.values()
        ),
        "all_parameter_budgets_pass": all(
            result["n_parameters"] <= 5000 for result in first.values()
        ),
        "deterministic_state": all(
            first[name]["state_checksum"] == second[name]["state_checksum"]
            for name in MODELS
        ),
        "deterministic_metrics": all(
            first[name]["evaluation_wmape"] == second[name]["evaluation_wmape"]
            for name in MODELS
        ),
        "runtime_within_limit": runtime < RUNTIME_LIMIT_SECONDS,
        "rss_within_limit": rss_delta < RSS_DELTA_LIMIT_GB,
    }
    decision = "S0_FR_PASS" if all(checks.values()) else "S0_FR_FAIL"
    payload = {
        "decision": decision,
        "country": "FR",
        "eval_year": eval_year,
        "seed": seed,
        "config": {
            "max_epochs": max_epochs,
            "patience": patience,
            "hidden_dim": config.hidden_dim,
            "sector_embed_dim": config.sector_embed_dim,
            "dropout": config.dropout,
            "clamp_frac": config.clamp_frac,
        },
        "runtime_seconds": runtime,
        "rss_delta_gb": rss_delta,
        "checks": checks,
        "results": first,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--eval-year", type=int, default=2025)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-epochs", type=int, default=200)
    parser.add_argument("--patience", type=int, default=20)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    payload = run_s0(
        eval_year=args.eval_year,
        seed=args.seed,
        output_path=args.output,
        max_epochs=args.max_epochs,
        patience=args.patience,
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["decision"] == "S0_FR_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

