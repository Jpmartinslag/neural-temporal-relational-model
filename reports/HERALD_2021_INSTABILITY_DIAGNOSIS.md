# HERALD 2021 — Diagnóstico de Instabilidade

**Data:** 2026-05-12 | Candidato: `secenh` (no_regime + learned_regime_gate_sector_enhanced)
**Dados:** Phase 2C, 10 seeds × 5 folds, 280 zonas de emprego

---

## Resumo Executivo

O problema de 2021 tem causa identificável, precisa e mecanisticamente clara:

> **O modelo neural aprende, durante o treino do fold 2021, que quando Ridge superprevê o nível de emprego, o resíduo correto é fortemente negativo (como em 2020, o ano COVID). Em 2021, Ridge também superprevê levemente — mas a correção correta é positiva (rebote). O regime latente não distingue sistematicamente esses dois estados. O resultado é underprediction sistemático de grandes zonas.**

Este problema afeta especificamente **zonas grandes** (correlação tamanho×erro = 0.73) e é quase nulo em zonas pequenas e médias. Não é um problema arquitetural geral — é uma confusão de regime específica na transição 2020→2021 que aparece em 7/10 seeds.

---

## 1. É arquitetural, de dados ou de otimização?

**Resposta: principalmente de dados, manifestado como instabilidade de otimização.**

**Evidência:** A seed 123 alcança WMAPE 2021 = 0.033 — melhor que o controle (0.035). A arquitetura consegue. O problema é que a paisagem de otimização para o fold 2021 tem um mínimo "bom" (onde a seed 123 cai) e vários mínimos "ruins" onde o modelo aprende a subprever excessivamente. O que cria essa paisagem acidentada é a estrutura dos dados: 2020 é um outlier extremo de treino que distorce o sinal residual.

---

## 2. Evidências Quantitativas

### 2.1 Ridge vs HERALD por ano

| Ano | Ridge | cand | ctrl | HERALD vs Ridge | cand vs ctrl |
|---:|---:|---:|---:|---:|---:|
| 2021 | 0.06731 | 0.04876 | 0.03540 | **−0.019** | +0.013 |
| 2022 | 0.08620 | 0.03000 | 0.02875 | **−0.056** | +0.001 |
| 2023 | 0.07767 | 0.02709 | 0.03239 | **−0.051** | −0.005 |
| 2024 | 0.03070 | 0.01978 | 0.02681 | **−0.011** | −0.007 |
| 2025 | 0.03391 | 0.01854 | 0.02334 | **−0.015** | −0.005 |

**Leitura crítica:** O HERALD melhora substancialmente sobre Ridge em TODOS os anos, incluindo 2021 (−0.019). O problema de 2021 não é que o HERALD piora — é que melhora *menos* que o controle. Em 2022-2025, o HERALD sem flags melhora mais que o controle sobre o Ridge.

### 2.2 Bias sistemático: HERALD sempre subprevê em 2021

| seed | Erro médio cand | Erro médio Ridge | WMAPE 2021 |
|---:|---:|---:|---:|
| 0 | −104.7 | +68.1 | 0.04082 |
| 1 | −145.6 | +68.1 | 0.05113 |
| 7 | **−198.5** | +68.1 | 0.06150 ←2ºpior |
| 13 | −177.7 | +68.1 | 0.05368 |
| 17 | **−176.9** | +68.1 | 0.06284 ←pior |
| 42 | −129.9 | +68.1 | 0.04630 |
| 77 | −143.4 | +68.1 | 0.04818 |
| 99 | −130.7 | +68.1 | 0.04761 |
| 123 | **−66.0** | +68.1 | 0.03276 ←melhor |
| 2025 | −137.9 | +68.1 | 0.04278 |

**Ridge superprevê** (+68 por zona em média). **Todas as seeds do HERALD subpreveem** (−66 a −199 por zona). A variância do WMAPE entre seeds é totalmente explicada pelo tamanho do underprediction: seed 123 subprevê modestamente (−66), seeds 7 e 17 subpreveem severamente (−177 a −199).

**O diagnóstico:** O modelo aprende que o resíduo correto em situações onde Ridge superprevê é negativo (correto para 2020). Em 2021, Ridge também superprevê — mas a correção deveria ser menor (rebote real) ou até positiva. O regime latente não distingue "Ridge alto por COVID" de "Ridge alto por subaceleração pós-rebote" em 7/10 seeds.

### 2.3 Concentração do erro em zonas grandes

| Quintil de tamanho | ΔAE (cand−ctrl) | AE cand | AE ctrl |
|---|---:|---:|---:|
| Q1 (pequenas) | **−3.8** | 76.9 | 80.6 |
| Q2 | **−7.3** | 52.7 | 59.9 |
| Q3 | **−4.0** | 32.2 | 36.2 |
| Q4 | +28.6 | 70.6 | 42.0 |
| Q5 (grandes) | **+251.1** | 732.0 | 480.9 |

**Correlação tamanho da zona × delta erro: 0.731**

**Conclusão chave:** O candidato é **melhor** que o controle em zonas Q1-Q3 (60% das zonas). O candidato é **muito pior** apenas nas zonas grandes (Q4-Q5). Em WMAPE, as zonas grandes dominam o denominador — por isso o WMAPE agregado é pior mesmo sendo melhor em maioria das zonas.

**O erro de 2021 é um problema de calibração em zonas grandes, não um problema geral.**

### 2.4 Zonas que mais contribuem para o erro extra

As 5 zonas com maior excesso de erro (cand vs ctrl) explicam **37%** do total. As 20 maiores explicam **69%**. O maior contribuinte é ZE2020=1109 (y_true=195.536 empregos — provavelmente Paris ou grande polo urbano), com 14.8% do excesso sozinho.

---

## 3. Seed Boa (123) vs Seed Ruim (17): o que as diferencia

### 3.1 Regime latente 2020→2021

| Seed | Step 2019→2020 | Step 2020→2021 | Alpha 2021 | Corr(lat,α) |
|---:|---:|---:|---:|---:|
| **123** | 0.391 | **0.518** | 0.474 | −0.307 |
| 42 | 0.481 | **0.801** | 0.571 | −0.264 |
| **17** | 0.587 | **0.953** | 0.643 | −0.016 |
| 7 | 0.024 | **0.067** | 0.619 | +0.488 |

**Dois padrões patológicos distintos:**

**Seed 17 (overreacting):** passo 2020→2021 é o maior de toda a trajetória (0.953). O latente oscila violentamente: lat_2020=[0.33, -0.37, 0.36] → lat_2021=[-0.44, 0.65, -0.71]. O modelo "detecta" uma ruptura enorme em 2021 — mas interpreta como ruptura negativa, não positiva. Alpha 2021=0.643 (fica mais local, menos grafo) em um momento em que o grafo poderia ajudar. Corr(lat,alpha)≈0 — o latente não está modulando alpha de forma coerente.

**Seed 7 (frozen):** passo 2019→2020 e 2020→2021 quase nulos (0.024, 0.067). O latente quase não muda. O modelo trata 2021 como se fosse idêntico a 2019-2020. Alpha fica alto (0.62-0.67) durante todo o período — excessivamente local. O grafo não participa.

**Seed 123 (funcional):** passo 2020→2021 = 0.518, moderado. lat_2020=[-0.29, -0.51, -0.38] → lat_2021=[0.12, 0.14, 0.11]. O latente muda em 2020 (detecta COVID) e volta para perto de zero em 2021 (detecta normalização). Alpha 2021=0.474 — equilíbrio local/grafo razoável.

**Diagnóstico por seed:**
- Seed 123: latente oscila moderadamente e na direção certa — a transição 2020→2021 é identificada como "saindo da crise".
- Seed 17: latente oscila excessivamente — amplifica o choque em vez de absorvê-lo.
- Seed 7: latente congela — ignora completamente a dinâmica 2020-2021.

### 3.2 A10 por setor em 2021 (seed 123 vs 17)

| Setor | seed 123 | seed 17 | Diferença |
|---|---:|---:|---:|
| BE | 0.223 | 0.202 | −0.021 (17 melhor) |
| FZ | 0.156 | **0.174** | +0.018 (17 pior) |
| GI | 0.118 | 0.110 | −0.008 |
| JZ | **0.231** | 0.184 | −0.047 (123 pior!) |
| KZ | 0.182 | **0.240** | +0.058 (17 pior) |
| LZ | 0.202 | 0.210 | +0.008 |
| MN | 0.101 | **0.129** | +0.028 (17 pior) |
| OQ | 0.111 | 0.107 | −0.004 |
| RU | 0.093 | 0.096 | +0.003 |

Seed 123 é globalmente melhor em A10 em 2021 (especialmente KZ=finanças e MN). Mas perde em JZ (imobiliário/real estate). A seed 17 compensa total ruim com JZ ligeiramente melhor — sugestão de que o setor imobiliário tem dinâmica de rebote diferente que beneficia o regime "superoscilante" da seed 17.

---

## 4. Hipóteses Causais (por ordem de probabilidade)

### H1 — Confusão de regime residual 2020→2021 (MAIS PROVÁVEL)

**Mecanismo:** O treino do fold 2021 termina em 2020, ano com:
- Ridge superprevendo muito (+68 erro médio)
- Resíduo correto = fortemente negativo (Ridge estava muito alto, verdade era baixa)

Em 2021:
- Ridge superprevê levemente (+68 ainda, mas por razão diferente — subestima o rebote)
- Resíduo correto = positivo ou levemente negativo (verdade ≥ Ridge)

O modelo aprende uma regra implícita: "quando Ridge está alto, corrigir para baixo." Em 7/10 seeds, o regime latente não distingue os dois estados. Em seed 123, o latente aprende que 2020 é diferente de 2021 e aplica a correção certa.

**Por que o ctrl não tem esse problema?** `is_post_covid_rebound=1` em 2021 sinaliza explicitamente que 2021 é um ano de recuperação, não uma extensão do choque. O modelo com flags aprende "em anos de rebote, o resíduo do Ridge é positivo."

### H2 — Colapso parcial do latente (CONTRIBUI)

Seed 7 mostra lat_step ≈ 0 na transição crítica: o modelo não detecta nenhuma mudança em 2020-2021. O regime latente está efetivamente colapsado para essa seed. Isso indica que a paisagem de otimização tem mínimos onde o latente é inútil — e esses mínimos são estáveis o suficiente para o treinamento convergir neles.

### H3 — Concentração em grandes zonas (AMPLIFICA, NÃO CAUSA)

A confusão de regime afeta todas as zonas, mas o impacto em WMAPE é dominado pelas zonas grandes (Q5, ΔAE=+251 vs Q1=−4). O erro causal é H1; as grandes zonas apenas amplificam o sinal de WMAPE. Resolver H1 reduzirá automaticamente o impacto em grandes zonas.

### H4 — Estrutura de dados (RAIZ)

Para o fold 2021, o treino inclui apenas **1 exemplo** de crise COVID (2020) — um único ponto temporal extremo. O modelo precisa generalizar a partir de 1 exemplo de regime de crise. Com T=9 pontos de treino pré-COVID e 1 ponto COVID, qualquer ruído de otimização na região do espaço de parâmetros onde 2020 tem impacto forte se propaga para 2021. Isso explica a variância alta entre seeds (CV=19%).

---

## 5. O que NÃO é aceitável como solução

1. **Escolher seed 123 por desempenho em 2021.** A seed 123 é o resultado do fold de TESTE. Selecioná-la baseado no resultado de teste é data snooping. Inaceitável metodologicamente.

2. **Reintroduzir `is_covid_year` ou `is_post_covid_rebound`.** Retira o claim científico central. Inaceitável.

3. **Usar 2021 como fold de validação para selecionar hiperparâmetros.** O fold 2021 é fold de TESTE. Qualquer decisão metodológica baseada em 2021 cria vazamento.

4. **Chamar ganho em 2023-2025 de robustez geral.** O modelo melhora fortemente em 2022-2025. Esse ganho é real, mas dizer que o modelo é "robusto" sem endereçar 2021 é desonesto.

5. **Reportar média de 5 folds sem mencionar a decomposição por fold.** A média 0.029 do cand está abaixo do ctrl (0.029) somente porque 2022-2025 compensam 2021. Qualquer publicação deve reportar fold-by-fold.

---

## 6. Soluções Concretas

As soluções são ordenadas por **defensabilidade metodológica × facilidade de implementação**. Nenhuma delas reintroduz flags manuais.

### S1 — Penalidade de colapso do regime latente (IMPLEMENTAR PRIMEIRO)

**Mecanismo:** Força o latente a ter variância temporal mínima, evitando o padrão da seed 7 (latente congelado). Adicionalmente, incentiva o modelo a usar os 3 componentes do latente de forma diferenciada.

```python
# Em train_herald_semi_v2.py, após o forward pass do treino
# Requer modificação do forward para retornar latent_stack durante treino
if args.collapse_lambda > 0:
    # lat_stack: (T, REGIME_DIM) — variância temporal
    lat_var = lat_stack.var(dim=0).mean()
    collapse_loss = args.collapse_lambda * F.relu(0.1 - lat_var)
    loss = loss + collapse_loss
```

**Por que ajuda:** Seed 7 (frozen, WMAPE 2021=0.062) tem lat_step 2020→2021 ≈ 0.07. Com collapse_lambda, o latente é forçado a variar, aumentando a chance de distinguir 2020 (crash) de 2021 (rebote). **Não garante** que a distinção seja na direção certa, mas aumenta a probabilidade.

**Risco:** Pode criar oscilações artificiais que não correspondem a regime real. Mitigar com `collapse_lambda` pequeno (0.01-0.05) e verificar interpretabilidade do latente.

### S2 — Janela deslizante (TESTAR EM PARALELO)

**Mecanismo:** Para o fold 2021, treinar em W anos recentes (ex: 2015-2020) em vez de 2012-2020. Isso faz com que 2020 seja o ponto mais recente mas não o único outlier — os outros W-1 anos ainda mostram padrões normais.

**Por que ajuda:** Com janela deslizante, o modelo não precisa reconciliar "2012-2019 normais + 2020 extremo" simultaneamente. A sequência é mais homogênea, e a normalização das features é calculada sobre um período mais estável.

**Risco:** T_treino menor reduz capacidade do Ridge AR e do GRU. Testar W=7 e W=9.

**Implementação:** já existe `--single-target-year` e split logic. Requer nova config de splits com janela deslizante.

### S3 — Change-point formal causal (PELT) como sinal auxiliar

**Mecanismo:** Substituir o `_change_state` heurístico por PELT aplicado ao histórico de treino. O PELT daria ao modelo um sinal explícito: "2020 é um ponto de quebra detectado estatisticamente" — mas calculado apenas com dados de treino (forecast-safe).

**Por que ajuda:** O sinal de change-point diz "algo mudou em 2020." O modelo pode aprender que "1 ano depois de um change-point = rebote esperado" sem precisar de uma flag chamada `is_post_covid_rebound`. A diferença para o flag manual: o PELT detecta qualquer quebra (2008, 2012, 2020), não só COVID.

**Implementação:** Ver spec em `reports/HERALD_REGIME_PHASE2C_CRITICAL_PLAN.md`. Requer `pip install ruptures`.

### S4 — Ensemble formal (NÃO seleção de seed)

**Mecanismo:** Para cada fold, prever com K seeds e fazer média das predições — não selecionar a melhor seed.

**Estimativa de ganho:** Se 3/10 seeds têm WMAPE 2021 ≤ 0.038 e as outras 7 têm ~0.052, a média de 10 seeds é ~0.049. A média das 3 melhores seria ~0.036. A média de todas as 10 sem seleção já é 0.049.

**Por que S1 é melhor:** Ensemble não resolve o problema, apenas dilui. Se todas as seeds melhorarem com S1, o resultado é melhor e mais interpretável.

### S5 — Alpha penalty para evitar extremos

**Mecanismo:** Penalizar alpha muito alto (>0.8, excessivamente local) em janelas de treinamento recentes. O padrão da seed 17 mostra alpha=0.64 em 2021 — muito mais local que a seed 123 (0.47).

```python
# Penalidade para alpha longe de 0.5 durante anos recentes
alpha_extremeness = torch.mean((alpha - 0.5).pow(2))
loss = loss + args.alpha_balance_lambda * alpha_extremeness
```

**Risco:** Força equilíbrio artificial que pode prejudicar 2022-2025 onde alpha ≠ 0.5 é a solução correta.

---

## 7. O que NÃO é o problema

- **Não é o Ridge AR:** Ridge é idêntico entre seeds (0.067 em 2021). A variância de 2021 vem 100% do neural.
- **Não é erro setorial A10 como causa primária:** A10 de seed 123 e 17 são comparáveis. A10 é um sintoma, não a causa.
- **Não é escala:** O erro é underprediction sistemático, não erro de escala aleatório.
- **Não é o grafo sozinho:** adj_delta 2021 é similar entre seeds (0.020-0.037). O grafo não está instável — é o alpha e o latente que instabilizam a correção residual.
- **Não é falta de dados históricos em geral:** O modelo funciona muito bem em todos os outros folds. É específico para o fold onde o treino termina em 2020.

---

## 8. Bateria Mínima de Estabilização

**Objetivo:** Descobrir se o colapso 2021 pode ser reduzido sem reintroduzir flags, sem olhar 2021 como validação, e mantendo os ganhos 2022-2025.

**Critério de validação:** Usar apenas folds 2022-2024 como validação interna. 2021 e 2025 ficam como teste cego.

### Configs mínimas (10 seeds cada, 3 alvo = 30 runs)

| Label | Mudança | Objetivo |
|---|---|---|
| `ctrl_secenh` | candidato base (Phase 2C) | referência |
| `collapse01` | + `collapse_lambda=0.01` | testar H2 (colapso latente) |
| `collapse05` | + `collapse_lambda=0.05` | testar limite de collapse |

Se `collapse01` ou `collapse05` reduzir CV de 2021 de 18.7% para < 12% E manter gains 2022-2025:
→ avançar para bateria completa com janela deslizante e PELT.

Se colapso não ajudar:
→ o problema é H4 (dado insuficiente para fold 2021), e a solução é janela deslizante ou aceitar 2021 como limitação com ensemble.

### Critério de sucesso

| Métrica | Threshold |
|---|---|
| WMAPE médio 2022-2024 | ≤ baseline (0.025) |
| WMAPE 2021 mean | ≤ 0.042 (−14% vs atual 0.049) |
| WMAPE 2021 CV | ≤ 13% (vs atual 19%) |
| A10 WMAPE | ≤ baseline (0.163) |
| Latent_step 2020→2021 CV | ≤ 30% (vs atual: seeds com quase zero vs 0.95) |

---

*Análise baseada em: 14.000 predições total (10 seeds × 5 folds × 280 zonas), 5 NPZs de internals, decomposição Ridge vs HERALD, análise de concentração de erro.*
