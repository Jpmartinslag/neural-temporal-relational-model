# HERALD 53 - France ZE2020 temporal bipartite reconstruction result

**Date:** 2026-07-24  
**Decision:** DEC-079  
**Status:** `COMPLETE_GATE_FAIL_MASKED_RECONSTRUCTION_SPECIFICATION_CLOSED`

## 1. Question

The pre-registered test asked whether a small nonlinear model can reconstruct
three artificially hidden ZE-sector shares from the directly observed current
bipartite composition and its one-year lag, beyond linear, compositional,
single-information-source, and shuffled controls.

This is a representation preflight. It is not production imputation, a
forecast, a causal test, or a dynamic graph-neural model.

## 2. Execution and integrity

- Meso smoke: job `7782201`, exit `0:0`, 42 seconds
- Meso full array: `7782372`, five tasks, all exit `0:0`
- runtime per seed: 32m59s--38m31s
- stderr: empty for every task
- seeds: 42--46
- evaluation years: 2017--2025
- five fixed ZE-disjoint folds
- views: nine
- metric rows: 2,025
- comparisons per view: 225
- evaluated hidden cells per view: 37,800
- duplicate metric keys: zero
- finite outputs: complete
- train/test ZE overlap: zero
- exactly three hidden sectors per ZE-year: confirmed
- identical hidden targets across views: confirmed
- maximum compositional error: `2.22e-16`
- MLP convergence: 219/225 (`97.33%`)

The six non-converged full-MLP fits reached the fixed 300-epoch ceiling. Removing
them does not change the decision: among the remaining 219 comparisons, the
full MLP still beats temporal persistence in only `2.28%`.

The artificial masks are distributed across all nine sectors for every seed.
The source panel remains untouched, and an explicit mutation test confirms
that changing 2021 cannot change samples constructed for 2020.

## 3. Aggregate result

Lower error is better.

| View | Masked MAE | Masked RMSE | Allocation MAE | Convergence |
|---|---:|---:|---:|---:|
| `temporal_persistence` | 0.009652 | 0.013349 | 0.030838 | 100% |
| `mlp_bipartite` | 0.013498 | 0.018250 | 0.042119 | 97.33% |
| `sector_mean_closure` | 0.014632 | 0.020720 | 0.046526 | 100% |
| `mlp_sector_shuffle` | 0.016030 | 0.021533 | 0.050074 | 99.56% |
| `mlp_current_only` | 0.017057 | 0.023756 | 0.052959 | 100% |
| `mlp_temporal_shuffle` | 0.018747 | 0.025627 | 0.058056 | 100% |
| `ridge_bipartite` | 0.020675 | 0.027883 | 0.062968 | 100% |
| `mlp_history_only` | 0.022628 | 0.030552 | 0.065880 | 100% |
| `random_closure` | 0.073102 | 0.097801 | 0.216186 | 100% |

## 4. Registered gates

| Condition | Result | Decision |
|---|---:|---|
| integrity, masks, composition, target identity, ZE separation | all true | PASS |
| lower aggregate MAE than Ridge | lift `+0.007177`; 99.1% wins | PASS |
| lower aggregate MAE than sector-mean closure | lift `+0.001134`; 70.7% wins | PASS |
| lower aggregate MAE than temporal persistence | lift `-0.003846`; 2.2% wins | **FAIL** |
| beat history-only MLP | lift `+0.009130`; 100% wins | PASS |
| beat current-only MLP | lift `+0.003560`; 92.4% wins | PASS |
| degrade under sector shuffle | `+0.002532`; 94.2% | PASS |
| degrade under temporal shuffle | `+0.005249`; 100% | PASS |
| beat Ridge and both information ablations by year | 9/9 years | PASS |
| seed MAE coefficient of variation at most 20% | 0.64% | PASS |

The five MLP victories over temporal persistence all occur in 2022. Persistence
is better in every paired comparison in the other eight evaluation years.
Because every registered condition is required, the gate fails.

## 5. Interpretation

The ablations and shuffles provide evidence that the MLP uses both current
sector composition and temporal history: removing either source or destroying
their identities consistently increases reconstruction error. The nonlinear
model also strongly improves over the matched Ridge model.

However, the observed ZE-sector compositions are highly persistent. The same
ZE's previous-year sector allocation remains substantially more accurate than
the learned representation. Therefore the experiment does not justify adding
a neural temporal bipartite layer for this reconstruction task.

This is a partial methodological finding, not a model promotion:

- joint temporal and compositional information is detectable;
- nonlinear integration outperforms matched linear and shuffled controls;
- the simplest economic-memory control remains decisively stronger;
- the tested masked-reconstruction specification is closed;
- no production imputation, dynamic GNN, recommendation, causal, or policy
  claim is authorized.

Reopening requires a materially different learning objective whose value is
not equivalent to reproducing a highly persistent annual composition. Epoch,
width, mask-rate, or threshold tuning on this result is not a valid reopen
condition.

## 6. Artifacts

```text
hpc_results/fr_ze2020_temporal_bipartite_full_20260724_150150/
```

The directory is collected locally, gitignored, and retained outside the
canonical source tree. Combined-output SHA-256 checksums:

```text
metrics  6da6962b0378e9e62dc8ee4b4b9d226e840fc16fbdc9760b9411aae33f37e702
summary  7b64d90a8109a7deb169c59e6db8fe025a6b6212e797f9bf15a1e35bfa2c6dad
gate     8789e442b7afb16df11c3a0d9df444f34e0c2527386435d4fdc7ba2da5724756
```
