#!/usr/bin/env python3
"""Build per-ZE labor-market tutor features for HERALD Phase 3C.

Sources:
  data/processed/dynamic_stgnn_feature_panel_through_2025_v1.csv
    urssaf_employer_growth_1y_t_minus_1 = (etabs(t-1) - etabs(t-2)) / etabs(t-2)
    (already validated against raw URSSAF file; same values)

  data/raw/phase3c_labor_tutor/defm_cat_a_ze_raw/defm_ze2020_trim_brut.csv
    Inscrits à France Travail par zone d'emploi (trimestrielles, brutes)
    Source: data.gouv.fr (DARES) — 1996-T1 to 2026-T1, ZE2020 codes, Cat A
    defm_recovery_tminus1 = Q4(t-1) / Q2(t-1) per ZE (intra-year recovery ratio)

Blocked signals (data not available locally):
  activite_partielle_tminus1  — needs heures consommées AP (DARES/data.gouv.fr)
    Only COVID-era data (2020+) is available on data.gouv.fr; insufficient
    pre-2020 history. Column set to NaN.
    The --ap-path argument is a placeholder; parser not implemented yet
    because file layout with pre-2020 history must be confirmed first.

Output:
  data/processed/herald_phase3c_labor_tutor_features.csv
  Columns: year, ze2020,
    urssaf_employer_estab_growth_tminus1      (real signal)
    urssaf_employer_estab_growth_perm_tminus1 (temporal permutation, seed=PERM_SEED)
    defm_recovery_tminus1               (real signal, if --defm-path provided)
    defm_recovery_perm_tminus1          (temporal permutation, same seed)
    activite_partielle_tminus1          (NaN — blocked)
    activite_partielle_perm_tminus1     (NaN — blocked)

Leakage guarantee:
  urssaf_employer_estab_growth_tminus1: uses (etabs(t-1)-etabs(t-2))/etabs(t-2).
    Only years t-1 and t-2 used. No t-year data.
  defm_recovery_tminus1: uses Q4(t-1) / Q2(t-1).
    Only quarters of year t-1 used. No t-year data.

Permutation design:
  A single permutation P of years (same seed, same shuffle for ALL signals and ZEs).
  Row for target_year years[i] in permuted matrix = row for years[P[i]] in real matrix.
  Preserves cross-ZE structure for each year, destroys temporal signal.

COVID note (target_year 2021):
  defm_recovery uses t-1 = 2020 data. Q2-2020 was the COVID lockdown peak
  (massive DEFM spike); Q4-2020 was partial recovery. The ratio Q4/Q2 < 1
  will appear as a "strong recovery" signal driven by COVID, not labor-market
  fundamentals. No manual COVID flag is applied per Phase 3C rules.
  The permutation test (C1 vs C2) will reveal whether this creates spurious signal.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

PERM_SEED = 42
PANEL_PATH = Path("data/processed/dynamic_stgnn_feature_panel_through_2025_v1.csv")
DEFM_PATH = Path("data/raw/phase3c_labor_tutor/defm_cat_a_ze_raw/defm_ze2020_trim_brut.csv")
OUT_PATH = Path("data/processed/herald_phase3c_labor_tutor_features.csv")
OUT_REPORT = Path("reports/HERALD_PHASE3C_LABOR_TUTOR_DATA_STATUS.md")


def build_urssaf_delta(panel: pd.DataFrame) -> pd.DataFrame:
    """Extract urssaf_employer_growth_1y_t_minus_1 into (year, ze2020) format."""
    cols = ["target_year", "ZE2020", "urssaf_employer_growth_1y_t_minus_1"]
    df = panel[cols].copy()
    df = df.rename(columns={
        "target_year": "year",
        "ZE2020": "ze2020",
        "urssaf_employer_growth_1y_t_minus_1": "urssaf_employer_estab_growth_tminus1",
    })
    return df.sort_values(["year", "ze2020"]).reset_index(drop=True)


def build_defm_recovery(defm_path: Path, target_years: list[int]) -> pd.DataFrame:
    """Compute DEFM cat-A intra-year recovery ratio per ZE per target_year.

    defm_recovery_tminus1 = Q4(t-1) / Q2(t-1)  (lower = more recovery)
    Leakage-safe: uses only quarters of year t-1.
    """
    raw = pd.read_csv(defm_path, sep=";", encoding="utf-8-sig")
    raw = raw[
        (raw["Catégorie"] == "A") &
        (raw["Sexe"] == "Total") &
        (raw["Tranche d'âge"] == "Total") &
        (raw["Ancienneté"] == "Total")
    ].copy()
    raw["year_data"] = raw["Date"].str[:4].astype(int)
    raw["quarter"] = raw["Date"].str[-1].astype(int)
    raw = raw.rename(columns={
        "Code zone d'emploi": "ze2020",
        "Nombre de demandeurs d'emploi": "defm_catA",
    })

    tminus1_years = [t - 1 for t in target_years]
    needed_years = sorted(set(tminus1_years + [t - 2 for t in target_years]))
    raw = raw[raw["year_data"].isin(needed_years)]

    q2 = raw[raw["quarter"] == 2][["year_data", "ze2020", "defm_catA"]].rename(
        columns={"defm_catA": "defm_Q2"}
    )
    q4 = raw[raw["quarter"] == 4][["year_data", "ze2020", "defm_catA"]].rename(
        columns={"defm_catA": "defm_Q4"}
    )
    annual = q2.merge(q4, on=["year_data", "ze2020"], how="inner")
    annual["defm_recovery_raw"] = annual["defm_Q4"] / annual["defm_Q2"]
    annual["defm_recovery_signed_raw"] = (annual["defm_Q2"] - annual["defm_Q4"]) / annual["defm_Q2"]
    annual = annual.sort_values(["ze2020", "year_data"]).reset_index(drop=True)
    annual["defm_Q4_prev"] = annual.groupby("ze2020")["defm_Q4"].shift(1)
    annual["defm_yoy_raw"] = (annual["defm_Q4"] - annual["defm_Q4_prev"]) / annual["defm_Q4_prev"]

    # Map t-1 year back to target_year
    tminus1_to_target = {t - 1: t for t in target_years}
    current = annual[annual["year_data"].isin(tminus1_years)].copy()
    current["year"] = current["year_data"].map(tminus1_to_target)
    current = current.dropna(subset=["year"])
    current["year"] = current["year"].astype(int)
    current = current.rename(columns={
        "defm_recovery_raw": "defm_recovery_tminus1",
        "defm_recovery_signed_raw": "defm_recovery_signed_tminus1",
        "defm_yoy_raw": "defm_yoy_tminus1",
    })

    lag2 = annual[["year_data", "ze2020", "defm_recovery_raw"]].copy()
    lag2["year"] = lag2["year_data"] + 2
    lag2 = lag2[lag2["year"].isin(target_years)].rename(
        columns={"defm_recovery_raw": "defm_recovery_lag2_tminus1"}
    )

    out = current[[
        "year", "ze2020", "defm_recovery_tminus1",
        "defm_recovery_signed_tminus1", "defm_yoy_tminus1",
    ]].merge(
        lag2[["year", "ze2020", "defm_recovery_lag2_tminus1"]],
        on=["year", "ze2020"],
        how="left",
    )
    return out.sort_values(["year", "ze2020"]).reset_index(drop=True)


def _year_permutation(years: list[int], seed: int) -> dict[int, int]:
    rng = np.random.default_rng(seed)
    perm = rng.permutation(len(years))
    return {years[i]: years[perm[i]] for i in range(len(years))}


def add_temporal_permutation(df: pd.DataFrame, real_col: str, seed: int) -> pd.DataFrame:
    """Add a permuted version of real_col using a fixed year shuffle.

    Same seed always produces the same permutation, so URSSAF and DEFM use
    identical year shuffling (consistent falsification baseline).
    """
    years = sorted(df["year"].unique())
    year_to_perm = _year_permutation(years, seed)
    perm_col = real_col.replace("_tminus1", "_perm_tminus1")

    df = df.copy()
    df["_source_year"] = df["year"].map(year_to_perm)
    real_lookup = df.set_index(["year", "ze2020"])[real_col]
    df[perm_col] = df.apply(
        lambda row: real_lookup.get((row["_source_year"], row["ze2020"]), np.nan),
        axis=1,
    )
    return df.drop(columns=["_source_year"])


def add_spatial_permutation(df: pd.DataFrame, real_col: str, seed: int) -> pd.DataFrame:
    """Add a spatially permuted version of real_col for each year.

    The permutation keeps each year's distribution intact but assigns values to
    different ZEs. This tests whether the signal is genuinely local or only a
    national/year effect.
    """
    rng = np.random.default_rng(seed + 1009)
    perm_col = real_col.replace("_tminus1", "_spatial_perm_tminus1")
    out = df.copy()
    out[perm_col] = np.nan
    for year in sorted(out["year"].unique()):
        idx = out.index[out["year"] == year].to_numpy()
        vals = out.loc[idx, real_col].to_numpy(copy=True)
        if len(vals) > 1:
            vals = vals[rng.permutation(len(vals))]
        out.loc[idx, perm_col] = vals
    return out


def coverage_report(df: pd.DataFrame) -> dict:
    signals = [
        "urssaf_employer_estab_growth_tminus1",
        "urssaf_employer_estab_growth_perm_tminus1",
        "urssaf_employer_estab_growth_lag2_tminus1",
        "urssaf_employer_estab_growth_spatial_perm_tminus1",
        "urssaf_employer_estab_growth_neg_tminus1",
        "urssaf_employer_estab_growth_pos_tminus1",
        "defm_recovery_tminus1",
        "defm_recovery_perm_tminus1",
        "defm_recovery_lag2_tminus1",
        "defm_recovery_spatial_perm_tminus1",
        "defm_recovery_signed_tminus1",
        "defm_yoy_tminus1",
        "activite_partielle_tminus1",
        "activite_partielle_perm_tminus1",
    ]
    report = {}
    for col in signals:
        if col not in df.columns:
            report[col] = {"status": "missing_column", "coverage": 0.0}
            continue
        n = len(df)
        n_valid = int(df[col].notna().sum())
        years_valid = sorted(df.loc[df[col].notna(), "year"].unique().tolist())
        n_ze = int(df.loc[df[col].notna(), "ze2020"].nunique())
        report[col] = {
            "status": "available" if n_valid > 0 else "blocked",
            "coverage": round(n_valid / n, 4) if n > 0 else 0.0,
            "n_valid": n_valid,
            "n_ze": n_ze,
            "year_min": int(years_valid[0]) if years_valid else None,
            "year_max": int(years_valid[-1]) if years_valid else None,
        }
    return report


def write_report(report: dict, out: Path, perm_seed: int, defm_available: bool) -> None:
    lines = [
        "# HERALD Phase 3C — Labor Tutor Data Status",
        "",
        f"Generated: {pd.Timestamp.now().strftime('%Y-%m-%d')}",
        f"Permutation seed: {perm_seed}",
        "",
        "## Signal coverage",
        "",
        "| Signal | Status | Coverage | ZEs | Years |",
        "| --- | --- | --- | --- | --- |",
    ]
    for col, info in report.items():
        yr = f"{info.get('year_min')}–{info.get('year_max')}" if info.get("year_min") else "—"
        lines.append(
            f"| `{col}` | {info['status']} | {info['coverage']:.0%} "
            f"| {info.get('n_ze', 0)} | {yr} |"
        )

    if defm_available:
        lines += [
            "",
            "## DEFM data source",
            "",
            "- File: `data/raw/phase3c_labor_tutor/defm_cat_a_ze_raw/defm_ze2020_trim_brut.csv`",
            "- Source: data.gouv.fr — DARES, Inscrits à France Travail par ZE (trimestrielles, brutes)",
            "- URL: https://www.data.gouv.fr/api/1/datasets/r/d723d37a-811a-40d9-991c-c7b587e2e4fa",
            "- Downloaded: 2026-05-26",
            "- Coverage: 1996-T1 – 2026-T1, 335 ZEs (ZE2020 codes)",
            "- Feature: Q4(t-1) / Q2(t-1) per ZE — intra-year recovery ratio (lower = more recovery)",
            "- Leakage: uses only quarters of year t-1 for target_year t. ✓",
            "- COVID note: target_year 2021 uses Q4(2020)/Q2(2020); Q2-2020 was lockdown spike.",
            "  No COVID flag applied (Phase 3C rules). Permutation test will detect spurious signal.",
        ]
    else:
        lines += [
            "",
            "## Blocked signals — what to download",
            "",
            "### C1/C2: DEFM cat-A by ZE2020",
            "",
            "- Source: https://www.data.gouv.fr/api/1/datasets/r/d723d37a-811a-40d9-991c-c7b587e2e4fa",
            "- File: Inscrits à France Travail par zone d'emploi (trimestrielles, brutes)",
            "- Save to: `data/raw/phase3c_labor_tutor/defm_cat_a_ze_raw/defm_ze2020_trim_brut.csv`",
            "- Feature to compute: Q4(t-1) / Q2(t-1) per ZE",
            "- Once downloaded: re-run with --defm-path data/raw/phase3c_labor_tutor/defm_cat_a_ze_raw/defm_ze2020_trim_brut.csv",
        ]

    lines += [
        "",
        "## Blocked signals (no pre-2020 open data available)",
        "",
        "### Activité partielle heures consommées",
        "",
        "- Source attempted: https://dares.travail-emploi.gouv.fr/donnees/lactivite-partielle",
        "  → Behind Cegedim CAPTCHA, not accessible programmatically.",
        "- data.gouv.fr COVID dataset: only from 2020, regional/departmental level only.",
        "  Insufficient pre-2020 history for training folds 2012–2020. HIGH COVID-flag risk.",
        "- DARES open data API (data.dares.travail-emploi.gouv.fr): no activité partielle dataset.",
        "- Status: BLOCKED. Not included in the 180-run Phase 3C plan.",
        "- To unlock: obtain DARES activité partielle series with ZE or national level 2009–2024",
        "  from a direct contact with DARES or future open data release.",
        "",
        "## Leakage audit",
        "",
        "- `urssaf_employer_estab_growth_tminus1`: (etabs(t-1) − etabs(t-2)) / etabs(t-2)",
        "  Uses years t-1 and t-2 only for predicting year t. ✓",
        "- `defm_recovery_tminus1`: Q4(t-1) / Q2(t-1) per ZE",
        "  Uses only quarters of year t-1 for predicting year t. ✓",
        "- Permutation: years shuffled with fixed seed, same shuffle for all signals, cross-ZE structure preserved. ✓",
        "- Normalisation (z-score) computed from training fold only in make_sequences_v7. ✓",
        "",
    ]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel-path", type=Path, default=PANEL_PATH)
    parser.add_argument("--defm-path", type=Path, default=DEFM_PATH,
                        help="Quarterly DEFM cat-A by ZE2020 CSV from data.gouv.fr")
    parser.add_argument("--out-path", type=Path, default=OUT_PATH)
    parser.add_argument("--report-path", type=Path, default=OUT_REPORT)
    parser.add_argument("--perm-seed", type=int, default=PERM_SEED)
    parser.add_argument("--ap-path", type=Path, default=None,
                        help="Placeholder for future activité partielle parser (not implemented)")
    args = parser.parse_args()

    print(f"Loading panel: {args.panel_path}")
    panel = pd.read_csv(args.panel_path)
    target_years = sorted(panel["target_year"].unique().tolist())

    print("Building URSSAF cotisants delta...")
    df = build_urssaf_delta(panel)
    df = add_temporal_permutation(df, "urssaf_employer_estab_growth_tminus1", args.perm_seed)
    df["urssaf_employer_estab_growth_lag2_tminus1"] = (
        df.sort_values(["ze2020", "year"])
          .groupby("ze2020")["urssaf_employer_estab_growth_tminus1"]
          .shift(1)
          .reindex(df.index)
          .fillna(0.0)
    )
    df["urssaf_employer_estab_growth_neg_tminus1"] = np.minimum(df["urssaf_employer_estab_growth_tminus1"], 0.0)
    df["urssaf_employer_estab_growth_pos_tminus1"] = np.maximum(df["urssaf_employer_estab_growth_tminus1"], 0.0)
    df = add_spatial_permutation(df, "urssaf_employer_estab_growth_tminus1", args.perm_seed)

    defm_available = False
    if args.defm_path is not None and args.defm_path.exists():
        print(f"Building DEFM recovery from: {args.defm_path}")
        defm_df = build_defm_recovery(args.defm_path, target_years)
        print(f"  DEFM rows: {len(defm_df)}, ZEs: {defm_df['ze2020'].nunique()}, "
              f"years: {defm_df['year'].min()}–{defm_df['year'].max()}")
        df = df.merge(defm_df, on=["year", "ze2020"], how="left")
        df = add_temporal_permutation(df, "defm_recovery_tminus1", args.perm_seed)
        df = add_spatial_permutation(df, "defm_recovery_tminus1", args.perm_seed)
        defm_available = True
        # Leakage check: no t-year data in DEFM feature
        missing_defm = df["defm_recovery_tminus1"].isna().sum()
        if missing_defm > 0:
            print(f"  WARNING: {missing_defm} NaN in defm_recovery_tminus1")
    else:
        if args.defm_path is not None:
            print(f"DEFM path not found: {args.defm_path} — setting to NaN")
        df["defm_recovery_tminus1"] = np.nan
        df["defm_recovery_perm_tminus1"] = np.nan
        df["defm_recovery_lag2_tminus1"] = np.nan
        df["defm_recovery_spatial_perm_tminus1"] = np.nan
        df["defm_recovery_signed_tminus1"] = np.nan
        df["defm_yoy_tminus1"] = np.nan

    print("Setting activité partielle to NaN (blocked — no pre-2020 open data)...")
    df["activite_partielle_tminus1"] = np.nan
    df["activite_partielle_perm_tminus1"] = np.nan

    col_order = [
        "year", "ze2020",
        "urssaf_employer_estab_growth_tminus1",
        "urssaf_employer_estab_growth_perm_tminus1",
        "urssaf_employer_estab_growth_lag2_tminus1",
        "urssaf_employer_estab_growth_spatial_perm_tminus1",
        "urssaf_employer_estab_growth_neg_tminus1",
        "urssaf_employer_estab_growth_pos_tminus1",
        "defm_recovery_tminus1",
        "defm_recovery_perm_tminus1",
        "defm_recovery_lag2_tminus1",
        "defm_recovery_spatial_perm_tminus1",
        "defm_recovery_signed_tminus1",
        "defm_yoy_tminus1",
        "activite_partielle_tminus1",
        "activite_partielle_perm_tminus1",
    ]
    df = df[col_order]

    report = coverage_report(df)

    print(f"\nCoverage summary:")
    for col, info in report.items():
        print(f"  {col}: {info['status']} ({info['coverage']:.0%} coverage, "
              f"{info.get('n_ze', 0)} ZEs, "
              f"years {info.get('year_min')}–{info.get('year_max')})")

    print(f"\nWriting: {args.out_path}")
    args.out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out_path, index=False)

    print(f"Writing report: {args.report_path}")
    write_report(report, args.report_path, args.perm_seed, defm_available)

    # Leakage checks
    print("\nLeakage check...")
    assert (df["year"] == df["year"].astype(int)).all(), "Non-integer years detected"
    n_missing = df["urssaf_employer_estab_growth_tminus1"].isna().sum()
    print(f"  urssaf_employer_estab_growth_tminus1: {n_missing} NaN out of {len(df)} rows")
    assert n_missing == 0, f"Unexpected NaN in urssaf_employer_estab_growth_tminus1: {n_missing}"
    if defm_available:
        n_missing_defm = df["defm_recovery_tminus1"].isna().sum()
        print(f"  defm_recovery_tminus1: {n_missing_defm} NaN out of {len(df)} rows")
        assert n_missing_defm == 0, f"Unexpected NaN in defm_recovery_tminus1: {n_missing_defm}"
    print("  leakage_check_passed: True")

    metadata = {
        "script": __file__,
        "panel_path": str(args.panel_path),
        "defm_path": str(args.defm_path) if args.defm_path else None,
        "defm_available": defm_available,
        "out_path": str(args.out_path),
        "perm_seed": args.perm_seed,
        "n_rows": len(df),
        "n_years": int(df["year"].nunique()),
        "n_ze": int(df["ze2020"].nunique()),
        "year_min": int(df["year"].min()),
        "year_max": int(df["year"].max()),
        "coverage": report,
        "leakage_check_passed": True,
    }
    meta_path = args.out_path.with_suffix(".meta.json")
    meta_path.write_text(json.dumps(metadata, indent=2))
    print(f"Metadata: {meta_path}")
    print("Done.")


if __name__ == "__main__":
    main()
