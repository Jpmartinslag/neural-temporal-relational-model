"""
HERALD Phase 4E-A training wrapper.

Purpose: run the European canonical panel as the causal Phase 4E-A baseline
after retiring leakage-affected Phase 4A/4D results.

What this wrapper does:
  1. Points train_herald_v6 globals to the Phase 4E panel (from prepare_phase4e_panel.py).
  2. Overrides feature_columns() to return only BASELINE_ANNUAL_FEATURES
     (lag1/2/3, growth_1y/2y) — equivalent to ablation="regime_exclusive".
     This EXPLICITLY excludes NON_PREDICTIVE_FIELDS (flag_is_covid_year,
     flag_is_rebound_year) from the model input.
  3. Forces q_tensor to zero (no employment tensor, no sector tensor).
  4. Calls trainer.main() — no changes to train_herald_semi_v2.py.
  5. Injects metadata into the per-run JSON after training.

Required env vars:
  PHASE4E_COUNTRY       — fr | nl | be | pt
  PHASE4E_PANEL         — path to panel_ze2020.csv
  PHASE4E_SPLITS        — path to splits.csv
  PHASE4E_SIDE_A10      — path to a10_ze2020.csv
  PHASE4E_GEO_ADJ       — path to adj_identity.csv
  PHASE4E_MOB_ADJ       — path to adj_identity.csv (identity for Phase 4E-A)

Optional:
  PHASE4E_CONFIG_LABEL  — config label for metadata (default: baseline_annual)

Feature policy (non-negotiable for Phase 4E-A):
  BASELINE_ANNUAL_FEATURES = [lag1_births, lag2_births, lag3_births,
                               growth_1y, growth_2y]
  → translated to HERALD cols: side_lag_1/2/3, growth_1y, growth_2y
  NON_PREDICTIVE_FIELDS excluded: is_covid_year, is_post_covid_rebound
"""

import json
import os
import sys
from pathlib import Path

import numpy as np

BASE = Path(__file__).resolve().parents[2]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))
if str(BASE / "src/modeles") not in sys.path:
    sys.path.insert(0, str(BASE / "src/modeles"))


def _require_env(name: str) -> str:
    v = os.environ.get(name)
    if not v:
        print(f"ERROR: {name} is required", file=sys.stderr)
        sys.exit(1)
    return v


# HERALD columns that correspond to BASELINE_ANNUAL_FEATURES
_BASELINE_HERALD_COLS = ["side_lag_1", "side_lag_2", "side_lag_3", "growth_1y", "growth_2y"]

# Columns that must NEVER appear in x_ann (NON_PREDICTIVE_FIELDS → HERALD names)
_NON_PREDICTIVE_HERALD = ["is_covid_year", "is_post_covid_rebound"]


def _graph_stats(adj_path: str) -> dict:
    import pandas as pd
    df = pd.read_csv(adj_path)
    mat = df.drop("source_idx", axis=1).values.astype(float)
    N = mat.shape[0]
    diag = np.diag(mat)
    density = float((mat > 0).sum() - N) / (N * (N - 1)) if N > 1 else 0.0
    return {
        "shape": list(mat.shape),
        "graph_density": round(density, 6),
        "graph_diag_mean": round(float(diag.mean()), 6),
        "graph_diag_min": round(float(diag.min()), 6),
        "graph_diag_max": round(float(diag.max()), 6),
    }


def _inject_metadata(metadata_path: str, country: str, config_label: str,
                     panel_path: str = "") -> None:
    p = Path(metadata_path)
    if not p.exists():
        return
    data = json.loads(p.read_text())
    data["phase"]           = os.environ.get("PHASE4E_PHASE", "4E-A")
    data["country"]         = country
    data["config_label"]    = config_label
    data["graph_policy"]    = "identity"
    data["tensor_policy"]   = "zero"
    data["feature_policy"]  = "baseline_annual"
    data["panel_path"]      = panel_path
    data["non_predictive_fields_excluded"] = _NON_PREDICTIVE_HERALD
    data["baseline_annual_features"]       = _BASELINE_HERALD_COLS
    p.write_text(json.dumps(data, indent=2))


def main() -> None:
    phase = os.environ.get("PHASE4E_PHASE", "4E-A")
    country      = _require_env("PHASE4E_COUNTRY")
    panel_path   = _require_env("PHASE4E_PANEL")
    splits_path  = _require_env("PHASE4E_SPLITS")
    side_a10     = _require_env("PHASE4E_SIDE_A10")
    geo_adj      = _require_env("PHASE4E_GEO_ADJ")
    mob_adj      = _require_env("PHASE4E_MOB_ADJ")
    config_label = os.environ.get("PHASE4E_CONFIG_LABEL", "baseline_annual")

    # Verify all files exist before importing trainer (fast fail)
    for label, path in [
        ("panel", panel_path), ("splits", splits_path), ("a10", side_a10),
        ("geo_adj", geo_adj), ("mob_adj", mob_adj),
    ]:
        if not Path(path).exists():
            print(f"ERROR: {label} file not found: {path}", file=sys.stderr)
            sys.exit(1)

    graph_meta = _graph_stats(geo_adj)
    print(f"[{phase} baseline wrapper] country={country} config={config_label}")
    print(f"[4E-A wrapper] panel={panel_path}")
    print(f"[4E-A wrapper] graph_density={graph_meta['graph_density']:.4f}  "
          f"diag_mean={graph_meta['graph_diag_mean']:.4f}")
    print(f"[4E-A wrapper] features: {_BASELINE_HERALD_COLS}")
    print(f"[4E-A wrapper] excluded: {_NON_PREDICTIVE_HERALD}")

    # ── Parse --regime-metadata-path from argv for post-training injection ─
    metadata_path = None
    for i, arg in enumerate(sys.argv):
        if arg == "--regime-metadata-path" and i + 1 < len(sys.argv):
            metadata_path = sys.argv[i + 1]
            break

    # ── Patch train_herald_v6 globals BEFORE importing trainer ────────────
    import train_herald_v6 as v6

    v6.GEO_ADJ_PATH  = Path(geo_adj)
    v6.MOB_ADJ_PATH  = Path(mob_adj)
    v6.PANEL_PATH    = Path(panel_path)
    v6.SPLITS_PATH   = Path(splits_path)
    v6.SIDE_A10_PATH = Path(side_a10)

    # Override feature_columns: return ONLY baseline lags + source flags.
    # This is equivalent to ablation="regime_exclusive" but enforced unconditionally,
    # regardless of what ablation the caller specifies.
    _orig_feature_columns = v6.feature_columns

    def _baseline_feature_columns(panel, ablation="full"):
        # Base features only — no COVID flags, no FLORES, no SIDE stock, no URSSAF
        cols = _BASELINE_HERALD_COLS + ["has_flores_source", "has_side_stock_source", "has_urssaf_source"]
        selected = [c for c in cols if c in panel.columns]
        # Hard safety check: no NON_PREDICTIVE field should slip in
        leaked = [c for c in selected if c in _NON_PREDICTIVE_HERALD]
        if leaked:
            raise RuntimeError(
                f"[4E-A] NON_PREDICTIVE_FIELDS leaked into feature set: {leaked}. "
                "This is a methodology violation. Aborting."
            )
        return selected

    v6.feature_columns = _baseline_feature_columns

    # Force q_tensor to zero via build_quarterly_tensor override.
    # The international wrapper would set up a real tensor; we skip it entirely.
    def _zero_quarterly_tensor(zones_sorted, years_sorted):
        T, N = len(years_sorted), len(zones_sorted)
        return np.zeros((T, 3, N, 2), dtype=np.float32)

    v6.build_quarterly_tensor = _zero_quarterly_tensor

    # ── Import and run trainer ────────────────────────────────────────────
    import train_herald_regime_experiment as trainer
    trainer.main()

    # ── Inject Phase 4E-A metadata into per-run JSON ─────────────────────
    if metadata_path:
        _inject_metadata(metadata_path, country, config_label, panel_path=panel_path)
        print(f"[4E-A wrapper] metadata injected → {metadata_path}")


if __name__ == "__main__":
    main()
