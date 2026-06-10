# HERALD — Dynamic Economic Graph: Literature Review

**Created:** 2026-06-10  
**Status:** `PASS_WITH_LIMITATIONS` — bibliographic search performed 2026-06-10; some references UNVERIFIED  
**Scope:** Methods and empirical work relevant to the dynamic economic graph (Bloco 2) and territorial recommendation (Bloco 3)

---

## Methodological Audit — This Document

| Item | Value |
|------|-------|
| Scientific question | What methods and empirical findings are most relevant for building an interpretable dynamic economic graph over short annual NUTS3 panels (T≈13, p=23–93 regions)? |
| Search axes | 25 axes as specified in the task brief |
| Search method | Web search 2026-06-10 (WebSearch tool); repository extraction |
| Verification | References classified by status; unverified not cited as primary evidence |
| Critical constraint | T≈13 annual observations severely limits method complexity |
| Claims NOT made | This review does not imply that any method will work on the HERALD data; all methods require empirical validation under G4 |

---

## 1. Problem Definition

The HERALD project has established (Phase 4N–4Q) that:
- Persistence is the best causal forecasting baseline for harmonized PT/IT/AT enterprise birth LOCO.
- Geographic queen-contiguity graph lags do not improve forecast accuracy (4P/4Q FAIL).
- Italian persistence residuals show robust spatial autocorrelation (4O-C PASS), indicating unexplained geographic structure.

The scientific gap: **no dynamic economic graph has been built or tested**. The question is not "does a graph help forecast?" but "what economic structure can we represent and interpret, given our data?"

The challenge: annual NUTS3 data (T≈13, p=23–151 regions, partial sector coverage) is a severe constraint for most graph learning methods. Methods must be chosen accordingly.

---

## 2. Taxonomy of Economic Graphs

### 2.1 By node type

| Node type | Example | Availability |
|-----------|---------|-------------|
| Territory (NUTS3/ZE) | Region × year | FR 306 ZE; NL 40 COROP; PT 25 NUTS3; IT 93 NUTS3; AT 35 NUTS3 |
| Sector (A10) | Industry × year | **FR 92.3%, NL 100%, PT 94.1%** — confirmed. **IT 0%, AT 0%** — `bd_size_r3` uses aggregate NACE only |
| Territory × Sector pair | Region-sector dyad | Available for FR, NL, PT; absent for IT and AT at NUTS3 |
| Product (HS/CN) | Export basket | Country-level only (not NUTS3) |
| Firm | Individual enterprise | Not available at NUTS3 aggregation |

> **Data correction (2026-06-10):** Earlier versions of this document stated "AT full, IT partial." This is incorrect. `bd_size_r3` uses NACE aggregate `B-S_X_K642` for both IT and AT — no A10 territorial sector breakdown exists in the current extract. `bd_hgnace_r` provides FR/NL/PT sector births 2019–2023. IT and AT are used only in Path H aggregate (`enterprise_birth` total).

### 2.2 By edge type

| Edge type | Semantic | Example data source |
|-----------|----------|-------------------|
| Geographic contiguity | Physical adjacency | NUTS3 shapefile (available) |
| Functional economic area | Commuting, trade | Commuting surveys (partial) |
| Sector similarity | Co-presence or co-growth | Enterprise birth A10 by NUTS3 |
| Employment structure similarity | Labor market proximity | `nama_10r_3empers` |
| Input-output link | Supplier-customer | OECD/Eurostat I-O tables (country-level) |
| Product space proximity | Productive capability distance | Hidalgo & Hausmann (2007) |
| Granger-predictive | Lagged linear predictability | Estimated; NOT causal |
| Partial correlation | Conditional independence | GLASSO; precision matrix |
| Community membership | Latent group | DSBM |

### 2.3 By construction method

| Type | Description | Methods |
|------|-------------|---------|
| **Observed** | Built from known data; no statistical learning | Geographic contiguity, sector similarity, commuting matrices |
| **Estimated-static** | Statistically estimated; single graph for entire period | GLASSO, partial correlation |
| **Estimated-dynamic** | Time-varying graph estimated from data | TVGL, DSBM, temporal SBM |
| **Learned** | Graph structure learned end-to-end with prediction objective | GNN with graph structure learning |

**Recommendation:** Start with observed (G1) before moving to estimated (G2). Do not begin with learned (G2 end-to-end) — too many parameters for T≈13.

---

## 3. Static vs Dynamic Economic Graphs

### 3.1 Static approaches (appropriate as baseline)

A single adjacency matrix representing the average or typical relationship over the study period. Interpretable and stable, but misses temporal dynamics.

- **Product space (Hidalgo et al., 2007):** Country-level bipartite projection (country × product → product × product proximity). Well-documented; requires export data at sector level; available at country but not NUTS3 for PT/IT/AT.
- **Sector co-presence:** Which sectors consistently co-locate in the same NUTS3? Measurable from enterprise birth A10 data where available.
- **Correlation matrix:** Pearson/Spearman correlation of enterprise birth growth across NUTS3. Dense; not a proper graph; useful as sanity check.
- **Geographic contiguity:** Already tested (4P/4Q); rejected for predictive use; available as spatial control.

### 3.2 Dynamic approaches (target for Bloco 2)

A sequence of graphs, one per year (or window), capturing how relations evolve.

Key challenge: with T≈13 and p=23–93, most dynamic graph estimation methods are severely underpowered. The number of parameters grows as p² per time step. Regularization is mandatory.

---

## 4. Observed vs Learned Graphs

| Dimension | Observed | Learned |
|-----------|----------|---------|
| Transparency | Full — source known | Partial — depends on method |
| Leakage risk | Low (if construction uses t-1 data) | High — must verify carefully |
| Interpretability | Direct economic meaning | Requires post-hoc interpretation |
| Data requirement | Low (known sources) | High (T >> p for reliable estimation) |
| Validation complexity | Low | High (null model, bootstrap, stability) |

**HERALD position:** Observed graph (G1) first; learned sparse graph (G2) only after G1 is validated.

---

## 5. Territory-Sector-Product-Capability Relations

The economic complexity literature (Hidalgo & Hausmann 2007, 2009) formalizes productive capabilities:
- Countries and regions hold **capabilities** (skills, infrastructure, institutions).
- **Products** require bundles of capabilities to produce.
- **Relatedness** = capability overlap between two products or sectors.
- **Diversification** follows paths of high relatedness (low-distance jumps).

For HERALD:
- NUTS3 regions are analogous to countries in the product space framework.
- Enterprise birth by sector A10 is an observable proxy for capability presence.
- The enterprise-birth correlation matrix across NUTS3 × sectors is a first approximation of a capability graph.
- **Critical limitation:** NUTS3 MAUP — the same economic activity appears differently depending on administrative boundaries.

Related work: Neffke, Henning & Boschma (2011) — "How do regions diversify over time?" used plant-level labor flow data to construct skill-relatedness graphs. Similar approach not feasible at NUTS3 level without microdata.

---

## 6. Detecting Regimes and Structural Changes

Economic dynamics of interest: growth waves, crises (2008–2009), stagnation (2012–2014), COVID shock (2020).

### 6.1 Change-point detection on graphs

Given a sequence of yearly graphs, detect when the network structure changes significantly.

| Method | Key reference | Suitability for T≈13 |
|--------|--------------|----------------------|
| CUSUM on edge weights | Page (1954) | Yes — one statistic per edge |
| PELT | Killick et al. (2012) | Yes — efficient; requires sufficient T per segment |
| BOCPD | Adams & MacKay (2007) | Yes — Bayesian; handles short series |
| Spectral change detection | — | Moderate — eigenvalue monitoring of adjacency matrix |

With T≈13, at most 1–2 change points can be reliably detected per edge. Aggregate to country-sector level for more power.

### 6.2 Temporal community detection

Communities = groups of territories or sector-territory pairs that show similar dynamics together.

| Method | Reference | Suitability |
|--------|-----------|------------|
| Sliding-window Louvain | — | Yes — simple; stability measured by NMI across windows |
| Dynamic SBM (DSBM) | Matias & Miele (2017) | Moderate — requires sufficient T and reasonable p |
| Spectral temporal clustering | — | Yes — computationally light |
| Non-negative matrix factorization (NMF) | — | Yes — low-rank; interpretable factors |

**Key caution:** Communities detected from data are statistical clusters, not economic zones. External validation required (see G4).

---

## 7. Explainability

### 7.1 Why attention weights are insufficient

Jain & Wallace (2019) showed that attention weights can be arbitrarily permuted without changing model predictions in some architectures. The conclusion is widely accepted: **attention weight magnitude ≠ feature importance**.

In HERALD context: if a GNN assigns high attention to a neighbor, this does not mean the neighbor causally influences the target. The edge weight could reflect spurious correlation or confounding.

**Required for honest explainability:**
1. Permuted-graph baseline: re-estimate with shuffled edges and compare explanations.
2. Intervention-based explanation: mask edge; measure change in prediction.
3. Stability: explanations should be reproducible across seeds and bootstrap samples.

### 7.2 Methods compatible with short series

| Method | Description | Suitability |
|--------|-------------|------------|
| Edge ranking (by magnitude + stability) | Sort edges by weight and bootstrap stability | Yes |
| Influence maps (PageRank or degree centrality) | Identify most-connected nodes | Yes |
| Counterfactual graph editing | Remove edge; measure prediction change | Yes for linear models |
| SHAP for graph features | Shapley values over graph features | Moderate for linear; problematic for GNN |
| Attention-based (GNN) | Attention weights as importance | Only valid with permutation test |

---

## 8. Validation of Graph Edges

A learned or constructed edge is not a proven economic relation without:

1. **Statistical test:** Is the edge weight significantly different from null? (permutation test, FDR)
2. **Temporal stability:** Does the edge persist across years and bootstrap resamples?
3. **Null model comparison:** Is the graph sparser than Erdős-Rényi? Than configuration model?
4. **Economic coherence:** Does the edge connect regions or sectors with known economic links?
5. **MAUP sensitivity:** Does the edge survive a rescaling to NUTS2 (if data available)?

**What cannot be claimed from a learned edge without these tests:**
- "Region A influences region B economically."
- "Sector X and sector Y are substitutes/complements."
- "This community represents a functional economic area."

---

## 9. Methodological Risks

| Risk | Description | Mitigation |
|------|-------------|------------|
| T << p | T≈13 << p=93 (Italy) means underdetermined systems | Strong regularization; aggregate to NUTS2; restrict to top-k features |
| MAUP | NUTS3 boundaries are administrative; spurious spatial patterns possible | Sensitivity analysis at NUTS2; compare with known functional areas |
| Leakage | Edge weights computed using target-year data | Strict: construct edges using data through t-1 only |
| Overfitting | Complex models with T≈13 will memorize rather than generalize | Use leave-one-year-out; bootstrap; cross-country validation |
| Confirmation bias | Selectively reporting graph structures that match expectations | Pre-register acceptance criteria (G0 gate) |
| Granger/causal confusion | Granger-predictive edges labeled as causal | Explicit labeling: "Granger-predictive edge, not structural causal link" |
| COVID 2020 as outlier | 2020 is the last year in panel; will dominate change-point detection | Report 2020 separately; run sensitivity excluding 2020 |
| Attention misuse | GNN attention weights presented as economic explanation | Permutation test required before any explanation claim |

---

## 10. Methods Compatible with Short Annual Series (T≈13)

Priority ranking for HERALD:

| Rank | Method | Why suitable | Minimum T needed |
|------|--------|-------------|-----------------|
| 1 | Sector similarity from enterprise birth A10 (observed) | No estimation; fully interpretable | T=1 |
| 2 | Rolling Pearson/Spearman correlation (5-year window) | Simple; interpretable; stable | T≥5 |
| 3 | Graphical Lasso (GLASSO) with strong regularization | Sparse; well-studied; T>p needed → use p << T | T>p (feasible with aggregation) |
| 4 | Sparse VAR (Granger) with L1 | Low-rank; requires explicit causality warning | T≥2p |
| 5 | DSBM (Matias & Miele 2017) | Probabilistic; handles T≈13 with few communities | T≥10, K≤5 |
| 6 | Temporal GLASSO (TVGL) | Detects temporal change; robust to short T with smoothing | T≥15 recommended |
| 7 | NMF (temporal) | Interpretable factors; no explicit graph | T≥10 |
| 8 | Graph structure learning (GNN end-to-end) | Rich but overparameterized for T≈13 | T>>100 |

**Start at rank 1 (sector similarity, no estimation). Add complexity only after G1 is validated under G4. GLASSO (rank 3), sparse VAR (rank 4), TVGL (rank 6), DSBM (rank 5) are conditional experiments requiring G1 validation to pass first.**

**For T≈13:** GLASSO requires p << T; aggregate to country-sector level (p≤9 sectors × 3 countries = 27) before applying. TVGL needs T≥15; treat as experimental. DSBM needs K≤5 communities and T≥10; feasible but requires strong regularization. GNN end-to-end (rank 8) is future work only — T>>100 required for reliable graph structure learning.

---

## 11. Scientific Gap

After the HERALD Phase 4 experiments:

| Gap | Description |
|-----|-------------|
| GAP-1 | No dynamic economic graph has been built for PT/IT/AT |
| GAP-2 | Sector-territory relations at NUTS3 level are unmapped |
| GAP-3 | The nature of Italian residual spatial autocorrelation (4O-C) is unexplained |
| GAP-4 | Economic waves (growth, crisis, stagnation) not characterized at community level |
| GAP-5 | No interpretive framework connecting forecast errors to economic structure |
| GAP-6 | No data inventory of sector A10 availability at NUTS3 for IT (known incomplete) |

---

## 12. Proposed Progressive Methodology

Aligning with roadmap G0–G6:

| Step | Method | Data | Output |
|------|--------|------|--------|
| G0 | Conceptual contract | — | Node/edge definitions |
| G1a | Enterprise birth sector distribution similarity (A10) | `france_panel.csv`, `nl_panel.csv`, `pt_panel.csv` (mask_sector_a10 ≥ 0.92) | Territory-to-territory similarity graph (FR, NL, PT nucleus) |
| G1b | Sector-growth correlation matrix (rolling 5-year window, causal) | A10 enterprise birth growth, FR/NL/PT | Weighted co-growth graph; no estimation needed |
| G1c | Employment A10 complement | BE qtensor, FR/NL/PT qtensor | Employment-weighted layer; BE included here |
| G1d | Commuting / functional area edges | NL COROP 2022; BE Census 2011; PT INE commuting | Mobility-weighted layer (NL, BE, PT) |
| G1e | Geographic contiguity (control/null reference only) | NUTS3 shapefile | Queen adjacency; tested and rejected in 4P/4Q; kept as null baseline |
| G2a | GLASSO on region × sector growth | T=13 annual; restrict p | Sparse precision graph |
| G2b | DSBM community detection | T=13; K=3–5 communities | Community assignments |
| G3 | CUSUM/BOCPD on edge weights | Edge weight series | Change points (2009, 2012, 2020) |
| G4 | Bootstrap + permutation + null model | All above | Validated edge set |
| G5 | Edge ranking + community maps | Validated graph | Interpretive visualizations |
| G6 | Graph as forecast regularizer (if G4 passes) | Validated graph | WMAPE test |

---

## 13. Comparative Table (≥30 Works)

The following table covers works directly relevant to the HERALD dynamic economic graph. Verification status noted.

| # | Reference | Node | Edge | Temporal | Method | Data | T | Task | Interpretable | Validated | Limitation | Relevance | Status |
|---|-----------|------|------|----------|--------|------|---|------|---------------|-----------|------------|-----------|--------|
| 1 | Hidalgo et al. 2007 (Science) | Product | Proximity | Static | Bipartite projection | UN COMTRADE | Multi-year | Diversification prediction | High | Yes | Country-level only | Product space for Bloco 3 | VERIFIED_PRIMARY |
| 2 | Hidalgo & Hausmann 2009 (PNAS) | Country/Product | Capability distance | Static | ECI/PCI | UN COMTRADE | Multi-year | Complexity measurement | High | Yes | Country-level; no NUTS3 | ECI for territory characterization | VERIFIED_PRIMARY |
| 3 | Pachot et al. 2021 (ACM) | Product/Company | Semantic proximity | Static | Word2Vec + complexity | French I-O + trade | Static | Industrial recommendation | High | Partial | Not publicly reproducible | Direct ancestor of Bloco 3 | VERIFIED_PRIMARY |
| 4 | Pachot et al. 2021b (MORS@RecSys) | Company/Territory | Productive compatibility | Static | Multi-objective optim. | French data | Static | Sustainable recommendation | High | Partial | Workshop paper | Bloco 3 objective framing | VERIFIED_INSTITUTIONAL |
| 5 | Pachot et al. 2022 (arXiv) | Product/Supplier | I-O customer-supplier | Static | I-O + product space | French I-O | Static | Distributed manufacturing | High | Partial | Country-level I-O | Bloco 3 I-O component | VERIFIED_PRIMARY |
| 6 | Hallac et al. 2017 (KDD) | Variable/Series | Conditional independence | Dynamic | TVGL | Financial/health | T=100+ | Network inference | Moderate | Yes | Requires T >> p | G2 candidate (with strong reg.) | VERIFIED_PRIMARY |
| 7 | Matias & Miele 2017 (JRSS-B) | Node | Markov community | Dynamic | DSBM | Network data | T≥20 rec. | Community evolution | Moderate | Yes | Parameter estimation can fail for short T | G2/G3 community detection | VERIFIED_PRIMARY |
| 8 | EconoGNN 2026 (PLOS One) | Country | Trade | Dynamic | GNN + complexity | COMTRADE + PWT | T=25 | Resilience prediction | Moderate | Yes | Country-level; T=25 >> our T=13 | Example of temporal GNN for economics | UNVERIFIED |
| 9 | Friedman et al. 2008 (Biostatistics) | Variable | Partial correlation | Static | GLASSO | — | Any | Sparse graph estimation | High | Yes | Static; T >> p required | G2 foundational method | UNVERIFIED |
| 10 | Shojaie & Fox 2022 (Ann. Rev.) | Variable | Granger-predictive | Dynamic | VAR + L1 | — | — | Causality review | High | — | Review paper; Granger ≠ causality | Methodological caution | UNVERIFIED |
| 11 | Hamilton 1989 (Econometrica) | Time series | — | Dynamic | Markov switching | Macroeconomic | — | Regime detection | Moderate | Yes | No explicit graph | HERALD regime learner basis | VERIFIED_PRIMARY |
| 12 | Kim 1994 (J. Econometrics) | Time series | — | Dynamic | Switching state-space | Macroeconomic | — | Regime switching | Moderate | Yes | No explicit graph | HERALD regime learner basis | VERIFIED_PRIMARY |
| 13 | Truong et al. 2020 (Signal Processing) | Time series | — | Dynamic | CUSUM, PELT, BOCPD | Various | Short OK | Change-point detection | High | Yes | Off-line detection only | G3 regime change detection | VERIFIED_PRIMARY |
| 14 | Anselin 1988 (textbook) | Territory | Geographic | Static | Moran's I, spatial lag | Spatial data | — | Spatial autocorrelation | High | Yes | Static | Phase 4O methodology basis | UNVERIFIED |
| 15 | Moran 1950 (Biometrika) | Territory | Geographic | Static | Moran's I statistic | Spatial data | — | Autocorrelation test | High | Yes | One statistic | Phase 4O primary metric | UNVERIFIED |
| 16 | Jain & Wallace 2019 (NAACL) | — | — | — | Attention analysis | NLP | — | Explainability critique | High | Yes | Domain = NLP | Attention ≠ explanation caution | UNVERIFIED |
| 17 | Jacobs et al. 1991 (Neural Computation) | — | — | — | MoE | — | — | Expert gating | Moderate | Yes | Static regime assignment | HERALD architecture basis | VERIFIED_PRIMARY |
| 18 | Neffke, Henning & Boschma 2011 | Region/Sector | Labor flow | Dynamic | Plant-level labor mobility | Swedish microdata | Multi-year | Regional diversification | High | Yes | Requires plant microdata (unavailable) | Relatedness concept; microdata unavailable | UNVERIFIED |
| 19 | Audretsch & Fritsch 2002 (Regional Studies) | Region | — | Dynamic | OLS panel | German regions | 1980s-90s | Firm formation + growth | Moderate | Yes | Single country; dated | Enterprise birth as regional growth indicator | UNVERIFIED |
| 20 | Page 1954 (Biometrika) | Time series | — | Dynamic | CUSUM | Industrial quality | — | Change detection | High | Yes | Offline only | G3 baseline change detection | UNVERIFIED |
| 21 | Adams & MacKay 2007 (arXiv) | Time series | — | Dynamic | BOCPD | — | Short OK | Online change detection | High | Yes | Requires prior spec. | G3 Bayesian change detection | UNVERIFIED |
| 22 | Killick et al. 2012 (JASA) | Time series | — | Dynamic | PELT | — | Short OK | Efficient change-point | High | Yes | Assumes independence | G3 efficient change detection | UNVERIFIED |
| 23 | Louvain / Blondel et al. 2008 | Node | Undirected | Static | Modularity optimization | — | — | Community detection | Moderate | Yes | Resolution limit | G2 static community baseline | UNVERIFIED |
| 24 | TVGL application to finance | Variable | Conditional dependence | Dynamic | TVGL | Financial data | T=100+ | Network change | Moderate | Yes | Finance context; T >> ours | G2 application example | UNVERIFIED |
| 25 | Temporal GNN survey 2023 (TDS) | Node | Various | Dynamic | Survey | Various | — | Various | — | — | Survey; not primary | General context for temporal GNNs | UNVERIFIED |
| 26 | Product Space analysis Brazil (USITC) | Product | Proximity | Static | Hidalgo method | Trade data | Multi-year | Diversification | High | Yes | Country-level | Product space application | UNVERIFIED |
| 27 | Hierarchical SBM (Bayesian Analysis 2022) | Node | Multiplex | Static | Hierarchical SBM | Network data | — | Community detection | Moderate | Yes | Complex estimation | G2 multiplex extension | UNVERIFIED |
| 28 | Bridging short-term and long-term structural change (arXiv 2021) | Country/Product | Relatedness | Dynamic | Structural decomposition | COMTRADE | Long | Diversification dynamics | Moderate | Partial | Country-level | G3 structural change framing | UNVERIFIED |
| 29 | Sparse VAR with Lasso | Variable | Granger | Dynamic | VAR + L1 | Economic panels | T≥50 rec. | Network inference | Moderate | Yes | T >> ours; causality caveat | G2 alternative to TVGL | UNVERIFIED |
| 30 | Input-output propagation literature (Acemoglu et al. 2012) | Sector | Supplier-customer | Static | I-O analysis | I-O tables | — | Shock propagation | High | Yes | Aggregate I-O; no NUTS3 | G1 I-O edge type | UNVERIFIED |

---

## 14. Key Distinctions (methodological)

The following distinctions MUST be maintained in all HERALD outputs:

| Concept A | ≠ | Concept B | Why |
|-----------|---|-----------|-----|
| Pearson correlation | | Partial correlation (conditional independence) | Correlation confounds; GLASSO removes it |
| Granger predictability | | Economic causality | Granger = "A predicts B conditional on past B"; structural causality requires intervention |
| Attention weight magnitude | | Feature importance | Attention can be arbitrary; requires permutation test |
| Spatial autocorrelation in residuals | | Predictive benefit from spatial lag | 4O-C proved signal exists; 4P/4Q proved lag feature does not help |
| Graph community | | Functional economic area | Statistical cluster ≠ economic zone without external validation |
| Learned edge | | Proven economic relation | Estimation artifact possible; requires null model, bootstrap, economic coherence check |
| Association | | Causality | Observational data cannot establish structural causality without intervention |

---

## 15. Summary: Literature Gaps and HERALD Contribution

**Note on data sources:**
- `bd_size_r3` (Eurostat) provides total enterprise births and stock for IT and AT at NUTS3 — but uses aggregate NACE `B-S_X_K642`, not A10 sector breakdown. IT and AT are excluded from the sector graph nucleus.
- `bd_hgnace_r` (Eurostat) provides FR, NL, PT sector births 2019–2023 (NACE sections, mappable to A10). This is a complement to the canonical sector panels.
- Sector A10 births confirmed available: FR (92.3%), NL (100%), PT (94.1%).

**What exists:**
- Product space and economic complexity at country level (well-developed).
- Territorial recommendation systems (Pachot et al. — at company/sector level, not NUTS3).
- Dynamic graph methods (TVGL, DSBM) — for T >> 13.
- GNN for economic resilience (EconoGNN 2026) — country-level, T=25.

**What does not exist for NUTS3 short annual panels:**
- A validated dynamic economic graph at NUTS3 level with T≈13.
- A method-to-data fit validated for sector enterprise birth.
- Territorial economic recommendation from NUTS3 observable sector dynamics.

**HERALD potential contribution:**
- First dynamic economic graph calibrated on harmonized NUTS3 `enterprise_birth` A10 panel.
- Progressive validation protocol (G0→G6) that separates association from causality.
- Honest evaluation: graph validated independently of WMAPE.
- Template for short-panel economic graph construction with documented limitations.

This is a realistic and publishable contribution **without** claiming causal inference, recommendation operationality, or GNN necessity.
