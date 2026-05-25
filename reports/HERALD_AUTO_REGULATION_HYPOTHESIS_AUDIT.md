# HERALD — Auditoria Crítica da Hipótese de Auto-Regulação Latente

**Date:** 2026-05-20
**Scope:** auditor interno que regule o regime latente (dimensão ativa, abertura/poda, confiança).
**Inputs:** Phase 2K/2L results, `train_herald_v7.py`, `herald_regime_modes.py`, literatura.

---

## 0. Resumo executivo

A hipótese de **auto-regulação do regime latente sem flags manuais** é metodologicamente legítima e está bem documentada em literatura. Mas a forma atual implementada no HERALD (`mask_logits` global + hard-concrete + L1 leve) **não constitui auto-regulação real** — é uma simples atenuação multiplicativa estática. A Phase 2L mostrou três fatos críticos:

1. **A máscara nunca podou nenhuma dimensão** (effective_dim = ceiling em 80/80 runs HC+AUTO);
2. **HC5 obteve melhor mean WMAPE**, mas o ganho não vem da seleção de dimensões — vem do efeito colateral de regularização (passos latentes ~3× menores que L3_gate);
3. **2021 piorou em HC5** (p=0.49), o que invalida a leitura de "HC5 = melhor candidato" como conclusão científica.

**O caminho geral está correto**: rejeitar flags manuais e procurar auto-regulação é defensável. Mas o **mecanismo atual está mal dimensionado e mal posicionado**, e algumas das ideias mais ambiciosas (IBP nonparamétrico, MoE com router, Bayesian capacity) são **inadequadas para T=14**.

**Veredito:** continuar a direção, **reformular o mecanismo**, evitar overkill.

---

## 1. O que está correto no nosso caminho

| Item | Por quê é defensável |
|---|---|
| Não usar flags manuais | Phase 2J mostrou que no-flags SIDE2 bate flags SIDE2 limpo. Já validado empiricamente. |
| Procurar mecanismo interno antes de agente externo | Princípio de parcimônia. Adicionar agente é incremento metodológico maior. |
| Tratar `latent_dim=3` como hyperparam, não como achado | Já documentado no README da Phase 2K. Atitude correta. |
| Manter L3_gate como referência defensável | L3_gate venceu em 2021 e tem menor variância. Não abandonar sem evidência pareada significativa. |
| Phase 2L cobrir blocos ortogonais (fixed dim, auto-mask, HC, step cap, A10) | Boa cobertura do espaço de design. |

---

## 2. O que está metodologicamente fraco

### 2.1. A máscara atual não auto-regula. Ela atenua.

Código (`train_herald_v7.py:108-110`):

```python
if auto_mask:
    self.mask_logits = nn.Parameter(torch.zeros(self._latent_regime_dim))
```

Problemas:

1. **Sem dependência do input.** `mask_logits` é um `Parameter` global. Não condiciona em estado do mercado, ano, regime. Não pode "abrir mais capacidade quando o regime muda" — é estática.
2. **A máscara multiplica `latent_regime_t`** *depois* do MLP que já produziu o vetor latente. Reduz amplitude por dimensão, mas o MLP pode compensar aumentando os pesos da camada final. Isso é **redundância recuperável** — o modelo escapa da penalidade ajustando pesos a montante, não desligando dimensões.
3. **Hard-concrete penalty com offset enganoso.** Linha 197: `offset = beta * log(-gamma/zeta) ≈ 0.667 * log(0.1/1.1) ≈ -1.60`. O penalty term é `sigmoid(logits - offset)`. No início (logits=0), penalty ≈ `sigmoid(1.60) = 0.832`. A penalidade não cresce monotonicamente com a abertura da máscara — ela já começa saturada. Isso quebra a interpretação L0 "espera-se que λ pequeno produza poucas ativações".
4. **λ=0.005 absoluto, sem annealing.** O paper original de Louizos et al (2018) recomenda annealing de β (temperatura) e/ou λ, especialmente em redes pequenas. HERALD usa β fixo = 2/3 e λ fixo. Sem schedule.

**Conclusão:** o experimento HC5/HC8/AUTO* da Phase 2L não testou "HERALD pode escolher dimensão". Testou "HERALD com vetor latente fixo multiplicado por sigmoid(parâmetro escalar não-condicionado)". A inferência "HERALD não consegue auto-regular" é prematura — o **mecanismo testado não permite auto-regulação real**.

### 2.2. O regime é compartilhado globalmente. T=14 não suporta seleção bayesiana de capacidade.

`herald_regime_modes.py` constrói `regime[ti]` por **ano**, não por zona. O latente também é produzido a partir de estatísticas globais (`e_t.mean`, `e_t.std`) e é compartilhado entre as 280 zonas. Portanto:

- N efetivo para seleção de dimensão latente = número de anos com sinal regime distinguível ≈ **14 (2012-2025)** com talvez 3-4 anos verdadeiramente discriminantes (2020, 2021, 2022).
- Procedimentos nonparamétricos (IBP, Beta-Bernoulli, Dirichlet) precisam de N >> 50 para identificar número de features. **IBP/DP em T=14 é inviável.**
- Critério informativo (BIC, ELBO comparison) sobre número de dimensões pode operar com T=14 *se a comparação é entre 2-3 valores de K e cada K é refittado várias seeds*. Isso é exatamente o que Phase 2K fez. Mas a "auto-mask" não é seleção bayesiana — é regularização suave.

### 2.3. Confusão entre dois objetivos distintos

A hipótese mistura duas coisas:

| Objetivo A: **escolha de dimensão** | Objetivo B: **modulação adaptativa de confiança** |
|---|---|
| Quantas dim usar globalmente | Quando confiar no regime aprendido vs sinal Ridge |
| Decisão de arquitetura | Decisão por ano/zona/setor |
| Group lasso, L0, BIC | Confidence-gated mixing, uncertainty-aware gating |
| Já testado em Phase 2K/2L | Parcialmente coberto por alpha gate |

Tratar ambos como "um auditor interno" obscurece qual problema está sendo resolvido. Recomendo **separar explicitamente** A e B nas próximas baterias.

### 2.4. HC5_l0_005 vs L3_gate — leitura cuidadosa

Da Phase 2L fine audit:

- HC5 mean = 0.02035 vs L3 = 0.02142 (Δ=-0.00106), **p=0.1055 (não significativo)**.
- Wins pareados HC5 vs L3: **6/10 seeds**. Isso é praticamente coin-flip.
- HC5 vs L3 em **2021**: HC5 PIOR (+0.00203, wins=4/10).
- Ganho total de HC5 vem de **2025** (Δ=-0.00358), que é o ano mais fácil.
- HC5 tem `latent_step_2020→2021` (fold 2021) ≈ 0.50 vs L3=1.48 → HC5 é mais inerte. Pode ser sub-reação a COVID, não vantagem genuína.

Reportar HC5 como "melhor candidato preliminar" sem qualificação leva ao mesmo erro da Phase 2D: confundir mean WMAPE com robustez.

---

## 3. Literatura relevante

Liguei cada item à decisão concreta no HERALD. Não copiei a literatura inteira.

### 3.1. Sparsity estruturada / seleção de capacidade

- **Louizos, Welling, Kingma (2018), "Learning Sparse Neural Networks through L0 Regularization", ICLR.** https://arxiv.org/abs/1712.01312
  Origem do hard-concrete. **Recomenda annealing, λ grande no início, e penaliza grupos estruturados (filtros inteiros), não escalares individuais.** O HERALD aplica hard-concrete a 5 escalares, sem annealing, com λ=0.005. Implementação minimalista — não a versão do paper.

- **Wen, Wu, Wang, Chen, Li (NeurIPS 2016), "Learning Structured Sparsity in Deep Neural Networks".** https://arxiv.org/abs/1608.03665
  Group lasso para podar canais/filtros. Penaliza a **norma L2 do grupo**, não escalares. Análogo correto para HERALD: penalizar `||W_latent[:, d]||_2` no MLP que produz `latent_regime_t[d]`, não apenas a máscara. Isso força podar a **fonte** da dimensão, não só o seu output.

- **Yuan, Lin (2006), "Model Selection and Estimation in Regression with Grouped Variables", JRSS-B.** Doi 10.1111/j.1467-9868.2005.00532.x
  Fundamento estatístico do group lasso. Diretamente aplicável a podar uma dimensão latente inteira.

- **Frankle, Carbin (ICLR 2019), "The Lottery Ticket Hypothesis".** https://arxiv.org/abs/1803.03635
  Justifica pruning iterativo (treinar denso → podar → retreinar). Possível mas custoso para HERALD; usar como fallback se outras vias falharem.

### 3.2. Estimação variacional / dropout estocástico

- **Gal, Hron, Kendall (NeurIPS 2017), "Concrete Dropout".** https://arxiv.org/abs/1705.07832
  Aprende taxa de dropout por unidade via concrete relaxation. Penalidade KL contra prior Bernoulli. **Mais informativa que máscara escalar**: dropout rate por dimensão tem interpretação probabilística limpa. Recomendado para HERALD.

- **Kingma, Salimans, Welling (NeurIPS 2015), "Variational Dropout and the Local Reparameterization Trick".** https://arxiv.org/abs/1506.02557
  Base teórica. Útil para entender por que λ fixo sem KL prior gera sub-determinação.

- **Molchanov, Ashukha, Vetrov (ICML 2017), "Variational Dropout Sparsifies Deep Neural Networks".** https://arxiv.org/abs/1701.05369
  Mostra que variational dropout induz sparsity automática. Mais agressivo que hard-concrete em redes pequenas. Possível alternativa.

### 3.3. Nonparametric Bayesian latent features

- **Griffiths, Ghahramani (JMLR 2011), "The Indian Buffet Process: An Introduction and Review".** https://www.jmlr.org/papers/v12/griffiths11a.html
  Permite número de features latentes "crescer com os dados". **Não aplicável a T=14.** Inferência IBP requer N grande para identificar K com confiança. Descartar.

- **Nalisnick, Smyth (2017), "Stick-Breaking Variational Autoencoders".** https://arxiv.org/abs/1605.06197
  Versão variacional com truncamento (K_max fixo). Mais tratável que IBP puro. Ainda assim, T=14 é insuficiente para estimar Beta(α) sobre as varas. Descartar para esta escala.

### 3.4. Dynamic capacity / adaptive computation

- **Graves (2016), "Adaptive Computation Time for Recurrent Neural Networks".** https://arxiv.org/abs/1603.08983
  Modelo decide quantos "passos de pensamento" por timestep. Análogo: HERALD poderia decidir quantas dimensões latentes "ativar" *por ano*, condicional ao input. Promissor mas complexo. Usar como Phase 3+ se Phase 2M/N validar a direção.

- **Shazeer et al (ICLR 2017), "Outrageously Large Neural Networks: The Sparsely-Gated Mixture-of-Experts Layer".** https://arxiv.org/abs/1701.06538
  MoE com routing. Inadequado em T=14 sem MoE-load-balancing problema severo: router subaprende.

- **Fedus, Zoph, Shazeer (JMLR 2022), "Switch Transformer".** https://arxiv.org/abs/2101.03961
  Top-1 routing simplifica MoE. Mesmo argumento: T=14 não justifica overhead arquitetural.

### 3.5. Two-level regime (discreto + contínuo)

- **Fox, Sudderth, Jordan, Willsky (2008-2011), "Sticky HDP-HMM" / "BP-AR-HMM".** https://arxiv.org/abs/1102.1248
  HMM bayesiano com regimes discretos + emissões. Mais alinhado com narrativa "regime econômico". Computacionalmente pesado mas pode rodar em T=14 dado que regimes plausíveis ≤ 3.

- **Hamilton (1989), "A New Approach to the Economic Analysis of Nonstationary Time Series and the Business Cycle", Econometrica.** Clássico. Markov-switching. Diretamente publicável em literatura econômica francesa. Vale considerar como wrapper sobre HERALD.

### 3.6. Uncertainty-aware gating

- **Kendall, Gal (NeurIPS 2017), "What Uncertainties Do We Need in Bayesian Deep Learning for Computer Vision?"** https://arxiv.org/abs/1703.04977
  Distingue aleatória e epistêmica. Análogo: gate alpha do HERALD poderia ponderar pela incerteza do graph-residual. Útil se quiseres tornar alpha mais "inteligente" sem mexer na dimensão latente.

---

## 4. Mecanismos recomendados (em ordem de prioridade)

### Tier 1 — implementação pequena, ganho informacional alto

1. **Hard-concrete com λ alto (0.05–0.20) + annealing de β.**
   Custo: trocar `_hard_concrete_beta` por scheduler linear `β: 2/3 → 1/3 ao longo do treino`; expor `--latent-dim-l0-lambda 0.05/0.10/0.20`. Tempo: ~2h código.
   Critério de sucesso: ao menos um config produz `effective_dim < ceiling` em ≥ 50% das seeds **sem perder mean WMAPE** vs L3_gate.
   **Justificativa:** testa se "hard-concrete falhou por λ fraco" é a explicação correta. Falsificação direta da Phase 2L.

2. **Group lasso sobre os pesos do MLP que produz `latent_regime`.**
   Penalizar `Σ_d ||W_out[:, d]||_2`. Isso pune a *fonte* da dimensão, não só seu output. λ entre 1e-4 e 1e-2.
   Custo: ~3h código. Inclui um termo extra no loss.
   Critério: dimensões com norma de coluna < 1e-3 são consideradas podadas.

3. **Concrete Dropout por dimensão latente.**
   Aprende uma taxa de dropout `p_d` para cada uma das K dimensões via concrete relaxation com prior KL. Mais informativo que hard-concrete: posterior interpretável.
   Custo: ~4h código (módulo separado).

### Tier 2 — mudança estrutural, vale se Tier 1 não destravar

4. **Two-level regime: discreto sticky-HDP-HMM (K≤3) sobre o sinal global × contínuo HERALD por zona.**
   O HMM define o estado macroeconômico (calmo / choque / recuperação) e o latente HERALD modula condicional ao estado. Mais perto da narrativa econômica francesa. Caminho publicável em econometria.
   Custo: ~1 semana (incluindo `pomegranate` ou `hmmlearn`).
   Risco: complica falsificações causais.

5. **Uncertainty-gated alpha.**
   Calcular `var(graph_residual)` via dropout MC ou ensembling, e ponderar `alpha` por isso. Resolve objetivo B (confiança) sem mexer em dim latente.
   Custo: ~3h.

### Tier 3 — só se Tier 1+2 produzirem resultados ambíguos

6. **Lottery ticket-style pruning iterativo.** Treinar com K=8, podar dimensões com menor norma a cada epoch, retreinar.
   Caro mas defensável metodologicamente.

---

## 5. Mecanismos descartados (com justificativa)

| Mecanismo | Por quê descartar para HERALD agora |
|---|---|
| **Indian Buffet Process** | T=14. Inferência IBP requer N grande. Insolvente. |
| **Stick-breaking VAE** | Idem. Truncamento ainda exige estimar Beta(α) confiavelmente. |
| **Sparse MoE (Switch / Shazeer)** | Overhead arquitetural; router não consegue aprender em T=14 com 280 zonas; load balancing acrescenta loss extra que compete com WMAPE. |
| **Adaptive Computation Time** | Demasiado complexo. Não justificável em paper antes de validar Tier 1. |
| **Bayesian nonparametric latent features puros** | Mesma razão: tamanho amostral. |
| **Reinforcement-learned gating (RL para alpha)** | Variance + sample inefficiency em T=14. Não publicável. |
| **Agente externo (LLM, decisor)** | Overkill antes de testar mecanismos diferenciáveis simples. |
| **Variational dropout (Molchanov)** | Funciona mas é mais agressivo que necessário; concrete dropout é melhor compromisso. |

---

## 6. O mecanismo afeta só alpha ou também o grafo?

Lendo `train_herald_v7.py:158-168` e `:270-280`:

- Variantes `learned_regime_gate*`: `latent_regime_t` entra **apenas no alpha_gate**.
- Variantes `learned_regime_both*` e `learned_regime_graph`: `latent_regime_t` entra **também em `_dynamic_adj`** via `latent_proj_q/k`.

A máscara `_latent_dim_mask` é aplicada uma única vez (`train_herald_v7.py:259`) **antes** de qualquer uso. Portanto:

- Em variantes `_gate`: a auto-regulação afeta só a decisão local/grafo (objetivo B implícito).
- Em variantes `_both`: a auto-regulação afeta também a construção da dynamic_adj. **Risco maior**: podar uma dimensão também muda o grafo. Benefício: mecanismo mais expressivo se funcionar.

### Recomendação

- **Tier 1 baterias rodam só em `_gate`** (mesmo terreno da Phase 2L).
- Se Tier 1 destravar pruning real, então repetir em `_both` com mesmo λ/schedule. **Não misturar `_both` + nova auto-regulação na mesma bateria** — duas variáveis confundem leitura.

---

## 7. Bateria experimental proposta — Phase 2M

**Nome:** `phase2m_latent_autoreg_strong`
**Goal:** falsificar a explicação "auto-regulação falhou por λ fraco". Testar concrete dropout e group lasso. Manter blocks A10 e step06 fora desta bateria.

### Configs (11 × 10 seeds = 110 runs)

| Label | Dim_ceil | Mask type | λ (L0/group) | β | Annealed | Notes |
|---|---:|---|---:|---:|---|---|
| `L3_gate` | 3 | none | 0.0 | — | — | reference (re-run from Phase 2L for paired) |
| `HC5_l0_005` | 5 | hard_concrete | 0.005 | 2/3 | no | reference (re-run for paired) |
| `L4_a10g` | 4 | none | 0.0 | — | — | reference for A10 |
| `HC5_l0_020` | 5 | hard_concrete | 0.020 | 2/3 | no | 4× λ |
| `HC5_l0_050` | 5 | hard_concrete | 0.050 | 2/3 | no | 10× λ |
| `HC5_l0_100` | 5 | hard_concrete | 0.100 | 2/3 | no | 20× λ |
| `HC5_l0_050_anneal` | 5 | hard_concrete | 0.050 | 2/3 → 1/3 | yes | annealed β |
| `HC8_l0_050` | 8 | hard_concrete | 0.050 | 2/3 | no | larger ceiling, strong λ |
| `GL5_005` | 5 | group_lasso on `latent_regime[-2].weight` cols | 0.005 | — | — | group lasso |
| `GL5_020` | 5 | group_lasso | 0.020 | — | — | stronger |
| `CD5_kl_001` | 5 | concrete_dropout (KL prior `Beta(0.5,0.5)`) | KL_w = 0.001 | 0.1 | — | concrete dropout |

### Falsificações

- **`HC5_l0_100`** (λ 20× maior): se ainda assim `effective_dim = 5`, falsifica a hipótese "λ fraco". Conclusão: a arquitetura da máscara é o problema, não a calibração.
- **Re-run de L3_gate e HC5_l0_005** na mesma bateria: garante paired comparison limpa contra Phase 2L sem cross-batch noise (seed/env).

### Métricas obrigatórias por config

| Métrica | Como medir |
|---|---|
| mean WMAPE 2021-2025 | já no JSON |
| WMAPE 2021 ranking | mesmo |
| WMAPE 2025 ranking | mesmo |
| A10 sector_wmape_mean | mesmo |
| effective_dim mean/min/max/std | conta de mask_values > 0.05 |
| seed std (mean WMAPE) | std entre seeds |
| latent_step_2020→2021 (fold 2021) | já no JSON |
| paired wins vs L3_gate, HC5_l0_005, L4_a10g | + Wilcoxon p |
| group-lasso column norms (configs GL) | adicionar ao JSON |

### Critério de vitória (decisão Phase 2M)

Para promover qualquer config a "melhor candidato científico":

- **Tem que reduzir effective_dim em ≥ 50% das seeds**, OU
- Tem que melhorar paired vs L3_gate **simultaneamente em mean WMAPE E em 2021 E com p < 0.05 Wilcoxon**.

Se nenhum config satisfaz, conclusão será: **HERALD não consegue auto-regular sob mecanismos atuais e literatura testada**. Pular para Tier 2 (sticky-HDP-HMM) ou aceitar L3_gate como referência operacional.

### Custo

11 × 10 = 110 runs. ~30 GPU-hours considerando ~16 min/run histórico. Cabe em uma noite de fila.

---

## 8. Riscos de interpretação

1. **Variance bias.** Algumas configs HC têm std ~2× L3_gate. Um ganho de mean é fácil de obter aumentando variance. Sempre reportar paired wins + Wilcoxon, nunca só mean.

2. **2025 ≠ vitória científica.** 2025 é o ano mais fácil. Ganhar 2025 e perder 2021 não é avanço — é re-distribuição. Phase 2L confirma isso para HC5.

3. **Effective_dim = ceiling não prova "modelo precisa de K dim".** Prova que "o mecanismo testado não conseguiu desligar dimensões". Distinção crítica para o paper.

4. **Cherry-picking de comparação.** L3_gate, HC5, L4_a10g cada um vence em uma dimensão. Apresentar todos os três sempre, não escolher o que favorece narrativa.

5. **T=14 amostra todas as configurações simultaneamente.** Não há split entre "set de seleção de modelo" e "set de validação". Reportar resultados como "audit interno", não como "validação out-of-sample da seleção arquitetural".

6. **Confusão objetivo A (dim) vs B (confiança).** Phase 2M ataca só A. Objetivo B (uncertainty-gated alpha) é Phase 2N separada.

---

## 9. Veredito final

**Continuar a direção, reformular o mecanismo, manter expectativas calibradas.**

- ✅ A ideia de auto-regulação interna é metodologicamente legítima.
- ✅ Há literatura sólida e implementações testáveis (hard-concrete annealed, group lasso, concrete dropout).
- ❌ O experimento atual (Phase 2L) não testou auto-regulação real; testou regularização suave com λ subdimensionado.
- ❌ Algumas ideias (IBP, MoE, ACT) são inadequadas para T=14 e devem ser explicitamente descartadas no paper.
- ⚠️ Mesmo se Phase 2M validar pruning, HC5 só vence ciência se ganhar paired e 2021. Hoje não ganha.

### Sequência recomendada

1. **Phase 2M (proposta acima):** falsificar "λ fraco", testar group lasso e concrete dropout. ~1 semana.
2. Se Tier 1 destravar pruning → **Phase 2M-bis:** repetir top-2 mecanismos em `_both` variant para testar efeito no grafo.
3. Se Tier 1 falhar limpo (todos λ altos sem pruning) → **publicar como negative result**: "HERALD com latente compartilhado globalmente não admite auto-regulação simples sob mecanismos diferenciáveis testados; L3_gate fixo é o ponto operacional defensável; agente externo ou two-level discreto+contínuo (sticky-HMM) ficam como direção futura."
4. **Phase 2N (separada):** uncertainty-gated alpha (objetivo B). Não misturar com dim selection.

### O que NÃO fazer

- Não adicionar agente LLM/RL antes de Phase 2M.
- Não rodar bateria de 20+ configs misturando dim + sector + step. Phase 2L já fez isso e a leitura ficou confusa.
- Não promover HC5_l0_005 a "melhor candidato" em texto científico sem qualificação (p=0.105 paired, 2021 pior).
- Não claim "HERALD self-regulates" sob nenhuma circunstância nos dados atuais.

---

## 10. Checklist de validação para o próximo experimento

- [ ] λ alto (≥ 0.05) testado com hard-concrete
- [ ] Annealing de β implementado
- [ ] Group lasso adicionado como falsificação alternativa
- [ ] Concrete dropout testado como segundo caminho
- [ ] Paired comparison vs L3_gate + HC5_l0_005 + L4_a10g em TODA tabela
- [ ] Effective_dim reportado com min/max/std, não só mean
- [ ] 2021 e 2025 reportados separadamente, não só mean
- [ ] Wilcoxon p reportado em cada paired
- [ ] Falsificação `HC5_l0_100` rodando para fechar "λ fraco" como explicação
- [ ] Custo total ≤ ~30 GPU-hours

Se este checklist estiver completo e o veredito for negativo, **publicar como negative result é um resultado válido**.
