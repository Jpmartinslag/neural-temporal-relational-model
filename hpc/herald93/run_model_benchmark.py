"""HERALD 93: one Slurm task per (method, scenario, seed, width).

Every method sees the same released observations, the same masks, the same candidate
support, the same folds and the same origins, and none of them sees an edge label. The
truth is opened only after the method has produced its forecasts and its edge scores.

Training happens once, on the periods before the first scoring origin. The inputs then roll
forward one origin at a time and the model is *not* refitted: refitting at every origin
would change the comparison into one about training budget, and would make the classical
arm's cost incomparable with the neural ones.
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

from src.data.synthetic.generate_france_multisignal_v92 import (  # noqa: E402
    FINAL_SEEDS, MultisignalConfig, generate_multisignal, model_inputs,
)
from src.modeles.france_ze2020 import herald93_benchmark as bench  # noqa: E402

SCENARIOS = ("S0_NULL", "S1_SHARED")
METHODS = ("persistence", "sparse_var", "mtgnn", "nri", "herald")
WIDTHS = (64,)
N_SCORE = 12
# Thirty epochs for every neural arm, chosen before the grid ran and identical across
# arms. The smoke used two, which is enough to prove the mechanics and far too few to judge
# a model: HERALD forecast worse than persistence there, as an untrained network should.
EPOCHS = 30


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


def task_grid(methods=METHODS, scenarios=SCENARIOS, seeds=FINAL_SEEDS,
              widths=WIDTHS) -> list[tuple]:
    grid = []
    for method in methods:
        for scenario in scenarios:
            for seed in seeds:
                for width in (widths if method in bench.NEURAL_METHODS else (0,)):
                    grid.append((method, scenario, seed, width))
    return grid


def build_view(dataset, decision_period: int, support, names) -> bench.PanelView:
    return bench.PanelView(model_inputs(dataset, decision_period), support, names)


def run_task(method: str, scenario: str, seed: int, width: int, n_zones: int,
             epochs: int, n_score: int) -> dict:
    if width >= bench.FORBIDDEN_WIDTH:
        raise ValueError(f"width {width} is not permitted in this study")
    started = time.time()
    dataset = generate_multisignal(MultisignalConfig(
        seed=seed, n_zones=n_zones, scenario=scenario))
    names = list(dataset["signals"])
    support = bench.candidate_support(dataset["truth"]["prior"], k=40)
    n_periods = len(dataset["metadata"]["years"])
    first_score = n_periods - n_score
    origins = list(range(first_score, n_periods))

    train_view = build_view(dataset, first_score - 1, support, names)
    cost = {"parameters": 0, "epochs": 0, "seconds": 0.0}
    model = None

    if method == "sparse_var":
        fitted = bench.fit_sparse_var(train_view, first_score - 1)
        cost = {"parameters": fitted["parameters"], "epochs": 0,
                "seconds": fitted["seconds"]}
        static_scores = fitted["edge_scores"]
    elif method in bench.NEURAL_METHODS:
        import torch
        # One thread, fixed seed. The relational arms accumulate messages with index_add,
        # whose summation order over CPU threads is not fixed, and the smoke caught the
        # consequence: the same run twice gave different forecasts for NRI and for HERALD.
        # A benchmark that cannot reproduce itself cannot separate a method from noise.
        torch.set_num_threads(1)
        torch.manual_seed(seed)
        torch.use_deterministic_algorithms(True, warn_only=True)
        pairs = np.array(np.nonzero(support))
        prior = np.asarray(dataset["truth"]["prior"], float)[support]
        if method == "herald":
            model = bench.HeraldMultisignal(len(names), width, pairs, prior, n_zones)
        elif method == "nri":
            model = bench.NRILite(len(names), width, pairs, n_zones)
        else:
            model = bench.MTGNNLite(len(names), width, n_zones, support.astype(float))
        trained = bench.train_neural(method, model, train_view, first_score - 1,
                                     epochs, seed)
        cost = {"parameters": trained["parameters"], "epochs": trained["epochs"],
                "seconds": trained["seconds"], "loss_history": trained["loss_history"]}
        static_scores = None
    else:
        static_scores = np.zeros((n_zones, n_zones))

    predictions, targets, masks, persistence = [], [], [], []
    scores_by_period: dict[int, np.ndarray] = {}
    abstention_rate = []
    for origin in origins:
        view = build_view(dataset, origin - 1, support, names)
        target = dataset_growth(dataset, names, origin)
        observed = np.isfinite(target)
        previous = view.filled[:, origin - 1, :]
        if method == "persistence":
            prediction = previous
        elif method == "sparse_var":
            prediction = bench.predict_sparse_var(view, origin, fitted)
            scores_by_period[origin] = static_scores
        else:
            prediction = bench.forecast_with(model, view, origin)
            scores_by_period[origin] = bench.edge_matrix_from(model, view, origin)
            if method == "herald":
                import torch
                with torch.no_grad():
                    block, seen = view.window(origin)
                    output = model(torch.as_tensor(block, dtype=torch.float32),
                                   torch.as_tensor(seen, dtype=torch.float32),
                                   torch.as_tensor(seen, dtype=torch.float32).mean(1))
                abstention_rate.append(float((output["abstention"] > 0.5).float().mean()))
        predictions.append(prediction)
        targets.append(np.nan_to_num(target))
        masks.append(observed)
        persistence.append(previous)

    prediction = np.stack(predictions)
    target = np.stack(targets)
    mask = np.stack(masks)
    base = np.stack(persistence)
    forecast = bench.forecast_metrics(prediction, target, mask, base)
    per_signal = {
        name: bench.forecast_metrics(prediction[:, index], target[:, index],
                                     mask[:, index], base[:, index])
        for index, name in enumerate(names)}

    relational: dict = {}
    events: dict = {}
    if scores_by_period:
        last = origins[-1]
        relational = bench.relational_metrics(
            scores_by_period[last], dataset["truth"], support, last, keep=0)
        events = bench.typed_event_metrics(scores_by_period, dataset["truth"], support,
                                           origins, keep=0)

    gradients = {}
    if model is not None:
        gradients = bench.component_gradient_norms(
            model, train_view, bench.last_released_origin(train_view))

    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
    return {
        "kind": "herald93_benchmark_task",
        "method": method, "scenario": scenario, "seed": seed, "width": width,
        "n_zones": n_zones, "n_score": n_score, "origins": origins,
        "environment": {"python": platform.python_version(), "numpy": np.__version__,
                        "torch": _torch_version()},
        "cost": {**cost, "peak_memory_mb": round(peak, 1),
                 "total_seconds": round(time.time() - started, 1)},
        "capabilities": CAPABILITIES[method],
        "forecast": forecast,
        "forecast_per_signal": per_signal,
        "relational": relational,
        "events": events,
        "gradients": gradients,
        "abstention_rate": float(np.mean(abstention_rate)) if abstention_rate else None,
        "support_size": int(support.sum()),
    }


def dataset_growth(dataset, names, origin: int) -> np.ndarray:
    """The evaluation target: realised log-growth at ``origin``, from the full panel.

    Taken from the dataset rather than from a released view because the evaluator is
    allowed to know what happened; the *model* never receives this array.
    """
    out = []
    for name in names:
        block = dataset["signals"][name]
        values = np.asarray(block["values"], float)
        mask = np.asarray(block["availability_mask"], bool)
        lag = 4 if block["freq"] == "A" else 1
        logs = np.where(mask, np.log(np.maximum(values, 1e-9)), np.nan)
        out.append(logs[origin] - logs[origin - lag] if origin - lag >= 0
                   else np.full(values.shape[1], np.nan))
    return np.stack(out)


def _torch_version() -> str:
    try:
        import torch
        return torch.__version__
    except ImportError:
        return "absent"


CAPABILITIES = {
    "persistence": {"learns_graph": False, "graph_kind": None, "objective": "none",
                    "aim": "forecast floor"},
    "sparse_var": {"learns_graph": True, "graph_kind": "static", "objective": "lasso",
                   "aim": "relational recovery", "support_restricted": True},
    "mtgnn": {"learns_graph": True, "graph_kind": "static", "objective": "forecast",
              "aim": "forecast", "support_restricted": True},
    "nri": {"learns_graph": True, "graph_kind": "static", "objective": "forecast + KL",
            "aim": "relational recovery", "support_restricted": True},
    "herald": {"learns_graph": True, "graph_kind": "dynamic", "objective": "forecast",
               "aim": "relational recovery + forecast", "support_restricted": True},
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-id", type=int)
    parser.add_argument("--out-dir", type=Path)
    parser.add_argument("--n-zones", type=int, default=280)
    parser.add_argument("--n-score", type=int, default=N_SCORE)
    parser.add_argument("--epochs", type=int, default=EPOCHS)
    parser.add_argument("--widths", type=int, nargs="*", default=list(WIDTHS))
    parser.add_argument("--seeds", type=int, nargs="*", default=list(FINAL_SEEDS))
    parser.add_argument("--methods", type=str, nargs="*", default=list(METHODS))
    parser.add_argument("--scenarios", type=str, nargs="*", default=list(SCENARIOS))
    parser.add_argument("--dry-run", action="store_true")
    arguments = parser.parse_args()

    grid = task_grid(arguments.methods, arguments.scenarios, tuple(arguments.seeds),
                     tuple(arguments.widths))
    if arguments.dry_run:
        print(json.dumps({"kind": "herald93_plan", "n_tasks": len(grid),
                          "grid": grid[:8], "last": grid[-1]}, indent=2))
        return 0
    if arguments.task_id is None or arguments.out_dir is None:
        parser.error("--task-id and --out-dir are required unless --dry-run")
    if not 0 <= arguments.task_id < len(grid):
        parser.error(f"task-id must lie in [0, {len(grid) - 1}]")

    method, scenario, seed, width = grid[arguments.task_id]
    report = run_task(method, scenario, seed, width, arguments.n_zones,
                      arguments.epochs, arguments.n_score)
    name = f"bench_{method}_{scenario}_{seed}_w{width}.json"
    atomic_json(report, arguments.out_dir / name)
    print(f"{method:11s} {scenario:10s} seed={seed} w={width} "
          f"mae={report['forecast']['mae']:.5f} "
          f"skill={report['forecast']['skill_vs_persistence']:+.4f} "
          f"edgeF1={report['relational'].get('edge_f1', float('nan')):.3f} "
          f"[{report['cost']['total_seconds']}s]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
