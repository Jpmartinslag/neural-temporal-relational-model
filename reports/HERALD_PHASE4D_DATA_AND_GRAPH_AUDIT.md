# HERALD Phase 4D — Data and Graph Audit

**Date:** 2026-05-30
**Scope:** International generalisation data pipeline — NL, BE, PT, FR
**Purpose:** Identify which new data/graphs can improve generalisation before next HPC battery
**Rule:** No training launched. No architecture changed. No data invented.

---

## 1. Sector Similarity Graph

**Status:** DONE — all 3 countries

Built from existing `a10_ze2020.csv` (sector births by region × year). Averages last 5 years of sector distribution per zone, computes cosine similarity, row-normalises.

| Country | Zones | Cosine range | Weight CV | Source years |
|---------|-------|-------------|-----------|--------------|
| NL | 40 | 0.022–0.027 | 0.162 | 2020–2024 |
| BE | 42 | 0.016–0.028 | 0.165 | 2016–2020 |
| PT | 25 | 0.027–0.047 | 0.213 | 2018–2022 |

**Density warning:** The dense version (threshold=0) is fully connected (density=1.0) — every zone connects to every other zone. The normalised weight CV ≈ 0.16–0.21 shows that weights are not perfectly uniform, but the difference between the most and least similar pair is small (cosine 0.62–1.00 before normalisation). A fully dense graph may add noise similarly to a random prior. **The top-k sparse versions should be preferred for training.**

Sparse variants generated: top-5 (density ≈ 0.12–0.21) and top-8 (density ≈ 0.20–0.33).

**Files created:**
- `data/external/build_phase4d_sector_similarity.py` (supports `--top-k N`)
- `data/processed/phase4d/nl/adj_sector_similarity.csv` (dense, 40×41)
- `data/processed/phase4d/nl/adj_sector_similarity_top5.csv` (sparse, 40×41)
- `data/processed/phase4d/nl/adj_sector_similarity_top8.csv` (sparse, 40×41)
- `data/processed/phase4d/be/adj_sector_similarity.csv` (dense, 42×43)
- `data/processed/phase4d/be/adj_sector_similarity_top5.csv` (sparse, 42×43)
- `data/processed/phase4d/be/adj_sector_similarity_top8.csv` (sparse, 42×43)
- `data/processed/phase4d/pt/adj_sector_similarity.csv` (dense, 25×26)
- `data/processed/phase4d/pt/adj_sector_similarity_top5.csv` (sparse, 25×26)
- `data/processed/phase4d/pt/adj_sector_similarity_top8.csv` (sparse, 25×26)

**HERALD use:** Graph regularizer (smooth_term, gate_entropy, alpha_smooth). Replaces `adj_geo` in experiments wanting functional proximity instead of geographic contiguity.

**Forecast-safe:** Yes — built from sector births data already in the model panel. No leakage.

**Comparable across countries:** Yes — same A10 sectors, same method.

---

## 2. Commuting Graph (functional adjacency)

### 2a. Netherlands — DONE

**Source:** CBS StatLine 85481NED — "Pendelen; reisafstand en vervoersmiddel", December 2022 snapshot
**Geographic level:** COROP×COROP native — no aggregation required
**Year:** 2022

| Metric | Value |
|--------|-------|
| Zones | 40 COROP |
| Avg diagonal (self-commute) | 0.630 (range 0.393–0.872) |
| Avg off-diagonal neighbours | 30.4 |
| Row sums | 1.0000 (validated) |
| NaN | 0 |

**Files:**
- `data/external/build_phase4d_commuting_graph.py` (reproducible builder for NL and BE)
- `data/external/netherlands/raw/commuting/85481NED_corop_commuting_2022.json`
- `data/processed/phase4d/nl/adj_commuting.csv` (40×41)

**HERALD use:** Alternative `adj_geo` that captures functional labour market connections. Richer than geographic contiguity (30 neighbours vs 4.4 for queen contiguity).

**Forecast-safe:** Yes — 2022 snapshot used as static prior, not target-year specific.

**Caveats:** Single cross-section (2022). Commuting patterns shift slowly; reasonable to treat as structural proxy over 2016–2024 eval window.

---

### 2b. Belgium — DONE

**Source:** StatBel Census 2011 commuting matrix — "Census 2011 Matrix van woon-werkverkeer per geslacht"
**Geographic level:** Arrondissement×arrondissement native (NIS codes → 42 zones)
**Year:** 2011

| Metric | Value |
|--------|-------|
| Zones | 42 arrondissements |
| Avg diagonal (self-commute) | 0.584 (range 0.331–0.811) |
| Avg off-diagonal neighbours | 40.8 |
| Row sums | 1.0000 (validated) |
| NaN | 0 |

**Files:**
- `data/external/belgium/raw/commuting/TU_CENSUS_2011_COMMUTERS_MUNTY.txt` (raw StatBel OD matrix)
- `data/processed/phase4d/be/adj_commuting.csv` (42×43)

**HERALD use:** Same as NL — alternative `adj_geo` for BE.

**Caveats:** 2011 data (oldest of the three). No more recent official national OD matrix from StatBel. Patterns have likely shifted post-2011, especially around Brussels and Flemish growth zones.

---

### 2c. Portugal — BLOCKED

**Attempted source:** INE Censos 2021, indicator 0012340 — "Movimentos pendulares (Interações na unidade territorial)"

**Blockers — two independent issues:**

1. **Data design:** The indicator 0012340 records only cross-NUTS3 commuting flows. Within-NUTS3 commuting (the diagonal) is zero by design for 24 of 25 zones. Only PT_170 (AML) shows a non-zero diagonal because AML was split in NUTS2024 and the intra-AML cross-flows are counted. This produces a structurally incorrect prior for HERALD (no zone retains its own labour force).

2. **Classification mismatch:** The INE indicator uses NUTS2024. Our PT panel uses NUTS2021 (25 zones). The conversion is non-trivial:
   - AML: 1 zone (NUTS2021 PT_170) → 2 zones (NUTS2024 1A0 + 1B0)
   - Centro: 8 zones (NUTS2021 16B–16J) → 6 zones (NUTS2024 191–196)
   - Alentejo: 5 zones (NUTS2021 181–187) → 4 zones (NUTS2024 1C1–1C4)
   
   Without a verified NUTS2021→NUTS2024 concordance table with population weights, reliable aggregation/disaggregation is not possible.

**Recommendation:** Do not use PT commuting graph in Phase 4D. If needed for a future phase, request the Censos 2011 municipality-level OD matrix from INE and aggregate to NUTS2021 boundaries.

---

## 3. Eurostat Business Demography (bd_hgnace_r)

**Source:** Eurostat API — `bd_hgnace_r` (business demography by NUTS and NACE)
**Downloaded:** Full dataset (1.4M rows), filtered to NL/PT/FR at NUTS3

### Coverage

| Country | Years | NUTS3 zones | NACE sections | Births non-null | Stock non-null |
|---------|-------|-------------|--------------|-----------------|----------------|
| FR | 2020–2023 | 102 | 11 | 75% | 75% |
| NL | 2020–2023 | 56 (40 COROP match) | 11 | 69% | 69% |
| PT | 2019–2023 | 41 (25 match) | 11 | 59% | 59% |
| **BE** | **—** | **ABSENT** | **—** | — | — |

**Belgium completely absent from bd_hgnace_r.** Belgium does not report regional business demography to Eurostat under this table.

**NACE sections available:** B-E, F, G, H, I, J, K_L, M_N, P_Q, R_S_X_S94 (11 sections, not directly A10). Mapping to our A10 is approximate (e.g., G+H+I → GI; K+L split → KZ+LZ).

**Forecast-safe:** Data is published with 1–2 year lag. Using year T data for year T training is NOT safe. Using as lag-1 feature is safe.

**Critical limitation:** Only 2019+ for sector-level data. Our training windows start 2008 (BE), 2010 (NL), 2008 (PT). Eurostat BD cannot serve as historical feature.

**Use case:** Validation comparison (HERALD predictions vs Eurostat BD actuals for 2020-2023). NOT usable as training feature for most of the historical window.

**Files:**
- `data/external/eurostat_business_demography/bd_hgnace_r_raw.csv` (25K rows, filtered)
- `data/external/eurostat_business_demography/bd_hgnace_r_raw_full.csv` (1.4M rows)
- `data/external/eurostat_business_demography/process_bd_hgnace_r.py`
- `data/processed/phase4d/eurostat_bd_panel.csv` (8.2K rows, 8 cols)

---

## 4. Eurostat Business Demography (bd_size_r3)

**Source:** Eurostat API — `bd_size_r3` (business demography by size class and NUTS)
**Downloaded:** 5.3MB, decoded from gzip

| Country | Years | NUTS3 zones | Match with ours | NACE sections |
|---------|-------|-------------|-----------------|---------------|
| FR | 2008–2020 | 199 | — | B-S_X_K642 (total only) |
| NL | 2008–2020 | 48 | 40/40 match | B-S_X_K642 (total only) |
| PT | 2008–2020 | 47 | 25/25 match | B-S_X_K642 (total only) |
| **BE** | **—** | **ABSENT** | — | — |

**Critical limitation:** bd_size_r3 has NO sector breakdown — only total B-S with size class (0 employees, 1-9, ≥10). Cannot be used to build sectoral features.

**Use case:** Enterprise size distribution as contextual feature (large vs small firm concentration). Useful as supplementary feature but not a sector tensor substitute.

**Files:**
- `data/external/eurostat_business_demography/bd_size_r3_raw.csv` (5.3MB)

---

## 5. Portugal GEP/Quadros de Pessoal

**Source:** GEP/MTSSS — "Série Quadros de Pessoal 2014-2024" (Relatório Único, October reference month)

**Files downloaded:**
- `data/external/portugal/gep_quadros_pessoal/seriesqp_2014_2024.xlsx`
- `data/external/portugal/gep_quadros_pessoal/qp2024pub.xlsx`
- `data/external/portugal/gep_quadros_pessoal/Dashboard_seriesqp_2014_2024.xlsx`

### What exists

| Table | Geographic level | Sector | Years | Indicator |
|-------|-----------------|--------|-------|-----------|
| q16_b | NUTS3 (23 mainland) | None — total | 2014–2024 | TCO (wage workers) |
| q13 | National (Continente) | CAE Rev.3 A–U | 2014–2024 | TCO |
| Quadro 60 (qp2024pub) | NUTS2 (5 regions) | CAE Rev.3 A–U | 2024 only | TCO |
| INE 0006909 | NUTS2 | NACE 2 sections | up to 2022 | Employees |

**Critical gap:** There is NO published cross-tabulation of NUTS3 × CAE for TCO/employment in any open dataset. The cross-tab simply does not exist in public form.

**Coverage note:** GEP covers continental Portugal only (excludes Açores PT_200 and Madeira PT_300). Starts 2014 — does not cover 2008–2013 (HERALD PT training window start).

### Disaggregation options

**Option A (national shares → NUTS3):** `T[zone,sector,year] = q16_b[zone,year] × (q13[sector,year] / q13[total,year])`. Assumes identical sector mix across all NUTS3 — clearly false. Worse than births proxy because births capture actual regional × sector heterogeneity.

**Option B (NUTS2 shares → NUTS3 biproportional):** Use NUTS2 × CAE shares (Quadro 60 in each annual publication) + NUTS3 within-NUTS2 marginals. Better than Option A but requires downloading ~10 annual files and is still synthetic.

**Best option for real data:** Custom data request to GEP (`https://www.gep.mtsss.gov.pt/pedido-de-informacao-estatistica`). GEP accepts custom tabulations from microdata for academic use (2–4 weeks, typically free). This is the only path to a true NUTS3 × CAE employment tensor for PT.

**Conclusion:** No `qtensor_jobs_panel.csv` created. Current births proxy remains the best available open-data option. Label explicitly as proxy.

---

## 6. Availability Table

| Dado | FR | NL | BE | PT | Status | Fonte | Uso HERALD |
|------|----|----|----|----|--------|-------|------------|
| Births por região (painel) | ✓ | ✓ | ✓ | ✓ | **DONE** | INSEE/CBS/ONSS/INE | target, feature |
| Stock por região (painel) | ✓ | ✓ | ✓ | ✓ | **DONE** | mismo | feature |
| adj_geo (contiguidade) | ✓ | ✓ | ✓ | ✓ | **DONE Phase 4C** | Eurostat NUTS3 shapefile | grafo espacial |
| adj_sector_similarity | — | ✓ | ✓ | ✓ | **NEW Phase 4D** | a10_ze2020.csv (interno) | grafo funcional |
| adj_commuting | — | ✓ | ✓ | ✗ | **NL/BE done; PT bloqueado** | CBS 85481NED / StatBel Census 2011 | grafo funcional |
| Tensor empregos (Q7) | ✓ | ✓ | ✓ | ✗ | **PT bloqueado** | INSEE/CBS/ONSS | tensor setorial |
| Tensor births × CAE | — | — | — | ✓ (proxy) | Proxy marcado | INE 0009703 | tensor setorial proxy |
| Eurostat BD regional (births+stock) | ✓ | ✓ | ✗ | ✓ | **BE ausente; só 2019+** | Eurostat bd_hgnace_r | validação externa |
| Eurostat BD size class | ✓ | ✓ | ✗ | ✓ | **BE ausente; sem NACE** | Eurostat bd_size_r3 | feature contextual |
| Commuting PT (Censos 2021) | — | — | — | ✗ | **BLOQUEADO (NUTS mismatch + cross-only)** | INE 0012340 | — |
| GEP NUTS3 × CAE (TCO) | — | — | — | ✗ | **BLOQUEADO (dado não publicado)** | GEP microdata (necessita pedido) | tensor setorial real |

---

## 7. Bloqueios documentados

### B1 — Belgium ausente do Eurostat BD
Belgium does not report regional business demography (bd_hgnace_r, bd_size_r3) to Eurostat. Confirmed from full dataset (1.4M rows). **No workaround with open data.** ONSS data (already in pipeline) is the correct source for BE enterprise data.

### B2 — Portugal tensor empregos real (NUTS3 × CAE)
GEP Quadros de Pessoal does not publish a NUTS3 × CAE employment cross-table. The data exists at national × CAE (q13) and NUTS3 × total (q16_b) but not crossed. **Resolution:** Custom data request to GEP (academic use, free, ~2-4 weeks).

### B3 — Portugal commuting (Censos 2021)
INE indicator 0012340 uses NUTS2024 classification (26 zones) while our PT panel uses NUTS2021 (25 zones). Concordance is non-trivial (3 non-1:1 zone changes). Additionally, the indicator only captures inter-NUTS3 flows (diagonal=0 for 24/25 zones), which is structurally incorrect for a commuting prior. **Resolution:** Request Censos 2011 OD matrix from INE (municipality level, then aggregate to NUTS2021).

### B4 — Eurostat BD histórico (pré-2019)
bd_hgnace_r only covers 2019+. bd_size_r3 covers 2008-2020 but has no NACE sector breakdown. No harmonized Eurostat source covers the full training window with sector breakdown. **Resolution:** None for open data. Country-specific sources (already in pipeline) remain primary.

---

## 8. Validações executadas

```
python3 -m py_compile data/external/build_phase4d_sector_similarity.py  → OK
```

**Sector similarity matrices:**
- All 3 countries: row sums ∈ [1.0000, 1.0000], NaN=0, values ≥ 0 ✓

**NL commuting:**
- Shape (40, 41), row sums 1.0000, NaN=0, diagonal populated (all > 0) ✓

**BE commuting:**
- Shape (42, 43), row sums 1.0000, NaN=0, diagonal populated ✓

**PT commuting:** NOT created (BLOQUEADO — see B3)

**NUTS3 match (NL):** All 40 COROP codes present in Eurostat bd_hgnace_r and bd_size_r3 ✓
**NUTS3 match (PT):** All 25 NUTS2021 codes present in Eurostat bd_size_r3 ✓

---

## 9. Bateria Phase 4D — Configurações finais

**Bateria pronta para lançar.** Smoke test passado (NL, 10/10 configs, 1 época, cpu). Audit plan: 0 erros, 1 aviso (PT proxy).

### Configs NL/BE (10 por país, 20 seeds = 200 runs)

| Config | Features | Tensor | Graph | Hipótese |
|--------|----------|--------|-------|----------|
| `best_4a` | NL: current_clean / BE: side5_lag1 | zero | identity | Replicar Phase 4A melhor (controlo) |
| `geo_4c` | side5_lag1_growth1y | zero | adj_geo (real) | Replicar Phase 4C melhor (controlo) |
| `commuting_dense_no_tensor` | side5_lag1_growth1y | zero | adj_commuting | Grafo funcional denso sozinho? |
| `commuting_top5_no_tensor` | side5_lag1_growth1y | zero | adj_commuting_top5 | Top-5 comutação isola sinal estrutural? |
| `commuting_top8_no_tensor` | side5_lag1_growth1y | zero | adj_commuting_top8 | Top-8 vs top-5 — densidade óptima? |
| `commuting_top5_tensor` | side5_lag1_growth1y | effectifs_lag1 | adj_commuting_top5 | Comutação + tensor = melhor combinação? |
| `sector_top5_no_tensor` | side5_lag1_growth1y | zero | adj_sector_sim_top5 | Similaridade setorial sozinha vs geo? |
| `sector_top8_no_tensor` | side5_lag1_growth1y | zero | adj_sector_sim_top8 | Mais vizinhos setoriais = melhor? |
| `sector_top5_tensor` | side5_lag1_growth1y | effectifs_lag1 | adj_sector_sim_top5 | Setor + tensor vs comutação + tensor? |
| `graph_perm_control` | side5_lag1_growth1y | zero | adj_commuting_top5_**perm** | Grafo real ≠ grafo aleatório? (null model) |

### Configs PT (7, 20 seeds = 140 runs)

| Config | Features | Tensor | Graph |
|--------|----------|--------|-------|
| `best_4a` | side5_lag1_growth1y | effectifs_lag1 (proxy) | identity |
| `geo_4c` | side5_lag1_growth1y | effectifs_lag1 (proxy) | adj_geo (real) |
| `sector_top5_no_tensor` | side5_lag1_growth1y | zero | adj_sector_sim_top5 |
| `sector_top8_no_tensor` | side5_lag1_growth1y | zero | adj_sector_sim_top8 |
| `sector_top5_births` | side5_lag1_growth1y | effectifs_lag1 (proxy) | adj_sector_sim_top5 |
| `sector_top8_births` | side5_lag1_growth1y | effectifs_lag1 (proxy) | adj_sector_sim_top8 |
| `graph_perm_control` | side5_lag1_growth1y | zero | adj_sector_sim_top5_**perm** |

### Critérios de vitória

| Critério | Threshold | Interpretação |
|----------|-----------|---------------|
| graph_real < graph_perm | qualquer melhoria | Estrutura espacial existe (grafo não é ruído) |
| melhor funcional < geo_4c | qualquer melhoria | Grafo funcional supera contiguidade geográfica |
| melhor funcional ≤ best_4a + 1% | ≤1% regressão | Não regride vs Phase 4A |
| melhor funcional < geo_4c × 0.97 | ≥3% melhoria | **Vitória forte** — confirma hipótese Phase 4D |

### Pergunta científica central

> **O grafo de comutação laboral (funcional) activa o componente espacial do HERALD de forma que a contiguidade geográfica não consegue?**

Phase 4A (identity) ≈ Phase 4C (geographic contiguity) → o grafo geográfico não ajudou.
Phase 4D testa se a estrutura funcional do mercado de trabalho (commuting) ou a estrutura sectorial são os grafos relevantes para generalização.

### Scripts de lançamento

```bash
# Audit pré-lançamento (obrigatório)
python3 hpc/phase4/audit_phase4d_plan.py

# Smoke test local (obrigatório)
bash hpc/phase4/smoke_test_phase4d.sh nl
bash hpc/phase4/smoke_test_phase4d.sh be
bash hpc/phase4/smoke_test_phase4d.sh pt

# Submit HPC
bash hpc/phase4/submit_herald_phase4d_nl.sh
bash hpc/phase4/submit_herald_phase4d_be.sh
bash hpc/phase4/submit_herald_phase4d_pt.sh

# Audit pós-resultados
python3 hpc/phase4/audit_phase4d_results.py \
  --root hpc_results/herald_phase4d_nl_YYYYMMDD_r1 \
  --phase4a-wmape 0.058184 --phase4c-wmape 0.060751
```

---

## 10. Ficheiros criados/modificados nesta fase

```
# Builders reprodutíveis
data/external/build_phase4d_sector_similarity.py          [NEW — --top-k N]
data/external/build_phase4d_commuting_graph.py             [NEW — NL+BE, top-k]

# Dados externos baixados
data/external/eurostat_business_demography/
  bd_hgnace_r_raw.csv / bd_hgnace_r_raw_full.csv / bd_size_r3_raw.csv / process_bd_hgnace_r.py
data/external/netherlands/raw/commuting/85481NED_corop_commuting_2022.json
data/external/belgium/raw/commuting/TU_CENSUS_2011_COMMUTERS_MUNTY.txt
data/external/portugal/raw/ine_commuting_0012340.json (bloqueado)
data/external/portugal/gep_quadros_pessoal/{seriesqp_2014_2024.xlsx, qp2024pub.xlsx, ...}

# Grafos processados
data/processed/phase4d/
  {nl,be,pt}/adj_identity.csv                              [NEW]
  {nl,be,pt}/adj_sector_similarity.csv          (dense)    [NEW]
  {nl,be,pt}/adj_sector_similarity_top5.csv                [NEW]
  {nl,be,pt}/adj_sector_similarity_top8.csv                [NEW]
  {nl,be,pt}/adj_sector_similarity_top5_perm.csv (seed=42) [NEW]
  {nl,be}/adj_commuting.csv                     (dense)    [NEW]
  {nl,be}/adj_commuting_top5.csv                           [NEW]
  {nl,be}/adj_commuting_top8.csv                           [NEW]
  {nl,be}/adj_commuting_top5_perm.csv           (seed=42)  [NEW]
  eurostat_bd_panel.csv                                     [NEW]

# Infraestrutura HPC
hpc/phase4/phase4d_configs.sh                              [NEW]
hpc/phase4/run_herald_phase4d_seed.sh                      [NEW]
hpc/phase4/run_herald_phase4d_array.sbatch                 [NEW]
hpc/phase4/submit_herald_phase4d_{nl,be,pt}.sh             [NEW]
hpc/phase4/smoke_test_phase4d.sh                           [NEW]
hpc/phase4/audit_phase4d_plan.py                           [NEW]
hpc/phase4/audit_phase4d_results.py                        [NEW]

# Wrapper actualizado (graph metadata injection)
hpc/phase4/run_herald_phase4_wrapper.py                    [MODIFIED]

# Relatório
reports/HERALD_PHASE4D_DATA_AND_GRAPH_AUDIT.md             [NEW]
```

---

*Última actualização: 2026-05-30. Nenhum treinamento lançado. Nenhum arquivo Phase 4A/4C modificado.*
