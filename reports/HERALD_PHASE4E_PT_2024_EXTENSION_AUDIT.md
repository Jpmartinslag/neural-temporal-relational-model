# HERALD — Auditoria da Extensão Portugal 2024 (Phase 4E)

**Data:** 2026-06-02
**Âmbito:** Integração recente do painel europeu HERALD, foco em Portugal Phase 4E
(extensão de 2008–2022 → 2008–2024 com indicadores INE NUTS 2024).
**Projeto:** `/home/jpdark/Downloads/project_recomm/dataset`
**Método:** verificação empírica de todos os artefactos + re-execução determinística
do pipeline + leitura do código do core HERALD. Postura crítica; nada assumido como correto.

---

## 1. Resumo executivo

**VEREDITO: PASS — pode treinar a bateria 4E no HPC.**

A extensão Portugal 2024 está **tecnicamente correta e metodologicamente sólida** no que
foi introduzido por este trabalho: integridade de dados, mapeamento NUTS 2024 → 25 zonas,
adapter PT, preparação Phase 4E e reprodutibilidade do pipeline **passam todos**. Os alvos
2010–2022 são **byte-idênticos** aos do pipeline PT anterior (nenhuma regressão de dados).

Durante a auditoria foi encontrado um problema metodológico de alta severidade (`F1`):
as features `growth_1y`/`growth_2y` vinham da forma histórica leaky
`(y_t − y_{t-1})/y_{t-1}` em alguns painéis de origem. A correção foi aplicada **na camada
canônica Phase 4E**, antes do treino: `build_european_panel.py` agora recalcula
`growth_1y[t] = (y_{t-1} − y_{t-2})/y_{t-2}` e
`growth_2y[t] = (y_{t-1} − y_{t-3})/y_{t-3}` para todos os países. A validação agora bloqueia
qualquer retorno da forma leaky. Isso não altera runs históricas; apenas torna a Phase 4E
causal.

Conclusão prática:
- ✅ **Treinar a bateria 4E comparativa**: SIM. PT é tratado em pé de igualdade com FR/NL/BE.
- ✅ **Usar a Phase 4E como painel causal novo**: SIM, desde que os treinos usem os CSVs
  regenerados após esta correção.

---

## 2. Arquivos e cobertura

| Arquivo | Linhas | Zonas | Anos | Dup | NaN indevido | Status |
|---|---|---|---|---|---|---|
| `portugal_births_panel_nuts3.csv` | 425 | 25 | 2008–2024 | 0 | não (lag-início) | ✅ |
| `portugal_stock_panel_nuts3.csv` | 425 | 25 | 2008–2024 | 0 | 0 | ✅ |
| `portugal_qtensor_births_cae_nuts3.csv` | 4250 | 25 | 2008–2024 | 0 | 0 | ✅ |
| `portugal_qtensor_employment_eurostat_nuts3.csv` | 6250 | 25 | 2000–2024 | 0 | 0 | ✅ |
| `european_panel/pt_panel.csv` | 425 | 25 | 2008–2024 | 0 | não (mascarado) | ✅ |
| `phase4e/pt/panel_ze2020.csv` | 425 | 25 | 2008–2024 | 0 | não (mascarado) | ✅ |
| `phase4e/pt/a10_ze2020.csv` | 425 | 25 | 2008–2024 | 0 | 0 | ✅ |
| `phase4e/pt/splits.csv` | 15 folds | — | 2010–2024 | — | — | ✅ |

**Verificações de integridade (todas PASS):**
- Contagens de linhas batem exatamente com o esperado.
- **25 zonas presentes em todos os anos** (sem ano incompleto).
- **Zero duplicatas** nas chaves `(zone, year)` e `(zone, year, a10)`.
- NaN presentes são **apenas os esperados** e estão cobertos por máscara ou são início-de-série:
  - `side_lag_1/2/3`: NaN em 2008/2009/2010 (sem ano anterior) → `feature_forecast_safe=0` em 2008.
  - `sector_*`: NaN apenas em 2008, com `mask_sector_a10=0` nesses registos (0 casos de NaN com máscara=1).
  - `eu_sts_turnover_lag1`, `eu_eei_lag1`: 100% NaN (sinais bloqueados, ver `MISSING_DATA_SEARCH`), cobertos por `mask_eu_signals`.
  - `eu_employment_rate_lag1` / `eu_credit_standards_lag1`: NaN parcial (lag + anos iniciais), cobertos por máscara.

`a10_ze2020.csv` confirmado como **tensor de emprego Eurostat/ARDECO** (colunas
`BE,FZ,GI,JZ,KZ,LZ,MN,OQ,RU,total`; fontes `Eurostat nama_10r_3empers` 2000–2023 +
`ARDECO SNETZ 2024`), **não** proxy de births.

---

## 3. Auditoria do mapeamento NUTS 2024 → 25 zonas HERALD

**Status: PASS.**

- Mapa em `src/data/ingest_portugal_panel_nuts3.py` (`NUTS2024_TO_HERALD_NUTS3`).
- **Caso crítico PT_170 confirmado:** `1A0` (Grande Lisboa) → `170` e `1B0`
  (Península de Setúbal) → `170`. A agregação é feita por
  `groupby(["zone_id","target_year"]).sum()` (linha 139-144) → as duas sub-regiões
  NUTS 2024 são **somadas** na zona histórica PT_170 (Área Metropolitana de Lisboa).
- **Sanity numérico:** PT_170 = 81.619 births (2022), a maior zona do país por larga
  margem (2.ª = PT_11A/Porto = 42.702), consistente com a fusão Lisboa+Setúbal.
- **25 zonas presentes, contíguas e sem duplicação.** Nenhuma zona ausente ou agregada
  incorretamente. `meta_nuts3_code` coincide 1:1 com os códigos NUTS3 (`PT111`…`PT300`),
  `PT_170` rotulado "Área Metropolitana de Lisboa".
- Splice temporal: 2008–2022 via indicadores antigos (NUTS 2013), 2023–2024 via novos
  (NUTS 2024 remapeados). A continuidade dos alvos foi confirmada (ver §4).

---

## 4. Auditoria anti-vazamento temporal

**Status: PASS.**

| Verificação | Resultado |
|---|---|
| `side_lag_1[t] == target[t-1]` | ✅ 0 mismatches (400 linhas) |
| `side_lag_2[t] == target[t-2]` | ✅ 0 mismatches |
| `side_lag_3[t] == target[t-3]` | ✅ 0 mismatches |
| `target[2024]` não entra como feature de 2024 | ✅ (via lags) |
| `is_covid_year` / `is_post_covid_rebound` fora do input | ✅ excluídos pelo wrapper, com guard rígido |
| `growth_1y` / `growth_2y` usam apenas anos anteriores | ✅ 0 mismatches após correção Phase 4E |

- **Lags seguros**: `side_lag_1/2/3` usam estritamente anos anteriores. Verificado
  numericamente em todas as zonas/anos com zero discrepâncias.
- **NON_PREDICTIVE_FIELDS**: `run_herald_phase4e_a_wrapper.py` substitui
  `feature_columns()` por `BASELINE_ANNUAL_FEATURES` e tem guard que **aborta** se
  `is_covid_year`/`is_post_covid_rebound` entrarem no conjunto de features (linhas 147-156).
  Confirmado: `x_ann` = `[side_lag_1, side_lag_2, side_lag_3, growth_1y, growth_2y]`.
- **Concordância de alvos old vs new (2010–2022)**: byte-idêntica. O splice NUTS 2024
  não alterou os anos históricos.
- **Growth causal corrigido no painel canônico**: `growth_1y/2y` agora são recalculados
  em `build_european_panel.py` a partir de lags apenas. Verificação empírica pós-correção:
  `safe_bad=0` e `leaky_match=0` para FR/NL/BE/PT.

---

## 5. Auditoria do adapter PT

**Status: PASS.**

- **Lê diretamente de `data/external/portugal/processed/`** (linhas 47-50 do
  `pt_adapter.py`): births, stock, qtensor births CAE e tensor de emprego Eurostat.
  **Não depende** de `data/processed/phase4/pt` (o painel antigo congelado em 2022).
- `node_idx`: **contíguo 0–24**, sem buracos, e **estável em todos os anos** (mesma
  ordenação `region_id → node_idx` ano a ano).
- `region_id` / `meta_nuts3_code`: coerentes (`PT_111`↔`PT111`, …), `region_level=NUTS3`,
  `meta_region_system=NUTS3`.
- `flag_target_concept = enterprise_birth` (correto para PT; distinto de FR =
  `establishment_creation`). A comparação PT vs FR não deve usar valor absoluto sem ajuste
  de conceito (já documentado no STANDARD_PLAN).

---

## 6. Auditoria Phase 4E

**Status: PASS.**

- `phase4e/pt/panel_ze2020.csv`: 425 linhas, 25 zonas, **2008–2024**;
  `feature_forecast_safe=1` em 400 linhas (25 não-safe = ano 2008).
- `a10_ze2020.csv`: **tensor de emprego Eurostat/ARDECO** (confirmado no log do
  `prepare_phase4e_panel.py`: "Eurostat employment tensor"), não proxy births.
- `splits.csv`: **15 folds, 2010–2024**, estritamente ex-ante (`train_years_max = eval_year-1`,
  `train_years_min=2008`). COVID corretamente marcado em treino a partir do fold 2021.
- Adjacências: `adj_geo` 25×25, `adj_mob` 25×25 (`phase4e/pt`); `adj_identity` 25×25
  (`phase4d/pt`, usado pela bateria 4E-A de grafo-identidade). Todas quadradas e completas.

---

## 7. Validação executada (task 7)

| Comando | Resultado |
|---|---|
| `py_compile` nos 6 scripts alterados | ✅ ALL OK |
| `ingest_portugal_panel.py` | ✅ EXIT 0 (usa 0014099 p/ 2023-2024) |
| `ingest_portugal_panel_nuts3.py` | ✅ EXIT 0, PREFLIGHT PASS, 4250/425 linhas |
| `build_pt_eurostat_employment_tensor.py` | ✅ EXIT 0, PREFLIGHT PASS, 6250 linhas |
| `build_european_panel.py --country all` | ✅ EXIT 0, PT 425×43 |
| `prepare_phase4e_panel.py --country all` | ✅ EXIT 0, splits 15 folds |
| `bash hpc/phase4/smoke_test_phase4e_a.sh` | ✅ PASS=4 FAIL=0, 1 época CPU, FR/NL/BE/PT |

Após a correção F1, os ficheiros externos PT permanecem estáveis e os painéis canônicos
foram regenerados com `growth_*` causal. O pipeline é determinístico end-to-end
(raws INE/Eurostat em cache).

---

## 8. Problemas encontrados

### F1 — `growth_1y`/`growth_2y` violavam o contrato t-1 (ALTA, CORRIGIDO na Phase 4E)

- **Sintoma original:** no painel, `growth_1y = (y_t − y_{t-1})/y_{t-1}` e
  `growth_2y = (y_t − y_{t-2})/y_{t-2}` (100% de correspondência empírica). Ou seja,
  ambas dependem do **alvo do ano corrente `y_t`**.
- **Contrato violado:** `schema.py:12` declara *"growth_* : year-on-year pct-change,
  computed at t-1"* e marca os campos como `feature_t1` (pré-`t`).
- **Caminho de consumo:** `train_herald_v6.py:make_sequences` constrói `x_ann_full` sobre
  `t_full_idx = anos ≤ target_year` (linha 617, 647-649) e `build_annual_tensor`
  (linha 311-324) coloca `growth_1y[t]` no **mesmo timestep** do alvo `y[t]`, sem shift.
  `feature_columns()` (linha 595) inclui `growth_1y/2y`. Logo o vetor de features do
  passo-alvo contém informação derivada de `y_t` → **vazamento temporal parcial**.
- **Por que não é vazamento total (WMAPE ≠ 0):** a reconstrução exata exigiria o produto
  não-linear `lag1·(1+growth_1y)`, que a componente Ridge linear não representa; a parte
  NN poderia explorar parcialmente. Empiricamente o WMAPE PT é 0,24 (não ~0), confirmando
  que não há reconstrução perfeita — mas o sinal é informativo e potencialmente otimista.
- **Abrangência:** o painel **França** (baseline validado V6/V7) tem a **forma idêntica**
  (leaky-form 100%, safe-form 0%). É um problema **do core HERALD / construção do painel,
  anterior a este trabalho**, não específico de Portugal.
- **Correção aplicada:** `build_european_panel.py` agora recalcula `growth_1y/2y` de forma
  causal para todos os países antes de validar e salvar o painel europeu:
  `growth_1y[t]=(lag1-lag2)/lag2`; `growth_2y[t]=(lag1-lag3)/lag3`.
- **Guardrail aplicado:** `validation.py` agora marca erro se `growth_1y` voltar a bater
  com `(target_births-lag1_births)/lag1_births`.
- **Verificação pós-correção:** FR/NL/BE/PT têm `safe_bad=0` e `leaky_match=0`.
- **Escopo:** as runs históricas não foram alteradas. A correção vale para a Phase 4E
  regenerada e futuras baterias europeias.

### F2 — Sector births PT ausente em 2008 no painel (BAIXA)

- `sector_*` é NaN em 2008 no `pt_panel` (mascarado com `mask_sector_a10=0`), embora o
  tensor bruto `portugal_qtensor_births_cae_nuts3.csv` tenha 2008. Perda de 1 ano de
  cobertura setorial, **corretamente mascarada** (sem vazamento). 2008 já é não-forecast-safe.
  Sem ação requerida.

### F3 — Nome da coluna-alvo enganador no painel Phase 4E (BAIXA / cosmético)

- Em `phase4e/pt/panel_ze2020.csv` o alvo chama-se `side_establishment_creations_official`
  (slot herdado do esquema FR), mas o conceito PT é *enterprise birth*. O
  `flag_target_concept = enterprise_birth` corrige isto a jusante, **sem risco analítico**.
  Recomenda-se (opcional) renomear para um nome neutro ou anotar a coluna.

---

## 9. Correções feitas

1. **`src/data/european_panel/README.md`** — adicionada nota "Portugal births extension
   2023–2024" documentando explicitamente: 2008–2022 via indicadores INE antigos
   (`0009702/0009703/0009819`, NUTS 2013); 2023–2024 via novos (`0014098/0014099/0014061`,
   NUTS 2024) remapeados para 25 zonas; caso crítico `PT_170 = 1A0 + 1B0`. (Correção
   pequena e localizada, doc-only, fecha a task 6.)
2. **`src/data/european_panel/build_european_panel.py`** — adicionada função
   `enforce_causal_growth()` para recalcular `growth_1y/2y` apenas com lags antes de
   qualquer validação/salvamento.
3. **`src/data/european_panel/validation.py`** — adicionada validação anti-vazamento para
   bloquear `growth_*` não causal.

Nenhum arquivo antigo de runs históricas ou arquitetura do HERALD foi alterado. Os painéis
Phase 4E foram regenerados com a correção causal. Nenhum push efetuado.

---

## 10. Veredito final

**PODE TREINAR no HPC a bateria Phase 4E** com Portugal, em pé de igualdade com FR/NL/BE.

- A extensão PT 2024 é correta: integridade, mapeamento NUTS, anti-vazamento de lags,
  adapter, prep 4E e reprodutibilidade **todos PASS**.
- A ressalva `F1` foi corrigida para a Phase 4E: os CSVs regenerados não carregam mais
  growth leaky.

**Condições:**
1. Para a bateria comparativa 4E (efeito de country embedding / sinais EU): **liberado**.
2. Para qualquer **claim científico de acurácia absoluta** (WMAPE como métrica de qualidade
   do modelo): usar apenas resultados treinados após a correção causal da Phase 4E; runs
   históricas com growth antigo devem ser tratadas como comparativas/diagnósticas.

**Itens operacionais fora deste âmbito** (registados para acompanhamento): a run 4E-A FR
(`herald_phase4e_a_fr_20260601_114359_r1`) terminou **sem resultados** (0 JSONs); precisa de
re-execução para completar a validação 4E-A em FR. Não bloqueia o treino PT.
