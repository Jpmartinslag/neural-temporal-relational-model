"""
HERALD -- France ZE2020 training block orchestrator.

See reports/canonical/HERALD_18_FR_ZE2020_TRAINING_PLAN.md. This script
implements NO new training logic and NO new model: it imports and calls
the already-existing, already-tested run_* functions from the four
current training scripts and consolidates their metrics into one summary
table. No HPC job is launched here. No claim of final performance. No
automatic recommendation.

Orchestrates, in order:
  1. train_fr_ze2020_baselines.py            (persistence, ridge_temporal)
  2. train_fr_ze2020_relational_baselines.py  (+ ridge_relational)
  3. train_fr_ze2020_neural_relational_mlp.py (+ mlp_relational)
  4. train_fr_ze2020_sector_graph_prototype.py (persistence_sector, graph_mlp
     -- different grain, ZE x sector x year, not directly comparable to 1-3)

Output:
  data/processed/france_ze2020/fr_ze2020_training_block_summary_v1.csv
  columns: model_family, model_name, target, grain, eval_year_start,
  eval_year_end, mean_wmape, claim_status, source_script.
  claim_status is always "training_block_summary_smoke_local_only" -- this
  is a local consolidation of smoke results, never a headline claim.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.modeles.france_ze2020.train_fr_ze2020_baselines import (  # noqa: E402
    DEFAULT_EVAL_YEARS,
    RIDGE_ALPHA,
    RIDGE_MIN_TRAIN_YEARS,
    load_panel,
    run_baselines,
)
from src.modeles.france_ze2020.train_fr_ze2020_neural_relational_mlp import (  # noqa: E402
    DEFAULT_MAX_EPOCHS as NEURAL_MAX_EPOCHS,
)
from src.modeles.france_ze2020.train_fr_ze2020_neural_relational_mlp import (  # noqa: E402
    SEED as NEURAL_SEED,
)
from src.modeles.france_ze2020.train_fr_ze2020_neural_relational_mlp import (  # noqa: E402
    attach_dominant_sector_national_signal,
    load_prototype_panel,
    run_neural_relational_smoke,
)
from src.modeles.france_ze2020.train_fr_ze2020_relational_baselines import (  # noqa: E402
    load_relational_panel,
    run_relational_baselines,
)
from src.modeles.france_ze2020.train_fr_ze2020_sector_graph_prototype import (  # noqa: E402
    DEFAULT_MAX_EPOCHS as GRAPH_MAX_EPOCHS,
)
from src.modeles.france_ze2020.train_fr_ze2020_sector_graph_prototype import (  # noqa: E402
    SEED as GRAPH_SEED,
)
from src.modeles.france_ze2020.train_fr_ze2020_sector_graph_prototype import (  # noqa: E402
    build_graph_node_features,
    build_node_table,
    run_sector_graph_smoke,
)

DEFAULT_OUTPUT_DIR = REPO_ROOT / "data/processed/france_ze2020"
SUMMARY_CLAIM_STATUS = "training_block_summary_smoke_local_only"

SUMMARY_COLUMNS = [
    "model_family",
    "model_name",
    "target",
    "grain",
    "eval_year_start",
    "eval_year_end",
    "mean_wmape",
    "claim_status",
    "source_script",
]

MODEL_FAMILY = {
    "persistence": "baseline",
    "ridge": "baseline",
    "ridge_temporal": "baseline",
    "ridge_relational": "relational_baseline",
    "mlp_relational": "neural_smoke",
    "persistence_sector": "baseline",
    "graph_mlp": "graph_smoke",
}


def _summarize(
    metrics: pd.DataFrame, target: str, grain: str, source_script: str
) -> pd.DataFrame:
    if metrics.empty:
        return pd.DataFrame(columns=SUMMARY_COLUMNS)
    rows = []
    for model_name, group in metrics.groupby("model"):
        rows.append(
            {
                "model_family": MODEL_FAMILY.get(model_name, "unknown"),
                "model_name": model_name,
                "target": target,
                "grain": grain,
                "eval_year_start": int(group["eval_year"].min()),
                "eval_year_end": int(group["eval_year"].max()),
                "mean_wmape": float(group["wmape"].mean()),
                "claim_status": SUMMARY_CLAIM_STATUS,
                "source_script": source_script,
            }
        )
    return pd.DataFrame(rows)


def run_training_block(
    eval_years: list[int] = DEFAULT_EVAL_YEARS,
    min_train_years: int = RIDGE_MIN_TRAIN_YEARS,
    alpha: float = RIDGE_ALPHA,
    max_epochs: int | None = None,
    seed: int | None = None,
) -> pd.DataFrame:
    neural_epochs = max_epochs if max_epochs is not None else NEURAL_MAX_EPOCHS
    graph_epochs = max_epochs if max_epochs is not None else GRAPH_MAX_EPOCHS
    neural_seed = seed if seed is not None else NEURAL_SEED
    graph_seed = seed if seed is not None else GRAPH_SEED

    summaries = []

    # 1. Temporal baselines (ZE-level)
    panel = load_panel()
    _, metrics_1 = run_baselines(panel, eval_years, min_train_years, alpha)
    summaries.append(
        _summarize(
            metrics_1,
            target="observed_value",
            grain="ze_x_year",
            source_script="train_fr_ze2020_baselines.py",
        )
    )

    # 2. Relational baselines (ZE-level + ZE-to-ZE)
    relational_panel = load_relational_panel()
    _, metrics_2 = run_relational_baselines(relational_panel, eval_years, min_train_years, alpha)
    summaries.append(
        _summarize(
            metrics_2,
            target="observed_value",
            grain="ze_x_year",
            source_script="train_fr_ze2020_relational_baselines.py",
        )
    )

    # 3. Neural relational smoke (ZE-level + ZE-to-ZE + sector)
    prototype_panel = attach_dominant_sector_national_signal(load_prototype_panel())
    _, metrics_3, _ = run_neural_relational_smoke(
        prototype_panel,
        eval_years=eval_years,
        min_train_years=min_train_years,
        alpha=alpha,
        max_epochs=neural_epochs,
        seed=neural_seed,
    )
    summaries.append(
        _summarize(
            metrics_3,
            target="observed_value",
            grain="ze_x_year",
            source_script="train_fr_ze2020_neural_relational_mlp.py",
        )
    )

    # 4. Sector graph smoke (different grain: ZE x sector x year)
    nodes, _ = build_graph_node_features(build_node_table())
    _, metrics_4 = run_sector_graph_smoke(
        nodes, eval_years=eval_years, min_train_years=min_train_years, max_epochs=graph_epochs, seed=graph_seed
    )
    summaries.append(
        _summarize(
            metrics_4,
            target="sector_share",
            grain="ze_x_sector_x_year",
            source_script="train_fr_ze2020_sector_graph_prototype.py",
        )
    )

    summary = pd.concat(summaries, ignore_index=True)[SUMMARY_COLUMNS]
    return summary.sort_values(["grain", "model_family", "model_name"]).reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "France ZE2020 training block orchestrator -- runs the 4 existing "
            "smoke/baseline scripts and consolidates their metrics. No new model, "
            "no HPC, no headline claim, no recommendation."
        )
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--eval-years", type=int, nargs="+", default=DEFAULT_EVAL_YEARS)
    parser.add_argument("--min-train-years", type=int, default=RIDGE_MIN_TRAIN_YEARS)
    parser.add_argument("--alpha", type=float, default=RIDGE_ALPHA)
    parser.add_argument("--max-epochs", type=int, default=None)
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()

    summary = run_training_block(
        eval_years=args.eval_years,
        min_train_years=args.min_train_years,
        alpha=args.alpha,
        max_epochs=args.max_epochs,
        seed=args.seed,
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = args.output_dir / "fr_ze2020_training_block_summary_v1.csv"
    summary.to_csv(summary_path, index=False)

    print("TRAINING BLOCK SUMMARY -- smoke/local only, not a headline claim.")
    print(summary.to_string(index=False))
    print(f"Saved: {summary_path}")


if __name__ == "__main__":
    main()
