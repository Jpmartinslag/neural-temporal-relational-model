# HERALD 49 - France ZE2020 context-conditioned sector-relation result

**Date:** 2026-07-23  
**Decision:** DEC-077  
**Status:** `COMPLETE_GATE_FAIL_TARGET_FEATURE_SPECIFICATION_CLOSED`

## 1. Question

The registered test asked whether lagged source-sector change carries
transferable information about target-sector growth after conditioning on the
lagged economic composition of a ZE2020.

This is an association and predictive-precedence test. It is not a causal test.

## 2. Execution

- Meso array: `7781010`
- seeds: 42--46
- evaluation years: 2019--2025
- five ZE-disjoint folds
- registered comparisons: 175 per view
- metric rows: 1,050
- runtime per seed: 3h13m--3h29m
- exit code: `0:0` for all five tasks
- stderr: empty for all five tasks
- all substantive and shuffled models converged
- train/test ZE overlap: zero
- test populations: identical across views

The direct-execution import defect found in the first audit invocation was
corrected in the audit script. Six focused HPC tests pass after the correction.
The model outputs themselves were complete and did not require rerunning.

## 3. Aggregate result

Lower MAE is better.

| View | Mean MAE | Mean R2 | Convergence |
|---|---:|---:|---:|
| `pooled_linear_relation` | 0.177429 | -0.097388 | 100% |
| `context_conditioned_mlp` | 0.274963 | -3.161535 | 100% |
| `context_shuffled_mlp` | 0.278184 | -3.704550 | 100% |
| `source_shuffled_mlp` | 0.289329 | -5.022892 | 100% |
| `no_source_mlp` | 0.296391 | -4.321679 | 100% |
| `target_shuffled_mlp` | 0.304271 | -3.783966 | 100% |

The context-conditioned MLP improved mean MAE over the no-source MLP by
0.021429 and won 61.1% of paired comparisons. This limited result is not enough
to identify the source-sector relation or the ZE-context interaction.

## 4. Registered gates

| Condition | Result | Decision |
|---|---:|---|
| finite metrics, complete views/populations, zero ZE overlap, convergence | all true | PASS |
| lower mean MAE than `no_source_mlp` | +0.021429 lift | PASS |
| lower mean MAE than `pooled_linear_relation` | -0.097534 lift; 1/175 wins | FAIL |
| source shuffle degrades in at least 60% of pairs | 53.7% | FAIL |
| context shuffle degrades in at least 60% of pairs | 49.1% | FAIL |
| target shuffle degrades by at least 5% and loses at least 80% | +15.5% mean degradation, 66.3% losses | FAIL |

The pooled linear control outperformed the nonlinear view for every seed and
every evaluation year. Context-shuffle degradation changed sign across years
and seeds, so the aggregate difference cannot be treated as stable
ZE-conditioned relation evidence.

## 5. Interpretation

The experiment shows a small amount of nonlinear predictive information beyond
the matched no-source MLP. It does not show that this information comes
reliably from the source-sector lag or from its interaction with ZE context.
The much stronger pooled linear control shows that added nonlinearity is not
justified for this target and feature representation.

Therefore:

- the current target-growth and lagged-composition specification is closed;
- no temporal relation encoder is authorized from DEC-077;
- Phase 7 is not rerun or reinterpreted;
- other sector-relation hypotheses remain possible only with a materially
  different economic representation and a new pre-registered decision;
- no structural causality, dynamic graph-neural validation, territorial
  recommendation, or policy claim is authorized.

## 6. Artifacts

```text
hpc_results/fr_ze2020_context_sector_relation_20260722_220553/
fr_ze2020_context_sector_relation_hpc_audit_report.json
```

The result directory is local/remote and gitignored. The audit report SHA-256
is `9c2390cd5be5257af6f4396679a71de9469209c90f93829d3444639ad78713c5`.
