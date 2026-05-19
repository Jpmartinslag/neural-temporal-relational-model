# HERALD Regime Architecture Review

**Auditoria científica e metodológica sênior**
Data: 2026-05-12 | Versão: 1.1

---

## Addendum (Phase 2C prep)

Foi preparado um plano crítico separado em:

- `reports/HERALD_REGIME_PHASE2C_CRITICAL_PLAN.md`

Esse plano introduz:

1. **smooth simétrico experimental** (`smooth_regime_source=none`) para remover vantagem estrutural do controle manual;
2. **testes de falsificação explícitos** (regime permutado, latente zerado na inferência, latente congelado, fold 2021 isolado);
3. bateria Phase 2C com configs críticas prontas para submissão, sem lançamento automático.

> Nota: o `change_point` formal (PELT/BOCPD causal por fold) permanece como especificação metodológica recomendada; ainda não foi integrado como modo novo no código.

---

## Resumo Executivo

HERALD tem uma infraestrutura experimental sólida e uma hipótese legítima. O mecanismo de regime latente (`no_regime + learned_regime_gate + no_source_flags`) vence o controle em WMAPE médio (+0.36 pp) e em 2025 (-5.2 pp), mas **falha gravemente em 2021** (+16.9 pp vs. controle) e **degrada A10 sistematicamente** (p=0.020). A conclusão operacional "promissor mas ainda não substitui o controle" está correta, porém subestima os problemas reais.

**Problemas graves identificados:**

1. O candidato Phase 2A é melhor na média porque compensa um desastre em 2021 com ganhos em 2023-2025. Isso é overfit ao período post-COVID normalizado, não robustez geral.
2. A hipótese central ("HERALD detecta regimes sem flags manuais") não é demonstrável com T=14 anos, 5 folds de teste e n=10 seeds. Nenhum dos resultados é estatisticamente significativo (todos p ≥ 0.13).
3. `latent_change` e `change_point` usam código idêntico (`_change_state`). São pseudovariantes.
4. A penalidade de suavização do grafo é **assimétrica**: `manual_flags` recebe desconto no smooth_term durante anos de crise (regime_weight > 0), `no_regime` recebe penalidade plena. Isso não é uma comparação justa.
5. O `sector_prior_gate` no V7 usa `pred.detach()` — a predição total não contribui gradiente para a cabeça setorial, o que pode sub-treinar a gate.

**Recomendação global:** Não substituir o controle manual ainda. Phase 2B tem justificativa metodológica, mas o critério de decisão precisa ser auditado sobre o fold 2021 explicitamente, não apenas WMAPE médio.

---

## 1. Problemas Encontrados (críticos)

### 1.1 Desempenho assimétrico por fold — o candidato quebra em 2021

Análise fold-by-fold do melhor candidato Phase 2A (`no_regime + learned_regime_gate + no_source_flags`) vs. controle (`manual_flags + with_source_flags`):

| Ano | Ctrl WMAPE | Cand WMAPE | Delta |
|---:|---:|---:|---:|
| 2021 | 0.03224 | 0.04915 | **+0.01691** ← colapso |
| 2022 | 0.03000 | 0.02948 | -0.00052 |
| 2023 | 0.03411 | 0.02485 | **-0.00926** |
| 2024 | 0.02626 | 0.02168 | -0.00458 |
| 2025 | 0.02338 | 0.01819 | -0.00519 |

O candidato perde feio em 2021 (+52% erro relativo) e ganha em 2023-2025. A média WMAPE levemente melhor do candidato (0.02867 vs. 0.02902) mascara que 2021 é um desastre. 2021 é o ano de rebote COVID — exatamente o ano que `is_post_covid_rebound` identifica. O modelo latente não aprendeu esse regime; aprendeu padrões 2022-2025 e falhou na transição.

**Consequência direta:** Qualquer afirmação de que "o regime latente é tão bom quanto os flags manuais" é factualmente errada para o período mais difícil de generalizar.

### 1.2 Nenhum resultado é estatisticamente significativo

Todos os p-values Wilcoxon para as comparações principais são altos:

| Comparação | Métrica | p |
|---|---|---|
| `no_regime+latent_gate+no_src` vs `manual_flags` | WMAPE médio | 0.922 |
| `no_regime+latent_gate+no_src` vs `manual_flags` | WMAPE 2025 | 0.131 |
| `no_regime+latent_gate+no_src` vs `manual_flags` | A10 WMAPE | **0.020** |

O único resultado significativo é a **degradação** de A10. A melhora em 2025 (p=0.131) não passa de chance com N=10 seeds. Afirmar que o regime latente "melhora anos recentes" sem qualificação estatística é enganoso.

### 1.3 `latent_change` e `change_point` são pseudovariantes

No arquivo `herald_regime_modes.py`, linhas 70-71:

```python
elif regime_mode in {"latent_change", "change_point"}:
    vec = _change_state(growth_z, abs_z, vol_z)
```

Ambos executam o código idêntico. A bateria usa `change_point` como se fosse uma abordagem distinta, mas gera exatamente o mesmo vetor de regime que `latent_change`. A diferença real na bateria é que `change_point` usa variante `full` (regime externo condicionando o grafo), enquanto a série `change_point + learned_regime_gate` combina esse sinal externo com o gate latente. Mas os dois nomes `change_point` e `latent_change` são confusos e enganosos como nomenclatura científica.

### 1.4 Assimetria na penalidade de suavização do grafo

No forward pass do V7 (`train_herald_v7.py`, linhas 215-218):

```python
reg_delta = torch.sum(torch.abs(regime_t - regime_prev))
regime_weight = torch.tanh(reg_delta)
smooth_term = smooth_term + delta_sq * (1.0 - regime_weight)
```

Quando `regime_mode = manual_flags`, o vetor `regime_t` tem valor ~1 em `is_covid_year=2020` e `is_post_covid_rebound=2021`. Isso gera `reg_delta > 0 → regime_weight > 0 → smooth_term reduzido`. O modelo manual tem licença para mudar o grafo drasticamente em anos de crise.

Quando `regime_mode = no_regime`, `regime_t = zeros` para todos os anos. `reg_delta = 0` sempre. `smooth_term` é a penalidade completa. O modelo latente **não tem mecanismo de escape da penalidade de suavização** mesmo que detecte internamente uma quebra. A decisão de design (comentário na linha 213) evita que o latente invente quebras para relaxar a penalidade — mas cria uma comparação intrinsecamente desigual.

**Em resumo:** `manual_flags` tem uma vantagem estrutural de capacidade representacional que o regime latente não tem. Os resultados comparativos não são puros.

### 1.5 `pred.detach()` na cabeça setorial do V7

Em `train_herald_v7.py`, linha 275:

```python
sector_input = torch.cat([h, pred.detach().unsqueeze(-1), sec_prior_t], dim=-1)
```

O `detach()` foi colocado para evitar que o gradiente da loss setorial polua o backbone principal. Esta é uma escolha razoável de engenharia, mas tem um custo: a cabeça setorial não pode aprender que certos regimes estão associados a certas composições setoriais. Ela aprende condicionado no estado `h` (que vem do backbone) mas a predição total não tem gradiente fluindo para a representação compartilhada pela ótica da loss setorial. Isso limita a capacidade do sector head de aprender compensações entre total e composição.

### 1.6 Internals salvos apenas do último fold

Em `train_herald_semi_v2.py`, linha 429:

```python
last = internals_by_year[max(internals_by_year)]
```

O NPZ salva apenas os internals do último fold (target_year=2025). Para auditoria de regime, isso significa que não há NPZ comparativo de como o latente se comportava no fold 2021 (o mais problemático). Não é possível verificar se o regime latente aprendeu algo interpretável para 2020 sem rodar novamente com patch.

---

## 2. Riscos de Vazamento Temporal

### 2.1 Sem vazamento direto — verificado

A função `build_regime_vectors` em `herald_regime_modes.py`:
- Normalização usa `train_mask = target_year <= train_max`. ✓
- `_global_lag_signals` usa `side_lag_1` (lag-1) e `growth_1y`/`growth_2y` (também lags). ✓
- `pct_change()` ao nível global não expõe informação futura porque os lags são do ano anterior. ✓

### 2.2 Latente livre de vazamento — verificado

O regime latente em V7 (linhas 183-187):

```python
latent_context = torch.cat([e_t.mean(dim=0), e_t.std(dim=0, unbiased=False)], dim=-1)
latent_regime_t = self.latent_regime(latent_context)
```

`e_t` é derivado de `x_ann` (features normalizadas por média do train), `x_q` (quarterly, idem), e `h_local` (estado GRU dos passos anteriores). Nenhum desses contém o target futuro. ✓

**Observação importante para defesa:** O GRU `h_local` acumula sinais de 2020-2021 durante o forward pass de inferência. Isso é correto e inevitável — o modelo PODE observar o sinal econômico de 2020, mas não o LABEL manual. Esta distinção deve estar explícita no paper para evitar crítica do tipo "o modelo viu o COVID de qualquer forma."

### 2.3 Imputação — fronteira crítica

Em `make_sequences` (v6), linhas 643-654:

```python
imp.fit(flat_train)
x_ann_train = imp.transform(...)
x_ann_full = imp.transform(...)
mean = x_ann_train.mean(axis=(0,1), keepdims=True)
std  = x_ann_train.std(axis=(0,1), keepdims=True)
```

Imputação e normalização usam apenas dados de treino. ✓

### 2.4 `sector_lag1_tensor` — verificado

```python
def sector_lag1_tensor(sec_props_tensor):
    for t in range(sec_props_tensor.shape[0]):
        if t > 0:
            prev = sec_props_tensor[t-1]
            ...
        out[t] = fill
```

O prior setorial para o ano t usa proporcões reais do ano t-1. Para o fold 2025 com train_max=2024, o prior de 2025 usa os valores observados de 2024. Isso é forecast-safe. ✓

### 2.5 `no_source_flags` remove corretamente

`drop_source_flag_columns` remove exatamente `{'has_flores_source', 'has_side_stock_source', 'has_urssaf_source'}`. Confirmado pelo audit CSV: `dropped_source_flags_count=3` para todos os runs `no_source_flags`. ✓

Entretanto: esses flags de disponibilidade de fonte são **proxies temporais indiretos** — `has_flores_source=0` pode marcar anos antes da entrada do Flores (antes de ~2018). Isso é implicitamente uma flag de época. A decisão de testá-los via ablação é correta.

---

## 3. Avaliação da Metodologia Atual

### 3.1 Hipótese central: está corretamente formulada?

A hipótese "HERALD aprende regimes econômicos sem flags manuais" é legítima, porém **não está operacionalizada de forma refutável com T=14**.

**Problema de potência:** Com T=14, apenas 5 folds de teste (2021-2025), e N=10 seeds para Wilcoxon, o poder estatístico é insuficiente para detectar efeitos menores que ~0.003 WMAPE ao nível 5%. Os resultados actuais têm p ≥ 0.13 para a métrica principal. O experimento não tem tamanho amostral suficiente para confirmar OU refutar a hipótese.

**Alternativa mais defensável:** reformular como "qual é a perda máxima ao substituir flags manuais por regime latente, e é tolerável operacionalmente?" Em vez de testar superioridade, testar não-inferioridade com margem delta=0.002 WMAPE.

### 3.2 O controle `manual_flags` é adequado?

Parcialmente. Há dois controles diferentes que não foram separados claramente:

- `manual_flags + with_source_flags`: controle de produção atual
- `manual_flags + no_source_flags`: controle para comparação justa com o candidato

Phase 2A mostrou que `manual_flags + no_source_flags` (WMAPE=0.02902) é *melhor* que `manual_flags + with_source_flags` (0.02919). Portanto, remover os source flags ajuda mesmo o controle manual. O candidato latente deveria ser comparado **especificamente contra** `manual_flags + no_source_flags`. Phase 2B faz isso (controle `ctrl`), o que é correto.

### 3.3 `no_regime` como controle: é suficiente?

`no_regime` (zeros) serve como "floor" — o modelo sem nenhuma informação de regime. O WMAPE de `no_regime + none + no_source_flags` (0.03008) é pior que todos os outros, o que indica que ALGUM sinal de regime ajuda. Isso é útil, mas não distingue entre:

- O sinal ser útil porque codifica economicamente algo real (crise, expansão)
- O sinal servir apenas como âncora temporal (o modelo aprende a associar o vetor ao índice temporal)

Para distinguir esses casos precisaria de um experimento com **permutação temporal dos vetores de regime** (baralhar os regimes aleatoriamente entre anos mantendo a distribuição marginal). Este controle está ausente.

### 3.4 `change_point`: metodologicamente defensável?

A função `_change_state` usa um threshold manual `abs_z > 1.0`:

```python
positive_break = max(growth_z, 0.0) if abs_z > 1.0 else 0.0
```

Isso é **metodologicamente fraco** pelos seguintes motivos:
- O threshold 1.0 é arbitrário (não há justificativa no código ou documento).
- Não é um método formal de change-point — é uma heurística de z-score.
- Com T≈14, um std de crescimento normalizado inclui muito ruído amostral.
- A saída é determinística (não probabilística): anos com abs_z=0.99 recebem zero, anos com abs_z=1.01 recebem o sinal completo.

Alternativas formais: PELT (Killick et al. 2012, JASA), BOCPD (Adams & MacKay 2007) ou o CUSUM clássico. Qualquer um seria mais defensável em uma publicação.

### 3.5 Critério Pareto: é correto?

O `pareto_rank_hint` em `audit_herald_phase2b_a10_guard.py`:

```python
pareto_rank_hint = rank(mean_wmape) + rank(wmape_2025) + rank(sector_wmape_mean)
```

Isso é **soma de ranks com pesos iguais implícitos** — não é uma análise de Pareto. Uma análise de Pareto real identificaria fronteiras não-dominadas entre os três objetivos sem colapsar em um escalar. A nomenclatura "Pareto hint" no código é honesta, mas o relatório não deve usar esse número como se fosse Pareto-ótimo.

**Problema mais sério:** Os três objetivos têm escalas diferentes e interpretabilidades diferentes:
- `mean_wmape` e `wmape_2025` são altamente correlacionados (mesma escala)
- `sector_wmape_mean` é ~6× maior em magnitude e mede uma coisa diferente

Isso dá ao A10 um peso desproporcional na soma de ranks se houver variação similar em todos os termos.

### 3.6 Confusão melhora-2025 vs. robustez geral

**Sim, há confusão.** O candidato é melhor em 2023-2025 e pior em 2021. A interpretação "melhora anos recentes" está correta mas incompleta. A questão certa é: *o candidato é melhor em anos fora do shock COVID?* Os dados respondem: sim para 2023-2025 (período de normalização pós-COVID), mas não para 2022 (ruído pós-rebote). A melhora parece ser relativa ao aprendizado de tendências de 2023-2025 especificamente.

### 3.7 Interpretabilidade do regime latente

A única métrica de interpretabilidade nos dados é `corr_latent_mean_vs_alpha_mean` (da Phase 2A). Para `no_regime + learned_regime_gate`:
- `corr_latent_mean_vs_alpha_mean = 0.264` (no_source) e `0.119` (with_source)

Correlação de 0.26 entre o regime latente médio e alpha médio é **fraca**. Isso significa que o regime latente não está claramente modulando o gate alpha como esperado. Para o `change_point` equivalente é 0.086. Essas correlações não sustentam a afirmação de que "o regime latente modula o arbitrage local/grafo de forma interpretável."

---

## 4. Leitura da Phase 2A

### 4.1 Integridade

- 80/80 runs completos. ✓
- Todos os metadata JSON presentes e corretos (`source_flags_in_annual_features`, `dropped_source_flags_count`). ✓
- Sementes conforme especificado: 0,1,7,13,17,42,77,99,123,2025. ✓

### 4.2 Leitura fold-by-fold

O único candidato que melhora o WMAPE médio é `no_regime + learned_regime_gate + no_source_flags`. Mas o perfil por fold revela:

| Fold | Característica | Candidato vs Ctrl |
|---|---|---|
| 2021 | rebote COVID | **-52% pior** (crítico) |
| 2022 | pós-rebote, alta volatilidade | levemente melhor |
| 2023 | normalização | **+27% melhor** |
| 2024 | crescimento estável | +17% melhor |
| 2025 | crescimento estável | **+22% melhor** |

O padrão é claro: o regime latente falhou no único ano que requer reconhecimento de crise, mas aprendeu padrões 2023-2025. Isso sugere que o latente não captura eventos extremos com dados insuficientes de treino, mas aprende tendências de curto prazo.

### 4.3 Estabilidade entre seeds

Os coeficientes de variação (std/mean) das 10 seeds:

| Config | CV WMAPE médio | CV WMAPE 2025 | CV A10 |
|---|---|---:|---:|
| manual_flags | 7.0% | 25.8% | 4.4% |
| no_regime+latent_gate | 10.6% | 33.0% | 4.7% |
| change_point+latent_gate | 10.4% | 28.5% | 3.2% |

O candidato latente tem variabilidade 50% maior entre seeds no WMAPE médio vs. controle. Isso é evidência de otimização mais instável — o latente está encontrando soluções diferentes dependendo da inicialização.

### 4.4 A10 por setor

Os dados aggregados mostram A10 WMAPE médio:
- `manual_flags + no_source`: 0.1724
- `no_regime + latent_gate + no_source`: 0.1797

Degradação de +4.2% relativa. O setor mais afetado seria visível nos per-run JSONs (setor KZ=0.251 no seed 0 do controle). O candidato parece degradar mais os setores com maior variabilidade temporal (KZ, LZ, FZ).

### 4.5 Alpha por ano

O alpha médio (local vs. grafo) no fold 2025:
- `manual_flags`: ~0.51 (equilíbrio)
- `no_regime + latent_gate + no_source`: ~0.49 (levemente mais grafo)

Os perfis são similares, o que reforça que o mecanismo latente não está fundamentalmente reorganizando a mistura local/grafo — está fazendo ajustes marginais.

### 4.6 Conclusão sobre Phase 2A

A conclusão "promissor mas ainda não substitui o controle" está **correta mas insuficientemente severa**. O candidato:
- NÃO é melhor de forma significativa em nenhuma métrica (todos p ≥ 0.13 exceto A10)
- É sistematicamente pior em A10 (p=0.020)
- Falha gravemente no fold 2021 que é o mais difícil

A leitura correta é: o candidato aprendeu padrões do período de normalização pós-COVID mas NÃO aprendeu o evento de quebra estrutural (rebote 2021) que os flags manuais capturavam explicitamente.

---

## 5. Plano de Auditoria Phase 2B

Phase 2B ainda não está disponível (`hpc_results/herald_regime_phase2b_a10_guard_20260512_r1/` não existe). Os comandos abaixo assumem que o root será disponível após conclusão do job.

### 5.1 Agregação e integridade

```bash
# Após conclusão do job
ROOT="hpc_results/herald_regime_phase2b_a10_guard_<STAMP>"

# 1. Agregar
python3 hpc/regime/aggregate_herald_regime_results.py --root "$ROOT"

# 2. Auditoria strict (todos os 10 labels × 10 seeds obrigatórios)
python3 hpc/regime/audit_herald_phase2b_a10_guard.py --root "$ROOT" --strict
```

### 5.2 Verificações obrigatórias antes de interpretar

```bash
# a) Confirmar que TODOS os runs usam no_source_flags
python3 -c "
import pandas as pd
df = pd.read_csv('$ROOT/reports/audit_phase2b_a10_guard/phase2b_runs.csv')
assert (df.source_policy == 'no_source_flags').all(), 'CONTAMINAÇÃO: algum run com source flags'
print('source_policy OK')

# b) Confirmar que ctrl é manual_flags, não no_regime
ctrl = df[df.label == 'ctrl']
assert (ctrl.regime_mode == 'manual_flags').all(), 'ctrl não é manual_flags'
print('ctrl identity OK')

# c) Confirmar seed coverage
for lbl, g in df.groupby('label'):
    n = g.seed.nunique()
    if n != 10:
        print(f'ALERTA: label={lbl} tem {n}/10 seeds')
print('seed coverage verificado')
"
```

### 5.3 Tabela principal

Prioridade de leitura (em ordem):

1. **A10 WMAPE**: o candidato resolve a degradação?
2. **WMAPE 2021**: o candidato ainda falha no rebote COVID?
3. **WMAPE médio**: não deve degradar mais de 0.002 vs ctrl

```bash
python3 -c "
import pandas as pd, numpy as np
df = pd.read_csv('$ROOT/reports/audit_phase2b_a10_guard/phase2b_runs.csv')

# Per-fold por label
folds = []
for p in Path('$ROOT/reports/per_run').glob('*.json'):
    import json
    d = json.loads(p.read_text())
    meta = json.loads((Path('$ROOT/metadata') / p.name).read_text())
    for k, v in d.items():
        for yr, wm in v.get('per_year_total', {}).items():
            folds.append({'label': meta.get('experiment_label'), 'seed': v['seed'],
                          'year': int(yr), 'wmape': wm})

fold_df = pd.DataFrame(folds)
tbl = fold_df.groupby(['label','year'])['wmape'].mean().unstack()
print(tbl.to_string())
"
```

### 5.4 Análise Pareto real (não soma de ranks)

```bash
python3 -c "
import pandas as pd
df = pd.read_csv('$ROOT/reports/audit_phase2b_a10_guard/phase2b_summary.csv')
# Fronteira de Pareto sobre 3 objetivos
def is_dominated(row, others):
    return any(
        (o.mean_wmape <= row.mean_wmape) and
        (o.wmape_2025 <= row.wmape_2025) and
        (o.sector_wmape_mean <= row.sector_wmape_mean) and
        (o.mean_wmape < row.mean_wmape or o.wmape_2025 < row.wmape_2025 or
         o.sector_wmape_mean < row.sector_wmape_mean)
        for o in others.itertuples()
    )
pareto = [r for r in df.itertuples() if not is_dominated(r, df[df.label != r.label])]
print('Pareto-ótimos:')
for r in pareto:
    print(f'  label={r.label} mean={r.mean_wmape:.5f} 2025={r.wmape_2025:.5f} A10={r.sector_wmape_mean:.5f}')
"
```

### 5.5 Análise pareada vs ctrl (por seed)

```bash
python3 hpc/regime/audit_herald_phase2b_a10_guard.py --root "$ROOT"
# Verificar: paired_vs_ctrl.csv
# Critério: coluna mean_wmape_p < 0.05 E mean_wmape_delta < 0 para aceitar candidato
# Critério: coluna sector_wmape_mean_delta <= 0 para aceitar (A10 não piorou)
```

### 5.6 Análise A10 por setor

```bash
python3 -c "
import pandas as pd
from pathlib import Path
import json, glob

# Comparar sector_wmape por setor para cada label
rows = []
for p in Path('$ROOT/reports/per_run').glob('*.json'):
    d = json.loads(p.read_text())
    meta_p = Path('$ROOT/metadata') / p.name
    meta = json.loads(meta_p.read_text()) if meta_p.exists() else {}
    for k, v in d.items():
        lbl = meta.get('experiment_label', 'unknown')
        for s, wm in v.get('sector_wmape', {}).items():
            rows.append({'label': lbl, 'seed': v['seed'], 'sector': s, 'wmape': wm})
df = pd.DataFrame(rows)
tbl = df.groupby(['label', 'sector'])['wmape'].mean().unstack()
delta = tbl.subtract(tbl.loc['ctrl'], axis=1)
print('Delta A10 por setor vs ctrl (negativo = melhor):')
print(delta.drop('ctrl').to_string())
"
```

### 5.7 Critério de decisão Phase 2B

Um candidato avança somente se satisfizer **todos** os critérios:

| Critério | Threshold | Prioridade |
|---|---|---|
| WMAPE médio vs ctrl | delta ≤ +0.001 | BLOQUEADOR |
| WMAPE 2021 vs ctrl | delta ≤ +0.005 | BLOQUEADOR |
| A10 WMAPE vs ctrl | delta ≤ 0 (não degradar) | BLOQUEADOR |
| WMAPE 2025 vs ctrl | delta ≤ 0 (melhora) | Desejável |
| Wilcoxon p (A10) | p ≥ 0.05 (não sign. degradação) | BLOQUEADOR |
| CV entre seeds | ≤ 12% WMAPE médio | Desejável |

---

## 6. Literatura Relevante

### 6.1 Artigos consolidados

**Regime switching e modelos de estado:**
- Hamilton, J.D. (1989). "A New Approach to the Economic Analysis of Nonstationary Time Series and the Business Cycle." *Econometrica*, 57(2), 357-384. — O modelo fundacional de Markov-switching. HERALD usa uma gate determinística onde Hamilton usaria probabilidades de transição estocásticas.
- Kim, C.-J. (1994). "Dynamic linear models with Markov-switching." *Journal of Econometrics*, 60(1-2), 1-22. — Combina filtro de Kalman com Markov switching; relevante para o componente de estado latente.

**Change-point formal:**
- Killick, R., Fearnhead, P., & Eckley, I.A. (2012). "Optimal Detection of Changepoints with a Linear Computational Cost." *Journal of the American Statistical Association*, 107(500), 1590-1598. — Algoritmo PELT; substituto direto para `_change_state`.
- Adams, R.P. & MacKay, D.J.C. (2007). "Bayesian Online Changepoint Detection." arXiv:0710.3742. — BOCPD; fornece probabilidades de run-length, forecast-safe por construção.

**Graph neural networks para séries temporais:**
- Wu, Z., Pan, S., Chen, F., Long, G., Zhang, C., & Yu, P.S. (2020). "Connecting the Dots: Multivariate Time Series Forecasting with Graph Neural Networks." *KDD 2020*. — MTGNN aprende adjacência dinamicamente; arquitetura mais próxima de HERALD.
- Yu, B., Yin, H., & Zhu, Z. (2018). "Spatio-Temporal Graph Convolutional Networks: A Deep Learning Framework for Traffic Forecasting." *IJCAI 2018*. — STGCN; baseline padrão para grafo espácio-temporal.

**Mixture of Experts:**
- Jordan, M.I. & Jacobs, R.A. (1994). "Hierarchical Mixtures of Experts and the EM Algorithm." *Neural Computation*, 6(2), 181-214. — Fundamento teórico do MoE; relevante para avaliar se o mecanismo `alpha_gate` é de fato um expert routing.
- Shazeer, N., et al. (2017). "Outrageously Large Neural Networks: The Sparsely-Gated Mixture-of-Experts Layer." *ICLR 2017*. — Mostra que o colapso de experts é o problema central no MoE treinado com gradiente; diretamente relevante para HERALD.

**Painéis curtos e T pequeno:**
- Arellano, M. & Bond, S. (1991). "Some Tests of Specification for Panel Data." *Review of Economic Studies*, 58(2), 277-297. — Mostra os limites de métodos NN em painéis com T pequeno; contexto para HERALD (T≈14).

**Attention e regime:**
- Bahdanau, D., Cho, K., & Bengio, Y. (2015). "Neural Machine Translation by Jointly Learning to Align and Translate." *ICLR 2015*. — Fundamento do mecanismo de atenção usado no dynamic_adj de HERALD.

### 6.2 Preprints promissores (verificar existência antes de citar)

- Bhethanabhotla, S. et al. (ca. 2023). "Mixture of Experts for Time Series Forecasting" — Vários grupos testaram MoE para séries temporais; verificar literatura recente em arXiv:cs.LG + "time series" + "mixture of experts".
- Trabalhos recentes sobre "latent regime learning" + "economic forecasting": buscar NeurIPS/ICLR 2023-2025 com termos "regime-aware forecasting" ou "structural break neural".

**ATENÇÃO:** Não citar preprints sem verificar existência e conteúdo real. As entradas acima são direcionamentos de busca, não citações verificadas.

### 6.3 Ideias especulativas (não publicadas neste contexto)

- "Temporal Graph Network" (Rossi et al., ICLR 2020) — grafo que evolui com tempo; possível base para tratar o grafo territorial como dinâmico com regimes.
- State Space Models neurais (S4, Mamba): não adequados diretamente (projetados para sequências longas), mas a ideia de estado latente eficiente pode inspirar uma versão compacta do latent_regime para T pequeno.

---

## 7. Propostas de Arquitetura

Ordenadas por viabilidade para T≈14:

### 7.1 Substituir `_change_state` por PELT/BOCPD (ALTA PRIORIDADE)

O threshold manual `abs_z > 1.0` em `_change_state` é cientificamente fraco. Substituir por:

```python
# Pré-processamento ex-ante: rodar BOCPD nos dados de treino
# Saída: probabilidade de changepoint em cada ano
from ruptures import Pelt  # pip install ruptures

def change_point_pelt(growth_series, penalty=3.0):
    """Forecast-safe: usar apenas train_data até train_max."""
    model = Pelt(model="rbf").fit(growth_series.reshape(-1,1))
    breakpoints = model.predict(pen=penalty)
    # Converter em vetor binário por ano
    vec = np.zeros(len(growth_series))
    for bp in breakpoints[:-1]:
        if bp < len(vec):
            vec[bp] = 1.0
    return vec
```

Isso substitui `_change_state` por detecção estaticamente fundamentada. A penalidade `pen` é um hiperparâmetro, mas documentável e com interpretação clara (BIC-like).

### 7.2 Penalização de colapso de regime latente (ALTA PRIORIDADE)

O código não tem garantia de que o regime latente use os 3 componentes de forma diferenciada. Adicionar:

```python
# Na loss: penalizar variância baixa do latente ao longo do tempo
latent_stack = torch.stack(latent_regime_list, dim=0)  # (T, REGIME_DIM)
latent_var = latent_stack.var(dim=0).mean()
collapse_penalty = args.collapse_lambda * torch.clamp(0.1 - latent_var, min=0.0)
loss = loss + collapse_penalty
```

Isso garante que o regime latente varie ao longo do tempo em vez de colapsar para um vetor constante.

### 7.3 Regime latente com horizonte temporal (MÉDIA PRIORIDADE)

O regime latente atual usa apenas `e_t.mean(0)` e `e_t.std(0)` — pooling instantâneo sobre zonas. Para T pequeno, adicionar uma janela temporal:

```python
# Usar h_local acumulado como contexto estendido
# h_local já carrega informação dos passos anteriores via GRU
# Adicionar a diferença entre h_local atual e h_local anterior como sinal de mudança
if h_local_prev is not None:
    change_signal = torch.norm(h_local - h_local_prev, dim=-1).mean()
    latent_context = torch.cat([
        e_t.mean(dim=0), e_t.std(dim=0, unbiased=False),
        change_signal.unsqueeze(0).expand(self.hidden_dim)  # broadcast
    ], dim=-1)
```

Isso dá ao regime latente um sinal de "quão diferente o estado atual é do anterior" sem usar nenhuma label manual.

### 7.4 Gate de incerteza para A10 (ALTA PRIORIDADE para Phase 2B)

A degradação de A10 pode ser mitigada com um gate de confiança na cabeça setorial:

```python
# Uncertainty-weighted blend entre prior (conservador) e neural (mais expressivo)
# A uncertainty vem da entropia do estado h: baixa entropia = alta confiança no neural
h_entropy = -(torch.softmax(h, dim=-1) * torch.log_softmax(h, dim=-1)).sum(-1, keepdim=True)
confidence = torch.sigmoid(-h_entropy)  # alta entropia = baixa confiança
prior_weight = (1.0 - confidence) * torch.sigmoid(self.sector_prior_gate(sector_input))
sector = prior_weight * sec_prior_t + (1.0 - prior_weight) * neural_sector
```

Isso protege o A10 em anos de incerteza (onde h tem entropia alta, como crises) sem fixar o prior completamente.

### 7.5 Loss multi-objetivo com ε-constraint A10 (ALTA PRIORIDADE)

Em vez de `sector_lambda` como hiperparâmetro de busca, implementar um ε-constraint dinâmico:

```python
# Durante treino: se loss_sec exceder threshold epsilon, aumentar peso dinamicamente
epsilon_sec = args.sector_epsilon  # e.g. 0.15 (valor alvo de loss setorial)
if loss_sec.item() > epsilon_sec:
    effective_lambda = args.sector_lambda * (loss_sec.item() / epsilon_sec)
else:
    effective_lambda = args.sector_lambda
loss = loss_main + effective_lambda * loss_sec + loss_rank + loss_graph
```

Isso elimina o grid search de `sector_lambda` e garante que A10 não degrade abaixo de um threshold.

### 7.6 Penalidade de suavização simétrica (CORREÇÃO DE BUG METODOLÓGICO)

Para resolver a assimetria identificada na seção 1.4, o peso de regime_weight deveria usar o sinal latente quando regime explícito é zero:

```python
# Usar o norm do latente como proxy de regime_weight quando regime explícito = 0
if variant in learned_gate_variants:
    effective_regime = latent_regime_t
else:
    effective_regime = regime_t

if A_t is not None and A_prev is not None:
    delta_sq = torch.sum((A_t - A_prev) ** 2)
    reg_delta = torch.sum(torch.abs(effective_regime - regime_prev_eff))
    regime_weight = torch.tanh(reg_delta)
    smooth_term = smooth_term + delta_sq * (1.0 - regime_weight)
```

Isso permite ao regime latente também relaxar a penalidade de suavização quando detecta uma quebra, tornando a comparação justa.

**ATENÇÃO:** Esta mudança altera o incentivo de treinamento — o modelo poderia criar quebras falsas para relaxar a penalidade. O comentário existente no código explica explicitamente por que isso foi evitado. Se for implementado, adicionar penalidade de colapso (#7.2) simultaneamente.

### 7.7 Router local/grafo por setor (BAIXA PRIORIDADE — requer T>20)

MoE com 3 experts: local_only, graph_only, setor-específico. Com T=14 isso é sub-identificado. Reservar para quando o painel estiver disponível até 2027+.

---

## 8. Ablações Obrigatórias

As seguintes ablações são necessárias antes de qualquer publicação:

### 8.1 Ablação de permutação temporal do regime (CRÍTICA)

Baralhar os vetores de regime aleatoriamente entre anos (mantendo a distribuição marginal). Se o modelo ainda funcionar bem, o regime não está sendo usado como informação sobre o estado econômico — está sendo usado como âncora temporal.

```bash
# Adicionar em train_herald_regime_experiment.py:
# --regime-temporal-shuffle: permuta o vetor de regime entre anos do treino
```

### 8.2 Ablação de regime constante não-zero

Usar um vetor de regime constante = [0.5, 0.5, 0.5] para todos os anos. Se isso for equivalente a `no_regime`, o regime não tem efeito dinâmico real.

### 8.3 Ablação de single-fold 2021

Rodar o candidato com treino apenas até 2020 (fold 2021 isolado) e reportar a WMAPE especificamente para o rebote. Se o candidato não consegue prever 2021 mesmo sem os outros folds, o problema é estrutural.

### 8.4 Ablação do latente removido (latente zerado na inferência)

Durante inferência, forçar `latent_regime_t = zeros`. Se WMAPE não mudar, o latente não está sendo usado de fato pelo modelo.

### 8.5 Bootstrap temporal para band de confiança

Com N=10 seeds, a incerteza amostral é alta. Adicionar bootstrap sobre os dados de treino (block bootstrap preservando a estrutura temporal) para estimar a variabilidade da métrica atribuível aos dados versus à inicialização do modelo.

---

## 9. Critério de Decisão Final

### 9.1 Phase 2B — aceitar um candidato se e somente se:

```
CONDIÇÃO NECESSÁRIA (todos devem ser verdadeiros):
  1. delta_wmape_2021 ≤ +0.005 vs ctrl (não quebrar no rebote COVID)
  2. delta_A10_wmape ≤ 0 vs ctrl (não degradar setor)
  3. p_wilcoxon(A10) ≥ 0.05 (degradação A10 não significativa)
  4. delta_wmape_medio ≤ +0.001 vs ctrl

CONDIÇÃO SUFICIENTE (ao menos um):
  5. delta_wmape_2025 < -0.002 vs ctrl (melhora recente significativa)
  6. OR: delta_wmape_medio < -0.001 vs ctrl (melhora geral)
```

### 9.2 Phase 2B — o que fazer com resultado de cada linha

| Label | O que testar | Aceitar se |
|---|---|---|
| `ctrl` | baseline de referência | — |
| `candidate` | candidato Phase 2A sem mudança | Falha esperada em 2021 |
| `sec02`..`sec05` | mais peso A10 | se resolve A10 sem quebrar 2021 |
| `secenh` | sector_enhanced + latent | candidato mais forte para Phase 3 |
| `alpha005` | mais suavização alpha | se estabiliza sem perder 2025 |
| `smooth003` | mais suavização grafo | — |
| `cp_sec02` | change_point como auxílio | se PELT melhorar cp, substituir |
| `both_sec02` | latente grafo+gate | maior expressividade, maior risco overfit |

### 9.3 Recomendação final por linha de código

| Componente | Recomendação | Urgência |
|---|---|---|
| `is_covid_year` + `is_post_covid_rebound` | **Manter provisoriamente** | — |
| `_change_state` threshold manual | **Substituir por PELT/BOCPD** | Alta |
| `latent_regime` sem colapso prevention | **Adicionar penalidade de variância** | Alta |
| Smooth_term assimétrico | **Corrigir ou documentar explicitamente como design choice** | Média |
| `pred.detach()` no sector head | **Manter** — gradiente cruzado cria instabilidade | Baixa |
| `internals` single-fold | **Salvar por fold** para auditoria real | Média |
| Pareto com soma de ranks | **Substituir por fronteira Pareto formal** | Média |
| Wilcoxon com N=10 | **Reportar como evidência fraca, não conclusiva** | Alta |

---

## 10. Questões Abertas para o Professor

1. **Interpretabilidade vs. desempenho**: O regime latente com melhor WMAPE em 2023-2025 e pior em 2021 tem valor científico mesmo assim? Ou a robustez ao shock de 2021 é não-negociável para a claim?

2. **O T=14 é suficiente para o claim?**: Com 5 folds de teste, nenhum resultado é estatisticamente significativo. O paper precisaria reformular a claim como "direção promissora" ou "prova de conceito" — não como evidência de superioridade.

3. **Flag proxy vs. flag causal**: `is_covid_year` é uma flag de época (qualquer modelo pode aprender "o modelo vai bem nos anos recentes"). Um regime latente que funciona somente em 2023-2025 pode ser igualmente tautológico — está codificando "depois de 2022" sem entender o que aconteceu.

4. **Comparação com o professor**: O professor criticou os flags manuais por "condicionar o modelo a reconhecer a crise". Mas um regime latente que piora em 2021 e melhora em 2023-2025 não resolveu esse problema — apenas o substituiu por uma heurística de tendência recente.

---

*Auditoria concluída. Relatório baseado exclusivamente no código e dados disponíveis em:*
- `src/modeles/train_herald_v7.py`
- `src/modeles/train_herald_semi_v2.py`
- `src/modeles/train_herald_regime_experiment.py`
- `src/modeles/herald_regime_modes.py`
- `hpc/regime/*.{py,sh}`
- `hpc_results/herald_regime_discovery_20260512_latentgate_phase2a_r2/`
- `reports/HERALD_REGIME_DISCOVERY_BATTERY.md`
