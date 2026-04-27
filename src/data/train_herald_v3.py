"""
HERALD V3 — Dynamic Adaptive Graph for Territorial Establishment Forecasting

Key structural change vs V2:
  V2: adaptive_adj() computed once before the temporal loop — static for all timesteps.
  V3: A_t computed inside the GRUCell loop from node embeddings that include h_{t-1}.
      The adjacency is different for each year.

Architecture per timestep t:
  h_{t-1} (previous GRU hidden state, includes all economic history up to t-1)
  + x_ann[t]  (annual features: lags, FLORES, stocks, flags — all at t-1)
  + x_q[t]    (URSSAF Q1-Q3 of year t-1)
  + regime[t] (is_covid_year, is_post_covid_rebound, global_growth_norm)
  → e_t  = relu(annual_proj(x_ann) + q_proj(quarterly_enc(x_q)) + h_proj(h_{t-1}))
  → Q_t, K_t = proj_Q(e_t), proj_K(e_t)
  → A_t  = topk_sparse_softmax(Q_t K_t^T / sqrt(d_k) + γ_geo·log(A_geo) + γ_mob·log(A_mob))
  → m_t  = msg_proj(A_t @ e_t)
  → g_t  = sigmoid(MLP([e_t, m_t, regime_t]))
  → z_t  = g_t * e_t + (1 − g_t) * m_t
  → h_t  = GRUCell(z_t, h_{t-1})
  → residual_t = Linear(h_t)

V2 outputs NOT overwritten. All V3 outputs use _v3_ prefix:
  data/processed/herald_v3_predictions_{ablation}_seed_{seed}_v1.csv
  data/processed/herald_v3_internals_{ablation}_seed_{seed}_v1.npz
  reports/herald_v3_metrics_v1.json
  reports/HERALD_V3_MODEL_V1.md
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
except ModuleNotFoundError as exc:
    raise SystemExit("PyTorch required. Run inside conda torch environment.") from exc

ROOT       = Path(__file__).resolve().parents[2]
PROCESSED  = ROOT / "data/processed"
REPORTS    = ROOT / "reports"
METADATA   = ROOT / "metadata"
RAW_URSSAF = ROOT / "data/raw/employment/urssaf/urssaf_emploi_ze_quarterly_raw.csv"

PANEL_PATH    = PROCESSED / "dynamic_stgnn_feature_panel_v1.csv"
SPLITS_PATH   = METADATA  / "dynamic_stgnn_walk_forward_splits_v1.csv"
GEO_ADJ_PATH  = PROCESSED / "graph_adjacency_core_v0.csv"
MOB_ADJ_PATH  = PROCESSED / "graph_adjacency_mobility_v0.csv"
NODE_IDX_PATH = PROCESSED / "graph_node_index_core_v0.csv"

OUT_JSON = REPORTS / "herald_v3_metrics_v1.json"
OUT_MD   = REPORTS / "HERALD_V3_MODEL_V1.md"

TARGET_COL  = "side_establishment_creations_official"
A17_SECTORS = ["az","de","c1","c2","c3","c4","c5","fz","gz","hz",
               "iz","jz","kz","lz","mn","oq","ru"]
REGIME_DIM  = 3   # [is_covid_year, is_post_covid_rebound, global_growth_norm]

# ZE2020 codes for key diagnostic zones
KEY_ZONES = {"Paris": 1109, "Lyon": 8421, "Marseille": 9312, "Toulouse": 7625}


# ─── helpers ──────────────────────────────────────────────────────────────────

def wmape(y_true, y_pred):
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    d = np.abs(y_true).sum()
    return float(np.abs(y_true - y_pred).sum() / d) if d > 0 else np.nan


def set_seed(seed):
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def row_normalize(adj):
    adj = np.asarray(adj, dtype=np.float32)
    s = adj.sum(axis=1, keepdims=True)
    return np.divide(adj, s, out=np.zeros_like(adj), where=s > 0)


def load_adjacency(path):
    df = pd.read_csv(path)
    if "source_idx" in df.columns:
        df = df.drop(columns=["source_idx"])
    return row_normalize(df.to_numpy(dtype=np.float32))


def fit_ridge_ar(train, test):
    cols = [c for c in ["side_lag_1","side_lag_2","side_lag_3","growth_1y","growth_2y"]
            if c in train.columns]
    tr = train.dropna(subset=[TARGET_COL])
    te = test.dropna(subset=[TARGET_COL])
    m = Pipeline([("imp", SimpleImputer(strategy="median")),
                  ("sc",  StandardScaler()),
                  ("r",   Ridge(alpha=1.0))])
    m.fit(tr[cols].values.astype(float), tr[TARGET_COL].values.astype(float))
    return np.maximum(m.predict(te[cols].values.astype(float)), 0.0)


def fit_ridge_expanding(train, pred_year, min_years=3):
    holdout = train[train["target_year"] == pred_year].copy()
    fit     = train[train["target_year"] < pred_year].copy()
    if fit["target_year"].nunique() < min_years or len(holdout) == 0:
        return holdout, np.full(len(holdout), np.nan)
    return holdout, fit_ridge_ar(fit, holdout)


# ─── quarterly tensor ──────────────────────────────────────────────────────────

def build_quarterly_tensor(zones_sorted, years_sorted):
    """(T, 3, N, 2): Q1-Q3 of T-1 → predict T. Q4 excluded (not forecast-safe)."""
    df = pd.read_csv(RAW_URSSAF, dtype={"code_zone_d_emploi": str})
    df["code_zone_d_emploi"] = df["code_zone_d_emploi"].str.zfill(4)
    df = df.groupby(["annee","trimestre","code_zone_d_emploi"])[
        ["effectifs_salaries_cvs","masse_salariale_cvs"]
    ].sum().reset_index()
    df = df[df["trimestre"] <= 3].copy()

    zone_to_idx = {z: i for i, z in enumerate(zones_sorted)}
    year_to_idx = {y: i for i, y in enumerate(years_sorted)}
    T, N = len(years_sorted), len(zones_sorted)
    tensor = np.zeros((T, 3, N, 2), dtype=np.float32)

    for _, row in df.iterrows():
        source_year = int(row["annee"])
        target_year = source_year + 1
        q  = int(row["trimestre"]) - 1
        ze = int(row["code_zone_d_emploi"])
        if target_year not in year_to_idx or ze not in zone_to_idx:
            continue
        ti, zi = year_to_idx[target_year], zone_to_idx[ze]
        tensor[ti, q, zi, 0] = float(row["effectifs_salaries_cvs"])
        tensor[ti, q, zi, 1] = float(row["masse_salariale_cvs"])
    return tensor


def normalize_quarterly(tensor_full, train_t_idx):
    T, Q, N, F_ = tensor_full.shape
    flat_train = tensor_full[train_t_idx].reshape(-1, F_)
    mean = flat_train.mean(axis=0, keepdims=True)
    std  = flat_train.std(axis=0, keepdims=True)
    std  = np.where(std == 0, 1.0, std)
    return (tensor_full - mean) / std, mean, std


# ─── sector target ─────────────────────────────────────────────────────────────

def build_sector_target(panel, zones_sorted, years_sorted):
    T, N, S = len(years_sorted), len(zones_sorted), len(A17_SECTORS)
    out = np.full((T, N, S), np.nan, dtype=np.float32)
    zone_to_idx = {z: i for i, z in enumerate(zones_sorted)}
    year_to_idx = {y: i for i, y in enumerate(years_sorted)}
    sec_cols  = [f"flores_etab_{s}_t_minus_1" for s in A17_SECTORS]
    available = [c for c in sec_cols if c in panel.columns]
    if not available:
        return out
    for row in panel.itertuples(index=False):
        yr, ze = int(row.target_year), int(row.ZE2020)
        if yr not in year_to_idx or ze not in zone_to_idx:
            continue
        ti, zi = year_to_idx[yr], zone_to_idx[ze]
        vals  = np.array([getattr(row, c) if hasattr(row, c) else np.nan
                          for c in available], dtype=np.float32)
        total = np.nansum(vals)
        if total > 0:
            out[ti, zi, :len(available)] = vals / total
    return out


# ─── annual tensor ─────────────────────────────────────────────────────────────

def build_annual_tensor(panel, cols, zones_sorted, years_sorted):
    T, N, F_ = len(years_sorted), len(zones_sorted), len(cols)
    x = np.zeros((T, N, F_), dtype=np.float32)
    y = np.full((T, N), np.nan, dtype=np.float32)
    zone_to_idx = {z: i for i, z in enumerate(zones_sorted)}
    year_to_idx = {yr: i for i, yr in enumerate(years_sorted)}
    for row in panel.itertuples(index=False):
        yr, ze = int(row.target_year), int(row.ZE2020)
        if yr not in year_to_idx or ze not in zone_to_idx:
            continue
        ti, zi = year_to_idx[yr], zone_to_idx[ze]
        x[ti, zi] = [float(getattr(row, c)) if hasattr(row, c) else 0.0 for c in cols]
        y[ti, zi]  = float(getattr(row, TARGET_COL))
    return x, y


# ─── regime vectors ────────────────────────────────────────────────────────────

def build_regime_vectors(panel, years_sorted, train_max):
    """
    Returns (T, REGIME_DIM) float32 array:
      [0] is_covid_year
      [1] is_post_covid_rebound
      [2] global_growth_norm  = mean(side_lag_1[t]) / mean(side_lag_1[t-1]) - 1,
          normalized by training-period mean/std (forecast-safe: uses t-2 and t-1 data).
    """
    T = len(years_sorted)
    year_to_idx = {y: i for i, y in enumerate(years_sorted)}

    agg = (panel.groupby("target_year")
           .agg(is_covid=("is_covid_year", "first"),
                is_rebound=("is_post_covid_rebound", "first"),
                mean_lag1=("side_lag_1", "mean"))
           .reset_index()
           .sort_values("target_year")
           .reset_index(drop=True))

    agg["global_growth"] = agg["mean_lag1"].pct_change().fillna(0.0)

    # Normalize by training statistics only
    train_mask = agg["target_year"] <= train_max
    g_mean = float(agg.loc[train_mask, "global_growth"].mean())
    g_std  = float(agg.loc[train_mask, "global_growth"].std())
    if np.isnan(g_std) or g_std < 1e-8:
        g_std = 1.0
    agg["global_growth_norm"] = (agg["global_growth"] - g_mean) / g_std

    regime = np.zeros((T, REGIME_DIM), dtype=np.float32)
    for _, row in agg.iterrows():
        yr = int(row["target_year"])
        if yr not in year_to_idx:
            continue
        ti = year_to_idx[yr]
        regime[ti, 0] = float(row["is_covid"])
        regime[ti, 1] = float(row["is_rebound"])
        regime[ti, 2] = float(row["global_growth_norm"])
    return regime


# ─── HERALD V3 architecture ────────────────────────────────────────────────────

class QuarterlyEncoder(nn.Module):
    """GRU over Q1-Q3 of year T-1 → annual employment momentum per zone."""
    def __init__(self, in_dim=2, hidden_dim=16):
        super().__init__()
        self.gru = nn.GRU(in_dim, hidden_dim, batch_first=True)

    def forward(self, x):
        # x: (N, 3, 2)
        _, h = self.gru(x)    # h: (1, N, hidden_dim)
        return h.squeeze(0)   # (N, hidden_dim)


def topk_sparse_softmax(logits: torch.Tensor, k: int) -> torch.Tensor:
    """
    Per-row: keep the top-k logits, set the rest to -inf, apply softmax.
    logits: (N, N)  →  returns (N, N) row-stochastic sparse matrix.
    """
    k = min(k, logits.shape[-1])
    topk_vals, topk_idx = torch.topk(logits, k, dim=-1)
    sparse = torch.full_like(logits, float("-inf"))
    sparse.scatter_(-1, topk_idx, topk_vals)
    out = torch.softmax(sparse, dim=-1)
    return torch.nan_to_num(out, nan=0.0)  # safety: all-inf row → 0


class HERALDv3Residual(nn.Module):
    """
    HERALD V3: per-timestep dynamic adjacency conditioned on h_{t-1}.

    The key difference from V2:
      V2 calls self.adaptive_adj() once before the loop (static matrix).
      V3 calls self._dynamic_adj(e_t, prior_logits) inside the loop,
         where e_t includes h_{t-1} via self.h_proj(h). A_t therefore
         changes every year based on the accumulated economic state.
    """

    def __init__(self, num_nodes, annual_dim, hidden_dim,
                 attn_dim=8, q_hidden=16, n_sectors=17,
                 top_k=10, prior_strength_init=1.0):
        super().__init__()
        self.num_nodes  = num_nodes
        self.hidden_dim = hidden_dim
        self.attn_dim   = attn_dim
        self.top_k      = top_k
        self.n_sectors  = n_sectors

        # Quarterly encoder
        self.quarterly_enc = QuarterlyEncoder(in_dim=2, hidden_dim=q_hidden)
        self.q_proj        = nn.Linear(q_hidden, hidden_dim)

        # Annual projection
        self.annual_proj = nn.Linear(annual_dim, hidden_dim)

        # Temporal context: h_{t-1} → hidden  (the V3 key change)
        self.h_proj = nn.Linear(hidden_dim, hidden_dim)

        # Dynamic attention projections
        self.proj_Q = nn.Linear(hidden_dim, attn_dim)
        self.proj_K = nn.Linear(hidden_dim, attn_dim)

        # Learnable prior strength (γ_geo, γ_mob) — scalars
        self.gamma_geo = nn.Parameter(torch.tensor(float(prior_strength_init)))
        self.gamma_mob = nn.Parameter(torch.tensor(float(prior_strength_init)))

        # Static adaptive embeddings (used only in static_adaptive ablation)
        self.static_emb_1 = nn.Parameter(torch.empty(num_nodes, attn_dim))
        self.static_emb_2 = nn.Parameter(torch.empty(attn_dim, num_nodes))
        nn.init.orthogonal_(self.static_emb_1)
        nn.init.orthogonal_(self.static_emb_2)

        # Message projection
        self.msg_proj = nn.Linear(hidden_dim, hidden_dim)

        # Regime gate: [e_t (H), m_t (H), regime_t (R)] → (N, 1)
        self.gate_mlp = nn.Sequential(
            nn.Linear(hidden_dim * 2 + REGIME_DIM, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 1),
        )

        # GRU cell (recurrent state update)
        self.gru_cell = nn.GRUCell(hidden_dim, hidden_dim)

        # Outputs
        self.out_main   = nn.Linear(hidden_dim, 1)
        self.out_sector = nn.Linear(hidden_dim, n_sectors)

    # ── adjacency helpers ───────────────────────────────────────────────────

    def _static_adj(self) -> torch.Tensor:
        """Adaptive static adjacency for static_adaptive ablation."""
        return torch.softmax(
            torch.relu(self.static_emb_1 @ self.static_emb_2), dim=1
        )

    def _dynamic_adj(self, e_t: torch.Tensor,
                     prior_logits: torch.Tensor) -> torch.Tensor:
        """
        Dynamic adjacency for timestep t.
        e_t includes h_{t-1} via h_proj, so A_t depends on prior economic state.
        prior_logits = γ_geo·log(A_geo+ε) + γ_mob·log(A_mob+ε) — structural bias.
        """
        Q = self.proj_Q(e_t)                           # (N, d_k)
        K = self.proj_K(e_t)                           # (N, d_k)
        raw = (Q @ K.T) / (self.attn_dim ** 0.5)       # (N, N)
        return topk_sparse_softmax(raw + prior_logits, self.top_k)

    # ── forward ─────────────────────────────────────────────────────────────

    def forward(self, x_annual_seq, x_quarterly_seq, regime_seq,
                adj_geo, adj_mob, adj_log_geo, adj_log_mob,
                ablation="full", return_internals=False):
        """
        x_annual_seq:    list[T] of (N, F_ann)
        x_quarterly_seq: list[T] of (N, 3, 2)
        regime_seq:      list[T] of (REGIME_DIM,)
        adj_geo, adj_mob:          (N, N) fixed row-normalized adjacency
        adj_log_geo, adj_log_mob:  (N, N) log-adjacency for prior anchoring
        ablation: full | self_only | fixed_geo_mob_only | static_adaptive |
                  dynamic_adaptive_no_quarterly | dynamic_adaptive_no_regime |
                  dynamic_adaptive_no_smooth

        Returns (train):  preds (T,N), sectors (T,N,S), smooth_loss scalar
        Returns (internals): + adj_tensor (T,N,N), gate_tensor (T,N,1)
        """
        N      = self.num_nodes
        device = next(self.parameters()).device

        h = torch.zeros(N, self.hidden_dim, device=device)

        # Prior logits: fixed throughout sequence, but γ_geo/γ_mob are learned
        prior_logits  = self.gamma_geo * adj_log_geo + self.gamma_mob * adj_log_mob
        static_adj_m  = self._static_adj()
        fixed_blend   = 0.5 * adj_geo + 0.5 * adj_mob

        pred_list, sector_list = [], []
        adj_list, gate_list    = [], []
        smooth_loss  = torch.tensor(0.0, device=device)
        n_smooth     = 0
        A_prev       = None

        for x_ann, x_q, regime_t in zip(x_annual_seq, x_quarterly_seq, regime_seq):
            regime_exp = regime_t.unsqueeze(0).expand(N, -1)  # (N, R)

            # ── 1. Encode annual + quarterly ──────────────────────────────
            ann = F.relu(self.annual_proj(x_ann))          # (N, H)

            if ablation == "dynamic_adaptive_no_quarterly":
                q_enc = torch.zeros_like(ann)
            else:
                q_enc = F.relu(self.q_proj(self.quarterly_enc(x_q)))  # (N, H)

            # ── 2. Node embedding with temporal context from h_{t-1} ─────
            # This is the V3 key change: h_{t-1} informs e_t → informs A_t
            e_t = F.relu(ann + q_enc + self.h_proj(h))    # (N, H)

            # ── 3. Adjacency and message passing ──────────────────────────
            if ablation == "self_only":
                A_t = None
                m_t = e_t                               # identity: no neighbors

            elif ablation == "fixed_geo_mob_only":
                A_t = fixed_blend
                m_t = self.msg_proj(A_t @ e_t)

            elif ablation == "static_adaptive":
                A_t = static_adj_m                      # same matrix every step
                m_t = self.msg_proj(A_t @ e_t)

            else:
                # full | dynamic_adaptive_no_quarterly |
                # dynamic_adaptive_no_regime | dynamic_adaptive_no_smooth
                A_t = self._dynamic_adj(e_t, prior_logits)
                m_t = self.msg_proj(A_t @ e_t)

            # ── 4. Temporal smoothness ────────────────────────────────────
            if (A_t is not None and A_prev is not None
                    and ablation != "dynamic_adaptive_no_smooth"):
                smooth_loss = smooth_loss + torch.sum((A_t - A_prev) ** 2)
                n_smooth += 1

            # ── 5. Regime gate ────────────────────────────────────────────
            if ablation == "self_only":
                z_t = e_t
                g_t = torch.ones(N, 1, device=device)
            else:
                if ablation == "dynamic_adaptive_no_regime":
                    regime_for_gate = torch.zeros_like(regime_exp)
                else:
                    regime_for_gate = regime_exp
                gate_in = torch.cat([e_t, m_t, regime_for_gate], dim=-1)
                g_t = torch.sigmoid(self.gate_mlp(gate_in))  # (N, 1)
                z_t = g_t * e_t + (1.0 - g_t) * m_t

            # ── 6. GRU cell update: h_{t-1} → h_t ────────────────────────
            h = self.gru_cell(z_t, h)

            # ── 7. Residual prediction from updated state ─────────────────
            pred   = self.out_main(h).squeeze(-1)                  # (N,)
            sector = torch.softmax(self.out_sector(h), dim=-1)     # (N, S)

            pred_list.append(pred)
            sector_list.append(sector)

            if return_internals:
                A_store = A_t if A_t is not None else torch.eye(N, device=device)
                adj_list.append(A_store.detach())
                gate_list.append(g_t.detach())

            A_prev = A_t

        if n_smooth > 0:
            smooth_loss = smooth_loss / n_smooth

        preds   = torch.stack(pred_list,   dim=0)   # (T, N)
        sectors = torch.stack(sector_list, dim=0)   # (T, N, S)

        if return_internals:
            adj_tensor  = torch.stack(adj_list,  dim=0)  # (T, N, N)
            gate_tensor = torch.stack(gate_list, dim=0)  # (T, N, 1)
            return preds, sectors, smooth_loss, adj_tensor, gate_tensor

        return preds, sectors, smooth_loss


# ─── feature columns ──────────────────────────────────────────────────────────

def feature_columns(panel, ablation="full"):
    base   = ["side_lag_1","side_lag_2","side_lag_3","growth_1y","growth_2y"]
    flores = [c for c in panel.columns
              if c.startswith("flores_") and c.endswith("_t_minus_1")
              and "etab_" not in c]
    side   = [c for c in panel.columns
              if c.startswith("side_stock_") and c.endswith("_t_minus_1")]
    flags  = ["has_flores_source","has_side_stock_source","has_urssaf_source",
              "is_covid_year","is_post_covid_rebound"]

    # URSSAF annual is redundant when QuarterlyGRU is active (corr=0.995).
    # Re-enable it only when quarterly is disabled.
    if ablation == "dynamic_adaptive_no_quarterly":
        urssaf = [c for c in panel.columns
                  if c.startswith("urssaf_") and c.endswith("_t_minus_1")]
    else:
        urssaf = []

    cols = base + flores + side + urssaf + flags
    return [c for c in cols if c in panel.columns]


# ─── sequence builder ─────────────────────────────────────────────────────────

def make_sequences(panel, cols, q_tensor, sector_tensor,
                   zones_sorted, years_sorted, train_max, target_year, args):
    year_to_idx  = {y: i for i, y in enumerate(years_sorted)}
    t_train_idx  = [year_to_idx[y] for y in years_sorted if y <= train_max]
    t_full_idx   = [year_to_idx[y] for y in years_sorted if y <= target_year]
    test_idx     = year_to_idx[target_year]

    x_annual, y  = build_annual_tensor(panel, cols, zones_sorted, years_sorted)

    # Ridge residual labels — expanding mode: Ridge trained only on years < pred_year
    train_df = panel[panel["target_year"] <= train_max].copy()
    test_df  = panel[panel["target_year"] == target_year].copy()
    ridge_test = fit_ridge_ar(train_df, test_df)

    ridge      = np.full((len(years_sorted), len(zones_sorted)), np.nan, dtype=np.float32)
    zone_to_idx = {z: i for i, z in enumerate(zones_sorted)}

    for pred_year in sorted(train_df["target_year"].unique()):
        holdout, rp = fit_ridge_expanding(train_df, int(pred_year))
        for row, p in zip(holdout.itertuples(index=False), rp):
            if np.isfinite(p):
                ridge[year_to_idx[int(row.target_year)],
                      zone_to_idx[int(row.ZE2020)]] = p
    for row, p in zip(test_df.itertuples(index=False), ridge_test):
        ridge[test_idx, zone_to_idx[int(row.ZE2020)]] = p

    # Annual features: impute + scale on train
    imp        = SimpleImputer(strategy="median")
    flat_train = x_annual[t_train_idx].reshape(-1, x_annual.shape[-1])
    imp.fit(flat_train)
    x_ann_train = imp.transform(flat_train).reshape(
        len(t_train_idx), len(zones_sorted), -1)
    x_ann_full  = imp.transform(
        x_annual[t_full_idx].reshape(-1, x_annual.shape[-1])
    ).reshape(len(t_full_idx), len(zones_sorted), -1)

    mean = x_ann_train.mean(axis=(0, 1), keepdims=True)
    std  = x_ann_train.std(axis=(0, 1), keepdims=True)
    std  = np.where(std == 0, 1.0, std)
    x_ann_train = (x_ann_train - mean) / std
    x_ann_full  = (x_ann_full  - mean) / std

    # Quarterly
    q_norm, _, _ = normalize_quarterly(q_tensor, t_train_idx)
    q_train = q_norm[t_train_idx]
    q_full  = q_norm[t_full_idx]

    # Zone normalization (fold-safe)
    train_y_raw = y[t_train_idx]
    zone_mean   = np.nanmean(train_y_raw, axis=0)
    zone_std    = np.nanstd(train_y_raw,  axis=0)
    zone_std    = np.where(zone_std < 1.0, 1.0, zone_std)

    # Residuals
    train_resid = (train_y_raw - ridge[t_train_idx]) / zone_std[np.newaxis, :]
    mask        = np.isfinite(train_resid).astype(np.float32)
    train_resid = np.nan_to_num(train_resid, nan=0.0).astype(np.float32)

    # Volume weights (WMAPE-aligned)
    zone_weight = np.clip(zone_mean / zone_mean.mean(), 0.1, 10.0)

    # Sector target
    sec_train = sector_tensor[t_train_idx]
    sec_mask  = np.isfinite(sec_train).all(axis=-1).astype(np.float32)
    sec_train = np.nan_to_num(sec_train, nan=1.0 / 17)

    # Regime vectors (normalized by train_max stats)
    regime_all   = build_regime_vectors(panel, years_sorted, train_max)
    regime_train = regime_all[t_train_idx]
    regime_full  = regime_all[t_full_idx]

    return {
        "zones":          zones_sorted,
        "years_full":     [y for y in years_sorted if y <= target_year],
        "x_ann_train":    x_ann_train.astype(np.float32),
        "x_ann_full":     x_ann_full.astype(np.float32),
        "q_train":        q_train.astype(np.float32),
        "q_full":         q_full.astype(np.float32),
        "regime_train":   regime_train.astype(np.float32),
        "regime_full":    regime_full.astype(np.float32),
        "train_resid":    train_resid,
        "mask":           mask,
        "zone_weight":    zone_weight.astype(np.float32),
        "zone_std":       zone_std.astype(np.float32),
        "sec_train":      sec_train.astype(np.float32),
        "sec_mask":       sec_mask.astype(np.float32),
        "test_y":         y[test_idx],
        "test_ridge":     ridge[test_idx],
        "test_mask":      np.isfinite(y[test_idx]) & np.isfinite(ridge[test_idx]),
        "target_year":    target_year,
    }


# ─── training ─────────────────────────────────────────────────────────────────

def train_herald_v3(seq, adj_geo, adj_mob, args, device):
    N          = len(seq["zones"])
    annual_dim = seq["x_ann_train"].shape[-1]

    model = HERALDv3Residual(
        num_nodes=N,
        annual_dim=annual_dim,
        hidden_dim=args.hidden_dim,
        attn_dim=args.attn_dim,
        q_hidden=args.q_hidden,
        n_sectors=len(A17_SECTORS),
        top_k=args.top_k,
        prior_strength_init=args.prior_strength_init,
    ).to(device)

    opt   = torch.optim.AdamW(model.parameters(), lr=args.lr,
                               weight_decay=args.weight_decay)
    huber = nn.HuberLoss(delta=args.huber_delta, reduction="none")

    x_ann    = torch.tensor(seq["x_ann_train"],  device=device)
    x_q      = torch.tensor(seq["q_train"],      device=device)
    regime   = torch.tensor(seq["regime_train"], device=device)
    target   = torch.tensor(seq["train_resid"],  device=device)
    mask     = torch.tensor(seq["mask"],         device=device)
    zone_w   = torch.tensor(seq["zone_weight"],  device=device)
    sec_t    = torch.tensor(seq["sec_train"],    device=device)
    sec_m    = torch.tensor(seq["sec_mask"],     device=device)

    adj_g     = torch.tensor(adj_geo, device=device)
    adj_m_t   = torch.tensor(adj_mob, device=device)
    eps       = 1e-6
    adj_log_g = torch.log(adj_g   + eps)
    adj_log_m = torch.log(adj_m_t + eps)

    T        = x_ann.shape[0]
    ablation = args.ablation
    history = []

    model.train()
    for ep in range(args.epochs):
        opt.zero_grad()

        ann_list = [x_ann[t]               for t in range(T)]
        q_list   = [x_q[t].permute(1,0,2)  for t in range(T)]  # (3,N,2)→(N,3,2)
        reg_list = [regime[t]              for t in range(T)]

        pred_main, pred_sector, smooth_loss = model(
            ann_list, q_list, reg_list,
            adj_g, adj_m_t, adj_log_g, adj_log_m,
            ablation=ablation, return_internals=False,
        )

        zone_w_bc = zone_w.unsqueeze(0).expand_as(pred_main)
        denom     = torch.clamp((mask * zone_w_bc).sum(), min=1.0)
        loss_main = (huber(pred_main, target) * mask * zone_w_bc).sum() / denom

        eps_kl    = 1e-8
        kl        = sec_t * (torch.log(sec_t + eps_kl) - torch.log(pred_sector + eps_kl))
        loss_sec  = (kl.sum(-1) * sec_m).sum() / torch.clamp(sec_m.sum(), min=1.0)

        loss = loss_main + args.sector_lambda * loss_sec + args.smooth_lambda * smooth_loss
        loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), args.grad_clip)
        opt.step()

        history.append({
            "epoch": ep + 1,
            "loss_total": float(loss.detach().cpu().item()),
            "loss_main": float(loss_main.detach().cpu().item()),
            "loss_sector": float(loss_sec.detach().cpu().item()),
            "loss_smooth": float(smooth_loss.detach().cpu().item()),
        })

    # ── Inference on full sequence (train + test) ──────────────────────────
    model.eval()
    with torch.no_grad():
        x_ann_f  = torch.tensor(seq["x_ann_full"],   device=device)
        x_q_f    = torch.tensor(seq["q_full"],        device=device)
        reg_f    = torch.tensor(seq["regime_full"],   device=device)
        T_full   = x_ann_f.shape[0]

        ann_f  = [x_ann_f[t]              for t in range(T_full)]
        q_f    = [x_q_f[t].permute(1,0,2) for t in range(T_full)]
        reg_fl = [reg_f[t]                for t in range(T_full)]

        pred_f, sec_f, smooth_f, adj_t, gate_t = model(
            ann_f, q_f, reg_fl,
            adj_g, adj_m_t, adj_log_g, adj_log_m,
            ablation=ablation, return_internals=True,
        )

    internals = {
        "dynamic_adj":           adj_t.cpu().numpy(),    # (T_full, N, N)
        "gate_values":           gate_t.cpu().numpy(),   # (T_full, N, 1)
        "gamma_geo":             float(model.gamma_geo.item()),
        "gamma_mob":             float(model.gamma_mob.item()),
        "smooth_loss_inference": float(smooth_f.item()),
        "years":                 seq["years_full"],
        "node_order":            seq["zones"],
        "training_history":      history,
    }
    return pred_f[-1].cpu().numpy(), sec_f[-1].cpu().numpy(), internals


# ─── evaluation loop ──────────────────────────────────────────────────────────

def evaluate_herald_v3(panel, splits, cols, q_tensor, sector_tensor,
                       zones_sorted, years_sorted, adj_geo, adj_mob, args, device):
    rows, internals_by_year = [], {}

    for _, split in splits.iterrows():
        target_year = int(split["target_year"])
        train_max   = int(split["train_years_max"])
        print(f"  Fold {target_year}...", flush=True)

        seq = make_sequences(panel, cols, q_tensor, sector_tensor,
                             zones_sorted, years_sorted, train_max, target_year, args)
        residual, _, internals = train_herald_v3(seq, adj_geo, adj_mob, args, device)
        internals["target_year"] = target_year
        internals_by_year[target_year] = internals

        mask_    = seq["test_mask"]
        y_true   = seq["test_y"][mask_]
        ridge_p  = seq["test_ridge"][mask_]
        zone_std = seq["zone_std"][mask_]
        y_pred   = np.maximum(ridge_p + residual[mask_] * zone_std, 0.0)

        for ze, yt, yp in zip(np.asarray(zones_sorted)[mask_], y_true, y_pred):
            rows.append({"model": "herald_v3", "target_year": target_year,
                         "ZE2020": int(ze), "y_true": float(yt), "y_pred": float(yp),
                         "abs_error": float(abs(yt - yp))})

    return rows, internals_by_year


# ─── diagnostics ──────────────────────────────────────────────────────────────

def compute_adj_diagnostics(internals_by_year, zones_sorted, node_idx_df):
    """Per-fold adjacency metrics + top-10 neighbors for key zones."""
    ze_to_libze  = {int(r["ze2020"]): r["libze2020"] for _, r in node_idx_df.iterrows()}
    zone_idx_map = {z: i for i, z in enumerate(zones_sorted)}

    diag_rows       = []
    smooth_by_fold  = {}
    key_zone_top10  = {}

    for yr_raw, intern in sorted(internals_by_year.items()):
        yr = int(yr_raw)
        adj_arr = intern["dynamic_adj"]   # (T, N, N)
        years_f = intern["years"]
        T       = adj_arr.shape[0]

        # Smooth: mean ||A_t - A_{t-1}||_F over adjacent pairs
        smooth_vals = [float(np.sum((adj_arr[t] - adj_arr[t-1])**2))
                       for t in range(1, T)]
        smooth_mean         = float(np.mean(smooth_vals)) if smooth_vals else 0.0
        smooth_by_fold[yr]  = {"mean_smooth": round(smooth_mean, 6),
                               "per_year": {int(years_f[t]): round(smooth_vals[t-1], 6)
                                            for t in range(1, T)}}

        # Density and gamma values (last timestep)
        A_last  = adj_arr[-1]
        density = float((A_last > 1e-4).mean())
        diag_rows.append({
            "target_year":  yr,
            "smooth_mean":  round(smooth_mean, 6),
            "density_last": round(density, 4),
            "gamma_geo":    round(intern["gamma_geo"], 4),
            "gamma_mob":    round(intern["gamma_mob"], 4),
        })

        # Top-10 neighbors for key cities (last timestep of this fold)
        for city, ze_code in KEY_ZONES.items():
            zi = zone_idx_map.get(ze_code)
            if zi is None:
                continue
            row     = A_last[zi]
            top10i  = np.argsort(row)[::-1][:10]
            top10   = [{"rank": int(r+1),
                        "ze2020": int(zones_sorted[idx]),
                        "name":   ze_to_libze.get(int(zones_sorted[idx]), str(zones_sorted[idx])),
                        "weight": round(float(row[idx]), 5)}
                       for r, idx in enumerate(top10i) if row[idx] > 1e-6]
            key_zone_top10.setdefault(city, {})[int(yr)] = top10

    return diag_rows, smooth_by_fold, key_zone_top10


def compute_gate_diagnostics(internals_by_year, years_of_interest=(2019, 2020, 2021, 2022, 2024)):
    """Mean gate value per year (from last fold which has the longest sequence)."""
    last_intern = internals_by_year[max(internals_by_year)]
    gate_arr    = last_intern["gate_values"]  # (T, N, 1)
    years_f     = last_intern["years"]

    gate_by_year = {}
    for t, yr in enumerate(years_f):
        if int(yr) in years_of_interest:
            gate_by_year[int(yr)] = round(float(gate_arr[t].mean()), 5)
    return gate_by_year


# ─── report writer ────────────────────────────────────────────────────────────

def write_report(rows, args, internals_by_year, zones_sorted, node_idx_df):
    df      = pd.DataFrame(rows)
    metrics = []
    for (model, year), g in df.groupby(["model", "target_year"]):
        metrics.append({"model": model, "target_year": int(year),
                        "wmape": wmape(g["y_true"], g["y_pred"]), "n": len(g)})
    mdf        = pd.DataFrame(metrics)
    mean_wmape = float(mdf["wmape"].mean())

    ridge_ar      = 0.0668
    stgnn_v1      = 0.0610
    herald_v2_exp = 0.0271

    diag_rows, smooth_by_fold, key_zone_top10 = compute_adj_diagnostics(
        internals_by_year, zones_sorted, node_idx_df
    )
    gate_by_year = compute_gate_diagnostics(internals_by_year)

    run_key = f"{args.ablation}_seed_{args.seed}"
    result  = {
        "ablation":                    args.ablation,
        "seed":                        args.seed,
        "mean_wmape":                  round(mean_wmape, 6),
        "delta_vs_ridge_ar":           round(mean_wmape - ridge_ar, 6),
        "delta_vs_stgnn_v1":           round(mean_wmape - stgnn_v1, 6),
        "delta_vs_herald_v2_expanding":round(mean_wmape - herald_v2_exp, 6),
        "per_year":                    mdf.sort_values("target_year").to_dict(orient="records"),
        "adj_diagnostics":             diag_rows,
        "smooth_loss_by_fold":         smooth_by_fold,
        "gate_mean_by_year":           gate_by_year,
        "key_zone_top10_neighbors":    {
            city: {str(yr): t10 for yr, t10 in yr_data.items()}
            for city, yr_data in key_zone_top10.items()
        },
    }

    def _json_safe(obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        raise TypeError(f"Not JSON serializable: {type(obj)}")

    # Append to existing JSON (accumulate multiple runs)
    existing = {}
    if OUT_JSON.exists():
        existing = json.loads(OUT_JSON.read_text(encoding="utf-8"))
    existing[run_key] = result
    OUT_JSON.write_text(json.dumps(existing, indent=2, default=_json_safe),
                        encoding="utf-8")

    # Markdown report (overwrite — always shows all accumulated runs)
    lines = [
        "# HERALD V3 — Dynamic Adaptive Graph",
        "",
        "## Architecture",
        "- **V3 key change**: A_t computed per timestep inside GRUCell loop",
        "  (V2 computed adaptive_adj once before the loop — static).",
        "- e_t = relu(annual_proj(x_ann) + q_proj(quarterly_enc(x_q)) + h_proj(h_{t-1}))",
        "- A_t = topk_sparse_softmax(Q_t K_t^T / sqrt(d_k) + γ_geo·log(A_geo) + γ_mob·log(A_mob))",
        "- Gate: g_t = sigmoid(MLP([e_t, m_t, regime_t])) where regime_t = [covid, rebound, growth]",
        "- z_t = g_t * e_t + (1−g_t) * m_t  →  h_t = GRUCell(z_t, h_{t-1})",
        "- Regularization: λ_smooth · mean(||A_t − A_{t-1}||_F²)",
        "- Residual: final_pred = Ridge_AR_pred + neural_residual * zone_std",
        "",
        "## Results",
        "",
        "| Run | Mean WMAPE | vs Ridge AR | vs STGNN V1 | vs HERALD V2 exp |",
        "|---|---:|---:|---:|---:|",
        f"| Ridge AR baseline | {ridge_ar:.4f} | — | — | — |",
        f"| Dynamic STGNN V1  | {stgnn_v1:.4f} | {stgnn_v1-ridge_ar:+.4f} | — | — |",
        f"| HERALD V2 expanding (ref) | {herald_v2_exp:.4f} | {herald_v2_exp-ridge_ar:+.4f} | {herald_v2_exp-stgnn_v1:+.4f} | — |",
    ]
    for rk, rv in sorted(existing.items()):
        mw = rv["mean_wmape"]
        lines.append(
            f"| HERALD V3 {rk} | {mw:.4f} "
            f"| {mw-ridge_ar:+.4f} | {mw-stgnn_v1:+.4f} | {mw-herald_v2_exp:+.4f} |"
        )

    lines += [
        "",
        f"## Per-year WMAPE — {run_key}",
        "",
        "| Year | WMAPE | N |",
        "|---:|---:|---:|",
    ]
    for r in mdf.sort_values("target_year").itertuples(index=False):
        lines.append(f"| {r.target_year} | {r.wmape:.6f} | {r.n} |")

    lines += [
        "",
        "## Adjacency Diagnostics",
        "",
        "| Fold | Smooth Mean | Density (last t) | γ_geo | γ_mob |",
        "|---:|---:|---:|---:|---:|",
    ]
    for d in diag_rows:
        lines.append(
            f"| {d['target_year']} | {d['smooth_mean']:.6f} "
            f"| {d['density_last']:.4f} | {d['gamma_geo']:.4f} | {d['gamma_mob']:.4f} |"
        )

    if gate_by_year:
        lines += ["", "## Gate Diagnostics (mean gate value by year, last fold)", ""]
        lines += ["| Year | Mean g_t |", "|---:|---:|"]
        for yr in sorted(gate_by_year):
            lines.append(f"| {yr} | {gate_by_year[yr]:.5f} |")

    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"\n=== HERALD V3 ({run_key}) ===")
    print(f"Mean WMAPE:             {mean_wmape:.6f}")
    print(f"Delta vs Ridge AR:      {mean_wmape - ridge_ar:+.6f}")
    print(f"Delta vs STGNN V1:      {mean_wmape - stgnn_v1:+.6f}")
    print(f"Delta vs HERALD V2 exp: {mean_wmape - herald_v2_exp:+.6f}")
    print()
    print(mdf.sort_values("target_year").to_string(index=False))

    if gate_by_year:
        print("\nGate means by year (last fold):", gate_by_year)


# ─── main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="HERALD V3 — Dynamic Adaptive Graph")
    parser.add_argument("--epochs",             type=int,   default=800)
    parser.add_argument("--hidden-dim",         type=int,   default=32)
    parser.add_argument("--q-hidden",           type=int,   default=16)
    parser.add_argument("--attn-dim",           type=int,   default=8)
    parser.add_argument("--top-k",              type=int,   default=10)
    parser.add_argument("--prior-strength-init",type=float, default=1.0)
    parser.add_argument("--lr",                 type=float, default=1e-3)
    parser.add_argument("--weight-decay",       type=float, default=1e-4)
    parser.add_argument("--huber-delta",        type=float, default=300.0)
    parser.add_argument("--grad-clip",          type=float, default=5.0)
    parser.add_argument("--smooth-lambda",      type=float, default=0.1,
                        help="Weight for temporal smoothness regularization ||A_t - A_{t-1}||_F^2")
    parser.add_argument("--sector-lambda",      type=float, default=0.1)
    parser.add_argument("--seed",               type=int,   default=0)
    parser.add_argument("--device",
                        default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--ablation",           default="full",
                        choices=[
                            "full",
                            "self_only",
                            "fixed_geo_mob_only",
                            "static_adaptive",
                            "dynamic_adaptive_no_quarterly",
                            "dynamic_adaptive_no_regime",
                            "dynamic_adaptive_no_smooth",
                        ])
    args = parser.parse_args()

    set_seed(args.seed)
    device = torch.device(args.device)

    print("Loading data...")
    panel      = pd.read_csv(PANEL_PATH).sort_values(["target_year","ZE2020"]).reset_index(drop=True)
    splits     = pd.read_csv(SPLITS_PATH)
    node_idx_df= pd.read_csv(NODE_IDX_PATH)
    cols       = feature_columns(panel, ablation=args.ablation)
    adj_geo    = load_adjacency(GEO_ADJ_PATH)
    adj_mob    = load_adjacency(MOB_ADJ_PATH)

    zones_sorted = sorted(panel["ZE2020"].unique())
    years_sorted = sorted(panel["target_year"].unique())

    print("Building quarterly tensor...")
    q_tensor      = build_quarterly_tensor(zones_sorted, years_sorted)
    sector_tensor = build_sector_target(panel, zones_sorted, years_sorted)
    print(f"  Quarterly tensor: {q_tensor.shape}")
    print(f"  Sector tensor:    {sector_tensor.shape}")
    print(f"  Annual features:  {len(cols)}")
    print(f"  Ablation:         {args.ablation}")
    print(f"  Device:           {device}")

    print(f"\nTraining HERALD V3 (ablation={args.ablation}, seed={args.seed})...")
    rows, internals_by_year = evaluate_herald_v3(
        panel, splits, cols, q_tensor, sector_tensor,
        zones_sorted, years_sorted, adj_geo, adj_mob, args, device,
    )

    pred   = pd.DataFrame(rows)
    suffix = f"{args.ablation}_seed_{args.seed}"

    out_pred      = PROCESSED / f"herald_v3_predictions_{suffix}_v1.csv"
    out_internals = PROCESSED / f"herald_v3_internals_{suffix}_v1.npz"
    out_history   = REPORTS / f"herald_v3_training_history_{suffix}_v1.csv"

    pred.to_csv(out_pred, index=False)

    history_rows = []
    for target_year, intern in sorted(internals_by_year.items()):
        for item in intern.get("training_history", []):
            history_rows.append({
                "ablation": args.ablation,
                "seed": args.seed,
                "target_year": int(target_year),
                **item,
            })
    pd.DataFrame(history_rows).to_csv(out_history, index=False)

    # Save internals from the last fold (longest sequence: train + test 2024)
    last = internals_by_year[max(internals_by_year)]
    np.savez_compressed(
        out_internals,
        dynamic_adj            = last["dynamic_adj"],             # (T, N, N)
        gate_values            = last["gate_values"],             # (T, N, 1)
        gamma_geo              = np.array([last["gamma_geo"]]),
        gamma_mob              = np.array([last["gamma_mob"]]),
        smooth_loss_inference  = np.array([last["smooth_loss_inference"]]),
        years                  = np.array(last["years"]),
        node_order             = np.array(last["node_order"]),
    )

    write_report(rows, args, internals_by_year, zones_sorted, node_idx_df)

    print(f"\nSaved: {out_pred}")
    print(f"Saved: {out_internals}")
    print(f"Saved: {out_history}")
    print(f"Saved: {OUT_JSON}")
    print(f"Saved: {OUT_MD}")


if __name__ == "__main__":
    main()
