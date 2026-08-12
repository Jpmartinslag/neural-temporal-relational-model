# HERALD 90 — identificação relacional por sinais económicos complementares

**Registo:** DEC-127. Sucede ao `STOP` do HERALD 89, que **não** é reinterpretado como
sucesso.
**Âmbito:** 280 ZE2020 atuais, sem Córsega.

## 0. Honestidade sobre a ordem de escrita

A Etapa 1 (auditoria dos sinais reais e torneio barato) **foi executada antes** deste
documento existir, porque é um probe NumPy de segundos e porque o seu resultado decide se
as etapas seguintes chegam a ser escritas. A Etapa 1 é portanto **exploratória**, e está
assim marcada em todo o relatório.

As Etapas 2 a 4 são pré-registadas: a spec fixa-as antes de qualquer gerador, oráculo ou
rede ser escrito. O gate de direção usado na Etapa 1 (`≥ 4/5 seeds`) veio do enunciado da
tarefa, não de mim, e foi aplicado sem alteração. Onde duas agregações razoáveis discordam,
**ambas são reportadas**, nunca só a favorável.

## 1. Pergunta científica

O HERALD 89 estabeleceu que criações anuais de estabelecimentos, isoladamente, não
identificam relações entre territórios: nem um oráculo que conhece o grafo verdadeiro o
distingue de um grafo baralhado. A pergunta desta etapa é outra:

> Informação passada da zona A, medida em indicadores laborais densos, acrescenta poder
> preditivo à evolução futura da zona B, para além da própria história de B e das
> tendências económicas gerais — e faz isso ao longo do commuting observado?

Linguagem admitida: **associação, precedência temporal, impacto preditivo, relação
territorial estimada**. Nunca causalidade estrutural.

## 2. Sinais candidatos

| sinal | fonte | frequência | papel |
|---|---|---|---|
| efetivos assalariados privados | Urssaf | trimestral | candidato |
| massa salarial | Urssaf | trimestral | candidato, correlacionado com o anterior |
| estabelecimentos empregadores | Urssaf | anual | candidato |
| taxa de desemprego localizada | Insee | trimestral | candidato |
| criações de estabelecimentos | Insee SIDE | anual | auxiliar e alvo económico posterior |

**Emprego e massa salarial são redundantes por construção.** Nenhum resultado conjunto
conta os dois como provas independentes: a Etapa 5 mede contribuição **incremental** e
inclui um braço com um sinal deliberadamente duplicado, cujo ganho tem de ser
substancialmente inferior ao de acrescentar um sinal diferente.

## 3. Unidade temporal e folds

Frequência canónica escolhida **após** medir cobertura: trimestral para emprego, salários e
desemprego; anual para estabelecimentos e criações. Sinais anuais entram como estado
conhecido, repetido apenas depois da publicação, nunca retroativamente. Criações não são
convertidas artificialmente em trimestres.

Rolling one-step-ahead. Para cada origem, treino em todos os passos estritamente
anteriores; o passo pontuado é avaliado uma vez. Nenhum hiperparâmetro é refeito no passo
pontuado.

## 4. Seeds

| papel | seeds |
|---|---|
| torneio da Etapa 1 (permutações e grafos aleatórios) | **9001–9005** |
| desenvolvimento e calibração das Etapas 2–3 | **9101–9120** |
| avaliação final das Etapas 3–4 | **9201–9205** |

Conjuntos disjuntos e novos. As cinco seeds finais intocadas do HERALD 89 (8901–8905)
**não** são reutilizadas: pertencem a outro instrumento e a outra verdade, e reaproveitá-las
misturaria dois pré-registos.

## 5. Controles

Cada braço com vizinhos é comparado, nos mesmos folds, contra:

- **B0** baseline local: história própria, variação própria, média nacional, sazonalidade,
  indicadores das quebras metodológicas conhecidas;
- **B1** baseline + commuting observado;
- **B2** baseline + commuting com identidades permutadas por derangement fixo;
- **B3** baseline + vizinhos aleatórios com o mesmo grau e o mesmo multiconjunto de pesos
  por linha;
- **B4** baseline com apenas a informação agregada.

**A média nacional está no B0.** Nenhum placebo pode ganhar por introduzir agregação que a
base não tenha.

Quebras metodológicas — Urssaf 2021 (DSN individual) e 2023 (aprendizes), Insee 2018T1
(extensão de campo), choque comum 2020–2021 — entram como regressores de perturbação. Nunca
são lidas como dinâmica territorial.

## 6. Métricas e gate de direção

Reporta-se distribuição, não apenas média: ganho por fold, mediana, quartis, proporção
favorável, por ano e por seed.

Um sinal é **RELATION_INFORMATIVE** apenas se, cumulativamente:

1. o commuting observado supera o permutado;
2. supera também os vizinhos aleatórios com grau igualado;
3. supera o baseline local;
4. a direção é favorável em **≥ 4/5 seeds** (agregação por seed, mediana dos seus folds);
5. o ganho não se concentra numa única origem temporal.

Nenhum ganho mínimo grande é fixado à partida. O critério é **direção e consistência**.

## 7. Ordem das etapas e autorizações

```
Etapa 1  auditoria dos sinais reais + torneio barato   -> authorises_multisignal_oracle
Etapa 2  gerador sintético multissinal + oráculos      -> authorises_neural_synthetic
Etapa 3  arquitetura multissinal no sintético          -> authorises_french_diagnostic
Etapa 4  aplicação diagnóstica ao painel francês
```

Cada etapa emite um booleano explícito. Uma etapa não autorizada **não é escrita nem
submetida**.

`authorises_multisignal_oracle` exige **≥ 2 sinais RELATION_INFORMATIVE**. Com exatamente
um, a hipótese multissinal fica sem base e o que resta é uma linha de sinal único, que é um
resultado diferente e tem de ser declarado como tal.

## 8. Gates das etapas seguintes, congelados aqui

Sintético com verdade conhecida: `edge F1 ≥ 0,50`; `dense correlation ≥ 0,30`; `event F1`
tipado `≥ 0,30`; estabilidade entre seeds `≥ 0,90`; `predicted-added-edge-rate` no NULL
`≤ 0,10`; AUPRC acima da prevalência; o conjunto tem de melhorar o melhor sinal isolado
**sem** subir o falso positivo; duplicar o mesmo sinal **não** pode produzir ganho
equivalente a acrescentar um sinal diferente. Toda métrica de aresta reporta o número de
positivos.

**Boa previsão com recuperação de arestas falhada continua a ser rejeição para descoberta
relacional.**

França real, sem verdade de arestas: ganho fora da amostra, superioridade contra
permutações, estabilidade entre seeds e leave-one-period-out, concordância entre sinais,
confiança e abstenção, eventos acima do piso de ruído, nenhuma alegação causal.

## 9. Diagnóstico contra evidência

Um cenário sintético responde a "esta arquitetura consegue recuperar um grafo que existe";
nunca a "existem estas relações em França". Supervisão direta por `A_true` é diagnóstico de
representabilidade e não é método aplicável a França, onde não há rótulos de arestas.

## 10. Regras de paragem

Parar se nenhum sinal for `RELATION_INFORMATIVE`; parar se o oráculo multissinal não
distinguir `A_true` de `A_permuted`; parar antes de França se o sintético falhar os gates
eliminatórios. Não estender a exposição sintética para 32×, 64× ou 128×: isso produziria um
diagnóstico cada vez menos representativo de França.

## 11. O que esta etapa não reabre

Não reinterpreta os resultados negativos do HERALD 87, 88 e 89 — eles são a justificação
desta etapa. Não inclui a Córsega. Não faz grid extenso de hiperparâmetros. Não usa o painel
legado com vazamento, nem crescimento entre milésimos FLORES, nem trata emprego privado
Urssaf como emprego total.
