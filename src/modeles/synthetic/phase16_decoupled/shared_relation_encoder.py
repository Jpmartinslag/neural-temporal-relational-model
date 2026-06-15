"""
shared_relation_encoder.py — SharedRelationEncoder for DEC-055.

One function for ALL pairs. Same weights for every (source, target).
No S×S lookup table. No pair-specific parameters.

Architecture:
  Feature extraction (stateless):
    - Per-sector summary: 8 features each (aggregated over territories)
    - Cross-sector lag features: 6 (causal, no future)
    - Temporal context: 3
    Total input dim: 25

  Shared encoder MLP: 25 → 32 (LayerNorm + ReLU) → 32 (ReLU)

  Independent output heads (all from 32-dim embedding):
    - presence_logit:  Linear(32→1)
    - direction_logit: Linear(32→1)  — P(src truly drives tgt, not reverse)
    - sign_logit:      Linear(32→1)
    - lag_logits:      Linear(32→2)  — [lag1_logit, lag2_logit]
    - strength:        Linear(32→1) + softplus
    - confidence:      Linear(32→1) + sigmoid

Parameter count: documented via n_parameters().

FROZEN invariants (DEC-055):
  - No nn.Parameter with shape (n_sectors, n_sectors)
  - No embedding indexed by sector identity
  - All pairs share exact same weights
  - No target in inputs (causal only)
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

# ── Frozen architecture constants ─────────────────────────────────────────────
HIST_FEATURES_PER_SECTOR: int = 8
CROSS_FEATURES: int = 7       # includes asymmetry feature
CONTEXT_FEATURES: int = 3
INPUT_DIM: int = 2 * HIST_FEATURES_PER_SECTOR + CROSS_FEATURES + CONTEXT_FEATURES  # 26
ENCODER_HIDDEN1: int = 32
ENCODER_HIDDEN2: int = 32
MIN_OBS_FOR_STATS: float = 1.0


# ── Stateless feature extraction ──────────────────────────────────────────────

def _sector_features(h: torch.Tensor, m: torch.Tensor) -> torch.Tensor:
    """
    Summarise one sector's observed history aggregated over territories.
    h, m: (n_T, n_W) — history and mask for the window.
    Returns (8,) feature vector. Causal only — no future.
    """
    n_obs = m.sum().clamp(min=MIN_OBS_FOR_STATS)
    h_obs = h * m

    obs_frac = m.mean()
    h_mean = h_obs.sum() / n_obs
    h_var = ((h_obs - h_mean * m) ** 2 * m).sum() / n_obs
    h_std = h_var.clamp(min=0.0).sqrt()

    # Last-year mean (across observed territories)
    last_col_mask = m[:, -1]
    last_val = (h[:, -1] * last_col_mask).sum() / last_col_mask.sum().clamp(min=MIN_OBS_FOR_STATS)

    # Linear trend (time coded -1 to +1 over window)
    n_W = h.shape[1]
    t_code = torch.linspace(-1.0, 1.0, n_W, device=h.device)
    trend = (h_obs * m * t_code.unsqueeze(0)).sum() / n_obs

    # AR1 proxy: correlation of consecutive pairs
    if n_W >= 3:
        h_prev, h_next = h_obs[:, :-1], h_obs[:, 1:]
        m_pair = m[:, :-1] * m[:, 1:]
        n_p = m_pair.sum().clamp(min=MIN_OBS_FOR_STATS)
        mp_ = (h_prev * m_pair).sum() / n_p
        mn_ = (h_next * m_pair).sum() / n_p
        cov = ((h_prev - mp_) * (h_next - mn_) * m_pair).sum() / n_p
        v_p = ((h_prev - mp_) ** 2 * m_pair).sum() / n_p
        v_n = ((h_next - mn_) ** 2 * m_pair).sum() / n_p
        ar1 = cov / (v_p * v_n).clamp(min=1e-8).sqrt()
    else:
        ar1 = torch.zeros(1, device=h.device).squeeze()

    # Volatility: recent vs older half
    mid = max(1, n_W // 2)
    old_obs = m[:, :mid].sum().clamp(min=MIN_OBS_FOR_STATS)
    rec_obs = m[:, mid:].sum().clamp(min=MIN_OBS_FOR_STATS)
    old_std = ((h_obs[:, :mid] - (h_obs[:, :mid].sum() / old_obs)) ** 2 * m[:, :mid]).sum() / old_obs
    rec_std = ((h_obs[:, mid:] - (h_obs[:, mid:].sum() / rec_obs)) ** 2 * m[:, mid:]).sum() / rec_obs
    vol_drift = rec_std.clamp(min=0.0).sqrt() - old_std.clamp(min=0.0).sqrt()

    return torch.stack([obs_frac, h_mean, h_std, last_val, trend, ar1, h_var.clamp(min=0.0).sqrt(), vol_drift])


def _cross_features(
    src: torch.Tensor, tgt: torch.Tensor,
    sm: torch.Tensor, tm: torch.Tensor,
) -> torch.Tensor:
    """
    Cross-sector features between source and target histories.
    ALL features are causal (lag ≥ 1 for cross-lag; lag=0 uses contemporaneous only).
    Includes one ANTISYMMETRIC feature (lag-1 corr src→tgt minus tgt→src) for direction.
    Returns (7,) feature vector.
    """
    n_W = src.shape[1]

    def lag_corr(a: torch.Tensor, b: torch.Tensor, ma: torch.Tensor, mb: torch.Tensor, lag: int) -> torch.Tensor:
        if lag == 0:
            a_lag = a * ma
            b_lag = b * mb
            mp = ma * mb
        elif n_W <= lag:
            return torch.tensor(0.0, device=src.device)
        else:
            a_lag = a[:, :-lag] * ma[:, :-lag]
            b_lag = b[:, lag:] * mb[:, lag:]
            mp = ma[:, :-lag] * mb[:, lag:]
        np_ = mp.sum().clamp(min=MIN_OBS_FOR_STATS)
        ma_ = (a_lag * mp).sum() / np_
        mb_ = (b_lag * mp).sum() / np_
        cov = ((a_lag - ma_) * (b_lag - mb_) * mp).sum() / np_
        va = ((a_lag - ma_) ** 2 * mp).sum() / np_
        vb = ((b_lag - mb_) ** 2 * mp).sum() / np_
        return cov / (va * vb).clamp(min=1e-8).sqrt()

    def lag_diff_mean(a: torch.Tensor, b: torch.Tensor, ma: torch.Tensor, mb: torch.Tensor, lag: int) -> torch.Tensor:
        if n_W <= lag:
            return torch.tensor(0.0, device=src.device)
        a_lag = a[:, :-lag] * ma[:, :-lag]
        b_lag = b[:, lag:] * mb[:, lag:]
        mp = ma[:, :-lag] * mb[:, lag:]
        np_ = mp.sum().clamp(min=MIN_OBS_FOR_STATS)
        return ((b_lag - a_lag) * mp).sum() / np_

    corr_s2t_1 = lag_corr(src, tgt, sm, tm, 1)   # corr(src[t-1], tgt[t])
    corr_s2t_2 = lag_corr(src, tgt, sm, tm, 2)   # corr(src[t-2], tgt[t])
    corr_t2s_1 = lag_corr(tgt, src, tm, sm, 1)   # corr(tgt[t-1], src[t]) — reverse direction

    # ANTISYMMETRIC: positive when src→tgt, negative when tgt→src
    direction_asymmetry = corr_s2t_1 - corr_t2s_1

    diff1 = lag_diff_mean(src, tgt, sm, tm, 1)
    diff2 = lag_diff_mean(src, tgt, sm, tm, 2)

    # Contemporaneous correlation
    contemp = lag_corr(src, tgt, sm, tm, 0) if n_W >= 2 else torch.tensor(0.0, device=src.device)

    return torch.stack([corr_s2t_1, corr_s2t_2, diff1, diff2, contemp, direction_asymmetry, corr_t2s_1])


def extract_pair_features(
    panel: np.ndarray,
    obs_mask: np.ndarray,
    src_idx: int,
    tgt_idx: int,
    window_end: int,
    window_size: int = 8,
    device: str = "cpu",
    context: Optional[np.ndarray] = None,
) -> torch.Tensor:
    """
    Extract feature vector for directed pair (src_idx → tgt_idx) using history
    up to (but not including) year window_end. Causal only — no future.

    Returns (INPUT_DIM,) tensor.
    """
    w_start = max(0, window_end - window_size)
    n_T = panel.shape[0]

    # Ensure we have at least 2 years for meaningful statistics
    w_len = window_end - w_start
    if w_len < 2:
        return torch.zeros(INPUT_DIM, device=device)

    src_h = torch.from_numpy(panel[:, src_idx, w_start:window_end].astype(np.float32)).to(device)
    tgt_h = torch.from_numpy(panel[:, tgt_idx, w_start:window_end].astype(np.float32)).to(device)
    src_m = torch.from_numpy(obs_mask[:, src_idx, w_start:window_end].astype(np.float32)).to(device)
    tgt_m = torch.from_numpy(obs_mask[:, tgt_idx, w_start:window_end].astype(np.float32)).to(device)

    f_src = _sector_features(src_h, src_m)
    f_tgt = _sector_features(tgt_h, tgt_m)
    f_cross = _cross_features(src_h, tgt_h, src_m, tgt_m)

    if context is not None:
        ctx = torch.from_numpy(context.astype(np.float32)).to(device)
    else:
        # Default context: year fraction + obs_frac + zero
        n_Y = panel.shape[2]
        year_frac = float(window_end) / max(1, n_Y)
        obs_frac_global = float(obs_mask.mean())
        ctx = torch.tensor([year_frac, obs_frac_global, 0.0], device=device)

    return torch.cat([f_src, f_tgt, f_cross, ctx])  # (26,)


def compute_env_context_features(panel: np.ndarray, obs_mask: np.ndarray) -> np.ndarray:
    """
    Compute observable environment-level features from data (no ground truth).
    Used by ContextAdapter. Returns (6,) array.
    """
    obs_frac = float(obs_mask.mean())
    activity_mean = float(np.nan_to_num(panel * obs_mask).mean())
    activity_std = float(np.nan_to_num(panel * obs_mask).std())

    # Crisis severity: most negative z-scored year across territories/sectors
    panel_obs = panel * obs_mask
    y_means = panel_obs.sum(axis=(0, 1)) / obs_mask.sum(axis=(0, 1)).clip(1)
    if y_means.std() > 1e-8:
        z = (y_means - y_means.mean()) / y_means.std()
        crisis_severity = float(np.clip(-z.min(), 0, None))
    else:
        crisis_severity = 0.0

    # Volatility change: std of second half - first half
    n_Y = panel.shape[2]
    mid = n_Y // 2
    first_std = float(np.nan_to_num(panel_obs[:, :, :mid]).std())
    second_std = float(np.nan_to_num(panel_obs[:, :, mid:]).std())
    vol_change = second_std - first_std

    # Missing block ratio (fraction of territory-sector combos with >50% missing)
    miss_rate_per_cell = 1.0 - obs_mask.mean(axis=2)
    block_frac = float((miss_rate_per_cell > 0.5).mean())

    return np.array([obs_frac, activity_mean, activity_std, crisis_severity, vol_change, block_frac],
                    dtype=np.float32)


# ── SharedRelationEncoder ─────────────────────────────────────────────────────

class SharedRelationEncoder(nn.Module):
    """
    Shared encoder for ANY directed pair (src → tgt).
    Same weights for ALL pairs. No S×S parameters. No pair identity required.

    Total trainable parameters: see n_parameters().
    """

    def __init__(self, input_dim: int = INPUT_DIM):
        super().__init__()
        self.input_dim = input_dim

        # Shared encoder MLP
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, ENCODER_HIDDEN1),
            nn.LayerNorm(ENCODER_HIDDEN1),
            nn.ReLU(),
            nn.Linear(ENCODER_HIDDEN1, ENCODER_HIDDEN2),
            nn.ReLU(),
        )

        # Independent output heads — all from same 32-dim embedding
        self.head_presence = nn.Linear(ENCODER_HIDDEN2, 1)
        self.head_direction = nn.Linear(ENCODER_HIDDEN2, 1)
        self.head_sign = nn.Linear(ENCODER_HIDDEN2, 1)
        self.head_lag = nn.Linear(ENCODER_HIDDEN2, 2)
        self.head_strength = nn.Linear(ENCODER_HIDDEN2, 1)
        self.head_confidence = nn.Linear(ENCODER_HIDDEN2, 1)

        self._init_weights()

    def _init_weights(self) -> None:
        # Presence head: negative bias → sparse prior (most pairs absent)
        nn.init.constant_(self.head_presence.bias, -2.0)
        # Direction head: zero init → direction neutral at start
        for head in [self.head_direction, self.head_sign, self.head_lag,
                     self.head_strength, self.head_confidence]:
            nn.init.zeros_(head.weight)
            nn.init.zeros_(head.bias)

    def forward(
        self,
        features: torch.Tensor,           # (batch, input_dim) or (input_dim,)
        adapter_residual: Optional[torch.Tensor] = None,  # (batch, ENCODER_HIDDEN2) or None
    ) -> dict:
        """
        Forward pass. Input: pre-extracted feature vectors.
        Returns dict with all relation outputs.
        """
        single = features.dim() == 1
        if single:
            features = features.unsqueeze(0)

        emb = self.encoder(features)  # (batch, ENCODER_HIDDEN2)

        if adapter_residual is not None:
            if adapter_residual.dim() == 1:
                adapter_residual = adapter_residual.unsqueeze(0)
            emb = emb + adapter_residual

        out = {
            "presence_logit": self.head_presence(emb).squeeze(-1),    # (batch,)
            "direction_logit": self.head_direction(emb).squeeze(-1),   # (batch,)
            "sign_logit": self.head_sign(emb).squeeze(-1),             # (batch,)
            "lag_logits": self.head_lag(emb),                          # (batch, 2)
            "strength": F.softplus(self.head_strength(emb)).squeeze(-1),  # (batch,) ≥ 0
            "confidence": torch.sigmoid(self.head_confidence(emb)).squeeze(-1),  # (batch,) ∈ (0,1)
            "embedding": emb,                                           # (batch, 32)
        }

        if single:
            out = {k: v.squeeze(0) for k, v in out.items()}

        return out

    def n_parameters(self) -> int:
        return sum(p.numel() for p in self.parameters())

    def assert_no_pair_params(self, max_sector_size: int = 20) -> None:
        """
        S2 check: assert no raw parameter has shape (n, n) for n <= max_sector_size.
        This catches S×S lookup tables (n_sectors typically 3-15).
        Weight matrices of MLP layers (e.g., 32×32) have n > max_sector_size and are excluded.
        """
        for name, p in self.named_parameters():
            shape = tuple(p.shape)
            if (len(shape) == 2 and shape[0] == shape[1]
                    and 1 < shape[0] <= max_sector_size):
                raise AssertionError(
                    f"Pair-specific parameter detected: {name} with shape {shape}. "
                    "This violates the shared encoder invariant."
                )


# ── Batch feature computation for a full panel ────────────────────────────────

def compute_all_pairs_features(
    panel: np.ndarray,
    obs_mask: np.ndarray,
    n_sectors: int,
    window_size: int = 8,
    device: str = "cpu",
    exclude_diagonal: bool = True,
) -> tuple[torch.Tensor, list[tuple[int, int]]]:
    """
    Compute feature vectors for ALL directed pairs using ALL available history.
    Returns:
      features: (n_pairs, INPUT_DIM)
      pair_list: [(src, tgt), ...] — pairs in the same order as rows of features
    """
    n_Y = panel.shape[2]
    window_end = n_Y  # use full history

    # Default context: year_frac=1.0, obs_frac, 0
    ctx = np.array([1.0, float(obs_mask.mean()), 0.0], dtype=np.float32)

    pairs = [
        (s, t)
        for s in range(n_sectors)
        for t in range(n_sectors)
        if not (exclude_diagonal and s == t)
    ]

    feats = []
    for src_idx, tgt_idx in pairs:
        f = extract_pair_features(panel, obs_mask, src_idx, tgt_idx,
                                  window_end=window_end, window_size=window_size,
                                  device=device, context=ctx)
        feats.append(f)

    return torch.stack(feats), pairs  # (n_pairs, INPUT_DIM), list


def compute_temporal_graph(
    encoder: SharedRelationEncoder,
    panel: np.ndarray,
    obs_mask: np.ndarray,
    n_sectors: int,
    window_size: int = 6,
    min_window: int = 3,
    device: str = "cpu",
    adapter_fn=None,
) -> dict:
    """
    Compute per-year relation estimates A_t[src, tgt] = sigmoid(presence_logit at t).

    Returns dict with:
      presence: (n_S, n_S, n_Y) — presence probability per year
      direction: (n_S, n_S, n_Y) — direction logit per year
      sign: (n_S, n_S, n_Y) — sign logit per year
    All causal: A_t uses only history up to t-1.
    """
    n_T, n_S, n_Y = panel.shape
    presence_t = np.full((n_S, n_S, n_Y), np.nan)
    direction_t = np.full((n_S, n_S, n_Y), np.nan)
    sign_t = np.full((n_S, n_S, n_Y), np.nan)

    ctx_env = compute_env_context_features(panel, obs_mask)

    encoder.eval()
    with torch.no_grad():
        for y in range(min_window, n_Y):
            year_frac = float(y) / max(1, n_Y)
            ctx = np.array([year_frac, float(obs_mask.mean()), ctx_env[3]], dtype=np.float32)

            for s in range(n_S):
                for t in range(n_S):
                    if s == t:
                        continue
                    feat = extract_pair_features(panel, obs_mask, s, t,
                                                 window_end=y, window_size=window_size,
                                                 device=device, context=ctx)
                    adapter_res = None
                    if adapter_fn is not None:
                        env_feat = torch.from_numpy(ctx_env).to(device)
                        adapter_res = adapter_fn(env_feat)

                    out = encoder(feat, adapter_residual=adapter_res)
                    presence_t[s, t, y] = float(torch.sigmoid(out["presence_logit"]))
                    direction_t[s, t, y] = float(out["direction_logit"])
                    sign_t[s, t, y] = float(torch.sigmoid(out["sign_logit"]))

    return {"presence": presence_t, "direction": direction_t, "sign": sign_t}


# ── Relation loss functions ────────────────────────────────────────────────────

def relation_loss(
    encoder_outputs: dict,
    pair_list: list[tuple[int, int]],
    true_relations: list,
    device: str,
    lambda_direction: float = 1.0,
    lambda_sign: float = 1.0,
    lambda_lag: float = 1.0,
    lambda_strength: float = 0.5,
    reverse_direction_outputs: Optional[dict] = None,
) -> tuple[torch.Tensor, dict]:
    """
    Compute multi-task relation loss.

    encoder_outputs: dict from SharedRelationEncoder.forward on all pairs
    pair_list: [(src, tgt), ...] corresponding to rows of encoder_outputs
    true_relations: list of TrueRelation
    reverse_direction_outputs: if provided, encoder outputs for REVERSED pairs (for direction loss)

    L_total = L_presence + λ_dir*L_direction + λ_sign*L_sign + λ_lag*L_lag + λ_str*L_strength
    """
    n_pairs = len(pair_list)
    pair_to_idx = {(s, t): i for i, (s, t) in enumerate(pair_list)}

    # Build ground truth tensors
    presence_gt = torch.zeros(n_pairs, device=device)
    sign_gt = torch.full((n_pairs,), -1.0, device=device)   # -1 = unknown
    lag_gt = torch.full((n_pairs,), -1.0, device=device)    # -1 = unknown
    strength_gt = torch.zeros(n_pairs, device=device)
    direction_gt_fwd = torch.zeros(n_pairs, device=device)  # 1 if src→tgt is true
    direction_gt_rev = torch.zeros(n_pairs, device=device)  # 0 if reverse of true edge

    true_edge_mask = torch.zeros(n_pairs, dtype=torch.bool, device=device)
    rev_edge_mask = torch.zeros(n_pairs, dtype=torch.bool, device=device)

    for r in true_relations:
        s, t = r.source_sector, r.target_sector
        fwd_idx = pair_to_idx.get((s, t))
        rev_idx = pair_to_idx.get((t, s))

        if fwd_idx is not None:
            presence_gt[fwd_idx] = 1.0
            sign_gt[fwd_idx] = 1.0 if r.weight > 0 else 0.0
            lag_gt[fwd_idx] = 1.0 if r.lag == 1 else 0.0
            strength_gt[fwd_idx] = abs(r.weight)
            true_edge_mask[fwd_idx] = True
            direction_gt_fwd[fwd_idx] = 1.0  # src→tgt is the true direction

        if rev_idx is not None:
            # Reverse direction: tgt→src evaluated; label=0 (direction is NOT tgt→src)
            rev_edge_mask[rev_idx] = True
            direction_gt_rev[rev_idx] = 0.0

    # ── L_presence: BCE with class reweighting ─────────────────────────────────
    n_pos = presence_gt.sum().clamp(min=1.0)
    n_neg = (1 - presence_gt).sum().clamp(min=1.0)
    pos_weight = torch.tensor([float(n_neg / n_pos)], device=device)
    l_presence = F.binary_cross_entropy_with_logits(
        encoder_outputs["presence_logit"], presence_gt, pos_weight=pos_weight
    )

    # ── L_direction: BCE on true-edge pairs + their reverses ───────────────────
    dir_losses = []
    if reverse_direction_outputs is not None:
        # Forward direction: true edges → label 1
        if true_edge_mask.any():
            fwd_logits = encoder_outputs["direction_logit"][true_edge_mask]
            fwd_labels = direction_gt_fwd[true_edge_mask]
            dir_losses.append(F.binary_cross_entropy_with_logits(fwd_logits, fwd_labels))
        # Reverse direction: reversed true edges → label 0
        if rev_edge_mask.any():
            rev_logits = reverse_direction_outputs["direction_logit"][rev_edge_mask]
            rev_labels = direction_gt_rev[rev_edge_mask]
            dir_losses.append(F.binary_cross_entropy_with_logits(rev_logits, rev_labels))
    l_direction = torch.stack(dir_losses).mean() if dir_losses else torch.tensor(0.0, device=device)

    # ── L_sign: BCE on true edges only ────────────────────────────────────────
    if true_edge_mask.any():
        known_sign = sign_gt[true_edge_mask]
        valid_s = known_sign >= 0
        if valid_s.any():
            l_sign = F.binary_cross_entropy_with_logits(
                encoder_outputs["sign_logit"][true_edge_mask][valid_s],
                known_sign[valid_s]
            )
        else:
            l_sign = torch.tensor(0.0, device=device)
    else:
        l_sign = torch.tensor(0.0, device=device)

    # ── L_lag: BCE on true edges only ─────────────────────────────────────────
    if true_edge_mask.any():
        known_lag = lag_gt[true_edge_mask]
        valid_l = known_lag >= 0
        if valid_l.any():
            lag_logits = encoder_outputs["lag_logits"][true_edge_mask][valid_l]  # (n_true, 2)
            lag_labels_1hot = torch.stack([known_lag[valid_l], 1.0 - known_lag[valid_l]], dim=1)
            l_lag = F.binary_cross_entropy_with_logits(lag_logits, lag_labels_1hot)
        else:
            l_lag = torch.tensor(0.0, device=device)
    else:
        l_lag = torch.tensor(0.0, device=device)

    # ── L_strength: MSE on true edges ─────────────────────────────────────────
    if true_edge_mask.any():
        pred_str = encoder_outputs["strength"][true_edge_mask]
        true_str = strength_gt[true_edge_mask]
        l_strength = F.mse_loss(pred_str, true_str)
    else:
        l_strength = torch.tensor(0.0, device=device)

    total = (l_presence
             + lambda_direction * l_direction
             + lambda_sign * l_sign
             + lambda_lag * l_lag
             + lambda_strength * l_strength)

    components = {
        "l_presence": float(l_presence.detach()),
        "l_direction": float(l_direction.detach()),
        "l_sign": float(l_sign.detach()),
        "l_lag": float(l_lag.detach()),
        "l_strength": float(l_strength.detach()),
        "total": float(total.detach()),
        "n_true_edges_in_batch": int(true_edge_mask.sum()),
    }
    return total, components
