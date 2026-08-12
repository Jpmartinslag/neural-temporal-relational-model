"""Mutation audit for the HERALD 93 benchmark guards.

Each mutant reinstates a concrete way this comparison could flatter the proposal: a
privileged input, a leaked period, capacity smuggled into one arm, a relational path that is
secretly a node path, a hard top-k that freezes the graph, a summariser that hides a failed
criterion. No mutant stubs a function with a constant.
"""
from __future__ import annotations

import importlib.util
import pathlib
import sys

import numpy as np

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

spec = importlib.util.spec_from_file_location(
    "h93g", REPO / "tests" / "test_herald93_guards.py")
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)
gen, bench, driver = g.gen, g.bench, g.driver


def swap(target, name, replacement):
    original = getattr(target, name)
    setattr(target, name, replacement)
    return lambda: setattr(target, name, original)


def patch_file(relative: str, old: str, new: str):
    path = REPO / relative
    backup = path.read_text()
    mutated = backup.replace(old, new)
    assert mutated != backup, f"the mutation did not apply to {relative}"
    path.write_text(mutated)
    return lambda: path.write_text(backup)


def killed(name, guard, install) -> bool:
    undo = install()
    g._cache.clear()
    try:
        try:
            guard()
        except Exception as error:  # noqa: BLE001
            print(f"PASS  {name:40s} killed by {type(error).__name__}: {str(error)[:60]}")
            return True
        print(f"FAIL  {name:40s} SURVIVED  <-- guard insufficient")
        return False
    finally:
        undo()
        g._cache.clear()


def m_future_period_reaches_the_view():
    original = gen.model_inputs
    return swap(gen, "model_inputs",
                lambda dataset, decision: original(
                    dataset, len(dataset["metadata"]["years"]) - 1))


def m_release_dates_ignored():
    original = gen.model_inputs

    def bad(dataset, decision):
        released = original(dataset, decision)
        for name, block in released["signals"].items():
            source = dataset["signals"][name]
            years = np.asarray(dataset["metadata"]["years"])
            temporal = np.arange(len(years))[:, None] <= decision
            final = np.asarray(source["availability_mask"], bool) & temporal
            block["values"] = np.where(final, source["values"], np.nan)
            block["availability_mask"] = final.astype(np.int8)
        return released
    return swap(gen, "model_inputs", bad)


def m_latent_state_exported():
    original = gen.model_inputs

    def bad(dataset, decision):
        released = original(dataset, decision)
        released["metadata"] = dict(released["metadata"])
        released["metadata"]["latent_state"] = dataset["truth"]["state"]
        return released
    return swap(gen, "model_inputs", bad)


def m_support_becomes_the_true_graph():
    original = bench.candidate_support

    def bad(prior, k=40):
        del prior, k
        return None
    def better(prior, k=40):
        data = g.dataset()
        truth = np.asarray(data["truth"]["propagation"][-1]) != 0
        matrix = truth.copy()
        np.fill_diagonal(matrix, False)
        return matrix
    del bad
    return swap(bench, "candidate_support", better)


def m_view_reads_the_latent_path():
    original = bench.PanelView.__init__

    def bad(self, released, support, names):
        original(self, released, support, names)
        self.growth = self.growth * 0.0 + 1.0
        self.filled = np.nan_to_num(self.growth)
    return swap(bench.PanelView, "__init__", bad)


def m_grid_uses_calibration_seeds():
    return patch_file(
        "hpc/herald93/run_model_benchmark.py",
        "def task_grid(methods=METHODS, scenarios=SCENARIOS, seeds=FINAL_SEEDS,",
        "def task_grid(methods=METHODS, scenarios=SCENARIOS,\n"
        "              seeds=__import__('src.data.synthetic."
        "generate_france_multisignal_v92', fromlist=['x']).CALIBRATION_SEEDS,")


def m_absence_becomes_a_zero():
    original = bench.PanelView.window

    def bad(self, end, length=bench.CONTEXT):
        block, seen = original(self, end, length)
        return block, np.ones_like(seen)
    return swap(bench.PanelView, "window", bad)


def m_metric_ignores_the_mask():
    original = bench.forecast_metrics

    def bad(prediction, target, mask, persistence):
        return original(prediction, target, np.ones_like(mask, bool), persistence)
    return swap(bench, "forecast_metrics", bad)


def m_self_loops_restored():
    original = bench.candidate_support

    def bad(prior, k=40):
        support = original(prior, k)
        np.fill_diagonal(support, True)
        return support
    return swap(bench, "candidate_support", bad)


def m_static_score_credited_for_events():
    original = bench.typed_event_metrics

    def bad(scores_by_period, truth, support, periods, keep):
        """Score events against the truth's own movement instead of the method's."""
        propagation = np.asarray(truth["propagation"])
        moved = {period: (propagation[period] != 0).astype(float) for period in periods
                 if period - 1 >= 0}
        moved.update({period - 1: (propagation[period - 1] != 0).astype(float)
                      for period in periods if period - 1 >= 0})
        return original(moved, truth, support, periods, keep)
    return swap(bench, "typed_event_metrics", bad)


def m_events_lose_their_type():
    original = bench.typed_event_metrics

    def bad(scores_by_period, truth, support, periods, keep):
        absolute = {period: np.abs(matrix) * 0 + np.abs(matrix)
                    for period, matrix in scores_by_period.items()}
        # An untyped change: births and deaths read from the same end of the ranking.
        result = original(absolute, truth, support, periods, keep)
        return result
    return swap(bench, "typed_event_metrics", bad)


def m_relational_arm_gets_a_node_path():
    original = bench.HeraldMultisignal.forward

    def bad(self, block, seen, coverage):
        output = original(self, block, seen, coverage)
        output["relational"] = output["relational"] + self.node_head(output["state"])
        return output
    return swap(bench.HeraldMultisignal, "forward", bad)


def m_top_k_is_hard():
    original = bench.HeraldMultisignal.forward

    def bad(self, block, seen, coverage):
        import torch
        output = original(self, block, seen, coverage)
        output["edge_weight"] = output["edge_weight"].detach()
        return output
    return swap(bench.HeraldMultisignal, "forward", bad)


def m_one_signal_encoder_is_frozen():
    original = bench.TemporalEncoder.forward

    def bad(self, block, seen):
        import torch
        encoded = original(self, block, seen)
        frozen = encoded.clone()
        frozen[2] = encoded[2].detach()
        return frozen
    return swap(bench.TemporalEncoder, "forward", bad)


def m_fusion_drops_a_signal():
    original = bench.MaskedFusion.forward

    def bad(self, encoded, coverage):
        fused, weights = original(self, encoded, coverage)
        weights = weights.clone()
        weights[1] = weights[1] * 0.0
        return fused, weights
    return swap(bench.MaskedFusion, "forward", bad)


def m_duplicate_is_not_a_duplicate():
    from src.modeles.france_ze2020 import herald92_multisignal_oracle as h92
    original = h92.duplicate_signal

    def bad(dataset, source, alias, jitter=0.0, seed=0):
        result = original(dataset, source, alias, jitter=jitter, seed=seed)
        rng = np.random.default_rng(7)
        values = np.asarray(result["signals"][alias]["values"], float)
        result["signals"][alias] = dict(result["signals"][alias])
        result["signals"][alias]["values"] = values * rng.normal(1.0, 0.5, values.shape)
        return result
    return swap(h92, "duplicate_signal", bad)


def m_mtgnn_escapes_the_support():
    original = bench.MTGNNLite.adjacency

    def bad(self):
        import torch
        product = self.embed_source @ self.embed_target.T
        return torch.relu(torch.tanh(self.alpha * (product - product.T)))
    return swap(bench.MTGNNLite, "adjacency", bad)


def m_nri_escapes_the_support():
    original = bench.NRILite.__init__

    def bad(self, n_signals, hidden, pairs, n_zones):
        full = np.array(np.nonzero(~np.eye(n_zones, dtype=bool)))
        original(self, n_signals, hidden, full, n_zones)
    return swap(bench.NRILite, "__init__", bad)


def m_forecast_satisfies_the_recovery_gate():
    return patch_file(
        "hpc/herald93/summarize_benchmark.py",
        "    forecast_ok = median(skill) >= FORECAST_SKILL_MIN\n"
        "    recovery_ok = all(checks.values())",
        "    forecast_ok = median(skill) >= FORECAST_SKILL_MIN\n"
        "    recovery_ok = all(checks.values()) or forecast_ok")


def m_one_arm_gets_a_richer_likelihood():
    original = bench.HeraldMultisignal.__init__

    def bad(self, n_signals, hidden, pairs, prior, n_zones, top_k=bench.TOP_K_PROPAGATION):
        original(self, n_signals, hidden, pairs, prior, n_zones, top_k)
        import torch
        self.log_scale = torch.nn.Parameter(torch.zeros(1))
    return swap(bench.HeraldMultisignal, "__init__", bad)


def m_width_256_accepted():
    return patch_file(
        "src/modeles/france_ze2020/herald93_benchmark.py",
        "FORBIDDEN_WIDTH = 256", "FORBIDDEN_WIDTH = 4096")


def m_summariser_drops_failed_checks():
    return patch_file(
        "hpc/herald93/summarize_benchmark.py",
        "    return {\n        \"checks\": checks,",
        "    checks = {name: value for name, value in checks.items() if value}\n"
        "    return {\n        \"checks\": checks,")


CASES = [
    ("future_period_reaches_view", g.test_h1_no_future_period_reaches_a_view,
     m_future_period_reaches_the_view),
    ("release_dates_ignored", g.test_h2_release_dates_gate_the_inputs,
     m_release_dates_ignored),
    ("latent_state_exported", g.test_h3_latent_state_is_never_an_input,
     m_latent_state_exported),
    ("support_becomes_true_graph", g.test_h4_true_graph_never_reaches_a_model,
     m_support_becomes_the_true_graph),
    ("view_reads_latent_path", g.test_h5_truth_never_enters_the_design,
     m_view_reads_the_latent_path),
    ("grid_uses_calibration_seeds",
     g.test_h6_final_seeds_are_the_evaluation_seeds_and_calibration_is_elsewhere,
     m_grid_uses_calibration_seeds),
    ("absence_becomes_zero", g.test_h7_absence_is_not_a_zero, m_absence_becomes_a_zero),
    ("metric_ignores_mask",
     g.test_h8_masked_cells_are_excluded_from_the_loss_and_the_metrics,
     m_metric_ignores_the_mask),
    ("self_loops_restored", g.test_h9_no_self_loop_anywhere, m_self_loops_restored),
    ("static_score_credited_for_events",
     g.test_h10_a_static_prior_gets_no_credit_for_a_new_edge,
     m_static_score_credited_for_events),
    ("node_path_in_relational_arm",
     g.test_h12_the_relational_arm_has_no_node_only_path,
     m_relational_arm_gets_a_node_path),
    ("top_k_is_hard", g.test_h13_top_k_does_not_block_the_gradient, m_top_k_is_hard),
    ("signal_encoder_frozen", g.test_h14_every_signal_receives_gradient,
     m_one_signal_encoder_is_frozen),
    ("fusion_drops_a_signal", g.test_h15_no_signal_is_dropped_by_the_fusion,
     m_fusion_drops_a_signal),
    ("duplicate_is_not_a_duplicate", g.test_h16_duplication_is_not_complementarity,
     m_duplicate_is_not_a_duplicate),
    ("mtgnn_escapes_support",
     g.test_h17_every_arm_gets_the_same_support_and_the_same_origins,
     m_mtgnn_escapes_the_support),
    ("nri_escapes_support", g.test_h18_nri_stays_inside_the_support,
     m_nri_escapes_the_support),
    ("forecast_satisfies_recovery_gate",
     g.test_h19_forecast_and_recovery_are_reported_separately,
     m_forecast_satisfies_the_recovery_gate),
    ("one_arm_richer_likelihood",
     g.test_h20_the_same_objective_and_scale_are_used_by_every_neural_arm,
     m_one_arm_gets_a_richer_likelihood),
    ("width_256_accepted", g.test_h21_width_256_is_refused, m_width_256_accepted),
    ("summariser_drops_failed_checks", g.test_h22_the_summariser_reports_failures,
     m_summariser_drops_failed_checks),
]


if __name__ == "__main__":
    survivors = len(CASES) - sum(killed(*case) for case in CASES)
    print(f"\n{len(CASES) - survivors}/{len(CASES)} mutants killed")
    raise SystemExit(1 if survivors else 0)
