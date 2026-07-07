"""
France ZE2020 integrated dashboard.

See reports/canonical/HERALD_22_FR_ZE2020_DASHBOARD_MVP.md. Static, self-contained
HTML (Plotly embedded locally, same technique already used by
src/data/european_panel/build_observatory_v04_dashboard.py -- duplicated here as a
small private helper rather than imported, to keep this France-only MVP decoupled
from the unrelated European Observatory track).

Shows, for a selected ZE2020: the controlled prediction (persistence/ridge,
already-audited baseline -- NEVER claimed superior), a descriptive sectoral
view, and the exploratory relational signals from HERALD_20/21. Block 1
is the current audited architecture summary. It does not create a new model
claim; it only explains the already documented chain.

Reads ONLY already-canonical/already-audited inputs:
  data/processed/france_ze2020/fr_ze2020_clean_panel.csv          (observed series)
  data/processed/france_ze2020/fr_ze2020_baseline_predictions_v1.csv (persistence/ridge,
    regenerable -- if missing, the prediction panel shows observed-only and says so,
    it never fabricates a predicted series)
  data/processed/france_ze2020/fr_ze2020_sector_panel.csv          (descriptive sector shares)
  data/processed/france_ze2020/fr_ze2020_sector_relational_features.csv (dominant
    sector / diversity badges)
  data/processed/france_ze2020/fr_ze2020_sector_graph_predictions_v1.csv (optional,
    sector_share predicted vs observed -- only shown if the file exists)
  data/processed/france_ze2020/fr_ze2020_exploratory_relation_signals.csv
  data/processed/france_ze2020/fr_ze2020_exploratory_relation_examples.csv
  data/external/ze2020_geometry.geojson  (already used by Observatory v0.3/v0.4;
    280/280 join coverage against the canonical panel, verified by this builder's
    own test, not assumed)

Never dynamic_stgnn_feature_panel*, never graph_adjacency_core_v0.csv/
graph_adjacency_mobility_v0.csv, never train_herald_v6/v7/semi_v2/regime_experiment.

Output:
  reports/dashboards/fr_ze2020_dashboard_mvp.html
"""

from __future__ import annotations

import base64
import json
import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[3]
CLEAN_PANEL_PATH = ROOT / "data/processed/france_ze2020/fr_ze2020_clean_panel.csv"
BASELINE_PREDICTIONS_PATH = ROOT / "data/processed/france_ze2020/fr_ze2020_baseline_predictions_v1.csv"
SECTOR_PANEL_PATH = ROOT / "data/processed/france_ze2020/fr_ze2020_sector_panel.csv"
SECTOR_FEATURES_PATH = ROOT / "data/processed/france_ze2020/fr_ze2020_sector_relational_features.csv"
SECTOR_GRAPH_PREDICTIONS_PATH = (
    ROOT / "data/processed/france_ze2020/fr_ze2020_sector_graph_predictions_v1.csv"
)
RELATION_SIGNALS_PATH = ROOT / "data/processed/france_ze2020/fr_ze2020_exploratory_relation_signals.csv"
RELATION_EXAMPLES_PATH = ROOT / "data/processed/france_ze2020/fr_ze2020_exploratory_relation_examples.csv"
NEURAL_FEATURE_SIGNALS_PATH = (
    ROOT / "data/processed/france_ze2020/fr_ze2020_neural_relational_feature_signals_v1.csv"
)
GEOMETRY_PATH = ROOT / "data/external/ze2020_geometry.geojson"
FINAL_COMPARISON_DASHBOARD_PATH = ROOT / "reports/dashboards/herald_france_final_dashboard.html"

OUT_DIR = ROOT / "reports/dashboards"
OUT_PATH = OUT_DIR / "fr_ze2020_dashboard_mvp.html"

GEOMETRY_NOT_AUDITED_MESSAGE = "Géométrie ZE2020 non auditée."
PREDICTION_NOT_FOUND_MESSAGE = "Prévision auditée non disponible à cette granularité."
RELATIONAL_CAVEAT = "Signal exploratoire, non causal."
GLOBAL_CAVEAT = "Associations exploratoires: ni causalité, ni prescription automatique."

ARCHITECTURE_STEPS = [
    (
        "01",
        "Données observées",
        "Créations d'établissements, secteurs A10, géométrie ZE2020.",
        "Source publique",
    ),
    (
        "02",
        "Panel propre",
        "280 zones, années harmonisées, identifiants ZE2020 stabilisés.",
        "Base comparable",
    ),
    (
        "03",
        "Mémoire temporelle",
        "Lags et croissances sûres: seules les années passées entrent.",
        "Sans fuite future",
    ),
    (
        "04",
        "Noeuds ZE x secteur",
        "Chaque secteur est replacé dans la structure locale de sa zone.",
        "Position sectorielle",
    ),
    (
        "05",
        "Relations exploratoires",
        "Similarités ZE-ZE, interactions sectorielles et stabilité des signaux.",
        "Non causal",
    ),
    (
        "06",
        "Lecture intégrée",
        "Carte, prévision de contrôle, secteurs, graphe et comparaison historique.",
        "Aide à l'analyse",
    ),
]

RELATION_FAMILIES = [
    "ze_to_ze_similarity",
    "ze_to_ze_same_sector_signal",
    "intra_ze_sector_interaction",
    "ze_sector_specialization",
]

FEATURE_LABELS_FR = {
    "lag_1": "niveau observé l'année précédente",
    "lag_2": "niveau observé deux ans avant",
    "lag_3": "niveau observé trois ans avant",
    "growth_1y_safe": "croissance récente construite sur retards",
    "growth_2y_safe": "croissance deux ans construite sur retards",
    "similar_ze_lag_1_mean": "niveau moyen des zones similaires",
    "similar_ze_lag_1_weighted_mean": "niveau pondéré des zones similaires",
    "similar_ze_growth_1y_safe_mean": "croissance moyenne des zones similaires",
    "similar_ze_count": "nombre de zones similaires disponibles",
    "sector_share_lag_1": "poids du secteur dominant dans la zone",
    "sector_growth_lag_1": "croissance sectorielle récente",
    "sector_growth_lag_2": "croissance sectorielle retardée",
    "sector_diversity_lag_1": "diversité sectorielle",
    "sector_concentration_hhi_lag_1": "concentration sectorielle",
    "national_sector_share_lag_1": "poids national du secteur",
    "national_sector_growth_lag_1": "dynamique nationale du secteur",
    "top_sector_signal_lag_1": "signal du secteur dominant",
}


def _plotly_js_tag() -> tuple[str, str]:
    """Embed Plotly locally if available, else fall back to CDN (documented,
    same technique as build_observatory_v04_dashboard.py -- duplicated as a
    small utility, not imported, to avoid coupling this France-only MVP to
    the unrelated European Observatory module)."""
    try:
        import plotly as _plotly

        js_path = Path(_plotly.__file__).parent / "package_data" / "plotly.min.js"
        if js_path.exists():
            js = js_path.read_text(encoding="utf-8")
            logger.info("Embedding Plotly locally (%d KB)", len(js) // 1024)
            return f"<script>{js}</script>", "local_embedded"
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not load local Plotly: %s", exc)
    logger.warning("Falling back to Plotly CDN (dashboard will need internet)")
    return '<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>', "cdn_fallback"


def _integrated_comparison_dashboard_b64(plotly_tag: str) -> str:
    """Embed the previous comparison dashboard without coupling its JS state."""
    if not FINAL_COMPARISON_DASHBOARD_PATH.exists():
        return ""

    html = FINAL_COMPARISON_DASHBOARD_PATH.read_text(encoding="utf-8")
    html = html.replace('<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>', plotly_tag)
    html = html.replace("HERALD", "Modèle territorial")
    html = html.replace("herald", "modele_territorial")
    return base64.b64encode(html.encode("utf-8")).decode("ascii")


def load_clean_panel(path: Path = CLEAN_PANEL_PATH) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"ze2020": str})
    df["year"] = df["year"].astype(int)
    return df


def load_geometry(path: Path = GEOMETRY_PATH, panel_codes: set[str] | None = None) -> dict | None:
    """Returns the raw GeoJSON dict, filtered to the canonical 280-zone scope,
    or None if the file is missing or has zero overlap with the panel --
    never fabricates a map. Coverage is logged, not assumed."""
    if not path.exists():
        logger.warning("%s -- %s", GEOMETRY_NOT_AUDITED_MESSAGE, path)
        return None
    with open(path, encoding="utf-8") as f:
        geo = json.load(f)

    geo_codes = {feat["properties"].get("ze2020") for feat in geo["features"]}
    if panel_codes is not None:
        covered = panel_codes & geo_codes
        logger.info("Geometry coverage: %d/%d panel zones covered", len(covered), len(panel_codes))
        if not covered:
            logger.warning("%s -- zero overlap with canonical panel", GEOMETRY_NOT_AUDITED_MESSAGE)
            return None
        geo = dict(geo)
        geo["features"] = [f for f in geo["features"] if f["properties"].get("ze2020") in panel_codes]
    return geo


def _iter_coordinate_pairs(coords):
    """Yield lon/lat pairs from Polygon or MultiPolygon coordinate arrays."""
    if not isinstance(coords, list):
        return
    if len(coords) >= 2 and all(isinstance(v, (int, float)) for v in coords[:2]):
        yield float(coords[0]), float(coords[1])
        return
    for child in coords:
        yield from _iter_coordinate_pairs(child)


def build_geometry_centroids(geometry: dict | None) -> dict[str, dict[str, float]]:
    """Small approximate centroids are enough for drawing relation edges over
    the map. The choropleth remains the true geometry."""
    if geometry is None:
        return {}
    centroids: dict[str, dict[str, float]] = {}
    for feature in geometry.get("features", []):
        ze = feature.get("properties", {}).get("ze2020")
        pairs = list(_iter_coordinate_pairs(feature.get("geometry", {}).get("coordinates", [])))
        if not ze or not pairs:
            continue
        lon = sum(p[0] for p in pairs) / len(pairs)
        lat = sum(p[1] for p in pairs) / len(pairs)
        centroids[ze] = {"lon": lon, "lat": lat}
    return centroids


def load_predictions(path: Path = BASELINE_PREDICTIONS_PATH) -> pd.DataFrame | None:
    if not path.exists():
        logger.warning("%s -- %s", PREDICTION_NOT_FOUND_MESSAGE, path)
        return None
    df = pd.read_csv(path, dtype={"ze2020": str})
    df["year"] = df["year"].astype(int)
    return df


def load_sector_panel(path: Path = SECTOR_PANEL_PATH) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"ze2020": str, "sector_code": str})
    df["year"] = df["year"].astype(int)
    return df


def load_sector_features(path: Path = SECTOR_FEATURES_PATH) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"ze2020": str})
    df["year"] = df["year"].astype(int)
    return df


def load_sector_graph_predictions(path: Path = SECTOR_GRAPH_PREDICTIONS_PATH) -> pd.DataFrame | None:
    if not path.exists():
        return None
    df = pd.read_csv(path, dtype={"ze2020": str, "sector_code": str})
    df["year"] = df["year"].astype(int)
    return df


def load_relation_signals(path: Path = RELATION_SIGNALS_PATH) -> pd.DataFrame:
    return pd.read_csv(path, dtype={"source_id": str, "target_id": str, "sector_code": str})


def load_relation_examples(path: Path = RELATION_EXAMPLES_PATH) -> pd.DataFrame:
    return pd.read_csv(path, dtype={"ze2020": str, "related_ze2020": str})


def load_neural_feature_signals(path: Path = NEURAL_FEATURE_SIGNALS_PATH) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["eval_year"] = df["eval_year"].astype(int)
    return df


def build_neural_signal_data(signals: pd.DataFrame) -> dict[int, list[dict]]:
    data: dict[int, list[dict]] = {}
    for year, group in signals.groupby("eval_year"):
        rows = (
            group.assign(abs_importance=group["importance_score"].abs())
            .sort_values("abs_importance", ascending=False)
            .head(8)
        )
        data[int(year)] = [
            {
                "feature": str(r.feature),
                "label": FEATURE_LABELS_FR.get(str(r.feature), str(r.feature)),
                "importance_score": float(r.importance_score),
                "claim_status": str(r.claim_status),
            }
            for r in rows.itertuples()
        ]
    return data


def build_ze_data(
    clean_panel: pd.DataFrame,
    predictions: pd.DataFrame | None,
    sector_panel: pd.DataFrame,
    sector_features: pd.DataFrame,
    sector_graph_predictions: pd.DataFrame | None,
    relation_signals: pd.DataFrame,
    relation_examples: pd.DataFrame,
) -> dict:
    """One dict per ze2020, embedded client-side -- the dashboard never
    queries a server, every panel is a lookup into this structure."""
    zones = sorted(clean_panel["ze2020"].unique())
    labels = clean_panel[["ze2020", "ze2020_label"]].drop_duplicates().set_index("ze2020")["ze2020_label"]

    ze_data: dict[str, dict] = {}
    for ze in zones:
        series = clean_panel[clean_panel["ze2020"] == ze].sort_values("year")
        observed = {int(r.year): float(r.establishment_creations) for r in series.itertuples()}

        pred_by_model: dict[str, dict[int, float]] = {}
        if predictions is not None:
            ze_pred = predictions[predictions["ze2020"] == ze]
            for model_name, group in ze_pred.groupby("model"):
                pred_by_model[model_name] = {int(r.year): float(r.y_pred) for r in group.itertuples()}

        sector_rows = sector_panel[sector_panel["ze2020"] == ze]
        sector_by_year: dict[int, dict[str, float]] = {}
        sector_labels: dict[str, str] = {}
        for year, group in sector_rows.groupby("year"):
            sector_by_year[int(year)] = dict(zip(group["sector_code"], group["sector_share"]))
            sector_labels.update(dict(zip(group["sector_code"], group["sector_label"])))

        feat_rows = sector_features[sector_features["ze2020"] == ze].drop_duplicates(subset=["year"])
        feat_rows = feat_rows.sort_values("year")
        dominant_sector_latest = None
        diversity_latest = None
        if not feat_rows.empty:
            last = feat_rows.iloc[-1]
            if pd.notna(last.get("dominant_sector_lag_1")):
                dominant_sector_latest = last["dominant_sector_lag_1"]
            if pd.notna(last.get("sector_diversity_lag_1")):
                diversity_latest = float(last["sector_diversity_lag_1"])

        sector_pred_compare: list[dict] = []
        if sector_graph_predictions is not None:
            ze_sg = sector_graph_predictions[sector_graph_predictions["ze2020"] == ze]
            for r in ze_sg.itertuples():
                sector_pred_compare.append(
                    {
                        "year": int(r.year),
                        "sector_code": r.sector_code,
                        "model": r.model,
                        "y_true": float(r.y_true),
                        "y_pred": float(r.y_pred),
                        "claim_status": r.claim_status,
                    }
                )

        relations: list[dict] = []
        ze_signals = relation_signals[
            ((relation_signals["source_id"] == ze) & (relation_signals["source_type"] == "ZE2020"))
            | (
                (relation_signals["source_type"] == "ZE2020xSetor")
                & relation_signals["source_id"].str.startswith(f"{ze}_", na=False)
            )
        ]
        for r in ze_signals.itertuples():
            target_display = r.target_label if pd.notna(r.target_label) and str(r.target_label) else r.target_id
            if r.target_type == "ZE2020xSetor" and "_" in str(r.target_id):
                target_display = str(r.target_label).split(" - ", 1)[-1] if pd.notna(r.target_label) else r.target_id
            relations.append(
                {
                    "source_type": r.source_type,
                    "source_id": r.source_id,
                    "target_type": r.target_type,
                    "relation_family": r.relation_family,
                    "target_id": r.target_id,
                    "target_label": r.target_label,
                    "target_display": target_display,
                    "sector_code": r.sector_code if pd.notna(r.sector_code) else "",
                    "sector_label": r.sector_label if pd.notna(r.sector_label) else "",
                    "year_start": int(r.year_start),
                    "year_end": int(r.year_end),
                    "signal_strength": float(r.signal_strength),
                    "stability_score": float(r.stability_score),
                }
            )

        ze_data[ze] = {
            "label": labels.get(ze, ""),
            "observed": observed,
            "predictions": pred_by_model,
            "sector_by_year": sector_by_year,
            "sector_labels": sector_labels,
            "dominant_sector": dominant_sector_latest,
            "diversity": diversity_latest,
            "sector_pred_compare": sector_pred_compare,
            "relations": relations,
            "examples": [],
        }
    return ze_data


def build_sector_color_index(sector_panel: pd.DataFrame) -> list[str]:
    """Stable, sorted list of all sector codes -- lets the dashboard assign
    the same color to a sector everywhere (map, bars, legends) instead of
    re-deriving a palette per year."""
    return sorted(sector_panel["sector_code"].dropna().unique().tolist())


def build_map_metrics(ze_data: dict, relation_signals: pd.DataFrame) -> dict:
    """Precomputed z-values by year for each map color option."""
    observed_by_year: dict[int, dict[str, float]] = {}
    error_by_year: dict[int, dict[str, float]] = {}
    dominant_sector_by_year: dict[int, dict[str, str]] = {}
    stability_avg_by_year: dict[int, dict[str, float]] = {}

    similarity = relation_signals[relation_signals["relation_family"] == "ze_to_ze_similarity"]

    for ze, data in ze_data.items():
        for year, value in data["observed"].items():
            observed_by_year.setdefault(year, {})[ze] = value
            ridge = data["predictions"].get("ridge", {})
            if year in ridge:
                error_by_year.setdefault(year, {})[ze] = abs(value - ridge[year])
        for year, sector_values in data["sector_by_year"].items():
            if sector_values:
                dominant_sector_by_year.setdefault(year, {})[ze] = max(
                    sector_values.items(), key=lambda kv: kv[1]
                )[0]

    all_years = sorted(observed_by_year)
    for year in all_years:
        active = similarity[
            (similarity["year_start"].astype(int) <= year)
            & (similarity["year_end"].astype(int) >= year)
        ]
        if active.empty:
            continue
        for ze, value in active.groupby("source_id")["stability_score"].mean().items():
            stability_avg_by_year.setdefault(year, {})[ze] = float(value)

    return {
        "observed": observed_by_year,
        "error": error_by_year,
        "dominant_sector": dominant_sector_by_year,
        "stability_avg": stability_avg_by_year,
    }


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>France ZE2020 — Intelligence territoriale</title>
{plotly_tag}
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
  .subtitle {{ color:var(--muted); margin-bottom:10px; line-height:1.45; max-width:1180px; }}
  .section {{ margin-top:26px; }}
  .section-title {{ font-size:20px; font-weight:720; margin:0 0 6px; }}
  .section-note {{ color:var(--muted); font-size:14px; line-height:1.45; max-width:1200px; margin-bottom:10px; }}
  .card {{ background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:12px; }}
  .caveat-line {{ font-size:12px; color:#ffd180; background:#111525; border:1px solid #6f5a2b; padding:5px 8px; border-radius:999px; display:inline-block; margin-bottom:8px; }}
  .arch-row {{ display: flex; gap: 10px; flex-wrap: wrap; }}
  .arch-card {{ flex:1; min-width:180px; background:#111525; border:1px solid #3a4263; border-radius:8px; padding:12px; text-align:left; }}
  .arch-card .step-no {{ font-size:11px; color:var(--semi); font-weight:800; letter-spacing:.04em; }}
  .arch-card .step-title {{ font-size:14px; font-weight:760; margin-top:5px; color:#eef2ff; }}
  .arch-card .step-text {{ font-size:12px; color:#c8d2ef; line-height:1.35; margin-top:6px; }}
  .arch-card .step-badge {{ font-size:11px; color:#ffd180; margin-top:8px; border:1px solid #6f5a2b; border-radius:999px; padding:3px 7px; display:inline-block; }}
  .controls {{ display: flex; gap: 12px; flex-wrap: wrap; align-items: center; margin-bottom: 10px; }}
  .controls label {{ font-size:12px; color:var(--muted); margin-right:4px; font-weight:700; }}
  select {{ background:#111525; color:var(--text); border:1px solid var(--line); border-radius:6px; padding:7px 10px; }}
  input[type=range] {{ accent-color:var(--semi); }}
  .map-grid {{ display: grid; grid-template-columns: minmax(620px, 1.4fr) minmax(360px, 0.8fr); gap: 14px; align-items: start; }}
  .grid2 {{ display: grid; grid-template-columns: minmax(520px, 1fr) minmax(520px, 1fr); gap: 14px; margin-top: 14px; }}
  .kpis {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 8px; margin-bottom: 10px; }}
  .kpi {{ background:#111525; border:1px solid var(--line); border-radius:8px; padding:10px; }}
  .kpi .label {{ color: var(--muted); font-size: 11px; }}
  .kpi .value {{ font-size:20px; font-weight:760; margin-top:3px; color:#eef2ff; }}
  table.rel-table {{ width:100%; font-size:12px; border-collapse:collapse; }}
  table.rel-table th, table.rel-table td {{ padding:7px 6px; border-bottom:1px solid var(--line); text-align:left; }}
  table.rel-table th {{ color:#cbd5ff; font-weight:700; }}
  .example-box {{ font-size:12px; background:#111525; border-left:3px solid var(--v6); padding:9px; margin-top:6px; color:#dbe4ff; line-height:1.45; }}
  .badge {{ display:inline-block; background:#111525; border:1px solid var(--line); border-radius:999px; padding:3px 8px; font-size:11px; margin-right:6px; color:#cbd5ff; }}
  button.control-btn {{ background:#111525; color:var(--text); border:1px solid var(--line); border-radius:6px; padding:7px 11px; cursor:pointer; }}
  button.control-btn:hover {{ border-color:var(--semi); }}
  .geometry-blocked {{ padding:40px; text-align:center; color:#ffd180; background:#111525; border:1px solid #6f5a2b; border-radius:8px; }}
  #map-container {{ min-height: 620px; }}
  #map-legend {{ display:flex; flex-wrap:wrap; gap:6px; margin-top:8px; }}
  .legend-chip {{ display:inline-flex; align-items:center; gap:6px; background:#111525; border:1px solid var(--line); border-radius:999px; padding:4px 8px; font-size:11px; color:#cbd5ff; }}
  .legend-swatch {{ width:10px; height:10px; border-radius:2px; display:inline-block; }}
  #edge-legend, .legend-row {{ display:flex; flex-wrap:wrap; gap:6px; margin:8px 0; }}
  #sector-legend {{ display:flex; flex-wrap:wrap; gap:6px; margin-top:8px; }}
  .mode-btns {{ display:flex; gap:6px; flex-wrap:wrap; }}
  .mode-btn {{ background:#111525; color:var(--text); border:1px solid var(--line); border-radius:999px; padding:7px 14px; font-size:13px; cursor:pointer; }}
  .mode-btn:hover {{ border-color:var(--semi); }}
  .mode-btn.active {{ background:var(--semi); border-color:var(--semi); color:#1a1208; font-weight:700; }}
  details.advanced-controls {{ margin-top:10px; }}
  details.advanced-controls summary {{ cursor:pointer; color:#cbd5ff; font-size:12px; font-weight:700; padding:4px 0; }}
  details.advanced-controls .controls {{ margin-top:8px; padding-top:8px; border-top:1px dashed var(--line); }}
  #relation-map-list {{ max-height: 250px; overflow: auto; }}
  .muted {{ color:var(--muted); }}
  .integrated-frame {{ width:100%; min-height:920px; border:1px solid var(--line); border-radius:8px; background:#0f1220; }}
  .integrated-note {{ display:flex; gap:8px; flex-wrap:wrap; align-items:center; margin:8px 0 12px; }}
  footer {{ text-align:center; font-size:11px; color:var(--muted); padding:20px; }}
  @media (max-width: 1120px) {{ .map-grid, .grid2 {{ grid-template-columns: 1fr; }} #map-container {{ min-height: 500px; }} }}
</style>
</head>
<body>

<div class="wrap">
  <h1>France ZE2020 — Intelligence territoriale</h1>
  <div class="subtitle">Prévision contrôlée, structure sectorielle et signaux relationnels exploratoires par zone d'emploi.</div>
  <div class="caveat-line">{global_caveat}</div>

<div class="section">
  <div class="section-title">Architecture du pipeline</div>
  <div class="section-note">Chaîne actuelle auditée: les données restent séparées entre observation, entrée causale, relations exploratoires et lecture visuelle.</div>
  <div class="card">
    <div class="arch-row">
      {architecture_cards}
    </div>
  </div>
</div>

<div class="section">
  <div class="section-title">Carte territoriale ZE2020 et graphe relationnel</div>
  <div class="section-note">Choisissez une zone, une année, puis un niveau de réseau. Ces liens sont des signaux exploratoires reconstruits à partir des trajectoires; ils ne sont pas des causalités.</div>
  <div class="card">
    <div class="controls">
      <label>Zone d'emploi</label>
      <select id="ze-select" onchange="selectZone(this.value)"></select>
      <label>Année</label>
      <input id="year-slider" type="range" min="{min_relation_year}" max="{max_year}" value="{max_year}" step="1" oninput="setYear(this.value)">
      <strong id="year-label">{max_year}</strong>
      <button id="play-year-btn" class="control-btn" type="button" onclick="toggleYearPlayback()">Lecture</button>
      <label>Couleur de la carte</label>
      <select id="map-metric-select" onchange="renderMap()">
        <option value="observed">Valeur observée</option>
        <option value="error">Erreur |observé - ridge|</option>
        <option value="dominant_sector">Secteur dominant</option>
        <option value="stability_avg">Stabilité relationnelle moyenne</option>
      </select>
    </div>
    <div class="controls">
      <label>Niveau de réseau</label>
      <div class="mode-btns" id="mode-btns">
        <button type="button" class="mode-btn" data-mode="clear" onclick="setNetworkMode('clear')">Vue claire</button>
        <button type="button" class="mode-btn" data-mode="strong" onclick="setNetworkMode('strong')">Relations fortes</button>
        <button type="button" class="mode-btn" data-mode="medium" onclick="setNetworkMode('medium')">Relations moyennes</button>
        <button type="button" class="mode-btn" data-mode="full" onclick="setNetworkMode('full')">Réseau complet</button>
      </div>
    </div>
    <details class="advanced-controls">
      <summary>Mode avancé : réglages détaillés du graphe</summary>
      <div class="controls">
        <label>Famille spatiale</label>
        <select id="map-family-select" onchange="renderMap()">
          <option value="ze_to_ze_similarity">Similarité ZE-ZE</option>
          <option value="ze_to_ze_same_sector_signal">Même secteur entre ZE</option>
          <option value="all">Toutes les relations spatiales</option>
        </select>
        <label>Top connexions</label>
        <select id="topk-select" onchange="renderMap(); renderRelations();">
          <option value="5" selected>5</option>
          <option value="10">10</option>
          <option value="20">20</option>
          <option value="40">40</option>
          <option value="80">80</option>
          <option value="200">200</option>
        </select>
        <label>Signal min.</label>
        <input id="min-signal-slider" type="range" min="0" max="1" value="0.80" step="0.05" oninput="setSignalThreshold(this.value)">
        <strong id="min-signal-label">0.80</strong>
        <label>Stabilité min.</label>
        <input id="min-stability-slider" type="range" min="0" max="1" value="0.50" step="0.05" oninput="setStabilityThreshold(this.value)">
        <strong id="min-stability-label">0.50</strong>
        <label>Intensité</label>
        <select id="relation-mode-select" onchange="renderMap(); renderRelations();">
          <option value="stable" selected>Relations stables</option>
          <option value="strong">Signaux forts</option>
          <option value="medium_recurrent">Signaux moyens récurrents</option>
          <option value="strong_unstable">Signaux forts peu stables</option>
          <option value="all_detected">Tous les signaux détectés</option>
        </select>
        <label>Profondeur</label>
        <select id="graph-depth-select" onchange="renderMap(); renderRelations();">
          <option value="1" selected>1 pas</option>
          <option value="2">2 pas</option>
          <option value="3">3 pas</option>
          <option value="4">4 pas</option>
          <option value="5">5 pas</option>
          <option value="6">6 pas, réseau élargi</option>
        </select>
      </div>
    </details>
    <div id="edge-legend" class="legend-row">
      <span class="legend-chip"><span class="legend-swatch" style="background:#f7834f"></span>Relation directe</span>
      <span class="legend-chip"><span class="legend-swatch" style="background:#b084f5"></span>Chemin indirect (origine → zone pont → zone atteinte)</span>
      <span class="legend-chip"><span class="legend-swatch" style="background:#ffd180"></span>Zone pont</span>
      <span class="legend-chip muted">Épaisseur = intensité du signal</span>
      <span class="legend-chip muted">Opacité = stabilité</span>
    </div>
    <div class="map-grid">
      <div>
        <div id="map-container"></div>
        <div id="map-legend"></div>
      </div>
      <div>
        <div id="zone-summary"></div>
        <div class="caveat-line">{relational_caveat}</div>
        <div id="relation-map-list"></div>
      </div>
    </div>
  </div>
</div>

<div class="grid2">
  <div class="section">
    <div class="section-title">Prévision globale contrôlée</div>
    <div class="card">
      <div class="caveat-line">La prévision sert de contrôle. Aucune affirmation de supériorité prédictive.</div>
      <div id="prediction-chart"></div>
    </div>
  </div>

  <div class="section">
    <div class="section-title">Structure sectorielle</div>
    <div class="card">
      <div id="sector-info"></div>
      <div id="sector-chart"></div>
      <div id="sector-legend"></div>
      <div id="sector-pred-compare"></div>
    </div>
  </div>
</div>

<div class="grid2">
  <div class="section">
    <div class="section-title">Graphe des relations détectées</div>
    <div class="card">
      <div class="caveat-line">{relational_caveat}</div>
      <div class="controls">
        <label>Famille</label>
        <select id="family-select" onchange="renderRelations()">
          <option value="all">Toutes</option>
          <option value="ze_to_ze_similarity">Similarité ZE-ZE</option>
          <option value="ze_to_ze_same_sector_signal">Même secteur entre ZE</option>
          <option value="intra_ze_sector_interaction">Interaction sectorielle intra-ZE</option>
          <option value="ze_sector_specialization">Spécialisation sectorielle</option>
        </select>
      </div>
      <div id="relation-graph"></div>
      <div id="relation-tables"></div>
      <div id="relation-examples"></div>
    </div>
  </div>

  <div class="section">
    <div class="section-title">Signaux appris par les modèles</div>
    <div class="card">
      <div id="neural-signals"></div>
      <div id="annual-detail"></div>
    </div>
  </div>
</div>

<div class="section">
  <div class="section-title">Tableau comparatif intégré</div>
  <div class="section-note">Vue historique de comparaison des modèles, intégrée ici pour la présentation. Elle reste isolée du panneau ZE2020 afin de ne pas mélanger les scripts ni les états interactifs.</div>
  <div class="integrated-note">
    <span class="badge">Comparaison modèles</span>
    <span class="badge">Carte par zone</span>
    <span class="badge">Secteurs A10</span>
    <span class="badge">Fonctionnement embarqué</span>
  </div>
  <iframe id="integrated-comparison-dashboard" class="integrated-frame" title="Tableau comparatif intégré"></iframe>
</div>

</div>

<footer>
  France ZE2020 — tableau de bord exploratoire. {plotly_dep_note}
</footer>

<script>
const ZE_DATA = {ze_data_json};
const MAP_METRICS = {map_metrics_json};
const GEOMETRY = {geometry_json};
const CENTROIDS = {centroids_json};
const NEURAL_SIGNALS = {neural_signals_json};
const ZONES = {zones_json};
const SECTOR_CODES_ALL = {sector_codes_json};
const INTEGRATED_DASHBOARD_B64 = "{integrated_dashboard_b64}";
const SECTOR_COLORS = ['#4aa3ff','#66bb6a','#f7834f','#b084f5','#26a69a','#ffd180','#ef5350','#8bd3ff','#cbd5ff'];
const SECTOR_COLOR_INDEX = {{}};
SECTOR_CODES_ALL.forEach(function(c, i) {{ SECTOR_COLOR_INDEX[c] = SECTOR_COLORS[i % SECTOR_COLORS.length]; }});
const FAMILY_LABELS_FR = {{
  ze_to_ze_similarity: 'Similarité ZE-ZE',
  ze_to_ze_same_sector_signal: 'Même secteur entre ZE',
  intra_ze_sector_interaction: 'Interaction sectorielle intra-ZE',
  ze_sector_specialization: 'Spécialisation sectorielle'
}};
function familyLabel(code) {{ return FAMILY_LABELS_FR[code] || code; }}
let selectedZe = ZONES[0];
let selectedYear = {max_year};
let yearTimer = null;
let minSignal = 0.35;
let minStability = 0.15;

function minDashboardYear() {{
  return Number(document.getElementById('year-slider').min);
}}

function maxDashboardYear() {{
  return Number(document.getElementById('year-slider').max);
}}

function populateZeSelect() {{
  const sel = document.getElementById('ze-select');
  ZONES.forEach(function(ze) {{
    const opt = document.createElement('option');
    opt.value = ze;
    opt.textContent = ze + ' -- ' + (ZE_DATA[ze].label || '');
    sel.appendChild(opt);
  }});
  sel.value = selectedZe;
}}

function setYear(year) {{
  selectedYear = Number(year);
  document.getElementById('year-label').textContent = selectedYear;
  renderMap();
  renderPrediction();
  renderSector();
  renderRelations();
  renderAnnualDetail();
  renderNeuralSignals();
}}

const NETWORK_MODES = {{
  clear:  {{ depth: 1, topk: 5,   signal: 0.80, stability: 0.50, relMode: 'stable' }},
  strong: {{ depth: 1, topk: 10,  signal: 0.55, stability: 0.25, relMode: 'strong' }},
  medium: {{ depth: 3, topk: 20,  signal: 0.30, stability: 0.15, relMode: 'medium_recurrent' }},
  full:   {{ depth: 6, topk: 40,  signal: 0.00, stability: 0.00, relMode: 'all_detected' }}
}};

function setNetworkMode(mode) {{
  const cfg = NETWORK_MODES[mode];
  if (!cfg) return;
  document.querySelectorAll('.mode-btn').forEach(function(b) {{
    b.classList.toggle('active', b.dataset.mode === mode);
  }});
  document.getElementById('graph-depth-select').value = String(cfg.depth);
  document.getElementById('topk-select').value = String(cfg.topk);
  document.getElementById('relation-mode-select').value = cfg.relMode;
  document.getElementById('min-signal-slider').value = cfg.signal;
  document.getElementById('min-stability-slider').value = cfg.stability;
  setSignalThreshold(cfg.signal, false);
  setStabilityThreshold(cfg.stability, false);
  renderMap();
  renderRelations();
}}

function setSignalThreshold(value, rerender=true) {{
  minSignal = Number(value);
  document.getElementById('min-signal-label').textContent = minSignal.toFixed(2);
  if (rerender) {{ renderMap(); renderRelations(); }}
}}

function setStabilityThreshold(value, rerender=true) {{
  minStability = Number(value);
  document.getElementById('min-stability-label').textContent = minStability.toFixed(2);
  if (rerender) {{ renderMap(); renderRelations(); }}
}}

function toggleYearPlayback() {{
  const btn = document.getElementById('play-year-btn');
  if (yearTimer) {{
    clearInterval(yearTimer);
    yearTimer = null;
    btn.textContent = 'Lecture';
    return;
  }}
  btn.textContent = 'Pause';
  yearTimer = setInterval(function() {{
    const next = selectedYear >= maxDashboardYear() ? minDashboardYear() : selectedYear + 1;
    document.getElementById('year-slider').value = next;
    setYear(next);
  }}, 950);
}}

function activeRelationsForSelected(mapOnly=false) {{
  const d = ZE_DATA[selectedZe];
  const familySelect = mapOnly ? document.getElementById('map-family-select').value : document.getElementById('family-select').value;
  let rels = d.relations.filter(function(r) {{
    return r.year_start <= selectedYear && r.year_end >= selectedYear;
  }});
  if (familySelect !== 'all') {{
    rels = rels.filter(function(r) {{ return r.relation_family === familySelect; }});
  }}
  if (mapOnly) {{
    rels = rels.filter(function(r) {{
      return r.target_type === 'ZE2020' && CENTROIDS[selectedZe] && CENTROIDS[r.target_id];
    }});
  }}
  return rels;
}}

function activeZeRelations(ze) {{
  const d = ZE_DATA[ze];
  if (!d) return [];
  return d.relations.filter(function(r) {{
    return r.target_type === 'ZE2020' &&
      r.year_start <= selectedYear &&
      r.year_end >= selectedYear &&
      CENTROIDS[ze] &&
      CENTROIDS[r.target_id];
  }});
}}

function graphPathsForSelected(maxDepth) {{
  const rows = [];
  let frontier = [{{
    node: selectedZe,
    path: [selectedZe],
    labels: [ZE_DATA[selectedZe].label || selectedZe],
    signal_strength: 1,
    stability_score: 1,
    families: []
  }}];
  for (let depth = 1; depth <= maxDepth; depth++) {{
    const next = [];
    frontier.forEach(function(state) {{
      activeZeRelations(state.node).forEach(function(edge) {{
        if (state.path.includes(edge.target_id)) return;
        const targetLabel = ZE_DATA[edge.target_id] ? ZE_DATA[edge.target_id].label : edge.target_display;
        const newState = {{
          node: edge.target_id,
          path: state.path.concat([edge.target_id]),
          labels: state.labels.concat([targetLabel]),
          signal_strength: Math.min(state.signal_strength, edge.signal_strength),
          stability_score: Math.min(state.stability_score, edge.stability_score),
          families: state.families.concat([edge.relation_family])
        }};
        if (depth >= 2) {{
          rows.push({{
            source_id: selectedZe,
            target_id: edge.target_id,
            target_label: targetLabel,
            relation_family: 'chemin_relationnel_' + depth + '_pas',
            signal_strength: newState.signal_strength,
            stability_score: newState.stability_score,
            depth: depth,
            path: newState.path,
            path_labels: newState.labels,
            families: newState.families,
            via_id: newState.path[1],
            via_label: newState.labels[1]
          }});
        }}
        next.push(newState);
      }});
    }});
    frontier = sortAndFilterRelations(next).slice(0, 90);
  }}
  const dedup = {{}};
  rows.forEach(function(r) {{
    const key = r.path.join('>');
    if (!dedup[key] || r.stability_score > dedup[key].stability_score ||
        (r.stability_score === dedup[key].stability_score && r.signal_strength > dedup[key].signal_strength)) {{
      dedup[key] = r;
    }}
  }});
  return sortAndFilterRelations(Object.values(dedup));
}}

function sortAndFilterRelations(rels) {{
  const mode = document.getElementById('relation-mode-select').value;
  let out = mode === 'all_detected'
    ? rels.slice()
    : rels.filter(function(r) {{ return r.signal_strength >= minSignal && r.stability_score >= minStability; }});
  if (mode === 'medium_recurrent') {{
    out = out.filter(function(r) {{ return r.signal_strength >= 0.35 && r.signal_strength < 0.9 && r.stability_score >= 0.25; }});
    out.sort(function(a,b) {{ return b.stability_score - a.stability_score || b.signal_strength - a.signal_strength; }});
  }} else if (mode === 'strong_unstable') {{
    out = out.filter(function(r) {{ return r.signal_strength >= 0.85 && r.stability_score <= 0.25; }});
    out.sort(function(a,b) {{ return b.signal_strength - a.signal_strength || a.stability_score - b.stability_score; }});
  }} else if (mode === 'strong') {{
    out.sort(function(a,b) {{ return b.signal_strength - a.signal_strength || b.stability_score - a.stability_score; }});
  }} else if (mode === 'all_detected') {{
    out.sort(function(a,b) {{ return b.signal_strength - a.signal_strength || b.stability_score - a.stability_score; }});
  }} else {{
    out.sort(function(a,b) {{ return b.stability_score - a.stability_score || b.signal_strength - a.signal_strength; }});
  }}
  return out;
}}

function signalBand(value, stability) {{
  if (value >= 0.80 && stability >= 0.35) return 'fort';
  if (value >= 0.35 || stability >= 0.25) return 'moyen';
  return 'faible';
}}

function sectorLabel(code) {{
  for (const ze of ZONES) {{
    const labels = ZE_DATA[ze].sector_labels || {{}};
    if (labels[code]) return labels[code];
  }}
  return code;
}}

function renderSectorLegend(targetId, codes) {{
  const box = document.getElementById(targetId);
  if (!codes || codes.length === 0) {{
    box.innerHTML = '';
    return;
  }}
  box.innerHTML = codes.map(function(s) {{
    return '<span class="legend-chip"><span class="legend-swatch" style="background:' +
      (SECTOR_COLOR_INDEX[s] || '#888') + '"></span><b>' + s + '</b> ' +
      sectorLabel(s) + '</span>';
  }}).join('');
}}

function renderMap() {{
  const metricKey = document.getElementById('map-metric-select').value;
  const metric = (MAP_METRICS[metricKey] || {{}})[selectedYear] || {{}};
  if (!GEOMETRY) {{
    document.getElementById('map-container').innerHTML =
      '<div class="geometry-blocked">{geometry_blocked_message}</div>';
    return;
  }}
  const locations = ZONES;
  let z, colorscale, showscale;
  if (metricKey === 'dominant_sector') {{
    const sectorIndex = {{}};
    SECTOR_CODES_ALL.forEach(function(s, i) {{ sectorIndex[s] = i; }});
    const denom = Math.max(1, SECTOR_CODES_ALL.length - 1);
    z = locations.map(function(ze) {{ return (metric[ze] === undefined) ? null : sectorIndex[metric[ze]]; }});
    colorscale = SECTOR_CODES_ALL.map(function(s, i) {{ return [i / denom, SECTOR_COLOR_INDEX[s]]; }});
    showscale = false;
    const presentSectors = Array.from(new Set(Object.values(metric))).filter(Boolean).sort();
    renderSectorLegend('map-legend', presentSectors);
  }} else {{
    z = locations.map(function(ze) {{ return (metric[ze] === undefined) ? null : metric[ze]; }});
    colorscale = metricKey === 'error' ? [[0,'#20253a'],[0.45,'#4aa3ff'],[1,'#f7834f']] : [[0,'#20253a'],[0.45,'#4aa3ff'],[1,'#26a69a']];
    showscale = true;
    renderSectorLegend('map-legend', []);
  }}
  const data = [{{
    type: 'choropleth',
    geojson: GEOMETRY,
    locations: locations,
    z: z,
    featureidkey: 'properties.ze2020',
    colorscale: colorscale,
    showscale: showscale,
    marker: {{ line: {{ width: 0.45, color: '#9aa6b2' }} }},
    text: locations.map(function(ze) {{ return ZE_DATA[ze].label || ze; }}),
    hovertemplate: '<b>%{{text}}</b><br>Code ZE: %{{location}}<br>Valeur: %{{z}}<extra></extra>',
    name: 'ZE2020'
  }}];
  const mapRels = sortAndFilterRelations(activeRelationsForSelected(true))
    .slice(0, Number(document.getElementById('topk-select').value));
  const graphDepth = Number(document.getElementById('graph-depth-select').value);
  const pathRels = graphDepth > 1
    ? graphPathsForSelected(graphDepth).slice(0, Number(document.getElementById('topk-select').value))
    : [];
  mapRels.forEach(function(r) {{
    const a = CENTROIDS[selectedZe], b = CENTROIDS[r.target_id];
    data.push({{
      type: 'scattergeo',
      lon: [a.lon, b.lon],
      lat: [a.lat, b.lat],
      mode: 'lines',
      line: {{
        width: 1.6 + 1.4 * Math.max(0, Math.min(1, r.signal_strength)),
        color: 'rgba(213,94,0,' + Math.max(0.45, Math.min(0.85, r.stability_score)) + ')'
      }},
      hovertemplate: (ZE_DATA[selectedZe].label || selectedZe) + ' → ' + (ZE_DATA[r.target_id] ? ZE_DATA[r.target_id].label : r.target_display) +
        '<br>' + familyLabel(r.relation_family) +
        '<br>intensité=' + signalBand(r.signal_strength, r.stability_score) +
        '<br>signal=' + r.signal_strength.toFixed(3) +
        '<br>stabilité=' + r.stability_score.toFixed(2) +
        '<br><i>Signal exploratoire, non causal.</i><extra></extra>',
      name: 'relation spatiale directe',
      showlegend: false
    }});
  }});
  pathRels.forEach(function(r) {{
    const lons = r.path.map(function(ze) {{ return CENTROIDS[ze].lon; }});
    const lats = r.path.map(function(ze) {{ return CENTROIDS[ze].lat; }});
    data.push({{
      type: 'scattergeo',
      lon: lons,
      lat: lats,
      mode: 'lines',
      line: {{
        width: 1.4 + 1.1 * Math.max(0, Math.min(1, r.signal_strength)),
        color: 'rgba(176,132,245,' + Math.max(0.40, Math.min(0.75, r.stability_score)) + ')',
        dash: 'dot'
      }},
      hovertemplate: r.path_labels.join(' → ') +
        '<br>chemin relationnel en ' + r.depth + ' pas' +
        '<br>intensité=' + signalBand(r.signal_strength, r.stability_score) +
        '<br>signal=' + r.signal_strength.toFixed(3) +
        '<br>stabilité=' + r.stability_score.toFixed(2) +
        '<br><i>Chemin exploratoire, non causal.</i><extra></extra>',
      name: 'chemin relationnel',
      showlegend: false
    }});
  }});
  // One node = one role = one label. A zone can be the origin, a direct
  // relation, an indirect bridge, or an indirect target -- never more than
  // one at a time, so its name is never drawn twice on the map.
  const nodeRoles = {{}};
  nodeRoles[selectedZe] = {{ label: ZE_DATA[selectedZe].label || selectedZe, role: 'origin', stability: 1 }};
  mapRels.forEach(function(r) {{
    if (!nodeRoles[r.target_id] && CENTROIDS[r.target_id]) {{
      nodeRoles[r.target_id] = {{
        label: ZE_DATA[r.target_id] ? ZE_DATA[r.target_id].label : r.target_display,
        role: 'direct',
        stability: r.stability_score
      }};
    }}
  }});
  pathRels.forEach(function(r) {{
    r.path.slice(1, -1).forEach(function(ze, i) {{
      if (!nodeRoles[ze] && CENTROIDS[ze]) {{
        nodeRoles[ze] = {{ label: r.path_labels[i + 1], role: 'bridge' }};
      }}
    }});
    if (!nodeRoles[r.target_id] && CENTROIDS[r.target_id]) {{
      nodeRoles[r.target_id] = {{ label: r.target_label, role: 'reached' }};
    }}
  }});

  function nodeIdsByRole(roles) {{
    return Object.keys(nodeRoles).filter(function(ze) {{ return roles.indexOf(nodeRoles[ze].role) !== -1; }});
  }}

  const originDirectIds = nodeIdsByRole(['origin', 'direct']);
  if (originDirectIds.length > 0) {{
    data.push({{
      type: 'scattergeo',
      lon: originDirectIds.map(function(ze) {{ return CENTROIDS[ze].lon; }}),
      lat: originDirectIds.map(function(ze) {{ return CENTROIDS[ze].lat; }}),
      mode: 'markers',
      text: originDirectIds.map(function(ze) {{
        return nodeRoles[ze].label + (nodeRoles[ze].role === 'origin' ? ' — zone sélectionnée' : ' — relation directe');
      }}),
      marker: {{
        size: originDirectIds.map(function(ze) {{ return nodeRoles[ze].role === 'origin' ? 10 : 6.5; }}),
        color: originDirectIds.map(function(ze) {{ return nodeRoles[ze].role === 'origin' ? '#D55E00' : '#0072B2'; }}),
        line: {{ width: 1, color: '#fff' }}
      }},
      hovertemplate: '%{{text}}<extra></extra>',
      name: 'zones directes',
      showlegend: false
    }});
  }}
  const bridgeIds = nodeIdsByRole(['bridge']);
  if (bridgeIds.length > 0) {{
    data.push({{
      type: 'scattergeo',
      lon: bridgeIds.map(function(ze) {{ return CENTROIDS[ze].lon; }}),
      lat: bridgeIds.map(function(ze) {{ return CENTROIDS[ze].lat; }}),
      mode: 'markers',
      marker: {{ size: 6.5, color: '#ffd180', symbol: 'circle', line: {{ width: 1, color: '#0f1220' }} }},
      text: bridgeIds.map(function(ze) {{ return nodeRoles[ze].label + ' — zone pont'; }}),
      hovertemplate: '%{{text}}<extra></extra>',
      name: 'zones ponts',
      showlegend: false
    }});
  }}
  const reachedIds = nodeIdsByRole(['reached']);
  if (reachedIds.length > 0) {{
    data.push({{
      type: 'scattergeo',
      lon: reachedIds.map(function(ze) {{ return CENTROIDS[ze].lon; }}),
      lat: reachedIds.map(function(ze) {{ return CENTROIDS[ze].lat; }}),
      mode: 'markers',
      marker: {{ size: 6.5, color: '#b084f5', symbol: 'circle', line: {{ width: 1, color: '#eef2ff' }} }},
      text: reachedIds.map(function(ze) {{ return nodeRoles[ze].label + ' — connexion indirecte'; }}),
      hovertemplate: '%{{text}}<extra></extra>',
      name: 'zones indirectes',
      showlegend: false
    }});
  }}
  const layout = {{
    geo: {{ fitbounds: 'geojson', visible: false, bgcolor: '#171b2d' }},
    margin: {{ t: 10, b: 10, l: 10, r: 10 }},
    height: 620,
    showlegend: false,
    paper_bgcolor: '#171b2d',
    plot_bgcolor: '#171b2d',
    font: {{ color: '#eef2ff' }}
  }};
  Plotly.newPlot('map-container', data, layout, {{displayModeBar: false}});
  document.getElementById('map-container').on('plotly_click', function(ev) {{
    const ze = ev.points[0].location || ev.points[0].text;
    selectZone(ze);
  }});
  renderMapRelationList(mapRels, pathRels);
}}

function selectZone(ze) {{
  selectedZe = ze;
  document.getElementById('ze-select').value = ze;
  renderMap();
  renderPrediction();
  renderSector();
  renderRelations();
  renderAnnualDetail();
  renderNeuralSignals();
}}

function formatNum(x) {{
  if (x === undefined || x === null || Number.isNaN(Number(x))) return '-';
  return Number(x).toLocaleString('fr-FR', {{maximumFractionDigits: 0}});
}}

function renderZoneSummary() {{
  const d = ZE_DATA[selectedZe];
  const observed = d.observed[selectedYear];
  const ridge = d.predictions.ridge ? d.predictions.ridge[selectedYear] : undefined;
  const sectorMap = d.sector_by_year[selectedYear] || {{}};
  let dom = '-';
  if (Object.keys(sectorMap).length > 0) {{
    dom = Object.entries(sectorMap).sort(function(a,b) {{ return b[1]-a[1]; }})[0][0];
  }}
  const neuralRows = NEURAL_SIGNALS[selectedYear] || [];
  const neuralTop = neuralRows.length > 0 ? neuralRows[0].label : '—';
  document.getElementById('zone-summary').innerHTML =
    '<h2>' + (d.label || selectedZe) + '</h2>' +
    '<div class="muted">Code ZE2020: ' + selectedZe + '</div>' +
    '<div class="kpis">' +
      '<div class="kpi"><div class="label">Année</div><div class="value">' + selectedYear + '</div></div>' +
      '<div class="kpi"><div class="label">Observé</div><div class="value">' + formatNum(observed) + '</div></div>' +
      '<div class="kpi"><div class="label">Ridge contrôle</div><div class="value">' + formatNum(ridge) + '</div></div>' +
      '<div class="kpi"><div class="label">Secteur dominant</div><div class="value">' + dom + '</div></div>' +
      '<div class="kpi"><div class="label">Signal neuronal dominant</div><div class="value">' + neuralTop + '</div></div>' +
    '</div>';
}}

function renderMapRelationList(mapRels, pathRels) {{
  renderZoneSummary();
  if (mapRels.length === 0 && (!pathRels || pathRels.length === 0)) {{
    document.getElementById('relation-map-list').innerHTML =
      '<div class="caveat-line">Aucune relation spatiale active pour ce filtre et cette année.</div>';
    return;
  }}
  const rows = mapRels.map(function(r) {{
    return '<tr><td>' + (ZE_DATA[r.target_id] ? ZE_DATA[r.target_id].label : r.target_display) + '</td><td class="muted">' + r.target_id + '</td><td>' +
      familyLabel(r.relation_family) + '</td><td>' + signalBand(r.signal_strength, r.stability_score) + '</td><td>' +
      r.signal_strength.toFixed(3) + '</td><td>' +
      r.stability_score.toFixed(2) + '</td></tr>';
  }}).join('');
  document.getElementById('relation-map-list').innerHTML =
    '<table class="rel-table"><tr><th>Zone reliée</th><th>Code</th><th>Famille</th><th>Intensité</th><th>Signal</th><th>Stab.</th></tr>' +
    rows + '</table>' + pathTableHtml(pathRels || []);
}}

function pathTableHtml(pathRels) {{
  if (!pathRels || pathRels.length === 0) return '';
  const rows = pathRels.map(function(r) {{
    return '<tr><td>' + r.path_labels.join(' → ') + '</td><td>' + r.depth + '</td><td>' +
      signalBand(r.signal_strength, r.stability_score) + '</td><td>' +
      r.signal_strength.toFixed(3) + '</td><td>' + r.stability_score.toFixed(2) + '</td></tr>';
  }}).join('');
  return '<br><b>Chemins relationnels indirects</b>' +
    '<table class="rel-table"><tr><th>Chemin</th><th>Pas</th><th>Intensité</th><th>Signal</th><th>Stab.</th></tr>' +
    rows + '</table>';
}}

function renderPrediction() {{
  const d = ZE_DATA[selectedZe];
  const years = Object.keys(d.observed).map(Number).sort();
  const observedVals = years.map(function(y) {{ return d.observed[y]; }});
  const traces = [{{ x: years, y: observedVals, mode: 'lines+markers', name: 'Observé', line: {{color:'#eef2ff', width:2}} }}];
  let hasPrediction = false;
  Object.keys(d.predictions).forEach(function(model) {{
    const predYears = Object.keys(d.predictions[model]).map(Number).sort();
    if (predYears.length > 0) {{
      hasPrediction = true;
      traces.push({{
        x: predYears,
        y: predYears.map(function(y) {{ return d.predictions[model][y]; }}),
        mode: 'markers',
        name: 'Prévu (' + model + ')'
      }});
    }}
  }});
  traces.push({{
    x: [selectedYear, selectedYear],
    y: [Math.min.apply(null, observedVals), Math.max.apply(null, observedVals)],
    mode: 'lines',
    name: 'Année sélectionnée',
    line: {{color:'#D55E00', width:1.5, dash:'dot'}},
    hoverinfo: 'skip'
  }});
  const layout = {{ margin: {{t:20,b:30,l:48,r:10}}, height: 300, legend: {{orientation:'h'}}, yaxis: {{rangemode:'tozero', gridcolor:'#30364f'}}, xaxis: {{gridcolor:'#30364f'}}, paper_bgcolor:'#171b2d', plot_bgcolor:'#171b2d', font:{{color:'#eef2ff'}} }};
  Plotly.newPlot('prediction-chart', traces, layout, {{displayModeBar: false}});
  if (!hasPrediction) {{
    document.getElementById('prediction-chart').insertAdjacentHTML('beforeend',
      '<div class="caveat-line">{prediction_not_found_message}</div>');
  }}
}}

function renderSector() {{
  const d = ZE_DATA[selectedZe];
  const info = document.getElementById('sector-info');
  info.innerHTML =
    (d.dominant_sector ? '<span class="badge">Secteur dominant: ' + d.dominant_sector + '</span>' : '') +
    (d.diversity !== null ? '<span class="badge">Diversité: ' + d.diversity.toFixed(2) + '</span>' : '');

  const sectorMap = d.sector_by_year[selectedYear] || {{}};
  const sectors = Object.entries(sectorMap).sort(function(a,b) {{ return b[1] - a[1]; }});
  const traces = [{{
    y: sectors.map(function(kv) {{ return kv[0] + ' — ' + (d.sector_labels[kv[0]] || kv[0]); }}),
    x: sectors.map(function(kv) {{ return kv[1]; }}),
    text: sectors.map(function(kv) {{ return (kv[1] * 100).toFixed(1) + '%'; }}),
    textposition: 'auto',
    type: 'bar',
    orientation: 'h',
    marker: {{color: sectors.map(function(kv) {{ return SECTOR_COLOR_INDEX[kv[0]] || '#4aa3ff'; }})}}
  }}];
  const layout = {{
    margin: {{t:12,b:28,l:215,r:16}},
    height: 320,
    showlegend: false,
    paper_bgcolor:'#171b2d',
    plot_bgcolor:'#171b2d',
    font:{{color:'#eef2ff'}},
    xaxis:{{tickformat:'.0%', gridcolor:'#30364f', range:[0, Math.max(0.35, Math.max.apply(null, sectors.map(function(kv) {{ return kv[1]; }})) * 1.15)]}},
    yaxis:{{gridcolor:'#30364f', automargin:true}}
  }};
  renderSectorLegend('sector-legend', sectors.map(function(kv) {{ return kv[0]; }}));
  Plotly.newPlot('sector-chart', traces, layout, {{displayModeBar: false}});

  const cmp = document.getElementById('sector-pred-compare');
  if (d.sector_pred_compare.length === 0) {{
    cmp.innerHTML = '<div class="caveat-line">{prediction_not_found_message}</div>';
  }} else {{
    let rows = d.sector_pred_compare.filter(function(r) {{ return r.year === selectedYear; }}).slice(0, 18).map(function(r) {{
      return '<tr><td>' + r.year + '</td><td>' + r.sector_code + '</td><td>' + r.model +
        '</td><td>' + r.y_true.toFixed(3) + '</td><td>' + r.y_pred.toFixed(3) + '</td></tr>';
    }}).join('');
    cmp.innerHTML = '<div class="caveat-line">Comparaison sectorielle descriptive, non utilisée comme preuve de prévision.</div>' +
      '<table class="rel-table"><tr><th>Année</th><th>Secteur</th><th>Modèle</th><th>Réel</th><th>Prévu</th></tr>' + rows + '</table>';
  }}
}}

function renderRelations() {{
  const d = ZE_DATA[selectedZe];
  let rels = activeRelationsForSelected(false);
  const graphDepth = Number(document.getElementById('graph-depth-select').value);
  const pathRels = graphDepth > 1
    ? graphPathsForSelected(graphDepth).slice(0, 5)
    : [];

  const top = sortAndFilterRelations(rels).slice(0, Number(document.getElementById('topk-select').value));
  const angleStep = (2 * Math.PI) / Math.max(top.length, 1);
  const xs = [0], ys = [0], texts = [ZE_DATA[selectedZe].label || selectedZe];
  const edgeTraces = [];
  top.forEach(function(r, i) {{
    const angle = i * angleStep;
    const x = Math.cos(angle), y = Math.sin(angle);
    xs.push(x); ys.push(y); texts.push(r.target_display || r.target_id);
    edgeTraces.push({{
      x: [0, x], y: [0, y], mode: 'lines',
      line: {{ width: Math.max(1, r.signal_strength * 6), color: 'rgba(247,131,79,' + Math.max(0.18, r.stability_score) + ')' }},
      showlegend: false, hoverinfo: 'skip'
    }});
  }});
  const nodeTrace = {{ x: xs, y: ys, mode: 'markers+text', text: texts, textposition: 'top center',
    marker: {{ size: [20].concat(top.map(function() {{ return 12; }})), color: ['#f7834f'].concat(top.map(function(r) {{ return r.target_type === 'ZE2020' ? '#4aa3ff' : '#b084f5'; }})), line:{{width:1,color:'#eef2ff'}} }} }};
  const layout = {{ margin: {{t:10,b:10,l:10,r:10}}, height: 280, xaxis: {{visible:false}}, yaxis: {{visible:false}}, showlegend: false, paper_bgcolor:'#171b2d', plot_bgcolor:'#171b2d', font:{{color:'#eef2ff'}} }};
  Plotly.newPlot('relation-graph', edgeTraces.concat([nodeTrace]), layout, {{displayModeBar: false}});

  const byStability = rels.slice().sort(function(a,b) {{ return b.stability_score - a.stability_score; }}).slice(0,5);
  const byStrength = rels.slice().sort(function(a,b) {{ return b.signal_strength - a.signal_strength; }}).slice(0,5);
  const byMedium = rels.slice().filter(function(r) {{ return r.signal_strength >= 0.35 && r.signal_strength < 0.9 && r.stability_score >= 0.25; }}).sort(function(a,b) {{ return b.stability_score - a.stability_score || b.signal_strength - a.signal_strength; }}).slice(0,5);
  function tableHtml(title, list) {{
    let rows = list.map(function(r) {{
      return '<tr><td>' + (r.target_display || r.target_id) + '</td><td class="muted">' + r.target_id + '</td><td>' + familyLabel(r.relation_family) +
        '</td><td>' + r.signal_strength.toFixed(3) + '</td><td>' + r.stability_score.toFixed(2) + '</td></tr>';
    }}).join('');
    return '<b>' + title + '</b><table class="rel-table"><tr><th>Relation</th><th>Code</th><th>Famille</th><th>Signal</th><th>Stab.</th></tr>' + rows + '</table>';
  }}
  document.getElementById('relation-tables').innerHTML =
    tableHtml('Relations les plus stables', byStability) +
    tableHtml('Signaux les plus forts', byStrength) +
    tableHtml('Signaux moyens récurrents', byMedium) +
    pathTableHtml(pathRels);

  const ex = document.getElementById('relation-examples');
  const stable = byStability[0];
  if (!stable) {{
    ex.innerHTML = '';
    return;
  }}
  ex.innerHTML = '<div class="example-box">Lecture: ' + (d.label || selectedZe) +
    ' présente un signal relationnel actif avec ' + (stable.target_display || stable.target_id) +
    ' dans la famille ' + stable.relation_family +
    '. Ce signal est exploratoire et doit être interprété par un spécialiste.</div>';
}}

function renderAnnualDetail() {{
  const d = ZE_DATA[selectedZe];
  const sectorMap = d.sector_by_year[selectedYear] || {{}};
  const sectors = Object.entries(sectorMap).sort(function(a,b) {{ return b[1]-a[1]; }}).slice(0, 5);
  const rels = activeRelationsForSelected(false).sort(function(a,b) {{ return b.stability_score - a.stability_score; }}).slice(0, 5);
  const sectorRows = sectors.map(function(kv) {{
    return '<tr><td>' + kv[0] + '</td><td>' + (kv[1] * 100).toFixed(1) + '%</td></tr>';
  }}).join('');
  const relRows = rels.map(function(r) {{
    return '<tr><td>' + familyLabel(r.relation_family) + '</td><td>' + (r.target_display || r.target_id) + '</td><td>' +
      r.stability_score.toFixed(2) + '</td></tr>';
  }}).join('');
  document.getElementById('annual-detail').innerHTML =
    '<div class="caveat-line">Lecture filtrée par année. Association exploratoire, non causale.</div>' +
    '<b>Composition sectorielle principale</b><table class="rel-table"><tr><th>Secteur</th><th>Part</th></tr>' + sectorRows + '</table>' +
    '<br><b>Relations actives les plus stables</b><table class="rel-table"><tr><th>Famille</th><th>Cible</th><th>Stab.</th></tr>' + relRows + '</table>';
}}

function renderNeuralSignals() {{
  const rows = (NEURAL_SIGNALS[selectedYear] || []).map(function(r) {{
    const width = Math.min(100, Math.abs(r.importance_score));
    const color = r.importance_score >= 0 ? '#4aa3ff' : '#ef5350';
    return '<tr><td>' + r.label + '<div class="muted">' + r.feature + '</div></td><td>' +
      r.importance_score.toFixed(3) + '<div class="scorebar"><span style="width:' + width + '%;background:' + color + '"></span></div></td></tr>';
  }}).join('');
  document.getElementById('neural-signals').innerHTML =
    '<div class="caveat-line">Réseau MLP relationnel: importance par permutation, pas une relation entre deux entités.</div>' +
    '<b>Signaux utilisés par la couche neuronale</b><table class="rel-table"><tr><th>Signal</th><th>Importance</th></tr>' + rows + '</table>';
}}

populateZeSelect();
setNetworkMode('clear');
selectZone(selectedZe);
mountIntegratedDashboard();

function mountIntegratedDashboard() {{
  const frame = document.getElementById('integrated-comparison-dashboard');
  if(!frame || !INTEGRATED_DASHBOARD_B64) return;
  const binary = atob(INTEGRATED_DASHBOARD_B64);
  const bytes = new Uint8Array(binary.length);
  for(let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  frame.srcdoc = new TextDecoder('utf-8').decode(bytes);
}}
</script>

</body>
</html>
"""


def render_dashboard(
    ze_data: dict,
    map_metrics: dict,
    geometry: dict | None,
    centroids: dict[str, dict[str, float]],
    neural_signals: dict[int, list[dict]],
    sector_codes: list[str],
) -> str:
    architecture_cards = "\n".join(
        f'<div class="arch-card"><div class="step-no">{num}</div>'
        f'<div class="step-title">{title}</div>'
        f'<div class="step-text">{text}</div>'
        f'<div class="step-badge">{badge}</div></div>'
        for num, title, text, badge in ARCHITECTURE_STEPS
    )

    plotly_tag, plotly_dep = _plotly_js_tag()
    integrated_dashboard_b64 = _integrated_comparison_dashboard_b64(plotly_tag)
    plotly_dep_note = (
        "Plotly intégré localement, fonctionnement hors ligne."
        if plotly_dep == "local_embedded"
        else "Plotly via CDN, connexion internet requise."
    )

    zones = sorted(ze_data.keys())
    years = sorted({int(year) for data in ze_data.values() for year in data["observed"]})
    relation_year_starts = [
        int(r["year_start"])
        for data in ze_data.values()
        for r in data["relations"]
        if r.get("target_type") == "ZE2020"
    ]
    min_relation_year = min(relation_year_starts) if relation_year_starts else min(years)

    return HTML_TEMPLATE.format(
        plotly_tag=plotly_tag,
        plotly_dep_note=plotly_dep_note,
        global_caveat=GLOBAL_CAVEAT,
        relational_caveat=RELATIONAL_CAVEAT,
        geometry_blocked_message=GEOMETRY_NOT_AUDITED_MESSAGE,
        prediction_not_found_message=PREDICTION_NOT_FOUND_MESSAGE,
        architecture_cards=architecture_cards,
        ze_data_json=json.dumps(ze_data),
        map_metrics_json=json.dumps(map_metrics),
        geometry_json=json.dumps(geometry) if geometry is not None else "null",
        centroids_json=json.dumps(centroids),
        neural_signals_json=json.dumps(neural_signals),
        integrated_dashboard_b64=integrated_dashboard_b64,
        zones_json=json.dumps(zones),
        sector_codes_json=json.dumps(sector_codes),
        min_year=min(years),
        min_relation_year=min_relation_year,
        max_year=max(years),
    )


def build_dashboard() -> str:
    clean_panel = load_clean_panel()
    panel_codes = set(clean_panel["ze2020"].unique())

    predictions = load_predictions()
    sector_panel = load_sector_panel()
    sector_features = load_sector_features()
    sector_graph_predictions = load_sector_graph_predictions()
    relation_signals = load_relation_signals()
    relation_examples = load_relation_examples()
    neural_feature_signals = load_neural_feature_signals()
    geometry = load_geometry(panel_codes=panel_codes)
    centroids = build_geometry_centroids(geometry)
    neural_signals = build_neural_signal_data(neural_feature_signals)
    sector_codes = build_sector_color_index(sector_panel)

    ze_data = build_ze_data(
        clean_panel,
        predictions,
        sector_panel,
        sector_features,
        sector_graph_predictions,
        relation_signals,
        relation_examples,
    )
    map_metrics = build_map_metrics(ze_data, relation_signals)

    return render_dashboard(ze_data, map_metrics, geometry, centroids, neural_signals, sector_codes)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    html = build_dashboard()
    OUT_PATH.write_text(html, encoding="utf-8")
    print(f"Saved: {OUT_PATH} ({len(html) // 1024} KB)")


if __name__ == "__main__":
    main()
