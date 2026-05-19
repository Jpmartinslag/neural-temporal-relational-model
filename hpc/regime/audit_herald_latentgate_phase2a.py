#!/usr/bin/env python3
"""Methodological audit for HERALD LatentGate Phase 2A results.

This script is intentionally operational: it prepares all audit tables/checks
and writes machine-readable outputs. It does not assert scientific conclusions.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd


PHASE2A_CONFIGS: List[Tuple[str, str, str]] = [
    ("manual_flags", "full", "with_source_flags"),
    ("manual_flags", "full", "no_source_flags"),
    ("no_regime", "full", "with_source_flags"),
    ("no_regime", "full", "no_source_flags"),
    ("no_regime", "learned_regime_gate", "with_source_flags"),
    ("no_regime", "learned_regime_gate", "no_source_flags"),
    ("change_point", "learned_regime_gate", "with_source_flags"),
    ("change_point", "learned_regime_gate", "no_source_flags"),
]

SOURCE_COLUMNS = [
    "has_flores_source",
    "has_side_stock_source",
    "has_urssaf_source",
]

LEARNED_SUFFIXES = ("learned_regime_graph", "learned_regime_gate", "learned_regime_both")


@dataclass(frozen=True)
class ParsedTag:
    regime_mode: str
    learned_variant: str
    source_policy: str


def parse_tag(tag: str) -> ParsedTag:
    regime_mode = tag.replace("regime_", "", 1) if tag.startswith("regime_") else tag
    source_policy = "with_source_flags"
    if regime_mode.endswith("_no_source_flags"):
        regime_mode = regime_mode[: -len("_no_source_flags")]
        source_policy = "no_source_flags"
    learned_variant = "none"
    for suffix in LEARNED_SUFFIXES:
        if regime_mode.endswith(f"_{suffix}"):
            regime_mode = regime_mode[: -(len(suffix) + 1)]
            learned_variant = suffix
            break
    return ParsedTag(regime_mode=regime_mode, learned_variant=learned_variant, source_policy=source_policy)


def config_label(regime_mode: str, learned_variant: str, source_policy: str) -> str:
    return f"{regime_mode}|{learned_variant}|{source_policy}"


def build_expected_paths(root: Path, seeds: Sequence[int]) -> Dict[str, List[Path]]:
    out = {"per_run_json": [], "total_csv": [], "sector_csv": [], "internals_npz": [], "metadata_json": []}
    for seed in seeds:
        for mode, variant, source_policy in PHASE2A_CONFIGS:
            tag = f"regime_{mode}"
            if variant != "full":
                tag = f"{tag}_{variant}"
            if source_policy == "no_source_flags":
                tag = f"{tag}_no_source_flags"
            suffix = f"full_{tag}_seed_{seed}"
            out["per_run_json"].append(root / "reports" / "per_run" / f"{tag}_seed_{seed}.json")
            out["total_csv"].append(root / "data_processed" / f"herald_semi_v2_predictions_total_{suffix}_v1.csv")
            out["sector_csv"].append(root / "data_processed" / f"herald_semi_v2_predictions_sector_{suffix}_v1.csv")
            out["internals_npz"].append(root / "data_processed" / f"herald_semi_v2_internals_{suffix}_v1.npz")
            out["metadata_json"].append(root / "metadata" / f"{tag}_seed_{seed}.json")
    return out


def list_existing(root: Path) -> Dict[str, List[Path]]:
    return {
        "per_run_json": sorted((root / "reports" / "per_run").glob("regime_*_seed_*.json")),
        "total_csv": sorted((root / "data_processed").glob("herald_semi_v2_predictions_total_*.csv")),
        "sector_csv": sorted((root / "data_processed").glob("herald_semi_v2_predictions_sector_*.csv")),
        "internals_npz": sorted((root / "data_processed").glob("herald_semi_v2_internals_*.npz")),
        "metadata_json": sorted((root / "metadata").glob("regime_*_seed_*.json")),
    }


def wilcoxon_exact_p(diffs: Sequence[float]) -> Optional[float]:
    d = np.array([float(x) for x in diffs if float(x) != 0.0], dtype=float)
    n = len(d)
    if n == 0:
        return None
    absd = np.abs(d)
    order = np.argsort(absd)
    absd = absd[order]
    signs = np.sign(d[order])

    ranks = np.empty(n, dtype=float)
    i = 0
    rank = 1
    while i < n:
        j = i
        while j < n and absd[j] == absd[i]:
            j += 1
        avg = (rank + (rank + (j - i) - 1)) / 2.0
        ranks[i:j] = avg
        rank += (j - i)
        i = j

    w_plus = float(ranks[signs > 0].sum())
    total = float(ranks.sum())
    w = min(w_plus, total - w_plus)
    count = 0
    total_cfg = 1 << n
    for mask in range(total_cfg):
        s = 0.0
        for idx, rk in enumerate(ranks):
            if (mask >> idx) & 1:
                s += rk
        if min(s, total - s) <= w + 1e-12:
            count += 1
    return float(count / total_cfg)


def load_runs(per_run_json_paths: Iterable[Path]) -> pd.DataFrame:
    rows: List[dict] = []
    for path in sorted(per_run_json_paths):
        payload = json.loads(path.read_text(encoding="utf-8"))
        for run_key, result in payload.items():
            tag = str(result.get("run_tag", ""))
            parsed = parse_tag(tag)
            rows.append(
                {
                    "run_key": run_key,
                    "run_tag": tag,
                    "regime_mode": parsed.regime_mode,
                    "learned_variant": parsed.learned_variant,
                    "source_policy": parsed.source_policy,
                    "config_label": config_label(parsed.regime_mode, parsed.learned_variant, parsed.source_policy),
                    "seed": int(result.get("seed")),
                    "mean_wmape": float(result.get("total_wmape_mean")),
                    "wmape_2025": float(result.get("total_wmape_2025")),
                    "sector_wmape_mean": float(result.get("sector_wmape_mean")),
                    "gamma_geo": float(result.get("gamma_geo")),
                    "gamma_mob": float(result.get("gamma_mob")),
                    "alpha_by_year": result.get("alpha_by_year") or {},
                    "path": str(path),
                }
            )
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values(["config_label", "seed"]).reset_index(drop=True)


def summarize_main(runs: pd.DataFrame) -> pd.DataFrame:
    if runs.empty:
        return pd.DataFrame()
    out = (
        runs.groupby(["regime_mode", "learned_variant", "source_policy"], as_index=False)
        .agg(
            n=("seed", "count"),
            mean_wmape=("mean_wmape", "mean"),
            std_wmape=("mean_wmape", "std"),
            wmape_2025=("wmape_2025", "mean"),
            std_wmape_2025=("wmape_2025", "std"),
            sector_wmape_mean=("sector_wmape_mean", "mean"),
            std_sector_wmape=("sector_wmape_mean", "std"),
            gamma_geo=("gamma_geo", "mean"),
            gamma_mob=("gamma_mob", "mean"),
        )
        .sort_values("mean_wmape")
        .reset_index(drop=True)
    )
    out["gamma_mob_over_geo"] = out["gamma_mob"] / out["gamma_geo"].replace(0.0, np.nan)
    return out


def make_paired_vs_manual(runs: pd.DataFrame) -> pd.DataFrame:
    if runs.empty:
        return pd.DataFrame()
    rows: List[dict] = []
    for source_policy in sorted(runs["source_policy"].unique()):
        sub = runs[runs["source_policy"] == source_policy].copy()
        p_mean = sub.pivot_table(index="seed", columns=["regime_mode", "learned_variant"], values="mean_wmape")
        p_2025 = sub.pivot_table(index="seed", columns=["regime_mode", "learned_variant"], values="wmape_2025")
        p_sec = sub.pivot_table(index="seed", columns=["regime_mode", "learned_variant"], values="sector_wmape_mean")
        if ("manual_flags", "none") not in p_mean.columns:
            continue
        base_mean = p_mean[("manual_flags", "none")]
        base_2025 = p_2025[("manual_flags", "none")]
        base_sec = p_sec[("manual_flags", "none")]
        for col in p_mean.columns:
            if col == ("manual_flags", "none"):
                continue
            alt_label = f"{col[0]}|{col[1]}"
            dm = (p_mean[col] - base_mean).dropna()
            d25 = (p_2025[col] - base_2025).dropna()
            ds = (p_sec[col] - base_sec).dropna()
            rows.append(
                {
                    "source_policy": source_policy,
                    "comparison": f"{alt_label} vs manual_flags|none",
                    "n": int(len(dm)),
                    "wins_mean": int((dm < 0).sum()),
                    "losses_mean": int((dm > 0).sum()),
                    "delta_mean_avg": float(dm.mean()),
                    "wilcoxon_p_mean": wilcoxon_exact_p(dm.tolist()),
                    "wins_2025": int((d25 < 0).sum()),
                    "losses_2025": int((d25 > 0).sum()),
                    "delta_2025_avg": float(d25.mean()),
                    "wilcoxon_p_2025": wilcoxon_exact_p(d25.tolist()),
                    "wins_sector": int((ds < 0).sum()),
                    "losses_sector": int((ds > 0).sum()),
                    "delta_sector_avg": float(ds.mean()),
                    "wilcoxon_p_sector": wilcoxon_exact_p(ds.tolist()),
                }
            )
    return pd.DataFrame(rows).sort_values(["source_policy", "comparison"]).reset_index(drop=True)


def make_source_policy_delta(runs: pd.DataFrame) -> pd.DataFrame:
    if runs.empty:
        return pd.DataFrame()
    rows: List[dict] = []
    for regime_mode, learned_variant in sorted(runs[["regime_mode", "learned_variant"]].drop_duplicates().itertuples(index=False, name=None)):
        sub = runs[(runs["regime_mode"] == regime_mode) & (runs["learned_variant"] == learned_variant)]
        if set(sub["source_policy"].unique()) != {"with_source_flags", "no_source_flags"}:
            continue
        p = sub.pivot(index="seed", columns="source_policy", values=["mean_wmape", "wmape_2025", "sector_wmape_mean"])
        dm = (p[("mean_wmape", "no_source_flags")] - p[("mean_wmape", "with_source_flags")]).dropna()
        d25 = (p[("wmape_2025", "no_source_flags")] - p[("wmape_2025", "with_source_flags")]).dropna()
        ds = (p[("sector_wmape_mean", "no_source_flags")] - p[("sector_wmape_mean", "with_source_flags")]).dropna()
        rows.append(
            {
                "regime_mode": regime_mode,
                "learned_variant": learned_variant,
                "n": int(len(dm)),
                "delta_mean_no_minus_with": float(dm.mean()),
                "wilcoxon_p_mean": wilcoxon_exact_p(dm.tolist()),
                "delta_2025_no_minus_with": float(d25.mean()),
                "wilcoxon_p_2025": wilcoxon_exact_p(d25.tolist()),
                "delta_sector_no_minus_with": float(ds.mean()),
                "wilcoxon_p_sector": wilcoxon_exact_p(ds.tolist()),
            }
        )
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values(["regime_mode", "learned_variant"]).reset_index(drop=True)


def alpha_tables(runs: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    if runs.empty:
        return pd.DataFrame(), pd.DataFrame()
    rows = []
    for r in runs.itertuples(index=False):
        alpha_by_year = r.alpha_by_year if isinstance(r.alpha_by_year, dict) else {}
        for year, value in alpha_by_year.items():
            try:
                yy = int(year)
            except Exception:
                continue
            rows.append(
                {
                    "regime_mode": r.regime_mode,
                    "learned_variant": r.learned_variant,
                    "source_policy": r.source_policy,
                    "seed": int(r.seed),
                    "year": yy,
                    "alpha": float(value),
                }
            )
    if not rows:
        return pd.DataFrame(), pd.DataFrame()
    df = pd.DataFrame(rows)
    by_cfg_year = (
        df.groupby(["regime_mode", "learned_variant", "source_policy", "year"], as_index=False)
        .agg(alpha_mean=("alpha", "mean"), alpha_std=("alpha", "std"), n=("seed", "count"))
        .sort_values(["regime_mode", "learned_variant", "source_policy", "year"])
        .reset_index(drop=True)
    )
    by_seed = (
        df.groupby(["regime_mode", "learned_variant", "source_policy", "seed"], as_index=False)
        .agg(alpha_mean_all_years=("alpha", "mean"), alpha_std_all_years=("alpha", "std"))
        .sort_values(["regime_mode", "learned_variant", "source_policy", "seed"])
        .reset_index(drop=True)
    )
    return by_cfg_year, by_seed


def inspect_npz_for_run(root: Path, run_key: str) -> Optional[dict]:
    npz_path = root / "data_processed" / f"herald_semi_v2_internals_{run_key}_v1.npz"
    if not npz_path.exists():
        return None
    z = np.load(npz_path, allow_pickle=True)
    out: Dict[str, object] = {
        "npz_path": str(npz_path),
        "npz_exists": True,
        "has_latent_regime_values": bool("latent_regime_values" in z.files),
        "has_alpha_values": bool("alpha_values" in z.files),
        "has_adj_delta_by_year": bool("adj_delta_by_year" in z.files),
    }
    if "latent_regime_values" not in z.files:
        out["latent_collapsed"] = True
        return out

    latent = np.array(z["latent_regime_values"], dtype=float)
    if latent.ndim == 1:
        latent = latent[:, None]
    out["latent_shape"] = "x".join(str(int(x)) for x in latent.shape)
    out["latent_mean"] = float(np.nanmean(latent))
    out["latent_std"] = float(np.nanstd(latent))
    out["latent_abs_max"] = float(np.nanmax(np.abs(latent)))
    out["latent_collapsed"] = bool(float(np.nanstd(latent)) < 1e-3)

    latent_year = np.nanmean(latent, axis=1)
    out["latent_step_abs_mean"] = float(np.nanmean(np.abs(np.diff(latent_year)))) if len(latent_year) > 1 else np.nan
    out["latent_step_abs_max"] = float(np.nanmax(np.abs(np.diff(latent_year)))) if len(latent_year) > 1 else np.nan

    if "years" in z.files:
        years = np.array(z["years"]).reshape(-1)
        t = min(len(years), len(latent_year))
        out["years_min"] = int(np.min(years[:t])) if t else None
        out["years_max"] = int(np.max(years[:t])) if t else None
        if t > 1:
            step = np.abs(np.diff(latent_year[:t]))
            idx = int(np.argmax(step))
            out["top_rupture_from_year"] = int(years[idx])
            out["top_rupture_to_year"] = int(years[idx + 1])
            out["top_rupture_magnitude"] = float(step[idx])

    if "alpha_values" in z.files:
        alpha = np.array(z["alpha_values"], dtype=float)
        if alpha.ndim == 1:
            alpha = alpha[:, None]
        alpha_year = np.nanmean(alpha, axis=1)
        m = min(len(alpha_year), len(latent_year))
        if m >= 3 and np.nanstd(alpha_year[:m]) > 0 and np.nanstd(latent_year[:m]) > 0:
            out["corr_latent_mean_vs_alpha_mean"] = float(np.corrcoef(latent_year[:m], alpha_year[:m])[0, 1])
        else:
            out["corr_latent_mean_vs_alpha_mean"] = np.nan

    if "adj_delta_by_year" in z.files:
        adj = np.array(z["adj_delta_by_year"], dtype=float).reshape(-1)
        lstep = np.abs(np.diff(latent_year))
        m = min(len(lstep), len(adj))
        if m >= 3 and np.nanstd(lstep[:m]) > 0 and np.nanstd(adj[:m]) > 0:
            out["corr_latent_abs_step_vs_adj_delta"] = float(np.corrcoef(lstep[:m], adj[:m])[0, 1])
        else:
            out["corr_latent_abs_step_vs_adj_delta"] = np.nan
    return out


def latent_tables(root: Path, runs: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    if runs.empty:
        return pd.DataFrame(), pd.DataFrame()
    sub = runs[runs["learned_variant"] == "learned_regime_gate"].copy()
    if sub.empty:
        return pd.DataFrame(), pd.DataFrame()
    rows = []
    for r in sub.itertuples(index=False):
        rec = inspect_npz_for_run(root, r.run_key)
        if rec is None:
            rows.append(
                {
                    "regime_mode": r.regime_mode,
                    "learned_variant": r.learned_variant,
                    "source_policy": r.source_policy,
                    "seed": int(r.seed),
                    "run_key": r.run_key,
                    "npz_exists": False,
                }
            )
            continue
        rec.update(
            {
                "regime_mode": r.regime_mode,
                "learned_variant": r.learned_variant,
                "source_policy": r.source_policy,
                "seed": int(r.seed),
                "run_key": r.run_key,
            }
        )
        rows.append(rec)
    per_run = pd.DataFrame(rows)

    summary_cols = [
        "latent_std",
        "latent_step_abs_mean",
        "latent_step_abs_max",
        "corr_latent_mean_vs_alpha_mean",
        "corr_latent_abs_step_vs_adj_delta",
    ]
    existing_summary_cols = [c for c in summary_cols if c in per_run.columns]
    per_cfg = (
        per_run.groupby(["regime_mode", "learned_variant", "source_policy"], as_index=False)[existing_summary_cols]
        .mean(numeric_only=True)
        .sort_values(["regime_mode", "learned_variant", "source_policy"])
        .reset_index(drop=True)
    )
    if "latent_collapsed" in per_run.columns:
        collapsed = (
            per_run.groupby(["regime_mode", "learned_variant", "source_policy"], as_index=False)["latent_collapsed"]
            .sum()
            .rename(columns={"latent_collapsed": "collapsed_count"})
        )
        per_cfg = per_cfg.merge(collapsed, on=["regime_mode", "learned_variant", "source_policy"], how="left")
    return per_run, per_cfg


def source_flag_audit(root: Path, runs: pd.DataFrame) -> pd.DataFrame:
    if runs.empty:
        return pd.DataFrame()
    rows = []
    for r in runs.itertuples(index=False):
        tag = r.run_tag
        meta_path = root / "metadata" / f"{tag}_seed_{int(r.seed)}.json"
        ok = meta_path.exists()
        rec = {
            "regime_mode": r.regime_mode,
            "learned_variant": r.learned_variant,
            "source_policy": r.source_policy,
            "seed": int(r.seed),
            "meta_path": str(meta_path),
            "meta_exists": bool(ok),
            "source_flags_in_annual_features": np.nan,
            "dropped_source_flags_count": np.nan,
            "dropped_source_flags": "",
            "source_flag_policy_ok": False,
        }
        if ok:
            payload = json.loads(meta_path.read_text(encoding="utf-8"))
            source_in = payload.get("source_flags_in_annual_features")
            dropped = payload.get("dropped_source_flags") or []
            rec["source_flags_in_annual_features"] = bool(source_in)
            rec["dropped_source_flags_count"] = int(len(dropped))
            rec["dropped_source_flags"] = ",".join(sorted(str(x) for x in dropped))
            if r.source_policy == "no_source_flags":
                rec["source_flag_policy_ok"] = (
                    source_in is False and sorted(dropped) == sorted(SOURCE_COLUMNS)
                )
            else:
                rec["source_flag_policy_ok"] = (source_in is True)
        rows.append(rec)
    df = pd.DataFrame(rows)
    return df.sort_values(["regime_mode", "learned_variant", "source_policy", "seed"]).reset_index(drop=True)


def write_markdown_stub(
    out_path: Path,
    integrity: dict,
    main_table_path: Path,
    paired_path: Path,
    source_delta_path: Path,
    latent_cfg_path: Path,
    source_audit_path: Path,
) -> None:
    lines = [
        "# HERALD LatentGate Phase 2A Audit (draft, no conclusion)",
        "",
        "This report is intentionally pre-interpretation. Fill narrative only after all expected artifacts arrive.",
        "",
        "## Checklist de integridade",
        "",
        f"- Completion ratio: `{integrity['completion_ratio']:.2%}`",
        f"- Expected runs: `{integrity['expected_runs']}`",
        f"- Observed runs: `{integrity['observed_runs']}`",
        f"- Expected seeds: `{integrity['expected_seed_count']}`",
        f"- Observed seeds: `{integrity['observed_seed_count']}`",
        "",
        "Artifact counts:",
        "",
        f"- per_run JSON: `{integrity['counts']['per_run_json']['observed']}` / `{integrity['counts']['per_run_json']['expected']}`",
        f"- total CSV: `{integrity['counts']['total_csv']['observed']}` / `{integrity['counts']['total_csv']['expected']}`",
        f"- sector CSV: `{integrity['counts']['sector_csv']['observed']}` / `{integrity['counts']['sector_csv']['expected']}`",
        f"- internals NPZ: `{integrity['counts']['internals_npz']['observed']}` / `{integrity['counts']['internals_npz']['expected']}`",
        f"- metadata JSON: `{integrity['counts']['metadata_json']['observed']}` / `{integrity['counts']['metadata_json']['expected']}`",
        "",
        "## Tabelas geradas",
        "",
        f"- Tabela principal: `{main_table_path.name}`",
        f"- Tabela pareada vs manual_flags: `{paired_path.name}`",
        f"- with_source vs no_source: `{source_delta_path.name}`",
        f"- Latente (agregado): `{latent_cfg_path.name}`",
        f"- Auditoria source flags: `{source_audit_path.name}`",
        "",
        "## Veredito",
        "",
        "_Pending data completion and post-hoc interpretation._",
    ]
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True, help="OUT_ROOT of phase 2A run")
    parser.add_argument(
        "--seeds",
        default="0 1 7 13 17 42 77 99 123 2025",
        help="Expected seeds as space-separated integers",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Defaults to <root>/reports/audit_phase2a",
    )
    parser.add_argument("--strict", action="store_true", help="Exit non-zero on incompleteness")
    args = parser.parse_args()

    root = args.root
    output_dir = args.output_dir or (root / "reports" / "audit_phase2a")
    output_dir.mkdir(parents=True, exist_ok=True)
    seeds = [int(x) for x in args.seeds.split()]

    expected = build_expected_paths(root, seeds)
    observed = list_existing(root)

    counts = {}
    missing_index = {}
    extra_index = {}
    for key in expected:
        exp_set = set(expected[key])
        obs_set = set(observed[key])
        counts[key] = {"expected": len(exp_set), "observed": len(obs_set)}
        missing_index[key] = sorted(str(p) for p in (exp_set - obs_set))
        extra_index[key] = sorted(str(p) for p in (obs_set - exp_set))

    runs = load_runs(observed["per_run_json"])
    main_table = summarize_main(runs)
    paired = make_paired_vs_manual(runs)
    source_delta = make_source_policy_delta(runs)
    alpha_cfg_year, alpha_seed = alpha_tables(runs)
    latent_per_run, latent_cfg = latent_tables(root, runs)
    source_audit = source_flag_audit(root, runs)

    expected_runs = len(seeds) * len(PHASE2A_CONFIGS)
    observed_runs = int(len(runs))
    completion_ratio = (observed_runs / expected_runs) if expected_runs else 0.0
    observed_seed_count = int(runs["seed"].nunique()) if not runs.empty else 0

    integrity = {
        "expected_runs": expected_runs,
        "observed_runs": observed_runs,
        "completion_ratio": completion_ratio,
        "expected_seed_count": len(seeds),
        "observed_seed_count": observed_seed_count,
        "counts": counts,
        "missing_paths": missing_index,
        "extra_paths": extra_index,
        "config_seed_counts": (
            runs.groupby(["regime_mode", "learned_variant", "source_policy"])["seed"].nunique().reset_index().to_dict(orient="records")
            if not runs.empty
            else []
        ),
    }

    expected_config_counts = {}
    for mode, variant, source_policy in PHASE2A_CONFIGS:
        learned_variant = "none" if variant == "full" else variant
        label = config_label(mode, learned_variant, source_policy)
        expected_config_counts[label] = len(seeds)
    observed_config_counts = (
        runs.groupby("config_label")["seed"].nunique().to_dict() if not runs.empty else {}
    )
    config_count_ok = all(
        int(observed_config_counts.get(label, 0)) == expected
        for label, expected in expected_config_counts.items()
    )
    integrity["expected_config_counts"] = expected_config_counts
    integrity["observed_config_counts"] = {str(k): int(v) for k, v in observed_config_counts.items()}
    integrity["config_count_ok"] = bool(config_count_ok)

    # Save outputs
    runs_path = output_dir / "phase2a_runs_normalized.csv"
    main_path = output_dir / "phase2a_main_table.csv"
    paired_path = output_dir / "phase2a_paired_vs_manual.csv"
    source_delta_path = output_dir / "phase2a_source_policy_delta.csv"
    alpha_cfg_year_path = output_dir / "phase2a_alpha_by_config_year.csv"
    alpha_seed_path = output_dir / "phase2a_alpha_by_seed.csv"
    latent_run_path = output_dir / "phase2a_latent_per_run.csv"
    latent_cfg_path = output_dir / "phase2a_latent_by_config.csv"
    source_audit_path = output_dir / "phase2a_source_flag_audit.csv"
    integrity_path = output_dir / "phase2a_integrity.json"
    md_stub_path = output_dir / "PHASE2A_AUDIT_DRAFT.md"

    runs.to_csv(runs_path, index=False)
    main_table.to_csv(main_path, index=False)
    paired.to_csv(paired_path, index=False)
    source_delta.to_csv(source_delta_path, index=False)
    alpha_cfg_year.to_csv(alpha_cfg_year_path, index=False)
    alpha_seed.to_csv(alpha_seed_path, index=False)
    latent_per_run.to_csv(latent_run_path, index=False)
    latent_cfg.to_csv(latent_cfg_path, index=False)
    source_audit.to_csv(source_audit_path, index=False)
    integrity_path.write_text(json.dumps(integrity, indent=2, ensure_ascii=False), encoding="utf-8")
    write_markdown_stub(
        md_stub_path,
        integrity=integrity,
        main_table_path=main_path,
        paired_path=paired_path,
        source_delta_path=source_delta_path,
        latent_cfg_path=latent_cfg_path,
        source_audit_path=source_audit_path,
    )

    print(f"Saved: {runs_path}")
    print(f"Saved: {main_path}")
    print(f"Saved: {paired_path}")
    print(f"Saved: {source_delta_path}")
    print(f"Saved: {alpha_cfg_year_path}")
    print(f"Saved: {alpha_seed_path}")
    print(f"Saved: {latent_run_path}")
    print(f"Saved: {latent_cfg_path}")
    print(f"Saved: {source_audit_path}")
    print(f"Saved: {integrity_path}")
    print(f"Saved: {md_stub_path}")
    print(
        f"Completion: {observed_runs}/{expected_runs} runs "
        f"({completion_ratio:.2%}) | seeds={observed_seed_count}/{len(seeds)}"
    )

    if args.strict:
        source_ok = bool(source_audit["source_flag_policy_ok"].all()) if not source_audit.empty else False
        paths_exact = all(
            not missing_index[k] and not extra_index[k]
            for k in missing_index
        )
        complete = (
            observed_runs == expected_runs
            and all(counts[k]["observed"] == counts[k]["expected"] for k in counts)
            and paths_exact
            and config_count_ok
            and source_ok
        )
        if not complete:
            raise SystemExit(2)


if __name__ == "__main__":
    main()
