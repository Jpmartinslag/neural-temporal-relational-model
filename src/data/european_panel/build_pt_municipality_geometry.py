"""
Build Portugal continental municipality (concelho) geometry for the
Observatory v0.4.1 visual upgrade.

No municipal-level geometry existed in the repo before this script. Two
official/reproducible candidate sources were evaluated:

  1. Eurostat/GISCO LAU 2021 (https://gisco-services.ec.europa.eu/distribution/v2/lau/)
     — official, versioned, but at FREGUESIA (civil parish, n=3092) granularity
     for Portugal, not municipality. Would require dissolving by the 4-digit
     INE "Dicofre" municipality code embedded in LAU_ID[:4] (verified: GISCO
     LAU_ID prefix "1006" == INE Dicofre "1006" for Caldas da Rainha).
  2. geoapi.pt (https://json.geoapi.pt/) — a free aggregator that redistributes
     Direção-Geral do Território (DGT) / Carta Administrativa Oficial de
     Portugal (CAOP) municipal boundaries directly at concelho granularity,
     with the official Dicofre code and name attached to every feature
     (GeoJSON properties include "Dicofre", "Concelho", "Distrito" — the
     standard CAOP schema).

This script uses source (2): it already provides municipality-level geometry
(no dissolve needed) with the official 4-digit Dicofre code, traceable to
DGT/CAOP. Each response is cached to data/external/portugal/geometry/raw/
(not committed — regenerable, see manifest for checksums) so re-runs are
idempotent and do not re-download.

Crosswalk: our PT panel (`data/processed/european_panel/pt_municipal_sector_panel.csv`)
uses a different, INE-internal 7-digit geocod (NUTS2013/2024 vintage-dependent,
per DEC-062 harmonisation) with a `region_name` field. Matching is done by
NORMALISED MUNICIPALITY NAME (lowercase, accent-stripped, punctuation-stripped)
between the panel's 278 distinct (region_id, region_name) pairs and geoapi.pt's
308 (Dicofre, name) pairs. No code-to-code mapping was assumed reproducible
across the two schemes.

Output:
  data/processed/geometries/pt_municipalities_continental.geojson
    — FeatureCollection, properties.panel_id = our 7-digit region_id,
      properties.dicofre, properties.name, properties.distrito
  data/processed/geometries/pt_municipalities_continental_manifest.json
    — source, fetch date, checksum, match coverage, unmatched names
"""
from __future__ import annotations

import hashlib
import json
import re
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests

REPO_ROOT = Path(__file__).resolve().parents[3]
RAW_DIR = REPO_ROOT / "data/external/portugal/geometry/raw"
OUT_GEOJSON = REPO_ROOT / "data/processed/geometries/pt_municipalities_continental.geojson"
OUT_MANIFEST = REPO_ROOT / "data/processed/geometries/pt_municipalities_continental_manifest.json"
PANEL_PATH = REPO_ROOT / "data/processed/european_panel/pt_municipal_sector_panel.csv"

GEOAPI_BASE = "https://json.geoapi.pt"
N_EXPECTED_TOTAL = 308   # 278 continental + 19 Açores + 11 Madeira
N_EXPECTED_CONTINENTAL = 278
TIMEOUT = 20
MAX_WORKERS = 8
# CAOP source geometry is very high resolution (~4,500 coordinate points per
# municipality on average); simplify for dashboard embedding. 0.001 deg
# (~110m at this latitude) keeps national-scale visual fidelity while
# cutting file size by ~25x (29.7 MB -> 1.2 MB).
SIMPLIFY_TOLERANCE_DEG = 0.001


def _normalise_name(name: str) -> str:
    name = unicodedata.normalize("NFKD", str(name))
    name = "".join(c for c in name if not unicodedata.combining(c))
    name = name.lower().strip()
    name = re.sub(r"[^a-z0-9 ]", "", name)
    name = re.sub(r"\s+", " ", name)
    return name


def fetch_municipios_list() -> list[str]:
    cache = RAW_DIR / "_municipios_list.json"
    if cache.exists():
        return json.loads(cache.read_text())
    resp = requests.get(f"{GEOAPI_BASE}/municipios", timeout=TIMEOUT)
    resp.raise_for_status()
    names = resp.json()
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(names))
    return names


def fetch_municipio(name: str) -> dict | None:
    safe = name.replace("/", "_")
    cache = RAW_DIR / f"{safe}.json"
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    try:
        resp = requests.get(f"{GEOAPI_BASE}/municipio/{name}", timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        cache.write_text(json.dumps(data), encoding="utf-8")
        return data
    except Exception as exc:  # noqa: BLE001
        print(f"WARN: failed to fetch {name!r}: {exc}")
        return None


def fetch_all_municipios(names: list[str]) -> dict[str, dict]:
    results: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {ex.submit(fetch_municipio, n): n for n in names}
        for fut in as_completed(futures):
            name = futures[fut]
            data = fut.result()
            if data:
                results[name] = data
    return results


def load_panel_crosswalk() -> pd.DataFrame:
    """region_id (7-digit geocod) -> region_name, continental only."""
    df = pd.read_csv(PANEL_PATH)
    cont = df[df["is_continental"] == True][["region_id", "region_name"]].drop_duplicates()
    cont = cont.astype({"region_id": str})
    return cont.reset_index(drop=True)


def build_geojson(municipios: dict[str, dict], crosswalk: pd.DataFrame) -> tuple[dict, dict]:
    cw_by_norm = {_normalise_name(r["region_name"]): r["region_id"]
                  for _, r in crosswalk.iterrows()}
    matched_norms: set[str] = set()
    features = []
    unmatched_geoapi = []

    for name, data in municipios.items():
        geojson_feat = data.get("geojson")
        if not geojson_feat or geojson_feat.get("type") != "Feature":
            continue
        props = geojson_feat.get("properties", {})
        dicofre = props.get("Dicofre") or data.get("codigoine")
        concelho_name = props.get("Concelho") or data.get("nome") or name
        norm = _normalise_name(concelho_name)
        panel_id = cw_by_norm.get(norm)
        if panel_id is None:
            unmatched_geoapi.append(concelho_name)
            continue
        matched_norms.add(norm)
        feat = {
            "type": "Feature",
            "properties": {
                "panel_id": panel_id,
                "name": concelho_name,
                "dicofre": dicofre,
                "distrito": props.get("Distrito") or data.get("distrito"),
            },
            "geometry": geojson_feat.get("geometry"),
        }
        features.append(feat)

    unmatched_panel = [
        r["region_name"] for _, r in crosswalk.iterrows()
        if _normalise_name(r["region_name"]) not in matched_norms
    ]

    fc = {"type": "FeatureCollection", "features": features}
    coverage = {
        "n_panel_continental": len(crosswalk),
        "n_matched": len(features),
        "n_unmatched_panel": len(unmatched_panel),
        "unmatched_panel_names": unmatched_panel,
        "n_unmatched_geoapi": len(unmatched_geoapi),
        "unmatched_geoapi_names": unmatched_geoapi[:30],
    }
    return fc, coverage


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    OUT_GEOJSON.parent.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    names = fetch_municipios_list()
    print(f"geoapi.pt municipios list: {len(names)} names")
    municipios = fetch_all_municipios(names)
    print(f"Fetched {len(municipios)}/{len(names)} municipality records "
          f"({time.time()-t0:.1f}s)")

    crosswalk = load_panel_crosswalk()
    print(f"Panel continental crosswalk: {len(crosswalk)} municipalities")

    fc, coverage = build_geojson(municipios, crosswalk)
    print(f"Matched {coverage['n_matched']}/{coverage['n_panel_continental']} "
          f"continental municipalities")
    if coverage["unmatched_panel_names"]:
        print(f"Unmatched panel names: {coverage['unmatched_panel_names']}")

    n_features_before_simplify = len(fc["features"])
    if fc["features"]:
        gdf = gpd.GeoDataFrame.from_features(fc["features"], crs="EPSG:4326")
        gdf["geometry"] = gdf.geometry.simplify(SIMPLIFY_TOLERANCE_DEG, preserve_topology=True)
        gdf["geometry"] = gdf.geometry.buffer(0)  # repair any simplify-induced invalidities
        n_invalid = int((~gdf.geometry.is_valid).sum())
        if n_invalid:
            print(f"WARN: {n_invalid} invalid geometries after simplify+buffer(0)")
        gdf.to_file(OUT_GEOJSON, driver="GeoJSON")
        fc = json.loads(OUT_GEOJSON.read_text(encoding="utf-8"))
    assert len(fc["features"]) == n_features_before_simplify, \
        "Simplification changed feature count — aborting"

    checksum = _sha256_file(OUT_GEOJSON)

    status = (
        "COMPLETE_278_278" if coverage["n_matched"] == N_EXPECTED_CONTINENTAL
        else "PARTIAL_DO_NOT_FABRICATE"
    )

    manifest = {
        "source": "geoapi.pt (redistributes DGT/CAOP municipal boundaries; "
                   "GeoJSON properties Dicofre/Concelho/Distrito match the official CAOP schema)",
        "source_url": GEOAPI_BASE,
        "fallback_official_source": (
            "Eurostat/GISCO LAU 2021 (gisco-services.ec.europa.eu/distribution/v2/lau/), "
            "freguesia-level, dissolve by LAU_ID[:4] == INE Dicofre code (verified equal "
            "to geoapi.pt codigoine for Caldas da Rainha=1006 and other spot checks)"
        ),
        "panel_crosswalk_source": str(PANEL_PATH.relative_to(REPO_ROOT)),
        "crosswalk_method": "normalised municipality name match (no code-to-code assumption)",
        "n_expected_continental": N_EXPECTED_CONTINENTAL,
        "n_expected_total_pt": N_EXPECTED_TOTAL,
        "coverage": coverage,
        "status": status,
        "geojson_sha256": checksum,
        "geojson_n_features": len(fc["features"]),
        "geojson_size_bytes": OUT_GEOJSON.stat().st_size,
        "simplify_tolerance_deg": SIMPLIFY_TOLERANCE_DEG,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "raw_cache_dir": str(RAW_DIR.relative_to(REPO_ROOT)) + " (not committed — regenerable; re-run this script)",
        "warning": (
            "Do NOT fabricate geometry for unmatched municipalities. "
            "If status != COMPLETE_278_278, the dashboard PT layer must fall back "
            "to the table/heatmap view for the unmatched subset or entirely."
        ),
    }
    OUT_MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Status: {status}")
    print(f"Wrote {OUT_GEOJSON} ({len(fc['features'])} features, sha256={checksum[:16]}...)")
    print(f"Wrote {OUT_MANIFEST}")


if __name__ == "__main__":
    main()
