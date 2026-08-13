# Final comparison — protocol folder

**The comparison has NOT been run.** No number from it exists. This folder holds the operational
material for it; the specification itself is at
[`reports/canonical/HERALD_98_FINAL_MODEL_COMPARISON_SPECIFICATION.md`](../../canonical/HERALD_98_FINAL_MODEL_COMPARISON_SPECIFICATION.md).

Nothing in this folder may be submitted without explicit authorisation. The stage is frozen by
HERALD 97 / DEC-146, and this specification is the first thing that would unfreeze it.

---

## Pre-submission checklist

Every line is verified and signed off **before** a job is submitted. The point is that after
submission, none of them can be changed without invalidating the run.

### Data and population

- [ ] one universe only: the multirelational generator at 280 zones, `relational_scale = 1.0`
- [ ] scenarios `M0_NULL` and `M1_MULTIRELATIONAL`, same seeds, same budget, no reduced null
- [ ] seeds 9971–9975, verified never generated before by a guard against the retired list
- [ ] twelve rolling origins, identical for every arm, written into the summary
- [ ] expanding-window folds, one-standard-error rule, no contiguous training tail

### Fairness

- [ ] every arm reads the same released observations and the same availability masks
- [ ] absence is a mask channel; no arm receives a zero where a value is missing
- [ ] no arm receives the adjacency, the latent state, the relational component or edge labels
- [ ] no arm receives a feature the others do not, and this is asserted by a guard
- [ ] arms that are handed a graph are placed in a separate category from arms that learn one
- [ ] widths restricted to 32, 64, 128; a guard asserts that 256 is refused by the constructor
- [ ] one shared metric function; no arm computes its own AUPRC

### Gates

- [ ] the seven recovery gates are written into the summariser before submission
- [ ] the forecasting gate is written in with them
- [ ] the gate values are committed, and the commit precedes the job ID

### Controls

- [ ] `M0_NULL` present for every arm at full budget
- [ ] permuted graphs: derangement and degree-matched, for Axis C
- [ ] the oracle, on the same target as the arms it bounds
- [ ] prevalence printed beside every AUPRC, per support and per family

### Guards and mutants

- [ ] guards written before the arms they guard
- [ ] every mutant reinstates a concrete defect; none stubs a function with a constant
- [ ] guards and mutants run inside the first task of every array, under `set -e`
- [ ] the validation job completes before the grid is submitted

### Reporting

- [ ] smoke results are never reported as findings
- [ ] HERALD 93 and HERALD 96 numbers are never merged into one ranking
- [ ] a target mismatch is resolved by a separate table, never by a footnote

---

## Cost

About **16 h of CPU across roughly 130 array tasks**, under 1 GB peak per task, finishing in
roughly the wall-clock time of the longest task — around 25 minutes plus queueing. The
per-arm breakdown, and the scaling assumptions behind it, are in §7 of the specification.

`all_pairs` at 280 zones would be 78 120 ordered pairs and is deliberately not in the plan; it
stays an 80-zone diagnostic, where HERALD 96 already showed that containing every true edge
does not produce recovery.

---

## Submission order, when authorised

1. validation job: guards, mutants, one smoke seed — **stop if anything fails**
2. the grid, as one Slurm array
3. consolidation and the gate summary
4. results document and a DEC recording the decision on France

Between steps 2 and 4 there is nothing to decide: the gates were fixed in step 0.
