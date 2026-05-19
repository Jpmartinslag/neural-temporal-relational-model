# HERALD Regime Discovery — Phase 2C Critical Plan

Data: 2026-05-12 | Versão: 1.1
Status: **Preparação concluída (sem lançamento GPU)**

### Correções aplicadas nesta sessão

- ✅ `train_herald_regime_experiment.py`: metadata JSON agora registra `smooth_regime_source`,
  `latent_train_mode`, `latent_inference_mode`, `regime_seq_transform`, `single_target_year`,
  `is_falsification_test`, `comparison_is_symmetric`. Antes esses campos eram invisíveis
  ao sistema de auditoria, tornando impossível distinguir runs de falsificação de candidatos reais.
- ✅ `hpc/regime/audit_herald_phase2c_critical.py`: novo script de auditoria específico para
  Phase 2C. Lê os novos campos do metadata e analisa as duas questões críticas separadamente
  (smooth simétrico e falsificação). Produce `PHASE2C_CRITICAL_AUDIT.md` com veredicto por
  falsificação, fold-by-fold e critério de encaminhamento explícito.

---

## 1. Objetivo científico da Phase 2C

Testar se o ganho recente de `no_regime + learned_regime_gate + no_source_flags` é:

1. **defensável metodologicamente** (sem vantagem estrutural oculta),
2. **funcional** (regime realmente modula decisão, não apenas decorativo),
3. **robusto** (não depende de um fold/ano específico),
4. **compatível com A10** (sem troca implícita de objetivo).

Phase 2C é deliberadamente **crítica/falsificadora**.

---

## 2. Problema estrutural corrigido: smoothing assimétrico

### 2.1 Achado

No `train_herald_v7.py`, o `smooth_term` reduz penalização quando `reg_delta` é alto:

`smooth_term += delta_sq * (1 - tanh(reg_delta))`

Se `reg_delta` vem de `regime_t` explícito:

- `manual_flags`: tem saltos exógenos (COVID/rebound) e recebe alívio;
- `no_regime`: vetor zero, sem alívio.

Isso introduz assimetria metodológica.

### 2.2 Patch experimental (já preparado)

Novo controle em V7/SemiV2:

- `--smooth-regime-source explicit` (default, comportamento antigo)
- `--smooth-regime-source none` (**simétrico crítico**: nenhum alívio por regime)
- `--smooth-regime-source latent` (alívio guiado por latente, experimental)

Implementado sem quebrar o principal: defaults preservam comportamento atual.

---

## 3. Change-point formal (especificação precisa, ainda não implementado)

### 3.1 Diretriz

Substituir heurística `change_point` por CP formal causal por fold (preferência: PELT).

### 3.2 Inputs (causais)

Para cada fold com `train_max`:

- usar apenas anos `<= train_max`;
- série anual agregada de sinais lagged (`global_growth`, `abs(global_growth)`, `local_dispersion`);
- **sem target futuro**.

### 3.3 Formulação proposta (PELT, custo L2)

Para série \(x_{1:n}\), otimizar:

\[
\min_{\tau} \sum_{k=0}^{m} C(x_{\tau_k+1:\tau_{k+1}}) + \beta m
\]

- \(C\): SSE intrassegmento (piecewise-constant mean),
- \(\beta\): penalização (ex.: \(\log(n)\hat{\sigma}^2\) no treino do fold).

Saída por ano:

- `cp_state_t = [is_break_t, distance_to_last_break_t, segment_vol_t]` (dim=3).

Para anos > `train_max` no mesmo fold:

- atualizar estado apenas com observáveis do ano corrente (sem recomputar com dados futuros).

### 3.4 Implementação de referência (Python, requer `ruptures`)

```python
import ruptures as rpt
import numpy as np

def change_point_pelt_per_fold(global_growth_train: np.ndarray,
                                train_years: list,
                                all_years: list,
                                penalty: float = 3.0) -> np.ndarray:
    """
    Detecta breakpoints em global_growth_train (apenas anos <= train_max).
    Retorna vetor binário len(all_years): 1 = início de novo regime no treino, 0 caso contrário.
    Anos de teste ficam sempre em 0 (forecast-safe).
    penalty ≈ 3.0 ~ BIC para T pequeno. Testar {1.5, 3.0, 6.0}.
    """
    if len(global_growth_train) < 3:
        return np.zeros(len(all_years), dtype=np.float32)
    try:
        algo = rpt.Pelt(model="rbf", min_size=2, jump=1)
        bps = algo.fit(global_growth_train.reshape(-1, 1)).predict(pen=penalty)
    except Exception:
        return np.zeros(len(all_years), dtype=np.float32)

    break_years = set()
    for bp in bps[:-1]:  # último é sempre len(série)
        if 0 < bp < len(train_years):
            break_years.add(train_years[bp])

    year_to_idx = {y: i for i, y in enumerate(all_years)}
    vec = np.zeros(len(all_years), dtype=np.float32)
    for yr in break_years:
        if yr in year_to_idx:
            vec[year_to_idx[yr]] = 1.0
    return vec
```

Para produzir um vetor de regime REGIME_DIM=3 equivalente ao `_change_state`:
`[is_break_t, distance_to_last_break_normalized, segment_volatility_t]`.

### 3.5 Riscos metodológicos

- T pequeno (14 anos) ⇒ alta variância de breakpoints entre folds;
- penalização β sensível — reportar sensibilidade a {1.5, 3.0, 6.0};
- CP deve ser tratado como **sinal auxiliar**, não verdade causal;
- `ruptures` deve estar disponível no ambiente HPC (verificar antes de lançar).

---

## 4. Testes de falsificação (Phase 2C)

Novos controles em SemiV2/V7 (já preparados):

1. `--regime-seq-transform permute_random` (regime temporal permutado),
2. `--latent-inference-mode zero` (latente zerado apenas na inferência),
3. `--latent-train-mode frozen_first` (latente congelado),
4. `--single-target-year 2021` (fold 2021 isolado).

Interpretação:

- se permutar não piora, regime explícito/latente está fraco;
- se zerar latente em inferência não muda, latente é decorativo;
- se congelar latente não piora, latente não carrega dinâmica útil;
- fold 2021 isolado testa robustez em transição crítica.

### ⚠️ Limitação crítica: `falsify_regime_permute` para `no_regime`

Para `regime_mode=no_regime`, o vetor de regime explícito é sempre zero. A permutação
temporal de um vetor de zeros é trivialmente idêntica ao original. Portanto
**`falsify_regime_permute` não testa nada quando `regime_mode=no_regime`**.

Para tornar este teste informativo, há duas opções:

**Opção A (recomendada, sem modificação de código):** usar `regime_mode=change_point`
em vez de `no_regime` para o teste de permutação. O `change_point` produz um vetor
não-trivial que, ao ser permutado, perde o alinhamento temporal:

```
change_point + learned_regime_gate + no_source_flags + falsify_regime_permute
```

**Opção B (modificação maior):** implementar `--feature-annual-temporal-shuffle` em
`train_herald_semi_v2.py` — permuta a sequência de anos das features anuais `x_ann`.
Isso testaria se o backbone usa estrutura temporal das features, não apenas o regime.

Phase 2C mantém a config atual (`no_regime + permute`) como placeholder, reconhecendo
que ela não é informativa. Substituir por Opção A antes de lançar.

---

## 5. Configurações exatas da bateria Phase 2C

Plano de execução: `REGIME_PLAN=phase2c_critical` (já adicionado no script HPC).

1. `manual_flags + full + no_source_flags + ctrl_manual`
2. `no_regime + full + no_source_flags + ctrl_noregime`
3. `no_regime + learned_regime_gate + no_source_flags + cand_baseline`
4. `no_regime + learned_regime_gate + no_source_flags + cand_sym_smooth`
   - `smooth_regime_source=none`
5. `no_regime + learned_regime_gate + no_source_flags + falsify_regime_permute`
   - `smooth_regime_source=none`, `regime_seq_transform=permute_random`
6. `no_regime + learned_regime_gate + no_source_flags + falsify_latent_inf_zero`
   - `smooth_regime_source=none`, `latent_inference_mode=zero`
7. `no_regime + learned_regime_gate + no_source_flags + falsify_latent_frozen`
   - `smooth_regime_source=none`, `latent_train_mode=frozen_first`
8. `no_regime + learned_regime_gate + no_source_flags + fold2021_probe`
   - `smooth_regime_source=none`, `single_target_year=2021`

Seeds sugeridas:

- mínimo: 10 seeds padrão (`0 1 7 13 17 42 77 99 123 2025`)
- recomendado para inferência mais forte: 20+ seeds

---

## 6. Critérios de vitória (Phase 2C)

Uma variante sem flags manuais só avança se:

1. mantém restrições de causalidade (sem `is_covid_year`/`is_post_covid_rebound`, sem target futuro);
2. `Δ mean WMAPE` vs `ctrl_manual` dentro de não-inferioridade (margem operacional definida);
3. `Δ 2025` não piora;
4. `Δ A10` não piora de forma consistente;
5. testes de falsificação **derrubam** variantes decorativas;
6. ganho não depende exclusivamente de 2025 nem de poucas zonas.

---

## 7. Artefatos esperados

Por seed e config:

- `reports/per_run/*.json` e `*.md`,
- `data_processed/herald_semi_v2_predictions_total_*.csv`,
- `data_processed/herald_semi_v2_predictions_sector_*.csv`,
- `data_processed/herald_semi_v2_internals_*.npz`,
- `metadata/*.json`.

Agregados:

- `reports/herald_regime_discovery_runs.csv`,
- `reports/herald_regime_discovery_summary.csv`,
- relatório auditável por pareado/fold/setor.

---

## 8. Comandos HPC (preparados, não executados)

Validação de plano:

```bash
python3 hpc/regime/audit_herald_regime_plan.py \
  --root hpc_results/herald_regime_phase2c_critical_<STAMP> \
  --seeds "0 1 7 13 17 42 77 99 123 2025" \
  --plan phase2c_critical
```

Submissão (quando autorizado):

```bash
STAMP=$(date +%Y%m%d_%H%M%S)
OUT_ROOT="hpc_results/herald_regime_phase2c_critical_${STAMP}" \
REGIME_PLAN=phase2c_critical \
bash hpc/regime/submit_herald_regime_discovery.sh
```

Monitoramento:

```bash
squeue -u "$USER"
sacct -j <JOBID> --format=JobID,JobName%30,State,ExitCode,Elapsed
tail -f logs/herald-regime-<JOBID>_0.out
```

---

## 9. Checklist operacional

### 9.1 Corrigir antes de GPU

- [x] `train_herald_regime_experiment.py`: registrar novos campos no metadata (**feito**).
- [x] `audit_herald_phase2c_critical.py`: criar script de auditoria Phase 2C (**feito**).
- [ ] **Corrigir `falsify_regime_permute`**: substituir `no_regime` por `change_point` como
  regime_mode para que a permutação tenha efeito real (ver seção 4 acima).
- [ ] **Definir margem formal de não-inferioridade**: ex. `delta_wmape ≤ +0.001` vs ctrl.
  Documentar antes de lançar para evitar ajuste pós-hoc do threshold.
- [ ] **Confirmar `ruptures` disponível no HPC**: necessário para PELT (se incluído na Phase 2C).
- [ ] **Confirmar política de múltiplas comparações**: com 8 configs e 3 métricas, são 24
  testes. Decidir entre Bonferroni, FDR, ou simplesmente reportar sem correção (e reconhecer).

### 9.2 Pode testar com smoke CPU (10 epochs, 2 seeds)

```bash
REGIME_PLAN=phase2c_critical EPOCHS=10 SEEDS="0 1" DEVICE=cpu \
  bash hpc/regime/submit_herald_regime_discovery.sh
```

Verificar após smoke:
- [ ] 8 × 2 = 16 JSONs de per_run gerados.
- [ ] Metadata JSON tem os campos: `is_falsification_test`, `smooth_regime_source`,
  `latent_train_mode`, `latent_inference_mode`, `regime_seq_transform`, `single_target_year`.
- [ ] `fold2021_probe`: CSV de predições tem apenas ZE2020 do ano 2021.
- [ ] `falsify_latent_inf_zero`: NPZ internals tem `latent_regime_values ≈ 0`.
- [ ] `falsify_latent_frozen`: NPZ internals tem `latent_regime_values[0] ≈ latent_regime_values[-1]`.
- [ ] `audit_herald_phase2c_critical.py` processa os 16 runs sem erro.
- [ ] `py_compile` de todos os scripts principais passa sem erro.

### 9.3 Só após treino completo

- [ ] Comparação robusta fold-by-fold com 10 seeds completas.
- [ ] Wilcoxon pareado com N=10 (reportar como evidência fraca se p ≥ 0.05).
- [ ] Perfil A10 por setor para `cand_sym_smooth` vs `ctrl_manual`.
- [ ] Mapas de erro por zona (concentração geográfica do ganho/perda).
- [ ] Decisão final de avanço para Phase 3 (MoE) baseada nos 4 critérios da seção 6.

---

## 10. Nota crítica final

Phase 2C não é para “confirmar” a hipótese de regime aprendido.
É para tentar **falsificá-la** sob controles metodológicos mais justos.
