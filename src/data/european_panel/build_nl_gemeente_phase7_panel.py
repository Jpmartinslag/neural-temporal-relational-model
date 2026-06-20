"""
DEC-065: Build NL gemeente proxy Phase 7 panel.

Transforms nl_gemeente_birth_proxy_panel.csv (proxy_disaggregated_by_stock_share)
into the Phase 7 velocity panel format expected by run_sector_precedence_task.py.

Output columns:
  country, territory_id, observation_year, sector_id,
  observed_value, lag1_value, velocity,
  structural_mask, observation_mask,
  evidence_type, proxy_method, region_system

Key constraints:
  - Only proxy_computed rows (evidence_status == 'proxy_computed')
  - velocity = estimated_births[t] / estimated_births[t-1] - 1 (strictly causal)
  - structural_mask = 1 for all 9 NL A10 sectors (KZ is present in NL COROP data)
  - observation_mask = 1 when velocity is finite (both t and t-1 non-zero and non-NaN)
  - evidence_type = 'proxy_disaggregated_by_stock_share' must be preserved
  - N gemeenten: 355 (proxy_computed)
  - Years: 2007-2025 → 14 rolling 6-year windows possible
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

IN_PROXY = Path("data/processed/european_panel/nl_gemeente_birth_proxy_panel.csv")
OUT_PANEL = Path("data/processed/phase7_nl_gemeente_proxy/nl_gemeente_phase7_panel.csv")
OUT_MANIFEST = Path("data/processed/phase7_nl_gemeente_proxy/nl_gemeente_phase7_panel_manifest.json")

OBSERVABLE_SECTORS = ["BE", "FZ", "GI", "JZ", "KZ", "LZ", "MN", "OQ", "RU"]
EVIDENCE_TYPE = "proxy_disaggregated_by_stock_share"
PROXY_METHOD = "corop_births_allocated_by_gemeente_stock_share"
REGION_SYSTEM = "GEMEENTE_PROXY"
COUNTRY = "NL"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build_phase7_panel(in_path: Path = IN_PROXY) -> pd.DataFrame:
    raw = pd.read_csv(in_path)

    # Only proxy_computed rows
    df = raw[raw["evidence_status"] == "proxy_computed"].copy()

    # Rename to canonical Phase 7 column names
    df = df.rename(columns={
        "gm_code": "territory_id",
        "year": "observation_year",
        "sector_a10": "sector_id",
        "estimated_births_gemeente": "observed_value",
    })

    df = df[["territory_id", "observation_year", "sector_id", "observed_value"]].copy()
    df = df.sort_values(["territory_id", "sector_id", "observation_year"]).reset_index(drop=True)

    # Lag1 and velocity (strictly causal: only use lag1)
    df["lag1_value"] = df.groupby(["territory_id", "sector_id"])["observed_value"].shift(1)
    # velocity = value[t] / value[t-1] - 1; guard against zero denominator
    df["velocity"] = np.where(
        (df["lag1_value"].notna()) & (df["lag1_value"] != 0) & (df["observed_value"].notna()),
        df["observed_value"] / df["lag1_value"] - 1,
        np.nan,
    )

    # Structural mask: 1 for all 9 sectors (KZ is present in NL data)
    df["structural_mask"] = df["sector_id"].isin(OBSERVABLE_SECTORS).astype(int)

    # Observation mask: 1 when velocity is finite
    df["observation_mask"] = (
        df["velocity"].notna()
        & np.isfinite(df["velocity"])
        & (df["structural_mask"] == 1)
    ).astype(int)

    # Metadata columns required by DEC-065
    df["country"] = COUNTRY
    df["evidence_type"] = EVIDENCE_TYPE
    df["proxy_method"] = PROXY_METHOD
    df["region_system"] = REGION_SYSTEM

    # Reorder
    cols = [
        "country", "territory_id", "observation_year", "sector_id",
        "observed_value", "lag1_value", "velocity",
        "structural_mask", "observation_mask",
        "evidence_type", "proxy_method", "region_system",
    ]
    df = df[cols]
    return df


def _leakage_check(df: pd.DataFrame) -> str:
    """Verify velocity uses only lag1 (no future leakage)."""
    min_year = df["observation_year"].min()
    min_year_rows = df[(df["observation_year"] == min_year) & (df["structural_mask"] == 1)]
    if min_year_rows["observation_mask"].eq(0).all():
        return "PASS"
    return "FAIL: first year has observation_mask=1"


def main() -> None:
    OUT_PANEL.parent.mkdir(parents=True, exist_ok=True)

    panel = build_phase7_panel()

    # Checks
    assert set(panel["evidence_type"].unique()) == {EVIDENCE_TYPE}, "evidence_type mismatch"
    assert panel["country"].eq(COUNTRY).all(), "country mismatch"
    leakage = _leakage_check(panel)

    panel.to_csv(OUT_PANEL, index=False)
    checksum = sha256_file(OUT_PANEL)

    n_territories = panel["territory_id"].nunique()
    n_observable = panel[panel["structural_mask"] == 1]["sector_id"].nunique()
    n_observation_mask = panel["observation_mask"].sum()

    manifest = {
        "experiment": "DEC-065",
        "evidence_type": EVIDENCE_TYPE,
        "proxy_method": PROXY_METHOD,
        "region_system": REGION_SYSTEM,
        "country": COUNTRY,
        "n_rows": len(panel),
        "n_gemeenten": n_territories,
        "n_sectors": n_observable,
        "n_observation_mask": int(n_observation_mask),
        "years": sorted(panel["observation_year"].unique().tolist()),
        "sectors": sorted(panel["sector_id"].unique().tolist()),
        "leakage_check": leakage,
        "panel_checksum_sha256": checksum,
        "source_proxy_panel": str(IN_PROXY),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "warning": (
            "This panel uses proxy_disaggregated_by_stock_share evidence. "
            "It is NOT observed births. All results must carry evidence_type in outputs. "
            "Evaluation must report proxy-excluded sensitivity."
        ),
    }

    OUT_MANIFEST.write_text(json.dumps(manifest, indent=2))

    print(f"Panel: {len(panel)} rows, {n_territories} gemeenten, {n_observable} sectors")
    print(f"observation_mask=1: {n_observation_mask}")
    print(f"Leakage check: {leakage}")
    print(f"SHA256: {checksum}")
    print(f"Wrote: {OUT_PANEL}")
    print(f"Wrote: {OUT_MANIFEST}")


if __name__ == "__main__":
    main()
