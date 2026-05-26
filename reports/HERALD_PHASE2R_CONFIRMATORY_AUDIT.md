# HERALD Phase 2R Confirmatory Audit

STRICT PASS

## Main Read

- Best mean WMAPE: `HC5_trainopt` = 0.020094.
- `L5_trainopt` vs `L5_gate_no_auditor`: mean delta -0.000375, wins 17/20, p=0.002818, bootstrap CI95 [-0.000575, -0.000170].
- Pareto labels over mean/2021/2025/A10: HC5_trainopt, L5_trainopt, L5_gate_no_auditor, AUD_alpha_trainopt, L4_a10g.

## Summary

| Label | N | Mean | Std | 2021 | 2022 | 2023 | 2024 | 2025 | A10 | shrink 2021 | shrink 2025 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| HC5_trainopt | 20 | 0.020094 | 0.001330 | 0.036884 | 0.017649 | 0.016261 | 0.017825 | 0.011853 | 0.159532 | 0.953 | 0.963 |
| L5_trainopt | 20 | 0.020233 | 0.001703 | 0.035020 | 0.018300 | 0.016001 | 0.019320 | 0.012525 | 0.158238 | 0.965 | 0.963 |
| L5_gate_no_auditor | 20 | 0.020608 | 0.001767 | 0.034888 | 0.018820 | 0.016612 | 0.019618 | 0.013101 | 0.158233 | 1.000 | 1.000 |
| AUD_alpha_trainopt | 20 | 0.020745 | 0.002126 | 0.033779 | 0.020637 | 0.017923 | 0.019530 | 0.011856 | 0.156780 | 0.963 | 0.972 |
| AUD_both_trainopt | 20 | 0.020835 | 0.002122 | 0.034213 | 0.020895 | 0.017054 | 0.020057 | 0.011955 | 0.158666 | 0.965 | 0.972 |
| L4_a10g | 20 | 0.021135 | 0.002082 | 0.034820 | 0.020013 | 0.016789 | 0.021082 | 0.012969 | 0.156460 | 1.000 | 1.000 |
| L3_gate | 20 | 0.021264 | 0.001743 | 0.035403 | 0.020197 | 0.016878 | 0.019897 | 0.013943 | 0.157675 | 1.000 | 1.000 |
| side2_AUDboth | 20 | 0.021330 | 0.002112 | 0.034182 | 0.021744 | 0.017910 | 0.020265 | 0.012550 | 0.158665 | 1.000 | 1.000 |
| clean_flags_side2 | 20 | 0.027600 | 0.002580 | 0.036019 | 0.033284 | 0.027907 | 0.027578 | 0.013214 | 0.166599 | 1.000 | 1.000 |
| clean_flags_side2_trainopt | 20 | 0.027688 | 0.002466 | 0.036508 | 0.033013 | 0.028805 | 0.027111 | 0.013001 | 0.166841 | 0.953 | 0.957 |
| extended_flags_current_trainopt | 20 | 0.029332 | 0.003235 | 0.035774 | 0.030564 | 0.033870 | 0.024623 | 0.021830 | 0.174932 | 0.930 | 0.927 |
| extended_flags_current | 20 | 0.029686 | 0.003423 | 0.035642 | 0.028853 | 0.033278 | 0.026498 | 0.024159 | 0.174546 | 1.000 | 1.000 |
| ridge_side2 | 20 | 0.056691 | 0.000000 | 0.071763 | 0.071474 | 0.071574 | 0.036200 | 0.032446 | 0.175036 | 1.000 | 1.000 |

## Interpretation Rule

- Promote `L5_trainopt` only if it keeps paired mean gain vs `L5_gate_no_auditor` and is non-inferior on 2021/A10.
- Treat `HC5_trainopt` as a trade-off candidate unless it also survives 2021/A10.
- Treat auditor variants as stabilizers, not proof of autonomous regime discovery.
- Keep flags rows as controls; the no-flags claim must not depend on comparing against a noisy or unfair flag baseline.
