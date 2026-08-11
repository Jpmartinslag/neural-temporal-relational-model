"""HERALD 75 -- third attempt, written against tests/test_herald75_guards.py.

The previous two implementations carried correct intent in their comments and incorrect
behaviour in their code (DEC-117, DEC-118). The guards were written before this file and each
one maps to a defect that reached a commit. If a guard fails, this file is wrong.

Alignment, which is what DEC-118 got backwards:

    input step i  ->  features from year Y_i          (contains growth g[i])
    target step i ->  state  at year Y_{i+1}          (thresholds growth g[i+1])
    magnitude     ->  growth at year Y_{i+1}

    loss   : every step except the last
    score  : the last step, exactly once, never in any loss

Window, per the owner's instruction to widen training as far as the data allows:
expanding from the first year with defined growth, two years reserved for validation, one
year scored. At eval year 2025 that is nine training transitions and 9.9 observations per
graph parameter at rank 4, against the 4.39 of the fixed five-year window.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn

SECTORS = ["BE", "FZ", "GI", "JZ", "KZ", "LZ", "MN", "OQ", "RU"]
N_SEC = len(SECTORS)

HIDDEN_DIM = 64      # EconoGNN
N_LAYERS = 2         # EconoGNN; MTGNN gcn_depth
LR = 1e-3            # EconoGNN; MTGNN
DROPOUT = 0.2        # EconoGNN
TOP_K = 28           # MTGNN subgraph_size 20/207 scaled to 280
STATE_TH = 0.10      # Eurostat-OECD; EU Implementing Regulation
RANK_DEFAULT = 4     # HERALD_71 section 4
N_VAL_YEARS = 2      # owner's instruction


# ----------------------------------------------------------------- transforms


def growth(Y):
    G = np.full_like(Y, np.nan)
    G[1:] = np.log1p(np.maximum(Y[1:], 0)) - np.log1p(np.maximum(Y[:-1], 0))
    return G


def states_from_growth(g, th=STATE_TH):
    """Exposed so the leakage guard can attempt exactly the reconstruction that broke
    HERALD_74: threshold any candidate feature and compare it with the target."""
    return np.where(g <= -th, 0, np.where(g >= th, 2, 1)).astype(float)


def prior_logits(C):
    """log1p keeps an absent edge at 0; standardisation is over PRESENT edges only.

    DEC-118: standardising over everything put absent edges at a constant -0.127 that a later
    `abs()` read as signal. Absent edges are pinned to the minimum instead of acquiring a
    magnitude of their own.
    """
    L = np.log1p(np.maximum(C, 0.0))
    off = ~np.eye(len(C), dtype=bool)
    present = off & (C > 0)
    if present.any():
        mu, sd = L[present].mean(), max(L[present].std(), 1e-9)
        out = (L - mu) / sd
        out[~present] = out[present].min() if present.any() else 0.0
    else:
        out = np.zeros_like(L)
    np.fill_diagonal(out, 0.0)
    return out


def build_features(Y):
    """Features at index t describe year t and earlier. Never year t+1."""
    G = growth(Y)
    total = np.maximum(Y.sum(2, keepdims=True), 1e-9)
    return np.stack([np.nan_to_num(G),
                     np.log1p(np.maximum(Y, 0)),
                     Y / total], axis=-1)


def presence_mask(Y):
    return (Y > 0).astype(np.float32)


# ------------------------------------------------------------------ fold logic


def graph_parameters(n_zones, n_years, rank):
    return 2 * n_zones * rank + n_years * rank + 1


def assemble_fold(Y, eval_index, rank=RANK_DEFAULT, n_val=N_VAL_YEARS):
    """Returns (x, tgt, meta) with the alignment stated in the module docstring.

    Input steps run from the first year with defined growth up to `eval_index - 1`; the target
    of step i is the state of year i+1, so the final target is `eval_index` and it is scored,
    not trained on.
    """
    n_years, n_zones, _ = Y.shape
    feats, S, G = build_features(Y), states_from_growth(growth(Y)), growth(Y)
    S[0] = np.nan
    first = 1                                          # first index with defined growth
    steps = list(range(first, eval_index))             # inputs
    if len(steps) < n_val + 2:
        raise ValueError(f"eval_index {eval_index} leaves too few steps for {n_val} validation years")
    n_cells = n_zones * N_SEC
    x = feats[steps].reshape(len(steps), n_cells, -1)
    tgt = S[[i + 1 for i in steps]].reshape(len(steps), n_cells)
    mag = G[[i + 1 for i in steps]].reshape(len(steps), n_cells)
    target_years = [i + 1 for i in steps]
    scored = target_years[-1]
    val_years = target_years[-(n_val + 1):-1]
    train_years = target_years[:-(n_val + 1)]
    meta = {
        "input_steps": steps,
        "target_years": target_years,
        "train_target_years": train_years,
        "val_target_years": val_years,
        "scored_year": scored,
        "train_labels": len(train_years) * n_zones * N_SEC,
        "graph_parameters": graph_parameters(n_zones, n_years, rank),
        "mag": mag,
    }
    return x, tgt, meta


def fold_year_assignment(shuffle=False, seed=0, n_steps=9):
    """The temporal placebo permutes ONLY which `z` row each year uses.

    DEC-118: the previous placebo permuted the data and the `z` index together, so every
    observation kept its true regime and the control tested loop order alone.
    """
    years = list(range(1, n_steps + 1))
    if shuffle:
        z_index = list(np.random.default_rng(seed).permutation(years))
    else:
        z_index = list(years)
    return {"input_years": years, "z_index": z_index}


# ----------------------------------------------------------------------- model


def topk_sparse_softmax(logits, k):
    k = min(k, logits.shape[-1])
    vals, idx = torch.topk(logits, k, dim=-1)
    sparse = torch.full_like(logits, float("-inf"))
    sparse.scatter_(-1, idx, vals)
    return torch.nan_to_num(torch.softmax(sparse, dim=-1), nan=0.0)


class HERALD75(nn.Module):
    def __init__(self, n_zones, n_years, in_dim, rank=RANK_DEFAULT, k=TOP_K):
        super().__init__()
        self.n_zones, self.k, self.rank = n_zones, k, rank
        self.enc = nn.Sequential(nn.Linear(in_dim, HIDDEN_DIM), nn.ReLU(), nn.Dropout(DROPOUT))
        self.gru = nn.GRUCell(HIDDEN_DIM, HIDDEN_DIM)
        self.U = nn.Parameter(torch.randn(n_zones, rank) * 0.1)
        self.V = nn.Parameter(torch.randn(n_zones, rank) * 0.1)
        # z starts small but non-zero: at exactly zero, U and V receive no gradient at all
        # (DEC-118 measured 0.0), which is a cold start rather than a prior.
        self.z = nn.Parameter(torch.full((n_years, rank), 0.05))
        self.gamma = nn.Parameter(torch.tensor(1.0))
        self.msg = nn.ModuleList([nn.Linear(HIDDEN_DIM, HIDDEN_DIM) for _ in range(N_LAYERS)])
        self.head_state = nn.Linear(HIDDEN_DIM * 2, 3)
        self.head_mag = nn.Linear(HIDDEN_DIM * 2, 1)

    def deviation(self, z_row):
        return (self.U * self.z[z_row]) @ self.V.T

    def adjacency(self, prior, z_row):
        raw = self.deviation(z_row)
        logits = self.gamma * prior + raw
        logits = logits - torch.diag(torch.full((self.n_zones,), float("inf"), device=logits.device))
        return topk_sparse_softmax(logits, self.k), raw

    def forward(self, x_seq, prior, mask_seq, z_rows):
        T, Z, S, _ = x_seq.shape
        h = torch.zeros(Z * S, HIDDEN_DIM, device=x_seq.device)
        out = {"logits": [], "mag": [], "adj": [], "raw": [], "hidden": [], "msg": []}
        for t in range(T):
            m = mask_seq[t].reshape(Z * S, 1)
            e = self.enc(x_seq[t].reshape(Z * S, -1)) * m
            h = self.gru(e, h * m) * m
            hn = h.reshape(Z, S, -1)
            A, raw = self.adjacency(prior, z_rows[t])
            msg = hn
            for layer in self.msg:
                msg = torch.relu(layer(torch.einsum("ij,jsd->isd", A, msg))) * mask_seq[t].unsqueeze(-1)
            z = torch.cat([hn, msg], dim=-1).reshape(Z * S, -1)
            out["logits"].append(self.head_state(z))
            out["mag"].append(self.head_mag(z).squeeze(-1))
            out["adj"].append(A)
            out["raw"].append(raw)
            out["hidden"].append(hn)
            out["msg"].append(msg)
        return out


# --------------------------------------------------------- reliability and events


def shrink(weights, counts, prior_mean):
    pos = counts[counts > 0]
    med = np.median(pos) if pos.size else 1.0
    w = counts / (counts + med)
    return w * weights + (1.0 - w) * prior_mean


def classify_edges(dev_mean, dev_seeds, noise_sd, z_crit=1.96, stability_min=1.0):
    """Bands are assigned on the LEARNED DEVIATION, not on prior + deviation.

    DEC-118: classifying `gamma*prior + raw` and taking `abs()` made the absence of commuting
    look like evidence, and 5,852 zero-commuting edges were called `strong_real`. The observed
    prior is not inferred and needs no reliability band; only the learned part does.
    """
    off = ~np.eye(dev_mean.shape[0], dtype=bool)
    stab = dev_seeds.std(0)
    rel = np.abs(dev_mean) / np.maximum(noise_sd, 1e-12)
    consistent = np.abs(dev_mean) >= stability_min * np.maximum(stab, 1e-12)
    real = (rel >= z_crit) & consistent
    if real[off].any():
        cut = np.quantile(np.abs(dev_mean[off & real]), 0.90)
    else:
        cut = np.inf
    band = np.where(~real, "noise", np.where(np.abs(dev_mean) >= cut, "strong_real", "weak_real"))
    band = band.astype(object)
    np.fill_diagonal(band, "excluded")
    return band, rel, stab


def edge_events(A_prev, A_now):
    was, now = A_prev > 0, A_now > 0
    return np.argwhere(~was & now), np.argwhere(was & ~now)


def negative_binomial_floor(Y, prior, model_fn, phi=2.5, reps=8, seed=0):
    """Noise floor in the SAME unit as observed movement: 1 - corr(A_first, A_last).

    DEC-118: the previous floor was `median(noise_sd)` in logit units, compared against a
    dimensionless movement, and measured model instability rather than sampling noise.
    """
    rng = np.random.default_rng(seed)
    movements = []
    for _ in range(reps):
        lam = np.maximum(Y, 0.05)
        r = lam / max(phi - 1.0, 1e-6)
        Yr = rng.negative_binomial(r, r / (r + lam)).astype(float)
        adjs = model_fn(Yr)
        off = ~np.eye(adjs[0].shape[0], dtype=bool)
        movements.append(1.0 - float(np.corrcoef(adjs[0][off], adjs[-1][off])[0, 1]))
    return float(np.mean(movements))


# --------------------------------------------------------------- test-facing API


def _fit(Y, prior, eval_index, rank, epochs, seed, z_rows=None, train=True, device="cpu"):
    x_np, tgt_np, meta = assemble_fold(Y, eval_index, rank=rank)
    dev = torch.device(device)
    torch.manual_seed(seed)
    x = torch.tensor(x_np.reshape(len(x_np), Y.shape[1], N_SEC, -1), dtype=torch.float32, device=dev)
    tgt = torch.tensor(np.nan_to_num(tgt_np), dtype=torch.long, device=dev)
    mag = torch.tensor(np.nan_to_num(meta["mag"]), dtype=torch.float32, device=dev)
    mk = torch.tensor(presence_mask(Y)[meta["input_steps"]], dtype=torch.float32, device=dev)
    P = torch.tensor(prior, dtype=torch.float32, device=dev)
    rows = z_rows if z_rows is not None else meta["input_steps"]
    model = HERALD75(Y.shape[1], Y.shape[0], x.shape[-1], rank=rank).to(dev)
    n_loss = len(x_np) - 1                      # the final step is scored, never trained on
    if train:
        opt = torch.optim.Adam(model.parameters(), lr=LR)
        ce, hub = nn.CrossEntropyLoss(), nn.HuberLoss()
        model.train()
        for _ in range(epochs):
            opt.zero_grad()
            o = model(x, P, mk, rows)
            loss = sum(ce(o["logits"][i], tgt[i]) for i in range(n_loss)) / n_loss
            loss = loss + 0.1 * sum(hub(o["mag"][i], mag[i]) for i in range(n_loss)) / n_loss
            loss.backward()
            opt.step()
    model.eval()
    with torch.no_grad():
        o = model(x, P, mk, rows)
    return model, o, meta


def _pack(o, model):
    return {"adj": np.stack([a.cpu().numpy() for a in o["adj"]]),
            "logits": np.stack([a.cpu().numpy() for a in o["logits"]]),
            "mag": np.stack([a.cpu().numpy() for a in o["mag"]]),
            "raw": np.stack([a.cpu().numpy() for a in o["raw"]]),
            "z": model.z.detach().cpu().numpy()}


def export_twice(Y, eval_index, seed=0, rank=RANK_DEFAULT, epochs=3):
    prior = np.zeros((Y.shape[1], Y.shape[1]))
    model, _, _ = _fit(Y, prior, eval_index, rank, epochs, seed)
    x_np, _, meta = assemble_fold(Y, eval_index, rank=rank)
    dev = next(model.parameters()).device
    x = torch.tensor(x_np.reshape(len(x_np), Y.shape[1], N_SEC, -1), dtype=torch.float32, device=dev)
    mk = torch.tensor(presence_mask(Y)[meta["input_steps"]], dtype=torch.float32, device=dev)
    P = torch.tensor(prior, dtype=torch.float32, device=dev)
    model.eval()
    with torch.no_grad():
        a = _pack(model(x, P, mk, meta["input_steps"]), model)
        b = _pack(model(x, P, mk, meta["input_steps"]), model)
    return a, b


def trace_node(Y, zone, sector, eval_index, seed=0, rank=RANK_DEFAULT, epochs=3):
    prior = np.zeros((Y.shape[1], Y.shape[1]))
    model, o, _ = _fit(Y, prior, eval_index, rank, epochs, seed)
    return {"hidden": np.stack([hh[zone, sector].cpu().numpy() for hh in o["hidden"]]),
            "outgoing_message": np.stack([mm[zone, sector].cpu().numpy() for mm in o["msg"]])}


def score_arm(Y, relational, placebo=False, seed=0, k=10):
    """Light kNN arm used only by the placebo-validity guard, mirroring the analogy block."""
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.metrics import f1_score
    G = growth(Y)
    S = states_from_growth(G)
    S[0] = np.nan
    T, Z, _ = Y.shape
    rng = np.random.default_rng(seed)
    def feats(t):
        cat = lambda A: np.concatenate([A[:, s] for s in range(N_SEC)])
        # DEC-103: the national sector mean absorbs most of what a neighbour block carries.
        # It belongs in the BASE, otherwise a random-neighbour placebo adds it and beats the
        # base, which is what the guard caught on the first run.
        sect_mean = np.repeat(np.nanmean(G[t], axis=0), Z)
        X = [cat(G[t]), cat(np.log1p(np.maximum(Y[t], 0))), sect_mean]
        if relational:
            traj = np.concatenate([G[max(1, t - 3):t + 1, :, s].T for s in range(N_SEC)], axis=0)
            fin = np.isfinite(traj).all(1)
            Tz = np.zeros_like(traj)
            if fin.any():
                Tz[fin] = (traj[fin] - traj[fin].mean(1, keepdims=True)) / np.maximum(traj[fin].std(1, keepdims=True), 1e-9)
            Cm = Tz @ Tz.T / traj.shape[1]
            sec = np.repeat(np.arange(N_SEC), Z)
            same = sec[:, None] == sec[None, :]
            np.fill_diagonal(same, False)
            Cm = np.where(same, Cm, -np.inf)
            if placebo:
                idx = np.stack([rng.choice(np.where(sec == sec[i])[0][np.where(sec == sec[i])[0] != i],
                                           size=k, replace=False) for i in range(len(Cm))])
            else:
                idx = np.argpartition(-Cm, k, axis=1)[:, :k]
            X.append(np.nan_to_num(cat(G[t])[idx]).mean(1))
        return np.column_stack(X)
    tr = list(range(2, T - 2))
    Xtr = np.vstack([feats(t) for t in tr])
    ytr = np.concatenate([np.concatenate([S[t + 1][:, s] for s in range(N_SEC)]) for t in tr])
    te = T - 2
    Xte = feats(te)
    yte = np.concatenate([S[te + 1][:, s] for s in range(N_SEC)])
    ok, okt = np.isfinite(ytr), np.isfinite(yte)
    m = HistGradientBoostingClassifier(max_iter=80, random_state=seed)
    m.fit(np.nan_to_num(Xtr[ok]), ytr[ok])
    return float(f1_score(yte[okt], m.predict(np.nan_to_num(Xte[okt])), average="macro"))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        rng = np.random.default_rng(0)
        Y = rng.poisson(np.maximum(rng.uniform(20, 400, (12, 9)) * np.ones((14, 1, 1)), 1.0)).astype(float)
        x, tgt, meta = assemble_fold(Y, eval_index=13)
        print(json.dumps({k: v for k, v in meta.items() if k != "mag"}, default=str, indent=2))
        print("obs per graph parameter:", meta["train_labels"] / meta["graph_parameters"])
