# HERALD Phase 4 — Auditoria Independente do Próximo Passo

Data: 2026-06-09 (rev. 2 — incorpora revisão por pares interna)
Auditor: revisão científica independente (sem implementação de código, sem
lançamento de jobs, sem pressuposto de que expandir países seja correto)
Fontes internas: Phase 4H-B (`7434844`), Phase 4I-A (`7439835`),
`run_phase4i_benchmark.py`, painel `data/processed/phase4g/joint/panel_ze2020.csv`.

> **Rev. 2 — correções aceitas de revisão interna (2026-06-09):** (1) escopo do
> claim explicitado nos dois sentidos; (2) Eurostat mantém **duas** populações
> (enterprise births e employer enterprise births) — a prescrição "migrar para
> employer births" foi **retirada**; (3) a incompatibilidade do alvo é entre os
> quatro países, não FR-vs-resto; (4) NUTS3 não garante comparabilidade (MAUP) —
> harmonizar = nova versão do dataset; (5) conformal vira exploratório, não
> promessa de cobertura; (6) gate de Espanha substituído por critério
> multi-dimensional; (7) multi-step exige protocolo de lags/covariáveis futuras.
> A estrutura D agora é **gate semântico → gate preditivo → decisão**.

---

## 1. Veredito executivo (máx. 15 linhas)

A evidência atual **não** justifica expandir países agora, **não** justifica um
modelo maior e **não** sustenta a hipótese de transferência por grafo/residual.
Sobre quatro domínios, persistência é o melhor baseline balanceado (0.0939) e
Ridge não-ponderado é o melhor modelo treinável (0.0969); o grafo real **não
supera consistentemente** identidade ou permutação (BE teve pequeno ganho, não
significativo); a compatibilidade por descritores melhora NL e PT mas destrói FR
(+113%) e BE (+27%). O painel tem leakage controlado nesta fase (growth_1y/2y são
causais, construídos de defasagens, não do ano-alvo), o protocolo LOCO é correto e
o controle de permutação é válido. **Protocolo:** é *parameter zero-shot com
histórico do país-alvo disponível* (lags e desvios por zona vêm do passado do
próprio país), **não** cold-start completo — distinção já estabelecida no audit
4H. **Escopo do
claim:** *pode-se* afirmar positivamente que o método atual **não transfere
robustamente nestes quatro países e neste protocolo**; *não* se pode afirmar que
grafos/residuais nunca transferirão para outros países ou protocolos — n=4 e o
desbalanceamento (FR 280 zonas vs. PT 25) impedem a generalização. A recomendação
de menor risco é **D**, dividida em dois gates sequenciais: **(i) gate semântico**
— tabela de equivalência dos quatro alvos via documentação oficial antes de
qualquer expansão; **(ii) gate preditivo** — combinação simples
persistência/Ridge (média 50/50, pesos por LOCO interno, fallback persistência),
com calibração conformal apenas exploratória. Só depois decidir entre painel
europeu harmonizado + Espanha, ou fechar como artigo frugal (C). A alternativa
conservadora é **C**: reportar Ridge/persistência como resultado principal honesto
de um benchmark frugal.

---

## 2. Achados ordenados por severidade

### Crítico

- **C1. Quatro países = quatro domínios. Escopo do claim deve ser preciso nos
  dois sentidos.** *Pode-se* afirmar positivamente: o método atual (residual
  neural compartilhado, operador de grafo intra-país, seletor por descritores)
  **não transfere robustamente nestes quatro países e neste protocolo** — isso é
  evidência direta, com controles de falsificação. *Não* se pode afirmar a
  proposição universal "grafos/residuais nunca transferem": n=4 domínios e seeds
  não são amostras territoriais independentes (4H-B Seção 7). Erro a evitar:
  enfraquecer o resultado a ponto de não afirmar nada, OU inflá-lo a uma negação
  universal. Ambos são incorretos.

- **C2. Comparabilidade do alvo não está estabelecida e é provavelmente
  heterogênea — falta verificação documental.** O alvo é
  `side_establishment_creations_official` (criação de **estabelecimentos**), com
  coluna separada `side_enterprise_creations_official`. Os indícios abaixo vêm
  dos *adapters* de ingestão do projeto, **não** de documentação oficial; são
  hipóteses a confirmar contra os metadados nacionais de NL, BE e PT antes de
  qualquer claim:
  - **FR:** créations d'établissements (SIRENE/INSEE), unidade = estabelecimento;
  - **NL:** CBS `83631NED` *OprichtingenVanVestigingen* — geometria COROP.
    Confirmado **quanto à unidade local** (vestigingen = estabelecimentos/unidades
    locais, cf. CBS `81575ned`), como FR; **equivalência demográfica ainda por
    verificar** (regras de reativação, fusões/cisões, limiar de atividade);
  - **BE:** aparentemente primeiras inscrições à TVA — registro fiscal, que
    tende a sobrecontar vs. births demográficos; a confirmar;
  - **PT:** entradas GEP/Quadros de Pessoal — unidade a **confirmar**.

  Até essa verificação, a redação correta é: *comparabilidade não estabelecida e
  provavelmente heterogênea entre os quatro países*.

  Eurostat, por sua vez, mantém **duas** populações distintas: *enterprise
  births* (inclui empresas sem empregados) e *employer enterprise births* (≥1
  empregado), ambas com regra de reativação de 2 anos e exclusão de
  fusões/cisões. **Não** há justificativa para migrar obrigatoriamente para
  "employer births": é preciso primeiro identificar qual indicador Eurostat e
  qual conceito nacional melhor correspondem a cada target atual. Conclusão: os
  quatro países podem estar medindo quatro objetos diferentes; isto é mais grave
  para a tese científica do que qualquer escolha de arquitetura, e exige uma
  **tabela de equivalência** (gate semântico) antes de qualquer expansão.

- **C3. Desbalanceamento territorial extremo condiciona toda conclusão.**
  Contagem de linhas: FR 2800 (280 zonas), BE 420 (42), NL 400 (40), PT 250 (25).
  France domina o pooled fit a menos que se balanceie; mas balancear melhora FR e
  degrada os menores (4I-A). Ou seja, a métrica "country-balanced" e a "pooled"
  podem inverter o ranking de modelos. Qualquer claim deve fixar a métrica e
  mostrar sensibilidade às duas.

### Alto

- **A1. O grafo é block-diagonal: nunca testou message passing transfronteiriço.**
  Confirmado em 4H-B/4H concept audit. O experimento testou transferência de um
  operador de grafo para a topologia *intra-país* de um país não visto — não
  troca de informação entre países. Logo, "grafo não generaliza" refere-se a um
  operador intra-país compartilhado, não a difusão espacial entre territórios.

- **A2. Compatibilidade por distância de descritores não prediz transferência.**
  4I-A: o seletor escolhe 2 fontes em 27/28 folds, melhora NL/PT mas falha
  catastroficamente em FR/BE. Proximidade de descritores ≠ compatibilidade
  dinâmica. Isto enfraquece a hipótese "proximidade geográfica → transferência".

- **A3. A vantagem da persistência é um resultado dependente do horizonte de 1
  ano — não um artefato.** Persistência é um resultado científico válido neste
  horizonte; o ponto é que sua vantagem **pode não permanecer** em horizontes
  maiores (t+2/t+3, multi-step), que não foram testados. Vencer persistência num
  único passo anual é um teste fraco da utilidade de estrutura espaço-temporal,
  mas o resultado não deve ser desqualificado como artefato nem extrapolado para
  além do horizonte avaliado.

### Médio

- **M1. Fragilidade dos vencedores marginais.** NL `base_identity` vence por
  margem de seletor de 0.000075; ganho concentrado em 2019 e 2024. PT por
  margens da ordem de 1e-4. São diagnósticos locais, não componentes universais.

- **M2. O MLP pequeno (0.189) não é evidência contra não-linearidade.** É um único
  ponto de capacidade/treino instável (std de seed alto: FR 0.071, PT 0.090). Não
  permite concluir "não-linearidade não ajuda" — apenas que *este* MLP, *neste*
  regime, falha. Não usar como prova contra B.

### Baixo / Confirmações positivas

- **B1. Sem leakage nesta fase.** Verificado manualmente: `growth_1y = lag1/lag2−1`
  e `growth_2y = lag1/lag3−1` (BE 2015: 1679/1223−1 = 0.3729 ✓). Persistência e
  drift não usam essas features; Ridge/EN/MLP usam features causais. A nota de
  leakage histórica (growth usando ano-alvo) **não** se aplica ao painel 4G/4I.
- **B2. Protocolo LOCO e controles de falsificação válidos** (exclusão de país,
  imputer/scaler só em fontes, permutação de grafo preservando grau, controle EU
  fold-safe). O lado de execução está correto.

---

## 3. O que os resultados demonstram e o que não demonstram

**Demonstram (sobre estes 4 países, alvo atual, horizonte 1 ano):**
- Persistência é o piso universal e Ridge não-ponderado o melhor treinável.
- Um residual neural compartilhado *incondicional* não melhora transferência
  zero-shot de forma robusta.
- Distância de descritores e o operador de grafo intra-país atual não são
  mecanismos confiáveis de seleção/transferência.
- O pipeline causal t-1, rolling origin e LOCO está corretamente implementado.

**NÃO demonstram (claim universal):**
- Que residual/grafo "nunca generaliza" para outros países/protocolos (n=4).
- Que message passing transfronteiriço é inútil (nunca foi testado).
- Que não-linearidade é inútil (testou-se um MLP frágil).
- Que o ganho de persistência se manteria em horizontes >1 ano ou multi-step.
- Que os países são comparáveis no conceito de alvo (C2 em aberto).

---

## 4. Matriz de decisão A/B/C/D

(A opção "E. Outra" foi **eliminada**: o que antes era E — combinação + conformal
+ harmonização — é exatamente o conteúdo de D, não uma alternativa distinta.)

| Critério | A. Expandir p/ países próximos da FR | B. Melhorar arquit./seleção c/ 4 países | C. Reformular: Ridge/persistência = resultado principal | D. Etapa intermediária frugal (gate semântico → combinação → decisão) |
|---|---|---|---|---|
| Ganho científico | Médio (mais domínios) mas diluído por heterogeneidade | Baixo (já há sinal de transferência negativa) | Alto p/ honestidade; baixo p/ novidade | **Alto** (resolve ambiguidades + claim defensável frugal) |
| Risco metodológico | **Alto** (C2 comparabilidade, geometrias mistas, quebras de série) | Médio-alto (overfit a 4 domínios, p-hacking de config) | Baixo | **Baixo** |
| Custo de dados | Alto (ingestão/harmonização Eurostat por país) | Nulo | Nulo | Baixo |
| Custo computacional | Alto (re-treino LOCO ampliado) | Alto (baterias neurais) | Nulo | **Baixo** |
| Capacidade de falsificação | Aumenta domínios mas confunde fonte de erro | Baixa (difícil isolar causa) | N/A | **Alta** (testa hipóteses isoladas barato) |
| Adequação ao artigo ("frugal") | Tensiona o framing frugal | Contradiz (capacidade sem evidência) | Coerente, mas pouco vendável sozinho | **Mais coerente** com "apprentissage frugal" |

Leitura: **A** é a opção de maior risco/custo e menor ganho marginal de
informação no momento. **B** contraria a evidência. **C** é seguro mas magro.
**D** (etapa intermediária centrada em combinação de previsões + conformal
exploratório + harmonização do alvo) maximiza ganho de informação por custo; **C**
é o resultado final caso o gate preditivo de D não bata persistência.

---

## 5. Auditoria dos países candidatos

Disponibilidade territorial: Eurostat publica business demography regional a
**NUTS3** sob base legal nova (Regulamento (UE) 2019/2152, European Business
Statistics) a partir do ano de referência **2021**; antes disso a cobertura
NUTS3 era de coleta voluntária/piloto (anos 2008–2010 e séries `bd_h`
históricas 2004–2020 com lacunas). Comparabilidade internacional é considerada
alta para a população de empresas **empregadoras**, mas Eurostat publica também
a população de *enterprise births* incluindo empresas sem empregados — são dois
indicadores distintos, e a escolha deve seguir da tabela de equivalência (gate
semântico), não de uma migração imposta.

**Aviso MAUP:** NUTS3 **não** é condição automática de comparabilidade para
previsão territorial. **Fato confirmado pelos adapters de ingestão: o painel atual
já mistura geometrias** — FR usa **ZE2020** (zones d'emploi), NL **COROP**, BE
**arrondissements**, PT **NUTS3**. São quatro escalas/zoneamentos diferentes,
não NUTS3 homogêneo. Por isso sofrem do *Modifiable Areal Unit Problem*: o erro e
a estrutura espacial mudam com a escala e o zoneamento. Padronizar tudo em NUTS3
seria uma **nova versão do dataset** (re-agregação + reconstrução causal dos
lags), não uma correção pequena. A coluna abaixo "Conceito births" indica o
indicador Eurostat candidato, ainda **a confirmar** contra a fonte nacional.

| País | Territorial | Período NUTS3 utilizável | Conceito births | Setores (NACE) | Emprego | Geometria / fluxos transfronteiriços | Comparabilidade c/ painel atual |
|---|---|---|---|---|---|---|---|
| **Alemanha (DE)** | NUTS3 (Kreise, ~400) | Births NUTS3 fracos historicamente; melhora pós-2021 | Eurostat births (empregadoras ou total — a confirmar) | Bom | Bom | Fronteira terrestre direta c/ FR/BE; muitos fluxos | **Média.** Forte economicamente, mas conceito ≠ estabelecimentos FR; risco de quebra de série |
| **Espanha (ES)** | NUTS3 (provincias, 52) | Participou de pilotos; cobertura razoável pós-2021 | Eurostat births (empregadoras ou total — a confirmar) | Bom | Bom | Fronteira c/ FR (Pirenéus, fluxo menor) | **Média.** Boa contiguidade com PT/FR |
| **Itália (IT)** | NUTS3 (province, ~107) | Voluntária em pilotos; cobertura média | Eurostat births (empregadoras ou total — a confirmar) | Bom | Bom | Fronteira c/ FR (Alpes) | **Média.** Heterogeneidade Norte/Sul alta |
| **Luxemburgo (LU)** | NUTS3 = 1 unidade (país inteiro) | OK mas trivial | Eurostat births (empregadoras ou total — a confirmar) | Limitado p/ NUTS3 | Forte commuting | **Núcleo** de fluxo transfronteiriço FR/BE/DE | **Baixa como domínio** (1 território ≈ 0 variância espacial), **alta** como caso de fluxo |
| **Suíça (CH)** | NUTS3-equivalente (cantões, 26) | **Fora do Regulamento UE**; dados via OFS, não Eurostat | Definição OFS, **não** harmonizada Eurostat | Diferente | Bom | Núcleo de commuting c/ FR (arc lémanique) | **Baixa.** Quebra de fonte e definição; risco de incomparabilidade |

Conclusão da auditoria de países: **Espanha** é a candidata prioritária **a
preflight** (contiguidade FR/PT, NUTS3 estável, dentro do quadro Eurostat) — não
uma integração já aprovada. **Alemanha** é
o teste mais forte de heterogeneidade. **Luxemburgo e Suíça não devem entrar
como domínios independentes** (LU é território único; CH está fora do quadro
Eurostat — quebra de definição). Nenhum deve entrar antes de C2 resolvido **e**
de Espanha passar o gate multi-dimensional (Seção 8): equivalência conceitual do
target, continuidade temporal, granularidade territorial, cobertura setorial e
reconstrução causal dos lags. O critério "não degradar os 4 atuais em >1%" é
**necessário mas não suficiente** — não decide integração sozinho.

---

## 6. Avaliação obrigatória dos 10 pontos

1. **4 países bastam para concluir não-generalização?** Sim para o claim
   *condicional* ("não transfere nestes 4 países + este protocolo"), com apoio
   dos controles de falsificação. Não para o claim *universal* ("nunca
   transfere"): n=4, inferência cruzada apenas descritiva.
2. **Adicionar países aumenta evidência independente?** Parcialmente, mas
   acrescenta heterogeneidade e problemas de comparabilidade (C2) que podem
   *reduzir* a interpretabilidade do erro de transferência. Não é solução
   automática.
3. **Países prioritários (apenas candidatos):** ES (contiguidade + quadro
   Eurostat estável), depois DE (heterogeneidade). "Prioritário" aqui significa
   *candidato a preflight*, **não** integração aprovada. ES exige preflight real
   antes de entrar: conceito de target, anos disponíveis, granularidade NUTS3,
   cobertura setorial e disponibilidade dos lags em t-1. Evitar LU (território
   único) e CH (fora do Eurostat).
4. **Proximidade geográfica como hipótese de transferência:** defensável como
   *hipótese*, mas 4I-A já mostra que proximidade de descritores **não** prediz
   transferência. Proximidade geográfica deve ser testada como hipótese
   falsificável, não assumida.
5. **NUTS3/alvo/setores/período harmonizáveis?** Período sim (2015–2024,
   2021+ legalmente coberto; verificar quebra de série em 2021). NUTS3 disponível
   para BE/ES/IT/DE; **FR usa zones d'emploi (ZE2020), não NUTS3** —
   incompatibilidade geométrica real, agravada por MAUP (re-agregar = nova versão
   do dataset). Alvo: harmonizável **somente após** uma tabela de equivalência —
   há ≥4 conceitos em jogo (établissements FR, vestigingen NL, inscrições TVA BE,
   entradas GEP PT) e **dois** indicadores Eurostat (births totais vs. de
   empregadoras). Migrar para "employer births" não é justificado a priori.
6. **Grafos transfronteiriços necessários agora?** Não. Introduzem nova variável
   experimental prematuramente. Primeiro estabelecer um alvo comparável e um
   baseline de combinação; só então testar arestas transfronteiriças com controle
   de permutação.
7. **Persistência favorecida pelo horizonte anual curto?** Sim, provavelmente em
   parte. Horizonte de 1 passo favorece persistência estruturalmente. Testar
   horizonte t+2/t+3 é válido **mas não imediato**: exige protocolo definido para
   obter lags e covariáveis futuras (forecast recursivo ou direto), senão se
   compara persistência contra modelo alimentado por informação indisponível —
   comparação injusta. Definir o contrato de features futuras antes de prometer
   multi-step.
8. **LOCO é justo para treinados vs. persistência?** Sim — persistência usa
   `side_lag_1` do próprio país-alvo, e os treinados recebem o mesmo histórico
   t-1. O protocolo é simétrico e causal. Persistência não tem vantagem indevida.
9. **Leakage / ponderação / baseline mal especificado?** Sem leakage nesta fase
   (B1). Ponderação **é** uma variável crítica (C3): balanced vs. unweighted
   invertem rankings — deve ser sempre reportado em par. Baselines bem
   especificados (last_value, drift, AR-OLS, EN, spatial-lag com permutação).
10. **Maior ganho de informação por custo:** gate semântico (tabela de
    equivalência dos 4 alvos) + benchmark de **combinação de previsões**
    (persistência⊕Ridge; 50/50, pesos por LOCO interno, fallback persistência),
    com calibração conformal **exploratória** (cobertura agregada, calibração
    rolling — não promessa por país). Custo quase nulo, falsificabilidade alta,
    resolve a ambiguidade central antes de qualquer expansão.

---

## 7. Recomendação principal e alternativa conservadora

**Principal (D):** executar uma **etapa intermediária frugal** em dois gates
antes de A/B/C:
1. **Gate semântico (C2):** produzir uma tabela de equivalência dos quatro alvos
   (établissements FR, vestigingen NL, inscrições TVA BE, entradas GEP PT) usando
   documentação oficial e, quando possível, comparar cada série nacional com o
   indicador Eurostat candidato (births total vs. empregadoras). Não migrar para
   "employer births" sem essa evidência; documentar o conceito efetivo e
   restringir claims ao que o alvo realmente mede.
2. **Gate preditivo:** avaliar **combinação de previsões** simples —
   persistência, Ridge, média fixa 50/50, pesos escolhidos só por LOCO interno,
   fallback para persistência. Calibração conformal apenas **exploratória**.
3. Reportar sempre métrica country-balanced **e** pooled (sensibilidade C3).

Isto produz uma contribuição metodológica coerente com "apprentissage frugal"
sem gastar dados/compute em expansão de risco alto.

**Conservadora (C):** se não houver apetite para (1)-(2), reformular o artigo
em torno de "benchmark frugal honesto: persistência e Ridge dominam STGNN em
painéis anuais curtos territoriais", reportando 4H/4I como resultado negativo
principal com os controles de falsificação como força metodológica.

**Não recomendado agora:** A (expandir) e B (mais arquitetura) — ambos têm
ganho esperado de informação baixo relativo ao custo e ao risco metodológico
não resolvido (C2/C3).

---

## 8. Plano sequencial com critérios objetivos de avanço/parada

- **Gate 1 — Semântico (comparabilidade do alvo).**
  Produzir tabela de equivalência dos 4 alvos vs. indicador Eurostat candidato.
  Critério de avanço, em ordem:
  - **(obrigatório) equivalência documental:** cada alvo nacional mapeia a um
    conceito Eurostat segundo os metadados oficiais (unidade, reativação,
    fusões/cisões, limiar de atividade);
  - **(diagnóstico secundário) comparação de níveis, crescimento e rupturas**
    entre série nacional e Eurostat — apenas para detectar discrepâncias, **não**
    como prova de equivalência;
  - **(regra anti-viés) nenhum limiar estatístico decidido após observar os
    resultados** (sem ajuste post-hoc do critério de aceitação).

  Para/ajusta se: conceitos irredutíveis → restringir o claim ("establishment
  creations FR + births
  outros") e documentar como limitação explícita. **Não** impor "employer
  births".
- **Gate 2 — Preditivo (combinação, custo ~nulo).**
  Combinações: persistência, Ridge, média 50/50, pesos por LOCO interno, fallback
  persistência. Critérios de avanço, explícitos:
  - **métrica primária:** WMAPE média balanceada **por país** (a combinação
    iguala ou supera o melhor componente em ≥3/4 países);
  - **métrica secundária:** WMAPE pooled;
  - **restrição:** nenhum país degrada mais de 1% vs. o melhor componente;
  - **diagnóstico:** reportar vitórias por **ano e país** (não só agregados).

  Conformal entra como análise **exploratória** apenas. Encerra como artigo C se
  a combinação não superar persistência.
- **Gate 3 — Decisão A/B (condicional).**
  Só se Gate 2 mostrar que um componente treinável adiciona valor robusto **e**
  os critérios multi-dimensionais de novos países (H4) forem satisfeitos.

Regra de parada global (**limiar operacional provisório, não fundamentado em
teoria**): qualquer etapa que não bata persistência na métrica primária (WMAPE
média balanceada por país) por **≥1% relativo** — i.e. WMAPE_modelo ≤ 0.99 ×
WMAPE_persistência — com estabilidade entre anos, encerra a linha e converte em
resultado negativo reportável. O valor de 1% é convenção a ser revisada (ex.:
calibrar contra o desvio entre seeds/anos); declarar explicitamente que é
relativo, não absoluto.

---

## 9. Hipóteses falsificáveis

- **H1.** Combinação persistência⊕Ridge reduz WMAPE balanceado vs. melhor
  componente isolado em ≥3/4 países. (Falsa se ≤2.)
- **H2 (exploratória, não promessa).** Com quatro países heterogêneos e ~7 folds
  com dependência temporal, **não** se promete cobertura formal forte. Usar
  resíduos rolling-origin **normalizados por país** e reportar cobertura **por
  país e agregada** como diagnóstico — nunca como gate de aprovação.
- **H3.** Os quatro alvos nacionais medem objetos diferentes (FR établissements,
  NL vestigingen, BE inscrições TVA, PT entradas GEP). **Equivalência é primeiro
  documental:** definir, a partir dos metadados oficiais, se cada alvo mapeia ao
  mesmo conceito Eurostat (unidade, regra de reativação, tratamento de
  fusões/cisões). Correlação alta entre séries **não** prova equivalência
  semântica (duas séries podem co-mover medindo objetos distintos); serve apenas
  como verificação secundária após a equivalência conceitual estar estabelecida.
  (H3 falsa se os metadados oficiais confirmarem o mesmo conceito em todos.)
- **H4 (integração de novos países — multi-critério).** ES só é integrável se
  passar **todos**: (a) equivalência conceitual do target; (b) continuidade
  temporal (sem quebra inexplicada, incl. 2021); (c) granularidade territorial
  compatível (MAUP avaliado); (d) cobertura setorial alinhada; (e) reconstrução
  causal dos lags. Critério de não-degradação dos 4 atuais (>1%) é necessário mas
  **não suficiente** — entra só após (a)–(e).
- **H5 (transfronteiriço, condicional).** Um grafo com arestas FR–ES reais bate
  o mesmo grafo com arestas transfronteiriças permutadas em ≥2 países. (Só
  testar após H1–H4.)
- **H6 (horizonte).** A vantagem de persistência diminui a horizonte 2–3 anos
  ou multi-step; se mantida, confirma limitação estrutural do alvo anual.

---

## 10. Referências verificadas

- Eurostat — *Business demography statistics* (Statistics Explained). Conceito de
  enterprise birth, regra de reativação 2 anos; duas populações (births totais e
  de empregadoras); comparabilidade internacional mais alta para empregadoras.
  https://ec.europa.eu/eurostat/statistics-explained/index.php?title=Business_demography_statistics
- Eurostat — *Business demography: information on data* (definições, populações,
  cobertura nacional).
  https://ec.europa.eu/eurostat/web/business-demography/information-data
- Eurostat — *Business demography (bd) metadata / SIMS* (definições e fontes).
  https://ec.europa.eu/eurostat/cache/metadata/en/bd_sims.htm
- Eurostat — *NUTS overview* (geometrias territoriais; base para análise MAUP).
  https://ec.europa.eu/eurostat/web/nuts
- Eurostat — *Structural business statistics at regional level* (NUTS2/NUTS3).
  https://ec.europa.eu/eurostat/statistics-explained/index.php?title=Structural_business_statistics_at_regional_level
- Eurostat — *Business demography – historical data (2004-2020) (bd_h)*, metadados
  ESMS (cobertura/lacunas NUTS3 históricas).
  https://ec.europa.eu/eurostat/cache/metadata/en/bd_h_esms.htm
- Eurostat/OECD — *Manual on Business Demography Statistics* (2007), KS-RA-07-010.
  https://ec.europa.eu/eurostat/documents/3859598/5901585/KS-RA-07-010-EN.PDF
- Regulamento (UE) 2019/2152 (European Business Statistics) — base legal de
  business demography regional a partir do ano de referência 2021. (Referência
  citada via Eurostat Statistics Explained; verificar texto consolidado em
  EUR-Lex antes de citar no artigo.)
- Fudenberg, Gao, Liang — *The Transfer Performance of Economic Models*,
  arXiv:2202.04796. "Algoritmos black-box superam modelos econômicos dentro do
  domínio, mas generalizam pior entre domínios." Suporte direto ao padrão HERALD.
  https://arxiv.org/abs/2202.04796
- *Domain Generalization in Time Series Forecasting*, ACM TKDD, 10.1145/3643035.
  https://dl.acm.org/doi/10.1145/3643035
- *Mind the naive forecast! A rigorous evaluation of forecasting models for time
  series with low predictability*, Applied Intelligence (2025),
  10.1007/s10489-025-06268-w. Naive não é significativamente superado em séries de
  baixa previsibilidade.
  https://link.springer.com/article/10.1007/s10489-025-06268-w
- Wang, Hyndman, Li, Kang — *Forecast combinations: An over 50-year review*,
  International Journal of Forecasting 39(4), 2023. Combinação supera componentes
  individuais de forma consistente ("forecast combination puzzle").
  https://www.sciencedirect.com/science/article/abs/pii/S0169207022001480
- Zeng, Chen, Zhang, Xu — *Are Transformers Effective for Time Series
  Forecasting?* (DLinear), AAAI 2023, arXiv:2205.13504. Modelo linear simples
  iguala/supera Transformers em forecasting de longo horizonte. Suporta que Ridge
  vencer não é embaraço.
  https://arxiv.org/abs/2205.13504
- Openshaw — *The Modifiable Areal Unit Problem* (CATMOG 38, 1984) e Arbia,
  *The modifiable areal unit problem in regional economics*. Resultados
  estatísticos dependem da escala e do zoneamento das unidades — base do aviso
  MAUP para misturar ZE2020/NUTS3.
  https://www.researchgate.net/publication/23731603_The_modifiable_areal_unit_problem_in_regional_economics
- Xu, Xie — *Conformal Prediction for Time Series* (EnbPI), arXiv:2010.09107, e
  Gibbs, Candès — *Adaptive Conformal Inference Under Distribution Shift*,
  NeurIPS 2021. Exchangeability é violada em séries temporais → garantias
  conformais clássicas enfraquecem; suporta tratar conformal como exploratório.
  https://arxiv.org/abs/2010.09107
- *Rolling-Origin Conformal Prediction under Local Stationarity and Weak
  Dependence*, arXiv:2605.08422 (2026). Taxa de erro de cobertura O(T^{-β/(2β+1)})
  → cobertura instável com T pequeno (≈7 folds). **Recente, verificar antes de
  citar.**
  https://arxiv.org/abs/2605.08422

**Citações herdadas do 4H concept audit a verificar antes de publicar:** os DOIs
arXiv:2603.02756 (Li et al. 2026) e arXiv:2505.19547 (STRAP) e os links
proceedings.mlr.press v267/v280 devem ser reverificados individualmente
(ano/DOI/autoria); alguns IDs 2026 não foram confirmáveis nesta auditoria e não
devem ser tratados como evidência direta.

---

## 10b. Suporte bibliográfico das decisões (mapa decisão → evidência)

| Decisão da auditoria | Evidência primária | Tipo |
|---|---|---|
| Não aumentar a arquitetura; Ridge vencer não é falha | Zeng et al. (DLinear, AAAI 2023); Si et al. (ICML 2025); Ke et al. (CoLLAs 2025) | Direta (forecasting) |
| Persistência difícil de bater em horizonte curto | *Mind the naive forecast!* (Applied Intelligence 2025); literatura de baselines de persistência | Direta |
| Transferência entre domínios degrada modelos flexíveis | Fudenberg et al. (*Transfer Performance of Economic Models*, arXiv:2202.04796) | Direta (econômica) |
| DG temporal é difícil; alinhar sistemas incompatíveis gera transferência negativa | *Domain Generalization in Time Series Forecasting* (ACM TKDD 10.1145/3643035); Li et al. 2026 (a verificar) | Direta / analógica |
| Combinação persistência⊕Ridge como próximo passo | Wang, Hyndman et al. (*Forecast combinations: 50-year review*, IJF 2023) | Direta |
| Não padronizar geometrias sem estudar escala | Openshaw (1984); Arbia (MAUP em economia regional) | Direta (espacial) |
| Conformal só exploratório com T pequeno e heterogêneo | Xu & Xie (EnbPI 2021); Gibbs & Candès (ACI, NeurIPS 2021); rolling-origin conformal 2026 (a verificar) | Direta (metodológica) |
| Comparabilidade de business demography exige conceito harmonizado | Eurostat *Business demography statistics*; OECD/Eurostat *Manual* (2007) | Direta (estatística oficial) |

**Distinção importante:** as evidências de forecasting/STGNN são em grande parte
de **tráfego, energia e sensores** — analogia, não prova direta para criação de
empresas territorial. O suporte *direto* ao domínio econômico vem de Fudenberg et
al. e da estatística oficial Eurostat/OECD. Tratar as duas classes com pesos
diferentes no artigo.

---

## 11. Perguntas ainda sem evidência suficiente

- O alvo FR (`side_establishment_creations_official`) é conversível para
  enterprise births Eurostat (população total ou de empregadoras, a definir pela
  tabela de equivalência)? Qual a razão births/creations e sua
  variância entre países?
- A vantagem de persistência sobrevive a horizonte >1 ano? (não testado)
- Existe quebra de série em 2021 (mudança de base legal EBS) nos países Eurostat
  dentro de 2015–2024?
- Uma combinação calibrada por domínio-fonte bate persistência sem ler o alvo?
  (hipótese central não testada)

---

### Resumo de severidade

| ID | Severidade | Achado |
|---|---|---|
| C1 | Crítico | n=4 domínios: claim só condicional (in-scope), não universal |
| C2 | Crítico | ≥4 conceitos de alvo (établissements/vestigingen/TVA/GEP) + 2 indicadores Eurostat; MAUP em ZE2020 vs NUTS3 |
| C3 | Crítico | Desbalanceamento FR 280 vs PT 25 inverte rankings balanced/pooled |
| A1 | Alto | Grafo block-diagonal: transfronteiriço nunca testado |
| A2 | Alto | Distância de descritores não prediz transferência |
| A3 | Alto | Vantagem de persistência dependente do horizonte de um ano |
| M1 | Médio | Vencedores marginais frágeis (NL/PT, margens ~1e-4) |
| M2 | Médio | MLP único e instável não falsifica não-linearidade |
| B1 | Confirmação | Sem leakage nesta fase (growth causal) |
| B2 | Confirmação | LOCO e falsificações corretamente implementados |
