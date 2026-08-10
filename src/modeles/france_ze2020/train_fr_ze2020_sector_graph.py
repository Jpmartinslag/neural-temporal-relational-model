"""HERALD 63 -- learned sector-affinity graph over a fixed commuting prior.

Implements the specification in reports/canonical/HERALD_63_FR_ZE2020_SECTOR_GRAPH_SPEC.md
(DEC-093), written before this file existed.

Grain: ZE2020 x A10 x year.  Target: r = log1p(y_t) - log1p(y_{t-1}), so persistence is
exactly r = 0.  Graph: A[(i,s)->(j,q)] = C_t[i,j] * S_t[s,q], with C_t fixed official
commuting (release-aware) and S_t a 9x9 matrix learned per year.

Causal integrity, enforced structurally rather than by assertion:
  * every feature reads only years <= t-1 (build_features);
  * training for evaluation year t uses target years <= t-1 (rolling_origin);
  * S_t for the evaluation year is never trained; the model is served S_{t-1} (spec 3.5).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn

SECTORS = ["BE", "FZ", "GI", "JZ", "KZ", "LZ", "MN", "OQ", "RU"]
N_SEC = len(SECTORS)
FEATURES = ["lag1", "lag2", "lag3", "g1", "g2", "share_lag1", "log_lag1", "log_total_lag1"]


# --------------------------------------------------------------------------- data


def load_panel(path: Path):
    """Return Y (T, N, S), years, zones."""
    df = pd.read_csv(path)
    missing = [c for c in SECTORS + ["target_year", "ZE2020"] if c not in df.columns]
    if missing:
        raise ValueError(f"panel missing columns: {missing}")
    years = sorted(df.target_year.unique())
    zones = sorted(df.ZE2020.unique())
    zi = {z: k for k, z in enumerate(zones)}
    yi = {y: k for k, y in enumerate(years)}
    Y = np.full((len(years), len(zones), N_SEC), np.nan, dtype=np.float64)
    for row in df.itertuples(index=False):
        Y[yi[row.target_year], zi[row.ZE2020]] = [getattr(row, s) for s in SECTORS]
    if np.isnan(Y).any():
        raise ValueError(f"panel has {int(np.isnan(Y).sum())} missing cells; spec assumes none")
    return Y, years, zones


def build_features(Y: np.ndarray):
    """X (T, N, S, F) using only years <= t-1.  Rows with t < 3 are left as NaN."""
    T, N, S = Y.shape
    X = np.full((T, N, S, len(FEATURES)), np.nan, dtype=np.float64)
    eps = 1e-9
    for t in range(3, T):
        lag1, lag2, lag3 = Y[t - 1], Y[t - 2], Y[t - 3]
        total1 = lag1.sum(axis=1, keepdims=True)
        # Growth as a log1p difference, not a ratio. A ratio divides by the observed zero
        # that HERALD_57/DEC-082 recorded (5218/2016/JZ), producing ~4e9 and a standard
        # deviation of ~4e7 that annihilates every other feature under standardisation.
        # The log1p form is finite at zero and lives on the same scale as the target.
        feats = np.stack(
            [
                lag1,
                lag2,
                lag3,
                np.log1p(np.maximum(lag1, 0.0)) - np.log1p(np.maximum(lag2, 0.0)),
                np.log1p(np.maximum(lag2, 0.0)) - np.log1p(np.maximum(lag3, 0.0)),
                lag1 / np.maximum(total1, eps),
                np.log1p(np.maximum(lag1, 0.0)),
                np.broadcast_to(np.log1p(np.maximum(total1, 0.0)), lag1.shape),
            ],
            axis=-1,
        )
        X[t] = feats
    return X


def build_target(Y: np.ndarray):
    """r = log1p(y_t) - log1p(y_{t-1}); persistence is r = 0."""
    T = Y.shape[0]
    R = np.full_like(Y, np.nan)
    for t in range(1, T):
        R[t] = np.log1p(np.maximum(Y[t], 0.0)) - np.log1p(np.maximum(Y[t - 1], 0.0))
    return R


def apply_sector_placebo(Y: np.ndarray, seed: int):
    """Permute sector labels per zone, held fixed across all years.

    Deliberately NOT permuted per year: that would scramble each cell's own history, so the
    placebo would face a strictly harder target and beating it would prove nothing. Holding
    the permutation fixed in time leaves every sector time series and every zone-year total
    exactly intact -- persistence scores identically -- and destroys only the correspondence
    between a sector's identity and its slot *across zones*, which is the single thing a
    zone-shared S_t can exploit.
    """
    rng = np.random.default_rng(seed)
    out = np.empty_like(Y)
    for i in range(Y.shape[1]):
        perm = rng.permutation(N_SEC)
        out[:, i, :] = Y[:, i, perm]
    return out


def load_commuting(path: Path, zones, decision_years):
    """C_cross[dy] (N, N) row-normalised, release-aware per decision year."""
    df = pd.read_csv(path)
    zi = {int(z): k for k, z in enumerate(zones)}
    N = len(zones)
    out = {}
    for dy in decision_years:
        sub = df[(df.decision_year == dy) & (df.is_self_loop == 0) & (df.data_available == 1)]
        if sub.empty:
            raise ValueError(f"no strict ex-ante commuting for decision year {dy}")
        if sub.observation_year.nunique() != 1:
            raise ValueError(f"decision year {dy} maps to multiple snapshots")
        C = np.zeros((N, N))
        hit = 0
        for a, b, w in zip(sub.source_ze2020, sub.target_ze2020, sub.edge_weight):
            ia, ib = zi.get(int(a)), zi.get(int(b))
            if ia is not None and ib is not None:
                C[ia, ib] = w
                hit += 1
        if hit == 0:
            raise ValueError(f"decision year {dy}: no edges mapped onto the zone index")
        rs = C.sum(axis=1, keepdims=True)
        C = np.divide(C, rs, out=np.zeros_like(C), where=rs > 0)
        out[dy] = C
    return out


# -------------------------------------------------------------------------- model


class SectorGraphModel(nn.Module):
    def __init__(self, n_features, n_years, hidden=64, use_graph=True):
        super().__init__()
        self.use_graph = use_graph
        self.enc = nn.Sequential(
            nn.Linear(n_features, hidden), nn.ReLU(), nn.Linear(hidden, hidden), nn.ReLU()
        )
        head_in = hidden * 2 if use_graph else hidden
        self.head = nn.Sequential(nn.Linear(head_in, hidden), nn.ReLU(), nn.Linear(hidden, 1))
        # S_t logits, one 9x9 per year; zero init = uniform affinity. No temporal penalty.
        self.S_logits = nn.Parameter(torch.zeros(n_years, N_SEC, N_SEC))
        # within-zone vs cross-zone mixing, learned rather than assumed
        self.self_mix = nn.Parameter(torch.tensor(0.0))

    def sector_affinity(self, t_idx):
        return torch.softmax(self.S_logits[t_idx], dim=-1)

    def forward(self, x, C, t_idx, s_override=None):
        """x (N, S, F); C (N, N); returns r_hat (N, S)."""
        e = self.enc(x)
        if not self.use_graph:
            return self.head(e).squeeze(-1)
        S = self.sector_affinity(t_idx) if s_override is None else s_override
        a = torch.sigmoid(self.self_mix)
        # C_eff = a*I + (1-a)*C_cross, applied without materialising the identity
        z_cross = torch.einsum("ij,jqd->iqd", C, e)
        z = a * e + (1.0 - a) * z_cross
        m = torch.einsum("sq,iqd->isd", S, z)
        return self.head(torch.cat([e, m], dim=-1)).squeeze(-1)


# ------------------------------------------------------------------------ metrics


def wmape(y_true, y_pred):
    denom = np.abs(y_true).sum()
    if denom <= 0:
        return float("nan")
    return float(np.abs(y_true - y_pred).sum() / denom)


def ndcg_at_k(y_true, y_pred, k=3):
    """Mean NDCG@k over zones, ranking sectors by predicted growth."""
    scores = []
    for i in range(y_true.shape[0]):
        order = np.argsort(-y_pred[i])[:k]
        gains = np.maximum(y_true[i][order], 0.0)
        disc = 1.0 / np.log2(np.arange(2, len(order) + 2))
        dcg = float((gains * disc).sum())
        best = np.sort(np.maximum(y_true[i], 0.0))[::-1][:k]
        idcg = float((best * disc[: len(best)]).sum())
        if idcg > 0:
            scores.append(dcg / idcg)
    return float(np.mean(scores)) if scores else float("nan")


def precision_at_k(y_true, y_pred, k=3):
    hits = []
    for i in range(y_true.shape[0]):
        top_p = set(np.argsort(-y_pred[i])[:k].tolist())
        top_t = set(np.argsort(-y_true[i])[:k].tolist())
        hits.append(len(top_p & top_t) / k)
    return float(np.mean(hits))


# ------------------------------------------------------------------------ fitting


def ridge_baseline(Xtr, Rtr, Xte, alpha=1.0):
    """Closed-form ridge on the same causal features, standardised."""
    mu, sd = Xtr.mean(0), Xtr.std(0)
    sd = np.where(sd > 1e-9, sd, 1.0)
    A = np.column_stack([np.ones(len(Xtr)), (Xtr - mu) / sd])
    B = np.column_stack([np.ones(len(Xte)), (Xte - mu) / sd])
    P = A.T @ A + alpha * np.eye(A.shape[1])
    P[0, 0] -= alpha
    beta = np.linalg.solve(P, A.T @ Rtr)
    return B @ beta


def run_fold(Y, X, R, C_by_dy, years, eval_year, args, device):
    """Train on target years <= eval_year-1, score eval_year."""
    yi = {y: k for k, y in enumerate(years)}
    te = yi[eval_year]
    train_idx = [yi[y] for y in years if 3 <= yi[y] and y <= eval_year - 1]
    if not train_idx:
        raise ValueError(f"no training years for eval year {eval_year}")

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)

    model = SectorGraphModel(len(FEATURES), len(years), args.hidden, args.arm != "no_graph")
    model.to(device)
    opt = torch.optim.Adam(model.parameters(), lr=args.lr)
    huber = nn.HuberLoss(delta=1.0)

    # standardise features on training years only
    flat = X[train_idx].reshape(-1, len(FEATURES))
    mu, sd = flat.mean(0), flat.std(0)
    sd = np.where(sd > 1e-9, sd, 1.0)

    def prep(t):
        return torch.tensor((X[t] - mu) / sd, dtype=torch.float32, device=device)

    xs = {t: prep(t) for t in train_idx + [te]}
    rs = {t: torch.tensor(R[t], dtype=torch.float32, device=device) for t in train_idx}
    # One commuting snapshot per fold: the one an analyst deciding in `eval_year` actually
    # holds. Using each training year's own later snapshot would feed the fold information
    # published after its decision date.
    C_fold = torch.tensor(C_by_dy[eval_year], dtype=torch.float32, device=device)
    cs = {t: C_fold for t in train_idx + [te]}

    # Early stopping on the last training year. The first fold trains on four years only,
    # and without this the graph path diverges (the exp() reconversion then amplifies it).
    # The validation year is inside the causal window, so this selects no test information.
    fit_idx, val_t = train_idx[:-1], train_idx[-1]
    if not fit_idx:  # too few years to hold one out; fit on everything
        fit_idx, val_t = train_idx, None
    serve_t = fit_idx[-1]  # S is served from the last *fitted* year, never a later one

    best = (float("inf"), None)
    for ep in range(args.epochs):
        model.train()
        opt.zero_grad()
        loss = 0.0
        for t in fit_idx:
            loss = loss + huber(model(xs[t], cs[t], t), rs[t])
        (loss / len(fit_idx)).backward()
        opt.step()
        if val_t is not None and (ep + 1) % args.val_every == 0:
            model.eval()
            with torch.no_grad():
                sv = model.sector_affinity(serve_t) if args.arm != "no_graph" else None
                pv = model(xs[val_t], cs[val_t], val_t, s_override=sv).cpu().numpy()
                lv = Y[val_t - 1]
                score = wmape(Y[val_t], np.maximum((lv + 1.0) * np.exp(np.clip(pv, -5, 5)) - 1.0, 0.0))
            if np.isfinite(score) and score < best[0]:
                best = (score, {k: v.detach().clone() for k, v in model.state_dict().items()})
    if best[1] is not None:
        model.load_state_dict(best[1])

    # serve with the last fitted year's affinity; the evaluation year's was never trained
    model.eval()
    with torch.no_grad():
        s_prev = model.sector_affinity(serve_t) if args.arm != "no_graph" else None
        r_hat = model(xs[te], cs[te], te, s_override=s_prev).cpu().numpy()
        r_unif = None
        if args.arm != "no_graph":
            unif = torch.full((N_SEC, N_SEC), 1.0 / N_SEC, device=device)
            r_unif = model(xs[te], cs[te], te, s_override=unif).cpu().numpy()
        S_learned = (
            model.sector_affinity(serve_t).cpu().numpy() if args.arm != "no_graph" else None
        )

    lag1 = Y[te - 1]
    y_true = Y[te]

    def to_level(r):
        return np.maximum((lag1 + 1.0) * np.exp(np.clip(r, -5, 5)) - 1.0, 0.0)

    out = {
        "eval_year": int(eval_year),
        "n_cells": int(y_true.size),
        "wmape_model": wmape(y_true, to_level(r_hat)),
        "wmape_persistence": wmape(y_true, lag1),
        "ndcg3_model": ndcg_at_k(y_true - lag1, r_hat),
        "ndcg3_persistence": ndcg_at_k(y_true - lag1, np.zeros_like(r_hat)),
        "precision3_model": precision_at_k(y_true - lag1, r_hat),
    }
    if r_unif is not None:
        out["wmape_uniform_S"] = wmape(y_true, to_level(r_unif))  # G5 artifact control

    Xtr = np.concatenate([X[t].reshape(-1, len(FEATURES)) for t in train_idx])
    Rtr = np.concatenate([R[t].reshape(-1) for t in train_idx])
    r_ridge = ridge_baseline(Xtr, Rtr, X[te].reshape(-1, len(FEATURES))).reshape(y_true.shape)
    out["wmape_ridge"] = wmape(y_true, to_level(r_ridge))
    out["ndcg3_ridge"] = ndcg_at_k(y_true - lag1, r_ridge)
    return out, S_learned


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--panel-path", type=Path, required=True)
    p.add_argument("--commuting-path", type=Path, required=True)
    p.add_argument("--arm", default="main", choices=["main", "placebo_sector", "no_graph"])
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--epochs", type=int, default=400)
    p.add_argument("--hidden", type=int, default=64)
    p.add_argument("--lr", type=float, default=0.01)
    p.add_argument("--val-every", type=int, default=10)
    p.add_argument("--eval-years", default="2019,2020,2021,2022,2023,2024,2025")
    p.add_argument("--out-dir", type=Path, required=True)
    p.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    args = p.parse_args()

    device = torch.device(args.device)
    Y, years, zones = load_panel(args.panel_path)
    if args.arm == "placebo_sector":
        # fixed permutation seeded independently of the model seed, so all seeds of the
        # placebo arm face the same destroyed structure
        Y = apply_sector_placebo(Y, seed=20260810)

    X = build_features(Y)
    R = build_target(Y)
    eval_years = [int(v) for v in args.eval_years.split(",")]
    C_by_dy = load_commuting(args.commuting_path, zones, sorted(set(eval_years)))

    args.out_dir.mkdir(parents=True, exist_ok=True)
    folds, mats = [], {}
    for ey in eval_years:
        res, S = run_fold(Y, X, R, C_by_dy, years, ey, args, device)
        folds.append(res)
        if S is not None:
            mats[str(ey)] = S
        print(f"[{args.arm} s{args.seed}] {ey} wmape={res['wmape_model']:.5f} "
              f"pers={res['wmape_persistence']:.5f} ridge={res['wmape_ridge']:.5f}", flush=True)

    summary = {
        "arm": args.arm,
        "seed": args.seed,
        "epochs": args.epochs,
        "folds": folds,
        "mean_wmape_model": float(np.mean([f["wmape_model"] for f in folds])),
        "mean_wmape_persistence": float(np.mean([f["wmape_persistence"] for f in folds])),
        "mean_wmape_ridge": float(np.mean([f["wmape_ridge"] for f in folds])),
        "mean_ndcg3_model": float(np.mean([f["ndcg3_model"] for f in folds])),
        "spec": "HERALD_63 / DEC-093",
    }
    if any("wmape_uniform_S" in f for f in folds):
        summary["mean_wmape_uniform_S"] = float(
            np.mean([f["wmape_uniform_S"] for f in folds if "wmape_uniform_S" in f])
        )
    (args.out_dir / "metrics.json").write_text(json.dumps(summary, indent=2))
    if mats:
        np.savez(args.out_dir / "sector_affinity.npz", sectors=np.array(SECTORS), **mats)
    print(json.dumps({k: v for k, v in summary.items() if k != "folds"}, indent=2))


if __name__ == "__main__":
    main()
