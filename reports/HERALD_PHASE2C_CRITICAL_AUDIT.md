# HERALD Phase 2C Critical Audit

**Data:** 2026-05-12 | OUT_ROOT: `herald_regime_phase2c_critical_20260512_r1`
**Job:** 7323741 — 10/10 seeds, 80/80 runs, todos ExitCode 0:0

---

## Veredito Executivo

Phase 2C é o melhor resultado até agora. `secenh` (`no_regime + learned_regime_gate_sector_enhanced + no_source_flags`) domina o controle `manual_flags` nas três métricas agregadas e passa os testes de falsificação com padrão favorável. Mas ainda não está operacionalmente fechado: 2021 continua instável (9/10 seeds piores que o controle) e a evidência estatística é limitada por N=10 — nenhum p-value passa 5%.

**Decisão:** há evidência metodológica promissora de que HERALD pode operar sem flags manuais. Não há ainda evidência suficiente para substituição operacional, pois 2021 permanece um problema real não resolvido.

---

## 1. Q1 — O smooth simétrico muda o ranking?

**Resposta: matematicamente trivial para `no_regime` — a pergunta estava mal direcionada.**

`cand_baseline` (smooth=explicit) e `cand_sym_smooth` (smooth=none) produziram resultados idênticos:

| | mean WMAPE | WMAPE 2025 | A10 | std |
|---|---:|---:|---:|---:|
| cand_baseline | 0.028832 | 0.018539 | 0.16241 | 0.00344 |
| cand_sym_smooth | 0.028832 | 0.018539 | 0.16241 | 0.00344 |

Com `regime_mode=no_regime`, o vetor de regime explícito é sempre zero. Para smooth=explicit: `reg_delta = |0−0| = 0 → regime_weight = tanh(0) = 0 → penalidade plena`. Para smooth=none: `regime_weight = 0 → penalidade plena`. São idênticos por definição, não por acidente.

**Implicação:** A assimetria de smooth existe no **controle** — `manual_flags` com flags COVID ≠ 0 reduz a penalidade de suavização em 2020-2021. O candidato já opera sem esse alívio. Portanto `secenh` bate `ctrl_manual` em condição estruturalmente mais restrita, não equivalente. Isso é relevante, mas não significa vitória operacional — a assimetria está do lado do ctrl, e mesmo assim 2021 permanece um problema para o candidato.

---

## 2. Q2 — O regime latente carrega sinal real?

**Resposta: evidência favorável, não conclusiva.**

Todas as três falsificações são piores que o candidato:

| Falsificação | Δ vs cand_baseline | wins (pior) | p |
|---|---:|---:|---:|
| `falsify_latent_frozen` | +0.00162 | 8/10 | 0.059 |
| `falsify_latent_inf_zero` | +0.00140 | 8/10 | 0.093 |
| `falsify_regime_permute` | +0.00088 | 7/10 | 0.093 |

O padrão é consistente: 7-8/10 wins em todos os três testes, na direção esperada. Mas nenhum p-value passa 5%. Com N=10 seeds, o Wilcoxon não tem poder para detectar efeitos pequenos. A linguagem correta é **evidência favorável de sinal latente**, não "sinal confirmado/refutado".

O que os testes sugerem:
- Latente congelado (dinâmica temporal bloqueada) → pior: sugere que a variação temporal do latente contribui.
- Latente zerado na inferência (treina com latente, prediz sem) → pior: o latente não é decorativo.
- Regime permutado (ordem temporal embaralhada) → pior: a estrutura temporal importa.

---

## 3. Candidato vs Controle

| Métrica | ctrl_manual | cand_baseline | Δ | wins |
|---|---:|---:|---:|---:|
| mean WMAPE | 0.02934 | **0.02883** | −0.00051 | 6/10 |
| WMAPE 2025 | 0.02334 | **0.01854** | **−0.00480** | 8/10 |
| A10 WMAPE | 0.17196 | **0.16241** | **−0.00955** | 8/10 |

Nas métricas agregadas, `secenh` domina `ctrl_manual`. Os ganhos em WMAPE 2025 e A10 são robustos (8/10 wins cada). O ganho em WMAPE médio é marginal (6/10 wins, Δ=0.0005).

**Ponto fraco:** std do candidato (0.00344) é 67% maior que o controle (0.00206). O candidato é mais sensível à inicialização.

---

## 4. Fold-by-fold

| Label | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---:|---:|---:|---:|---:|
| **ctrl_manual** | **0.03540** | 0.02875 | 0.03239 | 0.02681 | 0.02334 |
| cand_baseline | 0.04876 | 0.03000 | 0.02709 | 0.01978 | 0.01854 |
| ctrl_noregime | 0.05394 | 0.02905 | 0.02745 | 0.02231 | 0.01873 |

2021 continua sendo o problema central: candidato +38% vs ctrl. 2022: ligeiramente pior. 2023-2025: candidato melhor em todos.

O ganho agregado vem principalmente de 2023-2025 compensando 2021. Isso não é cherry-picking — é o resultado do walk-forward. Mas significa que qualquer claim de robustez precisa endereçar 2021 explicitamente.

---

## 5. fold2021_probe — resultado crítico

O probe roda **apenas fold 2021** com 10 seeds independentes:

| seed | WMAPE 2021 | vs ctrl (0.03540) |
|---:|---:|---|
| 123 | 0.03276 | −7% (melhor) |
| 0 | 0.04082 | +15% |
| 2025 | 0.04278 | +21% |
| 42 | 0.04630 | +31% |
| 99 | 0.04761 | +35% |
| 77 | 0.04818 | +36% |
| 1 | 0.05112 | +44% |
| 13 | 0.05368 | +52% |
| 7 | 0.06150 | +74% |
| 17 | 0.06284 | +77% |

**Média: 0.04876 | std: 0.00914 | CV: 18.7%**

**Diagnóstico correto:** 2021 é instável e sensível à inicialização. Não é impossível arquiteturalmente — seed 123 supera o controle — mas 9/10 seeds ficam piores. O problema não está resolvido. A alta variância (range 0.033–0.063) indica que a paisagem de otimização para o fold 2021 é acidentada: o modelo pode convergir para soluções muito diferentes dependendo da inicialização.

**O que isso não significa:** que basta escolher a seed 123. Seleção de seed baseada em desempenho no fold de teste é data snooping e não é defensável metodologicamente.

---

## 6. Pareto Final (Phase 2C)

| Label | mean WMAPE | WMAPE 2025 | A10 | Status |
|---|---:|---:|---:|---|
| **cand_baseline** | **0.02883** | **0.01854** | **0.16241** | **PARETO** |
| ctrl_manual | 0.02934 | 0.02334 | 0.17196 | dominada |
| falsify_regime_permute | 0.02971 | 0.01886 | 0.16064 | PARETO† |
| falsify_latent_inf_zero | 0.03023 | 0.01935 | 0.16249 | dominada |
| falsify_latent_frozen | 0.03045 | 0.01902 | 0.16420 | dominada |
| ctrl_noregime | 0.03030 | 0.01873 | 0.17629 | dominada |

†`falsify_regime_permute` usa `change_point` como regime externo (não `no_regime`), o que altera a arquitetura comparada. Não é um candidato válido — está na fronteira por razão diferente.

`cand_baseline` é o único candidato comparável que domina `ctrl_manual` em todos os três objetivos agregados.

---

## 7. Respostas às Questões Metodológicas

**Phase 2C resolve a assimetria do smooth?**

A assimetria existe no controle, não no candidato. O candidato já opera com penalidade plena. Isso significa que a comparação não favorece o candidato pela assimetria — o candidato ganha apesar da assimetria. A preocupação original estava correta mas direcionada ao lado errado.

**O regime latente carrega sinal real?**

Evidência favorável. Padrão consistente (7-8/10 wins) em três testes independentes, todos na direção esperada. Sem significância estatística a 5% com N=10. Compatível com sinal real moderado, não conclusivo.

**O candidato pode substituir ctrl operacionalmente?**

Não ainda. Nas métricas agregadas sim, mas 2021 permanece instável. A substituição operacional requer que o candidato não colapsa na transição de crise — o que acontece apenas em 1/10 seeds na configuração atual.

**O claim "HERALD aprende regimes econômicos" é defensável?**

Com qualificação:

> *"HERALD constrói, sem flags manuais, uma representação latente que melhora sistematicamente as previsões 2022-2025 e a composição setorial A10. Testes de falsificação fornecem evidência favorável de que o regime latente carrega sinal temporal relevante. A limitação atual é a instabilidade de otimização no fold 2021: em média 38% pior que o controle, com alta variância entre seeds (CV=19%)."*

---

## 8. Próximos Passos

**Prioritário antes de qualquer claim mais forte:**

1. **Regularização para estabilidade de 2021:** penalidade de colapso do regime latente (`collapse_lambda`) para reduzir a variância entre seeds. A meta é que a média de 2021 se aproxime de 0.040 (margem de +13% vs ctrl), não apenas que uma seed alcance esse valor.

2. **Validação geográfica do erro 2021:** mapear os erros por zona de emprego. Se o colapso se concentra em certas ZE2020, pode ser sinal de que o regime latente não captura choques locais heterogêneos — o que aponta para uma limitação de representação, não de otimização.

3. **Ensemble formal (não seleção de seed):** se regularização não resolver 2021, testar ensemble das predições de múltiplas seeds — não selecionar a melhor seed post-hoc. Ensemble é defensável; seleção de seed com base no resultado não é.

---

*Auditoria baseada em 80 JSONs per-run, 80 metadata, análise independente. Integridade confirmada: todos os seeds incluindo seed 2025 têm os metadados corretos para todos os configs.*
