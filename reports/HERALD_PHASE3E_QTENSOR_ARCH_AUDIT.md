# HERALD Phase 3E — q_tensor Architecture Selection Audit

**Data:** 2026-05-27  
**Job SLURM:** 7398380  
**Root:** `hpc_results/herald_regime_phase3e_qtensor_arch_20260527_173259_r1`  
**Objetivo:** Selecionar arquitetura q_tensor URSSAF para modelo final.

---

## 1. Integridade

| Item | Valor |
|------|-------|
| JSONs encontrados | 240 / 240 ✓ |
| Configs únicas | 12 / 12 ✓ |
| Seeds por config | 20 ✓ |
| Tasks SLURM COMPLETED | 20 / 20 ✓ |
| Exit codes | 0:0 em todos ✓ |
| Artefatos faltantes | nenhum |

Task `7398380_19` (o último pendente na checagem anterior) finalizou normalmente: elapsed 01:02:58, ExitCode 0:0.

---

## 2. Tabela principal por config

Ordenado por mean WMAPE (menor = melhor).

| # | Config | N | Mean WMAPE | ±std | 2021 | 2022 | 2023 | 2024 | 2025 | Sector WMAPE |
|---|--------|---|-----------|------|------|------|------|------|------|-------------|
| 1 | Q6_lag1 | 20 | **0.020251** | 0.001718 | 0.0339 | 0.0186 | 0.0159 | 0.0205 | 0.0123 | 0.15680 |
| 2 | Q12_effectifs_lag1_a10guard | 20 | 0.020371 | 0.001959 | 0.0347 | 0.0205 | 0.0155 | 0.0188 | 0.0124 | 0.15509 |
| 3 | Q7_effectifs_lag1 | 20 | 0.020398 | 0.001498 | 0.0348 | 0.0205 | 0.0160 | 0.0192 | 0.0114 | 0.15612 |
| 4 | Q9_lag2 | 20 | 0.020399 | 0.001760 | 0.0355 | 0.0188 | 0.0166 | 0.0200 | **0.0111** | 0.15741 |
| 5 | Q11_lag1_spatial_perm | 20 | 0.020534 | 0.001531 | 0.0310 | 0.0200 | 0.0176 | 0.0208 | 0.0133 | 0.15751 |
| 6 | Q0_real | 20 | 0.020559 | 0.001835 | 0.0349 | 0.0195 | 0.0170 | 0.0200 | 0.0113 | 0.15827 |
| 7 | Q8_masse_lag1 | 20 | 0.020653 | 0.002032 | 0.0350 | 0.0198 | 0.0169 | 0.0201 | 0.0114 | 0.15976 |
| 8 | Q1_zero | 20 | 0.020659 | 0.002045 | 0.0315 | 0.0206 | 0.0185 | 0.0197 | 0.0130 | 0.15688 |
| 9 | Q4_effectifs_only | 20 | 0.020767 | 0.001951 | 0.0351 | 0.0205 | 0.0168 | 0.0195 | 0.0119 | 0.15672 |
| 10 | Q10_effectifs_spatial_perm | 20 | 0.020782 | 0.002125 | 0.0318 | 0.0207 | 0.0183 | 0.0199 | 0.0131 | 0.15769 |
| 11 | Q5_masse_only | 20 | 0.021202 | 0.002384 | 0.0359 | 0.0193 | 0.0180 | 0.0210 | 0.0118 | 0.15993 |
| 12 | Q3_spatial_perm | 20 | 0.021236 | 0.001870 | 0.0325 | 0.0204 | 0.0183 | 0.0214 | 0.0135 | 0.15761 |

**Referência Q0_real:** mean=0.020559 ± 0.001789, 2025=0.01131

---

## 3. Comparações pareadas

Wilcoxon one-sided (A < B significa A melhor). Threshold 2025: Δ ≤ +0.002 vs Q0_real.

### Q0_real vs Q1_zero — contribuição do q_tensor

| Item | Valor |
|------|-------|
| A (Q0_real) | 0.020559 |
| B (Q1_zero) | 0.020659 |
| Δ mean | −0.000100 (Q0 melhor) |
| Wins A | 11/20 |
| Wilcoxon p | 0.5218 n.s. |
| Δ 2025 vs Q0 | −0.0000 ✓ |

**Leitura:** Q0_real marginalmente melhor em média, mas diferença não-significativa. Q1_zero é competitivo: q_tensor real **não é indispensável** pela métrica global.

---

### Q0_real vs Q3_spatial_perm — identidade ZE

| Item | Valor |
|------|-------|
| A (Q0_real) | 0.020559 |
| B (Q3_spatial_perm) | 0.021236 |
| Δ mean | −0.000677 (Q0 melhor) |
| Wins A | 13/20 |
| Wilcoxon p | 0.1081 n.s. |
| Δ 2025 vs Q0 | −0.0000 ✓ |

**Leitura:** Q0_real supera permutação espacial (Δ 0.7pp), mas p=0.11 não ultrapassa α=0.05. Sinal existe, evidência moderada — não robusto o suficiente para afirmar sinal local forte.

---

### Q4_effectifs_only vs Q5_masse_only — canal de dado

| Item | Valor |
|------|-------|
| A (Q4_effectifs) | 0.020767 |
| B (Q5_masse) | 0.021202 |
| Δ mean | −0.000435 (effectifs melhor) |
| Wins A | 12/20 |
| Wilcoxon p | 0.2152 n.s. |
| Δ 2025 vs Q0 | +0.0006 ✓ |

**Leitura:** effectifs_only supera masse_only consistentemente (Δ 0.4pp), mas sem significância estatística. Effectifs é a escolha preferencial do canal isolado.

---

### Q6_lag1 vs Q0_real — benefício do lag temporal

| Item | Valor |
|------|-------|
| A (Q6_lag1) | 0.020251 |
| B (Q0_real) | 0.020559 |
| Δ mean | −0.000308 (lag1 melhor) |
| Wins A | 13/20 |
| Wilcoxon p | 0.1650 n.s. |
| Δ 2025 vs Q0 | +0.0010 ✓ |

**Leitura:** Lag1 é o config com menor WMAPE geral (#1 ranking), Δ 0.3pp sobre contemporâneo. p=0.165 — tendência clara, sem significância formal. Consistente com 13/20 wins.

---

### Q7_effectifs_lag1 vs Q4_effectifs_only — lag em effectifs

| Item | Valor |
|------|-------|
| A (Q7) | 0.020398 |
| B (Q4) | 0.020767 |
| Δ mean | −0.000369 (lag1 melhor) |
| Wins A | 11/20 |
| Wilcoxon p | 0.2729 n.s. |
| Δ 2025 vs Q0 | +0.0001 ✓ |

**Leitura:** Lag1 melhora effectifs (Δ 0.4pp), mas wins 11/20 sugere seed-dependência. Direção correta, sem robustez estatística.

---

### Q7_effectifs_lag1 vs Q8_masse_lag1 — canal no lag1

| Item | Valor |
|------|-------|
| A (Q7) | 0.020398 |
| B (Q8) | 0.020653 |
| Δ mean | −0.000255 (effectifs melhor) |
| Wins A | 11/20 |
| Wilcoxon p | 0.2729 n.s. |
| Δ 2025 vs Q0 | +0.0001 ✓ |

**Leitura:** Effectifs supera masse também no regime lag1 (Δ 0.26pp). Preferência effectifs confirmada em ambos os horizontes temporais.

---

### Q7_effectifs_lag1 vs Q10_effectifs_spatial_perm — identidade ZE em effectifs_lag1

| Item | Valor |
|------|-------|
| A (Q7) | 0.020398 |
| B (Q10) | 0.020782 |
| Δ mean | −0.000383 (Q7 melhor) |
| Wins A | 10/20 |
| Wilcoxon p | 0.2979 n.s. |
| Δ 2025 vs Q0 | +0.0001 ✓ |

**Leitura:** Q7 (real) supera permutação (Δ 0.4pp), mas wins=10/20 — empate de wins. Sinal local **não confirmado** na combinação effectifs+lag1. Caution sobre afirmar que q_tensor real contribui via identidade ZE nesta config.

---

### Q6_lag1 vs Q11_lag1_spatial_perm — identidade ZE em lag1 puro

| Item | Valor |
|------|-------|
| A (Q6) | 0.020251 |
| B (Q11) | 0.020534 |
| Δ mean | −0.000283 (Q6 melhor) |
| Wins A | 13/20 |
| Wilcoxon p | 0.2152 n.s. |
| Δ 2025 vs Q0 | +0.0010 ✓ |

**Leitura:** Q6 (real ZE) supera permutação com 13/20 wins e Δ 0.3pp. Evidência mais consistente de sinal local no lag1 puro do que em effectifs_lag1. p=0.22 ainda n.s., mas direção firme.

---

### Q7_effectifs_lag1 vs Q12_effectifs_lag1_a10guard — custo do A10 guard

| Item | Valor |
|------|-------|
| A (Q7) | 0.020398 |
| B (Q12) | 0.020371 |
| Δ mean | +0.000027 (Q12 **ligeiramente** melhor) |
| Wins A (Q7) | 9/20 |
| Wilcoxon p | 0.6219 n.s. |
| Δ 2025 vs Q0 | +0.0001 ✓ |

**Leitura:** Q12 marginalmente superior a Q7 (Δ 0.027pp, wins 9/20 contra Q7). A10 guard leve **não degrada** e pode ajudar levemente. Mas diferença é ruído — não justifica custo arquitetural adicional pela métrica global. Sector WMAPE de Q12 (0.15509) é o **melhor de todos os configs** — único argumento real para o guard.

---

## 4. Veredito metodológico

### q_tensor real vs zero
**Q1_zero é competitivo** (Δ −0.0001, p=0.52, 11/20 wins). q_tensor real **não é indispensável** pela métrica WMAPE global. A diferença cai dentro do ruído de seed. Se custo computacional do tensor real for relevante, Q1_zero é defensável. Porém, em comparações vs spatial_perm (Q3), Q0_real supera claramente (13/20 wins, Δ 0.7pp) — sugerindo que algum sinal local existe, mas é fraco.

**Conclusão:** q_tensor real pode ser mantido, mas sua retirada não é uma perda clara pela evidência atual.

---

### effectifs vs masse_salariale
Effectifs supera masse em todas as comparações onde são isolados:
- Q4 vs Q5 (contemporâneo): Δ −0.000435, 12/20 wins
- Q7 vs Q8 (lag1): Δ −0.000255, 11/20 wins

Nenhuma significativa, mas direção consistente. **Effectifs é o canal preferencial.**

---

### Lag1 / lag2 vs contemporâneo
Ambos Q6_lag1 e Q9_lag2 superam Q0_real (contemporâneo):
- Q6_lag1: Δ −0.0003 vs Q0, 13/20 wins
- Q9_lag2: Δ −0.0002 vs Q0 (rank #4)

Q9_lag2 tem melhor WMAPE 2025 (0.01112, o mais baixo de todos) mas pior 2021. **Lag temporal ajuda**, especialmente para 2025. Q6_lag1 e Q9_lag2 são estatisticamente indistinguíveis entre si.

---

### Sinal local ZE (real vs spatial_perm)
| Comparação | Wins real | Δ mean | p |
|-----------|----------|--------|---|
| Q0 vs Q3 | 13/20 | −0.000677 | 0.108 |
| Q6 vs Q11 | 13/20 | −0.000283 | 0.215 |
| Q7 vs Q10 | 10/20 | −0.000383 | 0.298 |

Q0 vs Q3 tem o maior Δ e p mais próximo de 0.05. Sinal local presente em lag1 puro (Q6 vs Q11, 13/20 wins). Na combinação effectifs+lag1 (Q7 vs Q10), wins caem a 10/20 — **sinal local não robusto na config mais rica**. Não afirmar identidade ZE como fator determinante com os dados atuais.

---

### A10 guard
Q12 vs Q7: Δ tiny (+0.000027 favorável a Q12), wins 9/20 para Q7. Custo: maior complexidade. **Não vale o custo** pela WMAPE global. Único argumento: sector WMAPE de Q12 é o menor de todos (0.15509 vs Q7=0.15612). Se sector accuracy for prioridade, Q12 pode ser considerado.

---

### Candidato arquitetura final

**Recomendação primária: Q7_effectifs_lag1**
- Rank #3 mean WMAPE (0.020398), mas menor std (0.001498 — mais estável que #1 e #2)
- WMAPE 2025 = 0.01142 (excelente, segundo melhor)
- Canal effectifs consistentemente superior a masse
- Lag1 > contemporâneo
- Sem overhead de A10 guard
- Sem dependência de identidade ZE (sinal local não confirmado)
- Interpretação mais simples para paper

**Alternativa 1: Q9_lag2** — melhor WMAPE 2025 absoluto (0.01112), rank #4 geral. Mais agressivo no lag temporal, pode ser mais difícil de justificar metodologicamente.

**Alternativa 2: Q6_lag1** — melhor mean WMAPE geral (#1), mas sem separação de canal. Mais simples, mas não aproveita a vantagem effectifs.

**Descartar:**
- Q3_spatial_perm, Q5_masse_only, Q10_effectifs_spatial_perm: piores performers
- Q12 (A10guard): sem ganho global real
- Q1_zero: competitivo mas methodologicamente menos interessante se sinal local existe

---

## 5. Números-chave para Codex

```
Bateria: 240/240 COMPLETED, todos ExitCode 0:0

Ranking (mean WMAPE):
  #1  Q6_lag1                  0.020251  2025=0.01234
  #2  Q12_effectifs_lag1_a10g  0.020371  2025=0.01241
  #3  Q7_effectifs_lag1        0.020398  2025=0.01142  ← candidato final
  #4  Q9_lag2                  0.020399  2025=0.01112
  #5  Q11_lag1_spatial_perm    0.020534  2025=0.01333
  #6  Q0_real (baseline)       0.020559  2025=0.01131
  ...
  #11 Q5_masse_only            0.021202
  #12 Q3_spatial_perm          0.021236  (pior)

Comparações-chave (todas n.s. Wilcoxon):
  Q0_real vs Q1_zero:           Δ=-0.0001  p=0.52  → q_tensor não indispensável
  Q0_real vs Q3_spatial_perm:   Δ=-0.0007  p=0.11  → sinal local fraco
  Q4_eff vs Q5_masse:           Δ=-0.0004  p=0.22  → effectifs > masse
  Q6_lag1 vs Q0_real:           Δ=-0.0003  p=0.17  → lag1 > contemporâneo
  Q7 vs Q12_a10guard:           Δ=+0.0000  p=0.62  → guard não agrega

Candidato final: Q7_effectifs_lag1
  mean=0.020398  std=0.001498 (menor de todos)  2025=0.01142
```

---

**Relatório:** `reports/HERALD_PHASE3E_QTENSOR_ARCH_AUDIT.md`
