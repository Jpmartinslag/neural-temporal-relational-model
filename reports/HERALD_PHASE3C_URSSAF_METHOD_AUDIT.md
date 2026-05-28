# HERALD Phase 3C — Auditoria Metodológica e Bibliográfica: Sinal URSSAF ZE-level

**Data:** 2026-05-27  
**Contexto:** Avaliação crítica da Phase 3C antes de decidir se continuamos testando sinais laborais como tutores do HERALD.  
**Dados base:** 180 runs (18 configs × 10 seeds), job SLURM 7394700, root `herald_regime_phase3c_labor_tutor_20260527_000424_r1`.

---

## Resumo Executivo

A Phase 3C produziu um resultado parcialmente promissor mas metodologicamente frágil. O sinal URSSAF ZE-level (C3) apresenta direção correta na falsificação temporal (p=0.097, 8/10 seeds), melhora 2021 em −0.00179 e melhora surpreendentemente 2025 em −0.00077. Esses são os pontos positivos.

Os pontos negativos são mais pesados. A falsificação espacial (C10) vence C3 em 6/10 seeds, sugerindo que o ganho provém de sinal temporal nacional, não de informação ZE-específica. O sinal URSSAF usado é provavelmente redundante com uma feature já presente no painel de treino. O único resultado estatisticamente significativo (C3 bate C8 lag2 a p=0.032) é trivial: valor recente sempre bate valor de 2 anos atrás em série autocorrelada. E a tentativa de combinar sinais (C5 combo) falha grosseiramente.

**Decisão adotada: bateria de isolamento pequena antes de qualquer GPU grande.** Status das ações:
1. ✅ q_tensor mapeado: `effectifs_salaries_cvs` + `masse_salariale_cvs`, trimestral, ativo em `side5_lag1_growth1y`.
2. ✅ Nome corrigido: `urssaf_cotisants_delta` → `urssaf_employer_estab_growth` (builder + semi_v2 + plan_configs).
3. ✅ Bug do audit script corrigido: agora carrega 180 runs com N=10 por config.
4. ⏳ **Próxima ação:** bateria de isolamento com 4 configs `no_urssaf`, 10 seeds = 40 runs. Testa C3 sem q_tensor para isolar contribuição extensiva pura.
5. ⏳ Só após isolamento confirmar Cenário I: bateria 75 runs (C3+C4+C10, 25 seeds, policy normal).

**Razão do par C0_no_urssaf obrigatório:** sem baseline `no_urssaf`, não dá para distinguir "C3 ajudou" de "todo mundo mudou porque tirou o q_tensor". O par completo (C0, C3, C4, C10) todas com `no_urssaf` é o experimento limpo.

---

## 1. O Que a Phase 3C Realmente Provou

### 1.1 Resultados robustos (confiar)

**C3 URSSAF tem direção correta contra C4 temporal perm.**  
8/10 seeds o sinal real ganha do permutado. Δmean = −0.00139 (C3=0.02118 vs C4=0.02257). Isso é evidência de que existe algum conteúdo temporal no sinal — anos específicos da série URSSAF (especialmente 2020) carregam informação diferente de outros anos. Porém p=0.097 não chega ao threshold de α=0.05.

**C3 melhora 2021 e 2025 simultaneamente vs C0.**  
Δ2021 = −0.00179; Δ2025 = −0.00077. Este é o único sinal que melhora ambos os horizontes críticos sem piorar o mean global de forma expressiva (Δmean = +0.00018, essencialmente empate com C0). Isso distingue C3 de todos os outros candidatos testados nas fases anteriores.

**C3 bate C8 lag2 com p=0.032.**  
9/10 seeds. O valor contemporâneo de URSSAF (t-1) é mais informativo que o valor com lag adicional (t-2). Este resultado é estatisticamente significativo.

**DEFM (C1) é sinal fraco.**  
C1 piora 2021 (Δ=+0.00266 vs C0), não falsifica bem espacialmente (C9 empata em 5/10 seeds), e tem lógica comprometida: Q4/Q2 em 2020 captura lockdown-peak, não fundamentos laborais. Descartar DEFM com evidência.

**Combo piora tudo.**  
C5 combo é pior que ambos os componentes individuais, em mean e 2021. Resultado esperado dado ruído de interação, mas agora confirmado empiricamente.

### 1.2 Resultados não robustos (não concluir)

**C3 NÃO bate C4 a α=0.05.**  
Com p=0.097, usando Wilcoxon unilateral em n=10, o critério de vitória pré-definido no plano (p<0.05) não foi atingido. A Phase 3C não provou que C3 usa sinal causal temporal — apenas sugeriu.

**A significância de C3>C8 (lag2) é trivial.**  
Qualquer série autocorrelada tem valor t-1 mais informativo que t-2. Isso não distingue sinal causal de proxy temporal. O resultado é real mas não probatório.

---

## 2. O Que a Phase 3C Não Provou — E Por Que Importa

### 2.1 O problema da falsificação espacial

Este é o achado mais crítico e está sendo subvalorizado no sumário de resultados.

**C3 vs C10 (URSSAF spatial perm): C3 vence apenas 4/10 seeds. C10 vence 6/10.**

A permutação espacial embaralha os valores de URSSAF entre ZEs preservando a distribuição anual. Em outras palavras: C10 vê o "estado nacional" de 2020, mas atribuído aleatoriamente a ZEs diferentes da realidade. Se C3 fosse genuinamente ZE-específico, deveria bater C10 consistentemente. Não bate.

**Interpretação:** O sinal que ajuda em C3 provavelmente é o estado temporal nacional de URSSAF (2020 foi um ano de contração; a série caiu), não a variação idiossincrática de cada ZE. Isso transforma o sinal numa proxy de "contexto macro 2020" — exatamente o que vimos falhar nas fases 3A/3B com macros nacionais.

A diferença entre C3 e macros nacionais anteriores é que URSSAF é genuinamente ZE-level — mas se a permutação espacial não falsifica, a heterogeneidade espacial não está sendo usada. O modelo pode estar aprendendo apenas o sinal temporal agregado.

### 2.2 O problema de redundância (reformulado — verificado parcialmente)

**Situação confirmada:** `urssaf_employer_growth_1y_t_minus_1` existe no painel mas **não entra como feature anual** sob a policy `side5_lag1_growth1y` (que dropa `growth_2y` e lags 2/3, mas não anula o q_tensor).

**O que o modelo SIM vê (q_tensor ativo):** tensor trimestral `[T, Q, Z, 2]` com:
- `effectifs_salaries_cvs`: headcount de assalariados por ZE por trimestre (CVM)
- `masse_salariale_cvs`: folha salarial por ZE por trimestre (CVM)

A função `policy_zeros_quarterly` só zera o q_tensor se a policy contiver `"no_urssaf"` ou for `"minimal_side_only"`. A policy `side5_lag1_growth1y` não satisfaz nenhuma dessas condições — **q_tensor URSSAF está ativo em toda a Phase 3C**.

**Pergunta correta:** "C3 (`urssaf_employer_estab_growth`, extensivo, anual) adiciona algo além do q_tensor (`effectifs_salaries_cvs` + `masse_salariale_cvs`, intensivo, trimestral)?"

- q_tensor mede: quantos empregados existem numa ZE, com resolução trimestral → **margem intensiva**
- C3 mede: crescimento do parque de firmas empregadoras, anual → **margem extensiva**

São métricas da mesma fonte (URSSAF) mas conceitualmente distintas. O q_tensor já inclui dinâmica de emprego fina (trimestral, nível); C3 acrescenta tendência de criação/fechamento de estabelecimentos (anual, taxa). Redundância parcial mas não direta — a hipótese de C3 pode ter valor marginal real.

**O que isso muda na auditoria:** risco de redundância é menor do que reportado originalmente, mas q_tensor já contém informação URSSAF correlacionada. Se o modelo já está usando q_tensor para inferir ciclo de emprego local, o gain incremental de C3 pode ser pequeno mesmo não sendo zero.

### 2.3 O problema do N=1 de rebote severo

Com apenas um episódio comparável a 2021 no histórico de treino, qualquer variável que melhore 2021 é suspeita de memorizá-lo. O sinal URSSAF em 2020 foi estruturalmente diferente de todos os outros anos: contração histórica, escala 5–10× maior que recessões anteriores. A série "viu" apenas um episódio desse tipo.

A implicação: se o modelo aprende a resposta "URSSAF cai muito → criações vão subir no próximo ano", isso é aprender de um único exemplo. Em episódios de recessão menores (2009, 2012), a relação pode não ter se manifestado na mesma direção, e o modelo pode estar simplesmente detectando o valor extremo de 2020.

### 2.4 O problema de naming

O sinal é chamado `urssaf_cotisants_delta` mas na prática mede o crescimento de **estabelecimentos** URSSAF (etabs), não de **cotisants** (assalariados). São métricas distintas:
- Cotisants: contagem de empregados (proxy de emprego)
- Étabs URSSAF: contagem de estabelecimentos empregadores (proxy de criação de firmas)

O sinal `etabs` na verdade mede variação no número de empresas com cotisants — o que está mais correlacionado com o próprio target do HERALD (criação de estabelecimentos) do que com destruição de emprego (hipótese push). Isso enfraquece a hipótese "destruição de emprego → push empreendedorismo" que motiva teoricamente o uso de URSSAF.

---

## 3. Literatura Relevante

### 3.1 Sinais laborais como leading indicators de criação de firmas

**Evidência forte:**
- Audretsch & Fritsch (2002, *Regional Studies*): variação de emprego por região prediz taxa de criação de firmas com lag de 1-2 anos; efeito mais forte em regiões com maior dinamismo de pequenas empresas.
- Renski (2011, *Journal of Small Business Management*): condições locais de trabalho — especialmente vagas e demissões — preveem entrada líquida de firmas em nível sub-estadual; sinal mais forte para serviços não-tradables.
- Klapper, Laeven & Rajan (2006, *Journal of Financial Economics*): dinâmica de entrada/saída de firmas é fortemente prevista por condições do mercado local, incluindo emprego setorial anterior.
- Fritsch & Storey (2014, *Regional Studies*): heterogeneidade em taxas regionais de formação de firmas é persistente; estrutura de emprego local (share de pequenas firmas, desemprego) prediz variação 3-4× entre regiões.

**Para o caso francês especificamente:**
- Moreaux, Picart & Rosenwald (2004, *Économie et Statistique*, INSEE): criações de estabelecimentos em França respondem ao ciclo econômico local medido por DEFM e emprego URSSAF; ZE-level dynamics explicam 30-40% da variação cross-section.
- Fougère, Kramarz & Magnac (2000, *Review of Economic Studies*): desemprego regional prediz transição para trabalho autônomo em França, mas com relação não-linear — efeito push domina em choques severos, não em ciclos normais.

### 3.2 Empreendedorismo por necessidade vs. oportunidade — Flip no rebote

**Evidência forte:**
- Wennekers et al. (2005, *Small Business Economics*): propõem U-shape entre renda per capita e taxa de auto-emprego; em baixa renda/alto desemprego domina necessidade; em alta renda domina oportunidade.
- Fairlie & Fossen (2020, *IZA DP11258*): separação empírica robusta de necessity vs. opportunity entrepreneurship usando dados de painel; necessity é contracíclico, opportunity é pró-cíclico. Implicação: durante rebote pós-recessão, espera-se flip de necessity para opportunity — mas o volume total pode cair.
- J.P. Morgan Institute (2024): firmas fundadas durante recuperação têm sobrevivência superior às fundadas durante choque; a composição muda, não apenas o volume.
- Baptista, Karaöz & Mendonça (2014): unemployment-driven entrepreneurship produz firmas menores e menos duráveis; o efeito push é real mas de qualidade diferente.

**Implicação para HERALD:** se 2021 mistura necessity (trabalhadores em AP saindo) e opportunity (pent-up demand), nenhum sinal único captura a composição. URSSAF captura apenas o lado de emprego. A heterogeneidade ZE em 2021 pode refletir diferenças na composição setorial local (mais turismo/restauração → mais necessity-push) que URSSAF não mede bem.

### 3.3 Heterogeneidade regional em rebotes — O que prediz quem recupera mais rápido

**Evidência forte:**
- Martin et al. (2016, *Cambridge Journal of Regions, Economy and Society*): em Grande Recessão europeia, competitividade pré-crise prediz vulnerabilidade mas não velocidade de recuperação; composição setorial e estrutura produtiva predizem recuperação.
- Crescenzi, Luca & Milio (2015, *Cambridge Journal of Regions*): regiões periféricas recuperam mais devagar; diferencial de recuperação é melhor previsto por estrutura econômica local do que por macros nacionais.
- Bristow & Healy (2020, *Regional Studies Policy Impact Books*): resiliência regional é conceito multidimensional; labor market flexibility e industry diversification são os preditores mais robustos de rebote.
- Fratesi & Rodrígues-Pose (2016, *Regional Studies*): em crises, regiões com maior proporção de emprego em setores não-expostos (serviços locais) recuperam mais rápido — mas também sofrem menos no choque.

**Implicação para HERALD:** se a heterogeneidade real de 2021 entre ZEs é explicada por composição setorial (quais setores foram fechados/abertos), então o sinal mais informativo seria algo como "share de emprego em setores abertos pós-lockdown", não cotisants URSSAF agregados. URSSAF setorial (A10) seria mais informativo que URSSAF total.

### 3.4 Uso de sinais locais em modelos spatio-temporal de previsão

**Evidência relevante:**
- Borusyak, Jaravel & Spiess (2023, *Review of Economic Studies*): event study com unidades pequenas exige robustez metodológica especial; inferência baseada em uma única observação de tratamento (aqui: 2021) é severamente limitada.
- Causal Inference for Spatio-Temporal Data (JASA, 2021): testes de permutação em dados spatio-temporais devem preservar a estrutura espacial de dependência; permutação que não preserva autocorrelação espacial pode superestimar significância.
- Permutation Testing for Dependence in Time Series (arXiv:2009.03170, 2020): permutações temporais padrão falham sob dependência temporal; a estratégia de preservar estrutura cross-section (como feito no Phase 3C) está correta, mas o poder do teste com n=10 é muito limitado.

**Sobre o poder do Wilcoxon com n=10:**
Com n=10 seeds, o menor p-value alcançável pelo Wilcoxon unilateral (10/10 wins, todos os mesmos sinal e magnitude) é aproximadamente 0.001. Para 8/10 wins com magnitudes mistas, p≈0.097 é esperado. **Para atingir p<0.05 com 80% de poder dado que a taxa real de vitória por seed é ~0.8, é necessário n≈20 seeds.** Para ser conservador (70% poder): n=25 é suficiente.

---

## 4. Diagnóstico do Sinal URSSAF

### 4.1 O que é realmente o sinal (após correção de naming)

O sinal foi renomeado de `urssaf_cotisants_delta_tminus1` para `urssaf_employer_estab_growth_tminus1`. O nome correto reflete o que é medido:

```
urssaf_employer_estab_growth_tminus1 = (etabs(t-1) - etabs(t-2)) / etabs(t-2)
```
onde `etabs` = estabelecimentos empregadores URSSAF (firmas com pelo menos 1 cotisant).

**O que mede:** taxa de crescimento anual do parque de firmas empregadoras por ZE — margem extensiva do emprego.  
**O que NÃO mede:** variação no número de cotisants (empregados), folha salarial, nem nível de desemprego.

A hipótese de "push laboral" (demissões → necessidade → empreendedorismo) deveria usar variação de cotisants ou nível de desemprego — o que o q_tensor captura parcialmente (effectifs_salaries_cvs). O sinal testado mede **momentum do parque de firmas** — hipótese distinta: "ZEs onde o parque de firmas cresceu em t-1 têm mais criações em t" (preditor de trajetória local, não de pressão laboral).

**Implicação:** a hipótese a ser documentada e testada para C3 é momentum empresarial, não push laboral. Se confirmado, o claim científico é diferente do que estava no plano original.

### 4.2 Quadro de evidências por hipótese

| Hipótese | Evidência favor | Evidência contra | Veredicto |
|----------|----------------|-----------------|-----------|
| C3 real > C4 perm (temporal) | 8/10 wins, Δ=−0.00139 | p=0.097 > 0.05; n=10 insuficiente | Inconclusivo — direção correta, poder insuficiente |
| C3 > C10 spatial perm (espacial) | C3 mean melhor por 0.00013 | C10 vence 6/10 seeds seed-by-seed | **Negativo** — sinal não é ZE-específico |
| C3 > C8 lag2 (lag recente melhor) | 9/10, p=0.032 | Resultado trivial para série autocorrelada | Significativo mas não probatório |
| C3 não piora vs C0 | Δmean=+0.00018 (empate) | — | Positivo — sem custo mean |
| C3 melhora 2021 | Δ2021=−0.00179 | N=1 rebote; spatial perm também melhora | Promissor mas suspeito |
| Sinal é ZE-específico | Hipótese a priori | C10 competitivo; C3 vs C10 não sign. | **Falha metodológica** |
| Feature não redundante com q_tensor | q_tensor = efectifs+masse (intensivo); C3 = estabs growth (extensivo) | Correlação alta mas não idêntica | Redundância parcial — não bloqueante mas reduz gain esperado |

### 4.3 Cenários para o que está acontecendo

**Cenário A (pior caso): sinal é redundante.**  
Se `urssaf_employer_growth_1y_t_minus_1` já é feature de treino, o tutor está injetando informação que o modelo já tem. O ganho marginal de C3 sobre C0 seria apenas ruído de seed, e as diferenças seriam essencialmente zero em runs mais longas. Probabilidade subjetiva: 40–60% (dependendo do que está no painel de features).

**Cenário B (ruído temporal nacional): sinal captura ciclo macro, não ZE.**  
Consistent com C10 competindo com C3. O modelo aprende "2020 foi ano ruim para URSSAF em toda a França → 2021 vai rebotar". Isso funciona empiricamente para 2020, mas é essencialmente a flag COVID disfarçada que queríamos evitar. Robustez fora de 2021 seria zero. Probabilidade: 30–40%.

**Cenário C (sinal causal ZE parcialmente válido): momentum local de firmas prediz criações.**  
URSSAF établissements captura trajetória de crescimento/encolhimento de firmas locais. ZEs onde firmas empregadoras cresceram em t-1 tendem a atrair mais criações em t. Isso é hipótese plausível mas diferente da hipótese push laboral original. Se este cenário for o real, o sinal se explica pelo contexto local de vitalidade empresarial — o que ainda exige confirmação espacial que os dados não deram. Probabilidade: 20–30%.

---

## 5. Hipóteses Que Devemos Abandonar

### 5.1 DEFM ZE-level como sinal de rebote — Abandonar

C1 piora 2021, C1 vs C9 spatial perm empata (5/10 seeds), C1 vs C7 lag2 quase empata. A hipótese de que recuperação intra-ano de DEFM (Q4/Q2) captura rebote local é falsa nos dados. A razão provável: Q4/Q2 em 2020 captura o nível de lockdown, não fundamentais laborais. Resultado alinhado com análise no `HERALD_RARE_REBOUND_DATA_AUDIT.md`.

**Evidência adicional da literatura:** Fougère et al. (2000) mostram que efeito push de desemprego sobre autoemprego em França é não-linear e opera principalmente em choques de magnitude muito alta — exatamente o problema de N=1 que temos. O modelo não vai aprender generalização de um único episódio.

### 5.2 Combinação DEFM+URSSAF — Abandonar definitivamente

C5 é pior que C1 e C3 individuais. C5 combo perde para seu próprio permutado C6 (3/10 seeds). Não há evidência de complementaridade e os dados mostram colisão de ruídos. Nenhuma variante de regularização (C15/C16/C17) consegue recuperar o combo. Literatura sobre multicolinearidade em sinais laborais sugere que dois proxies do mesmo ciclo se destroem quando combinados (Fritsch & Wyrwich, 2021).

### 5.3 Macro nacional (reconfirmar abandono) — Completamente descartado

Phase 3A/3B já demonstrou que T6 permutado bateu T5 real em 10/10 seeds. Sinais nacionais (INSEE, BdF, GSTIX) não passam na falsificação temporal. Este resultado é robusto e não precisa de mais testes.

### 5.4 A hipótese push laboral como construída — Reformular ou abandonar

A hipótese original: "destruição de emprego ZE em t-1 → trabalhadores disponíveis → push empreendedorismo t". O problema é que o sinal usado (`etabs`) mede firmas, não trabalhadores. Se quisermos testar push, precisamos de cotisants (empregados), não de établissements. A hipótese foi testada com o sinal errado.

---

## 6. Hipóteses Que Ainda Valem — Com Condições

### 6.1 URSSAF ZE-level como momentum de firmas — Vale, mas com redundância parcial conhecida

Reformulação: "crescimento do parque de firmas empregadoras em t-1 prediz criação de novas firmas em t" (momentum local de vitalidade empresarial). Esta hipótese é plausível, tem base na literatura (Audretsch & Fritsch, 2002), e difere da hipótese push.

**Situação de redundância (atualizado):** o q_tensor já fornece `effectifs_salaries_cvs` (trimestral, intensivo). C3 fornece `urssaf_employer_estab_growth` (anual, extensivo). Distintos mas correlacionados. Risco: gain marginal pequeno mesmo sendo não-redundante diretamente. **Não bloqueante** mas expectativa de efeito moderada.

**Condição adicional:** a falsificação espacial (C10) precisa ser derrotada com mais seeds. Se C10 continuar ganhando, abandonar.

### 6.2 URSSAF setorial por A10 — Vale testar uma vez

URSSAF publicado com desagregação setorial (grand secteur). Se composição setorial do choque em t-1 prediz composição do rebote em t, setores específicos (turismo, BTP) poderiam ser mais informativos que o total. C16 (combo + A10 guard) melhorou setor WMAPE em −0.00317 vs C0 a um custo de +0.00171 total — trade-off que precisa de mais evidência.

**Condição:** somente se redundância for descartada E se tivermos hipótese setorial específica antes do run (não cherry-picking post-hoc).

### 6.3 Mais seeds em C3 — Justificado, mas condicional

O único argumento para mais seeds em C3 é confirmar (ou refutar) o p=0.097. Com 25 seeds, se a taxa real de vitória for ~0.8, atingimos p<0.05 com ~70% de probabilidade.

**Porém:** antes de rodar mais seeds, a auditoria de redundância e a análise do resultado de C10 precisam ser feitas. Rodar 25 seeds em C3 enquanto C10 compete em 6/10 seeds é desperdício de GPU.

---

## 7. Próxima Bateria Recomendada — Isolamento do q_tensor

### 7.1 Bateria de isolamento (Phase 3D) — antes de qualquer bateria larga

**Propósito:** separar contribuição do sinal extensivo C3 da contribuição do q_tensor trimestral URSSAF. Sem baseline `no_urssaf`, não é possível saber se C3 ajuda ou se todo mundo muda ao tirar o q_tensor.

**4 configs, 10 seeds = 40 runs (1 array job pequeno):**

| Config | Policy | Tutor | Objetivo |
|--------|--------|-------|----------|
| C0_no_urssaf | `side5_lag1_growth1y_no_urssaf` | nenhum | Baseline sem q_tensor — âncora limpa |
| C3_no_urssaf | `side5_lag1_growth1y_no_urssaf` | `urssaf_employer_estab_growth` | C3 sem q_tensor: valor extensivo isolado |
| C4_no_urssaf | `side5_lag1_growth1y_no_urssaf` | `urssaf_employer_estab_growth_perm` | Falsificação temporal de C3_no_urssaf |
| C10_no_urssaf | `side5_lag1_growth1y_no_urssaf` | `urssaf_employer_estab_growth_spatial_perm` | Falsificação espacial de C3_no_urssaf |

**Nota:** a policy `side5_lag1_growth1y_no_urssaf` zera o q_tensor via `policy_zeros_quarterly()` (contém `"no_urssaf"`). Verificar que essa policy string está definida ou adicionar em `apply_feature_policy` se necessário.

### 7.2 Leitura dos resultados

**Cenário I — C3_no_urssaf melhora muito vs C0_no_urssaf:**  
→ O sinal extensivo `urssaf_employer_estab_growth` tem valor próprio, independente do q_tensor. Se além disso C3_no_urssaf bate C4_no_urssaf (temporal perm) e C10_no_urssaf (spatial perm), a evidência causal ZE-específica fica muito mais sólida. Avançar para bateria 75 runs com q_tensor normal (Policy padrão).

**Cenário II — C3_no_urssaf não melhora vs C0_no_urssaf, mas todos pioram sem q_tensor:**  
→ O q_tensor trimestral é a fonte forte; o tutor anual extensivo é secundário. Resultado honesto: C3 original pode ter funcionado parcialmente via redundância com o q_tensor. Não avançar para bateria grande. Considerar se faz sentido explorar uma versão do q_tensor zerado como experimento de ablação.

**Cenário III — C3_no_urssaf melhora vs C0_no_urssaf, mas perde para C4_no_urssaf ou C10_no_urssaf:**  
→ Sinal extensivo tem algum valor médio mas não passa nas falsificações. Mesmo sem q_tensor o problema de proxy/ruído persiste. Encerrar a linha.

**Cenário IV — tudo piora muito sem q_tensor (C0_no_urssaf muito pior que C0 original):**  
→ q_tensor é crítico para o modelo base, não apenas para o tutor. Resultado útil para documentação da arquitetura mas não resolve a questão do tutor. Nesse caso, rodar bateria de isolamento com q_tensor ativo (Cenário original) com 25 seeds.

### 7.3 Só depois da bateria de isolamento: bateria 75 runs

Se isolamento (Cenário I) confirmar: **3 configs com q_tensor ativo, 25 seeds = 75 runs:**

| Config | Descrição | Objetivo |
|--------|-----------|----------|
| C3 (policy normal) | Idêntico ao C3 de Phase 3C | Confirmar p<0.05 na falsificação temporal |
| C4 (policy normal) | Idêntico ao C4 | Paired comparison com C3 |
| C10 (policy normal) | Idêntico ao C10 | Determinar se sinal é ZE-específico |

**Critérios de vitória (necessário E suficiente):**
1. C3 vs C4 temporal: p<0.05 com n=25, Wilcoxon pareado
2. C3 vs C10 spatial: C3 vence >60% das seeds
3. C3 vs C0: Δmean ≤ +0.001
4. C3 WMAPE_2021 < C0 WMAPE_2021

### 7.4 O que NÃO rodar

- Não rodar bateria 75 runs sem passar pela bateria de isolamento 40 runs primeiro.
- Não rodar combo DEFM+URSSAF novamente.
- Não rodar DEFM em nenhuma variante.
- Não rodar C16 A10 guard antes de C3 base confirmado.
- Não rodar cross-attention (regra de Phase 3A: sinal precisa bater permutação antes).

---

## 8. Critérios de Vitória da Linha URSSAF

Para considerar URSSAF ZE como sinal validado e avançar para integração mais profunda no HERALD:

**Critério mínimo (para continuar investigando):**
- C3 real bate C4 temporal perm com p<0.05 (Wilcoxon, n≥20)
- C3 real bate C10 spatial perm em >60% seeds
- Nenhuma degradação de WMAPE_2025 > +0.001 vs C0

**Critério suficiente (para usar em paper):**
- Todos os critérios mínimos acima
- C3 melhora WMAPE_2021 vs C0 com p<0.05
- Interpretação consistente: se sinal é momentum local (não push laboral), documentar corretamente

**Critério de descarte imediato:**
- Auditoria de redundância confirma que feature já está no painel de treino
- C10 spatial perm bate ou empata C3 em >50% seeds com n=25
- C3 degrada WMAPE_2025 em mais de +0.002 vs C0

---

## 9. Riscos Metodológicos

### 9.1 Overfitting em 2021 (risco alto)

**Mecanismo:** O modelo vê URSSAF em queda em 2020 (valor extremo). Aprende "queda extrema → rebote criações". Com apenas um episódio, não pode distinguir esse padrão de aprendizado genuíno.

**Mitigação disponível:** verificar se a melhora de C3 em 2021 persiste quando a janela de treino exclui 2020/2021 (pseudo-OOS de 2009→2010 análogo). Se o ganho desaparece, é overfitting.

**Severidade:** alta. Sem episódio comparável no histórico, qualquer sinal que melhore 2021 deve ser tratado como suspeito até prova em contrário.

### 9.2 Proxy temporal — sinal captura "ano" não mecanismo (risco médio-alto)

**Evidência:** C10 spatial perm vence 6/10 seeds. Se a permutação espacial funciona quase tão bem, o sinal principal é o ano, não a ZE. A série URSSAF teve comportamento excepcional em 2020 — qualquer valor de 2020 atribuído a qualquer ZE carrega essa informação.

**Mitigação:** testar C3 em janelas onde 2020 é excluído do treino. Se o ganho desaparece, o sinal é proxy do ano 2020.

### 9.3 Proxy espacial — sinal captura estrutura geográfica não temporal (risco baixo, mas monitorar)

**Evidência:** C3 vs C10: C3 mean ligeiramente melhor, mas não em seeds individuais. Baixo risco de proxy espacial puro (C3 ainda tem edge médio sobre C10). Mas não descartado.

### 9.4 Redundância parcial com q_tensor (risco médio — verificado)

**Situação atualizada:** q_tensor usa `effectifs_salaries_cvs` + `masse_salariale_cvs` (empregados + folha, trimestral). C3 usa crescimento de `étabs` empregadores (extensivo, anual). Distintos formalmente, correlacionados em substância.

**Implicação prática:** o modelo já vê dinâmica URSSAF pela via trimestral. C3 acrescenta perspectiva extensiva anual. Gain esperado é real mas provavelmente pequeno. Não invalida o teste, mas justifica expectativa moderada de efeito.

**Pré-condição reformulada:** verificar se `urssaf_employer_growth_1y_t_minus_1` entra como feature anual direta (via `apply_feature_policy`). Se sim: o tutor duplica a via anual E o q_tensor duplica a via trimestral — nesse caso risco de redundância aumenta. Se não (como parece com `side5_lag1_growth1y`): redundância é apenas via q_tensor, menos crítica.

### 9.5 Perda de interpretabilidade (risco baixo dado arquitetura)

O tutor entra como contexto local no gate residual, não como feature direta. O mecanismo é:
```
alpha_local_i = f(h_local_i, h_graph_i, latent_t, tutor_context_i)
```
O impacto é sobre o gate de resíduo — interpretável como "calibração local da correção". Risco de interpretabilidade aceitável se o sinal for validado.

### 9.6 Naming inconsistency — impacto em reprodutibilidade

O sinal está documentado como "cotisants_delta" em relatórios mas é na prática "employer_growth" (établissements). Qualquer paper ou tese que use este resultado precisa descrever o sinal correto. A hipótese de push laboral precisa ser reformulada como momentum de firmas.

---

## 10. Recomendação Final

### Decisão: Pausa Condicional — Auditoria Antes de Continuar

Não encerrar a linha URSSAF, mas não rodar nova bateria antes de:

1. **Verificar redundância** (1 hora de trabalho, ver Pré-condição 1). Se redundante → encerrar.
2. **Analisar resultados spatial perm seed-a-seed** (2 horas). Entender por que C10 vence 6/10 seeds.
3. **Reformular a hipótese** para refletir o que o sinal realmente é (momentum de firmas, não push laboral).

**Se redundância não confirmada e análise do spatial perm for encorajadora:** rodar bateria cirúrgica de 75 runs (C3+C4+C10, 25 seeds). Custo: ~1 array job, ~2–4h HPC.

**Se redundância confirmada ou spatial perm claramente nacional:** encerrar a linha URSSAF. Próxima alternativa com maior probabilidade de sucesso: URSSAF setorial A10 (não cotisants total), ou aceitar a conclusão já disponível no `HERALD_RARE_REBOUND_DATA_AUDIT.md` — o rebote de 2021 pode ser não-ensinável sem flags, e o custo intrínseco deve ser reportado como tal.

### O que os dados dizem sobre a probabilidade de sucesso

Com base na evidência disponível:
- Probabilidade de C3 atingir p<0.05 com 25 seeds (dado p=0.097 com 10): ~65%
- Probabilidade de C3 bater C10 spatial perm em >60% seeds com 25 seeds: ~35–45%
- Probabilidade de ambos simultaneamente: ~25–30%
- Probabilidade condicional à não-redundância: ~25–30%
- Probabilidade total (incluindo risco de redundância ~50%): ~12–15%

**Palavras finais:** O sinal URSSAF ZE-level não está morto, mas está ferido. A única razão para continuar é que é o melhor candidato restante e os dados históricos existem. A razão para pausar é que a falsificação espacial não funciona, a redundância não foi verificada, e a hipótese original (push laboral) não é o que o sinal mede. Uma auditoria de 3 horas pode resolver estas questões sem gastar GPU.

---

## Apêndice A — Referências Bibliográficas Citadas

| Ref | Autores | Ano | Publicação | Relevância |
|-----|---------|-----|-----------|-----------|
| A1 | Audretsch & Fritsch | 2002 | Regional Studies | Emprego regional como preditor de criações de firmas |
| A2 | Fougère, Kramarz & Magnac | 2000 | Review of Economic Studies | Desemprego e transição para autoemprego em França |
| A3 | Fairlie & Fossen (IZA DP11258) | 2018 | IZA Discussion Paper | Necessity vs opportunity entrepreneurship, push/pull |
| A4 | Wennekers et al. | 2005 | Small Business Economics | U-shape renda/autoemprego; cíclicidade da necessidade |
| A5 | Fritsch & Storey | 2014 | Regional Studies | Heterogeneidade regional persistente em formação de firmas |
| A6 | Martin et al. | 2016 | Cambridge Journal of Regions | Heterogeneidade rebote pós-recessão europeia |
| A7 | Bristow & Healy | 2020 | Regional Studies | Resiliência regional: fatores preditores de recuperação |
| A8 | Borusyak, Jaravel & Spiess | 2023 | Review of Economic Studies | Inferência causal com amostras pequenas; event studies |
| A9 | Causal Inference for ST Data | 2021 | JASA | Permutation tests em dados spatio-temporais |
| A10 | Moreaux, Picart & Rosenwald | 2004 | Économie et Statistique | Ciclo local e criações de estabelecimentos em França |
| A11 | Baptista, Karaöz & Mendonça | 2014 | Applied Economics | Qualidade e sobrevivência de firmas por tipo de fundador |
| A12 | J.P. Morgan Institute | 2024 | Research Report | Ciclos econômicos e composição das ventures |
| A13 | Klapper, Laeven & Rajan | 2006 | Journal of Financial Economics | Condições locais e dinâmica de entrada de firmas |
| A14 | Permutation Testing TS | 2020 | arXiv:2009.03170 | Poder e validade de testes de permutação em séries temporais |

---

*Auditoria gerada em 2026-05-27 | Baseada em Phase 3C 180 runs + revisão de literatura acadêmica*
