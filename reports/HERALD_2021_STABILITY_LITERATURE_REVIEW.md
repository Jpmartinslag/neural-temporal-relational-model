# HERALD 2021 Stability Literature Review

## 1. Resumo executivo

O problema de instabilidade por seed no fold 2021 é compatível com **alta variância de otimização + baixa razão sinal/ruído em T≈14**. A literatura sugere que, para painel anual curto, a melhor estratégia não é aumentar complexidade do regime latente, e sim combinar: **(i)** regime switching parcimonioso e interpretável, **(ii)** detecção causal de ruptura sem vazamento, **(iii)** objetivos robustos focados em pior ano/grupo, **(iv)** estabilização por ensemble leve/SWA e regularização anti-colapso.

Veredito global: para HERALD, priorizar métodos simples e auditáveis (Markov/switching state-space pequeno, PELT/BOCPD causal no treino do fold, Group DRO por ano/região, SWA/deep ensemble curto). Métodos muito flexíveis (MoE grande, contrastivo pesado, IRM puro) devem ser apenas teste secundário.

## 2. Diagnóstico do problema HERALD 2021

- **Sintoma:** sem flags manuais o modelo melhora métrica agregada, mas 2021 colapsa em algumas seeds.
- **Hipótese principal:** 2021 é um regime raro/outlier no espaço temporal recente; com T curto, o otimizador aprende partições latentes instáveis entre seeds.
- **Falha provável de desenho:** objetivo privilegia média global (WMAPE total), subponderando pior-fold/ano crítico.
- **Risco metodológico central:** tentar “resolver” com arquitetura maior tende a aumentar overfitting em painel anual curto.

## 3. Métodos encontrados (crítico e aplicado ao HERALD)

### 3.1 Regime switching models

#### 3.1.1 Markov Switching (Hamilton, 1989)
- **Referência:** Hamilton, J. D. (1989), *Econometrica*. DOI: https://doi.org/10.2307/1912559
- **Status:** **Revisado por pares**
- **Ideia central:** série alterna entre poucos regimes com transições Markovianas.
- **Aplicação no HERALD:** usar 2 regimes latentes (normal vs ruptura) como gate para residual neural.
- **Risco de overfitting:** **baixo-médio** (se número de regimes pequeno).
- **Interpretabilidade:** **alta** (probabilidades de regime e matriz de transição).
- **Custo computacional:** **baixo**.
- **Faz sentido com T=14?:** **sim**, como núcleo parcimonioso.
- **Veredito:** **usar agora**.

#### 3.1.2 Switching State-Space (Kim, 1994; Ghahramani & Hinton, 2000)
- **Referências:**
  1) Kim, C.-J. (1994), *Journal of Econometrics*. DOI: https://doi.org/10.1016/0304-4076(94)90036-1
  2) Ghahramani, Z.; Hinton, G. (2000), *Neural Computation*. DOI: https://doi.org/10.1162/089976600300015826
- **Status:** **Revisado por pares**
- **Ideia central:** dinâmica contínua + estado discreto de regime.
- **Aplicação no HERALD:** tendência regional + choque setorial em estado latente discreto compartilhado por clusters territoriais.
- **Risco de overfitting:** **médio** (subir rápido se estado contínuo for grande).
- **Interpretabilidade:** **média-alta** (regime + dinâmica local).
- **Custo computacional:** **médio**.
- **Faz sentido com T=14?:** **sim**, com baixa dimensão e forte regularização.
- **Veredito:** **usar agora** (versão pequena).

#### 3.1.3 Recurrent SLDS (Linderman et al., 2017)
- **Referência:** Linderman, S. et al. (2017), *AISTATS*. https://proceedings.mlr.press/v54/linderman17a.html
- **Status:** **Revisado por pares** (com versão arXiv)
- **Ideia central:** probabilidade de transição de regime depende do estado contínuo.
- **Aplicação no HERALD:** gate de transição condicionado por embedding territorial/setorial.
- **Risco de overfitting:** **alto** em T curto.
- **Interpretabilidade:** **média**.
- **Custo computacional:** **médio-alto**.
- **Faz sentido com T=14?:** **fraco** sem pré-treino externo.
- **Veredito:** **testar depois**.

### 3.2 Change-point detection causal (sem vazamento)

#### 3.2.1 PELT (Killick et al., 2012)
- **Referência:** Killick, R.; Fearnhead, P.; Eckley, I. (2012), *JASA*. DOI: https://doi.org/10.1080/01621459.2012.737745
- **Status:** **Revisado por pares**
- **Ideia central:** detecção offline ótima com penalização.
- **Aplicação no HERALD:** detectar quebras no bloco de treino de cada fold e gerar feature “distância ao último change-point”.
- **Risco de overfitting:** **médio** (se penalização frouxa).
- **Interpretabilidade:** **alta**.
- **Custo computacional:** **baixo**.
- **Faz sentido com T=14?:** **sim**, restringindo a no máximo 1–2 quebras por unidade.
- **Veredito:** **usar agora**.

#### 3.2.2 BOCPD (Adams & MacKay, 2007)
- **Referência:** Adams, R.; MacKay, D. (2007), arXiv: https://arxiv.org/abs/0710.3742
- **Status:** **Preprint**
- **Ideia central:** detecção online Bayesiana por run-length.
- **Aplicação no HERALD:** probabilidade de ruptura no ano t como entrada causal do gate de regime.
- **Risco de overfitting:** **médio** (depende do prior/hazard).
- **Interpretabilidade:** **alta**.
- **Custo computacional:** **baixo-médio**.
- **Faz sentido com T=14?:** **sim**, desde que truncado e com prior simples.
- **Veredito:** **usar agora** (piloto).

#### 3.2.3 CUSUM (Page, 1954)
- **Referência:** Page, E. S. (1954), *Biometrika*. DOI: https://doi.org/10.1093/biomet/41.1-2.100
- **Status:** **Revisado por pares**
- **Ideia central:** monitoramento sequencial de mudança.
- **Aplicação no HERALD:** sinal de drift em resíduos do Ridge AR por região.
- **Risco de overfitting:** **baixo**.
- **Interpretabilidade:** **alta**.
- **Custo computacional:** **baixo**.
- **Faz sentido com T=14?:** **sim**.
- **Veredito:** **usar agora**.

#### 3.2.4 Ferramental prático `ruptures`
- **Referências:**
  1) Truong, C.; Oudre, L.; Vayatis, N. (2020), *Signal Processing*. DOI: https://doi.org/10.1016/j.sigpro.2019.107299 (**revisado**)
  2) Truong, C. et al. (2018), arXiv: https://arxiv.org/abs/1801.00826 (**preprint/software**)
- **Ideia central:** biblioteca padronizada para PELT/Binseg/Window.
- **Aplicação no HERALD:** padronizar auditoria de quebras por fold e evitar implementação ad hoc.
- **Risco de overfitting:** **baixo** (risco vem do tuning, não da ferramenta).
- **Interpretabilidade:** **alta**.
- **Custo computacional:** **baixo**.
- **Faz sentido com T=14?:** **sim**.
- **Veredito:** **usar agora**.

### 3.3 Estabilização de representações latentes

#### 3.3.1 Mean Teacher consistency (Tarvainen & Valpola, 2017)
- **Referência:** Tarvainen, A.; Valpola, H. (2017), *NeurIPS*. https://arxiv.org/abs/1703.01780
- **Status:** **Revisado por pares**
- **Ideia central:** consistência student-teacher (EMA) reduz variância do treino.
- **Aplicação no HERALD:** penalizar divergência de latente/regime entre rede online e EMA.
- **Risco de overfitting:** **baixo-médio**.
- **Interpretabilidade:** **média**.
- **Custo computacional:** **médio**.
- **Faz sentido com T=14?:** **sim**, se arquitetura pequena.
- **Veredito:** **usar agora**.

#### 3.3.2 Anti-collapse explícito (VICReg, Bardes et al., 2022)
- **Referência:** Bardes, A.; Ponce, J.; LeCun, Y. (2022), *ICLR*. https://arxiv.org/abs/2105.04906
- **Status:** **Revisado por pares**
- **Ideia central:** termos de variância/covariância para evitar colapso de representação.
- **Aplicação no HERALD:** aplicar nos embeddings de regime/setor para evitar que todas seeds convirjam para um único código degenerado.
- **Risco de overfitting:** **médio** (se peso da regularização for mal calibrado).
- **Interpretabilidade:** **média**.
- **Custo computacional:** **médio**.
- **Faz sentido com T=14?:** **sim**, com baixa dimensão latente.
- **Veredito:** **usar agora**.

#### 3.3.3 Smooth latent trajectories (SFA, Wiskott & Sejnowski, 2002)
- **Referência:** Wiskott, L.; Sejnowski, T. (2002), *Neural Computation*. DOI: https://doi.org/10.1162/089976602317318938
- **Status:** **Revisado por pares**
- **Ideia central:** aprender fatores que evoluem lentamente no tempo.
- **Aplicação no HERALD:** penalidade de variação temporal do regime latente (exceto em anos com alta probabilidade de ruptura).
- **Risco de overfitting:** **baixo**.
- **Interpretabilidade:** **média-alta**.
- **Custo computacional:** **baixo**.
- **Faz sentido com T=14?:** **sim**.
- **Veredito:** **usar agora**.

#### 3.3.4 Contrastive temporal pesado (CPC; TS2Vec)
- **Referências:**
  1) van den Oord, A.; Li, Y.; Vinyals, O. (2018), arXiv: https://arxiv.org/abs/1807.03748 (**preprint**)
  2) Yue, Z. et al. (2022), *AAAI*, https://arxiv.org/abs/2106.10466 (**revisado**)
- **Ideia central:** tarefas contrastivas para dinâmica temporal.
- **Aplicação no HERALD:** possível pré-treino multirregional, depois fine-tune leve.
- **Risco de overfitting:** **alto** em T=14 sem dados externos.
- **Interpretabilidade:** **baixa-média**.
- **Custo computacional:** **médio-alto**.
- **Faz sentido com T=14?:** **limitado**.
- **Veredito:** **testar depois**.

### 3.4 Mixture-of-Experts e gating adaptativo

#### 3.4.1 MoE clássico interpretável (Jacobs 1991; Jordan & Jacobs 1994)
- **Referências:**
  1) Jacobs, R. et al. (1991), *Neural Computation*. DOI: https://doi.org/10.1162/neco.1991.3.1.79
  2) Jordan, M.; Jacobs, R. (1994), *Neural Computation*. DOI: https://doi.org/10.1162/neco.1994.6.2.181
- **Status:** **Revisado por pares**
- **Ideia central:** poucos experts locais + gate probabilístico.
- **Aplicação no HERALD:** 2–3 experts (normal, choque, rebound) com gate condicionado por grafo/setor.
- **Risco de overfitting:** **médio**.
- **Interpretabilidade:** **alta** (probabilidades de roteamento).
- **Custo computacional:** **médio**.
- **Faz sentido com T=14?:** **sim**, somente com poucos experts.
- **Veredito:** **usar agora** (versão pequena).

#### 3.4.2 Sparse MoE moderno e colapso de experts (Shazeer 2017; Fedus 2022)
- **Referências:**
  1) Shazeer, N. et al. (2017), *ICLR*. https://arxiv.org/abs/1701.06538
  2) Fedus, W. et al. (2022), *JMLR*. https://www.jmlr.org/papers/v23/21-0998.html
- **Status:** **Revisado por pares**
- **Ideia central:** roteamento esparso com perdas de balanceamento.
- **Aplicação no HERALD:** inspiração para regularizador de balanceamento de gate.
- **Risco de overfitting:** **alto** para implementação “full”.
- **Interpretabilidade:** **média**.
- **Custo computacional:** **alto**.
- **Faz sentido com T=14?:** **não**, em versão grande.
- **Veredito:** **descartar** como arquitetura principal; **aproveitar só regularizador de balanceamento**.

#### 3.4.3 Gating interpretável para forecasting multivariado (TFT)
- **Referência:** Lim, B. et al. (2021), *International Journal of Forecasting*. DOI: https://doi.org/10.1016/j.ijforecast.2021.03.012
- **Status:** **Revisado por pares**
- **Ideia central:** blocos de gating e seleção de variáveis interpretáveis.
- **Aplicação no HERALD:** reutilizar apenas módulo de variável gating/attribution, não modelo completo.
- **Risco de overfitting:** **médio-alto** se usar TFT inteiro.
- **Interpretabilidade:** **alta**.
- **Custo computacional:** **médio-alto**.
- **Faz sentido com T=14?:** **parcial**.
- **Veredito:** **testar depois** (ablação modular).

### 3.5 Ensemble e seed stability

#### 3.5.1 Deep Ensembles (Lakshminarayanan et al., 2017)
- **Referência:** Lakshminarayanan, B. et al. (2017), *NeurIPS*. https://arxiv.org/abs/1612.01474
- **Status:** **Revisado por pares**
- **Ideia central:** média de múltiplos modelos com seeds distintas.
- **Aplicação no HERALD:** ensemble de 3–5 modelos para reduzir variância no fold 2021.
- **Risco de overfitting:** **baixo-médio**.
- **Interpretabilidade:** **média**.
- **Custo computacional:** **alto** (treino multiplicado por N).
- **Faz sentido com T=14?:** **sim**.
- **Veredito:** **usar agora** (N pequeno).

#### 3.5.2 SWA (Izmailov et al., 2018)
- **Referência:** Izmailov, P. et al. (2018), *UAI*. https://arxiv.org/abs/1803.05407
- **Status:** **Revisado por pares**
- **Ideia central:** média de pesos ao final do treino para solução mais plana.
- **Aplicação no HERALD:** pós-processamento padrão de cada seed para reduzir colapso.
- **Risco de overfitting:** **baixo**.
- **Interpretabilidade:** **neutra**.
- **Custo computacional:** **baixo**.
- **Faz sentido com T=14?:** **sim**.
- **Veredito:** **usar agora**.

#### 3.5.3 Snapshot Ensembles (Huang et al., 2017)
- **Referência:** Huang, G. et al. (2017), *ICLR*. https://arxiv.org/abs/1704.00109
- **Status:** **Revisado por pares**
- **Ideia central:** múltiplos snapshots de um único treino cíclico.
- **Aplicação no HERALD:** alternativa barata a deep ensemble.
- **Risco de overfitting:** **médio**.
- **Interpretabilidade:** **baixa**.
- **Custo computacional:** **médio**.
- **Faz sentido com T=14?:** **sim**, mas secundário.
- **Veredito:** **testar depois**.

#### 3.5.4 Model Soups (Wortsman et al., 2022)
- **Referência:** Wortsman, M. et al. (2022), *ICML*. https://arxiv.org/abs/2203.05482
- **Status:** **Revisado por pares**
- **Ideia central:** média de pesos de modelos finos sem custo extra de inferência.
- **Aplicação no HERALD:** combinar checkpoints/seeds estáveis.
- **Risco de overfitting:** **médio** (depende de compatibilidade de bacias).
- **Interpretabilidade:** **baixa**.
- **Custo computacional:** **baixo-médio**.
- **Faz sentido com T=14?:** **sim**.
- **Veredito:** **testar depois**.

### 3.6 Robust training sob regime shift

#### 3.6.1 Group DRO / worst-group (Sagawa et al., 2020)
- **Referência:** Sagawa, S. et al. (2020), *ICLR*. https://arxiv.org/abs/1911.08731
- **Status:** **Revisado por pares**
- **Ideia central:** minimizar erro no pior grupo em vez da média.
- **Aplicação no HERALD:** grupos = ano (2021...2025), macro-região, setor A10.
- **Risco de overfitting:** **baixo-médio** (melhor que overfocus em média).
- **Interpretabilidade:** **alta** (erros por grupo explícitos).
- **Custo computacional:** **médio**.
- **Faz sentido com T=14?:** **sim**.
- **Veredito:** **usar agora**.

#### 3.6.2 Distributional Robust Optimization (Levy et al., 2020)
- **Referência:** Levy, D. et al. (2020), *NeurIPS*. https://arxiv.org/abs/2010.05893
- **Status:** **Revisado por pares**
- **Ideia central:** otimizar pior caso em vizinhança distribucional (ex.: CVaR).
- **Aplicação no HERALD:** objetivo híbrido média + CVaR por ano.
- **Risco de overfitting:** **médio**.
- **Interpretabilidade:** **média**.
- **Custo computacional:** **médio-alto**.
- **Faz sentido com T=14?:** **parcial**.
- **Veredito:** **testar depois**.

#### 3.6.3 IRM (Arjovsky et al., 2019)
- **Referência:** Arjovsky, M. et al. (2019), arXiv: https://arxiv.org/abs/1907.02893
- **Status:** **Preprint**
- **Ideia central:** aprender preditores invariantes entre ambientes.
- **Aplicação no HERALD:** ambientes = anos e regiões.
- **Risco de overfitting:** **alto** em amostra curta por instabilidade de otimização.
- **Interpretabilidade:** **média**.
- **Custo computacional:** **médio-alto**.
- **Faz sentido com T=14?:** **fraco**.
- **Veredito:** **descartar** no curto prazo.

### 3.7 Multiobjetivo (WMAPE total, 2021, A10)

#### 3.7.1 Pareto MTL / MGDA (Sener & Koltun, 2018; Lin et al., 2019)
- **Referências:**
  1) Sener, O.; Koltun, V. (2018), *NeurIPS*. https://arxiv.org/abs/1810.04650
  2) Lin, X. et al. (2019), *NeurIPS*. https://arxiv.org/abs/1912.12854
- **Status:** **Revisado por pares**
- **Ideia central:** otimização multiobjetivo explícita no gradiente.
- **Aplicação no HERALD:** objetivos separados para WMAPE total, WMAPE-2021 e erro A10.
- **Risco de overfitting:** **médio** (se fronteira muito explorada).
- **Interpretabilidade:** **alta** (trade-offs explícitos).
- **Custo computacional:** **médio**.
- **Faz sentido com T=14?:** **sim**, com 2–3 objetivos fixos.
- **Veredito:** **usar agora**.

#### 3.7.2 ε-constraint (Mavrotas, 2009)
- **Referência:** Mavrotas, G. (2009), *Applied Mathematics and Computation*. DOI: https://doi.org/10.1016/j.amc.2009.03.037
- **Status:** **Revisado por pares**
- **Ideia central:** otimizar objetivo principal com restrições mínimas nos secundários.
- **Aplicação no HERALD:** minimizar WMAPE global sujeito a teto de erro em 2021 e A10.
- **Risco de overfitting:** **baixo-médio**.
- **Interpretabilidade:** **alta**.
- **Custo computacional:** **baixo-médio**.
- **Faz sentido com T=14?:** **sim**.
- **Veredito:** **usar agora**.

## 4. Tabela comparativa

| Método | Classe | Overfit (T=14) | Interpretabilidade | Custo | T=14 | Veredito |
|---|---|---:|---:|---:|---|---|
| Markov Switching (Hamilton) | Regime switching | Baixo-Médio | Alta | Baixo | Forte | **Usar agora** |
| Switching State-Space pequeno | Regime switching | Médio | Média-Alta | Médio | Forte | **Usar agora** |
| PELT + CUSUM + ruptures | Change-point causal | Baixo-Médio | Alta | Baixo | Forte | **Usar agora** |
| BOCPD truncado | Change-point causal | Médio | Alta | Baixo-Médio | Forte | **Usar agora** |
| Mean Teacher + smooth latent | Estabilização latente | Baixo-Médio | Média | Baixo-Médio | Forte | **Usar agora** |
| VICReg (anti-collapse) | Estabilização latente | Médio | Média | Médio | Bom | **Usar agora** |
| MoE pequeno (2–3 experts) | MoE/gating | Médio | Alta | Médio | Bom | **Usar agora** |
| Sparse MoE grande | MoE/gating | Alto | Média | Alto | Fraco | **Descartar** |
| SWA | Seed stability | Baixo | Neutra | Baixo | Forte | **Usar agora** |
| Deep Ensemble (3–5) | Seed stability | Baixo-Médio | Média | Alto | Forte | **Usar agora** |
| Snapshot / Model soups | Seed stability | Médio | Baixa | Médio | Bom | **Testar depois** |
| Group DRO (ano/região/A10) | Robust shift | Baixo-Médio | Alta | Médio | Forte | **Usar agora** |
| DRO tipo CVaR | Robust shift | Médio | Média | Médio-Alto | Parcial | **Testar depois** |
| IRM | Robust shift | Alto | Média | Médio-Alto | Fraco | **Descartar** |
| Pareto MTL | Multiobjetivo | Médio | Alta | Médio | Bom | **Usar agora** |
| ε-constraint | Multiobjetivo | Baixo-Médio | Alta | Baixo-Médio | Forte | **Usar agora** |

## 5. Top 5 métodos recomendados para o HERALD

1. **Group DRO por ano/região/setor A10** (Sagawa et al., 2020) para atacar diretamente pior-fold 2021.
2. **Markov/switching state-space parcimonioso** (Hamilton, Kim) como camada de regime interpretável e estável.
3. **Pipeline causal de change-point (PELT/CUSUM/BOCPD)** rodando apenas no treino de cada fold.
4. **SWA + Deep Ensemble pequeno (3–5 seeds)** para reduzir sensibilidade de inicialização sem trocar arquitetura.
5. **Multiobjetivo com ε-constraint** para preservar simultaneamente WMAPE total, 2021 e A10.

## 6. Métodos descartados (no curto prazo)

- **Sparse MoE grande / Switch-style full architecture:** custo alto, risco de colapso de experts, excesso de capacidade para T=14.
- **IRM puro como solução principal:** literatura aponta fragilidade de otimização; com poucos anos tende a instabilidade e resultados erráticos.
- **Contrastive temporal pesado sem pré-treino externo:** provável superajuste em painel anual curto.

## 7. Proposta de bateria experimental HERALD (sem flags manuais)

1. **Baseline estável:** Ridge AR + residual NN atual, com 10 seeds fixas.
2. **Ablation A (regime parcimonioso):** adicionar regime 2-estados (Hamilton/Kim style).
3. **Ablation B (ruptura causal):** features de change-point (PELT/CUSUM/BOCPD) geradas fold-a-fold sem futuro.
4. **Ablation C (estabilidade latente):** smoothness + Mean Teacher + VICReg leve.
5. **Ablation D (robustez):** Group DRO com grupos por ano e macro-região.
6. **Ablation E (objetivo):** ε-constraint para garantir limite de erro em 2021 e A10.
7. **Ablation F (seed control):** SWA por seed + ensemble final de 3–5 modelos.
8. **Critério de aceitação:** melhora ou manutenção de WMAPE total, redução do pior-ano (2021), menor variância entre seeds, sem queda relevante em A10.

## 8. Riscos metodológicos

- **Vazamento temporal** ao detectar quebras com janela que inclui futuro do fold.
- **Tuning excessivo em 2021** (overfitting de benchmark), perdendo generalização 2022–2025.
- **Confundir estabilidade por ensemble com aprendizado causal de regime** (ensemble mascara, não explica sozinho).
- **Latentes não identificáveis**: sem restrições de entropia/suavidade, regimes mudam sem significado econômico.
- **Complexidade > dados**: arquiteturas grandes tendem a aparentar ganho por seed e colapsar em replicação.

## 9. Recomendação final

Para estabilizar 2021 sem reintroduzir flags, o caminho metodologicamente mais sólido é: **regime switching pequeno e interpretável + change-point causal + Group DRO + SWA/ensemble curto + objetivo com restrição explícita para 2021 e A10**.

Isso maximiza explicabilidade e robustez em painel anual curto, reduz dependência de seed e controla overfitting melhor do que arquiteturas profundas de regime mais complexas.
