"""Run HERALD with alternative regime encodings.

This wrapper keeps the public HERALD training scripts untouched.  It monkey
patches only two forecast-safe contracts for the current process:

1. annual feature selection, to remove manual COVID/rebound flags when needed;
2. regime vector construction, to swap manual flags for latent/inferred regimes.
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

import train_herald_v6 as base
import train_herald_semi_v2 as semiv2
from herald_regime_modes import (
    REGIME_MODES,
    build_regime_vectors as build_alt_regime_vectors,
    get_pelt_breakpoints,
    get_regime_metadata,
)


SOURCE_FLAG_COLUMNS = {
    "has_flores_source",
    "has_side_stock_source",
    "has_urssaf_source",
}

SIDE5_ALL = ["side_lag_1", "side_lag_2", "side_lag_3", "growth_1y", "growth_2y"]

# Phase 2I: features to drop beyond the no_flores_no_side_stock_a10 base.
_SIDE5_EXTRA_DROPS = {
    "side5_full":          [],
    "side5_drop_lag1":     ["side_lag_1"],
    "side5_drop_lag2":     ["side_lag_2"],
    "side5_drop_lag3":     ["side_lag_3"],
    "side5_drop_growth1y": ["growth_1y"],
    "side5_drop_growth2y": ["growth_2y"],
    "side5_lags_only":     ["growth_1y", "growth_2y"],
    "side5_growth_only":   ["side_lag_1", "side_lag_2", "side_lag_3"],
    "side5_lag1_growth1y": ["side_lag_2", "side_lag_3", "growth_2y"],
}

FEATURE_POLICIES = (
    "current_clean",
    "no_flores",
    "no_urssaf",
    "no_side_stock_a10",
    "no_flores_no_urssaf",
    "no_flores_no_side_stock_a10",
    "no_urssaf_no_side_stock_a10",
    "minimal_side_only",
    *sorted(_SIDE5_EXTRA_DROPS),
)

QUARTERLY_TENSOR_POLICIES = (
    "real",
    "zero",
    "temporal_perm",       # NOT fold-safe — do not use for causal claims
    "spatial_perm",
    "effectifs_only",
    "masse_only",
    "lag1",
    "effectifs_lag1",      # Phase 3E: lag1 + keep effectifs only
    "masse_lag1",          # Phase 3E: lag1 + keep masse_salariale only
    "lag2",                # Phase 3E: shift q_tensor 2 years back
    "effectifs_spatial_perm",  # Phase 3E: effectifs_only + spatial perm
    "lag1_spatial_perm",   # Phase 3E: lag1 + spatial perm
)


def apply_quarterly_tensor_policy(q, policy, rng_seed):
    """Transform the quarterly tensor for Phase 3D ablations.

    Args:
        q: [T, Q, N, 2] float32 array from build_quarterly_tensor
        policy: one of QUARTERLY_TENSOR_POLICIES
        rng_seed: integer seed for reproducible permutations
    Returns:
        transformed array of same shape
    """
    if policy == "real":
        return q
    if policy == "zero":
        return np.zeros_like(q)
    T, _Q, N, _C = q.shape
    rng = np.random.RandomState(rng_seed)
    if policy == "temporal_perm":
        perm = rng.permutation(T)
        return q[perm].copy()
    if policy == "spatial_perm":
        perm = rng.permutation(N)
        return q[:, :, perm, :].copy()
    if policy == "effectifs_only":
        q = q.copy()
        q[:, :, :, 1] = 0.0
        return q
    if policy == "masse_only":
        q = q.copy()
        q[:, :, :, 0] = 0.0
        return q
    if policy == "lag1":
        q_lag = np.zeros_like(q)
        q_lag[1:] = q[:-1]
        return q_lag
    if policy == "effectifs_lag1":
        q_lag = np.zeros_like(q)
        q_lag[1:] = q[:-1]
        q_lag[:, :, :, 1] = 0.0
        return q_lag
    if policy == "masse_lag1":
        q_lag = np.zeros_like(q)
        q_lag[1:] = q[:-1]
        q_lag[:, :, :, 0] = 0.0
        return q_lag
    if policy == "lag2":
        q_lag = np.zeros_like(q)
        q_lag[2:] = q[:-2]
        return q_lag
    if policy == "effectifs_spatial_perm":
        q = q.copy()
        q[:, :, :, 1] = 0.0
        perm = rng.permutation(N)
        return q[:, :, perm, :]
    if policy == "lag1_spatial_perm":
        q_lag = np.zeros_like(q)
        q_lag[1:] = q[:-1]
        perm = rng.permutation(N)
        return q_lag[:, :, perm, :]
    raise ValueError(f"Unknown quarterly_tensor_policy: {policy!r}")

MACRO_FEATURE_SETS = {
    "none": [],
    "climat_affaires": ["fr_climat_affaires_t_minus_1"],
    "climat_emploi": ["fr_climat_emploi_t_minus_1"],
    "climat_affaires_emploi": [
        "fr_climat_affaires_t_minus_1",
        "fr_climat_emploi_t_minus_1",
    ],
    "bdf_conj_services": ["fr_bdf_conj_services_climate_t_minus_1"],
    "bdf_gstix": ["fr_bdf_gstix_comp_t_minus_1"],
    "bdf_conj_gstix": [
        "fr_bdf_conj_services_climate_t_minus_1",
        "fr_bdf_gstix_comp_t_minus_1",
    ],
    "insee_bdf_core": [
        "fr_climat_affaires_t_minus_1",
        "fr_climat_emploi_t_minus_1",
        "fr_bdf_conj_services_climate_t_minus_1",
        "fr_bdf_gstix_comp_t_minus_1",
    ],
    "bdf_nowcast": ["fr_bdf_nowcast_pib_t_minus_1"],
    "climat_affaires_bdf": [
        "fr_climat_affaires_t_minus_1",
        "fr_bdf_nowcast_pib_t_minus_1",
    ],
    "climat_affaires_emploi_bdf": [
        "fr_climat_affaires_t_minus_1",
        "fr_climat_emploi_t_minus_1",
        "fr_bdf_nowcast_pib_t_minus_1",
    ],
}


def drop_source_flag_columns(cols):
    return [c for c in cols if c not in SOURCE_FLAG_COLUMNS]


def apply_feature_policy(cols, policy):
    """Remove input blocks for feature-noise ablations.

    URSSAF is mainly consumed through the quarterly tensor, so annual feature
    filtering handles FLORES/SIDE-stock while the quarterly branch is zeroed
    separately when the policy removes URSSAF.

    Phase 2I side5_* policies apply no_flores_no_side_stock_a10 as base, then
    drop specific SIDE5 features according to _SIDE5_EXTRA_DROPS.
    """
    if policy == "current_clean":
        return list(cols)
    if policy in _SIDE5_EXTRA_DROPS:
        out = [c for c in cols if not c.startswith("flores_")]
        out = [c for c in out if not c.startswith("side_stock_")]
        to_drop = set(_SIDE5_EXTRA_DROPS[policy])
        return [c for c in out if c not in to_drop]
    out = list(cols)
    if "no_flores" in policy or policy == "minimal_side_only":
        out = [c for c in out if not c.startswith("flores_")]
    if "no_side_stock_a10" in policy or policy == "minimal_side_only":
        out = [c for c in out if not c.startswith("side_stock_")]
    return out


def apply_ridge_feature_policy(df, policy):
    """Drop SIDE5 columns from the Ridge AR component for Phase 2I policies."""
    if policy not in _SIDE5_EXTRA_DROPS:
        return df
    to_drop = [c for c in _SIDE5_EXTRA_DROPS[policy] if c in df.columns]
    if not to_drop:
        return df
    return df.drop(columns=to_drop)


def expected_side5_features(policy):
    if policy not in _SIDE5_EXTRA_DROPS:
        return list(SIDE5_ALL)
    drop = set(_SIDE5_EXTRA_DROPS[policy])
    return [c for c in SIDE5_ALL if c not in drop]


def append_macro_features(cols, panel, macro_feature_set):
    extra = MACRO_FEATURE_SETS[macro_feature_set]
    missing = [c for c in extra if c not in panel.columns]
    if missing:
        raise ValueError(
            f"Macro feature set {macro_feature_set!r} requires missing columns: {missing}"
        )
    out = list(cols)
    for c in extra:
        if c not in out:
            out.append(c)
    return out


def policy_zeros_quarterly(policy):
    return "no_urssaf" in policy or policy == "minimal_side_only"


_FALSIFICATION_LABELS = frozenset({
    "falsify_regime_permute",
    "falsify_latent_inf_zero",
    "falsify_latent_frozen",
    "fold2021_probe",
})


def _peek_str(argv, flag, default=""):
    """Read a flag value from argv without consuming it."""
    for i, a in enumerate(argv):
        if a == flag and i + 1 < len(argv):
            return argv[i + 1]
        if a.startswith(flag + "="):
            return a[len(flag) + 1:]
    return default


def _peek_int(argv, flag, default=None):
    v = _peek_str(argv, flag, "")
    try:
        return int(v)
    except (ValueError, TypeError):
        return default


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--regime-mode", required=True, choices=REGIME_MODES)
    parser.add_argument("--drop-source-flags", action="store_true")
    parser.add_argument("--feature-policy", default="current_clean", choices=FEATURE_POLICIES)
    parser.add_argument("--macro-feature-set", default="none", choices=sorted(MACRO_FEATURE_SETS))
    parser.add_argument("--quarterly-tensor-policy", default="real", choices=QUARTERLY_TENSOR_POLICIES)
    parser.add_argument("--regime-metadata-path", type=Path, default=None)
    parser.add_argument("--experiment-label", default="")
    # Only the four args the wrapper owns are consumed here.
    # All semi_v2 knobs (smooth-regime-source, latent-*-mode, regime-seq-transform,
    # single-target-year) stay in `remaining` so semiv2.main() receives them intact.
    # Their values are peeked directly from sys.argv for metadata recording only.
    regime_args, remaining = parser.parse_known_args()

    original_feature_columns = base.feature_columns
    original_fit_ridge_ar = base.fit_ridge_ar
    original_predict_ridge_future = base.predict_ridge_future
    original_build_regime_vectors = base.build_regime_vectors
    original_build_quarterly_tensor = base.build_quarterly_tensor
    feature_columns_seen = []
    ridge_columns_seen = []
    zeroed_quarterly = policy_zeros_quarterly(regime_args.feature_policy)
    qtensor_policy = regime_args.quarterly_tensor_policy
    perm_seed = _peek_int(remaining, "--seed", 42)

    def patched_feature_columns(panel, ablation="full"):
        if regime_args.regime_mode == "manual_flags":
            cols = original_feature_columns(panel, ablation="full")
        else:
            cols = original_feature_columns(panel, ablation="regime_exclusive")
        if regime_args.drop_source_flags:
            cols = drop_source_flag_columns(cols)
        cols = apply_feature_policy(cols, regime_args.feature_policy)
        cols = append_macro_features(cols, panel, regime_args.macro_feature_set)
        feature_columns_seen[:] = cols
        return cols

    def patched_fit_ridge_ar(train, test):
        train_p = apply_ridge_feature_policy(train, regime_args.feature_policy)
        test_p = apply_ridge_feature_policy(test, regime_args.feature_policy)
        ridge_cols = [
            c for c in SIDE5_ALL
            if c in train_p.columns and c in test_p.columns
        ]
        ridge_columns_seen[:] = ridge_cols
        return original_fit_ridge_ar(train_p, test_p)

    def patched_predict_ridge_future(train_df, future_df):
        train_p = apply_ridge_feature_policy(train_df, regime_args.feature_policy)
        future_p = apply_ridge_feature_policy(future_df, regime_args.feature_policy)
        ridge_cols = [
            c for c in SIDE5_ALL
            if c in train_p.columns and c in future_p.columns
        ]
        ridge_columns_seen[:] = ridge_cols
        return original_predict_ridge_future(train_p, future_p)

    def patched_build_regime_vectors(panel, years_sorted, train_max, **kwargs):
        if regime_args.regime_mode == "manual_flags":
            return original_build_regime_vectors(panel, years_sorted, train_max)
        return build_alt_regime_vectors(
            panel, years_sorted, train_max, regime_args.regime_mode, **kwargs
        )

    def patched_build_quarterly_tensor(*args, **kwargs):
        q = original_build_quarterly_tensor(*args, **kwargs)
        if zeroed_quarterly:
            return np.zeros_like(q)
        if qtensor_policy != "real":
            q = apply_quarterly_tensor_policy(q, qtensor_policy, perm_seed)
        return q

    base.feature_columns = patched_feature_columns
    base.fit_ridge_ar = patched_fit_ridge_ar
    base.predict_ridge_future = patched_predict_ridge_future
    base.build_regime_vectors = patched_build_regime_vectors
    base.build_quarterly_tensor = patched_build_quarterly_tensor

    try:
        # Re-inject quarterly_tensor_policy so semiv2 can record it in the per-run JSON.
        remaining = list(remaining) + ["--quarterly-tensor-policy", qtensor_policy]
        sys.argv = [sys.argv[0], *remaining]
        semiv2.main()
    finally:
        base.feature_columns = original_feature_columns
        base.fit_ridge_ar = original_fit_ridge_ar
        base.predict_ridge_future = original_predict_ridge_future
        base.build_regime_vectors = original_build_regime_vectors
        base.build_quarterly_tensor = original_build_quarterly_tensor

    if regime_args.regime_metadata_path is not None:
        regime_args.regime_metadata_path.parent.mkdir(parents=True, exist_ok=True)
        # Peek values from remaining (forwarded to semiv2, not consumed by this parser).
        smooth_src = _peek_str(remaining, "--smooth-regime-source", "explicit")
        latent_train = _peek_str(remaining, "--latent-train-mode", "normal")
        latent_inf_raw = _peek_str(remaining, "--latent-inference-mode", "match_train")
        eff_latent_inf = latent_train if latent_inf_raw == "match_train" else latent_inf_raw
        regime_transform = _peek_str(remaining, "--regime-seq-transform", "none")
        tutor_feature_set = _peek_str(remaining, "--tutor-feature-set", "none")
        tutor_transform = _peek_str(remaining, "--tutor-state-transform", "none")
        labor_tutor_fset = _peek_str(remaining, "--labor-tutor-feature-set", "none")
        single_year = _peek_int(remaining, "--single-target-year", None)
        _side5_remaining = set(feature_columns_seen) & set(SIDE5_ALL)
        _dropped_side5 = sorted(set(SIDE5_ALL) - _side5_remaining)
        if not ridge_columns_seen:
            ridge_columns_seen[:] = expected_side5_features(regime_args.feature_policy)
        payload = {
            "regime_mode": regime_args.regime_mode,
            "experiment_label": regime_args.experiment_label,
            "is_falsification_test": regime_args.experiment_label in _FALSIFICATION_LABELS,
            "manual_flags_in_annual_features": regime_args.regime_mode == "manual_flags",
            "manual_flags_in_regime_vector": regime_args.regime_mode == "manual_flags",
            "source_flags_in_annual_features": not regime_args.drop_source_flags,
            "dropped_source_flags": sorted(SOURCE_FLAG_COLUMNS) if regime_args.drop_source_flags else [],
            "feature_policy": regime_args.feature_policy,
            "macro_feature_set": regime_args.macro_feature_set,
            "macro_features": list(MACRO_FEATURE_SETS[regime_args.macro_feature_set]),
            "tutor_feature_set": tutor_feature_set,
            "tutor_state_transform": tutor_transform,
            "labor_tutor_feature_set": labor_tutor_fset,
            "annual_feature_count": len(feature_columns_seen),
            "annual_features": list(feature_columns_seen),
            "dropped_side5_features": _dropped_side5,
            "ridge_features": list(ridge_columns_seen),
            "ridge_dropped_side5_features": sorted(set(SIDE5_ALL) - set(ridge_columns_seen)),
            "quarterly_tensor_policy": qtensor_policy,
            "quarterly_tensor_zeroed": bool(zeroed_quarterly) or qtensor_policy == "zero",
            "q_tensor_channels_active": (
                [] if (zeroed_quarterly or qtensor_policy == "zero")
                else ["effectifs_salaries_cvs"] if qtensor_policy == "effectifs_only"
                else ["masse_salariale_cvs"] if qtensor_policy == "masse_only"
                else ["effectifs_salaries_cvs", "masse_salariale_cvs"]
            ),
            "q_tensor_transform_seed": (
                perm_seed if qtensor_policy in {"temporal_perm", "spatial_perm"} else None
            ),
            "smooth_regime_source": smooth_src,
            "latent_train_mode": latent_train,
            "latent_inference_mode": eff_latent_inf,
            "regime_seq_transform": regime_transform,
            "single_target_year": single_year,
            "comparison_is_symmetric": smooth_src != "explicit",
            "training_entrypoint": "src/modeles/train_herald_regime_experiment.py",
            "wrapped_entrypoint": "src/modeles/train_herald_semi_v2.py",
        }
        # Save PELT breakpoints per fold for causality audit (Phase 2D H2)
        if regime_args.regime_mode.startswith("pelt_") or regime_args.regime_mode == "resid_pelt":
            pelt_bkps = get_pelt_breakpoints()
            payload["pelt_breakpoints_by_train_max"] = {
                str(k): v for k, v in sorted(pelt_bkps.items())
            }
        regime_meta = get_regime_metadata()
        if regime_meta:
            payload["regime_diagnostics_by_train_max"] = {
                str(k): v for k, v in sorted(regime_meta.items())
            }
        regime_args.regime_metadata_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
