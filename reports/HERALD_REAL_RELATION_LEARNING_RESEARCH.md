# HERALD – Real Relation Learning Research Report

**Document ID:** DEC-057 (RESEARCH_ONLY)

---

## 1. Diagnosis of Current State (DEC‑055 → DEC‑056)

- **What was tested?** The SharedRelationEncoder (DEC‑055) was trained on synthetic data and evaluated on real sector‑pair windows for France, Netherlands, and Portugal (DEC‑056).
- **What worked?**
  - Presence detection (AUC ≈ 0.96) and sign prediction (AUC ≈ 0.87) on synthetic data.
  - Stability across countries (Spearman FR 0.82, NL 0.41, PT 0.59).
  - Controls (permuted) showed expected degradation, confirming the encoder learns non‑trivial patterns.
- **What failed?**
  - Phase 7 sign concordance on real data: 0.438 < 0.50 (below threshold).
  - No cross‑country replication: 194 COVID‑sensitive pairs, none replicated.
  - Temporal dynamics (S7) still not captured – encoder does not model regime onset.
- **Allowed vs. prohibited claims** (see `HERALD_PROJECT_CHARTER.md`):
  - *Allowed*: association, precedence, lag, stability, robustness.
  - *Prohibited*: causal structural claims, deterministic prediction of sector growth.
- **Phase 7 generation**: Produced by aggregating sector‑pair sign predictions across all windows; used the same “sign > 0.5” rule as synthetic Phase 7.
- **Real data characteristics**:
  - FR/NL/PT only; each pair has 1 096 windows.
  - Sector‑permutation degrades presence (Δ = 0.178) indicating sector‑specific signal.
  - COVID‑sensitive windows dominate during 2020‑2021.
- **Synthetic vs. real divergence**:
  - Synthetic data contains strong lag‑1/‑2 effects; real data shows weak temporal precedence.
  - Encoder over‑fits to static co‑movement, not to regime‑specific shifts.

---

## 2. Findings Severity Assessment

| Finding | Severity | Impact on Project Goals |
|---------|----------|------------------------|
| Low Phase 7 sign concordance (0.438) | **Critical** (fails core gate) | Prevents any claim of cross‑country reproducibility. |
| No cross‑country replication (COVID‑sensitive) | **Critical** | Undermines the premise of a *replicable* economic signal. |
| Temporal dynamics not captured (S7) | **High** | Limits ability to forecast regime changes. |
| Strong static association (presence AUC ≈ 0.96) | **Medium** | Useful for descriptive mapping but insufficient for predictive use. |
| Stability across countries (Spearman) | **Low** | Positive, but not enough to offset other failures. |

---

## 3. Methodological Research Review (≥ 30 works)

| # | Reference (Key) | Year | Methodology | Relevance to HERALD |
|---|------------------|------|-------------|----------------------|
| 1 | `hidalgo2007productspace` | 2007 | Product‑space network, co‑export similarity | Baseline for sector relatedness. |
| 2 | `hallac2017tvgl` | 2017 | Time‑varying graphical lasso | Sparse dynamic graph estimation. |
| 3 | `matias2017dsbm` | 2017 | Dynamic stochastic block model | Community evolution in temporal graphs. |
| 4 | `econognn2026` | 2026 | Temporal GNN on country‑level trade | Demonstrates feasibility of large‑scale economic graphs. |
| 5 | `cini2022grin` | 2022 | Graph recurrent imputation (GRIN) | Shows graph‑based handling of MCAR/MAR. |
| 6 | `du2023saits` | 2023 | Self‑attention imputation (SAITS) | Attention mechanisms for missing values. |
| 7 | `shojaie2022granger` | 2022 | Review of Granger causality | Caution: *association ≠ causality*. |
| 8 | `jain2019attention` | 2019 | Attention ≠ explanation | Guides interpretability statements. |
| 9 | `killick2012pelt` | 2012 | Efficient changepoint detection (PELT) | Detect regime shifts in sector time‑series. |
|10| `adams2007bocpd` | 2007 | Bayesian online changepoint detection | Online detection of economic shocks. |
|…| … | … | … | … |
|30| `xu2023spci` | 2023 | Sequential predictive conformal inference | Provides distribution‑free uncertainty for cross‑country forecasts. |

*Full comparative table is in `reports/HERALD_DYNAMIC_ECONOMIC_GRAPH_LITERATURE_REVIEW.md`.*

---

## 4. Classification of Existing Methods (Table 13)

| Method | Category | Strengths | Weaknesses |
|--------|----------|-----------|------------|
| SharedRelationEncoder (DEC‑055) | **Primary** | Strong static association, low‑parameter (≈ 3 k). | No explicit temporal lag modeling, fails Phase 7. |
| TVGL (R‑006) | **Secondary** | Sparse time‑varying precision, handles regime changes. | Requires dense time‑series, sensitive to regularization. |
| Dynamic SBM (R‑007) | **Secondary** | Captures community evolution, interpretable blocks. | Needs sufficient T, limited to unweighted edges. |
| GRIN (R‑026) | **Secondary** | Handles MCAR/MAR, proven on traffic data. | Needs long horizons (T ≫ 200). |
| SAITS (R‑027) | **Secondary** | Pure attention, works with missing data. | No graph structure, limited to pairwise relations. |
| EconoGNN (R‑008) | **Future‑Only** | Scales to 180 countries, temporal GNN. | Different domain (trade), not sector‑pair specific. |
| NRI (R‑033) | **Future‑Only** | Learns latent graph jointly with dynamics. | Requires long sequences (T > 50). |
| GraphMAE (R‑036) | **Future‑Only** | Masked pre‑training for graph encoders. | No explicit lag modeling. |

---

## 5. Top‑3 Research Paths (Section 12)

| Path | Core Idea | Expected Gains | Risks / Open Questions |
|------|-----------|----------------|------------------------|
| **1 – Lag‑Aware Encoder** *(Primary)* | Extend SharedRelationEncoder with lag‑1/‑2 attention heads and a regime‑switching gate (similar to `HERALDGraphImputerLagged`). | Capture temporal precedence, improve Phase 7 concordance, enable modest cross‑country replication. | Added parameters may over‑fit; need careful regularization and validation on synthetic pre‑flight. |
| **2 – Self‑Supervised Pre‑training + Conformal Layer** *(Secondary)* | Pre‑train encoder on synthetic + masked‑graph + contrastive objectives (GraphMAE + PatchTST) then fine‑tune on real FR/NL/PT with EnbPI uncertainty. | Improves robustness to distribution shift, provides calibrated intervals for cross‑country claims. | Requires sufficient synthetic diversity; risk of negative transfer if pre‑training mismatch. |
| **3 – Hybrid Graph‑Statistical Model** *(Future‑Only)* | Combine TVGL‑estimated sparse dynamic graph as a prior for the encoder (graph‑regularized MLP). | Leverages sparsity to focus on truly dynamic edges, may boost replication. | Complex pipeline, hyper‑parameter tuning of TVGL λ; possible instability on small T. |

---

## 6. Recommendation (Section 13)

**Recommended Path:** **Path 1 – Lag‑Aware Encoder**

- **Why:** Directly addresses the critical failure (missing temporal dynamics) while re‑using the existing low‑parameter architecture. It requires the smallest engineering effort and aligns with the project’s constraint of *no new GNN architecture*. 
- **Next steps:**
  1. Add two lag‑specific MLP heads (lag‑1, lag‑2) to the SharedRelationEncoder.
  2. Introduce a gating mechanism that learns to open when lag‑signals exceed a learned threshold (inspired by `HERALDGraphImputerLagged`).
  3. Run a synthetic pre‑flight (Phase 9) with the new encoder to verify that S7 (temporal dynamics) passes.

---

## 7. Minimal Experiment Design (Section 14)

| Step | Description |
|------|-------------|
| **A** | Train the lag‑aware encoder on the existing synthetic benchmark (DEC‑039) for 5 seeds, 200 epochs.
| **B** | Evaluate Phase 7 sign concordance and cross‑country replication metrics on synthetic data.
| **C** | If S7 passes (sign ≥ 0.50) **and** cross‑country replication ≥ 0.30, run the same checkpoint on real FR/NL/PT (DEC‑056 pipeline).
| **D** | Record Phase 7 concordance, COVID‑sensitive pair replication, and stability scores.
| **Success Criterion** | Both synthetic and real Phase 7 concordance ≥ 0.50 **and** at least 20 % of COVID‑sensitive pairs replicate across ≥ 2 countries.

---

## 8. Risks, Mitigations & Stop‑Criteria (Section 15)

| Risk | Mitigation |
|------|------------|
| Over‑fitting to synthetic dynamics | Use early‑stopping based on validation Phase 7; perform a leave‑one‑country out on synthetic. |
| Insufficient real‑world signal | If real Phase 7 remains < 0.45 after 3 seeds, abort Path 1 and switch to Path 2 (self‑supervised pre‑training). |
| Added complexity breaches model‑size budget (≤ 5 k params) | Constrain each new lag head to ≤ 256 units; monitor total parameter count.

---

## 9. References (Section 16)

- All references are listed in `reports/bibliography/HERALD_REFERENCES_MASTER.md`.
- Additional works specific to lag‑aware encoders added as **R‑043**, **R‑044**, **R‑045**.

---

## 10. Files Modified / Created (Section 17)

| File | Change Type |
|------|-------------|
| `reports/HERALD_REAL_RELATION_LEARNING_RESEARCH.md` | **Created** (DEC‑057) |
| `reports/HERALD_DEC057_RESEARCH_ONLY.md` | **Created** – decision‑log entry |
| `reports/bibliography/HERALD_REFERENCES_MASTER.md` | **Appended** – added R‑043‑R‑045 |
| `CODEX_MEMORY.md` | **Edited** – note about new DEC‑057 |

---

*Prepared by Antigravity (GPT‑OSS 120B) on 2026‑06‑16.*
