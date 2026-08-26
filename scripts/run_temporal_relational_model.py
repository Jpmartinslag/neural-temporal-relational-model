#!/usr/bin/env python3
"""Neutral public entrypoint for the Neural Temporal-Relational Model.

Runs the proposed model end to end on one synthetic dataset draw: generates (or you can
point it at) a panel with a known relational graph, builds the temporal encoder and the
relational learner, trains for the requested number of epochs, produces a forecast and a
set of connection (edge) scores, and reports gradient diagnostics that catch a dead
component before anyone reads a metric.

This script is a thin, neutrally-named wrapper around the repository's own internal,
already-tested benchmark driver (see docs/EXPERIMENT_PROVENANCE.md for the exact module
path and why it was chosen as canonical). It does not reimplement the model and does not
change any number the internal module would have produced -- it exists so that an
evaluator can run "the model" without first learning any internal experiment identifier.

Two modes:
  --smoke    Small panel, few zones, few periods, one fixed seed, few epochs. Runs in
             seconds on a laptop CPU. Proves the architecture executes, produces a real
             gradient in every component, and is deterministic. It is NOT a reproduction
             of any reported result -- see docs/RESULTS_AND_LIMITATIONS.md for those.
  (default)  Full-size run (280 zones by default), still local/CPU, still no download --
             closer to, but still smaller than, the frozen HPC grid behind the reported
             numbers (docs/REPRODUCIBILITY.md, "Reproducing the frozen headline results").

Nothing here demonstrates a scientific claim. It demonstrates that the model runs.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

_DRIVER_PATH = REPO_ROOT / "hpc" / "herald93" / "run_model_benchmark.py"
_BENCH_PATH = REPO_ROOT / "src" / "modeles" / "france_ze2020" / "herald93_benchmark.py"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


# Public, neutral scenario names -> the internal generator's scenario identifiers.
SCENARIOS = {
    "with-mechanism": "S1_SHARED",   # a relational effect is present and shared by every signal
    "no-mechanism": "S0_NULL",       # no relational effect anywhere; the false-positive floor
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the proposed temporal-relational model on one synthetic dataset draw.",
        epilog="See docs/PROJECT_OVERVIEW.md for what the temporal encoder, the relational "
               "learner, and the two scenarios below mean, and docs/RESULTS_AND_LIMITATIONS.md "
               "for what a single local run like this one does and does not demonstrate.")
    parser.add_argument("--smoke", action="store_true",
                        help="Small, fast configuration (20 zones, 4 scoring periods, "
                             "3 epochs, one fixed non-final seed). Overrides --zones/"
                             "--periods/--epochs/--seed unless given explicitly.")
    parser.add_argument("--zones", type=int, default=None,
                        help="Number of synthetic territories (minimum 20). Default 280, "
                             "or 20 with --smoke.")
    parser.add_argument("--periods", type=int, default=None,
                        help="Number of final periods to score. Default 12, or 4 with --smoke.")
    parser.add_argument("--epochs", type=int, default=None,
                        help="Training epochs. Default 30, or 3 with --smoke.")
    parser.add_argument("--width", type=int, default=64,
                        help="Hidden width of the temporal encoder and relational scorer "
                             "(width 256 is refused by construction; see "
                             "docs/RESULTS_AND_LIMITATIONS.md).")
    parser.add_argument("--seed", type=int, default=None,
                        help="Random seed. Default a fixed calibration seed (9301) with "
                             "--smoke; otherwise you must pass one explicitly, so that a "
                             "full-size run is never silently attributed to the seeds used "
                             "for reported results without saying so.")
    parser.add_argument("--scenario", choices=sorted(SCENARIOS), default="with-mechanism",
                        help="'with-mechanism': a relational effect is present. "
                             "'no-mechanism': no relational effect anywhere -- the model "
                             "must not report structure it cannot have found.")
    parser.add_argument("--out", type=Path, default=None,
                        help="Write the full JSON report here. Prints a summary either way.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    n_zones = args.zones if args.zones is not None else (20 if args.smoke else 280)
    n_score = args.periods if args.periods is not None else (4 if args.smoke else 12)
    epochs = args.epochs if args.epochs is not None else (3 if args.smoke else 30)
    if args.seed is not None:
        seed = args.seed
    elif args.smoke:
        seed = 9301  # a fixed, non-final calibration seed -- never one of the 5 reported seeds
    else:
        print("error: --seed is required outside --smoke (see --help)", file=sys.stderr)
        return 2

    scenario_id = SCENARIOS[args.scenario]

    print(f"[1/6] configuration: zones={n_zones} periods={n_score} epochs={epochs} "
         f"width={args.width} seed={seed} scenario={args.scenario} (cpu)")

    driver = _load(_DRIVER_PATH, "temporal_relational_model_driver")
    bench = _load(_BENCH_PATH, "temporal_relational_model_core")

    print("[2/6] generating the synthetic panel with a known relational graph "
         "(the graph is never given to the model)")
    print("[3/6] building the temporal encoder + masked multisignal fusion + "
         "shared relational scorer (the proposed model)")
    print("[4/6] training (masked Gaussian negative log-likelihood on log-growth, "
         "one learned scale per signal)")

    report = driver.run_task(
        method="herald",  # the proposed model's internal identifier; see naming map in
                          # docs/EXPERIMENT_PROVENANCE.md -- never presented as the public name
        scenario=scenario_id, seed=seed, width=args.width,
        n_zones=n_zones, epochs=epochs, n_score=n_score,
    )

    print("[5/6] forecast produced (skill vs. persistence: "
         f"{report['forecast']['skill_vs_persistence']:+.4f}) and connection scores produced "
         f"(edge AUPRC vs. this support's own prevalence "
         f"{report['relational'].get('prevalence', float('nan')):.3f}: "
         f"{report['relational'].get('auprc', float('nan')):.3f})")

    gradients = report.get("gradients", {})
    dead = [name for name in ("encoder", "fusion", "scorer", "relational_head", "node_head")
            if gradients.get(name, 0.0) <= 0.0]
    print(f"[6/6] gradient check: encoder={gradients.get('encoder', float('nan')):.3g} "
         f"fusion={gradients.get('fusion', float('nan')):.3g} "
         f"scorer={gradients.get('scorer', float('nan')):.3g} "
         f"relational_head={gradients.get('relational_head', float('nan')):.3g}"
         + (f"  -- DEAD: {dead}" if dead else "  -- all components trained"))

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2, default=lambda v: v.tolist()))
        print(f"full report written to {args.out}")

    print("\nThis run demonstrates that the model executes and trains on CPU. It is not a "
         "reproduction of any headline result -- see docs/RESULTS_AND_LIMITATIONS.md and "
         "docs/REPRODUCIBILITY.md, 'Reproducing the frozen headline results'.")
    return 1 if dead else 0


if __name__ == "__main__":
    sys.exit(main())
