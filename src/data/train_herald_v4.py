"""
HERALD V4 — Sectoral Dynamic Graph for Territorial Economic Forecasting
Revision: per-sector GRU backbone + sector embedding gate + sector AR lags

Architecture (revised — fixes V4.0 bottleneck):

1. Per-sector independent GRU cells (n_sectors × GRUCell(H_s, H_s)):
   Each sector has its own hidden state h_s that evolves independently.
   Eliminates the sector_agg bottleneck where 9×H was crushed to H.

2. Sector embedding in gate:
   gate_in_s = concat([e_s, m_s, h_s, regime_t, sector_emb_s])
   Each sector gets a unique identity embedding (dim=8), enabling the shared
   gate MLP to learn genuinely different self/neighbor balance per sector.

3. Ridge baseline with sector-specific AR lags:
   For sector s, Ridge features include lag_1_s = creations of s at t-1,
   in addition to total AR lags. Stronger baseline → cleaner neural residual.

4. Shared node embedding from mean sector context:
   h_ctx = mean(h over sectors) → h_ctx_proj → H
   e_t   = relu(proj_e(concat([ann, q_enc, h_ctx])))
   The adjacency A_t uses the overall economic state (mean across sectors),
   while each sector's gate uses its own per-sector hidden state.

Flow per timestep t:
  h: (9, N, H_s)  — per-sector hidden states
  h_ctx = mean(h, dim=0) → proj → H
  e_t   = relu(proj_e([ann, q_enc, h_ctx]))        (N, H) shared
  A_t   = topk_softmax(Q K^T/√d + regime_shift + prior)
  m_t   = msg_proj(A_t @ e_t)                       (N, H) shared
  e_s   = proj_self(e_t)                            (N, H_s) shared
  m_s   = proj_msg_(m_t)                            (N, H_s) shared
  For each sector s:
    g_s  = sigmoid(gate_mlp([e_s, m_s, h[s], regime, sector_emb[s]]))
    z_s  = g_s * e_s + (1−g_s) * m_s
    h[s] = GRUCell_s(z_s, h[s])
    pred_s = decoder_s(h[s])

V3 outputs NOT overwritten. All V4 outputs use _v4_ prefix:
  data/processed/herald_v4_predictions_{ablation}_seed_{seed}_v1.csv
  data/processed/herald_v4_internals_{ablation}_seed_{seed}_v1.npz
  reports/herald_v4_metrics_v1.json
  reports/HERALD_V4_MODEL_V1.md
"""

import argparse
import json
import zipfile
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
SIDE_ZIP   = ROOT / "data/raw/business_demography/side/DS_SIDE_CREA_ETAB_COM_2024_CSV_FR.zip"

PANEL_PATH       = PROCESSED / "dynamic_stgnn_feature_panel_v1.csv"
SPLITS_PATH      = METADATA  / "dynamic_stgnn_walk_forward_splits_v1.csv"
GEO_ADJ_PATH     = PROCESSED / "graph_adjacency_core_v0.csv"
MOB_ADJ_PATH     = PROCESSED / "graph_adjacency_mobility_v0.csv"
NODE_IDX_PATH    = PROCESSED / "graph_node_index_core_v0.csv"
SIDE_A10_PATH    = PROCESSED / "side_creations_a10_ze2020_v1.csv"

OUT_JSON = REPORTS / "herald_v4_metrics_v1.json"
OUT_MD   = REPORTS / "HERALD_V4_MODEL_V1.md"

TARGET_COL    = "side_establishment_creations_official"
A10_SECTORS   = ["BE", "FZ", "GI", "JZ", "KZ", "LZ", "MN", "OQ", "RU"]
REGIME_DIM    = 3   # [is_covid_year, is_post_covid_rebound, global_growth_norm]
                    # EXCLUSIVE: covid/rebound NOT in annual features

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


# ─── SIDE A10 sectoral panel ───────────────────────────────────────────────────

def load_or_build_side_a10_panel(zones_sorted):
    """
    Build or load sectoral establishment creations per ZE2020 × year.
    Source: DS_SIDE_CREA_ETAB_COM_2024, filtered to ZE2020 + all legal forms.
    Output columns: target_year, ZE2020, BE, FZ, GI, JZ, KZ, LZ, MN, OQ, RU, total
    """
    if SIDE_A10_PATH.exists():
        return pd.read_csv(SIDE_A10_PATH)

    print("  Building SIDE A10 panel from source ZIP (first run only)...")
    zone_set = set(zones_sorted)

    with zipfile.ZipFile(SIDE_ZIP) as zf:
        fname = [f for f in zf.namelist() if f.endswith("_data.csv")][0]
        with zf.open(fname) as f:
            raw = pd.read_csv(f, sep=";", encoding="latin1",
                              usecols=["ACTIVITY","GEO_OBJECT","GEO",
                                       "LEGAL_FORM","SIDE_MEASURE","TIME_PERIOD","OBS_VALUE"])

    df = raw[
        (raw["GEO_OBJECT"] == "ZE2020") &
        (raw["LEGAL_FORM"] == "_T") &
        (raw["SIDE_MEASURE"] == "UNIT_LOC_BURE") &
        (raw["ACTIVITY"].isin(A10_SECTORS + ["_T"]))
    ].copy()

    df["ZE2020"] = df["GEO"].astype(int)
    df = df[df["ZE2020"].isin(zone_set)]
    df = df.rename(columns={"TIME_PERIOD": "target_year", "OBS_VALUE": "creations"})
    df["creations"] = pd.to_numeric(df["creations"], errors="coerce").fillna(0).astype(int)

    pivot = df.pivot_table(
        index=["target_year", "ZE2020"],
        columns="ACTIVITY",
        values="creations",
        aggfunc="sum",
        fill_value=0,
    ).reset_index()
    pivot.columns.name = None

    # Ensure all sectors present
    for s in A10_SECTORS:
        if s not in pivot.columns:
            pivot[s] = 0

    pivot["total"] = pivot[A10_SECTORS].sum(axis=1)
    out = pivot[["target_year", "ZE2020"] + A10_SECTORS + ["total"]].copy()
    out = out.sort_values(["target_year", "ZE2020"]).reset_index(drop=True)
    out.to_csv(SIDE_A10_PATH, index=False)
    print(f"  Saved: {SIDE_A10_PATH}")
    return out


# ─── Ridge AR per sector ───────────────────────────────────────────────────────

def fit_ridge_ar_sector(train_df, test_df, sector):
    """
    Ridge for one sector. Features:
    - Total AR lags (side_lag_1/2/3, growth_1y/2y)
    - Sector stock (side_stock_{sector}_t_minus_1)
    - Sector-specific AR lag (lag1_{sector}) — new: stronger sector-level signal
    """
    ar_cols   = [c for c in ["side_lag_1","side_lag_2","side_lag_3","growth_1y","growth_2y"]
                 if c in train_df.columns]
    stk_col   = f"side_stock_{sector.lower()}_t_minus_1"
    sec_lag   = f"lag1_{sector}"
    feat_cols = (ar_cols
                 + ([stk_col]  if stk_col  in train_df.columns else [])
                 + ([sec_lag]  if sec_lag  in train_df.columns else []))

    tr = train_df.dropna(subset=[sector])
    te = test_df.dropna(subset=[sector])
    if len(tr) < 10 or len(te) == 0:
        return np.zeros(len(te))

    m = Pipeline([("imp", SimpleImputer(strategy="median")),
                  ("sc",  StandardScaler()),
                  ("r",   Ridge(alpha=1.0))])
    m.fit(tr[feat_cols].values.astype(float), tr[sector].values.astype(float))
    return np.maximum(m.predict(te[feat_cols].values.astype(float)), 0.0)


def fit_ridge_sectors_expanding(train_df_all, pred_year, min_years=3):
    """Expanding Ridge per sector: train only on years < pred_year."""
    holdout = train_df_all[train_df_all["target_year"] == pred_year].copy()
    fit_df  = train_df_all[train_df_all["target_year"] < pred_year].copy()
    if fit_df["target_year"].nunique() < min_years or len(holdout) == 0:
        return holdout, {s: np.full(len(holdout), np.nan) for s in A10_SECTORS}

    preds = {}
    for s in A10_SECTORS:
        preds[s] = fit_ridge_ar_sector(fit_df, holdout, s)
    return holdout, preds


# ─── quarterly tensor (same as V3) ────────────────────────────────────────────

def build_quarterly_tensor(zones_sorted, years_sorted):
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


def build_sector_tensor(a10_panel, zones_sorted, years_sorted):
    """Build (T, N, 9) tensor of A10 sectoral creations."""
    T, N, S = len(years_sorted), len(zones_sorted), len(A10_SECTORS)
    out = np.full((T, N, S), np.nan, dtype=np.float32)
    zone_to_idx = {z: i for i, z in enumerate(zones_sorted)}
    year_to_idx = {y: i for i, y in enumerate(years_sorted)}

    for row in a10_panel.itertuples(index=False):
        yr, ze = int(row.target_year), int(row.ZE2020)
        if yr not in year_to_idx or ze not in zone_to_idx:
            continue
        ti, zi = year_to_idx[yr], zone_to_idx[ze]
        out[ti, zi] = [float(getattr(row, s, 0.0)) for s in A10_SECTORS]
    return out


# ─── regime vectors (exclusive: no covid/rebound in annual features) ───────────

def build_regime_vectors(panel, years_sorted, train_max):
    """
    (T, 3): [is_covid_year, is_post_covid_rebound, global_growth_norm]
    V4: these flags are EXCLUSIVE to regime_t — removed from annual features.
    """
    T = len(years_sorted)
    year_to_idx = {y: i for i, y in enumerate(years_sorted)}

    agg = (panel.groupby("target_year")
           .agg(is_covid=("is_covid_year","first"),
                is_rebound=("is_post_covid_rebound","first"),
                mean_lag1=("side_lag_1","mean"))
           .reset_index().sort_values("target_year").reset_index(drop=True))

    agg["global_growth"] = agg["mean_lag1"].pct_change().fillna(0.0)
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


# ─── HERALD V4 architecture ────────────────────────────────────────────────────

class QuarterlyEncoder(nn.Module):
    def __init__(self, in_dim=2, hidden_dim=16):
        super().__init__()
        self.gru = nn.GRU(in_dim, hidden_dim, batch_first=True)

    def forward(self, x):
        _, h = self.gru(x)
        return h.squeeze(0)


def topk_sparse_softmax(logits: torch.Tensor, k: int) -> torch.Tensor:
    k = min(k, logits.shape[-1])
    topk_vals, topk_idx = torch.topk(logits, k, dim=-1)
    sparse = torch.full_like(logits, float("-inf"))
    sparse.scatter_(-1, topk_idx, topk_vals)
    out = torch.softmax(sparse, dim=-1)
    return torch.nan_to_num(out, nan=0.0)


class HERALDv4Residual(nn.Module):
    """
    HERALD V4 (revised): Per-sector GRU backbone + sector embedding gate.

    Each sector has its own GRUCell(H_s, H_s) hidden state that evolves
    independently. The gate is conditioned on per-sector state + sector
    identity embedding — genuine differentiation without bottleneck compression.
    """

    SECTOR_EMB_DIM = 8

    def __init__(self, num_nodes, annual_dim, hidden_dim, sector_hidden,
                 n_sectors=9, attn_dim=8, q_hidden=16,
                 top_k=10, prior_strength_init=1.0):
        super().__init__()
        self.num_nodes     = num_nodes
        self.hidden_dim    = hidden_dim     # H — shared embedding dimension
        self.sector_hidden = sector_hidden  # H_s — per-sector GRU dimension
        self.n_sectors     = n_sectors
        self.attn_dim      = attn_dim
        self.top_k         = top_k
        H, H_s, E = hidden_dim, sector_hidden, self.SECTOR_EMB_DIM

        # ── shared input encoders ─────────────────────────────────────────
        self.quarterly_enc = QuarterlyEncoder(in_dim=2, hidden_dim=q_hidden)
        self.q_proj        = nn.Linear(q_hidden, H)
        self.annual_proj   = nn.Linear(annual_dim, H)

        # h_context: mean of per-sector states → H for shared embedding
        self.h_ctx_proj = nn.Linear(H_s, H)
        # Node embedding: concat([ann(H), q_enc(H), h_ctx(H)]) → H
        self.proj_e     = nn.Linear(H * 3, H)

        # ── dynamic adjacency ─────────────────────────────────────────────
        self.regime_to_query = nn.Linear(REGIME_DIM, attn_dim)
        self.proj_Q = nn.Linear(H, attn_dim)
        self.proj_K = nn.Linear(H, attn_dim)

        self.gamma_geo = nn.Parameter(torch.tensor(float(prior_strength_init)))
        self.gamma_mob = nn.Parameter(torch.tensor(float(prior_strength_init)))

        # Static adaptive embeddings (static_adaptive ablation only)
        self.static_emb_1 = nn.Parameter(torch.empty(num_nodes, attn_dim))
        self.static_emb_2 = nn.Parameter(torch.empty(attn_dim, num_nodes))
        nn.init.orthogonal_(self.static_emb_1)
        nn.init.orthogonal_(self.static_emb_2)

        # ── shared message + mixing projections (H → H_s) ─────────────────
        self.msg_proj  = nn.Linear(H, H)     # message in shared space
        self.proj_self = nn.Linear(H, H_s)   # project shared embed → sector space
        self.proj_msg_ = nn.Linear(H, H_s)   # project shared message → sector space

        # ── sector identity embedding ─────────────────────────────────────
        self.sector_emb = nn.Embedding(n_sectors, E)

        # ── sector gate (shared MLP, differentiated via sector embedding + h_s) ─
        # Input: [e_s(H_s), m_s(H_s), h_s(H_s), regime(R), sector_emb(E)]
        gate_dim = H_s + H_s + H_s + REGIME_DIM + E
        self.sector_gate_mlp = nn.Sequential(
            nn.Linear(gate_dim, H),
            nn.ReLU(),
            nn.Linear(H, 1),
        )
        nn.init.constant_(self.sector_gate_mlp[-1].bias, -1.0)

        # Global gate for no_sector_gate ablation (no sector embedding, no h_s)
        # Input: [e_s(H_s), m_s(H_s), regime(R)]
        global_gate_dim = H_s + H_s + REGIME_DIM
        self.global_gate_mlp = nn.Sequential(
            nn.Linear(global_gate_dim, H),
            nn.ReLU(),
            nn.Linear(H, 1),
        )
        nn.init.constant_(self.global_gate_mlp[-1].bias, -1.0)

        # ── per-sector temporal backbone ──────────────────────────────────
        # Each sector has its own GRUCell and output decoder
        self.gru_cells = nn.ModuleList(
            [nn.GRUCell(H_s, H_s) for _ in range(n_sectors)]
        )
        self.decoders = nn.ModuleList(
            [nn.Linear(H_s, 1) for _ in range(n_sectors)]
        )

    # ── adjacency helpers ─────────────────────────────────────────────────────

    def _static_adj(self):
        return torch.softmax(
            torch.relu(self.static_emb_1 @ self.static_emb_2), dim=1
        )

    def _dynamic_adj(self, e_t, prior_logits, regime_t):
        regime_shift = self.regime_to_query(regime_t)
        Q = self.proj_Q(e_t) + regime_shift.unsqueeze(0)
        K = self.proj_K(e_t)
        raw = (Q @ K.T) / (self.attn_dim ** 0.5)
        return topk_sparse_softmax(raw + prior_logits, self.top_k)

    # ── forward ───────────────────────────────────────────────────────────────

    def forward(self, x_annual_seq, x_quarterly_seq, regime_seq,
                adj_geo, adj_mob, adj_log_geo, adj_log_mob,
                ablation="full", return_internals=False):
        """
        x_annual_seq:    list[T] of (N, F_ann)
        x_quarterly_seq: list[T] of (N, 3, 2)
        regime_seq:      list[T] of (REGIME_DIM,)
        ablation: full | self_only | fixed_geo_mob_only | static_adaptive |
                  no_sector_gate | no_quarterly | no_regime | no_smooth
        """
        N      = self.num_nodes
        device = next(self.parameters()).device
        H_s    = self.sector_hidden

        # Per-sector hidden states: (n_sectors, N, H_s)
        h = torch.zeros(self.n_sectors, N, H_s, device=device)

        prior_logits = self.gamma_geo * adj_log_geo + self.gamma_mob * adj_log_mob
        static_adj_m = self._static_adj()
        fixed_blend  = 0.5 * adj_geo + 0.5 * adj_mob

        # Precompute sector embeddings: (n_sectors, E)
        sec_idx  = torch.arange(self.n_sectors, device=device)
        sec_embs = self.sector_emb(sec_idx)  # (9, E)

        pred_list, adj_list, gate_list = [], [], []
        smooth_loss = torch.tensor(0.0, device=device)
        n_smooth    = 0
        A_prev      = None

        for x_ann, x_q, regime_t in zip(x_annual_seq, x_quarterly_seq, regime_seq):
            regime_exp = regime_t.unsqueeze(0).expand(N, -1)  # (N, R)

            # ── 1. Shared node embedding ──────────────────────────────────
            ann = F.relu(self.annual_proj(x_ann))

            if ablation == "no_quarterly":
                q_enc = torch.zeros_like(ann)
            else:
                q_enc = F.relu(self.q_proj(self.quarterly_enc(x_q)))

            # Mean sector state → shared temporal context
            h_ctx = F.relu(self.h_ctx_proj(h.mean(dim=0)))  # (N, H)
            e_t   = F.relu(self.proj_e(torch.cat([ann, q_enc, h_ctx], dim=-1)))

            # ── 2. Dynamic adjacency ──────────────────────────────────────
            if ablation == "self_only":
                A_t = None
                m_t = e_t
            elif ablation == "fixed_geo_mob_only":
                A_t = fixed_blend
                m_t = self.msg_proj(A_t @ e_t)
            elif ablation == "static_adaptive":
                A_t = static_adj_m
                m_t = self.msg_proj(A_t @ e_t)
            else:
                regime_for_adj = (torch.zeros_like(regime_t)
                                  if ablation == "no_regime" else regime_t)
                A_t = self._dynamic_adj(e_t, prior_logits, regime_for_adj)
                m_t = self.msg_proj(A_t @ e_t)

            # ── 3. Temporal smoothness ────────────────────────────────────
            if A_t is not None and A_prev is not None and ablation != "no_smooth":
                smooth_loss = smooth_loss + torch.sum((A_t - A_prev) ** 2)
                n_smooth += 1

            # ── 4. Shared projections to sector space ─────────────────────
            e_s = self.proj_self(e_t)   # (N, H_s)
            m_s = self.proj_msg_(m_t)   # (N, H_s)

            regime_for_gate = (torch.zeros_like(regime_exp)
                               if ablation == "no_regime" else regime_exp)

            # ── 5. Per-sector GRU update ──────────────────────────────────
            new_h         = []
            sector_preds  = []
            sector_gates  = []

            for s in range(self.n_sectors):
                h_s = h[s]  # (N, H_s)

                if ablation == "self_only":
                    g_s = torch.ones(N, 1, device=device)
                    z_s = e_s
                elif ablation == "no_sector_gate":
                    # Shared global gate — no sector embedding, no per-sector h
                    gin = torch.cat([e_s, m_s, regime_for_gate], dim=-1)
                    g_s = torch.sigmoid(self.global_gate_mlp(gin))  # (N, 1)
                    z_s = g_s * e_s + (1.0 - g_s) * m_s
                else:
                    # Sector-specific gate: conditioned on sector embedding + h_s
                    sec_emb_exp = sec_embs[s].unsqueeze(0).expand(N, -1)  # (N, E)
                    gin = torch.cat([e_s, m_s, h_s, regime_for_gate, sec_emb_exp], dim=-1)
                    g_s = torch.sigmoid(self.sector_gate_mlp(gin))  # (N, 1)
                    z_s = g_s * e_s + (1.0 - g_s) * m_s

                h_s_new = self.gru_cells[s](z_s, h_s)          # (N, H_s)
                pred_s  = self.decoders[s](h_s_new)             # (N, 1)

                new_h.append(h_s_new)
                sector_preds.append(pred_s)
                sector_gates.append(g_s)

            h = torch.stack(new_h, dim=0)  # (9, N, H_s)

            pred  = torch.cat(sector_preds, dim=-1)   # (N, 9)
            gates = torch.cat(sector_gates, dim=-1)   # (N, 9)
            pred_list.append(pred)

            if return_internals:
                A_store = A_t if A_t is not None else torch.eye(N, device=device)
                adj_list.append(A_store.detach())
                gate_list.append(gates.detach())

            A_prev = A_t

        if n_smooth > 0:
            smooth_loss = smooth_loss / n_smooth

        preds = torch.stack(pred_list, dim=0)   # (T, N, 9)

        if return_internals:
            adj_tensor  = torch.stack(adj_list,  dim=0)  # (T, N, N)
            gate_tensor = torch.stack(gate_list, dim=0)  # (T, N, 9)
            return preds, smooth_loss, adj_tensor, gate_tensor

        return preds, smooth_loss


# ─── feature columns (V4: excludes covid/rebound — exclusive to regime_t) ─────

def feature_columns_v4(panel, ablation="full"):
    base   = ["side_lag_1","side_lag_2","side_lag_3","growth_1y","growth_2y"]
    flores = [c for c in panel.columns
              if c.startswith("flores_") and c.endswith("_t_minus_1")
              and "etab_" not in c]
    side   = [c for c in panel.columns
              if c.startswith("side_stock_") and c.endswith("_t_minus_1")]
    flags  = ["has_flores_source","has_side_stock_source","has_urssaf_source"]
    # NOTE: is_covid_year and is_post_covid_rebound EXCLUDED — in regime_t only

    if ablation == "no_quarterly":
        urssaf = [c for c in panel.columns
                  if c.startswith("urssaf_") and c.endswith("_t_minus_1")]
    else:
        urssaf = []

    cols = base + flores + side + urssaf + flags
    return [c for c in cols if c in panel.columns]


# ─── sequence builder ─────────────────────────────────────────────────────────

def make_sequences_v4(panel, a10_panel, cols, q_tensor,
                      zones_sorted, years_sorted, train_max, target_year, args):
    year_to_idx  = {y: i for i, y in enumerate(years_sorted)}
    t_train_idx  = [year_to_idx[y] for y in years_sorted if y <= train_max]
    t_full_idx   = [year_to_idx[y] for y in years_sorted if y <= target_year]
    test_idx     = year_to_idx[target_year]
    zone_to_idx  = {z: i for i, z in enumerate(zones_sorted)}

    x_annual, y_total = build_annual_tensor(panel, cols, zones_sorted, years_sorted)
    sector_tensor     = build_sector_tensor(a10_panel, zones_sorted, years_sorted)

    # ── Ridge per sector (expanding) ────────────────────────────────────────
    # Build sector-specific lag features: lag1_{s} = creations of s at t-1
    a10_lagged = a10_panel[["target_year","ZE2020"] + A10_SECTORS].copy()
    a10_lagged["target_year"] = a10_lagged["target_year"] + 1  # shift: lag value
    a10_lagged = a10_lagged.rename(columns={s: f"lag1_{s}" for s in A10_SECTORS})

    # Merge: annual features + sector targets + sector lags
    merged = (panel[["target_year","ZE2020"] + [c for c in cols if c in panel.columns]]
              .merge(a10_panel[["target_year","ZE2020"] + A10_SECTORS],
                     on=["target_year","ZE2020"], how="left")
              .merge(a10_lagged, on=["target_year","ZE2020"], how="left"))

    train_df_all = merged[merged["target_year"] <= train_max].copy()
    test_df      = merged[merged["target_year"] == target_year].copy()

    # Ridge per sector for test year
    ridge_test_s = {}
    for s in A10_SECTORS:
        ridge_test_s[s] = fit_ridge_ar_sector(train_df_all, test_df, s)

    # Ridge per sector for each training year (expanding)
    ridge = np.full((len(years_sorted), len(zones_sorted), len(A10_SECTORS)),
                    np.nan, dtype=np.float32)
    for pred_year in sorted(train_df_all["target_year"].unique()):
        holdout, preds_s = fit_ridge_sectors_expanding(train_df_all, int(pred_year))
        for s_idx, s in enumerate(A10_SECTORS):
            rp = preds_s[s]
            for row, p in zip(holdout.itertuples(index=False), rp):
                if np.isfinite(p):
                    ridge[year_to_idx[int(row.target_year)],
                          zone_to_idx[int(row.ZE2020)], s_idx] = p

    for s_idx, s in enumerate(A10_SECTORS):
        rp = ridge_test_s[s]
        for row, p in zip(test_df.itertuples(index=False), rp):
            ridge[test_idx, zone_to_idx[int(row.ZE2020)], s_idx] = p

    # ── Annual feature normalization ─────────────────────────────────────────
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

    # ── Quarterly normalization ──────────────────────────────────────────────
    q_norm, _, _ = normalize_quarterly(q_tensor, t_train_idx)
    q_train = q_norm[t_train_idx]
    q_full  = q_norm[t_full_idx]

    # ── Sector residuals and normalization ───────────────────────────────────
    # sector_tensor: (T, N, 9) — actual creations
    # ridge: (T, N, 9) — Ridge predictions
    train_y_s = sector_tensor[t_train_idx]            # (T_train, N, 9)
    train_r_s = ridge[t_train_idx]                    # (T_train, N, 9)

    # Zone-sector std: (N, 9) — from train residuals
    train_resid_raw = train_y_s - train_r_s           # (T_train, N, 9)
    zone_sector_std = np.nanstd(train_resid_raw, axis=0)  # (N, 9)
    zone_sector_std = np.where(zone_sector_std < 1.0, 1.0, zone_sector_std)

    train_resid = train_resid_raw / zone_sector_std[np.newaxis, :, :]
    mask_s      = np.isfinite(train_resid).astype(np.float32)
    train_resid = np.nan_to_num(train_resid, nan=0.0).astype(np.float32)

    # Volume weights: (N, 9) — zone-sector mean normalised by global sector mean
    zone_sector_mean = np.nanmean(train_y_s, axis=0)  # (N, 9)
    global_sector_mean = np.nanmean(train_y_s, axis=(0, 1))  # (9,)
    global_sector_mean = np.where(global_sector_mean < 1.0, 1.0, global_sector_mean)
    zone_sector_weight = zone_sector_mean / global_sector_mean[np.newaxis, :]
    zone_sector_weight = np.clip(zone_sector_weight, 0.1, 10.0)

    # Sector volume weight: (9,) — how much each sector contributes to total loss
    sector_vol_total = np.nansum(train_y_s, axis=(0, 1))  # (9,)
    sector_vol_total = np.where(sector_vol_total < 1.0, 1.0, sector_vol_total)
    sector_vol_weight = sector_vol_total / sector_vol_total.sum()  # (9,) sums to 1

    # Regime vectors
    regime_all   = build_regime_vectors(panel, years_sorted, train_max)
    regime_train = regime_all[t_train_idx]
    regime_full  = regime_all[t_full_idx]

    return {
        "zones":               zones_sorted,
        "years_full":          [y for y in years_sorted if y <= target_year],
        "x_ann_train":         x_ann_train.astype(np.float32),
        "x_ann_full":          x_ann_full.astype(np.float32),
        "q_train":             q_train.astype(np.float32),
        "q_full":              q_full.astype(np.float32),
        "regime_train":        regime_train.astype(np.float32),
        "regime_full":         regime_full.astype(np.float32),
        "train_resid":         train_resid,          # (T_train, N, 9)
        "mask_s":              mask_s,               # (T_train, N, 9)
        "zone_sector_weight":  zone_sector_weight.astype(np.float32),  # (N, 9)
        "sector_vol_weight":   sector_vol_weight.astype(np.float32),   # (9,)
        "zone_sector_std":     zone_sector_std.astype(np.float32),     # (N, 9)
        "test_y_s":            sector_tensor[test_idx],   # (N, 9)
        "test_ridge_s":        ridge[test_idx],           # (N, 9)
        "test_mask_s":         (np.isfinite(sector_tensor[test_idx]) &
                                np.isfinite(ridge[test_idx])).all(axis=-1),  # (N,)
        "target_year":         target_year,
    }


# ─── training ─────────────────────────────────────────────────────────────────

def train_herald_v4(seq, adj_geo, adj_mob, args, device):
    N          = len(seq["zones"])
    annual_dim = seq["x_ann_train"].shape[-1]

    model = HERALDv4Residual(
        num_nodes=N,
        annual_dim=annual_dim,
        hidden_dim=args.hidden_dim,
        sector_hidden=args.sector_hidden,
        n_sectors=len(A10_SECTORS),
        attn_dim=args.attn_dim,
        q_hidden=args.q_hidden,
        top_k=args.top_k,
        prior_strength_init=args.prior_strength_init,
    ).to(device)

    opt   = torch.optim.AdamW(model.parameters(), lr=args.lr,
                               weight_decay=args.weight_decay)
    huber = nn.HuberLoss(delta=args.huber_delta, reduction="none")

    x_ann    = torch.tensor(seq["x_ann_train"],        device=device)
    x_q      = torch.tensor(seq["q_train"],            device=device)
    regime   = torch.tensor(seq["regime_train"],       device=device)
    target   = torch.tensor(seq["train_resid"],        device=device)  # (T, N, 9)
    mask_s   = torch.tensor(seq["mask_s"],             device=device)  # (T, N, 9)
    zs_w     = torch.tensor(seq["zone_sector_weight"], device=device)  # (N, 9)
    sv_w     = torch.tensor(seq["sector_vol_weight"],  device=device)  # (9,)

    adj_g     = torch.tensor(adj_geo, device=device)
    adj_m_t   = torch.tensor(adj_mob, device=device)
    eps       = 1e-6
    adj_log_g = torch.log(adj_g   + eps)
    adj_log_m = torch.log(adj_m_t + eps)

    T        = x_ann.shape[0]
    ablation = args.ablation

    model.train()
    for ep in range(args.epochs):
        opt.zero_grad()

        ann_list = [x_ann[t]              for t in range(T)]
        q_list   = [x_q[t].permute(1,0,2) for t in range(T)]
        reg_list = [regime[t]             for t in range(T)]

        preds, smooth_loss = model(
            ann_list, q_list, reg_list,
            adj_g, adj_m_t, adj_log_g, adj_log_m,
            ablation=ablation, return_internals=False,
        )
        # preds: (T, N, 9)

        # Volume-weighted Huber loss per sector, aggregated by sector volume
        # zs_w broadcast: (1, N, 9), sv_w: (1, 1, 9)
        zs_w_bc = zs_w.unsqueeze(0)                   # (1, N, 9)
        sv_w_bc = sv_w.unsqueeze(0).unsqueeze(0)       # (1, 1, 9)

        per_elem = huber(preds, target) * mask_s * zs_w_bc  # (T, N, 9)
        denom    = torch.clamp((mask_s * zs_w_bc).sum(dim=(0,1)), min=1.0)  # (9,)
        loss_per_sector = per_elem.sum(dim=(0,1)) / denom   # (9,)
        loss_main = (loss_per_sector * sv_w).sum()           # scalar

        loss = loss_main + args.smooth_lambda * smooth_loss
        loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), args.grad_clip)
        opt.step()

    # ── Inference on full sequence ───────────────────────────────────────────
    model.eval()
    with torch.no_grad():
        x_ann_f = torch.tensor(seq["x_ann_full"],  device=device)
        x_q_f   = torch.tensor(seq["q_full"],      device=device)
        reg_f   = torch.tensor(seq["regime_full"], device=device)
        T_full  = x_ann_f.shape[0]

        ann_f  = [x_ann_f[t]              for t in range(T_full)]
        q_f    = [x_q_f[t].permute(1,0,2) for t in range(T_full)]
        reg_fl = [reg_f[t]                for t in range(T_full)]

        preds_f, smooth_f, adj_t, gate_t = model(
            ann_f, q_f, reg_fl,
            adj_g, adj_m_t, adj_log_g, adj_log_m,
            ablation=ablation, return_internals=True,
        )

    internals = {
        "dynamic_adj":           adj_t.cpu().numpy(),   # (T, N, N)
        "sector_gates":          gate_t.cpu().numpy(),  # (T, N, 9)
        "gamma_geo":             float(model.gamma_geo.item()),
        "gamma_mob":             float(model.gamma_mob.item()),
        "smooth_loss_inference": float(smooth_f.item()),
        "years":                 seq["years_full"],
        "node_order":            seq["zones"],
    }
    return preds_f[-1].cpu().numpy(), internals  # (N, 9)


# ─── evaluation loop ──────────────────────────────────────────────────────────

def evaluate_herald_v4(panel, a10_panel, splits, cols, q_tensor,
                       zones_sorted, years_sorted, adj_geo, adj_mob, args, device):
    rows, internals_by_year = [], {}

    for _, split in splits.iterrows():
        target_year = int(split["target_year"])
        train_max   = int(split["train_years_max"])
        print(f"  Fold {target_year}...", flush=True)

        seq = make_sequences_v4(panel, a10_panel, cols, q_tensor,
                                zones_sorted, years_sorted, train_max,
                                target_year, args)

        resid_s, internals = train_herald_v4(seq, adj_geo, adj_mob, args, device)
        internals["target_year"] = target_year
        internals_by_year[target_year] = internals

        mask_     = seq["test_mask_s"]                  # (N,) — valid zones
        y_s       = seq["test_y_s"][mask_]              # (N_valid, 9)
        ridge_s   = seq["test_ridge_s"][mask_]          # (N_valid, 9)
        zstd_s    = seq["zone_sector_std"][mask_]       # (N_valid, 9)
        pred_s    = np.maximum(ridge_s + resid_s[mask_] * zstd_s, 0.0)

        zones_arr = np.asarray(zones_sorted)[mask_]
        for zi, ze in enumerate(zones_arr):
            for si, s in enumerate(A10_SECTORS):
                rows.append({
                    "model":       "herald_v4",
                    "target_year": target_year,
                    "ZE2020":      int(ze),
                    "sector":      s,
                    "y_true":      float(y_s[zi, si]),
                    "y_pred":      float(pred_s[zi, si]),
                    "abs_error":   float(abs(y_s[zi, si] - pred_s[zi, si])),
                })

    return rows, internals_by_year


# ─── report writer ────────────────────────────────────────────────────────────

def write_report_v4(rows, args, internals_by_year, zones_sorted, node_idx_df):
    df  = pd.DataFrame(rows)

    # ── per-sector metrics ──────────────────────────────────────────────────
    sector_metrics = []
    for (sector, year), g in df.groupby(["sector","target_year"]):
        sector_metrics.append({
            "sector": sector, "target_year": int(year),
            "wmape": wmape(g["y_true"], g["y_pred"]), "n": len(g),
        })
    smdf = pd.DataFrame(sector_metrics)

    # Mean WMAPE per sector across years
    sector_mean = smdf.groupby("sector")["wmape"].mean().reset_index()
    sector_mean = sector_mean.sort_values("wmape")

    # Overall mean WMAPE (all sectors, all years)
    overall_wmape = wmape(df["y_true"], df["y_pred"])

    # Total creations: aggregate predictions across sectors
    total_df = df.groupby(["target_year","ZE2020"]).agg(
        y_true=("y_true","sum"), y_pred=("y_pred","sum")
    ).reset_index()
    total_by_year = {yr: wmape(g["y_true"], g["y_pred"])
                     for yr, g in total_df.groupby("target_year")}
    total_mean = np.mean(list(total_by_year.values()))

    # ── gamma and adjacency diagnostics ─────────────────────────────────────
    last = internals_by_year[max(internals_by_year)]
    gate_arr  = last["sector_gates"]  # (T, N, 9)
    years_f   = last["years"]

    # Mean sector gate per sector (last fold)
    # High g_t[zone,s] = more self; low = more neighbors
    sector_gate_mean = gate_arr.mean(axis=(0, 1))  # (9,)

    # Adjacency smoothness
    adj_arr = last["dynamic_adj"]   # (T, N, N)
    smooth_vals = [float(np.sum((adj_arr[t] - adj_arr[t-1])**2))
                   for t in range(1, len(adj_arr))]

    # Top-5 neighbors for key zones
    ze_to_libze  = {int(r["ze2020"]): r["libze2020"]
                    for _, r in node_idx_df.iterrows()}
    zone_idx_map = {z: i for i, z in enumerate(zones_sorted)}

    def _json_safe(obj):
        if isinstance(obj, (np.integer,)): return int(obj)
        if isinstance(obj, (np.floating,)): return float(obj)
        if isinstance(obj, np.ndarray): return obj.tolist()
        raise TypeError(type(obj))

    ridge_ar  = 0.0668
    stgnn_v1  = 0.0610
    herald_v3 = 0.0261

    tag     = f"_{args.run_tag}" if args.run_tag else ""
    run_key = f"{args.ablation}{tag}_seed_{args.seed}"
    result  = {
        "ablation":            args.ablation,
        "seed":                args.seed,
        "overall_wmape":       round(overall_wmape, 6),
        "total_wmape_mean":    round(total_mean, 6),
        "delta_vs_ridge_ar":   round(total_mean - ridge_ar, 6),
        "delta_vs_herald_v3":  round(total_mean - herald_v3, 6),
        "per_sector_mean_wmape": sector_mean.set_index("sector")["wmape"].round(6).to_dict(),
        "per_year_total_wmape": {int(k): round(v, 6) for k, v in total_by_year.items()},
        "sector_gate_mean_per_sector": {
            A10_SECTORS[i]: round(float(sector_gate_mean[i]), 5)
            for i in range(len(A10_SECTORS))
        },
        "adj_smooth_by_year": {
            int(years_f[t]): round(smooth_vals[t-1], 6)
            for t in range(1, len(years_f))
        },
        "gamma_geo": round(last["gamma_geo"], 4),
        "gamma_mob": round(last["gamma_mob"], 4),
    }

    existing = {}
    if OUT_JSON.exists():
        existing = json.loads(OUT_JSON.read_text(encoding="utf-8"))
    existing[run_key] = result
    OUT_JSON.write_text(json.dumps(existing, indent=2, default=_json_safe),
                        encoding="utf-8")

    # ── markdown ──────────────────────────────────────────────────────────────
    lines = [
        "# HERALD V4 — Sectoral Dynamic Graph",
        "",
        "## Architecture",
        "- **Sectoral output**: predict creations per A10 sector (9) × zone",
        "- **Sector-specific gates (N,9)**: each sector has its own self/neighbor balance",
        "- **Regime shifts Q_t**: non-redundant — covid/rebound exclusive to regime_t",
        "- **Concat node embedding**: no signal interference in e_t",
        "- **Gate bias -1.0**: starts neighbor-favoring",
        "",
        "## Results (total = sum of sectors)",
        "",
        "| Run | Total WMAPE | vs Ridge AR | vs HERALD V3 |",
        "|---|---:|---:|---:|",
        f"| Ridge AR | {ridge_ar:.4f} | — | — |",
        f"| HERALD V3 full (ref) | {herald_v3:.4f} | {herald_v3-ridge_ar:+.4f} | — |",
    ]
    for rk, rv in sorted(existing.items()):
        mw = rv["total_wmape_mean"]
        lines.append(f"| HERALD V4 {rk} | {mw:.4f} "
                     f"| {mw-ridge_ar:+.4f} | {mw-herald_v3:+.4f} |")

    lines += [
        "",
        f"## Per-sector WMAPE — {run_key}",
        "",
        "| Sector | Mean WMAPE | Gate self-weight |",
        "|---|---:|---:|",
    ]
    gm = result["sector_gate_mean_per_sector"]
    pm = result["per_sector_mean_wmape"]
    for s in sorted(pm, key=lambda x: pm[x]):
        lines.append(f"| {s} | {pm[s]:.5f} | {gm.get(s, '?'):.4f} |")

    lines += [
        "",
        "## Adjacency Dynamics (last fold)",
        "",
        "| Year transition | Smooth ||A_t - A_{t-1}||² |",
        "|---|---:|",
    ]
    for yr, v in sorted(result["adj_smooth_by_year"].items()):
        marker = " ← COVID" if int(yr) == 2020 else (" ← rebound" if int(yr) == 2021 else "")
        lines.append(f"| →{yr} | {v:.6f}{marker} |")

    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"\n=== HERALD V4 ({run_key}) ===")
    print(f"Total WMAPE (sum sectors): {total_mean:.6f}")
    print(f"Delta vs Ridge AR:         {total_mean - ridge_ar:+.6f}")
    print(f"Delta vs HERALD V3:        {total_mean - herald_v3:+.6f}")
    print()
    print("Per-sector mean WMAPE:")
    for s in sorted(pm, key=lambda x: pm[x]):
        print(f"  {s}: {pm[s]:.5f}  (gate self={gm.get(s,'?'):.3f})")
    print()
    print("Gate self-weight by sector (mean, last fold):")
    print("  High = self-reliant / Low = spatially porous")
    for s, g in sorted(gm.items(), key=lambda x: x[1]):
        bar = "█" * int(g * 20)
        print(f"  {s}: {g:.3f} {bar}")


# ─── main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="HERALD V4 — Sectoral Dynamic Graph")
    parser.add_argument("--epochs",             type=int,   default=800)
    parser.add_argument("--hidden-dim",         type=int,   default=32,
                        help="Shared node embedding dimension H")
    parser.add_argument("--sector-hidden",      type=int,   default=16,
                        help="Per-sector GRU hidden dimension H_s")
    parser.add_argument("--q-hidden",           type=int,   default=16)
    parser.add_argument("--attn-dim",           type=int,   default=8)
    parser.add_argument("--top-k",              type=int,   default=10)
    parser.add_argument("--prior-strength-init",type=float, default=1.0)
    parser.add_argument("--lr",                 type=float, default=1e-3)
    parser.add_argument("--weight-decay",       type=float, default=1e-4)
    parser.add_argument("--huber-delta",        type=float, default=300.0)
    parser.add_argument("--grad-clip",          type=float, default=5.0)
    parser.add_argument("--smooth-lambda",      type=float, default=0.1)
    parser.add_argument("--seed",               type=int,   default=0)
    parser.add_argument("--device",
                        default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--ablation", default="full",
                        choices=[
                            "full",
                            "self_only",
                            "fixed_geo_mob_only",
                            "static_adaptive",
                            "no_sector_gate",
                            "no_quarterly",
                            "no_regime",
                            "no_smooth",
                        ])
    parser.add_argument("--run-tag", default="",
                        help="Optional tag appended to run_key for sensitivity runs")
    args = parser.parse_args()

    set_seed(args.seed)
    device = torch.device(args.device)

    print("Loading data...")
    panel       = pd.read_csv(PANEL_PATH).sort_values(["target_year","ZE2020"]).reset_index(drop=True)
    splits      = pd.read_csv(SPLITS_PATH)
    node_idx_df = pd.read_csv(NODE_IDX_PATH)
    cols        = feature_columns_v4(panel, ablation=args.ablation)
    adj_geo     = load_adjacency(GEO_ADJ_PATH)
    adj_mob     = load_adjacency(MOB_ADJ_PATH)

    zones_sorted = sorted(panel["ZE2020"].unique())
    years_sorted = sorted(panel["target_year"].unique())

    print("Loading A10 sectoral panel...")
    a10_panel = load_or_build_side_a10_panel(zones_sorted)
    print(f"  A10 panel: {a10_panel.shape} — years {a10_panel['target_year'].min()}–{a10_panel['target_year'].max()}")

    print("Building quarterly tensor...")
    q_tensor = build_quarterly_tensor(zones_sorted, years_sorted)
    print(f"  Quarterly tensor: {q_tensor.shape}")
    print(f"  Annual features:  {len(cols)}  (covid/rebound in regime_t only)")
    print(f"  hidden_dim:       {args.hidden_dim}  sector_hidden: {args.sector_hidden}")
    print(f"  Ablation:         {args.ablation}")
    print(f"  Device:           {device}")

    print(f"\nTraining HERALD V4 (ablation={args.ablation}, seed={args.seed})...")
    rows, internals_by_year = evaluate_herald_v4(
        panel, a10_panel, splits, cols, q_tensor,
        zones_sorted, years_sorted, adj_geo, adj_mob, args, device,
    )

    pred      = pd.DataFrame(rows)
    tag       = f"_{args.run_tag}" if args.run_tag else ""
    suffix    = f"{args.ablation}{tag}_seed_{args.seed}"
    out_pred  = PROCESSED / f"herald_v4_predictions_{suffix}_v1.csv"
    out_int   = PROCESSED / f"herald_v4_internals_{suffix}_v1.npz"

    pred.to_csv(out_pred, index=False)

    last = internals_by_year[max(internals_by_year)]
    np.savez_compressed(
        out_int,
        dynamic_adj           = last["dynamic_adj"],           # (T, N, N)
        sector_gates          = last["sector_gates"],          # (T, N, 9)
        gamma_geo             = np.array([last["gamma_geo"]]),
        gamma_mob             = np.array([last["gamma_mob"]]),
        smooth_loss_inference = np.array([last["smooth_loss_inference"]]),
        years                 = np.array(last["years"]),
        node_order            = np.array(last["node_order"]),
        sector_names          = np.array(A10_SECTORS),
    )

    write_report_v4(rows, args, internals_by_year, zones_sorted, node_idx_df)

    print(f"\nSaved: {out_pred}")
    print(f"Saved: {out_int}")
    print(f"Saved: {OUT_JSON}")
    print(f"Saved: {OUT_MD}")


if __name__ == "__main__":
    main()
