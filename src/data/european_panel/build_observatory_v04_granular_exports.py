"""
DEC-065 consolidation / Observatory v0.4 granular prep.

Builds the clean exports for the granular FR/PT/NL Observatory contract:
  - granular_territory_state_panel.csv  (Layer 1: territory state, all sources)
  - granular_relation_edges.csv         (Layer 2: ONLY FR/PT_MUNI/NL_COROP observed)
  - blocked_proxy_edges.csv             (NL gemeente proxy edges, BLOCKED_PROXY_ARTIFACT)
  - manifest.json                       (checksums, sources, DEC references)

Hard rule (DEC-065): NL gemeente proxy relation edges NEVER appear in
granular_relation_edges.csv. They may only appear in the territory state
panel tagged evidence_type=proxy_disaggregated_by_stock_share,
allowed_use=territory_state_context_only.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).parents[3]
OUT_DIR = REPO_ROOT / "data/processed/herald_observatory_v04_granular"

FR_NL_PT_PANEL = REPO_ROOT / "data/processed/economic_graph/sector_panel_fr_nl_pt.csv"
PT_MUNI_PANEL = REPO_ROOT / "data/processed/phase7_pt_municipal/pt_municipal_phase7_panel.csv"
NL_GEMEENTE_PANEL = REPO_ROOT / "data/processed/phase7_nl_gemeente_proxy/nl_gemeente_phase7_panel.csv"

DEC066_CANDIDATES = REPO_ROOT / "data/processed/phase7_threshold_calibration/phase7_threshold_candidates.csv"
NL_GEMEENTE_PROMOTED = REPO_ROOT / "data/processed/phase7_nl_gemeente_proxy/results/latest.csv"

GROWTH_THRESHOLD = 0.02
TRAINING_LABELS = {"ROBUST_ORIGINAL", "FINE_GRAIN_SUPPORTED"}


def classify_state(velocity: float) -> str:
    if pd.isna(velocity):
        return "INSUFFICIENT_DATA"
    if velocity > GROWTH_THRESHOLD:
        return "GROWTH"
    if velocity < -GROWTH_THRESHOLD:
        return "DECLINE"
    return "STAGNATION"


def build_territory_state_panel() -> pd.DataFrame:
    rows = []

    # FR ZE2020 observed + NL COROP observed (same source file)
    base = pd.read_csv(FR_NL_PT_PANEL, low_memory=False)
    for country, region_system, source_table in [
        ("FR", "ZE2020", "SIDE/SIRENE via sector_panel_fr_nl_pt.csv"),
        ("NL", "COROP", "CBS 83631NED via sector_panel_fr_nl_pt.csv"),
    ]:
        sub = base[base["country"] == country].copy()
        sub = sub.sort_values(["region_id", "sector_a10", "observation_year"])
        sub["velocity"] = sub.groupby(["region_id", "sector_a10"])["sector_births"].pct_change(fill_method=None)
        for _, r in sub.iterrows():
            rows.append({
                "country": country,
                "region_id": r["region_id"],
                "region_name": r.get("region_name", ""),
                "region_system": region_system,
                "year": int(r["observation_year"]),
                "sector_a10": r["sector_a10"],
                "value": r["sector_births"],
                "state": classify_state(r["velocity"]),
                "velocity": r["velocity"],
                "evidence_type": "observed_births",
                "source_table": source_table,
                "allowed_use": "territory_state,relation_graph,training_label",
            })

    # PT municipal observed
    pt = pd.read_csv(PT_MUNI_PANEL)
    for _, r in pt.iterrows():
        rows.append({
            "country": "PT",
            "region_id": r["territory_id"],
            "region_name": "",
            "region_system": "MUNICIPALITY",
            "year": int(r["observation_year"]),
            "sector_a10": r["sector_id"],
            "value": r["observed_value"],
            "state": classify_state(r["velocity"]),
            "velocity": r["velocity"],
            "evidence_type": "observed_births",
            "source_table": "INE 0009703/0014099 via pt_municipal_phase7_panel.csv",
            "allowed_use": "territory_state,relation_graph,training_label",
        })

    # NL gemeente proxy/context — territory state ONLY, never relation graph
    nl_gm = pd.read_csv(NL_GEMEENTE_PANEL)
    for _, r in nl_gm.iterrows():
        rows.append({
            "country": "NL",
            "region_id": r["territory_id"],
            "region_name": "",
            "region_system": "GEMEENTE_PROXY",
            "year": int(r["observation_year"]),
            "sector_a10": r["sector_id"],
            "value": r["observed_value"],
            "state": classify_state(r["velocity"]),
            "velocity": r["velocity"],
            "evidence_type": "proxy_disaggregated_by_stock_share",
            "source_table": "CBS 83631NED x 81575NED via nl_gemeente_phase7_panel.csv",
            "allowed_use": "territory_state_context_only",
        })

    df = pd.DataFrame(rows)
    cols = ["country", "region_id", "region_name", "region_system", "year",
            "sector_a10", "value", "state", "velocity", "evidence_type",
            "source_table", "allowed_use"]
    return df[cols]


def build_relation_edges() -> pd.DataFrame:
    """FR + PT_MUNI + NL (COROP) observed labels ONLY. No NL gemeente proxy."""
    candidates = pd.read_csv(DEC066_CANDIDATES)
    allowed_countries = {"FR": "ZE2020", "NL": "COROP", "PT_MUNI": "MUNICIPALITY"}
    sub = candidates[candidates["country"].isin(allowed_countries.keys())].copy()

    rows = []
    for _, r in sub.iterrows():
        country_raw = r["country"]
        out_country = "PT" if country_raw == "PT_MUNI" else country_raw
        region_system = allowed_countries[country_raw]
        rows.append({
            "country": out_country,
            "region_system": region_system,
            "source_sector": r["source_sector"],
            "target_sector": r["target_sector"],
            "sign": "+" if r["beta"] > 0 else "-",
            "beta": r["beta"],
            "q_fdr": r["q_fdr"],
            "bss": r["bootstrap_sign_stability"],
            "window": f"{int(r['window_start'])}-{int(r['window_end'])}",
            "label_class": r["label"],
            "evidence_type": "observed_births",
            "allowed_for_training_label": bool(r["label"] in TRAINING_LABELS),
        })
    df = pd.DataFrame(rows)
    cols = ["country", "region_system", "source_sector", "target_sector", "sign",
            "beta", "q_fdr", "bss", "window", "label_class", "evidence_type",
            "allowed_for_training_label"]
    return df[cols]


def build_blocked_proxy_edges() -> pd.DataFrame:
    """All 121 NL gemeente proxy promoted edges, permanently marked BLOCKED."""
    if not NL_GEMEENTE_PROMOTED.exists():
        return pd.DataFrame(columns=[
            "country", "region_system", "source_sector", "target_sector", "sign",
            "beta", "q_fdr", "bss", "window", "label_class", "evidence_type",
            "allowed_for_training_label", "reason",
        ])
    proxy = pd.read_csv(NL_GEMEENTE_PROMOTED)
    rows = []
    for _, r in proxy.iterrows():
        rows.append({
            "country": "NL",
            "region_system": "GEMEENTE_PROXY",
            "source_sector": r["source_sector"],
            "target_sector": r["target_sector"],
            "sign": "+" if r["beta"] > 0 else "-",
            "beta": r["beta"],
            "q_fdr": r["q_fdr"],
            "bss": r["bootstrap_sign_stability"],
            "window": f"{int(r['window_start'])}-{int(r['window_end'])}",
            "label_class": "BLOCKED_PROXY_ARTIFACT",
            "evidence_type": "proxy_disaggregated_by_stock_share",
            "allowed_for_training_label": False,
            "reason": "stock_share_induced_artifact",
        })
    df = pd.DataFrame(rows)
    cols = ["country", "region_system", "source_sector", "target_sector", "sign",
            "beta", "q_fdr", "bss", "window", "label_class", "evidence_type",
            "allowed_for_training_label", "reason"]
    return df[cols]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    territory_state = build_territory_state_panel()
    territory_path = OUT_DIR / "granular_territory_state_panel.csv"
    territory_state.to_csv(territory_path, index=False)
    print(f"Wrote {territory_path} ({len(territory_state)} rows)")

    relation_edges = build_relation_edges()
    relation_path = OUT_DIR / "granular_relation_edges.csv"
    relation_edges.to_csv(relation_path, index=False)
    print(f"Wrote {relation_path} ({len(relation_edges)} rows)")
    assert "NL_GEMEENTE" not in relation_edges["region_system"].values
    assert (relation_edges["region_system"] != "GEMEENTE_PROXY").all()

    blocked = build_blocked_proxy_edges()
    blocked_path = OUT_DIR / "blocked_proxy_edges.csv"
    blocked.to_csv(blocked_path, index=False)
    print(f"Wrote {blocked_path} ({len(blocked)} rows)")

    manifest = {
        "dec_references": ["DEC-063", "DEC-064", "DEC-065", "DEC-066"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sources": {
            "fr_nl_corop_observed": str(FR_NL_PT_PANEL.relative_to(REPO_ROOT)),
            "pt_municipal_observed": str(PT_MUNI_PANEL.relative_to(REPO_ROOT)),
            "nl_gemeente_proxy": str(NL_GEMEENTE_PANEL.relative_to(REPO_ROOT)),
            "dec066_labelled_candidates": str(DEC066_CANDIDATES.relative_to(REPO_ROOT)),
            "nl_gemeente_proxy_promoted_blocked": str(NL_GEMEENTE_PROMOTED.relative_to(REPO_ROOT)),
        },
        "outputs": {
            "granular_territory_state_panel.csv": {
                "rows": len(territory_state),
                "sha256": sha256_file(territory_path),
            },
            "granular_relation_edges.csv": {
                "rows": len(relation_edges),
                "sha256": sha256_file(relation_path),
            },
            "blocked_proxy_edges.csv": {
                "rows": len(blocked),
                "sha256": sha256_file(blocked_path),
            },
        },
        "rules": {
            "nl_gemeente_proxy_relation_edges_forbidden": True,
            "nl_gemeente_proxy_allowed_use": ["territory_state_context_only"],
            "nl_corop_observed_status": "VALID_OBSERVED",
            "nl_gemeente_proxy_status": "BLOCKED_FOR_RELATION_LABELS",
            "blocked_proxy_reason": "stock_share_induced_artifact",
        },
        "warning": (
            "NL gemeente proxy data (evidence_type=proxy_disaggregated_by_stock_share) "
            "must NEVER appear in granular_relation_edges.csv. It may only be used for "
            "territory state visualisation / local context, never as a sector to sector "
            "relation label or training signal. See reports/HERALD_DEC065_NL_GEMEENTE_PROXY_PHASE7_AUDIT.md."
        ),
    }
    manifest_path = OUT_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Wrote {manifest_path}")


if __name__ == "__main__":
    main()
