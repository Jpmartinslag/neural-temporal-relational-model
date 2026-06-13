# HERALD — Pesquisa Arquitetural pós-DEC-045
**DEC-046 — RESEARCH_ONLY | Data: 2026-06-13**
**Pergunta central:** Como melhorar transferência grafal, adaptação a novos países, reconstrução OOD e explicabilidade auditável?

---

## 1. Diagnóstico DEC-045 — Causa-raiz da Falha

### 1.1 O que funcionou

| Componente | Resultado | Interpretação |
|-----------|-----------|---------------|
| Edge AUC em OOD (novel_lag2, novel_highvar) | **0,611** (vs 0,55 threshold) | A atenção de setor aprendida identifica pares conectados mesmo em cenários nunca vistos |
| Oracle wiring | AUC=1,000 | O mecanismo de atenção é estruturalmente correto |
| T2 vs T1 (multi-ambiente) | ratio=0,9959 | Treinar em mais cenários tem ganho marginal positivo |

### 1.2 O que falhou e por quê

**X5 FAIL — Imputação:** `herald_lagged ≥ no_graph` em 3/3 seeds. **Causa:** O MLP foi treinado em dinâmicas AR(1) com frac_nonlinear=0-30%. Para reconstruir valores em cenários 85-90% não-lineares, o MLP precisaria aplicar `w·tanh(x_source)`, mas aprendeu apenas `w·x_source`. A mensagem de atenção grafal chega corretamente ao neurônio de destino — mas o cabeçote MLP processa essa mensagem com uma função linear inadequada para a distribuição alvo. O MLP aprende apenas uma transformação linear (hipótese a verificar por ablação — DEC-047 §10).

**X9 FAIL — Oracle não bate ffill:** O oracle fixa a matriz de atenção nos pares verdadeiros, mas o MLP permanece treinado em domínio linear. Com dinâmicas 90% não-lineares + structural break no ano 8, o MLP produz previsões sistematicamente fora da escala real. Forward fill (cópia do último valor observado) domina porque a série tem alta autocorrelação de curto prazo — o MLP não supera uma cópia ingênua quando a distribuição se afastou radicalmente.

**X8 FAIL — Consistência de seeds:** O padrão acima é idêntico para todos os 3 seeds testados, confirmando que é estrutural, não ruído de seed.

### 1.3 Resumo estrutural

```
HERALD tem dois sub-problemas distintos com comportamentos distintos:

  [A] Identificação de estrutura (atenção)  → TRANSFERE (AUC=0,611 OOD)
  [B] Função de reconstrução (MLP)          → NÃO TRANSFERE sem adaptação
```

O MLP é um decoder treinado de forma supervisionada num domínio. Ele não é invariante à distribuição de dinâmicas. Esta separação é a chave para a proposta arquitetural correta.

---

> **ESTADO DE EVIDÊNCIA (DEC-045 → DEC-047)**
>
> | Componente | Estado | Evidência |
> |-----------|--------|-----------|
> | **Transferência da estrutura grafal** (atenção lag-1/lag-2) | **CONFIRMADO** | AUC=0.611 OOD (X6 PASS, gate X1-X9) |
> | **Reconstrução dos valores** (MLP decoder) | **FALHA** | X5/X9 FAIL — MLP não transfere; ffill domina em 3/3 seeds |
> | **Adaptação few-shot** (adapter + K% labels) | **NÃO AVALIADO** | A avaliar em DEC-047 (gates A1-A10) |
> | **Calibração de incerteza** (EnbPI/conformal) | **ADIADO** | Após escolha de estratégia de reconstrução |
>
> **Nota:** As relações no gerador sintético são "relações dirigidas implantadas no gerador sintético" — não constituem evidência de causalidade. Para dados observacionais, usar "associação dirigida/defasada" em vez de "efeito causal".

---

## 2. O que já foi testado e os seus limites

| Método | DEC | Resultado | Limitação identificada |
|--------|-----|-----------|----------------------|
| Imputação por MLP contemporânea (HERALDGraphImputer) | DEC-042 | AUC 0,39-0,43 — arquitecturalmente inadequado | B3: ignora lags 1 e 2 |
| Grafo geográfico (queen-contiguity) | DEC-010/011 | FAIL — não melhora previsão em FR/IT | Topologia territorial não é preditor forte |
| Neural graph-temporal (GConvGRU, EvolveGCN-H) | DEC-031 | S1_FR_FAIL — p_temporal=1,0, indistinguível de null | T muito curto; sem sinal suficiente para redes recorrentes grafais |
| P6 dual-graph (DDEG_S1) | DEC-029 | DUAL_GRAPH_S1_FAIL | Overfitting; nomes de setor inválidos |
| HERALDGraphImputerLagged (Phase 10) | DEC-043 | PHASE10_PARTIAL — AUC 0,64-0,71 mas MAE +1-2% | AR dominante; MLP não excede ffill por mais de 5% |
| Multi-ambiente T2 (Phase 11) | DEC-045 | Ganho marginal 0,41%; MLP não generaliza OOD | Gap de distribuição (0-30% NL → 85-90% NL) demasiado largo para T2 simples |

**Métodos já refutados sem hipótese nova (não retomar):**
- Geographic graph prediction (Phases 4P/4Q, DEC-010/011) — FECHADO
- P6 sector edge labels como explicação (DEC-029) — FECHADO
- GConvGRU / EvolveGCN-H preditivo (DEC-031) — FECHADO
- Neural imputador sem lag (Phase 9) — substituído por lagged

---

## 3. Arquitetura atual — Representação interna

```
HERALDGraphImputerLagged (n_S=9, n_T=30):
  Parâmetros treináveis:
    log_sect_attn_lag1 : (9,9)  — atenção source→target em lag-1
    log_sect_attn_lag2 : (9,9)  — atenção source→target em lag-2
    log_terr_attn      : (30,30) — atenção territorial contemporânea
    MLP                : 10→64→32→2 (mean, log_sigma)

  Inputs ao MLP (10 dims por célula (t,s,y)):
    7 temporais : [obs_t, mask_t, mean_obs, delta_t, ffill_val, trend_slope, age_since_obs]
    3 grafais   : [sector_nb_lag1, sector_nb_lag2, territory_nb]

  Loss : NLL gaussiana nas células observadas
  adj_s: adjacência simétrica binária somada aos log-attn (prior suave)
```

**Limitações estruturais identificadas:**
1. MLP com 10→64→32→2 é linear por seção — funciona bem se residuais são gaussianos, falha sob não-linearidades fortes
2. Normalização ausente — os valores brutos variam entre países e anos, amplificando distribuição shift
3. Atenção territorial é contemporânea — usa apenas vizinhos no mesmo ano, não capta propagação temporal
4. Função de perda (NLL gaussiana) assume resíduos normais — inadequada se erros têm caudas pesadas OOD
5. Treinamento por-dataset: cada (panel, mask) treina um modelo do zero — sem transferência de conhecimento inter-tarefa

---

## 4. Pesquisa bibliográfica — Métodos candidatos

*(Apenas fontes primárias verificadas; ver secção 10 para classificação completa)*

### 4.1 Eixo A — Imputação espaço-temporal grafal

**GRIN** (Cini, Marisca, Alippi — ICLR 2022) é o estado-da-arte em imputação por GNN. Usa GCRNN bidirecional (GRU sobre grafo por difusão). Trata explicitamente MCAR e block masking. Código oficial disponível. **Problema para HERALD:** desenhado para T>>200 (sensores, tráfego, qualidade de ar). Com T=20 e N=9 setores, o GCRNN bidirecional perde a maioria dos parâmetros ao aprendizado spurious. Uso directo: inadvisable. Uso do princípio de separação encoder/decoder grafal: sim.

**SAITS** (Du, Cote, Liu — Expert Systems with Applications 2023) usa Diagonal-Masked Self-Attention para imputação de séries temporais sem grafo explícito. Mais compatível com T pequeno. Não distingue lag-1 de lag-2. Referência para o cabeçote de imputação.

**CSDI** (Tashiro et al. — NeurIPS 2021) aplica score-based diffusion condicional. Alta capacidade, mas: (a) lento a inferência, (b) pouca interpretabilidade, (c) sem aprendizagem de estrutura grafal. **Para HERALD com T=20:** custo computacional injustificado, ganho de interpretabilidade negativo.

**PriSTI** (Liu et al. — arXiv 2302.09746 / ICDE 2023) combina diffusion com prior espaço-temporal. Mais próximo de HERALD (spatial + temporal), mas mesmos problemas de CSDI.

**GRAPE** (You et al. — NeurIPS 2020) trata imputação como link prediction em bipartite graph. Elegante mas sem lag explícito e sem atenção dirigida. Referência conceptual.

### 4.2 Eixo B — Domain adaptation / generalization para grafos

**GTrans** (Jin et al. — ICLR 2023) faz test-time graph transformation: aprende a modificar a topologia do grafo ao tempo de teste. Relevante para o problema de HERALD onde a topologia territorial muda entre países. Limitação: desenhado para mudança de topologia, não de dinâmicas do sinal.

**UDAGCN** (Wu et al. — WWW 2020) usa adversarial domain adaptation para GCN. Desenhado para classificação de nós, não para imputação temporal. Princípio aplicável (alinhamento de distribuição de representações), mas transferência directa não é viável.

**Task-Adaptive Few-Shot Node Classification** (Wang et al. — KDD 2022) — meta-learning para classificação de nós com poucos exemplos. Princípio: conjuntos de suporte de nós e protótipos por classe. Não directamente aplicável a imputação regressiva, mas informa o protocolo few-shot.

### 4.3 Eixo C — Neural Relational Inference + Graph Structure Learning

**NRI** (Kipf, Fetaya, Wang, Welling, Zemel — ICML 2018) aprende relações entre entidades via VAE: encoder infere grafo latente discreto, decoder gera trajetórias. **Relevante:** O problema HERALD é similar — queremos aprender relações sector→sector a partir de dinâmicas. **Problema:** NRI assume dinâmicas homogéneas (todas as entidades seguem o mesmo tipo de relação), T>>20, N>>9. Com T=20 e N=9 sectores, o encoder NRI não tem sinal suficiente para aprender relações fiáveis. Código disponível mas requer adaptação significativa.

**GTS** (Shang, Chen, Bi — ICLR 2021) aprende estrutura de grafo discreta para previsão de múltiplas séries temporais. Abordagem mais compatível com HERALD: o grafo é parâmetro aprendível, optimizado junto com a previsão. **Problema:** desenhado para previsão (horizon T), não imputação; sem distinção de lag; sem sinal de direcção.

**SLAPS** (Fatemi et al. — NeurIPS 2021) combina auto-supervisão com aprendizagem de estrutura. O grafo é aprendido para maximizar tanto performance preditiva como consistência auto-supervisionada. Relevante para o eixo de pretraining.

### 4.4 Eixo D — Auto-supervisão e masked pretraining

**GraphMAE** (Hou et al. — KDD 2022) — masked graph autoencoder: reconstrói features de nós mascarados usando GNN como decoder. O encoder aprende representações de nós sem supervisão de labels. **Aplicação a HERALD:** pré-treinar um encoder de setor que reconstrói valores mascarados do painel usando o grafo — exactamente o objectivo da Fase 9/10, mas com pretraining em múltiplos datasets antes de fine-tuning num país novo.

**PatchTST** (Nie et al. — ICLR 2023) trata séries temporais como sequências de patches e usa masked autoencoding. Sem grafo, mas princípio transferível: divisão em janelas, masking estrutural, reconstrução. Com T=20 os patches são poucos (2-4), limitando ganho.

**SimMTM** (Dong et al. — NeurIPS 2023 Spotlight) usa contrastive learning com reconstrução mascarada temporal. Vizinhos temporais como pares positivos. Sem grafo. Abordagem mais económica que diffusion.

### 4.5 Eixo E — Conformal prediction e incerteza

**EnbPI** (Xu & Xie — ICML 2021) — conformal intervals para séries temporais com distribuição em mudança. Usa ensemble + PI online. **Adequado para HERALD:** funciona sem troca de dados entre treino e teste, não assume troca de distribuição, fornece cobertura marginal válida para séries dependentes.

**SPCI** (Xu & Xie — ICML 2023) — extensão sequencial do EnbPI com quantile regression condicional. Melhor cobertura condicional. Requer séries temporais suficientemente longas para calibração (T≥30 recomendado, T=20 é marginal).

**Barber, Candès, Ramdas, Tibshirani — AoS 2023** (Conformal Prediction Beyond Exchangeability) — resultado teórico: intervalos conformais com garantias válidas sob distribuição shift se o shift é monitorizado e o tamanho da janela é adaptado. Relevante para aplicação cross-country.

**Angelopoulos & Bates — tutorial arXiv 2107.07511** — referência técnica para implementação. Não é método per se, mas guia formal de implementação.

---

## 5. Avaliação de transferibilidade por método candidato

| Método | Resolve DEC-045? | T≈10-20? | Multi-território/sector? | Mask explícita? | Grafo dirigido+lag? | Sem labels alvo? | Código utilizável? | Custo impl. | Risco overfit | Explicabilidade | Adequação HERALD |
|--------|-----------------|----------|--------------------------|-----------------|---------------------|------------------|--------------------|-------------|----------------|-----------------|------------------|
| Frozen attn + adapter MLP | **SIM** — resolve X5/X9 | **SIM** | SIM | SIM | SIM (herda) | Parcial (few-shot) | **SIM** (HERALD codebase) | Baixo | Baixo-médio | Alta | **MÁXIMA** |
| GRIN completo | Parcial | NÃO (T>>200) | SIM | SIM | Não (undirected) | NÃO | SIM | Alto | Alto | Média | Baixa |
| SAITS | Parcial | SIM | Sem grafo | SIM | NÃO | NÃO | SIM | Médio | Médio | Média | Média |
| CSDI/PriSTI | Parcial (imputação) | NÃO | SIM | SIM | NÃO | NÃO | SIM | **Muito alto** | Baixo | **Baixa** | Baixa |
| GTrans | Não (topologia, não dinâmica) | SIM | SIM | NÃO | Parcial | NÃO | SIM | Médio | Médio | Média | Baixa |
| NRI | Parcial (estrutura) | NÃO (T>>50) | SIM | Parcial | SIM | NÃO | SIM | Alto | **Alto** | Média | Baixa |
| GTS | Parcial (previsão) | NÃO (T>>50) | SIM | NÃO | NÃO | NÃO | Parcial | Alto | Alto | Média | Baixa |
| GraphMAE pretraining | SIM (pretraining) | **SIM** | SIM | SIM | Herda grafo | **SIM** | SIM | Médio | Baixo | Alta | Alta |
| SimMTM | Parcial | **SIM** | Sem grafo | SIM | NÃO | **SIM** | SIM | Médio | Baixo | Média | Média |
| MAML/Reptile | Parcial (few-shot) | SIM | SIM | Parcial | NÃO (genérico) | Parcial | SIM | Médio | Médio | Baixa | Baixa-média |
| EnbPI/SPCI | Não (apenas UQ) | Marginal (T≥30 ideal) | SIM | NÃO | NÃO | SIM | SIM | Baixo | N/A | Alta | Complementar |
| MoE por país | Parcial | SIM | SIM | SIM | Herda | NÃO | HERALD | Médio | Médio | Alta | Média-alta |

---

## 6. Avaliação da proposta "direction preferential" (Secção 6 do briefing)

A proposta é:
1. Encoder temporal-grafal pré-treinado com tarefas auto-supervisionadas
2. Atenção/relações grafais congeladas inicialmente
3. Adapters ou decoder pequeno adaptado ao novo país
4. Treinamento com poucos labels conhecidos
5. Reconstrução mascarada + edge prediction + lag/sign prediction
6. Saída com abstention e intervalos conformais

**É metodologicamente defensável? Sim.** É mais forte que apenas fine-tuning do MLP por três razões:

| Comparação | Fine-tuning completo | Frozen attention + adapter |
|-----------|---------------------|---------------------------|
| Preserva estrutura transferida (AUC=0,611) | Pode destruir | **Preserva** |
| Eficiência com poucos labels | Overfit com < 5% | **Melhor com 1-5%** |
| Gradient flow para atenção | Necessário (destabiliza) | **Bloqueado (estável)** |
| Custo de implementação | Baixo | Médio (adiciona adapters) |
| Interpretabilidade | Moderada | **Alta** (atenção auditável) |
| Risco de esquecimento catastrófico | Alto | **Baixo** |

**É melhor que fine-tuning puro do MLP?** Sim, quando:
- Poucas labels do país alvo (< 20% do dataset)
- O gap de distribuição é grande mas a estrutura grafal é similar
- É importante auditar quais relações sector→sector são usadas

**Caveat:** Se o novo país tem uma estrutura grafal radicalmente diferente (ex. sectores dominantes distintos), congelar a atenção pode prejudicar. Solução: protocolo em dois andamentos — primeiro verificar se AUC do atenção congelada é > 0,5 no novo país; só então adaptar o decoder.

---

## 7. Os três caminhos recomendados

### PATH 1 — `RECOMMENDED_NOW`: Pretrain mascarado + Frozen attention + Adapter MLP (few-shot)

**Motivação directa de DEC-045:** O componente [A] (atenção) transfere (AUC=0,611); o componente [B] (MLP) não transfere. Separar e adaptar [B] com poucos labels é a intervenção cirúrgica correcta.

**Arquitectura:**
```
Fase 1 — Pretraining (sem labels do país alvo):
  Dados: múltiplos cenários sintéticos ou países com dados disponíveis
  Tarefa A (reconstrução mascarada): reconstruir células mascaradas aleatoriamente
  Tarefa B (edge prediction): dado o painel, prever se par (s_i, s_j) tem relação → AUC
  Tarefa C (lag prediction): dado o sinal de cruzamento, classificar lag como 1 ou 2
  Loss: λ_A · L_reconstruction + λ_B · L_edge + λ_C · L_lag

Fase 2 — Frozen attention + adapter MLP (com K% labels do país alvo):
  log_sect_attn_lag1, log_sect_attn_lag2, log_terr_attn → FROZEN
  MLP original → FROZEN
  Adapter: MLP_adapter = Linear(32→16→32) inserido antes da camada final (bottleneck)
  Treino: apenas adapter + cabeçote final com K% labels
  K ∈ {1%, 5%, 10%, 20%} dos anos × territórios × setores do país alvo

Avaliação:
  Test: células mascaradas restantes (80-99%)
  Comparação: zero-shot vs decoder-only vs full fine-tuning vs adapter
```

**Função de perda de adaptação:** MSE nas células observadas do país alvo (K% disponíveis)

**Dados necessários:** Dados do país alvo com T≥8 anos e pelo menos 1 setor completo para calibração.

**Protocolo train/val/test:** train=early years alvo (K% dos anos), val=anos intermédios, test=anos finais (never seen). Atenção: não usar dados de teste para seleccionar K ou lr.

**Controles negativos:**
1. Random-adapter: adapter com pesos aleatórios (não treinado) — deve ser pior
2. Full fine-tune sem freeze: adapter + MLP treinados (testa se freeze ajuda)
3. No-graph adapter: adapter com adj_s=0 (testa se grafo congelado contribui)
4. Ridge com os mesmos K% labels

**Métricas:**
- MAE / RMSE nas células escondidas
- Edge AUC (atenção congelada vs atenção liberada)
- Cobertura conformal (EnbPI) nos 90% intervalos
- Sign accuracy (reconstrução de tendência)

**Critérios fail-closed:**
- Se adapter-MAE ≥ Ridge-MAE com K=10%: ADAPTER_NOT_USEFUL — adoptar apenas Ridge + atenção para auditoria
- Se AUC atenção congelada < 0,5 no novo país: STRUCTURE_INCOMPATIBLE — repensar antes de congelar
- Se cobertura conformal < 80% nos 90% intervalos: UNCERTAINTY_UNCALIBRATED

**Custo estimado:** Baixo. Reutiliza HERALDGraphImputerLagged. O adapter tem ~500-1000 parâmetros. Pilot local < 30 min.

**Plano incremental:**
1. DEC-047: definir split few-shot nos cenários sintéticos existentes
2. Implementar adapter como módulo opcional (parâmetro `use_adapter=True`)
3. Pilot local: novel_lag2, seeds [1000, 2000, 3000], K ∈ {1%, 5%, 10%, 20%}
4. Avaliar X1-X5 gates equivalentes (adaptar nomenclatura)
5. Se pilot PASS: estender ao real data (PT alvo, treino FR+NL)

**Hipótese falsificável:** "Com K=5% labels do domínio alvo e atenção congelada, o adapter MLP atinge MAE < no_graph e < Ridge nos cenários novel_lag2 e novel_highvar, para todas as masks (MCAR e block)."

---

### PATH 2 — `SECONDARY`: Masked pretraining com tarefa de reconstrução + edge/lag prediction auto-supervisionado

**Motivação:** O pretraining da Fase 1 do PATH 1 pode ser explorado de forma mais aprofundada antes de qualquer fine-tuning. Especificamente, treinar com tarefas múltiplas de auto-supervisão em muitos datasets sintéticos (centenas de seeds × cenários) pode levar a um encoder mais robusto do que o treinado por NLL single-dataset.

**Diferença do PATH 1:** PATH 2 foca-se em maximizar a qualidade do pretraining antes de qualquer adaptação. O resultado é um modelo "foundation-light" para o domínio económico territorial com T curto.

**Arquitectura:**
```
Encoder grafal (atenção lag-1/lag-2 + território):
  Parâmetros compartilhados entre tarefas
  Input: (panel_mascarado, mask, adj_s, adj_t)
  Output: representação de cada célula (T, S, Y) de 32 dims

Decoder A (reconstrução mascarada):
  Linear(32 → 1) — reconstrói valor mascarado
  Loss: MSE nas células mascaradas (proporção = 50%, aleatória)

Decoder B (edge prediction):
  MLP(64 → 1) sobre par de representações de setor — binária (existe relação?)
  Loss: BCE com balanceamento positivo/negativo
  Target: true_relations do gerador

Decoder C (lag prediction):
  MLP(32 → 2) sobre representação do setor source — classifica lag 1 vs 2
  Loss: CE apenas para relações verdadeiras

Decoder D (sign prediction):  
  MLP(32 → 1) sobre representação da relação — classifica positivo vs negativo
  Loss: BCE

Datasets de pretraining: 200-500 seeds × 4 cenários = 800-2000 mini-datasets
  incluindo cenários com frac_nonlinear até 0,9 (cobrindo distribuição alvo)
```

**Chave:** incluir cenários com frac_nonlinear até 0,9 no pretraining — ao contrário da Fase 10 e 11 onde o treino era restrito a 0-30%. Isso endereça directamente o gap de distribuição da DEC-045.

**Hipótese falsificável:** "Um encoder pré-treinado com reconstrução mascarada em 2000 mini-datasets (incluindo frac_nonlinear=0-0,9) atinge edge AUC ≥ 0,65 e MAE < no_graph em novel_lag2 sem qualquer fine-tuning (zero-shot), superior ao modelo treinado da DEC-045 (AUC=0,611, MAE > no_graph)."

**Custo estimado:** Médio. Pilot local possível (200 seeds × 150 epochs ≈ 20-40 min). HPC necessário para 2000 seeds.

**Plano incremental:**
1. Estender o gerador para amostrar frac_nonlinear ∈ U[0, 0,9] (não apenas cenários fixos)
2. Implementar multi-task training loop (adaptar trainer.py da Phase 11)
3. Pilot com 50 seeds × 3 tarefas × 100 epochs ≈ 15 min
4. Comparar AUC zero-shot vs PATH 1 zero-shot baseline

---

### PATH 3 — `FUTURE_ONLY`: Graph Structure Learning end-to-end com sinal dirigido/defasado

**Motivação:** NRI (Kipf et al. 2018) e GTS (Shang et al. 2021) aprendem a estrutura do grafo conjuntamente com as dinâmicas. Se HERALD tivesse T>>50 e N>>20 setores, esta abordagem seria preferível ao pretraining + frozen attention porque eliminaria a necessidade de adj_s como input.

**Por que FUTURE_ONLY:**
- T curto (T=20) aumenta risco de sobreajuste nas matrizes de adjacência aprendidas; requer validação com T≥25 antes de adoção (não é um requisito universal de T>50, mas sim uma cautela específica para HERALD com N=9)
- N=9 setores cria apenas 72 pares (off-diagonal) — o espaço de busca é tratável, mas o sinal é escasso
- Com 3-4 países no HERALD actual, a meta-tarefa tem demasiado poucas amostras
- O risco de sobreajuste à estrutura do dataset de treino é elevado sem regularização muito forte

**Condição de reabertura:** N_countries ≥ 8, T ≥ 25, e pretraining de PATH 2 testado e validado primeiro. Validação com T≥25 obrigatória antes de adopção. Reabrir como DEC-048 quando estas condições forem satisfeitas.

**Referências base:** NRI (Kipf 2018, ICML), GTS (Shang 2021, ICLR), SLAPS (Fatemi 2021, NeurIPS).

---

## 8. Métodos avaliados e classificados

| Método | Classificação | Razão |
|--------|--------------|-------|
| Frozen attn + adapter MLP (few-shot) | `RECOMMENDED_NOW` | Intervenção cirúrgica directa para DEC-045 |
| Masked pretraining multi-task | `SECONDARY` | Melhora pretraining antes de adaptação; mais custo |
| Graph structure learning (NRI/GTS) | `FUTURE_ONLY` | T curto (T=20) aumenta risco de sobreajuste nas matrizes de adjacência; requer validação com T≥25 antes de adoção |
| GRIN completo | `SECONDARY_BASELINE` | T>>200 ideal mas pode servir como baseline de comparação; implementação adiada para após resultado few-shot |
| CSDI / PriSTI (diffusion) | `REJECT` | Custo injustificado, baixa interpretabilidade, sem grafo dirigido+lag |
| GTrans test-time | `REJECT` | Resolve shift de topologia, não shift de dinâmicas |
| UDAGCN adversarial | `REJECT` | Classificação de nós; não imputação temporal |
| MAML/Reptile meta-learning | `REJECT` | Precisa muitas meta-tasks; 3-4 países é insuficiente |
| Mixture-of-Experts por país | `SECONDARY` | Interessante mas mais complexo que adapter; implementar depois de PATH 1 |
| EnbPI / SPCI conformal | Complementar a PATH 1 | UQ válida; T=20 é marginal para calibração; adicionar como camada |
| SAITS (sem grafo) | `SECONDARY_BASELINE` | Pode servir como baseline de referência sem grafo; implementação adiada para após resultado few-shot |

---

## 9. Experimento mínimo recomendado (não executar nesta tarefa)

**DEC-047 (proposta):** Few-shot adapter evaluation — comparação zero-shot vs decoder-only vs full fine-tuning

**Setup:**
- Sintético, cenários novel_lag2 e novel_highvar
- 3 seeds de treino few-shot: [1000, 2000, 3000]
- K ∈ {1%, 5%, 10%, 20%} de labels disponíveis do cenário alvo
- 5 condições:
  1. Zero-shot (DEC-045 baseline) — sem adaptação
  2. Decoder-only adapter (frozen attention, adapter MLP treinado em K labels)
  3. Full fine-tuning (toda a rede treinada em K labels)
  4. no_graph baseline (MAE sem grafo, K labels)
  5. Ridge com K% labels como baseline interpretável
- Masks: MCAR-30 e block-30
- Épocas de adaptação: 50 (adapter-only) e 150 (full fine-tune)
- Avaliação: MAE e RMSE nos 80-99% ocultos, edge AUC da atenção, cobertura conformal (EnbPI simples)

**Métricas de sucesso (gates pré-definidos antes da execução):**
- A1: adapter-MAE < zero-shot-MAE para K=5% em novel_lag2 (intervenção útil)
- A2: adapter-MAE < full-finetune-MAE para K=1% (eficiência com poucos labels)
- A3: frozen-AUC ≥ zero-shot-AUC (frozen não destrói estrutura)
- A4: Ridge < adapter para K=1% (se sim → não há sinal suficiente nos 1% labels)
- A5: cobertura conformal 90% ≥ 80% (intervalos válidos)

**O que o experimento pode revelar:**
- Se A1 PASS: PATH 1 é viável — proceder com DEC-047
- Se A1 FAIL: O problema é mais profundo — tentar PATH 2 primeiro
- Se A2 PASS: Adapter é superior a full fine-tuning para poucos labels — confirma hipótese
- Se A4 PASS para todos os K: Ridge domina sempre — o modelo neural não é útil em modo few-shot

**Custo estimado:** < 30 min localmente. Sem HPC.

---

## 10. Referências verificadas (novas para esta pesquisa)

*(Referências anteriores R-001 a R-025 permanecem válidas; ver HERALD_REFERENCES_MASTER.md)*

| Ref | Autores | Título | Venue | Ano | DOI / URL | Código | Status |
|-----|---------|--------|-------|-----|-----------|--------|--------|
| R-026 | Cini, Marisca, Alippi | Filling the G_ap_s: Multivariate Time Series Imputation by GNNs (GRIN) | ICLR 2022 | 2022 | openreview.net/forum?id=kOu3-S3wJ7 | [github.com/Graph-Machine-Learning-Group/grin](https://github.com/Graph-Machine-Learning-Group/grin) | `VERIFIED_PRIMARY` |
| R-027 | Du, Cote, Liu | SAITS: Self-Attention-based Imputation for Time Series | Expert Systems with Applications | 2023 | arxiv.org/abs/2202.08516 | [github.com/WenjieDu/SAITS](https://github.com/WenjieDu/SAITS) | `VERIFIED_PRIMARY` |
| R-028 | Tashiro, Song, Song, Ermon | CSDI: Conditional Score-based Diffusion Models for Probabilistic Time Series Imputation | NeurIPS 2021 | 2021 | proceedings.neurips.cc/paper/2021/hash/cfe8504bda37b575c70ee1a8276f3486 | [github.com/ermongroup/CSDI](https://github.com/ermongroup/CSDI) | `VERIFIED_PRIMARY` |
| R-029 | Liu et al. | PriSTI: A Conditional Diffusion Framework for Spatiotemporal Imputation | ICDE 2023 / arXiv | 2023 | arxiv.org/abs/2302.09746 | não confirmado | `PREPRINT` |
| R-030 | You, Ma, Ding, Kochenderfer, Leskovec | Handling Missing Data with Graph Representation Learning (GRAPE) | NeurIPS 2020 | 2020 | proceedings.neurips.cc/paper/2020/hash/dc36f18a9a0a776671d4879cae69b551 | github (ver paper) | `VERIFIED_PRIMARY` |
| R-031 | Wu, Pan, Zhou, Chang, Zhu | Unsupervised Domain Adaptive Graph Convolutional Networks (UDAGCN) | WWW 2020 | 2020 | dl.acm.org/doi/10.1145/3366423.3380219 | [github.com/TrustAGI-Lab/UDAGCN](https://github.com/TrustAGI-Lab/UDAGCN) | `VERIFIED_PRIMARY` |
| R-032 | Jin, Zhao, Ding, Liu, Tang, Shah | Empowering Graph Representation Learning with Test-Time Graph Transformation (GTrans) | ICLR 2023 | 2023 | openreview.net/forum?id=Lnxl5pr018 | [github.com/ChandlerBang/GTrans](https://github.com/ChandlerBang/GTrans) | `VERIFIED_PRIMARY` |
| R-033 | Kipf, Fetaya, Wang, Welling, Zemel | Neural Relational Inference for Interacting Systems (NRI) | ICML 2018 | 2018 | proceedings.mlr.press/v80/kipf18a | [github.com/ethanfetaya/NRI](https://github.com/ethanfetaya/NRI) | `VERIFIED_PRIMARY` |
| R-034 | Shang, Chen, Bi | Discrete Graph Structure Learning for Forecasting Multiple Time Series (GTS) | ICLR 2021 | 2021 | openreview.net/forum?id=WEHSlH5mOk | não confirmado | `VERIFIED_PRIMARY` |
| R-035 | Fatemi, El Asri, Kazemi | SLAPS: Self-Supervision Improves Structure Learning for Graph Neural Networks | NeurIPS 2021 | 2021 | proceedings.neurips.cc/paper/2021/file/bf499a12e998d178afd964adf64a60cb | não confirmado | `VERIFIED_PRIMARY` |
| R-036 | Hou, Liu, Cen, Dong, Yang, Wang, Tang | GraphMAE: Self-Supervised Masked Graph Autoencoders | KDD 2022 | 2022 | dl.acm.org/doi/abs/10.1145/3534678.3539321 | [github.com/THUDM/GraphMAE](https://github.com/THUDM/GraphMAE) | `VERIFIED_PRIMARY` |
| R-037 | Nie, Nguyen, Sinthong, Kalagnanam | A Time Series is Worth 64 Words: Long-term Forecasting with Transformers (PatchTST) | ICLR 2023 | 2023 | arxiv.org/abs/2211.14730 | [github.com/yuqinie98/PatchTST](https://github.com/yuqinie98/PatchTST) | `VERIFIED_PRIMARY` |
| R-038 | Dong, Wu, Zhang, Zhang, Wang, Long | SimMTM: A Simple Pre-Training Framework for Masked Time-Series Modeling | NeurIPS 2023 Spotlight | 2023 | proceedings.neurips.cc/paper_files/paper/2023/hash/5f9bfdfe3685e4ccdbc0e7fb29cccf2a | [github.com/thuml/SimMTM](https://github.com/thuml/SimMTM) | `VERIFIED_PRIMARY` |
| R-039 | Xu, Xie | Conformal Prediction Interval for Dynamic Time-Series (EnbPI) | ICML 2021 | 2021 | proceedings.mlr.press/v139/xu21h | [github.com/hamrel-cxu/EnbPI](https://github.com/hamrel-cxu/EnbPI) | `VERIFIED_PRIMARY` |
| R-040 | Xu, Xie | Sequential Predictive Conformal Inference for Time Series (SPCI) | ICML 2023 | 2023 | proceedings.mlr.press/v202/xu23r | [github.com/hamrel-cxu/SPCI-code](https://github.com/hamrel-cxu/SPCI-code) | `VERIFIED_PRIMARY` |
| R-041 | Barber, Candès, Ramdas, Tibshirani | Conformal Prediction Beyond Exchangeability | Annals of Statistics 51(2) | 2023 | doi:10.1214/23-AOS2276 | não confirmado | `VERIFIED_PRIMARY` |
| R-042 | Angelopoulos, Bates | A Gentle Introduction to Conformal Prediction and Distribution-Free UQ | arXiv tutorial | 2023 | arxiv.org/abs/2107.07511 | notebooks incluídos | `PREPRINT` |

---

## 11. Lacunas bibliográficas identificadas

1. **Relações grafais dirigidas+assinadas+defasadas para dados económicos curtos (T=10-20):** Não foi encontrado, nas referências revisadas, método que combine simultaneamente (a) direcção, (b) sinal positivo/negativo, (c) lag específico, e (d) T curto. NRI e GTS são os mais próximos mas não satisfazem T curto. Esta é uma **contribuição original possível do HERALD**.

2. **Adaptação de domínio para imputação temporal territorial:** A maioria dos métodos de domain adaptation é para classificação de nós. Adaptação para imputação de séries económicas NUTS3 com T curto não tem referência directa.

3. **Intervalos conformais para grafos com máscaras estruturais (block missing):** EnbPI e SPCI assumem observações sequenciais sem gaps estruturais. Block missing + conformal é uma combinação não coberta na literatura principal revisada.

---

## 12. Riscos e limites da proposta

| Risco | Probabilidade | Impacto | Mitigação |
|-------|--------------|---------|-----------|
| Adapter overfita com K=1% | Alta | Médio | Regularização L2 forte; early stopping rigoroso; Ridge como fallback |
| AUC atenção congelada < 0,5 no novo país | Média | Alto | Protocolo de verificação antes de congelar: se AUC < 0,5 → fine-tune atenção |
| Pretraining não cobre distribuição do país real | Média | Alto | Incluir cenários sintéticos com alta não-linearidade; usar dados reais de treino quando disponíveis |
| Conformal com T=20 produz intervalos muito largos | Alta | Baixo | Documentar como limitação; não apresentar como intervalos apertados |
| Interpretação errada da atenção congelada como "causalidade" | Média | **Muito alto** | Protocolo de linguagem: "relações dirigidas implantadas no gerador sintético" (sintético); "associações dirigidas/defasadas" (real); nunca "causalidade" nem "efeito causal" — usar "associação dirigida" ou "efeito observacional" |

---

## 13. Recomendação principal — Síntese

**Implementar PATH 1 como próximo experimento (DEC-047).**

A evidência da DEC-045 é clara: a separação entre identificação estrutural (transferível) e função de reconstrução (não transferível sem adaptação) é o diagnóstico central. A intervenção mínima válida é congelar o que transfere e adaptar o que não transfere com poucos labels.

**Arquitectura proposta em linguagem simples:**
> "Depois de treinar a atenção sector→sector num conjunto de dados suficientemente diverso, congelar essa atenção. Quando chega um novo país ou cenário, treinar apenas um 'adaptador' pequeno (bottleneck de 32→16→32 neurónios) inserido no decoder MLP, usando 5-10% das observações disponíveis do novo país. O resto da rede permanece fixo. A atenção continua auditável: os pares sector→sector com maior atenção são os que o modelo julga mais relevantes para a imputation. Adicionar intervalos conformais (EnbPI) como camada de saída para quantificar a incerteza de forma válida mesmo sob mudança de distribuição."

**O que esta proposta NÃO resolve:**
- Gap de distribuição extremo sem nenhum label do país alvo (K=0%) — zero-shot falha
- Países com topologia territorial radicalmente diferente (territórios desconexos, ilhas)
- Séries com T < 8 anos — adaptação inviável
- Causalidade económica — nenhuma arquitectura nesta proposta estabelece causalidade

**Ficheiros a criar em DEC-047 (futuro):**
- `src/modeles/synthetic/phase12_few_shot/adapter.py` — módulo de adapter
- `src/modeles/synthetic/phase12_few_shot/run_pilot.py` — pilot few-shot
- `src/modeles/synthetic/phase12_few_shot/gates_phase12.py` — gates A1-A5
- `tests/test_phase12_few_shot.py`
- `reports/HERALD_PHASE12_FEW_SHOT_ADAPTER.md`
