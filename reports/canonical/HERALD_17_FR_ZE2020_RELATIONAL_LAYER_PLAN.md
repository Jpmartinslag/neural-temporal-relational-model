# HERALD 17 — France ZE2020 Relational Layer: Audit and Plan

**Created:** 2026-06-24. **Status:** PLANNING_ONLY — nenhum modelo neural/grafo foi
implementado, nenhum treino pesado foi executado, nenhum claim de performance é feito
nesta pass. Este documento responde a três perguntas: o que já existe no repositório que
poderia alimentar uma camada relacional ZE2020/setores, o que falta ou precisa de
reconstrução, e qual hipótese e MVP devem ser testados antes de qualquer modelo
neural/grafo final.

**Scope:** apenas a camada relacional FR/ZE2020 — não toca o dashboard, `hpc_results/`,
Itália/Áustria, dados brutos, a cadeia limpa França/ZE2020 (`fr_ze2020_clean_panel.csv`,
`fr_ze2020_model_ready_panel.csv`) nem `train_fr_ze2020_baselines.py`. Não reabre nenhum
branch fechado (DEC-008/009/023/029/031) sem nova hipótese — ver §4 e §7.

**Lido antes desta pass:** `README.md`, `reports/README.md`,
`reports/HERALD_CURRENT_STATE.md`, `reports/HERALD_NAMING_CONVENTIONS.md`,
`reports/canonical/HERALD_03..04, 09, 10, 14, 15, 16`, `reports/herald_artifact_registry.json`,
`/home/jpdark/.codex/RTK.md`, `CODEX_MEMORY.md`. Cross-referenciado, não duplicado.

---

## 0. Restrição estrutural herdada da cadeia limpa (HERALD_15 §10)

`reports/herald_artifact_registry.json::PANEL_FR_ZE2020_MODEL_READY_CAUSAL` proíbe
explicitamente **"Adding a sector dimension or graph/network structure to this file"**.
Qualquer camada relacional ou setorial é, por regra já existente, um **arquivo novo**,
nunca uma edição de `fr_ze2020_clean_panel.csv`/`fr_ze2020_model_ready_panel.csv`. Este
plano assume essa restrição como ponto de partida, não como descoberta nova.

---

## 0b. Técnicas existentes verificadas (motivação metodológica do MVP2)

Pesquisa curta (não é revisão bibliográfica longa) para confirmar que o MVP2 é uma etapa
metodológica conhecida — testar agregações relacionais simples antes de qualquer GNN —
e não uma invenção ad-hoc deste projeto.

| Técnica | Ideia central | Relação com ZE2020 | Serve para o MVP2? | Risco/cuidado metodológico |
|---|---|---|---|---|
| Spatial Lag / SLX model (LeSage & Pace; PySAL `spreg`, `spreg.ML_Lag`/`spreg.GM_Lag`) | A variável dependente ou os preditores são "lagados espacialmente" por `Wy`/`WX`, a média ponderada dos vizinhos via uma matriz de pesos `W` | É a justificativa formal direta do MVP2: "vizinhos pesados" é exatamente o que as features `similar_ze_*` calculam, só que com `W` definido por similaridade de trajetória em vez de uma matriz geográfica fixa | Sim — é a referência metodológica central | Um SAR/SLX completo estima um parâmetro espacial com inferência formal; aqui usamos só a feature agregada como input de Ridge, sem estimar esse parâmetro — mais simples, sem claim de autocorrelação espacial validada |
| Bartik (1991) shift-share / shift-share instruments (ver NBER w24408, w33236) | Decompõe o crescimento local em um componente nacional por setor × uma composição local pré-determinada (pesos fixos no tempo) | Mapeia diretamente para a Categoria C (composição setorial da ZE × sinal setorial nacional) | Motivacional apenas — Categoria C está `BLOQUEADO/PENDING_PROVENANCE` nesta pass (ver §1, item 6, e §B abaixo) | Shift-share é desenhado para identificação causal via instrumento; aqui seria usado só como *feature* preditiva — nunca como prova de efeito causal |
| Hidalgo, Klinger, Barabási & Hausmann (2007), "The Product Space Conditions the Development of Nations", *Science* 317 | Relacionamento entre produtos/setores via co-ocorrência de especialização revelada, usado para prever diversificação futura | Análogo conceitual à Categoria B/C (relatedness entre setores em vez de geografia) | Não nesta pass — precisa do painel setorial, que está bloqueado | Relatedness de produto/setor não é território; adaptar exigiria o dado setorial canônico que ainda não existe (§B) |
| k-NN / graph feature engineering antes de GNN (prática padrão de pré-processamento; ver também `KNN-GNN`, k-NN graph construction) | Construir um grafo via k-vizinhos-mais-próximos num espaço de features, agregar estatísticas dos vizinhos como *feature tabular* antes de qualquer rede neural de grafo | É exatamente o método do MVP2: similaridade de trajetória, top-k positivo, agregação simples (média/média ponderada) | Sim — é o método central implementado nesta pass | É preciso garantir que o espaço de features usado para achar vizinhos não inclua o ano-alvo — resolvido aqui via janela expansiva estritamente `< t` (ver §10) |
| Shchur, Mumme, Bojchevski & Günnemann (2018), "Pitfalls of Graph Neural Network Evaluation" (NeurIPS RLR workshop; arXiv:1811.05868) | Sob comparação justa (mesmos splits, mesmo tuning), baselines simples (MLP, regressão logística, label propagation) batem arquiteturas GNN mais sofisticadas em vários benchmarks-padrão | Justificativa direta de por que este projeto testa features relacionais simples (MVP2) antes de qualquer GNN (MVP3) — e por que os 3 modelos do MVP2 precisam compartilhar exatamente o mesmo conjunto de teste por ano (ver §10) | Sim — justificativa metodológica central da ordem MVP2→MVP3 | A lição é sobre rigor de avaliação (splits/tuning idênticos); aplicada aqui ao exigir mesmo `n_test` por ano entre os 3 modelos antes de comparar WMAPE |

Conclusão da pesquisa: o MVP2 não é uma técnica nova — é a aplicação direta de "spatial-lag-like
feature engineering" (vizinhança ponderada) e da prática estabelecida de testar baselines
simples antes de GNN, adaptada para usar similaridade de trajetória (não uma matriz
geográfica sem proveniência) como definição de vizinhança.

---

## 1. Inventário de artefatos existentes

Vocabulário de status usado nesta tabela (subconjunto do pedido na tarefa, alinhado ao
vocabulário já existente em `reports/HERALD_NAMING_CONVENTIONS.md` §6 e
`reports/herald_artifact_registry.json`):

`CANONICAL_INPUT` · `CANDIDATE_RAW_RELATION` · `CANDIDATE_NEEDS_PROVENANCE` ·
`CLOSED_BRANCH_REFERENCE` · `SECTOR_RELATION_EVIDENCE` · `LEGACY_DO_NOT_USE` ·
`UNKNOWN_REVIEW_REQUIRED`.

| # | Arquivo | Tipo de relação | Granularidade | Gerador encontrado? | Status | Pode ser usado agora? | Observação |
|---|---|---|---|---|---|---|---|
| 1 | `data/processed/france_ze2020/fr_ze2020_clean_panel.csv` | base observada (sem relação) | ZE2020, 280 zonas | Sim — `build_fr_ze2020_clean_panel.py` | `CANONICAL_INPUT` | Sim, como base | HERALD_15 §3. Sem growth/lag/setor. |
| 2 | `data/processed/france_ze2020/fr_ze2020_model_ready_panel.csv` | tempo→trajetória (lag_1/2/3, growth_1y/2y_safe) | ZE2020, 280 zonas | Sim — `build_fr_ze2020_model_ready_panel.py` | `CANONICAL_INPUT` | Sim — é o input do MVP1 | HERALD_15 §10. Único painel que `train_fr_ze2020_baselines.py` lê. |
| 3 | `data/processed/graph_adjacency_core_v0.csv` | ZE→ZE, vizinhança geográfica binária | ZE2020, 280×280 | **Não** — script ausente da árvore atual (HERALD_16 §4.1) | `CANDIDATE_NEEDS_PROVENANCE` | Não como input confiável; sim como matéria-prima candidata | **Verificado nesta pass:** simétrica, diagonal zero, mesmo conjunto de 280 zonas e mesma ordenação `node_idx`/`node_id` do painel canônico atual (0 divergências em 280 linhas, comparado contra `fr_ze2020_model_ready_panel.csv`). Consistência estrutural alta, mas o método de construção (limiar de distância? contiguidade administrativa?) é desconhecido. |
| 4 | `data/processed/graph_adjacency_mobility_v0.csv` | ZE→ZE, mobilidade ponderada (pré-COVID) | ZE2020, 280×280 | **Não** — idem | `CANDIDATE_NEEDS_PROVENANCE` | Não como input confiável; sim como matéria-prima candidata | Assimétrica (fluxo direcional), linhas somam 1.0 (normalizada). Mesma verificação estrutural do item 3 aplica. `reports/HERALD_INTELLIGENCE_LAYER_SPEC.md` descreve como "mobilité pré-COVID, peut sous-représenter télétravail". |
| 5 | `data/processed/graph_node_index_core_v0.csv` | índice ZE2020 ↔ `node_idx` (não é relação em si) | ZE2020, 280 linhas | Não | `CANDIDATE_NEEDS_PROVENANCE` | Sim, como índice apenas | Ordenação idêntica ao `node_id` de `fr_ze2020_model_ready_panel.csv` (verificado nesta pass) — útil se as matrizes 3/4 forem revalidadas, mas não certifica os *valores* delas. |
| 6 | `data/processed/side_creations_a10_ze2020_through_2025_v1.csv` | ZE × setor (A10), criações por ano | ZE2020 × 9 setores A10, 280×14×9 | Parcial — dado commitado junto com V4/V5 (`bc43a79`), sem builder dedicado na árvore | `CANDIDATE_NEEDS_PROVENANCE` | Sim, com cautela | **Novo achado desta pass:** a coluna `total` reconcilia exatamente (diff máx. absoluta = 0.0, 3920/3920 linhas) com `establishment_creations` do painel canônico `fr_ze2020_clean_panel.csv`. Conteúdo internamente consistente com a linhagem canônica atual, mesmo sem builder próprio na árvore. Candidato mais forte da Categoria C — ver §2.C. |
| 7 | `data/processed/herald_observatory_v04_granular/granular_relation_edges.csv` | setor→setor (precedência temporal, lag-1) | país-agregado (FR/NL_COROP/PT_Municipal), **não desagregado por ZE** | Sim — `build_sector_precedence_graph.py` + `build_observatory_v04_granular_exports.py` | `SECTOR_RELATION_EVIDENCE` | Sim, por tier (DEC-066) | FR=9 arestas, mas só 1 `ROBUST_ORIGINAL` (RU→MN, ela própria `FR_COVID_SENSITIVE`, DEC-060); as outras 8 são `FINE_GRAIN_SUPPORTED`/`EXPLORATORY_FINE_GRAIN`. Relação agregada nacional, não ZE-específica. |
| 8 | `data/processed/sector_precedence_results/` | setor→setor, bundle bruto Phase 7 | país-agregado | Sim — DEC-034, `SECTOR_PRECEDENCE_PROTOTYPE_READY` | `SECTOR_RELATION_EVIDENCE` | Sim (frozen) | Mesma ressalva do item 7: agregado, não por ZE. |
| 9 | `data/processed/france_relation_audit/` | diagnóstico (não é dado relacional) | ZE2020 e NUTS3 comparados | Sim — `run_dec060_france_signal_audit.py` | `CLOSED_BRANCH_REFERENCE` | Sim, como referência metodológica | DEC-060: explica por que FR tem sinal setorial fraco — efeito de escala ecológica (zonas pequenas → \|β\| menor), não falha de método. Essencial para calibrar expectativas de qualquer relação setorial ZE-específica futura. |
| 10 | `data/processed/economic_graph/sector_panel_fr_nuts3.csv`, `g1_l2_cogrowth/`, `g1_observable/`, `g2_preflight/`, `g2_dynamics/` | território↔território (co-growth, estrutura) e setor relatedness | **Não ZE2020** — IDs de região tipo `1101`/`2714`/`7515` que **não correspondem** ao espaço de códigos `ze2020` canônico (`"0051".."9999"` zero-padded, verificado nesta pass) | Sim — `build_g1_l2_cogrowth.py`, `build_g1_observable_graph.py`, `build_g2_*.py` | `CANDIDATE_NEEDS_PROVENANCE` para uso em ZE2020 (precisa de crosswalk verificado); `CLOSED_BRANCH_REFERENCE` para uso preditivo | Não diretamente — esquema de ID diferente, sem crosswalk documentado para `ze2020` | G1-L2 co-growth é `VALIDATED` como associação descritiva (DEC-019/020), mas Phase 5 (corretor neural fixo sobre o mesmo grafo) é `NOT_SUPPORTED` (DEC-023) — negativo específico para uso preditivo, não apenas falta de prova. |
| 11 | `data/processed/economic_graph/g1_l1_sector/` | setor→setor, RCA co-specialization | país-agregado | Sim — `build_g1_l1_sector_graph.py` | `CLOSED_BRANCH_REFERENCE` | Não | `NOT_SUPPORTED` (DEC-017: NL pass, FR fail). |
| 12 | `data/processed/dual_graph_s1/`, `dual_graph_pilot_all_folds/`, `dual_graph_tensors/` | grafo duplo aprendido (território+setor) | FR **NUTS3**, não ZE2020 | Sim — `build_dual_graph_tensors.py` | `LEGACY_DO_NOT_USE` / `CLOSED_BRANCH_REFERENCE` | Não | `DUAL_GRAPH_S1_FAIL` (DEC-029), todos os 7 critérios de gate falham. Rótulos de aresta setorial `INVALID_FOR_INTERPRETATION` (DEC-030). |
| 13 | `data/processed/graph_temporal_v2/FR/`, `graph_temporal_s1/` | adjacência ZE2020 derivada estatisticamente (correlação, `positive_topk`) por ano, usada como input de GNN | ZE2020, 280 nós, 9 setores | Sim — `build_graph_temporal_v2.py`, DEC-028 `FR_ADJACENCY_READY` | `CLOSED_BRANCH_REFERENCE` | Não como input de previsão | `S1_FR_FAIL` (DEC-031): GConvGRU/EvolveGCN-H indistinguíveis de nulos de permutação (p=1.0). **Este é o prior negativo mais direto para qualquer grafo ZE2020 como correção de previsão** — já foi tentado exatamente nesta granularidade e falhou. O *método* de construção da adjacência (correlação, sem nós isolados, 1 componente conectado) é reaproveitável como referência; a conclusão preditiva não. |
| 14 | `data/processed/dynamic_stgnn_feature_panel_v1.csv` e família (`flores_panel_ze2020_annual_v1.csv`, `side_stocks_lagged_ze2020_annual_v1.csv`, `dynamic_stgnn_walk_forward_splits_v1.csv`) | painel legado unificado (sem relação explícita, mas com vazamento confirmado) | ZE2020, 280 zonas | Sim — `build_dynamic_stgnn_feature_panel_v1.py` | `LEGACY_DO_NOT_USE` | Não | HERALD_15 §5: `growth_1y`/`growth_2y` são `pct_change()` sobre o próprio target — vazamento confirmado. |
| 15 | `data/external/ze2020_geometry.geojson` | geometria de polígono ZE2020 (não é grafo, mas matéria-prima para um) | ZE2020, 280 features | Geometria em si sim (usada pelo dashboard); builder de um **grafo** a partir dela não existe | `CANDIDATE_RAW_RELATION` | Não ainda — nenhum builder de contiguidade/distância existe sobre este arquivo | Permitiria construir uma matriz de vizinhança **nova e documentada** (queen contiguity ou distância de centroide), em vez de reutilizar os itens 3/4 sem proveniência. Mas: contiguidade geográfica já falhou como input preditivo em dois contextos distintos do projeto (DEC-008/009 Itália, DEC-031 FR ZE2020) — ver §4. |
| 16 | `data/processed/herald_observatory_v04_granular/blocked_proxy_edges.csv` | NL gemeente proxy (não-FR) | N/A para FR | Sim | `LEGACY_DO_NOT_USE` (fora de escopo FR) | Não | Listado apenas porque os termos de busca da tarefa incluíam "edge"/"relation"; não é um candidato FR. Mantido `BLOCKED_PROXY_ARTIFACT` por DEC-065, sem relação com este plano. |

---

## 2. Categorias de relações

### A. Relações ZE → ZE

**O que já existe:** itens 3, 4, 5, 13, 15 da tabela acima. Nenhum tem proveniência E
desempenho preditivo validado simultaneamente: os itens 3/4/5 têm boa consistência
estrutural (mesmo escopo de 280 zonas, mesma ordenação) mas método de construção
desconhecido; o item 13 tem método documentado (DEC-028) mas resultado preditivo
`FAIL` (DEC-031); o item 15 é só geometria, sem grafo construído ainda.

**O que falta:** uma matriz ZE↔ZE com (a) método de construção documentado e
reprodutível, (b) escopo de 280 zonas idêntico ao painel canônico, (c) nenhuma reutilização
silenciosa de um arquivo sem proveniência como se fosse confiável.

**Risco metodológico:** contiguidade geográfica como insumo preditivo já falhou duas
vezes no projeto, em dois contextos diferentes — Itália queen-contiguity (DEC-008/009,
`FAIL`) e FR ZE2020 correlação-estatística via `graph_temporal_v2` (DEC-031,
`S1_FR_FAIL`, indistinguível de grafo permutado). Isso não impede reabrir a pergunta, mas
significa que **qualquer nova tentativa precisa de uma hipótese genuinamente diferente**
(ex.: representação antes da previsão, não correção depois — ver §4), não apenas reusar
ou reconstruir a mesma adjacência geográfica.

**Pode entrar no primeiro protótipo (MVP2)?** Sim, mas apenas como *feature* simples
(média ponderada de vizinhos), nunca como grafo neural direto, e preferencialmente
construída diretamente das séries observadas (similaridade de trajetória de
`observed_value`) em vez de reativar os itens 3/4 sem proveniência — ver MVP2 em §5.

**Precisa de nova DEC?** Para MVP2 (feature linear simples, sem rede neural, comparada
contra o baseline já existente): não necessariamente, é o tipo de exploração de baixo
risco que o resto do projeto já fez sem DEC formal (ex.: G2 preflight). Para MVP3 (grafo
neural): **sim**, dado o histórico de 2 FAILs já registrados.

**Precisa de reconstrução/proveniência?** Sim, para os itens 3/4 se algum dia forem
usados como peso de aresta — caso contrário, preferir uma similaridade nova e documentada
(distância de centroide do item 15, ou similaridade de trajetória pura).

### B. Relações setor → setor

**O que já existe:** itens 7, 8, 9, 11 — o pipeline metodologicamente mais rigoroso do
projeto (bootstrap/permutação/FDR, DEC-033/034/066), mas **agregado por país**, não por
ZE. FR tem só 1 relação `ROBUST_ORIGINAL` (e ela é `FR_COVID_SENSITIVE`).

**O que falta:** uma versão **desagregada por ZE2020** — i.e., "este par de setores se
precede dentro desta zona específica", em vez de "dentro da França como um todo". Isso
não existe em lugar nenhum do repositório hoje.

**Risco metodológico:** DEC-060 já mostrou que o sinal setorial francês é
estruturalmente fraco no nível agregado por causa do tamanho pequeno das ZE2020
individuais (zonas pequenas → efeito \|β\| menor, FR 280 zonas vs PT 278 municípios vs NL
40 COROP). Desagregar por ZE multiplicaria esse problema de poder estatístico, não o
resolveria — qualquer rerun de Phase 7 por ZE deve esperar um sinal ainda mais fraco do
que o já fraco resultado agregado, não um sinal mais forte.

**Pode entrar no primeiro protótipo (MVP2)?** Sim, mas só como sinal **agregado
nacional**, broadcast como feature constante por ano/setor — nunca fingindo ser uma
relação ZE-específica que ainda não existe.

**Precisa de nova DEC?** Sim, para qualquer rerun de Phase 7 desagregado por ZE (custo de
HPC, e o próprio DEC-060 já recomenda cautela com o threshold atual nessa escala).

### C. Relações ZE × setor (especialização/composição)

**O que já existe:** item 6 (`side_creations_a10_ze2020_through_2025_v1.csv`) — o candidato mais
promissor desta auditoria. Reconciliado nesta pass contra o painel canônico (diff 0.0).

**O que falta:** um painel canônico de setor por ZE construído com o **mesmo rigor** da
linhagem `fr_ze2020_clean_panel.csv` → `fr_ze2020_model_ready_panel.csv` (código
zero-padded, filtro explícito de 280 zonas, máscaras de disponibilidade, *sem* reusar o
painel legado `dynamic_stgnn_feature_panel_v1.csv`). Hoje o item 6 não tem máscaras, não
tem features de lag/growth, e não tem teste de regressão como os painéis canônicos têm.

**Risco metodológico:** baixo — os valores já reconciliam exatamente com o painel
canônico. O risco real é de *padrão*, não de *conteúdo*: construir o painel sem replicar a
disciplina de máscaras/causal-safety já estabelecida em HERALD_15.

**Pode entrar no primeiro protótipo (MVP2)?** Sim — é a categoria mais pronta para um
próximo passo concreto: índice de concentração/diversificação setorial por ZE
(ex.: HHI inverso, share do setor dominante), usado como feature estática ou
quase-estática.

**Precisa de nova DEC?** Não para a construção do painel em si (mesmo padrão não-DEC já
usado para `fr_ze2020_clean_panel.csv`/`fr_ze2020_model_ready_panel.csv`). Sim antes de
usar como feature em qualquer claim de modelo treinado.

### D. Relações tempo → trajetória

**O que já existe:** completo. `fr_ze2020_model_ready_panel.csv` já tem `lag_1/2/3` e
`growth_1y_safe`/`growth_2y_safe`, causal-safe e testado (HERALD_15 §10, 13 testes).
Este é exatamente o MVP1 (controle).

**O que falta:** nada estrutural para a dimensão territorial; o equivalente setorial
virá "de graça" assim que o painel da Categoria C existir (mesmas fórmulas de
shift/growth, aplicadas por ZE×setor em vez de só por ZE).

**Risco metodológico:** nenhum — já causal-safe e testado.

**Pode entrar no primeiro protótipo?** Sim, já está dentro do MVP1.

**Precisa de nova DEC?** Não.

---

## 3. O que explicitamente NÃO deve ser usado ainda

| Artefato | Por quê | Pode ser usado como |
|---|---|---|
| `dynamic_stgnn_feature_panel_v1.csv` e família | Vazamento de target confirmado (HERALD_15 §5) | Histórico/motivação apenas |
| `graph_adjacency_core_v0.csv` | Gerador não encontrado na árvore atual | Matéria-prima candidata (consistência estrutural verificada, valores não verificados) |
| `graph_adjacency_mobility_v0.csv` | Idem | Idem |
| `graph_node_index_core_v0.csv` | Indexa os dois arquivos acima, cuja proveniência é desconhecida | Índice de referência apenas |
| `train_herald_v6.py`/`v7.py`/`semi_v2.py`/`regime_experiment.py` | `PENDING_REAUDIT`, dependem do painel legado com vazamento (HERALD_16) | Histórico de tentativas arquiteturais |
| `data/processed/dual_graph_s1/` e tensores associados | `DUAL_GRAPH_S1_FAIL` (DEC-029), rótulos de aresta `INVALID_FOR_INTERPRETATION` | Exemplo do que foi tentado e por que falhou |
| `data/processed/graph_temporal_v2/`, `graph_temporal_s1/` (como input de previsão) | `S1_FR_FAIL` (DEC-031) — indistinguível de grafo permutado | Referência metodológica de construção de adjacência (não a conclusão preditiva) |
| `economic_graph/g1_l2_cogrowth/`, `g1_observable/`, `g2_preflight/` (para uso ZE-específico) | Esquema de ID de região diferente do `ze2020` canônico, sem crosswalk verificado; e `NOT_SUPPORTED` para previsão (Phase 5, DEC-023) mesmo onde o ID combinasse | Evidência descritiva de co-growth nacional (DEC-019/020), nunca insumo ZE-específico sem crosswalk novo |
| `g1_l1_sector/` (RCA) | `NOT_SUPPORTED` (DEC-017) | Histórico |

Reuso permitido para todos os itens acima: **histórico, motivação, exemplo do que foi
tentado, hipótese para reconstrução**. Nunca como base atual sem reauditoria — consistente
com a regra já existente do projeto (Charter §8: falha de performance isolada nunca é
suficiente para reabrir um branch fechado; é preciso nova evidência + gate pré-registrado).

---

## 4. Hipótese científica

A Zone d'Emploi (ZE2020) não é uma divisão geográfica arbitrária: é uma unidade
metodológica oficial do INSEE que aproxima um mercado de trabalho local funcional
(mobilidade pendular, emprego, atividade econômica concentrada dentro de fronteiras que
tentam capturar onde as pessoas efetivamente trabalham e consomem). Por isso, tratar a
ZE como nó de uma rede é qualitativamente diferente de tratar, digamos, um quadrado de
grade arbitrário como nó — a unidade já carrega uma teoria econômica embutida na sua
própria definição.

**A hipótese:** relações entre ZEs e entre setores podem conter informação preditiva e
interpretativa que uma regressão temporal simples (persistência/Ridge sobre lags) não
representa. Um modelo neural/grafo futuro deveria aprender essas representações
territoriais e setoriais **antes** da etapa de previsão — como uma camada de
representação econômica — e não apenas como uma correção residual aplicada depois que a
previsão temporal já errou.

**Por que isso é uma hipótese genuinamente nova, e não apenas repetir o que já falhou
três vezes** (Itália queen-contiguity DEC-008/009, FR ZE2020 `graph_temporal` DEC-031,
FR NUTS3 grafo duplo DEC-029): todas as três tentativas anteriores usaram o grafo
**como insumo direto de um corretor de previsão** (a previsão de Ridge mais um termo de
grafo, ou um GNN substituindo diretamente o preditor). A hipótese aqui proposta é
arquiteturalmente diferente — usar a relação territorial/setorial como camada de
*representação* anterior à previsão, com uma saída explicitamente dividida em (1)
previsão controlada e (2) relações exploratórias, em vez de uma única saída de previsão
corrigida por grafo. Isso atende ao requisito do Charter §8 de que reabrir uma linha
fechada exige hipótese nova, não apenas repetir o experimento.

**Linguagem permitida:** associação, correlação, precedência temporal, valor preditivo,
hipótese exploratória, interpretação econômica por especialista — sempre com a frase de
não-causalidade já padronizada no projeto ("estas relações não estabelecem causalidade
estrutural").

**Linguagem proibida:** causalidade estrutural forte, "o modelo descobre a verdade",
"influência causal", "recomendação automática" (Bloco 3 — recomendação — permanece
0%, `NOT STARTED`, fora de escopo até Bloco 1+2 estarem completos per Charter).

---

## 5. MVP metodológico proposto (não implementado nesta pass)

### MVP 1 — Baseline temporal (controle, já existe)
- **Entrada:** `fr_ze2020_model_ready_panel.csv`.
- **Script:** `src/modeles/france_ze2020/train_fr_ze2020_baselines.py` (já existe,
  `claim_status=exploratory_smoke`).
- **Função:** controle contra o qual qualquer feature relacional precisa ganhar.

### MVP 2 — Features relacionais simples, sem rede neural
- Candidatos concretos, em ordem de prontidão:
  1. **Composição setorial por ZE** (Categoria C) — share do setor A10 dominante,
     índice de diversificação (HHI inverso), construído a partir do item 6 da tabela
     (já reconciliado contra o painel canônico).
  2. **Similaridade de trajetória entre ZEs** (Categoria A) — correlação ou distância
     entre séries de `observed_value`/`growth_*_safe`, calculada diretamente das
     observações já existentes — **sem** depender da proveniência desconhecida dos
     itens 3/4. k-vizinhos mais similares, média ponderada de seus lags como feature.
  3. **Sinal setorial nacional agregado** (Categoria B) — broadcast do
     `granular_relation_edges.csv` como feature constante por ano/setor, rotulado
     explicitamente como agregado nacional, não ZE-específico.
- **Comparação:** mesmo conjunto de anos de avaliação do MVP1 (causal rolling-origin),
  WMAPE contra persistência/Ridge.
- **Gate antes de avançar para MVP3:** a feature relacional precisa superar o Ridge do
  MVP1 por uma margem definida a priori, e superar um controle de grafo permutado —
  exatamente o tipo de gate que faltou nas três tentativas fechadas antes de irem para
  modelo neural completo.

### MVP 3 — Grafo neural simples (requer nova DEC antes de começar)
- Nós: ZE2020 (ou ZE2020×setor, se a Categoria C avançar).
- Arestas: apenas as relações que passaram o gate do MVP2.
- Features: lags/growth causal-safe já existentes.
- Saída: previsão + pesos/atenção/sinais exploratórios, separados explicitamente.
- **Não autorizado nesta pass.** Histórico de 3 FAILs prévios (DEC-008/009, DEC-029,
  DEC-031) exige hipótese pré-registrada e gate explícito antes de qualquer HPC.

### MVP 4 — Saída exploratória para economista
- Previsto baseline vs. previsto com relação vs. relações que mais contribuíram vs.
  correlações aprendidas, com o mesmo padrão de caveat já usado no dashboard v0.5.1
  ("Couche relationnelle", bloco colapsável de detalhes metodológicos, frase única de
  proibição de causalidade).

---

## 6. Estrutura de arquivos futura proposta (não criada nesta pass, exceto documentação)

**Dados (propostos, não criados):**
```
data/processed/france_ze2020/fr_ze2020_sector_panel.csv
data/processed/france_ze2020/fr_ze2020_sector_model_ready_panel.csv
data/processed/france_ze2020/fr_ze2020_territorial_similarity_v1.csv
data/processed/france_ze2020/fr_ze2020_relation_candidates.csv
```

**Scripts (propostos, não criados):**
```
src/data/france_ze2020/build_fr_ze2020_sector_panel.py
src/data/france_ze2020/build_fr_ze2020_territorial_similarity.py
src/modeles/france_ze2020/train_fr_ze2020_relational_baselines.py   # MVP2
src/modeles/france_ze2020/train_fr_ze2020_graph_model.py            # MVP3, NÃO autorizado
```

**Docs:**
```
reports/canonical/HERALD_17_FR_ZE2020_RELATIONAL_LAYER_PLAN.md   # este documento
reports/canonical/HERALD_18_FR_ZE2020_GRAPH_MODEL_AUDIT.md       # futuro, só após MVP3 ser autorizado
```

Nomenclatura ajustada em um ponto frente à sugestão original da tarefa: os nomes de
arquivo de dados/setor evitam reusar diretamente `fr_ze2020_territorial_edges.csv`/
`fr_ze2020_sector_edges.csv` como nomes de **insumo de modelo** antes que MVP2 mostre
sinal — `_similarity_`/`_candidates_` deixa explícito no nome que ainda é candidato, não
aresta validada, seguindo o mesmo padrão de nomenclatura honesta já usado em
`granular_relation_edges.csv` vs. `blocked_proxy_edges.csv`.

---

## 7. Checklist de decisão antes de construir qualquer peça acima

Para cada relação candidata, antes de transformá-la em código de produção:

- [ ] Existe dado reprodutível para a relação (builder na árvore, não apenas o CSV)?
- [ ] A granularidade bate com ZE2020 (não um esquema de ID diferente sem crosswalk)?
- [ ] O gerador está no repositório (não apenas o output)?
- [ ] Não há vazamento temporal (a relação usa só `t-1` e anterior)?
- [ ] A relação é interpretável economicamente por um não-especialista em ML?
- [ ] Existe baseline sem a relação para comparação (MVP1, já existe)?
- [ ] Existe teste para o builder?
- [ ] Existe caveat explícito contra causalidade no output?
- [ ] O output pode ser explicado a um economista sem jargão de ML?
- [ ] **(específico deste plano)** Se a relação envolve grafo de vizinhança/mobilidade
  geográfica, existe uma hipótese explicitamente diferente das três tentativas já
  fechadas (DEC-008/009, DEC-029, DEC-031), e não apenas uma repetição com outro nome?

---

## 8. Testes executados

```
$ rtk python3 -m pytest tests/test_herald_artifact_registry.py tests/test_herald_france_lineage_consistency.py -q
```
Resultado: ver §9 (saída real abaixo).

```
$ rtk git status --short
$ rtk git diff --name-only
$ rtk git diff --stat
```
Resultado: nenhuma alteração fora deste documento + (se aplicável) os dois pequenos
pointers de índice em `README.md`/`reports/README.md` (§9). Nenhum arquivo de dados,
dashboard, `hpc_results/`, Itália/Áustria, ou a cadeia limpa França/ZE2020 foi tocado.

---

## 9. Decisão pendente para aprovação humana antes de qualquer construção

Este plano não autoriza nenhuma das seguintes ações — todas aguardam decisão humana:

1. **Construir o painel setorial ZE2020 (Categoria C, MVP2 item 1)** — risco baixo
   (dados já reconciliados), mas ainda é trabalho novo de código+teste.
2. **Construir a similaridade de trajetória entre ZEs (Categoria A, MVP2 item 2)** —
   risco baixo, não depende de proveniência desconhecida.
3. **Reativar `graph_adjacency_core_v0.csv`/`mobility_v0.csv` para qualquer uso além de
   matéria-prima histórica** — não recomendado sem reconstrução documentada, dado o
   histórico de 3 FAILs em tentativas de grafo geográfico/correlacional como insumo
   preditivo neste mesmo projeto.
4. **Qualquer MVP3 (grafo neural)** — explicitamente bloqueado até MVP2 mostrar sinal
   medido contra um gate pré-registrado, e até uma nova DEC ser aberta.

Status em 2026-06-24: item 2 foi implementado nesta pass (ver §10 abaixo). Item 1
permanece bloqueado (sem proveniência suficiente). Itens 3 e 4 permanecem como estavam.

---

## 10. MVP2 implementation — relational simple features (2026-06-24)

**Status: smoke/exploratório. Nenhuma rede neural/grafo foi criada ou treinada. Nenhum
claim final de performance é feito.**

### O que foi implementado

**Categoria A apenas — similaridade de trajetória entre ZEs**, motivada pela técnica
"spatial-lag-like feature engineering" e pela prática de k-NN/graph-feature-engineering
antes de GNN (§0b).

- **Script:** `src/data/france_ze2020/build_fr_ze2020_relational_model_ready_panel.py`.
- **Entrada (única, somente leitura):** `data/processed/france_ze2020/fr_ze2020_model_ready_panel.csv`.
- **Saída:** `data/processed/france_ze2020/fr_ze2020_relational_model_ready_panel.csv`
  (3.920 linhas, 280 zonas × 14 anos, todas as 15 colunas do painel model-ready
  preservadas inalteradas + 5 colunas novas).
- **Método:** para cada ano de avaliação `t`, calcula uma matriz de correlação de
  Pearson ZE↔ZE sobre o histórico de `growth_1y_safe` restrito a anos estritamente
  `< t` (janela expansiva). Para cada zona, seleciona as até 5 zonas com correlação
  positiva mais alta (excluindo ela mesma). As features lêem apenas os valores
  `lag_1`/`growth_1y_safe` dessas vizinhas na própria linha do ano `t` — que já são,
  por construção do painel model-ready, valores defasados a `t-1` — nunca o
  `observed_value` de nenhuma zona no ano `t`.
- **Colunas novas:** `similar_ze_lag_1_mean`, `similar_ze_lag_1_weighted_mean`,
  `similar_ze_growth_1y_safe_mean`, `similar_ze_count`, `relational_feature_available`.
- **Disponibilidade verificada:** `relational_feature_available=0` para 2012-2016 (sem
  histórico suficiente — `growth_1y_safe` só existe a partir de 2014, e exigimos 3 anos
  de sobreposição mínima); `=1` para 2017-2025, com exatamente 5 vizinhos válidos para
  as 280×8=2.520 linhas elegíveis.

### O que foi recusado e por quê

| Categoria | Recusado? | Motivo |
|---|---|---|
| B — sinal setorial agregado nacional | Recusado nesta pass | Não há, no painel canônico atual, nenhum sinal setorial nacional já validado *na granularidade de ano* que pudesse ser simplesmente "broadcast" sem reconstruir o pipeline de `granular_relation_edges.csv` por ano-base — escopo maior do que um MVP2 mínimo; fica para uma iteração futura do MVP2, não para esta pass |
| C — composição/exposição setorial por ZE | **`BLOQUEADO/PENDING_PROVENANCE`** | `side_creations_a10_ze2020_through_2025_v1.csv` (HERALD_17 §1, item 6) não tem builder na árvore atual, apesar de seus valores reconciliarem exatamente com o painel canônico. Construir um painel setorial com o mesmo rigor de máscaras/causal-safety de HERALD_15 é trabalho novo de dados, não uma feature de modelo — fica para uma pass futura dedicada (ver `fr_ze2020_sector_panel.csv` em HERALD_17 §6) |
| A (alternativa) — contiguidade geográfica via `ze2020_geometry.geojson` | Recusado nesta pass | Construiria um SEGUNDO tipo de relação ZE→ZE (contiguidade espacial) além da similaridade de trajetória já implementada; nenhum builder existe ainda, e contiguidade geográfica já falhou 2 vezes neste projeto como insumo preditivo (DEC-008/009, DEC-031) — adicionar mais uma sem necessidade não está nas features "mínimas" pedidas |
| `graph_adjacency_core_v0.csv` / `graph_adjacency_mobility_v0.csv` | **Recusado, por regra explícita desta etapa** | Gerador ausente da árvore atual (HERALD_16 §4.1); nunca usados como fonte confiável nesta pass, nem direta nem indiretamente — confirmado por teste (`test_builder_reads_only_model_ready_panel_as_base`) |

### Como evitamos vazamento temporal

Três camadas de proteção, todas testadas:

1. A matriz de similaridade em si só usa `panel[panel["year"] < eval_year]` — nunca o
   ano avaliado (`tests/test_fr_ze2020_relational_model_ready_panel.py::test_similarity_uses_strictly_prior_years_only`).
2. As features das vizinhas usam `lag_1`/`growth_1y_safe`, que já são, pela construção
   do painel model-ready (HERALD_15 §10), estritamente `t-1`/anteriores — nunca o
   `observed_value` do ano `t` de nenhuma zona, alvo ou vizinha.
3. **Teste de invariância a truncamento de futuro:** construir o painel relacional a
   partir do painel completo e a partir de um painel truncado em `year <= eval_year`
   produz exatamente os mesmos valores relacionais em `eval_year` (diferença máxima
   absoluta = 0.0, verificado para `eval_year=2020` antes de escrever o teste e
   confirmado por `test_no_relational_feature_uses_the_target_years_own_observed_value`)
   — prova direta de que linhas de anos futuros não têm efeito nenhum.

### Por que isso vem antes de qualquer GNN

Per Charter §8 e o histórico já registrado deste projeto (3 FAILs prévios em
tentativas de grafo preditivo: DEC-008/009 Itália, DEC-029 FR NUTS3 grafo duplo,
DEC-031 FR ZE2020 `graph_temporal`), nenhuma rede neural de grafo deve ser tentada
sem primeiro mostrar, com o método mais simples possível, que a relação proposta
carrega algum valor preditivo — exatamente a lição de Shchur et al. (2018) sobre
testar baselines simples antes de arquiteturas sofisticadas (§0b). O MVP2 é esse
teste mínimo.

### Baseline relacional leve — resultado smoke

- **Script:** `src/modeles/france_ze2020/train_fr_ze2020_relational_baselines.py`
  (script novo; **não modifica** `train_fr_ze2020_baselines.py` — importa e reutiliza
  `predict_persistence`/`compute_wmape`/as constantes de janela de avaliação de lá,
  e define seu próprio `fit_predict_ridge` parametrizado por lista de features, para
  rodar Ridge tanto sobre as features temporais quanto sobre temporais+relacionais).
- **3 modelos, mesmo conjunto de teste por ano** (persistence, `ridge_temporal` —
  idêntico ao baseline original — e `ridge_relational` — mesmas features +
  `similar_ze_lag_1_mean`/`similar_ze_lag_1_weighted_mean`/`similar_ze_growth_1y_safe_mean`).
- **Janela comparável (2021-2025 — os únicos anos em que `ridge_relational` tem
  histórico suficiente, `RIDGE_MIN_TRAIN_YEARS=4` aplicado à disponibilidade
  relacional, que só começa em 2017):**

  | Modelo | WMAPE médio (2021-2025) |
  |---|---|
  | persistence | ≈0,070 |
  | ridge_temporal | ≈0,073 |
  | ridge_relational | ≈0,080 |

  **Leitura honesta:** nesta execução smoke, as features relacionais de similaridade
  de trajetória **não superaram** nem a persistência nem o Ridge temporal puro — pelo
  contrário, o WMAPE médio piorou. Isso não encerra a hipótese (é uma única
  execução, uma única definição de similaridade, um único alpha, 5 anos de
  avaliação), mas também não a sustenta. **Não constitui evidência a favor nem
  contra a camada relacional como um todo** — apenas contra esta primeira
  especificação simples de Categoria A.
- **2019-2020:** `ridge_relational` não roda (histórico relacional insuficiente,
  comportamento esperado e testado, não um bug) — `persistence`/`ridge_temporal`
  seguem rodando normalmente para esses anos, como no baseline original.
- Outputs: `data/processed/france_ze2020/fr_ze2020_relational_baseline_predictions_v1.csv`,
  `fr_ze2020_relational_baseline_metrics_v1.csv` — ambos com `claim_status=relational_smoke_result`
  em toda linha, intencionalmente não versionados (regeneráveis), mesmo padrão de
  `FR_ZE2020_BASELINE_PREDICTIONS_V1`.

### Claims autorizados e proibidos para este passo

- **Autorizado:** smoke/exploratório; comparação interna entre os 3 modelos sob o
  mesmo conjunto de teste; relato honesto de que a especificação testada não
  superou os baselines existentes.
- **Proibido:** claim final de performance; causalidade; recomendação automática;
  prova de influência econômica entre ZEs; tratar este resultado negativo como
  encerramento da hipótese da camada relacional (era uma especificação entre várias
  possíveis — ver MVP2 itens ainda não testados em §5); autorização implícita para
  MVP3.

### Status fechado do MVP2 Categoria A

**Fechado tecnicamente em 2026-06-24:** o painel relacional Categoria A foi
regenerado após corrigir o alinhamento entre pesos de similaridade e códigos ZE
em `similar_ze_lag_1_weighted_mean` (`44ef924`). A correção não muda a leitura
metodológica: o MVP2 é causal, reprodutível e útil como etapa de avaliação, mas
esta especificação de similaridade de trajetória não trouxe ganho preditivo sobre
os baselines simples na janela comparável.

### Testes

15/15 (`tests/test_fr_ze2020_relational_model_ready_panel.py`) + 11/11
(`tests/test_fr_ze2020_relational_baselines.py`), mais a bateria completa de
regressão (84/84, ver commits `6d07106`, `6a5ecb5`, `44ef924`).

### Decisão pendente atualizada

MVP3 (grafo neural) continua **não autorizado**. O resultado smoke desta pass não
move a agulha nessa decisão em nenhuma direção — nem a acelera (o resultado foi
neutro/levemente negativo) nem a encerra (faltam testar Categoria B/C e variações
de definição de similaridade antes de considerar a hipótese da camada relacional
esgotada).

---

## 11. MVP2 Categoria C — ZE×setor prototype (2026-06-24)

**Status: protótipo/smoke. Nenhuma rede neural/grafo final foi criada. Nenhuma
recomendação automática foi gerada. Nenhum claim causal ou de performance final é
feito.**

### Por que ZE×setor aproxima o futuro grafo econômico

A hipótese central deste plano (§4) é que a ZE2020 deve ser tratada como nó
econômico funcional, não como simples divisão geográfica — e que um grafo
econômico futuro precisa aprender representações territoriais **e setoriais**
antes da previsão. A Categoria A (§10) já deu à ZE uma vizinhança (ZE→ZE); a
Categoria C dá a cada ZE uma **composição interna** (que setores a compõem, em
que proporção, como essa composição evolui) — exatamente o segundo eixo que o
grafo bipartido território×setor da hipótese original (§4, "o modelo deve
aprender relações entre território e território; setor e setor; território e
setor") precisa para existir como dado tabular antes de qualquer arquitetura de
grafo. Sem essa camada, "ZE×setor" seria apenas uma frase no plano, não um dado.

### Auditoria do painel A10 (Parte 1)

`data/processed/side_creations_a10_ze2020_through_2025_v1.csv` — auditado nesta pass:

| Verificação | Resultado |
|---|---|
| Colunas | `target_year, ZE2020, BE, FZ, GI, JZ, KZ, LZ, MN, OQ, RU, total` |
| Anos | 2012-2025 (14 anos), sem buraco |
| Nº de ZE2020 | 280 (idêntico ao conjunto canônico) |
| Setores A10 | 9 (BE/FZ/GI/JZ/KZ/LZ/MN/OQ/RU — mesma nomenclatura já usada em `sector_panel_fr_nuts3.csv`/`sector_panel_fr_nl_pt.csv` e nos rótulos de `build_observatory_v05_narrative_exports.py`) |
| `ze2020` zero-padded 4 chars | Não no arquivo bruto (`int64`); corrigido no builder via `.str.zfill(4)` |
| `total` vs. `fr_ze2020_clean_panel.csv` | **Reconcilia exatamente — diff máx. absoluta = 0.0, 3.920/3.920 linhas** (re-verificado nesta pass, mesmo resultado do MVP2 Categoria A) |
| Valores negativos | Nenhum (`BE..RU`/`total` todos ≥ 0) |
| Cada ZE×ano tem os 9 setores | Sim — formato wide, 1 linha por ZE×ano, 9 colunas de setor sempre presentes |
| Missing | Zero valores nulos em qualquer coluna |
| `total == soma dos 9 setores` | Diff máx. absoluta = 0.0 (3.920/3.920 linhas) |
| Uso de valor futuro | N/A neste nível (painel bruto observado, sem features ainda — a auditoria de causalidade se aplica às etapas 2-3 abaixo) |

**Documentado e mantido:** o arquivo não tem builder próprio encontrado na árvore
atual (mesmo padrão de lacuna já documentado para `graph_adjacency_core_v0.csv`/
`mobility_v0.csv`, HERALD_16 §4.1) — é `CANDIDATE_NEEDS_PROVENANCE`. Usado nesta
pass apenas porque os checks acima passam, e **o builder novo
(`build_fr_ze2020_sector_panel.py`) re-verifica a reconciliação com o painel
canônico a cada execução e se recusa (`raise ValueError`) a escrever output se
ela algum dia parar de bater** — o caveat é reforçado em código, não só em
documentação. Não pode se tornar fonte definitiva sem auditoria de proveniência
adicional (localizar ou reconstruir o gerador original).

### O que foi construído (Partes 2-5)

| Etapa | Script | Output | Grão |
|---|---|---|---|
| 1. Painel setorial observado | `src/data/france_ze2020/build_fr_ze2020_sector_panel.py` | `data/processed/france_ze2020/fr_ze2020_sector_panel.csv` (35.280 linhas) | ZE×setor×ano |
| 2. Features setoriais causais | `src/data/france_ze2020/build_fr_ze2020_sector_relational_features.py` | `data/processed/france_ze2020/fr_ze2020_sector_relational_features.csv` (35.280 linhas) | ZE×setor×ano (com agregados ZE×ano e setor-nacional×ano embutidos) |
| 3. Integração com Categoria A | `src/data/france_ze2020/build_fr_ze2020_relational_sector_prototype_panel.py` | `data/processed/france_ze2020/fr_ze2020_relational_sector_prototype_panel.csv` (3.920 linhas) | ZE×ano (tempo + ZE→ZE + ZE×setor numa única linha) |
| 4. Saída exploratória | `src/modeles/france_ze2020/export_fr_ze2020_relational_prototype_examples.py` | `data/processed/france_ze2020/fr_ze2020_relational_prototype_examples.csv` (2.520 linhas — só onde Categoria A e Categoria C estão ambas disponíveis, 2017-2025) | ZE×ano, formato interpretável |

**Features setoriais implementadas** (todas `_lag_1`/`_lag_2`, nunca o ano-alvo):

- **ZE×setor (própria história):** `sector_share_lag_1`, `sector_growth_lag_1`
  (crescimento terminando em t-1, usa `lag_1`/`lag_2` da própria série),
  `sector_growth_lag_2` (crescimento terminando em t-2, um passo mais atrás, usa
  `lag_2`/`lag_3`) — mesma lógica causal de `growth_1y_safe`/`growth_2y_safe`,
  aplicada a duas observações de crescimento consecutivas em vez de duas janelas
  de referência diferentes.
- **ZE×ano (distribuição setorial da zona):** `dominant_sector_lag_1`,
  `dominant_sector_share_lag_1`, `sector_diversity_lag_1` (entropia de Shannon
  normalizada, 0-1), `sector_concentration_hhi_lag_1` (índice
  Herfindahl-Hirschman, 1/9-1), `commerce_share_lag_1` (setor GI — "Trade,
  transport and hospitality", o A10 mais próximo de comércio), `construction_share_lag_1`
  (setor FZ). Calculadas como estatística **contemporânea** da distribuição em
  t-1, depois deslocadas para a linha t — nunca a distribuição do próprio ano t.
- **Setor-nacional×ano:** `national_sector_share_lag_1`, `national_sector_growth_lag_1`
  (mesma soma sobre as 280 zonas, mesmo padrão calcular-depois-deslocar).
- **Integração:** `top_sector_signal_lag_1` = o próprio `sector_growth_lag_1` do
  setor que é dominante na zona naquele ano — "como está indo o setor que hoje
  domina esta ZE", composto só de colunas já causais.

### Features recusadas (Parte 1/3)

| Feature pedida | Decisão | Motivo |
|---|---|---|
| `services_share_lag_1` | **Não implementada** | A10 não tem um único código "serviços" — `JZ`/`MN`/`OQ`/`RU` são todos "services-like" mas economicamente heterogêneos (informação/comunicação, profissional/administrativo, administração pública/educação/saúde, artes/outros). Escolher um subconjunto arbitrário seria uma decisão de modelagem disfarçada de dado. A própria tarefa qualificou esta feature com "se possível" — exercido aqui o "não". |
| Painel A10 como fonte definitiva | **Não promovido** | Permanece `CANDIDATE_NEEDS_PROVENANCE`; usado só como candidato derivado com caveat reforçado em código (ver auditoria acima) |

### Como evitamos vazamento temporal (camada setorial)

Mesmas três camadas de proteção da Categoria A, replicadas para a Categoria C e
testadas (`tests/test_fr_ze2020_sector_relational_features.py`,
`tests/test_fr_ze2020_relational_sector_prototype.py`):

1. Todo `_lag_1`/`_lag_2` é construído por **deslocamento (`shift`) dentro do
   grupo correto** (ZE×setor, ZE, ou setor-nacional) — nunca por um cálculo que
   olhe o ano-alvo.
2. Estatísticas agregadas (distribuição ZE×ano, totais nacionais) são calculadas
   **contemporaneamente primeiro, deslocadas depois** — a ordem de operações é
   verificada, não assumida.
3. **Dois testes de invariância, replicados em cada uma das 3 etapas:**
   truncar o input em `year <= eval_year` produz exatamente os mesmos valores
   em `eval_year` que o painel completo; e mutar os valores do próprio
   `eval_year` (`sector_establishment_creations`/`sector_share` para valores
   extremos) não altera nenhuma feature `_lag_*` daquele mesmo `eval_year`.

### O que isto NÃO é

- **Não é o grafo neural final** — não há nó, aresta aprendida, ou arquitetura
  de rede em lugar nenhum desta pass. MVP3 continua bloqueado (§9, §10).
- **Não é recomendação automática** — a saída exploratória (`exploratory_note`)
  é uma frase-modelo determinística construída de colunas já causais, nunca uma
  sugestão de ação, nunca um ranking, nunca um "deveria investir aqui".
- **Não é claim causal nem de performance** — nenhum WMAPE foi recalculado nesta
  pass; nenhuma reconciliação ou disponibilidade de feature é apresentada como
  evidência de valor preditivo (isso é exatamente o que um futuro MVP2-C
  comparativo, análogo ao da Categoria A em §10, teria que testar antes de
  qualquer claim).
- **É, sim,** a base relacional econômica — tempo + ZE→ZE + ZE×setor numa
  única linha por zona-ano (`fr_ze2020_relational_sector_prototype_panel.csv`),
  exatamente o "não é GNN ainda, mas é a base para o futuro grafo" pedido.

### Exemplo de saída exploratória

```
ze2020=0051 (Alençon), 2017: ZE com trade, transport and hospitality como
setor dominante (share=31%); trajetória similar a 5 outras ZEs com sinal
recente de crescimento. Relação exploratória, sem claim causal.
```

### Testes

16/16 (`tests/test_fr_ze2020_sector_panel.py`) + 15/15
(`tests/test_fr_ze2020_sector_relational_features.py`) + 9/9
(`tests/test_fr_ze2020_relational_sector_prototype.py`) — 40 testes novos. Bateria
completa do trilho FR ZE2020 (incl. Categoria A e baselines): 124/124.

### Decisão pendente atualizada (2026-06-24)

MVP3 (grafo neural) continua **não autorizado**. A Categoria C amplia a base de
dados relacional (tempo + ZE→ZE + ZE×setor), mas não testa ainda se a composição
setorial tem valor preditivo — isso exigiria um MVP2-C comparativo análogo ao da
Categoria A (§10), que não foi pedido nesta pass e não foi executado. Próximo
passo sugerido para a apresentação de amanhã: apresentar o protótipo como
"previsão temporal + relações exploratórias (território e setor)", sem
recomendação automática final — exatamente como entregue aqui.

---

## 12. MVP3 neural prototypes — smoke only (2026-06-24)

**Status: protótipo/smoke. Nenhum claim de performance final. Nenhuma
causalidade. Nenhuma recomendação automática em lugar nenhum.**

Dois protótipos neurais leves, construídos em sequência (não em paralelo).
Nenhum dos dois substitui ou modifica os baselines/painéis já existentes —
ambos leem os painéis já causais como entrada read-only.

**Nota de implementação (PyTorch):** `import torch` falha neste ambiente
(`ModuleNotFoundError`) e a tarefa proíbe adicionar dependência pesada nova —
então os dois protótipos usam `sklearn.neural_network.MLPRegressor` (já
dependência existente do projeto) em vez de PyTorch puro. Para o MVP3-B, "message
passing" é manual (agregação numpy/pandas dos vizinhos), exatamente o fallback
"GraphSAGE simplificado manual" já autorizado pela tarefa quando PyG não está
disponível.

### MVP3-A — Neural relacional leve (ZE-level)

- **Script:** `src/modeles/france_ze2020/train_fr_ze2020_neural_relational_mlp.py`.
- **Entrada:** `fr_ze2020_relational_sector_prototype_panel.csv` (read-only) +
  um self-join read-only contra `fr_ze2020_sector_relational_features.csv`
  para resolver `national_sector_share_lag_1`/`national_sector_growth_lag_1`
  do setor dominante de cada ZE (essas duas colunas só existem no grão
  setor×ano, não no grão ZE×ano do painel prototype).
- **17 features:** temporais (5) + ZE→ZE (4) + setoriais (8), todas `_lag_1`/
  `_lag_2`/`growth_*_safe`, nunca o ano-alvo. Target: `observed_value`.
- **Achado metodológico não-trivial desta pass:** treinar o MLP direto sobre
  `observed_value` (escala 230-182.052, std≈10.500) colapsa para prever
  próximo de zero — WMAPE≈0,999, sintoma clássico de rede neural sobre target
  de escala muito heterogênea sem normalização do target. Corrigido
  reformulando o target como razão `observed_value/lag_1` (centrada em ~1,0,
  desvio ~0,08), prevendo a razão, depois reconstruindo
  `y_hat = razão_prevista × lag_1` (classe `RatioToLevelMLP`). WMAPE cai de
  0,999 para ~0,24 — ainda pior que os baselines, mas um resultado smoke
  honesto, não um pipeline quebrado.
- **4 modelos, mesmo conjunto de teste por ano** (persistence, ridge_temporal,
  ridge_relational, mlp_relational) — janela comparável 2021-2025 (mesma
  exigida pelos outros 3 modelos via `RIDGE_MIN_TRAIN_YEARS=4` sobre o
  histórico relacional, que só começa em 2017):

  | Modelo | WMAPE médio (2021-2025) |
  |---|---|
  | persistence | ≈0,070 |
  | ridge_temporal | ≈0,076 |
  | ridge_relational | ≈0,080 |
  | mlp_relational | ≈0,203 |

  **Leitura honesta:** o MLP relacional não superou nenhum baseline nesta
  especificação smoke — nem mesmo a persistência simples. Consistente com o
  padrão já observado em todo o MVP2: nenhuma das tentativas relacionais até
  aqui bateu o baseline temporal puro. Isso demonstra exatamente o ponto
  metodológico de Shchur et al. (§0b): testar o simples antes do sofisticado
  evita conclusões infladas sobre arquiteturas mais complexas.
- **Sinais exploratórios:** permutation importance (10 repetições, seed fixa)
  por feature por ano de avaliação, em `fr_ze2020_neural_relational_feature_signals_v1.csv`.
  `lag_1`/`lag_2`/`lag_3` dominam a importância (esperado, dado que `lag_1`
  também participa da reconstrução razão→nível) — **exploratório, não
  causalidade**.
- **Saídas:** `fr_ze2020_neural_relational_predictions_v1.csv`,
  `fr_ze2020_neural_relational_metrics_v1.csv`,
  `fr_ze2020_neural_relational_feature_signals_v1.csv` — toda linha
  `claim_status=neural_relational_smoke`.

### MVP3-B — Grafo experimental ZE2020×setor

- **Script:** `src/modeles/france_ze2020/train_fr_ze2020_sector_graph_prototype.py`.
- **Nós:** `ze2020_sector_code` (ex.: `0051_GI`), 2.520 nós únicos
  (280 ZE×9 setores), observados como 35.280 linhas nó-ano
  (280×9×14 anos). **Entrada:** `fr_ze2020_sector_panel.csv` +
  `fr_ze2020_sector_relational_features.csv` (read-only).
- **2 tipos de aresta implementados + 1 simplificação documentada:**
  1. **Intra-ZE (composição):** cada nó conectado aos 8 nós-setor irmãos da
     mesma ZE×ano. Mensagem = média dos `sector_share_lag_1`/
     `sector_growth_lag_1` próprios dos irmãos (já causais, nenhuma janela
     temporal nova necessária).
  2. **Cross-ZE, mesmo setor, trajetória similar:** para cada setor×ano,
     correlação de Pearson ZE↔ZE sobre o histórico de `sector_growth_lag_1`
     restrito a anos `< ano` (mesmo método expansivo da Categoria A, agora
     por setor). Top-5 vizinhas positivas; mensagem = média de
     `sector_share_lag_1`/`sector_growth_lag_1` das vizinhas.
  3. **"Mesmo setor nacional" — simplificação documentada:** em vez de um
     terceiro conjunto literal de arestas conectando todo nó ao mesmo
     `sector_code` nacionalmente (que duplicaria o mecanismo top-k do tipo 2
     a custo muito maior para um protótipo smoke), isso já está dobrado nas
     **features do próprio nó** (`national_sector_share_lag_1`/
     `national_sector_growth_lag_1` já vêm do painel setorial) — todo nó já
     "vê" o sinal nacional sem aresta separada.
- **Modelo:** `h_i = MLP([x_i, média_vizinhos_intra-ZE, média_vizinhos_cross-ZE])`
  — exatamente o "GraphSAGE simplificado manual" sugerido, via
  `sklearn.neural_network.MLPRegressor` sobre 16 features (11 próprias + 5 de
  mensagem).
- **Target:** `sector_share` (não `sector_establishment_creations`) — decisão
  proativa, não reativa: dado o achado do MVP3-A sobre instabilidade de target
  de escala heterogênea, foi escolhido direto o target já limitado a [0,1],
  evitando repetir o mesmo problema. Baseline: `y_hat = sector_share_lag_1`
  (persistência no próprio nó ZE×setor).
- **Achado de dados nesta pass:** exatamente 1 linha de
  `fr_ze2020_sector_relational_features.csv` tem `sector_establishment_creations=0`,
  causando `growth_lag_1`/`growth_lag_2` = `+inf` (divisão por zero) para a
  linha que a usa como `lag_2`/`lag_3`. Esse arquivo já está committed/testado
  (MVP2 Categoria C) e não foi alterado; o filtro de completude deste script
  novo foi reforçado para usar `np.isfinite` (não só `notna()`), excluindo o
  caso — documentado, não corrigido silenciosamente na fonte.
- **Resultado smoke (2021-2025, mesmo conjunto de teste):**

  | Modelo | WMAPE médio |
  |---|---|
  | persistence_sector | ≈0,109 |
  | graph_mlp | ≈0,121 |

  **Leitura honesta:** o grafo experimental tampouco superou a persistência
  simples nesta especificação — mas ficou na mesma ordem de grandeza (não
  degenerado), resultado smoke coerente com o padrão geral do projeto.
- **Sinais de relação exploratórios** (`fr_ze2020_sector_graph_relation_signals_v1.csv`,
  top-20 por ano por tipo): `intra_ze_composition` (correlação entre os 2
  setores de maior share da ZE, ex.: GI↔MN com correlação >0,98 em algumas
  ZEs) e `cross_ze_same_sector` (pares ZE-ZE mais correlacionados dentro do
  mesmo setor, ex.: `3206_KZ`↔`7618_KZ` com correlação ≈0,9998). **Exploratório,
  associação observada, não causalidade.**
- **Saídas:** `fr_ze2020_sector_graph_predictions_v1.csv`,
  `fr_ze2020_sector_graph_metrics_v1.csv`,
  `fr_ze2020_sector_graph_relation_signals_v1.csv` — toda linha
  `claim_status=sector_graph_smoke`.

### Por que isto demonstra o valor da IA, sem prometer mais do que entrega

Nenhum dos dois protótipos bateu os baselines simples nesta pass — e isso é
honestamente reportado, não escondido. O ponto destes protótipos não é "provar
que IA já ganha": é demonstrar a arquitetura (representação relacional +
setorial antes da previsão, mensagens de vizinhança manuais, sinais
exploratórios separados da previsão) que permitiria, com mais dados, mais
épocas, ou uma especificação de similaridade melhor, aprender combinações
não-lineares e relações latentes que uma regressão linear não consegue
representar por construção — exatamente a diferença entre "testar se vale a
pena" (o que MVP2/MVP3 fazem) e "assumir que vale a pena" (o que nenhuma DEC
deste projeto autoriza sem evidência).

### O que isto NÃO é

- **Não é claim de performance final** — os dois resultados smoke são
  negativos/neutros e reportados como tal.
- **Não é causalidade** — todo `signal_strength`/`importance_score` é
  associação observada (correlação ou permutation importance), nunca efeito
  causal.
- **Não é recomendação automática** — nenhuma coluna `recommendation`,
  nenhum ranking, nenhuma sugestão de política pública em nenhum dos 6 CSVs
  novos (verificado por teste).
- **Não é o grafo neural final do projeto** — MVP3-B é experimental e usa
  message passing manual com `MLPRegressor`, não uma arquitetura GNN treinada
  em escala; nenhuma DEC autoriza isso como arquitetura final.

### Testes

14/14 (`tests/test_fr_ze2020_neural_relational_mlp.py`) + 15/15
(`tests/test_fr_ze2020_sector_graph_prototype.py`) — 29 testes novos. Bateria
completa do trilho FR ZE2020 (Categoria A + Categoria C + MVP3): 130/130.

### Decisão pendente atualizada (2026-06-24)

Nenhum dos dois protótipos MVP3 produziu sinal forte o suficiente para
justificar escalar (mais épocas, arquitetura maior, HPC). Ambos permanecem
explicitamente smoke/experimentais. Próxima decisão pendente: se vale a pena
iterar a especificação (outra definição de similaridade, mais features, mais
épocas controladas) antes de considerar qualquer treino em escala — nenhuma
DEC nova foi aberta para autorizar isso nesta pass.
