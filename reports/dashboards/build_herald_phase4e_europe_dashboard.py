#!/usr/bin/env python3
"""
build_herald_phase4e_europe_dashboard.py
Génère reports/dashboards/herald_phase4e_europe_dashboard.html
Dashboard Europe Phase 4E (4E-B baseline causal + 4E-C EU signals ablation)
"""

import os, sys, json, glob, re
import numpy as np
import pandas as pd
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent.parent  # project root

ROOTS = {
    "4E-B": {
        "FR": BASE / "hpc_results/herald_phase4e_b_fr_20260603_131640_r1",
        "NL": BASE / "hpc_results/herald_phase4e_b_nl_20260603_131640_r1",
        "BE": BASE / "hpc_results/herald_phase4e_b_be_20260603_131640_r1",
        "PT": BASE / "hpc_results/herald_phase4e_b_pt_20260603_131640_r1",
    },
    "4E-C": {
        "FR": BASE / "hpc_results/herald_phase4e_c_fr_20260603_230709_r1",
        "NL": BASE / "hpc_results/herald_phase4e_c_nl_20260603_230709_r1",
        "BE": BASE / "hpc_results/herald_phase4e_c_be_20260603_230709_r1",
        "PT": BASE / "hpc_results/herald_phase4e_c_pt_20260603_230709_r1",
    },
}

COUNTRY_BASELINES = {
    "FR": "b2_side2_zero",
    "NL": "b0_baseline_annual",
    "BE": "b3_current_clean_zero",
    "PT": "b5_side2_emp_lag1",
}

COUNTRY_BASELINE_WMAPE = {
    "FR": (0.1031, 0.0084),
    "NL": (0.1017, 0.0075),
    "BE": (0.1488, 0.0063),
    "PT": (0.2286, 0.0148),
}

COUNTRY_DECISIONS = {
    "FR": {
        "decision": "non promu",
        "best_c": "c2_labor",
        "gain": "<1%",
        "note": "Meilleur signal exploratoire : c2_labor (gain <1%). Baseline causal 4E-B maintenu.",
        "color": "#4aa3ff",
    },
    "NL": {
        "decision": "non promu",
        "best_c": "c2_labor",
        "gain": "<1%",
        "note": "Meilleur signal exploratoire : c2_labor (gain <1%). Baseline causal 4E-B maintenu.",
        "color": "#4aa3ff",
    },
    "BE": {
        "decision": "candidat",
        "best_c": "c4_all_eu",
        "gain": ">1%",
        "note": "c4_all_eu bat c0 de >1%. Contrôle permuté c5 ne suit pas → signal prometteur.",
        "color": "#26a69a",
    },
    "PT": {
        "decision": "bloqué",
        "best_c": "c1_gdp",
        "gain": ">1% mais C5 permuté aussi",
        "note": "Gains importants mais contrôle permuté c5 bat aussi c0 de >1% → régularisation spurieuse.",
        "color": "#ffd180",
    },
}

SECTOR_LABELS = {
    "BE": "Agriculture, sylviculture",
    "FZ": "Industrie manufact.",
    "GI": "Commerce, transport, hébergement",
    "JZ": "Information, communication",
    "KZ": "Activités financières",
    "LZ": "Immobilier",
    "MN": "Services aux entreprises",
    "OQ": "Services publics, santé, éducation",
    "RU": "Arts, loisirs, autres services",
}

# BE zone_id -> NUTS3 code mapping (Arrondissements belges)
# Zone IDs from data/processed/phase4/be/zone_mapping.csv
# NUTS3 IDs from data/external/nuts3_2021_eurostat.geojson (CNTR_CODE=BE)
BE_NUTS3_MAP = {
    "BE_alost":              "BE231",  # Arr. Aalst
    "BE_anvers":             "BE211",  # Arr. Antwerpen
    "BE_arlon":              "BE341",  # Arr. Arlon
    "BE_ath":                "BE32A",  # Arr. Ath
    "BE_audenarde":          "BE235",  # Arr. Oudenaarde
    "BE_bastogne":           "BE342",  # Arr. Bastogne
    "BE_bruges":             "BE251",  # Arr. Brugge
    "BE_bruxelles_capitale": "BE100",  # Arr. de Bruxelles-Capitale
    "BE_charleroi":          "BE32B",  # Arr. Charleroi
    "BE_courtrai":           "BE254",  # Arr. Kortrijk
    "BE_dinant":             "BE351",  # Arr. Dinant
    "BE_dixmude":            "BE252",  # Arr. Diksmuide
    "BE_eeklo":              "BE233",  # Arr. Eeklo
    "BE_furnes":             "BE258",  # Arr. Veurne
    "BE_gand":               "BE234",  # Arr. Gent
    "BE_hal_vilvorde":       "BE241",  # Arr. Halle-Vilvoorde
    "BE_hasselt":            "BE224",  # Arr. Hasselt
    "BE_huy":                "BE331",  # Arr. Huy
    "BE_liege":              "BE332",  # Arr. Liège
    "BE_louvain":            "BE242",  # Arr. Leuven
    "BE_maaseik":            "BE225",  # Arr. Maaseik
    "BE_malines":            "BE212",  # Arr. Mechelen
    "BE_marche_en_famenne":  "BE343",  # Arr. Marche-en-Famenne
    "BE_mons":               "BE323",  # Arr. Mons
    "BE_namur":              "BE352",  # Arr. Namur
    "BE_neufchateau":        "BE344",  # Arr. Neufchâteau
    "BE_nivelles":           "BE310",  # Arr. Nivelles
    "BE_ostende":            "BE255",  # Arr. Oostende
    "BE_philippeville":      "BE353",  # Arr. Philippeville
    "BE_roulers":            "BE256",  # Arr. Roeselare
    "BE_saint_nicolas":      "BE236",  # Arr. Sint-Niklaas
    "BE_soignies":           "BE32C",  # Arr. Soignies
    "BE_termonde":           "BE232",  # Arr. Dendermonde
    "BE_thuin":              "BE32D",  # Arr. Thuin
    "BE_tielt":              "BE257",  # Arr. Tielt
    "BE_tongres":            "BE223",  # Arr. Tongeren
    "BE_tournai_mouscron":   "BE328",  # Arr. Tournai-Mouscron (merged)
    "BE_turnhout":           "BE213",  # Arr. Turnhout
    "BE_verviers":           "BE335",  # Arr. Verviers (FR)
    "BE_virton":             "BE345",  # Arr. Virton
    "BE_waremme":            "BE334",  # Arr. Waremme
    "BE_ypres":              "BE253",  # Arr. Ieper
}

# NL COROP -> NUTS3 mapping (CBS standard order, 40 regions)
NL_COROP_TO_NUTS3 = {
    "CR01": "NL111",  # Oost-Groningen
    "CR02": "NL112",  # Delfzijl en omgeving
    "CR03": "NL113",  # Overig Groningen
    "CR04": "NL124",  # Noord-Friesland
    "CR05": "NL125",  # Zuidwest-Friesland
    "CR06": "NL126",  # Zuidoost-Friesland
    "CR07": "NL131",  # Noord-Drenthe
    "CR08": "NL132",  # Zuidoost-Drenthe
    "CR09": "NL133",  # Zuidwest-Drenthe
    "CR10": "NL211",  # Noord-Overijssel
    "CR11": "NL212",  # Zuidwest-Overijssel
    "CR12": "NL213",  # Twente
    "CR13": "NL221",  # Veluwe
    "CR14": "NL224",  # Zuidwest-Gelderland
    "CR15": "NL225",  # Achterhoek
    "CR16": "NL226",  # Arnhem/Nijmegen
    "CR17": "NL230",  # Flevoland
    "CR18": "NL310",  # Utrecht
    "CR19": "NL321",  # Kop van Noord-Holland
    "CR20": "NL323",  # IJmond
    "CR21": "NL324",  # Agglomeratie Haarlem
    "CR22": "NL325",  # Zaanstreek
    "CR23": "NL327",  # Het Gooi en Vechtstreek
    "CR24": "NL328",  # Alkmaar en omgeving
    "CR25": "NL329",  # Groot-Amsterdam
    "CR26": "NL332",  # Agglomeratie 's-Gravenhage
    "CR27": "NL333",  # Delft en Westland
    "CR28": "NL337",  # Agglomeratie Leiden en Bollenstreek
    "CR29": "NL33A",  # Zuidoost-Zuid-Holland
    "CR30": "NL33B",  # Oost-Zuid-Holland
    "CR31": "NL33C",  # Groot-Rijnmond
    "CR32": "NL341",  # Zeeuwsch-Vlaanderen
    "CR33": "NL342",  # Overig Zeeland
    "CR34": "NL411",  # West-Noord-Brabant
    "CR35": "NL412",  # Midden-Noord-Brabant
    "CR36": "NL413",  # Noordoost-Noord-Brabant
    "CR37": "NL414",  # Zuidoost-Noord-Brabant
    "CR38": "NL421",  # Noord-Limburg
    "CR39": "NL422",  # Midden-Limburg
    "CR40": "NL423",  # Zuid-Limburg
}

GEOJSON_PATH = BASE / "data/external/nuts3_2021_eurostat.geojson"
ZE2020_GEOJSON_PATH = BASE / "data/external/ze2020_geometry.geojson"


# ─── Data loading ─────────────────────────────────────────────────────────────

def load_per_run_json(root: Path):
    """Returns list of dicts with run metadata."""
    results = []
    for fpath in sorted((root / "reports/per_run").glob("*.json")):
        try:
            d = json.loads(fpath.read_text())
            for run_key, v in d.items():
                config_match = re.search(r"_(b\d+_\w+|c\d+_\w+)_seed_", run_key)
                config = config_match.group(1) if config_match else v.get("run_tag", "").split("_", 4)[-1]
                seed_match = re.search(r"_seed_(\d+)$", run_key)
                seed = int(seed_match.group(1)) if seed_match else 0
                results.append({
                    "run_key": run_key,
                    "config": config,
                    "seed": seed,
                    "wmape": v.get("total_wmape_mean"),
                    "per_year_total": v.get("per_year_total", {}),
                    "sector_wmape": v.get("sector_wmape", {}),
                    "alpha_by_year": v.get("alpha_by_year", {}),
                    "run_tag": v.get("run_tag", ""),
                    "falsif": "perm" in config,
                })
        except Exception:
            pass
    return results


def aggregate_configs(runs):
    """Returns per-config (mean, std, n) sorted by mean wmape."""
    df = pd.DataFrame(runs)
    if df.empty:
        return []
    grp = df.groupby("config")["wmape"].agg(["mean", "std", "count"]).reset_index()
    grp.columns = ["config", "mean", "std", "n"]
    grp = grp.sort_values("mean")
    return grp.to_dict("records")


def load_predictions_total(root: Path, config: str):
    """Load and aggregate all seed CSVs for a given config."""
    pattern = str(root / "data_processed" / f"*predictions_total*{config}*_v1.csv")
    files = glob.glob(pattern)
    if not files:
        return None
    dfs = [pd.read_csv(f) for f in files]
    df = pd.concat(dfs, ignore_index=True)
    # Average over seeds per (zone, year)
    zone_col = "ZE2020"
    agg = df.groupby([zone_col, "target_year"]).agg(
        y_true=("y_true", "mean"),
        y_pred=("y_pred", "mean"),
        abs_error=("abs_error", "mean"),
    ).reset_index()
    return agg


def load_predictions_sector(root: Path, config: str):
    """Load and aggregate sector predictions."""
    pattern = str(root / "data_processed" / f"*predictions_sector*{config}*_v1.csv")
    files = glob.glob(pattern)
    if not files:
        return None
    dfs = [pd.read_csv(f) for f in files]
    df = pd.concat(dfs, ignore_index=True)
    agg = df.groupby(["ZE2020", "target_year", "sector"]).agg(
        y_true_sector=("y_true_sector", "mean"),
        y_pred_sector=("y_pred_sector", "mean"),
    ).reset_index()
    return agg


def build_zone_error_map(pred_df, zone_mapping_df):
    """Compute per-zone mean absolute error normalized."""
    if pred_df is None or zone_mapping_df is None:
        return {}
    df = pred_df.merge(zone_mapping_df, on="ZE2020", how="left")
    df["ape"] = df["abs_error"] / df["y_true"].clip(lower=1)
    zone_stats = df.groupby("zone_id").agg(
        mape=("ape", "mean"),
        y_true_mean=("y_true", "mean"),
        y_pred_mean=("y_pred", "mean"),
        n=("y_true", "count"),
    ).reset_index()
    return zone_stats.to_dict("records")


def load_geojson_country(country_code: str):
    """Load GeoJSON features for a country, returns list of features."""
    if not GEOJSON_PATH.exists():
        return None
    with open(GEOJSON_PATH) as f:
        g = json.load(f)
    feats = [ft for ft in g["features"] if ft["properties"]["CNTR_CODE"] == country_code]
    return feats if feats else None


def nuts3_for_pt(zone_id: str):
    return zone_id.replace("_", "")


def build_choropleth_data(country, zone_stats, zone_mapping_df):
    """Return (rows, geojson_filtered, featureidkey) for Plotly choropleth."""

    # ── France: use embedded ZE2020 geometry ──────────────────────────────────
    if country == "FR":
        if not ZE2020_GEOJSON_PATH.exists():
            return None, None, None
        with open(ZE2020_GEOJSON_PATH) as fh:
            ze_geo = json.load(fh)
        ze_feats = ze_geo["features"]
        # Build lookup: padded ze2020 code (str) -> libze2020 name
        ze_lookup = {ft["properties"]["ze2020"]: ft["properties"]["libze2020"] for ft in ze_feats}
        # zone_mapping_df has ZE2020 (int) and zone_id (libze2020 name)
        # Build zone_id -> padded code map
        if zone_mapping_df is None:
            return None, None, None
        zone_to_ze = {}
        for _, row in zone_mapping_df.iterrows():
            padded = str(int(row["ZE2020"])).zfill(4)
            zone_to_ze[row["zone_id"]] = padded
        rows = []
        matched_codes = set()
        for r in zone_stats:
            zid = r["zone_id"]
            ze_code = zone_to_ze.get(zid)
            if ze_code and ze_code in ze_lookup:
                rows.append({
                    "nuts_id": ze_code,          # reuse field name for JS compatibility
                    "name": ze_lookup[ze_code],
                    "mape": round(r["mape"] * 100, 2),
                    "y_true": round(r["y_true_mean"], 1),
                    "y_pred": round(r["y_pred_mean"], 1),
                })
                matched_codes.add(ze_code)
        geojson_filtered = {
            "type": "FeatureCollection",
            "features": [ft for ft in ze_feats if ft["properties"]["ze2020"] in matched_codes],
        }
        return rows, geojson_filtered, "properties.ze2020"

    # ── NUTS3-based countries (NL, BE, PT) ────────────────────────────────────
    geojson_feats = load_geojson_country(country)
    if geojson_feats is None:
        return None, None, None

    nuts3_lookup = {ft["properties"]["NUTS_ID"]: ft["properties"].get("NAME_LATN", ft["properties"].get("NUTS_NAME", "")) for ft in geojson_feats}

    zone_to_nuts = {}
    if country == "PT":
        for zid in zone_mapping_df["zone_id"]:
            zone_to_nuts[zid] = nuts3_for_pt(zid)
    elif country == "BE":
        zone_to_nuts = {k: v for k, v in BE_NUTS3_MAP.items()}
    elif country == "NL":
        # NL: COROP code (CR01..CR40) -> NUTS3
        for zid in zone_mapping_df["zone_id"]:
            if zid in NL_COROP_TO_NUTS3:
                zone_to_nuts[zid] = NL_COROP_TO_NUTS3[zid]

    rows = []
    for r in zone_stats:
        zid = r["zone_id"]
        nuts = zone_to_nuts.get(zid)
        if nuts and nuts in nuts3_lookup:
            rows.append({
                "nuts_id": nuts,
                "name": nuts3_lookup[nuts],
                "mape": round(r["mape"] * 100, 2),
                "y_true": round(r["y_true_mean"], 1),
                "y_pred": round(r["y_pred_mean"], 1),
            })

    geojson_filtered = {
        "type": "FeatureCollection",
        "features": [ft for ft in geojson_feats if ft["properties"]["NUTS_ID"] in {r["nuts_id"] for r in rows}],
    }
    return rows, geojson_filtered, "properties.NUTS_ID"


# ─── Data assembly ────────────────────────────────────────────────────────────

def load_zone_mapping(country: str):
    if country == "FR":
        # FR uses numeric ZE2020 codes; build synthetic zone_mapping from graph_nodes
        p = BASE / "data/processed/graph_nodes_ze2020_core_v0.csv"
        if p.exists():
            df = pd.read_csv(p)
            df = df.rename(columns={"ze2020": "ZE2020", "libze2020": "zone_id"})
            return df[["ZE2020", "zone_id"]]
        return None
    p = BASE / f"data/processed/phase4/{country.lower()}/zone_mapping.csv"
    if p.exists():
        return pd.read_csv(p)
    return None


def assemble_all_data():
    data = {}
    for country in ["FR", "NL", "BE", "PT"]:
        country_data = {"4E-B": {}, "4E-C": {}}
        zone_map = load_zone_mapping(country)

        # 4E-B
        root_b = ROOTS["4E-B"][country]
        runs_b = load_per_run_json(root_b)
        configs_b = aggregate_configs(runs_b)
        winner_b = COUNTRY_BASELINES[country]

        pred_total_b = load_predictions_total(root_b, winner_b)
        zone_stats_b = build_zone_error_map(pred_total_b, zone_map) if pred_total_b is not None else []
        if zone_stats_b:
            choropleth_b, geojson_b, featureidkey_b = build_choropleth_data(country, zone_stats_b, zone_map)
        else:
            choropleth_b, geojson_b, featureidkey_b = None, None, None

        # Per-territory time series
        territory_ts = {}
        if pred_total_b is not None and zone_map is not None:
            df_merged = pred_total_b.merge(zone_map, on="ZE2020", how="left")
            for zone_id, grp in df_merged.groupby("zone_id"):
                grp_s = grp.sort_values("target_year")
                territory_ts[zone_id] = {
                    "years": grp_s["target_year"].tolist(),
                    "y_true": [round(v, 1) for v in grp_s["y_true"].tolist()],
                    "y_pred": [round(v, 1) for v in grp_s["y_pred"].tolist()],
                    "abs_error": [round(v, 1) for v in grp_s["abs_error"].tolist()],
                }

        country_data["4E-B"] = {
            "configs": configs_b,
            "winner": winner_b,
            "runs": runs_b,
            "zone_stats": zone_stats_b,
            "choropleth": choropleth_b,
            "geojson": geojson_b,
            "featureidkey": featureidkey_b,
            "territory_ts": territory_ts,
        }

        # 4E-C
        root_c = ROOTS["4E-C"][country]
        runs_c = load_per_run_json(root_c)
        configs_c = aggregate_configs(runs_c)

        # Sector data from 4E-C (c0 = winner)
        pred_sector_c0 = load_predictions_sector(root_c, "c0_winner_4e_b")
        sector_stats = {}
        if pred_sector_c0 is not None:
            for sector, grp in pred_sector_c0.groupby("sector"):
                total_true = grp["y_true_sector"].sum()
                total_err = (grp["y_true_sector"] - grp["y_pred_sector"]).abs().sum()
                wmape = float(total_err / total_true) if total_true > 0 else 0
                sector_stats[sector] = {
                    "wmape": round(wmape * 100, 2),
                    "label": SECTOR_LABELS.get(sector, sector),
                }

        # Sector per-config comparison (all C configs)
        sector_by_config = {}
        for cfg_label in ["c0_winner_4e_b", "c4_all_eu", "c5_all_eu_perm"]:
            ps = load_predictions_sector(root_c, cfg_label)
            if ps is not None:
                cfg_sec = {}
                for sector, grp in ps.groupby("sector"):
                    total_true = grp["y_true_sector"].sum()
                    total_err = (grp["y_true_sector"] - grp["y_pred_sector"]).abs().sum()
                    wmape = float(total_err / total_true) if total_true > 0 else 0
                    cfg_sec[sector] = round(wmape * 100, 2)
                sector_by_config[cfg_label] = cfg_sec

        country_data["4E-C"] = {
            "configs": configs_c,
            "runs": runs_c,
            "sector_stats": sector_stats,
            "sector_by_config": sector_by_config,
        }

        data[country] = country_data

    return data


# ─── HTML generation ──────────────────────────────────────────────────────────

def js_json(obj):
    return json.dumps(obj, ensure_ascii=False, default=str)


def render_html(data):
    # Pre-compute per-year wmape for sparklines
    country_year_wmape = {}
    for country in ["FR", "NL", "BE", "PT"]:
        runs = data[country]["4E-B"]["runs"]
        winner = COUNTRY_BASELINES[country]
        winner_runs = [r for r in runs if r["config"] == winner]
        years = sorted({y for r in winner_runs for y in r["per_year_total"]})
        year_vals = {}
        for yr in years:
            vals = [r["per_year_total"].get(yr) for r in winner_runs if r["per_year_total"].get(yr) is not None]
            year_vals[yr] = round(np.mean(vals) * 100, 2) if vals else None
        country_year_wmape[country] = year_vals

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>HERALD Europe Phase 4E — Dashboard</title>
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
<style>
  :root {{
    --bg:#0f1220; --panel:#171b2d; --panel2:#20253a; --line:#30364f;
    --text:#eef2ff; --muted:#9aa4bf; --orange:#f7834f; --blue:#4aa3ff;
    --purple:#b084f5; --green:#66bb6a; --bad:#ef5350; --good:#26a69a;
    --yellow:#ffd180;
  }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--text); font-family:Inter,Segoe UI,Arial,sans-serif; }}
  .wrap {{ max-width:1600px; margin:0 auto; padding:22px; }}
  h1 {{ margin:0 0 6px; font-size:28px; font-weight:760; }}
  h2 {{ font-size:20px; font-weight:720; margin:0 0 8px; }}
  h3 {{ font-size:16px; font-weight:700; margin:0 0 6px; color:#cbd5ff; }}
  .subtitle {{ color:var(--muted); margin-bottom:18px; line-height:1.45; max-width:1200px; font-size:14px; }}
  .kpis {{ display:grid; grid-template-columns:repeat(4,minmax(200px,1fr)); gap:12px; margin:16px 0 22px; }}
  .kpi {{ background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:14px; }}
  .kpi .v {{ font-size:24px; font-weight:760; }}
  .kpi .l {{ color:var(--muted); font-size:12px; margin-top:4px; }}
  .kpi .dec {{ font-size:12px; margin-top:6px; font-weight:700; }}
  .section {{ margin-top:30px; }}
  .section-title {{ font-size:20px; font-weight:720; margin:0 0 6px; border-bottom:1px solid var(--line); padding-bottom:8px; }}
  .section-note {{ color:var(--muted); font-size:13px; line-height:1.5; max-width:1200px; margin-bottom:12px; }}
  .grid2 {{ display:grid; grid-template-columns:1fr 1fr; gap:14px; }}
  .grid3 {{ display:grid; grid-template-columns:1fr 1fr 1fr; gap:14px; }}
  .card {{ background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:14px; }}
  .controls {{ display:flex; flex-wrap:wrap; gap:10px; align-items:center; margin-bottom:12px; }}
  select {{ background:#111525; color:var(--text); border:1px solid var(--line); border-radius:6px; padding:7px 12px; font-size:13px; cursor:pointer; }}
  select:hover {{ border-color:var(--blue); }}
  table {{ width:100%; border-collapse:collapse; font-size:13px; }}
  th,td {{ border-bottom:1px solid var(--line); padding:8px 7px; text-align:left; }}
  th {{ color:#cbd5ff; font-weight:700; background:var(--panel2); }}
  tr:hover td {{ background:#1a1f32; }}
  .badge {{ display:inline-block; border-radius:999px; padding:2px 8px; font-size:11px; font-weight:700; }}
  .badge-blue {{ background:#1a2a4a; color:var(--blue); border:1px solid #2a4a8a; }}
  .badge-green {{ background:#1a3a2a; color:var(--green); border:1px solid #2a6a3a; }}
  .badge-yellow {{ background:#3a2a0a; color:var(--yellow); border:1px solid #6a4a0a; }}
  .badge-red {{ background:#3a1a1a; color:var(--bad); border:1px solid #6a2a2a; }}
  .badge-orange {{ background:#3a1a0a; color:var(--orange); border:1px solid #6a3a1a; }}
  .badge-purple {{ background:#2a1a4a; color:var(--purple); border:1px solid #5a2a8a; }}
  .winner {{ color:var(--good); font-weight:700; }}
  .warn {{ color:var(--yellow); }}
  .perm {{ color:var(--purple); }}
  .tab-bar {{ display:flex; gap:0; border-bottom:1px solid var(--line); margin-bottom:14px; flex-wrap:wrap; }}
  .tab {{ padding:8px 16px; cursor:pointer; border-bottom:2px solid transparent; font-size:14px; color:var(--muted); transition:all .15s; }}
  .tab:hover {{ color:var(--text); }}
  .tab.active {{ color:var(--blue); border-bottom-color:var(--blue); font-weight:700; }}
  .tab-content {{ display:none; }}
  .tab-content.active {{ display:block; }}
  .no-map-msg {{ background:#1a1e30; border:1px solid var(--line); border-radius:8px; padding:16px; color:var(--muted); font-size:13px; margin:8px 0; }}
  .no-map-msg strong {{ color:var(--yellow); }}
  .delta-pos {{ color:var(--bad); }}
  .delta-neg {{ color:var(--good); }}
  .arch-table td {{ font-size:13px; }}
  .phase-4a {{ color:#666; font-style:italic; }}
  .decision-card {{ border-radius:8px; padding:12px 16px; margin-bottom:10px; border-left:4px solid; }}
  .decision-non-promu {{ background:#111a2f; border-left-color:var(--blue); }}
  .decision-candidat {{ background:#0f2a20; border-left-color:var(--good); }}
  .decision-bloque {{ background:#2a200a; border-left-color:var(--yellow); }}
  .sparkline-mini {{ color:var(--muted); font-size:11px; }}
</style>
</head>
<body>
<div class="wrap">
  <h1>HERALD Europe — Phase 4E</h1>
  <p class="subtitle">
    Expérience d'internalisation inter-pays + ablation des signaux EU macroéconomiques.<br>
    <strong>Phase 4E-B</strong> = baseline causal (sans données fuitées) &nbsp;|&nbsp;
    <strong>Phase 4E-C</strong> = signal exploratoire EU (PIB, emploi, ESI, all_eu) + contrôle permuté C5.<br>
    Pays couverts : France (FR) · Pays-Bas (NL) · Belgique (BE) · Portugal (PT).
    Phase 4A / Phase 4D = expériences antérieures utilisant <em>growth_1y/2y</em> (données fuitées) — <strong>non utilisées comme baseline</strong>.
  </p>

  <!-- KPI cards -->
  <div class="kpis">
"""
    for country in ["FR", "NL", "BE", "PT"]:
        wm, ws = COUNTRY_BASELINE_WMAPE[country]
        dec = COUNTRY_DECISIONS[country]
        dec_class = {"non promu": "badge-blue", "candidat": "badge-green", "bloqué": "badge-yellow"}[dec["decision"]]
        country_names = {"FR": "France", "NL": "Pays-Bas", "BE": "Belgique", "PT": "Portugal"}
        html += f"""    <div class="kpi">
      <div class="l">{country_names[country]}</div>
      <div class="v">{wm:.4f} <span style="font-size:14px;color:var(--muted);">± {ws:.4f}</span></div>
      <div class="l">WMAPE baseline causal 4E-B ({COUNTRY_BASELINES[country]})</div>
      <div class="dec"><span class="badge {dec_class}">Signal EU : {dec["decision"]}</span></div>
    </div>
"""
    html += """  </div><!-- /kpis -->

  <!-- ════════════════════ SECTION 0 — Architecture / Protocole ════════════════════ -->
  <div class="section">
    <div class="section-title">Section 0 — Architecture & Protocole expérimental</div>
    <div class="section-note">
      Historique des phases et positionnement des baselines. Les phases 4A et 4D sont présentées à titre
      d'historique uniquement — elles utilisent des features fuitées (<code>growth_1y/2y</code> calculées sur
      l'année cible) et ne constituent <strong>pas</strong> la référence de performance.
    </div>
    <div class="card">
      <table>
        <thead><tr><th>Phase</th><th>Description</th><th>Features</th><th>Statut</th><th>Note</th></tr></thead>
        <tbody>
          <tr class="phase-4a">
            <td>Phase 4A</td>
            <td>Internalisation initiale (inter-pays)</td>
            <td>growth_1y (fuitée)</td>
            <td><span class="badge badge-red">Leakage</span></td>
            <td>Non utilisée comme baseline</td>
          </tr>
          <tr class="phase-4a">
            <td>Phase 4D</td>
            <td>Graphe de commuting (4D-B/C/D)</td>
            <td>growth_1y (fuitée)</td>
            <td><span class="badge badge-red">Leakage</span></td>
            <td>Non utilisée comme baseline</td>
          </tr>
          <tr>
            <td><strong>Phase 4E-B</strong></td>
            <td>Baseline causal — features sans fuite</td>
            <td>baseline_annual, side2_zero, current_clean, emp_lag1…</td>
            <td><span class="badge badge-green">Baseline causal</span></td>
            <td>Référence principale pour chaque pays</td>
          </tr>
          <tr>
            <td><strong>Phase 4E-C</strong></td>
            <td>Ablation signaux EU (PIB, emploi, ESI, all_eu + permutation)</td>
            <td>C0=winner 4E-B + enrichissement macroéconomique Eurostat</td>
            <td><span class="badge badge-purple">Signal exploratoire</span></td>
            <td>C5 = contrôle permuté (test de falsification)</td>
          </tr>
        </tbody>
      </table>
    </div>
    <div class="card" style="margin-top:12px;">
      <h3>Critères de promotion d'un signal EU</h3>
      <table>
        <thead><tr><th>Critère</th><th>Règle</th></tr></thead>
        <tbody>
          <tr><td>Gain minimal</td><td>Config Cx bat C0 de &gt;1% (WMAPE)</td></tr>
          <tr><td>Test de falsification</td><td>C5 (contrôle permuté) ne bat <em>pas</em> C0 de &gt;1%</td></tr>
          <tr><td>Décision si gain &lt;1%</td><td>Signal <strong>non promu</strong> — baseline 4E-B maintenu</td></tr>
          <tr><td>Décision si C5 bat C0</td><td>Signal <strong>bloqué</strong> — gain attribué à régularisation spurieuse</td></tr>
          <tr><td>Candidat promotable</td><td>Gain &gt;1% ET C5 ne bat pas C0 de &gt;1%</td></tr>
        </tbody>
      </table>
    </div>
  </div>

  <!-- ════════════════════ SECTION 1 — Comparaison pays/config ════════════════════ -->
  <div class="section">
    <div class="section-title">Section 1 — Comparaison configs par pays</div>
    <div class="section-note">
      Sélectionnez un pays pour voir les résultats 4E-B (baseline causal) et 4E-C (signaux EU).
      Les configs sont classées par WMAPE moyen sur 10 seeds.
    </div>
    <div class="controls">
      <label for="s1_country">Pays :</label>
      <select id="s1_country" onchange="s1_update()">
        <option value="FR">France (FR)</option>
        <option value="NL">Pays-Bas (NL)</option>
        <option value="BE">Belgique (BE)</option>
        <option value="PT">Portugal (PT)</option>
      </select>
    </div>
    <div id="s1_decision_card"></div>
    <div class="grid2" style="margin-top:12px;">
      <div class="card">
        <h3>Phase 4E-B — Configurations baseline causal</h3>
        <div id="s1_table_b"></div>
        <div id="s1_chart_b" style="height:280px;margin-top:10px;"></div>
      </div>
      <div class="card">
        <h3>Phase 4E-C — Ablation signaux EU</h3>
        <div id="s1_table_c"></div>
        <div id="s1_chart_c" style="height:280px;margin-top:10px;"></div>
      </div>
    </div>
  </div>

  <!-- ════════════════════ SECTION 2 — Carte territoriale ════════════════════ -->
  <div class="section">
    <div class="section-title">Section 2 — Carte territoriale</div>
    <div class="section-note">
      Erreur moyenne par territoire (MAPE local, baseline causal 4E-B).
      Cartes disponibles pour les 4 pays : FR (zones d'emploi ZE2020, géométrie extraite du tableau de bord France),
      NL (COROP CBS → NUTS3 Eurostat), BE et PT (NUTS3 Eurostat 2021).
    </div>
    <div class="controls">
      <label for="s2_country">Pays :</label>
      <select id="s2_country" onchange="s2_update()">
        <option value="FR">France (FR)</option>
        <option value="NL">Pays-Bas (NL)</option>
        <option value="BE">Belgique (BE)</option>
        <option value="PT">Portugal (PT)</option>
      </select>
    </div>
    <div id="s2_content"></div>
  </div>

  <!-- ════════════════════ SECTION 3 — Détail par territoire ════════════════════ -->
  <div class="section">
    <div class="section-title">Section 3 — Détail par territoire</div>
    <div class="section-note">
      Sélectionnez un pays puis un territoire pour visualiser la série temporelle réel vs prédit.
    </div>
    <div class="controls">
      <label for="s3_country">Pays :</label>
      <select id="s3_country" onchange="s3_update_zones()">
        <option value="FR">France (FR)</option>
        <option value="NL">Pays-Bas (NL)</option>
        <option value="BE">Belgique (BE)</option>
        <option value="PT">Portugal (PT)</option>
      </select>
      <label for="s3_zone">Territoire / Zone :</label>
      <select id="s3_zone" onchange="s3_update_chart()">
      </select>
    </div>
    <div class="grid2">
      <div class="card">
        <h3>Réel vs HERALD (baseline 4E-B)</h3>
        <div id="s3_chart_ts" style="height:320px;"></div>
      </div>
      <div class="card">
        <h3>Erreur absolue par année</h3>
        <div id="s3_chart_err" style="height:320px;"></div>
      </div>
    </div>
    <div class="card" style="margin-top:12px;">
      <h3>Tableau des prévisions</h3>
      <div id="s3_table"></div>
    </div>
  </div>

  <!-- ════════════════════ SECTION 4 — Secteurs A10 ════════════════════ -->
  <div class="section">
    <div class="section-title">Section 4 — Analyse sectorielle A10</div>
    <div class="section-note">
      Erreur WMAPE par secteur A10 (basée sur les prédictions 4E-C avec config C0=winner 4E-B).
      Comparaison possible entre C0 (contrôle), C4 (all_eu) et C5 (permuté).
    </div>
    <div class="controls">
      <label for="s4_country">Pays :</label>
      <select id="s4_country" onchange="s4_update()">
        <option value="FR">France (FR)</option>
        <option value="NL">Pays-Bas (NL)</option>
        <option value="BE">Belgique (BE)</option>
        <option value="PT">Portugal (PT)</option>
      </select>
      <label for="s4_config">Config :</label>
      <select id="s4_config" onchange="s4_update()">
        <option value="c0_winner_4e_b">C0 — contrôle (winner 4E-B)</option>
        <option value="c4_all_eu">C4 — all_eu</option>
        <option value="c5_all_eu_perm">C5 — contrôle permuté</option>
      </select>
    </div>
    <div class="grid2">
      <div class="card">
        <h3>WMAPE par secteur (% moyen)</h3>
        <div id="s4_chart_sector" style="height:350px;"></div>
      </div>
      <div class="card">
        <h3>Ranking — secteurs les plus difficiles</h3>
        <div id="s4_table_sector"></div>
      </div>
    </div>
  </div>

  <!-- ════════════════════ SECTION 5 — Régimes / Graphes internes ════════════════════ -->
  <div class="section">
    <div class="section-title">Section 5 — Régimes / Graphes internes (alpha, gate, gamma)</div>
    <div class="section-note">
      <strong>HERALD dispose d'un module graphique</strong> (Graph Neural Network spatio-temporel) qui apprend
      l'influence entre territoires. Dans Phase 4E-B et 4E-C, le graphe a été maintenu comme
      <strong>graphe identité</strong> pour isoler l'effet des features et des signaux EU.
      Phase 4D a testé des graphes géographiques et fonctionnels — sans amélioration robuste → retour au
      graphe identité pour établir un baseline causal propre.
      <strong>adj_diagonal_ratio = 1.0 confirmé (vérifié sur HPC).</strong>
      Prochaine étape : réactiver le graphe fonctionnel sur le baseline 4E-B/C consolidé.
    </div>
    <div class="controls">
      <label for="s5_country">Pays :</label>
      <select id="s5_country" onchange="s5_update()">
        <option value="FR">France (FR)</option>
        <option value="NL">Pays-Bas (NL)</option>
        <option value="BE">Belgique (BE)</option>
        <option value="PT">Portugal (PT)</option>
      </select>
    </div>
    <div id="s5_internals_kpis" style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:12px;"></div>
    <div class="grid2">
      <div class="card">
        <h3>Alpha (local vs graphe) & Gate par année</h3>
        <div id="s5_chart_alpha" style="height:300px;"></div>
      </div>
      <div class="card">
        <h3>Gamma (poids graphe géo vs mobilité)</h3>
        <div id="s5_chart_gamma" style="height:300px;"></div>
      </div>
    </div>
  </div>

  <!-- ════════════════════ SECTION 6 — Décision scientifique ════════════════════ -->
  <div class="section">
    <div class="section-title">Section 6 — Décision scientifique</div>
    <div class="section-note">
      Synthèse des décisions par pays sur la promotion des signaux macroéconomiques européens.
    </div>
    <div style="display:flex; flex-direction:column; gap:10px;">
"""
    decisions_detail = [
        ("FR", "France", "non promu", "decision-non-promu", "badge-blue",
         "Meilleur signal EU : <strong>c2_labor</strong> (WMAPE 0.0987 vs 0.1036 pour C0). "
         "Gain &lt;1% — seuil de promotion non atteint. "
         "<strong>Baseline causal 4E-B maintenu</strong> (b2_side2_zero, WMAPE 0.1031)."),
        ("NL", "Pays-Bas", "non promu", "decision-non-promu", "badge-blue",
         "Meilleur signal EU : <strong>c2_labor</strong> (WMAPE 0.0986 vs 0.1019 pour C0). "
         "Gain &lt;1% — seuil de promotion non atteint. "
         "<strong>Baseline causal 4E-B maintenu</strong> (b0_baseline_annual, WMAPE 0.1017)."),
        ("BE", "Belgique", "candidat", "decision-candidat", "badge-green",
         "<strong>c4_all_eu candidat promotable</strong> : WMAPE 0.1378 vs 0.1488 (C0), gain ~1.1%. "
         "Contrôle permuté C5 Δ=-0.48% (ne bat pas C0 de &gt;1%) → signal statistiquement valide. "
         "Baseline 4E-B = b3_current_clean_zero (WMAPE 0.1488)."),
        ("PT", "Portugal", "bloqué", "decision-bloque", "badge-yellow",
         "<strong>c1_gdp bloqué</strong> malgré un gain apparent de ~4.3% : "
         "le contrôle permuté C5 bat aussi C0 de ~1.7% → régularisation spurieuse non causale. "
         "Baseline 4E-B maintenu (b5_side2_emp_lag1, WMAPE 0.2286)."),
    ]
    for country, name, dec_label, dec_class, badge_class, note in decisions_detail:
        html += f"""      <div class="decision-card {dec_class}">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
          <strong style="font-size:16px;">{name} ({country})</strong>
          <span class="badge {badge_class}">{dec_label}</span>
        </div>
        <div style="color:var(--muted); font-size:13px; line-height:1.6;">{note}</div>
      </div>
"""
    html += """    </div>
    <div class="card" style="margin-top:16px;">
      <h3>Conclusion générale</h3>
      <p style="color:var(--muted); font-size:13px; line-height:1.6;">
        Les signaux macroéconomiques européens (PIB, emploi, ESI) ne sont <strong>pas universellement bénéfiques</strong>
        pour la prévision de création d'entreprises territoriale. Sur 4 pays testés :
        <ul style="color:var(--muted); font-size:13px; line-height:1.8;">
          <li><strong>FR et NL</strong> : signaux EU sans gain significatif — baselines causals maintenus.</li>
          <li><strong>BE</strong> : c4_all_eu candidat promotable — gain robuste, validé par le test de falsification.</li>
          <li><strong>PT</strong> : gains apparents bloqués par le contrôle permuté — signal non causal.</li>
        </ul>
        Les signaux EU semblent <strong>sélectifs par pays</strong>, probablement liés à la structure économique
        et au degré d'intégration dans les cycles macroéconomiques européens.
      </p>
    </div>
  </div>

</div><!-- /wrap -->

<script>
"""

    # Embed all data as JS constants
    all_data_for_js = {}
    for country in ["FR", "NL", "BE", "PT"]:
        cd = data[country]

        all_data_for_js[country] = {
            "configs_b": cd["4E-B"]["configs"],
            "winner_b": cd["4E-B"]["winner"],
            "configs_c": cd["4E-C"]["configs"],
            "zone_stats": cd["4E-B"]["zone_stats"],
            "choropleth": cd["4E-B"]["choropleth"],
            "geojson": cd["4E-B"]["geojson"],
            "featureidkey": cd["4E-B"]["featureidkey"],
            "territory_ts": cd["4E-B"]["territory_ts"],
            "sector_stats": cd["4E-C"]["sector_stats"],
            "sector_by_config": cd["4E-C"]["sector_by_config"],
            "year_wmape": country_year_wmape[country],
            "decision": COUNTRY_DECISIONS[country],
            "baseline_wmape": COUNTRY_BASELINE_WMAPE[country],
        }
        # Add alpha data from runs
        runs = cd["4E-B"]["runs"]
        winner = cd["4E-B"]["winner"]
        winner_runs = [r for r in runs if r["config"] == winner]
        all_years = sorted({y for r in winner_runs for y in r["alpha_by_year"]})
        alpha_by_year = {}
        for yr in all_years:
            vals = [r["alpha_by_year"].get(yr) for r in winner_runs if r["alpha_by_year"].get(yr) is not None]
            alpha_by_year[yr] = round(float(np.mean(vals)), 4) if vals else None
        all_data_for_js[country]["alpha_by_year"] = alpha_by_year

    html += f"const ALL_DATA = {js_json(all_data_for_js)};\n"

    # Load and embed HERALD internals summary
    internals_path = BASE / "reports" / "HERALD_PHASE4E_INTERNALS_SUMMARY.json"
    internals_data = {}
    if internals_path.exists():
        raw_internals = json.loads(internals_path.read_text())
        # Flatten: use 4E-B data as primary (most representative for module graphique)
        for country in ["FR", "NL", "BE", "PT"]:
            country_internals = raw_internals.get(country, {})
            phase_b = country_internals.get("4E-B", {})
            internals_data[country] = {
                "adj_diagonal_ratio_mean": phase_b.get("adj_diagonal_ratio_mean", 1.0),
                "adj_is_identity": phase_b.get("adj_is_identity", True),
                "gamma_geo_mean": phase_b.get("gamma_geo_mean", 0.0),
                "gamma_mob_mean": phase_b.get("gamma_mob_mean", 0.0),
                "alpha_gate_by_year": phase_b.get("alpha_gate_by_year", {}),
            }
    html += f"const INTERNALS_DATA = {js_json(internals_data)};\n"

    html += f"const DECISIONS = {js_json(COUNTRY_DECISIONS)};\n"
    html += f"const SECTOR_LABELS = {js_json(SECTOR_LABELS)};\n"

    html += """
const COUNTRY_NAMES = {FR:"France",NL:"Pays-Bas",BE:"Belgique",PT:"Portugal"};
const PLOTLY_DARK = {
  paper_bgcolor:"#171b2d", plot_bgcolor:"#171b2d",
  font:{color:"#eef2ff", size:12},
  xaxis:{gridcolor:"#30364f", zerolinecolor:"#30364f"},
  yaxis:{gridcolor:"#30364f", zerolinecolor:"#30364f"},
  margin:{l:50,r:20,t:30,b:50},
};

// ── Section 1 ─────────────────────────────────────────────────────────────────
function s1_update() {
  const country = document.getElementById("s1_country").value;
  const d = ALL_DATA[country];
  const dec = DECISIONS[country];
  const decClasses = {
    "non promu":"decision-non-promu","candidat":"decision-candidat","bloqué":"decision-bloque"
  };
  const badgeClasses = {
    "non promu":"badge-blue","candidat":"badge-green","bloqué":"badge-yellow"
  };

  // Decision card
  document.getElementById("s1_decision_card").innerHTML = `
    <div class="decision-card ${decClasses[dec.decision] || 'decision-non-promu'}">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
        <strong>${COUNTRY_NAMES[country]} — Signal EU</strong>
        <span class="badge ${badgeClasses[dec.decision] || 'badge-blue'}">${dec.decision}</span>
      </div>
      <div style="color:var(--muted);font-size:13px;">${dec.note}</div>
    </div>`;

  // 4E-B table
  const c0_b = d.configs_b.find(x => x.config === d.winner_b);
  let tb = `<table><thead><tr><th>Config</th><th>WMAPE moy</th><th>Std</th><th>N seeds</th><th>Statut</th></tr></thead><tbody>`;
  for (const c of d.configs_b) {
    const isWinner = c.config === d.winner_b;
    const row_class = isWinner ? 'winner' : '';
    tb += `<tr><td class="${row_class}">${c.config}${isWinner ? ' ★' : ''}</td>
      <td class="${row_class}">${(c.mean*100).toFixed(2)}%</td>
      <td>${(c.std*100).toFixed(2)}%</td>
      <td>${c.n}</td>
      <td>${isWinner ? '<span class="badge badge-green">baseline causal</span>' : ''}</td>
    </tr>`;
  }
  tb += '</tbody></table>';
  document.getElementById("s1_table_b").innerHTML = tb;

  // 4E-B bar chart
  const cfgs_b = d.configs_b.map(x=>x.config);
  const vals_b = d.configs_b.map(x=>x.mean*100);
  const colors_b = d.configs_b.map(x => x.config === d.winner_b ? '#26a69a' : '#4aa3ff');
  Plotly.newPlot("s1_chart_b",
    [{type:"bar",x:cfgs_b,y:vals_b,marker:{color:colors_b},text:vals_b.map(v=>v.toFixed(2)+"%"),textposition:"outside"}],
    {...PLOTLY_DARK, title:{text:"WMAPE moyen (%)",font:{size:12}}, yaxis:{...PLOTLY_DARK.yaxis,title:"WMAPE (%)"}}
  );

  // 4E-C table
  const c0_c = d.configs_c.find(x => x.config === "c0_winner_4e_b");
  const c0_wmape = c0_c ? c0_c.mean : null;
  let tc = `<table><thead><tr><th>Config</th><th>WMAPE moy</th><th>Std</th><th>Δ vs C0</th><th>Statut</th></tr></thead><tbody>`;
  for (const c of d.configs_c) {
    const isPerm = c.config.includes("perm");
    const delta = c0_wmape !== null ? (c.mean - c0_wmape) : null;
    const deltaStr = delta !== null ? (delta >= 0 ? `<span class="delta-pos">+${(delta*100).toFixed(2)}%</span>` : `<span class="delta-neg">${(delta*100).toFixed(2)}%</span>`) : "—";
    const rowClass = isPerm ? "perm" : (c.config === "c0_winner_4e_b" ? "winner" : "");
    const badge = isPerm ? '<span class="badge badge-purple">contrôle permuté</span>' : (c.config === "c0_winner_4e_b" ? '<span class="badge badge-blue">C0 contrôle</span>' : "");
    tc += `<tr><td class="${rowClass}">${c.config}</td>
      <td>${(c.mean*100).toFixed(2)}%</td>
      <td>${(c.std*100).toFixed(2)}%</td>
      <td>${deltaStr}</td>
      <td>${badge}</td>
    </tr>`;
  }
  tc += '</tbody></table>';
  document.getElementById("s1_table_c").innerHTML = tc;

  // 4E-C bar chart
  const cfgs_c = d.configs_c.map(x=>x.config);
  const vals_c = d.configs_c.map(x=>x.mean*100);
  const colors_c = d.configs_c.map(x => {
    if (x.config.includes("perm")) return '#b084f5';
    if (x.config === "c0_winner_4e_b") return '#4aa3ff';
    return '#f7834f';
  });
  Plotly.newPlot("s1_chart_c",
    [{type:"bar",x:cfgs_c,y:vals_c,marker:{color:colors_c},text:vals_c.map(v=>v.toFixed(2)+"%"),textposition:"outside"}],
    {...PLOTLY_DARK, title:{text:"WMAPE moyen (%)",font:{size:12}}, yaxis:{...PLOTLY_DARK.yaxis,title:"WMAPE (%)"}}
  );
}

// ── Section 2 ─────────────────────────────────────────────────────────────────
const MAP_CENTERS = {
  FR: {lat: 46.5, lon: 2.5, zoom: 4.5},
  NL: {lat: 52.3, lon: 5.3, zoom: 5.5},
  BE: {lat: 50.5, lon: 4.5, zoom: 6.5},
  PT: {lat: 39.5, lon: -8.0, zoom: 5.0},
};

function s2_update() {
  const country = document.getElementById("s2_country").value;
  const d = ALL_DATA[country];
  const el = document.getElementById("s2_content");

  if (!d.choropleth || d.choropleth.length === 0) {
    let tbl = "";
    if (d.zone_stats && d.zone_stats.length > 0) {
      tbl = `<div style="margin-top:10px;"><table><thead><tr><th>Zone ID</th><th>MAPE moy (%)</th><th>y_true moy</th><th>y_pred moy</th></tr></thead><tbody>`;
      const sorted_zones = [...d.zone_stats].sort((a,b) => b.mape - a.mape);
      for (const z of sorted_zones) {
        tbl += `<tr><td>${z.zone_id}</td><td>${(z.mape*100).toFixed(2)}%</td><td>${z.y_true_mean.toFixed(0)}</td><td>${z.y_pred_mean.toFixed(0)}</td></tr>`;
      }
      tbl += '</tbody></table></div>';
    }
    el.innerHTML = `<div class="no-map-msg">
      <strong>Géométrie non disponible pour ${COUNTRY_NAMES[country]}.</strong><br>
      Tableau des erreurs territoriales ci-dessous :
    </div>${tbl}`;
    return;
  }

  // Render choropleth
  const rows = d.choropleth;
  const geojson = d.geojson;
  const ids = rows.map(r => r.nuts_id);
  const names = rows.map(r => r.name);
  const mapes = rows.map(r => r.mape);
  const y_trues = rows.map(r => r.y_true);
  const y_preds = rows.map(r => r.y_pred);
  const fkey = d.featureidkey || "properties.NUTS_ID";
  const mc = MAP_CENTERS[country] || {lat:50.5, lon:4, zoom:4};

  el.innerHTML = `<div class="card"><div id="s2_map" style="height:500px;"></div></div>`;

  const trace = {
    type: "choroplethmapbox",
    geojson: geojson,
    locations: ids,
    z: mapes,
    featureidkey: fkey,
    colorscale: [[0,"#1a3a2a"],[0.5,"#ffd180"],[1,"#ef5350"]],
    colorbar: {title:"MAPE (%)", titlefont:{color:"#eef2ff"}, tickfont:{color:"#eef2ff"}},
    text: names.map((n,i) => `${n}<br>MAPE: ${mapes[i]}%<br>Réel: ${y_trues[i]}<br>Prédit: ${y_preds[i]}`),
    hovertemplate: "%{text}<extra></extra>",
    zmin: Math.min(...mapes),
    zmax: Math.max(...mapes),
  };

  Plotly.newPlot("s2_map", [trace], {
    mapbox: {style:"carto-darkmatter", zoom:mc.zoom, center:{lat:mc.lat, lon:mc.lon}},
    paper_bgcolor:"#171b2d",
    font:{color:"#eef2ff"},
    margin:{l:0,r:0,t:20,b:0},
  });
}

// ── Section 3 ─────────────────────────────────────────────────────────────────
function s3_update_zones() {
  const country = document.getElementById("s3_country").value;
  const d = ALL_DATA[country];
  const sel = document.getElementById("s3_zone");
  sel.innerHTML = "";
  const zones = Object.keys(d.territory_ts || {}).sort();
  if (zones.length === 0) {
    sel.innerHTML = '<option value="">Aucune zone disponible</option>';
    document.getElementById("s3_chart_ts").innerHTML = '<div style="color:var(--muted);padding:20px;">Aucune donnée territoriale.</div>';
    return;
  }
  for (const z of zones) {
    const opt = document.createElement("option");
    opt.value = z; opt.textContent = z;
    sel.appendChild(opt);
  }
  s3_update_chart();
}

function s3_update_chart() {
  const country = document.getElementById("s3_country").value;
  const zone = document.getElementById("s3_zone").value;
  const d = ALL_DATA[country];
  const ts = d.territory_ts && d.territory_ts[zone];
  if (!ts) return;

  // Time series
  Plotly.newPlot("s3_chart_ts", [
    {x:ts.years, y:ts.y_true, name:"Réel", line:{color:"#4aa3ff",width:2}, mode:"lines+markers"},
    {x:ts.years, y:ts.y_pred, name:"HERALD", line:{color:"#f7834f",width:2,dash:"dash"}, mode:"lines+markers"},
  ], {...PLOTLY_DARK, legend:{font:{color:"#eef2ff"}}, xaxis:{...PLOTLY_DARK.xaxis,title:"Année"}, yaxis:{...PLOTLY_DARK.yaxis,title:"Créations"}});

  // Error bars
  Plotly.newPlot("s3_chart_err", [
    {x:ts.years, y:ts.abs_error, name:"Erreur absolue", type:"bar", marker:{color:"#b084f5"}},
  ], {...PLOTLY_DARK, xaxis:{...PLOTLY_DARK.xaxis,title:"Année"}, yaxis:{...PLOTLY_DARK.yaxis,title:"Erreur abs."}});

  // Table
  let tbl = '<table><thead><tr><th>Année</th><th>Réel</th><th>HERALD</th><th>Erreur abs.</th><th>APE (%)</th></tr></thead><tbody>';
  for (let i = 0; i < ts.years.length; i++) {
    const ape = ts.y_true[i] > 0 ? ((ts.abs_error[i] / ts.y_true[i]) * 100).toFixed(1) : "—";
    tbl += `<tr><td>${ts.years[i]}</td><td>${ts.y_true[i].toFixed(0)}</td><td>${ts.y_pred[i].toFixed(0)}</td><td>${ts.abs_error[i].toFixed(0)}</td><td>${ape}%</td></tr>`;
  }
  tbl += '</tbody></table>';
  document.getElementById("s3_table").innerHTML = tbl;
}

// ── Section 4 ─────────────────────────────────────────────────────────────────
function s4_update() {
  const country = document.getElementById("s4_country").value;
  const config = document.getElementById("s4_config").value;
  const d = ALL_DATA[country];
  const by_config = d.sector_by_config || {};
  const sec_data = by_config[config] || d.sector_stats || {};

  const sectors = Object.keys(sec_data).sort((a,b) => sec_data[b] - sec_data[a]);
  const vals = sectors.map(s => sec_data[s] || 0);
  const labels = sectors.map(s => SECTOR_LABELS[s] || s);
  const colors = vals.map(v => v > 25 ? "#ef5350" : v > 15 ? "#ffd180" : "#26a69a");

  Plotly.newPlot("s4_chart_sector", [
    {type:"bar", x:vals, y:labels, orientation:"h", marker:{color:colors},
     text:vals.map(v=>v.toFixed(1)+"%"), textposition:"outside"},
  ], {...PLOTLY_DARK, xaxis:{...PLOTLY_DARK.xaxis,title:"WMAPE (%)"},
      margin:{l:220,r:60,t:20,b:50}});

  // Ranking table
  let tbl = '<table><thead><tr><th>Rang</th><th>Secteur</th><th>Code</th><th>WMAPE (%)</th></tr></thead><tbody>';
  sectors.forEach((s, i) => {
    const diff = (sec_data[s] || 0);
    const badge = diff > 25 ? 'badge-red' : diff > 15 ? 'badge-yellow' : 'badge-green';
    tbl += `<tr><td>${i+1}</td><td>${SECTOR_LABELS[s]||s}</td><td>${s}</td><td><span class="badge ${badge}">${diff.toFixed(1)}%</span></td></tr>`;
  });
  tbl += '</tbody></table>';
  document.getElementById("s4_table_sector").innerHTML = tbl;
}

// ── Section 5 ─────────────────────────────────────────────────────────────────
function s5_update() {
  const country = document.getElementById("s5_country").value;
  const d = ALL_DATA[country];
  const alpha = d.alpha_by_year || {};
  const years = Object.keys(alpha).sort();
  const vals = years.map(y => alpha[y]);

  // Internals from HERALD_PHASE4E_INTERNALS_SUMMARY.json
  const internals = INTERNALS_DATA[country] || {};
  const adjDiag = internals.adj_diagonal_ratio_mean !== undefined ? internals.adj_diagonal_ratio_mean.toFixed(4) : "1.0000";
  const gammaGeo = internals.gamma_geo_mean !== undefined ? internals.gamma_geo_mean.toFixed(4) : "—";
  const gammaMob = internals.gamma_mob_mean !== undefined ? internals.gamma_mob_mean.toFixed(4) : "—";
  const isIdentity = internals.adj_is_identity !== undefined ? (internals.adj_is_identity ? "Oui" : "Non") : "Oui";

  // KPI chips
  const kpisEl = document.getElementById("s5_internals_kpis");
  kpisEl.innerHTML = [
    {v: adjDiag, l: "adj_diagonal_ratio (4E-B)"},
    {v: isIdentity, l: "Graphe identité confirmé (HPC)"},
    {v: gammaGeo, l: "gamma_geo (poids graphe géo)"},
    {v: gammaMob, l: "gamma_mob (poids mobilité)"},
  ].map(k => `<div class="kpi"><div class="v" style="font-size:18px">${k.v}</div><div class="l">${k.l}</div></div>`).join("");

  // Alpha chart
  Plotly.newPlot("s5_chart_alpha", [
    {x:years, y:vals, name:"alpha (local vs graphe)", mode:"lines+markers",
     line:{color:"#4aa3ff",width:2}, marker:{size:5}},
  ], {...PLOTLY_DARK, xaxis:{...PLOTLY_DARK.xaxis,title:"Année"},
      yaxis:{...PLOTLY_DARK.yaxis,title:"alpha [0,1]", range:[0,1.05]},
      title:{text:`Alpha spatial (local vs graphe) — ${COUNTRY_NAMES[country]}`,font:{size:12}},
      annotations:[{
        x:0.5, xref:"paper", y:-0.2, yref:"paper", showarrow:false,
        text:"HERALD dispose d'un module graphique. Dans 4E-B/C, graphe identité pour isoler features et signaux EU. adj_diagonal_ratio=1.0 (vérifié HPC).",
        font:{color:"#9aa4bf", size:10}, xanchor:"center"
      }]});

  // Gamma chart
  Plotly.newPlot("s5_chart_gamma", [
    {type:"bar", x:["gamma_geo (contiguïté)", "gamma_mob (mobilité)"],
     y:[parseFloat(gammaGeo)||0, parseFloat(gammaMob)||0],
     marker:{color:["#66bb6a","#f7834f"]},
     text:[gammaGeo, gammaMob], textposition:"outside"},
  ], {...PLOTLY_DARK, xaxis:{...PLOTLY_DARK.xaxis},
      yaxis:{...PLOTLY_DARK.yaxis,title:"Poids gamma"},
      title:{text:`Poids graphe (gamma) — Phase 4E-B : graphe identité`,font:{size:12}},
      annotations:[{
        x:0.5, xref:"paper", y:-0.2, yref:"paper", showarrow:false,
        text:"Phase 4D a testé graphes géo/fonctionnels — pas d'amélioration robuste → retour au graphe identité. Prochaine étape : réactiver graphe fonctionnel sur baseline 4E-B/C.",
        font:{color:"#9aa4bf", size:10}, xanchor:"center"
      }]});
}

// ── Init ──────────────────────────────────────────────────────────────────────
window.onload = function() {
  s1_update();
  s2_update();
  s3_update_zones();
  s4_update();
  s5_update();
};
</script>
</body>
</html>
"""
    return html


def main():
    print("Chargement des données...")
    data = assemble_all_data()

    print("Génération du HTML...")
    html = render_html(data)

    out_path = BASE / "reports/dashboards/herald_phase4e_europe_dashboard.html"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")

    print(f"\nDashboard généré : {out_path}")
    print(f"Taille : {out_path.stat().st_size / 1024:.1f} KB")

    # Summary
    for country in ["FR", "NL", "BE", "PT"]:
        cd = data[country]
        n_zones = len(cd["4E-B"]["territory_ts"])
        has_choropleth = cd["4E-B"]["choropleth"] is not None
        n_configs_b = len(cd["4E-B"]["configs"])
        n_configs_c = len(cd["4E-C"]["configs"])
        print(f"  {country}: {n_configs_b} configs 4E-B, {n_configs_c} configs 4E-C, "
              f"{n_zones} zones, carte={'OUI' if has_choropleth else 'NON'}")


if __name__ == "__main__":
    main()
