# HERALD — Graph-Temporal FR Adjacency Preflight

**Date:** 2026-06-11
**Decision:** `FR_ADJACENCY_READY`
**DEC:** DEC-028
**Scope:** FR, schema 2.0, eval_years 2021–2025 (5 folds, candidate S1-FR years)

---

## 1. Purpose

This audit validates that the schema 2.0 adjacency tensors for France are:
- Structurally correct (symmetric, non-negative, no NaN);
- Causally clean (window ending at obs_year < eval_year);
- Temporally varying across sequence steps;
- Not forced to be fully connected (isolated nodes are allowed if economically correct);
- Ready for GConvGRU/EvolveGCN-H without further data preparation.

It does NOT train any model. It does NOT provide scientific evidence about forecast improvement.

---

## 2. Data

| Parameter | Value |
|-----------|-------|
| Country | FR |
| Regions | 280 zones d'emploi (ZE) |
| Sectors | 9 (BE, FZ, GI, JZ, KZ, LZ, MN, OQ, RU) |
| Source | `sector_panel_fr_nl_pt.csv` |
| Eval years audited | 2021, 2022, 2023, 2024, 2025 |
| T_SEQ | 5 time steps per fold |
| WINDOW | 5-year rolling causal window |
| MIN_PERIODS | 4 |
| Representation | positive_topk (primary), k=5 |
| k sensitivity | {3, 5, 10} |

**Observation years per fold:**

| Eval year | Observation years (T=5) |
|-----------|------------------------|
| 2021 | [2016, 2017, 2018, 2019, 2020] |
| 2022 | [2017, 2018, 2019, 2020, 2021] |
| 2023 | [2018, 2019, 2020, 2021, 2022] |
| 2024 | [2019, 2020, 2021, 2022, 2023] |
| 2025 | [2020, 2021, 2022, 2023, 2024] |

All observation years < eval_year — causal contract satisfied.

---

## 3. Degree Distribution Note

After applying top-k selection and symmetric union, each node *selects* at most k=5 neighbours. However, a node may *receive* edges from other nodes' selections. The final degree after symmetrization can therefore exceed k.

Correct statement: **each node selects at most k=5 positive-correlation neighbours before symmetrization; the final degree can exceed k due to received selections.**

This is the expected and correct behaviour of `_top_k_symmetric()`.

---

## 4. Adjacency Statistics at Snapshot obs_year = eval_year − 1 (k=5)

### FR/2021 — snapshot at obs_year=2020

| Sector | Edges | deg_min | deg_mean | deg_max | Isolated | Components | GCC | Sym | ≥0 | noNaN |
|--------|-------|---------|----------|---------|----------|-----------|-----|-----|----|-------|
| BE | 884 | 4 | 6.0 | 10 | 0 | 1 | 280 | ✓ | ✓ | ✓ |
| FZ | 904 | 4 | 6.1 | 10 | 0 | 1 | 280 | ✓ | ✓ | ✓ |
| GI | 853 | 4 | 5.7 | 9 | 0 | 1 | 280 | ✓ | ✓ | ✓ |
| JZ | 878 | 3 | 5.9 | 14 | 0 | 1 | 280 | ✓ | ✓ | ✓ |
| KZ | 882 | 4 | 5.9 | 10 | 0 | 1 | 280 | ✓ | ✓ | ✓ |
| LZ | 886 | 4 | 5.9 | 11 | 0 | 1 | 280 | ✓ | ✓ | ✓ |
| MN | 894 | 4 | 6.0 | 11 | 0 | 1 | 280 | ✓ | ✓ | ✓ |
| OQ | 872 | 4 | 5.8 | 11 | 0 | 1 | 280 | ✓ | ✓ | ✓ |
| RU | 905 | 4 | 6.2 | 10 | 0 | 1 | 280 | ✓ | ✓ | ✓ |

### FR/2022 — snapshot at obs_year=2021

| Sector | Edges | deg_min | deg_mean | deg_max | Isolated | Components | GCC |
|--------|-------|---------|----------|---------|----------|-----------|-----|
| BE | 893 | 4 | 6.0 | 10 | 0 | 1 | 280 |
| FZ | 877 | 3 | 5.9 | 10 | 0 | 1 | 280 |
| GI | 846 | 4 | 5.6 | 10 | 0 | 1 | 280 |
| JZ | 896 | 4 | 6.0 | 13 | 0 | 1 | 280 |
| KZ | 884 | 4 | 6.0 | 11 | 0 | 1 | 280 |
| LZ | 882 | 4 | 5.9 | 10 | 0 | 1 | 280 |
| MN | 907 | 3 | 6.1 | 10 | 0 | 1 | 280 |
| OQ | 885 | 3 | 6.0 | 11 | 0 | 1 | 280 |
| RU | 914 | 4 | 6.2 | 10 | 0 | 1 | 280 |

### FR/2023 — snapshot at obs_year=2022

| Sector | Edges | deg_min | deg_mean | deg_max | Isolated | Components | GCC |
|--------|-------|---------|----------|---------|----------|-----------|-----|
| BE | 896 | 4 | 6.0 | 10 | 0 | 1 | 280 |
| FZ | 879 | 4 | 5.9 | 10 | 0 | 1 | 280 |
| GI | 911 | 2 | 6.2 | 11 | 0 | 1 | 280 |
| JZ | 888 | 4 | 6.0 | 11 | 0 | 1 | 280 |
| KZ | 894 | 3 | 6.0 | 11 | 0 | 1 | 280 |
| LZ | 874 | 4 | 5.9 | 11 | 0 | 1 | 280 |
| MN | 896 | 4 | 6.0 | 11 | 0 | 1 | 280 |
| OQ | 900 | 3 | 6.1 | 11 | 0 | 1 | 280 |
| RU | 927 | 3 | 6.3 | 11 | 0 | 1 | 280 |

### FR/2024 — snapshot at obs_year=2023

| Sector | Edges | deg_min | deg_mean | deg_max | Isolated | Components | GCC |
|--------|-------|---------|----------|---------|----------|-----------|-----|
| BE | 892 | 4 | 6.0 | 10 | 0 | 1 | 280 |
| FZ | 885 | 4 | 6.0 | 10 | 0 | 1 | 280 |
| GI | 916 | 4 | 6.3 | 11 | 0 | 1 | 280 |
| JZ | 882 | 4 | 5.9 | 11 | 0 | 1 | 280 |
| KZ | 896 | 4 | 6.0 | 11 | 0 | 1 | 280 |
| LZ | 894 | 3 | 6.0 | 12 | 0 | 1 | 280 |
| MN | 917 | 3 | 6.2 | 11 | 0 | 1 | 280 |
| OQ | 918 | 4 | 6.2 | 12 | 0 | 1 | 280 |
| RU | 930 | 2 | 6.4 | 10 | 0 | 1 | 280 |

### FR/2025 — snapshot at obs_year=2024

| Sector | Edges | deg_min | deg_mean | deg_max | Isolated | Components | GCC |
|--------|-------|---------|----------|---------|----------|-----------|-----|
| BE | 904 | 4 | 6.1 | 11 | 0 | 1 | 280 |
| FZ | 875 | 4 | 5.9 | 10 | 0 | 1 | 280 |
| GI | 929 | 3 | 6.4 | 12 | 0 | 1 | 280 |
| JZ | 881 | 4 | 5.9 | 10 | 0 | 1 | 280 |
| KZ | 895 | 3 | 6.0 | 11 | 0 | 1 | 280 |
| LZ | 903 | 3 | 6.1 | 10 | 0 | 1 | 280 |
| MN | 889 | 3 | 6.0 | 10 | 0 | 1 | 280 |
| OQ | 915 | 4 | 6.2 | 11 | 0 | 1 | 280 |
| RU | 928 | 3 | 6.4 | 10 | 0 | 1 | 280 |

---

## 5. Raw Pearson Correlation Statistics (before positive_topk)

| Eval year | neg_fraction_mean | density_mean (|r|>0.3) | nan_fraction |
|-----------|-------------------|------------------------|-------------|
| FR/2021 | 0.389 | 0.621 | 0.000 |
| FR/2022 | 0.354 | 0.645 | 0.000 |
| FR/2023 | 0.312 | 0.669 | 0.000 |
| FR/2024 | 0.255 | 0.692 | 0.000 |
| FR/2025 | 0.263 | 0.693 | 0.000 |

- **26–39% of off-diagonal Pearson correlations are negative.** Positive_topk representation is required and correct: it selects only positive, high-weight connections.
- **0% NaN** — FR has complete sector coverage across all observation years in 2016–2024.
- **Trend**: negative fraction decreases over time (2021→2025), suggesting increasing aggregate co-movement coherence.

---

## 6. k-Sensitivity Analysis (snapshot at eval_year − 1)

| Eval year | k=3 (edges) | k=3 (isolated) | k=5 (edges) | k=5 (isolated) | k=10 (edges) | k=10 (isolated) |
|-----------|------------|----------------|------------|----------------|-------------|-----------------|
| FR/2021 | 4898 | 0 | 7958 | 0 | 15612 | 0 |
| FR/2022 | 4939 | 0 | 7984 | 0 | 15676 | 0 |
| FR/2023 | 4930 | 0 | 8065 | 0 | 15910 | 0 |
| FR/2024 | 5005 | 0 | 8130 | 0 | 16102 | 0 |
| FR/2025 | 4958 | 0 | 8119 | 0 | 16090 | 0 |

- **0 isolated nodes at k=3, 5, and 10** for all eval years. FR is well-connected at all sparsity levels.
- Edge count increases monotonically with k, as expected.
- The choice k=5 (primary) is not fragile: the graph is well-connected from k=3.

_Compare to NL: NL/2019 had 40 isolated nodes (all in OQ sector) at k=5 due to sparse early sector data. FR shows no such sparsity._

---

## 7. Temporal Variation of Adjacency Sequence

For all 5 eval years, `adjacency_seq[0]` (obs_year = eval_year−5) differs from `adjacency_seq[4]` (obs_year = eval_year−1). The adjacency sequence is not static — it reflects the rolling causal window and provides genuine temporal variation for the GNN.

This confirms criterion 7: the sequence is temporally informative, not a repeated copy.

---

## 8. Feature and Target Coverage

| Fold | n_observed_targets | target_mask_sum |
|------|-------------------|----------------|
| FR/2021 | 280 | 280 |
| FR/2022 | 280 | 280 |
| FR/2023 | 280 | 280 |
| FR/2024 | 280 | 280 |
| FR/2025 | 280 | 280 |

All 280 FR regions have observed targets in all 5 eval years. Target coverage is complete.

---

## 9. Fail-Closed Criteria (k=5)

| Criterion | Description | FR/2021 | FR/2022 | FR/2023 | FR/2024 | FR/2025 |
|-----------|-------------|---------|---------|---------|---------|---------|
| C1 | Perfect symmetry A = Aᵀ | ✓ | ✓ | ✓ | ✓ | ✓ |
| C2 | Zero negative off-diagonal weights | ✓ | ✓ | ✓ | ✓ | ✓ |
| C3 | Zero NaN/Inf in materialized edges | ✓ | ✓ | ✓ | ✓ | ✓ |
| C4 | Target coverage complete or masked | ✓ (280/280) | ✓ | ✓ | ✓ | ✓ |
| C5 | No sector entirely empty in all snapshots | ✓ | ✓ | ✓ | ✓ | ✓ |
| C6 | Isolated nodes and components documented | ✓ (0 iso, 1 comp) | ✓ | ✓ | ✓ | ✓ |
| C7 | Sequence varies temporally (adj[0] ≠ adj[4]) | ✓ | ✓ | ✓ | ✓ | ✓ |
| C8 | Past snapshot unchanged by future data | ✓ (T24 test) | ✓ | ✓ | ✓ | ✓ |

**All 8 criteria pass for all 5 eval years.**

---

## 10. Contrast with NL Engineering Smoke

| Dimension | NL (E0-v2) | FR (this audit) |
|-----------|-----------|----------------|
| n_regions | 40 | 280 |
| n_sectors | 9 | 9 |
| Isolated @k=5 | 40 (OQ sector, 2019) | 0 (all years) |
| neg_fraction | 29–36% | 26–39% |
| nan_fraction @snap | up to 11.1% (2019) | 0.0% (all) |
| Connected | 1 comp after 2019 | 1 comp (all) |
| Eval years audited | 3 | 5 |

FR has better data coverage than NL (no sparse early sector data), giving denser and more complete co-growth windows.

---

## 11. Decision

**`FR_ADJACENCY_READY`**

All 8 fail-closed criteria pass for all 5 candidate S1-FR eval years (2021–2025). The positive_topk adjacency representation is correct, causally clean, temporally varying, fully covered, and structurally sound for 280 FR regions and 9 sectors.

**Next step:** Implement GConvGRU (A1a), EvolveGCN-H (A1b), and A0-neural using schema 2.0 tensors and the contract in `HERALD_GRAPH_TEMPORAL_A1_IMPLEMENTATION_CONTRACT.md`. Do not execute S1-FR or HPC yet.

---

## 12. Artifacts

| Artifact | Path | Status |
|----------|------|--------|
| Schema 2.0 FR fold NPZs | `data/processed/graph_temporal_v2/FR/{2021..2025}/fold_v2.npz` | Regenerable — not versioned in git |
| Manifest v2 | `data/processed/graph_temporal_v2/manifest_v2.json` | Updated with FR folds and adjacency audit |
| This report | `reports/HERALD_GRAPH_TEMPORAL_FR_ADJACENCY_PREFLIGHT.md` | Versioned |

**Regeneration command (from repo root):**

```bash
python3 -m src.data.european_panel.build_graph_temporal_v2 \
  --countries FR \
  --eval-years 2021 2022 2023 2024 2025
```

Or via Python API:

```python
from src.data.european_panel.build_graph_temporal_v2 import export_v2, DEFAULT_SECTOR_PANEL, DEFAULT_OUT
export_v2(
    countries=['FR'],
    eval_years_by_country={'FR': [2021, 2022, 2023, 2024, 2025]},
    sector_panel_path=DEFAULT_SECTOR_PANEL,
    out_dir=DEFAULT_OUT.parent / 'graph_temporal_v2',
    t_seq=5, window=5, min_periods=4, k=5,
    run_adjacency_audit=True,
)
```
