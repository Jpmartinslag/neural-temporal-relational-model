# HERALD Phase 4E-C — EU Macro Signals Plan

**Status**: CONCLUÍDA — 2026-06-03/04 (Jobs 7426150–7426153)  
**Depende de**: Phase 4E-B ✅ CONCLUÍDA (2026-06-03)  
**Referência**: `reports/HERALD_EUROPEAN_PANEL_STANDARD_PLAN.md` §8

---

## Objetivo

Testar se sinais macroeconómicos europeus comuns melhoram as previsões de nascimento de empresas
em cima dos vencedores estabelecidos pela Phase 4E-B.

A hipótese é que o ciclo macro europeu (crescimento do PIB, mercado de trabalho, expectativas)
captura variação temporal não explicada pelas features locais.

---

## Baselines por país (Phase 4E-B)

| País | Config vencedora | WMAPE mean ± std |
|------|-----------------|-----------------|
| FR | `b2_side2_zero` | 0.1031 ± 0.0084 |
| NL | `b0_baseline_annual` | 0.1017 ± 0.0075 |
| BE | `b3_current_clean_zero` | 0.1488 ± 0.0063 |
| PT | `b5_side2_emp_lag1` | 0.2286 ± 0.0148 |

Phase 4A/4D não são baselines científicos — afectados por leakage temporal em `growth_1y`.
Ver `reports/HERALD_PHASE4E_A2_DEGRADATION_AUDIT.md`.

---

## Sinais candidatos

| Campo | Fonte | Disponibilidade |
|-------|-------|----------------|
| `eu_gdp_growth_lag1` | Eurostat `nama_10_gdp` (B1GQ, CLV_PCH_PRE) | ✅ usável |
| `eu_unemployment_rate_lag1` | Eurostat `une_rt_a` (Y15-74, PC_ACT) | ✅ usável |
| `eu_employment_rate_lag1` | Eurostat LFS (`lfst_r_lfu3rt`) | ✅ usável |
| `eu_esi_lag1` | EC Business & Consumer Surveys (`ei_bssi_m_r2`) | ✅ usável |

Todos os sinais usam lag t-1 para garantir causalidade — valor do ano anterior ao alvo.

---

## Design de ablação

| Config | Descrição |
|--------|-----------|
| **C0** | Winner 4E-B por país (baseline de referência) |
| **C1** | C0 + `eu_gdp_growth_lag1` |
| **C2** | C0 + `eu_unemployment_rate_lag1` + `eu_employment_rate_lag1` |
| **C3** | C0 + `eu_esi_lag1` |
| **C4** | C0 + todos os sinais EU (GDP + labor + ESI) |
| **C5** | C0 + sinais EU permutados (falsificação — controle nulo) |

**C5 é obrigatório.** Se sinais permutados ajudam tanto quanto os reais, o ganho é artefacto
(e.g., regularização implícita por mais features, não sinal económico).

---

## Critérios de vitória

| Critério | Threshold |
|----------|-----------|
| Sinal real bate baseline C0 | WMAPE menor em ≥1 país com Δ ≥ 1% |
| Controle permutado (C5) não melhora | Δ vs C0 < +1% em todos os países |
| Melhoria consistente | ≥2 países com Δ positivo para o mesmo sinal |
| Nenhum país regride | Δ vs C0 < +1% em qualquer país |

Se apenas 1 país melhora e os restantes degradam, o sinal é candidato a feature condicional
(regime macro nacional), não a feature europeia universal.

---

## Aviso sobre interpretação

Sinais macroeconómicos europeus são nacionais repetidos por região — cada região do país
recebe o mesmo valor agregado. Podem capturar regime macro temporal, mas **não são evidência
de heterogeneidade espacial local**. Um modelo que melhora com `eu_gdp_growth_lag1` aprendeu
a diferenciar anos bons de maus, não a diferenciar zonas.

---

## O que NÃO fazer

- Não comparar Phase 4E-C contra Phase 4A/4D (leakage-affected)
- Não comparar Phase 4E-C contra Phase 4E-A/A2 (intermediários históricos)
- Não adicionar >4 sinais EU numa única ablação
- Não fazer tuning de hiperparâmetros por país durante 4E-C
- Não incluir `flag_is_covid_year` ou `flag_is_rebound_year` em nenhum input

---

## Estado de implementação (2026-06-03)

**Scripts HPC prontos e smoke validado:**

| Ficheiro | Estado |
|----------|--------|
| `hpc/phase4/phase4e_c_configs.sh` | ✅ criado |
| `hpc/phase4/run_herald_phase4e_c_seed.sh` | ✅ criado |
| `hpc/phase4/run_herald_phase4e_c_array.sbatch` | ✅ criado |
| `hpc/phase4/smoke_test_phase4e_c.sh` | ✅ criado |
| `hpc/phase4/submit_herald_phase4e_c.sh` | ✅ criado |
| `hpc/phase4/audit_phase4e_c_results.py` | ✅ criado |
| `src/modeles/train_herald_regime_experiment.py` | ✅ EU sets adicionados + permutação |

**Sinais EU confirmados nos painéis** (0% NaN para GDP/ESI; 12–17% NaN para labor em BE/PT — anos antigos):

| Sinal | FR | NL | BE | PT |
|-------|----|----|----|----|
| `eu_gdp_growth_lag1` | ✅ | ✅ | ✅ | ✅ |
| `eu_esi_lag1` | ✅ | ✅ | ✅ | ✅ |
| `eu_unemployment_rate_lag1` | ✅ | ✅ | ⚠️ 17% NaN | ⚠️ 12% NaN |
| `eu_employment_rate_lag1` | ✅ | ✅ | ⚠️ 17% NaN | ⚠️ 12% NaN |

**Smoke local**: PASS=4 FAIL=0 (EPOCHS=1, CPU, seed=42)  
**Metadata validada**: `phase=4E-C`, `macro_feature_set` gravado, `is_falsification_test=True` para C5.  
**Permutação C5**: shuffle temporal in-place com `np.random.default_rng(seed + 99991)`.

## Nota operacional HPC — constraint `mpi`

`run_herald_phase4e_c_array.sbatch` usa `#SBATCH --constraint="mpi"` para evitar nós `nompi`
afetados pelo incidente HPC2 (nós H100 simatlabgpu02, igredgpu01, hpcgpu02, hpcgpu03 e
pascalgpu01 A100 com problema MPI/log). Decisão operacional, não metodológica — não afeta
resultados científicos.

## Resultados (2026-06-04)

**Completude**: 240/240 runs (60 por país). Zero erros.  
**Audit**: `reports/HERALD_PHASE4E_C_RESULTS_AUDIT.md`

### Vencedores por país e decisão de baseline

| País | Melhor config 4E-C | Δc0 | C5 permutado | Decisão |
|------|--------------------|-----|--------------|---------|
| FR | c2_labor | -0.0049 | +0.0075 (pior que c0) | **4E-B permanece baseline** — melhora <1%, sinal EU não justificado |
| NL | c2_labor | -0.0033 | +0.0133 (pior que c0) | **4E-B permanece baseline** — melhora <1%, sinal EU não justificado |
| BE | c4_all_eu | -0.0110 | -0.0048 (pior que c4) | **c4_all_eu candidato promovível** — bate c0 >1%, C5 não acompanha, ganho credível |
| PT | c1_gdp | -0.0428 | -0.0174 (também bate c0 >1%) | **Bloqueado por C5** — C5 permutado supera c0 >1%, ganho pode ser artefato de regularização |

### Interpretação dos sinais EU

- **GDP (c1)**: só ajuda PT (−4.3pp); degrada FR+NL fortemente. Não universal.
- **Labor (c2)**: melhora marginal consistente nos 4 países (<0.5pp cada), nunca cruza limiar >1%. Sinal mais estável mas fraco.
- **ESI (c3)**: ajuda FR e BE marginalmente; degrada NL. Não consistente.
- **All EU (c4)**: CONSISTENT (≥2 países) mas polarizado — BE+PT melhoram, FR+NL degradam. Regime macro diferente entre países ricos em dados vs. escassos.
- **C5 permutado**: falhou o controle em PT (bate c0 >1%). Sugere que PT beneficia de regularização implícita com mais features, não de sinal económico real.

### Próximos passos por país

| País | Ação |
|------|------|
| FR | Encerrar 4E-C. Baseline = b2_side2_zero (4E-B). |
| NL | Encerrar 4E-C. Baseline = b0_baseline_annual (4E-B). |
| BE | Promover c4_all_eu condicionalmente. Precisa ablação isolada antes de claim publicável. |
| PT | Não promover ainda. Investigar efeito regularização antes de nova bateria. |

---

## Para lançar no HPC

```bash
# 1. rsync para o HPC
rsync -av hpc/phase4/ meso:~/project_recomm_herald_v6_2025_20260430/dataset/hpc/phase4/
rsync -av src/modeles/ meso:~/project_recomm_herald_v6_2025_20260430/dataset/src/modeles/
rsync -av data/processed/phase4e/ meso:~/project_recomm_herald_v6_2025_20260430/dataset/data/processed/phase4e/

# 2. Verificar no HPC
ssh meso
cd ~/project_recomm_herald_v6_2025_20260430/dataset
source ~/venvs/herald-v5-env.sh
bash -n hpc/phase4/phase4e_c_configs.sh hpc/phase4/run_herald_phase4e_c_seed.sh hpc/phase4/run_herald_phase4e_c_array.sbatch
python3 -m py_compile hpc/phase4/audit_phase4e_c_results.py

# 3. Smoke remoto (antes de submeter)
EPOCHS=1 DEVICE=cpu bash hpc/phase4/smoke_test_phase4e_c.sh

# 4. Submit (só com autorização explícita)
bash hpc/phase4/submit_herald_phase4e_c.sh
```

**Auditoria pós-run:**
```bash
python3 hpc/phase4/audit_phase4e_c_results.py \
  --root-fr hpc_results/herald_phase4e_c_fr_<STAMP>_r1 \
  --root-nl hpc_results/herald_phase4e_c_nl_<STAMP>_r1 \
  --root-be hpc_results/herald_phase4e_c_be_<STAMP>_r1 \
  --root-pt hpc_results/herald_phase4e_c_pt_<STAMP>_r1
```
