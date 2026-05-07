"""
HERALD V6 — corrected dynamic graph + real sector head (A10 SIDE)

V6 keeps the V5 data contract but changes the scientific mechanism:
  - covid/rebound flags stay in the local annual path by default
  - annual, quarterly, and recurrent signals are concatenated before projection
  - regime shifts both attention queries and keys
  - graph loss is smooth by default, with optional regime contrast ablation
  - gate uses only [e_t, m_t], starts local-robust, and has weak entropy regularization
  - sector head conditions on stop-gradient total residual

V5 outputs are not overwritten. V6 prefix:
  data/processed/herald_v6_predictions_total_{ablation}{tag}_seed_{seed}_v1.csv
  data/processed/herald_v6_predictions_sector_{ablation}{tag}_seed_{seed}_v1.csv
  data/processed/herald_v6_internals_{ablation}{tag}_seed_{seed}_v1.npz
  reports/herald_v6_metrics_v1.json
  reports/HERALD_V6_MODEL_V1.md

Input and output paths can be overridden from the CLI to run additive
validation panels without mixing artifacts.
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

PANEL_PATH    = PROCESSED / "dynamic_stgnn_feature_panel_v1.csv"
SPLITS_PATH   = METADATA  / "dynamic_stgnn_walk_forward_splits_v1.csv"
GEO_ADJ_PATH  = PROCESSED / "graph_adjacency_core_v0.csv"
MOB_ADJ_PATH  = PROCESSED / "graph_adjacency_mobility_v0.csv"
NODE_IDX_PATH = PROCESSED / "graph_node_index_core_v0.csv"
SIDE_A10_PATH = PROCESSED / "side_creations_a10_ze2020_v1.csv"

OUT_JSON = REPORTS / "herald_v6_metrics_v1.json"
OUT_MD   = REPORTS / "HERALD_V6_MODEL_V1.md"

TARGET_COL  = "side_establishment_creations_official"
A10_SECTORS = ["BE", "FZ", "GI", "JZ", "KZ", "LZ", "MN", "OQ", "RU"]
REGIME_DIM  = 3
KEY_ZONES   = {"Paris": 1109, "Lyon": 8421, "Marseille": 9312, "Toulouse": 7625}


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


def predict_ridge_future(train_df, future_df):
    """Fit Ridge on training data and predict future features (no target required in future_df)."""
    lag_cols = [c for c in ["side_lag_1", "side_lag_2", "side_lag_3", "growth_1y", "growth_2y"]
                if c in train_df.columns]
    tr = train_df.dropna(subset=[TARGET_COL])
    m = Pipeline([("imp", SimpleImputer(strategy="median")),
                  ("sc",  StandardScaler()),
                  ("r",   Ridge(alpha=1.0))])
    m.fit(tr[lag_cols].values.astype(float), tr[TARGET_COL].values.astype(float))
    feat = future_df.reindex(columns=lag_cols).fillna(0).values.astype(float)
    return np.maximum(m.predict(feat), 0.0)


def build_future_panel_rows(panel, zones_sorted, future_years, prev_year_preds=None):
    """Build synthetic feature rows for future years (no observed target).

    Structural t-1 features are forward-filled from the last observed year.
    Lag and growth features are built from observed or predicted creations.
    """
    if prev_year_preds is None:
        prev_year_preds = {}

    last_obs = int(panel["target_year"].max())
    base = panel[panel["target_year"] == last_obs].copy()

    creation_lookup = {
        int(yr): panel[panel["target_year"] == yr]
                 .set_index("ZE2020")["side_establishment_creations_official"]
        for yr in panel["target_year"].unique()
    }

    result = []
    for future_year in sorted(future_years):
        row = base.copy()
        row["target_year"] = future_year

        def _get(yr):
            if yr in creation_lookup:
                return creation_lookup[yr]
            if yr in prev_year_preds:
                return pd.Series(prev_year_preds[yr])
            return None

        for col, yr in [("side_lag_1", future_year - 1),
                        ("side_lag_2", future_year - 2),
                        ("side_lag_3", future_year - 3)]:
            ser = _get(yr)
            if ser is not None:
                row[col] = row["ZE2020"].map(ser.to_dict())

        lag1 = row["side_lag_1"].replace(0.0, np.nan)
        lag2 = row["side_lag_2"].replace(0.0, np.nan)
        lag3 = row["side_lag_3"].replace(0.0, np.nan)
        row["growth_1y"] = (lag1 / lag2 - 1.0).fillna(0.0)
        row["growth_2y"] = (lag1 / lag3 - 1.0).fillna(0.0)
        row["is_covid_year"] = 0
        row["is_post_covid_rebound"] = 0
        row["side_establishment_creations_official"] = np.nan
        row["side_enterprise_creations_official"] = np.nan

        result.append(row)
        creation_lookup[future_year] = pd.Series({ze: np.nan for ze in zones_sorted})

    return pd.concat(result, ignore_index=True) if result else pd.DataFrame()


def run_future_forecast(panel, a10_panel, cols, zones_sorted, adj_geo, adj_mob,
                        args, device, forecast_horizon=2):
    """Train HERALD V6 on all observed data and produce prospective forecasts.

    For each future year the model is retrained from scratch on all data up to
    the last observed year.  2027 lags are constructed autoregressively from the
    2026 prediction.
    """
    print(f"\nProspective forecast — horizon {forecast_horizon} years...", flush=True)
    last_obs = int(panel["target_year"].max())
    future_years = [last_obs + h for h in range(1, forecast_horizon + 1)]
    prev_year_preds: dict = {}
    all_rows = []

    for future_year in future_years:
        print(f"  Forecasting {future_year}...", flush=True)

        future_df = build_future_panel_rows(panel, zones_sorted, [future_year], prev_year_preds)
        ext_panel  = pd.concat([panel, future_df], ignore_index=True)
        ext_years  = sorted(ext_panel["target_year"].unique())

        # Quarterly tensor with forward-fill for the future year
        ext_q = build_quarterly_tensor(zones_sorted, ext_years)
        fy_idx = ext_years.index(future_year)
        if ext_q[fy_idx].sum() == 0 and fy_idx > 0:
            ext_q[fy_idx] = ext_q[fy_idx - 1]

        ext_sec = build_sector_props_target(a10_panel, zones_sorted, ext_years)

        # make_sequences handles NaN-target future year: test_mask = all False
        seq = make_sequences(
            ext_panel, cols, ext_q, ext_sec,
            zones_sorted, ext_years, last_obs, future_year,
        )

        residual, _, _ = train_herald_v6(seq, adj_geo, adj_mob, args, device)

        ridge_pred = predict_ridge_future(
            panel, future_df.sort_values("ZE2020").reset_index(drop=True)
        )
        zone_std = seq["zone_std"]
        y_pred = np.maximum(ridge_pred + residual * zone_std, 0.0)

        prev_year_preds[future_year] = dict(zip(zones_sorted, y_pred.tolist()))

        for i, ze in enumerate(zones_sorted):
            all_rows.append({
                "model":         "herald_v6",
                "target_year":   future_year,
                "ZE2020":        int(ze),
                "y_pred":        float(y_pred[i]),
                "ridge_pred":    float(ridge_pred[i]),
                "forecast_type": "prospective",
                "seed":          args.seed,
            })

    return all_rows


# ─── A10 panel ────────────────────────────────────────────────────────────────

def load_or_build_side_a10_panel(zones_sorted):
    if SIDE_A10_PATH.exists():
        return pd.read_csv(SIDE_A10_PATH)
    print("  Building SIDE A10 panel from ZIP (first run only)...")
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
    df["ZE2020"]   = df["GEO"].astype(int)
    df = df[df["ZE2020"].isin(zone_set)]
    df = df.rename(columns={"TIME_PERIOD": "target_year", "OBS_VALUE": "creations"})
    df["creations"] = pd.to_numeric(df["creations"], errors="coerce").fillna(0).astype(int)
    pivot = df.pivot_table(index=["target_year","ZE2020"], columns="ACTIVITY",
                           values="creations", aggfunc="sum", fill_value=0).reset_index()
    pivot.columns.name = None
    for s in A10_SECTORS:
        if s not in pivot.columns:
            pivot[s] = 0
    pivot["total"] = pivot[A10_SECTORS].sum(axis=1)
    out = pivot[["target_year","ZE2020"] + A10_SECTORS + ["total"]].copy()
    out = out.sort_values(["target_year","ZE2020"]).reset_index(drop=True)
    out.to_csv(SIDE_A10_PATH, index=False)
    print(f"  Saved: {SIDE_A10_PATH}")
    return out


# ─── quarterly tensor ──────────────────────────────────────────────────────────

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
        sy = int(row["annee"]); ty = sy + 1
        q  = int(row["trimestre"]) - 1
        ze = int(row["code_zone_d_emploi"])
        if ty not in year_to_idx or ze not in zone_to_idx:
            continue
        ti, zi = year_to_idx[ty], zone_to_idx[ze]
        tensor[ti, q, zi, 0] = float(row["effectifs_salaries_cvs"])
        tensor[ti, q, zi, 1] = float(row["masse_salariale_cvs"])
    return tensor


def normalize_quarterly(tensor_full, train_t_idx):
    flat = tensor_full[train_t_idx].reshape(-1, tensor_full.shape[-1])
    mean = flat.mean(axis=0, keepdims=True)
    std  = flat.std(axis=0,  keepdims=True)
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


# ─── sector proportions target (replaces FLORES proxy) ────────────────────────

def build_sector_props_target(a10_panel, zones_sorted, years_sorted):
    """
    Returns (T, N, 9) float32 array of real A10 sector proportions.
    props[t, n, s] = actual_s / actual_total  where total > 0.
    NaN where total = 0 (masked out of sector loss).
    """
    T, N, S = len(years_sorted), len(zones_sorted), len(A10_SECTORS)
    out = np.full((T, N, S), np.nan, dtype=np.float32)
    zone_to_idx = {z: i for i, z in enumerate(zones_sorted)}
    year_to_idx = {y: i for i, y in enumerate(years_sorted)}
    for row in a10_panel.itertuples(index=False):
        yr, ze = int(row.target_year), int(row.ZE2020)
        if yr not in year_to_idx or ze not in zone_to_idx:
            continue
        ti, zi = year_to_idx[yr], zone_to_idx[ze]
        vals  = np.array([float(getattr(row, s, 0.0)) for s in A10_SECTORS], dtype=np.float32)
        total = vals.sum()
        if total > 0:
            out[ti, zi] = vals / total
    return out


# ─── regime vectors ────────────────────────────────────────────────────────────

def build_regime_vectors(panel, years_sorted, train_max):
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


# ─── HERALD V6 architecture ────────────────────────────────────────────────────

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


class HERALDv6Residual(nn.Module):
    """
    HERALD V6: dynamic graph with regime-exclusive Q/K shifts and a sector
    head conditioned on stop-gradient total residuals.
    """

    def __init__(self, num_nodes, annual_dim, hidden_dim,
                 attn_dim=8, q_hidden=16, n_sectors_a10=9,
                 top_k=10, prior_strength_init=1.0,
                 gate_bias_init=1.0):
        super().__init__()
        self.num_nodes      = num_nodes
        self.hidden_dim     = hidden_dim
        self.attn_dim       = attn_dim
        self.top_k          = top_k
        self.n_sectors_a10  = n_sectors_a10

        # Quarterly encoder
        self.quarterly_enc = QuarterlyEncoder(in_dim=2, hidden_dim=q_hidden)
        self.q_proj        = nn.Linear(q_hidden, hidden_dim)

        # Annual projection
        self.annual_proj = nn.Linear(annual_dim, hidden_dim)

        # Independent source fusion, replacing V5's ann + q + h addition.
        self.proj_e = nn.Linear(hidden_dim * 3, hidden_dim)

        # Dynamic attention with dual regime shifts.
        self.regime_proj_q = nn.Linear(REGIME_DIM, attn_dim)
        self.regime_proj_k = nn.Linear(REGIME_DIM, attn_dim)
        self.proj_Q = nn.Linear(hidden_dim, attn_dim)
        self.proj_K = nn.Linear(hidden_dim, attn_dim)

        self.gamma_geo = nn.Parameter(torch.tensor(float(prior_strength_init)))
        self.gamma_mob = nn.Parameter(torch.tensor(float(prior_strength_init)))

        self.static_emb_1 = nn.Parameter(torch.empty(num_nodes, attn_dim))
        self.static_emb_2 = nn.Parameter(torch.empty(attn_dim, num_nodes))
        nn.init.orthogonal_(self.static_emb_1)
        nn.init.orthogonal_(self.static_emb_2)

        # Message passing
        self.msg_proj = nn.Linear(hidden_dim, hidden_dim)

        # Gate excludes regime in V6.
        self.gate_mlp = nn.Sequential(
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 1),
        )
        nn.init.constant_(self.gate_mlp[-1].bias, float(gate_bias_init))

        # GRU cell
        self.gru_cell = nn.GRUCell(hidden_dim, hidden_dim)

        # Output heads
        self.out_main        = nn.Linear(hidden_dim, 1)  # total residual
        self.out_sector_a10  = nn.Linear(hidden_dim + 1, n_sectors_a10)

    def _static_adj(self):
        return torch.softmax(
            torch.relu(self.static_emb_1 @ self.static_emb_2), dim=1
        )

    def _dynamic_adj(self, e_t, prior_logits, regime_t):
        rq = self.regime_proj_q(regime_t)
        rk = self.regime_proj_k(regime_t)
        Q = self.proj_Q(e_t) + rq.unsqueeze(0)
        K = self.proj_K(e_t) + rk.unsqueeze(0)
        raw = (Q @ K.T) / (self.attn_dim ** 0.5)
        return topk_sparse_softmax(raw + prior_logits, self.top_k)

    def forward(self, x_annual_seq, x_quarterly_seq, regime_seq,
                adj_geo, adj_mob, adj_log_geo, adj_log_mob,
                ablation="full", return_internals=False):
        """
        ablation: full | self_only | fixed_geo_mob_only | static_adaptive |
                  contrast_loss | no_regime_in_graph | regime_exclusive |
                  no_sector_head | no_quarterly | no_smooth_no_contrast
        """
        N      = self.num_nodes
        device = next(self.parameters()).device

        h = torch.zeros(N, self.hidden_dim, device=device)

        prior_logits = self.gamma_geo * adj_log_geo + self.gamma_mob * adj_log_mob
        static_adj_m = self._static_adj()
        fixed_blend  = 0.5 * adj_geo + 0.5 * adj_mob

        pred_list, sector_list = [], []
        adj_list, gate_list    = [], []
        smooth_term = torch.tensor(0.0, device=device)
        contrast_term = torch.tensor(0.0, device=device)
        gate_entropy = torch.tensor(0.0, device=device)
        n_graph = 0
        n_gate = 0
        A_prev = None
        regime_prev = None
        adj_delta_list = []
        regime_delta_list = []

        for x_ann, x_q, regime_t in zip(x_annual_seq, x_quarterly_seq, regime_seq):
            ann   = F.relu(self.annual_proj(x_ann))
            q_enc = (torch.zeros_like(ann) if ablation == "no_quarterly"
                     else F.relu(self.q_proj(self.quarterly_enc(x_q))))
            e_t   = F.relu(self.proj_e(torch.cat([ann, q_enc, h], dim=-1)))

            # Adjacency
            if ablation == "self_only":
                A_t = None;  m_t = e_t
            elif ablation == "fixed_geo_mob_only":
                A_t = fixed_blend;  m_t = self.msg_proj(A_t @ e_t)
            elif ablation == "static_adaptive":
                A_t = static_adj_m; m_t = self.msg_proj(A_t @ e_t)
            else:
                r_adj = torch.zeros_like(regime_t) if ablation == "no_regime_in_graph" else regime_t
                A_t = self._dynamic_adj(e_t, prior_logits, r_adj)
                m_t = self.msg_proj(A_t @ e_t)

            # Conditional graph regularization.
            if A_t is not None and A_prev is not None:
                delta_sq = torch.sum((A_t - A_prev) ** 2)
                reg_delta = torch.sum(torch.abs(regime_t - regime_prev))
                regime_weight = torch.tanh(reg_delta)
                if ablation != "no_smooth_no_contrast":
                    smooth_term = smooth_term + delta_sq * (1.0 - regime_weight)
                    if ablation == "contrast_loss":
                        contrast_term = contrast_term - delta_sq * regime_weight
                    n_graph += 1
                if return_internals:
                    adj_delta_list.append(torch.sqrt(delta_sq.detach()))
                    regime_delta_list.append(reg_delta.detach())

            # Gate
            if ablation == "self_only":
                z_t = e_t
                g_t = torch.ones(N, 1, device=device)
            else:
                g_t = torch.sigmoid(self.gate_mlp(torch.cat([e_t, m_t], dim=-1)))
                z_t = g_t * e_t + (1.0 - g_t) * m_t
                eps = 1e-8
                gate_entropy = gate_entropy + (
                    -g_t * torch.log(g_t + eps) - (1.0 - g_t) * torch.log(1.0 - g_t + eps)
                ).mean()
                n_gate += 1

            h = self.gru_cell(z_t, h)

            pred   = self.out_main(h).squeeze(-1)                   # (N,)
            sector_input = torch.cat([h.detach(), pred.detach().unsqueeze(-1)], dim=-1)
            sector = torch.softmax(self.out_sector_a10(sector_input), dim=-1)

            pred_list.append(pred)
            sector_list.append(sector)

            if return_internals:
                A_store = A_t if A_t is not None else torch.eye(N, device=device)
                adj_list.append(A_store.detach())
                gate_list.append(g_t.detach())

            A_prev = A_t
            regime_prev = regime_t

        if n_graph > 0:
            smooth_term = smooth_term / n_graph
            contrast_term = contrast_term / n_graph
        if n_gate > 0:
            gate_entropy = gate_entropy / n_gate

        preds   = torch.stack(pred_list,   dim=0)  # (T, N)
        sectors = torch.stack(sector_list, dim=0)  # (T, N, 9)
        graph_losses = {
            "smooth_term": smooth_term,
            "contrast_term": contrast_term,
            "gate_entropy": gate_entropy,
        }

        if return_internals:
            adj_tensor  = torch.stack(adj_list,  dim=0)  # (T, N, N)
            gate_tensor = torch.stack(gate_list, dim=0)  # (T, N, 1)
            if adj_delta_list:
                adj_delta = torch.stack(adj_delta_list)
                regime_delta = torch.stack(regime_delta_list)
            else:
                adj_delta = torch.zeros(0, device=device)
                regime_delta = torch.zeros(0, device=device)
            return preds, sectors, graph_losses, adj_tensor, gate_tensor, regime_delta, adj_delta

        return preds, sectors, graph_losses


# ─── feature columns ──────────────────────────────────────────────────────────

def feature_columns(panel, ablation="full"):
    base   = ["side_lag_1","side_lag_2","side_lag_3","growth_1y","growth_2y"]
    flores = [c for c in panel.columns
              if c.startswith("flores_") and c.endswith("_t_minus_1")
              and "etab_" not in c]
    side   = [c for c in panel.columns
              if c.startswith("side_stock_") and c.endswith("_t_minus_1")]
    flags  = ["has_flores_source", "has_side_stock_source", "has_urssaf_source"]
    if ablation != "regime_exclusive":
        flags += ["is_covid_year", "is_post_covid_rebound"]
    urssaf = ([c for c in panel.columns
               if c.startswith("urssaf_") and c.endswith("_t_minus_1")]
              if ablation == "no_quarterly" else [])
    cols = base + flores + side + urssaf + flags
    return [c for c in cols if c in panel.columns]


# ─── sequence builder ─────────────────────────────────────────────────────────

def make_sequences(panel, cols, q_tensor, sec_props_tensor,
                   zones_sorted, years_sorted, train_max, target_year):
    year_to_idx  = {y: i for i, y in enumerate(years_sorted)}
    t_train_idx  = [year_to_idx[y] for y in years_sorted if y <= train_max]
    t_full_idx   = [year_to_idx[y] for y in years_sorted if y <= target_year]
    test_idx     = year_to_idx[target_year]
    zone_to_idx  = {z: i for i, z in enumerate(zones_sorted)}

    x_annual, y = build_annual_tensor(panel, cols, zones_sorted, years_sorted)

    train_df = panel[panel["target_year"] <= train_max].copy()
    test_df  = panel[panel["target_year"] == target_year].copy()
    if test_df[TARGET_COL].notna().any():
        ridge_test = fit_ridge_ar(train_df, test_df)
    else:
        # Prospective forecast years have no observed target; predict the
        # Ridge component directly from forecast-safe lag features.
        ridge_test = predict_ridge_future(train_df, test_df)

    ridge = np.full((len(years_sorted), len(zones_sorted)), np.nan, dtype=np.float32)
    for pred_year in sorted(train_df["target_year"].unique()):
        holdout, rp = fit_ridge_expanding(train_df, int(pred_year))
        for row, p in zip(holdout.itertuples(index=False), rp):
            if np.isfinite(p):
                ridge[year_to_idx[int(row.target_year)],
                      zone_to_idx[int(row.ZE2020)]] = p
    for row, p in zip(test_df.itertuples(index=False), ridge_test):
        ridge[test_idx, zone_to_idx[int(row.ZE2020)]] = p

    # Annual features
    imp = SimpleImputer(strategy="median")
    flat_train = x_annual[t_train_idx].reshape(-1, x_annual.shape[-1])
    imp.fit(flat_train)
    x_ann_train = imp.transform(flat_train).reshape(len(t_train_idx), len(zones_sorted), -1)
    x_ann_full  = imp.transform(
        x_annual[t_full_idx].reshape(-1, x_annual.shape[-1])
    ).reshape(len(t_full_idx), len(zones_sorted), -1)
    mean = x_ann_train.mean(axis=(0, 1), keepdims=True)
    std  = x_ann_train.std( axis=(0, 1), keepdims=True)
    std  = np.where(std == 0, 1.0, std)
    x_ann_train = (x_ann_train - mean) / std
    x_ann_full  = (x_ann_full  - mean) / std

    # Quarterly
    q_norm, _, _ = normalize_quarterly(q_tensor, t_train_idx)
    q_train = q_norm[t_train_idx]
    q_full  = q_norm[t_full_idx]

    # Zone normalization
    train_y_raw = y[t_train_idx]
    zone_mean   = np.nanmean(train_y_raw, axis=0)
    zone_std    = np.nanstd(train_y_raw,  axis=0)
    zone_std    = np.where(zone_std < 1.0, 1.0, zone_std)

    # Total residuals
    train_resid = (train_y_raw - ridge[t_train_idx]) / zone_std[np.newaxis, :]
    mask        = np.isfinite(train_resid).astype(np.float32)
    train_resid = np.nan_to_num(train_resid, nan=0.0).astype(np.float32)
    zone_weight = np.clip(zone_mean / zone_mean.mean(), 0.1, 10.0)

    # Real A10 sector proportion targets (replaces FLORES A17 proxy)
    sec_train = sec_props_tensor[t_train_idx]          # (T_train, N, 9)
    sec_mask  = np.isfinite(sec_train).all(axis=-1).astype(np.float32)  # (T_train, N)
    sec_train = np.nan_to_num(sec_train, nan=1.0 / len(A10_SECTORS))

    # Regime vectors
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
        "sec_train":      sec_train.astype(np.float32),   # real A10 proportions
        "sec_mask":       sec_mask.astype(np.float32),
        "test_y":         y[test_idx],
        "test_ridge":     ridge[test_idx],
        "test_mask":      np.isfinite(y[test_idx]) & np.isfinite(ridge[test_idx]),
        "target_year":    target_year,
        "train_y":        y[t_train_idx].astype(np.float32),
        "train_ridge":    ridge[t_train_idx].astype(np.float32),
    }


# ─── training ─────────────────────────────────────────────────────────────────

def train_herald_v6(seq, adj_geo, adj_mob, args, device):
    N          = len(seq["zones"])
    annual_dim = seq["x_ann_train"].shape[-1]

    model = HERALDv6Residual(
        num_nodes=N,
        annual_dim=annual_dim,
        hidden_dim=args.hidden_dim,
        attn_dim=args.attn_dim,
        q_hidden=args.q_hidden,
        n_sectors_a10=len(A10_SECTORS),
        top_k=args.top_k,
        prior_strength_init=args.prior_strength_init,
        gate_bias_init=args.gate_bias_init,
    ).to(device)

    opt   = torch.optim.AdamW(model.parameters(), lr=args.lr,
                               weight_decay=args.weight_decay)
    huber = nn.HuberLoss(delta=args.huber_delta, reduction="none")

    x_ann  = torch.tensor(seq["x_ann_train"],  device=device)
    x_q    = torch.tensor(seq["q_train"],      device=device)
    regime = torch.tensor(seq["regime_train"], device=device)
    target = torch.tensor(seq["train_resid"],  device=device)
    mask   = torch.tensor(seq["mask"],         device=device)
    zone_w = torch.tensor(seq["zone_weight"],  device=device)
    sec_t  = torch.tensor(seq["sec_train"],    device=device)   # real A10 proportions
    sec_m  = torch.tensor(seq["sec_mask"],     device=device)

    adj_g     = torch.tensor(adj_geo, device=device)
    adj_m_t   = torch.tensor(adj_mob, device=device)
    eps       = 1e-6
    adj_log_g = torch.log(adj_g   + eps)
    adj_log_m = torch.log(adj_m_t + eps)

    T        = x_ann.shape[0]
    ablation = args.ablation
    # no_sector_head: zero out sector loss so head doesn't train
    lam_sec  = 0.0 if ablation == "no_sector_head" else args.sector_lambda

    model.train()
    for ep in range(args.epochs):
        opt.zero_grad()

        ann_list = [x_ann[t]              for t in range(T)]
        q_list   = [x_q[t].permute(1,0,2) for t in range(T)]
        reg_list = [regime[t]             for t in range(T)]

        pred_main, pred_sector, graph_losses = model(
            ann_list, q_list, reg_list,
            adj_g, adj_m_t, adj_log_g, adj_log_m,
            ablation=ablation, return_internals=False,
        )

        zone_w_bc = zone_w.unsqueeze(0).expand_as(pred_main)
        denom     = torch.clamp((mask * zone_w_bc).sum(), min=1.0)
        loss_main = (huber(pred_main, target) * mask * zone_w_bc).sum() / denom

        eps_kl   = 1e-8
        kl       = sec_t * (torch.log(sec_t + eps_kl) - torch.log(pred_sector + eps_kl))
        loss_sec = (kl.sum(-1) * sec_m).sum() / torch.clamp(sec_m.sum(), min=1.0)

        loss_graph = (
            args.smooth_lambda * graph_losses["smooth_term"] +
            args.contrast_lambda * graph_losses["contrast_term"] -
            args.gate_entropy_lambda * graph_losses["gate_entropy"]
        )
        loss = loss_main + lam_sec * loss_sec + loss_graph
        loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), args.grad_clip)
        opt.step()

    # Inference on full sequence
    model.eval()
    with torch.no_grad():
        x_ann_f = torch.tensor(seq["x_ann_full"],  device=device)
        x_q_f   = torch.tensor(seq["q_full"],      device=device)
        reg_f   = torch.tensor(seq["regime_full"], device=device)
        T_full  = x_ann_f.shape[0]
        ann_f   = [x_ann_f[t]              for t in range(T_full)]
        q_f     = [x_q_f[t].permute(1,0,2) for t in range(T_full)]
        reg_fl  = [reg_f[t]                for t in range(T_full)]

        pred_f, sec_f, graph_f, adj_t, gate_t, regime_delta_t, adj_delta_t = model(
            ann_f, q_f, reg_fl,
            adj_g, adj_m_t, adj_log_g, adj_log_m,
            ablation=ablation, return_internals=True,
        )

    internals = {
        "dynamic_adj":          adj_t.cpu().numpy(),    # (T, N, N)
        "gate_values":          gate_t.cpu().numpy(),   # (T, N, 1)
        "regime_delta_by_year": regime_delta_t.cpu().numpy(),
        "adj_delta_by_year":    adj_delta_t.cpu().numpy(),
        "sector_proportions":   sec_f[-1].cpu().numpy(),# (N, 9)
        "gamma_geo":            float(model.gamma_geo.item()),
        "gamma_mob":            float(model.gamma_mob.item()),
        "smooth_loss_inference":float(graph_f["smooth_term"].item()),
        "contrast_loss_inference": float(graph_f["contrast_term"].item()),
        "gate_entropy_inference": float(graph_f["gate_entropy"].item()),
        "years":                seq["years_full"],
        "node_order":           seq["zones"],
    }
    return pred_f[-1].cpu().numpy(), sec_f[-1].cpu().numpy(), internals


# ─── evaluation ───────────────────────────────────────────────────────────────

def evaluate_herald_v6(panel, a10_panel, splits, cols, q_tensor, sec_props_tensor,
                       zones_sorted, years_sorted, adj_geo, adj_mob, args, device):
    total_rows, sector_rows = [], []
    internals_by_year = {}

    for _, split in splits.iterrows():
        target_year = int(split["target_year"])
        train_max   = int(split["train_years_max"])
        print(f"  Fold {target_year}...", flush=True)

        seq = make_sequences(panel, cols, q_tensor, sec_props_tensor,
                             zones_sorted, years_sorted, train_max, target_year)
        residual, sector_props, internals = train_herald_v6(seq, adj_geo, adj_mob, args, device)
        internals["target_year"] = target_year
        internals_by_year[target_year] = internals

        mask_     = seq["test_mask"]
        y_true    = seq["test_y"][mask_]
        ridge_p   = seq["test_ridge"][mask_]
        zone_std  = seq["zone_std"][mask_]
        y_pred    = np.maximum(ridge_p + residual[mask_] * zone_std, 0.0)
        s_props   = sector_props[mask_]   # (N_valid, 9)

        # For no_sector_head: use uniform proportions
        if args.ablation == "no_sector_head":
            s_props = np.full_like(s_props, 1.0 / len(A10_SECTORS))

        zones_arr = np.asarray(zones_sorted)[mask_]

        # Actual sector counts from A10 panel — needed for per-sector WMAPE
        a10_test = (a10_panel[a10_panel["target_year"] == target_year]
                    .set_index("ZE2020"))

        for i, (ze, yt, yp) in enumerate(zip(zones_arr, y_true, y_pred)):
            total_rows.append({"model": "herald_v6", "target_year": target_year,
                               "ZE2020": int(ze), "y_true": float(yt),
                               "y_pred": float(yp), "abs_error": float(abs(yt - yp))})
            for si, s in enumerate(A10_SECTORS):
                # y_true_sector: actual sector count from SIDE A10 (NaN if missing)
                y_true_s = float(a10_test.loc[ze, s]) \
                    if ze in a10_test.index else np.nan
                sector_rows.append({
                    "model":          "herald_v6",
                    "target_year":    target_year,
                    "ZE2020":         int(ze),
                    "sector":         s,
                    "y_true_sector":  y_true_s,
                    "y_pred_sector":  float(yp * s_props[i, si]),
                    "y_pred_total":   float(yp),
                    "prop_pred":      float(s_props[i, si]),
                })

    return total_rows, sector_rows, internals_by_year


# ─── report ───────────────────────────────────────────────────────────────────

def write_report(total_rows, sector_rows, args, internals_by_year):
    total_df  = pd.DataFrame(total_rows)
    sector_df = pd.DataFrame(sector_rows)

    # Total WMAPE per year
    total_metrics = []
    for (model, year), g in total_df.groupby(["model","target_year"]):
        total_metrics.append({"target_year": int(year),
                               "wmape": wmape(g["y_true"], g["y_pred"]), "n": len(g)})
    tmdf       = pd.DataFrame(total_metrics)
    mean_wmape = float(tmdf["wmape"].mean())

    # Per-sector WMAPE — the primary evaluation of the sector head
    sector_wmape = {}
    valid_sector = sector_df.dropna(subset=["y_true_sector"])
    for s in A10_SECTORS:
        df_s = valid_sector[valid_sector["sector"] == s]
        if len(df_s) > 0:
            sector_wmape[s] = round(wmape(df_s["y_true_sector"], df_s["y_pred_sector"]), 5)
    sector_wmape_mean = round(float(np.mean(list(sector_wmape.values()))), 5) \
        if sector_wmape else np.nan

    # Gate and gamma from last fold
    last = internals_by_year[max(internals_by_year)]
    gate_arr = last["gate_values"]  # (T, N, 1)
    years_f  = last["years"]
    gate_by_year = {int(yr): round(float(gate_arr[t].mean()), 5)
                    for t, yr in enumerate(years_f)
                    if int(yr) in (2019, 2020, 2021, 2022, 2024)}

    # Sector proportions (mean across zones, last fold)
    sec_props = last["sector_proportions"]  # (N, 9)
    sec_mean  = {A10_SECTORS[i]: round(float(sec_props[:, i].mean()), 4)
                 for i in range(len(A10_SECTORS))}

    def _json_safe(obj):
        if isinstance(obj, (np.integer,)): return int(obj)
        if isinstance(obj, (np.floating,)): return float(obj)
        if isinstance(obj, np.ndarray): return obj.tolist()
        raise TypeError(type(obj))

    ridge_ar  = 0.0668
    stgnn_v1  = 0.0610
    herald_v3 = 0.0261

    tag     = f"_{args.run_tag}" if getattr(args, "run_tag", "") else ""
    run_key = f"{args.ablation}{tag}_seed_{args.seed}"
    result  = {
        "ablation":             args.ablation,
        "seed":                 args.seed,
        "run_tag":              getattr(args, "run_tag", ""),
        "hidden_dim":           args.hidden_dim,
        "top_k":                args.top_k,
        "smooth_lambda":        args.smooth_lambda,
        "contrast_lambda":      args.contrast_lambda,
        "gate_bias_init":       args.gate_bias_init,
        "gate_entropy_lambda":  args.gate_entropy_lambda,
        "total_wmape_mean":     round(mean_wmape, 6),
        "delta_vs_ridge_ar":    round(mean_wmape - ridge_ar, 6),
        "delta_vs_v3":          round(mean_wmape - herald_v3, 6),
        "per_year_total":       {int(r["target_year"]): round(r["wmape"], 6)
                                 for _, r in tmdf.iterrows()},
        "sector_wmape":         sector_wmape,
        "sector_wmape_mean":    sector_wmape_mean,
        "gate_by_year":         gate_by_year,
        "gamma_geo":            round(last["gamma_geo"], 4),
        "gamma_mob":            round(last["gamma_mob"], 4),
        "regime_delta_by_year": [round(float(x), 6) for x in last["regime_delta_by_year"]],
        "adj_delta_by_year":    [round(float(x), 6) for x in last["adj_delta_by_year"]],
        "mean_sector_proportions": sec_mean,
    }

    existing = {}
    if OUT_JSON.exists():
        existing = json.loads(OUT_JSON.read_text(encoding="utf-8"))
    existing[run_key] = result
    OUT_JSON.write_text(json.dumps(existing, indent=2, default=_json_safe),
                        encoding="utf-8")

    lines = [
        "# HERALD V6 — dynamic graph + A10 sector head",
        "",
        "## Architecture",
        "- Regime-exclusive covid/rebound flags by default",
        "- e_t from concat([annual, quarterly, h]) + projection",
        "- Dynamic A_t with regime shifts in queries and keys",
        "- Conditional graph smooth/contrast loss",
        "- Gate excludes regime and starts from configurable bias",
        "- Sector head uses concat([h_t, stop_gradient(total_resid)])",
        "- Final sector: final_total × sector_proportions[:, s]",
        "",
        "| Run | Total WMAPE | vs Ridge AR | vs HERALD V3 |",
        "|---|---:|---:|---:|",
        f"| Ridge AR | {ridge_ar:.4f} | — | — |",
        f"| HERALD V3 full (ref) | {herald_v3:.4f} | {herald_v3-ridge_ar:+.4f} | — |",
    ]
    for rk, rv in sorted(existing.items()):
        mw = rv["total_wmape_mean"]
        lines.append(f"| V6 {rk} | {mw:.4f} | {mw-ridge_ar:+.4f} | {mw-herald_v3:+.4f} |")

    lines += ["", f"## Per-year total WMAPE — {run_key}", "",
              "| Year | WMAPE |", "|---:|---:|"]
    for yr, w in sorted(result["per_year_total"].items()):
        lines.append(f"| {yr} | {w:.6f} |")

    if sector_wmape:
        lines += ["", f"## Per-sector WMAPE — {run_key}",
                  f"Mean across sectors: {sector_wmape_mean}", "",
                  "| Sector | WMAPE |", "|---|---:|"]
        for s in sorted(sector_wmape, key=lambda x: sector_wmape[x]):
            lines.append(f"| {s} | {sector_wmape[s]:.5f} |")

    lines += ["", "## Mean predicted sector proportions (last fold)", "",
              "| Sector | Predicted proportion |", "|---|---:|"]
    for s, p in sorted(sec_mean.items(), key=lambda x: -x[1]):
        lines.append(f"| {s} | {p:.4f} |")

    lines += ["", f"## Graph deltas — {run_key}", "",
              "| Transition index | regime_delta | adj_delta |", "|---:|---:|---:|"]
    for i, (rd, ad) in enumerate(zip(result["regime_delta_by_year"], result["adj_delta_by_year"]), start=1):
        lines.append(f"| {i} | {rd:.6f} | {ad:.6f} |")

    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"\n=== HERALD V6 ({run_key}) ===")
    print(f"Total WMAPE:        {mean_wmape:.6f}")
    print(f"vs Ridge AR:        {mean_wmape - ridge_ar:+.6f}")
    print(f"vs HERALD V3:       {mean_wmape - herald_v3:+.6f}")
    if sector_wmape:
        print(f"Sector WMAPE mean:  {sector_wmape_mean:.5f}")
    print()
    for r in tmdf.sort_values("target_year").itertuples(index=False):
        print(f"  {r.target_year}: {r.wmape:.6f}")
    if sector_wmape:
        print("\nPer-sector WMAPE:")
        for s in sorted(sector_wmape, key=lambda x: sector_wmape[x]):
            print(f"  {s}: {sector_wmape[s]:.5f}")
    print(f"\nγ_geo={last['gamma_geo']:.3f}  γ_mob={last['gamma_mob']:.3f}")
    print(f"Gate 2020={gate_by_year.get(2020,'?')}  Gate 2021={gate_by_year.get(2021,'?')}")


# ─── main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="HERALD V6")
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
    parser.add_argument("--smooth-lambda",      type=float, default=0.01)
    parser.add_argument("--contrast-lambda",    type=float, default=0.0)
    parser.add_argument("--gate-entropy-lambda",type=float, default=0.001)
    parser.add_argument("--gate-bias-init",     type=float, default=1.0)
    parser.add_argument("--sector-lambda",      type=float, default=0.1)
    parser.add_argument("--seed",               type=int,   default=0)
    parser.add_argument("--panel-path", type=Path, default=PANEL_PATH)
    parser.add_argument("--splits-path", type=Path, default=SPLITS_PATH)
    parser.add_argument("--side-a10-path", type=Path, default=SIDE_A10_PATH)
    parser.add_argument("--prediction-output-dir", type=Path, default=PROCESSED)
    parser.add_argument("--metrics-path", type=Path, default=OUT_JSON)
    parser.add_argument("--model-card-path", type=Path, default=OUT_MD)
    parser.add_argument("--device",
                        default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--ablation", default="full",
                        choices=[
                            "full",
                            "self_only",
                            "fixed_geo_mob_only",
                            "static_adaptive",
                            "contrast_loss",
                            "no_regime_in_graph",
                            "regime_exclusive",
                            "no_sector_head",
                            "no_quarterly",
                            "no_smooth_no_contrast",
                        ])
    parser.add_argument("--run-tag", default="")
    parser.add_argument("--forecast-horizon", type=int, default=0,
                        help="Years ahead to forecast after the last observed year (0 = disabled).")
    parser.add_argument("--forecast-only", action="store_true",
                        help="Skip walk-forward evaluation; run only the prospective forecast.")
    args = parser.parse_args()

    set_seed(args.seed)
    device = torch.device(args.device)

    globals()["SIDE_A10_PATH"] = args.side_a10_path
    globals()["OUT_JSON"] = args.metrics_path
    globals()["OUT_MD"] = args.model_card_path
    args.prediction_output_dir.mkdir(parents=True, exist_ok=True)
    args.metrics_path.parent.mkdir(parents=True, exist_ok=True)
    args.model_card_path.parent.mkdir(parents=True, exist_ok=True)

    print("Loading data...")
    panel       = pd.read_csv(args.panel_path).sort_values(["target_year","ZE2020"]).reset_index(drop=True)
    splits      = pd.read_csv(args.splits_path)
    cols        = feature_columns(panel, ablation=args.ablation)
    adj_geo     = load_adjacency(GEO_ADJ_PATH)
    adj_mob     = load_adjacency(MOB_ADJ_PATH)

    zones_sorted = sorted(panel["ZE2020"].unique())
    years_sorted = sorted(panel["target_year"].unique())

    print("Loading A10 sectoral panel...")
    a10_panel = load_or_build_side_a10_panel(zones_sorted)

    print("Building tensors...")
    q_tensor          = build_quarterly_tensor(zones_sorted, years_sorted)
    sec_props_tensor  = build_sector_props_target(a10_panel, zones_sorted, years_sorted)
    print(f"  Quarterly:    {q_tensor.shape}")
    print(f"  Sector props: {sec_props_tensor.shape}")
    print(f"  Features:     {len(cols)}")
    print(f"  Ablation:     {args.ablation}  Device: {device}")

    tag    = f"_{args.run_tag}" if args.run_tag else ""
    suffix = f"{args.ablation}{tag}_seed_{args.seed}"

    if not args.forecast_only:
        print(f"\nTraining HERALD V6 (ablation={args.ablation}, seed={args.seed})...")
        total_rows, sector_rows, internals_by_year = evaluate_herald_v6(
            panel, a10_panel, splits, cols, q_tensor, sec_props_tensor,
            zones_sorted, years_sorted, adj_geo, adj_mob, args, device,
        )

        out_total  = args.prediction_output_dir / f"herald_v6_predictions_total_{suffix}_v1.csv"
        out_sector = args.prediction_output_dir / f"herald_v6_predictions_sector_{suffix}_v1.csv"
        out_int    = args.prediction_output_dir / f"herald_v6_internals_{suffix}_v1.npz"

        pd.DataFrame(total_rows).to_csv(out_total,  index=False)
        pd.DataFrame(sector_rows).to_csv(out_sector, index=False)

        last = internals_by_year[max(internals_by_year)]
        np.savez_compressed(
            out_int,
            dynamic_adj           = last["dynamic_adj"],
            gate_values           = last["gate_values"],
            regime_delta_by_year  = last["regime_delta_by_year"],
            adj_delta_by_year     = last["adj_delta_by_year"],
            sector_proportions    = last["sector_proportions"],
            gamma_geo             = np.array([last["gamma_geo"]]),
            gamma_mob             = np.array([last["gamma_mob"]]),
            smooth_loss_inference = np.array([last["smooth_loss_inference"]]),
            contrast_loss_inference = np.array([last["contrast_loss_inference"]]),
            gate_entropy_inference = np.array([last["gate_entropy_inference"]]),
            years                 = np.array(last["years"]),
            node_order            = np.array(last["node_order"]),
            sector_names          = np.array(A10_SECTORS),
        )

        write_report(total_rows, sector_rows, args, internals_by_year)

        print(f"\nSaved: {out_total}")
        print(f"Saved: {out_sector}")
        print(f"Saved: {out_int}")
        print(f"Saved: {OUT_JSON}")
        print(f"Saved: {OUT_MD}")

    if args.forecast_horizon > 0:
        forecast_rows = run_future_forecast(
            panel, a10_panel, cols, zones_sorted, adj_geo, adj_mob,
            args, device, forecast_horizon=args.forecast_horizon,
        )
        out_forecast = args.prediction_output_dir / f"herald_v6_forecast_{suffix}_v1.csv"
        pd.DataFrame(forecast_rows).to_csv(out_forecast, index=False)
        print(f"\nSaved prospective forecast: {out_forecast}")
        last_obs = int(panel["target_year"].max())
        for yr in range(last_obs + 1, last_obs + args.forecast_horizon + 1):
            yr_rows = [r for r in forecast_rows if r["target_year"] == yr]
            agg = sum(r["y_pred"] for r in yr_rows)
            print(f"  {yr} national aggregate forecast: {agg:,.0f}")


if __name__ == "__main__":
    main()
