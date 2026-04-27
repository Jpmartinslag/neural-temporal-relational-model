# HERALD Territorial Forecasting

This repository is now focused on **HERALD**:

```text
Heterogeneous Economic Relational Adaptive Learning for territorial Dynamics
```

The active task is annual forecasting of establishment creations by French employment zone (`ZE2020`, 280 zones), with forecast horizon `t+1`.

The supervised target is:

```text
side_establishment_creations_official
```

Legacy prototypes, old fixed-graph experiments, REI/SITADEL exploratory baselines, and obsolete reports were moved to:

```text
old/legacy_before_herald_focus_2026_04_27/
```

The move manifest is:

```text
old/legacy_before_herald_focus_2026_04_27/MANIFEST.csv
```

No legacy file was deleted. This cleanup is the transition point from exploratory modeling to HERALD-focused training and publication work.

## Current Status

Completed:

- Repository active surface reduced to HERALD + paper comparators.
- Legacy reports, fixed-graph prototypes, REI/SITADEL exploratory runs, old tensors, and obsolete predictions moved to `old/`.
- HERALD V3 training script implemented with dynamic adaptive graph `A_t`.
- Learning-curve logging added to future HERALD V3 runs.
- French validation dashboard generated.
- Statistical evidence package generated.
- Ridge AR, DCRNN, and Dynamic STGNN comparator artifacts retained.

Next phase:

- Train HERALD V4 / stress-test variants on stronger hardware.
- Use the current dashboard and statistical package as the validation baseline.
- Avoid reintroducing legacy prototype files into the active surface unless explicitly needed.

## Active Scientific Frame

HERALD is the proposed architecture. The article should compare HERALD against:

- `Ridge AR`: autoregressive tabular baseline.
- `DCRNN`: graph recurrent baseline.
- `Dynamic STGNN`: graph-aware neural baseline.
- `HERALD`: proposed dynamic adaptive graph model.

Internal HERALD development versions (`HERALD V1/V2`) are not part of the article narrative. They remain in `old/` only for traceability.

The article framing should be:

```text
Ridge AR / DCRNN / Dynamic STGNN are baselines.
HERALD is the proposed model.
HERALD ablations validate the contribution of quarterly signals, dynamic graph learning, temporal smoothing, and message passing.
```

## Active Files

### Training

```bash
python3 src/data/train_herald_v3.py
```

Main script:

```text
src/data/train_herald_v3.py
```

Comparator scripts retained for paper baselines:

```text
src/data/evaluate_dynamic_feature_panel_baselines_v1.py
src/data/train_dynamic_stgnn_models_v1.py
```

Feature-panel builder retained for reproducibility:

```text
src/data/build_dynamic_stgnn_feature_panel_v1.py
```

### Visualization And Evidence

```text
src/data/plot_herald_v3_dashboard.py
src/data/analyze_herald_v3_statistical_evidence.py
src/data/herald_map_utils.py
```

Main dashboard, in French:

```text
reports/figures/herald_v3_finetuning_dashboard_v1.html
```

Main statistical report:

```text
reports/HERALD_V3_STATISTICAL_EVIDENCE_V1.md
```

Statistical evidence outputs:

```text
reports/herald_v3_dm_tests_v1.csv
reports/herald_v3_zone_strata_v1.csv
reports/herald_v3_gamma_stability_v1.csv
reports/herald_v3_top_neighbors_v1.csv
reports/herald_v3_statistical_evidence_v1.json
```

## Active Data

The active training/evaluation surface is intentionally small:

```text
data/processed/dynamic_stgnn_feature_panel_v1.csv
metadata/dynamic_stgnn_walk_forward_splits_v1.csv
data/processed/graph_adjacency_core_v0.csv
data/processed/graph_adjacency_mobility_v0.csv
data/processed/graph_node_index_core_v0.csv
data/raw/employment/urssaf/urssaf_emploi_ze_quarterly_raw.csv
```

Current HERALD outputs are kept in:

```text
data/processed/herald_v3_predictions_*_v1.csv
data/processed/herald_v3_internals_*_v1.npz
reports/herald_v3_*_v1.*
```

Paper comparator outputs kept active:

```text
data/processed/dynamic_feature_panel_baseline_predictions_v1.csv
data/processed/dynamic_stgnn_model_predictions_seed_*_v1.csv
reports/dynamic_feature_panel_baseline_metrics_v1.json
reports/dynamic_stgnn_model_metrics*_v1.json
```

## Regenerate Dashboard

```bash
python3 src/data/plot_herald_v3_dashboard.py
```

The dashboard contains:

- predictive comparison against Ridge AR, DCRNN, and Dynamic STGNN;
- HERALD ablations;
- seed stability;
- dynamic graph map on French ZE2020 boundaries;
- graph movement over time;
- gate/message-share diagnostics;
- Diebold-Mariano validation;
- zone-size stratification;
- gamma stability;
- top adaptive neighbors;
- training curves when available.

## Regenerate Statistical Evidence

```bash
python3 src/data/analyze_herald_v3_statistical_evidence.py
```

## Train HERALD Full

Example:

```bash
python3 src/data/train_herald_v3.py \
  --ablation full \
  --seed 0 \
  --epochs 800 \
  --hidden-dim 32 \
  --q-hidden 16 \
  --attn-dim 8 \
  --lr 0.001 \
  --weight-decay 1e-4 \
  --huber-delta 300 \
  --smooth-lambda 0.1 \
  --top-k 10
```

Training now writes learning curves to:

```text
reports/herald_v3_training_history_<ablation>_seed_<seed>_v1.csv
```

## Current Evidence Summary

Using the existing 2021-2024 walk-forward artifacts:

```text
Ridge AR WMAPE:  0.06608
HERALD WMAPE:    0.02250
Relative gain:   65.96%
DM p-value:      2.74e-33
```

The strongest economic finding so far:

```text
gamma_mob mean ~= 1.087
gamma_geo mean ~= 0.056
```

Interpretation: the learned graph is anchored much more by commuting mobility than by simple geographic contiguity.

Current validated claim:

```text
HERALD outperforms Ridge AR and neural graph baselines on the 2021-2024 walk-forward task.
The ablation battery supports the value of message passing, quarterly labor-market signals, and temporal graph smoothing.
The learned graph is economically coherent because it is anchored more strongly in commuting mobility than in geographic adjacency.
```

Claim not yet final:

```text
HERALD has not yet fully established a causal interpretation of regime/crisis shifts in A_t.
The V4 phase should stress-test this claim on stronger hardware.
```

## Repository Hygiene Rule

Active root-level files should support only:

1. HERALD training.
2. HERALD visualization.
3. HERALD statistical evidence.
4. Baseline comparison needed for the paper.

Everything else belongs in `old/`.
