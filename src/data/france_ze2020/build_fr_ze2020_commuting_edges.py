#!/usr/bin/env python3
"""Build reproducible directed ZE2020 commuting edges from official INSEE flows.

The output is a relation-source artifact, not a trained graph. It keeps
observation-time and strict ex-ante availability separate so a later model
cannot silently use a file before its publication date.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request
import zipfile
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
RAW_DIR = ROOT / "data/external/france/raw/commuting"
PROCESSED_DIR = ROOT / "data/processed/france_ze2020"
COMMUNE_TO_ZE_PATH = ROOT / "data/interim/mappings/commune_to_ze2020_2026.csv"
CLEAN_PANEL_PATH = PROCESSED_DIR / "fr_ze2020_clean_panel.csv"
EDGES_OUT_PATH = PROCESSED_DIR / "fr_ze2020_commuting_edges.csv.gz"
SUMMARY_OUT_PATH = PROCESSED_DIR / "fr_ze2020_commuting_edge_summary.json"

COG_EVENTS_URL = "https://www.insee.fr/fr/statistiques/fichier/8740222/v_mvt_commune_2026.csv"
COG_EVENTS_SHA256 = "8b339fad8232e97233af3fd9468715af845e2cf8b14cb67b24d9a301ef8645f1"


@dataclass(frozen=True)
class SnapshotSpec:
    observation_year: int
    geography_reference_date: str
    release_date: str
    url: str
    sha256: str
    archive_member: str
    encoding: str
    observation_valid_from_year: int
    observation_valid_through_year: int
    strict_ex_ante_valid_from_year: int
    strict_ex_ante_valid_through_year: int
    quality_caveat: str

    @property
    def raw_name(self) -> str:
        return f"fr_commuting_{self.observation_year}.zip"

    @property
    def value_column(self) -> str:
        return f"NBFLUX_C{str(self.observation_year)[-2:]}_ACTOCC15P"


SNAPSHOTS = (
    SnapshotSpec(
        2012, "2014-01-01", "2015-06-25",
        "https://www.insee.fr/fr/statistiques/fichier/2022463/base-texte-flux-mobilite-domicile-lieu-travail-2012.zip",
        "6fc11a0aa75294e1f3ce53d84a65ee7852b1f2d164b5d99057f7e5a1179f478b",
        "base-texte-flux-mobilite-domicile-lieu-travail-2012.txt", "latin-1",
        2013, 2017, 2016, 2020,
        "INSEE sampling and rolling-census cautions apply.",
    ),
    SnapshotSpec(
        2017, "2020-01-01", "2020-12-09",
        "https://www.insee.fr/fr/statistiques/fichier/4509353/base-csv-flux-mobilite-domicile-lieu-travail-2017.zip",
        "14fad350aaf3aae9fc5edea4f6a6e286e5236d2211919d96dc81dc54f7be01d6",
        "base-flux-mobilite-domicile-lieu-travail-2017.csv", "utf-8-sig",
        2018, 2023, 2021, 2026,
        "INSEE sampling and rolling-census cautions apply.",
    ),
    SnapshotSpec(
        2023, "2026-01-01", "2026-06-25",
        "https://www.insee.fr/fr/statistiques/fichier/8998300/base-flux-mobilite-domicile-lieu-travail-2023_csv.zip",
        "ab658d314dca0ad7e15aa21cf50deca8153c29d86c8a9adb95cb4b5a8d68a25c",
        "base-flux-mobilite-domicile-lieu-travail-2023.csv", "utf-8-sig",
        2024, 9999, 2027, 9999,
        (
            "INSEE reports an uncorrected Maxey-sur-Vaise workplace-coding anomaly; "
            "sampling and rolling-census cautions also apply."
        ),
    ),
)

# Flow products expose these cities at arrondissement level; the canonical
# crosswalk uses their parent commune codes.
ARM_TO_PARENT = {
    **{f"751{i:02d}": "75056" for i in range(1, 21)},
    **{f"6938{i}": "69123" for i in range(1, 10)},
    **{f"6939{i}": "69123" for i in range(0, 10)},
    **{f"132{i:02d}": "13055" for i in range(1, 17)},
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _download(url: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=180) as response, path.open("wb") as output:
        while block := response.read(1024 * 1024):
            output.write(block)


def ensure_sources(raw_dir: Path = RAW_DIR, download_missing: bool = False) -> dict[str, Path]:
    expected = {
        "cog_events": (raw_dir / "v_mvt_commune_2026.csv", COG_EVENTS_URL, COG_EVENTS_SHA256),
        **{
            str(spec.observation_year): (raw_dir / spec.raw_name, spec.url, spec.sha256)
            for spec in SNAPSHOTS
        },
    }
    paths: dict[str, Path] = {}
    for key, (path, url, expected_hash) in expected.items():
        if not path.exists():
            if not download_missing:
                raise FileNotFoundError(
                    f"Missing {path}. Re-run with --download-missing; source: {url}"
                )
            _download(url, path)
        actual_hash = _sha256(path)
        if actual_hash != expected_hash:
            raise ValueError(f"Checksum mismatch for {path}: {actual_hash} != {expected_hash}")
        paths[key] = path
    return paths


def load_scope_and_mapping(
    clean_panel_path: Path = CLEAN_PANEL_PATH,
    mapping_path: Path = COMMUNE_TO_ZE_PATH,
) -> tuple[set[str], dict[str, str]]:
    clean = pd.read_csv(clean_panel_path, dtype={"ze2020": str})
    scope = set(clean["ze2020"].str.zfill(4).unique())
    if len(scope) != 280:
        raise ValueError(f"Expected 280 canonical ZE2020 zones, found {len(scope)}")
    mapping = pd.read_csv(mapping_path, dtype=str)
    mapping["ZE2020"] = mapping["ZE2020"].str.zfill(4)
    return scope, dict(zip(mapping["CODGEO"], mapping["ZE2020"]))


def load_movements(path: Path) -> dict[str, dict[str, set[str]]]:
    movements = pd.read_csv(path, dtype=str)
    movements = movements[movements["COM_AV"] != movements["COM_AP"]]
    by_date: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for row in movements.itertuples(index=False):
        by_date[str(row.DATE_EFF)][str(row.COM_AV)].add(str(row.COM_AP))
    return {date: dict(changes) for date, changes in by_date.items()}


class HistoricalZeResolver:
    def __init__(
        self,
        code_to_ze: dict[str, str],
        scope: set[str],
        movements_by_date: dict[str, dict[str, set[str]]],
        geography_reference_date: str,
    ) -> None:
        self.code_to_ze = code_to_ze
        self.scope = scope
        self.events = [
            (date, movements_by_date[date])
            for date in sorted(movements_by_date)
            if date > geography_reference_date
        ]
        self.cache: dict[str, str | None] = {}

    def resolve(self, code: object) -> str | None:
        raw = "" if pd.isna(code) else str(code).strip()
        if raw in self.cache:
            return self.cache[raw]
        state = {ARM_TO_PARENT.get(raw, raw)}
        for _, changes in self.events:
            state = {
                target
                for current in state
                for target in changes.get(current, {current})
            }
        zones = {self.code_to_ze[current] for current in state if current in self.code_to_ze}
        all_descendants_mapped = all(current in self.code_to_ze for current in state)
        resolved = (
            next(iter(zones))
            if all_descendants_mapped and len(zones) == 1 and zones <= self.scope
            else None
        )
        self.cache[raw] = resolved
        return resolved


def _read_snapshot_chunks(path: Path, spec: SnapshotSpec, chunksize: int = 200_000):
    with zipfile.ZipFile(path) as archive:
        if spec.archive_member not in archive.namelist():
            raise ValueError(f"Missing {spec.archive_member} in {path}")
        with archive.open(spec.archive_member) as stream:
            yield from pd.read_csv(
                stream,
                sep=";",
                encoding=spec.encoding,
                dtype={"CODGEO": str, "DCLT": str},
                usecols=["CODGEO", "DCLT", spec.value_column],
                chunksize=chunksize,
            )


def aggregate_snapshot(
    raw_path: Path,
    spec: SnapshotSpec,
    scope: set[str],
    code_to_ze: dict[str, str],
    movements_by_date: dict[str, dict[str, set[str]]],
) -> tuple[pd.DataFrame, dict[str, object]]:
    resolver = HistoricalZeResolver(
        code_to_ze,
        set(code_to_ze.values()),
        movements_by_date,
        spec.geography_reference_date,
    )
    pair_flow: dict[tuple[str, str], float] = defaultdict(float)
    origin_total: dict[str, float] = defaultdict(float)
    origin_in_scope_total: dict[str, float] = defaultdict(float)
    origin_interze_total: dict[str, float] = defaultdict(float)
    input_rows = 0
    input_total = source_resolved = destination_resolved = 0.0
    source_in_scope = destination_in_scope = pair_in_scope = 0.0

    for chunk in _read_snapshot_chunks(raw_path, spec):
        values = pd.to_numeric(chunk[spec.value_column], errors="raise").to_numpy(float)
        source = chunk["CODGEO"].map(resolver.resolve)
        target = chunk["DCLT"].map(resolver.resolve)
        input_rows += len(chunk)
        input_total += float(values.sum())
        source_resolved_mask = source.notna().to_numpy()
        target_resolved_mask = target.notna().to_numpy()
        source_mask = source.isin(scope).to_numpy()
        target_mask = target.isin(scope).to_numpy()
        source_resolved += float(values[source_resolved_mask].sum())
        destination_resolved += float(values[target_resolved_mask].sum())
        source_in_scope += float(values[source_mask].sum())
        destination_in_scope += float(values[target_mask].sum())
        pair_mask = source_mask & target_mask
        pair_in_scope += float(values[pair_mask].sum())

        working = pd.DataFrame({"source": source, "target": target, "value": values})
        for ze, value in (
            working[source.notna()].groupby("source")["value"].sum().items()
        ):
            origin_total[str(ze)] += float(value)
        paired = working[pair_mask]
        for (src, dst), value in (
            paired.groupby(["source", "target"])["value"].sum().items()
        ):
            src, dst = str(src), str(dst)
            pair_flow[(src, dst)] += float(value)
            origin_in_scope_total[src] += float(value)
            if src != dst:
                origin_interze_total[src] += float(value)

    rows = []
    for (source, target), commuter_count in sorted(pair_flow.items()):
        source_total = origin_total[source]
        in_scope_total = origin_in_scope_total[source]
        interze_total = origin_interze_total[source]
        is_self = source == target
        rows.append(
            {
                "relation_id": f"commuting__{spec.observation_year}__{source}__{target}",
                "source_ze2020": source,
                "target_ze2020": target,
                "observation_year": spec.observation_year,
                "relation_type": "residence_to_work_commuting",
                "relation_direction": "residence_ze_to_workplace_ze",
                "commuter_count": commuter_count,
                "origin_worker_share": commuter_count / source_total,
                "origin_in_scope_share": commuter_count / in_scope_total,
                "origin_interze_share": 0.0 if is_self else commuter_count / interze_total,
                "source_total_worker_count": source_total,
                "source_in_scope_worker_count": in_scope_total,
                "source_interze_worker_count": interze_total,
                "is_self_loop": int(is_self),
                "aggregated_flow_below_200_caution": int(commuter_count < 200.0),
                "observation_valid_from_year": spec.observation_valid_from_year,
                "observation_valid_through_year": spec.observation_valid_through_year,
                "strict_ex_ante_valid_from_year": spec.strict_ex_ante_valid_from_year,
                "strict_ex_ante_valid_through_year": spec.strict_ex_ante_valid_through_year,
                "source_release_date": spec.release_date,
                "source_geography_reference_date": spec.geography_reference_date,
                "data_available": 1,
                "claim_status": "official_commuting_relation_not_causal",
            }
        )
    edges = pd.DataFrame(rows)
    numeric = edges.select_dtypes(include=[np.number]).to_numpy(float)
    if not np.isfinite(numeric).all():
        raise ValueError(f"Non-finite value in commuting edges for {spec.observation_year}")

    summary = {
        "observation_year": spec.observation_year,
        "source_url": spec.url,
        "source_sha256": spec.sha256,
        "source_release_date": spec.release_date,
        "source_geography_reference_date": spec.geography_reference_date,
        "source_quality_caveat": spec.quality_caveat,
        "input_rows": input_rows,
        "input_total_worker_count": input_total,
        "source_code_resolution_coverage": source_resolved / input_total,
        "destination_code_resolution_coverage": destination_resolved / input_total,
        "source_in_scope_share": source_in_scope / input_total,
        "destination_in_scope_share": destination_in_scope / input_total,
        "in_scope_pair_coverage": pair_in_scope / input_total,
        "output_edge_count": len(edges),
        "output_source_zone_count": int(edges["source_ze2020"].nunique()),
        "output_target_zone_count": int(edges["target_ze2020"].nunique()),
    }
    return edges, summary


def build_commuting_edges(
    raw_dir: Path = RAW_DIR,
    download_missing: bool = False,
) -> tuple[pd.DataFrame, dict[str, object]]:
    paths = ensure_sources(raw_dir, download_missing)
    scope, code_to_ze = load_scope_and_mapping()
    movements = load_movements(paths["cog_events"])
    edge_frames = []
    snapshots = []
    for spec in SNAPSHOTS:
        edges, summary = aggregate_snapshot(
            paths[str(spec.observation_year)], spec, scope, code_to_ze, movements
        )
        edge_frames.append(edges)
        snapshots.append(summary)
    combined = pd.concat(edge_frames, ignore_index=True).sort_values(
        ["observation_year", "source_ze2020", "target_ze2020"]
    ).reset_index(drop=True)
    if combined["relation_id"].duplicated().any():
        raise ValueError("Duplicate commuting relation_id")
    summary = {
        "artifact": "fr_ze2020_commuting_edges",
        "status": "REGENERABLE_RELATION_SOURCE",
        "canonical_scope_zone_count": len(scope),
        "snapshot_count": len(SNAPSHOTS),
        "edge_count": len(combined),
        "cog_events_url": COG_EVENTS_URL,
        "cog_events_sha256": COG_EVENTS_SHA256,
        "snapshots": snapshots,
        "method": (
            "Official commune residence-to-workplace flows aggregated to canonical ZE2020; "
            "historical commune codes advanced with COG 2026 events; observation-time and "
            "strict ex-ante availability kept separate."
        ),
        "forbidden_claim": "No causal effect, validated neural gain, or recommendation claim.",
    }
    return combined, summary


def write_outputs(edges: pd.DataFrame, summary: dict[str, object]) -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    edges.to_csv(
        EDGES_OUT_PATH,
        index=False,
        compression={"method": "gzip", "mtime": 0},
    )
    SUMMARY_OUT_PATH.write_text(json.dumps(summary, indent=2, ensure_ascii=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--download-missing", action="store_true")
    args = parser.parse_args()
    edges, summary = build_commuting_edges(download_missing=args.download_missing)
    write_outputs(edges, summary)
    print(f"wrote {len(edges):,} edges to {EDGES_OUT_PATH}")
    print(f"wrote provenance summary to {SUMMARY_OUT_PATH}")


if __name__ == "__main__":
    main()
