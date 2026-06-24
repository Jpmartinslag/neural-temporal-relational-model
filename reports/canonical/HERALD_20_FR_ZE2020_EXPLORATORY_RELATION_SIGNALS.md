# HERALD 20 — France ZE2020 Exploratory Relation Signals

**Created:** 2026-06-24. **Status:** RELATION_LAYER_READY. Reorientação deliberada: esta
pass não otimiza previsão e não cria claim de performance. A previsão já está
controlada por baselines (HERALD_18); o foco agora é a estrutura relacional
território/setor que o bloco neural/grafo já calcula, organizada para leitura por um
especialista.

**Por que agora:** o job HPC `7498752` (5 seeds, HERALD_19) confirmou, de forma robusta
(não só num smoke de seed única), que nenhum dos 3 candidatos relacionais/neurais
(`ridge_relational`, `mlp_relational`, `graph_mlp`) bate seu baseline em WMAPE — 0 de 5
seeds em qualquer um dos três (gate G3 FAIL). **Isso não invalida a direção
relacional** — invalida apenas a hipótese de que ela melhora a previsão *nesta
especificação*. O mesmo job mostrou que os `relation_signals` são idênticos entre as 5
seeds (gate G4, overlap=1.0) — achado que esta pass esclarece com cuidado em §4.

---

## 1. Auditoria dos outputs existentes (Parte 1)

| Arquivo | Origem | Tipo de sinal | Granularidade | Ano/seeds | Pode ser usado pra interpretação? | Caveat |
|---|---|---|---|---|---|---|
| `data/processed/france_ze2020/fr_ze2020_neural_relational_feature_signals_v1.csv` | `train_fr_ze2020_neural_relational_mlp.py` | Permutation importance por feature | ZE×ano (agregado) | 2021-2025, seed única local (42) ou 5 seeds no HPC (`hpc_results/fr_ze2020_hpc_20260624_184345/seed_*/`) | Sim, mas como peso de contribuição ao MLP, não como relação entre entidades — `lag_1`/`lag_2`/`lag_3` dominam (esperado, fazem parte da reconstrução razão→nível, ver HERALD_17 §12) | `claim_status=neural_relational_smoke` |
| `data/processed/france_ze2020/fr_ze2020_sector_graph_relation_signals_v1.csv` | `train_fr_ze2020_sector_graph_prototype.py` | `intra_ze_composition` + `cross_ze_same_sector`, top-20/ano/tipo | ZE×setor×ano | 2019-2025, idêntico nas 5 seeds (determinístico, não depende do MLP) | **Sim — é a fonte primária desta pass para 2 das 4 famílias** | `claim_status=sector_graph_smoke` |
| `data/processed/france_ze2020/fr_ze2020_relational_model_ready_panel.csv` | `build_fr_ze2020_relational_model_ready_panel.py` | Agregados de vizinhança ZE→ZE (`similar_ze_*_mean`) | ZE×ano | 2017-2025 | Indiretamente — só tem o agregado, não a lista de arestas | Não tinha export explícito de arestas até esta pass (ver §2 item 1) |
| `data/processed/france_ze2020/fr_ze2020_sector_relational_features.csv` | `build_fr_ze2020_sector_relational_features.py` | `dominant_sector_lag_1`/`dominant_sector_share_lag_1` | ZE×setor×ano | 2013-2025 | Sim — fonte da Categoria `ze_sector_specialization` | Nenhum, já causal-safe |
| `hpc_results/fr_ze2020_hpc_20260624_184345/seed_*/fr_ze2020_*_signals_v1.csv` | Job HPC `7498752` | Mesmos 2 tipos acima, 5 cópias (uma por seed) | idem | 5 seeds | Sim, mas **idêntico** ao arquivo local (ver §4) — não soma evidência nova além de confirmar determinismo | Path gitignored (`hpc_results/`), não persistente em git |
| `reports/metrics/fr_ze2020_hpc_20260624_184345_gate_report.json` | `audit_fr_ze2020_hpc_results.py` | Gates G1-G5 (estatística agregada, não sinal individual) | Agregado | 5 seeds | Sim, como contexto de robustez, não como sinal em si | `claim_status=hpc_gate_audit_descriptive_only`, path gitignored |
| `data/processed/herald_observatory_v04_granular/granular_relation_edges.csv` (Phase 7, fora desta track) | `build_sector_precedence_graph.py` | Precedência setor→setor com lag-1 | **País-agregado**, não ZE | Multi-país, multi-janela | Sim, mas em grão diferente — **não misturado nesta pass** sem decisão de reconciliação de grão | FR tem só 1 `ROBUST_ORIGINAL` (e é COVID-sensível, DEC-060) |

**Termos de busca cobertos:** `relation_signals`, `feature importance`, `permutation
importance`, `graph edges`, `learned relations`, `sector graph`, `ZE similaridade`,
`sinais cross-ZE`, `sinais intra-ZE`, `sinais ZE×setor` — todos mapeados na tabela acima.

---

## 2. Artefato interpretável de relações (Parte 2)

**Script novo:** `src/data/france_ze2020/build_fr_ze2020_exploratory_relation_signals.py`.
**Output:** `data/processed/france_ze2020/fr_ze2020_exploratory_relation_signals.csv`
(6.215 linhas, schema de 20 colunas conforme especificado).

**4 famílias populadas, todas reaproveitando cálculo já existente — nenhum treino
novo:**

| `relation_family` | Linhas | Origem | O que é novo nesta pass |
|---|---|---|---|
| `ze_to_ze_similarity` | 5.769 | `similarity_matrix_for_year()` (já existe em `build_fr_ze2020_relational_model_ready_panel.py`, Categoria A) | **Reconstrução da lista explícita de arestas** — o builder original só exportava o agregado (`similar_ze_lag_1_mean`), nunca a lista de pares. Nenhum recálculo da similaridade em si. |
| `ze_to_ze_same_sector_signal` | 102 | `fr_ze2020_sector_graph_relation_signals_v1.csv`, linhas `cross_ze_same_sector` | Reaproveitado diretamente, só reorganizado/rotulado |
| `intra_ze_sector_interaction` | 64 | mesmo arquivo, linhas `intra_ze_composition` | Idem |
| `ze_sector_specialization` | 280 | `fr_ze2020_sector_relational_features.csv` (`dominant_sector_lag_1`/`_share_lag_1`) | Reduzido a 1 linha por ZE (setor dominante modal através do painel) |

**2 famílias do plano explicitamente NÃO populadas — lacuna documentada, não omissão
silenciosa:**

- `sector_to_sector_comovement` — a única evidência setor→setor já existente é a
  camada Phase 7 (país-agregado, fora desta track). Misturar esse grão com ZE2020 sem
  uma decisão de reconciliação de grão seria enganoso.
- `temporal_precedence_signal` — nenhum teste formal de precedência assinada (lag-1,
  bootstrap/permutação/FDR, o método já usado em Phase 7) foi rodado neste grão ZE2020.

**`stability_score` significa recorrência entre ANOS, não entre seeds.** As 4 famílias
populadas são determinísticas a partir dos dados de entrada (nenhum componente
aleatório/MLP) — isso explica, sem misticismo, por que o gate G4 do HPC encontrou
overlap=1.0 entre as 5 seeds: esses sinais específicos simplesmente não dependem da
seed do modelo neural, só dos painéis de entrada. Essa nuance é registrada aqui
explicitamente para que "estável entre seeds" não seja lido como um resultado mais
forte do que é.

**Achado ao construir:** para `ze_to_ze_similarity`, as correlações com `signal_strength`
mais alto tendem a ter `stability_score` mais baixo (picos de um único ano, não padrão
recorrente) — `rank_within_family` é só por `signal_strength`, então um leitor que olhe
só o rank 1 pode estar olhando um pico isolado. Por isso os exemplos (§3) priorizam
estabilidade, não força bruta do sinal.

---

## 3. Exemplos explicáveis (Parte 4)

**Script novo:** `src/data/france_ze2020/build_fr_ze2020_exploratory_relation_examples.py`.
**Output:** `data/processed/france_ze2020/fr_ze2020_exploratory_relation_examples.csv`
(20 linhas — 5 por família, selecionadas por estabilidade primeiro, força do sinal
depois).

Exemplo real gerado (`ze_to_ze_same_sector_signal`):

> No setor information and communication, ZE 2716 (Saint-Claude) e ZE 7606 (Béziers)
> mostram trajetórias parecidas. *(stability_score=0.57, presente em 4 de 7 anos)*

Exemplo real gerado (`ze_sector_specialization`):

> ZE 1112 (Roissy) é historicamente especializada no setor trade, transport and
> hospitality (setor dominante em 100% dos anos observados).

Exemplo real gerado (`intra_ze_sector_interaction`):

> Na ZE 7604 (Auch), os setores trade, transport and hospitality e professional and
> administrative services -- os dois com maior participação na zona -- têm trajetórias
> de crescimento associadas.

Todo `plain_language_interpretation` é copiado verbatim do `interpretation_label` da
tabela principal (§2) — nenhum texto é gerado de novo neste passo, evitando
divergência entre os dois arquivos.

---

## 4. Ranking de relações, não recomendação (Parte 5)

A própria coluna `rank_within_family` do arquivo principal (§2) já entrega o
ranking por família. Top-3 por família (`signal_strength` desc), para referência —
chamado aqui **relation ranking** / **exploratory signal ranking**, nunca
"recomendação":

**Top ZE↔ZE similarity (`ze_to_ze_similarity`)** — atenção: estes são os de maior
`signal_strength`, não necessariamente os mais estáveis (ver achado em §2):
ranks 1-3 são picos de ano único (`stability_score≈0.11`) — ilustram o sinal mais forte
já observado, não um padrão recorrente.

**Top ZE×setor specialization (`ze_sector_specialization`)**: zonas com
`signal_strength` (participação média do setor dominante) mais alta — tipicamente
zonas pequenas e fortemente concentradas num único setor.

**Top intra-ZE sector interaction (`intra_ze_sector_interaction`)** e **top cross-ZE
same-sector (`ze_to_ze_same_sector_signal`)**: ambos disponíveis via filtro do CSV
principal por `relation_family` + `rank_within_family`.

**Top temporal relation signals**: não existe ainda (ver §2, lacuna documentada).

---

## 5. As 10 perguntas

1. **O que são os nós?** ZE2020 (280 zonas) para `ze_to_ze_similarity` e
   `ze_sector_specialization`; ZE2020×setor (`node_id`, 2.520 combinações únicas) para
   `intra_ze_sector_interaction` e `ze_to_ze_same_sector_signal`. Setor isolado aparece
   só como atributo (`sector_code`/`sector_label`), não como nó próprio nesta pass.
   **Premissa herdada de HERALD_17 §4, reafirmada aqui:** a ZE2020 é tratada como nó
   econômico funcional — uma unidade que já aproxima um mercado de trabalho local
   (mobilidade, emprego, atividade concentrada) — não como uma divisão geográfica
   arbitrária. É essa premissa que justifica usar ZE2020 como nó de uma rede de
   relações em primeiro lugar.
2. **O que são as arestas?** Similaridade temporal entre ZEs (`ze_to_ze_similarity`,
   correlação de trajetória, top-5 por ano); mesma trajetória dentro do mesmo setor
   entre ZEs diferentes (`ze_to_ze_same_sector_signal`); composição dentro da própria ZE
   (`intra_ze_sector_interaction`, os 2 setores de maior peso movendo-se juntos);
   especialização setorial persistente (`ze_sector_specialization`, não é bem uma
   "aresta" entre dois nós do mesmo tipo, mas a relação ZE→setor dominante). Precedência
   temporal defasada (lag-1 assinado) **não está disponível ainda** neste grão (§2).
3. **O que a rede neural/grafo adiciona?** Nada de novo *nesta* extração específica —
   os 4 sinais aqui vêm de correlação/agregação direta, não de pesos aprendidos pelo
   MLP. O que a rede/grafo acrescentaria, em princípio, é a capacidade de combinar
   sinais temporais, territoriais e setoriais não-linearmente e destacar interações que
   não foram programadas como regra explícita — mas isso ainda não produziu um sinal
   relacional *adicional* validado além do que a correlação direta já mostra aqui. Essa
   é uma leitura honesta, não uma promessa.
4. **O que ela NÃO faz?** Não prova causalidade. Não gera recomendação automática. Não
   substitui um economista — toda interpretação aqui é rotulada como hipótese para
   especialista avaliar. **Não precisa bater o baseline preditivo para ser útil como
   ferramenta exploratória** — e de fato, nesta pass, não bateu (HERALD_19), e está
   sendo usada exploratoriamente mesmo assim, exatamente como pretendido.

---

## 6. Separação previsão ↔ relação (Parte 3, formalizada)

| | Previsão | Relação |
|---|---|---|
| Papel agora | **Controle** (já fechado, HERALD_18/19) | **Objeto principal desta análise** |
| Métrica | WMAPE/MAE/RMSE | `signal_strength` + `stability_score` (recorrência entre anos) |
| O que um resultado "negativo" significa | Modelo não bate baseline → não promover para HPC maior | **Não invalida o sinal relacional** — só significa que esta especificação não ajuda a prever |
| Objetivo | Já cumprido (controle estabelecido) | Explicar estrutura econômica territorial/setorial |
| Linguagem permitida | "não bateu baseline", "WMAPE pior" | associação, correlação, sinal relacional, interação econômica exploratória, hipótese para especialista |
| Linguagem proibida | "previsão superior" sem evidência | causalidade, influência causal, "o modelo descobriu", prova econômica, recomendação automática |

---

## 7. O que NÃO foi feito nesta pass

- Nenhum treino novo, nenhum ajuste de hiperparâmetro, nenhuma mudança de target pra
  ganhar WMAPE.
- Nenhuma submissão HPC nova.
- Nenhuma reconciliação de grão entre Phase 7 (país-agregado) e ZE2020 — `sector_to_sector_comovement`
  fica como lacuna documentada, não fabricada.
- Nenhum teste formal de precedência temporal assinada neste grão — `temporal_precedence_signal`
  idem.
- Nenhuma coluna `recommendation`/`recommended_action`/`policy_action` em nenhum dos 2
  CSVs novos (verificado por teste).

---

## Cross-reference

- Plano relacional: `reports/canonical/HERALD_17_FR_ZE2020_RELATIONAL_LAYER_PLAN.md`
- Plano de treino local: `reports/canonical/HERALD_18_FR_ZE2020_TRAINING_PLAN.md`
- Spec e resultado HPC: `reports/canonical/HERALD_19_FR_ZE2020_HPC_SPEC.md`
