"""HERALD DEC-027 — E0 Engineering Smoke: NL (Netherlands/COROP).

Purpose
-------
Validate the full data pipeline — tensor loading, causal ordering, adjacency
sequences, masks, Ridge alignment, dummy model pass, determinism, runtime and
memory — using NL as an engineering smoke.

NL is chosen because it has 40 COROP regions and complete 9-sector coverage,
making it a good-faith stress test of the pipeline at low scientific cost.

Scientific scope
----------------
This smoke is E0 (engineering validation only).  NL's G2 result is
COVID-SENSITIVE; NL does NOT constitute scientific evidence for graph models.
The first scientific local test (S1) uses FR.

Gate (all must pass for E0_PASS)
---------------------------------
* All 6 checks pass (leakage, masks, NaN/Inf, alignment, determinism, limits).
* runtime < 600s (10 min); peak memory < 4 GB.
* zero leakage violations.
* zero mask errors.
* identical outputs across two runs with the same seed.

Usage
-----
    python -m src.modeles.run_e0_smoke_nl
    python -m src.modeles.run_e0_smoke_nl --eval-years 2019 2020 2021 --seed 42
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import time
import tracemalloc
from pathlib import Path

import numpy as np

BASE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE))

from src.data.european_panel.build_graph_temporal_preflight import (
    LeakageError,
    export_preflight,
    load_fold,
    load_manifest,
    DEFAULT_OUT,
    DEFAULT_SECTOR_PANEL,
    DEFAULT_PANEL_DIR,
    WINDOW,
    MIN_PERIODS,
)

COUNTRY = "NL"
DEFAULT_EVAL_YEARS = [2019, 2020, 2021]
DEFAULT_SEED = 42
RUNTIME_LIMIT_S = 600.0  # 10 minutes on CPU
MEMORY_LIMIT_GB = 4.0

FINDINGS: list[str] = []
FAILURES: list[str] = []


def log(msg: str, severity: str = "INFO") -> None:
    FINDINGS.append(f"[{severity}] {msg}")
    print(f"[{severity}] {msg}")


# ---------------------------------------------------------------------------
# Check 1: Causal ordering
# ---------------------------------------------------------------------------

def check_causal_ordering(fold: dict, eval_year: int) -> bool:
    """Verify max(source_observation_year) < eval_year via manifest."""
    manifest = load_manifest(DEFAULT_OUT)
    fold_meta = next(
        (f for f in manifest["folds"]
         if f["country"] == COUNTRY and f["eval_year"] == eval_year),
        None,
    )
    if fold_meta is None:
        FAILURES.append(f"E0.causal: no manifest entry for NL/{eval_year}")
        return False

    max_obs = fold_meta["max_train_obs_year"]
    if max_obs >= eval_year:
        FAILURES.append(
            f"E0.causal: max_train_obs_year={max_obs} >= eval_year={eval_year} — LEAKAGE"
        )
        return False

    log(f"causal check OK: NL/{eval_year} max_obs={max_obs} < eval_year")
    return True


# ---------------------------------------------------------------------------
# Check 2: Adjacency sequence and sector ordering
# ---------------------------------------------------------------------------

def check_adjacency(fold: dict, eval_year: int, sectors: list[str]) -> bool:
    adj = fold["adj"]
    n_s, n_r, n_r2 = adj.shape
    ok = True

    if n_r != n_r2:
        FAILURES.append(f"E0.adj: non-square adjacency at NL/{eval_year}: {adj.shape}")
        ok = False

    # Symmetry
    for s in range(n_s):
        A = adj[s]
        finite = np.isfinite(A)
        diff = np.abs(A - A.T)
        if np.any(diff[finite & finite.T] > 1e-10):
            FAILURES.append(f"E0.adj: sector {sectors[s]} adjacency not symmetric at NL/{eval_year}")
            ok = False

    # Diagonal
    for s in range(n_s):
        diag = np.diag(adj[s])
        finite_diag = diag[np.isfinite(diag)]
        if len(finite_diag) and not np.allclose(finite_diag, 1.0):
            FAILURES.append(f"E0.adj: sector {sectors[s]} diagonal not 1.0 at NL/{eval_year}")
            ok = False

    if ok:
        log(f"adjacency check OK: NL/{eval_year} shape={adj.shape} symmetric diagonal=1")
    return ok


# ---------------------------------------------------------------------------
# Check 3: Masks
# ---------------------------------------------------------------------------

def check_masks(fold: dict, eval_year: int) -> bool:
    ok = True
    obs = fold["obs_mask"]
    struct = fold["struct_mask"]
    tm = fold["target_mask"]

    for name, arr in [("obs_mask", obs), ("struct_mask", struct), ("target_mask", tm)]:
        if np.any(np.isnan(arr.astype(float))):
            FAILURES.append(f"E0.masks: NaN in {name} at NL/{eval_year}")
            ok = False
        bad_vals = np.setdiff1d(np.unique(arr), [0, 1])
        if len(bad_vals):
            FAILURES.append(
                f"E0.masks: {name} has values outside {{0,1}}: {bad_vals} at NL/{eval_year}"
            )
            ok = False

    # obs_mask must be <= struct_mask (can't observe a structurally absent sector)
    if np.any(obs > struct):
        FAILURES.append(f"E0.masks: obs_mask > struct_mask at NL/{eval_year}")
        ok = False

    n_targets = int(tm.sum())
    log(f"masks check OK: NL/{eval_year} target_mask sum={n_targets}")
    return ok


# ---------------------------------------------------------------------------
# Check 4: NaN / Inf audit
# ---------------------------------------------------------------------------

def check_nan_inf(fold: dict, eval_year: int) -> bool:
    ok = True

    obs = fold["obs_mask"].astype(bool)
    feat = fold["features"]
    for c in range(feat.shape[2]):
        if np.any(~np.isfinite(feat[:, :, c][obs])):
            FAILURES.append(
                f"E0.nancheck: NaN/Inf in feature[{c}] where obs_mask=1 at NL/{eval_year}"
            )
            ok = False

    tm = fold["target_mask"].astype(bool)
    if np.any(~np.isfinite(fold["y_true"][tm])):
        FAILURES.append(f"E0.nancheck: NaN/Inf in y_true where target_mask=1 at NL/{eval_year}")
        ok = False

    if ok:
        log(f"NaN/Inf check OK: NL/{eval_year}")
    return ok


# ---------------------------------------------------------------------------
# Check 5: Ridge alignment and dummy model pass
# ---------------------------------------------------------------------------

def dummy_persistence(fold: dict) -> np.ndarray:
    """Minimal dummy model: predict y_true using Ridge prediction (already causal).

    This is the equal-capacity no-graph control: use the AR-Ridge prediction
    directly as the dummy output.  No graph information is used.
    """
    return fold["y_ridge"].copy()


def wmape(y_true: np.ndarray, y_pred: np.ndarray, mask: np.ndarray) -> float:
    mask = mask.astype(bool)
    if not mask.any():
        return np.nan
    yt = y_true[mask]
    yp = y_pred[mask]
    denom = np.sum(np.abs(yt))
    if denom < 1e-9:
        return np.nan
    return float(np.sum(np.abs(yt - yp)) / denom)


def check_ridge_alignment(fold: dict, eval_year: int) -> bool:
    ok = True
    tm = fold["target_mask"]
    yt = fold["y_true"]
    yr = fold["y_ridge"]

    n_target = int(tm.sum())
    if n_target == 0:
        FAILURES.append(f"E0.ridge: no observed targets at NL/{eval_year}")
        return False

    residual_stored = fold["residual"]
    residual_computed = np.where(tm.astype(bool), yt - yr, np.nan)
    diff = np.nanmax(np.abs(residual_stored - residual_computed))
    if diff > 1e-8:
        FAILURES.append(
            f"E0.ridge: residual mismatch (max diff={diff:.2e}) at NL/{eval_year}"
        )
        ok = False

    yp_dummy = dummy_persistence(fold)
    wm = wmape(yt, yp_dummy, tm)
    log(f"dummy model (no-graph Ridge): NL/{eval_year} WMAPE={wm:.4f} n_regions={n_target}")

    if ok:
        log(f"Ridge alignment check OK: NL/{eval_year} n_observed={n_target}")
    return ok


# ---------------------------------------------------------------------------
# Check 6: Determinism
# ---------------------------------------------------------------------------

def array_hash(arr: np.ndarray) -> str:
    return hashlib.md5(np.ascontiguousarray(arr)).hexdigest()


def check_determinism(eval_years: list[int]) -> bool:
    """Re-export tensors with the same parameters; compare checksums."""
    log("determinism check: re-exporting with same parameters...")
    tmp_dir = DEFAULT_OUT.parent / "graph_temporal_preflight_det_check"
    export_preflight(
        countries=["NL"],
        eval_years_by_country={"NL": eval_years},
        sector_panel_path=DEFAULT_SECTOR_PANEL,
        panel_dir=DEFAULT_PANEL_DIR,
        out_dir=tmp_dir,
    )

    ok = True
    for ey in eval_years:
        fold1 = load_fold(COUNTRY, ey, DEFAULT_OUT)
        fold2 = load_fold(COUNTRY, ey, tmp_dir)
        for key in ["features", "adj", "obs_mask", "struct_mask",
                    "y_true", "y_ridge", "residual", "target_mask"]:
            h1 = array_hash(fold1[key])
            h2 = array_hash(fold2[key])
            if h1 != h2:
                FAILURES.append(
                    f"E0.determinism: array {key!r} differs across runs for NL/{ey}"
                )
                ok = False

    if ok:
        log("determinism check OK: identical outputs across two export runs")

    # Clean up temp dir
    import shutil
    shutil.rmtree(tmp_dir, ignore_errors=True)
    return ok


# ---------------------------------------------------------------------------
# Main smoke
# ---------------------------------------------------------------------------

def run_smoke(eval_years: list[int], seed: int, rebuild: bool) -> bool:
    log(f"E0 smoke starting: NL, eval_years={eval_years}, seed={seed}")
    tracemalloc.start()
    t0 = time.perf_counter()

    # Build tensors (or reload existing)
    if rebuild or not (DEFAULT_OUT / COUNTRY / str(eval_years[0]) / "manifest.json").exists():
        log("Building preflight tensors for NL...")
        export_preflight(
            countries=["NL"],
            eval_years_by_country={"NL": eval_years},
            sector_panel_path=DEFAULT_SECTOR_PANEL,
            panel_dir=DEFAULT_PANEL_DIR,
            out_dir=DEFAULT_OUT,
        )

    # Load manifest
    manifest = load_manifest(DEFAULT_OUT)
    nl_folds = [f for f in manifest["folds"] if f["country"] == "NL"]
    sectors = nl_folds[0]["sectors"] if nl_folds else []
    log(f"Loaded manifest: {len(nl_folds)} NL folds, sectors={sectors}")

    all_ok = True

    # Run all checks per fold
    for eval_year in eval_years:
        fold = load_fold(COUNTRY, eval_year, DEFAULT_OUT)
        log(f"\n--- NL/{eval_year} ---")
        log(f"  features shape: {fold['features'].shape}")
        log(f"  adjacency shape: {fold['adj'].shape}")
        log(f"  obs_mask: {fold['obs_mask'].sum()} observed (region,sector) pairs")
        log(f"  target_mask: {fold['target_mask'].sum()} observed regions")

        ok1 = check_causal_ordering(fold, eval_year)
        ok2 = check_adjacency(fold, eval_year, sectors)
        ok3 = check_masks(fold, eval_year)
        ok4 = check_nan_inf(fold, eval_year)
        ok5 = check_ridge_alignment(fold, eval_year)

        all_ok = all_ok and ok1 and ok2 and ok3 and ok4 and ok5

    # Determinism check (re-export and compare)
    ok6 = check_determinism(eval_years)
    all_ok = all_ok and ok6

    elapsed = time.perf_counter() - t0
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    peak_gb = peak / 1024 ** 3

    log(f"\nRuntime: {elapsed:.2f}s (limit: {RUNTIME_LIMIT_S}s)")
    log(f"Peak memory: {peak_gb:.3f} GB (limit: {MEMORY_LIMIT_GB} GB)")

    if elapsed > RUNTIME_LIMIT_S:
        FAILURES.append(f"E0.runtime: {elapsed:.1f}s exceeds limit {RUNTIME_LIMIT_S}s")
        all_ok = False
    if peak_gb > MEMORY_LIMIT_GB:
        FAILURES.append(f"E0.memory: {peak_gb:.3f} GB exceeds limit {MEMORY_LIMIT_GB} GB")
        all_ok = False

    # Decision
    if all_ok:
        decision = "E0_PASS"
        log(f"\n{'='*60}")
        log(f"DECISION: {decision}", severity="PASS")
        log(f"{'='*60}")
        log("FR scientific local test is AUTHORIZED to proceed.")
    else:
        decision = "E0_FAIL"
        log(f"\n{'='*60}")
        log(f"DECISION: {decision}", severity="FAIL")
        log(f"{'='*60}")
        log("Failures:")
        for f in FAILURES:
            log(f"  {f}", severity="FAIL")
        log("FR scientific test is NOT authorized until failures are resolved.")

    return all_ok


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="E0 Engineering Smoke: NL")
    p.add_argument("--eval-years", nargs="+", type=int, default=DEFAULT_EVAL_YEARS)
    p.add_argument("--seed", type=int, default=DEFAULT_SEED)
    p.add_argument("--rebuild", action="store_true", help="Force rebuild of tensors")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    success = run_smoke(args.eval_years, args.seed, args.rebuild)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
