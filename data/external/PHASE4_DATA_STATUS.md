# Phase 4 — Data Status (actualizado 2026-05-28)

**Propósito:** Resumo de prontidão de dados por país antes do pipeline HPC Phase 4A.  
**Estado:** ✅ Todos os painéis principais validados pelo preflight. Prontos para preparação HPC.

---

## Consolidated Status Table

| Componente | Belgium | Netherlands | Portugal |
|------------|---------|-------------|----------|
| Enterprise births | ✅ Arrondissements, TVA primo-assujetissements, 2007–2020 | ✅ COROP oprichtingen vestigingen (CBS 83631NED), 2015–2025 | ✅ NUTS3 nascimentos de empresas (INE 0009702), 2008–2022 |
| Territory | ✅ 42 arrondissements | ✅ 40 COROP (CR01–CR40; CR98/CR99 excluídas) | ✅ 25 NUTS3 |
| Sector tensor | ✅ ONSS jobs × NACE-A10, 2008–2020 | ✅ CBS jobs × SBI-A10, 2010–2024 | ⚠️ sector_births × CAE-A10 (NOT employment) |
| Stock | ✅ Statbel TVA, 2007–2020 | ✅ CBS 81578NED, 2015–2025 | ✅ INE 0009819, 2008–2022 |
| Geometries | ✅ Statbel CC BY 4.0 | ✅ CBS open data | ✅ INE CAOP |

---

## Modelling Windows

| País | Births | Stock | Tensor | Primeira avaliação |
|------|--------|-------|--------|-------------------|
| **NL** | 2015–2025 | 2015–2025 | 2010–2024 (employment) | 2016 |
| **BE** | 2007–2020 | 2007–2020 | 2008–2020 (employment) | 2009 |
| **PT** | 2008–2022 | 2008–2022 | 2008–2022 (sector_births) | 2009 |

---

## Preflight Status (2026-05-28)

```
NL: PASS ✅  |  BE: PASS ✅  |  PT: PASS ✅
Run: python3 src/data/phase4_preflight.py
```

---

## Notas metodológicas críticas

### Netherlands
- **Births**: CBS 83631NED oprichtingen vestigingen — **idêntico ao conceito France SIRENE** ✅
- **Stock**: CBS 81578NED, clipped a 2015–2025. Anos 2007–2014 têm NaN (CBS não publica totais COROP antes de 2015).
- **Q-tensor**: CBS 83582NED, 2010–2024. Ano 2025 **não disponível e não proxied** no pipeline principal. Para modelos lag-1, o target 2025 usa qtensor 2024 — nenhum proxy necessário.
- **NaN suprimidos no qtensor**: 48 células (0.8%) suprimidas pelo CBS (controlo de divulgação estatística). Política: `jobs_suppressed=1`, preenchimento com 0. Documentado em `jobs_suppressed` flag column.
- ~~NL usa apenas ΔStock proxy~~ — **OBSOLETO**. NL tem births COROP reais 2015–2025.

### Belgium
- **Window principal**: 2008–2020 (qtensor começa 2008 — NACE Rev.1 em 2007 incompatível com A10).
- **2006 stock removido**: Statbel disponível desde 2006 mas excluído da janela principal.
- **2007 qtensor ausente**: correcto por design (NACE Rev.1). NÃO usar carry-forward 2008→2007 no pipeline principal. Sensibilidade apenas se documentado.
- **Conceito births**: Primo-assujetissements TVA (empresa legal ≠ estabelecimento físico). Diferença documentada.
- **Quebra metodológica 2018**: flagar no modelling.

### Portugal
- **Tensor framing**: `portugal_qtensor_births_cae_nuts3.csv` é um **sector_births_tensor**, NÃO Q7 effectifs.
  - França Q7 = URSSAF effectifs (stock de assalariados × sector × ZE)
  - Portugal tensor = nascimentos de empresas × CAE→A10 × NUTS3
  - **Não chamar de Q7 effectifs ou tensor laboral em nenhum contexto.**
  - Usar label: `sector_births_tensor` ou `sector_births_lag1` em todos os configs.
- **KZ = 0**: esperado (setor financeiro não aparece nos nascimentos de empresas INE).
- **Q7-equivalente (employment)**: requer GEP Quadros de Pessoal — **não ingested ainda**.

---

## Questões resolvidas

| # | Questão original | Estado |
|---|-----------------|--------|
| NL-4 | Verificar se CBS tem breakdown setor × COROP | ✅ Resolvido — CBS 83582NED confirmado |
| NL-5 | Validação ΔStock proxy | ✅ Obsoleto — births reais disponíveis |
| BE-1 | Births por arrondissement confirmados | ✅ Resolvido — TVA primo-assujetissements |
| BE-2 | Série pré-2021 disponível | ✅ Resolvido — 2007–2020 TVA disponível |
| BE-3 | RSZ cross-tab arrondissement × NACE | ✅ Resolvido — ONSS localunit confirmado |
| PT-6 | Escolha território 308 vs 23 | ✅ Decidido — 25 NUTS3 (reagregação de municípios) |
| PT-7 | Acesso GEP Quadros de Pessoal | ⚠️ Pendente — necessário para Q7-equivalente PT |

---

## Bloqueadores restantes antes de HPC

| País | Bloqueador | Impacto |
|------|-----------|---------|
| PT | GEP Quadros de Pessoal não ingerido | PT só tem sector_births_tensor, não Q7-equivalente. Modelos com employment signal não comparáveis a FR/NL/BE. |
| BE | Quebra metodológica TVA 2018 | Deve ser flagado nos resultados — não bloqueia mas afecta interpretação. |

**Nenhum bloqueador impede lançar Phase 4A com births + stock + sector_births_tensor (PT) ou qtensor_jobs (NL/BE).**
