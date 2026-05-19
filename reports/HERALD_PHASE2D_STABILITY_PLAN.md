# HERALD Phase 2D — Plano de Estabilização sem Flags Manuais

**Data:** 2026-05-12 | Base: Phase 2C candidato `secenh` (no_regime + learned_regime_gate_sector_enhanced)
**Revisão:** 2026-05-12 — 6 correções de implementação aplicadas antes de qualquer codificação

---

## 0. Correções obrigatórias (revisão pré-código)

As seções abaixo incorporam estas 6 correções. Nenhuma linha de código deve ser escrita antes de confirmar que cada uma está implementada corretamente.

| # | Problema | Risco se ignorado |
|---|---|---|
| C1 | `latent_regime_list` usa `.detach()` — loss H1 sem gradiente | H1 não treina; GPU gasta testando hipótese inativa |
| C2 | `alpha_list` usa `.detach()` — penalidade H4 sem gradiente | H4 não treina |
| C3 | PELT com fallback silencioso para zeros | D2 roda como `no_regime` disfarçado sem aviso |
| C4 | Zone DRO calculado com tamanho do ano de teste | Vazamento temporal |
| C5 | D6_combo incluído nos 100 runs mas condicional no texto | Contradição; D6 seria evidência inválida se D1a/D2a falharem |
| C6 | SWA com `update_bn` — v7 não tem BatchNorm | `update_bn` é no-op ou erro; evaluação usa modelo errado |

---

## 1. Diagnóstico consolidado (input para Phase 2D)

### 1.1 O que Phase 2C confirmou

- `secenh` domina `ctrl_manual` nas três métricas agregadas (mean WMAPE, WMAPE 2025, A10).
- Testes de falsificação mostram evidência favorável de sinal latente real (7-8/10 wins, direção correta, sem significância a 5%).
- Problema não resolvido: fold 2021 instável — WMAPE médio 0.049 vs ctrl 0.035 (+38%); CV entre seeds = 18.7%.

### 1.2 Mecanismo causal da instabilidade 2021

No fold 2021, o treino termina em 2020. Ridge superprevê em 2020 (err_2020 = −68 por zona) por colapso COVID. Em 2021, Ridge também superprevê levemente — mas por razão diferente: subestima o rebote. O regime latente deve distinguir "Ridge alto por choque → correção negativa" (2020) de "Ridge alto por subestimação rebote → correção positiva ou nula" (2021). Em 7/10 seeds, não distingue.

**Dois padrões patológicos distintos:**
- **Seed 17 (overreacting):** latent_step 2020→2021 = 0.953 (maior de toda a trajetória) — oscila excessivamente, interpreta 2021 como extensão do choque.
- **Seed 7 (frozen):** latent_step ≈ 0.067 — latente não detecta nada. Trata 2021 como idêntico a 2019.
- **Seed 123 (funcional):** latent_step = 0.518, moderado e na direção certa.

### 1.3 Auditoria de código — estado atual

| Componente | Status | Observação |
|---|---|---|
| `collapse_lambda` (arg) | **NÃO existe** | `latent_regime_list` coletado no forward mas sem loss de treino |
| Smoothness temporal do latente | **NÃO existe** | Só `smooth_term` (adj) e `alpha_smooth` (alpha) |
| PELT/BOCPD formal | **NÃO existe** | Modo `change_point` usa heurística zscore (`_change_state`) |
| `alpha_balance_lambda` | **NÃO existe** | Só `alpha_smooth_lambda` (penaliza variação temporal, não extremos) |
| SWA / ensemble | **NÃO existe** | Sem averaging de pesos ou de predições |
| Group DRO por zona | **parcial** | `zone_weight` existe no loss mas sem boost explícito por quintil |

---

## 2. Hipóteses testadas e descartadas antes de Phase 2D

### 2.1 H3 — Contexto residual do Ridge (DESCARTADO)

**Proposta:** usar err_{t-1} = y_{t-1} − ridge_{t-1} como feature de regime.

**Por que descartado:** para o fold 2021, o único lag disponível no treino é err_2020 = grande negativo (Ridge severamente superprevê em 2020). Este sinal aponta "correção fortemente negativa" — exatamente a direção errada para o rebote de 2021. A aceleração (err_2020 − err_2019) também é negativa. H3 **amplifica** a confusão 2020→2021 em vez de resolvê-la. O único ano onde H3 ajudaria (2022+) já tem err_2021 disponível, mas aí o problema já não existe. H3 é descartado.

### 2.2 IRM (DESCARTADO)

Instabilidade de otimização documentada na literatura para T curto. Descartado.

### 2.3 Contrastive temporal pesado (DESCARTADO)

Risco alto de overfitting sem pré-treino externo com T=14. Descartado.

### 2.4 Sparse MoE grande (DESCARTADO)

Excesso de capacidade para T=14, alto risco de colapso de experts. Descartado.

---

## 3. Hipóteses Phase 2D

### H1 — Anti-collapse + smoothness temporal do latente

**Diagnóstico:** seed 7 tem latente congelado (lat_step ≈ 0); seed 17 tem latente oscilando demais (lat_step = 0.953). Ambos falham por razões opostas.

**Proposta:** dois termos de regularização complementares:
- **Anti-collapse:** `F.relu(threshold − lat_var)` onde `lat_var = stack(latent_list_grad).var(dim=0).mean()`. Força o latente a ter variância temporal mínima (combate seed 7).
- **Smoothness temporal do latente:** `mean(|lat_t − lat_{t-1}|²)`. Penaliza passos excessivos (combate seed 17).

São forças opostas que, juntas, induzem variância moderada — sem colapso e sem caos. Referência: VICReg (anti-collapse, Bardes et al. 2022) + SFA (smooth features, Wiskott & Sejnowski 2002).

**Correção C1 — gradiente do latente:** `latent_regime_list` em `train_herald_v7.py` usa `.detach()` (`latent_regime_list.append(latent_regime_t.detach())`). Uma loss aplicada sobre esse tensor **não teria gradiente** — H1 seria silenciosamente inativa. A implementação correta exige duas listas paralelas no forward de v7:

```python
# train_herald_v7.py — dentro do loop temporal (forward)
latent_regime_list_grad.append(latent_regime_t)          # diferenciável — para loss
latent_regime_list.append(latent_regime_t.detach())       # para internals (não muda)
```

Após o loop, calcular e adicionar a `graph_losses`:
```python
if latent_regime_list_grad:
    lat_stack = torch.stack(latent_regime_list_grad, dim=0)  # (T, REGIME_DIM)
    lat_var = lat_stack.var(dim=0).mean()
    graph_losses["latent_collapse_term"] = F.relu(0.05 - lat_var)
    if lat_stack.shape[0] > 1:
        graph_losses["latent_smooth_term"] = ((lat_stack[1:] - lat_stack[:-1]) ** 2).mean()
    else:
        graph_losses["latent_smooth_term"] = torch.tensor(0.0, device=device)
```

Em `train_herald_semi_v2.py`, aplicar os lambdas via `graph_losses`:
```python
loss = loss + args.collapse_lambda * graph_losses["latent_collapse_term"]
loss = loss + args.latent_smooth_lambda * graph_losses["latent_smooth_term"]
```

**Risco:** baixo-médio. Lambda excessivo pode criar oscilações artificiais sem significado econômico.

**Critério de rejeição:** CV de WMAPE 2021 não reduz de 18.7% para < 13%, OU WMAPE 2022-2024 piora > 2% relativo vs `cand_2c`.

---

### H2 — Change-point causal formal via PELT por fold

**Diagnóstico:** o modo `change_point` atual usa `_change_state` (heurística zscore). Não detecta breakpoints formalmente. PELT fornece "distância ao último breakpoint" como sinal explícito e auditável.

**Proposta:** novo modo `pelt_regime` em `herald_regime_modes.py`:
- Para cada fold: rodar PELT sobre a série global (aggregate de `side_lag_1`) usando apenas dados ≤ `train_max`.
- Output: vetor [3] — `[dist_normalizada, indicador_1yr_pos_ruptura, indicador_2yr_pos_ruptura]`.
- Distância normalizada: `1 / (1 + anos_desde_ultima_ruptura)`.
- Restrição de penalidade: `pen ≥ 3` para evitar oversegmentation com T=9-13.
- Causalidade: garantida — PELT roda apenas em `agg.loc[train_mask]`.
- Biblioteca: `ruptures` (Truong et al. 2020, revisado por pares).

**Diferença vs `change_point` atual:** PELT detecta qualquer ruptura histórica (2008, 2012, 2020), não só COVID. O modelo aprende "pós-ruptura recente" sem receber nome do evento.

**Correção C3 — sem fallback silencioso:** O plano original propunha fallback para zeros quando `ruptures` não está instalado. Isso é errado: faria `pelt_regime` rodar identicamente a `no_regime` sem qualquer aviso — os runs D2a/D2b pareceriam completos mas testariam a hipótese errada.

A implementação correta: verificar `ruptures` na inicialização do modo, antes de qualquer treino:

```python
# herald_regime_modes.py — no topo, importação lazy com erro explícito
def _require_ruptures():
    try:
        import ruptures  # noqa: F401
    except ImportError as e:
        raise ImportError(
            "ruptures is required for pelt_regime modes. "
            "Install with: pip install ruptures"
        ) from e
```

Chamar `_require_ruptures()` no início de `build_regime_vectors` quando `regime_mode` começa com `"pelt_"`. O smoke test captura o erro antes de qualquer GPU ser alocada.

**Risco:** médio. Penalidade PELT requer tuning (pen muito baixo → oversegmentation; muito alto → sem ruptura detectada). Testar pen=3 e pen=5.

**Salvamento de breakpoints para auditoria:** `herald_regime_modes.py` armazena os breakpoints detectados por fold em um dict módulo-nível `_pelt_breakpoints {train_max → [year_list]}`. `train_herald_regime_experiment.py` lê esse dict após o treino e salva como `pelt_breakpoints_by_train_max` no metadata JSON de cada run. O script de auditoria lê esse campo e verifica `all(bkp_year <= train_max for bkp_year in bkps)`.

**Critério de rejeição:** qualquer breakpoint detectado com dados além de `train_max` (vazamento temporal — auditado pelo script de auditoria), OU mean WMAPE > cand_2c + 0.001.

---

### H4 — Penalidade de alpha para extremos em transições

**Diagnóstico:** seed 17 tem alpha=0.643 em 2021 (excessivamente local), seed 7 tem alpha=0.619. Seed 123 tem alpha=0.474 (equilíbrio). A `alpha_smooth_lambda` atual penaliza variação temporal de alpha, mas não extremos absolutos.

**Proposta:** penalidade `alpha_balance = mean((alpha − 0.5)²)` com `alpha_balance_lambda` separado. Encoraja alpha próximo de 0.5 (equilíbrio local/grafo) de forma soft.

**Correção C2 — gradiente do alpha:** `alpha_list` em `train_herald_v7.py` usa `.detach()` (`alpha_list.append(alpha.detach())`). A penalidade `(alpha − 0.5)²` sobre esse tensor **não teria gradiente**. A implementação correta: acumular `alpha` antes do detach e calcular o termo dentro do forward, retornando via `graph_losses`:

```python
# train_herald_v7.py — dentro do loop temporal (forward)
alpha_balance_list.append(((alpha - 0.5) ** 2).mean())   # diferenciável
alpha_list.append(alpha.detach())                          # para internals (não muda)
```

Após o loop:
```python
graph_losses["alpha_balance_term"] = torch.stack(alpha_balance_list).mean()
```

Em `train_herald_semi_v2.py`:
```python
loss = loss + args.alpha_balance_lambda * graph_losses["alpha_balance_term"]
```

**Risco:** médio. Alpha longe de 0.5 é correto em alguns anos. Lambda pequeno (0.003-0.01) mitiga. Se A10 degradar > 0.005, rejeitar.

**Critério de rejeição:** A10 WMAPE piora > 0.005 vs cand_2c, OU alpha 2022-2025 colabado em 0.5 (perde expressividade).

---

### H5 — Zone-size boost via zone_weight (DRO parcial)

**Diagnóstico:** 69% do erro extra de 2021 está nas 20 maiores zonas (Q4-Q5). O `zone_weight` já existe no loss, mas é calculado como `zone_mean / zone_mean.mean()` clipeado — proporcional ao tamanho médio histórico da zona no treino do fold.

**Proposta:** boost adicional para Q4-Q5 por fator k (ex. k=1.5). Equivale a Group DRO com grupos = quintil de tamanho histórico.

**Correção C4 — causalidade do zone_weight:** `zone_weight` em `train_herald_v6.py:671` é calculado como `np.clip(zone_mean / zone_mean.mean(), 0.1, 10.0)` onde `zone_mean = np.nanmean(train_y_raw, axis=0)` — usando apenas dados de treino do fold. Isso é causal.

O boost Q4-Q5 DEVE usar essa mesma `zone_mean` (ou `side_lag_1` histórico disponível no treino) para definir quintis — **nunca** usar `y_true` do ano de teste. Implementação correta:

```python
# make_sequences_v7 (ou equivalente em semi_v2)
zone_mean_train = np.nanmean(train_y_raw, axis=0)  # já existe
q4_threshold = np.nanpercentile(zone_mean_train, 60)
q5_threshold = np.nanpercentile(zone_mean_train, 80)
dro_boost = np.where(zone_mean_train >= q4_threshold,
                     np.where(zone_mean_train >= q5_threshold, k, (k + 1) / 2),
                     1.0)
zone_weight = np.clip((zone_mean_train / zone_mean_train.mean()) * dro_boost, 0.1, 10.0)
```

`k` passado como arg `--zone-dro-q45-boost` (default 1.0 = sem boost).

**Restrição metodológica:** calibrar k baseado em 2022-2024, não em 2021.

**Risco:** médio. Pode reduzir precisão em Q1-Q3 (60% das zonas) para melhorar Q4-Q5. Testar k=1.5 apenas.

**Critério de rejeição:** WMAPE Q1-Q3 piora > 3% relativo, OU A10 degrada > 0.005.

---

### H6 — SWA como estabilizador de seed

**Diagnóstico:** variância entre seeds é alta (CV=18.7%). SWA (Stochastic Weight Averaging) promedia pesos dos últimos N% do treino, encontrando solução mais plana e menos sensível a inicialização.

**Proposta:** SWA nos últimos 20% dos epochs (160 de 800). Usar `torch.optim.swa_utils.AveragedModel`.

**Nota metodológica:** SWA é estabilizador, não solução causal. Não resolve a confusão 2020→2021 — apenas dilui as soluções ruins dentro da mesma run. Deve ser rotulado como tal nos resultados. Não pode ser o claim principal do paper.

**Correção C6 — SWA sem BatchNorm:** v7 não usa BatchNorm (confirmado: `grep BatchNorm train_herald_v7.py` → sem resultado). `update_bn` não se aplica e chamá-lo é erro ou no-op enganoso — a avaliação usaria o modelo normal em vez do modelo médio. A implementação correta:

```python
# train_herald_semi_v2.py
from torch.optim.swa_utils import AveragedModel

swa_start_ep = int(args.epochs * (1.0 - args.swa_start_frac))
swa_model = AveragedModel(model) if args.swa_start_frac > 0 else None

for ep in range(args.epochs):
    # ... forward + loss + backward + opt.step() ...
    if swa_model is not None and ep >= swa_start_ep:
        swa_model.update_parameters(model)

# Avaliação: usar swa_model (pesos médios) — SEM update_bn
eval_model = swa_model if swa_model is not None else model
# Garantir que eval_model.eval() antes do passo de inferência
```

Sem `update_bn`. `swa_model` contém os pesos médios e é usado diretamente na inferência final do fold.

**Risco:** baixo-médio. Pode não ajudar se todos os mínimos locais convergem para o mesmo padrão ruim.

**Critério de rejeição:** CV de WMAPE 2021 entre seeds ≥ 18.7% (SWA sem efeito estabilizador).

---

## 4. Bateria Phase 2D — Configurações

**Baselines obrigatórias (sem mudanças de código):**

| Label | Regime Mode | Variant | Params chave | Propósito |
|---|---|---|---|---|
| `ctrl_manual` | manual_flags | full | padrão Phase 2C | referência upper bound |
| `ctrl_noregime` | no_regime | full | padrão Phase 2C | referência sem regime |
| `cand_2c` | no_regime | secenh | padrão Phase 2C | referência candidato atual |
| `ridge_ar` | — | — | Ridge only | lower bound |

**Variantes Phase 2D (requerem mudanças de código pequenas):**

| Label | H | Mudança vs cand_2c | collapse_λ | latsmooth_λ | alpha_bal_λ | zone_dro | SWA | Risco | Custo GPU |
|---|---|---|---|---|---|---|---|---|---|
| `D1a_col01` | H1 | +collapse+latsmooth leve | 0.01 | 0.005 | — | — | — | baixo | 1× |
| `D1b_col05` | H1 | +collapse+latsmooth forte | 0.05 | 0.01 | — | — | — | médio | 1× |
| `D2a_pelt3` | H2 | novo regime mode pelt pen=3 | — | — | — | — | — | médio | 1× |
| `D2b_pelt5` | H2 | novo regime mode pelt pen=5 | — | — | — | — | — | médio | 1× |
| `D3_aba` | H4 | +alpha_balance_lambda | — | — | 0.005 | — | — | médio | 1× |
| `D4_dro15` | H5 | zone Q4-Q5 weight ×1.5 | — | — | — | 1.5 | — | médio | 1× |
| `D5_swa` | H6 | SWA últimos 20% epochs | — | — | — | — | sim | baixo | 1× |
**Correção C5 — D6_combo removido da primeira bateria:** o plano original incluía D6 nos 120 runs mas condicionava sua interpretação ao sucesso de D1a e D2a. Isso é contraditório: se D1a ou D2a falharem, D6 seria evidência inválida de um efeito combinado. D6 é movido para a **segunda bateria (Phase 2D-r2)**, submetida apenas após análise dos resultados de r1.

**Total Phase 2D-r1:** 3 baselines + 7 variantes = **10 configs × 10 seeds = 100 runs.**

> `D6_combo` (col01 + pelt3 + swa) entra em Phase 2D-r2 somente se D1a E D2a individualmente passarem seus critérios de aceitação. Nomeação: `OUT_ROOT = hpc_results/herald_regime_phase2d_stability_YYYYMMDD_r2`.

Custo Phase 2D-r1 estimado (800 epochs, GPU A100): ~10h × 10 configs × 10 seeds / N_GPU paralelas.

---

## 5. Critério de rejeição por hipótese

| Label | Critério de rejeição (qualquer um basta) |
|---|---|
| `D1a`, `D1b` | CV WMAPE 2021 ≥ 18.7% (não melhora), OU WMAPE 2022-2024 degrada > 2% relativo vs cand_2c |
| `D2a`, `D2b` | Breakpoint detectado com dados > train_max (vazamento), OU mean WMAPE > cand_2c + 0.001 |
| `D3_aba` | A10 WMAPE piora > 0.005 vs cand_2c, OU alpha 2022-2025 colabado em 0.5 (perde expressividade) |
| `D4_dro15` | WMAPE Q1-Q3 piora > 3% relativo, OU A10 degrada > 0.005 |
| `D5_swa` | CV WMAPE 2021 entre seeds ≥ 18.7% (swa sem efeito estabilizador) |
| `D6_combo` | Qualquer critério dos componentes individuais que falharam |

---

## 6. Regras metodológicas Phase 2D

1. **Proibido:** `is_covid_year`, `is_post_covid_rebound` — em qualquer variante.
2. **Proibido:** usar target futuro ou err Ridge do próprio ano de teste.
3. **Proibido:** selecionar seed baseando em resultado de 2021 (data snooping).
4. **PELT** (H2): recalcular por fold com dados ≤ train_max. Auditar breakpoints detectados.
5. **Validação interna:** usar folds 2022-2024 como sinal de seleção. 2021 e 2025 ficam como teste cego.
6. **Comparação obrigatória:** reportar fold-by-fold (2021-2025) + seed-by-seed para 2021, não só média.
7. **A10 preservado:** variante que melhora total mas degrada A10 > 0.005 não substitui o HERALD atual.
8. **OUT_ROOT único:** `hpc_results/herald_regime_phase2d_stability_YYYYMMDD_r1` — nunca sobrescrever.

---

## 7. Mudanças de código necessárias

### 7.1 `src/modeles/train_herald_semi_v2.py` (H1, H4, H5, H6)

**Novos args:**
```python
parser.add_argument("--collapse-lambda", type=float, default=0.0)
parser.add_argument("--latent-smooth-lambda", type=float, default=0.0)
parser.add_argument("--alpha-balance-lambda", type=float, default=0.0)
parser.add_argument("--zone-dro-q45-boost", type=float, default=1.0)
parser.add_argument("--swa-start-frac", type=float, default=0.0,
                    help="Fraction of epochs to start SWA. 0=disabled.")
```

**No loop de treino — H1 e H4 via `graph_losses` (correções C1 e C2):**

H1 e H4 NÃO devem acessar os tensores via `model.last_latent_stack` nem via `alpha_list` — ambos já estão detachados. Em vez disso, os termos são calculados **dentro do forward de v7** (onde os tensores ainda têm gradiente) e retornados em `graph_losses`:

```python
# Em train_herald_semi_v2.py — após receber graph_losses do forward
loss = loss + args.collapse_lambda * graph_losses.get("latent_collapse_term", torch.tensor(0.0, device=device))
loss = loss + args.latent_smooth_lambda * graph_losses.get("latent_smooth_term", torch.tensor(0.0, device=device))
loss = loss + args.alpha_balance_lambda * graph_losses.get("alpha_balance_term", torch.tensor(0.0, device=device))
```

Os termos `latent_collapse_term`, `latent_smooth_term` e `alpha_balance_term` são adicionados ao `graph_losses` em `train_herald_v7.py` antes do `.detach()` das listas. Ver seção de mudanças em v7 abaixo.

**H6 — SWA (correção C6 — sem update_bn):**

```python
# train_herald_semi_v2.py
from torch.optim.swa_utils import AveragedModel

swa_start_ep = int(args.epochs * (1.0 - args.swa_start_frac))
swa_model = AveragedModel(model) if args.swa_start_frac > 0 else None

for ep in range(args.epochs):
    # ... forward + loss + backward + opt.step() normal ...
    if swa_model is not None and ep >= swa_start_ep:
        swa_model.update_parameters(model)

# SEM update_bn — v7 não usa BatchNorm
eval_model = swa_model if swa_model is not None else model
eval_model.eval()
# Usar eval_model no passo de inferência (return_internals=True)
```

**Mudanças em `train_herald_v7.py` (para C1 e C2):**

```python
# Dentro do loop temporal do forward, acumular versões não-detachadas
latent_regime_list_grad = []   # diferenciável — só para loss
alpha_balance_list = []        # diferenciável — só para loss

# Por timestep:
latent_regime_list_grad.append(latent_regime_t)       # antes do detach
latent_regime_list.append(latent_regime_t.detach())   # para internals — não muda

alpha_balance_list.append(((alpha - 0.5) ** 2).mean())  # antes do detach
alpha_list.append(alpha.detach())                        # para internals — não muda

# Após o loop, calcular e adicionar a graph_losses:
if latent_regime_list_grad:
    lat_stack = torch.stack(latent_regime_list_grad, dim=0)
    graph_losses["latent_collapse_term"] = F.relu(0.05 - lat_stack.var(dim=0).mean())
    if lat_stack.shape[0] > 1:
        graph_losses["latent_smooth_term"] = ((lat_stack[1:] - lat_stack[:-1]) ** 2).mean()
    else:
        graph_losses["latent_smooth_term"] = torch.tensor(0.0, device=device)
graph_losses["alpha_balance_term"] = torch.stack(alpha_balance_list).mean() if alpha_balance_list else torch.tensor(0.0, device=device)
```

### 7.2 `src/modeles/herald_regime_modes.py` (H2 — PELT)

**Novo modo `pelt_regime`:**
```python
def _pelt_change_features(train_series: np.ndarray, target_year: int,
                           train_years: np.ndarray, pen: float = 3.0) -> np.ndarray:
    """PELT change-point features. Causal: uses only train_series (data <= train_max)."""
    import ruptures as rpt  # sem try/except — falha explícita (correção C3)

    if len(train_series) < 4:
        return np.zeros(3, dtype=np.float32)

    algo = rpt.Pelt(model="rbf", min_size=2, jump=1).fit(train_series.reshape(-1, 1))
    bkps = algo.predict(pen=pen)  # returns list of breakpoint indices (end-exclusive)

    # Converter índice de breakpoint para ano
    bkp_years = [train_years[min(b - 1, len(train_years) - 1)] for b in bkps[:-1]]
    if not bkp_years:
        return np.zeros(3, dtype=np.float32)

    last_bkp_year = max(bkp_years)
    dist = int(target_year) - int(last_bkp_year)
    dist_feat = 1.0 / (1.0 + max(dist, 0))  # normalizado, 1.0=breakpoint neste ano
    is_1yr = float(dist == 1)
    is_2yr = float(dist == 2)
    return np.array([dist_feat, is_1yr, is_2yr], dtype=np.float32)
```

**Integração em `build_regime_vectors`:** adicionar `"pelt_regime_pen3"` e `"pelt_regime_pen5"` a `REGIME_MODES`. Adicionar `_require_ruptures()` no início da função quando o modo começa com `"pelt_"` — sem fallback silencioso (correção C3).

### 7.3 `hpc/regime/run_herald_regime_seed.sh` (novo plano `phase2d_stability`)

Adicionar ao `plan_configs()`:
```bash
phase2d_stability)
  # Baselines
  echo "manual_flags full no_source_flags ctrl_manual 0.1 0.001 0.01 explicit normal match_train none all"
  echo "no_regime full no_source_flags ctrl_noregime 0.1 0.001 0.01 none normal match_train none all"
  echo "no_regime learned_regime_gate_sector_enhanced no_source_flags cand_2c 0.2 0.001 0.01 none normal match_train none all"
  # H1 — anti-collapse + latent smooth
  echo "no_regime learned_regime_gate_sector_enhanced no_source_flags D1a_col01 0.2 0.001 0.01 none normal match_train none all"  # +collapse_lambda=0.01 latent_smooth=0.005
  echo "no_regime learned_regime_gate_sector_enhanced no_source_flags D1b_col05 0.2 0.001 0.01 none normal match_train none all"  # +collapse_lambda=0.05 latent_smooth=0.01
  # H2 — PELT
  echo "pelt_regime_pen3 learned_regime_gate_sector_enhanced no_source_flags D2a_pelt3 0.2 0.001 0.01 none normal match_train none all"
  echo "pelt_regime_pen5 learned_regime_gate_sector_enhanced no_source_flags D2b_pelt5 0.2 0.001 0.01 none normal match_train none all"
  # H4 — alpha balance
  echo "no_regime learned_regime_gate_sector_enhanced no_source_flags D3_aba 0.2 0.001 0.01 none normal match_train none all"  # +alpha_balance=0.005
  # H5 — zone DRO
  echo "no_regime learned_regime_gate_sector_enhanced no_source_flags D4_dro15 0.2 0.001 0.01 none normal match_train none all"  # +zone_dro_boost=1.5
  # H6 — SWA
  echo "no_regime learned_regime_gate_sector_enhanced no_source_flags D5_swa 0.2 0.001 0.01 none normal match_train none all"  # +swa_start_frac=0.8
  # D6_combo REMOVIDO desta bateria (correção C5) — entra em phase2d_stability_r2 somente se D1a e D2a passarem
  ;;
```

> **Nota:** os novos args (collapse_lambda, etc.) precisam ser passados via `common_args` ou como extensão do `run_regime`. A forma mais limpa é adicionar colunas ao plan_configs e expandir `common_args`. Ver seção 8 para a abordagem mínima.

---

## 8. Smoke test CPU (obrigatório antes de qualquer lançamento GPU)

```bash
#!/bin/bash
# smoke_test_phase2d.sh
set -euo pipefail

OUT_SMOKE="hpc_results/herald_phase2d_smoke_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$OUT_SMOKE"/{reports/per_run,data_processed,logs,metadata}

echo "=== HERALD Phase 2D — Smoke Test CPU (1 epoch) ==="

PYTHON=python3
PANEL_PATH="data/processed/dynamic_stgnn_feature_panel_through_2025_v1.csv"
SPLITS_PATH="metadata/dynamic_stgnn_walk_forward_splits_through_2025_v1.csv"
SIDE_A10_PATH="data/processed/side_creations_a10_ze2020_through_2025_v1.csv"

common_smoke() {
  echo \
    --panel-path "$PANEL_PATH" \
    --splits-path "$SPLITS_PATH" \
    --side-a10-path "$SIDE_A10_PATH" \
    --prediction-output-dir "$OUT_SMOKE/data_processed" \
    --metrics-path "$OUT_SMOKE/reports/per_run/smoke_$1.json" \
    --model-card-path "$OUT_SMOKE/reports/per_run/smoke_$1.md" \
    --epochs 1 \
    --hidden-dim 16 \
    --q-hidden 8 \
    --attn-dim 8 \
    --mode full \
    --v7-variant learned_regime_gate_sector_enhanced \
    --feature-mask-ratio 0.10 \
    --sector-mask-ratio 0.30 \
    --sector-lambda 0.2 \
    --smooth-lambda 0.01 \
    --gate-entropy-lambda 0.001 \
    --alpha-smooth-lambda 0.001 \
    --rank-lambda 0.02 \
    --lr 0.001 \
    --huber-delta 300 \
    --top-k 5 \
    --device cpu \
    --seed 0 \
    --single-target-year 2023 \
    --semi-warmup-epochs 0
}

echo "--- smoke: cand_2c (baseline) ---"
$PYTHON src/modeles/train_herald_regime_experiment.py \
  --regime-mode no_regime \
  --drop-source-flags \
  --experiment-label smoke_cand2c \
  --regime-metadata-path "$OUT_SMOKE/metadata/smoke_cand2c.json" \
  --smooth-regime-source none \
  $(common_smoke cand2c) \
  --run-tag smoke_cand2c

echo "--- smoke: D1a (collapse_lambda=0.01 + latent_smooth=0.005) ---"
$PYTHON src/modeles/train_herald_regime_experiment.py \
  --regime-mode no_regime \
  --drop-source-flags \
  --experiment-label smoke_D1a \
  --regime-metadata-path "$OUT_SMOKE/metadata/smoke_D1a.json" \
  --smooth-regime-source none \
  --collapse-lambda 0.01 \
  --latent-smooth-lambda 0.005 \
  $(common_smoke D1a) \
  --run-tag smoke_D1a

echo "--- smoke: D2a (pelt_regime_pen3) ---"
$PYTHON src/modeles/train_herald_regime_experiment.py \
  --regime-mode pelt_regime_pen3 \
  --drop-source-flags \
  --experiment-label smoke_D2a \
  --regime-metadata-path "$OUT_SMOKE/metadata/smoke_D2a.json" \
  --smooth-regime-source none \
  $(common_smoke D2a) \
  --run-tag smoke_D2a

echo "=== Smoke test completo. Verificar: ==="
echo "  1. Sem erros de import (ruptures, torch)"
echo "  2. Artefatos criados em $OUT_SMOKE"
echo "  3. Ausência de is_covid_year/is_post_covid_rebound nas features (grep)"
echo "  4. PELT breakpoints em metadata smoke_D2a.json são <= 2023 (fold único)"
ls "$OUT_SMOKE/reports/per_run/" 2>/dev/null || echo "ERRO: sem artefatos criados"
```

---

## 9. Auditoria planejada Phase 2D

O script de auditoria deve verificar os seguintes pontos após a conclusão dos runs:

### 9.1 Completude de runs

```python
# Para cada config × seed: verificar existência de JSON + CSV total + CSV setor + NPZ
EXPECTED_LABELS = ["ctrl_manual", "ctrl_noregime", "cand_2c",
                   "D1a_col01", "D1b_col05", "D2a_pelt3", "D2b_pelt5",
                   "D3_aba", "D4_dro15", "D5_swa"]
# D6_combo não está em r1 (ver correção C5) — entra em r2 com labels próprios
SEEDS = [0, 1, 7, 13, 17, 42, 77, 99, 123, 2025]
```

### 9.2 Ausência de flags manuais

```python
# Para todos os configs EXCETO ctrl_manual: verificar nos metadata JSON
assert metadata["manual_flags_in_annual_features"] == False
assert metadata["manual_flags_in_regime_vector"] == False
```

### 9.3 Ausência de source flags quando no_source

```python
assert metadata["source_flags_in_annual_features"] == False
assert metadata["dropped_source_flags"] == sorted(["has_flores_source", "has_side_stock_source", "has_urssaf_source"])
```

### 9.4 Causalidade das features PELT (D2a, D2b, D6_combo)

```python
# Para cada fold: verificar que breakpoints detectados estão DENTRO do treino
# Ler pelt_breakpoints_by_fold do metadata ou NPZ internals
for fold_year, bkps in pelt_breakpoints.items():
    train_max = splits[splits.target_year == fold_year]["train_years_max"].iloc[0]
    assert all(b <= train_max for b in bkps), f"VAZAMENTO em fold {fold_year}: bkps={bkps}"
```

### 9.5 Métricas principais (tabela de comparação)

Reportar por config:

| Métrica | Tipo | Critério de aceitação |
|---|---|---|
| WMAPE mean | agregado | ≤ cand_2c (0.02883) |
| WMAPE 2021 (mean de seeds) | fold | < 0.045 (−8% vs atual 0.049) |
| WMAPE 2021 (CV de seeds) | estabilidade | < 13% (vs atual 18.7%) |
| WMAPE 2025 | fold | ≤ cand_2c (0.01854) |
| A10 WMAPE | setor | ≤ cand_2c + 0.005 (0.16741) |
| Latent_step 2020→2021 (CV de seeds) | latente | < 30% (vs atual: range 0.07–0.95) |
| Alpha 2021 (mean de seeds) | alpha | entre 0.45 e 0.60 |
| Concentração erro grandes zonas (Q5 ΔAE) | zonas | < +200 (vs atual +251) |

### 9.6 Latent stability (seed-by-seed para fold 2021)

```python
# Para cada config: extrair latent_step 2020→2021 de cada NPZ seed
# Reportar: mean, std, CV, range (min-max)
# Flag: seeds com latent_step < 0.1 (frozen) ou > 0.8 (overreacting)
```

### 9.7 Alpha por ano

```python
# Para cada config: alpha_by_year de cada seed no fold mais recente
# Flag: alpha 2021 > 0.70 (excessivamente local) ou < 0.30 (excessivamente grafo)
```

### 9.8 Concentração de erro em grandes zonas (2021)

```python
# Para fold 2021: dividir zonas em quintis por y_true
# Calcular ΔAE (config − ctrl) por quintil
# Flag: se Q5 ΔAE > +200 (pior que cand_2c)
```

---

## 10. Ordem de execução

```
Phase 2D
│
├─ 1. Implementação (sem GPU)
│   ├─ train_herald_semi_v2.py: +collapse_lambda, +latent_smooth_lambda,
│   │                            +alpha_balance_lambda, +zone_dro_q45_boost, +swa
│   ├─ herald_regime_modes.py: +pelt_regime_pen3, +pelt_regime_pen5
│   └─ run_herald_regime_seed.sh: +phase2d_stability plan
│
├─ 2. Smoke test CPU (1 epoch, fold único)
│   └─ Verificar: sem erros, sem flags, PELT causal, artefatos ok
│
├─ 3. Submit GPU (10 seeds × 10 configs × 10 seeds = 100 runs)
│   └─ OUT_ROOT = hpc_results/herald_regime_phase2d_stability_YYYYMMDD_r1
│
├─ 4. Aggregação
│   └─ python3 hpc/regime/aggregate_herald_regime_results.py --root ...
│
├─ 5. Auditoria
│   └─ python3 hpc/regime/audit_herald_phase2d_stability.py --root ...
│
└─ 6. Decisão
    ├─ Configs que passam todos os critérios → candidatos Phase 2E (operacional)
    └─ Configs que falham → documentar por quê e descartar
```

---

## 11. O que NÃO é aceitável como resultado de Phase 2D

1. **Escolher o melhor config olhando WMAPE 2021 diretamente.** 2021 é fold de teste. Seleção deve ser por 2022-2024.
2. **Reportar só a média de 5 folds.** Obrigatório fold-by-fold.
3. **Combinar configs que falharam individualmente** esperando que "juntos melhoram". Se D1a falha, D6_combo não deve ser interpretado como evidência de H1.
4. **Afirmar que SWA "resolve 2021" causalmente.** SWA estabiliza — não explica.
5. **Declarar vitória se WMAPE médio melhora mas 2021 piora mais.** O mínimo aceitável: 2021 não pode piorar vs cand_2c.

---

## 12. Contexto bibliográfico (referências usadas neste plano)

- Hamilton (1989) — Markov Switching. *Econometrica*.
- Kim (1994) — Switching State-Space. *Journal of Econometrics*.
- Killick et al. (2012) — PELT. *JASA*. DOI: 10.1080/01621459.2012.737745
- Truong et al. (2020) — ruptures. *Signal Processing*. DOI: 10.1016/j.sigpro.2019.107299
- Bardes, Ponce, LeCun (2022) — VICReg. *ICLR*. arXiv: 2105.04906
- Wiskott & Sejnowski (2002) — SFA. *Neural Computation*. DOI: 10.1162/089976602317318938
- Sagawa et al. (2020) — Group DRO. *ICLR*. arXiv: 1911.08731
- Izmailov et al. (2018) — SWA. *UAI*. arXiv: 1803.05407
- Lakshminarayanan et al. (2017) — Deep Ensembles. *NeurIPS*. arXiv: 1612.01474

---

*Plano elaborado a partir de: HERALD_2021_INSTABILITY_DIAGNOSIS.md, HERALD_2021_STABILITY_LITERATURE_REVIEW.md, HERALD_PHASE2C_CRITICAL_AUDIT.md, HERALD_PHASE2B_A10_GUARD_AUDIT.md, auditoria de código de train_herald_semi_v2.py, train_herald_v7.py, herald_regime_modes.py.*
