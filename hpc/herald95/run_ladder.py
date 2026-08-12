"""HERALD 95: one Slurm task per (scenario, relational scale, seed).

Nothing about the architecture, the features, the noise, the metrics, the regularisation or
the gates changes from HERALD 94. One number varies: ``relational_scale``. Every arm, every
fold rule, every threshold and every control is imported rather than reimplemented, so a
difference between the two stages cannot come from a difference in the code that measures.

Each task also generates the *same seed and scenario at scale zero* and keeps it beside the
scaled world. The two are identical in every draw except the relational loading, so their
difference in the observations is the relational effect exactly. That paired baseline is what
makes "is the relation observable at this scale" a measurement rather than an inference.

Four arms:

``ridge_linear``      the reference, as in HERALD 94.
``mlp_nonlinear``     the candidate, unchanged.
``oracle_relational`` ridge over the same features **plus the true relational term**. It is
                      not a candidate model. It exists to answer one question -- could
                      anything have used this mechanism at this scale, given the observable
                      target -- and it is never scored as a peer, never selected on, and
                      never applied to France.
``herald_scorer``     the relational arm of HERALD 93, unchanged, for edge recovery.

The oracle is the pivot of the whole design. If it cannot beat the linear arm, the mechanism
does not reach the observations at that scale and no model's failure there says anything
about the model. If it can and the network cannot, the failure is the network's.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import resource
import sys
import tempfile
import time
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.data.synthetic.generate_france_multisignal_v94 import (  # noqa: E402
    NonlinearConfig, generate_nonlinear, model_inputs,
)
from src.modeles.france_ze2020 import herald94_composite as arms  # noqa: E402
from src.modeles.france_ze2020 import herald94_temporal_features as feat  # noqa: E402
from src.modeles.france_ze2020 import herald95_scale_ladder as ladder  # noqa: E402

sys.path.insert(0, str(REPO_ROOT / "hpc" / "herald94"))
from run_layer1 import (  # noqa: E402
    INTERACTION_PLAN, N_SCORE, PRIMARY_SIGNAL, TRAIN_START, evaluation_rows,
    fit_and_score, per_origin_losses, tables_for,
)

EDGE_EPOCHS = 30
EDGE_WIDTH = 64
SUPPORT_K = 40


def atomic_json(payload: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=path.name, suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(handle, "w") as stream:
            json.dump(payload, stream, indent=2, default=lambda value: value.tolist())
        os.replace(temporary, path)
    except Exception:
        try: os.unlink(temporary)
        except FileNotFoundError: pass
        raise


def task_grid(scenarios=ladder.LADDER_SCENARIOS, scales=ladder.SCALES,
              seeds=ladder.FINAL_SEEDS) -> list[tuple]:
    return [(scenario, scale, seed)
            for scenario in scenarios for scale in scales for seed in seeds]


def build(scenario: str, scale: float, seed: int, n_zones: int) -> dict:
    return generate_nonlinear(NonlinearConfig(
        seed=seed, n_zones=n_zones, scenario=scenario, relational_scale=scale,
        paired_streams=True))


def oracle_design(base: dict, table: dict, dataset: dict, periods: list[int],
                  signal: str) -> dict[str, np.ndarray]:
    """The base design with the true relational term at ``t - 1`` appended.

    At ``t - 1`` and not at ``t``: the relational term of period ``t - 1`` is what moved the
    latent path whose growth is realised at ``t``, so this is the causally correct column and
    not a look-ahead. The oracle is allowed to know the mechanism; it is not allowed to know
    the future.
    """
    truth = ladder.relational_regressor(dataset, signal)
    rows = []
    for period in periods:
        keys = base["keys"]
        selected = keys[:, 0] == period
        zones = keys[selected, 1]
        rows.append(truth[period - 1][zones])
    column = np.concatenate(rows)[:, None] if rows else np.zeros((0, 1))
    return {"x": np.concatenate([base["x"], column], axis=1),
            "y": base["y"], "keys": base["keys"]}


def edge_recovery(dataset: dict, seed: int, n_zones: int, origins: list[int],
                  n_score: int) -> dict:
    """HERALD 93's relational arm, unchanged, on this scale's world."""
    try:
        import torch
    except ImportError:
        return {"skipped": "torch absent"}
    from src.modeles.france_ze2020 import herald93_benchmark as bench

    torch.set_num_threads(1)
    torch.manual_seed(seed)
    torch.use_deterministic_algorithms(True, warn_only=True)

    names = list(dataset["signals"])
    support = bench.candidate_support(dataset["truth"]["prior"], k=SUPPORT_K)
    first_score = origins[0]
    view = bench.PanelView(model_inputs(dataset, first_score - 1), support, names)
    pairs = np.array(np.nonzero(support))
    prior = np.asarray(dataset["truth"]["prior"], float)[support]
    model = bench.HeraldMultisignal(len(names), EDGE_WIDTH, pairs, prior, n_zones)
    trained = bench.train_neural("herald", model, view, first_score - 1, EDGE_EPOCHS, seed)

    last = origins[-1]
    scoring = bench.PanelView(model_inputs(dataset, last - 1), support, names)
    scores = bench.edge_matrix_from(model, scoring, last)
    metrics = bench.relational_metrics(scores, dataset["truth"], support, last, keep=0)
    metrics["cost_seconds"] = trained["seconds"]
    metrics["support_size"] = int(support.sum())
    return metrics


def run_task(scenario: str, scale: float, seed: int, n_zones: int, epochs: int,
             n_score: int) -> dict:
    started = time.time()
    scaled = build(scenario, scale, seed, n_zones)
    baseline = build(scenario, 0.0, seed, n_zones)

    signals = list(scaled["signals"])
    diagnostics = ladder.ladder_diagnostics({0.0: baseline, scale: scaled}, signals)
    pairing = ladder.worlds_are_paired(scaled, baseline)

    block = scaled["signals"][PRIMARY_SIGNAL]
    target = feat.target_growth(np.asarray(block["values"], float),
                                np.asarray(block["availability_mask"], bool),
                                block["family"], PRIMARY_SIGNAL)
    n_periods = len(scaled["metadata"]["years"])
    origins = list(range(n_periods - n_score, n_periods))
    first_origin = origins[0]
    train_periods = list(range(TRAIN_START, first_origin))

    def evaluate(permute: dict | None, permute_seed: int) -> dict:
        training, evaluation = tables_for(scaled, origins, first_origin,
                                          permute, permute_seed)
        base = tuple(training["base_index"])
        train_base = arms.assemble_rows(training, target, train_periods, base)
        test_base = evaluation_rows(evaluation, target, base)
        results = {
            "ridge_linear": fit_and_score("ridge_linear", train_base, test_base,
                                          seed, epochs),
            "mlp_nonlinear": fit_and_score("mlp_nonlinear", train_base, test_base,
                                           seed, epochs),
        }
        # The oracle sees the same rows, the same folds and the same penalty rule; it
        # differs from the linear arm by exactly one column, the true relational term.
        train_oracle = oracle_design(train_base, training, scaled, train_periods,
                                     PRIMARY_SIGNAL)
        test_oracle = oracle_design(test_base, evaluation[origins[0]], scaled, origins,
                                    PRIMARY_SIGNAL)
        results["oracle_relational"] = fit_and_score("oracle_relational", train_oracle,
                                                     test_oracle, seed, epochs)
        return {"results": results, "train_base": train_base, "test_base": test_base}

    main = evaluate(None, 0)
    reference = main["results"]["ridge_linear"]["out_of_sample"]["mse"]
    summary = {}
    for name, result in main["results"].items():
        summary[name] = {
            "out_of_sample": result["out_of_sample"], "in_sample": result["in_sample"],
            "configuration": result["configuration"], "seconds": result["seconds"],
            "gain_over_ridge_linear": arms.gain_over(reference,
                                                     result["out_of_sample"]["mse"]),
            "per_origin_mse": per_origin_losses(result["prediction"], main["test_base"]),
        }

    destroyed = evaluate(INTERACTION_PLAN, seed)
    destroyed_reference = destroyed["results"]["ridge_linear"]["out_of_sample"]["mse"]
    controls = {"interaction_destroyed": {
        name: {"out_of_sample": result["out_of_sample"],
               "gain_over_ridge_linear": arms.gain_over(
                   destroyed_reference, result["out_of_sample"]["mse"])}
        for name, result in destroyed["results"].items()}}

    edges = edge_recovery(scaled, seed, n_zones, origins, n_score)

    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
    return {
        "kind": "herald95_ladder_task",
        "scenario": scenario, "relational_scale": scale, "seed": seed,
        "n_zones": n_zones, "primary_signal": PRIMARY_SIGNAL, "origins": origins,
        "environment": {"python": platform.python_version(), "numpy": np.__version__},
        "observable_diagnostics": diagnostics,
        "worlds_are_paired": pairing,
        "arms": summary,
        "controls": controls,
        "edge_recovery": edges,
        "calibration": scaled["calibration"],
        "cost": {"peak_memory_mb": round(peak, 1),
                 "total_seconds": round(time.time() - started, 1)},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-id", type=int)
    parser.add_argument("--out-dir", type=Path)
    parser.add_argument("--n-zones", type=int, default=280)
    parser.add_argument("--n-score", type=int, default=N_SCORE)
    parser.add_argument("--epochs", type=int, default=arms.EPOCHS)
    parser.add_argument("--seeds", type=int, nargs="*", default=list(ladder.FINAL_SEEDS))
    parser.add_argument("--scales", type=float, nargs="*", default=list(ladder.SCALES))
    parser.add_argument("--scenarios", type=str, nargs="*",
                        default=list(ladder.LADDER_SCENARIOS))
    parser.add_argument("--dry-run", action="store_true")
    arguments = parser.parse_args()

    grid = task_grid(tuple(arguments.scenarios), tuple(arguments.scales),
                     tuple(arguments.seeds))
    if arguments.dry_run:
        print(json.dumps({"kind": "herald95_plan", "n_tasks": len(grid),
                          "first": grid[0], "last": grid[-1]}, indent=2))
        return 0
    if arguments.task_id is None or arguments.out_dir is None:
        parser.error("--task-id and --out-dir are required unless --dry-run")
    if not 0 <= arguments.task_id < len(grid):
        parser.error(f"task-id must lie in [0, {len(grid) - 1}]")

    scenario, scale, seed = grid[arguments.task_id]
    report = run_task(scenario, scale, seed, arguments.n_zones, arguments.epochs,
                      arguments.n_score)
    atomic_json(report, arguments.out_dir / f"ladder_{scenario}_s{scale}_{seed}.json")
    observable = report["observable_diagnostics"]["per_scale"][str(scale)]["observable"]
    print(f"{scenario:16s} scale={scale:<4g} seed={seed} "
          f"snr={observable[PRIMARY_SIGNAL]['snr']:.4f} "
          f"clip={report['calibration']['clipped_share'][PRIMARY_SIGNAL]:.3f}")
    for name, entry in report["arms"].items():
        print(f"  {name:20s} mse={entry['out_of_sample']['mse']:.6f} "
              f"vs_linear={entry['gain_over_ridge_linear']:+.4f}")
    if "auprc" in report["edge_recovery"]:
        edges = report["edge_recovery"]
        print(f"  edges auprc={edges['auprc']:.4f} prevalence={edges['prevalence']:.4f} "
              f"f1={edges.get('edge_f1', float('nan')):.4f} "
              f"dense={edges.get('dense_correlation', float('nan')):.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
