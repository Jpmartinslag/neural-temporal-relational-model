"""HERALD 96: one Slurm task per (scenario, scale, support, seed).

Order inside a task is the order the specification fixes: the local baseline is fitted and
frozen, the residual is formed, the oracles are measured on that residual, and only then is
the arm trained. If the oracle fails the task records it and does not pretend the arm's
result means anything.
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

from src.data.synthetic.generate_multirelational_v96 import (  # noqa: E402
    FAMILIES, FINAL_SEEDS, SCALES, SCENARIOS, MultirelationalConfig,
    generate_multirelational, model_inputs,
)
from src.modeles.france_ze2020 import herald94_temporal_features as tf  # noqa: E402
from src.modeles.france_ze2020 import herald96_neural_granger as ng  # noqa: E402

N_SCORE = 12
TRAIN_START = 24
SUPPORTS = ("commuting_only", "similarity_only", "typed_union", "all_pairs")


def atomic_json(payload: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=path.name, suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(handle, "w") as stream:
            json.dump(payload, stream, indent=2, default=lambda v: v.tolist())
        os.replace(temporary, path)
    except Exception:
        try: os.unlink(temporary)
        except FileNotFoundError: pass
        raise


def task_grid(scenarios=SCENARIOS, scales=SCALES, supports=SUPPORTS,
              seeds=FINAL_SEEDS) -> list[tuple]:
    grid = []
    for scenario in scenarios:
        for scale in scales:
            for support in supports:
                for seed in seeds:
                    grid.append((scenario, scale, support, seed))
    return grid


def explained(residual: np.ndarray, column: np.ndarray) -> float:
    """Share of residual variance a single true regressor explains. The oracle."""
    column = np.asarray(column, float)[:, None]
    if column.std() < 1e-14 or residual.std() < 1e-14:
        return 0.0
    design = np.concatenate([np.ones_like(column), column], axis=1)
    beta = np.linalg.lstsq(design, residual, rcond=None)[0]
    return float(1.0 - np.mean((residual - design @ beta) ** 2)
                 / np.mean((residual - residual.mean()) ** 2))


def run_task(scenario: str, scale: float, support_name: str, seed: int, n_zones: int,
             epochs: int, n_score: int) -> dict:
    started = time.time()
    data = generate_multirelational(MultirelationalConfig(
        n_zones=n_zones, seed=seed, scenario=scenario, relational_scale=scale))
    block = data["signals"]["headcount"]
    target = tf.target_growth(np.asarray(block["values"], float),
                              np.asarray(block["availability_mask"], bool),
                              block["family"], "headcount")
    n_periods = len(data["metadata"]["years"])
    origins = list(range(n_periods - n_score, n_periods))
    first = origins[0]
    train_periods = list(range(TRAIN_START, first))

    train_table = tf.build_feature_table(model_inputs(data, first - 1))
    baseline = ng.fit_frozen_baseline(train_table, target, train_periods)
    frozen_checksum = baseline["checksum"]

    train_residual = ng.residual_target(baseline, train_table, target, train_periods)
    evaluation = {origin: tf.build_feature_table(model_inputs(data, origin - 1))
                  for origin in origins}
    parts = [ng.residual_target(baseline, evaluation[o], target, [o]) for o in origins]
    test_residual = np.concatenate([p["residual"] for p in parts])
    test_keys = np.concatenate([p["keys"] for p in parts])

    # ── oracles first ────────────────────────────────────────────────────────
    def column_for(field: str) -> np.ndarray:
        array = np.asarray(data["truth"][field] if field == "total_arriving"
                           else data["truth"]["per_family"][field], float)
        return np.array([array[int(p) - 1, int(z)] for p, z in test_keys])

    oracles = {family: explained(test_residual, column_for(family)) for family in FAMILIES}
    oracles["all_families"] = explained(test_residual, column_for("total_arriving"))
    oracle_ok = oracles["all_families"] > 0.0 or scenario == "M0_NULL"

    # ── the arm ──────────────────────────────────────────────────────────────
    view = model_inputs(data, first - 1)
    similarity = ng.causal_similarity(view, first - 1)
    supports = ng.build_supports(data["truth"]["commuting"], similarity, n_zones,
                                 include_all_pairs=(support_name == "all_pairs"))
    support = supports[support_name]
    pairs = np.array(np.nonzero(support))

    def residual_cube(table_by_origin, period_list) -> tuple[np.ndarray, np.ndarray]:
        cube = np.zeros((len(period_list), n_zones, len(ng.HORIZONS)))
        mask = np.zeros_like(cube)
        for index, origin in enumerate(period_list):
            for horizon_index, horizon in enumerate(ng.HORIZONS):
                ahead = origin + horizon - 1
                if ahead >= n_periods:
                    continue
                table = table_by_origin.get(origin)
                if table is None:
                    continue
                got = ng.residual_target(baseline, table, target, [ahead])
                for value, (period, zone) in zip(got["residual"], got["keys"]):
                    cube[index, int(zone), horizon_index] = value
                    mask[index, int(zone), horizon_index] = 1.0
        return cube, mask

    train_tables = {o: train_table for o in train_periods}
    train_cube, train_mask = residual_cube(train_tables, train_periods)
    test_cube, test_mask = residual_cube(evaluation, origins)

    train_design = ng.pair_features(train_table, pairs, train_periods)
    fan_in = pairs.shape[1] / max(n_zones, 1)
    params = ng.initialise(train_design["x"].shape[-1], ng.HIDDEN, len(ng.HORIZONS), seed,
                           fan_in=fan_in)
    fitted = ng.fit(params, train_design["x"], pairs, train_cube, train_mask, n_zones,
                    epochs=epochs)

    test_blocks = [ng.pair_features(evaluation[o], pairs, [o])["x"][0] for o in origins]
    test_x = np.stack(test_blocks)
    prediction, contribution = ng.predict_residual(fitted["params"], test_x, pairs, n_zones)
    error = (prediction - test_cube) * test_mask
    denominator = max(float(test_mask.sum()), 1.0)
    arm_mse = float((error ** 2).sum() / denominator)
    null_mse = float(((test_cube * test_mask) ** 2).sum() / denominator)
    residual_gain = float(1.0 - arm_mse / max(null_mse, 1e-18))
    per_horizon = {
        str(horizon): float(1.0 - (error[:, :, i] ** 2).sum()
                            / max(((test_cube[:, :, i] * test_mask[:, :, i]) ** 2).sum(), 1e-18))
        for i, horizon in enumerate(ng.HORIZONS)}

    scores = ng.edge_scores(fitted["params"], test_x, pairs.shape[1])

    # ── recovery ─────────────────────────────────────────────────────────────
    truth_matrix = np.zeros((n_zones, n_zones), bool)
    family_of = {}
    for family in FAMILIES:
        for source, sink in data["truth"]["relations"]["edges"][family]:
            truth_matrix[source, sink] = True
            family_of[(source, sink)] = family
    labels = truth_matrix[pairs[0], pairs[1]].astype(float)
    types = ng.edge_types(supports, pairs) if support_name != "all_pairs" else {
        "from_commuting": supports["commuting_only"][pairs[0], pairs[1]],
        "from_similarity": np.zeros(pairs.shape[1], bool)}

    def average_precision(score, label):
        if label.sum() == 0 or len(label) == 0:
            return float("nan")
        order = np.argsort(-score)
        hits = label[order]
        cumulative = np.cumsum(hits)
        precision = cumulative / np.arange(1, len(hits) + 1)
        return float((precision * hits).sum() / hits.sum())

    prevalence = float(labels.mean()) if labels.size else float("nan")
    budget = int(labels.sum())
    predicted = np.zeros_like(labels, bool)
    if budget > 0:
        predicted[np.argsort(-scores)[:budget]] = True
    true_positive = float((predicted & (labels > 0)).sum())
    precision = true_positive / max(predicted.sum(), 1)
    recall = true_positive / max(labels.sum(), 1)

    commuting_support_matrix = supports.get(
        "commuting_only", ng.commuting_support(data["truth"]["commuting"]))
    outside = np.array([not commuting_support_matrix[s, t]
                        for s, t in zip(pairs[0], pairs[1])])
    per_family_recovery = {}
    for family in FAMILIES:
        member = np.array([family_of.get((int(s), int(t))) == family
                           for s, t in zip(pairs[0], pairs[1])], bool)
        if member.sum() == 0:
            per_family_recovery[family] = {"n_in_support": 0}
            continue
        per_family_recovery[family] = {
            "n_in_support": int(member.sum()),
            "auprc": average_precision(scores, member.astype(float)),
            "prevalence": float(member.mean()),
            "recall_at_budget": float((predicted & member).sum() / max(member.sum(), 1)),
            "mean_score": float(scores[member].mean()),
            "mean_score_elsewhere": float(scores[~member].mean()) if (~member).any()
            else float("nan"),
        }

    outside_labels = labels * outside
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
    return {
        "kind": "herald96_neural_granger_task",
        "scenario": scenario, "relational_scale": scale, "support": support_name,
        "seed": seed, "n_zones": n_zones, "origins": origins,
        "environment": {"python": platform.python_version(), "numpy": np.__version__},
        "baseline": {"alpha": baseline["alpha"], "checksum_before": frozen_checksum,
                     "checksum_after": baseline["checksum"],
                     "frozen": baseline["checksum"] == frozen_checksum,
                     "train_residual_sd": float(train_residual["residual"].std()),
                     "test_residual_sd": float(test_residual.std())},
        "oracles": oracles, "oracle_is_usable": bool(oracle_ok),
        "arm": {
            "residual_gain": residual_gain, "per_horizon_gain": per_horizon,
            "parameters": fitted["parameters"], "n_pairs": int(pairs.shape[1]),
            "fan_in": float(fan_in),
            "final_loss": float(fitted["loss_history"][-1]),
        },
        "recovery": {
            "auprc": average_precision(scores, labels), "prevalence": prevalence,
            "edge_f1": float(2 * precision * recall / max(precision + recall, 1e-12)),
            "precision": float(precision), "recall": float(recall),
            "budget": budget,
            "n_true_in_support": int(labels.sum()),
            "n_true_outside_commuting_in_support": int(outside_labels.sum()),
            "auprc_outside_commuting": average_precision(
                scores[outside], labels[outside]) if outside.sum() > 0 else float("nan"),
            "recall_outside_commuting": float(
                (predicted & (labels > 0) & outside).sum()
                / max(outside_labels.sum(), 1)),
            "per_family": per_family_recovery,
            "edge_types": {"from_commuting": int(types["from_commuting"].sum()),
                           "from_similarity": int(types["from_similarity"].sum())},
        },
        "calibration": data["calibration"],
        "cost": {"peak_memory_mb": round(peak, 1),
                 "total_seconds": round(time.time() - started, 1)},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-id", type=int)
    parser.add_argument("--out-dir", type=Path)
    parser.add_argument("--n-zones", type=int, default=80)
    parser.add_argument("--n-score", type=int, default=N_SCORE)
    parser.add_argument("--epochs", type=int, default=ng.EPOCHS)
    parser.add_argument("--seeds", type=int, nargs="*", default=list(FINAL_SEEDS))
    parser.add_argument("--scales", type=float, nargs="*", default=list(SCALES))
    parser.add_argument("--supports", type=str, nargs="*", default=list(SUPPORTS))
    parser.add_argument("--scenarios", type=str, nargs="*", default=list(SCENARIOS))
    parser.add_argument("--dry-run", action="store_true")
    arguments = parser.parse_args()

    grid = task_grid(tuple(arguments.scenarios), tuple(arguments.scales),
                     tuple(arguments.supports), tuple(arguments.seeds))
    if arguments.dry_run:
        print(json.dumps({"kind": "herald96_plan", "n_tasks": len(grid),
                          "first": grid[0], "last": grid[-1]}, indent=2))
        return 0
    if arguments.task_id is None or arguments.out_dir is None:
        parser.error("--task-id and --out-dir are required unless --dry-run")
    if not 0 <= arguments.task_id < len(grid):
        parser.error(f"task-id must lie in [0, {len(grid) - 1}]")

    scenario, scale, support, seed = grid[arguments.task_id]
    report = run_task(scenario, scale, support, seed, arguments.n_zones,
                      arguments.epochs, arguments.n_score)
    atomic_json(report, arguments.out_dir
                / f"ng_{scenario}_s{scale}_{support}_{seed}.json")
    print(f"{scenario:20s} s={scale:<4g} {support:16s} seed={seed} "
          f"pairs={report['arm']['n_pairs']}")
    print(f"  oracle all={report['oracles']['all_families']:+.5f} "
          + " ".join(f"{f[:4]}={report['oracles'][f]:+.4f}" for f in FAMILIES))
    print(f"  arm residual_gain={report['arm']['residual_gain']:+.5f} "
          f"auprc={report['recovery']['auprc']:.4f} "
          f"prev={report['recovery']['prevalence']:.4f} "
          f"outside_auprc={report['recovery']['auprc_outside_commuting']:.4f} "
          f"n_out={report['recovery']['n_true_outside_commuting_in_support']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
