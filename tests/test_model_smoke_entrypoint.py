"""Guards on the public entrypoint (scripts/run_temporal_relational_model.py) itself.

tests/test_herald93_guards.py and tests/run_herald93_mutations.py already guard the
underlying model/generator module exhaustively. This file guards a different, narrower
failure mode: someone quietly editing the *entrypoint* to call something other than the
real relational model -- persistence, a baseline, a model with no relational path, a
constant/random score, or a non-deterministic path -- while its CLI still looks the same.
Each check here fails loudly if that substitution happens.
"""
from __future__ import annotations

import importlib.util
import pathlib
import subprocess
import sys

import numpy as np

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

ENTRYPOINT = REPO / "scripts" / "run_temporal_relational_model.py"


def _load_entrypoint():
    spec = importlib.util.spec_from_file_location("run_temporal_relational_model", ENTRYPOINT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def _run(scenario: str = "with-mechanism", seed: int = 9301, zones: int = 20,
         periods: int = 4, epochs: int = 2, width: int = 16) -> dict:
    entry = _load_entrypoint()
    driver = entry._load(entry._DRIVER_PATH, "smoke_guard_driver")
    scenario_id = entry.SCENARIOS[scenario]
    return driver.run_task(method="herald", scenario=scenario_id, seed=seed, width=width,
                           n_zones=zones, epochs=epochs, n_score=periods)


def test_entrypoint_calls_the_real_relational_model_not_a_substitute():
    """A swap to persistence/sparse_var/mtgnn/nri would change one of these three fields."""
    report = _run()
    assert report["method"] == "herald", (
        f"entrypoint ran {report['method']!r}, not the proposed relational model")
    capabilities = report["capabilities"]
    assert capabilities["learns_graph"] is True, "the run reports no learned graph at all"
    assert capabilities["graph_kind"] == "dynamic", (
        f"graph_kind is {capabilities['graph_kind']!r}; only the proposed model is 'dynamic' "
        "-- 'static' would mean MTGNN or NRI, None would mean persistence or the classical arm")


def test_gradients_are_nonzero_in_every_component():
    """A frozen or bypassed component is indistinguishable from a healthy one in a metric
    table alone; this is the check that catches it directly."""
    report = _run()
    gradients = report["gradients"]
    for component in ("encoder", "fusion", "scorer", "relational_head", "node_head"):
        assert gradients.get(component, 0.0) > 0.0, (
            f"component {component!r} received zero gradient in the smoke run")
    assert all(value > 0 for value in gradients["per_signal"]), (
        f"a per-signal encoder branch received no gradient: {gradients['per_signal']}")


def test_no_mechanism_scenario_does_not_explode():
    report = _run(scenario="no-mechanism")
    forecast = report["forecast"]
    assert np.isfinite(forecast["mae"]), "MAE is not finite in the no-mechanism scenario"
    assert np.isfinite(forecast["skill_vs_persistence"]), (
        "forecast skill is not finite in the no-mechanism scenario")
    for value in report["gradients"].values():
        if isinstance(value, (int, float)):
            assert np.isfinite(value), "a gradient norm is not finite (nan/inf)"


def test_shapes_match_the_configured_panel():
    zones, width = 20, 16
    report = _run(zones=zones, width=width)
    origins = report["origins"]
    assert len(origins) == report["n_score"]
    assert report["n_zones"] == zones


def test_determinism_same_seed_same_config():
    first = _run(seed=9301)
    second = _run(seed=9301)
    assert first["forecast"] == second["forecast"], "forecast is not deterministic"
    assert first["relational"] == second["relational"], "connection scores are not deterministic"
    assert first["gradients"] == second["gradients"], "gradients are not deterministic"


def test_connection_scores_are_not_a_frozen_or_seed_independent_constant():
    """Two different seeds must not produce byte-identical connection scores -- a frozen,
    hardcoded, or seed-independent output would pass the determinism check above and hide
    here instead."""
    a = _run(seed=9301)
    b = _run(seed=9302)
    assert a["relational"] != b["relational"], (
        "connection scores are identical across two different seeds -- "
        "suspect a frozen or constant output")


def test_cli_help_carries_no_legacy_internal_name():
    """The public entrypoint's help text must never reintroduce the legacy identifier."""
    result = subprocess.run([sys.executable, str(ENTRYPOINT), "--help"],
                            capture_output=True, text=True, check=True)
    combined = (result.stdout + result.stderr).lower()
    assert "herald" not in combined, "the legacy internal name leaked into --help output"


def test_smoke_defaults_stay_small_and_fast():
    """Locks in the 'few zones, few periods, few epochs' contract so --smoke cannot
    silently grow into something that no longer runs in seconds on a laptop CPU."""
    entry = _load_entrypoint()
    args = entry.build_parser().parse_args(["--smoke"])
    zones = args.zones if args.zones is not None else 20
    periods = args.periods if args.periods is not None else 4
    epochs = args.epochs if args.epochs is not None else 3
    assert zones <= 40, f"--smoke default zone count grew to {zones}"
    assert periods <= 8, f"--smoke default scoring periods grew to {periods}"
    assert epochs <= 5, f"--smoke default epoch count grew to {epochs}"


def test_full_size_run_refuses_to_guess_a_seed():
    """Outside --smoke, a seed must be given explicitly -- silently defaulting to one of
    the 5 seeds used for reported results would blur a local run with a frozen one."""
    entry = _load_entrypoint()
    assert entry.main([]) != 0, "running without --smoke and without --seed did not fail"
