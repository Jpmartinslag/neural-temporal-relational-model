# HERALD European Panel Standard — Plan

**Status**: Arquitectura implementada — adapters validados — Phase 4E-B estabelecida (baseline causal final por país)  
**Data**: 2026-05-31  
**Contexto**: Após Phase 4D (grafos funcionais, resultados marginais), mudança de direcção  
para padronização de dados em vez de complexificação de grafos.

> **Schema**: 43 campos catalogados, 43 exportados actualmente.
> `mask_target`, `mask_sector_a10`, `mask_employment`, `mask_tensor`
> e `mask_eu_signals` já existem no painel canónico.
>
> **Veredicto**: Schema europeu pronto para Phase 4E-A baseline padronizado.
> Ainda não pronto para claims de generalização completa.
> Phase 4E-B/C/D dependem de: excluir `NON_PREDICTIVE_FIELDS` dos inputs,
> carregar sinais EU, completar BE 2021–2024 e fazer o trainer consumir as máscaras
> quando houver tensor/loss parcial.

---

## 1. Diagnóstico: o estado actual é um remendo

### O que foi feito até Phase 4D

O HERALD foi construído para a França com fontes específicas:
- **Target**: SIDE / SIRENE (estabelecimentos, não empresas)
- **Emprego**: URSSAF (efectivos por sectore e zona de emprego)
- **Geometria**: ZE2020 (zonas de emprego, ~300 zonas, agregação coerente com mercado de trabalho)
- **Stock**: FLORES (stock de empresas activas)

Na extensão internacional (Phase 4, 4B, 4C, 4D), a abordagem foi:

> "Pegar nos dados de NL / BE / PT e forçá-los a parecer dados franceses."

Consequências concretas:
- Coluna `ZE2020` usada como identificador em todos os países — conceito francês exposto como ID universal
- `has_flores_source = 0`, `has_side_stock_source = 0`, `has_urssaf_source = 0` hardcoded — o modelo não sabe o que tem
- `side_establishment_creations_official` como nome de target — implica conceito administrativo francês
- Flags de COVID, rebound, `feature_forecast_safe` presentes mas sem validação formal
- Nenhum sinal europeu comum: Eurostat BD, LFS, ESI, ECB BLS ausentes
- Nenhum `country` explícito no painel — implícito no directório
- Sector A10 disponível mas sem máscara de cobertura sistematizada

### Resultado Phase 4D

Os grafos funcionais (commuting, sector similarity) não superaram o controlo de identidade de forma robusta:
- NL: melhor funcional (+1.4% regressão vs Phase 4A histórico ⚠️ leaky; -3.0% vs geo_4c)
- BE: perm control ganhou sobre todos os grafos reais (sem sinal espacial)
- PT: sector_top8 marginal (+0.3% vs 4A ⚠️ leaky, dentro do σ)

**Conclusão**: adicionar mais complexidade de grafo não é o caminho. O HERALD já captura
estrutura suficiente com identidade. O problema está na qualidade e homogeneidade dos dados.

---

## 2. Tese central

> O HERALD deve ter um núcleo comum europeu.  
> Cada país traduz os seus dados para um contrato europeu comum.  
> A generalização vem de padronização, coverage-aware learning e adapters por país —  
> não de remendos específicos por país.

**Contrato de dados, não remendo de modelo.**

---

## 3. Arquitectura proposta

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Fontes de dados                              │
│                                                                     │
│  França: SIDE, URSSAF, FLORES, SIRENE                               │
│  NL: CBS (COROP), Eurostat BD, LFS                                  │
│  BE: StatBel (arrondissements), Eurostat LFS, ECB BLS               │
│  PT: INE-GEP (Quadros de Pessoal), INE (NUTS3)                      │
│  Todos: Eurostat BD, LFS, STS, BCS/ESI, ECB BLS, GDP               │
└───────────┬─────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     Country Adapters                                │
│                                                                     │
│  FranceAdapter  →  painel canónico FR  ─┐                          │
│  NLAdapter      →  painel canónico NL  ─┤                          │
│  BEAdapter      →  painel canónico BE  ─┤→ EuropeanPanel (schema)  │
│  PTAdapter      →  painel canónico PT  ─┘                          │
│                                                                     │
│  + EUSignalLoader  →  sinais Eurostat/ECB comuns                    │
└───────────┬─────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Validation Layer                               │
│  - Campos obrigatórios presentes                                    │
│  - Continuidade temporal                                            │
│  - Integridade causal (lag1 = t-1)                                  │
│  - mask_target coerente com NaN                                     │
│  - flag_forecast_safe consistente                                   │
│  - Relatório de cobertura por campo                                 │
└───────────┬─────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       HERALD Core (frozen)                          │
│                                                                     │
│  Ridge AR + spatial GNN (V6/V7 architecture)                        │
│  + country_embedding (16-dim, opcional)                             │
│  + coverage-aware loss (mask_target)                                │
│  + tensor/grafo configurável por país (ablação secundária)          │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 4. Contrato de dados — campos canónicos

Ver `src/data/european_panel/schema.py` para especificação completa com `FieldSpec`.

### Obrigatórios (todos os adapters)

| Campo | Descrição |
|---|---|
| `country` | ISO 3166-1 alpha-2 |
| `region_id` | NUTS3-2021 ou ID nacional documentado |
| `region_name` | Rótulo legível (língua original) |
| `region_level` | NUTS3 / COROP / arrondissement / ZE2020 / … |
| `year` | Ano alvo t |
| `node_idx` | Índice inteiro estável (0-based) |
| `target_births` | Nascimentos em t (conceito documentado em `flag_target_concept`) |
| `lag1_births` | target_births em t-1 |
| `growth_1y` | log(t-1 / t-2) |
| `mask_target` | 1=observado, 0=ausente |
| `flag_target_concept` | 'establishment_creation' / 'enterprise_birth' / … |
| `flag_is_covid_year` | 1 para 2020 |
| `flag_is_rebound_year` | 1 para 2021 |
| `flag_forecast_safe` | 1 se todos os lags disponíveis sem lookahead |
| `meta_region_system` | Sistema regional usado |
| `meta_source_label` | SIDE / CBS / StatBel / INE-GEP / Eurostat-BD |

### Opcionais relevantes

| Campo | Origem típica |
|---|---|
| `lag2_births`, `lag3_births` | Derivado |
| `growth_2y` | Derivado |
| `stock_lag1` | Eurostat BD / nacional |
| `sector_BE … sector_RU` | Eurostat BD / nacional (A10 mapping) |
| `eu_employment_rate_lag1` | Eurostat LFS (lfst_r_lfe2emprt) |
| `eu_unemployment_rate_lag1` | Eurostat LFS (lfst_r_lfu3rt) |
| `eu_sts_turnover_lag1` | Eurostat STS (sts_trtu_a) |
| `eu_esi_lag1` | EC Business & Consumer Surveys |
| `eu_eei_lag1` | EC Business & Consumer Surveys |
| `eu_credit_standards_lag1` | ECB Bank Lending Survey |
| `eu_gdp_growth_lag1` | Eurostat nama_10_gdp |
| `mask_sector_a10` | Fracção de sectores A10 observados (0–1) |
| `mask_employment` | 1=tensor de emprego genuíno disponível, 0=ausente |
| `mask_tensor` | Peso operacional do tensor; 1=tensor genuíno, 0.5=proxy documentado, 0=desligado |
| `mask_eu_signals` | Fracção de sinais `eu_*` disponíveis na linha |
| `flag_has_national_employment` | 1 se tensor de emprego disponível |
| `flag_has_eurostat_bd` | 1 se Eurostat BD é fonte primária |

---

## 5. Fontes europeias comuns — auditoria de cobertura

### 5.1 Eurostat Business Demography (BD)

| Atributo | Detalhe |
|---|---|
| **Indicador** | `bd_hgnace_r` (births/deaths/active por actividade e região) |
| **Cobertura países** | FR ✓, NL ✓, PT ✓, **BE ✗** (não reporta) |
| **Nível regional** | NUTS2 (births por NACE A10 + NUTS2), nacional para stock |
| **Anos** | 2019–2023 (download actual) |
| **Lag publicação** | ~18–24 meses (2022 publicado em finais 2024) |
| **Causalidade** | Usável como target ou validação; não como feature lag-1 de t |
| **Campos contrato** | `target_births` (validação), `stock_lag1`, `sector_*` |
| **Bloqueio BE** | BE ausente — usar StatBel como fonte primária para BE |

### 5.2 Eurostat Labour Force Survey (LFS)

| Atributo | Detalhe |
|---|---|
| **Indicador** | `lfst_r_lfe2emprt` (emprego), `lfst_r_lfu3rt` (desemprego) |
| **Cobertura países** | FR ✓, NL ✓, BE ✓, PT ✓ |
| **Nível regional** | NUTS2 (emprego) e NUTS3 experimental (anos recentes) |
| **Anos** | 2003–2023 |
| **Lag publicação** | ~6 meses (2023 publicado Q2 2024) |
| **Causalidade** | `eu_employment_rate_lag1` = LFS de t-1, disponível no início de t |
| **Campos contrato** | `eu_employment_rate_lag1`, `eu_unemployment_rate_lag1` |
| **Nota** | LFS NUTS3 tem erros padrão elevados para países pequenos |

### 5.3 Eurostat Short-Term Business Statistics (STS)

| Atributo | Detalhe |
|---|---|
| **Indicador** | `sts_trtu_a` (turnover anual, sectores B–N) |
| **Cobertura países** | FR ✓, NL ✓, BE ✓, PT ✓ |
| **Nível regional** | Nacional apenas |
| **Anos** | 2000–2023 |
| **Lag publicação** | ~3–4 meses (publicação mensal; anual = média) |
| **Causalidade** | Turnover de t-1 disponível em Q1 de t |
| **Campos contrato** | `eu_sts_turnover_lag1` |
| **Nota** | Mede actividade de empresas existentes, não nascimentos |

### 5.4 Business and Consumer Surveys — ESI / EEI

| Atributo | Detalhe |
|---|---|
| **Indicador** | ESI (Economic Sentiment), EEI (Employment Expectations) |
| **Cobertura países** | FR ✓, NL ✓, BE ✓, PT ✓ + toda a EU |
| **Nível regional** | Nacional (mensal) |
| **Anos** | 1985–presente |
| **Lag publicação** | Zero (publicação no último dia útil do mês) |
| **Causalidade** | Média anual de t-1 disponível no início de t ✓ |
| **Campos contrato** | `eu_esi_lag1`, `eu_eei_lag1` |
| **Fonte** | Eurostat + EC DG ECFIN (CSV download directo) |
| **Hipótese** | ESI baixo em t-1 → menos nascimentos em t (expectativas negativas) |

### 5.5 ECB Bank Lending Survey (BLS)

| Atributo | Detalhe |
|---|---|
| **Indicador** | Net % de bancos a apertar critérios de crédito para PME |
| **Cobertura países** | FR ✓, NL ✓, BE ✓, PT ✓ (membros da Zona Euro) |
| **Nível regional** | Nacional |
| **Anos** | 2003–presente (trimestral) |
| **Lag publicação** | ~1 mês após trimestre |
| **Causalidade** | Média anual de t-1 disponível no início de t ✓ |
| **Campos contrato** | `eu_credit_standards_lag1` |
| **Hipótese** | Aperto de crédito em t-1 → redução de nascimentos em t (financiamento escasso) |
| **Nota** | Só Zona Euro — não extensível a países não-euro sem alternativa |

### 5.6 Eurostat GDP (nama_10_gdp)

| Atributo | Detalhe |
|---|---|
| **Indicador** | Taxa de crescimento real do PIB, nacional |
| **Cobertura países** | Toda a EU |
| **Nível regional** | Nacional (NUTS0) |
| **Anos** | 1975–2023 |
| **Lag publicação** | ~3 meses (flash) + revisão ~12 meses |
| **Causalidade** | Flash de t-1 disponível em Q1 de t ✓ |
| **Campos contrato** | `eu_gdp_growth_lag1` |
| **Nota** | Alta qualidade, alta correlação cross-country — usar com cuidado (colinearidade) |

---

## 6. Regras metodológicas (não negociáveis)

### Temporalidade e causalidade
1. **Nunca usar dado de t para prever t.** Features são sempre t-1 ou anteriores.
2. **Lag publication matters.** ESI e BLS são seguros (publicação antes de t). Eurostat BD não é seguro como feature (publicado 18–24 meses depois).
3. **Nowcast ≠ forecast.** Se qualquer feature de t for usada, é nowcast, não previsão. Documentar explicitamente.
4. **flag_forecast_safe=0** exclui a linha de treino e avaliação, sem excepção.

### Máscaras e imputação
5. **Não imputar sector ausente como zero.** Usar `mask_sector_a10` para escalar a contribuição do loss sectorial.
6. **mask_target=0** garante que a loss não penaliza NaN estrutural. Não imputar target ausente.
7. **mask_employment** gradua a confiança no sinal de emprego (NUTS3 > NUTS2 > nacional).

### Comparabilidade cross-country
8. **flag_target_concept** deve ser o mesmo ou comparabilidade deve ser declarada impossível.
9. **WMAPE cross-country só é válido se os conceitos forem comparáveis.** Caso contrário, reportar separadamente.
10. **Não generalizar uma feature que só ajuda um país.** Reportar explicitamente "ajuda NL, neutro BE, prejudica PT".

### Adição de features
11. **Uma feature de cada vez.** Ablação clara: baseline → +feature → diff.
12. **Não adicionar sinais macro em massa.** Máximo 2 sinais novos por bateria.
13. **Reportar quando feature ajuda só um país.** Não amalgamar resultados multi-país.

### Arquitectura
14. **Não alterar HERALD core durante Phase 4E.** Apenas o painel muda.
15. **Country embedding é opcional.** Testar como ablação, não como default.
16. **Grafos são ablação secundária.** Phase 4D mostrou que grafos funcionais não superam identidade de forma robusta. Não priorizar.

---

## 7. Estrutura de código — adapters

### Interface mínima de um adapter

```python
# src/data/european_panel/adapters/nl_adapter.py

import pandas as pd
from src.data.european_panel.schema import REQUIRED_FIELDS, empty_panel
from src.data.european_panel.validation import validate_panel, print_report


class NLAdapter:
    country = "NL"
    region_level = "COROP"
    meta_region_system = "COROP"
    meta_source_label = "CBS"
    flag_target_concept = "enterprise_birth"

    def __init__(self, data_root: str = "data/external/netherlands"):
        self.data_root = Path(data_root)

    def build(self, year_min: int = 2015, year_max: int = 2024) -> pd.DataFrame:
        # 1. Ler dados nacionais (CBS COROP births)
        # 2. Ler sinais Eurostat comuns (LFS, STS, ESI, BLS) e fazer join por ano
        # 3. Calcular lags e crescimentos
        # 4. Preencher masks e flags
        # 5. Renomear para schema canónico
        # 6. Garantir que OPTIONAL_FIELDS ausentes aparecem como NaN
        ...

    def validate(self, df: pd.DataFrame) -> dict:
        return validate_panel(df, country=self.country,
                              expected_years=range(year_min, year_max + 1))
```

### Mapeamento de colunas Phase 4 → schema canónico

| Phase 4 (actual) | Schema canónico | Notas |
|---|---|---|
| `ZE2020` | `region_id` + `meta_region_system` | ZE2020 é sistema francês; outros usam COROP/arr/NUTS3 |
| `target_year` | `year` | Renomear |
| `node_idx` | `node_idx` | Manter |
| `side_establishment_creations_official` | `target_births` | Renomear; documentar conceito em `flag_target_concept` |
| `side_lag_1` | `lag1_births` | Renomear |
| `side_lag_2` | `lag2_births` | Renomear |
| `side_lag_3` | `lag3_births` | Renomear |
| `growth_1y` | `growth_1y` | Manter |
| `growth_2y` | `growth_2y` | Manter |
| `side_stock_total_t_minus_1` | `stock_lag1` | Renomear |
| `has_flores_source` | `flag_has_national_employment` | Semântica diferente — rever |
| `feature_forecast_safe` | `flag_forecast_safe` | Renomear |
| `is_covid_year` | `flag_is_covid_year` | Renomear |
| `is_post_covid_rebound` | `flag_is_rebound_year` | Renomear |
| (ausente) | `country` | Adicionar |
| (ausente) | `region_name` | Adicionar |
| (ausente) | `region_level` | Adicionar |
| (ausente) | `mask_target` | Adicionar (1 onde target não é NaN) |
| (ausente) | `flag_target_concept` | Adicionar por adapter |
| (ausente) | `meta_source_label` | Adicionar por adapter |
| (ausente) | `eu_*` | Adicionar via EUSignalLoader |

---

## 8. Phase 4E — design experimental

### Objectivo

Testar se o painel padronizado com sinais europeus comuns melhora a generalização do HERALD
em NL, BE e PT sem regredir em França.

### Baterias propostas

#### 4E-A: Baseline padronizado (sanity check)
- Painel canónico por país, sem sinais EU, sem country embedding
- Mesmo contrato de dados, só com campos obrigatórios + sector A10
- ~~Comparar com Phase 4A: deve reproduzir resultados~~ → **OBSOLETO**: Phase 4A leaky em `growth_1y`; comparar com Phase 4E-A como novo baseline limpo
- **Concluído: 10 seeds por país** — resultados: FR 0.117±0.004, NL 0.104±0.008, BE 0.155±0.008, PT 0.247±0.014

#### 4E-B: Feature-policy ablation ✅ CONCLUÍDA (2026-06-03)
- Ablação de políticas de features no painel europeu causal: b0–b3 para todos os países, b4–b5 para PT
- **10 seeds, 4 configs FR/NL/BE + 6 configs PT = 180 runs**
- Vencedores por país: FR `b2_side2_zero` (0.1031), NL `b0_baseline_annual` (0.1017), BE `b3_current_clean_zero` (0.1488), PT `b5_side2_emp_lag1` (0.2286)
- **Phase 4E-B = baseline causal final por país. Phase 4E-C deve comparar contra estes vencedores.**
- Ver `reports/HERALD_PHASE4E_B_RESULTS_AUDIT.md` e `reports/HERALD_PHASE4E_B_FEATURE_POLICY_PLAN.md`

#### 4E-C: EU signals — ciclo económico ⬅ PRÓXIMA FASE
- Baselines por país: FR `b2_side2_zero`, NL `b0_baseline_annual`, BE `b3_current_clean_zero`, PT `b5_side2_emp_lag1`
- Sinais candidatos: `eu_gdp_growth_lag1`, `eu_unemployment_rate_lag1`, `eu_employment_rate_lag1`, `eu_esi_lag1`
- Ablações:
  - C0: winner 4E-B (baseline)
  - C1: + `eu_gdp_growth_lag1`
  - C2: + `eu_unemployment_rate_lag1` + `eu_employment_rate_lag1`
  - C3: + `eu_esi_lag1`
  - C4: + todos os sinais EU
  - C5: sinais permutados / falsificação
- Critério de vitória: sinal real bate baseline 4E-B; controle permutado não piora >1%; melhoria consistente em ≥2 países
- Ver `reports/HERALD_PHASE4E_C_EU_SIGNALS_PLAN.md`

#### 4E-D: EU signals — emprego e crédito
- Adicionar `eu_employment_rate_lag1` e `eu_credit_standards_lag1`
- Só Zona Euro para crédito (FR/NL/BE/PT todos elegíveis)
- **20 seeds, 4 configs**

### Critérios de sucesso Phase 4E

> **⚠️ ATENÇÃO (2026-06-03): Phase 4A/4D afectadas por leakage em `growth_1y`.**
> Os WMAPEs Phase 4A/4D não devem ser usados como threshold de comparação científica.
> Baseline causal estabelecido: **Phase 4E-B** por país — FR 0.1031, NL 0.1017, BE 0.1488, PT 0.2286. Phase 4E-A/A2 são intermediários históricos.
> Ver `reports/HERALD_PHASE4E_A2_DEGRADATION_AUDIT.md`.

| Critério | Threshold |
|---|---|
| WMAPE melhora vs Phase 4E-B (por país) | ≥1 país com melhoria ≥1% |
| Nenhum país regride vs Phase 4E-B (por país) | <1% regressão vs Phase 4E-B winner |
| França não regride | <0.5% regressão vs V6/V7 baseline |
| Estabilidade de seed | σ_seed < 0.008 por país |
| Feature ajuda ≥2 países | Para ser considerada "europeia" |
| ~~WMAPE melhora vs Phase 4A~~ | ~~≥1 país com melhoria ≥1%~~ — **OBSOLETO: Phase 4A leaky** |

### O que NÃO fazer em Phase 4E
- Não alterar `train_herald_v7.py` ou `train_herald_semi_v2.py`
- Não adicionar grafos complexos (Phase 4D já testou)
- Não adicionar >2 features macro por bateria
- Não fazer tuning de hiperparâmetros por país
- Não comparar WMAPE cross-country se conceitos de target forem diferentes
- Não fazer push automático de resultados
- Não apagar outputs de Phase 4A/4C/4D
- **Não incluir `flag_is_covid_year` ou `flag_is_rebound_year` em nenhum input de modelo.**
  Usar `schema.NON_PREDICTIVE_FIELDS` para filtrar antes de montar `x_ann`.
- Não comparar resultados BE com NL/PT sem explicitar a janela de dados usada.
- Não misturar Phase 4D PT com Phase 4E PT: Phase 4D usou births proxy; Phase 4E tem tensor Eurostat de emprego.

---

## 9. Estado actual por país

| País | Zonas | Anos | Target concept | Emp. tensor | Eurostat BD | LFS | BLS |
|---|---|---|---|---|---|---|---|
| **FR** | ~285 ZE2020 | 2008–2024 | establishment_creation | URSSAF ✓ | ✓ (validação) | ✓ | ✓ |
| **NL** | 40 COROP | 2015–2025 | enterprise_birth (CBS) | CBS ✓ | ✓ | ✓ | ✓ |
| **BE** | 42 arr. | 2007–2024 | enterprise_birth (StatBel) | StatBel ✓ | ✗ (ausente) | ✓ | ✓ |
| **PT** | 25 NUTS3 | 2008–2024 | enterprise_birth (INE-GEP) | Eurostat employment ✓ | ✓ | ✓ | ✓ |

**Notas**:
- BE ausente do Eurostat BD: confirmado empiricamente (Phase 4D data audit)
- PT tensor: Phase 4E usa Eurostat `nama_10r_3empers` (`EMP`, NUTS3 × NACE, 2000–2023)
  completado por ARDECO SNETZ 2024; Phase 4D antigo usou proxy de births por CAE.
- Conceitos de target não são directamente comparáveis cross-country sem ajuste

---

## 10. Entregáveis

### Criados neste plano
- [x] `src/data/european_panel/schema.py` — contrato canónico com FieldSpec
- [x] `src/data/european_panel/validation.py` — 11 checks de qualidade
- [x] `src/data/european_panel/README.md` — arquitectura e regras
- [x] `src/data/european_panel/adapters/__init__.py` — scaffold

### A criar em Phase 4E
- [ ] `src/data/european_panel/adapters/france_adapter.py`
- [ ] `src/data/european_panel/adapters/nl_adapter.py`
- [ ] `src/data/european_panel/adapters/be_adapter.py`
- [ ] `src/data/european_panel/adapters/pt_adapter.py`
- [ ] `src/data/european_panel/eu_signals/eurostat_lfs.py`
- [ ] `src/data/european_panel/eu_signals/eurostat_sts.py`
- [ ] `src/data/european_panel/eu_signals/ec_bcs.py`
- [ ] `src/data/european_panel/eu_signals/ecb_bls.py`
- [ ] `hpc/phase4e/` — configs, sbatch, submit scripts
- [ ] `reports/dashboards/herald_phase4e_*.html`

---

## 11. Referências de dados

- Eurostat Business Demography: https://ec.europa.eu/eurostat/web/business-demography
- Eurostat BD metadata (bd_sims): https://ec.europa.eu/eurostat/cache/metadata/en/bd_sims.htm
- Eurostat Labour Force Survey: https://ec.europa.eu/eurostat/web/lfs/information-data
- Eurostat STS: https://ec.europa.eu/eurostat/cache/metadata/en/sts_esms.htm
- Eurostat Business/Consumer Surveys: https://ec.europa.eu/eurostat/web/euro-indicators/information-data/business-consumer-surveys
- ECB Bank Lending Survey: https://www.ecb.europa.eu/stats/ecb_surveys/bank_lending_survey/html/index.hr.html
- Eurostat NUTS 2021 correspondence: https://ec.europa.eu/eurostat/web/nuts/correspondence-tables

---

## 12. Status update — Phase 4E-C data fill (2026-06-01)

Detalhe completo: `reports/HERALD_PHASE4E_MISSING_DATA_SEARCH.md`.

**Sinais EU comuns — INTEGRADO (5/7), nacional, lag-1 seguro:**

| campo | dataset Eurostat | status |
|---|---|---|
| `eu_gdp_growth_lag1` | `nama_10_gdp` (B1GQ, CLV_PCH_PRE) | ✅ usable |
| `eu_unemployment_rate_lag1` | `une_rt_a` (Y15-74, PC_ACT) | ✅ usable |
| `eu_employment_rate_lag1` | `lfsi_emp_a` (EMP_LFS, Y20-64) | ✅ usable |
| `eu_esi_lag1` | `ei_bssi_m_r2` (BS-ESI-I, média anual) | ✅ usable |
| `eu_sts_turnover_lag1` | `sts_trtu_a` (só comércio) | ⛔ blocked (conceito incompatível) |
| `eu_eei_lag1` | DG ECFIN BCS | ⛔ blocked (sem série país/ano limpa) |
| `eu_credit_standards_lag1` | ECB BLS | ✅ usable |

`mask_eu_signals` ≈ 0.65–0.71 nos anos cobertos (FR/NL/BE/PT) — antes 0.0.
Loaders em `src/data/european_panel/eu_signals/`; overlay em
`build_european_panel.py` (não altera adapters nem o core). Raws cacheados em
`data/raw/european_panel/`.

**Itens de dados agora resolvidos:**
- **BE tensor ONSS 2021–2024**: integrado; tensor BE cobre 2008–2024.
- **NL sector A10**: integrado via CBS 83631NED; `mask_sector_a10=1`.
- **PT employment tensor 2024**: integrado via ARDECO SNETZ 2024.
- **PT target births/stock 2023–2024**: integrado via indicadores INE NUTS-2024
  `0014098`, `0014099`, `0014061`, com mapeamento de volta para as 25 zonas HERALD.
