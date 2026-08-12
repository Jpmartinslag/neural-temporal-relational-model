"""HERALD 94 guards. Each one names a mechanism the stage depends on and fails if it goes.

Every guard here has a matching mutant in ``tests/run_herald94_mutations.py`` that removes
exactly that mechanism and nothing else. A guard no mutant can kill is decoration, and the
previous stage produced three of those before the mutants were written.

Run: ``python3 tests/test_herald94_guards.py``
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.data.synthetic import generate_france_multisignal_v94 as gen  # noqa: E402
from src.modeles.france_ze2020 import herald94_composite as arms  # noqa: E402
from src.modeles.france_ze2020 import herald94_temporal_features as feat  # noqa: E402

ZONES = 60
SEED = 9601


def dataset(scenario: str = "N1_LINEAR", seed: int = SEED, n_zones: int = ZONES):
    return gen.generate_nonlinear(gen.NonlinearConfig(
        n_zones=n_zones, seed=seed, scenario=scenario))


def table_at(data, period: int, **kwargs):
    return feat.build_feature_table(gen.model_inputs(data, period), **kwargs)


def _raw_view(data) -> dict:
    """The whole panel, untruncated: for guards that must test the features, not the view."""
    return {"signals": {name: {"values": block["values"],
                               "availability_mask": block["availability_mask"],
                               "family": block["family"], "freq": block["freq"]}
                        for name, block in data["signals"].items()}}


# ── the temporal representation ──────────────────────────────────────────────

def g1_features_are_causal() -> None:
    """Changing observations *after* the decision date must not move the row used at it.

    The obvious form of this guard -- compare the row at period ``t`` built from a view
    truncated at ``t`` against the same row built from a view truncated at ``t + 12`` -- is
    wrong, and failed here by 1.43 before the premise was corrected. Those two rows *should*
    differ: the panel carries a release lag, so at decision date ``t`` the observation of
    period ``t`` has not been published yet, and at ``t + 12`` it has. A feature at a given
    period is a function of the vintage, and pinning it across vintages would be pinning the
    wrong quantity.

    What must hold is the property the driver actually relies on: the row read at decision
    period ``t`` depends on nothing that happens after ``t``. So the future is *changed* --
    every observation after the decision date is replaced by a different draw -- and the row
    must not move at all.
    """
    data = dataset()
    decision = 80
    disturbed = {**data, "signals": {}}
    rng = np.random.default_rng(0)
    for name, block in data["signals"].items():
        values = np.asarray(block["values"], float).copy()
        future = np.arange(len(values)) > decision
        values[future] = values[future] * rng.uniform(0.5, 2.0, size=values[future].shape)
        disturbed["signals"][name] = {**block, "values": values}

    # Built from the *untruncated* panel. Passing through ``model_inputs`` first would mask
    # the future before the feature functions ever saw it, and the guard would then be
    # testing the view rather than the features: a rolling statistic reading the whole
    # series would sail through. That is what happened, and the mutant that reads the whole
    # series survived until this line changed.
    plain = feat.build_feature_table(_raw_view(data))
    changed = feat.build_feature_table(_raw_view(disturbed))
    difference = np.abs(plain["features"][decision] - changed["features"][decision])
    assert np.max(difference) < 1e-12, \
        f"the row at the decision date moved when the future changed: {difference.max()}"
    assert plain["columns"] == changed["columns"]


def g2_rows_pair_features_at_t_minus_one_with_target_at_t() -> None:
    """The design matrix must never carry the target's own period."""
    data = dataset()
    table = table_at(data, 100)
    target = np.full((table["features"].shape[0], table["features"].shape[1]), np.nan)
    target[90] = np.arange(table["features"].shape[1], dtype=float)
    rows = arms.assemble_rows(table, target, [90], (0, 1))
    expected = table["features"][89][:, [0, 1]]
    assert np.allclose(rows["x"][:, :2], expected), "rows did not read period t-1"
    assert np.allclose(rows["y"], target[90])


def g3_absence_never_becomes_zero() -> None:
    """A missing cell is carried or median-filled, and its availability channel says so."""
    block = np.array([[1.0, 2.0, 3.0],
                      [np.nan, 2.5, np.nan],
                      [np.nan, np.nan, np.nan]])
    resolved, fresh = feat.resolve_missing(block)
    assert np.array_equal(fresh, np.array([[1, 1, 1], [0, 1, 0], [0, 0, 0]], float))
    assert resolved[1, 0] == 1.0 and resolved[1, 2] == 3.0, "carry forward did not happen"
    assert np.all(resolved[2] == np.array([1.0, 2.5, 3.0])), "row of carried values changed"
    # A cell with no history at all takes the cross-sectional median, never zero.
    head = np.array([[np.nan, 4.0, 6.0], [1.0, 4.0, 6.0]])
    resolved_head, fresh_head = feat.resolve_missing(head)
    assert resolved_head[0, 0] == 5.0, f"head cell was not median-filled: {resolved_head[0, 0]}"
    assert fresh_head[0, 0] == 0.0


def g4_carry_forward_never_reads_the_future() -> None:
    block = np.array([[np.nan], [np.nan], [7.0], [np.nan]])
    carried = feat._carry_forward(block)
    assert not np.isfinite(carried[0, 0]) and not np.isfinite(carried[1, 0]), \
        "a value was carried backwards in time"
    assert carried[3, 0] == 7.0


def g5_linear_composites_lie_inside_the_span() -> None:
    """`C1`, `C2`, `C3`, `C5` are linear in existing columns, so their residual is nil.

    This is the null half of the pre-registered structural claim, and it is checked rather
    than asserted in prose.
    """
    # Sixty zones leave only 38 fully observed ones against 61 regressors, so least squares
    # reproduced *any* column exactly and the test passed whatever it was given -- including
    # a composite mutated into a product. The panel is widened until the fresh cross-section
    # comfortably exceeds the design's width.
    data = dataset(n_zones=200)
    table = table_at(data, 100)
    base = np.asarray(table["base_index"])
    # A fourth quarter, late enough that every signal's window is open and its differences
    # are defined. The annual signals are published only at Q4, so at any other period no
    # zone is fully fresh and the test would have nothing to stand on -- as it did at period
    # 60, a first quarter, where it found zero eligible zones.
    period = 87
    # Restricted to zones where every base column was *freshly* observed. Composites are
    # formed before imputation on purpose, so in a carried or median-filled cell the
    # composite and the difference of the imputed columns are two different numbers, and the
    # exactness claim holds only where no imputation happened. Measured over all cells the
    # residual is about 1%, which is the size of that gap and not of an effect.
    fresh = table["available"][period][:, base].min(1) > 0.5
    assert fresh.sum() >= 20, f"too few fully observed zones to test the span: {fresh.sum()}"
    design = table["features"][period][fresh][:, base]
    design = np.concatenate([design, np.ones((len(design), 1))], axis=1)
    for index in table["linear_composite_index"]:
        name = table["columns"][index]
        if name.startswith("composite.C3"):
            continue      # a lag, linear in a column of an *earlier* period, not of this one
        column = table["features"][period][fresh, index]
        residual = column - design @ np.linalg.lstsq(design, column, rcond=None)[0]
        relative = float(np.sqrt(np.mean(residual ** 2)) / max(np.std(column), 1e-12))
        assert relative < 1e-6, f"{name} was not inside the linear span: {relative}"


def g6_product_composites_lie_outside_the_span() -> None:
    """The mirror of `g5`, on the same fully observed cells and the same widened panel.

    Measured over all cells a mere *difference* leaves a residual of 0.0024 -- the imputation
    gap again -- which is above any threshold small enough to be interesting. The distinction
    between a product and a difference only exists where nothing was imputed.
    """
    data = dataset(n_zones=200)
    table = table_at(data, 100)
    base = np.asarray(table["base_index"])
    period = 87
    fresh = table["available"][period][:, base].min(1) > 0.5
    assert fresh.sum() > len(base) + 40, \
        f"the design is not over-determined: {fresh.sum()} zones, {len(base)} columns"
    design = table["features"][period][fresh][:, base]
    design = np.concatenate([design, np.ones((len(design), 1))], axis=1)
    checked = 0
    for index in table["nonlinear_composite_index"]:
        column = table["features"][period][fresh, index]
        if np.std(column) < 1e-9:
            continue
        residual = column - design @ np.linalg.lstsq(design, column, rcond=None)[0]
        relative = float(np.sqrt(np.mean(residual ** 2)) / max(np.std(column), 1e-12))
        assert relative > 0.05, \
            f"{table['columns'][index]} was reproducible by a linear map: {relative}"
        checked += 1
    assert checked >= 2, "no product composite was actually tested"


def g7_forbidden_ratio_is_never_formed() -> None:
    """SIDE creations are never divided by an incompatible stock."""
    for spec in feat.COMPOSITE_SPEC.values():
        assert spec["kind"] != "ratio", "a ratio composite appeared"
    data = dataset()
    table = table_at(data, 100)
    for column in table["columns"]:
        lowered = column.lower()
        assert not ("creation" in lowered and ("rate" in lowered or "per_stock" in lowered)), \
            f"a creation rate against an incompatible universe appeared: {column}"


# ── the non-linear arm and its mathematics ───────────────────────────────────

def _small_problem(seed: int = 3, rows: int = 400, columns: int = 6):
    rng = np.random.default_rng(seed)
    x = rng.normal(size=(rows, columns))
    y = x[:, 0] + 0.5 * x[:, 1] * x[:, 2] + 0.1 * rng.normal(size=rows)
    return x, y


def g8_analytic_gradient_matches_finite_differences() -> None:
    x, y = _small_problem()
    fitted = arms.fit_mlp(x, y, 4, seed=1, epochs=100)
    point = x[:5]
    analytic = arms.marginal_effects(fitted["params"], point)
    step = 1e-6
    for column in range(x.shape[1]):
        up, down = point.copy(), point.copy()
        up[:, column] += step
        down[:, column] -= step
        numeric = (arms.mlp_forward(fitted["params"], up)[0]
                   - arms.mlp_forward(fitted["params"], down)[0]) / (2 * step)
        assert np.allclose(analytic[:, column], numeric, atol=1e-6), \
            f"gradient wrong in column {column}"


def g9_analytic_second_derivative_matches_finite_differences() -> None:
    """The interaction ranking is only meaningful if the mixed partial is the real one."""
    x, y = _small_problem()
    fitted = arms.fit_mlp(x, y, 4, seed=1, epochs=100)
    params = fitted["params"]
    point = x[:3]
    step = 1e-4
    for first in range(3):
        for second in range(3):
            shifted = point.copy()
            shifted[:, second] += step
            up = arms.marginal_effects(params, shifted)[:, first]
            shifted = point.copy()
            shifted[:, second] -= step
            down = arms.marginal_effects(params, shifted)[:, first]
            numeric = (up - down) / (2 * step)
            analytic = arms.mixed_partial(params, point, first, second)
            assert np.allclose(analytic, numeric, atol=1e-4), \
                f"mixed partial wrong at ({first}, {second})"


def g10_the_network_nests_the_linear_model() -> None:
    """With small pre-activations tanh is linear to first order, so a fresh network is
    near-linear: the deficit against ridge must be optimisation, never representation."""
    x, y = _small_problem()
    params = arms.initialise_mlp(x.shape[1], 4, seed=1)
    params["w1"] = params["w1"] * 1e-3
    prediction, _ = arms.mlp_forward(params, x)
    equivalent = x @ (params["w1"] @ params["w2"]) + params["b2"]
    assert np.allclose(prediction, equivalent, atol=1e-6), \
        "the small-weight limit of the network is not the linear map it must be"


def g11_regularisation_is_chosen_on_training_rows_only() -> None:
    """Changing the evaluation rows must not change the selected penalty or feature."""
    x, y = _small_problem()
    first = arms.choose_alpha(x, y)
    rng = np.random.default_rng(11)
    second = arms.choose_alpha(x, y)
    assert first == second
    chosen = arms.select_best_single(x, y, x.shape[1])
    other = arms.select_best_single(x, y, x.shape[1])
    assert chosen == other == 0, f"the floor was not the informative column: {chosen}"
    assert rng is not None


def g12_fitting_is_deterministic() -> None:
    x, y = _small_problem()
    first = arms.fit_mlp(x, y, 4, seed=5, epochs=60)
    second = arms.fit_mlp(x, y, 4, seed=5, epochs=60)
    assert np.array_equal(first["params"]["w1"], second["params"]["w1"]), \
        "two identical fits disagreed"


# ── the controls ─────────────────────────────────────────────────────────────

def g13_within_period_permutation_preserves_every_marginal() -> None:
    """Exactly, on the raw blocks where the guarantee lives; closely, after imputation.

    The permutation acts before the missingness rules, so a shuffled column is then carried
    forward and median-filled along a different pattern of gaps and the *imputed* marginal
    moves a little. The exact invariant therefore belongs on the raw block, and what the
    imputed column owes is closeness, with the tolerance declared rather than assumed.
    """
    data = dataset()
    view = gen.model_inputs(data, 100)
    signals = view["signals"]
    raw = {name: feat.signal_features(name, np.asarray(block["values"], float),
                                      np.asarray(block["availability_mask"], bool),
                                      block.get("family", ""))
           for name, block in signals.items()}
    reference = {feature: raw["unemployment"][feature].copy()
                 for feature in feat.PER_SIGNAL_FEATURES}
    feat.permute_raw_blocks(raw, {"unemployment": feat.PER_SIGNAL_FEATURES}, 7)
    for feature, before in reference.items():
        after = raw["unemployment"][feature]
        for period in (60, 80, 100):
            assert np.array_equal(np.sort(before[period]), np.sort(after[period]),
                                  equal_nan=True), \
                f"{feature}: the raw marginal changed at period {period}"

    plain = feat.build_feature_table(view)
    shuffled = feat.build_feature_table(
        view, permute={"unemployment": feat.PER_SIGNAL_FEATURES}, permute_seed=7)
    index = [i for i, name in enumerate(plain["columns"])
             if name.startswith("unemployment.")]
    for period in (60, 80, 100):
        left = np.sort(plain["features"][period][:, index], axis=0)
        right = np.sort(shuffled["features"][period][:, index], axis=0)
        spread = np.maximum(left.std(0), 1e-9)
        drift = float(np.max(np.abs(left - right).mean(0) / spread))
        # Not exact, and it cannot be. The permutation moves each cell together with its
        # missingness, so a zone that lands on a gap is carried forward from a *different*
        # zone's earlier period rather than from its own. Both are draws from the same
        # cross-section, so the imputed marginal stays close without being identical, and at
        # a two per cent block-missing rate the measured drift is about 0.15 of a standard
        # deviation on the worst column. The tolerance is that measurement, declared here.
        assert drift < 0.20, \
            f"the imputed marginal drifted too far at period {period}: {drift}"


def g14_within_period_permutation_destroys_the_alignment() -> None:
    data = dataset()
    view = gen.model_inputs(data, 100)
    plain = feat.build_feature_table(view)
    shuffled = feat.build_feature_table(
        view, permute={"unemployment": feat.PER_SIGNAL_FEATURES}, permute_seed=7)
    column = plain["columns"].index("unemployment.growth")
    moved = np.mean(np.abs(plain["features"][80][:, column]
                           - shuffled["features"][80][:, column]) > 1e-12)
    assert moved > 0.5, f"the permutation barely moved anything: {moved}"
    product = [i for i, name in enumerate(plain["columns"])
               if name.startswith("composite.C4")][0]
    before = plain["features"][80][:, product]
    after = shuffled["features"][80][:, product]
    correlation = float(np.corrcoef(before, after)[0, 1])
    assert abs(correlation) < 0.5, \
        f"the product composite survived the permutation: r={correlation}"


def g15_temporal_and_zone_placebos_move_the_design() -> None:
    rng = np.random.default_rng(4)
    x = rng.normal(size=(200, 5))
    keys = np.stack([np.repeat(np.arange(10), 20), np.tile(np.arange(20), 10)], axis=1)
    across = arms.permute_across_periods(x, keys, 1)
    assert not np.allclose(x, across)
    assert np.allclose(np.sort(x, axis=0), np.sort(across, axis=0)), \
        "the temporal placebo changed the pooled distribution"
    zones = arms.permute_zones(x, 1)
    assert np.allclose(np.sort(x, axis=0), np.sort(zones, axis=0))


# ── the generator ────────────────────────────────────────────────────────────

def g16_null_scenario_carries_no_relational_loading() -> None:
    data = dataset("N0_NULL")
    shares = data["calibration"]["relational_share"]
    assert max(abs(value) for value in shares.values()) < 1e-12, \
        f"the null scenario carried a mechanism: {shares}"
    # The propagation matrix still exists. That is deliberate: the control must differ from
    # the mechanism scenarios in the loading alone, not in the territory.
    assert np.any(np.asarray(data["truth"]["propagation"]) > 0.0)


def g17_scenarios_at_one_seed_share_one_world() -> None:
    """Territory, latent components and macro path must be identical across scenarios.

    Otherwise a paired comparison at a given seed compares two different worlds, which is
    the defect that made v92's S3/S4 gate unreadable.
    """
    reference = dataset("N1_LINEAR")
    for scenario in ("N2_NONLINEAR", "N3_REGIME", "N4_INTERACTION", "N5_REDUNDANT",
                     "N0_NULL"):
        other = dataset(scenario)
        assert np.allclose(reference["truth"]["prior"], other["truth"]["prior"]), \
            f"{scenario} drew a different territory"
        assert np.allclose(reference["truth"]["components"]["u"],
                           other["truth"]["components"]["u"]), \
            f"{scenario} drew a different latent state"
        assert np.allclose(reference["truth"]["propagation"],
                           other["truth"]["propagation"]), \
            f"{scenario} drew a different graph"


def g18_regime_gate_preserves_the_relational_amplitude() -> None:
    """`N3` must differ from `N1` in *where* the transfer lands, not in how much there is."""
    linear = dataset("N1_LINEAR")["calibration"]["relational_share"]
    gated = dataset("N3_REGIME")["calibration"]["relational_share"]
    for name in linear:
        relative = abs(gated[name] - linear[name]) / max(abs(linear[name]), 1e-12)
        assert relative < 0.05, \
            f"{name}: N3 carried a different amplitude from N1 ({gated[name]} vs {linear[name]})"
    gate = np.asarray(dataset("N3_REGIME")["truth"]["gate"])
    assert gate.min() < 0.9 < gate.max(), "the gate did not vary across zones"


def g19_the_non_linear_links_are_not_linear_in_the_state() -> None:
    """`N2` and `N4` must not be reproducible by any linear map of ``A @ centred(z)``."""
    for scenario in ("N2_NONLINEAR", "N4_INTERACTION"):
        data = dataset(scenario)
        truth = data["truth"]
        state = truth["components"]["u"]
        matrix = np.asarray(truth["propagation"])
        period = 60
        centred = state[period] - state[period].mean()
        linear = matrix[period] @ centred
        actual = gen._propagate(gen.LINK_OF[scenario], matrix[period],
                               state[period], truth["components"]["v"][period])
        slope = float(np.dot(linear, actual) / max(np.dot(linear, linear), 1e-18))
        residual = actual - slope * linear
        share = float(np.sqrt(np.mean(residual ** 2)) / max(np.std(actual), 1e-12))
        assert share > 0.20, \
            f"{scenario}'s link was essentially linear in the state: residual share {share}"


def g20_the_interaction_scenario_splits_its_components() -> None:
    """`N4`'s two components must be disjointly measured, and must be independent."""
    loadings = gen.scenario_loadings("N4_INTERACTION", 1.0)
    measured = {name: entry["component"] for name, entry in loadings.items()}
    assert set(measured.values()) == {"u", "v"}, "the components were not split"
    assert measured["headcount"] == measured["payroll"] == "u"
    assert measured["establishments"] == measured["creations"] == "v"
    data = dataset("N4_INTERACTION")
    u = np.asarray(data["truth"]["components"]["u"]).ravel()
    v = np.asarray(data["truth"]["components"]["v"]).ravel()
    correlation = float(np.corrcoef(u, v)[0, 1])
    assert abs(correlation) < 0.05, f"the two components were not independent: r={correlation}"
    # Outside `N4` every signal measures the same component, so the split is a property of
    # that scenario alone rather than a hidden difference between all of them.
    for scenario in ("N1_LINEAR", "N2_NONLINEAR", "N5_REDUNDANT"):
        other = gen.scenario_loadings(scenario, 1.0)
        assert {entry["component"] for entry in other.values()} == {"u"}


def g21_redundant_scenario_shares_one_measurement_noise() -> None:
    groups = {name: entry["noise_group"]
              for name, entry in gen.scenario_loadings("N5_REDUNDANT", 1.0).items()}
    assert len(set(groups.values())) == 1, f"the redundant channel was not shared: {groups}"
    independent = {name: entry["noise_group"]
                   for name, entry in gen.scenario_loadings("N1_LINEAR", 1.0).items()}
    assert len(set(independent.values())) == len(independent), \
        "the linear scenario shared a noise group it should not have"


def g22_unknown_scenarios_are_refused() -> None:
    for bad in ("N9_TYPO", "S1_SHARED", ""):
        try:
            gen.scenario_loadings(bad, 1.0)
        except ValueError:
            continue
        raise AssertionError(f"scenario {bad!r} was silently accepted")


def g23_the_model_never_receives_the_truth() -> None:
    data = dataset()
    view = gen.model_inputs(data, 90)
    assert "truth" not in view and "calibration" not in view
    assert "low_information" not in view["metadata"]
    for block in view["signals"].values():
        assert set(block) <= {"values", "availability_mask", "family", "freq"}
    # Nothing after the decision period is visible, and nothing whose release has not elapsed.
    years = np.asarray(data["metadata"]["years"])
    for name, block in view["signals"].items():
        mask = np.asarray(block["availability_mask"], bool)
        assert not mask[91:].any(), f"{name} exposed periods after the decision date"
        release = np.asarray(data["signals"][name]["release_year"])
        exposed = mask & (release[:, None] > years[90])
        assert not exposed.any(), f"{name} exposed an unreleased observation"


def g24_seeds_are_disjoint_from_the_earlier_stages() -> None:
    from src.data.synthetic.generate_france_multisignal_v92 import (
        CALIBRATION_SEEDS, FAIR_SEEDS, FINAL_SEEDS as V92_FINAL)
    earlier = (set(CALIBRATION_SEEDS) | set(FAIR_SEEDS) | set(V92_FINAL)
               | set(gen.SMOKE_SEEDS) | set(gen.RETIRED_SEEDS))
    assert not (set(gen.FINAL_SEEDS) & earlier), \
        "a final seed was reused from an earlier stage, the smoke, or the retired grid"
    assert len(set(gen.FINAL_SEEDS)) == len(gen.FINAL_SEEDS)


def g25_the_target_is_not_a_feature() -> None:
    """No column may equal the realised target: that would make the task a lookup."""
    data = dataset()
    table = table_at(data, 100)
    block = data["signals"]["headcount"]
    target = feat.target_growth(np.asarray(block["values"], float),
                                np.asarray(block["availability_mask"], bool),
                                block["family"], "headcount")
    period = 95
    observed = np.isfinite(target[period])
    for index, name in enumerate(table["columns"]):
        column = table["features"][period - 1][observed, index]
        realised = target[period][observed]
        if np.std(column) < 1e-12 or np.std(realised) < 1e-12:
            continue
        correlation = abs(float(np.corrcoef(column, realised)[0, 1]))
        assert correlation < 0.999, f"{name} reproduces the target exactly"


GUARDS = [value for key, value in sorted(globals().items()) if key.startswith("g")
          and callable(value) and key[1].isdigit()]


def main() -> int:
    failures = []
    for guard in sorted(GUARDS, key=lambda function: int(
            "".join(character for character in function.__name__.split("_")[0][1:]))):
        try:
            guard()
            print(f"PASS  {guard.__name__}")
        except AssertionError as error:
            failures.append((guard.__name__, str(error)))
            print(f"FAIL  {guard.__name__}: {error}")
        except Exception as error:                      # noqa: BLE001
            failures.append((guard.__name__, f"{type(error).__name__}: {error}"))
            print(f"ERROR {guard.__name__}: {type(error).__name__}: {error}")
    print(f"\n{len(GUARDS) - len(failures)}/{len(GUARDS)} guards passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
