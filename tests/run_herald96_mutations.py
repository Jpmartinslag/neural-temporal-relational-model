"""HERALD 96 mutation audit. Each mutant removes one real mechanism, in memory.

None returns a fixed metric: a stub that returns a constant kills every guard that touches
it and proves only that the guards run.

Run: ``python3 tests/run_herald96_mutations.py``
"""
from __future__ import annotations

import contextlib
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.data.synthetic import generate_multirelational_v96 as gen  # noqa: E402
from src.modeles.france_ze2020 import herald94_temporal_features as tf  # noqa: E402
from src.modeles.france_ze2020 import herald96_neural_granger as ng  # noqa: E402
from tests import test_herald96_guards as guards  # noqa: E402


@contextlib.contextmanager
def swap(module, name: str, replacement):
    original = getattr(module, name)
    setattr(module, name, replacement)
    try:
        yield
    finally:
        setattr(module, name, original)


def q01_the_arm_gains_a_local_path():
    """A per-target intercept: an isolated zone would then be predicted after all."""
    original = ng.predict_residual

    def with_local(params, x, pairs, n_zones):
        prediction, contribution = original(params, x, pairs, n_zones)
        return prediction + 0.1, contribution
    return swap(ng, "predict_residual", with_local)


def q02_the_baseline_is_refitted_during_training():
    original = ng.fit

    def leaky(params, x, pairs, targets, masks, n_zones, **kwargs):
        result = original(params, x, pairs, targets, masks, n_zones, **kwargs)
        for record in guards.__dict__.get("_FROZEN", []):
            record["beta"] = record["beta"] * 1.01
        return result
    def fit_and_touch(table, target, train_periods):
        fitted = ng.fit_frozen_baseline.__wrapped__(table, target, train_periods) \
            if hasattr(ng.fit_frozen_baseline, "__wrapped__") else None
        return fitted
    original_baseline = ng.fit_frozen_baseline

    def mutable(table, target, train_periods):
        fitted = original_baseline(table, target, train_periods)
        guards.__dict__.setdefault("_FROZEN", []).append(fitted)
        return fitted
    class Both:
        def __enter__(self):
            self.a = swap(ng, "fit", leaky); self.a.__enter__()
            self.b = swap(ng, "fit_frozen_baseline", mutable); self.b.__enter__()
        def __exit__(self, *exc):
            self.b.__exit__(*exc); self.a.__exit__(*exc)
            guards.__dict__.pop("_FROZEN", None)
    return Both()


def q03_the_residual_is_the_raw_target():
    def raw(baseline, table, target, periods):
        scored = ng.baseline_prediction(baseline, table, target, periods)
        return {"residual": scored["y"], "keys": scored["keys"],
                "observed": scored["y"], "baseline": scored["prediction"]}
    return swap(ng, "residual_target", raw)


def q04_the_commuting_weight_enters_the_design():
    original = ng.pair_features

    def leaky(table, pairs, periods, signal=ng.PRIMARY_SIGNAL):
        design = original(table, pairs, periods, signal)
        # The candidate generator's own weight, appended as a value.
        weight = np.linspace(0.0, 1.0, design["x"].shape[1])[None, :, None]
        design["x"] = np.concatenate(
            [design["x"], np.repeat(weight, design["x"].shape[0], axis=0)], axis=2)
        return design
    return swap(ng, "pair_features", leaky)


def q05_similarity_edges_fall_inside_commuting():
    original = gen.build_relations

    def collapsed(n, commuting, distance, similarity, edges_per_family, rng):
        relations = original(n, commuting, distance, similarity, edges_per_family, rng)
        flow = np.array(np.nonzero(commuting > 0)).T
        relations["edges"]["similarity"] = [
            (int(flow[i, 0]), int(flow[i, 1])) for i in range(edges_per_family)]
        return relations
    return swap(gen, "build_relations", collapsed)


def q06_the_similarity_support_is_empty():
    return swap(ng, "similarity_support",
                lambda similarity, k=ng.SIMILARITY_K: np.zeros_like(similarity, dtype=bool))


def q07_all_pairs_drops_the_diagonal_block():
    def partial(n):
        support = np.zeros((n, n), bool)
        support[: n // 2, : n // 2] = True
        np.fill_diagonal(support, False)
        return support
    return swap(ng, "all_pairs_support", partial)


def q08_the_group_penalty_does_nothing():
    original = ng.fit

    def unpenalised(params, x, pairs, targets, masks, n_zones, **kwargs):
        kwargs["group_penalty"] = 0.0
        return original(params, x, pairs, targets, masks, n_zones, **kwargs)
    return swap(ng, "fit", unpenalised)


def q09_the_source_half_is_ignored():
    """Contributions depend on the target only, so shuffling the source changes nothing."""
    original = ng.contributions

    def target_only(params, x, half=None):
        width = x.shape[-1] // 2
        blinded = x.copy()
        blinded[..., :width] = 0.0
        return original(params, blinded)
    return swap(ng, "contributions", target_only)


def q10_the_null_scenario_propagates():
    original = gen.generate_multirelational

    def leaky(config=gen.MultirelationalConfig()):
        import dataclasses
        if config.scenario == "M0_NULL":
            config = dataclasses.replace(config, scenario="M1_MULTIRELATIONAL")
        return original(config)
    return swap(gen, "generate_multirelational", leaky)


def q11_edge_scores_come_from_the_weights_not_the_contributions():
    def internal(params, x, n_pairs):
        return np.repeat(float(np.abs(params["w2"]).mean()), n_pairs)
    return swap(ng, "edge_scores", internal)


def q12_the_union_is_not_the_union():
    original = ng.build_supports

    def truncated(commuting, similarity, n, include_all_pairs):
        supports = original(commuting, similarity, n, include_all_pairs)
        supports["typed_union"] = supports["commuting_only"].copy()
        return supports
    return swap(ng, "build_supports", truncated)


def q13_similarity_reads_the_whole_panel():
    original = ng.causal_similarity

    def leaky(view, decision_period, signal=ng.PRIMARY_SIGNAL):
        return original(view, len(view["signals"][signal]["values"]) - 1, signal)
    return swap(ng, "causal_similarity", leaky)


def q14_the_decoys_are_not_matched():
    original = gen.build_relations

    def unmatched(n, commuting, distance, similarity, edges_per_family, rng):
        relations = original(n, commuting, distance, similarity, edges_per_family, rng)
        # Decoys drawn at random rather than from the matched pool.
        relations["decoys"]["similarity"] = [
            (int(rng.integers(n)), int(rng.integers(n))) for _ in range(edges_per_family)]
        return relations
    return swap(gen, "build_relations", unmatched)


def q15_fitting_is_not_deterministic():
    original = ng.initialise

    def jittered(n_features, hidden, n_horizons, seed):
        params = original(n_features, hidden, n_horizons, seed)
        params["w1"] = params["w1"] + np.random.default_rng().normal(
            0.0, 1e-3, size=params["w1"].shape)
        return params
    return swap(ng, "initialise", jittered)


def q16_the_features_read_the_future():
    def leaky(series, window):
        out = np.full(series.shape, np.nan)
        for t in range(len(series)):
            seen = np.isfinite(series)
            if seen.sum() < 3:
                continue
            clock = np.arange(len(series), dtype=float)[:, None]
            mean_x = (seen * clock).sum(0) / np.maximum(seen.sum(0), 1)
            mean_y = np.where(seen, series, 0.0).sum(0) / np.maximum(seen.sum(0), 1)
            cx = (clock - mean_x) * seen
            cy = np.where(seen, series - mean_y, 0.0)
            variance = (cx ** 2).sum(0)
            out[t] = np.divide((cx * cy).sum(0), variance,
                               out=np.zeros(series.shape[1]), where=variance > 1e-12)
        return out
    return swap(tf, "_rolling_slope", leaky)


MUTANTS = [value for key, value in sorted(globals().items())
           if key.startswith("q") and key[1:3].isdigit() and callable(value)]


def main() -> int:
    survivors = []
    for mutant in MUTANTS:
        context = mutant()
        killed_by = []
        with context:
            for guard in guards.GUARDS:
                try:
                    guard()
                except Exception:                             # noqa: BLE001
                    killed_by.append(guard.__name__)
        if killed_by:
            print(f"killed   {mutant.__name__:52s} by {', '.join(killed_by[:2])}"
                  + (f" (+{len(killed_by) - 2})" if len(killed_by) > 2 else ""))
        else:
            survivors.append(mutant.__name__)
            print(f"SURVIVED {mutant.__name__}: no guard noticed")
    print(f"\n{len(MUTANTS) - len(survivors)}/{len(MUTANTS)} mutants killed")
    for name in survivors:
        print(f"  survivor: {name}")
    return 1 if survivors else 0


if __name__ == "__main__":
    sys.exit(main())
