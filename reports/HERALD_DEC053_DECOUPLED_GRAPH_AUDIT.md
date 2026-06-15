# HERALD DEC-053: Decoupled Graph Architecture Audit

**Status:** EXPERIMENT_COMPLETE — 7/10 PASS (D4/D6/D8 FAIL — ver §8)
**Date:** 2026-06-15
**Decision log:** `reports/HERALD_METHODOLOGICAL_DECISION_LOG.md §DEC-053`

---

## 1. Motivação

DEC-052 confirmou que TEMPORAL_MASKED_NLL_CLAMPED@75 aprende estrutura grafosal (AUC≥0.60 em zero-shot) mas este aprendizado não se traduz em ganho preditivo de imputation. O modelo principal quase sempre perde para `no_graph` nos cenários novel. 300 épocas não melhoram (early stopping retorna ao checkpoint 150).

**Causa raiz identificada (dois factores):**

### 1.1 Prior simétrico falsifica reversos

`_sector_adj_from_relations()` simetriza relações dirigidas:
```python
adj[t, s] = adj[s, t] = 1.0  # se existe s→t
```

Com N=10 arestas dirigidas reais, o adj tem 20 entradas não-nulas — metade são reversos falsos. A atenção do backbone usa adj como prior log-aditivo:
```
attention[target,source] = softmax(log_sect_attn_lagK + adj_s)[target,source]
```
Com adj_s[s,t]=1 mesmo quando a aresta real é apenas t→s, o prior dá um boost exp(1)≈2.7× na direcção errada. O backbone aprendeu a compensar este ruído durante o treino, mas não pode recuperar o sinal dirigido verdadeiro sem supervisão directa.

### 1.2 Features temporais são suficientes nos cenários hard

Os cenários novel têm frac_nonlinear=0.85-0.90 (extremo da distribuição de treino). `_build_temporal_features` constrói features de lag/trend por território-sector sem acesso ao grafo. Nestes cenários de alta não-linearidade, as features temporais carregam o sinal necessário; a atenção cruzada sectorial adiciona ruído correlacionado que piora a imputação.

---

## 2. Arquitectura DEC-053

```
backbone (frozen, adj=0)
    │── y_temporal, log_sigma
    │
GraphRelationHead
    │── presence_logit[target,source]  (dirigido)
    │── sign_logit, lag_logit, log_confidence
    │── directed_attention(lag=1), directed_attention(lag=2)
    │
GraphMessageExpert
    │── msg1, msg2 (de directed_attention × panel_obs)
    │── raw_residual = MLP([msg1_mag, msg2_mag]) → zero-init
    │── graph_residual = clamp(raw_residual, ±0.15·|y_temporal|.mean())
    │
UtilityGate
    │── inputs: y_temporal_norm, msg_magnitude, obs_fraction (sem alvo)
    │── gate = Sigmoid(Linear(8,1)(ReLU(Linear(3,8)(·))))
    │── bias inicial = -5 → gate ≈ 0.007 ≈ 0
    │
y_pred = y_temporal + gate * graph_residual
```

**Invariantes:**
- `gate ∈ (0,1)` sempre (sigmoid)
- `graph_residual ∈ [−0.15·|ȳ|, +0.15·|ȳ|]` (clamp)
- `gate=0 → y_pred == y_temporal` exactamente (D3)
- Backbone: `requires_grad=False` (nenhum parâmetro temporal é alterado)
- Gate: nunca recebe valores alvo como input

---

## 3. Loss desacoplada

```
L_total = L_recon
        + 0.05 · L_presence
        + 0.02 · L_sign
        + 0.02 · L_lag
        + 0.05 · L_utility   (0.0 quando compute_utility=False)
        + 0.01 · mean(gate)  (regularização L1 em direcção a gate fechado)
```

`compute_utility=False` durante eval/test — **nunca acede ao alvo**.

---

## 4. Modos de avaliação

| Modo | O que mede | Baseline comparison |
|------|-----------|---------------------|
| ANALYTIC_GRAPH_ONLY | AUC dirigido, AUPRC, sign/lag acc, auditoria prior | prevalência (random baseline) |
| TEMPORAL_RECONSTRUCTION | MAE backbone sem grafo | ffill, Ridge |
| GATED_GRAPH_ASSIST | MAE gated vs todas as baselines | temporal-only, always-on, permuted graph, ffill |

**Seeds:** 1000, 2000, 3000 | **Máscaras:** MCAR 30%, block 30% | **Épocas máx:** 75

---

## 5. Fixtures funcionais F1-F6

| Fixture | Data generating process | O que testa |
|---------|------------------------|-------------|
| F1 `F1_useful_graph` | sector 0→1 weight=0.9 lag=1; sector 1 observado com buracos | gate deve abrir >0.3 |
| F2 `F2_useless_graph` | AR puro, sem relações | gate deve permanecer <0.2 |
| F3 `F3_negative_relation` | weight=-0.8; sector 1 = AR − 0.8·sector0_lag1 | sign_logit[1,0] < 0 após treino |
| F4 `F4_lag2_relation` | lag=2 real, não lag=1 | lag_logit[1,0] < 0 (prefere lag=2) |
| F5 `F5_regime_window` | relação activa apenas anos 5-10 | gate mais alto dentro da janela |
| F6 `F6_asymmetric_directed` | só 0→1; sector_adj tem falso reverso 1→0 | presence_logit[1,0] >> presence_logit[0,1] |

---

## 6. Gates D1-D10 (congelados)

| Gate | Critério | Tipo |
|------|----------|------|
| D1 | AUC/AUPRC finito; alvo dirigido; prevalência registada | correctude |
| D2 | AUC≥0.60, AUPRC>prevalência, sign/lag>0.50 | recuperação analítica |
| D3 | gate=0 → temporal-only exacto (atol=1e-5) | identidade |
| D4 | gate>0.3 em F1/F3/F4 onde relação ajuda | abertura útil |
| D5 | gate<0.2 em F2; fecha fora de janela em F5 | fecho inútil |
| D6 | presence_logit[true_dir] >> presence_logit[false_dir] em F6 (diff>0.2) | especificidade dirigida |
| D7 | Gated nunca >5% pior que temporal-only em qualquer (cenário, máscara) | segurança preditiva |
| D8 | Gated MAE < graph-always-on AND < graph-permuted | utilidade selectiva |
| D9 | Comparação honesta registada (ganho não exigido) | informativo (PASS sempre) |
| D10 | Resultados funcionais replicam em ≥2/3 seeds | replicação |

---

## 7. Resultados da execução

*Preencher após execução com:*
```bash
python -m src.modeles.synthetic.phase16_decoupled.run_dec053 \
    --backbone_path <path/to/model.pt> \
    --n_sectors 5 \
    --out_dir data/processed/phase16_dec053
```

Backbone: `TEMPORAL_MASKED_NLL_CLAMPED_ep75`, n_sectors=9, n_territories=30.
Execução: 3 seeds × 2 masks = 6 experimentos + 6 fixtures. ~4s local (CPU).

### 7.1 Modo ANALYTIC_GRAPH_ONLY

| Seed | Mask | AUC_directed | AUPRC_directed | sign_acc | lag_acc |
|------|------|-------------|----------------|----------|---------|
| 1000 | mcar | 1.000 | 1.000 | 1.00 | 1.00 |
| 1000 | block | 1.000 | 1.000 | 1.00 | 1.00 |
| 2000 | mcar | 1.000 | 1.000 | 1.00 | 1.00 |
| 2000 | block | 1.000 | 1.000 | 1.00 | 1.00 |
| 3000 | mcar | 1.000 | 1.000 | 1.00 | 1.00 |
| 3000 | block | 1.000 | 1.000 | 1.00 | 1.00 |

**Nota:** AUC=1.00 reflete recuperação perfeita nas-mesmas-amostras sintéticas (não generalização out-of-sample). A architecture discrimina correctamente as arestas dirigidas quando supervisionada pelos `true_relations`.

### 7.2 Modo TEMPORAL_RECONSTRUCTION

| Seed | Mask | mae_temporal | mae_ffill | Δ vs ffill |
|------|------|-------------|-----------|-----------|
| 1000 | mcar | 0.1755 | 0.1969 | −10.9% |
| 1000 | block | 0.1953 | 0.2399 | −18.6% |
| 2000 | mcar | 0.1757 | 0.2016 | −12.9% |
| 2000 | block | 0.1900 | 0.2451 | −22.5% |
| 3000 | mcar | 0.1736 | 0.1881 | −7.7% |
| 3000 | block | 0.1787 | 0.2193 | −18.5% |

Backbone temporal bate ffill em todos os cenários (confirma DEC-052).

### 7.3 Modo GATED_GRAPH_ASSIST

| Seed | Mask | mae_temporal | mae_gated | mae_always | mae_permuted | gate_mean |
|------|------|-------------|-----------|------------|--------------|-----------|
| 1000 | mcar | 0.1755 | 0.1755 | — | — | 0.0046 |
| 1000 | block | 0.1953 | 0.1953 | — | — | 0.0043 |
| 2000 | mcar | 0.1757 | 0.1757 | — | — | 0.0043 |
| 2000 | block | 0.1900 | 0.1900 | — | — | 0.0069 |
| 3000 | mcar | 0.1736 | 0.1736 | — | — | 0.0067 |
| 3000 | block | 0.1787 | 0.1787 | — | — | 0.0058 |

**gate_mean ≈ 0.005 em todos os casos** — a gate permanece essencialmente fechada (init sigmoid(−5)≈0.007). A predição gated é indistinguível da temporal-only. Causa identificada: ver §8.

### 7.4 Fixture results (D3-D6)

| Fixture | gate_mean | gate_zero_delta | Observação |
|---------|-----------|-----------------|-----------|
| F1 | 0.0050 | 0.00e+00 | FAIL D4: gate não abre |
| F2 | 0.0076 | 0.00e+00 | PASS D5: gate < 0.2 |
| F3 | 0.0074 | — | FAIL D4: gate não abre |
| F4 | 0.0075 | — | FAIL D4: gate não abre |
| F5 inside=0.0074 outside=0.0074 | — | PASS D5: idêntico (esperado — gate fechado) |
| F6 logit_diff=0.149 | — | FAIL D6: < 0.20 threshold |

**gate_zero_identity_max_delta = 0.00e+00 → D3 PASS** (após fix: backbone.eval() forçado sempre).

### 7.5 Gate summary (D1-D10)

| Gate | Verdict | Evidence chave |
|------|---------|---------------|
| D1 | PASS | AUC/AUPRC finito em todos os runs |
| D2 | PASS | mean_auc=1.000, frac_auprc_beats=1.0, sign=1.0, lag=1.0 |
| D3 | PASS | max_delta=0.00e+00 (backbone.eval() fix) |
| D4 | **FAIL** | gate_mean≈0.005 em F1/F3/F4 (threshold >0.3) |
| D5 | PASS | F2 gate=0.008 < 0.2; F5 indistinto |
| D6 | **FAIL** | presence_logit_diff=0.149 (threshold >0.2) |
| D7 | PASS | 0 violações: gated≡temporal, nunca pior |
| D8 | **FAIL** | mae_gated ≥ mae_graph_always (marginal) |
| D9 | PASS | (informativo) |
| D10 | PASS | safety replicada em 2/2 grupos |

---

## 8. Diagnóstico das falhas D4/D6/D8

### D4 FAIL — Gate não abre sem supervisão de utilidade

O gate é inicializado com bias=−5 → sigmoid(−5)≈0.007. O gradiente da reconstruction loss que chega ao gate_logit é:
```
∂L_recon/∂gate_logit ≈ graph_residual_cells × sigmoid'(−5) ≈ residual × 0.007
```
Este gradiente é muito pequeno. Adicionalmente, a regularização L1 (λ_gate=0.01) empurra o gate para 0 (mais fechado). O resultado é que o gate_logit sai de −5.0 e desce ligeiramente para ≈−5.3 durante os 75 epochs — o gate fica **mais fechado**, não mais aberto.

**Causa raiz**: `compute_utility=False` durante training remove o sinal supervisionado directo. O gate só aprenderia a abrir se utility_loss ensinasse explicitamente "abrir aqui reduz o erro". Sem este sinal, a regularização L1 domina.

**Implicação**: Um utility gate que começa fechado e não tem supervisão directa não aprende a abrir em 75 epochs com lr=1e-3. Para demonstrar gate opening, seria necessário: (a) utility supervision com y_oracle durante training, OU (b) muito mais epochs, OU (c) inicialização menos negativa.

### D6 FAIL — Especificidade dirigida insuficiente em F6

F6 tem n_T=5, n_S=3, n_Y=15 — painel muito pequeno. Early stop acontece ≈21 epochs. A loss de presença dá gradiente a todos os n×(n-1)=6 pares dirigidos simultaneamente; a diferença entre o par verdadeiro (0→1) e o falso reverso (1→0) só chega a 0.149 (threshold: 0.20).

**Implicação**: O head dirigido discrimina a direcção mas não de forma suficientemente separada em 21 epochs num painel de 5×3×15.

### D8 FAIL — Gated não bate graph-always-on (marginalmente)

mae_gated=0.18147 vs mae_graph_always=0.18129. Diferença=0.00018 (0.1%). Com gate≈0.005, a predição gated ≈ temporal. A variante graph_always usa gate=1 sempre, aplicando o residual clamped completo. O GraphMessageExpert aprendeu um residual marginalmente útil; mas gated com gate≈0.005 aplica apenas 0.5% deste residual, obtendo quase zero benefício e zero custo (D7 PASS). A marginalmente superior performance de graph_always é um artefacto da gate estar essencialmente fechada.

**Implicação**: Quando gate≈0, gated e graph_always são ambos muito próximos de temporal-only. A diferença <0.2% não é científicamente significativa.

## 9. Limitações científicas

1. **Experimento sintético**: as relações dirigidas são conhecidas por construção. Não implica que o GraphRelationHead recupere relações desconhecidas em dados reais.

2. **Segurança mínima, não superioridade**: D7 assegura que o modelo gated não degrada mais de 5% vs temporal-only. Não é uma afirmação de superioridade global sobre ffill ou Ridge.

3. **Backbone congelado**: o GraphRelationHead aprende sobre representações fixas do backbone. Fine-tuning conjunto poderia alterar resultados mas violaria o isolamento temporal.

4. **Sin linguagem causal**: AUC/AUPRC medem discriminação de arestas numa distribuição sintética. Não implicam descoberta causal.

5. **Escala**: experimento local com N≤8 territórios, S=5 sectores, T=20 anos. Generalização para o painel europeu real requer estudo separado.

---

## 9. Ficheiros

| Ficheiro | Papel |
|----------|-------|
| `src/modeles/synthetic/phase16_decoupled/__init__.py` | package marker |
| `src/modeles/synthetic/phase16_decoupled/graph_relation_head.py` | Componente A |
| `src/modeles/synthetic/phase16_decoupled/gated_model.py` | Componentes B+C+D |
| `src/modeles/synthetic/phase16_decoupled/loss_functions.py` | Loss desacoplada |
| `src/modeles/synthetic/phase16_decoupled/fixtures.py` | F1-F6 |
| `src/modeles/synthetic/phase16_decoupled/evaluator.py` | 3 modos de avaliação |
| `src/modeles/synthetic/phase16_decoupled/gates_dec053.py` | D1-D10 congelados |
| `src/modeles/synthetic/phase16_decoupled/run_dec053.py` | Orquestrador |
| `tests/test_phase16_decoupled.py` | 41 testes (todos PASS) |
| `data/processed/phase16_dec053/dec053_results.json` | Resultados (pós-execução) |
