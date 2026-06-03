"""
HERALD Phase 4E-A2 wrapper.

Runs the canonical European Phase 4E panel using the best Phase 4A protocol for
each country. Unlike Phase 4E-A, this wrapper does not force baseline features
or zero tensors globally. It lets train_herald_regime_experiment apply the
country-specific feature_policy and quarterly_tensor_policy.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[2]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))
if str(BASE / "src/modeles") not in sys.path:
    sys.path.insert(0, str(BASE / "src/modeles"))


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        print(f"ERROR: {name} is required", file=sys.stderr)
        sys.exit(1)
    return value


def _graph_stats(adj_path: str) -> dict:
    df = pd.read_csv(adj_path)
    mat = df.drop("source_idx", axis=1).values.astype(float)
    n = mat.shape[0]
    diag = np.diag(mat)
    density = float((mat > 0).sum() - n) / (n * (n - 1)) if n > 1 else 0.0
    return {
        "graph_shape": list(mat.shape),
        "graph_density": round(density, 6),
        "graph_diag_mean": round(float(diag.mean()), 6),
    }


def _build_long_qtensor(qtensor_path: str, qtensor_col: str, country: str,
                        zones_sorted: list[int], years_sorted: list[int]) -> np.ndarray:
    qt = pd.read_csv(qtensor_path)
    eu_panel_name = "france" if country == "fr" else country
    eu_panel = pd.read_csv(BASE / f"data/processed/european_panel/{eu_panel_name}_panel.csv")
    mapping = (
        eu_panel[["region_id", "node_idx"]]
        .drop_duplicates()
        .assign(ZE2020=lambda d: d["node_idx"].astype(int) + 1)
    )
    zone_map = dict(zip(mapping["region_id"], mapping["ZE2020"]))

    if "zone_id" not in qt.columns:
        raise ValueError(f"{qtensor_path} must contain zone_id")
    if qtensor_col not in qt.columns:
        raise ValueError(f"{qtensor_path} missing qtensor_col={qtensor_col!r}")

    qt = qt.copy()
    qt["ZE2020"] = qt["zone_id"].map(zone_map)
    qt = qt.dropna(subset=["ZE2020"]).copy()
    qt["ZE2020"] = qt["ZE2020"].astype(int)
    agg = qt.groupby(["ZE2020", "target_year"], as_index=False)[qtensor_col].sum()

    zone_to_idx = {int(z): i for i, z in enumerate(zones_sorted)}
    year_to_idx = {int(y): i for i, y in enumerate(years_sorted)}
    tensor = np.zeros((len(years_sorted), 3, len(zones_sorted), 2), dtype=np.float32)
    for _, row in agg.iterrows():
        z = int(row["ZE2020"])
        y = int(row["target_year"])
        if z not in zone_to_idx or y not in year_to_idx:
            continue
        tensor[year_to_idx[y], :, zone_to_idx[z], 0] = float(row[qtensor_col])
    return tensor


def _inject_metadata(metadata_path: str, extra: dict) -> None:
    p = Path(metadata_path)
    if not p.exists():
        return
    data = json.loads(p.read_text())
    data.update(extra)
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")


def main() -> None:
    country = _require_env("PHASE4E_COUNTRY")
    panel_path = _require_env("PHASE4E_PANEL")
    splits_path = _require_env("PHASE4E_SPLITS")
    side_a10 = _require_env("PHASE4E_SIDE_A10")
    geo_adj = _require_env("PHASE4E_GEO_ADJ")
    mob_adj = _require_env("PHASE4E_MOB_ADJ")
    label = os.environ.get("PHASE4E_CONFIG_LABEL", "unknown")
    feature_policy = os.environ.get("PHASE4E_FEATURE_POLICY", "unknown")
    tensor_policy = os.environ.get("PHASE4E_TENSOR_POLICY", "zero")
    qtensor_path = os.environ.get("PHASE4E_QTENSOR", "none")
    qtensor_col = os.environ.get("PHASE4E_QTENSOR_COL", "none")

    for name, path in [
        ("panel", panel_path),
        ("splits", splits_path),
        ("a10", side_a10),
        ("geo_adj", geo_adj),
        ("mob_adj", mob_adj),
    ]:
        if not Path(path).exists():
            print(f"ERROR: {name} file not found: {path}", file=sys.stderr)
            sys.exit(1)
    if qtensor_path != "none" and not Path(qtensor_path).exists():
        print(f"ERROR: qtensor file not found: {qtensor_path}", file=sys.stderr)
        sys.exit(1)

    metadata_path = None
    for i, arg in enumerate(sys.argv):
        if arg == "--regime-metadata-path" and i + 1 < len(sys.argv):
            metadata_path = sys.argv[i + 1]
            break

    import train_herald_v6 as v6

    v6.GEO_ADJ_PATH = Path(geo_adj)
    v6.MOB_ADJ_PATH = Path(mob_adj)
    v6.PANEL_PATH = Path(panel_path)
    v6.SPLITS_PATH = Path(splits_path)
    v6.SIDE_A10_PATH = Path(side_a10)

    def _phase4e_qtensor(zones_sorted, years_sorted):
        if qtensor_path == "none":
            return np.zeros((len(years_sorted), 3, len(zones_sorted), 2), dtype=np.float32)
        return _build_long_qtensor(qtensor_path, qtensor_col, country, zones_sorted, years_sorted)

    v6.build_quarterly_tensor = _phase4e_qtensor

    graph_meta = _graph_stats(geo_adj)
    print(f"[4E-A2 wrapper] country={country} label={label}")
    print(f"[4E-A2 wrapper] panel={panel_path}")
    print(f"[4E-A2 wrapper] feature_policy={feature_policy} tensor_policy={tensor_policy}")
    print(f"[4E-A2 wrapper] qtensor={qtensor_path} col={qtensor_col}")
    print(f"[4E-A2 wrapper] graph_density={graph_meta['graph_density']:.4f}")

    import train_herald_regime_experiment as trainer

    trainer.main()

    if metadata_path:
        _inject_metadata(
            metadata_path,
            {
                "phase": "4E-A2",
                "country": country,
                "config_label": label,
                "panel_path": panel_path,
                "graph_policy": "identity",
                "tensor_policy": tensor_policy,
                "feature_policy": feature_policy,
                "qtensor_path": qtensor_path,
                "qtensor_col": qtensor_col,
                **graph_meta,
            },
        )
        print(f"[4E-A2 wrapper] metadata injected -> {metadata_path}")


if __name__ == "__main__":
    main()
