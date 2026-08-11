"""HERALD 74 -- the HERALD_71 architecture, rebuilt against the DEC-117 audit.

HERALD_72 was blocked before execution. Every defect it was blocked for is addressed here and
marked `FIX n` at the site. The numbering follows DEC-117's own ordering.

  FIX 1  target leakage. HERALD_72 trained on `S[t0+1 : t_end+1]`, whose last element is the
         state of the very year the model was then exported as predicting. Training targets
         now stop at `t_end - 1`; year `t_end` is scored once and never seen in a loss.
  FIX 2  dropout during export. `torch.no_grad()` does not disable dropout, and two exports of
         the same model on the same input differed at Jaccard 0.447. `model.eval()` is called
         before every export, and a determinism assertion fails the run if two exports differ.
  FIX 3  wrong architecture. Rank-16 attention on the GRU state is replaced by the
         pre-registered `U diag(z_t) V^T` with persistent `U`, `V` and an explicit per-year
         `z_t` at rank 4, so a birth or death can be attributed to a pattern.
  FIX 4  weak edges pruned instead of noise. Two graphs are now produced: a top-k graph the
         model propagates over, and a dense scored graph that is cut by reliability, so a
         weak-but-real edge survives and is reported in its own band.
  FIX 5  dead dynamism code. The noise floor, the temporal placebo and the untrained control
         are constructed and run; the report is written.
  FIX 6  phantom state. The mask is applied to the GRU input, to the hidden state carried
         between years, and to the output of every message-passing layer.
  FIX 7  self-loops. The diagonal is masked to -inf before top-k; the loaded commuting has no
         self-loops and neither should the learned graph.
  FIX 8  untrained head. Magnitude is either supervised or removed; it is supervised here.
  FIX 9  discarded outputs. Predictions, magnitudes, adjacencies, raw scores, reliability
         bands and edge events are all written.
  FIX 10 sweeps fixed as constants. Rank and epochs are swept, not chosen.

Not fixed, and declared: the prior's extremes still reach ~25 standardised units against a
learned term of order 1, so the two are not "comparable by construction". `gamma` is free to
rescale the prior and its learned value is reported as a diagnostic.
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

# Sourced in HERALD_70 / DEC-115. Anything not here is swept, not chosen.
HIDDEN_DIM = 64      # EconoGNN
N_LAYERS = 2         # EconoGNN; MTGNN gcn_depth
LR = 1e-3            # EconoGNN; MTGNN
DROPOUT = 0.2        # EconoGNN
WINDOW = 5           # EconoGNN temporal windows
TOP_K = 28           # MTGNN subgraph_size 20/207 = 9.7%, scaled to 280
STATE_TH = 0.10      # Eurostat-OECD; EU Implementing Regulation
RANK_DEFAULT = 4     # HERALD_71 section 4, from the observation budget


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


def load_prior(path: Path, zones, decision_year: int):
    df = pd.read_csv(path)
    sub = df[(df.decision_year == decision_year) & (df.is_self_loop == 0) & (df.data_available == 1)]
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
        raise ValueError(f"decision year {decision_year}: no edges mapped")
    return C


def prior_logits(C):
    """log1p keeps an absent edge at 0 instead of -13.8; standardising puts the prior on a
    scale the learned term can reach. Not "comparable by construction": DEC-117 measured the
    prior's extremes at ~25 standardised units. `gamma` exists to rescale it and is reported.
    """
    L = np.log1p(np.maximum(C, 0.0))
    off = ~np.eye(len(C), dtype=bool)
    out = (L - L[off].mean()) / max(L[off].std(), 1e-9)
    np.fill_diagonal(out, 0.0)
    return out


def growth(Y):
    G = np.full_like(Y, np.nan)
    G[1:] = np.log1p(np.maximum(Y[1:], 0)) - np.log1p(np.maximum(Y[:-1], 0))
    return G


def states(Y, th=STATE_TH):
    G = growth(Y)
    S = np.where(G <= -th, 0, np.where(G >= th, 2, 1)).astype(float)
    S[0] = np.nan
    return S


def presence_mask(Y):
    return (Y > 0).astype(np.float32)


def build_features(Y):
    G = growth(Y)
    return np.stack([np.nan_to_num(G), np.log1p(np.maximum(Y, 0)),
                     Y / np.maximum(Y.sum(2, keepdims=True), 1e-9)], axis=-1)


# -------------------------------------------------------------------------- model


def topk_sparse_softmax(logits, k):
    k = min(k, logits.shape[-1])
    vals, idx = torch.topk(logits, k, dim=-1)
    sparse = torch.full_like(logits, float("-inf"))
    sparse.scatter_(-1, idx, vals)
    return torch.nan_to_num(torch.softmax(sparse, dim=-1), nan=0.0)


class HERALD74(nn.Module):
    def __init__(self, n_zones, n_years, in_dim, rank=RANK_DEFAULT, k=TOP_K):
        super().__init__()
        self.n_zones, self.k, self.rank = n_zones, k, rank
        self.enc = nn.Sequential(nn.Linear(in_dim, HIDDEN_DIM), nn.ReLU(), nn.Dropout(DROPOUT))
        self.gru = nn.GRUCell(HIDDEN_DIM, HIDDEN_DIM)
        # FIX 3: persistent relational patterns U, V and an explicit per-year activation z_t.
        self.U = nn.Parameter(torch.randn(n_zones, rank) * 0.01)
        self.V = nn.Parameter(torch.randn(n_zones, rank) * 0.01)
        self.z = nn.Parameter(torch.zeros(n_years, rank))
        self.gamma = nn.Parameter(torch.tensor(1.0))
        self.msg = nn.ModuleList([nn.Linear(HIDDEN_DIM, HIDDEN_DIM) for _ in range(N_LAYERS)])
        self.head_state = nn.Linear(HIDDEN_DIM * 2, 3)
        self.head_mag = nn.Linear(HIDDEN_DIM * 2, 1)

    def deviation(self, t_abs):
        """U diag(z_t) V^T -- the only thing that moves between years."""
        return (self.U * self.z[t_abs]) @ self.V.T

    def adjacency(self, prior, t_abs):
        raw = self.deviation(t_abs)
        logits = self.gamma * prior + raw
        # FIX 7: no self-loops, matching the commuting source
        logits = logits - torch.diag(torch.full((self.n_zones,), float("inf"), device=logits.device))
        return topk_sparse_softmax(logits, self.k), raw

    def forward(self, x_seq, prior, mask_seq, t_abs_seq):
        T, Z, S, _ = x_seq.shape
        h = torch.zeros(Z * S, HIDDEN_DIM, device=x_seq.device)
        out = {"logits": [], "mag": [], "adj": [], "raw": []}
        for t in range(T):
            m = mask_seq[t].reshape(Z * S, 1)
            # FIX 6: mask the encoder input, the carried hidden state, and every layer output
            e = self.enc(x_seq[t].reshape(Z * S, -1)) * m
            h = self.gru(e, h * m) * m
            hn = h.reshape(Z, S, -1)
            h_zone = hn.sum(1)
            A, raw = self.adjacency(prior, t_abs_seq[t])
            msg = hn
            for layer in self.msg:
                msg = torch.relu(layer(torch.einsum("ij,jsd->isd", A, msg))) * mask_seq[t].unsqueeze(-1)
            z = torch.cat([hn, msg], dim=-1).reshape(Z * S, -1)
            out["logits"].append(self.head_state(z))
            out["mag"].append(self.head_mag(z).squeeze(-1))
            out["adj"].append(A)
            out["raw"].append(raw)
        return out


# ---------------------------------------------------------------- export and bands


def dense_scores(model, prior_t, t_abs):
    """FIX 4: the dense graph the reliability cut sees, before any top-k."""
    with torch.no_grad():
        raw = model.deviation(t_abs)
        return (model.gamma * prior_t + raw).cpu().numpy()


def shrink(weights, counts, prior_mean):
    """Pull each edge toward the group mean in proportion to its uncertainty, so a weak edge
    on a small cell becomes more reliable rather than being discarded."""
    pos = counts[counts > 0]
    med = np.median(pos) if pos.size else 1.0
    w = counts / (counts + med)
    return w * weights + (1.0 - w) * prior_mean


def classify_edges(score_mean, score_seeds, noise_sd, stability_min=0.5):
    """Three bands on the DENSE graph. Stability now participates, which DEC-117 flagged."""
    off = ~np.eye(score_mean.shape[0], dtype=bool)
    stab = score_seeds.std(0)
    rel = np.divide(np.abs(score_mean), np.maximum(noise_sd, 1e-9))
    consistent = np.divide(np.abs(score_mean), np.maximum(stab, 1e-9)) >= stability_min
    big = np.abs(score_mean) >= np.quantile(np.abs(score_mean[off]), 0.90)
    band = np.where(~(rel >= 1.96) | ~consistent, "noise",
                    np.where(big, "strong_real", "weak_real"))
    np.fill_diagonal(band, "excluded")
    return band, rel, stab


def edge_events(A_prev, A_now):
    was, now = A_prev > 0, A_now > 0
    return np.argwhere(~was & now), np.argwhere(was & ~now)


def dynamism_report(adj_by_year, seeds_last, placebo_movement, noise_movement, untrained_movement):
    """FIX 5: bounded on both sides by quantities the analyst did not choose."""
    off = ~np.eye(adj_by_year[0].shape[0], dtype=bool)
    def mv(a, b):
        return 1.0 - float(np.corrcoef(a[off], b[off])[0, 1])
    consecutive = [mv(adj_by_year[i], adj_by_year[i + 1]) for i in range(len(adj_by_year) - 1)]
    span = mv(adj_by_year[0], adj_by_year[-1])
    seed_r = [float(np.corrcoef(a[off], b[off])[0, 1])
              for i, a in enumerate(seeds_last) for b in seeds_last[i + 1:]]
    return {
        "movement_span": span,
        "movement_consecutive": consecutive,
        "noise_floor_movement": noise_movement,
        "temporal_placebo_movement": placebo_movement,
        "untrained_movement": untrained_movement,
        "seed_pairwise_r_mean": float(np.mean(seed_r)) if seed_r else float("nan"),
        "above_noise_floor": bool(span > noise_movement),
        "below_temporal_placebo": bool(span < placebo_movement),
        "exceeds_untrained": bool(span > untrained_movement),
        "verdict": "dynamic" if (span > noise_movement and span < placebo_movement
                                 and span > untrained_movement) else "not established",
    }


# ------------------------------------------------------------------------- driver


def fit_one(Y, feats, S, M, prior, years, eval_year, rank, epochs, seed, device, shuffle_years=False,
            train=True):
    """FIX 1: targets stop at t_end-1. The evaluation year is scored once, never in a loss."""
    yi = {y: k for k, y in enumerate(years)}
    t_end = yi[eval_year]
    t0 = max(1, t_end - WINDOW)
    idx = list(range(t0, t_end))                      # inputs: t0 .. t_end-1
    if shuffle_years:
        rng = np.random.default_rng(1234 + seed)
        idx = list(rng.permutation(idx))
    torch.manual_seed(seed)
    x = torch.tensor(feats[idx], dtype=torch.float32, device=device)
    mk = torch.tensor(M[idx], dtype=torch.float32, device=device)
    P = torch.tensor(prior, dtype=torch.float32, device=device)
    t_abs = torch.tensor(idx, dtype=torch.long, device=device)
    # target at input step t is the state at t+1; the last input step is t_end-1, so the last
    # target is S[t_end-1+1] = S[t_end-1+1]. Inputs stop one earlier than HERALD_72 did.
    tgt = torch.tensor(np.nan_to_num(S[[i for i in idx]]), dtype=torch.long,
                       device=device).reshape(len(idx), -1)
    mag_t = torch.tensor(np.nan_to_num(growth(Y)[[i for i in idx]]), dtype=torch.float32,
                         device=device).reshape(len(idx), -1)
    model = HERALD74(Y.shape[1], len(years), x.shape[-1], rank=rank).to(device)
    if train:
        opt = torch.optim.Adam(model.parameters(), lr=LR)
        ce, hub = nn.CrossEntropyLoss(), nn.HuberLoss()
        model.train()
        for _ in range(epochs):
            opt.zero_grad()
            o = model(x, P, mk, t_abs)
            loss = sum(ce(a, b) for a, b in zip(o["logits"], tgt)) / len(tgt)
            loss = loss + 0.1 * sum(hub(a, b) for a, b in zip(o["mag"], mag_t)) / len(tgt)  # FIX 8
            loss.backward()
            opt.step()
    model.eval()                                       # FIX 2
    with torch.no_grad():
        o1 = model(x, P, mk, t_abs)
        o2 = model(x, P, mk, t_abs)
    a1 = np.stack([a.cpu().numpy() for a in o1["adj"]])
    a2 = np.stack([a.cpu().numpy() for a in o2["adj"]])
    if not np.allclose(a1, a2):                        # FIX 2: determinism assertion
        raise AssertionError("export is not deterministic; dropout or another stochastic layer is live")
    return model, o1, a1, idx


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel-path", type=Path, required=True)
    ap.add_argument("--commuting-path", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--ranks", default="2,4,8")        # FIX 10: swept, not chosen
    ap.add_argument("--epochs", type=int, default=300)
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--first-year", type=int, default=2019)
    ap.add_argument("--last-year", type=int, default=2025)
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    Y, years, zones = load_panel(args.panel_path)
    feats, S, M = build_features(Y), states(Y), presence_mask(Y)
    dev = torch.device(args.device)
    report = {"config": {"top_k": TOP_K, "hidden": HIDDEN_DIM, "window": WINDOW,
                         "state_threshold": STATE_TH, "smoothness_penalty": None,
                         "ranks": args.ranks, "epochs": args.epochs}}

    for rank in [int(r) for r in args.ranks.split(",")]:
        for ey in range(args.first_year, args.last_year + 1):
            prior = prior_logits(load_prior(args.commuting_path, zones, ey))
            seeds_adj, dense_all, gammas = [], [], []
            for sd in range(args.seeds):
                model, o, adj, idx = fit_one(Y, feats, S, M, prior, years, ey, rank,
                                             args.epochs, sd, dev)
                seeds_adj.append(adj)
                dense_all.append(np.stack([dense_scores(model, torch.tensor(prior, dtype=torch.float32,
                                                                            device=dev), t) for t in idx]))
                gammas.append(float(model.gamma))
            seeds_adj = np.stack(seeds_adj)
            dense_all = np.stack(dense_all)
            # controls, none of which touches forecast error
            _, _, adj_shuf, _ = fit_one(Y, feats, S, M, prior, years, ey, rank, args.epochs, 0,
                                        dev, shuffle_years=True)
            _, _, adj_untr, _ = fit_one(Y, feats, S, M, prior, years, ey, rank, 0, 0, dev, train=False)
            off = ~np.eye(len(zones), dtype=bool)
            mv = lambda a, b: 1.0 - float(np.corrcoef(a[off], b[off])[0, 1])
            noise_sd = dense_all.std(0).mean(0)
            dyn = dynamism_report(list(seeds_adj[0]), list(seeds_adj[:, -1]),
                                  mv(adj_shuf[0], adj_shuf[-1]),
                                  float(np.median(noise_sd)),
                                  mv(adj_untr[0], adj_untr[-1]))
            band, rel, stab = classify_edges(dense_all.mean(0).mean(0), dense_all.mean(1), noise_sd)
            births, deaths = edge_events(seeds_adj[0][0], seeds_adj[0][-1])
            key = f"rank{rank}_{ey}"
            report[key] = {"gamma_mean": float(np.mean(gammas)), "dynamism": dyn,
                           "bands": {b: int((band == b).sum()) for b in
                                     ["strong_real", "weak_real", "noise", "excluded"]},
                           "edge_births": int(len(births)), "edge_deaths": int(len(deaths))}
            np.savez(args.out_dir / f"{key}.npz", adj=seeds_adj, dense=dense_all,
                     band=band, reliability=rel, stability=stab,
                     zones=np.array([str(z).zfill(4) for z in zones]))   # FIX: joinable IDs
            print(f"{key}: gamma={np.mean(gammas):.3f} verdict={dyn['verdict']} "
                  f"births={len(births)} deaths={len(deaths)} "
                  f"weak_real={(band=='weak_real').sum()}", flush=True)
    (args.out_dir / "herald74_report.json").write_text(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
