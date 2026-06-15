"""
Phase 14 — DEC-049 Convergence Audit

Controlled experiment to test the TRAINING_BUDGET_TOO_SMALL hypothesis from DEC-048.

Three pretraining variants × three epoch budgets × two evaluation modes (zero-shot + few-shot)
on two novel test scenarios.

CRITICAL CONSTRAINT: Auxiliary edge/sign/lag supervision (GRAPH_MASKED_MULTITASK) is
SYNTHETIC-ONLY. This supervision requires true_relations ground truth which does NOT EXIST
in real country data (PT/IT/FR/NL/AT). Do NOT apply this objective to real country data.

Frozen weights: MULTITASK_ALPHA=0.1, MULTITASK_BETA=0.05, MULTITASK_GAMMA=0.05
Epoch budgets: [30, 75, 150] (300 only if E2 convergence trigger fires at 150)
"""
