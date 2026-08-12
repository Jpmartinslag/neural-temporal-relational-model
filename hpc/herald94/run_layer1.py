"""HERALD 94, Layer 1: one Slurm task per (scenario, seed).

Every arm sees the same released observations, the same masks, the same training window and
the same rolling origins. The realised target is opened only after all five arms and all
three controls have produced their predictions.

The feature table is rebuilt at every origin from a view truncated at that origin's decision
period, rather than built once and sliced. Slicing a table built at the end of the panel
would be faster and would leak: a rolling statistic computed with the whole series in scope
is not the statistic that was available at the decision date, however carefully its own
window is bounded.

Training happens once, on the periods before the first scoring origin, and no arm is refitted
as the origins roll forward. Refitting at every origin would turn the comparison into one
about training budget.
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
    FINAL_SEEDS, SCENARIOS, NonlinearConfig, generate_nonlinear, model_inputs,
)
from src.modeles.france_ze2020 import herald94_composite as arms  # noqa: E402
from src.modeles.france_ze2020 import herald94_temporal_features as feat  # noqa: E402

PRIMARY_SIGNAL = "headcount"
N_SCORE = 12
TRAIN_START = 24          # enough history for a 12-period trend and an 8-period volatility
HIDDEN = arms.HIDDEN

# The interaction the decisive control destroys. Unemployment's block carries `C4`'s second
# factor; headcount's regime channels carry `C6`'s gate. Headcount's own growth is left
# alone, because permuting it would destroy the target's own predictor and every arm would
# collapse together, which would prove nothing about interactions.
INTERACTION_PLAN = {
    "unemployment": feat.PER_SIGNAL_FEATURES,
    "headcount": ("regime_expansion", "regime_deceleration",
                  "regime_contraction", "regime_recovery"),
}


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


def task_grid(scenarios=SCENARIOS, seeds=FINAL_SEEDS) -> list[tuple]:
    return [(scenario, seed) for scenario in scenarios for seed in seeds]


def tables_for(dataset, origins: list[int], first_origin: int,
               permute: dict | None, permute_seed: int) -> tuple[dict, dict[int, dict]]:
    """The training table, and one evaluation table per origin, each causally truncated."""
    training = feat.build_feature_table(
        model_inputs(dataset, first_origin - 1), permute=permute, permute_seed=permute_seed)
    evaluation = {
        origin: feat.build_feature_table(
            model_inputs(dataset, origin - 1), permute=permute, permute_seed=permute_seed)
        for origin in origins}
    return training, evaluation


def design(table: dict, target: np.ndarray, periods: list[int],
           columns: tuple[int, ...]) -> dict[str, np.ndarray]:
    return arms.assemble_rows(table, target, periods, columns)


def evaluation_rows(evaluation: dict[int, dict], target: np.ndarray,
                    columns: tuple[int, ...]) -> dict[str, np.ndarray]:
    blocks = [arms.assemble_rows(table, target, [origin], columns)
              for origin, table in sorted(evaluation.items())]
    return {"x": np.concatenate([block["x"] for block in blocks]),
            "y": np.concatenate([block["y"] for block in blocks]),
            "keys": np.concatenate([block["keys"] for block in blocks])}


def fit_and_score(name: str, train: dict, test: dict, seed: int,
                  epochs: int) -> dict:
    """One arm, fitted on the training window and scored out of sample."""
    scaler = arms.standardise(train["x"])
    train_x, test_x = arms.apply_scaler(train["x"], scaler), arms.apply_scaler(test["x"], scaler)
    started = time.time()
    periods = train.get("keys")
    periods = periods[:, 0] if periods is not None and len(periods) else None
    if name == "mlp_nonlinear":
        fitted = arms.fit_mlp_selected(train_x, train["y"], HIDDEN, seed, epochs=epochs,
                                       periods=periods)
        in_sample = arms.predict_mlp(train_x, fitted)
        prediction = arms.predict_mlp(test_x, fitted)
        parameters = fitted["parameters"]
        state = fitted
    else:
        alpha = arms.choose_alpha(train_x, train["y"], periods)
        fitted = arms.fit_ridge(train_x, train["y"], alpha)
        in_sample = arms.predict_ridge(train_x, fitted)
        prediction = arms.predict_ridge(test_x, fitted)
        parameters = int(train_x.shape[1] + 1)
        state = {"alpha": alpha, **fitted}
    # The same fairness test as the penalty grid, applied to the network's budget: if the
    # selected stopping epoch is the largest on offer, the fit was cut short and the
    # comparison would be about the budget rather than about the model. The smoke ran at a
    # ceiling of 300 and hit it, which is why the grid runs at the full budget.
    configuration = ({"weight_decay": fitted["selection"]["weight_decay"],
                      "epochs": fitted["selection"]["epochs"],
                      "epochs_at_budget_ceiling":
                          fitted["selection"]["epochs"] >= epochs}
                     if name == "mlp_nonlinear" and "selection" in fitted
                     else {"alpha": state.get("alpha"),
                           "alpha_at_grid_boundary":
                               state.get("alpha") == max(arms.RIDGE_ALPHAS)})
    return {
        "arm": name,
        "out_of_sample": arms.loss_of(prediction, test["y"]),
        "in_sample": arms.loss_of(in_sample, train["y"]),
        "parameters": parameters, "seconds": round(time.time() - started, 2),
        "configuration": configuration,
        "prediction": prediction, "state": state, "scaler": scaler,
    }


def per_origin_losses(prediction: np.ndarray, test: dict) -> dict[int, float]:
    out = {}
    for origin in np.unique(test["keys"][:, 0]):
        rows = test["keys"][:, 0] == origin
        out[int(origin)] = float(np.mean((prediction[rows] - test["y"][rows]) ** 2))
    return out


def explain(fitted: dict, test_x: np.ndarray, columns: tuple[str, ...],
            top: int = 12) -> dict:
    """The mathematical account of the non-linear arm, from its fitted parameters.

    Nothing here is an attribution heuristic: for one hidden layer the first and second
    derivatives are closed-form, so the marginal effects and the interaction ranking are
    exact properties of the fitted function.
    """
    params = fitted["params"]
    gradients = arms.marginal_effects(params, test_x)
    mean_effect = gradients.mean(0)
    absolute = np.abs(gradients).mean(0)
    hessian = arms.interaction_strength(params, test_x)
    upper = np.triu(hessian, k=1)
    order = np.argsort(upper, axis=None)[::-1][:top]
    pairs = [(int(index // len(hessian)), int(index % len(hessian))) for index in order]
    ranked = [{"first": columns[a] if a < len(columns) else f"available[{a - len(columns)}]",
               "second": columns[b] if b < len(columns) else f"available[{b - len(columns)}]",
               "strength": float(upper[a, b])} for a, b in pairs if upper[a, b] > 0.0]
    ranking = np.argsort(absolute)[::-1][:top]
    curves = {}
    for column in ranking[:6]:
        curve = arms.partial_effect_curve(params, test_x, int(column))
        label = (columns[column] if column < len(columns)
                 else f"available[{column - len(columns)}]")
        curves[label] = {"x": curve["x"], "y": curve["y"]}
    surfaces = {}
    for entry in ranked[:2]:
        first = _index_of(columns, entry["first"], test_x.shape[1])
        second = _index_of(columns, entry["second"], test_x.shape[1])
        if first is None or second is None:
            continue
        surface = arms.interaction_surface(params, test_x, first, second)
        surfaces[f"{entry['first']}|{entry['second']}"] = surface
    return {
        "mean_marginal_effect": {
            (columns[index] if index < len(columns)
             else f"available[{index - len(columns)}]"): float(mean_effect[index])
            for index in ranking},
        "mean_absolute_marginal_effect": {
            (columns[index] if index < len(columns)
             else f"available[{index - len(columns)}]"): float(absolute[index])
            for index in ranking},
        "top_interactions": ranked,
        "partial_effect_curves": curves,
        "interaction_surfaces": surfaces,
    }


def _index_of(columns: tuple[str, ...], label: str, width: int) -> int | None:
    if label in columns:
        return columns.index(label)
    if label.startswith("available["):
        return len(columns) + int(label[len("available["):-1])
    return None


def ablate(train: dict, test: dict, columns: tuple[str, ...], signals: tuple[str, ...],
           seed: int, selection: dict, reference: float) -> dict[str, float]:
    """Refit the non-linear arm with one signal's columns removed at a time.

    The regularisation is *inherited* from the main fit rather than re-selected. An ablation
    must change one thing -- which signal is present -- and re-running the selection would
    change the penalty and the stopping epoch as well, so a difference could no longer be
    attributed to the removed signal. It is also what makes the ablation affordable: the
    selection sweep is twenty fits, and five re-selections dominated the task's cost.
    """
    out = {}
    width = len(columns)
    decay = selection.get("weight_decay", arms.WEIGHT_DECAY)
    stop = max(int(selection.get("epochs", arms.EPOCHS)), arms.MONITOR_EVERY)
    for signal in signals:
        keep = [index for index, name in enumerate(columns)
                if not name.startswith(f"{signal}.")]
        keep_full = keep + [width + index for index in keep]
        scaler = arms.standardise(train["x"][:, keep_full])
        fitted = arms.fit_mlp(arms.apply_scaler(train["x"][:, keep_full], scaler),
                              train["y"], HIDDEN, seed, epochs=stop, weight_decay=decay)
        prediction = arms.predict_mlp(
            arms.apply_scaler(test["x"][:, keep_full], scaler), fitted)
        out[signal] = arms.gain_over(
            reference, arms.loss_of(prediction, test["y"])["mse"])
    return out


def run_task(scenario: str, seed: int, n_zones: int, epochs: int, n_score: int) -> dict:
    started = time.time()
    dataset = generate_nonlinear(NonlinearConfig(
        seed=seed, n_zones=n_zones, scenario=scenario))
    block = dataset["signals"][PRIMARY_SIGNAL]
    target = feat.target_growth(np.asarray(block["values"], float),
                                np.asarray(block["availability_mask"], bool),
                                block["family"], PRIMARY_SIGNAL)
    n_periods = len(dataset["metadata"]["years"])
    origins = list(range(n_periods - n_score, n_periods))
    first_origin = origins[0]
    train_periods = list(range(TRAIN_START, first_origin))

    def evaluate(permute: dict | None, permute_seed: int) -> dict:
        training, evaluation = tables_for(dataset, origins, first_origin,
                                          permute, permute_seed)
        columns = training["columns"]
        base = tuple(training["base_index"])
        nonlinear = tuple(training["nonlinear_composite_index"])
        base_and_products = base + nonlinear

        train_base = design(training, target, train_periods, base)
        test_base = evaluation_rows(evaluation, target, base)
        train_full = design(training, target, train_periods, base_and_products)
        test_full = evaluation_rows(evaluation, target, base_and_products)

        best_column = arms.select_best_single(
            arms.apply_scaler(train_base["x"], arms.standardise(train_base["x"])),
            train_base["y"], len(base))
        single = tuple([base[best_column]])
        train_single = design(training, target, train_periods, single)
        test_single = evaluation_rows(evaluation, target, single)
        duplicated = base + tuple([base[best_column]] * len(nonlinear))
        train_duplicated = design(training, target, train_periods, duplicated)
        test_duplicated = evaluation_rows(evaluation, target, duplicated)

        results = {
            "best_single": fit_and_score("best_single", train_single, test_single,
                                         seed, epochs),
            "ridge_linear": fit_and_score("ridge_linear", train_base, test_base,
                                          seed, epochs),
            "ridge_composite": fit_and_score("ridge_composite", train_full, test_full,
                                             seed, epochs),
            "mlp_nonlinear": fit_and_score("mlp_nonlinear", train_base, test_base,
                                           seed, epochs),
            "duplicated": fit_and_score("duplicated", train_duplicated, test_duplicated,
                                        seed, epochs),
        }
        # The null half of the pre-registered structural claim: the four composites that are
        # linear functions of existing columns must not move a linear model.
        train_linear_composite = design(
            training, target, train_periods,
            base + tuple(training["linear_composite_index"]))
        test_linear_composite = evaluation_rows(
            evaluation, target, base + tuple(training["linear_composite_index"]))
        results["ridge_linear_composites_only"] = fit_and_score(
            "ridge_linear_composites_only", train_linear_composite,
            test_linear_composite, seed, epochs)
        return {"results": results, "columns": columns, "best_column": columns[base[best_column]],
                "train_base": train_base, "test_base": test_base,
                "training": training}

    main = evaluate(None, 0)
    reference = main["results"]["best_single"]["out_of_sample"]["mse"]
    linear_mse = main["results"]["ridge_linear"]["out_of_sample"]["mse"]

    summary = {}
    for name, result in main["results"].items():
        summary[name] = {
            "out_of_sample": result["out_of_sample"], "in_sample": result["in_sample"],
            "parameters": result["parameters"], "seconds": result["seconds"],
            "configuration": result["configuration"],
            "gain_over_best_single": arms.gain_over(reference,
                                                    result["out_of_sample"]["mse"]),
            "gain_over_ridge_linear": arms.gain_over(linear_mse,
                                                     result["out_of_sample"]["mse"]),
            # Every arm is scored on the same rows: a row survives on the target being
            # observed, which does not depend on which columns the arm reads.
            "per_origin_mse": per_origin_losses(result["prediction"], main["test_base"]),
        }

    # ── controls, each refitted from scratch on the corrupted inputs ─────────
    controls = {}
    destroyed = evaluate(INTERACTION_PLAN, seed)
    controls["interaction_destroyed"] = {
        name: {"out_of_sample": result["out_of_sample"],
               "gain_over_best_single": arms.gain_over(
                   destroyed["results"]["best_single"]["out_of_sample"]["mse"],
                   result["out_of_sample"]["mse"]),
               "gain_over_ridge_linear": arms.gain_over(
                   destroyed["results"]["ridge_linear"]["out_of_sample"]["mse"],
                   result["out_of_sample"]["mse"])}
        for name, result in destroyed["results"].items()}

    for label, corrupt in (("temporal_alignment_destroyed", arms.permute_across_periods),
                           ("zones_shuffled", None)):
        train = {"x": (arms.permute_zones(main["train_base"]["x"], seed) if corrupt is None
                       else corrupt(main["train_base"]["x"], main["train_base"]["keys"], seed)),
                 "y": main["train_base"]["y"], "keys": main["train_base"]["keys"]}
        test = {"x": (arms.permute_zones(main["test_base"]["x"], seed + 1) if corrupt is None
                      else corrupt(main["test_base"]["x"], main["test_base"]["keys"], seed + 1)),
                "y": main["test_base"]["y"]}
        placebo_single = fit_and_score("ridge_linear", train, test, seed, epochs)
        placebo_mlp = fit_and_score("mlp_nonlinear", train, test, seed, epochs)
        controls[label] = {
            "ridge_linear": placebo_single["out_of_sample"],
            "mlp_nonlinear": placebo_mlp["out_of_sample"],
            "mlp_gain_over_ridge": arms.gain_over(placebo_single["out_of_sample"]["mse"],
                                                  placebo_mlp["out_of_sample"]["mse"]),
        }

    scaler = main["results"]["mlp_nonlinear"]["scaler"]
    test_x = arms.apply_scaler(main["test_base"]["x"], scaler)
    base_columns = tuple(main["columns"][index] for index in main["training"]["base_index"])
    explanation = explain(main["results"]["mlp_nonlinear"]["state"], test_x, base_columns)
    ablation = ablate(main["train_base"], main["test_base"], base_columns,
                      main["training"]["signals"], seed,
                      main["results"]["mlp_nonlinear"]["state"].get("selection", {}),
                      main["results"]["mlp_nonlinear"]["out_of_sample"]["mse"])

    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
    return {
        "kind": "herald94_layer1_task",
        "scenario": scenario, "seed": seed, "n_zones": n_zones,
        "primary_signal": PRIMARY_SIGNAL, "origins": origins,
        "train_periods": [train_periods[0], train_periods[-1]],
        "best_single_column": main["best_column"],
        "environment": {"python": platform.python_version(), "numpy": np.__version__},
        "arms": summary,
        "controls": controls,
        "explanation": explanation,
        "ablation_gain_when_signal_removed": ablation,
        "calibration": dataset["calibration"],
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
    parser.add_argument("--seeds", type=int, nargs="*", default=list(FINAL_SEEDS))
    parser.add_argument("--scenarios", type=str, nargs="*", default=list(SCENARIOS))
    parser.add_argument("--dry-run", action="store_true")
    arguments = parser.parse_args()

    grid = task_grid(tuple(arguments.scenarios), tuple(arguments.seeds))
    if arguments.dry_run:
        print(json.dumps({"kind": "herald94_plan", "n_tasks": len(grid),
                          "first": grid[0], "last": grid[-1]}, indent=2))
        return 0
    if arguments.task_id is None or arguments.out_dir is None:
        parser.error("--task-id and --out-dir are required unless --dry-run")
    if not 0 <= arguments.task_id < len(grid):
        parser.error(f"task-id must lie in [0, {len(grid) - 1}]")

    scenario, seed = grid[arguments.task_id]
    report = run_task(scenario, seed, arguments.n_zones, arguments.epochs,
                      arguments.n_score)
    atomic_json(report, arguments.out_dir / f"layer1_{scenario}_{seed}.json")
    table = report["arms"]
    print(f"{scenario:16s} seed={seed} best={report['best_single_column']}")
    for name, entry in table.items():
        print(f"  {name:28s} mse={entry['out_of_sample']['mse']:.6f} "
              f"gain_vs_single={entry['gain_over_best_single']:+.4f} "
              f"gain_vs_linear={entry['gain_over_ridge_linear']:+.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
