"""HERALD 64 -- deterministic estimation of the France ZE2020 relational layer.

Implements the definitions and gates of
reports/canonical/HERALD_64_FR_ZE2020_RELATION_DEFINITIONS.md (DEC-095), written before
this file existed.

No neural network, no seed, no optimiser. DEC-091 and DEC-094 measured that a learned
graph is not reproducible on this data (seed correlation 0.695 and 0.704); this estimator
is deterministic, so running it twice returns the same graph.

Families produced
  precedence_intra   sector s at t precedes sector r at t+1, same zone
  precedence_cross   sector s in zone i precedes sector r in zone j, weighted by commuting
  comovement         contemporaneous association, candidate only (HERALD_64 3.1)

Statistic (HERALD_64 section 4), pooled over the 280 zones so that each of the 81 sector
pairs is estimated from 280 observations rather than one:

    P_t[s, r] = partial correlation of g[i, s, t] with g[i, r, t+1] given g[i, r, t]

Conditioning on the target's own past is not optional: without it the statistic measures
autocorrelation and every pair looks connected.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

SECTORS = ["BE", "FZ", "GI", "JZ", "KZ", "LZ", "MN", "OQ", "RU"]
N_SEC = len(SECTORS)
SECTOR_LABELS = {
    "BE": "Industry",
    "FZ": "Construction",
    "GI": "Trade, transport, hospitality",
    "JZ": "Information and communication",
    "KZ": "Finance and insurance",
    "LZ": "Real estate",
    "MN": "Professional and administrative services",
    "OQ": "Public administration, education, health",
    "RU": "Other services",
}


# --------------------------------------------------------------------------- io


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_panel(path: Path):
    df = pd.read_csv(path)
    missing = [c for c in SECTORS + ["target_year", "ZE2020"] if c not in df.columns]
    if missing:
        raise ValueError(f"panel missing columns: {missing}")
    years = sorted(df.target_year.unique())
    zones = sorted(df.ZE2020.unique())
    yi = {y: k for k, y in enumerate(years)}
    zi = {z: k for k, z in enumerate(zones)}
    Y = np.full((len(years), len(zones), N_SEC), np.nan)
    for row in df.itertuples(index=False):
        Y[yi[row.target_year], zi[row.ZE2020]] = [getattr(row, s) for s in SECTORS]
    if np.isnan(Y).any():
        raise ValueError("panel has missing cells; HERALD_57/DEC-082 states there are none")
    return Y, years, zones


def growth(Y: np.ndarray) -> np.ndarray:
    """g[t] = log1p(y[t]) - log1p(y[t-1]); g[0] undefined.

    log1p rather than a ratio, for the reason recorded in HERALD_63 section 9 defect 1:
    the observed zero cell makes a ratio diverge.
    """
    G = np.full_like(Y, np.nan)
    G[1:] = np.log1p(np.maximum(Y[1:], 0.0)) - np.log1p(np.maximum(Y[:-1], 0.0))
    return G


def load_commuting(path: Path, zones, decision_year: int) -> np.ndarray:
    """Row-normalised cross-ZE commuting for one decision year (DEC-073, release-aware)."""
    df = pd.read_csv(path)
    sub = df[
        (df.decision_year == decision_year)
        & (df.is_self_loop == 0)
        & (df.data_available == 1)
    ]
    if sub.empty:
        raise ValueError(f"no strict ex-ante commuting for decision year {decision_year}")
    if sub.observation_year.nunique() != 1:
        raise ValueError(f"decision year {decision_year} maps to multiple snapshots")
    zi = {int(z): k for k, z in enumerate(zones)}
    C = np.zeros((len(zones), len(zones)))
    for a, b, w in zip(sub.source_ze2020, sub.target_ze2020, sub.edge_weight):
        ia, ib = zi.get(int(a)), zi.get(int(b))
        if ia is not None and ib is not None:
            C[ia, ib] = w
    if not C.any():
        raise ValueError(f"decision year {decision_year}: no edges mapped onto the zone index")
    rs = C.sum(axis=1, keepdims=True)
    return np.divide(C, rs, out=np.zeros_like(C), where=rs > 0)


# -------------------------------------------------------------------- statistic


def _resid(y: np.ndarray, x: np.ndarray) -> np.ndarray:
    """Residual of y after removing the linear part of x (with intercept)."""
    A = np.column_stack([np.ones(len(x)), x])
    beta, *_ = np.linalg.lstsq(A, y, rcond=None)
    return y - A @ beta


def partial_corr(a: np.ndarray, b: np.ndarray, ctrl: np.ndarray):
    """Partial correlation of a and b given ctrl. Returns (r, n)."""
    ok = np.isfinite(a) & np.isfinite(b) & np.isfinite(ctrl)
    if ok.sum() < 20:
        return np.nan, int(ok.sum())
    ra, rb = _resid(a[ok], ctrl[ok]), _resid(b[ok], ctrl[ok])
    sa, sb = ra.std(), rb.std()
    if sa < 1e-12 or sb < 1e-12:
        return np.nan, int(ok.sum())
    return float(np.corrcoef(ra, rb)[0, 1]), int(ok.sum())


def fisher_p(r: float, n: int, n_ctrl: int = 1) -> float:
    """Two-sided p-value via Fisher's z. dof reduced by the conditioning variables."""
    if not np.isfinite(r) or n - n_ctrl - 3 <= 0:
        return np.nan
    r = float(np.clip(r, -0.999999, 0.999999))
    z = np.arctanh(r) * np.sqrt(n - n_ctrl - 3)
    # survival of |Z| under the standard normal, without scipy
    from math import erfc, sqrt

    return float(erfc(abs(z) / sqrt(2.0)))


def benjamini_hochberg(pvals: np.ndarray, q: float):
    """Return a boolean mask of rejections at FDR q (HERALD_64 R4)."""
    p = np.asarray(pvals, dtype=float)
    ok = np.isfinite(p)
    out = np.zeros(p.shape, dtype=bool)
    if not ok.any():
        return out
    idx = np.where(ok)[0]
    order = idx[np.argsort(p[idx])]
    m = len(order)
    thresh = q * (np.arange(1, m + 1) / m)
    passing = p[order] <= thresh
    if passing.any():
        kmax = np.max(np.where(passing)[0])
        out[order[: kmax + 1]] = True
    return out


# ------------------------------------------------------------------- estimators


def estimate_intra(G: np.ndarray, t: int, zone_subset=None):
    """P[s, r] for the transition t -> t+1, within the same zone."""
    src, tgt, ctrl = G[t], G[t + 1], G[t]
    if zone_subset is not None:
        src, tgt, ctrl = src[zone_subset], tgt[zone_subset], ctrl[zone_subset]
    R = np.full((N_SEC, N_SEC), np.nan)
    P = np.full((N_SEC, N_SEC), np.nan)
    N = np.zeros((N_SEC, N_SEC), dtype=int)
    for s in range(N_SEC):
        for r in range(N_SEC):
            rr, n = partial_corr(src[:, s], tgt[:, r], ctrl[:, r])
            R[s, r], N[s, r] = rr, n
            P[s, r] = fisher_p(rr, n)
    return R, P, N


def estimate_cross(G: np.ndarray, C: np.ndarray, t: int, zone_subset=None):
    """P[s, r] across zones: sector s in the commuting-weighted neighbourhood of zone j.

    The source signal reaching zone j is the commuting-weighted average of sector s over
    all origins i != j, which keeps the estimate at the sector-pair level rather than
    creating one parameter per zone pair.
    """
    Cn = C.copy()
    np.fill_diagonal(Cn, 0.0)
    rs = Cn.sum(axis=1, keepdims=True)
    Cn = np.divide(Cn, rs, out=np.zeros_like(Cn), where=rs > 0)
    # neighbour[j, s] = sum_i Cn[j, i] * g[i, s, t]   (inflow-weighted average)
    src = Cn @ G[t]
    tgt, ctrl = G[t + 1], G[t]
    if zone_subset is not None:
        src, tgt, ctrl = src[zone_subset], tgt[zone_subset], ctrl[zone_subset]
    R = np.full((N_SEC, N_SEC), np.nan)
    P = np.full((N_SEC, N_SEC), np.nan)
    N = np.zeros((N_SEC, N_SEC), dtype=int)
    for s in range(N_SEC):
        for r in range(N_SEC):
            rr, n = partial_corr(src[:, s], tgt[:, r], ctrl[:, r])
            R[s, r], N[s, r] = rr, n
            P[s, r] = fisher_p(rr, n)
    return R, P, N


def estimate_comovement(G: np.ndarray, t: int, zone_subset=None):
    """Contemporaneous association at t, no lag, no conditioning. Candidate family."""
    g = G[t] if zone_subset is None else G[t][zone_subset]
    R = np.full((N_SEC, N_SEC), np.nan)
    P = np.full((N_SEC, N_SEC), np.nan)
    N = np.zeros((N_SEC, N_SEC), dtype=int)
    for s in range(N_SEC):
        for r in range(N_SEC):
            if s == r:
                continue
            ok = np.isfinite(g[:, s]) & np.isfinite(g[:, r])
            n = int(ok.sum())
            if n < 20 or g[ok, s].std() < 1e-12 or g[ok, r].std() < 1e-12:
                continue
            rr = float(np.corrcoef(g[ok, s], g[ok, r])[0, 1])
            R[s, r], N[s, r] = rr, n
            P[s, r] = fisher_p(rr, n, n_ctrl=0)
    return R, P, N


# ------------------------------------------------------------------------ gates


def shuffled_years(Y: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """R1 placebo: shuffle years independently within each zone-sector series.

    Every marginal is preserved exactly -- each cell keeps its own 14 values -- and only
    the temporal order, which is the thing precedence claims to read, is destroyed.
    """
    out = np.empty_like(Y)
    T, N, S = Y.shape
    for i in range(N):
        for s in range(S):
            out[:, i, s] = Y[rng.permutation(T), i, s]
    return out


def run_family(name, fn, G, years, transitions, q, C_by_year=None):
    """Estimate one family across all transitions, returning per-year matrices and rows."""
    mats, rows = {}, []
    for t in transitions:
        args = (G, C_by_year[years[t + 1]], t) if C_by_year else (G, t)
        R, P, N = fn(*args)
        mats[years[t + 1]] = R
        flat_p = P.ravel()
        rej = benjamini_hochberg(flat_p, q).reshape(P.shape)
        for s in range(N_SEC):
            for r in range(N_SEC):
                if not np.isfinite(R[s, r]):
                    continue
                rows.append(
                    {
                        "relation_family": name,
                        "decision_year": int(years[t + 1]),
                        "source_sector": SECTORS[s],
                        "target_sector": SECTORS[r],
                        "source_label": SECTOR_LABELS[SECTORS[s]],
                        "target_label": SECTOR_LABELS[SECTORS[r]],
                        "weight": round(float(R[s, r]), 6),
                        "p_value": round(float(P[s, r]), 8),
                        "n_zones": int(N[s, r]),
                        "bh_rejected": bool(rej[s, r]),
                    }
                )
    return mats, rows


def count_survivors(fn, G, years, transitions, q, C_by_year=None):
    """Number of BH-surviving pairs per transition -- the quantity R1 compares."""
    counts = {}
    for t in transitions:
        args = (G, C_by_year[years[t + 1]], t) if C_by_year else (G, t)
        _, P, _ = fn(*args)
        counts[years[t + 1]] = int(benjamini_hochberg(P.ravel(), q).sum())
    return counts


def stability(fn, G, years, transitions, zones_n, q, C_by_year=None, n_splits=10, seed=7):
    """R2: sign stability across 10 disjoint halves of the zones."""
    rng = np.random.default_rng(seed)
    signs = {}
    for split in range(n_splits):
        perm = rng.permutation(zones_n)
        half = perm[: zones_n // 2]
        for t in transitions:
            args = (G, C_by_year[years[t + 1]], t) if C_by_year else (G, t)
            R, _, _ = fn(*args, zone_subset=half)
            for s in range(N_SEC):
                for r in range(N_SEC):
                    if np.isfinite(R[s, r]):
                        signs.setdefault((years[t + 1], s, r), []).append(np.sign(R[s, r]))
    out = {}
    for key, vals in signs.items():
        v = np.array(vals)
        out[key] = float(max((v > 0).mean(), (v < 0).mean()))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel-path", type=Path, required=True)
    ap.add_argument("--commuting-path", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--fdr-q", type=float, default=0.10)
    ap.add_argument("--first-year", type=int, default=2019)
    ap.add_argument("--last-year", type=int, default=2025)
    ap.add_argument("--placebo-seed", type=int, default=20260810)
    args = ap.parse_args()

    Y, years, zones = load_panel(args.panel_path)
    G = growth(Y)
    yi = {y: k for k, y in enumerate(years)}
    # transition t -> t+1 is labelled by its target year, which must be in the window
    transitions = [yi[y] - 1 for y in range(args.first_year, args.last_year + 1)]
    C_by_year = {
        y: load_commuting(args.commuting_path, zones, y)
        for y in range(args.first_year, args.last_year + 1)
    }

    args.out_dir.mkdir(parents=True, exist_ok=True)
    families = {
        "precedence_intra": (estimate_intra, None),
        "precedence_cross": (estimate_cross, C_by_year),
        "comovement": (estimate_comovement, None),
    }

    all_rows, report = [], {}
    rng = np.random.default_rng(args.placebo_seed)
    Y_placebo = shuffled_years(Y, rng)
    G_placebo = growth(Y_placebo)

    for name, (fn, C) in families.items():
        mats, rows = run_family(name, fn, G, years, transitions, args.fdr_q, C)
        all_rows.extend(rows)

        real = count_survivors(fn, G, years, transitions, args.fdr_q, C)
        fake = count_survivors(fn, G_placebo, years, transitions, args.fdr_q, C)
        wins = sum(1 for y in real if real[y] > fake[y])
        r1 = wins >= 5

        st = stability(fn, G, years, transitions, len(zones), args.fdr_q, C)
        surviving = {(r["decision_year"], r["source_sector"], r["target_sector"])
                     for r in rows if r["bh_rejected"]}
        stable = 0
        for r in rows:
            if not r["bh_rejected"]:
                continue
            key = (r["decision_year"], SECTORS.index(r["source_sector"]),
                   SECTORS.index(r["target_sector"]))
            frac = st.get(key, 0.0)
            r["sign_stability"] = round(frac, 3)
            r["r2_stable"] = bool(frac >= 0.8)
            stable += int(frac >= 0.8)

        stab_vals = sorted(round(v, 3) for v in st.values())
        report[name] = {
            "survivors_real_by_year": {str(int(k)): int(v) for k, v in real.items()},
            "survivors_placebo_by_year": {str(int(k)): int(v) for k, v in fake.items()},
            "sign_stability_all_pairs": {
                "min": stab_vals[0],
                "median": stab_vals[len(stab_vals) // 2],
                "share_below_0.8": round(sum(1 for v in stab_vals if v < 0.8) / len(stab_vals), 3),
                "n_pairs": len(stab_vals),
            },
            "years_real_beats_placebo": wins,
            "R1_pass": bool(r1),
            "bh_surviving_edges": len(surviving),
            "R2_stable_edges": stable,
            "R2_pass": bool(surviving and stable / max(len(surviving), 1) >= 0.5),
        }
        np.savez(args.out_dir / f"{name}_matrices.npz",
                 sectors=np.array(SECTORS), **{str(k): v for k, v in mats.items()})
        print(f"[{name}] R1 real vs placebo survivors, {wins}/7 years -> "
              f"{'PASS' if r1 else 'FAIL'} | BH edges {len(surviving)} | R2 stable {stable}",
              flush=True)

    df = pd.DataFrame(all_rows)
    df.to_csv(args.out_dir / "fr_ze2020_relation_estimates_v1.csv", index=False)
    report["inputs"] = {
        "panel": {"path": str(args.panel_path), "sha256": sha256(args.panel_path)},
        "commuting": {"path": str(args.commuting_path), "sha256": sha256(args.commuting_path)},
    }
    report["protocol"] = {
        "spec": "HERALD_64 / DEC-095",
        "fdr_q": args.fdr_q,
        "window": [args.first_year, args.last_year],
        "n_tests": int(len(all_rows)),
        "deterministic": True,
        "placebo_seed": args.placebo_seed,
        "claim_status": "conditional_temporal_association_not_causal",
    }
    (args.out_dir / "fr_ze2020_relation_estimation_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False)
    )
    print(json.dumps({k: v for k, v in report.items() if k in families}, indent=2))


if __name__ == "__main__":
    main()
