# HERALD — Auditoria de Dados: Rebote Raro e Criação de Estabelecimentos

**Data:** 2026-05-26  
**Contexto:** Phase 3A (Block A): 50/50 runs OK — T6 (macro permutado) venceu T5 (macro real) em 10/10 seeds, todas as métricas. Phase 3B signal screen: 110/110 runs de triagem confirmaram que os sinais reais não apresentam forma temporal causal distinguível. Nenhum dos sinais testados — INSEE climat affaires, INSEE climat emploi, BdF conjoncture services, GSTIX composto — apresentou evidência causal utilizável para prever o rebote de 2021. Decisão: **não avançar para cross-attention**.

**Objetivo desta auditoria:** inventariar variáveis públicas, causais e defensáveis que possam explicar especificamente por que a criação de estabelecimentos acelera após choque econômico (foco: 2021), sem flags manuais.

---

## 0. Diagnóstico Prévio: Por Que 2021 É Difícil

A dificuldade não é técnica — é estrutural. O diagnóstico já estabelecido:

> O Ridge superprevê tanto em 2020 quanto em 2021. Em 2020, a correção correta é **para baixo** (choque). Em 2021, é **para cima ou neutra** (rebote). O modelo aprende com 2020 que "Ridge alto → corrigir para baixo". Em 2021, essa regra está errada.

Para um sinal ser útil, ele precisa distinguir **choque de rebote** sem dizer explicitamente "COVID". Três formas possíveis de fazer isso:

**O que um sinal útil precisaria fazer:**
1. Capturar **recuperação intra-ano em t-1**: não o nível anual de 2020, mas a trajetória dentro de 2020 (ex: Q4 melhor que Q2) → sinal de que a economia já estava se recuperando antes de t
2. Capturar **pressão de saída do emprego**: trabalhadores em chômage partiel ou com contrato rompido em t-1 → pool de potenciais empreendedores disponível em t
3. Capturar **composição setorial local**: quais setores de uma ZE foram destruídos em t-1 e quais estão em recuperação → determina heterogeneidade do rebote entre ZEs

**Risco central:** qualquer variável que seja extrema em 2020 e normal em outros anos é essencialmente um flag COVID contínuo disfarçado. A pergunta é se existe uma série que varia continuamente ao longo do histórico (incluindo crises menores de 2009, 2012) de modo que o modelo possa aprender a relação sem overfitting ao caso 2020.

---

## 1. Tabela de Candidatos — Visão Completa

Legenda de colunas:
- **Lag op.**: dados disponíveis antes ou no início do ano t previsto
- **Hist.**: cobertura histórica suficiente antes de 2021 (mínimo 2009)
- **Hipótese**: mecanismo causal plausível para criação de estabelecimentos
- **Granular.**: N=nacional, R=região, D=département, ZE=zone d'emploi, S=setor A10
- **Sep. 2020/2021**: o sinal distingue os dois anos com valores diferentes (não binário)
- **Rebote ≠ crise**: captura especificamente rebote, não só deterioração
- **Flag disfarçado**: risco de ser indicador COVID binário sob forma contínua
- **Proxy temporal**: risco de capturar apenas "ano" em vez de mecanismo
- **Veredicto**: usar / testar / descartar

---

### Bloco 1 — Empreendedorismo / Autoempresário

| # | Variável | Fonte | URL | Freq. | Granul. | Anos dispon. | Lag op. | Hist. | Hipótese clara | Sep. 2020/2021 | Rebote ≠ crise | Flag disfarçado | Proxy temporal | Custo integração | Veredicto |
|---|----------|-------|-----|-------|---------|-------------|---------|-------|----------------|---------------|---------------|----------------|----------------|------------------|-----------|
| 1.1 | **Criações por forma jurídica — share micro-entrepreneur** | INSEE SIDE | https://www.insee.fr/fr/statistiques/series/102687958 | Mensal | N, S parcial | 2007–pres. | t-1 anual | ✓ | Alta: labor market push → ME fácil de abrir | Sim (ME share subiu 2021) | Parcial | Baixo | Médio | Baixo (SIDE já carregado) | **Testar** |
| 1.2 | **Criações por NAF A88 → agregadas A10** | INSEE SIDE | https://www.insee.fr/fr/statistiques/series/102687958 | Mensal | N, S | 2007–pres. | t-1 anual | ✓ | Composição setorial de t-1 como preditor de composição t | Sim | Sim (turismo/deliver) | Baixo | Baixo | Baixo (já disponível) | **Usar (verificar se já em features)** |
| 1.3 | **Créations par département** | INSEE SIRENE | https://www.data.gouv.fr/fr/datasets/base-sirene-des-entreprises-et-de-leurs-etablissements-siren-siret/ | Mensal | D | 2007–pres. | t-1 anual | ✓ | Variação territorial prévia | Sim | Parcial | Baixo | Médio | Alto (aggregation ZE→dept complexa) | **Descartar (dept ≠ ZE2020)** |
| 1.4 | Dados APCE/Bpifrance históricos | Bpifrance | Não público completo | Irregular | N | Fragmentado | Incerto | ✗ | — | — | — | — | — | Alto | **Descartar** |
| 1.5 | **Taux de pérennité des entreprises** | INSEE | https://www.insee.fr/fr/statistiques/2015399 | Anual | N, S | 2010–pres. | t-2 a t-3 | Parcial | Sobrevivência t-3 → qualidade criações | Não | Não | Baixo | Alto | Médio | **Descartar (lag longo, proxy temporal)** |

---

### Bloco 2 — Mercado de Trabalho / Push Factor

| # | Variável | Fonte | URL | Freq. | Granul. | Anos dispon. | Lag op. | Hist. | Hipótese clara | Sep. 2020/2021 | Rebote ≠ crise | Flag disfarçado | Proxy temporal | Custo integração | Veredicto |
|---|----------|-------|-----|-------|---------|-------------|---------|-------|----------------|---------------|---------------|----------------|----------------|------------------|-----------|
| 2.1 | **DEFM catégorie A — nível anual por ZE** | France Travail (ex-Pôle Emploi) | https://www.francetravail.org/statistiques-analyses/demandeurs-demploi.html | Mensal | ZE (ZE2010→ZE2020, reconstrução necessária) | 2001–pres. | t-1 anual | ✓ | Desemprego alto t-1 → push necessity entrepreneurship em t | Sim (pico 2020) | **Baixo**: nível alto historicamente prediz criação baixa; efeito push opera na margem | Baixo | Médio | Médio (verificar alinhamento ZE2020) | **Testar (variante de nível — hipótese fraca)** |
| 2.2 | **DEFM — variação anual t-1 vs t-2 por ZE** | France Travail | mesma | Mensal | ZE | 2001–pres. | t-1 | ✓ | Queda de DEFM t-1 = recuperação → criação t mais alta | **Sim (DEFM começa cair Q3/2020)** | **Maior que nível** | Baixo | Baixo | Médio | **Testar — prioridade média** |
| 2.2b | **DEFM — recuperação intra-ano: H2/H1 ou Q4/Q2 de t-1** | France Travail | mesma | Mensal | ZE | 2001–pres. | t-1 | ✓ | Recuperação dentro do próprio t-1 = sinal forward de rebote | **Sim (forte em 2020: Q4 >> Q2)** | **Melhor candidato** | **Baixo** | Baixo | Médio | **Testar — prioridade alta (captura recuperação intra-ano)** |
| 2.3 | **Activité partielle — heures consommées** | DARES | https://dares.travail-emploi.gouv.fr/donnees/l-activite-partielle | Mensal | N, S (A88 parcial) | 2008–pres. | t-1 anual | ✓ | Pico AP em 2020 → trabalhadores em AP planejam saída → criações 2021 | **Sim (2020=extremo)** | **Sim: saída do AP → AE/ME** | **Médio (pico 2020 é quase binário)** | Médio | Médio | **Testar (mas risco flag alto)** |
| 2.4 | **AP — taxa de saída / fim de contrato pós-AP** | DARES | mesma | Mensal | N, S | 2020–pres. | parcial | ✗ (sem histórico pré-2020 relevante) | — | — | — | Alto | — | Alto | **Descartar (sem histórico)** |
| 2.5 | **Ruptures conventionnelles homologuées** | DARES | https://dares.travail-emploi.gouv.fr/donnees/les-ruptures-conventionnelles | Trim. | N, R | 2008–pres. | t-1 | ✓ | RC = saída amigável → frequentemente precede criação empresa | Sim (queda 2020, rebote 2021) | **Sim: rebote RC > choque** | Baixo | Baixo | Médio | **Testar** |
| 2.6 | **Cotisants URSSAF (emprego assalariado) par ZE** | URSSAF Open Data | https://open.urssaf.fr/explore/?sort=modified | Trim. | ZE, S (A38/A88) | 2009–pres. | t-1 trim. | ✓ | Queda emprego t-1 → criação t (push) | Sim (queda 2020 Q2, rebote 2021) | Médio | Baixo | Médio | Médio-Alto (A10 aggregation) | **Testar (ZE!!)** |
| 2.7 | Licenciements économiques | DARES | https://dares.travail-emploi.gouv.fr/ | Trim. | N, R | 2005–pres. | t-1 | ✓ | Licenciamento t-1 → desemprego → push criação | Sim (2020 alto) | Baixo (correlação histórica negativa) | Médio | Médio | Médio | **Descartar (proxy temporal + sinal ambíguo)** |
| 2.8 | Transitions emploi→non-emploi (enquête emploi) | INSEE | https://www.insee.fr/fr/statistiques/series/001694063 | Anual | N | 2003–pres. | t-1, lag ~12m | ✓ | Transição direta para conta própria | Parcial | Parcial | Baixo | Médio | Alto (série curta, lag) | **Descartar** |

---

### Bloco 3 — Apoio Público / Amortecedor COVID

| # | Variável | Fonte | URL | Freq. | Granul. | Anos dispon. | Lag op. | Hist. | Hipótese clara | Sep. 2020/2021 | Flag disfarçado | Veredicto |
|---|----------|-------|-----|-------|---------|-------------|---------|-------|----------------|---------------|----------------|-----------|
| 3.1 | **PGE — encours accordés** | Banque de France | https://www.banque-france.fr/statistiques/credit/financement-de-leconomie | Mensal | N (S limitado) | 2020–pres. | t-1 | **✗ (zero pré-2020)** | — | Sim (binário na prática) | **Alto: É um indicador COVID** | **Descartar** |
| 3.2 | Fonds de solidarité | DGFiP | https://www.impots.gouv.fr/professionnel/le-fonds-de-solidarite | Mensal | N, S, D (parcial) | 2020–2022 | — | ✗ | — | Sim (binário) | **Alto** | **Descartar** |
| 3.3 | Crédit trésorerie total entreprises | BdF Webstat | https://webstat.banque-france.fr/ | Mensal | N, S | 2003–pres. | t-1 | ✓ | Trésorerie disponível → criação mais fácil | Parcial (PGE distorce) | Médio (2020 distorção PGE) | **Descartar (contaminado por PGE)** |

---

### Bloco 4 — Crédito e Financiamento PME

| # | Variável | Fonte | URL | Freq. | Granul. | Anos dispon. | Lag op. | Hist. | Hipótese clara | Sep. 2020/2021 | Flag disfarçado | Proxy temporal | Custo | Veredicto |
|---|----------|-------|-----|-------|---------|-------------|---------|-------|----------------|---------------|----------------|----------------|-------|-----------|
| 4.1 | **Crédit aux PME — encours** | BdF Webstat | https://webstat.banque-france.fr/ | Mensal | N (R limitado) | 2006–pres. | t-1 | ✓ | Crédito disponível t-1 → capital inicial disponível | Parcial (2020: distorcido por PGE) | Médio | Baixo | Médio | **Descartar (PGE distorce 2020; sem granularidade ZE)** |
| 4.2 | **Taux de refus crédit PME (enquête BdF)** | BdF | https://www.banque-france.fr/statistiques/monetaire-et-financier/credit | Trim. | N, R | 2012–pres. | t-1 | ✓ | Alta recusa → barreira criação; baixa recusa → facilita | Sim | Sim (refus caiu pós-2021) | Baixo | Baixo | Médio | **Testar** |
| 4.3 | Taux crédit moyen nouveaux emprunts | BdF Webstat | mesma | Mensal | N | 2003–pres. | t-1 | ✓ | Taxa baixa → capital acessível → criação | Parcial | Baixo | Médio (tendência) | Médio | **Descartar (tendência secular domina)** |
| 4.4 | SAFE France (BCE) | BCE / BdF | https://www.ecb.europa.eu/stats/ecb_surveys/safe/html/index.en.html | Semestral | N | 2009–pres. | t-1 | ✓ | Percepção acesso crédito | Parcial | Baixo | Baixo | Alto (BCE, não ZE) | **Descartar (granularidade insuficiente)** |

---

### Bloco 5 — Heterogeneidade Setorial

| # | Variável | Fonte | URL | Freq. | Granul. | Anos dispon. | Lag op. | Hist. | Hipótese clara | Sep. 2020/2021 | Rebote ≠ crise | Flag disfarçado | Custo | Veredicto |
|---|----------|-------|-----|-------|---------|-------------|---------|-------|----------------|---------------|---------------|----------------|-------|-----------|
| 5.1 | **IPI Industrie Manufacturière par secteur** | INSEE | https://www.insee.fr/fr/statistiques/series/001745504 | Mensal | N, S (A21) | 1990–pres. | t-1 | ✓ | Produção industrial t-1 → criação estabelecimentos industriais | Sim | Parcial | Baixo | Baixo | Médio | **Testar (limitado a industria)** |
| 5.2 | **Permis de construire** | SDES/MTES | https://www.statistiques.developpement-durable.gouv.fr/permis-de-construire | Mensal | D, commune | 2007–pres. | t-1 | ✓ | Permis t-1 → criação BTP em t | Sim (2020 queda, 2021 rebote forte) | **Sim (forte em BTP)** | Baixo | Baixo | Médio (aggregação ZE→D) | **Testar (setor BTP)** |
| 5.3 | **Nuitées hôtelières par département** | INSEE/DGE | https://www.data.gouv.fr/fr/datasets/frequentation-des-hebergements-touristiques/ | Mensal | D | 2014–pres. | t-1 | Parcial (2014) | Turismo t-1 → criações em hébergement-restauration t | Sim (colapso 2020, rebote 2021) | Sim | Baixo | Baixo | Médio | **Testar (setor I)** |
| 5.4 | VAB setorial (comptes trimestriels) | INSEE | https://www.insee.fr/fr/statistiques/series/001564262 | Trim. | N, S A10 | 1995–pres. | t-1 | ✓ | VAB setorial t-1 → criação setorial t | Sim | Médio | Baixo | Médio (lag publ. ~6m) | Médio | **Testar** |
| 5.5 | Indice production BTP | INSEE | https://www.insee.fr/fr/statistiques/series/001745508 | Mensal | N | 1990–pres. | t-1 | ✓ | BTP t-1 → criação setor F | Sim | Sim | Baixo | Baixo | Baixo | **Testar** |
| 5.6 | E-commerce (FEVAD/Eurostat) | FEVAD / Eurostat | Parcialmente público | Anual | N | 2006–pres. | t-1, lag ~12m | ✓ | Crescimento e-commerce → criações delivery/logística | Sim | **Sim (2021 explodiu)** | Baixo | Médio (fonte FEVAD, não oficial) | Alto | **Descartar (fonte não oficial)** |

---

### Bloco 6 — Mobilidade / Atividade Local

| # | Variável | Fonte | URL | Freq. | Granul. | Anos dispon. | Lag op. | Hist. | Flag disfarçado | Custo | Veredicto |
|---|----------|-------|-----|-------|---------|-------------|---------|-------|----------------|-------|-----------|
| 6.1 | Google/Apple mobility | Google/Apple | Não oficial | Diária | Município | 2020–2022 | — | **✗ (2020 apenas)** | Médio | Alto | **Descartar (sem histórico)** |
| 6.2 | Trafic voyageurs SNCF | SNCF Open Data | https://ressources.data.sncf.com | Mensal | Gare | 2015–pres. | t-1 | Parcial | Baixo | Alto (não ZE) | **Descartar (granularidade inadequada)** |
| 6.3 | Fréquentation touristique Atout France | Atout France | Não histórico público completo | Anual | R | 2010–pres. | t-1 | ✓ | Baixo | Alto | **Descartar (já coberto por nuitées)** |

---

## 2. Ranking dos 10 Melhores Candidatos

Critério de ranking: combinação de (a) hipótese causal forte, (b) granularidade útil para HERALD, (c) cobertura histórica suficiente, (d) separação 2020 vs 2021, (e) baixo risco de flag disfarçado.

| Rank | Variável | Hipótese Central | Granularidade Chave | Risco Metodológico Principal |
|------|----------|-----------------|--------------------|-----------------------------|
| **1** | DEFM por ZE — recuperação intra-ano (H2/H1 t-1) | Recuperação dentro de 2020 = sinal forward de rebote local | **ZE** | Alinhamento ZE2010→ZE2020; relação pode não generalizar além de 2021 |
| **2** | Cotisants URSSAF por ZE — variação t-1 vs t-2 | Destruição emprego territorial t-1 → pool push criação t | **ZE, S parcial** | Correlação histórica negativa domina; push opera na margem; verificar pré-2015 |
| **3** | DEFM por ZE — variação anual t-1 vs t-2 | Queda desemprego t-1 = recuperação → criação t mais alta | **ZE** | Correlação invertida; variação melhora vs nível mas mesma estrutura |
| **4** | Activité partielle — heures consommées t-1 | Pico AP em 2020 → trabalhadores em standby → saída como AE em t | N, S | Muito extremo em 2020; risco de flag quase-binário; nacional |
| **5** | Ruptures conventionnelles — variação t-1 | RC rebotam antes de criações; transição intencional emprego→AE | N, R | **Nacional**: não cria heterogeneidade ZE; contexto global apenas |
| **6** | Permis de construire par département | Atividade BTP t-1 → criações setor F em t | D (→ ZE) | Mismatch géographique D→ZE2020; efeito setor-específico (F) |
| **7** | Taux refus crédit PME (BdF) | Acesso crédito t-1 → criação empresas t | N (R parcial) | Sem granularidade ZE; série desde 2012 apenas |
| **8** | Nuitées hôtelières par département | Turismo t-1 → criações hébergement-restauration | D (→ ZE) | Só desde 2014; rebote setor-específico (I) |
| **9** | Share micro-entrepreneur t-1 (SIDE composição) | Alta proporção ME = labor push presente → prediz aceleração | N, S (SIDE já disponível) | Verificar se já está em features SIDE; auto-correlação forte |
| **10** | VAB setorial (comptes trim.) | VAB setorial baixo t-1 → rebote criações setoriais t | N, S A10 | Nacional; lag publicação ~6m; relação não-linear fraca |

---

## 3. Análise Crítica dos Candidatos Principais — Por Que São Candidatos, Não Certezas

### 3.1 DEFM por ZE — Direção da Variação

**O que motiva:** A taxa de queda do desemprego no segundo semestre de 2020 (DEFM caindo desde setembro 2020 em muitas ZEs) poderia sinalizar recuperação local antes de se ver no total de criações. Uma ZE onde o DEFM caiu rapidamente em 2020 H2 pode ter rebotado mais forte em 2021 criações.

**Por que não é certeza:**
- Correlação histórica DEFM × criação é **negativa** em anos normais (mais desemprego → menos criação). Em anos de rebote, a direção pode inverter, mas o modelo precisa aprender essa não-linearidade com um único episódio de treino (2009 foi diferente em natureza e menor em magnitude).
- Alinhamento ZE2020: France Travail publicou séries por ZE2020 apenas a partir de 2022-2023. Reconstrução histórica ZE2010→ZE2020 por correspondência geográfica está disponível mas com incerteza.
- O mecanismo é "push de necessidade" (unemployment → ME/AE), que funciona melhor para criar microempresas fáceis, não para prever o **volume total** que inclui criações de capital mais elevado.

**Risco de permutação:** Se o sinal fosse embaralhado temporalmente, o modelo veria outro ano com DEFM caindo (ex: 2017 ou 2015) e não criaria confusão análoga ao 2021. Isso é **favorável** à falsificação: o sinal temporal real deve ganhar. Mas ainda precisa testar.

### 3.2 Activité Partielle

**O que motiva:** activité partielle mede trabalhadores mantidos em vínculo formal, mas com atividade reduzida. Em 2020, isso pode representar uma reserva de trabalhadores em transição: parte volta ao emprego normal, parte muda de trajetória e pode abrir atividade própria em 2021. Por isso, AP é um candidato para capturar pressão de saída laboral sem usar uma flag manual.

**Por que não é certeza:**
- O valor de 2020 é extremo, quase binário. Há risco real de virar um proxy de COVID, não um mecanismo geral.
- A série é nacional/setorial, não ZE-level. Sozinha não cria heterogeneidade espacial; precisa entrar como contexto, não como regra global.
- O modelo precisa mostrar que AP real vence AP permutado. Sem isso, não há evidência causal aproveitável.

### 3.3 Cotisants URSSAF por ZE

**O que motiva:** Variação de cotisants = criação/destruição de emprego formal. Queda cotisants em ZE i em 2020 → trabalhadores disponíveis → push criação em 2021. ZE-level. Disponível via open.urssaf.fr.

**Distinção do uso anterior de URSSAF no projeto:** URSSAF foi integrado antes como painel de features de emprego para previsão direta. A novidade aqui é diferente: usar **Δcotisants ZE como tutor local no gate de resíduo** — o sinal não entra como feature de previsão mas como contexto de calibração local. Verificar antes do treino se essa variação está ou não presente nas features atuais do painel; se estiver, o ganho seria nulo por duplicidade.

**Por que não é certeza:**
- Queda cotisants ZE × criações ZE: correlação histórica provavelmente negativa (ZE com mais destruição de emprego são geralmente deprimidas → menos criações). O efeito push opera em margem, não como relação dominante.
- Lag de publicação: ~3 meses (trimestral). Para prever 2021, precisa cotisants 2020 completo, disponível no início de 2021. Operacionalmente OK.
- Agregação setorial para A10 é possível (URSSAF publica por grand secteur) mas complica integração.

---

## 4. Lista de Descartados com Justificativa

| Variável | Razão de Descarte |
|----------|------------------|
| PGE encours | Zero fora de 2020–2022 → flag binário COVID |
| Fonds de solidarité | Zero fora de 2020–2022 + dados públicos incompletos |
| Crédit trésorerie entreprises | Distorcido por PGE em 2020; sem separação ZE |
| Taux crédit moyen | Tendência secular domina sinal cíclico |
| SAFE (BCE) | Semestral, nacional, sem histórico ZE |
| Transitions emploi→non-emploi | Lag longo; série nacional; histórico inadequado |
| Taux de pérennité | Lag 2–3 anos; proxy temporal não causal |
| Créations par département | Dept ≠ ZE2020; sem benefício sobre SIDE já disponível |
| APCE/Bpifrance | Dados históricos incompletos/não públicos |
| Activité partielle — saída pós-AP | Série existe apenas 2020+; sem histórico |
| Licenciements économiques | Correlação negativa histórica; proxy temporal |
| Google/Apple mobility | Sem histórico pré-2020; fonte não oficial |
| Trafic SNCF | Granularidade inadequada para ZE |
| E-commerce FEVAD | Fonte não oficial; lag longo |
| Atout France tourisme | Coberto por nuitées; série pública incompleta |
| VAB setorial | Nacional apenas; lag publicação; relação não-linear fraca |
| IPI | Nacional; limitado a industria (setor B/C, irrelevante para maioria de ZEs terciárias) |

---

## 5. Top 3 Para Próxima Bateria

### Candidato A — DEFM por ZE, recuperação intra-ano: *Δ intra-t-1 por ZE*
- **Construção:** Para cada ZE, razão H2/H1 ou Q4/Q2 de DEFM catA no ano t-1. Captura recuperação dentro do próprio t-1, não só o nível anual. Variante adicional: variação anual t-1 vs t-2.
- **Fonte:** France Travail statistiques par ZE (https://www.francetravail.org/statistiques-analyses/demandeurs-demploi.html). Reconstrução histórica ZE2010→ZE2020 necessária.
- **Pré-requisito:** Verificar disponibilidade de série mensal por ZE2020 com cobertura 2009–2019 antes de qualquer run. Um alinhamento incorreto é silencioso e contamina todos os resultados.
- **Por que está no top 3:** Único sinal ZE-level de labor market não testado. Hipótese concreta (recuperação local visível antes de rebote de criações). Distinto dos macros nacionais descartados em 3A/3B.

### Candidato B — Cotisants URSSAF por ZE (variação): *destruição de emprego territorial*
- **Construção:** Para cada ZE, variação cotisants t-1 vs t-2 em % — especificamente a variação negativa (destruição), não o nível. Já foi testado URSSAF no projeto em contexto diferente (features de emprego no painel geral); a novidade aqui é usar a **variação causal trimestral/anual como tutor local para o gate de resíduo**, não como feature de previsão direta.
- **Fonte:** open.urssaf.fr — https://open.urssaf.fr/explore/ (séries trimestrais por ZE, disponíveis desde ~2009)
- **Distinção do uso anterior:** Não é URSSAF genérico no painel. É Δcotisants ZE como contexto local para calibração do resíduo HERALD. Verificar que não é redundante com features existentes antes de rodar.
- **Por que está no top 3:** ZE-level, histórico inclui 2009, hipótese de push laboral clara e diferente dos sinais de clima.

### Candidato C — Activité partielle heures consommées (nacional): *pressão de saída laboral*
- **Construção:** Soma anual de heures consommées t-1, normalizada pela média histórica (ex: AP_t-1 / mean(AP_2009:t-2)). Variante: taxa de queda em 2020 H2 vs pico 2020 H1 (captura a saída do AP).
- **Fonte:** DARES — https://dares.travail-emploi.gouv.fr/donnees/l-activite-partielle (mensal, desde 2008)
- **Risco explícito:** A variável é quasi-binária — valor 2020 é 20–50× o histórico. O modelo pode aprender "AP extremo → criação alta" sem mecanismo causal. Testar via permutação é obrigatório; se permutado ganhar, descartar imediatamente.
- **Por que está no top 3 (não ruptures conventionnelles):** AP tem hipótese push mais direta (trabalhadores em standby → saída → AE) e série mais longa que RC. RC é nacional sem ZE e parcialmente concurrent ao target — rebaixado para contexto global opcional.

---

## 6. Proposta Phase 3C

### 6.1 Hipótese Central
*Sinal de mercado de trabalho territorial (destruição/recuperação de emprego) em t-1 fornece contexto causal local para o gate de resíduo, melhorando a predição de rebotes raros.*

### 6.2 Configs Propostas

| Config | Descrição | Sinal | Entrada |
|--------|-----------|-------|---------|
| **C0** | Baseline T0 — HERALD no-flags (controle) | Nenhum | — |
| **C1** | DEFM ZE recuperação intra-ano como contexto ZE-local | DEFM H2/H1 t-1 por ZE | ZE-level gate context |
| **C2** | Falsificação C1 (permuta temporal) | DEFM shuffle por ZE | ZE-level gate context |
| **C3** | URSSAF cotisants ZE variação como contexto ZE-local | Δ cotisants ZE t-1 vs t-2 | ZE-level gate context |
| **C4** | Falsificação C3 | Cotisants permutado por ZE | ZE-level gate context |
| **C5** | Activité partielle heures t-1 como contexto global | AP normalizado nacional t-1 | Gate context global |
| **C6** | Falsificação C5 | AP permutado | Gate context global |

**Número de runs:** 7 configs × 10 seeds = 70 runs.  
Se GPU limitado: priorizar C0, C1, C2, C3, C4 (50 runs — foco ZE-level).  
**Pré-condição:** não iniciar C1/C2 e C3/C4 sem confirmar disponibilidade das séries por ZE2020 com cobertura 2009–2019.

### 6.3 Controles Permutados

Para C1, C2: permutação shufflea os anos de DEFM, preservando estrutura cross-ZE (permuta temporal, não espacial). Assim C2 vê o vetor espacial de DEFM mas em ano errado → testa se é o conteúdo temporal que importa.

Para C3, C4: permutação shufflea os anos da série URSSAF por ZE, preservando a estrutura cross-ZE de cada ano (permuta temporal, não espacial). Assim C4 mantém o padrão territorial de cotisants, mas no ano errado.

Para C5, C6: como AP é sinal global, a permutação shufflea os anos da série nacional.

### 6.4 Métricas e Critérios de Vitória

**Critério primário (necessário):**
- Cx (sinal real) WMAPE_mean < Cx+1 (permutado) com p<0.05 (Wilcoxon pareado)

**Critério secundário (suficiente para avançar):**
- Cx WMAPE_2021 < C0 WMAPE_2021 com p<0.05

**Critério de descarte automático:**
- Cx WMAPE_mean ≥ C0 WMAPE_mean (regride vs baseline)

**Guard rail:**
- Cx WMAPE_2025 não pode exceder C0 WMAPE_2025 em mais de 0.003

### 6.5 Riscos Metodológicos

1. **Reconstrução histórica ZE2010→ZE2020:** France Travail publicou séries por ZE2020 com reconstrução parcial. Antes de treinar C1/C2, verificar que o alinhamento está correto para anos 2009–2019. Um mapeamento incorreto introduz ruído que pode fazer C2 ganhar de C1 artificialmente.

2. **Correlação invertida em contexto de rebote:** A relação DEFM→criação é negativa em anos normais e possivelmente positiva em rebotes. O modelo pode não aprender essa não-linearidade de uma única instância (2020→2021). Isso não é um bug de dado — é uma limitação fundamental de amostras raras.

3. **N=1 de rebound severo no histórico:** 2021 é o único rebote de magnitude equivalente na série disponível. O modelo não pode aprender de outros episódios comparáveis. Qualquer sinal que melhore 2021 pode ser overfitting ao episódio específico. Verificar robustez em 2009→2010 como pseudo-out-of-sample.

4. **Risco de proxy temporal:** Se DEFM ou cotisants tiveram tendência de queda 2010–2019, o modelo pode aprender "ano mais recente = DEFM menor = mais criações" sem mecanismo causal. Testar removendo tendência antes de usar como feature.

5. **Dados URSSAF:** open.urssaf.fr tem dados desde ~2009, mas qualidade da série pré-2015 por ZE varia. Verificar continuidade metodológica antes de treinar.

---

## 7. Conclusão Honesta

**Pergunta central:** *Existe algum dado público, com histórico anual/mensal e lag operacional plausível, que ajude a explicar por que a criação de estabelecimentos sobe após choque econômico, especificamente 2021, sem flags manuais?*

**Resposta:** *Motiva exploração adicional, mas não sustenta expectativa de sucesso.*

Os candidatos identificados (DEFM por ZE — recuperação intra-ano, cotisants URSSAF ZE, activité partielle) têm hipóteses econômicas defensáveis e cobertura histórica suficiente. Nenhum deles foi testado na arquitetura HERALD. Vale testar bateria de 50–70 runs, **condicionada** à confirmação prévia de disponibilidade real das séries DEFM e URSSAF por ZE2020 em vintage causal.

No entanto, três restrições estruturais reduzem significativamente a probabilidade de sucesso:

**1. Problema de sinal invertido.** Os melhores candidatos (desemprego alto, destruição emprego) são negativamente correlacionados com criação de estabelecimentos em anos normais. O efeito push de rebote existe na literatura, mas opera em margem e pode ser domado pela correlação histórica dominante. O modelo dificilmente aprenderá a inverter o sinal para 2021 especificamente sem overfitting.

**2. N=1 de rebote severo.** Com apenas um episódio de rebote pós-choque severo na série de treino (2021), qualquer variável que se adapte bem a 2021 é suspeita de memorizar o episódio. A única forma de distinguir aprendizado de memorização seria ter outro rebote de magnitude comparável nos dados — o que não existe.

**3. Natureza composta do rebote.** O pico de 2021 foi resultado de pelo menos cinco forças simultâneas: pent-up demand pós-lockdown, labor push de chômage partiel, digital boom, BTP aquecido e recuperação de turismo. Nenhuma série única captura essa composição. Sinais setoriais separados (permis de construire para BTP, nuitées para turismo) podem melhorar previsão **setorial** mais do que o total, o que é interessante mas diferente do problema central.

**Se Phase 3C falhar como 3A/3B:** a conclusão operacional seria que o rebote de 2021 é um evento não-ensinável por dados públicos disponíveis sem flags manuais. A melhor abordagem seria reportar a distribuição completa por seed (não selecionar a melhor seed post-hoc, que é seleção não-defensável), considerar um ensemble pré-definido por critério operacional (ex: mediana das 10 seeds), e aceitar erro mais alto em 2021 como custo intrínseco da robustez temporal.

**Não propor cross-attention enquanto nenhum sinal vencer sua permutação.**

---

*Auditoria manual — 2026-05-26 | Baseada em fontes públicas INSEE, DARES, France Travail, URSSAF, Banque de France*
