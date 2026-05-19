# HERALD Phase 2B A10 Guard — Auditoria Independente

**Data:** 2026-05-12 | OUT_ROOT: `herald_regime_phase2b_a10_guard_20260512_r1`

---

## Veredito executivo

Phase 2B **não resolve o problema A10 de forma operacional**. Nenhuma variante substitui o controle `manual_flags` sem trade-off grave.

O resultado mais forte — `secenh` — domina o controle nos três objetivos agregados (WMAPE médio, WMAPE 2025, A10 médio) e é o único candidato Pareto não-dominado junto com `sec03`. Mas esse resultado é enganoso: o colapso em 2021 (+39% vs ctrl) é sistematicamente ocultado na média de 5 folds. Quando 4 folds melhoram e 1 colapsa, a média pode parecer boa.

**Recomendação: avançar para Phase 2C.** Não há candidato robusto ainda.

---

## 1. Integridade

| Artifact | Esperado | Encontrado | Status |
|---|---:|---:|---|
| JSONs per_run | 100 | 100 | ✓ |
| metadata JSON | 100 | 100 | ✓ |
| Labels distintos | 10 | 10 | ✓ |
| Seeds por label | 10 | 10 | ✓ |
| source_policy | no_source_flags | todos | ✓ |
| Strict audit | — | PASS | ✓ |

Labels confirmados: `ctrl`, `candidate`, `sec02`, `sec03`, `sec05`, `secenh`, `alpha005`, `smooth003`, `cp_sec02`, `both_sec02`.

---

## 2. Tabela Principal

| Label | Mean WMAPE | ±std | WMAPE 2025 | A10 WMAPE | γ_mob/γ_geo | α 2025 | λ_sec |
|---|---:|---:|---:|---:|---:|---:|---:|
| `secenh` | **0.02868** | 0.00313 | **0.01849** | **0.16357** | 2.60 | 0.535 | 0.2 |
| `sec05` | 0.02906 | 0.00331 | 0.01913 | 0.16937 | 3.74 | 0.530 | 0.5 |
| `sec02` | 0.02908 | 0.00307 | 0.02042 | 0.17448 | 3.02 | 0.500 | 0.2 |
| **`ctrl`** | **0.02908** | **0.00155** | 0.02287 | 0.17264 | 3.04 | 0.517 | 0.1 |
| `candidate` | 0.02912 | 0.00330 | 0.01868 | 0.17851 | 3.35 | 0.483 | 0.1 |
| `sec03` | 0.02934 | 0.00363 | 0.01833 | 0.17356 | 3.59 | 0.513 | 0.3 |
| `smooth003` | 0.02942 | 0.00278 | 0.02024 | 0.17638 | 4.16 | 0.503 | 0.2 |
| `alpha005` | 0.02964 | 0.00310 | 0.01985 | 0.17580 | 2.97 | 0.512 | 0.2 |
| `cp_sec02` | 0.02974 | 0.00310 | 0.02131 | 0.17662 | 4.16 | 0.474 | 0.2 |
| `both_sec02` | 0.02983 | 0.00394 | 0.01972 | 0.17570 | 3.44 | 0.498 | 0.2 |

**Observação crítica sobre std:** O controle `ctrl` tem std=0.00155 — a menor de todas. Todos os candidatos sem flags manuais têm std 2-2.5× maior. Isso é evidência de instabilidade de otimização, não apenas de expressividade.

---

## 3. Fold-by-fold — o número que mais importa

| Label | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---:|---:|---:|---:|---:|
| **`ctrl`** | **0.03539** | 0.02927 | 0.03223 | 0.02564 | 0.02287 |
| `candidate` | 0.05104 | 0.02863 | 0.02629 | 0.02095 | 0.01868 |
| `sec02` | 0.05191 | 0.02943 | 0.02522 | 0.01841 | 0.02042 |
| `sec03` | 0.05243 | 0.03044 | 0.02564 | 0.01988 | 0.01833 |
| `sec05` | 0.05287 | 0.02803 | 0.02388 | 0.02140 | 0.01913 |
| `secenh` | 0.04912 | 0.02954 | 0.02690 | 0.01935 | 0.01849 |
| `alpha005` | 0.05466 | 0.02882 | 0.02580 | 0.01907 | 0.01985 |
| `smooth003` | 0.05287 | 0.02983 | 0.02429 | 0.01987 | 0.02024 |
| `cp_sec02` | 0.05170 | 0.02985 | 0.02573 | 0.02010 | 0.02131 |
| `both_sec02` | 0.05321 | 0.03095 | 0.02540 | 0.01985 | 0.01972 |

### Leitura crítica

**O colapso de 2021 é universal e se agrava com sector_lambda crescente.**

- `secenh` é o melhor candidato em 2021 (0.04912), mas ainda é **+39% pior** que o controle (0.03539).
- `alpha005` é o pior em 2021 (0.05466, +54%).
- Aumentar `sector_lambda` de 0.1 (`candidate`) para 0.5 (`sec05`) piora 2021 de 0.05104 para 0.05287.
- **Nenhuma variante corrije 2021.** A hipótese de que "mais peso A10 ajuda a aprender a estrutura de crise" é refutada.

**O ganho em 2023-2025 é real mas concentrado nos folds recentes:**

- 2023: todos os candidatos melhoram vs ctrl (range -0.006 a -0.008)
- 2024: melhora forte (range -0.004 a -0.007)
- 2025: melhora forte (range -0.002 a -0.004)

Isso não é robustez geral — é aprendizado dos padrões de normalização 2023-2025. O modelo está se especializando nos anos recentes à custa de 2021.

---

## 4. Comparação Pareada vs Ctrl (N=10 seeds)

| Label | Δ mean | p_mean | Δ 2025 | p_2025 | Δ A10 | p_A10 | wins/10 |
|---|---:|---:|---:|---:|---:|---:|---:|
| `candidate` | +0.00004 | 0.575 | **-0.00419** | 0.285 | +0.00587 | 0.093 | 4/10 |
| `sec02` | -0.00000 | 0.879 | -0.00245 | 0.445 | +0.00184 | 0.575 | 4/10 |
| `sec03` | +0.00026 | 0.879 | -0.00454 | 0.139 | +0.00092 | 0.333 | 4/10 |
| `sec05` | -0.00002 | 0.445 | -0.00374 | 0.241 | **-0.00327** | 0.139 | 6/10 |
| `secenh` | **-0.00040** | 0.508 | **-0.00438** | 0.333 | **-0.00907** | **0.059** | 6/10 |
| `alpha005` | +0.00056 | 0.333 | -0.00302 | 0.203 | +0.00316 | 0.959 | 3/10 |
| `smooth003` | +0.00034 | 0.721 | -0.00263 | 0.959 | +0.00374 | 0.114 | 3/10 |
| `cp_sec02` | +0.00066 | 0.879 | -0.00157 | 0.333 | +0.00398 | 0.173 | 4/10 |
| `both_sec02` | +0.00075 | 0.333 | -0.00315 | 0.241 | +0.00306 | 0.721 | 3/10 |

### Leitura crítica

**Nenhum resultado é estatisticamente significativo ao nível 5%.** O mais próximo é a melhora de A10 de `secenh` (p=0.059). Com N=10 seeds, o poder do Wilcoxon é insuficiente para detectar diferenças menores que ~0.003 WMAPE.

`secenh` tem o melhor perfil: 6/10 wins em WMAPE médio, delta A10 = -0.009, mas p=0.508 para mean e p=0.059 para A10. Nenhum dos resultados positivos de `secenh` seria publicável como estatisticamente significativo isoladamente.

---

## 5. Análise Pareto

Objetivos: minimizar `mean_wmape`, `wmape_2025`, `sector_wmape_mean`.

| Label | Mean WMAPE | WMAPE 2025 | A10 WMAPE | Status |
|---|---:|---:|---:|---|
| `secenh` | 0.02868 | 0.01849 | 0.16357 | **PARETO** |
| `sec03` | 0.02934 | 0.01833 | 0.17356 | **PARETO** |
| `ctrl` | 0.02908 | 0.02287 | 0.17264 | DOMINADA |
| `sec05` | 0.02906 | 0.01913 | 0.16937 | DOMINADA (por secenh) |
| `candidate` | 0.02912 | 0.01868 | 0.17851 | DOMINADA |
| todos os outros | — | — | — | DOMINADOS |

**`secenh` domina o controle em todas as três métricas agregadas.** Isso parece uma vitória clara. Mas:

**Por que isso é enganoso:** O Pareto agrega sobre os 5 folds. O trade-off real é:
- secenh melhora 2022-2025 (−7 a −16%)
- secenh piora **dramaticamente** 2021 (+39%)

Um modelo que é 39% pior no único fold que testa recuperação de crise não é operacionalmente válido, mesmo que sua média seja melhor. A análise Pareto sobre métricas agregadas esconde o fold mais crítico.

**`sec03` na fronteira Pareto é ilusório:** sec03 tem melhor WMAPE 2025 (0.01833) que secenh, mas pior A10 (0.17356 vs 0.16357) e WMAPE 2021 de 0.05243. É dominado em A10 e não resolve 2021.

---

## 6. A10 por Setor

### Tabela de WMAPE por setor (média das 10 seeds)

| Label | BE | FZ | GI | JZ | KZ | LZ | MN | OQ | RU |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `ctrl` | 0.2244 | 0.1964 | 0.1352 | **0.1556** | 0.2501 | 0.2220 | 0.1583 | **0.1057** | **0.1061** |
| `secenh` | **0.2027** | 0.1883 | 0.1318 | 0.1894 | **0.2381** | **0.2071** | **0.0910** | 0.1165 | 0.1073 |

### Delta A10 por setor (secenh vs ctrl, negativo = melhor)

| BE | FZ | GI | JZ | KZ | LZ | MN | OQ | RU |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **-0.0217** | -0.0081 | -0.0034 | **+0.0338** | -0.0119 | -0.0149 | **-0.0673** | +0.0108 | +0.0012 |

**Leitura:**

`secenh` com `learned_regime_gate_sector_enhanced` melhora dramaticamente **MN** (−6.7pp, manufatura/não-agrícola) e **BE** (−2.2pp), mas **destrói JZ** (+3.4pp — atividades imobiliárias/financeiras) e degrada ligeiramente OQ (+1.1pp).

Isso não é uma melhora uniforme de A10 — é uma redistribuição de erro setorial. MN e BE melhoram porque a cabeça setorial enhanced aprende melhor os padrões desses setores. JZ piora porque o regime latente com enhanced head não captura bem a dinâmica de serviços financeiros.

Para os outros candidatos:
- `sec05` (λ=0.5): melhora FZ (−2.2pp) e JZ (−0.7pp), mas degrada OQ (+1.1pp). A pressão setorial alta reorganiza A10 de forma diferente.
- `candidate` sem aumento de λ: degrada KZ (+2.2pp) — finanças/seguros — o mais afetado.
- `alpha005` e `smooth003`: pioram A10 em quase todos os setores vs ctrl.

---

## 7. Regime Latente (análise dos NPZ, seed 0)

### Sumário

| Label | latent_std | collapsed | max_step_year | corr(lat,α) | adj_delta_2021 |
|---|---:|---|---|---:|---:|
| `ctrl` | 0.148 | Não | 2013 | **0.748** | 1.103 |
| `candidate` | 0.418 | Não | **2023** | 0.525 | 0.037 |
| `sec05` | 0.601 | Não | 2022 | **-0.575** | 0.021 |
| `secenh` | 0.362 | Não | **2021** | 0.622 | 0.052 |
| `both_sec02` | 0.445 | Não | 2023 | 0.503 | 0.036 |

### Achados críticos

**1. O ctrl tem o latente mais correlacionado com alpha (0.748).** Isso confirma que mesmo com flags manuais o modelo constrói representação latente interna coerente. O latente do ctrl é estável (std=0.148) e captura a transição de "muito local" (alpha≈0.97 em 2012) para "mais grafo" (alpha≈0.54 em 2023).

**2. `secenh` tem o max_step em 2021** — o modelo identifica corretamente 2021 como o maior ponto de ruptura temporal. Isso é o comportamento desejado: o regime latente muda mais quando há mudança econômica real. Correlação latente-alpha = 0.622, razoável.

**3. `sec05` tem correlação negativa (−0.575)** — com sector_lambda=0.5, o modelo reorganizou sua lógica interna de forma patológica. O regime latente move na direção oposta ao alpha. O modelo está usando o regime para compensar a pressão excessiva do loss setorial, não para capturar dinâmica econômica. **`sec05` não é um candidato válido.**

**4. Assimetria crítica no adj_delta:** O ctrl tem adj_delta 2021=1.103 e 2022=1.182 — 15-20× maior que qualquer candidato latente (max 0.057 para candidate). Isso confirma diretamente o problema estrutural documentado na auditoria anterior: **o ctrl usa os flags COVID/rebound para permitir grandes mudanças no grafo durante a crise. Os candidatos latentes nunca têm essa liberdade** — o smooth_term os penaliza com força máxima em todos os anos. A comparação é fundamentalmente assimétrica.

**5. Nenhum modelo colapsa** (latent_std > 0.05 para todos), o que é positivo. Os vetores latentes variam ao longo do tempo.

---

## 8. Grafo e Gamma

**γ_mob/γ_geo:** Todos os modelos privilegiam a mobilidade sobre a geografia pura (ratio > 1). O ctrl tem ratio 3.04. `secenh` tem 2.60 — mais equilibrado. `smooth003` e `cp_sec02` têm 4.16 — muito dependentes de mobilidade.

**`smooth003` não reduziu instabilidade:** O adj_delta de `smooth003` (0.02-0.09 por ano) é comparável ao dos outros candidatos. O smooth_lambda maior simplesmente penalizou mais o treino sem mudar o padrão de variação de grafo.

**`learned_regime_both` no `both_sec02`:** O latente afeta tanto o grafo quanto o gate alpha. Mas adj_delta (0.013-0.047) não é maior que o `candidate` (0.018-0.057). O grafo não está aproveitando o regime latente para fazer mudanças interpretáveis maiores.

---

## 9. Metodologia — Respostas diretas

**Phase 2B resolve o problema A10?**

Parcialmente. `secenh` melhora A10 médio em 0.9pp, principalmente pelo setor MN. Mas degrada JZ em 3.4pp e ainda colapsa em 2021. Não há resolução completa.

**Alguma variante sem flags manuais pode substituir ctrl?**

Não. Nenhuma variante passa o teste de não-colapsar em 2021 dentro da margem operacional. A melhor variante (`secenh`) tem WMAPE 2021 = 0.04912 vs ctrl 0.03539 — 39% pior. Isso é inaceitável para uso operacional em previsão territorial.

**Ainda precisamos de Phase 2C?**

**Sim, obrigatoriamente.** Phase 2C testa a questão que Phase 2B não responde: o ganho de `secenh` é real ou é artefato da assimetria estrutural na penalidade de suavização? Se o ctrl perde sua vantagem quando a comparação é simétrica (smooth_regime_source=none), o resultado Phase 2B pode estar subestimando o candidato. Se não perder, o colapso em 2021 é estrutural e Phase 3 não se justifica.

**O resultado suporta "HERALD aprende regimes"?**

Não como afirmação forte. Suporta apenas: *"HERALD constrói representação latente interna que correlaciona com dinâmica econômica (corr 0.5-0.75) e muda mais em anos de transição (secenh: max_step em 2021). Este sinal não é suficiente para substituir flags manuais em 2021, mas há evidência de sinal latente real."*

A afirmação publicável neste momento é mais fraca: **"há sinal latente, não operacional ainda."**

---

## 10. Ranking Final com Justificativa

### Para avanço a Phase 2C

**`secenh` — candidato prioritário:**
- Único Pareto não-dominado com A10 < ctrl
- Latente coerente (max_step em 2021, corr=0.622)
- Ainda colapsa em 2021 — precisa de smooth simétrico para entender se a assimetria explica parte do problema

**`sec05` — descartar:**
- Correlação latente-alpha negativa (−0.575) — estrutura interna patológica
- Melhora KZ/FZ mas sem fundamento interpretável

**`both_sec02` — descartar para Phase 2C:**
- WMAPE médio pior que ctrl
- Instabilidade 2× maior que ctrl (std=0.00394)
- O grafo latente não está adicionando valor interpretável

**`smooth003`, `alpha005`, `cp_sec02` — descartados:**
- Todos piores que ctrl em WMAPE médio
- Sem compensação em A10 ou 2025 suficiente

---

## 11. Conclusão

Phase 2B produziu um resultado interessante em `secenh` — dominância Pareto sobre o controle. Mas essa dominância é artificial: esconde o colapso de 2021 dentro da média de 5 folds, e o controle tem vantagem estrutural de 15-20× maior liberdade de mudança de grafo em anos de crise (adj_delta_2021: 1.103 vs 0.052).

O experimento `secenh` com `learned_regime_gate_sector_enhanced` tem o latente mais interpretável da bateria (ruptura em 2021, correlação 0.622 com alpha) e a melhor melhora A10 individual (MN −6.7pp). Mas ainda não é robusto.

**Decisão: Phase 2C é necessária.** O objetivo de Phase 2C é verificar se `secenh` com smooth simétrico mantém a dominância Pareto. Se sim, temos pela primeira vez um candidato sem flags manuais que supera o controle de forma metodologicamente defensável. Se não, o sinal latente ainda existe mas a vantagem era artefato de design.

---

---

## Nota metodológica sobre a análise de regime latente

A análise de `latent_regime_values`, `adj_delta`, correlação latente-alpha e padrão de ruptura temporal (seção 7) foi feita apenas sobre **seed 0** de cada variante. Isso é suficiente para formular hipóteses fortes — especialmente o achado do adj_delta assimétrico (1.103 vs 0.052 em 2021) e o max_step de `secenh` em 2021 — mas não é conclusivo.

Antes de citar esses resultados como evidência definitiva, repetir a análise NPZ para as 10 seeds via:

```bash
rsync -az meso-direct:~/project_recomm_herald_v6_2025_20260430/hpc_results/herald_regime_phase2b_a10_guard_20260512_r1/data_processed/*secenh*.npz \
  hpc_results/herald_regime_phase2b_a10_guard_20260512_r1/data_processed/
```

e verificar se:
- o max_step em 2021 para `secenh` é consistente entre seeds (ou só seed 0);
- o adj_delta_2021 do ctrl é sistematicamente ≥ 1.0 em todas as seeds;
- a correlação latente-alpha de `secenh` (0.622) se mantém na média das 10 seeds.

Até essa verificação: tratar os achados de regime latente como **hipótese forte, não conclusão definitiva**.

---

*Auditoria baseada em: 100 JSONs per-run, 100 metadata, 5 NPZ internals (seed 0), análise independente das saídas dos scripts oficiais.*
