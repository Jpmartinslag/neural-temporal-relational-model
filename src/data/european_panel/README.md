# HERALD European Panel — Architecture

## Motivação

O HERALD foi calibrado para a França com fontes específicas (SIDE, URSSAF, FLORES). A
extensão a NL, BE e PT revelou um padrão de "remendo por país": cada país recebe colunas
renomeadas, flags forçados a zero e adaptações ad hoc no `prepare_phase4_panel.py`.

Este módulo substitui essa abordagem por um **contrato de dados canónico**: cada país
implementa um adapter que exporta sempre o mesmo schema. O HERALD core nunca vê diferenças
de fonte ou sistema regional — só vê o painel harmonizado.

```
Fontes nacionais     →  CountryAdapter  →  EuropeanPanel (schema.py)
Fontes Eurostat/ECB  →  EUSignalLoader  ↗
                                         ↓
                                      validation.py
                                         ↓
                                      HERALD core
```

---

## Estrutura de ficheiros

```
src/data/european_panel/
├── README.md            ← este ficheiro
├── schema.py            ← contrato canónico: FieldSpec, REQUIRED_FIELDS, …
├── validation.py        ← verificação pós-adapter: temporalidade, NaN, máscaras
├── adapters/
│   ├── __init__.py
│   ├── france_adapter.py    ← SIDE/A10/URSSAF para schema canónico
│   ├── nl_adapter.py        ← CBS COROP para schema canónico
│   ├── be_adapter.py        ← StatBel arrondissements para schema canónico
│   └── pt_adapter.py        ← INE/GEP NUTS3 para schema canónico
└── eu_signals/          (Phase 4E-C — INTEGRADO)
    ├── eurostat_client.py  ← cliente REST JSON-stat + cache em data/raw/
    ├── eurostat_gdp.py     ← nama_10_gdp (GDP growth real, nacional)
    ├── eurostat_lfs.py     ← lfsi_emp_a / une_rt_a (emprego/desemprego, nacional)
    ├── ec_bcs.py           ← ei_bssi_m_r2 (ESI, mensal→média anual)
    ├── ecb_bls.py          ← ECB BLS crédito PME, trimestral→média anual
    ├── assemble.py         ← overlay lag-1 + recálculo de mask_eu_signals
    └── fetch_all.py        ← CLI: baixa raws + escreve eu_signals_annual.csv
```

> STS turnover e EEI ficam NaN (documentado como blocked em
> `reports/HERALD_PHASE4E_MISSING_DATA_SEARCH.md`). ECB BLS foi integrado em
> 2026-06-02 como `eu_credit_standards_lag1`.

---

## Contrato de dados (`schema.py`)

**Estado actual do schema**:
- Campos catalogados em `FIELD_CATALOGUE`: **43**
- Colunas exportadas pelos adapters actuais: **43**
- Máscaras de observabilidade já exportadas:
  - `mask_target` — target observado
  - `mask_sector_a10` — cobertura sectorial A10 observada
  - `mask_employment` — 1=tensor de emprego genuíno, 0=ausente
  - `mask_tensor` — peso operacional do tensor; `0.5` indica proxy, `1.0` tensor genuíno
  - `mask_eu_signals` — proporção de `eu_*` não-NaN por linha
- **Phase 4E-C (2026-06-02):** 5 dos 7 sinais `eu_*` preenchidos via Eurostat/ECB
  (`eu_gdp_growth_lag1`, `eu_employment_rate_lag1`, `eu_unemployment_rate_lag1`,
  `eu_esi_lag1`, `eu_credit_standards_lag1`), nacional, lag-1 seguro.
  `mask_eu_signals` ≈ 0.65–0.71 nos anos cobertos (FR/NL/BE/PT). STS turnover
  e EEI continuam NaN. O overlay corre em `build_european_panel.py` após cada
  adapter; o core do modelo não foi alterado. Desactivar com `--no-eu-signals`.
- **Netherlands sector births update (2026-06-02):** CBS 83631NED foi integrado
  como `sector_*` por COROP × HERALD A10, com lag-1 aplicado no adapter NL.
  `mask_sector_a10=1.0` no painel NL.
- **Belgium tensor update (2026-06-02):** ONSS Q4 2021–2024 foi integrado no
  `belgium_qtensor_jobs_panel.csv`; o tensor BE passa a cobrir 2008–2024.
- **Portugal tensor update (2026-06-02):** `nama_10r_3empers` foi integrado como
  tensor regional de emprego por sector (`EMP`, NUTS3 × NACE, 2000–2023) e
  completado em 2024 com ARDECO SNETZ (`Employment by industry`, NUTS3, A10).
  O painel PT mantém sector births como `sector_*`, mas `mask_employment=1` e
  `mask_tensor=1` quando o tensor Eurostat/ARDECO está presente.
- **Portugal births extension 2023–2024 (2026-06-02):** o painel PT passou de
  2008–2022 para 2008–2024. Anos 2008–2022 usam os indicadores INE antigos
  (`0009702` births total, `0009703` births × CAE, `0009819` stock, NUTS 2013);
  anos 2023–2024 usam os novos indicadores INE NUTS 2024 (`0014098` births total,
  `0014099` births × CAE, `0014061` stock), remapeados para as 25 zonas HERALD
  históricas. Caso crítico: `PT_170` = soma de Grande Lisboa (`1A0`) + Península
  de Setúbal (`1B0`), preservando a Área Metropolitana de Lisboa antiga. Mapa em
  `src/data/ingest_portugal_panel_nuts3.py` (`NUTS2024_TO_HERALD_NUTS3`).

Campos obrigatórios em todos os adapters:

| Campo | Tipo | Papel |
|---|---|---|
| `country` | str | ISO 3166-1 alpha-2 |
| `region_id` | str | NUTS3-2021 ou ID nacional documentado |
| `region_name` | str | Rótulo legível |
| `region_level` | str | NUTS3 / COROP / arrondissement / ZE2020 / … |
| `year` | int | Ano alvo t |
| `node_idx` | int | Índice inteiro estável (0-based), coerente com adjacency |
| `target_births` | float | Nascimentos de empresas/estabelecimentos em t |
| `lag1_births` | float | target_births de t-1 |
| `growth_1y` | float | variação percentual causal: `(t-1 - t-2) / t-2` |
| `mask_target` | float | 1=observado, 0=ausente (escala a loss) |
| `flag_target_concept` | str | 'establishment_creation' / 'enterprise_birth' / … |
| `flag_is_covid_year` | int | 1 para 2020 |
| `flag_is_rebound_year` | int | 1 para 2021 |
| `flag_forecast_safe` | int | 1 se todos os lags necessários disponíveis |
| `meta_region_system` | str | Sistema regional usado |
| `meta_source_label` | str | SIDE / CBS / StatBel / INE-GEP / Eurostat-BD |

Campos opcionais relevantes: `lag2_births`, `lag3_births`, `growth_2y`, `stock_lag1`,
`sector_BE…RU` (A10), `eu_employment_rate_lag1`, `eu_esi_lag1`, `eu_credit_standards_lag1`,
`eu_gdp_growth_lag1`, `mask_sector_a10`, `mask_employment`, `mask_tensor`,
`mask_eu_signals`, `flag_has_national_employment`.

Ver `schema.py` para catálogo completo com `source_hint` por campo.

---

## Adapter — interface mínima

```python
class CountryAdapter:
    country: str = "XX"

    def build(self, year_min: int, year_max: int) -> pd.DataFrame:
        """
        Produzir painel no schema europeu canónico.
        Deve conter todos os REQUIRED_FIELDS.
        Campos opcionais ausentes devem estar como NaN (não omitidos).
        """
        ...

    def validate(self, df: pd.DataFrame) -> dict:
        from src.data.european_panel.validation import validate_panel
        return validate_panel(df, country=self.country)
```

---

## Regras metodológicas

### Causalidade temporal
- Nunca usar dado de ano t para prever t.
- `lag1_*` = valor em t-1; `eu_*_lag1` = média anual de t-1 publicada antes de t.
- `flag_forecast_safe=0` exclui a linha de treino e avaliação.
- Nowcast ≠ forecast. Não chamar previsão ex-ante de nowcast.

### Campos não preditivos (`NON_PREDICTIVE_FIELDS`)
Os campos `flag_is_covid_year` e `flag_is_rebound_year` são **metadata de auditoria**,
não features preditivas. Estão em `schema.NON_PREDICTIVE_FIELDS` e devem ser excluídos
de `x_ann`, `q_tensor`, regime vector e qualquer input de modelo.

Razão: codificam conhecimento explícito de datas específicas (2020, 2021), o que constitui
lookahead implícito em contextos de generalização temporal. O `train_herald_semi_v2.py`
(pipeline Phase 4) não os usa como features — esta regra formaliza e protege esse comportamento.

O antigo `train_dynamic_stgnn_models_v1.py` usava-os via `feature_columns()`. Esse trainer
não é usado nas baterias Phase 4D/4E e não deve ser referenciado para novos experimentos.

### Targets e comparabilidade
- `flag_target_concept` documenta o conceito exacto.
- Não comparar WMAPE entre países se os conceitos forem diferentes.
- Não imputar sector ausente como zero sem `mask_sector_a10`.
- **Estado Phase 4G/4H/4I (LOCO):** a equivalência semântica dos 4 targets (FR
  créations d'établissements, NL oprichtingen van vestigingen, BE primo-
  assujettissements TVA, PT entradas GEP) **ainda não está estabelecida
  documentalmente**. Gate 1 do próximo passo é uma auditoria semântica oficial
  obrigatória antes de qualquer comparação cross-country ou expansão. Ver
  `reports/HERALD_PHASE4_NEXT_STEP_INDEPENDENT_AUDIT.md`.

### Sinais macro
- Adicionar sinais `eu_*` um de cada vez, com ablação por país.
- Não adicionar 20 features macro de uma vez sem baseline limpo.
- Reportar quando uma feature ajuda apenas um país — não generalizar.

### Sinais europeus comuns
- Eurostat BD, LFS, STS, BCS/ESI, ECB BLS: cobertura comum FR/NL/BE/PT.
- BE ausente do Eurostat BD (confirmado empiricamente — `bd_hgnace_r` e `bd_size_r3`).
  Para BE: StatBel é fonte primária; Eurostat BD apenas para validação cruzada.
- ECB BLS: apenas membros da Zona Euro. FR/NL/BE/PT cobertos desde 2003.

### Grafos e tensores
- Grafos e tensores são **ablações secundárias**, não parte do contrato base.
- O contrato europeu define as features; grafos são configuração de treino.
- Phase 4D mostrou que grafos funcionais não superam identidade de forma robusta
  (perm control venceu em BE; margem NL/PT < σ).

---

## Phase 4E — plano experimental

Ver `reports/HERALD_EUROPEAN_PANEL_STANDARD_PLAN.md` para o plano completo.

Sequência de baterias:
1. `phase4e_baseline` — painel padronizado, sem sinais EU, sem embedding
2. `phase4e_country_embed` — + country embedding (16-dim, aprendido)
3. `phase4e_eu_signals` — + Eurostat/LFS/ESI/ECB-BLS por ablação
4. `phase4e_tensor_masks` — usar `mask_tensor`/`mask_employment` na loss e nas configs

Critérios de vitória:
- WMAPE melhora vs Phase 4E-A/A2 causal baseline em ≥2 países
- Nenhum país regride >1% vs seu baseline causal limpo
- França é analisada separadamente porque V6/V7 usa pipeline nacional distinto
- Estabilidade: σ_seed < 0.005
