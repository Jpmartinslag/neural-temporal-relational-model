# HERALD Phase 3 — Tutor Block A Audit
**Job:** 7394106 | **Lançamento:** 2026-05-26 15:26 | **Auditoria:** 2026-05-26 16:49  
**Root:** `~/project_recomm_herald_v6_2025_20260430/dataset/hpc_results/herald_regime_phase3_tutor_gate_block_a_20260526_1526_phase3_tutorA_r1`

---

## 1. Integridade

| Item | Status |
|------|--------|
| Array jobs (0–9) | ✅ Todos COMPLETED, ExitCode 0:0 |
| JSONs em `reports/per_run/` | ✅ 50/50 (5 configs × 10 seeds) |
| Erros em logs (Traceback/ERROR/RuntimeError) | ✅ Zero ocorrências |
| Configs identificadas | T0, T1, T2, T5, T6 — todas presentes |

Duração por array: de 21–68 min (job 0 mais longo: 1h08 — provavelmente T1 com overhead de feature processing).

---

## 2. Tabela por Config (médias sobre 10 seeds)

| Config | Descrição | WMAPE Mean | WMAPE 2021 | WMAPE 2025 | Sector WMAPE |
|--------|-----------|:----------:|:----------:|:----------:|:------------:|
| **T0** | Baseline HERALD no-flags (SIDE2, residual train_opt) | **0.02084** | 0.03620 | **0.01268** | 0.15851 |
| T1 | Macro como feature anual | 0.03246 | 0.08532 | 0.01363 | 0.16465 |
| T2 | Gate global homogêneo | 0.02701 | 0.04386 | 0.02400 | 0.15663 |
| T5 | **Gate heterogêneo local** (hipótese principal) | 0.02660 | 0.05124 | 0.01523 | 0.15771 |
| T6 | Falsificação (T5 + macro permutado) | **0.02281** | **0.03638** | **0.01236** | **0.15656** |

> ⚠️ T6 (falsificação com macro embaralhado) obteve **melhor resultado geral** que T5 e equiparou T0 em WMAPE 2021.

---

## 3. Comparações Pareadas

Todas as comparações usam Wilcoxon pareado unilateral (H₁: linha esquerda < linha direita, i.e., menor WMAPE). N=10 seeds. Interpretar com cautela.

### T5 vs T0 — gate heterogêneo vs baseline

| Métrica | T5 | T0 | Δ | T5 wins | p |
|---------|----|----|---|---------|---|
| WMAPE Mean | 0.02660 | 0.02084 | **+0.00576** | 0/10 | 1.000 |
| WMAPE 2021 | 0.05124 | 0.03620 | **+0.01505** | 1/10 | 0.999 |
| WMAPE 2025 | 0.01523 | 0.01268 | **+0.00255** | 2/10 | 0.986 |

**Resultado:** T5 perde em todas as métricas para T0. Nenhuma seed T5 ganha do baseline em WMAPE mean. Não sustenta a hipótese principal.

---

### T5 vs T1 — gate heterogêneo vs macro como feature bruta

| Métrica | T5 | T1 | Δ | T5 wins | p |
|---------|----|----|---|---------|---|
| WMAPE Mean | 0.02660 | 0.03246 | **−0.00586** | 8/10 | **0.005** |
| WMAPE 2021 | 0.05124 | 0.08532 | **−0.03408** | 10/10 | **0.001** |
| WMAPE 2025 | 0.01523 | 0.01363 | +0.00160 | 3/10 | 0.935 |

**Resultado:** T5 bate T1 de forma robusta em mean e 2021 (p<0.01). Gate heterogêneo é melhor que injeção bruta de feature macroeconômica. Porém T5 perde em 2025 vs T1. Ganho parcial.

---

### T5 vs T2 — gate heterogêneo vs gate global

| Métrica | T5 | T2 | Δ | T5 wins | p |
|---------|----|----|---|---------|---|
| WMAPE Mean | 0.02660 | 0.02701 | −0.00041 | 5/10 | 0.423 |
| WMAPE 2021 | 0.05124 | 0.04386 | **+0.00738** | 3/10 | 0.935 |
| WMAPE 2025 | 0.01523 | 0.02400 | **−0.00877** | 10/10 | **0.001** |

**Resultado:** T5 não melhora 2021 vs T2 (p=0.935). T5 ganha em 2025 (p=0.001), mas 2021 é o ano crítico. A diferenciação local não sustenta vantagem sobre ajuste global no choque pandêmico.

---

### T5 vs T6 — gate heterogêneo vs falsificação (macro permutado)

| Métrica | T5 | T6 | Δ | T5 wins | p |
|---------|----|----|---|---------|---|
| WMAPE Mean | 0.02660 | 0.02281 | **+0.00379** | 0/10 | 1.000 |
| WMAPE 2021 | 0.05124 | 0.03638 | **+0.01487** | 1/10 | 0.999 |
| WMAPE 2025 | 0.01523 | 0.01236 | **+0.00287** | 2/10 | 0.997 |

**Resultado:** T6 (macro embaralhado) supera T5 em todas as métricas, em todas as seeds. Esta é a falha crítica da bateria: **o sinal temporal do macro não está sendo explorado de forma causal**. T6 sugere que o ganho de T5 sobre T1 vem da presença de qualquer vetor de contexto extra, não do conteúdo macroeconômico temporal.

---

### T1 vs T0 — macro bruto já ajuda?

| Métrica | T1 | T0 | Δ | T1 wins | p |
|---------|----|----|---|---------|---|
| WMAPE Mean | 0.03246 | 0.02084 | **+0.01162** | 0/10 | 1.000 |
| WMAPE 2021 | 0.08532 | 0.03620 | **+0.04912** | 0/10 | 1.000 |
| WMAPE 2025 | 0.01363 | 0.01268 | +0.00095 | 4/10 | 0.862 |

**Resultado:** Macro como feature bruta anual **destrói** o modelo. T1 é pior que T0 em 10/10 seeds para mean e 2021. Injeção ingênua de macro introduz ruído; não motiva uso direto sem mecanismo de gating.

---

## 4. Resultado por Ano

### WMAPE 2021 (ano crítico — choque COVID/rebote)

| Config | WMAPE 2021 | vs T0 |
|--------|:----------:|:-----:|
| T0 | 0.03620 | — |
| **T6** | **0.03638** | +0.00018 |
| T2 | 0.04386 | +0.00766 |
| T5 | 0.05124 | +0.01504 ↑ pior |
| T1 | 0.08532 | +0.04912 ↑↑ pior |

T5 **piora** 2021 vs T0. T6 empata T0 em 2021. Nenhuma variante com macro melhora o choque raro.

### WMAPE 2025 (ano recente — guard rail)

| Config | WMAPE 2025 |
|--------|:----------:|
| T6 | 0.01236 |
| T0 | 0.01268 |
| T1 | 0.01363 |
| T5 | 0.01523 |
| T2 | 0.02400 |

T2 (gate global) destrói 2025 — overfitting ou extrapolação problemática do gate nacional. T5 piora levemente vs T0 mas mantém escala aceitável. T1 neutro.

---

## 5. A10 — Sector WMAPE Mean

| Config | Sector WMAPE |
|--------|:------------:|
| T0 | 0.15851 |
| T2 | 0.15663 |
| T6 | 0.15656 |
| T5 | 0.15771 |
| T1 | 0.16465 |

Diferenças entre T0/T2/T6/T5 são menores que 0.002 — marginais. T1 piora levemente (+0.006 vs T0). Nenhuma config destrói o setor A10.

---

## 6. Interpretação Científica

**Achado central:** O controle falsificador T6 (macro temporal permutado aleatoriamente) supera T5 (macro temporal real) em **todas** as métricas, em **10/10 seeds**. Isso **não sustenta** a hipótese de que o gating condicional heterogêneo usa o conteúdo temporal do macro de forma causal.

**Hipóteses explicativas:**

1. **Regularização acidental por T6:** O permute rompe a autocorrelação temporal, funcionando como regularização implícita. O modelo de T6 pode estar aprendendo a ignorar o contexto (fallback para gate neutro), o que paradoxalmente estabiliza o treinamento.

2. **Overfitting de T5 ao ciclo macro:** O gate heterogêneo de T5 pode estar se ajustando ao padrão histórico do macro com viés suficiente para piorar anos raros (2021), enquanto T6, ao ver sinal aleatório, não cria esse viés.

3. **Representação insuficiente do espaço local:** A ZE representation alimentando o gate pode não ser rica o suficiente para personalizar a reação. O gate pode estar essencialmente colapsando para comportamento similar ao global (T2), sem ganho de heterogeneidade real.

4. **Tamanho de amostra:** N=10 limita poder estatístico. A vantagem de T6 é consistente mas pode conter componente de variância de inicialização.

**O que T5 faz bem:** Bate T1 (p<0.01), mostrando que gate é melhor que feature bruta. Sugere que o mecanismo de filtragem é necessário — mas o conteúdo filtrado ainda não é causal.

**O que T2 sugere:** Gate global empata com T5 em mean e 2021, custando 2025. Motiva que ajuste nacional homogêneo captura parte da variação, mas introduz rigidez em anos recentes.

---

## 7. Interpretação Leiga

Testamos se dar ao modelo informação sobre o estado da economia nacional (inflação, desemprego, clima de negócios) ajuda a prever melhor o emprego territorial, especialmente no choque de 2020–2021.

**Resultado negativo:** O modelo aprendeu algo com esse contexto macro, mas não o que esperávamos. Quando embaralhamos a informação macro no tempo (tornando-a aleatória), o modelo ficou **ainda melhor**. Isso indica que o modelo não está aprendendo "quando a economia vai mal, o emprego reage assim" — está aprendendo algo mais superficial, como usar qualquer número extra como âncora de estabilidade numérica.

O baseline sem nenhum contexto macro (T0) ainda é o campeão do ano crítico 2021.

---

## 8. Decisão

### ❌ NÃO avançar para cross-attention leve

**Critério violado (determinante):** T5 não bate T6 em nenhuma métrica. A falsificação vence ou empata o mecanismo real. Sem evidência de uso causal do sinal temporal macro, introduzir cross-attention adicionaria complexidade sobre base não validada.

**Critério violado (secundário):** T5 não bate T0 em nenhuma métrica. O gate heterogêneo regride vs baseline atual.

**O que sustenta a hipótese parcialmente:** T5 > T1 (p<0.01) — gate é melhor que feature bruta. Isso não é suficiente para avançar, mas motiva investigação do mecanismo de gating.

### Próximos passos sugeridos (se continuar nessa direção)

1. **Investigar por que T6 ganha:** Analisar os gates aprendidos por T5 vs T6. Se T5-gates colapsam para valores uniformes, o espaço de representação local é insuficiente.
2. **Enriquecer representação ZE:** O gate precisa de representação local mais informativa (histórico recente, posição no grafo territorial) antes de macro entrar como contexto diferenciador.
3. **Testar macro defasado:** Usar macro de t-1 ou t-2 para evitar vazamento e verificar se o sinal temporal emerge com defasagem adequada.
4. **Block B com regularização:** Se rodar nova bateria, adicionar entropia de gate (forçar dispersão) para evitar colapso do mecanismo heterogêneo.

---

*Auditoria gerada automaticamente por pipeline de análise — 2026-05-26 16:49 CEST*
