#!/usr/bin/env python3
"""Search and classify BPE 2020 source candidates.

This script is intentionally conservative: it discovers candidate metadata and
probes small HTTP headers/ranges, but it does not ingest any dataset into the
project panel. A candidate must be validated separately before integration.
"""

from __future__ import annotations

import csv
import json
import os
import re
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
METADATA_DIR = ROOT / "metadata"
REPORTS_DIR = ROOT / "reports" / "archive" / "source_search"

OUT_CSV = METADATA_DIR / "bpe_2020_source_candidates_v0.csv"
OUT_JSON = REPORTS_DIR / "bpe_2020_source_candidates_v0.json"
OUT_MD = REPORTS_DIR / "BPE_2020_SOURCE_CANDIDATES_V0.md"

USER_AGENT = "project-recomm-bpe2020-source-scan/0.1"
TIMEOUT_SECONDS = 8
PROBE_HTTP = os.environ.get("BPE2020_PROBE_HTTP", "0") == "1"
socket.setdefaulttimeout(TIMEOUT_SECONDS)


DATA_GOUV_QUERIES = [
    "BPE 2020 INSEE",
    "Base permanente des équipements 2020 INSEE",
    "Base Permanente des Equipements 2020",
    "bpe20",
    "bpe 2020 services commerce",
    "bpe 2020 sport loisir",
    "bpe 2020 ensemble géolocalisé",
    '"bpe20_ensemble_csv.zip"',
    '"bpe20_ensemble.csv"',
]

REGIONAL_QUERY_TERMS = [
    "Auvergne Rhône Alpes",
    "Auvergne-Rhône-Alpes",
    "Bourgogne Franche Comté",
    "Bourgogne-Franche-Comté",
    "Bretagne",
    "Centre Val de Loire",
    "Centre-Val de Loire",
    "Corse",
    "Grand Est",
    "Hauts de France",
    "Hauts-de-France",
    "Ile de France",
    "Île-de-France",
    "Normandie",
    "Nouvelle Aquitaine",
    "Nouvelle-Aquitaine",
    "Occitanie",
    "Pays de la Loire",
    "Provence Alpes Côte d Azur",
    "Provence-Alpes-Côte d'Azur",
    "PACA",
    "Guadeloupe",
    "Martinique",
    "Guyane",
    "La Réunion",
    "Mayotte",
]

DEPARTMENT_QUERY_TERMS = [
    "Ain 01",
    "Aisne 02",
    "Allier 03",
    "Alpes-Maritimes 06",
    "Bouches-du-Rhône 13",
    "Calvados 14",
    "Charente-Maritime 17",
    "Côte-d'Or 21",
    "Côtes-d'Armor 22",
    "Doubs 25",
    "Finistère 29",
    "Gironde 33",
    "Hérault 34",
    "Ille-et-Vilaine 35",
    "Isère 38",
    "Loire-Atlantique 44",
    "Maine-et-Loire 49",
    "Manche 50",
    "Moselle 57",
    "Nord 59",
    "Oise 60",
    "Pas-de-Calais 62",
    "Puy-de-Dôme 63",
    "Bas-Rhin 67",
    "Haut-Rhin 68",
    "Rhône 69",
    "Saône-et-Loire 71",
    "Paris 75",
    "Seine-Maritime 76",
    "Seine-et-Marne 77",
    "Yvelines 78",
    "Somme 80",
    "Var 83",
    "Vaucluse 84",
    "Vendée 85",
    "Vienne 86",
    "Haute-Vienne 87",
    "Vosges 88",
    "Essonne 91",
    "Hauts-de-Seine 92",
    "Seine-Saint-Denis 93",
    "Val-de-Marne 94",
    "Val-d'Oise 95",
]

DATA_GOUV_QUERIES.extend([f"BPE 2020 {term}" for term in REGIONAL_QUERY_TERMS])
DATA_GOUV_QUERIES.extend([f"Base permanente équipements 2020 {term}" for term in REGIONAL_QUERY_TERMS])
DATA_GOUV_QUERIES.extend([f"BPE 2020 {term}" for term in DEPARTMENT_QUERY_TERMS])

CKAN_PORTALS = {
    "openig": "https://ckan.openig.org/api/3/action/package_search",
    "ternum_bfc": "https://trouver.ternum-bfc.fr/api/3/action/package_search",
    "grandlyon": "https://download.data.grandlyon.com/api/3/action/package_search",
    "open_data_hautsdefrance": "https://opendata.hautsdefrance.fr/api/3/action/package_search",
    "geo2france": "https://www.geo2france.fr/geonetwork/srv/api/search/records/_search",
}

ARCGIS_QUERIES = [
    "bpe20",
    "BPE 2020 INSEE",
    "Base Permanente Equipements 2020",
    "base permanente équipements 2020",
]
ARCGIS_QUERIES.extend([f"BPE 2020 {term}" for term in REGIONAL_QUERY_TERMS])
ARCGIS_QUERIES.extend([f"base permanente équipements 2020 {term}" for term in REGIONAL_QUERY_TERMS])
ARCGIS_QUERIES.extend([f"BPE20 {term}" for term in DEPARTMENT_QUERY_TERMS])

KNOWN_ODATASETS = {
    "public_ods_bpe_all_millesime": "https://public.opendatasoft.com/api/explore/v2.1/catalog/datasets/buildingref-france-bpe-all-millesime",
    "public_ods_bpe_geolocated_millesime": "https://public.opendatasoft.com/api/explore/v2.1/catalog/datasets/buildingref-france-bpe-all-geolocated-millesime",
    "pdl_ods_bpe_geolocated": "https://data.paysdelaloire.fr/api/explore/v2.1/catalog/datasets/base-permanente-des-equipements-ensemble-geolocalisee-france0",
}

ODATA_PORTALS = {
    "public": "https://public.opendatasoft.com/api/explore/v2.1/catalog/datasets",
    "paysdelaloire": "https://data.paysdelaloire.fr/api/explore/v2.1/catalog/datasets",
    "hautsdefrance": "https://opendata.hautsdefrance.fr/api/explore/v2.1/catalog/datasets",
    "grandparissud": "https://data.grandparissud.fr/api/explore/v2.1/catalog/datasets",
    "grandest": "https://www.datagrandest.fr/data4citizen/api/explore/v2.1/catalog/datasets",
}

DIRECT_HISTORICAL_URLS = [
    "https://www.insee.fr/fr/statistiques/fichier/3568629/bpe20_ensemble_csv.zip",
    "https://www.insee.fr/fr/statistiques/fichier/3568638/bpe20_ensemble_xy_csv.zip",
]


@dataclass
class Candidate:
    source_system: str
    dataset_title: str
    organization: str
    dataset_page: str
    resource_title: str
    resource_format: str
    resource_url: str
    year_signal: str
    coverage_signal: str
    access_status: str
    content_type: str
    content_length: str
    classification: str
    usable_for_mosaic: str
    notes: str


def log(message: str) -> None:
    print(message, flush=True)


def fetch_json(url: str) -> dict[str, Any] | None:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return {"data": [], "result": {"results": []}, "success": True, "_not_found": True}
        log(f"WARN fetch_json failed: {url} :: {exc}")
        return None
    except Exception as exc:  # noqa: BLE001 - scanner must keep going
        log(f"WARN fetch_json failed: {url} :: {exc}")
        return None


def probe_url(url: str) -> tuple[str, str, str]:
    if not url:
        return "", "", ""
    if not PROBE_HTTP:
        return "not_probed", "", ""

    headers = {"User-Agent": USER_AGENT}
    file_like = any(
        marker in url.lower()
        for marker in [
            ".csv",
            ".zip",
            ".geojson",
            ".json",
            "exports/csv",
            "download?",
            "/download/",
            "datasets/r/",
        ]
    )

    methods = ("HEAD", "GET") if file_like else ("HEAD",)
    for method in methods:
        req = urllib.request.Request(url, headers=headers, method=method)
        if method == "GET":
            req.add_header("Range", "bytes=0-2047")
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
                status = str(resp.status)
                ctype = resp.headers.get("content-type", "")
                clen = resp.headers.get("content-length", "")
                return status, ctype, clen
        except urllib.error.HTTPError as exc:
            ctype = exc.headers.get("content-type", "") if exc.headers else ""
            clen = exc.headers.get("content-length", "") if exc.headers else ""
            return str(exc.code), ctype, clen
        except Exception as exc:  # noqa: BLE001
            last_error = type(exc).__name__
            time.sleep(0.2)
    return f"error:{last_error}", "", ""


def text_blob(*parts: str) -> str:
    return " ".join(p or "" for p in parts).lower()


def detect_year(blob: str, url: str) -> str:
    years = sorted(set(re.findall(r"\b20(?:19|20|21|22|23|24)\b", blob + " " + url)))
    if "2020" in years:
        return "2020"
    if years:
        return ",".join(years)
    if re.search(r"\bbpe20\b", blob + " " + url):
        return "2020"
    return ""


def detect_coverage(blob: str, url: str) -> str:
    combined = blob + " " + url.lower()
    if any(x in combined for x in ["france métropolitaine", "france metropolitaine", " drom", "national", "france0", "france entière"]):
        return "national_or_france_claim"
    regional_markers = [
        "auvergne",
        "bourgogne",
        "franche-comté",
        "franche comté",
        "bretagne",
        "centre-val de loire",
        "centre val de loire",
        "corse",
        "grand est",
        "hauts-de-france",
        "hauts de france",
        "île-de-france",
        "ile-de-france",
        "ile de france",
        "normandie",
        "nouvelle-aquitaine",
        "nouvelle aquitaine",
        "occitanie",
        "pays de la loire",
        "provence",
        "paca",
        "guadeloupe",
        "martinique",
        "guyane",
        "réunion",
        "reunion",
        "mayotte",
        "région",
        "regionale",
        "régionale",
    ]
    if any(x in combined for x in regional_markers):
        return "regional"
    departmental_markers = [
        "seine-maritime",
        "departement",
        "département",
        "_76_",
        " 76 ",
        "bpe-76",
        "bpe 76",
        "calvados",
        "gironde",
        "nord",
        "paris",
        "yvelines",
        "essonne",
        "hauts-de-seine",
        "seine-saint-denis",
        "val-de-marne",
        "val-d'oise",
    ]
    if any(x in combined for x in departmental_markers):
        return "departmental"
    return ""


def classify(candidate: Candidate) -> Candidate:
    blob = text_blob(
        candidate.dataset_title,
        candidate.organization,
        candidate.dataset_page,
        candidate.resource_title,
        candidate.resource_url,
        candidate.notes,
    )
    has_bpe = "bpe" in blob or "base permanente" in blob
    year = candidate.year_signal
    coverage = candidate.coverage_signal
    status = candidate.access_status
    url = candidate.resource_url.lower()

    if "bpe20_ensemble_csv.zip" in url or "bpe20_ensemble.csv" in url:
        if status.startswith("2"):
            candidate.classification = "national_exact_candidate"
            candidate.usable_for_mosaic = "yes"
        elif status == "not_probed":
            candidate.classification = "national_exact_needs_probe"
            candidate.usable_for_mosaic = "maybe"
        else:
            candidate.classification = "national_exact_unavailable"
            candidate.usable_for_mosaic = "no"
        return candidate

    if not has_bpe:
        candidate.classification = "reject_not_bpe"
        candidate.usable_for_mosaic = "no"
    elif year != "2020":
        candidate.classification = "reject_wrong_or_unclear_year"
        candidate.usable_for_mosaic = "no"
    elif status == "not_probed" and coverage == "national_or_france_claim":
        candidate.classification = "national_claim_needs_probe"
        candidate.usable_for_mosaic = "maybe"
    elif status == "not_probed" and coverage in {"regional", "departmental"}:
        candidate.classification = f"{coverage}_mosaic_candidate_needs_probe"
        candidate.usable_for_mosaic = "maybe"
    elif not status.startswith("2"):
        candidate.classification = "candidate_unavailable_or_restricted"
        candidate.usable_for_mosaic = "no"
    elif coverage == "national_or_france_claim":
        candidate.classification = "national_claim_needs_content_validation"
        candidate.usable_for_mosaic = "maybe"
    elif coverage in {"regional", "departmental"}:
        candidate.classification = f"{coverage}_mosaic_candidate"
        candidate.usable_for_mosaic = "maybe"
    else:
        candidate.classification = "bpe2020_candidate_unclear_coverage"
        candidate.usable_for_mosaic = "maybe"
    return candidate


def make_candidate(
    source_system: str,
    dataset_title: str,
    organization: str,
    dataset_page: str,
    resource_title: str,
    resource_format: str,
    resource_url: str,
    notes: str = "",
) -> Candidate:
    blob = text_blob(dataset_title, organization, dataset_page, resource_title, resource_url, notes)
    status, ctype, clen = probe_url(resource_url)
    cand = Candidate(
        source_system=source_system,
        dataset_title=dataset_title,
        organization=organization,
        dataset_page=dataset_page,
        resource_title=resource_title,
        resource_format=resource_format,
        resource_url=resource_url,
        year_signal=detect_year(blob, resource_url),
        coverage_signal=detect_coverage(blob, resource_url),
        access_status=status,
        content_type=ctype,
        content_length=clen,
        classification="",
        usable_for_mosaic="",
        notes=notes,
    )
    return classify(cand)


def iter_data_gouv() -> list[Candidate]:
    candidates: list[Candidate] = []
    seen_resources: set[str] = set()
    for query in DATA_GOUV_QUERIES:
        log(f"data.gouv query: {query}")
        for page in range(1, 3):
            params = urllib.parse.urlencode({"q": query, "page_size": 20, "page": page})
            data = fetch_json(f"https://www.data.gouv.fr/api/1/datasets/?{params}")
            if not data:
                continue
            for ds in data.get("data", []):
                title = ds.get("title") or ""
                desc = ds.get("description") or ""
                blob = text_blob(title, desc)
                if "bpe" not in blob and "base permanente" not in blob:
                    continue
                org = (ds.get("organization") or {}).get("name") or ""
                page_url = ds.get("page") or ""
                for resource in ds.get("resources", []):
                    url = resource.get("url") or resource.get("latest") or ""
                    if not url or url in seen_resources:
                        continue
                    rtitle = resource.get("title") or ""
                    rfmt = resource.get("format") or ""
                    rblob = text_blob(title, desc, rtitle, rfmt, url)
                    if not any(x in rblob for x in ["bpe", "base permanente", "csv", "zip", "shp", "geojson", "featureserver", "arcgis"]):
                        continue
                    seen_resources.add(url)
                    candidates.append(
                        make_candidate("data_gouv", title, org, page_url, rtitle, rfmt, url, "discovered via data.gouv search")
                    )
    return candidates


def iter_ckan() -> list[Candidate]:
    candidates: list[Candidate] = []
    seen_resources: set[str] = set()
    for portal, base_url in CKAN_PORTALS.items():
        if "geonetwork" in base_url:
            continue
        for query in ("BPE 2020", "bpe20", "Base permanente équipements"):
            log(f"CKAN {portal} query: {query}")
            params = urllib.parse.urlencode({"q": query, "rows": 50})
            data = fetch_json(f"{base_url}?{params}")
            if not data or not data.get("success"):
                continue
            for ds in data.get("result", {}).get("results", []):
                title = ds.get("title") or ""
                org = (ds.get("organization") or {}).get("title") or ds.get("author") or ""
                page_url = ds.get("url") or ds.get("remote_url") or ""
                if not page_url and ds.get("name"):
                    domain = base_url.split("/api/")[0]
                    page_url = f"{domain}/dataset/{ds.get('name')}"
                notes = ds.get("notes") or ""
                for resource in ds.get("resources", []):
                    url = resource.get("url") or ""
                    if not url or url in seen_resources:
                        continue
                    seen_resources.add(url)
                    api = resource.get("api") or ""
                    extra_notes = "discovered via CKAN"
                    if api:
                        extra_notes += f"; api={api[:500]}"
                    candidates.append(
                        make_candidate(
                            f"ckan_{portal}",
                            title,
                            org,
                            page_url,
                            resource.get("name") or "",
                            resource.get("format") or "",
                            url,
                            notes=(notes[:800] + " " + extra_notes).strip(),
                        )
                    )
    return candidates


def iter_opendatasoft_search() -> list[Candidate]:
    candidates: list[Candidate] = []
    seen: set[str] = set()
    search_terms = [
        "bpe",
        "bpe20",
        "base permanente équipements",
        "base permanente des équipements",
    ]
    for portal, base_url in ODATA_PORTALS.items():
        for term in search_terms:
            log(f"Opendatasoft {portal} query: {term}")
            params = urllib.parse.urlencode({"where": f'search(title, "{term}") or search(description, "{term}")', "limit": 50})
            data = fetch_json(f"{base_url}?{params}")
            if not data:
                continue
            for ds in data.get("results", []):
                dataset_id = ds.get("dataset_id") or ""
                if not dataset_id:
                    continue
                dataset_api = f"{base_url}/{dataset_id}"
                if dataset_api in seen:
                    continue
                seen.add(dataset_api)
                metas = ds.get("metas", {})
                default = metas.get("default", {})
                dcat = metas.get("dcat", {})
                title = default.get("title") or dataset_id
                desc = default.get("description") or ""
                blob = text_blob(title, desc, dcat.get("temporal") or "")
                if "bpe" not in blob and "base permanente" not in blob:
                    continue
                page = dataset_api.replace("/api/explore/v2.1/catalog/datasets/", "/explore/dataset/")
                notes = (
                    f"Opendatasoft search; temporal={dcat.get('temporal') or ''}; "
                    f"records_count={default.get('records_count') or ds.get('records_count') or ''}; "
                    f"territory={default.get('territory') or ''}; {desc[:500]}"
                )
                candidates.append(
                    make_candidate(
                        f"opendatasoft_search_{portal}",
                        title,
                        default.get("publisher") or dcat.get("creator") or "",
                        page,
                        f"{dataset_id}.csv",
                        "csv",
                        f"{dataset_api}/exports/csv",
                        notes=notes,
                    )
                )
    return candidates


def iter_arcgis() -> list[Candidate]:
    candidates: list[Candidate] = []
    seen: set[str] = set()
    for query in ARCGIS_QUERIES:
        log(f"ArcGIS query: {query}")
        params = urllib.parse.urlencode(
            {"f": "json", "q": query, "num": 50, "sortField": "modified", "sortOrder": "desc"}
        )
        data = fetch_json(f"https://www.arcgis.com/sharing/rest/search?{params}")
        if not data:
            continue
        for item in data.get("results", []):
            url = item.get("url") or ""
            item_id = item.get("id") or ""
            key = url or item_id
            if not key or key in seen:
                continue
            title = item.get("title") or ""
            desc = item.get("description") or ""
            blob = text_blob(title, desc, url)
            if "bpe" not in blob and "base permanente" not in blob:
                continue
            seen.add(key)
            page_url = f"https://www.arcgis.com/home/item.html?id={item_id}" if item_id else ""
            candidates.append(
                make_candidate(
                    "arcgis_search",
                    title,
                    item.get("owner") or "",
                    page_url,
                    title,
                    item.get("type") or "",
                    url,
                    notes=desc[:800],
                )
            )
    return candidates


def iter_opendatasoft_known() -> list[Candidate]:
    candidates: list[Candidate] = []
    for name, url in KNOWN_ODATASETS.items():
        log(f"Opendatasoft known dataset: {name}")
        data = fetch_json(url)
        if not data:
            continue
        metas = data.get("metas", {})
        default = metas.get("default", {})
        dcat = metas.get("dcat", {})
        title = default.get("title") or data.get("dataset_id") or name
        desc = default.get("description") or ""
        temporal = dcat.get("temporal") or ""
        records = str(default.get("records_count") or data.get("records_count") or "")
        base_page = url.replace("/api/explore/v2.1/catalog/datasets/", "/explore/dataset/")
        export_base = url + "/exports/csv"
        notes = f"known Opendatasoft dataset; temporal={temporal}; records_count={records}; {desc[:500]}"
        candidates.append(
            make_candidate(
                f"opendatasoft_{name}",
                title,
                default.get("publisher") or dcat.get("creator") or "",
                base_page,
                f"{data.get('dataset_id')}.csv",
                "csv",
                export_base,
                notes=notes,
            )
        )
    return candidates


def iter_direct_historical() -> list[Candidate]:
    return [
        make_candidate(
            "direct_historical_insee",
            "INSEE historical BPE 2020",
            "INSEE",
            "https://www.insee.fr/fr/statistiques/3568629",
            url.rsplit("/", 1)[-1],
            "zip",
            url,
            notes="historical URL from old scripts and documentation",
        )
        for url in DIRECT_HISTORICAL_URLS
    ]


def dedupe(candidates: list[Candidate]) -> list[Candidate]:
    by_key: dict[str, Candidate] = {}
    for candidate in candidates:
        key = candidate.resource_url or f"{candidate.source_system}:{candidate.dataset_title}:{candidate.resource_title}"
        old = by_key.get(key)
        if old is None:
            by_key[key] = candidate
            continue
        if old.access_status and not old.access_status.startswith("2") and candidate.access_status.startswith("2"):
            by_key[key] = candidate
    return sorted(by_key.values(), key=lambda c: (c.classification, c.source_system, c.dataset_title, c.resource_title))


def write_outputs(candidates: list[Candidate]) -> None:
    METADATA_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    rows = [asdict(c) for c in candidates]
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else list(Candidate.__annotations__.keys()))
        writer.writeheader()
        writer.writerows(rows)

    summary: dict[str, Any] = {
        "candidate_count": len(candidates),
        "by_classification": {},
        "by_usable_for_mosaic": {},
        "outputs": {"csv": str(OUT_CSV), "json": str(OUT_JSON), "markdown": str(OUT_MD)},
        "candidates": rows,
    }
    for candidate in candidates:
        summary["by_classification"][candidate.classification] = summary["by_classification"].get(candidate.classification, 0) + 1
        summary["by_usable_for_mosaic"][candidate.usable_for_mosaic] = summary["by_usable_for_mosaic"].get(candidate.usable_for_mosaic, 0) + 1

    OUT_JSON.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    maybe = [c for c in candidates if c.usable_for_mosaic in {"yes", "maybe"}]
    unavailable_exact = [c for c in candidates if c.classification == "national_exact_unavailable"]
    source_groups: dict[str, int] = {}
    for c in maybe:
        group = f"{c.coverage_signal or 'unknown'} | {c.dataset_title} | {c.organization}"
        source_groups[group] = source_groups.get(group, 0) + 1
    md = [
        "# BPE 2020 Source Candidates V0",
        "",
        "This report inventories candidate sources for reconstructing or replacing the missing BPE 2020 national file.",
        "",
        "## Summary",
        "",
        f"- Total candidates: {len(candidates)}",
        f"- Potential mosaic candidates: {len(maybe)}",
        f"- Historical national URLs unavailable: {len(unavailable_exact)}",
        "",
        "## Classification Counts",
        "",
    ]
    for key, value in sorted(summary["by_classification"].items()):
        md.append(f"- `{key}`: {value}")
    md.extend(["", "## Potential Mosaic Candidates", ""])
    if not maybe:
        md.append("- No directly usable candidates found yet.")
    else:
        for c in maybe[:80]:
            md.append(
                f"- `{c.classification}` | status `{c.access_status}` | {c.dataset_title} | {c.resource_title} | {c.resource_url}"
            )
    md.extend(["", "## Potential Source Groups", ""])
    if not source_groups:
        md.append("- No source groups found.")
    else:
        for group, count in sorted(source_groups.items(), key=lambda item: (-item[1], item[0]))[:80]:
            md.append(f"- {group}: {count} resources")
    md.extend(
        [
            "",
            "## Guardrail",
            "",
            "Do not integrate a candidate only because metadata says BPE 2020. Validate the real content year, geography, and schema first.",
        ]
    )
    OUT_MD.write_text("\n".join(md) + "\n", encoding="utf-8")


def main() -> int:
    candidates: list[Candidate] = []
    collectors = [
        iter_direct_historical,
        iter_data_gouv,
        iter_ckan,
        iter_arcgis,
        iter_opendatasoft_search,
        iter_opendatasoft_known,
    ]
    for collector in collectors:
        try:
            candidates.extend(collector())
        except Exception as exc:  # noqa: BLE001
            log(f"WARN collector failed: {collector.__name__}: {exc}")

    candidates = dedupe(candidates)
    write_outputs(candidates)
    log(f"wrote {OUT_CSV}")
    log(f"wrote {OUT_JSON}")
    log(f"wrote {OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
