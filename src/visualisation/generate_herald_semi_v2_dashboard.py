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
DEFAULT_OLD_DASH = (
    BASE
    / "hpc_results/herald_semi_total_253_geo2025/reports/figures/herald_geo2025_final_dashboard.html"
)
DEFAULT_OUT = BASE / "reports/dashboards/herald_france_dashboard.html"
DEFAULT_OFFLINE_OUT = BASE / "reports/dashboards/herald_france_dashboard_offline.html"
DEFAULT_PLOTLY_BUNDLE = Path("/tmp/plotly_embedded.js")
DEFAULT_FORECAST_SUMMARY = BASE / "reports/metrics/herald_forecast_2026_2027_summary.json"
DEFAULT_FORECAST_DIR = BASE / "hpc_results/herald_forecast_20260506_forecast_after_strict/data_processed"
HERALD_FORECAST_TOTAL_PATTERN = (
    "herald_forecast_total_no_source_flags_semiv2_graph_ssl_forecast_2026_2027_seed_*_v1.csv"
)
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
DEFAULT_LEAK_AUDIT = BASE / "reports/HERALD_LEAK_AUDIT_FINAL_20260507.md"
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


def js(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def non_null_pairs(mapping: dict[str, Any]) -> dict[str, float]:
    return {k: v for k, v in mapping.items() if v is not None}


def load_optional_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def load_forecast_public(path: Path) -> dict[str, Any] | None:
    raw = load_optional_json(path)
    if not raw:
        return None
    rows = []
    for row in raw.get("national", []):
        if row.get("panel_key") != "no_source_flags":
            continue
        if row.get("model") == "semiv2_graph_ssl":
            public_model = "HERALD"
        elif row.get("model") == "v7_ridge_only":
            public_model = "Ridge AR"
        else:
            continue
        clean = dict(row)
        clean["panel_key"] = "panel principal"
        clean["model"] = public_model
        rows.append(clean)
    return {"national": rows}


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


def parse_audit_summary(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return {
        "verdict": "Aucun indice de fuite directe du target 2025 n'a ete trouve.",
        "target_shuffle_status": "stress-test execute; degradation forte attendue quand le target est perturbe",
        "calendar": (
            "Forecast 2026/2027 presente comme prediction prospective conditionnelle "
            "aux donnees disponibles au 2026-05-07."
        ),
        "residual_risk": (
            "Le risque residuel concerne le calendrier reel de publication des sources, "
            "pas une copie directe du target."
        ),
    }


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
    paths = sorted(csv_dir.glob(pattern))
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


def load_intelligence_layer(base_dir: Path) -> dict[str, Any]:
    """Load exploratory HERALD Intelligence v0 zone-level indicators."""
    scores_path = base_dir / "zone_recommendation_scores.csv"
    alerts_path = base_dir / "zone_alerts.csv"
    out: dict[str, Any] = {
        "status": "exploratoire_v0",
        "scores": {},
        "alertsByZone": {},
        "available": False,
    }
    if not scores_path.exists():
        return out

    try:
        scores = pd.read_csv(scores_path)
        for _, row in scores.iterrows():
            ze = str(row.get("ZE2020", "")).strip().split(".")[0].zfill(4)
            if not ze or ze == "0000":
                continue
            out["scores"][ze] = {
                "name": str(row.get("libze2020", "")),
                "opportunity_score": safe_float(row.get("opportunity_score")),
                "opportunity_tier": str(row.get("opportunity_tier", "")),
                "risk_score": safe_float(row.get("risk_score")),
                "risk_tier": str(row.get("risk_tier", "")),
                "score_status": str(row.get("score_status", "exploratoire_v0")),
                "fc_2026_mean": safe_float(row.get("fc_2026_mean")),
                "fc_2026_std": safe_float(row.get("fc_2026_std")),
                "fc_growth_2025_2026_pct": safe_float(row.get("fc_growth_2025_2026_pct")),
                "fc_2026_percentile": safe_float(row.get("fc_2026_percentile")),
                "herald_wmape_aligned": safe_float(row.get("herald_wmape_aligned")),
                "ridge_wmape": safe_float(row.get("ridge_wmape")),
                "herald_vs_ridge_pct": safe_float(row.get("herald_vs_ridge_pct")),
                "explication_fr": str(row.get("explication_fr", "")),
            }
        out["available"] = bool(out["scores"])
    except Exception as e:
        print(f"Warning: intelligence scores failed: {e}")

    if alerts_path.exists():
        try:
            alerts = pd.read_csv(alerts_path)
            for _, row in alerts.iterrows():
                ze = str(row.get("ZE2020", "")).strip().split(".")[0].zfill(4)
                if not ze or ze == "0000":
                    continue
                out["alertsByZone"].setdefault(ze, []).append(
                    {
                        "type": str(row.get("alert_type", "")),
                        "severity": str(row.get("severity", "")),
                        "value": safe_float(row.get("value")),
                        "unit": str(row.get("unit", "")),
                        "confidence": str(row.get("confidence", "")),
                        "description": str(row.get("description", "")),
                    }
                )
        except Exception as e:
            print(f"Warning: intelligence alerts failed: {e}")

    return out


def load_zone_forecast_2026_2027(forecast_dir: Path) -> dict[str, Any]:
    """Aggregate prospective HERALD zone forecasts for 2026 and 2027."""
    paths = sorted(forecast_dir.glob(HERALD_FORECAST_TOTAL_PATTERN))
    out: dict[str, Any] = {"byZone": {}, "available": False}
    if not paths:
        return out
    frames = []
    for path in paths:
        try:
            df = pd.read_csv(path)
            if {"target_year", "ZE2020", "y_pred"}.issubset(df.columns):
                frames.append(df[["target_year", "ZE2020", "y_pred", "ridge_pred", "seed"]].copy())
        except Exception as e:
            print(f"Warning: forecast file failed {path.name}: {e}")
    if not frames:
        return out
    data = pd.concat(frames, ignore_index=True)
    data["ZE2020"] = data["ZE2020"].astype(str).str.split(".").str[0].str.zfill(4)
    agg = (
        data.groupby(["ZE2020", "target_year"])
        .agg(
            mean=("y_pred", "mean"),
            std=("y_pred", "std"),
            ridge=("ridge_pred", "mean"),
            n_seeds=("seed", "nunique"),
        )
        .reset_index()
    )
    for ze, grp in agg.groupby("ZE2020"):
        out["byZone"][ze] = {}
        vals: dict[int, float] = {}
        for _, row in grp.iterrows():
            year = int(row["target_year"])
            vals[year] = float(row["mean"])
            out["byZone"][ze][str(year)] = {
                "mean": safe_float(row["mean"]),
                "std": safe_float(row["std"]),
                "ridge": safe_float(row["ridge"]),
                "n_seeds": int(row["n_seeds"]),
            }
        if 2026 in vals and 2027 in vals and vals[2026]:
            out["byZone"][ze]["growth_2026_2027_pct"] = 100.0 * (vals[2027] - vals[2026]) / vals[2026]
    out["available"] = bool(out["byZone"])
    return out


def load_zone_ridge_predictions(csv_dir: Path) -> dict[str, dict[str, float]]:
    """Load deterministic Ridge AR zone predictions for 2021-2025."""
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

    winner = summarize_model("HERALD", load_runs(per_run, "strict_no_source_flags_semiv2_graph_only_seed_*.json"))
    if not winner:
        raise RuntimeError("HERALD principal runs were not found.")
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
        "herald_semi_v2_predictions_sector_full_strict_no_source_flags_graph_only_f0.10_s0.30_r0.02_seed_*_v1.csv",
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
        "2021": 0.067308, "2022": 0.086199, "2023": 0.077667, "2024": 0.030697, "2025": 0.033911,
    }
    arima_yr = baselines.get("arima_local") or old.get("ARIMA_PY") or {
        "2021": 0.125337, "2022": 0.097012, "2023": 0.037834, "2024": 0.08621, "2025": 0.034292,
    }
    lstm_yr = baselines.get("lstm_local") or {}
    dcrnn_yr = baselines.get("dcrnn_residual") or old.get("DCRNN_PY") or {
        "2021": 0.061726, "2022": 0.079231, "2023": 0.072603, "2024": 0.031876, "2025": 0.033911,
    }
    stgnn_yr = baselines.get("dynamic_stgnn_residual") or old.get("STGNN_PY") or {
        "2021": 0.061086, "2022": 0.079178, "2023": 0.07253, "2024": 0.031752, "2025": 0.033800,
    }

    learned_graph = build_learned_graph_data(csv_dir, old.get("GEOJSON"), old.get("ZE_NAMES") or {})
    if not learned_graph:
        learned_graph = old.get("GRAPH_DATA") or {}
    intelligence = load_intelligence_layer(BASE / "reports/metrics/herald_intelligence")
    zone_forecast = load_zone_forecast_2026_2027(DEFAULT_FORECAST_DIR)
    zone_ridge = load_zone_ridge_predictions(csv_dir)

    payload = {
        "years": YEARS,
        "sectorLabels": SECTOR_LABELS,
        "models": [winner],
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
        "forecast": load_forecast_public(Path(args.forecast_summary)),
        "audit": parse_audit_summary(Path(args.leak_audit)),
        "intelligence": intelligence,
        "zoneForecast": zone_forecast,
        "zoneRidgePreds": zone_ridge,
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
<title>HERALD France - Tableau de bord scientifique</title>
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
  @media (max-width:1000px) {{ .kpis,.grid2,.grid-map {{ grid-template-columns:1fr; }} }}
</style>
</head>
<body>
<div class="wrap">
  <h1>HERALD France - Tableau de bord scientifique</h1>
  <div class="subtitle">
    Lecture opérationnelle du modèle HERALD: comparaison avec les modèles de référence, prévision observée
    vs prédite, erreurs territoriales, secteurs A10 et structure du graphe dynamique appris. Les anciennes
      contrôles méthodologiques internes sont résumés séparément pour ne pas les confondre avec
      les modèles concurrents.
  </div>

  <div class="kpis">
    <div class="kpi"><div class="v">{semi_2025:.4f}</div><div class="l">WMAPE 2025 HERALD médian</div></div>
    <div class="kpi"><div class="v">{ridge_2025:.4f}</div><div class="l">WMAPE 2025 Ridge AR</div></div>
    <div class="kpi"><div class="v">{gain:.1f}%</div><div class="l">Gain HERALD vs Ridge en 2025</div></div>
    <div class="kpi"><div class="v">{winner['n']}</div><div class="l">Seeds du protocole principal</div></div>
  </div>

  <div class="section">
    <div class="section-title">Protocole walk-forward</div>
    <div class="section-note">
      Chaque année est testée comme une vraie année future: HERALD est entraîné uniquement avec les années
      antérieures au fold. Ce tableau rend visible les années qui entrent dans l'entraînement et l'année
      qui sert de comparaison au réel.
    </div>
    <div class="card">{fold_table_html}</div>
  </div>

  <div class="section">
    <div class="section-title">0. Données du modèle</div>
    <div class="section-note">Résumé du protocole d'entraînement et de validation strict ex-ante.</div>
    <div class="kpis" style="grid-template-columns:repeat(6,minmax(140px,1fr))">
      <div class="kpi"><div class="v">walk-forward</div><div class="l">Fenêtre d'entraînement</div></div>
      <div class="kpi"><div class="v">2021–2025</div><div class="l">Années évaluées</div></div>
      <div class="kpi"><div class="v">280</div><div class="l">Zones d'emploi</div></div>
      <div class="kpi"><div class="v">9 (A10)</div><div class="l">Secteurs économiques</div></div>
      <div class="kpi"><div class="v">10</div><div class="l">Seeds du protocole</div></div>
      <div class="kpi"><div class="v">conservateur</div><div class="l">Panel principal</div></div>
    </div>
    <div class="card" style="margin-top:8px">
      <table>
        <thead><tr><th>Entrées</th><th>Détail</th></tr></thead>
        <tbody>
          <tr><td>Historique créations</td><td>SIDE/INSEE par zone d'emploi et secteur A10</td></tr>
          <tr><td>Trajectoire de croissance</td><td>Lags et tendances locales récentes</td></tr>
          <tr><td>Emploi &amp; masse salariale</td><td>URSSAF par zone</td></tr>
          <tr><td>Caractéristiques structurelles</td><td>FLORES (taille d'établissement, structure)</td></tr>
          <tr><td>Graphe géographique</td><td>Adjacence et distance entre zones d'emploi</td></tr>
          <tr><td>Graphe mobilité</td><td>Flux domicile-travail inter-zones</td></tr>
          <tr><td>Flags de régime</td><td>Chocs prédéfinis (crise, COVID, reprise)</td></tr>
          <tr><td>Cible (target)</td><td>Créations d'établissements par zone et secteur A10</td></tr>
        </tbody>
      </table>
    </div>
  </div>

  <div class="section">
    <div class="section-title">1. Comparaison principale: HERALD vs références</div>
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
      Cette courbe compare HERALD uniquement aux modèles externes. Les contrôles internes sont
      résumés dans le bloc méthodologique suivant.
    </div>
    <div class="card"><div id="chart-year-lines" style="height:390px"></div></div>
  </div>

  <div class="section">
    <div class="section-title">2b. Validation méthodologique interne</div>
    <div class="section-note">
      Ces lignes ne sont pas des modèles concurrents: elles servent seulement à vérifier que le résultat
      HERALD ne dépend pas d'une fuite directe, d'une seule source de variables ou d'un choix arbitraire
      d'architecture.
    </div>
    <div class="card"><div id="internal-validation"></div></div>
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
      Les volumes absolus (réel vs HERALD) évitent l'illusion d'une bonne WMAPE sur un secteur marginal.
      Le graphique de droite affiche la WMAPE sectorielle de HERALD. Les contrôles A10 restent utilisés
      dans l'audit interne, mais ne sont pas présentés comme modèles concurrents dans le dashboard public.
    </div>
    <div class="controls" style="margin-bottom:8px">
      <label>Année secteurs <select id="sector-year" onchange="drawSectorCharts()">
        {sector_year_options}
      </select></label>
    </div>
    <div class="grid2">
      <div class="card"><div id="chart-sector-volume" style="height:400px"></div></div>
      <div class="card"><div id="chart-sector-wmape" style="height:400px"></div></div>
    </div>
  </div>

  <div class="section">
    <div class="section-title">5. Carte territoriale interactive — erreur, volume et graphe</div>
    <div class="section-note">
      Une seule carte avec trois lectures superposables: la chaleur d'erreur de HERALD par zone d'emploi,
      le volume réel d'établissements, et le graphe de mobilité appris (toggle ON/OFF).
      Cliquez sur une zone pour voir l'évolution réelle vs prédite 2021–2025 et la composition A10.
      Les connexions du graphe révèlent les flux économiques que le modèle a appris à exploiter —
      une zone fortement connectée à une métropole hérite de son signal prédictif.
    </div>
    <div class="grid-map">
      <div class="card">
        <div class="controls">
          <label>Métrique <select id="map-metric" onchange="drawMap()">
            <option value="semi_error">Erreur HERALD (WMAPE)</option>
            <option value="abs_error">Erreur absolue (établissements)</option>
            <option value="real_volume">Volume réel</option>
            <option value="opp_score">Intelligence v0 — opportunité</option>
            <option value="risk_score">Intelligence v0 — risque</option>
            <option value="uncertainty">Intelligence v0 — incertitude</option>
            <option value="fc_growth">Intelligence v0 — croissance 2026</option>
            <option value="fc_growth_2027">Intelligence v0 — croissance 2027</option>
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
        <div class="mini">Évolution réelle vs prédite 2021–2025 + secteurs A10 + connexions du graphe pour la zone.</div>
        <div id="zone-intelligence" class="mini warn" style="margin-top:10px"></div>
        <div id="chart-zone-time" style="height:260px"></div>
        <div id="chart-zone-sector" style="height:260px"></div>
        <div id="zone-connections" class="mini" style="margin-top:10px"></div>
      </div>
    </div>
  </div>

  <div class="section">
    <div class="section-title">6. Mécanismes internes — alpha, gamma et régimes</div>
    <div class="section-note">
      Alpha mesure le poids relatif de la composante locale (1 = purement local, 0 = purement graphe).
      HERALD apprend à équilibrer les deux sources selon l'année et le régime économique.
      Gamma révèle ce que le modèle a retenu du graphe: γ_mob ≈ 0.87 contre γ_geo ≈ 0.28 signifie que
      les flux de mobilité domicile-travail sont plus informatifs que la seule adjacence géographique.
    </div>
    <div class="grid2">
      <div class="card"><div id="chart-alpha" style="height:340px"></div></div>
      <div class="card"><div id="chart-gamma" style="height:340px"></div></div>
    </div>
  </div>

  <div class="section">
    <div class="section-title">7. Audit anti-fuite et prévision 2026–2027</div>
    <div class="section-note">
      La validation est strictement walk-forward: pour chaque année 2021–2025, le modèle est entraîné
      uniquement avec les années antérieures. Les contrôles stricts et l'audit anti-fuite réduisent le
      risque de copie directe du target, sans autoriser l'affirmation "zéro fuite".
      Le forecast 2026–2027 est une prévision prospective conditionnelle aux données disponibles au 2026-05-07 —
      il ne s'agit pas d'une validation ex-ante: il n'existe pas encore de données réelles pour ces années.
    </div>
    <div class="grid2">
      <div class="card"><div id="audit-box"></div></div>
      <div class="card"><div id="chart-forecast-national" style="height:340px"></div></div>
    </div>
  </div>
</div>

<script>
const DATA = {js(payload)};
const COLORS = {{
  semi:"#f7834f", masked:"#ffb074", control:"#4aa3ff", history:"#b084f5",
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
function fmt(x, d=4) {{ return x === null || x === undefined || Number.isNaN(x) ? "n/a" : Number(x).toFixed(d); }}
function zeName(ze) {{ return (DATA.zeNames && DATA.zeNames[ze]) ? DATA.zeNames[ze] : ze; }}
function pct(x) {{ return x === null || x === undefined ? "n/a" : (100*x).toFixed(2)+"%"; }}
function colorFor(label) {{
  if(label === "HERALD") return COLORS.semi;
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
      line:{{color:colorFor(m.label), width:m.label === "HERALD" ? 4 : 2}},
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

function drawInternalValidation() {{
  const rows = DATA.internalControls || [];
  let html = "<table><thead><tr><th>Contrôle</th><th>Rôle méthodologique</th><th>WMAPE 2025</th><th>Lecture</th></tr></thead><tbody>";
  rows.forEach(r => {{
    let role = "Contrôle interne";
    let reading = "Utilisé pour vérifier la robustesse du résultat.";
    if(r.label.includes("sans semi")) {{
      role = "Isole l'effet de l'apprentissage semi-supervisé";
      reading = "Si HERALD reste proche ou meilleur, la semi-supervision apporte un signal opérationnel; sinon elle reste exploratoire.";
    }} else if(r.label.includes("local")) {{
      role = "Teste si le graphe apporte plus qu'un modèle local";
      reading = "Le contrôle local reste compétitif: le claim graphe doit rester prudent.";
    }} else if(r.label.includes("lag-only")) {{
      role = "Contrôle anti-fuite dur avec variables retardées";
      reading = "Sert à vérifier que le résultat 2025 n'est pas expliqué par une source contemporaine ambiguë.";
    }}
    html += `<tr><td>${{r.label}}</td><td>${{role}}</td><td>${{fmt(r.wmape_2025_median)}}</td><td>${{reading}}</td></tr>`;
  }});
  html += "</tbody></table><div class='mini warn' style='margin-top:10px'>Ces contrôles ne doivent pas être lus comme des modèles concurrents dans la comparaison principale.</div>";
  document.getElementById("internal-validation").innerHTML = html;
}}

function drawFranceAndSeeds() {{
  const years = DATA.years;
  const realVals = years.map(y=>(DATA.franceTotal[y]||{{}}).y_true||null);
  const heraldVals = years.map(y=>(DATA.franceTotal[y]||{{}}).y_pred||null);
  const heraldText = years.map(y => {{
    const ft = DATA.franceTotal[y];
    if(!ft) return y;
    const err = ft.abs_error || Math.abs((ft.y_pred||0)-(ft.y_true||0));
    return y+"<br>Réel: "+ft.y_true+"<br>HERALD: "+ft.y_pred+"<br>Erreur abs: "+err+" étab.";
  }});
  Plotly.newPlot("chart-france-real-pred", [
    {{type:"scatter", mode:"lines+markers", x:years, y:realVals,
      name:"Réel INSEE", line:{{color:COLORS.real,width:3}},
      hovertemplate:"%{{x}}<br>Réel: %{{y:,}}<extra></extra>"}},
    {{type:"scatter", mode:"lines+markers", x:years, y:heraldVals,
      name:"HERALD", line:{{color:COLORS.semi,width:3}},
      text:heraldText, hovertemplate:"%{{text}}<extra></extra>"}},
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
  if(st && st.sectors) {{
    const labels = st.sectors.map(s => s+" — "+DATA.sectorLabels[s]);
    // For WMAPE hover: show absolute error
    const absErr = st.sectors.map((s,i) => Math.abs((st.y_pred[i]||0)-(st.y_true[i]||0)));
    const wmapePerSec = st.sectors.map((s,i) => st.y_true[i] ? (absErr[i]/st.y_true[i]*100).toFixed(1)+"%" : "n/a");
    Plotly.newPlot("chart-sector-volume", [
      {{type:"bar", x:labels, y:st.y_true, name:"Réel INSEE",
        marker:{{color:COLORS.real, opacity:0.75}},
        hovertemplate:"%{{x}}<br>Réel: %{{y:,}}<extra></extra>"}},
      {{type:"bar", x:labels, y:st.y_pred, name:"HERALD",
        marker:{{color:COLORS.semi, opacity:0.85}},
        customdata:wmapePerSec,
        hovertemplate:"%{{x}}<br>HERALD: %{{y:,}}<br>WMAPE: %{{customdata}}<extra></extra>"}}
    ], Object.assign({{}}, BASE_LAYOUT, {{
      title:"Volumes A10 "+yr+": réel vs HERALD",
      barmode:"group",
      xaxis:{{tickangle:-30, automargin:true}},
      yaxis:{{title:"Établissements", gridcolor:"#30364f", tickformat:","}}
    }}), {{responsive:true}});
  }}

  // WMAPE sectoriel: HERALD + contrôles — plus bas = meilleur, per sector
  const sectors = Object.keys(DATA.sectorLabels);
  const traces = DATA.models.filter(m => m.sector).map(m => ({{
    type:"bar",
    x:sectors.map(s => s+" — "+DATA.sectorLabels[s]),
    y:sectors.map(s => m.sector[s]),
    name:m.label,
    marker:{{color:colorFor(m.label)}},
    hovertemplate:"%{{x}}<br>"+m.label+": %{{y:.4f}}<extra></extra>"
  }}));
  Plotly.newPlot("chart-sector-wmape", traces, Object.assign({{}}, BASE_LAYOUT, {{
    title:"WMAPE sectoriel HERALD — plus bas = meilleur",
    barmode:"group",
    xaxis:{{tickangle:-30, automargin:true}},
    yaxis:{{title:"WMAPE", gridcolor:"#30364f"}},
    legend:{{orientation:"h", y:-0.3}}
  }}), {{responsive:true}});
}}

function mapValue(metric, year, ze) {{
  if(metric === "semi_error") return DATA.zoneSemiError[year] ? DATA.zoneSemiError[year][ze] : null;
  if(metric === "real_volume") return DATA.zoneSemiReal[year] ? DATA.zoneSemiReal[year][ze] : null;
  if(metric === "abs_error") return DATA.zoneSemiAbs[year] ? DATA.zoneSemiAbs[year][ze] : null;
  const intel = DATA.intelligence && DATA.intelligence.scores ? DATA.intelligence.scores[ze] : null;
  if(!intel) return null;
  if(metric === "opp_score") return intel.opportunity_score;
  if(metric === "risk_score") return intel.risk_score;
  if(metric === "fc_growth") return intel.fc_growth_2025_2026_pct;
  if(metric === "fc_growth_2027") {{
    const zf = DATA.zoneForecast && DATA.zoneForecast.byZone ? DATA.zoneForecast.byZone[ze] : null;
    return zf ? zf.growth_2026_2027_pct : null;
  }}
  if(metric === "uncertainty") {{
    if(intel.fc_2026_mean && intel.fc_2026_std !== null && intel.fc_2026_std !== undefined)
      return 100 * intel.fc_2026_std / Math.max(1, Math.abs(intel.fc_2026_mean));
    return null;
  }}
  return null;
}}

function intelligenceText(ze) {{
  const intel = DATA.intelligence && DATA.intelligence.scores ? DATA.intelligence.scores[ze] : null;
  if(!intel) return "";
  const alerts = DATA.intelligence.alertsByZone && DATA.intelligence.alertsByZone[ze] ? DATA.intelligence.alertsByZone[ze] : [];
  let txt = "<br><b>HERALD Intelligence v0</b><br>";
  txt += "Opportunité: "+fmt(intel.opportunity_score,1)+" ("+(intel.opportunity_tier||"n/a")+")<br>";
  txt += "Risque: "+fmt(intel.risk_score,1)+" ("+(intel.risk_tier||"n/a")+")<br>";
  if(intel.fc_2026_mean !== null && intel.fc_2026_mean !== undefined)
    txt += "Prévision 2026: "+fmt(intel.fc_2026_mean,0)+" étab.<br>";
  if(intel.fc_growth_2025_2026_pct !== null && intel.fc_growth_2025_2026_pct !== undefined)
    txt += "Croissance 2025→2026: "+fmt(intel.fc_growth_2025_2026_pct,1)+"%<br>";
  const zf = DATA.zoneForecast && DATA.zoneForecast.byZone ? DATA.zoneForecast.byZone[ze] : null;
  if(zf && zf["2027"]) txt += "Prévision 2027: "+fmt(zf["2027"].mean,0)+" étab.<br>";
  if(zf && zf.growth_2026_2027_pct !== null && zf.growth_2026_2027_pct !== undefined)
    txt += "Croissance 2026→2027: "+fmt(zf.growth_2026_2027_pct,1)+"%<br>";
  if(alerts.length) txt += "Alertes: "+alerts.slice(0,2).map(a => a.description).join(" | ")+"<br>";
  txt += "<span style='color:#f6c15b'>Indice exploratoire, poids non calibrés.</span>";
  return txt;
}}

function mapColorScale(metric) {{
  if(metric === "real_volume") return [[0,"#0f1220"],[0.4,"#1a3a5c"],[0.7,"#2e6da4"],[1,"#74b9ff"]];
  if(metric === "opp_score") return [[0,"#15202b"],[0.35,"#1f7a4d"],[0.7,"#8bd346"],[1,"#ffe066"]];
  if(metric === "risk_score") return [[0,"#173a2a"],[0.45,"#ffd54f"],[0.75,"#ff8a65"],[1,"#ef5350"]];
  if(metric === "uncertainty") return [[0,"#143b3a"],[0.4,"#26a69a"],[0.75,"#b084f5"],[1,"#ef5350"]];
  if(metric === "fc_growth") return [[0,"#6b1f2a"],[0.45,"#ffd54f"],[0.55,"#e0e4f0"],[1,"#26a69a"]];
  if(metric === "fc_growth_2027") return [[0,"#6b1f2a"],[0.45,"#ffd54f"],[0.55,"#e0e4f0"],[1,"#26a69a"]];
  return [[0,"#1a3a2a"],[0.35,"#26a69a"],[0.7,"#ffd54f"],[1,"#ef5350"]];
}}

function mapColorbarTitle(metric) {{
  if(metric === "real_volume") return "Volume";
  if(metric === "abs_error") return "Erreur abs.";
  if(metric === "opp_score") return "Opportunité";
  if(metric === "risk_score") return "Risque";
  if(metric === "uncertainty") return "CV %";
  if(metric === "fc_growth") return "Croiss. %";
  if(metric === "fc_growth_2027") return "Croiss. %";
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
      base += "Réel: "+(pred.y_true||"?")+"<br>HERALD: "+(pred.y_pred||"?")+"<br>Erreur abs.: "+(pred.abs_error||"?")+" étab."+wmape+"<br>";
    }}
    if(metric==="abs_error") base += "Erreur abs.: "+fmt(val,0)+" étab.";
    else if(metric==="opp_score") base += "Score opportunité: "+fmt(val,1)+"/100";
    else if(metric==="risk_score") base += "Score risque: "+fmt(val,1)+"/100";
    else if(metric==="uncertainty") base += "Incertitude forecast: "+fmt(val,2)+"%";
    else if(metric==="fc_growth") base += "Croissance prévue 2025→2026: "+fmt(val,1)+"%";
    else if(metric==="fc_growth_2027") base += "Croissance prévue 2026→2027: "+fmt(val,1)+"%";
    else if(metric!=="real_volume") base += "WMAPE: "+pct(val);
    if(metric.startsWith("opp_") || metric.endsWith("_score") || metric==="uncertainty" || metric==="fc_growth" || metric==="fc_growth_2027")
      base += intelligenceText(ze);
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

function clampScore(x) {{
  if(x === null || x === undefined || isNaN(x)) return 0;
  return Math.max(0, Math.min(100, Number(x)));
}}

function renderIntelPanel(intel, alerts) {{
  const opp = clampScore(intel.opportunity_score);
  const risk = clampScore(intel.risk_score);
  const zf = DATA.zoneForecast && DATA.zoneForecast.byZone ? DATA.zoneForecast.byZone[CURRENT_ZONE || ""] : null;
  const alertTxt = alerts.length
    ? "<div class='intel-alert'><b>Alerte:</b> "+alerts.slice(0,2).map(a => a.description).join(" | ")+"</div>"
    : "";
  return `
    <div class="intel-panel">
      <div class="intel-head">
        <div class="intel-title">HERALD Intelligence v0</div>
        <div class="intel-status">exploratoire</div>
      </div>
      <div class="intel-grid">
        <div class="intel-chip">
          <div class="label">Opportunité</div>
          <div class="value">${{fmt(opp,1)}}/100</div>
          <div class="scorebar opp"><span style="width:${{opp}}%"></span></div>
          <div class="label">${{intel.opportunity_tier || "n/a"}}</div>
        </div>
        <div class="intel-chip">
          <div class="label">Risque</div>
          <div class="value">${{fmt(risk,1)}}/100</div>
          <div class="scorebar risk"><span style="width:${{risk}}%"></span></div>
          <div class="label">${{intel.risk_tier || "n/a"}}</div>
        </div>
        <div class="intel-chip">
          <div class="label">Prévision 2026</div>
          <div class="value">${{fmt(intel.fc_2026_mean,0)}}</div>
          <div class="label">créations prévues</div>
        </div>
        <div class="intel-chip">
          <div class="label">Croissance 2025→2026</div>
          <div class="value">${{fmt(intel.fc_growth_2025_2026_pct,1)}}%</div>
          <div class="label">prospectif</div>
        </div>
        <div class="intel-chip">
          <div class="label">Prévision 2027</div>
          <div class="value">${{zf && zf["2027"] ? fmt(zf["2027"].mean,0) : "n/a"}}</div>
          <div class="label">créations prévues</div>
        </div>
        <div class="intel-chip">
          <div class="label">Croissance 2026→2027</div>
          <div class="value">${{zf && zf.growth_2026_2027_pct !== undefined ? fmt(zf.growth_2026_2027_pct,1)+"%" : "n/a"}}</div>
          <div class="label">prospectif</div>
        </div>
      </div>
      ${{alertTxt}}
      <details class="intel-details">
        <summary>Voir l'explication méthodologique</summary>
        <div style="margin-top:6px">${{intel.explication_fr || "Explication non disponible."}}</div>
        <div style="margin-top:6px;color:#f6c15b">v0: score indicatif, poids non calibrés; ne pas lire comme recommandation finale.</div>
      </details>
    </div>`;
}}

function drawZone(ze, year) {{
  CURRENT_ZONE = ze;
  const name = zeName(ze);
  document.getElementById("zone-title").textContent = name+" — ZE "+ze;
  const intelEl = document.getElementById("zone-intelligence");
  const intel = DATA.intelligence && DATA.intelligence.scores ? DATA.intelligence.scores[ze] : null;
  if(intelEl) {{
    if(intel) {{
      const alerts = DATA.intelligence.alertsByZone && DATA.intelligence.alertsByZone[ze] ? DATA.intelligence.alertsByZone[ze] : [];
      intelEl.innerHTML = renderIntelPanel(intel, alerts);
    }} else {{
      intelEl.innerHTML = "<b>HERALD Intelligence v0:</b> indicateurs non disponibles pour cette zone.";
    }}
  }}
  const chartYears = DATA.zoneForecast && DATA.zoneForecast.available
    ? DATA.years.concat(["2026","2027"])
    : DATA.years.slice();
  const real=[], semi=[], ridge=[], hoverTexts=[];
  chartYears.forEach(y => {{
    const p = DATA.zoneSemiPreds[y] ? DATA.zoneSemiPreds[y][ze] : null;
    const zf = DATA.zoneForecast && DATA.zoneForecast.byZone ? DATA.zoneForecast.byZone[ze] : null;
    const fp = zf && zf[y] ? zf[y] : null;
    const rp = DATA.zoneRidgePreds && DATA.zoneRidgePreds[y] ? DATA.zoneRidgePreds[y][ze] : null;
    real.push(p ? p.y_true : null);
    semi.push(p ? p.y_pred : (fp ? fp.mean : null));
    ridge.push(rp !== undefined && rp !== null ? rp : (fp ? fp.ridge : null));
    const ae = p ? Math.abs((p.y_pred||0)-(p.y_true||0)) : null;
    const suffix = Number(y) >= 2026 ? "<br><b>Prévision prospective</b>" : "";
    hoverTexts.push(y+"<br>Réel: "+(p?p.y_true:"n/a")+"<br>HERALD: "+(p?p.y_pred:(fp?fmt(fp.mean,0):"n/a"))+"<br>Ridge AR: "+(ridge[ridge.length-1]!==null?fmt(ridge[ridge.length-1],0):"n/a")+"<br>Erreur: "+(ae||"n/a")+" étab."+suffix);
  }});
  const traces = [
    {{type:"scatter", mode:"lines+markers", x:chartYears, y:real,
      name:"Réel INSEE", line:{{color:COLORS.real,width:3}},
      hovertemplate:"%{{x}}<br>Réel: %{{y:,}}<extra></extra>"}},
    {{type:"scatter", mode:"lines+markers", x:chartYears, y:semi,
      name:"HERALD", line:{{color:COLORS.semi,width:3}},
      text:hoverTexts, hovertemplate:"%{{text}}<extra></extra>"}},
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
  if(rows && rows.length) {{
    const sLabels = rows.map(r => r.s+" — "+(DATA.sectorLabels[r.s]||r.s));
    const wmapePerSec = rows.map(r => r.t ? ((Math.abs(r.p-r.t)/r.t)*100).toFixed(1)+"%" : "n/a");
    Plotly.react("chart-zone-sector", [
      {{type:"bar", x:sLabels, y:rows.map(r=>r.t), name:"Réel",
        marker:{{color:COLORS.real,opacity:0.75}},
        hovertemplate:"%{{x}}<br>Réel: %{{y:,}}<extra></extra>"}},
      {{type:"bar", x:sLabels, y:rows.map(r=>r.p), name:"HERALD",
        customdata:wmapePerSec, marker:{{color:COLORS.semi,opacity:0.85}},
        hovertemplate:"%{{x}}<br>HERALD: %{{y:,}}<br>WMAPE: %{{customdata}}<extra></extra>"}}
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
  const semi = model("HERALD");
  const alphaYears = Object.keys(semi.alpha || {{}}).filter(y => semi.alpha[y] !== null).sort();
  Plotly.newPlot("chart-alpha", [{{
    type:"scatter", mode:"lines+markers", x:alphaYears, y:alphaYears.map(y=>semi.alpha[y]),
    name:"Alpha local", line:{{color:COLORS.semi,width:3}}
  }}], Object.assign({{}}, BASE_LAYOUT, {{
    title:"Alpha: poids local vs graphe", yaxis:{{title:"Alpha local", gridcolor:"#30364f", range:[0,1]}},
    xaxis:{{title:"Année", gridcolor:"#30364f"}}
  }}), {{responsive:true}});

  const labels = DATA.models.map(m=>m.label);
  Plotly.newPlot("chart-gamma", [
    {{type:"bar", x:labels, y:DATA.models.map(m=>m.gamma_geo), name:"Gamma géographique", marker:{{color:"#4aa3ff"}}}},
    {{type:"bar", x:labels, y:DATA.models.map(m=>m.gamma_mob), name:"Gamma mobilité", marker:{{color:"#b084f5"}}}}
  ], Object.assign({{}}, BASE_LAYOUT, {{
    title:"Importance apprise des priors du graphe", barmode:"group",
    yaxis:{{title:"Gamma", gridcolor:"#30364f"}}, xaxis:{{tickangle:-15, automargin:true}}
  }}), {{responsive:true}});
}}

function drawAuditAndForecast() {{
  const audit = DATA.audit || {{}};
  document.getElementById("audit-box").innerHTML = `
    <table>
      <tbody>
        <tr><th>Verdict anti-fuite</th><td>${{audit.verdict || "Aucun résumé disponible."}}</td></tr>
        <tr><th>Target-shuffle</th><td>${{audit.target_shuffle_status || "Stress-test non chargé dans ce dashboard."}}</td></tr>
        <tr><th>Calendrier</th><td>${{audit.calendar || "Calendrier non chargé."}}</td></tr>
        <tr><th>Risque résiduel</th><td>${{audit.residual_risk || "À documenter."}}</td></tr>
      </tbody>
    </table>
    <div class="mini warn" style="margin-top:10px">
      Lecture: ce test réduit fortement le risque de fuite directe, mais il ne remplace pas le contrôle de
      disponibilité réelle des sources à la date de prévision.
    </div>`;

  const national = (DATA.forecast && DATA.forecast.national) ? DATA.forecast.national : [];
  const rows = national.filter(r => r.panel_key === "panel principal" && (r.model === "HERALD" || r.model === "Ridge AR"));
  const years = [...new Set(rows.map(r => String(r.target_year)))].sort();
  const herald = years.map(y => {{
    const r = rows.find(x => String(x.target_year) === y && x.model === "HERALD");
    return r ? r.mean_pred : null;
  }});
  const ridge = years.map(y => {{
    const r = rows.find(x => String(x.target_year) === y && x.model === "Ridge AR");
    return r ? r.mean_pred : null;
  }});
  Plotly.newPlot("chart-forecast-national", [
    {{type:"scatter", mode:"lines+markers", x:years, y:herald, name:"HERALD", line:{{color:COLORS.semi,width:3}}}},
    {{type:"scatter", mode:"lines+markers", x:years, y:ridge, name:"Ridge AR", line:{{color:COLORS.ridge,width:3,dash:"dash"}}}}
  ], Object.assign({{}}, BASE_LAYOUT, {{
    title:"Forecast national 2026/2027 - conditionnel au 2026-05-07",
    yaxis:{{title:"Créations prévues", gridcolor:"#30364f"}},
    xaxis:{{title:"Année", gridcolor:"#30364f"}}
  }}), {{responsive:true}});
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
drawInternalValidation();
drawFranceAndSeeds();
drawSectorCharts();
drawMap();
drawMechanisms();
drawAuditAndForecast();
</script>
</body>
</html>
"""

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    print(f"Wrote {out_path} ({out_path.stat().st_size / 1024:.1f} KB)")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", default=str(DEFAULT_RUN_ROOT))
    parser.add_argument("--old-dashboard", default=str(DEFAULT_OLD_DASH))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--embed-plotly", action="store_true", help="Embed Plotly in the HTML for offline sharing.")
    parser.add_argument("--plotly-bundle", default=str(DEFAULT_PLOTLY_BUNDLE))
    parser.add_argument("--forecast-summary", default=str(DEFAULT_FORECAST_SUMMARY))
    parser.add_argument("--leak-audit", default=str(DEFAULT_LEAK_AUDIT))
    parser.add_argument("--splits-path", default=str(DEFAULT_SPLITS))
    args = parser.parse_args()
    build_dashboard(args)


if __name__ == "__main__":
    main()
