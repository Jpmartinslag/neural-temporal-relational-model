# Dashboard HERALD — O que falta fazer

Data: 2026-05-18

## Em andamento agora

| Item | Estado | Detalhe |
|---|---|---|
| Phase 2J — comparação justa flags vs no flags | **em treino** | Job SLURM 7344087 · 20 runs (2 configs × 10 seeds) |

Quando o job terminar:
```bash
# 1. Recuperar do HPC
rsync -av meso-direct:~/project_recomm_herald_v6_2025_20260430/dataset/hpc_results/herald_regime_phase2j_fair_flag_20260518_170504_r1/ \
  hpc_results/herald_regime_phase2j_fair_flag_20260518_170504_r1/

# 2. Agregar
python3 hpc/regime/aggregate_herald_regime_results.py \
  --root hpc_results/herald_regime_phase2j_fair_flag_20260518_170504_r1

# 3. Regenerar o dashboard (vai detectar a pasta Phase 2J automaticamente)
python3 src/visualisation/generate_herald_semi_v2_dashboard.py
```

O dashboard vai substituir automaticamente "en attente" pelo WMAPE 2021 real do `lag1_growth1y_flags`.

---

## Para fazer amanhã

### Previsão prospectiva 2026/2027

O pipeline de forecast já existe em `hpc/forecast/`. A previsão condicional às dados disponíveis em
2026-05-07 precisa de ser apresentada ao cliente como o resultado operacional do HERALD.

```bash
# Ver scripts existentes
ls hpc/forecast/
```

Adicionar ao dashboard:
- Secção "7. Prévision 2026/2027" com mapa de previsão por zona
- Nota metodológica: previsão condicional, não ex-ante

---

## Dados em falta no dashboard atual

### HERALD flags clean (comparação justa)
- **Problema**: o "HERALD flags" exibido vem da Phase 2E (`ctrl_manual`) com TODAS as features
  (flores, side_stock, URSSAF, source flags) — não é comparável ao no flags (só SIDE2)
- **Fix**: Phase 2J (job 7344087) vai produzir `lag1_growth1y_flags` com mesmas entradas
- **Impacto**: conclusão "no flags bate flags" está suspensa até Phase 2J terminar

### KPI Gain HERALD vs Ridge
- **Estado actual**: 63.8% ✅ (corrigido — era 61.5% com valor Ridge errado)
- **Ridge AR 2025**: 0.036085 ✅ (strict exante no_source_flags)

### DCRNN e STGNN 2025
- **Estado actual**: preenchido ✅ (0.031156 e 0.031134 — strict exante no_source_flags)
- **Nota**: estes valores não têm separação por seed (determinísticos)

---

## Melhorias de dashboard desejadas (prioridade média)

| Item | Descrição |
|---|---|
| Tabela de comparação completa | Uma tabela única: todos os modelos × WMAPE 2021, médio, 2025, A10, std |
| WMAPE 2021 em KPI separado | O fold difícil não está em destaque; só visível no gráfico de linhas |
| Intervalos de confiança | Envelope das 10 seeds no gráfico real vs previsto |
| Secção 6 — contexto para leigo | Alpha, latent step, gamma precisam de explicação em linguagem territorial |
| Nota sobre "HERALD flags" | Enquanto Phase 2J não terminar, deixar claro que a comparação actual não é justa |

---

## Dados externos que precisamos rever

| Dataset | Estado | Ação |
|---|---|---|
| INSEE SIDE 2025 | Integrado | ok |
| Webstat BdF (CONJ, GSTIX) | Ficheiros descargados localmente | Phase 2H mostrou que não melhoram — não incluir no candidato principal |
| Atlas IAT | Auditado, standby | Não incluir até ter plano de uso metodologicamente limpo |
| Graphe mobilité 2021+ | Estático v0 | Verificar se precisa de actualização para a previsão 2026 |

---

## Não fazer (decisões tomadas)

- Macro INSEE/BdF nas entradas do modelo — testado Phase 2H, rejeitado
- Mais de 2 features SIDE — testado Phase 2I, `lag1_growth1y` vence
- Flags manuais como entradas fixas — suspenso até Phase 2J confirmar
