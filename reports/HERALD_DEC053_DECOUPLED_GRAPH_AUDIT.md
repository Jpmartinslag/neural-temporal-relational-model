# HERALD DEC-053: Decoupled Graph Architecture Audit

**Status:** IMPLEMENTADO — pronto para execução local
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

### 7.1 Modo ANALYTIC_GRAPH_ONLY

| Métrica | Valor | Threshold |
|---------|-------|-----------|
| edge_auc_directed | — | ≥0.60 (D2) |
| edge_auprc_directed | — | >prevalência (D2) |
| sign_acc | — | >0.50 (D2) |
| lag_acc | — | >0.50 (D2) |
| n_false_reverses (bias audit) | — | informativo |

### 7.2 Modo TEMPORAL_RECONSTRUCTION

| Baseline | MAE | vs ffill |
|----------|-----|---------|
| forward fill | — | — |
| Ridge | — | — |
| temporal-only | — | — |

### 7.3 Modo GATED_GRAPH_ASSIST

| Modelo | MAE | vs temporal-only |
|--------|-----|-----------------|
| forward fill | — | — |
| temporal-only | — | — |
| gated graph | — | — |
| graph-always-on | — | — |
| graph-permuted | — | — |

### 7.4 Fixture results (D3-D6)

| Fixture | gate_mean | Observação |
|---------|-----------|-----------|
| F1 | — | esperado >0.3 |
| F2 | — | esperado <0.2 |
| F3 | — | esperado >0.3 |
| F4 | — | esperado >0.3 |
| F5 inside window | — | esperado > outside |
| F6 logit diff | — | esperado >0.2 |

### 7.5 Gate summary (D1-D10)

*A preencher após execução.*

---

## 8. Limitações científicas

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
