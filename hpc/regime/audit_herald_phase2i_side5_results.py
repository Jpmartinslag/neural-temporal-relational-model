#!/usr/bin/env python3
"""Audit Phase 2I SIDE5 feature ablation results.

Usage:
    python3 hpc/regime/audit_herald_phase2i_side5_results.py \\
        --root hpc_results/herald_regime_phase2i_side5_20260518_1122_side5_audit_r1_r1 \\
        [--strict] [--min-runs N]

Outputs in <root>/reports/audit_phase2i_side5/:
    phase2i_integrity.json
    phase2i_summary_by_label.csv
    phase2i_paired_vs_side5_full.csv
    phase2i_feature_drop_impact.csv
    phase2i_seed_stability.csv
    phase2i_regulator_audit.csv
    PHASE2I_SIDE5_AUDIT.md

--strict  : exit 1 on any missing run, metadata or CSV.
--min-runs: minimum number of complete runs required (default 90 = 9 labels x 10 seeds).
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from scipy.stats import wilcoxon as _scipy_wilcoxon
    _HAS_SCIPY = True
except ImportError:
    _HAS_SCIPY = False


# ── constants ─────────────────────────────────────────────────────────────────

LABELS = [
    "side5_full",
    "drop_lag1",
    "drop_lag2",
    "drop_lag3",
    "drop_growth1y",
    "drop_growth2y",
    "lags_only",
    "growth_only",
    "lag1_growth1y",
]

SEEDS = [0, 1, 7, 13, 17, 42, 77, 99, 123, 2025]
EVAL_YEARS = [2021, 2022, 2023, 2024, 2025]
SIDE5_ALL = {"side_lag_1", "side_lag_2", "side_lag_3", "growth_1y", "growth_2y"}

EXPECTED_RUNS = len(LABELS) * len(SEEDS)   # 90

EXPECTED_SIDE5 = {
    "side5_full":    {"side_lag_1", "side_lag_2", "side_lag_3", "growth_1y", "growth_2y"},
    "drop_lag1":     {"side_lag_2", "side_lag_3", "growth_1y", "growth_2y"},
    "drop_lag2":     {"side_lag_1", "side_lag_3", "growth_1y", "growth_2y"},
    "drop_lag3":     {"side_lag_1", "side_lag_2", "growth_1y", "growth_2y"},
    "drop_growth1y": {"side_lag_1", "side_lag_2", "side_lag_3", "growth_2y"},
    "drop_growth2y": {"side_lag_1", "side_lag_2", "side_lag_3", "growth_1y"},
    "lags_only":     {"side_lag_1", "side_lag_2", "side_lag_3"},
    "growth_only":   {"growth_1y", "growth_2y"},
    "lag1_growth1y": {"side_lag_1", "growth_1y"},
}

TAG_PREFIX = "regime_no_regime_learned_regime_gate_sector_enhanced_no_source_flags"

# Phase 2H reference baseline
PHASE2H = {
    "mean_wmape": 0.025347,
    "wmape_2021": 0.036236,
    "wmape_2025": 0.014990,
    "sector_wmape_mean": 0.161675,
    "seed_std": 0.002189,
}

# Drop-experiment → readable description + what is being dropped
_DROP_EXPERIMENTS = [
    ("drop_lag1",     "remove side_lag_1",         {"side_lag_1"}),
    ("drop_lag2",     "remove side_lag_2",         {"side_lag_2"}),
    ("drop_lag3",     "remove side_lag_3",         {"side_lag_3"}),
    ("drop_growth1y", "remove growth_1y",          {"growth_1y"}),
    ("drop_growth2y", "remove growth_2y",          {"growth_2y"}),
    ("lags_only",     "only lags (drop growth)",   {"growth_1y", "growth_2y"}),
    ("growth_only",   "only growth (drop lags)",   {"side_lag_1", "side_lag_2", "side_lag_3"}),
    ("lag1_growth1y", "minimal lag1+growth1y",     {"side_lag_2", "side_lag_3", "growth_2y"}),
]


def _tag(label: str) -> str:
    return f"{TAG_PREFIX}_{label}"


# ── JSON parsing ──────────────────────────────────────────────────────────────

def _get_year(d: dict, year: int):
    """Fetch a year-keyed value from a dict that may use str or int keys."""
    v = d.get(str(year))
    if v is None:
        v = d.get(year)
    return v


def parse_run_json(path: Path) -> dict:
    raw = json.loads(path.read_text(encoding="utf-8"))
    result = next(iter(raw.values()))

    per_year = result.get("per_year_total") or {}
    alpha_by_year = result.get("alpha_by_year") or {}
    lsf = result.get("latent_step_by_fold") or {}

    # Average 2020→2021 latent step across all folds
    ls_vals = [
        float(steps["2020->2021"])
        for steps in lsf.values()
        if isinstance(steps, dict) and "2020->2021" in steps
    ]
    latent_step_2020_2021 = float(np.mean(ls_vals)) if ls_vals else None

    return {
        "seed": int(result.get("seed", -1)),
        "run_tag": str(result.get("run_tag", "")),
        "total_wmape_mean": result.get("total_wmape_mean"),
        "wmape_2021": _get_year(per_year, 2021),
        "wmape_2022": _get_year(per_year, 2022),
        "wmape_2023": _get_year(per_year, 2023),
        "wmape_2024": _get_year(per_year, 2024),
        "wmape_2025": _get_year(per_year, 2025),
        "sector_wmape_mean": result.get("sector_wmape_mean"),
        "alpha_2021": _get_year(alpha_by_year, 2021),
        "alpha_2025": _get_year(alpha_by_year, 2025),
        "gamma_geo": result.get("gamma_geo"),
        "gamma_mob": result.get("gamma_mob"),
        "latent_step_2020_2021": latent_step_2020_2021,
        "has_latent_step": bool(lsf),
    }


def parse_metadata_json(path: Path) -> dict:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {
        "experiment_label": raw.get("experiment_label", ""),
        "feature_policy": raw.get("feature_policy", ""),
        "manual_flags_in_annual_features": bool(raw.get("manual_flags_in_annual_features", True)),
        "manual_flags_in_regime_vector": bool(raw.get("manual_flags_in_regime_vector", True)),
        "source_flags_in_annual_features": bool(raw.get("source_flags_in_annual_features", True)),
        "macro_feature_set": str(raw.get("macro_feature_set", "")),
        "annual_features": sorted(raw.get("annual_features") or []),
        "annual_feature_count": int(raw.get("annual_feature_count", -1)),
        "dropped_side5_features": sorted(raw.get("dropped_side5_features") or []),
        "ridge_features": sorted(raw.get("ridge_features") or []),
        "ridge_dropped_side5_features": sorted(raw.get("ridge_dropped_side5_features") or []),
    }


# ── integrity check ───────────────────────────────────────────────────────────

def integrity_check(root: Path, strict: bool, min_runs: int) -> dict:
    per_run_dir = root / "reports" / "per_run"
    data_dir    = root / "data_processed"
    meta_dir    = root / "metadata"

    errors   = []
    warnings = []

    if not root.exists():
        msg = f"OUT_ROOT does not exist: {root}"
        if strict:
            print(f"ERROR: {msg}", file=sys.stderr)
            sys.exit(1)
        return {
            "ok": False, "errors": [msg], "warnings": [],
            "found_runs": 0, "expected_runs": min_runs,
            "found_json": 0, "found_meta": 0,
            "found_total_csv": 0, "found_sector_csv": 0, "found_npz": 0,
        }

    all_json      = list(per_run_dir.glob("*.json")) if per_run_dir.exists() else []
    all_meta      = list(meta_dir.glob("*.json"))    if meta_dir.exists()    else []
    all_total_csv = list(data_dir.glob("*predictions_total*.csv"))  if data_dir.exists() else []
    all_sector_csv= list(data_dir.glob("*predictions_sector*.csv")) if data_dir.exists() else []
    all_npz       = list(data_dir.glob("*internals*.npz"))          if data_dir.exists() else []

    found_runs = 0
    csv_errors = []

    for label in LABELS:
        tag = _tag(label)
        expected_set = EXPECTED_SIDE5[label]
        seeds_found = 0

        for seed in SEEDS:
            fname       = f"{tag}_seed_{seed}.json"
            json_path   = per_run_dir / fname
            meta_path   = meta_dir / fname
            csv_total   = data_dir / f"herald_semi_v2_predictions_total_full_{tag}_seed_{seed}_v1.csv"
            csv_sector  = data_dir / f"herald_semi_v2_predictions_sector_full_{tag}_seed_{seed}_v1.csv"

            if not json_path.exists():
                errors.append(f"Missing per-run JSON: {label}/seed={seed}")
                continue
            if not meta_path.exists():
                errors.append(f"Missing metadata: {label}/seed={seed}")
                continue

            seeds_found += 1
            found_runs  += 1

            if not csv_total.exists():
                csv_errors.append(f"Missing CSV total: {label}/seed={seed}")
            if not csv_sector.exists():
                csv_errors.append(f"Missing CSV sector: {label}/seed={seed}")

            try:
                meta = parse_metadata_json(meta_path)
            except Exception as exc:
                errors.append(f"Cannot parse metadata {label}/seed={seed}: {exc}")
                continue

            if meta["manual_flags_in_annual_features"]:
                errors.append(f"manual_flags_in_annual_features=True: {label}/seed={seed}")
            if meta["manual_flags_in_regime_vector"]:
                errors.append(f"manual_flags_in_regime_vector=True: {label}/seed={seed}")
            if meta["source_flags_in_annual_features"]:
                errors.append(f"source_flags_in_annual_features=True: {label}/seed={seed}")
            if meta["macro_feature_set"] != "none":
                errors.append(f"macro_feature_set={meta['macro_feature_set']!r}: {label}/seed={seed}")

            actual_side5 = set(meta["annual_features"]) & SIDE5_ALL
            if actual_side5 != expected_set:
                errors.append(
                    f"annual_features SIDE5 mismatch {label}/seed={seed}: "
                    f"expected={sorted(expected_set)} got={sorted(actual_side5)}"
                )
            if not meta["ridge_features"]:
                errors.append(f"ridge_features missing/empty: {label}/seed={seed}")
            else:
                ridge_side5 = set(meta["ridge_features"]) & SIDE5_ALL
                if ridge_side5 != expected_set:
                    errors.append(
                        f"ridge_features SIDE5 mismatch {label}/seed={seed}: "
                        f"expected={sorted(expected_set)} got={sorted(ridge_side5)}"
                    )

        if seeds_found != len(SEEDS):
            warnings.append(f"{label}: found {seeds_found}/{len(SEEDS)} seeds")

    # Check for unexpected labels
    found_labels = set()
    for p in all_json:
        # filename: {tag}_seed_{seed}.json
        name = p.stem  # strip .json
        if "_seed_" in name:
            lbl_part = name.rsplit("_seed_", 1)[0].replace(TAG_PREFIX + "_", "", 1)
            found_labels.add(lbl_part)
    unexpected = found_labels - set(LABELS)
    if unexpected:
        errors.append(f"Unexpected labels found in results: {sorted(unexpected)}")

    # Cap CSV errors
    if len(csv_errors) > 20:
        errors.extend(csv_errors[:20])
        errors.append(f"... {len(csv_errors) - 20} more CSV errors omitted")
    else:
        errors.extend(csv_errors)

    warnings.append(f"NPZ internals count: {len(all_npz)} (not required for audit)")

    ok = (len(errors) == 0) and (found_runs >= min_runs)

    result = {
        "ok": ok,
        "expected_runs": min_runs,
        "found_runs": found_runs,
        "found_json": len(all_json),
        "found_meta": len(all_meta),
        "found_total_csv": len(all_total_csv),
        "found_sector_csv": len(all_sector_csv),
        "found_npz": len(all_npz),
        "errors": errors,
        "warnings": warnings,
    }

    if strict and not ok:
        print(f"ERROR: integrity check failed — {len(errors)} errors, {found_runs}/{min_runs} runs found.", file=sys.stderr)
        for e in errors[:30]:
            print(f"  {e}", file=sys.stderr)
        if len(errors) > 30:
            print(f"  ... {len(errors) - 30} more", file=sys.stderr)
        sys.exit(1)

    return result


# ── data loading ──────────────────────────────────────────────────────────────

def load_all_runs(root: Path) -> pd.DataFrame:
    per_run_dir = root / "reports" / "per_run"
    meta_dir    = root / "metadata"
    rows = []

    for label in LABELS:
        tag = _tag(label)
        for seed in SEEDS:
            fname     = f"{tag}_seed_{seed}.json"
            json_path = per_run_dir / fname
            meta_path = meta_dir / fname

            if not json_path.exists():
                continue

            try:
                run  = parse_run_json(json_path)
            except Exception as exc:
                print(f"Warning: cannot parse {fname}: {exc}", file=sys.stderr)
                continue

            meta = {}
            if meta_path.exists():
                try:
                    meta = parse_metadata_json(meta_path)
                except Exception as exc:
                    print(f"Warning: cannot parse metadata {fname}: {exc}", file=sys.stderr)

            rows.append({
                "label":                   label,
                "seed":                    run["seed"],
                "feature_policy":          meta.get("feature_policy", ""),
                "manual_flags_in_regime_vector": meta.get("manual_flags_in_regime_vector", None),
                "annual_feature_count":    meta.get("annual_feature_count", -1),
                "annual_features":         json.dumps(meta.get("annual_features", [])),
                "ridge_features":          json.dumps(meta.get("ridge_features", [])),
                "dropped_side5_features":  json.dumps(meta.get("dropped_side5_features", [])),
                "ridge_dropped_side5_features": json.dumps(meta.get("ridge_dropped_side5_features", [])),
                "total_wmape_mean":        run["total_wmape_mean"],
                "wmape_2021":              run["wmape_2021"],
                "wmape_2022":              run["wmape_2022"],
                "wmape_2023":              run["wmape_2023"],
                "wmape_2024":              run["wmape_2024"],
                "wmape_2025":              run["wmape_2025"],
                "sector_wmape_mean":       run["sector_wmape_mean"],
                "alpha_2021":              run["alpha_2021"],
                "alpha_2025":              run["alpha_2025"],
                "gamma_geo":               run["gamma_geo"],
                "gamma_mob":               run["gamma_mob"],
                "latent_step_2020_2021":   run["latent_step_2020_2021"],
                "has_latent_step":         run["has_latent_step"],
            })

    return pd.DataFrame(rows) if rows else pd.DataFrame()


# ── analysis ──────────────────────────────────────────────────────────────────

def compute_summary(df: pd.DataFrame) -> pd.DataFrame:
    agg = (
        df.groupby("label")
        .agg(
            n=("seed", "count"),
            mean_wmape_mean=("total_wmape_mean", "mean"),
            std_wmape_mean=("total_wmape_mean", "std"),
            wmape_2021_mean=("wmape_2021", "mean"),
            wmape_2022_mean=("wmape_2022", "mean"),
            wmape_2023_mean=("wmape_2023", "mean"),
            wmape_2024_mean=("wmape_2024", "mean"),
            wmape_2025_mean=("wmape_2025", "mean"),
            sector_wmape_mean=("sector_wmape_mean", "mean"),
            sector_wmape_std=("sector_wmape_mean", "std"),
            alpha_2021_mean=("alpha_2021", "mean"),
            alpha_2025_mean=("alpha_2025", "mean"),
            gamma_geo_mean=("gamma_geo", "mean"),
            gamma_mob_mean=("gamma_mob", "mean"),
            annual_feature_count=("annual_feature_count", "first"),
        )
        .reset_index()
    )
    order = {l: i for i, l in enumerate(LABELS)}
    agg["_ord"] = agg["label"].map(order)
    return agg.sort_values("_ord").drop(columns="_ord").reset_index(drop=True)


def _wilcoxon_p(a: np.ndarray, b: np.ndarray) -> float:
    if not _HAS_SCIPY:
        return float("nan")
    diffs = a - b
    if np.all(diffs == 0):
        return 1.0
    try:
        _, p = _scipy_wilcoxon(diffs, alternative="two-sided")
        return float(p)
    except Exception:
        return float("nan")


def compute_paired_vs_reference(df: pd.DataFrame, ref: str = "side5_full") -> pd.DataFrame:
    if ref not in df["label"].values:
        return pd.DataFrame()

    ref_df  = df[df["label"] == ref].set_index("seed")
    rows    = []

    for label in LABELS:
        if label == ref:
            continue
        cmp_df = df[df["label"] == label].set_index("seed")
        seeds  = ref_df.index.intersection(cmp_df.index)
        if len(seeds) == 0:
            continue

        ref_mean   = ref_df.loc[seeds, "total_wmape_mean"].values.astype(float)
        cmp_mean   = cmp_df.loc[seeds, "total_wmape_mean"].values.astype(float)
        ref_2021   = ref_df.loc[seeds, "wmape_2021"].values.astype(float)
        cmp_2021   = cmp_df.loc[seeds, "wmape_2021"].values.astype(float)
        ref_2025   = ref_df.loc[seeds, "wmape_2025"].values.astype(float)
        cmp_2025   = cmp_df.loc[seeds, "wmape_2025"].values.astype(float)
        ref_a10    = ref_df.loc[seeds, "sector_wmape_mean"].values.astype(float)
        cmp_a10    = cmp_df.loc[seeds, "sector_wmape_mean"].values.astype(float)

        # wins = label beats ref (lower WMAPE)
        wins_mean  = int(np.sum(cmp_mean < ref_mean))
        losses_mean= int(np.sum(cmp_mean > ref_mean))
        ties_mean  = int(np.sum(cmp_mean == ref_mean))

        rows.append({
            "label":               label,
            "n_seeds":             len(seeds),
            "delta_mean_wmape":    float(np.mean(cmp_mean - ref_mean)),
            "delta_wmape_2021":    float(np.mean(cmp_2021 - ref_2021)),
            "delta_wmape_2025":    float(np.mean(cmp_2025 - ref_2025)),
            "delta_sector_wmape":  float(np.mean(cmp_a10  - ref_a10)),
            "wins_mean":           wins_mean,
            "losses_mean":         losses_mean,
            "ties_mean":           ties_mean,
            "p_mean":              _wilcoxon_p(cmp_mean, ref_mean),
            "p_2021":              _wilcoxon_p(cmp_2021, ref_2021),
            "p_2025":              _wilcoxon_p(cmp_2025, ref_2025),
        })

    return pd.DataFrame(rows)


def _interpret(delta_mean: float, wins: int, n: int) -> str:
    """Classify feature importance from ablation result.

    delta_mean > 0 means removal degraded (label is worse than side5_full).
    wins = seeds where label beat side5_full.
    losses = n - wins = seeds where label lost to side5_full.
    """
    losses = n - wins
    if delta_mean > 0 and losses >= 7:
        return "essential"
    if delta_mean < 0 and wins >= 6:
        return "redundant_or_noise"
    return "mixed"


def compute_feature_drop_impact(paired: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for label, description, _ in _DROP_EXPERIMENTS:
        r = paired[paired["label"] == label]
        if r.empty:
            continue
        r = r.iloc[0]
        n = int(r["n_seeds"])
        wins = int(r["wins_mean"])
        rows.append({
            "experiment":          description,
            "label":               label,
            "delta_mean_wmape":    r["delta_mean_wmape"],
            "delta_wmape_2021":    r["delta_wmape_2021"],
            "delta_wmape_2025":    r["delta_wmape_2025"],
            "delta_sector_wmape":  r["delta_sector_wmape"],
            "wins_vs_side5_full":  wins,
            "n_seeds":             n,
            "interpretation":      _interpret(float(r["delta_mean_wmape"]), wins, n),
        })
    return pd.DataFrame(rows)


def compute_seed_stability(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for label in LABELS:
        sub = df[df["label"] == label]
        if sub.empty:
            continue
        wmape   = sub["total_wmape_mean"].astype(float)
        w2021   = sub["wmape_2021"].astype(float)
        best_i  = int(sub.loc[wmape.idxmin(), "seed"])
        worst_i = int(sub.loc[wmape.idxmax(), "seed"])
        rows.append({
            "label":           label,
            "n":               len(sub),
            "mean_wmape_mean": float(wmape.mean()),
            "std_wmape_mean":  float(wmape.std()),
            "min_wmape_mean":  float(wmape.min()),
            "max_wmape_mean":  float(wmape.max()),
            "best_seed":       best_i,
            "worst_seed":      worst_i,
            "wmape_2021_mean": float(w2021.mean()),
            "wmape_2021_std":  float(w2021.std()),
            "wmape_2021_min":  float(w2021.min()),
            "wmape_2021_max":  float(w2021.max()),
        })
    return pd.DataFrame(rows)


def compute_regulator_audit(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for label in LABELS:
        sub = df[df["label"] == label]
        if sub.empty:
            continue
        ggeo = sub["gamma_geo"].astype(float).dropna()
        gmob = sub["gamma_mob"].astype(float).dropna()
        ls   = sub["latent_step_2020_2021"].astype(float).dropna()
        geo_mean = float(ggeo.mean()) if len(ggeo) else float("nan")
        mob_mean = float(gmob.mean()) if len(gmob) else float("nan")
        ratio    = mob_mean / geo_mean if geo_mean != 0 else float("nan")
        rows.append({
            "label":                        label,
            "alpha_2021_mean":              float(sub["alpha_2021"].astype(float).mean()),
            "alpha_2021_std":               float(sub["alpha_2021"].astype(float).std()),
            "alpha_2025_mean":              float(sub["alpha_2025"].astype(float).mean()),
            "alpha_2025_std":               float(sub["alpha_2025"].astype(float).std()),
            "gamma_geo_mean":               geo_mean,
            "gamma_mob_mean":               mob_mean,
            "gamma_ratio_mob_geo":          ratio,
            "latent_step_2020_2021_mean":   float(ls.mean()) if len(ls) > 0 else float("nan"),
            "latent_step_2020_2021_std":    float(ls.std())  if len(ls) > 1 else float("nan"),
        })
    return pd.DataFrame(rows)


# ── markdown helpers ──────────────────────────────────────────────────────────

def _f(v, fmt=".6f") -> str:
    """Format float or return NA."""
    if v is None:
        return "NA"
    try:
        if np.isnan(float(v)):
            return "NA"
        return format(float(v), fmt)
    except (TypeError, ValueError):
        return str(v)


def _d(v) -> str:
    """Format a delta value with sign."""
    if v is None:
        return "NA"
    try:
        x = float(v)
        if np.isnan(x):
            return "NA"
        return f"{'+' if x >= 0 else ''}{x:.6f}"
    except (TypeError, ValueError):
        return str(v)


def _p(v) -> str:
    """Format p-value."""
    if v is None:
        return "NA"
    try:
        x = float(v)
        if np.isnan(x):
            return "NA"
        return f"{x:.4f}"
    except (TypeError, ValueError):
        return str(v)


# ── markdown report ───────────────────────────────────────────────────────────

def write_markdown(
    root: Path,
    integrity: dict,
    summary: pd.DataFrame,
    paired: pd.DataFrame,
    impact: pd.DataFrame,
    stability: pd.DataFrame,
    regulator: pd.DataFrame,
    df_all: pd.DataFrame,
) -> str:
    L = []
    a = L.append

    a("# HERALD Phase 2I — SIDE5 Feature Audit")
    a("")
    a(f"OUT_ROOT: `{root}`")
    a("")
    a("## 1. Resumo executivo")
    a("")
    a("Phase 2I audita a contribuição de cada uma das 5 features SIDE do candidato `best_simplified`")
    a("(Phase 2H), removendo uma por vez e testando combinações mínimas.")
    a("")
    a(f"- 9 variantes × {len(SEEDS)} seeds = {EXPECTED_RUNS} runs esperadas.")
    a(f"- Referência Phase 2H `best_simplified`:")
    a(f"  - Mean WMAPE: {PHASE2H['mean_wmape']:.6f}")
    a(f"  - WMAPE 2021: {PHASE2H['wmape_2021']:.6f}")
    a(f"  - WMAPE 2025: {PHASE2H['wmape_2025']:.6f}")
    a(f"  - A10 WMAPE: {PHASE2H['sector_wmape_mean']:.6f}")
    a(f"  - Seed std: {PHASE2H['seed_std']:.6f}")
    a("")
    a("## 2. Integridade da bateria")
    a("")
    a(f"| Artefato | Encontrado | Esperado |")
    a(f"|---|---:|---:|")
    a(f"| runs completas (JSON+metadata) | {integrity['found_runs']} | {integrity['expected_runs']} |")
    a(f"| JSON per-run | {integrity['found_json']} | {integrity['expected_runs']} |")
    a(f"| metadata | {integrity['found_meta']} | {integrity['expected_runs']} |")
    a(f"| CSV predictions_total | {integrity['found_total_csv']} | {integrity['expected_runs']} |")
    a(f"| CSV predictions_sector | {integrity['found_sector_csv']} | {integrity['expected_runs']} |")
    a(f"| NPZ internals | {integrity['found_npz']} | informacional |")
    a("")
    a(f"Integridade OK: `{integrity['ok']}`")
    if integrity["errors"]:
        a("")
        a(f"Erros ({len(integrity['errors'])}):")
        for e in integrity["errors"][:30]:
            a(f"  - {e}")
        if len(integrity["errors"]) > 30:
            a(f"  - ... {len(integrity['errors']) - 30} mais omitidos")
    if integrity["warnings"]:
        a("")
        a("Avisos:")
        for w in integrity["warnings"]:
            a(f"  - {w}")
    a("")
    a("## 3. Tabela principal por label")
    a("")

    if not summary.empty:
        a("| label | n | mean WMAPE | std | WMAPE 2021 | WMAPE 2022 | WMAPE 2023 | WMAPE 2024 | WMAPE 2025 | A10 WMAPE | feat_n |")
        a("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
        for _, row in summary.iterrows():
            a(
                f"| {row['label']} | {int(row['n'])} "
                f"| {_f(row['mean_wmape_mean'])} | {_f(row['std_wmape_mean'])} "
                f"| {_f(row['wmape_2021_mean'])} | {_f(row['wmape_2022_mean'])} "
                f"| {_f(row['wmape_2023_mean'])} | {_f(row['wmape_2024_mean'])} "
                f"| {_f(row['wmape_2025_mean'])} | {_f(row['sector_wmape_mean'])} "
                f"| {int(row['annual_feature_count'])} |"
            )
        a("")
        a(
            f"Referência Phase 2H `best_simplified` (10 seeds): "
            f"mean={PHASE2H['mean_wmape']:.6f}, "
            f"2021={PHASE2H['wmape_2021']:.6f}, "
            f"2025={PHASE2H['wmape_2025']:.6f}, "
            f"A10={PHASE2H['sector_wmape_mean']:.6f}, "
            f"std={PHASE2H['seed_std']:.6f}"
        )
    a("")
    a("## 4. Comparação pareada vs side5_full")
    a("")

    if not paired.empty:
        a("Positivo = label pior que side5_full. Negativo = label melhor.")
        a("")
        a("| label | delta mean | delta 2021 | delta 2025 | delta A10 | wins/losses/ties | p_mean | p_2021 | p_2025 |")
        a("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
        for _, row in paired.iterrows():
            wlt = f"{int(row['wins_mean'])}/{int(row['losses_mean'])}/{int(row['ties_mean'])}"
            a(
                f"| {row['label']} "
                f"| {_d(row['delta_mean_wmape'])} | {_d(row['delta_wmape_2021'])} "
                f"| {_d(row['delta_wmape_2025'])} | {_d(row['delta_sector_wmape'])} "
                f"| {wlt} | {_p(row['p_mean'])} | {_p(row['p_2021'])} | {_p(row['p_2025'])} |"
            )
        a("")
        a("wins/losses/ties: vezes que label venceu/perdeu/empatou com side5_full (menor WMAPE = vencer).")
        if not _HAS_SCIPY:
            a("")
            a("**Nota:** scipy não disponível — p-values reportados como NA. Instale scipy para p-values.")
    a("")
    a("## 5. Importância das 5 features")
    a("")

    if not impact.empty:
        a("| experimento | delta mean | delta 2021 | delta 2025 | delta A10 | wins/n | interpretação |")
        a("|---|---:|---:|---:|---:|---:|---|")
        for _, row in impact.iterrows():
            wn = f"{int(row['wins_vs_side5_full'])}/{int(row['n_seeds'])}"
            a(
                f"| {row['experiment']} "
                f"| {_d(row['delta_mean_wmape'])} | {_d(row['delta_wmape_2021'])} "
                f"| {_d(row['delta_wmape_2025'])} | {_d(row['delta_sector_wmape'])} "
                f"| {wn} | {row['interpretation']} |"
            )
        a("")
        a("Critério de interpretação automática:")
        a("- `essential`: remoção piora mean WMAPE E label perde >= 7/10 seeds.")
        a("- `redundant_or_noise`: remoção melhora mean WMAPE E label ganha >= 6/10 seeds.")
        a("- `mixed`: todos os outros casos.")
    a("")
    a("## 6. Estabilidade por seed")
    a("")

    if not stability.empty:
        a("| label | n | mean | std | min | max | best_seed | worst_seed | 2021_mean | 2021_std |")
        a("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
        for _, row in stability.iterrows():
            a(
                f"| {row['label']} | {int(row['n'])} "
                f"| {_f(row['mean_wmape_mean'])} | {_f(row['std_wmape_mean'])} "
                f"| {_f(row['min_wmape_mean'])} | {_f(row['max_wmape_mean'])} "
                f"| {int(row['best_seed'])} | {int(row['worst_seed'])} "
                f"| {_f(row['wmape_2021_mean'])} | {_f(row['wmape_2021_std'])} |"
            )
        a("")
        a(f"Referência Phase 2H std entre seeds: {PHASE2H['seed_std']:.6f}")
    a("")
    a("## 7. Reguladores internos (alpha, gamma, latente)")
    a("")

    if not regulator.empty:
        has_latent = bool(df_all["latent_step_2020_2021"].notna().any()) if not df_all.empty else False
        header = "| label | alpha_2021 | α±std | alpha_2025 | α±std | gamma_geo | gamma_mob | mob/geo |"
        sep    = "|---|---:|---:|---:|---:|---:|---:|---:|"
        if has_latent:
            header += " latent 2020→2021 | ±std |"
            sep    += "---:|---:|"
        a(header)
        a(sep)
        for _, row in regulator.iterrows():
            line = (
                f"| {row['label']} "
                f"| {_f(row['alpha_2021_mean'])} | ±{_f(row['alpha_2021_std'])} "
                f"| {_f(row['alpha_2025_mean'])} | ±{_f(row['alpha_2025_std'])} "
                f"| {_f(row['gamma_geo_mean'])} | {_f(row['gamma_mob_mean'])} "
                f"| {_f(row['gamma_ratio_mob_geo'], '.3f')} |"
            )
            if has_latent:
                line += f" {_f(row['latent_step_2020_2021_mean'])} | ±{_f(row['latent_step_2020_2021_std'])} |"
            a(line)
        a("")
        a("Leitura:")
        a("- `alpha_2021` elevado vs outros anos → modelo mudou arbitragem local/grafo em 2021.")
        a("- `gamma_mob >> gamma_geo` → grafo de mobilidade domina o prior geográfico.")
        a("- Latente 2020→2021 grande → estado latente detectou o choque de COVID.")
        a("- Se alpha ou latente muda entre variantes, a feature removida influenciava o mecanismo interno.")
    a("")
    a("## 8. Veredito")
    a("")
    a("### 8.1 Veredito automático preliminar")
    a("")

    if not impact.empty:
        essential  = impact[impact["interpretation"] == "essential"]["experiment"].tolist()
        redundant  = impact[impact["interpretation"] == "redundant_or_noise"]["experiment"].tolist()
        mixed_list = impact[impact["interpretation"] == "mixed"]["experiment"].tolist()
        if essential:
            a(f"Features **essenciais** (remoção degrada >= 7/10 seeds): {', '.join(essential)}")
        else:
            a("Nenhuma feature marcada automaticamente como essencial (limiar 7/10 seeds).")
        if redundant:
            a(f"")
            a(f"Features potencialmente **redundantes** (remoção melhora >= 6/10 seeds): {', '.join(redundant)}")
        if mixed_list:
            a(f"")
            a(f"Resultado **mixed** (sem conclusão automática): {', '.join(mixed_list)}")
        a("")
        a("**Verificar manualmente** antes de aceitar qualquer veredito — os limiares acima são orientativos.")
    a("")
    a("### 8.2 Questões a responder")
    a("")
    a("1. `side5_full` permanece melhor que todas as variantes reduzidas na média e em 2021?")
    a("2. Alguma feature é redundante — sua remoção não degrada, possivelmente melhora?")
    a("3. `lag1_growth1y` (2 features) é suficiente — mantém WMAPE médio a < 1 std do `side5_full`?")
    a("4. `growth_only` (sem lags) é inviável — perde claramente em 2021 e na média?")
    a("5. O modelo depende mais de nível (`side_lag_1`) ou de tendência (`growth_1y`/`growth_2y`)?")
    a("")
    a("## 9. Limites metodológicos")
    a("")
    a("- Painel, splits e hiperparâmetros idênticos entre variantes — ablação isola a feature, não interações com arquitetura.")
    a("- 10 seeds por variante: potência estatística limitada para diferenças pequenas (< 0.001 WMAPE).")
    a("- Comparações pareadas assumem que as seeds são a única fonte de variação entre variantes.")
    a("- `drop_*` remove a feature de **ambos** o branch neural e o Ridge AR — ablação limpa.")
    a("- `growth_only` e `lag1_growth1y` têm poucas features; risco de colapso ou representação degenerada.")
    a("- Nenhuma permutação de tendências nesta fase; a falsificação de `growth_1y`/`growth_2y` é prevista para fase futura.")
    a("")
    a("## 10. Próximos passos")
    a("")
    a("- Se `side5_full` dominar em todas as métricas: confirmar `best_simplified` e prosseguir para audit de reguladores.")
    a("- Se feature redundante confirmada: bateria de confirmação com 20 seeds antes de simplificar.")
    a("- Se `lag1_growth1y` competitivo: testar estabilidade com 20 seeds antes de simplificar.")
    a("- Independente desta fase: audit de permutação de tendências conforme plano SIDE5 (Phase 2J).")

    return "\n".join(L) + "\n"


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Audit Phase 2I SIDE5 feature ablation results.")
    parser.add_argument("--root",     type=Path, required=True, help="Phase 2I OUT_ROOT")
    parser.add_argument("--strict",   action="store_true",      help="Exit 1 on any integrity error")
    parser.add_argument("--min-runs", type=int, default=EXPECTED_RUNS,
                        help=f"Minimum complete runs required (default {EXPECTED_RUNS})")
    args = parser.parse_args()

    # ── integrity ──
    print(f"Auditing: {args.root}")
    integrity = integrity_check(args.root, args.strict, args.min_runs)

    if not args.root.exists():
        print(f"ERROR: OUT_ROOT does not exist: {args.root}", file=sys.stderr)
        sys.exit(1)

    audit_dir = args.root / "reports" / "audit_phase2i_side5"
    audit_dir.mkdir(parents=True, exist_ok=True)

    (audit_dir / "phase2i_integrity.json").write_text(
        json.dumps(integrity, indent=2), encoding="utf-8"
    )
    n_err = len(integrity["errors"])
    print(
        f"Integrity: found={integrity['found_runs']}/{integrity['expected_runs']} runs, "
        f"ok={integrity['ok']}, errors={n_err}"
    )
    for e in integrity["errors"][:5]:
        print(f"  {e}", file=sys.stderr)

    # ── load ──
    print("Loading run data...")
    df = load_all_runs(args.root)

    if df.empty:
        print("No runs loaded — cannot produce analysis tables.", file=sys.stderr)
        md = write_markdown(args.root, integrity, pd.DataFrame(), pd.DataFrame(),
                            pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame())
        (audit_dir / "PHASE2I_SIDE5_AUDIT.md").write_text(md, encoding="utf-8")
        print(f"Partial report written: {audit_dir / 'PHASE2I_SIDE5_AUDIT.md'}")
        if args.strict:
            sys.exit(1)
        return

    print(f"Loaded {len(df)} runs, {df['label'].nunique()} labels.")

    # ── compute ──
    summary   = compute_summary(df)
    paired    = compute_paired_vs_reference(df, "side5_full")
    impact    = compute_feature_drop_impact(paired)
    stability = compute_seed_stability(df)
    regulator = compute_regulator_audit(df)

    # ── write CSVs ──
    summary.to_csv(  audit_dir / "phase2i_summary_by_label.csv",      index=False)
    paired.to_csv(   audit_dir / "phase2i_paired_vs_side5_full.csv",   index=False)
    impact.to_csv(   audit_dir / "phase2i_feature_drop_impact.csv",    index=False)
    stability.to_csv(audit_dir / "phase2i_seed_stability.csv",         index=False)
    regulator.to_csv(audit_dir / "phase2i_regulator_audit.csv",        index=False)

    # ── write markdown ──
    md = write_markdown(args.root, integrity, summary, paired, impact, stability, regulator, df)
    (audit_dir / "PHASE2I_SIDE5_AUDIT.md").write_text(md, encoding="utf-8")

    # ── stdout summary ──
    print("\n--- Summary by label ---")
    cols = ["label", "n", "mean_wmape_mean", "std_wmape_mean", "wmape_2021_mean", "wmape_2025_mean", "sector_wmape_mean"]
    print(summary[[c for c in cols if c in summary.columns]].to_string(index=False))

    if not paired.empty:
        print("\n--- Paired vs side5_full ---")
        print(paired[["label", "delta_mean_wmape", "wins_mean", "losses_mean", "p_mean"]].to_string(index=False))

    if not impact.empty:
        print("\n--- Feature drop impact ---")
        print(impact[["experiment", "delta_mean_wmape", "wins_vs_side5_full", "interpretation"]].to_string(index=False))

    print(f"\nAudit output: {audit_dir}")
    for f in sorted(audit_dir.iterdir()):
        print(f"  {f.name}")


if __name__ == "__main__":
    main()
