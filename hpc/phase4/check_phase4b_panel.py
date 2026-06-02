#!/usr/bin/env python3
"""Preflight check: verify Phase 4B columns exist in panel."""
import sys
import pandas as pd

panel_path = sys.argv[1]
country = sys.argv[2] if len(sys.argv) > 2 else "?"

p = pd.read_csv(panel_path)
missing = [c for c in ["side_lag_2", "side_lag_3", "growth_2y"] if c not in p.columns]
if missing:
    sys.exit(
        f"Phase 4B columns missing from {panel_path}: {missing}\n"
        f"Run: python3 hpc/phase4/prepare_phase4_panel.py --country {country}"
    )
n_ok = int(p["side_lag_2"].notna().sum())
print(f"Phase 4B panel OK — side_lag_2/3 + growth_2y present ({n_ok}/{len(p)} non-NaN rows)")
