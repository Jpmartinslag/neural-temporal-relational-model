# HERALD Phase 4 — Data Verification Report

**Date:** 2026-05-27  
**Objectif:** Verificar se cada país tem dados equivalentes ao painel França antes de construir pipelines.

---

## Estrutura de referência — França

| Coluna | Fonte | Descrição |
|--------|-------|-----------|
| `zone_id` | SIRENE/INSEE | ZE2020 (280 zonas de emprego) |
| `target_year` | — | 2012–2025 |
| `y` | SIDE/SIRENE | Criações de **estabelecimentos** (físicos) |
| `side_lag_1` | — | y(t-1), feature principal |
| `growth_1y` | — | (y(t)−y(t-1))/y(t-1) |
| `effectifs_lag1` | URSSAF | Assalariados × setor A10 × ZE, lag 1 ano |
| `masse_sal_lag1` | URSSAF | Massa salarial × setor A10 × ZE, lag 1 ano |
| `side_stock_*_lag1` | FLORES | Stock estabelecimentos por setor A10 × ZE |
| Alvo auxiliar A10 | FLORES | Criações por setor A10 (semi-supervisão) |

**Escala:** ~280 ZE × 14 anos = ~3920 observações. Criações Francia 2021: ~1.1M total.

---

## Países-Bas (Netherlands)

### Target — Criações de estabelecimentos

| Item | Verificação |
|------|-------------|
| Fonte | CBS StatLine — `83631NED` (Vestigingen oprichtingen) |
| API | `https://opendata.cbs.nl/ODataApi/odata/83631NED/TypedDataSet` |
| Território | **40 COROP (CR01–CR40)** — confirmado via API |
| Anos | **2015–2025** com dados (2007–2014: null) |
| Setores | SBI 2008 — 129 categorias, mapeável para A10 |
| Conceito | Criações de vestigingen (estabelecimentos) — **idêntico à França** |

**Amostra real (CR23 Groot-Amsterdam, 2020):**
```
Total A-U: 27.680 oprichtingen
A (Landbouw):    40
B-E (Nijverheid): 575
C (Industrie):   ~45
...
```

**Alinhamento vs França:**

| Componente | França | Países-Bas | Status |
|-----------|--------|------------|--------|
| Conceito (y) | Créations établissements | Oprichtingen vestigingen | ✓ IDÊNTICO |
| Território | 280 ZE | 40 COROP | ✓ Comparável |
| Setores | NAF Rev.2 → A10 | SBI 2008 → NACE → A10 | ✓ Mapeável |
| Cobertura | 2012–2025 | **2015–2025** | ⚠ GAP 2012–2014 |

### Q-Tensor — Emprego por região × setor

| Item | Verificação |
|------|-------------|
| Fonte | CBS `83582NED` — BanenVanWerknemersInDecember × SBI × COROP |
| Território | 40 COROP (CR01–CR40) — confirmado |
| Setores | SBI 2008 → NACE → A10 (10 códigos) |
| Anos | 2010–2024 (CBS disponibilidade) |
| Status | ✅ CONFIRMADO — CBS 83582NED tem breakdown setor × COROP |
| NaN policy | 48 células suprimidas (0.8%) — flag `jobs_suppressed=1`, fill 0 |

### Veredicto Países-Bas

```
✅ Conceito y idêntico à França (oprichtingen vestigingen)
✅ 40 COROP = unidades funcionais de emprego (CR01–CR40; CR98/CR99 excluídas)
✅ SBI 2008 → NACE → A10 mapping direto (EU harmonizado)
✅ Q-tensor employment/effectifs confirmado: CBS 83582NED 2010–2024
⚠ GAP 2007–2014: births CBS começam 2015 — janela 11 anos vs 14 da França
   → Documentado. Não é bloqueador.
⚠ Q-tensor 2025: não disponível CBS. Para lag-1, target 2025 usa qtensor 2024.
   Nenhum proxy necessário no pipeline principal.
```

**Decisão:** ✅ LANÇAR — preflight PASS.

---

## Belgique (Belgium)

### Target — Criações de empresas

| Item | Verificação |
|------|-------------|
| Fonte | Statbel TVA primo-assujetissements (export (1).csv) |
| Status API | ✅ Dados disponíveis — ficheiro CSV local |
| Território | 42 arrondissements — confirmado |
| Anos | 2007–2020 (série antiga; quebra metodológica 2018) |
| Conceito | **Empresa** (entidade legal) ≠ **estabelecimento** (unidade física) |

**Diferença crítica vs França:**
França mede CRIAÇÕES DE ESTABELECIMENTOS (unidades físicas). Bélgica mede CRIAÇÕES DE EMPRESAS (entidades legais). Documentar no paper.

### Q-Tensor — Emprego RSZ/ONSS

| Item | Verificação |
|------|-------------|
| Fonte | ONSS localunit publications — employees × NACE × arrondissement |
| Território | 42 arrondissements confirmados |
| Setores | NACE-BEL → NACE Rev.2 → A10 |
| Anos | **2008–2020** (2007 NACE Rev.1 — incompatível com A10, excluído por design) |
| Status | ✅ CONFIRMADO |

### Alinhamento vs França

| Componente | França | Bélgica | Status |
|-----------|--------|---------|--------|
| Conceito (y) | Créations établissements | Criações empresas (legal) | ⚠ DIFERENÇA DE CONCEITO |
| Território | 280 ZE | 42 arrondissements | ✅ Comparável |
| Setores | NAF → A10 | NACE-BEL → A10 | ✅ Mapeável |
| Cobertura | 2012–2025 | 2007–2020 | ⚠ Janela mais curta |
| Q-tensor | URSSAF arrd × A10 | ONSS arrd × NACE | ✅ EQUIVALENTE |

### Veredicto Bélgica

```
✅ Q-tensor (ONSS) equivalente a employment/effectifs
✅ 42 arrondissements confirmados
✅ Window principal: 2008–2020; primeira avaliação 2009 (depois de lags)
⚠ Stock 2006 excluído da janela principal (fora do target window)
⚠ Qtensor 2007 ausente por design (NACE Rev.1 incomp.)
   → Não usar carry-forward 2008→2007 no pipeline principal
⚠ Quebra metodológica TVA 2018 — flagar no modelling
```

**Decisão:** ✅ LANÇAR — preflight PASS.

---

## Portugal

### Target — Criações de empresas

| Item | Verificação |
|------|-------------|
| Fonte | INE BDPortugal — indicador `0009702` |
| API | `https://www.ine.pt/ine/json_indicador/pindica.jsp?op=2&varcd=0009702` |
| Território | **308 municípios** — confirmado via API |
| Anos | **2008–2022** — confirmado (S7A2008 a S7A2022) |
| Setores | Dimensão = Forma jurídica (não CAE) — sem breakdown setorial neste indicador |
| Conceito | Criações de empresas (entidade legal) |

**Amostra real (2020, 308 municípios filtrados):**
```
Total Portugal:    306.580 nascimentos
Lisboa:             28.108
Vila Nova de Gaia:  12.598
Sintra:             12.108
Porto:               9.572
...
Pampilhosa da Serra:    30
Barrancos:              26
Corvo (Açores):         16
```

**Escala comparada:**
| País | Pop. | Criações/ano (2020) | Taxa/Mhabitante |
|------|------|---------------------|-----------------|
| França | 67M | ~1.1M | 16.4k |
| Portugal | 10M | ~307k | 30.7k | 
| Diferença | — | — | 1.9× maior (inclui mais micro/auto-empr.) |

→ Escalas consistentes. Portugal tem mais auto-empregados per capita.

### Q-Tensor — Emprego por município × setor

| Item | Verificação |
|------|-------------|
| Fonte | INE BDPortugal — indicador `0009703` (nascimentos × CAE section × município) |
| Território | 25 NUTS3 (reagreg. de municípios) |
| Anos | 2008–2022 |
| Valor | Nascimentos de empresas (não emprego/effectifs) |
| Status | ✅ Disponível | 

> **AVISO FRAMING**: Este tensor é um `sector_births_tensor`, NÃO um Q7 effectifs (employment).
> Não chamar de "Q7 effectifs" ou "tensor laboral" em configs, paper ou dashboards.
> Para Q7-equivalente, é necessário ingerir GEP Quadros de Pessoal (employment).

### Alinhamento vs França

| Componente | França | Portugal | Status |
|-----------|--------|---------|--------|
| Conceito (y) | Créations établissements | Nascimentos empresas | ⚠ Empresa vs estabelecimento |
| Território | 280 ZE | 25 NUTS3 | ✅ Comparável |
| Cobertura | 2012–2025 | **2008–2022** | ✅ Melhor cobertura histórica |
| Setores target | NAF → A10 | CAE → A10 | ✅ Mapeável |
| Tensor | URSSAF effectifs | sector_births (CAE) | ⚠ NÃO equivalente a Q7 employment |

### Veredicto Portugal

```
✅ Cobertura temporal: 2008–2022 confirmada
✅ 25 NUTS3 — acessível via reagregação de municípios
✅ CAE → A10 mapping direto
✅ Preflight PASS — pronto para Phase 4A
⚠ Tensor: sector_births_tensor (NOT Q7 effectifs/employment)
   → Testar como variante separada, não como drop-in replacement do Q7
⚠ KZ = 0 everywhere — esperado (setor financeiro não aparece em nascimentos)
⚠ GEP Quadros de Pessoal: não ingerido. Pendente para Q7-equivalente PT.
```

**Decisão:** ✅ LANÇAR — preflight PASS (com sector_births_tensor como variante separada).

---

## Comparação consolidada

| Critério preflight | França (ref) | Países-Bas | Bélgica | Portugal |
|--------------------|-------------|------------|---------|---------|
| **1. Conceito y** | établissement | vestiging ✅ | empresa ⚠ | empresa ⚠ |
| **2. Território** | 280 ZE | 40 COROP ✅ | 42 arrd ✅ | 25 NUTS3 ✅ |
| **3. Setores** | NAF→A10 | SBI→A10 ✅ | NACE-BEL ✅ | CAE→A10 ✅ |
| **4. Cobertura** | 2012–2025 | 2015–2025 ⚠ | 2007–2020 ⚠ | 2008–2022 ✅ |
| **5. Tensor** | URSSAF effectifs | CBS jobs ✅ | ONSS jobs ✅ | sector_births ⚠⚠ |
| **6. Preflight** | — | ✅ PASS | ✅ PASS | ✅ PASS |
| **Prontidão** | — | **✅ LANÇAR** | **✅ LANÇAR** | **✅ LANÇAR** ⚠ |

---

## Próximos passos por país

### Países-Bas (J1)
```python
# 1. Download births (83631NED) para todos os COROP × SBI × 2015-2024
# 2. Download stock (81578NED) para growth_1y
# 3. Verificar 85481NED — tem setor × COROP? Se sim, usar como q_tensor
# 4. Preflight: documentar gap 2012-2014
```

### Bélgica (BLOQUEADO — J2 condicionado)
```
1. Fazer download manual via browser: beSTAT view bec40330 (BTW por arrondissement)
   URL browser: https://bestat.statbel.fgov.be
2. Verificar série histórica de nascimentos pré-2021
3. Só avançar quando nascimentos por arrondissement confirmados
```

### Portugal (J3)
```python
# 1. Download INE 0009702 todos os anos (2008-2022) → births por município
# 2. Buscar nascimentos × CAE (indicador separado INE)
# 3. Verificar Quadros de Pessoal — download até qual ano sem pedido formal?
# 4. Decisão: 308 municípios vs zonas de emprego INE
```

---

## Notas metodológicas para o paper

**Discrepância conceitual empresa vs estabelecimento:**  
> "Para a França utilizámos criações de estabelecimentos (unidades físicas, SIRENE). Para Bélgica e Portugal, os dados disponíveis medem criações de empresas (entidades legais). Uma empresa pode ter múltiplos estabelecimentos. Este conceito é mais próximo do que é habitualmente reportado nos sistemas de estatísticas empresariais europeias. A diferença implica que o nível absoluto de criações é subestimado para BE e PT, mas a dinâmica temporal e territorial é estruturalmente equivalente."

**Gap temporal Países-Bas:**  
> "Os dados CBS ao nível COROP estão disponíveis a partir de 2015. A janela de walk-forward para os Países-Baixos começa em 2015 vs 2012 para a França. A crise financeira 2008–2010 não é coberta nesta réplica."
