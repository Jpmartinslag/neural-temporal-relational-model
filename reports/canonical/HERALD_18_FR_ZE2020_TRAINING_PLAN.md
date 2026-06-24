# HERALD 18 — France ZE2020 Training Block Plan

**Created:** 2026-06-24. **Status:** PLANNING_ONLY — organiza o bloco de treino local
já existente; não lança HPC, não treina pesado, não cria claim final de performance,
não gera recomendação automática. Nenhum modelo novo foi inventado nesta pass — o único
artefato de código novo é um orquestrador que chama os 4 scripts já existentes.

**Escopo:** apenas o bloco de treino FR/ZE2020 — não toca dashboard, `hpc_results/`,
Itália/Áustria, dados brutos, `train_herald_v6/v7/semi_v2/regime_experiment`, e não usa
`dynamic_stgnn_feature_panel*` em lugar nenhum.

**Lido antes desta pass:** `/home/jpdark/.codex/RTK.md`, `README.md`, `reports/README.md`,
`reports/HERALD_CURRENT_STATE.md`, `reports/HERALD_NAMING_CONVENTIONS.md`,
`reports/canonical/HERALD_15/16/17`, `reports/herald_artifact_registry.json`.

**Contexto herdado:** a cadeia limpa França/ZE2020 foi estendida até 2025 (commits
`c69a1aa`, `2203631`, fora desta pass) — 280 zonas × 14 anos (2012-2025). Todos os
números abaixo refletem esse estado atual, re-verificados nesta pass (`git status`/
`git log` checados antes de editar, conforme exigido).

---

## 1. Auditoria do estado atual do treino

| Script | Input | Target | Features | Modelo | Janela de avaliação | Saída | Status | Limitações |
|---|---|---|---|---|---|---|---|---|
| `train_fr_ze2020_baselines.py` | `fr_ze2020_model_ready_panel.csv` | `observed_value` | `lag_1/2/3`, `growth_1y/2y_safe` (5) | persistence (`y=lag_1`) + Ridge(α=1.0) | 2019-2025 (rolling-origin causal, `min_train_years=4`) | `fr_ze2020_baseline_predictions/metrics_v1.csv` (untracked) | `CURRENT_BASELINE_CONTROL` | Só nível ZE, sem relação, sem setor. persistence≈0,075, ridge≈0,076 — ridge não bate persistência de forma confiável |
| `train_fr_ze2020_relational_baselines.py` | `fr_ze2020_relational_model_ready_panel.csv` (reusa funções de `train_fr_ze2020_baselines.py`, não as duplica) | `observed_value` | as 5 temporais + `similar_ze_lag_1_mean`/`_weighted_mean`/`growth_1y_safe_mean` (3) | persistence + ridge_temporal + ridge_relational | 2021-2025 comparável (`min_train_years=4` sobre histórico relacional, que só começa em 2017) | `fr_ze2020_relational_baseline_predictions/metrics_v1.csv` (untracked) | `CURRENT_RELATIONAL_BASELINE` | ridge_relational (≈0,080) pior que ridge_temporal (≈0,073) e persistence (≈0,070) nesta especificação; só Categoria A (ZE→ZE), não usa setor ainda |
| `train_fr_ze2020_neural_relational_mlp.py` | `fr_ze2020_relational_sector_prototype_panel.csv` + self-join read-only em `fr_ze2020_sector_relational_features.csv` | `observed_value` (via razão `obs/lag_1`, reconstruída — ver achado em HERALD_17 §10) | 17 (temporais+ZE→ZE+setoriais) | `sklearn.neural_network.MLPRegressor` (16,8) envolto em `RatioToLevelMLP` | 2021-2025 (mesma janela comparável) | `fr_ze2020_neural_relational_predictions/metrics/feature_signals_v1.csv` (untracked) | `MVP3_SMOKE_NEURAL` | Pior que todos os baselines (≈0,203); poucas amostras de treino por ano; PyTorch não instalado neste ambiente (ver nota abaixo) |
| `train_fr_ze2020_sector_graph_prototype.py` | `fr_ze2020_sector_panel.csv` + `fr_ze2020_sector_relational_features.csv` | `sector_share` | 11 próprias + 5 de mensagem (agregação de vizinhos) = 16 | message passing manual (numpy/pandas) + `MLPRegressor` (16,8) | 2021-2025 | `fr_ze2020_sector_graph_predictions/metrics/relation_signals_v1.csv` (untracked) | `MVP3_SMOKE_GRAPH` | Pior que `persistence_sector` (0,121 vs 0,109), mas mesma ordem de grandeza; grafo manual simplificado (3º tipo de aresta dobrado em feature de nó); build completo ≈1 min local |

**Nota transversal:** todos os 4 scripts acima também carregam `NOT_FINAL_TRAINING` como
qualificador implícito — nenhum tem claim de performance final, nenhum está pronto para
HPC ainda (ver §5 para os critérios que faltam). Nenhum usa `dynamic_stgnn_feature_panel*`
nem `graph_adjacency_core_v0.csv`/`mobility_v0.csv` (verificado por teste em cada um).
Nenhum requer PyTorch/PyG instalados — ambos ausentes deste ambiente
(`ModuleNotFoundError: No module named 'torch'`), e a tarefa MVP3 proibiu adicionar
dependência pesada nova, então `sklearn.neural_network.MLPRegressor` substitui PyTorch
em ambos os protótipos neurais.

---

## 2. Arquitetura de treino local oficial — as 10 perguntas

1. **O que o modelo usa como entrada?** Para previsão ZE-level (Tarefa A): o painel
   integrado `fr_ze2020_relational_sector_prototype_panel.csv` (tempo + ZE→ZE + ZE×setor
   já numa única linha por zona-ano). Para o grafo setorial (Tarefa B):
   `fr_ze2020_sector_panel.csv` + `fr_ze2020_sector_relational_features.csv` (grão
   ZE×setor×ano).
2. **Quais são os nós?** Tarefa A: ZE2020 (280 zonas). Tarefa B: ZE2020×setor
   (`node_id=ze2020_sector_code`, 2.520 nós únicos, observados como 35.280 linhas
   nó-ano ao longo de 14 anos).
3. **Quais são as arestas?** Tarefa A: nenhuma aresta formal ainda — as features
   `similar_ze_*` são agregações de vizinhança pré-computadas, não uma estrutura de
   grafo que o modelo atravesse. Tarefa B: 2 tipos explícitos de aresta (intra-ZE
   composição setorial; cross-ZE mesmo setor por trajetória similar, top-5) + 1 tipo
   dobrado em feature de nó (sinal setorial nacional, ver HERALD_17 §12).
4. **Quais features entram?** Ver tabela do §1, coluna "Features", por script.
5. **Qual target será previsto?** Tarefa A: `observed_value` (diretamente nos baselines;
   via razão `observed_value/lag_1` no MLP, por estabilidade numérica — achado
   documentado em HERALD_17 §12, não decisão arbitrária). Tarefa B: `sector_share`
   (escolhido proativamente, não reativamente, pela mesma razão de estabilidade).
6. **O que sai do modelo?** Três coisas sempre separadas: (a) previsão (`y_pred` por
   linha, comparável a um baseline simples no mesmo conjunto de teste); (b) sinais
   exploratórios (`feature_signals`/`relation_signals`, nunca misturados com a
   previsão); (c) métricas (WMAPE/MAE/RMSE) com `claim_status` explícito em toda
   linha.
7. **O que é previsão?** O valor `y_pred` produzido por rolling-origin causal — treino
   estritamente em anos `< eval_year`, nunca usando dado do próprio `eval_year` (testado
   por invariância a truncamento/mutação em todos os 4 scripts).
8. **O que é relação exploratória?** Qualquer `signal_strength`, `importance_score`,
   `learned_or_aggregated_weight`, ou coeficiente de correlação/agregação reportado
   junto da previsão — sempre rotulado como associação observada, nunca como efeito.
9. **O que NÃO pode ser tratado como causal?** Nada do que sai destes scripts:
   diferenças de WMAPE entre modelos, pesos de agregação de vizinhos, permutation
   importance, correlação setor-setor ou ZE-ZE. Nenhum desses é — nem se aproxima de
   ser — uma estimativa de efeito causal.
10. **O que será testado localmente antes de HPC?** As 4 hipóteses H1-H4 do §5, cada
    uma com um critério de gate explícito — nenhuma foi testada formalmente ainda
    nesta pass (os resultados smoke já obtidos são insumo, não o teste formal em si).

**Formulação metodológica (já estabelecida em HERALD_17 §4, reafirmada aqui):** o
modelo não deve usar grafo/neural apenas como correção final de erro sobre a previsão
temporal. Ele deve usar as relações ZE→ZE e ZE×setor como **camada de representação
econômica antes da previsão** — exatamente por isso a Tarefa A já injeta as features
relacionais e setoriais diretamente no vetor de entrada do MLP (não como um termo de
correção aditivo sobre uma previsão Ridge já feita), e por isso a Tarefa B constrói o
grafo ZE×setor como representação primária, não como pós-processamento.

---

## 3. Duas tarefas de treino

### Tarefa A — Forecast ZE-level

- **Unidade:** ZE×ano (3.920 linhas, 280×14).
- **Input oficial:** `fr_ze2020_relational_sector_prototype_panel.csv`.
- **Target:** `observed_value`.
- **Scripts oficiais atuais:** `train_fr_ze2020_baselines.py` (`CURRENT_BASELINE_CONTROL`),
  `train_fr_ze2020_relational_baselines.py` (`CURRENT_RELATIONAL_BASELINE`),
  `train_fr_ze2020_neural_relational_mlp.py` (`MVP3_SMOKE_NEURAL`).
- **Modelo futuro (não autorizado):** grafo/neural real sobre ZE→ZE, só após uma
  especificação de similaridade ou arquitetura mostrar sinal num gate pré-registrado
  (§5).

### Tarefa B — Graph sector-level

- **Unidade:** ZE×setor×ano (35.280 linhas nó-ano, 2.520 nós únicos).
- **Input oficial:** `fr_ze2020_sector_panel.csv` + `fr_ze2020_sector_relational_features.csv`.
- **Target inicial:** `sector_share`.
- **Nós:** `ze2020_sector_code`.
- **Arestas:** intra-ZE (composição), cross-ZE mesmo setor (trajetória similar),
  sinal nacional setorial (feature de nó, não aresta — simplificação documentada).
- **Script oficial atual:** `train_fr_ze2020_sector_graph_prototype.py`
  (`MVP3_SMOKE_GRAPH`).
- **Modelo futuro (não autorizado):** GNN real / GNN temporal / grafo com atenção —
  só depois que o protótipo manual mostrar valor preditivo ou interpretativo num gate
  pré-registrado, e só com nova DEC.

**Os dois grãos não são diretamente comparáveis** (ZE×ano vs. ZE×setor×ano, targets
diferentes — `observed_value` vs. `sector_share`) — o resumo do §4 reporta os dois lado
a lado para visibilidade, nunca como um único ranking.

---

## 4. Orquestrador do bloco de treino (sem novo modelo)

**Script novo:** `src/modeles/france_ze2020/run_fr_ze2020_training_block.py`.

Apenas orquestra — importa e chama `run_baselines`, `run_relational_baselines`,
`run_neural_relational_smoke`, `run_sector_graph_smoke` dos 4 scripts já existentes
(verificado por teste: nenhuma classe `MLPRegressor`/`Ridge` nem redefinição de
`def run_*` dentro do orquestrador). Constrói o grafo setorial uma vez (~1 min,
custo dominante) e consolida todas as métricas num resumo único.

**Output:** `data/processed/france_ze2020/fr_ze2020_training_block_summary_v1.csv`
— colunas `model_family, model_name, target, grain, eval_year_start, eval_year_end,
mean_wmape, claim_status, source_script`. Toda linha:
`claim_status=training_block_summary_smoke_local_only`.

**Resultado consolidado (2021-2025 onde aplicável, ver coluna `eval_year_start` por
linha — janelas diferem por script conforme §1):**

| model_family | model_name | grain | mean_wmape |
|---|---|---|---|
| baseline | persistence | ze_x_year | ≈0,070-0,075 |
| baseline | ridge_temporal | ze_x_year | ≈0,076 |
| relational_baseline | ridge_relational | ze_x_year | ≈0,080 |
| neural_smoke | mlp_relational | ze_x_year | ≈0,203 |
| baseline | persistence_sector | ze_x_sector_x_year | ≈0,109 |
| graph_smoke | graph_mlp | ze_x_sector_x_year | ≈0,121 |

**Leitura honesta, repetida de HERALD_17:** em nenhuma das duas tarefas o modelo mais
sofisticado bateu o baseline mais simples nesta especificação. Isso não é o resultado
final do projeto — é o estado do bloco de treino HOJE, com uma especificação de
similaridade, uma arquitetura, um conjunto de épocas. **Não constitui claim de
performance nem prova contra a hipótese relacional como um todo.**

---

## 5. Spec para a próxima etapa HPC — hipóteses, NÃO executadas

### H1 — Features relacionais melhoram representação, mesmo sem ganho imediato de WMAPE
Features ZE→ZE + setor podem carregar informação representacional útil (para análise
exploratória, para um futuro modelo maior) mesmo que não melhorem WMAPE no smoke local
atual — o smoke local testa uma especificação simples e poucos dados, não a hipótese
em geral.

### H2 — Grafo ZE×setor pode aprender relações exploratórias úteis
Mesmo sem ganho de WMAPE, o grafo manual ZE×setor pode revelar pares
território-território ou composição setorial que sejam úteis para um economista
revisar — isso já está parcialmente demonstrado pelos `relation_signals` exportados
(HERALD_17 §12), mas não foi formalmente avaliado quanto a estabilidade/qualidade.

### H3 — Avaliação de modelos neurais não pode ser só WMAPE
A qualidade e estabilidade dos `relation_signals`/`feature_signals` exploratórios
importa tanto quanto o WMAPE — um modelo pode perder em WMAPE e ainda produzir sinais
exploratórios estáveis e interpretáveis (ou o contrário). Nenhuma métrica de
estabilidade de sinal foi definida ou testada ainda.

### H4 — A saída final deve sempre separar 3 coisas
Previsão | relação exploratória | caveat não-causal — nunca combinadas numa única
coluna ou frase que misture previsão com interpretação causal. Já é a convenção
seguida pelos 4 scripts atuais (verificado por teste); precisa continuar sendo a
convenção de qualquer trabalho futuro, incluindo HPC.

**Nenhuma das 4 hipóteses foi testada formalmente nesta pass** — os números do §1/§4
são o insumo (resultado smoke já obtido), não o teste do gate em si. Definir e rodar
esse teste formal localmente é o próximo passo antes de qualquer HPC.

### Checklist obrigatório para o próximo prompt HPC

Antes de qualquer submissão, o próximo prompt precisa responder explicitamente:

- [ ] Qual script será lançado (deve ser uma versão `READY_FOR_HPC_SPEC` de um dos 4
  atuais, ou um 5º script novo — nenhum dos 4 atuais tem esse status ainda, ver §1).
- [ ] Quais seeds (mínimo 3-5 seeds distintas, não 1 — todos os resultados smoke
  acima usam seed única, `SEED=42`).
- [ ] Quais anos de avaliação (manter a mesma janela comparável entre todos os
  modelos comparados, lição já aplicada em todo o MVP2/MVP3).
- [ ] Quais modelos entram na comparação (mínimo: o baseline correspondente +
  o candidato).
- [ ] Quais outputs são esperados (previsão, métricas, sinais exploratórios — os 3
  separados, nunca um só).
- [ ] Quais métricas (WMAPE no mínimo; MAE/RMSE se já usados; nenhuma métrica nova
  sem definição prévia).
- [ ] Qual limite de tempo/budget de cômputo (HPC não é "sem limite" — precisa de um
  teto explícito de horas/épocas).
- [ ] Qual critério de parada (early stopping já usado nos protótipos locais;
  definir o critério para a escala HPC).
- [ ] Qual comparação com baseline (gate pré-registrado: por quanto o candidato
  precisa superar o baseline para ser promovido — ver o padrão já usado em
  DEC-008/009/023/029/031 deste projeto, todos exigindo uma margem explícita, não
  "qualquer melhora").
- [ ] Como evitar claim indevido (toda saída mantém `claim_status` explícito; nenhuma
  conclusão causal; nenhuma recomendação automática até Bloco 3 do Charter estar
  autorizado, o que não é o caso).

**Nenhum destes itens foi decidido ou autorizado nesta pass — é a lista que o próximo
prompt HPC precisa preencher antes de lançar qualquer job.**

---

## 6. Testes

```
python3 -m pytest -q \
  tests/test_fr_ze2020_baselines.py \
  tests/test_fr_ze2020_relational_baselines.py \
  tests/test_fr_ze2020_neural_relational_mlp.py \
  tests/test_fr_ze2020_sector_graph_prototype.py \
  tests/test_fr_ze2020_training_block_runner.py \
  tests/test_herald_artifact_registry.py \
  tests/test_herald_france_lineage_consistency.py
```

Resultado: ver entrega final desta etapa.

---

## 7. Decisão pendente

1. **Nenhum dos 4 scripts atuais (nem o orquestrador) está `READY_FOR_HPC_SPEC`** —
   todos permanecem smoke/local. Promover qualquer um exigiria primeiro testar
   formalmente H1-H4 (§5) com múltiplas seeds e um gate pré-registrado.
2. **O orquestrador (`run_fr_ze2020_training_block.py`) é uma ferramenta de
   organização, não um modelo** — não deve ser confundido com um candidato a
   treino HPC.
3. **Próximo prompt HPC** precisa preencher o checklist do §5 antes de qualquer
   submissão — nenhum item foi decidido aqui.