"""HERALD 96 guards. Fifteen mechanisms the stage depends on, each with a matching mutant.

Run: ``python3 tests/test_herald96_guards.py``
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.data.synthetic import generate_multirelational_v96 as gen  # noqa: E402
from src.modeles.france_ze2020 import herald94_temporal_features as tf  # noqa: E402
from src.modeles.france_ze2020 import herald96_neural_granger as ng  # noqa: E402

ZONES = 80
SEED = 9951


def dataset(scenario: str = "M1_MULTIRELATIONAL", scale: float = 1.0,
            n_zones: int = ZONES, seed: int = SEED):
    return gen.generate_multirelational(gen.MultirelationalConfig(
        n_zones=n_zones, seed=seed, scenario=scenario, relational_scale=scale))


def _setup(data):
    block = data["signals"]["headcount"]
    target = tf.target_growth(np.asarray(block["values"], float),
                              np.asarray(block["availability_mask"], bool),
                              block["family"], "headcount")
    n_periods = len(data["metadata"]["years"])
    origins = list(range(n_periods - 12, n_periods))
    table = tf.build_feature_table(gen.model_inputs(data, origins[0] - 1))
    baseline = ng.fit_frozen_baseline(table, target, list(range(24, origins[0])))
    return table, target, baseline, origins


def p1_no_future_reaches_the_features() -> None:
    """Changing observations after the decision date must not move the row read at it."""
    data = dataset()
    decision = 80
    disturbed = {**data, "signals": {}}
    rng = np.random.default_rng(0)
    for name, block in data["signals"].items():
        values = np.asarray(block["values"], float).copy()
        future = np.arange(len(values)) > decision
        values[future] = values[future] * rng.uniform(0.5, 2.0, size=values[future].shape)
        disturbed["signals"][name] = {**block, "values": values}
    raw = lambda payload: {"signals": {                       # noqa: E731
        name: {"values": b["values"], "availability_mask": b["availability_mask"],
               "family": b["family"], "freq": b["freq"]}
        for name, b in payload["signals"].items()}}
    plain = tf.build_feature_table(raw(data))
    changed = tf.build_feature_table(raw(disturbed))
    moved = np.abs(plain["features"][decision] - changed["features"][decision]).max()
    assert moved < 1e-12, f"the decision-date row moved when the future changed: {moved}"


def p2_the_baseline_is_genuinely_frozen() -> None:
    """Relational training must not move a single baseline coefficient."""
    data = dataset()
    table, target, baseline, origins = _setup(data)
    before = np.array(baseline["beta"], copy=True)
    checksum = baseline["checksum"]

    pairs = np.array(np.nonzero(ng.commuting_support(data["truth"]["commuting"], k=5)))
    design = ng.pair_features(table, pairs, origins[:4])
    params = ng.initialise(design["x"].shape[-1], 4, len(ng.HORIZONS), seed=1)
    targets = np.zeros((len(origins[:4]), len(table["features"][0]), len(ng.HORIZONS)))
    masks = np.ones_like(targets)
    ng.fit(params, design["x"], pairs, targets, masks, len(table["features"][0]), epochs=5)

    assert np.array_equal(baseline["beta"], before), "a baseline coefficient moved"
    assert baseline["checksum"] == checksum


def p3_the_arm_has_no_local_path() -> None:
    """A zone with no incoming candidate must receive exactly zero prediction.

    If any local term existed, an isolated zone would still be predicted, and the arm's
    apparent skill could come from the target's own history rather than from a relation.
    """
    n_zones = 12
    pairs = np.array([[0, 1, 2], [3, 3, 4]])          # nothing arrives at zone 7
    rng = np.random.default_rng(2)
    x = rng.normal(size=(5, pairs.shape[1], 6))
    params = ng.initialise(6, 4, len(ng.HORIZONS), seed=3)
    prediction, _ = ng.predict_residual(params, x, pairs, n_zones)
    assert np.all(prediction[:, 7, :] == 0.0), "an isolated zone received a prediction"
    assert np.any(prediction[:, 3, :] != 0.0), "a connected zone received nothing"


def p4_the_residual_is_observed_minus_frozen_baseline() -> None:
    data = dataset()
    table, target, baseline, origins = _setup(data)
    block = ng.residual_target(baseline, table, target, origins[:3])
    scored = ng.baseline_prediction(baseline, table, target, origins[:3])
    assert np.allclose(block["residual"], scored["y"] - scored["prediction"], atol=0.0)
    # And the residual must be smaller than the raw target: the baseline does work.
    assert block["residual"].std() < scored["y"].std(), \
        "the residual is not smaller than the observed target"


def p5_no_prior_or_similarity_weight_enters_the_arm() -> None:
    """The arm's design matrix is trajectories only, never a candidate-generator weight."""
    data = dataset()
    table, _, _, origins = _setup(data)
    commuting = data["truth"]["commuting"]
    pairs = np.array(np.nonzero(ng.commuting_support(commuting, k=5)))
    design = ng.pair_features(table, pairs, origins[:3])
    width = design["x"].shape[-1]
    per_signal = len(tf.PER_SIGNAL_FEATURES)
    assert width == 2 * per_signal, \
        f"the design carries {width} columns, not the {2 * per_signal} trajectory ones"
    weights = commuting[pairs[0], pairs[1]]
    for column in range(width):
        values = design["x"][0][:, column]
        if values.std() < 1e-12 or weights.std() < 1e-12:
            continue
        correlation = abs(float(np.corrcoef(values, weights)[0, 1]))
        assert correlation < 0.999, f"column {column} reproduces the commuting weight"


def p6_relations_outside_commuting_exist_in_the_truth() -> None:
    data = dataset()
    outside = data["calibration"]["true_edges_outside_commuting"]
    assert outside["similarity"] == data["calibration"]["edges_per_family"]["similarity"]
    assert outside["complementarity"] == \
        data["calibration"]["edges_per_family"]["complementarity"]
    assert outside["commuting"] == 0, "a commuting-family edge fell outside commuting"
    # And they are genuinely unreachable from the commuting-only support.
    support = ng.commuting_support(data["truth"]["commuting"])
    for family in ("similarity", "complementarity"):
        for source, target in data["truth"]["relations"]["edges"][family]:
            assert not support[source, target], \
                f"a {family} edge is inside the commuting support after all"


def p7_the_model_can_consider_those_relations() -> None:
    """The similarity and union supports must actually contain some of them."""
    data = dataset()
    view = gen.model_inputs(data, 90)
    similarity = ng.causal_similarity(view, 90)
    supports = ng.build_supports(data["truth"]["commuting"], similarity, ZONES, True)
    for name in ("similarity_only", "typed_union", "all_pairs"):
        reachable = sum(
            1 for family in ("similarity", "complementarity")
            for source, target in data["truth"]["relations"]["edges"][family]
            if supports[name][source, target])
        assert reachable > 0, f"{name} contains no out-of-commuting true edge"
    assert sum(
        1 for family in ("similarity", "complementarity")
        for source, target in data["truth"]["relations"]["edges"][family]
        if supports["commuting_only"][source, target]) == 0


def p8_all_pairs_really_is_all_pairs() -> None:
    support = ng.all_pairs_support(ZONES)
    assert support.sum() == ZONES * (ZONES - 1)
    assert not np.any(np.diag(support))


def p9_the_group_penalty_acts_on_source_contributions() -> None:
    """A large penalty must drive contributions towards zero; a small one must not."""
    rng = np.random.default_rng(4)
    n_zones, n_periods, n_pairs = 10, 6, 20
    pairs = np.array([rng.integers(0, n_zones, n_pairs),
                      rng.integers(0, n_zones, n_pairs)])
    x = rng.normal(size=(n_periods, n_pairs, 6))
    targets = rng.normal(size=(n_periods, n_zones, len(ng.HORIZONS)))
    masks = np.ones_like(targets)
    sizes = {}
    for penalty in (0.0, 1.0):
        params = ng.initialise(6, 4, len(ng.HORIZONS), seed=5)
        ng.fit(params, x, pairs, targets, masks, n_zones, epochs=120,
               group_penalty=penalty)
        sizes[penalty] = float(np.abs(ng.contributions(params, x)[0]).mean())
    assert sizes[1.0] < 0.25 * sizes[0.0], \
        f"the group penalty barely shrank the contributions: {sizes}"


def p10_shuffling_a_source_destroys_its_contribution() -> None:
    """Permuting the source half of the design changes what that source contributes."""
    rng = np.random.default_rng(6)
    x = rng.normal(size=(4, 15, 8))
    params = ng.initialise(8, 4, len(ng.HORIZONS), seed=7)
    plain, _ = ng.contributions(params, x)
    shuffled = x.copy()
    order = rng.permutation(x.shape[1])
    shuffled[:, :, :4] = shuffled[:, order, :4]
    moved, _ = ng.contributions(params, shuffled)
    changed = float(np.mean(np.abs(plain - moved) > 1e-9))
    assert changed > 0.5, f"shuffling the source changed only {changed:.2%} of contributions"


def p11_the_null_scenario_hides_no_propagation() -> None:
    data = dataset(scenario="M0_NULL")
    assert max(abs(v) for v in data["calibration"]["relational_share"].values()) < 1e-12
    for matrix in data["truth"]["matrices"].values():
        assert np.all(matrix == 0.0), "the null scenario kept a propagation matrix"
    assert np.abs(np.asarray(data["truth"]["total_arriving"])).max() < 1e-12


def p12_edges_are_typed_and_the_type_is_reporting_only() -> None:
    data = dataset()
    view = gen.model_inputs(data, 90)
    similarity = ng.causal_similarity(view, 90)
    supports = ng.build_supports(data["truth"]["commuting"], similarity, ZONES, False)
    pairs = np.array(np.nonzero(supports["typed_union"]))
    types = ng.edge_types(supports, pairs)
    assert set(types) == {"from_commuting", "from_similarity"}
    assert types["from_commuting"].sum() > 0 and types["from_similarity"].sum() > 0
    assert len(types["from_commuting"]) == pairs.shape[1]
    # The union is exactly the union, so no edge is invented by the labelling.
    assert supports["typed_union"].sum() == (
        supports["commuting_only"] | supports["similarity_only"]).sum()


def p13_causal_similarity_uses_only_released_history() -> None:
    data = dataset()
    # Handed the *same*, untruncated panel and two different decision dates. If the function
    # honours its argument the two differ; if it silently reads the whole series they are
    # identical. Passing pre-truncated views instead hides that, because the truncation
    # already did the work -- which is how a mutant reading the whole panel survived.
    full = {"signals": {name: {"values": block["values"],
                               "availability_mask": block["availability_mask"],
                               "family": block["family"], "freq": block["freq"]}
                        for name, block in data["signals"].items()}}
    short = ng.causal_similarity(full, 60)
    long = ng.causal_similarity(full, 100)
    assert not np.allclose(np.nan_to_num(short, neginf=0.0),
                           np.nan_to_num(long, neginf=0.0)), \
        "the similarity ignores its decision date, so it is not causal"

    early = ng.causal_similarity(gen.model_inputs(data, 70), 70)
    late = ng.causal_similarity(gen.model_inputs(data, 100), 100)
    assert not np.allclose(np.nan_to_num(early, neginf=0.0),
                           np.nan_to_num(late, neginf=0.0)), \
        "the similarity does not change as history accumulates, so it may be non-causal"
    # It must be a weak proxy for the latent profile: strong enough to propose, too weak to
    # identify. Measured, not asserted.
    truth = np.asarray(data["truth"]["profile_similarity"])
    finite = np.isfinite(truth) & np.isfinite(late)
    correlation = float(np.corrcoef(truth[finite], late[finite])[0, 1])
    assert 0.05 < correlation < 0.95, \
        f"observable similarity correlates {correlation:.3f} with the latent profile"


def p13b_decoys_are_matched_to_their_true_edges() -> None:
    """Within a family, true pairs and decoys must be comparable on distance and profile.

    If they are not, a detector ranking on either quantity separates the classes for free and
    is credited with a discovery it never made. Nothing else in the suite checked this, and a
    mutant drawing decoys at random survived.
    """
    data = dataset()
    truth = data["truth"]
    distance = np.asarray(truth["distance"])
    profile = np.asarray(truth["profile_similarity"])
    for family in ("similarity", "complementarity"):
        edges = truth["relations"]["edges"][family]
        decoys = truth["relations"]["decoys"][family]
        assert len(decoys) >= 0.5 * len(edges), f"{family}: too few decoys to match against"
        for name, matrix, tolerance in (("distance", distance, 0.20),
                                        ("profile", profile, 0.25)):
            true_value = float(np.median([matrix[s, t] for s, t in edges]))
            decoy_value = float(np.median([matrix[s, t] for s, t in decoys]))
            spread = float(np.std(matrix[np.isfinite(matrix)]))
            gap = abs(true_value - decoy_value) / max(spread, 1e-12)
            assert gap < tolerance, \
                (f"{family}: {name} differs between true and decoy by {gap:.2f} standard "
                 f"deviations ({true_value:.3f} against {decoy_value:.3f})")


def p14_the_arms_run_different_code() -> None:
    """The oracle, the arm and the baseline must not be the same function."""
    assert ng.fit_frozen_baseline is not ng.fit
    assert ng.edge_scores is not ng.contributions
    rng = np.random.default_rng(8)
    x = rng.normal(size=(3, 10, 6))
    params = ng.initialise(6, 4, len(ng.HORIZONS), seed=9)
    scores = ng.edge_scores(params, x, 10)
    assert scores.shape == (10,), "edge scores are not one per pair"
    assert np.all(scores >= 0.0)
    # The score must be the measured contribution, so it has to differ between pairs and
    # equal the root-mean-square of what those pairs actually contributed. A mutant returning
    # a function of the weights alone passed the shape check happily.
    assert scores.std() > 1e-9, "every pair received the same score"
    contribution, _ = ng.contributions(params, x)
    expected = np.sqrt((contribution ** 2).mean(axis=(0, 2)))
    assert np.allclose(scores, expected), \
        "the edge score is not the measured contribution of the source"


def p15_fitting_is_deterministic_and_worlds_are_paired() -> None:
    rng = np.random.default_rng(10)
    n_zones, n_pairs = 8, 12
    pairs = np.array([rng.integers(0, n_zones, n_pairs), rng.integers(0, n_zones, n_pairs)])
    x = rng.normal(size=(4, n_pairs, 6))
    targets = rng.normal(size=(4, n_zones, len(ng.HORIZONS)))
    masks = np.ones_like(targets)
    first = ng.fit(ng.initialise(6, 4, len(ng.HORIZONS), 11), x, pairs, targets, masks,
                   n_zones, epochs=25)
    second = ng.fit(ng.initialise(6, 4, len(ng.HORIZONS), 11), x, pairs, targets, masks,
                    n_zones, epochs=25)
    assert np.array_equal(first["params"]["w1"], second["params"]["w1"]), \
        "two identical fits disagreed"
    # Paired worlds: only the relational loading may differ between scales.
    left, right = dataset(scale=0.0), dataset(scale=1.0)
    assert np.array_equal(left["truth"]["commuting"], right["truth"]["commuting"])
    assert np.array_equal(left["truth"]["profile"], right["truth"]["profile"])
    assert left["truth"]["relations"]["edges"] == right["truth"]["relations"]["edges"]
    for name in left["signals"]:
        assert np.array_equal(np.asarray(left["signals"][name]["availability_mask"]),
                              np.asarray(right["signals"][name]["availability_mask"])), \
            f"{name}: masks differ between scales"


GUARDS = [value for key, value in sorted(globals().items()) if key.startswith("p")
          and callable(value) and key[1].isdigit()]


def main() -> int:
    failures = []
    for guard in sorted(GUARDS, key=lambda f: int(
            "".join(c for c in f.__name__.split("_")[0][1:] if c.isdigit()))):
        try:
            guard()
            print(f"PASS  {guard.__name__}")
        except AssertionError as error:
            failures.append(guard.__name__)
            print(f"FAIL  {guard.__name__}: {error}")
        except Exception as error:                      # noqa: BLE001
            failures.append(guard.__name__)
            print(f"ERROR {guard.__name__}: {type(error).__name__}: {error}")
    print(f"\n{len(GUARDS) - len(failures)}/{len(GUARDS)} guards passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
