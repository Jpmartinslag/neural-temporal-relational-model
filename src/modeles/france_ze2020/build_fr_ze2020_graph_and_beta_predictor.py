"""HERALD 68 (DEC-110): typed relational graph + beta predictor.

Implements the specification in
reports/canonical/HERALD_68_FR_ZE2020_RELATIONAL_GRAPH_AND_BETA_PREDICTOR.md.

Every control that DEC-107 and DEC-109 showed was missing is applied here:

  * the primary baseline is mean reversion (`-g[t-1]` rank-matched), not persistence;
  * a matched no-economics synthetic panel is a standing gate;
  * the random floor uses the current year's marginal, not the previous year's prior;
  * uncertainty is paired-by-year with a block bootstrap over the 7 origins, because the
    origins are the units and their folds overlap -- seeds are near-deterministic and were
    the wrong uncertainty in DEC-101..106;
  * the relational block is distance-weighted top-50 with neighbour affinity retained, and
    is tested against a matched random-neighbour placebo on the standing configuration.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.metrics import f1_score
from sklearn.utils.class_weight import compute_sample_weight

SECTORS = ["BE", "FZ", "GI", "JZ", "KZ", "LZ", "MN", "OQ", "RU"]
N_SEC = len(SECTORS)
W_TRAJ = 4          # trajectory window for analogy
K_NEIGH = 50        # DEC-109 E7: 50 distance-weighted beats the 10-mean encoding
STATE_TH = 0.05     # kept for continuity with DEC-100; sensitivity is DEC-105 9.2


# --------------------------------------------------------------------------- data


def load_panel(path: Path):
    df = pd.read_csv(path)
    years = sorted(df.target_year.unique())
    zones = sorted(df.ZE2020.unique())
    yi = {y: k for k, y in enumerate(years)}
    zi = {z: k for k, z in enumerate(zones)}
    Y = np.zeros((len(years), len(zones), N_SEC))
    for r in df.itertuples(index=False):
        Y[yi[r.target_year], zi[r.ZE2020]] = [getattr(r, s) for s in SECTORS]
    return Y, years, zones


def growth(Y):
    G = np.full_like(Y, np.nan)
    G[1:] = np.log1p(np.maximum(Y[1:], 0)) - np.log1p(np.maximum(Y[:-1], 0))
    return G


def states(G, th=STATE_TH):
    S = np.where(G <= -th, 0, np.where(G >= th, 2, 1)).astype(float)
    S[0] = np.nan
    return S


def synthetic_panel(Y, phi, rng):
    """No-economics null (DEC-109 E2): per-cell quadratic log-trend + overdispersed noise.

    Contains no sectors interacting, no relations and no shocks -- only trend and counting
    noise. A model that scores higher here than on the real panel has learned noise reversion.
    """
    T, NZ, NS = Y.shape
    t = np.arange(T, dtype=float)
    out = np.empty_like(Y)
    for i in range(NZ):
        for s in range(NS):
            y = np.log1p(np.maximum(Y[:, i, s], 0))
            lam = np.expm1(np.polyval(np.polyfit(t, y, 2), t)).clip(0.05, None)
            if phi <= 1.0:
                out[:, i, s] = rng.poisson(lam)
            else:  # negative binomial with mean lam and variance phi*lam
                r = lam / max(phi - 1.0, 1e-6)
                out[:, i, s] = rng.negative_binomial(r, r / (r + lam))
    return out.astype(float)


# ------------------------------------------------------------------ relational block


def neighbour_index(G, t, rng=None, placebo=False):
    """Top-K same-sector analogues by trajectory correlation, using years <= t-1 only.

    Returns (idx, wgt): neighbour indices and their affinity weights. With placebo=True the
    neighbours are drawn at random inside the same sector, preserving K, the sector
    constraint and the summary statistics -- only the identity of the analogue is destroyed.
    """
    NZ = G.shape[1]
    sec_of = np.repeat(np.arange(N_SEC), NZ)
    traj = np.concatenate([G[t - W_TRAJ:t, :, s].T for s in range(N_SEC)], axis=0)
    fin = np.isfinite(traj).all(1)
    Tz = np.zeros_like(traj)
    if fin.any():
        m = traj[fin].mean(1, keepdims=True)
        sd = np.maximum(traj[fin].std(1, keepdims=True), 1e-9)
        Tz[fin] = (traj[fin] - m) / sd
    C = Tz @ Tz.T / traj.shape[1]
    same = sec_of[:, None] == sec_of[None, :]
    np.fill_diagonal(same, False)
    C = np.where(same & fin[None, :], C, -np.inf)
    if placebo:
        idx = np.empty((len(C), K_NEIGH), dtype=int)
        for s in range(N_SEC):
            pool = np.where((sec_of == s) & fin)[0]
            rows = np.where(sec_of == s)[0]
            if len(pool) <= 1:
                idx[rows] = rows[0]
                continue
            idx[rows] = rng.choice(pool, size=(len(rows), K_NEIGH), replace=True)
    else:
        idx = np.argpartition(-C, K_NEIGH, axis=1)[:, :K_NEIGH]
    wgt = np.take_along_axis(C, idx, 1)
    wgt = np.where(np.isfinite(wgt), wgt, 0.0)
    wgt = np.clip(wgt, 0.0, None) + 1e-6          # distance weighting, non-negative
    wgt /= wgt.sum(1, keepdims=True)
    return idx, wgt


def features(Y, G, S, t, relational, rng=None, placebo=False):
    NZ = Y.shape[1]
    cat = lambda A: np.concatenate([A[:, s] for s in range(N_SEC)])
    X = [cat(G[t - 1]), cat(G[t - 2]),
         cat(np.log1p(np.maximum(Y[t - 1], 0))),
         cat(Y[t - 1] / np.maximum(Y[t - 1].sum(1, keepdims=True), 1e-9))]
    if relational:
        idx, wgt = neighbour_index(G, t, rng=rng, placebo=placebo)
        g1 = cat(G[t - 1])
        s1 = cat(S[t - 1])
        gn = np.nan_to_num(g1[idx])
        X += [(gn * wgt).sum(1),                                   # weighted neighbour growth
              np.sqrt((wgt * (gn - (gn * wgt).sum(1, keepdims=True)) ** 2).sum(1)),
              (np.nan_to_num(s1[idx] == 2) * wgt).sum(1),          # weighted share growing
              (np.nan_to_num(s1[idx] == 0) * wgt).sum(1),          # weighted share declining
              np.take_along_axis(np.where(np.isfinite(wgt), wgt, 0), np.zeros((len(idx), 1), int), 1).ravel()]
    return np.column_stack(X)


# ---------------------------------------------------------------------- baselines


def rank_match(score, prior):
    """Map a continuous score onto class labels matching a given class prior (DEC-109 E1)."""
    n = len(score)
    order = np.argsort(score)
    out = np.empty(n, dtype=float)
    lo = int(round(prior[0] * n))
    mid = int(round(prior[1] * n))
    out[order[:lo]] = 0
    out[order[lo:lo + mid]] = 1
    out[order[lo + mid:]] = 2
    return out


def block_bootstrap_ci(deltas, rng, reps=5000):
    """CI over the 7 origins, which are the units. Seeds are not (DEC-107.3)."""
    d = np.asarray(deltas, float)
    boot = [rng.choice(d, size=len(d), replace=True).mean() for _ in range(reps)]
    return float(d.mean()), float(np.quantile(boot, 0.025)), float(np.quantile(boot, 0.975))


# ------------------------------------------------------------------------- run


def evaluate(Y, years, eval_years, seeds, relational, placebo=False, rng_seed=0):
    """Returns per-year macro-F1 (task A) and per-year within-sector Spearman (task B)."""
    G, S = growth(Y), states(growth(Y))
    yi = {y: k for k, y in enumerate(years)}
    NZ = Y.shape[1]
    sec_of = np.repeat(np.arange(N_SEC), NZ)
    f1_y, rho_y = [], []
    for ey in eval_years:
        t = yi[ey]
        tr = list(range(W_TRAJ + 2, t))
        rng = np.random.default_rng(rng_seed + 1000 * t)
        Xtr = np.vstack([features(Y, G, S, k, relational, rng, placebo) for k in tr])
        ytr = np.concatenate([np.concatenate([S[k][:, s] for s in range(N_SEC)]) for k in tr])
        gtr = np.concatenate([np.concatenate([G[k][:, s] for s in range(N_SEC)]) for k in tr])
        Xte = features(Y, G, S, t, relational, rng, placebo)
        yte = np.concatenate([S[t][:, s] for s in range(N_SEC)])
        gte = np.concatenate([G[t][:, s] for s in range(N_SEC)])
        ok, okt = np.isfinite(ytr), np.isfinite(yte)
        f1s, rhos = [], []
        for sd in seeds:
            clf = HistGradientBoostingClassifier(max_iter=400, learning_rate=0.05,
                                                 max_depth=6, random_state=sd)
            clf.fit(np.nan_to_num(Xtr[ok]), ytr[ok],
                    sample_weight=compute_sample_weight("balanced", ytr[ok]))
            f1s.append(f1_score(yte[okt], clf.predict(np.nan_to_num(Xte[okt])), average="macro"))
            reg = HistGradientBoostingRegressor(max_iter=400, learning_rate=0.05,
                                                max_depth=6, random_state=sd)
            m = np.isfinite(gtr)
            reg.fit(np.nan_to_num(Xtr[m]), gtr[m])
            p = reg.predict(np.nan_to_num(Xte))
            rs = []
            for s in range(N_SEC):                       # task B: rank zones inside a sector
                sel = (sec_of == s) & np.isfinite(gte)
                if sel.sum() < 20:
                    continue
                a = pd.Series(p[sel]).rank().values
                b = pd.Series(gte[sel]).rank().values
                rs.append(np.corrcoef(a, b)[0, 1])
            rhos.append(float(np.mean(rs)))
        f1_y.append(float(np.mean(f1s)))
        rho_y.append(float(np.mean(rhos)))
    return np.array(f1_y), np.array(rho_y)


def baselines(Y, years, eval_years):
    G, S = growth(Y), states(growth(Y))
    yi = {y: k for k, y in enumerate(years)}
    NZ = Y.shape[1]
    sec_of = np.repeat(np.arange(N_SEC), NZ)
    mr_f1, mr_rho, rnd_f1 = [], [], []
    rng = np.random.default_rng(7)
    for ey in eval_years:
        t = yi[ey]
        # DEC-109 E1 used the TRAINING-SET class quantiles, which is the stronger form of this
        # baseline (0.3910 vs 0.3713 for the previous-year prior). The stronger one is used, so
        # the model is not flattered by a weak null.
        trs = np.concatenate([np.concatenate([S[k][:, s] for s in range(N_SEC)])
                              for k in range(W_TRAJ + 2, t)])
        trs = trs[np.isfinite(trs)]
        prior = np.bincount(trs.astype(int), minlength=3) / len(trs)
        g1 = np.concatenate([G[t - 1][:, s] for s in range(N_SEC)])
        yte = np.concatenate([S[t][:, s] for s in range(N_SEC)])
        gte = np.concatenate([G[t][:, s] for s in range(N_SEC)])
        okt = np.isfinite(yte) & np.isfinite(g1)
        mr_f1.append(f1_score(yte[okt], rank_match(-g1[okt], prior), average="macro"))
        rs = []
        for s in range(N_SEC):
            sel = (sec_of == s) & np.isfinite(gte) & np.isfinite(g1)
            if sel.sum() < 20:
                continue
            rs.append(np.corrcoef(pd.Series(-g1[sel]).rank().values,
                                  pd.Series(gte[sel]).rank().values)[0, 1])
        mr_rho.append(float(np.mean(rs)))
        cur = np.bincount(yte[okt].astype(int), minlength=3) / okt.sum()   # E3: current marginal
        rnd_f1.append(float(np.mean([f1_score(yte[okt], rng.choice(3, okt.sum(), p=cur),
                                              average="macro") for _ in range(20)])))
    return np.array(mr_f1), np.array(mr_rho), np.array(rnd_f1)


def export_graph(Y, years, zones, out_dir, decision_years):
    """G-D: the graph must exist as an artifact independent of any model result."""
    G = growth(Y)
    NZ = len(zones)
    nodes, edges = [], []
    for ey in decision_years:
        t = years.index(ey)
        for i, z in enumerate(zones):
            tot = Y[t - 1, i].sum()
            for s_i, s in enumerate(SECTORS):
                nodes.append({"decision_year": ey, "ZE2020": z, "sector": s,
                              "level_t_minus_1": Y[t - 1, i, s_i],
                              "share_t_minus_1": Y[t - 1, i, s_i] / max(tot, 1e-9),
                              "growth_t_minus_1": G[t - 1, i, s_i]})
        idx, wgt = neighbour_index(G, t)
        sec_of = np.repeat(np.arange(N_SEC), NZ)
        for n in range(0, len(idx), 7):                   # every 7th node keeps the file small
            for k in range(min(10, K_NEIGH)):
                j = idx[n, k]
                edges.append({"decision_year": ey, "family": "analogy",
                              "src_ZE2020": zones[n % NZ], "src_sector": SECTORS[sec_of[n]],
                              "dst_ZE2020": zones[j % NZ], "dst_sector": SECTORS[sec_of[j]],
                              "weight": float(wgt[n, k])})
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    pd.DataFrame(nodes).to_csv(Path(out_dir) / "graph_nodes.csv", index=False)
    pd.DataFrame(edges).to_csv(Path(out_dir) / "graph_edges_analogy.csv", index=False)
    return len(nodes), len(edges)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel-path", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--seeds", type=int, default=20)
    args = ap.parse_args()

    Y, years, zones = load_panel(args.panel_path)
    EV = [y for y in range(2019, 2026)]
    seeds = list(range(args.seeds))
    rng = np.random.default_rng(20260811)
    res = {}

    mr_f1, mr_rho, rnd_f1 = baselines(Y, years, EV)
    print(f"{'year':>6}{'meanRev_F1':>12}{'meanRev_rho':>13}{'random_F1':>11}")
    for i, y in enumerate(EV):
        print(f"{y:>6}{mr_f1[i]:>12.4f}{mr_rho[i]:>13.4f}{rnd_f1[i]:>11.4f}")
    print(f"{'MEAN':>6}{mr_f1.mean():>12.4f}{mr_rho.mean():>13.4f}{rnd_f1.mean():>11.4f}\n")

    base_f1, base_rho = evaluate(Y, years, EV, seeds, relational=False)
    rel_f1, rel_rho = evaluate(Y, years, EV, seeds, relational=True)
    pla_f1, pla_rho = evaluate(Y, years, EV, seeds, relational=True, placebo=True, rng_seed=99)

    print(f"{'year':>6}{'base_F1':>10}{'rel_F1':>9}{'plac_F1':>9}   {'base_rho':>9}{'rel_rho':>9}{'plac_rho':>9}")
    for i, y in enumerate(EV):
        print(f"{y:>6}{base_f1[i]:>10.4f}{rel_f1[i]:>9.4f}{pla_f1[i]:>9.4f}   "
              f"{base_rho[i]:>9.4f}{rel_rho[i]:>9.4f}{pla_rho[i]:>9.4f}")
    print(f"{'MEAN':>6}{base_f1.mean():>10.4f}{rel_f1.mean():>9.4f}{pla_f1.mean():>9.4f}   "
          f"{base_rho.mean():>9.4f}{rel_rho.mean():>9.4f}{pla_rho.mean():>9.4f}")

    print("\n=== gates, paired by year with a block bootstrap over the 7 origins ===")
    for name, d in [("G-A  model - meanRev (F1)", base_f1 - mr_f1),
                    ("G-A  model - meanRev (rho)", base_rho - mr_rho),
                    ("G-C  relational - placebo (F1)", rel_f1 - pla_f1),
                    ("G-C  relational - placebo (rho)", rel_rho - pla_rho),
                    ("     relational - base (F1)", rel_f1 - base_f1)]:
        m, lo, hi = block_bootstrap_ci(d, rng)
        flag = "PASS" if lo > 0 else ("FAIL" if hi < 0 else "inconclusive")
        print(f"  {name:34} {m:+.4f}  CI95 [{lo:+.4f}, {hi:+.4f}]  {flag}")
        res[name] = {"mean": m, "lo": lo, "hi": hi, "verdict": flag}

    print("\n=== G-B: no-economics synthetic null ===")
    for phi in (1.0, 2.5):
        Ys = synthetic_panel(Y, phi, np.random.default_rng(int(phi * 100)))
        sf1, srho = evaluate(Ys, years, EV, seeds[:5], relational=False)
        v = "FAIL (null scores higher)" if sf1.mean() > base_f1.mean() else "PASS"
        print(f"  phi={phi}: synthetic F1 {sf1.mean():.4f} vs real {base_f1.mean():.4f}  -> {v}")
        res[f"G-B_phi{phi}"] = {"synthetic": float(sf1.mean()), "real": float(base_f1.mean())}

    n_nodes, n_edges = export_graph(Y, years, zones, args.out_dir, EV)
    print(f"\n=== G-D: graph artifact ===\n  nodes {n_nodes}  analogy edges {n_edges}")
    res["graph"] = {"nodes": n_nodes, "analogy_edges": n_edges}
    res["series"] = {"mean_reversion_f1": mr_f1.tolist(), "base_f1": base_f1.tolist(),
                     "rel_f1": rel_f1.tolist(), "placebo_f1": pla_f1.tolist(),
                     "mean_reversion_rho": mr_rho.tolist(), "base_rho": base_rho.tolist(),
                     "rel_rho": rel_rho.tolist(), "placebo_rho": pla_rho.tolist(),
                     "random_f1": rnd_f1.tolist(), "years": EV}
    (args.out_dir / "herald68_results.json").write_text(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
