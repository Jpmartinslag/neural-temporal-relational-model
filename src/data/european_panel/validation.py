"""
HERALD European Panel — validation layer.

Run after each country adapter produces its panel, before any training.
All checks are non-destructive: they report issues but do not modify the data.

Usage
-----
    from src.data.european_panel.validation import validate_panel, print_report

    panel = france_adapter.build()
    report = validate_panel(panel, country="FR", expected_years=range(2008, 2025))
    print_report(report)
    if report["errors"]:
        raise ValueError("Panel failed validation — fix errors before training.")
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd

from .schema import (
    REQUIRED_FIELDS,
    OPTIONAL_FIELDS,
    EU_SIGNAL_FIELDS,
    MASK_FIELDS,
    SECTOR_FIELDS,
    FIELD_BY_NAME,
    ID_FIELDS,
    NON_PREDICTIVE_FIELDS,
)


def validate_panel(
    df: pd.DataFrame,
    country: str,
    expected_years: Optional[range] = None,
) -> dict:
    """
    Run all validation checks on a European panel DataFrame.

    Returns
    -------
    dict with keys:
        "errors"   : list[str] — must be empty before training
        "warnings" : list[str] — non-blocking, logged for reproducibility
        "info"     : dict      — summary statistics for reporting
    """
    errors:   list[str] = []
    warnings: list[str] = []
    info:     dict = {"country": country}

    # ── 1. Required fields present ────────────────────────────────────────
    missing_required = [f for f in REQUIRED_FIELDS if f not in df.columns]
    if missing_required:
        errors.append(f"Missing required fields: {missing_required}")

    present_optional = [f for f in OPTIONAL_FIELDS if f in df.columns]
    absent_optional  = [f for f in OPTIONAL_FIELDS if f not in df.columns]
    info["optional_coverage"] = len(present_optional) / max(len(OPTIONAL_FIELDS), 1)
    if absent_optional:
        warnings.append(f"Optional fields absent ({len(absent_optional)}): {absent_optional[:10]}{'…' if len(absent_optional) > 10 else ''}")

    # Stop early if required fields are missing — subsequent checks would crash.
    if missing_required:
        return {"errors": errors, "warnings": warnings, "info": info}

    # ── 2. Country column consistency ─────────────────────────────────────
    countries_found = df["country"].unique().tolist()
    if len(countries_found) != 1:
        errors.append(f"Panel must contain exactly one country, found: {countries_found}")
    elif countries_found[0] != country:
        errors.append(f"Panel country={countries_found[0]!r} does not match expected {country!r}")

    # ── 3. Year continuity ────────────────────────────────────────────────
    regions = df["region_id"].unique()
    info["n_regions"] = len(regions)
    info["year_min"]  = int(df["year"].min())
    info["year_max"]  = int(df["year"].max())
    info["n_years"]   = df["year"].nunique()

    if expected_years is not None:
        expected_set = set(expected_years)
        actual_set   = set(df["year"].unique())
        missing_years = sorted(expected_set - actual_set)
        extra_years   = sorted(actual_set - expected_set)
        if missing_years:
            errors.append(f"Missing years: {missing_years}")
        if extra_years:
            warnings.append(f"Extra years beyond expected range: {extra_years}")

    # Check each region has a continuous year sequence
    gaps = []
    for rid in regions:
        sub = df[df["region_id"] == rid]["year"].sort_values().values
        diffs = np.diff(sub)
        if (diffs != 1).any():
            bad = sub[:-1][diffs != 1].tolist()
            gaps.append(f"{rid}: gap after {bad}")
    if gaps:
        errors.append(f"Year gaps detected in {len(gaps)} regions: {gaps[:5]}{'…' if len(gaps) > 5 else ''}")

    # ── 4. node_idx consistency ───────────────────────────────────────────
    idx_map = df.groupby("region_id")["node_idx"].nunique()
    non_unique = idx_map[idx_map > 1]
    if not non_unique.empty:
        errors.append(f"region_id mapped to >1 node_idx: {non_unique.index.tolist()}")

    max_idx  = df["node_idx"].max()
    n_unique = df["node_idx"].nunique()
    if max_idx != n_unique - 1:
        errors.append(
            f"node_idx not contiguous 0..N-1: max={max_idx}, n_unique={n_unique}"
        )

    # ── 5. Temporal causal integrity (no lookahead) ───────────────────────
    # lag1_births at year t must equal target_births at year t-1
    if "lag1_births" in df.columns and "target_births" in df.columns:
        df_sorted = df.sort_values(["region_id", "year"])
        shifted = (
            df_sorted
            .set_index(["region_id", "year"])["target_births"]
            .groupby(level=0)
            .shift(1)
            .reset_index(name="expected_lag1")
        )
        merged = df_sorted.merge(shifted, on=["region_id", "year"], how="left")
        mask = merged["expected_lag1"].notna() & merged["lag1_births"].notna()
        if mask.any():
            discrepancy = (merged.loc[mask, "lag1_births"] - merged.loc[mask, "expected_lag1"]).abs()
            if (discrepancy > 1e-3).any():
                n_bad = (discrepancy > 1e-3).sum()
                errors.append(
                    f"lag1_births does not match lag of target_births in {n_bad} rows "
                    f"(max diff={discrepancy.max():.4f}). Possible lookahead contamination."
                )

    # growth_* must be derived from lagged values only.
    #
    # KNOWN BUG (Phase 4A/4D): legacy ingest_*.py scripts computed
    #   growth_1y[t] = (y[t] - y[t-1]) / y[t-1]
    # which leaks the target year into a feature. This inflated Phase 4A/4D
    # WMAPEs and invalidates them as scientific baselines.
    #
    # Phase 4E canonical contract (this check enforces it):
    #   growth_1y[t] = (y[t-1] - y[t-2]) / y[t-2]   ← lag1_births and lag2_births only
    #   growth_2y[t] = (y[t-1] - y[t-3]) / y[t-3]   ← lag1_births and lag3_births only
    #
    # Any panel failing these checks must NOT be used for training.
    # See reports/HERALD_PHASE4E_A2_DEGRADATION_AUDIT.md for full analysis.
    growth_required = {"growth_1y", "growth_2y", "lag1_births", "lag2_births", "lag3_births"}
    if growth_required.issubset(df.columns):
        safe_g1 = (df["lag1_births"] - df["lag2_births"]) / df["lag2_births"]
        safe_g2 = (df["lag1_births"] - df["lag3_births"]) / df["lag3_births"]
        leaky_g1 = (df["target_births"] - df["lag1_births"]) / df["lag1_births"]

        for col, expected in [("growth_1y", safe_g1), ("growth_2y", safe_g2)]:
            mask = expected.notna() & df[col].notna()
            if mask.any():
                diff = (df.loc[mask, col] - expected.loc[mask]).abs()
                if (diff > 1e-8).any():
                    errors.append(
                        f"CAUSAL INTEGRITY FAILURE: {col} is not derived from lagged births only "
                        f"({int((diff > 1e-8).sum())} rows affected, max diff={diff.max():.6g}). "
                        f"Expected: (lag1-lag2)/lag2 for growth_1y, (lag1-lag3)/lag3 for growth_2y. "
                        f"This panel cannot be used for training — matches legacy leaky formula."
                    )

        mask = leaky_g1.notna() & df["growth_1y"].notna()
        if mask.any():
            leaky_diff = (df.loc[mask, "growth_1y"] - leaky_g1.loc[mask]).abs()
            n_leaky = int((leaky_diff < 1e-10).sum())
            if n_leaky > 0:
                errors.append(
                    f"TARGET LEAKAGE DETECTED: growth_1y matches (target_births-lag1)/lag1 "
                    f"in {n_leaky} rows. This is the Phase 4A/4D bug — using current target y[t] "
                    f"as a feature. Panel must be rebuilt with enforce_causal_growth()."
                )

    # ── 6. mask_target coherence ──────────────────────────────────────────
    if "mask_target" in df.columns:
        mask_vals = df["mask_target"]
        if not mask_vals.isin([0.0, 1.0]).all():
            warnings.append("mask_target contains values other than 0 and 1.")
        unmasked_nan = (df["mask_target"] == 1) & df["target_births"].isna()
        if unmasked_nan.any():
            errors.append(
                f"{unmasked_nan.sum()} rows have mask_target=1 but target_births is NaN."
            )
        masked_observed = (df["mask_target"] == 0) & df["target_births"].notna()
        if masked_observed.any():
            warnings.append(
                f"{masked_observed.sum()} rows have mask_target=0 but target_births is not NaN "
                f"(will be excluded from loss)."
            )
        info["pct_target_observed"] = float(mask_vals.mean())

    # ── 7. flag_forecast_safe ─────────────────────────────────────────────
    if "flag_forecast_safe" in df.columns:
        n_safe   = int((df["flag_forecast_safe"] == 1).sum())
        n_unsafe = int((df["flag_forecast_safe"] == 0).sum())
        info["n_forecast_safe"]   = n_safe
        info["n_forecast_unsafe"] = n_unsafe
        if n_safe == 0:
            errors.append("No rows with flag_forecast_safe=1 — panel cannot be used for training.")

    # ── 8. NaN audit per field ────────────────────────────────────────────
    nan_report = {}
    for col in df.columns:
        n_nan = int(df[col].isna().sum())
        if n_nan > 0:
            nan_report[col] = {"n_nan": n_nan, "pct": round(n_nan / len(df) * 100, 1)}
    info["nan_report"] = nan_report

    # Errors if required field has NaNs in forecast-safe rows
    # NaN in warm-up rows (flag_forecast_safe=0) is expected and not an error.
    safe_mask = df["flag_forecast_safe"] == 1 if "flag_forecast_safe" in df.columns else pd.Series(True, index=df.index)
    df_safe = df[safe_mask]

    # growth_1y = log(t-1/t-2): NaN is valid when t-2 is the warm-up year.
    LAG_FIELDS_ALLOWED_NAN = {"lag2_births", "lag3_births", "growth_1y", "growth_2y", "target_births"}
    for col in REQUIRED_FIELDS:
        if col not in df.columns or col in LAG_FIELDS_ALLOWED_NAN:
            continue
        n = int(df_safe[col].isna().sum()) if col in df_safe.columns else 0
        if n > 0:
            errors.append(f"Required field {col!r} has {n} NaN values in forecast-safe rows.")

    if "target_births" in df.columns and df["target_births"].isna().any():
        n = int(df["target_births"].isna().sum())
        warnings.append(
            f"target_births has {n} NaNs — check mask_target for consistency."
        )

    # ── 9. EU signals coverage ────────────────────────────────────────────
    eu_present = [f for f in EU_SIGNAL_FIELDS if f in df.columns]
    if eu_present:
        info["eu_signals_coverage"] = {
            f: round(df[f].notna().mean() * 100, 1) for f in eu_present
        }
    else:
        warnings.append("No eu_* signals present. Panel uses local features only.")

    # ── 10. Sector coverage ───────────────────────────────────────────────
    sector_present = [f for f in SECTOR_FIELDS if f in df.columns]
    if sector_present:
        info["n_sector_fields"] = len(sector_present)
        any_sector_nan = df[sector_present].isna().any(axis=1)
        info["pct_sector_complete"] = round(float((~any_sector_nan).mean()) * 100, 1)
    else:
        warnings.append("No sector_* fields present (A10 breakdown unavailable).")

    # ── 11. flag_target_concept ───────────────────────────────────────────
    if "flag_target_concept" in df.columns:
        concepts = df["flag_target_concept"].unique().tolist()
        info["target_concepts"] = concepts
        if len(concepts) > 1:
            warnings.append(
                f"Multiple target concepts in single panel: {concepts}. "
                "Cross-year comparison may be inconsistent."
            )

    # ── 12. NON_PREDICTIVE_FIELDS guard ──────────────────────────────────
    # Detect if caller passed a feature list containing flagged columns.
    # If predictive_feature_cols is not supplied, emit a reminder warning.
    non_pred_present = [f for f in NON_PREDICTIVE_FIELDS if f in df.columns]
    if non_pred_present:
        warnings.append(
            f"NON_PREDICTIVE_FIELDS present in panel: {non_pred_present}. "
            "These columns MUST be excluded from x_ann, q_tensor, regime vector, "
            "and any model input. Use schema.NON_PREDICTIVE_FIELDS to filter before training."
        )

    # ── 13. Availability masks ────────────────────────────────────────────
    if "mask_employment" not in df.columns:
        warnings.append(
            "mask_employment absent. Cannot distinguish genuine employment tensor "
            "from births proxy or absent signal. Required before Phase 4E-C/D."
        )
    else:
        bad = ~df["mask_employment"].between(0.0, 1.0, inclusive="both")
        if bad.any():
            errors.append(f"mask_employment outside [0,1] in {int(bad.sum())} rows.")

    if "mask_tensor" not in df.columns:
        warnings.append(
            "mask_tensor absent. Tensor-dependent configs cannot distinguish genuine, "
            "proxy, and absent tensors."
        )
    else:
        bad = ~df["mask_tensor"].between(0.0, 1.0, inclusive="both")
        if bad.any():
            errors.append(f"mask_tensor outside [0,1] in {int(bad.sum())} rows.")

    if "mask_eu_signals" not in df.columns:
        warnings.append(
            "mask_eu_signals absent (derived from eu_* coverage). "
            "Will be auto-populated once eu_* fields are loaded."
        )
    else:
        bad = ~df["mask_eu_signals"].between(0.0, 1.0, inclusive="both")
        if bad.any():
            errors.append(f"mask_eu_signals outside [0,1] in {int(bad.sum())} rows.")
        # Phase 4E-C: EU signals should be attached by build_european_panel.py.
        # All-zero mask means the overlay did not run (offline + no cache) or was
        # skipped (--no-eu-signals). Non-blocking, but flagged for reproducibility.
        if float(df["mask_eu_signals"].max()) == 0.0:
            warnings.append(
                "mask_eu_signals is 0 for every row — EU common signals were not "
                "attached. Run eu_signals.fetch_all (online) or rebuild without "
                "--no-eu-signals. See HERALD_PHASE4E_MISSING_DATA_SEARCH.md."
            )

    # ── 14. Country-specific temporal warnings ────────────────────────────
    country_val = df["country"].dropna().unique()
    if len(country_val) == 1:
        c = str(country_val[0])
        yr_max = int(df["year"].max())

        if c == "BE" and yr_max < 2023:
            warnings.append(
                f"BE panel ends at {yr_max}. For Phase 4E cross-country comparisons "
                "with NL (2025) and PT (2022), BE should be extended to 2021–2024. "
                "Phase 4E-A sanity check can run on current range."
            )

        if c == "NL" and yr_max >= 2025:
            # CBS Q-tensor (83582NED) covers through 2024.
            # Under effectifs_lag1 policy (q_lag[t] = q[t-1]):
            #   NL 2025 uses employment[2024] → available → flag_has_national_employment=1 is correct.
            # Under 'real' policy (q[t] = employment[t]):
            #   NL 2025 would need employment[2025] → not available → configs with 'real'
            #   policy must either exclude 2025 or treat tensor as absent for that year.
            warnings.append(
                "NL panel includes 2025. CBS Q-tensor stops at 2024. "
                "Under effectifs_lag1 policy this is safe (uses employment[2024] for target 2025). "
                "Under 'real' tensor policy, 2025 has no tensor and must be excluded or masked."
            )

    return {"errors": errors, "warnings": warnings, "info": info}


def print_report(report: dict, verbose: bool = True) -> None:
    """Print a human-readable validation report."""
    country = report["info"].get("country", "?")
    errors   = report["errors"]
    warnings = report["warnings"]
    info     = report["info"]

    print(f"\n{'='*60}")
    print(f"  European Panel Validation — {country}")
    print(f"{'='*60}")
    print(f"  Regions : {info.get('n_regions', '?')}")
    print(f"  Years   : {info.get('year_min', '?')}–{info.get('year_max', '?')} "
          f"({info.get('n_years', '?')} years)")
    print(f"  Opt. coverage : {info.get('optional_coverage', 0)*100:.0f}%")
    if "pct_target_observed" in info:
        print(f"  Target observed: {info['pct_target_observed']*100:.1f}%")
    if "n_forecast_safe" in info:
        print(f"  Forecast-safe rows: {info['n_forecast_safe']} "
              f"(unsafe: {info['n_forecast_unsafe']})")

    if errors:
        print(f"\n  ✗ ERRORS ({len(errors)}) — panel NOT ready for training:")
        for e in errors:
            print(f"      ✗ {e}")
    else:
        print(f"\n  ✓ No errors.")

    if warnings:
        print(f"\n  ⚠  Warnings ({len(warnings)}):")
        for w in warnings:
            print(f"      ⚠  {w}")

    if verbose and info.get("nan_report"):
        print(f"\n  NaN audit:")
        for col, d in info["nan_report"].items():
            print(f"      {col:<40} {d['n_nan']:>6} NaN  ({d['pct']}%)")

    if verbose and info.get("eu_signals_coverage"):
        print(f"\n  EU signal coverage:")
        for sig, pct in info["eu_signals_coverage"].items():
            bar = "█" * int(pct // 10) + "░" * (10 - int(pct // 10))
            print(f"      {sig:<40} {bar} {pct:.0f}%")

    status = "BLOCKED" if errors else ("PASS with warnings" if warnings else "PASS")
    print(f"\n  Status: {status}")
    print(f"{'='*60}\n")
