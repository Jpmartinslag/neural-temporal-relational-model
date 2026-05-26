# HERALD Phase 2R Confirmatory Plan

Phase 2R closes the current exploratory loop. It does not introduce a new
architecture family. It reruns the candidates that survived Phase 2O/2P/2Q with
more seeds and fair controls.

## Thesis Under Test

The defensible thesis is:

> HERALD no-flags is best framed as Ridge plus a learned residual correction,
> calibrated fold-by-fold using training years only.

The thesis not under claim is:

> HERALD has already learned a fully autonomous economic auditor or can select
> its latent dimensionality reliably.

## Configs

| Label | Role |
|---|---|
| `ridge_side2` | Ridge-only fallback inside the same pipeline |
| `L3_gate` | legacy no-flags reference with latent dim 3 |
| `L5_gate_no_auditor` | main no-shrinkage reference |
| `L5_trainopt` | primary candidate: no-flags residual shrinkage selected on train years |
| `HC5_trainopt` | best raw mean/2025 trade-off from Phase 2O |
| `AUD_alpha_trainopt` | auditor alpha-neutral guard with shrinkage |
| `AUD_both_trainopt` | auditor both-mode guard with shrinkage |
| `L4_a10g` | A10-guard control |
| `side2_AUDboth` | Phase 2Q input/architecture robustness control |
| `clean_flags_side2` | manual flags with the same clean SIDE2 inputs |
| `clean_flags_side2_trainopt` | clean manual flags plus same residual shrinkage mechanism |
| `extended_flags_current` | historical broader manual-flags control |
| `extended_flags_current_trainopt` | historical broader manual-flags control plus shrinkage |

Default size: 13 configs x 20 seeds = 260 runs.

## Acceptance Rule

Promote `L5_trainopt` only if it keeps:

- paired mean WMAPE improvement vs `L5_gate_no_auditor`;
- no material degradation on 2021;
- no material degradation on A10;
- seed stability comparable to the controls;
- a plausible train-only shrinkage distribution, not a boundary artifact.

`HC5_trainopt` can be reported as a trade-off if it remains best on mean/2025 but
continues to hurt 2021.

Auditor variants are stabilizers unless they dominate mean, 2021, 2025 and A10
together. They should not be described as autonomous regime discovery.

## Commands

```bash
STAMP=$(date +%Y%m%d_%H%M%S) bash hpc/regime/submit_herald_phase2r_confirmatory.sh
python3 hpc/regime/aggregate_herald_regime_results.py --root <OUT_ROOT>
python3 hpc/regime/audit_herald_phase2r_confirmatory.py --root <OUT_ROOT> --strict
```
