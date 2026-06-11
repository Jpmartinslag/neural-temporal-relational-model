# HERALD: Graph-Temporal Architecture Review

**Date:** 2026-06-11 (revised 2026-06-11 — matrix expanded to 20 entries; EconoGNN corrected; columns completed)
**Objective:** Define the methodologically defensible graph-temporal architecture space for HERALD Europe Economic (short annual panels, T≈10–15, structural missingness).
**Status:** COMPLETE FOR METHOD SELECTION — 20 entries; implementation remains blocked by the architecture decision gate.

> **Prior draft errors corrected:**
> - Matrix had only 10 entries; minimum required is 20. **Fixed.**
> - EconoGNN classified as "Fixo (Trade)". Correct classification: DTDG observado. **Fixed.**
> - EconoGNN decision was REJECT without justification. Correct classification: REFERENCE. **Fixed.**
> - Multiple required columns were absent. **Fixed.**
> - GConvGRU was pre-selected as the recommended architecture before the matrix comparison was complete. **This was premature. No architecture is pre-selected in this document. The decision document (HERALD_GRAPH_TEMPORAL_ARCHITECTURE_DECISION.md) must be read after this matrix.**

---

## Graph Category Taxonomy

For the "categoria do grafo" column, five mutually exclusive categories are used:

| Code | Category | Description |
|------|----------|-------------|
| **E-OBS** | Estático observado | Single fixed adjacency; built from data; does not change with time |
| **D-OBS** | Dinâmico observado | Sequence of observed adjacency matrices; no statistical estimation |
| **FIX-DYN** | Estrutura fixa com atributos dinâmicos | Topology frozen; node/edge attributes (features, weights) evolve |
| **PART-LEARN** | Parcialmente aprendido | Known prior graph + learned correction (gates, attention over candidates) |
| **FULL-LEARN** | Totalmente aprendido | End-to-end learned adjacency; no prior graph |

---

## Comparative Matrix (20 entries)

Columns:

1. **Referência** — First author + year + acronym
2. **Ano** — Publication year (preprint / official)
3. **Tarefa** — Supervised task type
4. **Domínio** — Application domain
5. **Unidade dos nós** — Node semantic unit
6. **Semântica das arestas** — Edge meaning
7. **Categoria do grafo** — One of the 5 taxonomy codes
8. **Evolução temporal** — How time is modeled
9. **Memória temporal** — Temporal memory mechanism
10. **Snapshots** — Number of time steps in published experiments
11. **Dimensão dos dados** — Node count × feature count (approx.)
12. **Missingness** — Native support for missing data
13. **Interpretabilidade** — Interpretability of outputs
14. **Custo** — Computational cost relative to HERALD budget
15. **Parâmetros** — Approximate parameter count (when available)
16. **Código** — Code availability and license
17. **Licença** — License (if known)
18. **Compatibilidade T curto** — Compatible with T≈10–15 annual snapshots
19. **Risco de overfitting** — Overfitting risk on short panels
20. **Componente reutilizável** — What HERALD can reuse
21. **Decisão HERALD** — REFERENCE / ADAPT / BASELINE / REJECT
22. **Justificativa** — One-line reason

---

| Referência | Ano | Tarefa | Domínio | Unidade dos nós | Semântica das arestas | Categoria do grafo | Evolução temporal | Memória temporal | Snapshots | Dimensão dados | Missingness | Interpretabilidade | Custo | Parâmetros | Código | Licença | T≈10–15 compat. | Risco overfit | Componente reutilizável | Decisão HERALD | Justificativa |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Seo et al. 2018 — GConvGRU | 2018 | Regressão, Classificação | Genérico (vídeo, grafos) | Nó genérico | Fixo (qualquer adjacência observada) | FIX-DYN | Sequencial por snapshot | GRU com convolução espectral de grafo | ~100–2000 (experimentos movimentados/vídeo) | N=any × F=any | Não nativo | Baixo (pesos GRU) | Baixo–Médio | ~2×d_h²×K (d_h=hidden, K=filtros Chebyshev); ≈2 000 p/ d_h=8,K=3 | Sim — PyTorch Geometric, stellargraph | MIT/Apache | **Sim**, se d_h≤8, K≤3, 1 camada | Alto sem dropout forte | Célula GRU com propagação de grafo — componente central de A1 | **ADAPT** | Validado conceitualmente por EconoGNN (2026); única arquitetura com evidência em domínio econômico; adaptar com d_h≤8, 1 camada, dropout≥0.3 |
| Seo et al. 2018 — GConvLSTM | 2018 | Regressão, Classificação | Genérico | Nó genérico | Fixo observado | FIX-DYN | Sequencial por snapshot | LSTM com convolução espectral de grafo | ~100–2000 | N=any × F=any | Não nativo | Baixo | Baixo–Médio | Maior que GConvGRU (~4×d_h²×K por 4 gates) | Sim — PyG, stellargraph | MIT/Apache | **Sim**, com restrições | Alto | Alternativa de ablação à GConvGRU; testar se LSTM vs GRU muda resultado | **ADAPT** | Ablação de memória vs. GConvGRU; EconoGNN reporta GConvLSTM F1=0.740 < GConvGRU F1=0.750 |
| Li et al. 2018 — DCRNN | 2018 | Regressão | Tráfego rodoviário | Sensor de trânsito | Difusão bidirecional sobre rede viária | FIX-DYN | Encoder–decoder com difusão | GRU com difusão de grafo | >1 000 (METR-LA: 34 272 steps) | N=207, 325 × F=1 | Não nativo | Muito baixo | Alto | ~370k params (METR-LA config) | Sim — TF e PyTorch | MIT | **Não** — encoder–decoder para horizonte >1 passo; T=10–15 insuficiente | Extremo (sem regularização forte) | Difusão bidirecional como alternativa a ChebNet; não usar end-to-end | REJECT | Escala exige T>>100; encoder–decoder inadequado para T≈10; acrescenta sobre GConvGRU sem benefício claro |
| Yu, Yin, Zhu 2018 — STGCN | 2018 | Regressão | Tráfego | Sensor de trânsito | Fixo (rede viária) | FIX-DYN | Blocos conv. temporais + GCN | Convolução temporal 1D (gated) | >1 000 (IJCAI-18 benchmarks) | N=228, 307 × F=1 | Não nativo | Baixo | Médio | ~300k params | Sim — PyTorch (VeritasYin/STGCN_IJCAI-18) | MIT | **Não** — convolução temporal requer T>>kernel size | Extremo com T=10–15 | Ideia de blocos puramente convolucionais (sem recorrência) | REJECT | Convolução temporal requer T>kernel (kernel=3 usual); T≈10 deixa <4 posições válidas; over-parameterizado |
| Pareja et al. 2020 — EvolveGCN-H | 2020 | Classificação de nó/aresta | Grafos dinâmicos (Bitcoin, Reddit) | Nó genérico | Dinâmico observado (arestas mudam por snapshot) | D-OBS | Evolução de pesos GCN via GRU | GRU para evoluir matrizes de peso do GCN | 10–137 snapshots (experimentos: Bitcoin 10, Reddit 137) | N~variable | Não nativo | Baixo–Médio | Médio | Depende de N e d_h; ~similar a GCN+GRU | Sim — IBM/EvolveGCN (PyTorch) | Apache 2.0 | **Sim** — testado com apenas 10 snapshots (Bitcoin) | Médio–Alto | Evolução de pesos GCN via GRU — permite adaptar grafo sem aprender N×N arestas | **ADAPT** | Única arquitetura testada com T tão curto quanto 10; permite topologia dinâmica sem aprender arestas densas; adequada para D-OBS L2 |
| Pareja et al. 2020 — EvolveGCN-O | 2020 | Classificação de nó/aresta | Grafos dinâmicos | Nó genérico | Dinâmico observado | D-OBS | Evolução de pesos GCN via LSTM+output gate | LSTM com gate de saída para evoluir pesos GCN | 10–137 snapshots | N~variable | Não nativo | Baixo | Médio | ~similar a EvolveGCN-H | Sim — IBM/EvolveGCN (PyTorch) | Apache 2.0 | **Sim** — mesma referência que EvolveGCN-H | Médio–Alto | Variante com LSTM; comparar ablação vs. EvolveGCN-H em T=10 | **ADAPT** | Alternativa de ablação para EvolveGCN-H; LSTM gate vs. GRU; testar se memória adicional ajuda com T tão curto |
| Wu et al. 2019 — Graph WaveNet | 2019 | Regressão | Tráfego | Sensor de trânsito | Totalmente aprendido (adaptive adjacency) | FULL-LEARN | Dilated causal conv. (WaveNet) | Dilatação temporal exponencial | >1 000 (METR-LA, PEMS-BAY) | N=207, 325 × F=2 | Não nativo | Muito baixo | Alto | ~600k params | Sim — nnzhan/WaveNet-in-GNN | MIT | **Não** — grafo aprendido de N×N params; T>>100 necessário | Extremo | Ideia de self-adaptive adjacency via embeddings de nó | REJECT | Aprende N×N matriz com N=23–306; T=10–15 torna impossible regularizar; performance irreproducível |
| Bai et al. 2020 — AGCRN | 2020 | Regressão | Tráfego | Sensor de trânsito | Totalmente aprendido (DAGG module) | FULL-LEARN | Sequencial | GRU com parâmetros nó-específicos (NAPL) | >1 000 (PEMSD4, PEMSD8) | N=307, 170 × F=3 | Não nativo | Muito baixo | Alto | ~750k params | Sim — LeiBAI/AGCRN (PyTorch) | MIT | **Não** — NAPL requer embedding d=64 por nó; N×d parâmetros só na embedding | Extremo | Conceito de node-specific params via embedding; útil como ablação frugal | REJECT | Aprender N embeddings+grafo com T=10–15 é estatisticamente impossível; projetado para N>100, T>1000 |
| Wu et al. 2020 — MTGNN | 2020 | Regressão | Séries multivariadas | Série temporal | Totalmente aprendido (mix-hop propagation) | FULL-LEARN | Conv. 1D dilated (TCN) | Convolução temporal | >1 000 (metrópoles de tráfego) | N=137–207 × F=1 | Não nativo | Muito baixo | Alto | ~1.2M params | Sim — nnzhan/MTGNN (PyTorch) | MIT | **Não** | Extremo | Ideia de mix-hop propagation para capturar vizinhança multi-hop | REJECT | TCN exige T>>kernel size; grafo totalmente aprendido; escala de tráfego incompatível |
| Shang, Chen, Bi 2021 — GTS | 2021 | Regressão | Séries temporais | Série temporal | Totalmente aprendido (Bernoulli gráfico) | FULL-LEARN | GRU | GRU | >1 000 (traffic benchmarks) | N=207 × F=1 | Não nativo | Baixo | Alto | ~500k params | Sim — chaoshangcs/GTS (PyTorch) | MIT | **Não** | Extremo | Estrutura de aprendizado probabilístico de grafo discreto; não aplicável a T=10–15 | REJECT | Aprende distribuição sobre grafos com T>100 amostras; T=10–15 insuficiente para estimação estável |
| Hallac, Park, Boyd, Leskovec 2017 — TVGL | 2017 | Inferência de rede | Finanças, Saúde | Série temporal multivariada | Matriz de precisão condicional (variação total) | PART-LEARN | Regularização de variação total entre snapshots | Não (L1 temporal, não recorrente) | ~10–100 | N<100 recomendado | Limitado (requer imputação prévia) | Médio (grafo esparso interpretável) | Muito alto (otimização convexa iterativa) | N²·T parâmetros; resolve com ADMM | Sim — davidhallac/TVGL (Python) | BSD | **Sim** — TVGL foi avaliado com T=10–50 em finanças | Baixo (regularização explícita) | Estimação de grafo esparso dinâmico (G2/G3 candidato para HERALD) | **BASELINE** | Método de inferência de grafo dinâmico mais frugal disponível; adequado como comparativo analítico para o grafo L2 observado |
| Matias, Miele 2017 — dynSBM | 2017 | Detecção de comunidade | Redes sociais, biológicas | Nó genérico | Dinâmico observado (Markov latente) | D-OBS | Cadeias de Markov para memberships latentes | Não (variacional EM, não recorrente) | 10–50 (avaliação em redes sociais) | N<200 recomendado | Não (requer rede completa) | Alto (memberships interpretáveis) | Médio (VEM iterativo) | K×K + N×K parâmetros (K=comunidades) | Sim — R dynsbm package (CRAN) | GPL | **Sim** — testado com T=10+ | Baixo (parâmetros limitados) | Modelo probabilístico de evolução de comunidade (G3 candidato) | **BASELINE** | Único modelo de comunidade temporal com evidência em T pequeno; alternativa analítica a Louvain sliding-window |
| Hamilton, Ying, Leskovec 2017 — GraphSAGE | 2017 | Classificação de nó | Redes sociais, citações | Nó genérico | Estático (qualquer) | E-OBS | Não (estático) | Não | N/A (transductivo/indutivo, 1 snapshot) | N=100k+ | Não nativo | Baixo | Baixo | ~1k–100k params | Sim — williamleif/GraphSAGE (PyTorch) | MIT | **Marginal** — estático; usável como baseline sem grafo temporal | Baixo–Médio | Aggregação por amostragem estocástica de vizinhança (componente reutilizável para 1-hop) | **BASELINE** | Baseline estático inativo temporalmente; comparativo para A0/A1 (ablação "sem memória temporal") |
| Xu, Ruan et al. 2020 — TGAT | 2020 | Classificação de nó e aresta | Redes de interação temporal (Reddit, Twitter) | Evento temporal | Contínuo temporal (eventos, não snapshots) | D-OBS | Self-attention temporal com encoding funcional | Multi-head attention temporal | Contínuo (não snapshots) | N=10k–200k | Não nativo | Médio (attention weights) | Alto | ~300k params | Sim — StatsDLMacedonia/TGAT-PyTorch | MIT | **Não** — contínuo temporal (não snapshot); assume eventos densos | Alto | Encoding funcional de tempo; attention temporal — conceito transferível | REJECT | Projetado para grafos de eventos contínuos (Twitter/Reddit); não compatível com snapshots anuais esparsos |
| Cini, Marisca, Bianchi, Alippi 2022 — GRIN | 2022 | Imputação de dados | Sensores ambientais, tráfego | Sensor | Fixo ou aprendido (qualquer) | FIX-DYN | Bidirecional recorrente + MPNN | GRU bidirecional | >1 000 (AQI, METR-LA) | N=36–207 | **Nativo** — projetado para missingness | Alto (imputação interpretável) | Médio | ~500k params | Sim — Graph-Machine-Learning-Group/grin | MIT | **Marginal** — recorrência bidirecional requer T suficiente; adaptar para T=10–15 com cuidado | Médio | Imputação bidirecional com GNN — componente reutilizável para tratamento de KZ e outros missings estruturais | **ADAPT** | Único modelo com missingness nativo e GNN; componente de imputação (não recorrência bidirecional completa) aplicável ao KZ/OQ mascarados |
| Gordon, Petousis, Zheng, Zamanzadeh, Bui 2021 — TSI-GNN | 2021 | Imputação de dados | Saúde (EHR) | Paciente (nó bipartido) | Bipartido paciente–feature, temporal | FIX-DYN | Message passing temporal em grafo bipartido | Variável (GNN por camada temporal) | >100 (EHR datasets) | N~variable | **Nativo** | Médio | Médio | ~variable | Sim — (Frontiers Open Access) | CC BY 4.0 | **Marginal** — bipartido e saúde; adaptar semântica | Médio | Grafo bipartido para missingness temporal — conceito aplicável a território×setor com ausências estruturais | **ADAPT** | Grafo bipartido + missingness nativo; conceito de nó feature-type relevante para estrutura território×setor de HERALD |
| Xu, Kosma, Vazirgiannis 2023 — TimeGNN | 2023 | Previsão de série temporal | Genérico multivariado | Série temporal | Aprendido dinâmico (padrões de correlação) | FULL-LEARN | Dinâmica de grafo aprendida por janela | GNN evolutivo (sem GRU explícita) | >100 (Energy, Exchange-Rate, Traffic) | N=7–862 | Não nativo | Baixo | Baixo–Médio | ~small (anunciado 4–80× speedup) | Não disponível publicamente (preprint arXiv:2307.14680) | Não declarada | **Não** — grafo aprendido dinâmico; T=10–15 insuficiente | Alto | Ideia de aprendizado eficiente de padrões temporais de grafo | REJECT | Aprende grafo dinâmico a cada janela; T=10–15 insuficiente; sem código disponível para verificação |
| Araujo, Rodrigues, Sousa 2026 — EconoGNN | 2026 | Classificação binária (resiliência econômica) | Economia nacional (183 países) | País | Comércio internacional (UN COMTRADE) — **DTDG: topologia e labels evoluem** | D-OBS | Sequencial snapshot (GConvGRU, 5 janelas temporais) | GConvGRU | Abstract: 25 anos; corpo usa painel histórico mais longo | N=183 × F=50+ | Não é foco metodológico | Alto (GNNExplainer: Fidelity+=0.827) | Médio | d_h=64, 2 camadas na configuração reportada | GitHub incompleto; Zenodo 10.5281/zenodo.18751102 citado pelo artigo | PLOS ONE (CC BY 4.0) | **Não demonstrado** para T≈10–15 | Alto | Evidência de domínio econômico para o conceito GConvGRU; protocolo e escala não transferem | **REFERENCE** | Publicação peer-reviewed relevante, mas não seleciona nem valida a arquitetura HERALD |
| Sparse VAR-Granger (L1) | 2000s | Regressão multivariada (Granger-predictability) | Econometria, finanças | Série territorial ou setorial | Aresta Granger-preditiva (condicional L1) | PART-LEARN | VAR com janela rolling | Não (VAR linear) | T≥2p necessário; com p=9 setores, T≥18 mínimo | p×T (p=var count) | Limitado | Alto (coeficientes interpretáveis) | Baixo | p²×p_lags parâmetros | Scipy/statsmodels (Python) | BSD | **Marginal** — p requer agregar (p≤5 para T=10–15) | Baixo–Médio com L1 forte | Inferência de causalidade Granger-preditiva agregada — sem usar termo "causality" | **BASELINE** | Baseline linear de inferência de grafo; T≥2p restringe severamente; claim deve ser explicitamente "Granger-predictive edge, not causal" |
| Ridge/AR sem grafo (H0/A0) | 2000s | Regressão temporal | Genérico | Território | Nenhuma (sem grafo) | E-OBS | Rolling-origin AR features | Nenhum (linear estático) | N/A | N×F_lag (F_lag=2–5) | Compatível com máscaras | Alto (coeficientes) | Mínimo | ~F_lag×N parâmetros | sklearn (Python) | BSD | **Sim** — baseline HERALD confirmado (Phase 4N) | Mínimo | Baseline canônico de comparação; H0b é melhor baseline atual (Phase 5 ablation) | **BASELINE** | Melhor baseline comprovado; A0 deve bater este antes de avançar para A1; persistence=H0 também |

---

## Analysis Notes

### 1. Short panels (T≈10–15)

Models designed for traffic forecasting (T>1000) cannot be applied to T=10–15 without catastrophic overfitting. **DCRNN, STGCN, AGCRN, MTGNN, Graph WaveNet, GTS** all require T>>100 and are rejected.

Models with explicit regularisation and evidence on short graph sequences are
the least implausible candidates: **EvolveGCN-H/O, TVGL and dynSBM**.
**GConvGRU/GConvLSTM remain candidates because of their simple recurrent
structure and EconoGNN precedent, not because short-panel adequacy has already
been demonstrated.**

### 2. Graph learning vs. fixed graph

With p=23–306 territories × 9 sectors, learning a full N×N adjacency matrix from T=10–15 annual observations is statistically impossible without strong priors. **Only models that accept a fixed or observed-dynamic graph are viable for A1**.

**FULL-LEARN** category models (Graph WaveNet, AGCRN, MTGNN, GTS, TimeGNN) are all rejected on this basis.

### 3. Missingness

PT KZ and NL OQ sectors have structural absences. Only **GRIN** and **TSI-GNN** offer native missingness support. GRIN's bidirectional recurrence cannot be applied directly to T=10–15 forward-only rolling-origin, but its message-passing imputation component can be adapted.

### 4. EconoGNN classification (corrected)

Prior draft classified EconoGNN as "Fixo (Trade)". **This is incorrect.** The
paper explicitly classifies the data structure as **DTDG with evolving topology
and evolving labels**. EconoGNN is a direct recent conceptual reference for
GConvGRU on an economic dynamic graph.

The decision changes from **REJECT** to **REFERENCE** because: (a) the paper is
verified; (b) it supports GConvGRU as an architecture concept in economic
domains; (c) task, scale and evaluation differences prevent direct reuse.

### 5. Pre-selection of GConvGRU

**GConvGRU is not pre-selected in this matrix.** The prior draft pre-selected it; this matrix corrects that. The architecture decision document (HERALD_GRAPH_TEMPORAL_ARCHITECTURE_DECISION.md) must derive from this matrix, not the reverse.

Based on this matrix, viable candidates for HERALD are:
- **A0 (no graph):** Ridge/AR (BASELINE) or simple GRU without graph
- **A1 (fixed observed graph):** GConvGRU (ADAPT) or EvolveGCN-H (ADAPT) — both need frugal configuration
- **A1 (dynamic observed graph):** EvolveGCN-H/O (ADAPT) — if L2 is rebuilt per snapshot
- **G2 (graph estimation):** TVGL (BASELINE) or dynSBM (BASELINE) — for analytical comparison only

**EvolveGCN-H is a serious contender for dynamic L2 topology**, because:
1. It adapts GCN weights to topological changes without learning N×N edges
2. It was empirically tested with T=10 snapshots (Bitcoin dataset)
3. It does not require learning a full adjacency matrix

**GConvGRU is a candidate for FIX-DYN and may be adapted to D-OBS only after
testing variable adjacency explicitly.**
**EvolveGCN-H is the more direct candidate for D-OBS** (observed L2 changes per
year), because it was designed for graph sequences with changing topology.

HERALD's current L2 artefacts are time-indexed observed graphs, so the default
representation is D-OBS. The architecture decision therefore requires a
same-target local comparison of low-capacity GConvGRU and EvolveGCN-H, with no
pre-selected winner.

---

## Classification Summary

| Decisão | Count | Entries |
|---------|------:|---------|
| REFERENCE | 1 | EconoGNN |
| ADAPT | 6 | GConvGRU, GConvLSTM, EvolveGCN-H, EvolveGCN-O, GRIN, TSI-GNN |
| BASELINE | 5 | TVGL, dynSBM, GraphSAGE, VAR-Granger, Ridge/AR |
| REJECT | 8 | DCRNN, STGCN, Graph WaveNet, AGCRN, MTGNN, GTS, TGAT, TimeGNN |
| **Total** | **20** | |
