"""
Build canonical European panels for all countries.

Usage
-----
    python3 src/data/european_panel/build_european_panel.py --country all
    python3 src/data/european_panel/build_european_panel.py --country france
    python3 src/data/european_panel/build_european_panel.py --country nl --out-dir /tmp/ep

Output
------
    data/processed/european_panel/france_panel.csv
    data/processed/european_panel/nl_panel.csv
    data/processed/european_panel/be_panel.csv
    data/processed/european_panel/pt_panel.csv
    data/processed/european_panel/european_panel_all.csv

Each file conforms to src/data/european_panel/schema.py.
Validation is run automatically; the script exits with code 1 if any country
has errors (not warnings).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

_HERE = Path(__file__).resolve().parent
_BASE = _HERE.parents[2]  # dataset root

# Make sure imports work when called from any working directory
if str(_BASE) not in sys.path:
    sys.path.insert(0, str(_BASE))

from src.data.european_panel.adapters.france_adapter import FranceAdapter
from src.data.european_panel.adapters.nl_adapter import NLAdapter
from src.data.european_panel.adapters.be_adapter import BEAdapter
from src.data.european_panel.adapters.pt_adapter import PTAdapter
from src.data.european_panel.validation import print_report
from src.data.european_panel.eu_signals import attach_eu_signals

_DEFAULT_OUT = _BASE / "data/processed/european_panel"

_ADAPTERS = {
    "france": FranceAdapter,
    "nl":     NLAdapter,
    "be":     BEAdapter,
    "pt":     PTAdapter,
}

# adapter key → ISO-2 geo code used by Eurostat / panel "country" column
_ISO2 = {"france": "FR", "nl": "NL", "be": "BE", "pt": "PT"}

_OUT_NAMES = {
    "france": "france_panel.csv",
    "nl":     "nl_panel.csv",
    "be":     "be_panel.csv",
    "pt":     "pt_panel.csv",
}


def enforce_causal_growth(df: pd.DataFrame) -> pd.DataFrame:
    """Recompute growth_* from lagged births only — Phase 4E causal contract.

    Phase 4A/4D LEGACY BUG: ingest_*.py scripts computed
      growth_1y[t] = (y[t] - y[t-1]) / y[t-1]
    which uses the target y[t] directly (lookahead leakage).
    This inflated Phase 4A/4D WMAPEs and invalidates them as baselines.

    Phase 4E canonical formula (this function enforces it):
      growth_1y[t] = (y_{t-1} - y_{t-2}) / y_{t-2}   ← lag1_births, lag2_births
      growth_2y[t] = (y_{t-1} - y_{t-3}) / y_{t-3}   ← lag1_births, lag3_births

    This function is called by build_european_panel before writing any panel.
    validation.py checks the output and raises errors on leakage.
    See reports/HERALD_PHASE4E_A2_DEGRADATION_AUDIT.md.
    """
    out = df.copy()
    required = {"lag1_births", "lag2_births", "lag3_births"}
    if not required.issubset(out.columns):
        return out

    out["growth_1y"] = (out["lag1_births"] - out["lag2_births"]) / out["lag2_births"]
    out["growth_2y"] = (out["lag1_births"] - out["lag3_births"]) / out["lag3_births"]
    out[["growth_1y", "growth_2y"]] = out[["growth_1y", "growth_2y"]].replace(
        [float("inf"), float("-inf")], pd.NA
    )
    return out


def build_country(key: str, out_dir: Path, verbose: bool = True,
                  with_eu_signals: bool = True) -> pd.DataFrame:
    adapter = _ADAPTERS[key]()
    print(f"\n{'='*60}")
    print(f"  Building {key.upper()} panel …")
    df = adapter.build()
    df = enforce_causal_growth(df)

    # Phase 4E-C: overlay harmonised EU signals (lag-1 safe) and recompute
    # mask_eu_signals. Adapters set eu_*_lag1 = NaN; this fills the available
    # national signals without touching the adapter or the model core.
    if with_eu_signals:
        df = attach_eu_signals(df, country=_ISO2[key], verbose=verbose)

    report = adapter.validate(df)
    print_report(report, verbose=verbose)

    out_path = out_dir / _OUT_NAMES[key]
    df.to_csv(out_path, index=False)
    print(f"  Saved → {out_path}  ({len(df)} rows × {df.shape[1]} cols)")

    return df, report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build European canonical panels for HERALD."
    )
    parser.add_argument(
        "--country",
        choices=["france", "nl", "be", "pt", "all"],
        default="all",
        help="Country to build (default: all)",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=_DEFAULT_OUT,
        help=f"Output directory (default: {_DEFAULT_OUT})",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress per-field NaN table in validation output",
    )
    parser.add_argument(
        "--no-eu-signals",
        action="store_true",
        help="Skip the Eurostat EU-signal overlay (eu_*_lag1 stay NaN).",
    )
    args = parser.parse_args()

    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    targets = list(_ADAPTERS.keys()) if args.country == "all" else [args.country]

    all_dfs = []
    all_errors = []

    for key in targets:
        df, report = build_country(key, out_dir, verbose=not args.quiet,
                                   with_eu_signals=not args.no_eu_signals)
        all_dfs.append(df)
        if report["errors"]:
            all_errors.extend([f"[{key.upper()}] {e}" for e in report["errors"]])

    if args.country == "all" and len(all_dfs) > 1:
        combined = pd.concat(all_dfs, ignore_index=True)
        combined_path = out_dir / "european_panel_all.csv"
        combined.to_csv(combined_path, index=False)
        print(f"\n  Combined → {combined_path}  ({len(combined)} rows × {combined.shape[1]} cols)")
        _print_combined_summary(combined)

    print(f"\n{'='*60}")
    if all_errors:
        print(f"  BUILD FAILED — {len(all_errors)} error(s):")
        for e in all_errors:
            print(f"    ✗ {e}")
        sys.exit(1)
    else:
        print("  ALL PANELS BUILT SUCCESSFULLY.")
        print(f"  Output: {out_dir}")


def _print_combined_summary(df: pd.DataFrame) -> None:
    print(f"\n  Combined panel summary:")
    print(f"  {'Country':<8} {'Regions':>8} {'Years':>12} {'Rows':>8} "
          f"{'Target obs%':>12} {'Sector cov%':>12} {'Emp tensor':>11} {'EU sig%':>9}")
    print("  " + "-"*83)
    for country in df["country"].unique():
        sub = df[df["country"] == country]
        n_reg   = sub["region_id"].nunique()
        yr_min  = sub["year"].min()
        yr_max  = sub["year"].max()
        n_rows  = len(sub)
        tgt_pct = sub["mask_target"].mean() * 100
        sec_pct = sub["mask_sector_a10"].mean() * 100
        emp     = int(sub["flag_has_national_employment"].max())
        eu_pct  = sub["mask_eu_signals"].mean() * 100 if "mask_eu_signals" in sub else 0.0
        print(f"  {country:<8} {n_reg:>8} {yr_min}-{yr_max:>4} {n_rows:>8} "
              f"{tgt_pct:>11.1f}% {sec_pct:>11.1f}% {'yes' if emp else 'no':>11} {eu_pct:>8.1f}%")


if __name__ == "__main__":
    main()
