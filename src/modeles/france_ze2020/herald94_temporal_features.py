"""HERALD 94: causal temporal features, and the declared composites built on them.

Every column produced here at period ``t`` is a function of observations released on or
before ``t``. The caller supplies a *released view* -- the same object HERALD 93 used, in
which nothing after the decision period and nothing whose publication lag has not elapsed is
visible -- and each feature reads only rows at or before its own. Causality is therefore a
property of the construction, and a guard checks it by rebuilding the table from a truncated
panel and requiring the shared rows to be identical rather than merely similar.

**Absence never becomes zero.** Zero is a legitimate value of a growth rate. Using it to
mean "not published" would make a stagnant zone indistinguishable from an unpublished one,
and every model here is linear or near-linear in its inputs, so the two would be given the
same response. Missingness is resolved in three declared steps, in order:

1. *carry forward within the zone*, from the last period at which the feature could be
   computed. This is what mixed frequency requires rather than what convenience suggests:
   the annual signals live at Q4 of a quarterly grid, so at Q1 the most recent employer
   establishment count is the one published at the previous Q4, and it is genuinely the best
   information available at that date. The availability channel is 1 only when the value is
   *fresh*, so the model can tell a current reading from a carried one;
2. *cross-sectional median at that period*, for cells with no history to carry -- the head of
   a series, before the observation window opens;
3. only if a feature is unavailable in every zone at that period does it become zero, and
   there its availability channel is zero too, which is what marks it as absent.

The unemployment rate is a bounded rate, so it enters on the logit scale; the count and
volume signals enter as logs. Year-over-year differences use lag 4 on the quarterly grid for
every signal, which removes seasonality from the difference instead of modelling it, and
makes the quarterly and annual signals comparable.
"""
from __future__ import annotations

import warnings
from typing import Any

import numpy as np

# One year on the quarterly grid. Every difference below is year-over-year.
YEAR_LAG = 4
TREND_WINDOW = 12
WINDOW = 8

PER_SIGNAL_FEATURES = (
    "level", "growth", "acceleration", "trend", "momentum", "volatility",
    "regime_expansion", "regime_deceleration", "regime_contraction", "regime_recovery",
    "national", "relative",
)

# Composites, declared before any result. `C1`, `C2`, `C3` and `C5` are linear functions of
# columns already in the table, so a linear model spanning it contains them exactly and they
# cannot improve it -- which is the point of listing them: they are the null half of the
# hypothesis. Only `C4` and `C6` are products.
COMPOSITE_SPEC: dict[str, dict[str, Any]] = {
    "C1_wage_per_head":        {"kind": "difference", "terms": (("payroll", "growth"),
                                                                ("headcount", "growth")),
                                "linear_in_features": True},
    "C2_size_per_site":        {"kind": "difference", "terms": (("headcount", "growth"),
                                                                ("establishments", "growth")),
                                "linear_in_features": True},
    "C3_creations_lead":       {"kind": "lagged", "terms": (("creations", "growth"),),
                                "lag": YEAR_LAG, "linear_in_features": True},
    "C4_tight_labour":         {"kind": "product", "terms": (("headcount", "growth"),
                                                             ("unemployment", "growth")),
                                "sign": -1.0, "linear_in_features": False},
    "C5_wage_intensity_turn":  {"kind": "difference", "terms": (("payroll", "acceleration"),
                                                                ("headcount", "acceleration")),
                                "linear_in_features": True},
    "C6_wage_by_regime":       {"kind": "regime_product",
                                "terms": (("payroll", "growth"),), "regime_of": "headcount",
                                "linear_in_features": False},
}
NONLINEAR_COMPOSITES = tuple(name for name, spec in COMPOSITE_SPEC.items()
                             if not spec["linear_in_features"])
LINEAR_COMPOSITES = tuple(name for name, spec in COMPOSITE_SPEC.items()
                          if spec["linear_in_features"])

# Universes that must never be divided by one another. SIDE creations count events in one
# universe and the active stock counts units in another; their ratio would measure the
# mismatch between the two registers, not a creation rate. Checked by guard.
FORBIDDEN_RATIOS = (("creations", "stock"), ("creations", "establishments_stock"))


def to_transform_scale(name: str, values: np.ndarray, mask: np.ndarray,
                       family: str) -> np.ndarray:
    """Logs for counts and volumes, logit for a bounded rate. Masked cells become NaN."""
    array = np.asarray(values, float)
    seen = np.asarray(mask, bool)
    if family == "logit_gaussian" or name == "unemployment":
        rate = np.clip(array / 100.0, 1e-4, 1.0 - 1e-4)
        out = np.log(rate / (1.0 - rate))
    else:
        out = np.log(np.maximum(array, 1e-9))
    return np.where(seen & np.isfinite(array), out, np.nan)


def _lagged_difference(series: np.ndarray, lag: int) -> np.ndarray:
    out = np.full_like(series, np.nan)
    if lag < len(series):
        out[lag:] = series[lag:] - series[:-lag]
    return out


def _rolling_slope(series: np.ndarray, window: int) -> np.ndarray:
    """Causal OLS slope of the series on time over the trailing ``window`` periods.

    NaN-aware: a period contributes only where it is observed, and the slope is defined
    only when at least three observations and some spread in time survive.
    """
    n_periods = len(series)
    out = np.full(series.shape, np.nan)
    time = np.arange(window, dtype=float)
    for t in range(n_periods):
        low = max(0, t - window + 1)
        block = series[low:t + 1]
        clock = time[:len(block)]
        seen = np.isfinite(block)
        count = seen.sum(0)
        enough = count >= 3
        if not np.any(enough):
            continue
        weight = seen.astype(float)
        total = np.maximum(count, 1)
        mean_x = (weight * clock[:, None]).sum(0) / total
        mean_y = np.where(seen, block, 0.0).sum(0) / total
        centred_x = (clock[:, None] - mean_x) * weight
        centred_y = np.where(seen, block - mean_y, 0.0)
        variance = (centred_x ** 2).sum(0)
        slope = np.divide((centred_x * centred_y).sum(0), variance,
                          out=np.full(series.shape[1], np.nan), where=variance > 1e-12)
        out[t] = np.where(enough, slope, np.nan)
    return out


def _rolling_stat(series: np.ndarray, window: int, kind: str) -> np.ndarray:
    n_periods = len(series)
    out = np.full(series.shape, np.nan)
    for t in range(n_periods):
        block = series[max(0, t - window + 1):t + 1]
        seen = np.isfinite(block)
        count = seen.sum(0)
        enough = count >= 2
        if not np.any(enough):
            continue
        filled = np.where(seen, block, 0.0)
        total = np.maximum(count, 1)
        mean = filled.sum(0) / total
        if kind == "mean":
            out[t] = np.where(enough, mean, np.nan)
        else:
            deviation = np.where(seen, block - mean, 0.0)
            out[t] = np.where(enough, np.sqrt((deviation ** 2).sum(0) / total), np.nan)
    return out


def _regime(growth: np.ndarray, acceleration: np.ndarray) -> np.ndarray:
    """Four mutually exclusive states, stacked as ``(4, T, N)``.

    A cell whose growth or acceleration is missing has no regime, and every one of its four
    channels is NaN rather than a silent "contraction". The states are a deterministic
    function of two columns already in the table, so they add nothing to a model that can
    form products -- which is exactly why `C6` is one of the two composites able to matter.
    """
    both = np.isfinite(growth) & np.isfinite(acceleration)
    rising = growth > 0.0
    speeding = acceleration >= 0.0
    states = np.stack([rising & speeding, rising & ~speeding,
                       ~rising & ~speeding, ~rising & speeding]).astype(float)
    return np.where(both[None, ...], states, np.nan)


def signal_features(name: str, values: np.ndarray, mask: np.ndarray,
                    family: str) -> dict[str, np.ndarray]:
    """The eleven-plus-one column block for one signal, all causal, NaN where undefined."""
    transformed = to_transform_scale(name, values, mask, family)
    growth = _lagged_difference(transformed, YEAR_LAG)
    acceleration = _lagged_difference(growth, YEAR_LAG)
    trend = _rolling_slope(transformed, TREND_WINDOW)
    average = _rolling_stat(growth, WINDOW, "mean")
    momentum = growth - average
    volatility = _rolling_stat(growth, WINDOW, "sd")
    regime = _regime(growth, acceleration)
    # The national component is the cross-zone mean of growth at each period: an aggregate
    # of the same released observations, identical across zones, never a future value.
    # A period at which no zone has published leaves an empty slice; the resulting NaN is
    # the correct answer and is resolved downstream by the declared missingness rules.
    with np.errstate(invalid="ignore"), warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        national = np.nanmean(np.where(np.isfinite(growth), growth, np.nan), axis=1)
    national = np.where(np.isfinite(national), national, np.nan)
    national_block = np.broadcast_to(national[:, None], growth.shape).copy()
    return {
        "level": transformed, "growth": growth, "acceleration": acceleration,
        "trend": trend, "momentum": momentum, "volatility": volatility,
        "regime_expansion": regime[0], "regime_deceleration": regime[1],
        "regime_contraction": regime[2], "regime_recovery": regime[3],
        "national": national_block, "relative": growth - national_block,
    }


def _carry_forward(block: np.ndarray) -> np.ndarray:
    """Last observed value carried forward within each zone. Causal by construction."""
    out = block.copy()
    seen = np.isfinite(out)
    index = np.where(seen, np.arange(len(out))[:, None], -1)
    index = np.maximum.accumulate(index, axis=0)
    valid = index >= 0
    safe = np.where(valid, index, 0)
    gathered = np.take_along_axis(np.nan_to_num(out, nan=0.0), safe, axis=0)
    return np.where(valid, gathered, np.nan)


def resolve_missing(block: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return ``(values, fresh)`` after the three declared steps.

    ``fresh`` is 1 only where the raw feature was computable at that very period, so a
    carried value is distinguishable from a current one. This is the availability channel
    the model receives.
    """
    fresh = np.isfinite(block).astype(float)
    carried = _carry_forward(block)
    still_missing = ~np.isfinite(carried)
    if np.any(still_missing):
        with np.errstate(invalid="ignore"), warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            median = np.nanmedian(np.where(np.isfinite(carried), carried, np.nan), axis=1)
        replacement = np.broadcast_to(median[:, None], carried.shape)
        carried = np.where(still_missing, replacement, carried)
    # Only a feature absent in every zone at that period reaches zero, and its availability
    # channel is already zero there.
    return np.nan_to_num(carried, nan=0.0, posinf=0.0, neginf=0.0), fresh


def composite_columns(raw: dict[str, dict[str, np.ndarray]]) -> dict[str, np.ndarray]:
    """The six declared composites, from the raw (pre-imputation) feature blocks.

    Built before imputation on purpose: a product of two carried-forward values would be a
    product of two stale readings, and the availability channels of its factors are what say
    so. The composite's own channel is the product of its factors' channels.
    """
    out: dict[str, np.ndarray] = {}
    for name, spec in COMPOSITE_SPEC.items():
        kind = spec["kind"]
        if kind == "difference":
            (first_signal, first_feature), (second_signal, second_feature) = spec["terms"]
            out[name] = raw[first_signal][first_feature] - raw[second_signal][second_feature]
        elif kind == "lagged":
            (signal, feature), = spec["terms"]
            series = raw[signal][feature]
            shifted = np.full_like(series, np.nan)
            lag = int(spec["lag"])
            shifted[lag:] = series[:-lag]
            out[name] = shifted
        elif kind == "product":
            (first_signal, first_feature), (second_signal, second_feature) = spec["terms"]
            out[name] = (raw[first_signal][first_feature]
                         * spec.get("sign", 1.0) * raw[second_signal][second_feature])
        elif kind == "regime_product":
            (signal, feature), = spec["terms"]
            series = raw[signal][feature]
            for state in ("expansion", "deceleration", "contraction", "recovery"):
                out[f"{name}_{state}"] = series * raw[spec["regime_of"]][f"regime_{state}"]
        else:
            raise ValueError(f"unknown composite kind {kind!r}")
    return out


def permute_raw_blocks(raw: dict[str, dict[str, np.ndarray]],
                       plan: dict[str, tuple[str, ...]], seed: int) -> None:
    """Permute named feature blocks across zones **within each period**, in place.

    This is the decisive control of the stage, and it has to act *here* -- on the raw blocks,
    before the composites are formed -- rather than on the assembled design matrix. Permuting
    an already-built product column would leave the product's factors still aligned with the
    rest of the row, so a model able to re-form the product from those factors would recover
    the interaction and the control would test nothing.

    Within-period permutation preserves every marginal distribution, every cross-sectional
    moment and every period effect exactly. The only quantity destroyed is the alignment
    between the permuted block and the rest of its zone's row.
    """
    rng = np.random.default_rng(seed)
    sample = next(iter(next(iter(raw.values())).values()))
    n_periods, n_zones = sample.shape
    # One order per period, shared by every permuted block: the blocks move together, so a
    # signal's features stay internally consistent and only their attachment to the zone is
    # broken. Independent orders per feature would also destroy each signal's own internal
    # structure and the control would then be testing something wider than the interaction.
    orders = [rng.permutation(n_zones) for _ in range(n_periods)]
    for signal, features in plan.items():
        for feature in features:
            block = raw[signal][feature]
            for period in range(n_periods):
                block[period] = block[period][orders[period]]


def build_feature_table(view: dict[str, Any], names: list[str] | None = None,
                        with_composites: bool = True,
                        permute: dict[str, tuple[str, ...]] | None = None,
                        permute_seed: int = 0) -> dict[str, Any]:
    """Assemble ``(T, N, F)`` features, their availability channels, and the column names.

    ``view`` is a released view: ``{"signals": {name: {"values", "availability_mask",
    "family", "freq"}}}``. Nothing else is read, and in particular no element of the
    generator's truth is reachable from here.
    """
    signals = view["signals"]
    names = list(names or signals)
    raw: dict[str, dict[str, np.ndarray]] = {}
    for name in names:
        block = signals[name]
        raw[name] = signal_features(name, np.asarray(block["values"], float),
                                    np.asarray(block["availability_mask"], bool),
                                    block.get("family", ""))
    if permute:
        permute_raw_blocks(raw, permute, permute_seed)

    columns: list[str] = []
    values: list[np.ndarray] = []
    available: list[np.ndarray] = []
    for name in names:
        for feature in PER_SIGNAL_FEATURES:
            resolved, fresh = resolve_missing(raw[name][feature])
            columns.append(f"{name}.{feature}")
            values.append(resolved)
            available.append(fresh)
    n_base = len(columns)

    if with_composites:
        for key, block in composite_columns(raw).items():
            resolved, fresh = resolve_missing(block)
            columns.append(f"composite.{key}")
            values.append(resolved)
            available.append(fresh)

    return {
        "features": np.stack(values, axis=-1),
        "available": np.stack(available, axis=-1),
        "columns": tuple(columns),
        "n_base_columns": n_base,
        "base_index": tuple(range(n_base)),
        "composite_index": tuple(range(n_base, len(columns))),
        "nonlinear_composite_index": tuple(
            index for index, column in enumerate(columns)
            if any(column.startswith(f"composite.{key}") for key in NONLINEAR_COMPOSITES)),
        "linear_composite_index": tuple(
            index for index, column in enumerate(columns)
            if any(column.startswith(f"composite.{key}") for key in LINEAR_COMPOSITES)),
        "signals": tuple(names),
    }


def target_growth(values: np.ndarray, mask: np.ndarray, family: str,
                  name: str) -> np.ndarray:
    """The evaluation target: realised year-over-year growth, ``(T, N)``, NaN where absent.

    Taken from the full panel because the evaluator is allowed to know what happened. The
    model never receives this array; the driver keeps it apart and opens it only after the
    arms have produced their predictions.
    """
    transformed = to_transform_scale(name, values, mask, family)
    return _lagged_difference(transformed, YEAR_LAG)
