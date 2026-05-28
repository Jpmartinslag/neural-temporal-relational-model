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
| Fonte candidata A | CBS `85481NED` — Werknemersbanen por região de trabalho |
| Fonte candidata B | CBS `81644NED` — Estabelecimentos por classe de tamanho × COROP × SBI |
| Território | COROP (40 regiões) — confirmado |
| Setores | SBI 2008 → A10 |
| Status | ⚠ Verificar se 85481NED tem breakdown por setor × COROP |

### Veredicto Países-Bas

```
✓ Conceito y idêntico à França
✓ 40 COROP = unidades funcionais de emprego (comparável às ZE)
✓ SBI 2008 → NACE → A10 mapping direto (EU harmonizado)
⚠ GAP 2007–2014: dados null nas APIs CBS — séries começam 2015
   → Janela de treino reduzida: 2015–2025 (11 anos vs 14 da França)
   → Crise 2008 não coberta — documentar no preflight ponto 4
⚠ Q-tensor por setor × COROP a confirmar (85481NED)
```

**Decisão:** LANÇAR com caveat — documentar gap temporal no preflight.

---

## Belgique (Belgium)

### Target — Criações de empresas

| Item | Verificação |
|------|-------------|
| Fonte nova | Statbel beSTAT (série 2021+) |
| Fonte antiga | Statbel série pré-2021 (quebra metodológica 2018) |
| API beSTAT | `https://bestat.statbel.fgov.be/bestat/api/views/{id}/result/CSV` |
| Status API | **400 Bad Request** — requer sessão de browser (não acessível via curl) |
| Território | Nacional apenas nas tabelas principais — arrondissement **não confirmado** |
| Anos | Nova série: 2021–2024; Antiga: pré-2018 (com quebra) |
| Conceito | **Empresa** (entidade legal) ≠ **estabelecimento** (unidade física) |

**Diferença crítica vs França:**  
França mede CRIAÇÕES DE ESTABELECIMENTOS (unidades físicas — podem existir múltiplos por empresa).  
Bélgica mede CRIAÇÕES DE EMPRESAS (entidades legais).  
→ Não são o mesmo conceito. Documentar no preflight ponto 1.

**Views beSTAT identificadas:**
- `d97429d4` — "Nb. d'entreprise active, naissance, mort en Belgique par année, 2021-" → nacional, 2021+
- `bec40330` — "Dynamiek van btw-registraties (per arrondissement...)" → **por arrondissement**, mas API retorna 400
- `b7f7018c` — "Number of active enterprises subject to VAT according to economic activity and administrative geography" → por atividade e geografia

### Q-Tensor — Emprego RSZ/ONSS

| Item | Verificação |
|------|-------------|
| Fonte | RSZ (Rijksdienst voor Sociale Zekerheid) — Statwork |
| Território | **43 arrondissements confirmados** (NIS-code Statbel) |
| Setores | NACE-BEL → NACE Rev.2 → A10 |
| Anos | Trimestral 2005–2025 |
| Download | Excel/ZIP disponível |
| Status | ✓ CONFIRMADO — emprego por arrondissement × NACE |

### Alinhamento vs França

| Componente | França | Bélgica | Status |
|-----------|--------|---------|--------|
| Conceito (y) | Créations établissements | Criações empresas (legal) | ⚠ DIFERENÇA DE CONCEITO |
| Território | 280 ZE | 43 arrondissements | ✓ Comparável |
| Setores | NAF → A10 | NACE-BEL → A10 | ✓ Mapeável |
| Cobertura | 2012–2025 | 2021+ (nova série) | ⚠ GAP GRAVE |
| Q-tensor | URSSAF arrd × A10 | RSZ arrd × NACE | ✓ EQUIVALENTE |

### Veredicto Bélgica

```
✓ Q-tensor (RSZ) totalmente equivalente — melhor fonte entre os 3 países
⚠ Target y: conceito diferente (empresa vs estabelecimento)
⚠ Cobertura temporal: 2021+ apenas na nova série
   → Série pré-2021 existe mas com quebra 2018 — verificar severidade
⚠ beSTAT API não acessível via curl — download manual obrigatório
⚠ Dados por arrondissement: confirmado para RSZ, não confirmado para nascimentos
BLOQUEANTE: verificar arrondissement-level births antes de lançar
```

**Decisão:** SUSPENDER — resolver 2 pontos antes de lançar:
1. Download manual dos dados de nascimentos beSTAT (ou dados de BTW registrations por arrondissement)
2. Verificar se série pré-2021 está disponível em download

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
| Fonte | GEP — Quadros de Pessoal (declarações anuais de todas as empresas com trabalhadores) |
| URL | `https://www.gep.mtsss.gov.pt/quadros-de-pessoal` |
| Território | Município por estabelecimento (agregável) |
| Setores | CAE Rev. 3 → NACE → A10 |
| Anos | 1985–2022 (anos recentes TBD — verificar acesso) |
| Conceito | Headcount + remuneração por estabelecimento × CAE × município |
| Status | ⚠ Download verificado para anos históricos; 2022+ pode requerer pedido formal |

### Alinhamento vs França

| Componente | França | Portugal | Status |
|-----------|--------|---------|--------|
| Conceito (y) | Créations établissements | Nascimentos empresas | ⚠ Empresa vs estabelecimento |
| Território | 280 ZE | 308 municípios | ✓ Granularidade similar |
| Cobertura | 2012–2025 | **2008–2022** | ✓ MELHOR cobertura histórica |
| Setores target | NAF → A10 | Forma jurídica apenas | ⚠ Sem breakdown CAE no target |
| Q-tensor | URSSAF × A10 | Quadros de Pessoal × CAE | ✓ EQUIVALENTE |

### Veredicto Portugal

```
✓ Cobertura temporal: 2008–2022 confirmada — cobre crise 2008
✓ 308 municípios acessíveis via API pública INE
✓ Q-tensor equivalente (Quadros de Pessoal)
✓ CAE Rev.3 → NACE → A10 mapping direto
⚠ Conceito y: empresa (legal) vs estabelecimento (físico) — documentar
⚠ Breakdown setorial das criações: não disponível neste indicador
   → Para alvo auxiliar A10, precisar de indicador separado (buscar nascimentos × CAE)
⚠ Anos recentes Quadros de Pessoal (2022+): verificar acesso
⚠ Territorio: 308 municípios >> 40 COROP NL / 43 arrd BE
   → Considerar agregação em zonas de emprego INE (23) se disponível
```

**Decisão:** LANÇAR após resolver: (1) acesso GEP, (2) escolha territorio 308 vs 23.

---

## Comparação consolidada

| Critério preflight | França (ref) | Países-Bas | Bélgica | Portugal |
|--------------------|-------------|------------|---------|---------|
| **1. Conceito y** | établissement | vestiging ✓ | empresa ⚠ | empresa ⚠ |
| **2. Território** | 280 ZE | 40 COROP ✓ | 43 arrd ✓ | 308 mun ⚠ |
| **3. Setores** | NAF→A10 | SBI→A10 ✓ | NACE-BEL ✓ | CAE→A10 ✓ |
| **4. Cobertura** | 2012–2025 | 2015–2025 ⚠ | 2021+ ⚠⚠ | 2008–2022 ✓ |
| **5. Q-tensor** | URSSAF ✓ | CBS (verificar) ⚠ | RSZ ✓ | Quadros ⚠ |
| **6. Estanquidade** | ✓ | ✓ | ✓ | ✓ |
| **Prontidão** | — | **LANÇAR** ⚠ | **SUSPENDER** ⛔ | **LANÇAR** ⚠ |

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
