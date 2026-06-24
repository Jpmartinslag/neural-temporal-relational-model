# HERALD 21 — France ZE2020 Relation Layer Audit

**Created:** 2026-06-24. **Status:** `RELATION_LAYER_AUDITED`. Auditoria da camada de
sinais relacionais exploratórios criada em HERALD_20 (commit `5086b1f`), antes de
aceitá-la como referência canônica. Nenhuma metodologia nova, nenhum treino, nenhuma
otimização de previsão, nenhuma recomendação criada nesta pass — só verificação e duas
correções pontuais.

---

## Arquivos auditados

- `data/processed/france_ze2020/fr_ze2020_exploratory_relation_signals.csv`
- `data/processed/france_ze2020/fr_ze2020_exploratory_relation_examples.csv`
- `src/data/france_ze2020/build_fr_ze2020_exploratory_relation_signals.py`
- `src/data/france_ze2020/build_fr_ze2020_exploratory_relation_examples.py`
- `reports/canonical/HERALD_20_FR_ZE2020_EXPLORATORY_RELATION_SIGNALS.md`
- `reports/herald_artifact_registry.json`
- `reports/canonical/HERALD_09_DATA_ASSET_MAP.md`
- `reports/canonical/HERALD_10_CODE_PATH_MAP.md`
- `reports/README.md`
- `tests/test_fr_ze2020_exploratory_relation_signals.py`
- `tests/test_fr_ze2020_exploratory_relation_examples.py`

---

## Tarefa 1 — Schema dos sinais (`fr_ze2020_exploratory_relation_signals.csv`)

| Check | Resultado |
|---|---|
| Existe | ✅ |
| 6.215 linhas | ✅ exato |
| `relation_id` único | ✅ |
| `claim_status` existe e nega causalidade | ✅ — sempre `exploratory_association_not_causal` |
| `caveat` não vazio | ✅ — menor caveat tem 178 caracteres, todos mencionam "causalidade" |
| Colunas proibidas (`recommendation`, `recommended_action`, `policy_action`, `causal_effect`, `causal_impact`) | ✅ nenhuma presente |
| IDs ZE2020 zero-padded 4 chars | ✅ — `source_id`/`target_id` quando `source_type`/`target_type=="ZE2020"` |
| Anos incluem 2025 | ✅ — `year_end` máximo é 2025, 1.720 linhas terminam em 2025 |
| `signal_strength` finito | ✅ |
| `stability_score` finito e em [0,1] | ✅ |
| `relation_family` só com famílias documentadas | ✅ — exatamente as 4: `ze_to_ze_similarity`, `ze_to_ze_same_sector_signal`, `intra_ze_sector_interaction`, `ze_sector_specialization`. `sector_to_sector_comovement`/`temporal_precedence_signal` **não aparecem** (lacuna documentada, não fabricada — confirmado) |

**Nenhum problema encontrado.**

---

## Tarefa 2 — Exemplos (`fr_ze2020_exploratory_relation_examples.csv`)

| Check | Resultado |
|---|---|
| Existe | ✅ |
| 20 linhas | ✅ exato |
| Exemplos vêm dos sinais reais | ✅ — verificado linha a linha: as 20 linhas reconciliam exatamente (mesmo `interpretation_label`/`plain_language_interpretation`) contra a linha correspondente em `fr_ze2020_exploratory_relation_signals.csv` |
| Nenhum texto sugere recomendação/causalidade | ✅ — varredura de `recomend`, `prescri`, `causal`, `prova `, `descobriu` em todos os 20 textos: zero ocorrências |
| Todo exemplo tem caveat | ✅ |
| Exemplos priorizam estabilidade | ✅ — `stability_score` médio por família: 0,94-1,00 (3 famílias) e 0,54 (`ze_to_ze_same_sector_signal`, ainda assim acima da mediana da família no arquivo-mãe) |
| Explicáveis para economista | ✅ (avaliação qualitativa) — frases em português, sem jargão de ML, sempre com a unidade territorial nomeada |

**Nenhum problema encontrado.**

---

## Tarefa 3 — Builders

| Check | `build_..._signals.py` | `build_..._examples.py` |
|---|---|---|
| Não lê `dynamic_stgnn_feature_panel*` | ✅ | ✅ |
| Não lê `graph_adjacency_core_v0`/`mobility_v0` | ✅ | ✅ |
| Não treina (`fit(`, `MLPRegressor`, `Ridge(`, `random_state`) | ✅ nenhum presente | ✅ nenhum presente |
| Determinístico | ✅ — testado por reconstrução em dobro, comparação exata |
| Outputs regeneráveis | ✅ — `status=REGENERABLE`, `tracked_in_git=false` no registry |
| Usa só inputs canônicos/já auditados | ✅ — `fr_ze2020_model_ready_panel.csv`, `fr_ze2020_sector_graph_relation_signals_v1.csv`, `fr_ze2020_sector_relational_features.csv` (todos já canônicos/testados em passes anteriores) | ✅ — só lê o output do builder anterior |
| Não mistura métrica preditiva com ranking relacional | ✅ — sem `wmape`/`mae`/`rmse`/`y_pred`/`y_true` em nenhum dos 2 schemas | ✅ |
| Não cria recomendação | ✅ | ✅ |

**Nenhum problema encontrado.**

---

## Tarefa 4 — Documentação (`HERALD_20`)

| Ideia exigida | Presente? |
|---|---|
| Previsão é controle, não objetivo principal | ✅ (§6, tabela explícita) |
| Relações econômicas são o objeto principal | ✅ (cabeçalho + §6) |
| ZE2020 é nó econômico funcional | ⚠️ **estava ausente** — corrigido nesta pass (§5, pergunta 1) |
| Rede/grafo revela associações e interações não-lineares | ✅ (§5, pergunta 3) — com a ressalva honesta de que isso ainda não produziu sinal adicional validado além da correlação direta |
| Sinais são exploratórios | ✅ (todo o documento) |
| Especialista humano interpreta | ✅ (§5, pergunta 4; §6) |
| Sem claim causal | ✅ |
| Sem recomendação automática | ✅ |
| Resultado HPC negativo não invalida a camada relacional | ✅ (cabeçalho + §7) |
| Limitações explícitas (sem setor→setor em grão ZE; sem precedência temporal formal) | ✅ (§2, §7) |

**1 lacuna real encontrada e corrigida:** a premissa de HERALD_17 §4 ("ZE2020 como nó
econômico funcional, não divisão geográfica arbitrária") nunca era reafirmada
explicitamente em HERALD_20 — só citada por referência cruzada. Adicionada
explicitamente na resposta à pergunta 1 (§5).

---

## Tarefa 5 — Registry e mapas

| Check | Resultado |
|---|---|
| `FR_ZE2020_EXPLORATORY_RELATION_SIGNALS_V1` registrado | ✅ |
| `status=REGENERABLE` | ✅ |
| `claim_authorized`/`claim_forbidden` negam causalidade e recomendação | ✅ |
| `generator_script` aponta pro caminho correto | ✅ — `src/data/france_ze2020/build_fr_ze2020_exploratory_relation_signals.py`, confirmado existente |
| Outputs classificados como camada exploratória, não treino preditivo | ✅ — `phase: "relational analysis reorientation"`, nunca `phase: "...smoke prototype"` como os scripts MVP3 |
| `HERALD_09`/`HERALD_10`/`reports/README.md` apontam pra `HERALD_20` | ✅ |

**Nenhum problema encontrado.**

---

## Tarefa 6 — Testes

```
python3 -m pytest -q tests/test_fr_ze2020_*.py tests/test_herald_artifact_registry.py tests/test_herald_france_lineage_consistency.py
```

**Resultado: 201/201 PASS** (2 rodadas, antes e depois da correção de teste abaixo).

**1 lacuna de teste real encontrada e corrigida:** `FORBIDDEN_COLUMN_NAMES` nos 2
arquivos de teste da camada relacional só verificava `recommendation`/
`recommended_action`/`policy_action` — não verificava `causal_effect`/`causal_impact`,
que esta própria auditoria (Tarefa 1) pede para checar. Adicionados aos dois conjuntos
de teste (`test_fr_ze2020_exploratory_relation_signals.py`,
`test_fr_ze2020_exploratory_relation_examples.py`). Re-rodado: 28/28 (só a camada
relacional) e 201/201 (bateria completa) continuam passando.

---

## Famílias relacionais — decisão

**Aceitas como referência canônica exploratória:**
- `ze_to_ze_similarity`
- `ze_to_ze_same_sector_signal`
- `intra_ze_sector_interaction`
- `ze_sector_specialization`

**Recusadas/não populadas nesta pass — permanecem lacuna documentada:**
- `sector_to_sector_comovement` (só existe em grão país-agregado, Phase 7; misturar
  grãos sem decisão de reconciliação seria enganoso)
- `temporal_precedence_signal` (nenhum teste formal de precedência assinada lag-1 foi
  rodado neste grão ZE2020 ainda)

---

## Limites metodológicos (repetidos deliberadamente)

- `stability_score` mede recorrência entre **anos**, não entre seeds — as 4 famílias
  são determinísticas a partir dos dados de entrada, sem componente de MLP/aleatório.
- O sinal de maior `signal_strength` em `ze_to_ze_similarity` tende a ter
  `stability_score` baixo (pico de um único ano) — `rank_within_family` é só por
  força do sinal, não por estabilidade; os exemplos (Parte 4) corrigem isso priorizando
  estabilidade na seleção.
- Nenhum sinal aqui prova causalidade, gera recomendação, ou substitui avaliação por
  especialista — toda interpretação é hipótese para revisão humana.

---

## Correções feitas nesta pass

1. `reports/canonical/HERALD_20_FR_ZE2020_EXPLORATORY_RELATION_SIGNALS.md` — adicionada
   a premissa "ZE2020 como nó econômico funcional" explicitamente na pergunta 1 (§5).
2. `tests/test_fr_ze2020_exploratory_relation_signals.py`,
   `tests/test_fr_ze2020_exploratory_relation_examples.py` — `FORBIDDEN_COLUMN_NAMES`
   ampliado para incluir `causal_effect`/`causal_impact`.

Nenhuma outra correção foi necessária — schema, builders, registry e mapas já estavam
corretos.

---

## Decisão final

**A camada relacional pode ser usada na explicação de amanhã.** Está limpa,
regenerável, determinística, documentada, sem vazamento conceitual (previsão↔relação
nunca misturadas), sem linguagem causal/de recomendação em nenhum dos 2 CSVs ou na
documentação, e as 2 lacunas reais encontradas nesta auditoria já foram corrigidas.

---

## Cross-reference

- Camada auditada: `reports/canonical/HERALD_20_FR_ZE2020_EXPLORATORY_RELATION_SIGNALS.md`
- Resultado HPC que motivou a reorientação: `reports/canonical/HERALD_19_FR_ZE2020_HPC_SPEC.md`
