"""Guards for the HERALD 93 four-method benchmark.

Each guard names one mechanism that a comparison of this kind can lose silently, and
``run_herald93_mutations.py`` removes exactly that mechanism. The list is deliberately
weighted towards the ways a *favourable* result can be manufactured: privileged inputs,
capacity smuggled into one arm, a dead relational path hidden behind a good forecast, and a
summariser that does not report what failed.
"""
from __future__ import annotations

import importlib.util
import pathlib
import sys

import numpy as np

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.data.synthetic import generate_france_multisignal_v92 as gen  # noqa: E402
from src.modeles.france_ze2020 import herald93_benchmark as bench  # noqa: E402

driver_spec = importlib.util.spec_from_file_location(
    "h93_driver", REPO / "hpc" / "herald93" / "run_model_benchmark.py")
driver = importlib.util.module_from_spec(driver_spec)
driver_spec.loader.exec_module(driver)

SMALL = dict(n_zones=140)
_cache: dict = {}


def dataset(scenario: str = "S1_SHARED", seed: int = 9401) -> dict:
    key = (scenario, seed)
    if key not in _cache:
        _cache[key] = gen.generate_multisignal(
            gen.MultisignalConfig(seed=seed, scenario=scenario, **SMALL))
    return _cache[key]


def support_of(data) -> np.ndarray:
    return bench.candidate_support(data["truth"]["prior"], k=40)


def view_of(data, decision: int) -> bench.PanelView:
    return bench.PanelView(gen.model_inputs(data, decision), support_of(data),
                           list(data["signals"]))


def herald_model(data, width: int = 16):
    import torch
    torch.manual_seed(0)
    support = support_of(data)
    pairs = np.array(np.nonzero(support))
    prior = np.asarray(data["truth"]["prior"], float)[support]
    return bench.HeraldMultisignal(len(data["signals"]), width, pairs, prior,
                                   data["truth"]["prior"].shape[0], top_k=4)


# ── Leakage ──────────────────────────────────────────────────────────────────

def test_h1_no_future_period_reaches_a_view():
    """A view built at decision period d must contain nothing published after d."""
    data = dataset()
    decision = 60
    view = view_of(data, decision)
    assert not view.observed[:, decision + 1:, :].any(), (
        "an observation from after the decision period survived into the view")


def test_h2_release_dates_gate_the_inputs():
    """Annual signals arrive with a lag; a view must not contain a not-yet-released year."""
    data = dataset()
    early = view_of(data, 40)
    late = view_of(data, 100)
    assert early.observed.sum() < late.observed.sum(), "release gating does nothing"
    for name, block in data["signals"].items():
        release = np.asarray(block["release_year"])
        years = np.asarray(data["metadata"]["years"])
        unreleased = (release > years[40]) & (release >= 0)
        index = list(data["signals"]).index(name)
        assert not early.observed[index][unreleased].any(), f"{name} leaked a release"


def test_h3_latent_state_is_never_an_input():
    released = gen.model_inputs(dataset(), 60)
    blob = repr(sorted(released.keys())) + repr(sorted(released["metadata"].keys()))
    for forbidden in ("truth", "state", "latent", "relational", "propagation",
                      "calibration", "low_information"):
        assert forbidden not in blob, f"{forbidden!r} reachable from model inputs"


def test_h4_true_graph_never_reaches_a_model():
    """The support is the commuting prior; it must not be the truth in disguise."""
    data = dataset()
    support = support_of(data)
    truth = np.asarray(data["truth"]["propagation"][-1]) != 0
    np.fill_diagonal(truth, False)
    overlap = (support & truth).sum() / max(support.sum(), 1)
    assert overlap < 0.95, (
        f"the candidate support is {overlap:.2%} true edges; it is a label, not a prior")
    assert support.sum() > truth.sum(), "the support is not wider than the truth"


def test_h5_truth_never_enters_the_design():
    """The view is reconstructible from the published signals alone."""
    data = dataset()
    view = view_of(data, 80)
    released = gen.model_inputs(data, 80)
    for index, name in enumerate(data["signals"]):
        block = released["signals"][name]
        values = np.asarray(block["values"], float)
        mask = np.asarray(block["availability_mask"], bool)
        lag = 4 if block["freq"] == "A" else 1
        logs = np.where(mask, np.log(np.maximum(values, 1e-9)), np.nan)
        expected = np.full_like(logs, np.nan)
        expected[lag:] = logs[lag:] - logs[:-lag]
        assert np.allclose(np.nan_to_num(view.growth[index]),
                           np.nan_to_num(expected)), name


def test_h6_final_seeds_are_the_evaluation_seeds_and_calibration_is_elsewhere():
    """The model grid runs on the final seeds; nothing else may have touched them."""
    assert set(driver.task_grid()) and all(
        seed in gen.FINAL_SEEDS for _, _, seed, _ in driver.task_grid())
    assert not set(gen.FINAL_SEEDS) & set(gen.CALIBRATION_SEEDS)
    assert not set(gen.FINAL_SEEDS) & set(gen.FAIR_SEEDS)


# ── Masks and absence ────────────────────────────────────────────────────────

def test_h7_absence_is_not_a_zero():
    """A missing cell must stay unobserved, and must reach the encoder as a flag."""
    data = dataset()
    view = view_of(data, 90)
    index = list(data["signals"]).index("establishments")
    assert not view.observed[index].all(), "the annual signal has no gaps at all"
    block, seen = view.window(80)
    assert seen.dtype == bool or set(np.unique(seen)) <= {0, 1}
    assert (block[seen == 0] == 0).all(), "an unobserved cell carries a value"
    assert seen[index].mean() < 1.0, "the mask channel is constant for an annual signal"


def test_h8_masked_cells_are_excluded_from_the_loss_and_the_metrics():
    prediction = np.zeros((2, 2, 3))
    target = np.array([[[1.0, 1.0, 1.0], [9.0, 9.0, 9.0]]] * 2)
    mask = np.array([[[True, True, True], [False, False, False]]] * 2)
    metrics = bench.forecast_metrics(prediction, target, mask, prediction)
    assert abs(metrics["mae"] - 1.0) < 1e-9, (
        f"masked cells entered the metric: mae {metrics['mae']}")


# ── Graph mechanics ──────────────────────────────────────────────────────────

def test_h9_no_self_loop_anywhere():
    data = dataset()
    support = support_of(data)
    assert not np.diagonal(support).any(), "the candidate support has a self loop"
    model = herald_model(data)
    pairs = model.pairs.numpy()
    assert not (pairs[0] == pairs[1]).any(), "a self pair reached the scorer"


def test_h10_a_static_prior_gets_no_credit_for_a_new_edge():
    """A method whose score never moves must score zero on typed events, not be excused."""
    data = dataset()
    support = support_of(data)
    static = np.asarray(data["truth"]["prior"], float)
    origins = list(range(90, 110))
    frozen = {origin: static for origin in origins}
    events = bench.typed_event_metrics(frozen, data["truth"], support, origins, keep=0)
    assert not (events["event_f1"] > 0.05), (
        f"a frozen score obtained event F1 {events['event_f1']}")


def test_h11_events_are_typed_and_dated():
    """Births and deaths are scored separately; an untyped change must not count."""
    data = dataset()
    support = support_of(data)
    propagation = np.asarray(data["truth"]["propagation"])
    changed = (propagation[1:] != 0) != (propagation[:-1] != 0)
    origins = [period for period in range(1, propagation.shape[0])
               if (changed[period - 1] & support).any()]
    assert origins, "the benchmark truth never moves; typed events cannot be tested"
    # A score that moves in the *wrong* direction must be punished, not rewarded: births
    # and deaths are read off opposite ends of the change.
    scores = {}
    for period in sorted(set(origins) | {p - 1 for p in origins}):
        now = (propagation[period] != 0).astype(float)
        scores[period] = -now
    events = bench.typed_event_metrics(scores, data["truth"], support, origins, keep=0)
    good = bench.typed_event_metrics(
        {period: (propagation[period] != 0).astype(float) for period in scores},
        data["truth"], support, origins, keep=0)
    assert good["event_f1"] > events["event_f1"], (
        "reversing the sign of the change did not change the typed event score")


def test_h12_the_relational_arm_has_no_node_only_path():
    """A zone's own state must not reach it except through messages from other zones.

    Tested by removing every edge. With no neighbour to hear from, the relational term can
    only be the head's bias, identical for every zone. If it still varies from zone to
    zone, something other than a message is feeding it, and an ablation of the graph would
    then measure nothing at all.

    An earlier version perturbed one zone's history and asserted its own relational output
    was unmoved. That was vacuous: at the real support size every zone has incoming edges,
    so the assertion never ran, and it was also wrong in principle, because the edge weight
    legitimately depends on both endpoints.
    """
    import torch
    data = dataset()
    support = support_of(data)
    empty = np.zeros((2, 0), dtype=int)
    prior = np.zeros(0)
    model = bench.HeraldMultisignal(len(data["signals"]), 16, empty, prior,
                                    support.shape[0], top_k=4)
    view = view_of(data, 90)
    block, seen = view.window(bench.last_released_origin(view))
    seen_t = torch.as_tensor(seen, dtype=torch.float32)
    output = model(torch.as_tensor(block, dtype=torch.float32), seen_t, seen_t.mean(1))
    relational = output["relational"].detach().numpy()
    spread = float(relational.std(axis=0).max())
    assert spread < 1e-6, (
        f"with no edges the relational term still varies across zones by {spread:.3e}; "
        "a node-only path is feeding it")


def test_h13_top_k_does_not_block_the_gradient():
    """Every candidate edge must receive gradient, not only the k that were selected."""
    import torch
    data = dataset()
    model = herald_model(data)
    view = view_of(data, 90)
    origin = bench.last_released_origin(view)
    block, seen = view.window(origin)
    block_t = torch.as_tensor(block, dtype=torch.float32)
    seen_t = torch.as_tensor(seen, dtype=torch.float32)
    output = model(block_t, seen_t, seen_t.mean(1))
    target = torch.as_tensor(view.filled[:, origin, :].T, dtype=torch.float32)
    mask = torch.as_tensor(view.observed[:, origin, :].T, dtype=torch.float32)
    assert mask.sum() > 0, "the probe period carries no released observation"
    loss = bench.masked_gaussian_nll(output["prediction"], target, mask, model.log_scale)
    grad = torch.autograd.grad(loss, output["edge_weight"], retain_graph=True)[0]
    reached = float((grad.abs() > 0).float().mean())
    assert reached > 0.5, (
        f"only {reached:.1%} of candidate edges received gradient; top-k is hard")


def test_h14_every_signal_receives_gradient():
    data = dataset()
    model = herald_model(data)
    view = view_of(data, 90)
    norms = bench.component_gradient_norms(model, view, bench.last_released_origin(view))
    per_signal = norms["per_signal"]
    assert all(value > 0 for value in per_signal), (
        f"a signal encoder received no gradient: {per_signal}")
    for key in ("scorer", "relational_head", "fusion", "node_head"):
        assert norms[key] > 0, f"{key} received no gradient"


def test_h15_no_signal_is_dropped_by_the_fusion():
    """The fusion must weight signals, never silently discard one."""
    import torch
    data = dataset()
    model = herald_model(data)
    view = view_of(data, 90)
    block, seen = view.window(bench.last_released_origin(view))
    seen_t = torch.as_tensor(seen, dtype=torch.float32)
    output = model(torch.as_tensor(block, dtype=torch.float32), seen_t, seen_t.mean(1))
    gates = output["gates"].detach().numpy()
    per_signal = gates.mean(1)
    assert (per_signal > 0).all(), f"a signal was zeroed by the fusion: {per_signal}"


# ── Fairness between arms ────────────────────────────────────────────────────

def test_h16_duplication_is_not_complementarity():
    """A duplicated channel must not be counted as a second independent signal."""
    data = dataset()
    from src.modeles.france_ze2020 import herald92_multisignal_oracle as h92
    duplicated = h92.duplicate_signal(data, "headcount", "headcount_copy")
    original = np.nan_to_num(np.asarray(data["signals"]["headcount"]["values"], float))
    copy = np.nan_to_num(np.asarray(duplicated["signals"]["headcount_copy"]["values"],
                                    float))
    assert np.allclose(original, copy), "the duplicate control is not a duplicate"


def test_h17_every_arm_gets_the_same_support_and_the_same_origins():
    data = dataset()
    support = support_of(data)
    pairs = np.array(np.nonzero(support))
    model = herald_model(data)
    nri = bench.NRILite(len(data["signals"]), 16, pairs, support.shape[0])
    assert np.array_equal(model.pairs.numpy(), nri.pairs.numpy()), (
        "HERALD and NRI are not restricted to the same candidate set")
    mtgnn = bench.MTGNNLite(len(data["signals"]), 16, support.shape[0],
                            support.astype(float))
    adjacency = mtgnn.adjacency().detach().numpy()
    assert not adjacency[~support].any(), "MTGNN scored a pair outside the support"


def test_h18_nri_stays_inside_the_support():
    data = dataset()
    support = support_of(data)
    pairs = np.array(np.nonzero(support))
    nri = bench.NRILite(len(data["signals"]), 16, pairs, support.shape[0])
    view = view_of(data, 90)
    matrix = bench.edge_matrix_from(nri, view, bench.last_released_origin(view))
    assert not matrix[~support].any(), "NRI produced a score outside the support"


def test_h19_forecast_and_recovery_are_reported_separately():
    """A forecasting gain must never be able to satisfy a recovery criterion."""
    gate_spec = importlib.util.spec_from_file_location(
        "h93_gate", REPO / "hpc" / "herald93" / "summarize_benchmark.py")
    gate = importlib.util.module_from_spec(gate_spec)
    gate_spec.loader.exec_module(gate)
    excellent_forecast = {
        "forecast": {"mae": 0.0, "wmape": 0.0, "skill_vs_persistence": 0.99},
        "relational": {"edge_f1": 0.0, "dense_correlation": 0.0, "auprc": 0.0,
                       "prevalence": 0.1, "predicted_added_edge_rate": 1.0},
        "events": {"event_f1": 0.0}, "gradients": {"scorer": 1.0},
    }
    verdict = gate.classify([excellent_forecast], [excellent_forecast])
    assert not verdict["relational_recovery_supported"], (
        "a perfect forecast satisfied the recovery gate")
    assert verdict["label"] == "PREDICTIVE_ONLY_NO_RELATIONAL_DISCOVERY_CLAIM"


def test_h20_the_same_objective_and_scale_are_used_by_every_neural_arm():
    """No arm may be given a better-specified likelihood than another."""
    data = dataset()
    support = support_of(data)
    pairs = np.array(np.nonzero(support))
    models = [herald_model(data),
              bench.NRILite(len(data["signals"]), 16, pairs, support.shape[0]),
              bench.MTGNNLite(len(data["signals"]), 16, support.shape[0],
                              support.astype(float))]
    for model in models:
        assert hasattr(model, "log_scale"), f"{type(model).__name__} has no learned scale"
        assert model.log_scale.numel() == len(data["signals"]), (
            "the per-signal scale does not cover every signal")


def test_h21_width_256_is_refused():
    data = dataset()
    support = support_of(data)
    pairs = np.array(np.nonzero(support))
    prior = np.asarray(data["truth"]["prior"], float)[support]
    for builder in (
            lambda: bench.HeraldMultisignal(5, 256, pairs, prior, support.shape[0]),
            lambda: bench.NRILite(5, 256, pairs, support.shape[0]),
            lambda: bench.MTGNNLite(5, 256, support.shape[0], support.astype(float))):
        try:
            builder()
        except ValueError:
            continue
        raise AssertionError("width 256 was accepted")


def test_h22_the_summariser_reports_failures():
    """A failing criterion must appear in the output, not be dropped from it."""
    gate_spec = importlib.util.spec_from_file_location(
        "h93_gate", REPO / "hpc" / "herald93" / "summarize_benchmark.py")
    gate = importlib.util.module_from_spec(gate_spec)
    gate_spec.loader.exec_module(gate)
    hopeless = {
        "forecast": {"mae": 1.0, "wmape": 1.0, "skill_vs_persistence": -1.0},
        "relational": {"edge_f1": 0.0, "dense_correlation": 0.0, "auprc": 0.0,
                       "prevalence": 0.5, "predicted_added_edge_rate": 1.0},
        "events": {"event_f1": 0.0}, "gradients": {"scorer": 0.0},
    }
    verdict = gate.classify([hopeless], [hopeless])
    assert any(value is False for value in verdict["checks"].values()), (
        "no criterion was reported as failing")
    assert set(verdict["checks"]) >= {
        "edge_f1_at_least_0_50", "dense_correlation_at_least_0_30",
        "no_structure_found_in_s0", "auprc_above_prevalence",
        "relational_gradient_is_non_zero"}


def test_h23_the_relational_scorer_still_learns_after_training():
    """The gradient must survive training, not merely exist at initialisation.

    Guard h13 checks that top-k does not block the gradient in a fresh model. It passed
    while the grid ran, and the grid still measured a scorer gradient of exactly 0.0 after
    thirty epochs beside 7.86 for the head consuming its output: the edge logits had drifted
    until the squashing function saturated, and the graph froze while the rest of the model
    went on training against it. A frozen graph and a graph that found nothing are
    indistinguishable in a metric table, so the distinction has to be guarded here.
    """
    data = dataset()
    model = herald_model(data, width=16)
    view = view_of(data, 90)
    # Saturation is a drift phenomenon: it needs enough steps to develop. Six epochs on
    # this fixture did not reproduce it and the mutant survived, which made the guard look
    # sufficient while the grid was demonstrating that it was not.
    trained = bench.train_neural("herald", model, view, 70, epochs=25, seed=0)
    assert trained["loss_history"][-1] < trained["loss_history"][0], "the model did not train"
    norms = bench.component_gradient_norms(model, view, bench.last_released_origin(view))
    ratio = norms["scorer"] / max(norms["relational_head"], 1e-12)
    assert norms["scorer"] > 1e-6 and ratio > 1e-4, (
        f"the scorer is frozen after training: gradient {norms['scorer']:.3e} "
        f"against {norms['relational_head']:.3e} for the head that consumes it "
        f"(ratio {ratio:.3e})")


def _main() -> int:
    names = sorted((name for name in globals() if name.startswith("test_")),
                   key=lambda n: int(n.split("_")[1][1:]))
    failures = 0
    for name in names:
        try:
            globals()[name]()
            print(f"PASS  {name}")
        except Exception as error:  # noqa: BLE001
            failures += 1
            print(f"FAIL  {name}\n      {type(error).__name__}: {str(error)[:240]}")
    print(f"\n{len(names) - failures}/{len(names)} guards passed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(_main())
