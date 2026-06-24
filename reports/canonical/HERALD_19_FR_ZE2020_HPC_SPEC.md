# HERALD 19 — France ZE2020 HPC Spec

**Created:** 2026-06-24. **Status:** SPEC_READY, **NÃO LANÇADO**. Este documento prepara a
submissão HPC para o cluster `meso` seguindo o "modo normal" já documentado do projeto
(`hpc/README.md`, `hpc/phase10_synthetic_lagged/README.md`). Nenhum `sbatch` foi
executado para produzir este documento. Submissão real exige confirmação humana
explícita (flag `--confirm-submit`, ver §6).

**Lido antes desta pass:** `/home/jpdark/.codex/RTK.md`, `hpc/README.md`,
`hpc/phase10_synthetic_lagged/README.md`, `reports/canonical/HERALD_18_FR_ZE2020_TRAINING_PLAN.md`,
`reports/herald_artifact_registry.json`, `reports/canonical/HERALD_10_CODE_PATH_MAP.md`.

---

## 0. Estado remoto verificado nesta pass (Tarefa 1)

| Verificação | Resultado |
|---|---|
| `ssh meso` | **OK** — `hpclogin01`, alias `meso` via `~/.ssh/config` (`ProxyJump mesoext`) |
| Diretório remoto `~/project_recomm_herald_v6_2025_20260430/dataset` | **OK**, existe |
| Git no diretório remoto | **NÃO é repositório git** (`fatal: not a git repository`) — sincronização é puramente via `rsync`, não `git pull`. Não há "commit remoto" a reportar; o estado remoto é o que o último `rsync` deixou lá |
| `~/.conda/envs/herald-v5/bin/python` | **OK**, Python 3.10.20 |
| `sklearn`/`pandas`/`numpy` no env remoto | `sklearn 1.7.2` (idêntico ao local), `pandas 2.3.3` (idêntico ao local), `numpy 2.2.6` (local é `1.26.4` — diferença de versão major, não testada; nenhuma operação deste bloco usa API específica de uma versão, mas fica registrado) |
| `sbatch`/`squeue` | **OK**, ambos em `/usr/bin/` |
| Disco | 50G livres / 100G (51% usado) — folga ampla para esta carga (sklearn, sem tensores grandes) |
| `hpc_results/` remoto | **Existe**, 5.4G já ocupados (de batteries anteriores, não relacionadas a este bloco) |
| `data/processed/france_ze2020/` remoto | **AUSENTE** — nada deste bloco foi sincronizado ainda |
| `src/modeles/france_ze2020/` remoto | **AUSENTE** |
| `hpc/france_ze2020/` remoto | **AUSENTE** (será criado por esta pass, localmente, e sincronizado depois) |

**Conclusão da Tarefa 1:** infraestrutura pronta (conexão, ambiente, scheduler, disco).
Nada deste bloco está sincronizado ainda — o primeiro passo de qualquer execução futura
é o `rsync` do §6.

---

## 1. Objetivo HPC

Rodar, em paralelo e com múltiplas seeds (o smoke local usou seed única), os 4 scripts
do bloco de treino já auditado (`HERALD_18_FR_ZE2020_TRAINING_PLAN.md`) para: (a)
verificar se o resultado smoke (nenhum modelo relacional/neural bateu o baseline) se
mantém estável através de seeds, ou se há variância que mude a leitura; (b) coletar
`feature_signals`/`relation_signals` através de múltiplas seeds para avaliar
estabilidade exploratória (H3); (c) produzir o primeiro teste formal das hipóteses
H1-H4, ainda dentro de um orçamento de cômputo modesto (CPU + sklearn, não GPU/torch).

**Não é objetivo desta etapa:** produzir um claim de performance final, treinar um GNN
real, ou autorizar recomendação automática.

## 2. Hipóteses (H1-H4)

- **H1** — Relações ZE→ZE e ZE×setor podem melhorar a representação econômica
  territorial, mesmo sem ganho claro no primeiro smoke local.
- **H2** — O grafo ZE×setor pode aprender padrões exploratórios entre composição
  setorial, zonas similares e trajetória temporal.
- **H3** — A avaliação neural/grafo deve medir WMAPE e também estabilidade/utilidade
  dos `relation_signals`.
- **H4** — A saída deve separar previsão, relação exploratória e caveat não causal.

Nenhuma das 4 foi testada formalmente ainda (HERALD_18 §5/§7) — esta é a primeira
tentativa de teste formal, com múltiplas seeds, não apenas um único smoke run.

## 3. Inputs oficiais

```
data/processed/france_ze2020/fr_ze2020_model_ready_panel.csv
data/processed/france_ze2020/fr_ze2020_relational_model_ready_panel.csv
data/processed/france_ze2020/fr_ze2020_relational_sector_prototype_panel.csv
data/processed/france_ze2020/fr_ze2020_sector_panel.csv
data/processed/france_ze2020/fr_ze2020_sector_relational_features.csv
```

Nenhum painel novo é criado por esta etapa. `dynamic_stgnn_feature_panel*` e
`graph_adjacency_core_v0.csv`/`mobility_v0.csv` **nunca** são lidos (verificado por
teste em cada um dos 4 scripts, herdado de HERALD_17/18).

## 4. Modelos, targets, seeds, anos

| Script | Modelos | Target | Grão | Produz `feature_signals`/`relation_signals`? |
|---|---|---|---|---|
| `train_fr_ze2020_baselines.py` | persistence, ridge_temporal | `observed_value` | ZE×ano | Não |
| `train_fr_ze2020_relational_baselines.py` | + ridge_relational | `observed_value` | ZE×ano | Não |
| `train_fr_ze2020_neural_relational_mlp.py` | + mlp_relational | `observed_value` (via razão `obs/lag_1`) | ZE×ano | Sim — `feature_signals` (permutation importance) |
| `train_fr_ze2020_sector_graph_prototype.py` | persistence_sector, graph_mlp | `sector_share` | ZE×setor×ano | Sim — `relation_signals` (intra-ZE + cross-ZE) |

**Seeds:** `[42, 43, 44, 45, 46]` — 5 seeds, não 1 (o smoke local usou só `SEED=42`).
Persistence/Ridge são determinísticos (sem seed); só `mlp_relational` e `graph_mlp`
variam por seed.

**Anos:** mesma janela já estabelecida — `eval_years=[2019..2025]` para os baselines
(janela própria de 7 anos), comparável em `[2021..2025]` para os 4 modelos juntos
(restrição de `RIDGE_MIN_TRAIN_YEARS=4` sobre o histórico relacional/setorial, que só
começa em 2017/2013 respectivamente — ver HERALD_17 §10/§12).

## 5. Métricas e relation_signals

- **Métricas:** WMAPE (já usado em todo o bloco), MAE, RMSE — nenhuma métrica nova sem
  definição prévia.
- **`feature_signals`** (`train_fr_ze2020_neural_relational_mlp.py`): permutation
  importance por feature por `eval_year`, `claim_status=neural_relational_smoke`.
- **`relation_signals`** (`train_fr_ze2020_sector_graph_prototype.py`): top-20 por ano
  por tipo (`intra_ze_composition`, `cross_ze_same_sector`), `claim_status=sector_graph_smoke`.
- **Novo nesta etapa — estabilidade entre seeds (H3):** o script de auditoria
  (`hpc/france_ze2020/audit_fr_ze2020_hpc_results.py`, §7) calcula, depois da coleta:
  - desvio-padrão do WMAPE por modelo através das 5 seeds;
  - para `feature_signals`: desvio-padrão do `importance_score` por feature através
    das seeds;
  - para `relation_signals`: taxa de recorrência dos pares `(source_node, target_node)`
    do top-20 através das seeds (quantos dos top-20 de uma seed também aparecem no
    top-20 de outra) — uma medida descritiva de estabilidade, não um teste estatístico
    formal.

## 6. Gates de sucesso/falha (pré-registrados, seguindo o padrão de DEC-008/009/023/029/031)

Nenhum destes gates foi avaliado ainda — são pré-registrados aqui, antes da execução,
exatamente para evitar ajustar o critério depois de ver o resultado (mesma disciplina
já usada nas DECs fechadas deste projeto).

| Gate | Critério |
|---|---|
| G1 — Sem vazamento/erro | 0 `NaN`/`Inf` não-esperado nos CSVs de métricas; todas as 5 seeds completam sem erro |
| G2 — Estabilidade do WMAPE | Desvio-padrão do WMAPE de `mlp_relational`/`graph_mlp` através das 5 seeds < 20% da média (caso contrário, o resultado smoke de seed única não é representativo) |
| G3 — Sinal de melhoria (H1) | `mlp_relational` ou `graph_mlp` bate seu baseline correspondente (`ridge_relational`/`persistence_sector`) em pelo menos 3 das 5 seeds — **não atingido no smoke local** (nenhuma seed testada ainda venceu) |
| G4 — Estabilidade de relação exploratória (H3) | Pelo menos 50% dos pares do top-20 de `relation_signals` recorrem em pelo menos 3 das 5 seeds |
| G5 — Separação de saída (H4) | Nenhum CSV mistura `y_pred` com `signal_strength`/`importance_score` na mesma coluna; nenhuma coluna `recommendation` em nenhum output |

**G3 é o gate que decide se H1/H2 têm qualquer sustentação** — G1/G5 são sanidade
(já garantidos por código+teste local), G2/G4 são sobre estabilidade (H3), não sobre
"o modelo é bom". **Promover qualquer modelo a candidato de treino maior exige G1+G3
no mínimo — decisão humana, não automática.**

## 7. Orçamento esperado

- 5 tasks (1 por seed), array Slurm `0-4`.
- Cada task roda os 4 scripts sequencialmente: ~1 min (build do grafo setorial,
  custo dominante) + poucos segundos (MLP/Ridge/persistence) ≈ **2-3 min por task**.
- `--cpus-per-task=4`, `--mem=8G` (sem torch/tensores grandes — sklearn puro), `--time=00:30:00`
  (folga generosa sobre os ~3 min esperados).
- Partição/QOS: `fast`/`fast` (mesma usada por `phase10_synthetic_lagged`, carga leve).
- **Custo total estimado: <15 min de cluster, 5 tasks × 4 CPUs.** Não é uma bateria
  pesada — a única razão para usar o cluster em vez do laptop é paralelizar as 5 seeds
  e manter o ambiente remoto consistente com o resto do projeto.

## 8. Comandos

### Sync local → meso (sem apagar o remoto)

```bash
rsync -avz --exclude='*.pyc' --exclude='hpc_results/' --exclude='data/external/' \
    /home/jpdark/Downloads/project_recomm/dataset/ \
    meso:~/project_recomm_herald_v6_2025_20260430/dataset/
```

### Smoke remoto (1 config pequena, sem sbatch — mesmo padrão de phase10)

```bash
ssh meso "cd ~/project_recomm_herald_v6_2025_20260430/dataset && \
    bash hpc/france_ze2020/smoke_test_fr_ze2020_hpc.sh"
```

### Dry-run do submit (mostra o comando, não submete)

```bash
ssh meso "cd ~/project_recomm_herald_v6_2025_20260430/dataset && \
    bash hpc/france_ze2020/submit_fr_ze2020_hpc.sh"
```

### Submit real (só com confirmação humana explícita)

```bash
ssh meso "cd ~/project_recomm_herald_v6_2025_20260430/dataset && \
    bash hpc/france_ze2020/submit_fr_ze2020_hpc.sh --confirm-submit"
```

### Monitoramento

```bash
ssh meso "squeue -u \$USER"
```

### Coleta de resultados

```bash
rsync -avz \
    meso:~/project_recomm_herald_v6_2025_20260430/dataset/hpc_results/fr_ze2020_hpc_<RUN_ID>/ \
    hpc_results/fr_ze2020_hpc_<RUN_ID>/
```

### Auditoria pós-coleta (gates G1-G5, descritivo, decisão humana)

```bash
python3 hpc/france_ze2020/audit_fr_ze2020_hpc_results.py \
    hpc_results/fr_ze2020_hpc_<RUN_ID>/ \
    --out reports/metrics/fr_ze2020_hpc_<RUN_ID>_gate_report.json
```

## 9. Caveat (repetido deliberadamente)

- **Sem claim causal.** `relation_signals`/`feature_signals` são associação observada
  (correlação, peso de agregação, permutation importance) — nunca efeito.
- **Sem recomendação automática.** Nenhuma saída desta etapa contém ranking de
  investimento, política pública, ou qualquer coluna `recommendation`.
- **Sem claim final de performance.** G3 (sinal de melhoria) não foi atingido no smoke
  local com seed única; mesmo que seja atingido aqui com 5 seeds, isso autoriza
  **discussão de próximo passo**, não uma conclusão de que o modelo relacional/grafo
  "funciona" — Bloco 3 (recomendação) do Charter permanece fora de escopo.

---

## Cross-reference

- Plano de treino local: `reports/canonical/HERALD_18_FR_ZE2020_TRAINING_PLAN.md`
- Camada relacional: `reports/canonical/HERALD_17_FR_ZE2020_RELATIONAL_LAYER_PLAN.md`
- Infraestrutura HPC: `hpc/france_ze2020/README.md`
