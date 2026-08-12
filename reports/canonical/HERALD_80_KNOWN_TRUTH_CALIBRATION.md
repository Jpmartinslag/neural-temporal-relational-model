# HERALD 80 — Outcome-calibrated known-truth control

Status: pre-execution amendment to HERALD 79
Date: 2026-08-11

HERALD 79 varied the deviation/prior score ratio, but post-run audit showed that
the incremental dynamic graph accounted for only 0.19%, 0.83% and 3.61% of
growth RMS in the native, medium and strong scenarios. It was therefore not a
valid strong positive control for end-to-end graph identification. Its results
remain immutable and are not discarded.

HERALD 80 retains the same real substrate, truth factors, graph paths, count
noise, architecture, recovery metrics and 199-permutation controls. It changes
only the outcome generator: the component attributable to `A[t]-A_prior` is
scaled prospectively to 5%, 25% and 75% of the graph-free/static-prior base
growth RMS. Actual post-clipping ratios are exported and guarded.

| scenario | graph-score ratio | target outcome RMS ratio | phi |
|---|---:|---:|---:|
| `calibrated_macro_null` | 0 | 0 | 2.5 |
| `calibrated_static_prior` | 0 | 0 | 2.5 |
| `calibrated_native` | 0.015 | 0.05 | 2.5 |
| `calibrated_medium` | 0.10 | 0.25 | 2.5 |
| `calibrated_medium_noisy` | 0.10 | 0.25 | 8.0 |
| `calibrated_strong` | 0.30 | 0.75 | 2.5 |

The decision rules remain those frozen in HERALD 79. This amendment prevents a
false attribution to the model when the supposedly strong injected outcome
signal was actually weak. It does not change any recovery threshold after
observing model recovery.
