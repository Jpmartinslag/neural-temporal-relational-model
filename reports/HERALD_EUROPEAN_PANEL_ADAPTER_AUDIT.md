# HERALD European Panel — Adapter Audit Report

**Data**: 2026-05-31  
**Status**: PASS com warnings documentados

> **Veredicto final**: Schema europeu pronto para Phase 4E-A (baseline padronizado).
> Ainda não pronto para claims de generalização completa.
> Phase 4E-B/C/D dependem de: (1) excluir `NON_PREDICTIVE_FIELDS` de todos os inputs,
> (2) consumir `mask_tensor`/`mask_employment` no trainer quando houver tensor ou loss parcial,
> (3) validar os sinais EU por ablação.

---

**Schema: 43 campos catalogados, 43 exportados actualmente**
- Máscaras exportadas: `mask_target`, `mask_sector_a10`, `mask_employment`,
  `mask_tensor`, `mask_eu_signals`
- `mask_eu_signals≈0.51–0.57` após overlay Eurostat/ESI lag-1
- `mask_tensor=1.0` nos 4 países após integração do tensor Eurostat de emprego em PT

---

## 1. Resumo executivo

| País | Status | Regiões | Anos | Linhas | Target obs% | Sector cov% | Emp. tensor |
|---|---|---|---|---|---|---|---|
| **FR** | ✓ PASS | 280 ZE2020 | 2012–2024 | 3 640 | 100% | 92.3% | URSSAF ✓ |
| **NL** | ✓ PASS | 40 COROP | 2015–2025 | 440 | 100% | 0% | CBS Q7 ✓ |
| **BE** | ✓ PASS | 42 arr. | 2007–2024 | 756 | 100% | 0% | StatBel ONSS ✓ |
| **PT** | ✓ PASS | 25 NUTS3 | 2008–2024 | 425 | 100% | 94.1% | Eurostat employment ✓ |
| **ALL** | ✓ PASS | 387 | — | 5 261 | 100% | 25.4% | — |

Nenhum país tem erros. Todos têm warnings esperados e documentados (ver §4).

---

## 2. Comparação painel antigo (Phase 4) vs painel canónico

### Metodologia
Merge exacto por `ZE2020/zone_idx × year`. Comparação sobre as colunas alinhadas.

### Resultados

| País | Rows match | Target max_diff | lag1 max_diff | growth_1y max_diff | Nota |
|---|---|---|---|---|---|
| **FR** | 3 640/3 640 ✓ | 0.000 | 0.000 | 0.000 | Perfeito |
| **NL** | 440/440 ✓ | 0.000 | 0.000 | 0.000 | Perfeito |
| **BE** | 756/756 ✓ | 0.000 | 0.000 | 0.000 | Perfeito; inclui extensão 2021–2024 |
| **PT** | 375/375 ✓ | 0.000 | 0.000 | 0.000 | Perfeito |

**Conclusão**: os adapters reproduzem os dados do Phase 4 sem divergência nos campos numéricos. Nenhum bug de cálculo introduzido.

### Diferenças de schema (esperadas, não são bugs)

| Campo Phase 4 (antigo) | Campo canónico | Diferença | Classificação |
|---|---|---|---|
| `ZE2020` (col. de ID) | `region_id` + `meta_region_system` | Sistema explicitado | Melhoria metodológica |
| `target_year` | `year` | Renomeado | Schema |
| `side_establishment_creations_official` | `target_births` | Renomeado | Schema |
| `side_lag_1/2/3` | `lag1/2/3_births` | Renomeados | Schema |
| `side_stock_total_t_minus_1` | `stock_lag1` | Renomeado | Schema |
| `feature_forecast_safe` | `flag_forecast_safe` | Renomeado + corrigido | Metodológica ↓ |
| `is_covid_year` | `flag_is_covid_year` | Renomeado | Schema |
| `is_post_covid_rebound` | `flag_is_rebound_year` | Renomeado | Schema |
| (ausente) | `country` | Adicionado | Melhoria |
| (ausente) | `region_name` | Adicionado | Melhoria |
| (ausente) | `mask_target` | Adicionado | Melhoria metodológica |
| (ausente) | `mask_sector_a10` | Adicionado | Melhoria metodológica |
| (ausente) | `flag_target_concept` | Adicionado | Melhoria crítica |
| (ausente) | `flag_has_eurostat_bd` | Adicionado | Rastreabilidade |
| (ausente) | `eu_*` (7 campos) | Adicionados (NaN) | Placeholder Phase 4E |

### Correção metodológica: `flag_forecast_safe`

O painel Phase 4 original marcava `feature_forecast_safe=1` em todos os anos, incluindo o primeiro
ano de cada região (onde `side_lag_1` é NaN). O adapter corrige isto:

```
out.loc[out["lag1_births"].isna(), "flag_forecast_safe"] = 0
```

Impacto: linhas "unsafe" correctas agora são exatamente 1 por região (o primeiro ano).

| País | Safe rows Phase 4 | Safe rows canónico | Diferença |
|---|---|---|---|
| FR | 3 640 (100%) | 3 360 (92.3%) | −280 (1 por zona) |
| NL | 440 (100%) | 400 (90.9%) | −40 (1 por zona) |
| BE | 756 (100%) | 714 (94.4%) | −42 (1 por zona) |
| PT | 375 (100%) | 350 (93.3%) | −25 (1 por zona) |

Este é um **fix metodológico correcto**, não uma perda de dados. O HERALD não deve usar
o primeiro ano como linha de previsão (lag1 ausente). Resultados históricos Phase 4A/4D
não são afectados (o modelo ignora estas linhas implicitamente nas folds de treino).

---

## 3. Cobertura por campo

### França (FR)

| Grupo | Campo | Cobertura | Fonte |
|---|---|---|---|
| Target | `target_births` | 100% | SIDE |
| Lags | `lag1_births` | 92.3% | SIDE (NaN = primeiro ano) |
| Sector | `sector_BE…RU` | 92.3% | SIDE A10 (NaN = primeiro ano) |
| Sector | `mask_sector_a10` | 100% (val. 0 ou 1) | derivado |
| Stock | `stock_lag1` | 76.9% | FLORES (NaN 3 primeiros anos) |
| EU signals | todos os `eu_*` | 0% | **não carregados** (Phase 4E) |
| Emp. tensor | `flag_has_national_employment` | 1 (todos) | URSSAF |

**Nota sobre sector A10 FR**: os `sector_*` são births por sector **lagged** (t-1).
O total sectorial = target_births do ano anterior (confirmado: max_diff = 0 internamente).
Para o primeiro ano (2012), sector_* é NaN e mask_sector_a10 = 0.

### Países Baixos (NL)

| Grupo | Campo | Cobertura | Fonte |
|---|---|---|---|
| Target | `target_births` | 100% | CBS 83631NED |
| Lags | `lag1_births` | 90.9% | CBS |
| Sector | `sector_*` | **0%** | **NÃO DISPONÍVEL** |
| Sector | `mask_sector_a10` | 0.0 (todos) | derivado |
| Stock | `stock_lag1` | 90.9% | CBS 81578NED |
| EU signals | todos os `eu_*` | 0% | não carregados |
| Emp. tensor | `flag_has_national_employment` | 1 (todos) | CBS 83582NED Q-tensor |

**Nota sector NL**: a CBS publica births por sector (`83631NED`) mas apenas para sectores
SBI a nível nacional (não COROP × sector). A10 disponível em `a10_ze2020.csv` é o
**Q-tensor de emprego** (jobs), não births por sector. `sector_*` permanece NaN.

**Nota 2025**: CBS Q-tensor disponível até 2024. Para previsão de 2025, `flag_forecast_safe=1`
mas sem emprego sectorial em t-1 (2024). O modelo pode prever 2025 com lag1/growth mas não
com Q-tensor sectorial.

### Bélgica (BE)

| Grupo | Campo | Cobertura | Fonte |
|---|---|---|---|
| Target | `target_births` | 100% | StatBel BCR |
| Lags | `lag1_births` | 92.9% | StatBel |
| Sector | `sector_*` | **0%** | **NÃO DISPONÍVEL** |
| Sector | `mask_sector_a10` | 0.0 (todos) | derivado |
| Stock | `stock_lag1` | 92.9% | StatBel |
| EU signals | todos os `eu_*` | 0% | não carregados |
| Emp. tensor | `flag_has_national_employment` | 1 (todos) | StatBel ONSS |
| `flag_has_eurostat_bd` | — | 0 (todos) | **BE ausente do Eurostat BD** |

**Nota sector BE**: StatBel BCR não publica births por arrondissement × sector na granularidade
necessária. O A10 disponível (`a10_ze2020.csv`) é emprego ONSS (jobs em milhares), não births.
Eurostat BD confirmado ausente para BE (verificado empiricamente no Phase 4D data audit).

**Nota anos**: pipeline canónico cobre 2007–2024 após integração do ficheiro StatBel
mensal 2021–2024. O tensor ONSS ainda cobre a janela antiga disponível no Phase 4.

### Portugal (PT)

| Grupo | Campo | Cobertura | Fonte |
|---|---|---|---|
| Target | `target_births` | 100% | INE 0009702/0014098 |
| Lags | `lag1_births` | 93.3% | INE |
| Sector | `sector_*` | 93.3% | INE 0009703/0014099 CAE → A10 (births by sector) ✓ |
| Sector | `mask_sector_a10` | 93.3% / 0% | 1 para anos com dados |
| Stock | `stock_lag1` | 93.3% | INE |
| EU signals | todos os `eu_*` | 0% | não carregados |
| Emp. tensor | `flag_has_national_employment` | **1 (todos)** | Eurostat `nama_10r_3empers`, EMP × NACE × NUTS3 |
| `flag_has_eurostat_bd` | — | 1 (todos) | Eurostat BD cobre PT |

**Nota tensor PT**: Phase 4D usou `portugal_qtensor_births_cae_nuts3.csv`, isto é,
births por CAE. Phase 4E agora tem `portugal_qtensor_employment_eurostat_nuts3.csv`,
um tensor de emprego regional por sector (`EMP`, Eurostat `nama_10r_3empers`),
mapeado de NUTS actual para as 25 regiões do painel HERALD.

**Nota sector PT**: INE publica births por CAE mapeados a A10. `sector_*` = births by sector
(mesma grandeza que target), lagged t-1. Total sectorial = target_births do ano anterior
(confirmado: max_diff = 0). Único país com sector A10 de births, além de França.

---

## 4. Máscaras de observabilidade

As máscaras existem nos 4 adapters e passam validação de intervalo `[0, 1]`.

| País | `mask_target` | `mask_sector_a10` | `mask_employment` | `mask_tensor` | `mask_eu_signals` | Leitura |
|---|---:|---:|---:|---:|---:|---|
| FR | 1.0 | 0–1 | 1.0 | 1.0 | ≈0.57 | target, sector, tensor e sinais EU parciais |
| NL | 1.0 | 0.0 | 1.0 | 1.0 | ≈0.57 | target e emprego genuínos; sector births ausente |
| BE | 1.0 | 0.0 | 1.0 | 1.0 | ≈0.52 | target e emprego genuínos; sector births ausente |
| PT | 1.0 | 0–1 | 1.0 | 1.0 | ≈0.53 | sector births disponível e tensor de emprego Eurostat genuíno |

**Acção necessária**: o trainer ainda precisa consumir `mask_tensor`/`mask_employment`
quando as configs usarem tensor ou perda parcial. Na Phase 4E-A estas máscaras são
metadata auditável, porque o tensor está desligado.

---

## 5. Riscos de vazamento temporal

### Verificação do validator (check 5)
O validator verifica numericamente que `lag1_births[t] == target_births[t-1]`:

| País | Lookahead detectado | Max diff |
|---|---|---|
| FR | ✗ nenhum | 0.000 |
| NL | ✗ nenhum | 0.000 |
| BE | ✗ nenhum | 0.000 |
| PT | ✗ nenhum | 0.000 |

### Sector A10 (FR e PT)
O shift `A10[t-1] → feature para ano t` foi aplicado correctamente via `target_year + 1`.
O primeiro ano de cada região tem `sector_*=NaN` e `mask_sector_a10=0` — não há lookahead.

### Stock lag-1
O stock é o valor do final de t-1. O join aplica `stock["target_year"] + 1 → feature para t`.
Validado: primeiro ano sem stock lag → NaN (não imputado como zero).

### EU signals
Todos os `eu_*` estão a NaN. Quando preenchidos em Phase 4E, devem seguir a regra:
- `eu_*_lag1` = média anual de t-1, publicada antes de t.
- Nunca usar t no mesmo `eu_*` que seria previsto.

---

## 6. Diferenças metodológicas por país

### Conceito de target
| País | Conceito | Fonte | Comparável entre si? |
|---|---|---|---|
| FR | `establishment_creation` | SIDE/SIRENE | ❌ com NL/BE/PT |
| NL | `enterprise_birth` | CBS | ✓ com BE, PT |
| BE | `enterprise_birth` | StatBel BCR | ✓ com NL, PT |
| PT | `enterprise_birth` | INE | equivalência Eurostat a confirmar |

**Implicação**: WMAPE cross-country FR vs NL/BE/PT não é directamente comparável.
FR conta estabelecimentos (incluindo novas filiais), NL/BE/PT contam empresas.
Para Phase 4E, manter avaliação separada por país. `flag_target_concept` documenta isto.

> **Correção Phase 4J (2026-06-09) — superseca a coluna "Comparável entre si?"
> acima.** A auditoria semântica oficial
> (`reports/HERALD_PHASE4J_SEMANTIC_TARGET_AUDIT.md`) mostra que **NL não é
> `enterprise_birth`**, mas `oprichtingen van vestigingen` (unidade local, como
> FR), e que **BE é uma primeira inscrição à TVA** (registo fiscal, com ruptura na
> saúde em jan/2022), não um nascimento demográfico. Logo NL/BE/PT **não** são
> mutuamente comparáveis como "empresas"; os rótulos `enterprise_birth` desta
> tabela para NL/BE estão imprecisos. Tratar o painel como multi-tarefa de targets
> heterogéneos (Path M). Conteúdo histórico preservado.

### Sector A10
| País | Sector disponível | Tipo | Grandeza |
|---|---|---|---|
| FR | ✓ | SIDE A10 births | mesma que target |
| NL | ❌ | Q-tensor = employment | diferente do target |
| BE | ❌ | Q-tensor = employment | diferente do target |
| PT | ✓ | INE CAE births | mesma que target |

**Implicação**: para Phase 4E, modelos com sector features só se aplicam a FR e PT.
Para NL e BE: usar employment tensor como feature separada (não como sector births).

### Tensor de emprego
| País | Tensor disponível | Tipo | Lag correcto? |
|---|---|---|---|
| FR | ✓ URSSAF | employment effectifs | ✓ (t-1) |
| NL | ✓ CBS | employment jobs (FTE) | ✓ (t-1) |
| BE | ✓ StatBel ONSS | employment jobs | ✓ (t-1) |
| PT | ✓ Eurostat | `nama_10r_3empers`, EMP × NACE × NUTS3 | ✓ até 2023; suficiente para target 2024 com lag1 |

**Implicação Phase 4D**: o "tensor" de PT era births proxy. Resultados de Phase 4D
(`sector_top8_births` = melhor PT) reflectem isso. Para Phase 4E, PT já possui tensor
de emprego genuíno via Eurostat `nama_10r_3empers`.

---

## 7. Recomendações antes de Phase 4E

### Pré-requisitos (bloqueantes)

| # | Recomendação | País | Prioridade |
|---|---|---|---|
| 1 | Fazer o trainer consumir `mask_tensor`/`mask_employment` nas configs tensor/loss parcial | Todos | Alta |
| 2 | Validar o tensor PT Eurostat contra o antigo proxy por ablação | PT | Alta |
| 3 | Carregar sinais EU restantes se forem usados em 4E-C/D | Todos | Média |
| 4 | Estender tensor ONSS BE para 2021–2024 se houver configs tensor BE pós-2020 | BE | Média |
| 5 | Carregar `eu_credit_standards_lag1` (ECB BLS) — Zona Euro apenas | FR/NL/BE/PT | Média |

### Recomendações metodológicas (não bloqueantes)

| # | Recomendação | Razão |
|---|---|---|
| 6 | Nunca comparar WMAPE FR vs NL/BE/PT directamente | Conceitos de target diferentes |
| 7 | Usar `mask_sector_a10` para escalar contribuição sectorial no loss | NL/BE sem sector births |
| 8 | Distinguir Phase 4D PT proxy de Phase 4E PT emprego Eurostat | evita misturar resultados antigos e novos |
| 9 | Adicionar sinais EU um de cada vez com ablação por país | Risco de colinearidade |
| 10 | Implementar `mask_eu_signals` automaticamente após carregar `eu_*` | Já previsto no validator |

---

## 8. Ficheiros produzidos

```
data/processed/european_panel/
├── france_panel.csv         3 640 rows × 43 cols
├── nl_panel.csv               440 rows × 43 cols
├── be_panel.csv               756 rows × 43 cols
├── pt_panel.csv               375 rows × 43 cols
└── european_panel_all.csv   5 211 rows × 43 cols

src/data/european_panel/
├── schema.py                  43 campos catalogados (FieldSpec)
├── validation.py              checks de qualidade + máscaras
├── build_european_panel.py    CLI: --country all|france|nl|be|pt
├── build_pt_eurostat_employment_tensor.py  PT Eurostat employment tensor
├── README.md                  arquitectura e regras
└── adapters/
    ├── __init__.py
    ├── france_adapter.py      FranceAdapter.build() + validate()
    ├── nl_adapter.py          NLAdapter.build() + validate()
    ├── be_adapter.py          BEAdapter.build() + validate()
    └── pt_adapter.py          PTAdapter.build() + validate()
```

---

## 9. Flags COVID/rebound — verificação de uso em trainers

| Trainer | Usa `flag_is_covid_year` como feature? | Notas |
|---|---|---|
| `train_dynamic_stgnn_models_v1.py` | **SIM** (via `feature_columns()`) | Trainer antigo, não usado em Phase 4+ |
| `train_herald_v5.py` | **SIM** (via `regime_seq`) | Trainer antigo |
| `train_herald_v6.py` | Apenas em modo `"manual_flags"` | Documentado; non-manual modes excluem |
| `train_herald_v7.py` | **NÃO** | Confirmado por grep |
| `train_herald_semi_v2.py` | **NÃO** | Confirmado por grep — pipeline Phase 4 |
| `herald_regime_modes.py` | Apenas em modo `"manual_flags"` | Explicitamente documentado |

**Conclusão**: o pipeline activo (Phase 4E usará `train_herald_semi_v2.py`) não usa estas flags
como features. `schema.NON_PREDICTIVE_FIELDS` formaliza esta restrição para futuros loaders.

---

## 10. Veredicto: o schema europeu está pronto para Phase 4E?

### Critérios cumpridos ✓

- [x] França reproduz o painel actual sem divergências (max_diff = 0 em target, lag1, growth_1y)
- [x] NL/BE/PT passam validação com warnings documentados
- [x] Sem vazamento temporal detectado em nenhum país
- [x] `mask_target` e `flag_forecast_safe` coerentes e corrigidos
- [x] Diferenças entre países explícitas no schema (`flag_target_concept`, `flag_has_eurostat_bd`,
      `flag_has_national_employment`, `mask_sector_a10`)
- [x] Correcção metodológica aplicada: `flag_forecast_safe=0` no primeiro ano de cada região
- [x] `NON_PREDICTIVE_FIELDS` definido em schema; trainer activo confirmado limpo
- [x] 43 campos catalogados / 43 exportados — schema canónico completo para 4E-A
- [x] NL `flag_has_national_employment` semântica clarificada: flag=1 quando emprego de t-1 disponível; CBS cobre até 2024, logo NL 2025 é flag=1 (usa CBS[2024] sob effectifs_lag1). Configs com policy `real` precisam excluir 2025 separadamente.
- [x] PT `flag_has_national_employment=1` após integração do tensor Eurostat EMP × NACE × NUTS3.

### Limitações documentadas (não bloqueam 4E-A)

| Limitação | País | Impacto | Bloqueia |
|---|---|---|---|
| Trainer ainda não consome `mask_tensor` | Todos | Tensor/loss parcial ainda dependem de configs externas | 4E-C/D |
| Sinais EU incompletos | Todos | 4/7 sinais carregados; STS/EEI/credit ainda ausentes | 4E-C/D |
| BE tensor ONSS pós-2020 ausente | BE | A10 de emprego BE não cobre toda a janela 2007–2024 | configs tensor BE |
| PT tensor sectorial só até 2023 | PT | suficiente para target 2024 com lag1; não para target 2025 | forecast 2025+ |

### Condições para Phase 4E

**4E-A (baseline padronizado)**: pronta agora. Os adapters reproduzem Phase 4A exactamente.

**4E-B (country embedding)**: pode arrancar, mas exige modificação minor no trainer.

**4E-C/D (EU signals, crédito)**: condicional até: (1) decidir quais sinais EU entram,
(2) fazer o trainer consumir `mask_tensor`/`mask_employment` quando houver tensor ou loss parcial,
(3) separar claramente configs tensor de configs baseline.

**Status final: PRONTO para 4E-A. CONDICIONAL para 4E-B/C/D.**
