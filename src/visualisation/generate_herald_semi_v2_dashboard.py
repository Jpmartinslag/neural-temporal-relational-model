#!/usr/bin/env python3
"""Generate the HERALD France scientific dashboard.

The dashboard is intentionally data-first:
- metrics are read from the current run JSON files;
- HERALD zone and A10 real-vs-predicted values are read from prediction CSVs;
- the old geo2025 dashboard is used only as a geometry/source fallback for the
  France map, control-model zone maps, and graph coordinates when those files are not
  present in the current run directory.
"""

from __future__ import annotations

import argparse
import glob
import json
import math
import os
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


BASE = Path("/home/jpdark/Downloads/project_recomm/dataset")


def _find_latest_run(base: Path) -> Path:
    candidates = sorted(glob.glob(str(base / "hpc_results/herald_strict_exante_*")))
    if candidates:
        return Path(candidates[-1])
    return base / "hpc_results/herald_strict_exante_20260506_strict_exante"


DEFAULT_RUN_ROOT = _find_latest_run(BASE)
DEFAULT_PHASE2I_RUN_ROOT = (
    BASE / "hpc_results/herald_regime_phase2i_side5_20260518_1122_side5_audit_r1_r1"
)
DEFAULT_FLAGS_RUN_ROOT = (
    BASE / "hpc_results/herald_regime_phase2e_residual_rebound_20260513_143746_r1"
)


def _find_latest_phase2j(base: Path) -> Path | None:
    candidates = sorted(glob.glob(str(base / "hpc_results/herald_regime_phase2j_fair_flag_*")))
    return Path(candidates[-1]) if candidates else None

DEFAULT_PHASE2J_RUN_ROOT = _find_latest_phase2j(BASE)


def _find_latest_phase2r(base: Path) -> Path | None:
    candidates = sorted(glob.glob(str(base / "hpc_results/herald_regime_phase2r_*")))
    return Path(candidates[-1]) if candidates else None

DEFAULT_PHASE2R_RUN_ROOT = _find_latest_phase2r(BASE)


def _find_latest_phase3e(base: Path) -> Path | None:
    candidates = sorted(glob.glob(str(base / "hpc_results/herald_regime_phase3e_qtensor_arch_*")))
    return Path(candidates[-1]) if candidates else None


DEFAULT_PHASE3E_RUN_ROOT = _find_latest_phase3e(BASE)

FLAGS_SECTOR_PATTERN = (
    "herald_semi_v2_predictions_sector_full_regime_manual_flags_no_source_flags_ctrl_manual_seed_*_v1.csv"
)
CLEAN_FLAGS_SECTOR_PATTERN = (
    "herald_semi_v2_predictions_sector_full_regime_manual_flags_no_source_flags_lag1_growth1y_flags_seed_*_v1.csv"
)
NF_CLEAN_SECTOR_PATTERN = (
    "herald_semi_v2_predictions_sector_full_regime_no_regime_learned_regime_gate_sector_enhanced_no_source_flags_lag1_growth1y_nf_seed_*_v1.csv"
)
DEFAULT_OLD_DASH = (
    BASE
    / "hpc_results/herald_semi_total_253_geo2025/reports/figures/herald_geo2025_final_dashboard.html"
)
DEFAULT_OUT = BASE / "reports/dashboards/herald_france_dashboard.html"
DEFAULT_OFFLINE_OUT = BASE / "reports/dashboards/herald_france_dashboard_offline.html"
DEFAULT_PLOTLY_BUNDLE = Path("/tmp/plotly_embedded.js")
# Historical baselines (2021-2025) used to fill years not covered by the strict ex-ante run
LEGACY_BASELINES_JSON = (
    BASE
    / "hpc_results/herald_semi_total_253_geo2025/baselines_v3_v6_stgnn"
    / "temporal_baselines/reports/final_temporal_baselines_metrics_v1.json"
)
LEGACY_STGNN_JSON = (
    BASE
    / "hpc_results/final_model_comparison_20260429/stgnn_reports"
    / "dynamic_stgnn_model_metrics_seed_0_v1.json"
)
# Legacy Semi V2 predictions covering 2021-2025 (used to fill zone/france data for 2021-2023)
LEGACY_SEMIV2_CSV_PATTERN = (
    "hpc_results/herald_showdown_20260504_173129/data_processed/"
    "herald_semi_v2_predictions_sector_full_semiv2_full_f0.10_s0.30_r0.02_seed_*_v1.csv"
)
DEFAULT_SPLITS = BASE / "metadata/dynamic_stgnn_walk_forward_splits_through_2025_v1.csv"

YEARS = ["2021", "2022", "2023", "2024", "2025"]
SECTORS = ["BE", "FZ", "GI", "JZ", "KZ", "LZ", "MN", "OQ", "RU"]
SECTOR_LABELS = {
    "BE": "Industrie / énergie",
    "FZ": "Construction",
    "GI": "Commerce / transport",
    "JZ": "Information / communication",
    "KZ": "Finance / assurance",
    "LZ": "Immobilier",
    "MN": "Services aux entreprises",
    "OQ": "Services publics",
    "RU": "Arts / loisirs",
}


def read_json_value(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if len(data) == 1 and isinstance(next(iter(data.values())), dict):
        return next(iter(data.values()))
    return data


def load_runs(per_run: Path, pattern: str) -> list[dict[str, Any]]:
    runs = []
    for path in sorted(per_run.glob(pattern)):
        if path.suffix != ".json":
            continue
        d = json.loads(path.read_text(encoding="utf-8"))
        # unwrap single-key wrapper produced by new training scripts
        if isinstance(d, dict) and len(d) == 1:
            inner = next(iter(d.values()))
            if isinstance(inner, dict):
                d = inner
        runs.append(d)
    return runs


def safe_float(x: Any) -> float | None:
    if x is None:
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    if math.isnan(v) or math.isinf(v):
        return None
    return v


def median_dict(runs: list[dict[str, Any]], key: str, labels: list[str]) -> dict[str, float | None]:
    out: dict[str, float | None] = {}
    for label in labels:
        vals = [safe_float((r.get(key) or {}).get(label)) for r in runs]
        vals = [v for v in vals if v is not None]
        out[label] = round(float(np.median(vals)), 6) if vals else None
    return out


def summarize_model(label: str, runs: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not runs:
        return None
    totals = [safe_float(r.get("total_wmape_mean")) for r in runs]
    totals = [v for v in totals if v is not None]
    vals_2025 = [
        safe_float(r.get("total_wmape_2025"))
        if safe_float(r.get("total_wmape_2025")) is not None
        else safe_float((r.get("per_year_total") or {}).get("2025"))
        for r in runs
    ]
    vals_2025 = [v for v in vals_2025 if v is not None]
    return {
        "label": label,
        "n": len(runs),
        "mean": round(float(np.mean(totals)), 6) if totals else None,
        "std": round(float(np.std(totals)), 6) if totals else None,
        "median": round(float(np.median(totals)), 6) if totals else None,
        "wmape_2025_mean": round(float(np.mean(vals_2025)), 6) if vals_2025 else None,
        "wmape_2025_median": round(float(np.median(vals_2025)), 6) if vals_2025 else None,
        "seed_2025": [round(float(v), 6) for v in vals_2025],
        "per_year": median_dict(runs, "per_year_total", YEARS),
        "sector": median_dict(runs, "sector_wmape", SECTORS),
        "alpha": median_dict(runs, "alpha_by_year", [str(y) for y in range(2012, 2026)]),
        "gate": median_dict(runs, "gate_by_year", [str(y) for y in range(2012, 2026)]),
        "gamma_geo": round(float(np.median([r["gamma_geo"] for r in runs if "gamma_geo" in r])), 6)
        if any("gamma_geo" in r for r in runs)
        else None,
        "gamma_mob": round(float(np.median([r["gamma_mob"] for r in runs if "gamma_mob" in r])), 6)
        if any("gamma_mob" in r for r in runs)
        else None,
    }


def model_patterns_for_run(run_root: Path) -> dict[str, str]:
    """Return dashboard input patterns for the selected HERALD run family."""
    if "phase3e_qtensor_arch" in run_root.name:
        stem = "full_regime_no_regime_learned_regime_gate_sector_enhanced_no_source_flags_Q7_effectifs_lag1"
        return {
            "json": "regime_no_regime_learned_regime_gate_sector_enhanced_no_source_flags_Q7_effectifs_lag1_seed_*.json",
            "sector": f"herald_semi_v2_predictions_sector_{stem}_seed_*_v1.csv",
            "graph": f"herald_semi_v2_internals_{stem}_seed_*_v1.npz",
            "label": "HERALD no flags Q7",
        }
    if "phase2j_fair_flag" in run_root.name:
        stem = "full_regime_no_regime_learned_regime_gate_sector_enhanced_no_source_flags_lag1_growth1y_nf"
        return {
            "json": "regime_no_regime_learned_regime_gate_sector_enhanced_no_source_flags_lag1_growth1y_nf_seed_*.json",
            "sector": f"herald_semi_v2_predictions_sector_{stem}_seed_*_v1.csv",
            "graph": f"herald_semi_v2_internals_{stem}_seed_*_v1.npz",
            "label": "HERALD no flags",
        }
    if "phase2i_side5" in run_root.name:
        stem = "full_regime_no_regime_learned_regime_gate_sector_enhanced_no_source_flags_lag1_growth1y"
        return {
            "json": f"regime_no_regime_learned_regime_gate_sector_enhanced_no_source_flags_lag1_growth1y_seed_*.json",
            "sector": f"herald_semi_v2_predictions_sector_{stem}_seed_*_v1.csv",
            "graph": f"herald_semi_v2_internals_{stem}_seed_*_v1.npz",
            "label": "HERALD no flags",
        }
    return {
        "json": "strict_no_source_flags_semiv2_graph_only_seed_*.json",
        "sector": "herald_semi_v2_predictions_sector_full_strict_no_source_flags_graph_only_f0.10_s0.30_r0.02_seed_*_v1.csv",
        "graph": "herald_semi_v2_internals_full_strict_no_source_flags_graph_only_f0.10_s0.30_r0.02_seed_*_v1.npz",
        "label": "HERALD no flags",
    }


def load_phase3e_q0_reference(run_root: Path) -> dict[str, Any] | None:
    if "phase3e_qtensor_arch" not in run_root.name:
        return None
    per_run = run_root / "reports/per_run"
    if not per_run.exists():
        return None
    runs = load_runs(
        per_run,
        "regime_no_regime_learned_regime_gate_sector_enhanced_no_source_flags_Q0_real_seed_*.json",
    )
    if not runs:
        return None
    m = summarize_model("HERALD no flags Q0", runs)
    if m:
        m["flags_source"] = "phase3e_q0_reference"
    return m


def load_dirty_flags_model() -> dict[str, Any] | None:
    """Load the historical HERALD flags control with the older, noisier input set.

    Primary: Phase 2E ctrl_manual (herald_regime_phase2e_residual_rebound_*).
    Fallback: Phase 2R extended_flags_current (herald_regime_phase2r_*).
    """
    per_run = DEFAULT_FLAGS_RUN_ROOT / "reports/per_run"
    if per_run.exists():
        m = summarize_model(
            "HERALD flags étendu",
            load_runs(per_run, "regime_manual_flags_no_source_flags_ctrl_manual_seed_*.json"),
        )
        if m:
            m["flags_source"] = "phase2e_dirty"
            return m
    # Fallback: Phase 2R extended_flags_current
    if DEFAULT_PHASE2R_RUN_ROOT is not None:
        per_run_r = DEFAULT_PHASE2R_RUN_ROOT / "reports/per_run"
        if per_run_r.exists():
            m = summarize_model(
                "HERALD flags étendu",
                load_runs(per_run_r, "regime_manual_flags_extended_flags_current_seed_*.json"),
            )
            if m:
                m["flags_source"] = "phase2r_extended"
                return m
    return None


def load_clean_flags_model() -> dict[str, Any] | None:
    """Load Phase 2J clean flags: same SIDE2 inputs as the no-flags model."""
    if DEFAULT_PHASE2J_RUN_ROOT is not None:
        per_run = DEFAULT_PHASE2J_RUN_ROOT / "reports/per_run"
        if per_run.exists():
            runs = load_runs(per_run, "regime_manual_flags_no_source_flags_lag1_growth1y_flags_seed_*.json")
            if runs:
                m = summarize_model("HERALD flags clean", runs)
                if m:
                    m["flags_source"] = "phase2j_clean"
                    return m
    return None


def load_clean_nf_model() -> dict[str, Any] | None:
    """Load Phase 2J no-flags (lag1_growth1y_nf) as HERALD no flags clean.

    Same inputs as flags clean — only difference is absence of manual regime flags.
    Serves as the fair internal evolution comparator for Q7.
    """
    if DEFAULT_PHASE2J_RUN_ROOT is not None:
        per_run = DEFAULT_PHASE2J_RUN_ROOT / "reports/per_run"
        if per_run.exists():
            runs = load_runs(
                per_run,
                "regime_no_regime_learned_regime_gate_sector_enhanced_no_source_flags_lag1_growth1y_nf_seed_*.json",
            )
            if runs:
                m = summarize_model("HERALD no flags clean", runs)
                if m:
                    m["flags_source"] = "phase2j_nf"
                    return m
    return None


def load_regime_internals(csv_dir: Path, pattern: str) -> dict[str, Any]:
    """Aggregate latent regime and internal weights for display."""
    paths = [p for p in sorted(csv_dir.glob(pattern)) if "_fold_" not in p.name]
    out: dict[str, Any] = {
        "latent": {},
        "latent_step": {},
        "alpha": {},
        "gamma_geo": None,
        "gamma_mob": None,
        "n": 0,
    }
    if not paths:
        return out

    latent_by_year: dict[str, list[np.ndarray]] = {}
    alpha_by_year: dict[str, list[float]] = {}
    gamma_geo: list[float] = []
    gamma_mob: list[float] = []
    for path in paths:
        try:
            z = np.load(path, allow_pickle=True)
        except Exception:
            continue
        if "years" not in z:
            continue
        years = [str(int(y)) for y in z["years"]]
        if "latent_regime_values" in z:
            lat = z["latent_regime_values"].astype(float)
            for idx, year in enumerate(years):
                if idx < lat.shape[0]:
                    latent_by_year.setdefault(year, []).append(lat[idx])
        if "alpha_values" in z:
            alpha = z["alpha_values"].astype(float)
            for idx, year in enumerate(years):
                if idx < alpha.shape[0]:
                    alpha_by_year.setdefault(year, []).append(float(np.nanmean(alpha[idx])))
        if "gamma_geo" in z:
            gamma_geo.append(float(np.asarray(z["gamma_geo"]).ravel()[0]))
        if "gamma_mob" in z:
            gamma_mob.append(float(np.asarray(z["gamma_mob"]).ravel()[0]))
        out["n"] += 1

    for year, vals in latent_by_year.items():
        arr = np.vstack(vals)
        out["latent"][year] = [round(float(v), 6) for v in np.nanmedian(arr, axis=0)]
    ordered_years = sorted(out["latent"], key=int)
    for prev, cur in zip(ordered_years[:-1], ordered_years[1:]):
        a = np.asarray(out["latent"][prev], dtype=float)
        b = np.asarray(out["latent"][cur], dtype=float)
        out["latent_step"][cur] = round(float(np.linalg.norm(b - a)), 6)
    out["alpha"] = {
        year: round(float(np.nanmedian(vals)), 6)
        for year, vals in alpha_by_year.items()
    }
    out["gamma_geo"] = round(float(np.nanmedian(gamma_geo)), 6) if gamma_geo else None
    out["gamma_mob"] = round(float(np.nanmedian(gamma_mob)), 6) if gamma_mob else None
    return out


def extract_js_const(name: str, html: str) -> Any:
    match = re.search(r"const\s+" + re.escape(name) + r"\s*=\s*([\{\[])", html)
    if not match:
        return None
    start = match.start(1)
    opener = html[start]
    closer = "}" if opener == "{" else "]"
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(html)):
        ch = html[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == opener:
            depth += 1
        elif ch == closer:
            depth -= 1
            if depth == 0:
                return json.loads(html[start : i + 1])
    return None


def load_old_constants(old_dashboard: Path) -> dict[str, Any]:
    if not old_dashboard.exists():
        return {}
    html = old_dashboard.read_text(encoding="utf-8")
    names = [
        "GEOJSON",
        "ZE_NAMES",
        "GRAPH_DATA",
        "NEW_CONN",
        "GATE_SM",
        "ZONE_V6",
        "ZONE_V6_PREDS",
        "RIDGE_YR",
        "ARIMA_PY",
        "DCRNN_PY",
        "STGNN_PY",
    ]
    return {name: extract_js_const(name, html) for name in names}


def load_baseline_years(
    run_root: Path,
    panel: str = "no_source_flags",
    legacy_json: Path | None = None,
    legacy_stgnn_json: Path | None = None,
) -> dict[str, dict[str, float | None]]:
    """Read per-year WMAPE for each baseline from the new run directory."""
    result: dict[str, dict[str, float | None]] = {}
    base_dir = run_root / "temporal_baselines"

    # Deterministic (ridge_ar, arima_local, naive_lag1) — rglob handles nested /reports/
    det_dir = base_dir / f"{panel}_deterministic"
    if det_dir.exists():
        for jf in sorted(det_dir.rglob("final_temporal_baselines_metrics_v1.json")):
            try:
                data = json.loads(jf.read_text(encoding="utf-8"))
                for entry in data.get("metrics_by_model_year", []):
                    m = entry.get("model", "")
                    y = str(entry.get("target_year", ""))
                    w = safe_float(entry.get("wmape"))
                    if m and y and w is not None:
                        result.setdefault(m, {})[y] = round(w, 6)
            except Exception:
                pass

    # LSTM: aggregate median across seeds — rglob handles nested /reports/
    lstm_by_year: dict[str, list[float]] = {}
    for seed_dir in sorted(base_dir.glob(f"{panel}_lstm_seed_*")):
        for jf in sorted(seed_dir.rglob("*.json")):
            try:
                data = json.loads(jf.read_text(encoding="utf-8"))
                for entry in data.get("metrics_by_model_year", []):
                    if entry.get("model") == "lstm_local":
                        y = str(entry.get("target_year", ""))
                        w = safe_float(entry.get("wmape"))
                        if y and w is not None:
                            lstm_by_year.setdefault(y, []).append(w)
            except Exception:
                pass
    if lstm_by_year:
        result["lstm_local"] = {y: round(float(np.median(v)), 6) for y, v in lstm_by_year.items()}

    # DCRNN + Dynamic STGNN: aggregate median across per_run JSONs
    per_run = run_root / "reports/per_run"
    for model_key in ("dcrnn_residual", "dynamic_stgnn_residual"):
        by_year: dict[str, list[float]] = {}
        for jf in sorted(per_run.glob(f"strict_{panel}_stgnn_dcrnn_seed_*.json")):
            try:
                data = json.loads(jf.read_text(encoding="utf-8"))
                for entry in data.get("metrics_by_model_year", []):
                    if entry.get("model") == model_key:
                        y = str(entry.get("target_year", ""))
                        w = safe_float(entry.get("wmape"))
                        if y and w is not None:
                            by_year.setdefault(y, []).append(w)
            except Exception:
                pass
        if by_year:
            result[model_key] = {y: round(float(np.median(v)), 6) for y, v in by_year.items()}

    # --- Legacy fill-in: years not covered by new run (e.g. 2021-2023) ---
    # New run data takes precedence; legacy only fills missing years.
    if legacy_json and Path(legacy_json).exists():
        try:
            leg = json.loads(Path(legacy_json).read_text(encoding="utf-8"))
            # Aggregate per model: median across seeds for each year
            leg_by: dict[str, dict[str, list[float]]] = {}
            for e in leg.get("metrics_by_model_year", []):
                m = e.get("model", "")
                y = str(e.get("target_year", ""))
                w = safe_float(e.get("wmape"))
                if m and y and w is not None:
                    leg_by.setdefault(m, {}).setdefault(y, []).append(w)
            for m, ydict in leg_by.items():
                cur = result.setdefault(m, {})
                for y, vals in ydict.items():
                    if y not in cur:  # only fill missing years
                        cur[y] = round(float(np.median(vals)), 6)
        except Exception:
            pass

    if legacy_stgnn_json and Path(legacy_stgnn_json).exists():
        try:
            leg = json.loads(Path(legacy_stgnn_json).read_text(encoding="utf-8"))
            leg_by2: dict[str, dict[str, list[float]]] = {}
            for e in leg.get("metrics_by_model_year", []):
                m = e.get("model", "")
                y = str(e.get("target_year", ""))
                w = safe_float(e.get("wmape"))
                if m and y and w is not None:
                    leg_by2.setdefault(m, {}).setdefault(y, []).append(w)
            for m, ydict in leg_by2.items():
                cur = result.setdefault(m, {})
                for y, vals in ydict.items():
                    if y not in cur:
                        cur[y] = round(float(np.median(vals)), 6)
        except Exception:
            pass

    return result


def build_semiv2_zone_data(csv_dir: Path, pattern: str) -> dict[str, Any]:
    paths = sorted(csv_dir.glob(pattern))
    if not paths:
        raise FileNotFoundError(f"No HERALD sector prediction CSV found in {csv_dir}")

    zone_frames = []
    sector_frames = []
    zsec_frames = []
    for path in paths:
        df = pd.read_csv(path)
        df["ZE2020"] = df["ZE2020"].astype(str).str.zfill(4)
        zone = (
            df.groupby(["ZE2020", "target_year"])
            .agg(y_true=("y_true_sector", "sum"), y_pred=("y_pred_total", "first"))
            .reset_index()
        )
        zone_frames.append(zone)
        sector = (
            df.groupby(["sector", "target_year"])
            .agg(y_true=("y_true_sector", "sum"), y_pred=("y_pred_sector", "sum"))
            .reset_index()
        )
        sector_frames.append(sector)
        zsec = (
            df.groupby(["ZE2020", "target_year", "sector"])
            .agg(y_true=("y_true_sector", "first"), y_pred=("y_pred_sector", "median"))
            .reset_index()
        )
        zsec_frames.append(zsec)

    zones = (
        pd.concat(zone_frames)
        .groupby(["ZE2020", "target_year"])
        .agg(y_true=("y_true", "first"), y_pred=("y_pred", "median"))
        .reset_index()
    )
    zones["abs_error"] = (zones["y_pred"] - zones["y_true"]).abs()
    zones["wmape"] = zones["abs_error"] / zones["y_true"].replace(0, np.nan)

    sectors = (
        pd.concat(sector_frames)
        .groupby(["sector", "target_year"])
        .agg(y_true=("y_true", "first"), y_pred=("y_pred", "median"))
        .reset_index()
    )
    zsec = (
        pd.concat(zsec_frames)
        .groupby(["ZE2020", "target_year", "sector"])
        .agg(y_true=("y_true", "first"), y_pred=("y_pred", "median"))
        .reset_index()
    )

    zone_error: dict[str, dict[str, float]] = {}
    zone_pred: dict[str, dict[str, dict[str, int]]] = {}
    zone_real: dict[str, dict[str, int]] = {}
    zone_abs: dict[str, dict[str, int]] = {}
    for year in YEARS:
        part = zones[zones["target_year"] == int(year)]
        zone_error[year] = {}
        zone_pred[year] = {}
        zone_real[year] = {}
        zone_abs[year] = {}
        for row in part.itertuples(index=False):
            ze = str(row.ZE2020)
            zone_error[year][ze] = round(float(row.wmape), 6)
            zone_real[year][ze] = int(round(float(row.y_true)))
            zone_abs[year][ze] = int(round(float(row.abs_error)))
            zone_pred[year][ze] = {
                "y_true": int(round(float(row.y_true))),
                "y_pred": int(round(float(row.y_pred))),
                "abs_error": int(round(float(row.abs_error))),
            }

    sector_totals_by_year: dict[str, dict[str, list[int] | list[str]]] = {}
    for year, grp in sectors.groupby("target_year"):
        part = grp.sort_values("y_true", ascending=False)
        sector_totals_by_year[str(int(year))] = {
            "sectors": part["sector"].tolist(),
            "y_true": [int(round(v)) for v in part["y_true"].tolist()],
            "y_pred": [int(round(v)) for v in part["y_pred"].tolist()],
        }

    zone_sector_pred: dict[str, dict[str, list[dict[str, int | str]]]] = {}
    for (ze, year), grp in zsec.groupby(["ZE2020", "target_year"]):
        zone_sector_pred.setdefault(str(ze), {})[str(int(year))] = [
            {"s": str(row.sector), "t": int(round(float(row.y_true))), "p": int(round(float(row.y_pred)))}
            for row in grp.sort_values("y_true", ascending=False).itertuples(index=False)
        ]

    france_year = (
        zones.groupby("target_year")
        .agg(y_true=("y_true", "sum"), y_pred=("y_pred", "sum"), abs_error=("abs_error", "sum"))
        .reset_index()
    )
    france_total = {
        str(int(row.target_year)): {
            "y_true": int(round(float(row.y_true))),
            "y_pred": int(round(float(row.y_pred))),
            "abs_error": int(round(float(row.abs_error))),
        }
        for row in france_year.itertuples(index=False)
    }

    return {
        "zone_error": zone_error,
        "zone_pred": zone_pred,
        "zone_real": zone_real,
        "zone_abs": zone_abs,
        "zone_sector_pred": zone_sector_pred,
        "sector_totals_by_year": sector_totals_by_year,
        "france_total": france_total,
    }


def empty_zone_data() -> dict[str, Any]:
    return {
        "zone_error": {},
        "zone_pred": {},
        "zone_real": {},
        "zone_abs": {},
        "zone_sector_pred": {},
        "sector_totals_by_year": {},
        "france_total": {},
    }


def safe_build_semiv2_zone_data(csv_dir: Path, pattern: str, label: str) -> dict[str, Any]:
    try:
        return build_semiv2_zone_data(csv_dir, pattern)
    except FileNotFoundError:
        print(f"Warning: {label} zone/sector CSV not found in {csv_dir}; metrics only.")
        return empty_zone_data()


def js(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def non_null_pairs(mapping: dict[str, Any]) -> dict[str, float]:
    return {k: v for k, v in mapping.items() if v is not None}


def load_optional_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def build_fold_table(path: Path) -> str:
    if not path.exists():
        return "<div class='mini'>Protocole de validation non disponible.</div>"
    df = pd.read_csv(path)
    rows = []
    for row in df.sort_values("target_year").itertuples(index=False):
        rows.append(
            "<tr>"
            f"<td>{int(row.target_year)}</td>"
            f"<td>{int(row.train_years_min)}-{int(row.train_years_max)}</td>"
            f"<td>{int(row.eval_year)}</td>"
            "<td>walk-forward</td>"
            "</tr>"
        )
    return (
        "<table><thead><tr><th>Année prédite</th><th>Années utilisées pour entraîner</th>"
        "<th>Année testée</th><th>Protocole</th></tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table>"
    )


def clean_connections(rows: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    if not rows:
        return []
    cleaned = []
    for row in rows:
        item = dict(row)
        if "control_weight" not in item:
            item["control_weight"] = item.get("v6_weight", item.get("weight_v6"))
        item.pop("v6_weight", None)
        item.pop("weight_v6", None)
        cleaned.append(item)
    return cleaned


def _flatten_coords(coords: Any) -> list[tuple[float, float]]:
    if not coords:
        return []
    if isinstance(coords, (list, tuple)) and len(coords) >= 2 and all(
        isinstance(v, (int, float)) for v in coords[:2]
    ):
        return [(float(coords[0]), float(coords[1]))]
    pts: list[tuple[float, float]] = []
    if isinstance(coords, (list, tuple)):
        for item in coords:
            pts.extend(_flatten_coords(item))
    return pts


def geojson_centroids(geojson: dict[str, Any] | None) -> dict[str, tuple[float, float]]:
    if not geojson:
        return {}
    out: dict[str, tuple[float, float]] = {}
    for feat in geojson.get("features", []):
        props = feat.get("properties") or {}
        ze = str(props.get("ze2020") or props.get("ZE2020") or feat.get("id") or "").zfill(4)
        pts = _flatten_coords((feat.get("geometry") or {}).get("coordinates"))
        # Keep only metropolitan France for the main map overlay. Overseas zones
        # are outside the displayed map extent and would distort edge readability.
        pts = [(lon, lat) for lon, lat in pts if -6 <= lon <= 10 and 41 <= lat <= 52]
        if not ze or not pts:
            continue
        out[ze] = (float(np.mean([p[0] for p in pts])), float(np.mean([p[1] for p in pts])))
    return out


def build_learned_graph_data(
    csv_dir: Path,
    geojson: dict[str, Any] | None,
    ze_names: dict[str, Any],
    pattern: str = "herald_semi_v2_internals_full_strict_no_source_flags_graph_only_f0.10_s0.30_r0.02_seed_*_v1.npz",
    max_edges: int = 70,
    total_edges: int = 500,
) -> dict[str, list[dict[str, Any]]]:
    paths = [p for p in sorted(csv_dir.glob(pattern)) if "_fold_" not in p.name]
    if not paths:
        return {}
    centroids = geojson_centroids(geojson)
    if not centroids:
        return {}

    adjs = []
    years = None
    node_order = None
    for path in paths:
        z = np.load(path, allow_pickle=True)
        if "dynamic_adj" not in z or "years" not in z or "node_order" not in z:
            continue
        adjs.append(z["dynamic_adj"].astype(np.float32))
        years = z["years"].astype(int)
        node_order = z["node_order"].astype(int)
    if not adjs or years is None or node_order is None:
        return {}

    mean_adj = np.mean(np.stack(adjs, axis=0), axis=0)
    node_codes = [str(int(x)).zfill(4) for x in node_order]
    graph: dict[str, dict[str, list[dict[str, Any]]]] = {}

    for t, year in enumerate(years):
        if str(int(year)) not in YEARS:
            continue
        mat = mean_adj[t].copy()
        np.fill_diagonal(mat, 0.0)
        prev = mean_adj[t - 1] if t > 0 else mat
        delta = np.abs(mat - prev)
        # Use a salience score so the displayed graph changes with the year:
        # strong edges remain visible, but annual reconfigurations are surfaced.
        score = mat + 3.0 * delta
        def collect_edges(score_matrix: np.ndarray, limit: int, multiplier: int = 4) -> list[dict[str, Any]]:
            rows: list[dict[str, Any]] = []
            flat_idx = np.argpartition(score_matrix.ravel(), -min(limit * multiplier, score_matrix.size))[
                -min(limit * multiplier, score_matrix.size) :
            ]
            ranked = flat_idx[np.argsort(score_matrix.ravel()[flat_idx])[::-1]]
            seen: set[tuple[str, str]] = set()
            for idx in ranked:
                i, j = np.unravel_index(int(idx), score_matrix.shape)
                if i == j:
                    continue
                zi, zj = node_codes[i], node_codes[j]
                if zi not in centroids or zj not in centroids:
                    continue
                key = tuple(sorted((zi, zj)))
                if key in seen:
                    continue
                seen.add(key)
                lon0, lat0 = centroids[zi]
                lon1, lat1 = centroids[zj]
                rows.append(
                    {
                        "lon0": round(lon0, 5),
                        "lat0": round(lat0, 5),
                        "lon1": round(lon1, 5),
                        "lat1": round(lat1, 5),
                        "ze_i": zi,
                        "ze_j": zj,
                        "name_i": ze_names.get(zi, zi),
                        "name_j": ze_names.get(zj, zj),
                        "weight": round(float(mat[i, j]), 6),
                        "delta": round(float(delta[i, j]), 6),
                        "score": round(float(score[i, j]), 6),
                    }
                )
                if len(rows) >= limit:
                    break
            return rows

        salient = collect_edges(score, max_edges, multiplier=5)
        # The total view must still be year-sensitive. Ranking only by raw
        # weight keeps almost the same strongest edges every year, which makes
        # the UI look static. Use the annual salience score for the displayed
        # total layer so it reflects both strong edges and reconfigurations.
        total = collect_edges(score, total_edges, multiplier=8)
        graph[str(int(year))] = {"salient": salient, "total": total}
    return graph


def load_zone_ridge_predictions(csv_dir: Path) -> dict[str, dict[str, float]]:
    """Load deterministic Ridge AR zone predictions for 2021-2025."""
    paths = sorted(csv_dir.glob("herald_semi_v2_predictions_total_*_seed_*_v1.csv"))
    if paths:
        frames = []
        for path in paths:
            try:
                df = pd.read_csv(path)
            except Exception:
                continue
            if {"target_year", "ZE2020", "ridge_pred"}.issubset(df.columns):
                frames.append(df[["target_year", "ZE2020", "ridge_pred"]])
        if frames:
            df = pd.concat(frames, ignore_index=True)
            df["ZE2020"] = df["ZE2020"].astype(str).str.split(".").str[0].str.zfill(4)
            agg = (
                df.groupby(["target_year", "ZE2020"], as_index=False)["ridge_pred"]
                .median()
            )
            out: dict[str, dict[str, float]] = {}
            for _, row in agg.iterrows():
                year = str(int(row["target_year"]))
                ze = str(row["ZE2020"])
                out.setdefault(year, {})[ze] = float(row["ridge_pred"])
            return out

    paths = sorted(csv_dir.glob("herald_v7_predictions_total_ridge_only_strict_no_source_flags_ridge_only_seed_0_v1.csv"))
    if not paths:
        paths = sorted((BASE / "data/processed").glob("dynamic_feature_panel_baseline_predictions_v1.csv"))
    if not paths:
        return {}
    try:
        df = pd.read_csv(paths[0])
    except Exception as e:
        print(f"Warning: ridge zone predictions failed: {e}")
        return {}
    pred_col = "ridge_pred" if "ridge_pred" in df.columns else "y_pred"
    if not {"target_year", "ZE2020", pred_col}.issubset(df.columns):
        return {}
    df["ZE2020"] = df["ZE2020"].astype(str).str.split(".").str[0].str.zfill(4)
    out: dict[str, dict[str, float]] = {}
    for _, row in df.iterrows():
        year = str(int(row["target_year"]))
        ze = str(row["ZE2020"])
        out.setdefault(year, {})[ze] = float(row[pred_col])
    return out


def build_dashboard(args: argparse.Namespace) -> None:
    run_root = Path(args.run_root)
    per_run = run_root / "reports/per_run"
    csv_dir = run_root / "data_processed"
    out_path = Path(args.out)
    old = load_old_constants(Path(args.old_dashboard))
    patterns = model_patterns_for_run(run_root)

    winner = summarize_model(patterns.get("label", "HERALD no flags"), load_runs(per_run, patterns["json"]))
    if not winner:
        raise RuntimeError("HERALD principal runs were not found.")
    no_flags_clean = load_clean_nf_model()
    dirty_flags = load_dirty_flags_model()
    clean_flags = load_clean_flags_model()
    internal_controls = [
        summarize_model(
            "Contrôle sans semi-supervision",
            load_runs(per_run, "strict_no_source_flags_semiv2_graph_only_nossl_seed_*.json"),
        ),
        summarize_model(
            "Contrôle local",
            load_runs(per_run, "strict_no_source_flags_v6_self_only_seed_*.json"),
        ),
        summarize_model(
            "Contrôle strict lag-only",
            load_runs(per_run, "strict_lag_only_semiv2_graph_only_seed_*.json"),
        ),
    ]
    internal_controls = [m for m in internal_controls if m is not None]

    zone_data = build_semiv2_zone_data(
        csv_dir,
        patterns["sector"],
    )
    flags_zone_data = safe_build_semiv2_zone_data(
        DEFAULT_FLAGS_RUN_ROOT / "data_processed",
        FLAGS_SECTOR_PATTERN,
        "HERALD flags étendu",
    )
    clean_flags_zone_data = (
        safe_build_semiv2_zone_data(
            DEFAULT_PHASE2J_RUN_ROOT / "data_processed",
            CLEAN_FLAGS_SECTOR_PATTERN,
            "HERALD flags clean",
        )
        if DEFAULT_PHASE2J_RUN_ROOT is not None
        else empty_zone_data()
    )
    nf_clean_zone_data = (
        safe_build_semiv2_zone_data(
            DEFAULT_PHASE2J_RUN_ROOT / "data_processed",
            NF_CLEAN_SECTOR_PATTERN,
            "HERALD no flags clean",
        )
        if DEFAULT_PHASE2J_RUN_ROOT is not None
        else empty_zone_data()
    )
    # Fill 2021-2023 zone/france data from legacy run (strict ex-ante only has 2024-2025)
    legacy_csvs = sorted(BASE.glob(LEGACY_SEMIV2_CSV_PATTERN))
    if legacy_csvs:
        try:
            legacy_zone = build_semiv2_zone_data(legacy_csvs[0].parent, legacy_csvs[0].name)
            for year in ["2021", "2022", "2023"]:
                if not zone_data["zone_error"].get(year):
                    zone_data["zone_error"][year] = legacy_zone["zone_error"].get(year, {})
                    zone_data["zone_pred"][year]  = legacy_zone["zone_pred"].get(year, {})
                    zone_data["zone_real"][year]  = legacy_zone["zone_real"].get(year, {})
                    zone_data["zone_abs"][year]   = legacy_zone["zone_abs"].get(year, {})
                if year not in zone_data["france_total"]:
                    ft = legacy_zone["france_total"].get(year)
                    if ft:
                        zone_data["france_total"][year] = ft
        except Exception as e:
            print(f"Warning: legacy zone fill failed: {e}")
    baselines = load_baseline_years(run_root, panel="no_source_flags",
                                    legacy_json=LEGACY_BASELINES_JSON,
                                    legacy_stgnn_json=LEGACY_STGNN_JSON)
    ridge_yr = baselines.get("ridge_ar") or old.get("RIDGE_YR") or {
        "2021": 0.067308, "2022": 0.086199, "2023": 0.077667, "2024": 0.030697, "2025": 0.036085,
    }
    # Correct 2025 Ridge AR — strict exante no_source_flags value (legacy files had 0.033911)
    ridge_yr["2025"] = 0.036085
    arima_yr = baselines.get("arima_local") or old.get("ARIMA_PY") or {
        "2021": 0.125337, "2022": 0.097012, "2023": 0.037834, "2024": 0.08621, "2025": 0.034292,
    }
    lstm_yr = baselines.get("lstm_local") or {}
    # Strict exante no_source_flags medians — used as fallback AND to fill missing years (esp. 2025)
    _dcrnn_strict = {"2021": 0.061489, "2022": 0.079708, "2023": 0.072683, "2024": 0.031266, "2025": 0.031156}
    _stgnn_strict = {"2021": 0.060871, "2022": 0.078993, "2023": 0.072616, "2024": 0.032167, "2025": 0.031134}
    _dcrnn_raw = baselines.get("dcrnn_residual") or old.get("DCRNN_PY") or {}
    _stgnn_raw = baselines.get("dynamic_stgnn_residual") or old.get("STGNN_PY") or {}
    # Merge: strict values first (all years), then override with any loaded values
    dcrnn_yr = {**_dcrnn_strict, **_dcrnn_raw}
    stgnn_yr = {**_stgnn_strict, **_stgnn_raw}

    learned_graph = build_learned_graph_data(
        csv_dir,
        old.get("GEOJSON"),
        old.get("ZE_NAMES") or {},
        pattern=patterns["graph"],
    )
    if not learned_graph:
        learned_graph = old.get("GRAPH_DATA") or {}
    zone_ridge = load_zone_ridge_predictions(csv_dir)

    payload = {
        "years": YEARS,
        "sectorLabels": SECTOR_LABELS,
        "models": [m for m in [winner, no_flags_clean, clean_flags] if m is not None],
        "historicalControl": dirty_flags,
        "internalControls": internal_controls,
        "ridgeYear": ridge_yr,
        "arimaYear": arima_yr,
        "lstmYear": lstm_yr,
        "dcrnnYear": dcrnn_yr,
        "stgnnYear": stgnn_yr,
        "geojson": old.get("GEOJSON"),
        "zeNames": old.get("ZE_NAMES") or {},
        "graphData": learned_graph,
        "newConn": clean_connections(old.get("NEW_CONN")),
        "zoneControl": old.get("ZONE_V6") or {},
        "zoneControlPreds": old.get("ZONE_V6_PREDS") or {},
        "zoneSemiError": zone_data["zone_error"],
        "zoneSemiPreds": zone_data["zone_pred"],
        "zoneSemiReal": zone_data["zone_real"],
        "zoneSemiAbs": zone_data["zone_abs"],
        "zoneSectorPreds": zone_data["zone_sector_pred"],
        "sectorTotalsByYear": zone_data["sector_totals_by_year"],
        "franceTotal": zone_data["france_total"],
        "zoneDirtyFlagsPreds": flags_zone_data["zone_pred"],
        "zoneDirtyFlagsSectorPreds": flags_zone_data["zone_sector_pred"],
        "dirtyFlagsSectorTotalsByYear": flags_zone_data["sector_totals_by_year"],
        "dirtyFlagsFranceTotal": flags_zone_data["france_total"],
        "zoneCleanFlagsPreds": clean_flags_zone_data["zone_pred"],
        "zoneCleanFlagsSectorPreds": clean_flags_zone_data["zone_sector_pred"],
        "cleanFlagsSectorTotalsByYear": clean_flags_zone_data["sector_totals_by_year"],
        "cleanFlagsFranceTotal": clean_flags_zone_data["france_total"],
        "zoneNfCleanPreds": nf_clean_zone_data["zone_pred"],
        "zoneNfCleanSectorPreds": nf_clean_zone_data["zone_sector_pred"],
        "nfCleanSectorTotalsByYear": nf_clean_zone_data["sector_totals_by_year"],
        "nfCleanFranceTotal": nf_clean_zone_data["france_total"],
        "zoneRidgePreds": zone_ridge,
        "regimeInternals": load_regime_internals(csv_dir, patterns["graph"]),
        "heraldInputs": {
            "annual": ["side_lag_1", "growth_1y"],
            "regime": "appris par le modèle; aucune flag crise/rebond",
            "variant": "lag1_growth1y",
            "strategy": "retirer les flags, enlever les entrées SIDE redondantes, garder seulement niveau récent + croissance 1 an",
        },
    }

    sector_year_options = "\n".join(
        f'<option value="{y}"{" selected" if y=="2025" else ""}>{y}</option>'
        for y in YEARS
    )

    semi_2025 = winner["wmape_2025_median"]
    ridge_2025 = safe_float(ridge_yr.get("2025"))
    gain = None
    if semi_2025 is not None and ridge_2025:
        gain = 100 * (ridge_2025 - semi_2025) / ridge_2025

    fold_table_html = build_fold_table(Path(args.splits_path))

    plotly_script = '<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>'
    if args.embed_plotly:
        bundle_path = Path(args.plotly_bundle)
        if not bundle_path.exists():
            raise FileNotFoundError(
                f"Plotly bundle not found: {bundle_path}. "
                "Run once with CDN or provide --plotly-bundle."
            )
        plotly_script = "<script>\n" + bundle_path.read_text(encoding="utf-8") + "\n</script>"

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>HERALD France - Comparaison modèles</title>
{plotly_script}
<style>
  :root {{
    --bg:#0f1220; --panel:#171b2d; --panel2:#20253a; --line:#30364f;
    --text:#eef2ff; --muted:#9aa4bf; --semi:#f7834f; --v6:#4aa3ff;
    --v7:#b084f5; --ridge:#66bb6a; --bad:#ef5350; --good:#26a69a;
  }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--text); font-family:Inter,Segoe UI,Arial,sans-serif; }}
  .wrap {{ max-width:1500px; margin:0 auto; padding:22px; }}
  h1 {{ margin:0 0 8px; font-size:30px; font-weight:760; letter-spacing:0; }}
  .subtitle {{ color:var(--muted); margin-bottom:18px; line-height:1.45; max-width:1100px; }}
  .kpis {{ display:grid; grid-template-columns:repeat(4,minmax(180px,1fr)); gap:12px; margin:16px 0 22px; }}
  .kpi {{ background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:14px; }}
  .kpi .v {{ font-size:26px; font-weight:760; }}
  .kpi .l {{ color:var(--muted); font-size:13px; margin-top:4px; }}
  .section {{ margin-top:26px; }}
  .section-title {{ font-size:20px; font-weight:720; margin:0 0 6px; }}
  .section-note {{ color:var(--muted); font-size:14px; line-height:1.45; max-width:1200px; margin-bottom:10px; }}
  .grid2 {{ display:grid; grid-template-columns:1fr 1fr; gap:14px; }}
  .grid-map {{ display:grid; grid-template-columns:minmax(620px,1.35fr) minmax(420px,0.9fr); gap:14px; align-items:start; }}
  .card {{ background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:12px; }}
  .controls {{ display:flex; flex-wrap:wrap; gap:10px; align-items:center; margin-bottom:10px; }}
  select {{ background:#111525; color:var(--text); border:1px solid var(--line); border-radius:6px; padding:7px 10px; }}
  table {{ width:100%; border-collapse:collapse; font-size:13px; }}
  th,td {{ border-bottom:1px solid var(--line); padding:7px 6px; text-align:left; }}
  th {{ color:#cbd5ff; font-weight:700; }}
  .mini {{ color:var(--muted); font-size:12px; line-height:1.4; }}
  .warn {{ color:#ffd180; }}
  .intel-panel {{ margin-top:10px; color:var(--text); }}
  .intel-head {{ display:flex; justify-content:space-between; gap:10px; align-items:flex-start; margin-bottom:8px; }}
  .intel-title {{ font-weight:720; color:#eef2ff; }}
  .intel-status {{ color:#f6c15b; font-size:11px; border:1px solid #6f5a2b; border-radius:999px; padding:3px 7px; white-space:nowrap; }}
  .intel-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:8px; }}
  .intel-chip {{ background:#111525; border:1px solid var(--line); border-radius:8px; padding:8px; }}
  .intel-chip .label {{ color:var(--muted); font-size:11px; margin-bottom:4px; }}
  .intel-chip .value {{ font-size:18px; font-weight:760; color:#eef2ff; }}
  .scorebar {{ height:7px; background:#242a3f; border-radius:999px; overflow:hidden; margin-top:6px; }}
  .scorebar > span {{ display:block; height:100%; border-radius:999px; }}
  .scorebar.opp > span {{ background:linear-gradient(90deg,#1f7a4d,#ffe066); }}
  .scorebar.risk > span {{ background:linear-gradient(90deg,#66bb6a,#ffd54f,#ef5350); }}
  .intel-alert {{ margin-top:8px; color:#ffd180; font-size:12px; }}
  .intel-details {{ margin-top:8px; color:var(--muted); font-size:12px; }}
  .intel-details summary {{ cursor:pointer; color:#cbd5ff; }}
  .arch-wrap {{ display:flex; flex-direction:column; gap:0; }}
  .arch-row {{ display:flex; align-items:stretch; gap:0; }}
  .arch-col {{ display:flex; flex-direction:column; gap:6px; }}
  .arch-box {{ background:#111525; border:1px solid #3a4263; border-radius:8px; padding:12px; }}
  .arch-box.input {{ border-color:#4aa3ff55; }}
  .arch-box.ridge {{ border-color:#66bb6a55; }}
  .arch-box.neural {{ border-color:#f7834f55; }}
  .arch-box.gate {{ border-color:#b084f555; }}
  .arch-box.output {{ border-color:#26a69a55; }}
  .arch-box h4 {{ margin:0 0 6px; font-size:12px; font-weight:700; text-transform:uppercase; letter-spacing:.06em; color:var(--muted); }}
  .arch-box .aname {{ font-size:15px; font-weight:760; color:#eef2ff; margin-bottom:6px; }}
  .arch-box ul {{ margin:0; padding-left:16px; color:var(--muted); font-size:12px; line-height:1.6; }}
  .arch-badge {{ display:inline-block; background:#1a2040; border:1px solid #3a4263; border-radius:5px; padding:3px 8px; font-size:11px; font-family:monospace; color:#9aa4bf; margin:2px 2px 2px 0; }}
  .arch-badge.hi {{ border-color:#4aa3ff88; color:#4aa3ff; }}
  .arch-badge.gate {{ border-color:#b084f588; color:#b084f5; }}
  .arch-badge.flag {{ border-color:#ffd18088; color:#ffd180; }}
  .arch-pipe {{ display:flex; align-items:center; justify-content:center; padding:0 8px; color:#f7834f; font-size:22px; font-weight:800; flex-shrink:0; }}
  .arch-pipe.vert {{ flex-direction:column; padding:4px 0; font-size:18px; }}
  .arch-pipe.thin {{ font-size:14px; color:#9aa4bf; }}
  .arch-branch {{ display:flex; flex-direction:column; gap:6px; flex:1; }}
  .arch-label {{ font-size:11px; color:var(--muted); margin-top:4px; }}
  .arch-label b {{ color:#eef2ff; }}
  .arch-divider {{ border:none; border-top:1px solid var(--line); margin:12px 0; }}
  .arch-compare {{ display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-top:12px; }}
  .arch-compare-card {{ background:#111525; border:1px solid var(--line); border-radius:8px; padding:12px; }}
  .arch-compare-card.nf {{ border-left:3px solid #f7834f; }}
  .arch-compare-card.fl {{ border-left:3px solid #ffd180; }}
  .arch-compare-card b {{ color:#eef2ff; font-size:14px; }}
  .arch-compare-card .acsub {{ color:var(--muted); font-size:12px; line-height:1.5; margin-top:6px; }}
  .arch-compare-card .acchips {{ display:flex; flex-wrap:wrap; gap:4px; margin-top:6px; }}
  .arch-phase-badge {{ display:inline-block; font-size:10px; font-weight:700; border-radius:999px; padding:2px 8px; margin-left:6px; vertical-align:middle; }}
  .arch-phase-badge.done {{ background:#1a3a1a; color:#66bb6a; border:1px solid #66bb6a55; }}
  .arch-phase-badge.pend {{ background:#2a2a1a; color:#ffd180; border:1px solid #ffd18055; }}
  .arch-metric {{ margin-top:8px; font-size:13px; }}
  .arch-metric .av {{ font-size:20px; font-weight:760; color:#eef2ff; }}
  .arch-metric .al {{ font-size:11px; color:var(--muted); }}
  .model-figure {{ display:grid; grid-template-columns:1fr 44px 1.45fr 44px 1fr; gap:10px; align-items:center; }}
  .model-node {{ background:#111525; border:1px solid #3a4263; border-radius:8px; padding:14px; min-height:142px; }}
  .model-node h3 {{ margin:0 0 10px; font-size:15px; color:#cbd5ff; }}
  .model-node .big {{ font-size:18px; font-weight:780; color:#eef2ff; margin-bottom:8px; }}
  .model-node ul {{ margin:0; padding-left:18px; color:var(--muted); line-height:1.55; font-size:13px; }}
  .model-arrow {{ text-align:center; color:#f7834f; font-size:30px; font-weight:800; }}
  .model-stack {{ display:grid; grid-template-columns:1fr; gap:8px; }}
  .model-step {{ background:#171b2d; border:1px solid #3a4263; border-radius:7px; padding:9px; }}
  .model-step strong {{ display:block; color:#eef2ff; margin-bottom:3px; }}
  .model-step span {{ color:var(--muted); font-size:12px; }}
  .model-compare {{ margin-top:12px; display:grid; grid-template-columns:1fr 1fr; gap:10px; }}
  .model-compare div {{ background:#111525; border:1px solid var(--line); border-radius:8px; padding:10px; color:var(--muted); font-size:13px; line-height:1.45; }}
  .model-compare b {{ color:#eef2ff; }}
  .regime-stat {{ display:grid; grid-template-columns:repeat(4,minmax(130px,1fr)); gap:10px; margin-bottom:10px; }}
  .regime-stat .kpi {{ padding:10px; }}
  @media (max-width:1000px) {{ .kpis,.grid2,.grid-map {{ grid-template-columns:1fr; }} }}
  @media (max-width:1000px) {{ .arch-compare,.model-figure,.model-compare {{ grid-template-columns:1fr; }} .model-arrow {{ display:none; }} }}
</style>
</head>
<body>
<div class="wrap">
  <h1>HERALD France - Comparaison modèles</h1>
  <div class="subtitle">
    HERALD flags, HERALD no flags, références classiques, carte par zone, secteurs A10 et régime appris.
  </div>

  <div class="kpis">
    <div class="kpi"><div class="v">{semi_2025:.4f}</div><div class="l">WMAPE 2025 HERALD médian</div></div>
    <div class="kpi"><div class="v">{ridge_2025:.4f}</div><div class="l">WMAPE 2025 Ridge AR</div></div>
    <div class="kpi"><div class="v">{gain:.1f}%</div><div class="l">Gain HERALD vs Ridge en 2025</div></div>
    <div class="kpi"><div class="v">{winner['n']}</div><div class="l">Seeds du protocole principal</div></div>
  </div>

  <div class="section">
    <div class="section-title">Protocole</div>
    <div class="section-note">
      Chaque année est testée comme une vraie année future: HERALD est entraîné uniquement avec les années
      antérieures au fold. Ce tableau rend visible les années qui entrent dans l'entraînement et l'année
      qui sert de comparaison au réel.
    </div>
    <div class="card">{fold_table_html}</div>
  </div>

  <div class="section">
    <div class="section-title">0. Architecture HERALD</div>
    <div class="section-note">
      À partir des <b>données publiques INSEE</b> sur les créations d'établissements, HERALD prédit combien
      d'entreprises vont être créées dans chaque territoire l'année suivante — sans connaître l'avenir.
      HERALD prédit les créations d'établissements par zone d'emploi et secteur, sans connaître l'avenir.
      Il apprend comment les territoires s'influencent mutuellement, quelle importance donner à la
      dynamique propre de chaque zone versus l'influence des voisins, et comment les flux de mobilité
      pendulaire structurent l'espace économique — le tout calibré sur l'historique des créations INSEE.
    </div>
    <div class="kpis" style="grid-template-columns:repeat(6,minmax(140px,1fr))">
      <div class="kpi"><div class="v">walk-forward</div><div class="l">Fenêtre d'entraînement</div></div>
      <div class="kpi"><div class="v">2021–2025</div><div class="l">Années évaluées</div></div>
      <div class="kpi"><div class="v">280</div><div class="l">Zones d'emploi</div></div>
      <div class="kpi"><div class="v">9 (A10)</div><div class="l">Secteurs économiques</div></div>
      <div class="kpi"><div class="v">10</div><div class="l">Seeds du protocole</div></div>
      <div class="kpi"><div class="v">2</div><div class="l">Entrées annuelles SIDE</div></div>
    </div>
    <div class="card" style="margin-top:8px">

      <!-- Architecture SVG — figure qualité article scientifique, v3 -->
      <svg viewBox="0 0 1020 420" style="width:100%;max-width:1020px;display:block;margin:12px auto 4px;font-family:Inter,Arial,sans-serif" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <marker id="ah"  viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10z" fill="#9aa4bf"/></marker>
          <marker id="ahb" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10z" fill="#4aa3ff"/></marker>
          <marker id="ahg" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10z" fill="#66bb6a"/></marker>
          <marker id="aho" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10z" fill="#f7834f"/></marker>
        </defs>

        <!-- ── HERALD bounding box ─────────────────────────────────────────── -->
        <rect x="188" y="10" width="640" height="380" rx="12" fill="none" stroke="#2a3050" stroke-dasharray="6,4" stroke-width="1.5"/>
        <text x="508" y="27" text-anchor="middle" fill="#9aa4bf" font-size="9.5" font-weight="700" letter-spacing="2">MODÈLE HERALD</text>

        <!-- ══════════════════════════ INPUT ══════════════════════════════ -->
        <!-- box: x=4 y=75 w=170 h=250, bottom=325, center-y=200 -->
        <rect x="4" y="75" width="170" height="250" rx="10" fill="#111525" stroke="#4aa3ff" stroke-width="1.5"/>
        <text x="89" y="97"  text-anchor="middle" fill="#4aa3ff" font-size="9"   font-weight="700" letter-spacing="1.2">DONNÉES INSEE</text>
        <text x="89" y="117" text-anchor="middle" fill="#eef2ff" font-size="14"  font-weight="700">Registre SIDE</text>
        <line x1="18" y1="126" x2="160" y2="126" stroke="#2a3050" stroke-width="1"/>

        <!-- signal 1: y=138 to y=196 -->
        <rect x="16" y="138" width="142" height="58" rx="6" fill="#141830" stroke="#4aa3ff28" stroke-width="1"/>
        <text x="87" y="156" text-anchor="middle" fill="#4aa3ff" font-size="9.5" font-weight="700">&#x2460;  Niveau récent</text>
        <text x="87" y="173" text-anchor="middle" fill="#9aa4bf" font-size="9">Combien d'entreprises ont été</text>
        <text x="87" y="187" text-anchor="middle" fill="#9aa4bf" font-size="9">créées ici l'an dernier ?</text>

        <!-- signal 2: y=204 to y=262 -->
        <rect x="16" y="204" width="142" height="58" rx="6" fill="#141830" stroke="#4aa3ff28" stroke-width="1"/>
        <text x="87" y="222" text-anchor="middle" fill="#4aa3ff" font-size="9.5" font-weight="700">&#x2461;  Tendance</text>
        <text x="87" y="239" text-anchor="middle" fill="#9aa4bf" font-size="9">Ce territoire accélère-t-il</text>
        <text x="87" y="253" text-anchor="middle" fill="#9aa4bf" font-size="9">ou ralentit-il ?</text>

        <text x="89" y="311" text-anchor="middle" fill="#9aa4bf" font-size="8">2 variables · 280 zones · millésime INSEE</text>

        <!-- input → Ridge -->
        <path d="M174 135 Q187 110 197 80" stroke="#4aa3ff" stroke-width="1.5" fill="none" marker-end="url(#ahb)"/>
        <!-- input → GNN -->
        <path d="M174 230 L197 235" stroke="#4aa3ff" stroke-width="1.5" fill="none" marker-end="url(#ahb)"/>

        <!-- ══════════════════════════ RIDGE AR ═══════════════════════════ -->
        <!-- box: x=200 y=30 w=215 h=128, bottom=158, center-y=94, right=415 -->
        <rect x="200" y="30" width="215" height="128" rx="10" fill="#111525" stroke="#66bb6a" stroke-width="1.5"/>
        <text x="307" y="52"  text-anchor="middle" fill="#66bb6a" font-size="9"  font-weight="700" letter-spacing="1.2">BASELINE LINÉAIRE</text>
        <text x="307" y="75"  text-anchor="middle" fill="#eef2ff" font-size="16" font-weight="700">Ridge AR</text>
        <line x1="214" y1="84" x2="401" y2="84" stroke="#2a3050" stroke-width="1"/>
        <text x="307" y="104" text-anchor="middle" fill="#9aa4bf" font-size="10" font-style="italic">ŷ_ridge = β · x_t</text>
        <text x="307" y="122" text-anchor="middle" fill="#9aa4bf" font-size="9">Régression pénalisée (L2)</text>
        <text x="307" y="137" text-anchor="middle" fill="#9aa4bf" font-size="9">sur les 2 signaux annuels SIDE</text>

        <!-- Ridge arc → combiner. Ridge right=(415,94). Combiner=(700,225). -->
        <!-- Arc stays above GNN top (y=175), control point at (580,44) -->
        <path d="M415 94 Q580 44 680 202" stroke="#66bb6a" stroke-width="1.5" stroke-dasharray="5,3" fill="none" marker-end="url(#ahg)"/>
        <!-- Label at arc midpoint, clear of HERALD label (y=27) -->
        <text x="560" y="58" fill="#66bb6a" font-size="9.5" text-anchor="middle" font-style="italic">ŷ_ridge</text>

        <!-- ══════════════════════════ GNN GROUP ══════════════════════════ -->
        <!-- box: x=200 y=178 w=455 h=200, bottom=378, center-y=278, right=655 -->
        <rect x="200" y="178" width="455" height="200" rx="10" fill="#111525" stroke="#f7834f" stroke-width="1.5"/>
        <text x="427" y="199" text-anchor="middle" fill="#f7834f" font-size="9" font-weight="700" letter-spacing="1.2">RÉSEAU DE NEURONES SPATIO-TEMPOREL</text>
        <line x1="214" y1="209" x2="641" y2="209" stroke="#2a3050" stroke-width="1"/>

        <!-- Left sub-box (local): x=214 y=219 w=185 h=145, right=399, center-x=306, center-y=291 -->
        <rect x="214" y="219" width="185" height="145" rx="8" fill="#171b2d" stroke="#2d3352" stroke-width="1"/>
        <text x="306" y="238" text-anchor="middle" fill="#9aa4bf" font-size="8.5" font-weight="700" letter-spacing=".8">DYNAMIQUE LOCALE</text>
        <text x="306" y="268" text-anchor="middle" fill="#eef2ff" font-size="20" font-weight="700" font-style="italic">α · e_t</text>
        <text x="306" y="291" text-anchor="middle" fill="#9aa4bf" font-size="8.5">Profil intrinsèque de la zone</text>
        <text x="306" y="306" text-anchor="middle" fill="#9aa4bf" font-size="8.5">embedding appris par le modèle</text>
        <text x="306" y="323" text-anchor="middle" fill="#b084f5" font-size="8"  font-style="italic">α ∈ [0,1] — appris par zone et par an</text>
        <text x="306" y="338" text-anchor="middle" fill="#b084f5" font-size="8"  font-style="italic">modulé par le régime temporel z_t</text>

        <!-- Plus circle: clear of both sub-boxes. left sub ends at x=399, right sub starts at x=445 -->
        <!-- cx=422, r=18 → x=404..440. Gap to left box: 5px. Gap to right box: 5px. -->
        <circle cx="422" cy="291" r="18" fill="#141830" stroke="#f7834f" stroke-width="1.5"/>
        <text x="422" y="297" text-anchor="middle" fill="#f7834f" font-size="21" font-weight="800">+</text>

        <!-- arrows into + circle (clear of boxes) -->
        <line x1="399" y1="291" x2="404" y2="291" stroke="#f7834f" stroke-width="1.4" marker-end="url(#aho)"/>
        <line x1="445" y1="291" x2="440" y2="291" stroke="#f7834f" stroke-width="1.4" marker-end="url(#aho)"/>

        <!-- Right sub-box (graph): x=445 y=219 w=200 h=145, right=645, center-x=545, center-y=291 -->
        <rect x="445" y="219" width="200" height="145" rx="8" fill="#171b2d" stroke="#2d3352" stroke-width="1"/>
        <text x="545" y="238" text-anchor="middle" fill="#9aa4bf" font-size="8.5" font-weight="700" letter-spacing=".8">INFLUENCE TERRITORIALE</text>
        <text x="545" y="267" text-anchor="middle" fill="#eef2ff" font-size="17" font-weight="700" font-style="italic">(1-α) · m_t</text>
        <text x="545" y="291" text-anchor="middle" fill="#9aa4bf" font-size="8.5">Agrégation des zones voisines</text>
        <text x="545" y="308" text-anchor="middle" fill="#9aa4bf" font-size="8"  font-style="italic">γ_mob · A_mob + γ_geo · A_geo</text>
        <text x="545" y="325" text-anchor="middle" fill="#9aa4bf" font-size="8">Graphe interne : mobilité pendulaire</text>
        <text x="545" y="340" text-anchor="middle" fill="#9aa4bf" font-size="8">et contiguïté géographique</text>
        <text x="545" y="356" text-anchor="middle" fill="#9aa4bf" font-size="7.5" font-style="italic">(non fourni par l'utilisateur)</text>

        <!-- GNN → combiner. + circle bottom at (422,309). Combiner at (700,225). -->
        <!-- Short path: from bottom of + down, then right and up to combiner left edge -->
        <!-- Goes via (422,370) then (680,370) then up to (680,225) - stays inside HERALD box -->
        <path d="M422 309 Q422 372 560 372 Q672 372 678 248" stroke="#f7834f" stroke-width="1.4" fill="none" marker-end="url(#aho)"/>
        <!-- Label along this path, clear of other elements, at y=382 (inside viewBox=420) -->
        <text x="500" y="387" fill="#f7834f" font-size="8.5" text-anchor="middle" font-style="italic">résidu neural  ε = f(x_t, A_mob, A_geo)</text>

        <!-- ══════════════════════════ COMBINER ⊕ ═════════════════════════ -->
        <!-- cx=700, cy=225, r=24. left=676, right=724, top=201, bottom=249 -->
        <circle cx="700" cy="225" r="24" fill="#111525" stroke="#9aa4bf" stroke-width="1.5"/>
        <text x="700" y="232" text-anchor="middle" fill="#eef2ff" font-size="22" font-weight="800">&#8853;</text>
        <text x="700" y="264" text-anchor="middle" fill="#9aa4bf" font-size="8.5" font-style="italic">ŷ_z = ŷ_ridge + ε · σ_z</text>

        <!-- combiner → output box (combiner right=724, output left=772) -->
        <path d="M724 225 L772 205" stroke="#9aa4bf" stroke-width="1.4" fill="none" marker-end="url(#ah)"/>

        <!-- ══════════════════════════ OUTPUTS ════════════════════════════ -->
        <!-- box: x=774 y=30 w=200 h=358, bottom=388 -->
        <rect x="774" y="30" width="200" height="358" rx="10" fill="#111525" stroke="#26a69a" stroke-width="1.5"/>
        <text x="874" y="52"  text-anchor="middle" fill="#26a69a" font-size="9" font-weight="700" letter-spacing="1.5">PRÉVISIONS</text>
        <line x1="786" y1="61" x2="962" y2="61" stroke="#2a3050" stroke-width="1"/>

        <!-- output 1: total. y=70 to y=200 -->
        <rect x="786" y="70" width="176" height="128" rx="7" fill="#171b2d" stroke="#26a69a33" stroke-width="1"/>
        <text x="874" y="91"  text-anchor="middle" fill="#26a69a" font-size="8.5" font-weight="700" letter-spacing=".8">PAR ZONE D'EMPLOI</text>
        <text x="874" y="120" text-anchor="middle" fill="#eef2ff" font-size="18" font-weight="700" font-style="italic">ŷ_z,t</text>
        <text x="874" y="143" text-anchor="middle" fill="#9aa4bf" font-size="8.5">Créations prévues par zone</text>
        <text x="874" y="158" text-anchor="middle" fill="#9aa4bf" font-size="8.5">280 zones d'emploi · 2021–2025</text>
        <text x="874" y="177" text-anchor="middle" fill="#26a69a" font-size="9.5" font-weight="700">WMAPE moyen : 0.021</text>
        <text x="874" y="193" text-anchor="middle" fill="#9aa4bf" font-size="8">(vs Ridge AR : 0.061)</text>

        <!-- output 2: sectors. y=212 to y=376 -->
        <rect x="786" y="212" width="176" height="162" rx="7" fill="#171b2d" stroke="#26a69a33" stroke-width="1"/>
        <text x="874" y="232"  text-anchor="middle" fill="#26a69a"  font-size="8.5" font-weight="700" letter-spacing=".8">DÉCOMPOSITION SECTORIELLE</text>
        <text x="874" y="259"  text-anchor="middle" fill="#eef2ff"  font-size="17"  font-weight="700" font-style="italic">ŷ_z,t,s</text>
        <text x="874" y="281"  text-anchor="middle" fill="#9aa4bf"  font-size="8.5">9 secteurs A10</text>
        <line x1="796" y1="287" x2="954" y2="287" stroke="#2a3050" stroke-width="0.8"/>
        <text x="874" y="302" text-anchor="middle" fill="#9aa4bf" font-size="8">Industrie · Construction</text>
        <text x="874" y="316" text-anchor="middle" fill="#9aa4bf" font-size="8">Commerce · Finance · Services</text>
        <text x="874" y="330" text-anchor="middle" fill="#9aa4bf" font-size="8">Immobilier · Information · Arts</text>
        <line x1="796" y1="338" x2="954" y2="338" stroke="#2a3050" stroke-width="0.8"/>
        <text x="874" y="353" text-anchor="middle" fill="#9aa4bf" font-size="7.5">Incertitude entre seeds (n=10)</text>
        <text x="874" y="367" text-anchor="middle" fill="#9aa4bf" font-size="7.5">Carte d'erreur par territoire</text>

        <!-- Figure caption — inside viewBox (height=420), y=407 -->
        <text x="508" y="407" text-anchor="middle" fill="#6a7490" font-size="7.8" font-style="italic">Figure 1. x_t ∈ R&#178; : signaux SIDE annuels (INSEE). A_mob, A_geo : graphes internes (mobilité + contiguïté). α_z,t ∈ [0,1] : arbitrage local/graphe appris. z_t : régime latent ou flags manuels. σ_z : écart-type de zone.</text>
      </svg>


    </div>
  </div>

  <div class="section">
    <div class="section-title">1. Comparaison</div>
    <div class="section-note">
      Ce bloc répond à la question centrale: HERALD tient-il face aux références classiques et aux modèles
      spatio-temporels utilisés comme points de comparaison. La barre 2025 est séparée de la moyenne pour
      éviter de cacher le comportement opérationnel récent.
    </div>
    <div class="grid2">
      <div class="card"><div id="chart-model-2025" style="height:360px"></div></div>
      <div class="card"><div id="chart-model-mean" style="height:360px"></div></div>
    </div>
  </div>

  <div class="section">
    <div class="section-title">2. Erreur par année</div>
    <div class="section-note">
      HERALD est évalué année par année pour éviter une conclusion fondée seulement sur une moyenne.
      Cette courbe compare HERALD flags, HERALD no flags et les modèles de référence.
    </div>
    <div class="card"><div id="chart-year-lines" style="height:390px"></div></div>
  </div>

  <div class="section">
    <div class="section-title">3. Réel vs prédit - France entière</div>
    <div class="section-note">
      HERALD est comparé directement au réel et aux deux références les plus fortes (Ridge AR et DCRNN).
      Le graphique de gauche montre les volumes absolus: une bonne WMAPE doit s'accompagner d'un alignement réel en niveau.
      L'erreur absolue (établissements) est affichée dans le survol pour chaque année.
      Le graphique de droite montre la dispersion entre seeds — une boîte étroite indique un modèle stable.
    </div>
    <div class="grid2">
      <div class="card"><div id="chart-france-real-pred" style="height:380px"></div></div>
      <div class="card"><div id="chart-seed-dist" style="height:380px"></div></div>
    </div>
  </div>

  <div class="section">
    <div class="section-title">4. Secteurs A10</div>
    <div class="section-note">
      Comparaison directe entre le réel, HERALD flags et HERALD no flags. Le but est de voir si la
      version sans flags garde aussi le signal sectoriel A10.
    </div>
    <div class="controls" style="margin-bottom:8px">
      <label>Année secteurs <select id="sector-year" onchange="drawSectorCharts()">
        {sector_year_options}
      </select></label>
    </div>
    <div class="card"><div id="chart-sector-volume" style="height:430px"></div></div>
  </div>

  <div class="section">
    <div class="section-title">5. Carte territoriale</div>
    <div class="section-note">
      Carte centrée sur les résultats déjà complets: erreur HERALD, volume réel, graphe et A10 au clic.
      La couche Intelligence sera relancée séparément avant d'être réintégrée ici.
    </div>
    <div class="grid-map">
      <div class="card">
        <div class="controls">
          <label>Métrique <select id="map-metric" onchange="drawMap()">
            <option value="semi_error">Erreur HERALD (WMAPE)</option>
            <option value="abs_error">Erreur absolue (établissements)</option>
            <option value="real_volume">Volume réel</option>
          </select></label>
          <label>Année <select id="map-year" onchange="handleMapYearSelect()"></select></label>
          <label style="display:flex;align-items:center;gap:6px">
            Animation <input type="range" id="map-year-slider" min="0" max="4" value="4"
              oninput="handleMapYearSlider()" style="width:120px;vertical-align:middle">
          </label>
          <button type="button" onclick="toggleMapAnimation()" id="map-play"
            style="background:#20253a;color:#eef2ff;border:1px solid #30364f;border-radius:6px;padding:7px 10px;cursor:pointer">
            ▶ Lecture
          </button>
          <label style="display:flex;align-items:center;gap:6px">
            Vitesse <select id="map-speed" onchange="restartMapAnimationIfNeeded()">
              <option value="1800">lente</option>
              <option value="1100" selected>normale</option>
              <option value="650">rapide</option>
            </select>
          </label>
          <label style="display:flex;align-items:center;gap:6px;cursor:pointer">
            <input type="checkbox" id="show-graph" onchange="drawMap()" style="width:16px;height:16px">
            Afficher le graphe
          </label>
          <label id="graph-mode-label" style="display:none">Mode graphe <select id="graph-mode" onchange="drawMap()">
            <option value="salient">Appris — top connexions lisibles</option>
            <option value="total">Total — densité des connexions</option>
          </select></label>
          <label id="graph-opacity-label" style="display:none">
            Opacité graphe <input type="range" id="graph-opacity" min="20" max="100" value="78"
              oninput="drawMap()" style="width:80px;vertical-align:middle">
          </label>
        </div>
        <div id="chart-map" style="height:590px"></div>
      </div>
      <div class="card">
        <div id="zone-title" class="section-title">Sélectionnez une zone</div>
        <div class="mini">Évolution réelle vs HERALD flags vs HERALD no flags 2021–2025 + secteurs A10 + connexions du graphe.</div>
        <div id="chart-zone-time" style="height:260px"></div>
        <div id="chart-zone-sector" style="height:260px"></div>
        <div id="zone-connections" class="mini" style="margin-top:10px"></div>
      </div>
    </div>
  </div>

  <div class="section">
    <div class="section-title">6. Régimes appris sans flags</div>
    <div class="section-note">
      Cette section montre ce que le modèle change en interne lorsqu'il ne reçoit aucune flag crise/rebond.
      Les courbes sont les dimensions du régime latent; les barres indiquent l'ampleur de changement entre deux années.
    </div>
    <div class="grid2">
      <div class="card"><div id="chart-regime-latent" style="height:360px"></div></div>
      <div class="card">
        <div id="regime-summary"></div>
        <div id="chart-regime-step" style="height:260px"></div>
      </div>
    </div>
  </div>

</div>

<script>
const DATA = {js(payload)};
const COLORS = {{
  semi:"#f7834f", masked:"#ffb074", control:"#4aa3ff", history:"#b084f5", nfclean:"#64b5f6",
  ridge:"#66bb6a", arima:"#26a69a", lstm:"#ffd54f", dcrnn:"#ec407a", stgnn:"#ab47bc",
  real:"#e0e4f0", bad:"#ef5350", good:"#26a69a"
}};
const BASE_LAYOUT = {{
  paper_bgcolor:"#171b2d", plot_bgcolor:"#171b2d", font:{{color:"#eef2ff"}},
  margin:{{t:48,b:48,l:58,r:24}}, hoverlabel:{{bgcolor:"#111525"}}
}};
let MAP_ANIMATION_TIMER = null;
let CURRENT_ZONE = null;

function model(label) {{ return DATA.models.find(m => m.label === label); }}
function heraldModel() {{ return DATA.models.find(m => String(m.label).startsWith("HERALD")) || DATA.models[0]; }}
function fmt(x, d=4) {{ return x === null || x === undefined || Number.isNaN(x) ? "n/a" : Number(x).toFixed(d); }}
function zeName(ze) {{ return (DATA.zeNames && DATA.zeNames[ze]) ? DATA.zeNames[ze] : ze; }}
function pct(x) {{ return x === null || x === undefined ? "n/a" : (100*x).toFixed(2)+"%"; }}
function colorFor(label) {{
  if(String(label).includes("no flags clean")) return COLORS.nfclean;
  if(String(label).includes("no flags")) return COLORS.semi;
  if(String(label).includes("flags étendu")) return COLORS.masked;
  if(String(label).includes("flags clean")) return COLORS.history;
  if(String(label).includes("HERALD flags")) return COLORS.history;
  if(label.includes("Contrôle")) return COLORS.control;
  if(label.includes("Ridge")) return COLORS.ridge;
  if(label.includes("ARIMA")) return COLORS.arima;
  if(label.includes("LSTM")) return COLORS.lstm;
  if(label.includes("DCRNN")) return COLORS.dcrnn;
  return COLORS.stgnn;
}}

function comparisonRows(metric) {{
  const rows = DATA.models.map(m => [m.label, metric === "2025" ? m.wmape_2025_median : m.mean, m.n]);
  const avg = obj => {{
    const vals = DATA.years.map(y => obj[y]).filter(v => v !== null && v !== undefined);
    return vals.length ? vals.reduce((a,b)=>a+b,0)/vals.length : null;
  }};
  if(metric === "2025") {{
    if(DATA.ridgeYear["2025"] !== undefined) rows.push(["Ridge AR", DATA.ridgeYear["2025"], 1]);
    if(DATA.arimaYear["2025"] !== undefined) rows.push(["ARIMA local", DATA.arimaYear["2025"], 1]);
    if(DATA.lstmYear && DATA.lstmYear["2025"] !== undefined) rows.push(["LSTM local", DATA.lstmYear["2025"], 10]);
    if(DATA.dcrnnYear["2025"] !== undefined) rows.push(["DCRNN", DATA.dcrnnYear["2025"], 10]);
    if(DATA.stgnnYear["2025"] !== undefined) rows.push(["Dynamic STGNN", DATA.stgnnYear["2025"], 10]);
  }} else {{
    rows.push(["Ridge AR", avg(DATA.ridgeYear), 1]);
    rows.push(["ARIMA local", avg(DATA.arimaYear), 1]);
    if(DATA.lstmYear && Object.keys(DATA.lstmYear).length) rows.push(["LSTM local", avg(DATA.lstmYear), 10]);
    rows.push(["DCRNN", avg(DATA.dcrnnYear), 10]);
    rows.push(["Dynamic STGNN", avg(DATA.stgnnYear), 10]);
  }}
  return rows.filter(r => r[1] !== null && r[1] !== undefined).sort((a,b) => b[1]-a[1]);
}}

function drawModelBars() {{
  [["chart-model-2025","2025","WMAPE 2025"],["chart-model-mean","mean","WMAPE moyen 2021-2025"]].forEach(cfg => {{
    const rows = comparisonRows(cfg[1]);
    Plotly.newPlot(cfg[0], [{{
      type:"bar", orientation:"h", y:rows.map(r=>r[0]), x:rows.map(r=>r[1]),
      marker:{{color:rows.map(r=>colorFor(r[0]))}},
      text:rows.map(r=>fmt(r[1])), textposition:"auto",
      hovertemplate:"%{{y}}<br>"+cfg[2]+": %{{x:.4f}}<extra></extra>"
    }}], Object.assign({{}}, BASE_LAYOUT, {{
      title:cfg[2]+" - plus bas = meilleur",
      xaxis:{{title:"WMAPE", gridcolor:"#30364f"}},
      yaxis:{{automargin:true}},
    }}), {{responsive:true}});
  }});
}}

function drawYearLines() {{
  const traces = [];
  DATA.models.forEach(m => {{
    const yvals = DATA.years.map(y=>m.per_year[y] ?? null);
    traces.push({{type:"scatter", mode:"lines+markers", x:DATA.years,
      y:yvals, name:m.label,
      line:{{color:colorFor(m.label), width:String(m.label).startsWith("HERALD") ? 4 : 2}},
      hovertemplate:"%{{x}}<br>%{{fullData.name}}: %{{y:.4f}}<extra></extra>"}});
  }});
  traces.push({{type:"scatter", mode:"lines+markers", x:DATA.years, y:DATA.years.map(y=>DATA.ridgeYear[y] ?? null),
    name:"Ridge AR", line:{{color:COLORS.ridge, width:2, dash:"dash"}}}});
  traces.push({{type:"scatter", mode:"lines+markers", x:DATA.years, y:DATA.years.map(y=>DATA.arimaYear[y] ?? null),
    name:"ARIMA local", line:{{color:COLORS.arima, width:2, dash:"dot"}}}});
  if(DATA.lstmYear && Object.keys(DATA.lstmYear).length)
    traces.push({{type:"scatter", mode:"lines+markers", x:DATA.years, y:DATA.years.map(y=>DATA.lstmYear[y]||null),
      name:"LSTM local", line:{{color:COLORS.lstm, width:2, dash:"dashdot"}}}});
  traces.push({{type:"scatter", mode:"lines+markers", x:DATA.years, y:DATA.years.map(y=>DATA.dcrnnYear[y]||null),
    name:"DCRNN", line:{{color:COLORS.dcrnn, width:2, dash:"dash"}}}});
  traces.push({{type:"scatter", mode:"lines+markers", x:DATA.years, y:DATA.years.map(y=>DATA.stgnnYear[y]||null),
    name:"Dynamic STGNN", line:{{color:COLORS.stgnn, width:2, dash:"dot"}}}});
  Plotly.newPlot("chart-year-lines", traces, Object.assign({{}}, BASE_LAYOUT, {{
    title:"WMAPE par année", yaxis:{{title:"WMAPE", gridcolor:"#30364f"}}, xaxis:{{title:"Année", gridcolor:"#30364f"}},
    legend:{{orientation:"h", y:-0.25}}
  }}), {{responsive:true}});
}}

function drawFranceAndSeeds() {{
  const years = DATA.years;
  const realVals = years.map(y=>(DATA.franceTotal[y]||{{}}).y_true||null);
  const heraldVals = years.map(y=>(DATA.franceTotal[y]||{{}}).y_pred||null);
  const nfCleanVals = years.map(y=>(DATA.nfCleanFranceTotal[y]||{{}}).y_pred||null);
  const cleanFlagsVals = years.map(y=>(DATA.cleanFlagsFranceTotal[y]||{{}}).y_pred||null);
  const dirtyFlagsVals = years.map(y=>((DATA.historicalControl && DATA.dirtyFlagsFranceTotal[y])||{{}}).y_pred||null);
  const heraldText = years.map(y => {{
    const ft = DATA.franceTotal[y];
    if(!ft) return y;
    const err = ft.abs_error || Math.abs((ft.y_pred||0)-(ft.y_true||0));
    return y+"<br>Réel: "+ft.y_true+"<br>HERALD no flags Q7: "+ft.y_pred+"<br>Erreur abs: "+err+" étab.";
  }});
  Plotly.newPlot("chart-france-real-pred", [
    {{type:"scatter", mode:"lines+markers", x:years, y:realVals,
      name:"Réel INSEE", line:{{color:COLORS.real,width:3}},
      hovertemplate:"%{{x}}<br>Réel: %{{y:,}}<extra></extra>"}},
    {{type:"scatter", mode:"lines+markers", x:years, y:heraldVals,
      name:"HERALD no flags Q7", line:{{color:COLORS.semi,width:3}},
      text:heraldText, hovertemplate:"%{{text}}<extra></extra>"}},
    {{type:"scatter", mode:"lines+markers", x:years, y:nfCleanVals,
      name:"HERALD no flags clean", line:{{color:COLORS.nfclean,width:2.5,dash:"dot"}},
      hovertemplate:"%{{x}}<br>HERALD no flags clean: %{{y:,}}<extra></extra>"}},
    {{type:"scatter", mode:"lines+markers", x:years, y:cleanFlagsVals,
      name:"HERALD flags clean", line:{{color:COLORS.history,width:2.5,dash:"dash"}},
      hovertemplate:"%{{x}}<br>HERALD flags clean: %{{y:,}}<extra></extra>"}},
    {{type:"scatter", mode:"lines+markers", x:years, y:dirtyFlagsVals,
      name:"HERALD flags étendu (contrôle historique)", line:{{color:COLORS.masked,width:1.5,dash:"dash"}},
      visible:"legendonly",
      hovertemplate:"%{{x}}<br>HERALD flags étendu: %{{y:,}}<extra></extra>"}},
  ], Object.assign({{}}, BASE_LAYOUT, {{
    title:"Volumes France entière: réel vs HERALD",
    yaxis:{{title:"Créations d'établissements", gridcolor:"#30364f", tickformat:","}},
    xaxis:{{title:"Année", gridcolor:"#30364f"}},
    legend:{{orientation:"h",y:-0.22}}
  }}), {{responsive:true}});

  const seedTraces = DATA.models.filter(m=>m.seed_2025 && m.seed_2025.length).map(m => ({{
    type:"box", y:m.seed_2025, name:m.label, marker:{{color:colorFor(m.label)}}, boxmean:true
  }}));
  Plotly.newPlot("chart-seed-dist", seedTraces, Object.assign({{}}, BASE_LAYOUT, {{
    title:"Distribution par seed - WMAPE 2025",
    yaxis:{{title:"WMAPE 2025", gridcolor:"#30364f"}}
  }}), {{responsive:true}});
}}

function drawSectorCharts() {{
  const yearSel = document.getElementById("sector-year");
  const yr = yearSel ? yearSel.value : "2025";

  // Volume: Réel vs HERALD for the selected observed year.
  const st = DATA.sectorTotalsByYear ? DATA.sectorTotalsByYear[yr] : null;
  const snfc = DATA.nfCleanSectorTotalsByYear ? DATA.nfCleanSectorTotalsByYear[yr] : null;
  const scf = DATA.cleanFlagsSectorTotalsByYear ? DATA.cleanFlagsSectorTotalsByYear[yr] : null;
  if(st && st.sectors) {{
    const labels = st.sectors.map(s => s+" — "+DATA.sectorLabels[s]);
    // For WMAPE hover: show absolute error
    const absErr = st.sectors.map((s,i) => Math.abs((st.y_pred[i]||0)-(st.y_true[i]||0)));
    const wmapePerSec = st.sectors.map((s,i) => st.y_true[i] ? (absErr[i]/st.y_true[i]*100).toFixed(1)+"%" : "n/a");
    Plotly.newPlot("chart-sector-volume", [
      {{type:"bar", x:labels, y:st.y_true, name:"Réel INSEE",
        marker:{{color:COLORS.real, opacity:0.75}},
        hovertemplate:"%{{x}}<br>Réel: %{{y:,}}<extra></extra>"}},
      {{type:"bar", x:labels, y:snfc && snfc.y_pred ? snfc.y_pred : st.sectors.map(_=>null), name:"HERALD no flags clean",
        marker:{{color:COLORS.nfclean, opacity:0.8}},
        hovertemplate:"%{{x}}<br>HERALD no flags clean: %{{y:,}}<extra></extra>"}},
      {{type:"bar", x:labels, y:scf && scf.y_pred ? scf.y_pred : st.sectors.map(_=>null), name:"HERALD flags clean",
        marker:{{color:COLORS.history, opacity:0.8}},
        hovertemplate:"%{{x}}<br>HERALD flags clean: %{{y:,}}<extra></extra>"}},
      {{type:"bar", x:labels, y:st.y_pred, name:"HERALD no flags Q7",
        marker:{{color:COLORS.semi, opacity:0.85}},
        customdata:wmapePerSec,
        hovertemplate:"%{{x}}<br>HERALD no flags: %{{y:,}}<br>WMAPE: %{{customdata}}<extra></extra>"}}
    ], Object.assign({{}}, BASE_LAYOUT, {{
      title:"Volumes A10 "+yr+": réel vs HERALD",
      barmode:"group",
      xaxis:{{tickangle:-30, automargin:true}},
      yaxis:{{title:"Établissements", gridcolor:"#30364f", tickformat:","}}
    }}), {{responsive:true}});
  }}
}}

function mapValue(metric, year, ze) {{
  if(metric === "semi_error") return DATA.zoneSemiError[year] ? DATA.zoneSemiError[year][ze] : null;
  if(metric === "real_volume") return DATA.zoneSemiReal[year] ? DATA.zoneSemiReal[year][ze] : null;
  if(metric === "abs_error") return DATA.zoneSemiAbs[year] ? DATA.zoneSemiAbs[year][ze] : null;
  return null;
}}

function mapColorScale(metric) {{
  if(metric === "real_volume") return [[0,"#0f1220"],[0.4,"#1a3a5c"],[0.7,"#2e6da4"],[1,"#74b9ff"]];
  return [[0,"#1a3a2a"],[0.35,"#26a69a"],[0.7,"#ffd54f"],[1,"#ef5350"]];
}}

function mapColorbarTitle(metric) {{
  if(metric === "real_volume") return "Volume";
  if(metric === "abs_error") return "Erreur abs.";
  return "WMAPE";
}}

function drawMap() {{
  const metric = document.getElementById("map-metric").value;
  const year = document.getElementById("map-year").value;
  const showGraph = document.getElementById("show-graph") && document.getElementById("show-graph").checked;
  const graphMode = document.getElementById("graph-mode") ? document.getElementById("graph-mode").value : "salient";
  const opacityEl = document.getElementById("graph-opacity");
  const opacity = opacityEl ? parseInt(opacityEl.value)/100 : 0.4;
  const opLabel = document.getElementById("graph-opacity-label");
  if(opLabel) opLabel.style.display = showGraph ? "flex" : "none";
  const modeLabel = document.getElementById("graph-mode-label");
  if(modeLabel) modeLabel.style.display = showGraph ? "flex" : "none";
  if(!DATA.geojson) return;

  const locs = [], vals = [], texts = [];
  DATA.geojson.features.forEach(f => {{
    const ze = String((f.properties && (f.properties.ze2020 || f.properties.ZE2020)) || f.id).padStart(4,"0");
    const val = mapValue(metric, year, ze);
    locs.push(ze); vals.push(val);
    const pred = DATA.zoneSemiPreds[year] ? DATA.zoneSemiPreds[year][ze] : null;
    let base = "<b>"+zeName(ze)+"</b><br>ZE "+ze+"<br>";
    if(pred) {{
      const wmape = val !== null && metric==="semi_error" ? " (WMAPE: "+pct(val)+")" : "";
      base += "Réel: "+(pred.y_true||"?")+"<br>HERALD no flags: "+(pred.y_pred||"?")+"<br>Erreur abs.: "+(pred.abs_error||"?")+" étab."+wmape+"<br>";
    }}
    if(metric==="abs_error") base += "Erreur abs.: "+fmt(val,0)+" étab.";
    else if(metric!=="real_volume") base += "WMAPE: "+pct(val);
    texts.push(base);
  }});

  const colorscale = mapColorScale(metric);

  const traces = [{{
    type:"choropleth", geojson:DATA.geojson, locations:locs, z:vals,
    featureidkey:"properties.ze2020", text:texts, hovertemplate:"%{{text}}<extra></extra>",
    colorscale:colorscale, marker:{{line:{{color:"#20253a", width:0.35}}}},
    colorbar:{{title:mapColorbarTitle(metric), thickness:12}}
  }}];

  // Graph overlay
  if(showGraph) {{
    const raw = DATA.graphData[year] || DATA.graphData[Object.keys(DATA.graphData||{{}}).sort().pop()];
    const gd = raw && Array.isArray(raw) ? raw : raw ? (raw[graphMode] || raw.salient || raw.total) : null;
    if(gd && Array.isArray(gd)) {{
      const edgeLon=[], edgeLat=[], nodeLon=[], nodeLat=[], nodeTxt=[];
      const limit = graphMode === "total" ? 260 : 70;
      gd.slice(0,limit).forEach(e => {{
        edgeLon.push(e.lon0,e.lon1,null); edgeLat.push(e.lat0,e.lat1,null);
        nodeLon.push(e.lon0,e.lon1); nodeLat.push(e.lat0,e.lat1);
        nodeTxt.push(
          (e.name_i||"")+" → "+(e.name_j||"")+"<br>Poids: "+fmt(e.weight,4)+"<br>Variation annuelle: "+fmt(e.delta,4),
          (e.name_j||"")+" ← "+(e.name_i||"")+"<br>Poids: "+fmt(e.weight,4)+"<br>Variation annuelle: "+fmt(e.delta,4)
        );
      }});
      const edgeAlpha = graphMode === "total" ? Math.max(0.58, Math.min(opacity,0.9)) : Math.max(0.72, opacity);
      const edgeColor = graphMode === "total" ? "rgba(0,229,255,"+edgeAlpha+")" : "rgba(255,111,0,"+edgeAlpha+")";
      const nodeColor = graphMode === "total" ? "#00e5ff" : "#ff6f00";
      traces.push({{type:"scattergeo",mode:"lines",lon:edgeLon,lat:edgeLat,
        line:{{color:edgeColor,width:graphMode==="total" ? 1.8 : 2.6}},
        hoverinfo:"skip",name:graphMode==="total"?"Graphe total":"Graphe appris"}});
      traces.push({{type:"scattergeo",mode:"markers",lon:nodeLon,lat:nodeLat,text:nodeTxt,
        hovertemplate:"%{{text}}<extra></extra>",
        marker:{{size:graphMode==="total" ? 4 : 5.8,color:nodeColor,opacity:graphMode==="total" ? 0.9 : 1}},name:"Zones"}});
    }}
  }}

  const mapLayout = {{
    paper_bgcolor:"#171b2d", plot_bgcolor:"#171b2d", font:{{color:"#eef2ff"}},
    geo:{{projection:{{type:"mercator"}},lonaxis:{{range:[-6,10]}},lataxis:{{range:[41,52]}},
      showland:true,landcolor:"#111525",showocean:true,oceancolor:"#0f1220",
      showcountries:true,countrycolor:"#30364f",showframe:false,bgcolor:"#171b2d"}},
    margin:{{t:10,b:10,l:10,r:10}}, showlegend:false
  }};
  Plotly.react("chart-map", traces, mapLayout, {{responsive:true}});
  const el = document.getElementById("chart-map");
  el.removeAllListeners && el.removeAllListeners("plotly_click");
  el.on("plotly_click", ev => {{
    if(ev.points && ev.points[0] && ev.points[0].location)
      drawZone(ev.points[0].location, year);
  }});
}}

function setMapYear(year) {{
  const my = document.getElementById("map-year");
  if(!my) return;
  my.value = String(year);
  const slider = document.getElementById("map-year-slider");
  if(slider) {{
    const idx = DATA.years.indexOf(String(year));
    if(idx >= 0) slider.value = String(idx);
  }}
  drawMap();
}}

function handleMapYearSelect() {{
  const my = document.getElementById("map-year");
  if(my) setMapYear(my.value);
}}

function handleMapYearSlider() {{
  const slider = document.getElementById("map-year-slider");
  if(!slider) return;
  const idx = Math.max(0, Math.min(DATA.years.length - 1, parseInt(slider.value || "0")));
  setMapYear(DATA.years[idx]);
}}

function stepMapYear() {{
  const my = document.getElementById("map-year");
  if(!my) return;
  const idx = DATA.years.indexOf(my.value);
  const next = DATA.years[(idx + 1) % DATA.years.length];
  setMapYear(next);
}}

function toggleMapAnimation() {{
  const btn = document.getElementById("map-play");
  if(MAP_ANIMATION_TIMER) {{
    clearInterval(MAP_ANIMATION_TIMER);
    MAP_ANIMATION_TIMER = null;
    if(btn) btn.textContent = "▶ Lecture";
    return;
  }}
  stepMapYear();
  const speed = parseInt((document.getElementById("map-speed") || {{value:"1100"}}).value);
  MAP_ANIMATION_TIMER = setInterval(stepMapYear, speed);
  if(btn) btn.textContent = "⏸ Pause";
}}

function restartMapAnimationIfNeeded() {{
  if(!MAP_ANIMATION_TIMER) return;
  clearInterval(MAP_ANIMATION_TIMER);
  const speed = parseInt((document.getElementById("map-speed") || {{value:"1100"}}).value);
  MAP_ANIMATION_TIMER = setInterval(stepMapYear, speed);
}}

function drawZone(ze, year) {{
  CURRENT_ZONE = ze;
  const name = zeName(ze);
  document.getElementById("zone-title").textContent = name+" — ZE "+ze;
  const chartYears = DATA.years.slice();
  const real=[], semi=[], nfClean=[], cleanFlags=[], ridge=[], hoverTexts=[];
  chartYears.forEach(y => {{
    const p = DATA.zoneSemiPreds[y] ? DATA.zoneSemiPreds[y][ze] : null;
    const pnfc = DATA.zoneNfCleanPreds && DATA.zoneNfCleanPreds[y] ? DATA.zoneNfCleanPreds[y][ze] : null;
    const pcf = DATA.zoneCleanFlagsPreds[y] ? DATA.zoneCleanFlagsPreds[y][ze] : null;
    const rp = DATA.zoneRidgePreds && DATA.zoneRidgePreds[y] ? DATA.zoneRidgePreds[y][ze] : null;
    real.push(p ? p.y_true : null);
    semi.push(p ? p.y_pred : null);
    nfClean.push(pnfc ? pnfc.y_pred : null);
    cleanFlags.push(pcf ? pcf.y_pred : null);
    ridge.push(rp !== undefined && rp !== null ? rp : null);
    const ae = p ? Math.abs((p.y_pred||0)-(p.y_true||0)) : null;
    hoverTexts.push(y+"<br>Réel: "+(p?p.y_true:"n/a")+"<br>HERALD no flags Q7: "+(p?p.y_pred:"n/a")+"<br>Ridge AR: "+(ridge[ridge.length-1]!==null?fmt(ridge[ridge.length-1],0):"n/a")+"<br>Erreur: "+(ae||"n/a")+" étab.");
  }});
  const traces = [
    {{type:"scatter", mode:"lines+markers", x:chartYears, y:real,
      name:"Réel INSEE", line:{{color:COLORS.real,width:3}},
      hovertemplate:"%{{x}}<br>Réel: %{{y:,}}<extra></extra>"}},
    {{type:"scatter", mode:"lines+markers", x:chartYears, y:semi,
      name:"HERALD no flags Q7", line:{{color:COLORS.semi,width:3}},
      text:hoverTexts, hovertemplate:"%{{text}}<extra></extra>"}},
    {{type:"scatter", mode:"lines+markers", x:chartYears, y:nfClean,
      name:"HERALD no flags clean", line:{{color:COLORS.nfclean,width:2.5,dash:"dot"}},
      hovertemplate:"%{{x}}<br>HERALD no flags clean: %{{y:,}}<extra></extra>"}},
    {{type:"scatter", mode:"lines+markers", x:chartYears, y:cleanFlags,
      name:"HERALD flags clean", line:{{color:COLORS.history,width:2.5,dash:"dash"}},
      hovertemplate:"%{{x}}<br>HERALD flags clean: %{{y:,}}<extra></extra>"}},
    {{type:"scatter", mode:"lines+markers", x:chartYears, y:ridge,
      name:"Ridge AR", line:{{color:COLORS.ridge,width:2.5,dash:"dash"}},
      text:hoverTexts, hovertemplate:"%{{text}}<extra></extra>"}}
  ];
  Plotly.react("chart-zone-time", traces, Object.assign({{}}, BASE_LAYOUT, {{
    title:"Réel vs HERALD vs Ridge — "+name, margin:{{t:36,b:32,l:52,r:12}},
    yaxis:{{title:"Établissements",gridcolor:"#30364f",tickformat:","}},
    xaxis:{{gridcolor:"#30364f"}}, legend:{{orientation:"h",y:-0.3}}
  }}), {{responsive:true}});

  // Sector bars for selected year
  const rows = DATA.zoneSectorPreds[ze] ? DATA.zoneSectorPreds[ze][year] : null;
  const nfCleanRows = DATA.zoneNfCleanSectorPreds && DATA.zoneNfCleanSectorPreds[ze] ? DATA.zoneNfCleanSectorPreds[ze][year] : null;
  const cleanFlagRows = DATA.zoneCleanFlagsSectorPreds[ze] ? DATA.zoneCleanFlagsSectorPreds[ze][year] : null;
  const nfCleanBySector = {{}};
  const cleanFlagBySector = {{}};
  if(nfCleanRows && nfCleanRows.length) nfCleanRows.forEach(r => {{ nfCleanBySector[r.s] = r.p; }});
  if(cleanFlagRows && cleanFlagRows.length) cleanFlagRows.forEach(r => {{ cleanFlagBySector[r.s] = r.p; }});
  if(rows && rows.length) {{
    const sLabels = rows.map(r => r.s+" — "+(DATA.sectorLabels[r.s]||r.s));
    const wmapePerSec = rows.map(r => r.t ? ((Math.abs(r.p-r.t)/r.t)*100).toFixed(1)+"%" : "n/a");
    Plotly.react("chart-zone-sector", [
      {{type:"bar", x:sLabels, y:rows.map(r=>r.t), name:"Réel",
        marker:{{color:COLORS.real,opacity:0.75}},
        hovertemplate:"%{{x}}<br>Réel: %{{y:,}}<extra></extra>"}},
      {{type:"bar", x:sLabels, y:rows.map(r=>nfCleanBySector[r.s] ?? null), name:"HERALD no flags clean",
        marker:{{color:COLORS.nfclean,opacity:0.8}},
        hovertemplate:"%{{x}}<br>HERALD no flags clean: %{{y:,}}<extra></extra>"}},
      {{type:"bar", x:sLabels, y:rows.map(r=>cleanFlagBySector[r.s] ?? null), name:"HERALD flags clean",
        marker:{{color:COLORS.history,opacity:0.8}},
        hovertemplate:"%{{x}}<br>HERALD flags clean: %{{y:,}}<extra></extra>"}},
      {{type:"bar", x:sLabels, y:rows.map(r=>r.p), name:"HERALD no flags Q7",
        customdata:wmapePerSec, marker:{{color:COLORS.semi,opacity:0.85}},
        hovertemplate:"%{{x}}<br>HERALD no flags Q7: %{{y:,}}<br>WMAPE: %{{customdata}}<extra></extra>"}}
    ], Object.assign({{}}, BASE_LAYOUT, {{
      title:"Secteurs A10 — "+year, barmode:"group", margin:{{t:36,b:60,l:52,r:12}},
      xaxis:{{tickangle:-30, automargin:true}},
      yaxis:{{title:"Établissements", gridcolor:"#30364f", tickformat:","}}
    }}), {{responsive:true}});
  }}

  // Show top graph connections for this zone
  const connEl = document.getElementById("zone-connections");
  if(connEl) {{
    const raw = DATA.graphData[year] || DATA.graphData[Object.keys(DATA.graphData||{{}}).sort().pop()] || [];
    const gd = Array.isArray(raw) ? raw : (raw.salient || []);
    const zePad = ze.padStart(4,"0");
    const linked = Array.isArray(gd) ? gd.filter(e =>
      String(e.ze_i||"").padStart(4,"0")===zePad || String(e.ze_j||"").padStart(4,"0")===zePad
    ).slice(0,5) : [];
    if(linked.length) {{
      connEl.innerHTML = "<b>Connexions du graphe ("+year+"):</b><br>" +
        linked.map(e => {{
          const other = String(e.ze_i||"").padStart(4,"0")===zePad ? (e.name_j||e.ze_j) : (e.name_i||e.ze_i);
          const w = fmt(e.weight||e.semi_weight||e.w, 3);
          const d = e.delta !== undefined ? ", variation annuelle: "+fmt(e.delta,3) : "";
          return "→ "+other+" (poids: "+w+d+")";
        }}).join("<br>");
    }} else {{
      connEl.innerHTML = "<span class='muted'>Pas de connexions de graphe disponibles pour "+year+".</span>";
    }}
  }}
}}

function drawMechanisms() {{
  const r = DATA.regimeInternals || {{}};
  const latent = r.latent || {{}};
  const years = Object.keys(latent).sort();
  const dims = [0,1,2];
  const traces = dims.map(i => ({{
    type:"scatter", mode:"lines+markers", x:years,
    y:years.map(y => latent[y] && latent[y][i] !== undefined ? latent[y][i] : null),
    name:"régime "+(i+1),
    line:{{width:3, color:["#f7834f","#4aa3ff","#b084f5"][i]}}
  }}));
  Plotly.newPlot("chart-regime-latent", traces, Object.assign({{}}, BASE_LAYOUT, {{
    title:"État latent appris par année",
    yaxis:{{title:"Valeur latente", gridcolor:"#30364f"}},
    xaxis:{{title:"Année", gridcolor:"#30364f"}},
    legend:{{orientation:"h", y:-0.25}}
  }}), {{responsive:true}});

  const steps = r.latent_step || {{}};
  const stepYears = Object.keys(steps).sort();
  Plotly.newPlot("chart-regime-step", [{{
    type:"bar", x:stepYears, y:stepYears.map(y => steps[y]),
    marker:{{color:stepYears.map(y => y === "2021" ? "#f7834f" : "#4aa3ff")}},
    hovertemplate:"%{{x}}<br>changement latent: %{{y:.3f}}<extra></extra>"
  }}], Object.assign({{}}, BASE_LAYOUT, {{
    title:"Changement du régime latent",
    yaxis:{{title:"distance vs année précédente", gridcolor:"#30364f"}},
    xaxis:{{title:"Année", gridcolor:"#30364f"}}
  }}), {{responsive:true}});

  const ratio = r.gamma_geo ? r.gamma_mob / r.gamma_geo : null;
  const step2021 = steps["2021"];
  const alpha2021 = (r.alpha || {{}})["2021"];
  const alpha2025 = (r.alpha || {{}})["2025"];
  document.getElementById("regime-summary").innerHTML = `
    <div class="regime-stat">
      <div class="kpi"><div class="v">${{fmt(step2021,3)}}</div><div class="l">transition 2020→2021</div></div>
      <div class="kpi"><div class="v">${{fmt(alpha2021,3)}}</div><div class="l">poids local 2021</div></div>
      <div class="kpi"><div class="v">${{fmt(alpha2025,3)}}</div><div class="l">poids local 2025</div></div>
      <div class="kpi"><div class="v">${{fmt(ratio,1)}}×</div><div class="l">mobilité vs géographie</div></div>
    </div>
    <table>
      <tbody>
        <tr><th>Entrées annuelles</th><td>${{(DATA.heraldInputs.annual || []).join(" + ")}}</td></tr>
        <tr><th>Stratégie</th><td>${{DATA.heraldInputs.strategy || "retirer les flags et garder les signaux utiles"}}</td></tr>
        <tr><th>Flags crise/rebond</th><td>absentes</td></tr>
        <tr><th>Régime</th><td>appris dans le modèle, affiché ici comme trajectoire latente</td></tr>
      </tbody>
    </table>`;
}}

function initSelects() {{
  const my = document.getElementById("map-year");
  if(my) {{
    DATA.years.forEach(y => {{ const o=document.createElement("option"); o.value=y; o.textContent=y; my.appendChild(o); }});
    my.value = "2025";
  }}
  const slider = document.getElementById("map-year-slider");
  if(slider) {{
    slider.max = String(DATA.years.length - 1);
    slider.value = String(Math.max(0, DATA.years.indexOf("2025")));
  }}
}}

initSelects();
drawModelBars();
drawYearLines();
drawFranceAndSeeds();
drawSectorCharts();
drawMap();
drawMechanisms();
</script>
</body>
</html>
"""

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    print(f"Wrote {out_path} ({out_path.stat().st_size / 1024:.1f} KB)")


def main() -> None:
    parser = argparse.ArgumentParser()
    if DEFAULT_PHASE3E_RUN_ROOT is not None and DEFAULT_PHASE3E_RUN_ROOT.exists():
        default_run_root = DEFAULT_PHASE3E_RUN_ROOT
    elif DEFAULT_PHASE2J_RUN_ROOT is not None and DEFAULT_PHASE2J_RUN_ROOT.exists():
        default_run_root = DEFAULT_PHASE2J_RUN_ROOT
    elif DEFAULT_PHASE2I_RUN_ROOT.exists():
        default_run_root = DEFAULT_PHASE2I_RUN_ROOT
    else:
        default_run_root = DEFAULT_RUN_ROOT
    parser.add_argument("--run-root", default=str(default_run_root))
    parser.add_argument("--old-dashboard", default=str(DEFAULT_OLD_DASH))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--embed-plotly", action="store_true", help="Embed Plotly in the HTML for offline sharing.")
    parser.add_argument("--plotly-bundle", default=str(DEFAULT_PLOTLY_BUNDLE))
    parser.add_argument("--splits-path", default=str(DEFAULT_SPLITS))
    args = parser.parse_args()
    build_dashboard(args)


if __name__ == "__main__":
    main()
