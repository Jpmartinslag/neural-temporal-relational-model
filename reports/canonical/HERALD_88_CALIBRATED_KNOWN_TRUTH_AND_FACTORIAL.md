# HERALD 88 — verdade conhecida calibrada, e o fatorial que só corre se ela passar

**Estado:** pré-registo, escrito antes de qualquer execução.
**Âmbito:** sintético apenas. Nenhuma afirmação sobre França.

## 1. O que este documento decide

O HERALD 87 falhou a recuperação de arestas (F1 0,256–0,284) e de eventos (0,028–0,033). A
auditoria de diagnóstico mostrou que a causa mais provável não é a arquitetura, e sim o
próprio banco de ensaio:

- o componente relacional é **0,12% da variância do crescimento latente** e **0,00126% da
  variância observável**;
- o grafo verdadeiro **não melhora** o MSE observável contra um prior permutado;
- o `event_f1` atribui **0 a anos corretamente estáticos**, e três das cinco origens de
  avaliação (2023, 2024, 2025) não contêm **nenhum** evento verdadeiro;
- o top-k duro dá gradiente **exatamente zero** às arestas excluídas.

O HERALD 88 corrige o instrumento antes de voltar a julgar o modelo, e ordena as decisões
para que nenhuma pergunta seja respondida antes da pergunta de que depende.

**O objetivo é testar recuperabilidade, não produzir evidência sobre França.**

## 2. Ordem obrigatória, com paragens

```
1. calibração do gerador   (NumPy, determinística)
2. oráculo observável      -> se falhar: PARAR, reportar CALIBRATED_BENCHMARK_STILL_UNIDENTIFIABLE
3. scorer supervisionado   -> se falhar: PARAR, rejeitar a arquitetura
4. fatorial 2x2            -> só aqui a loss preditiva e o top-k são julgados
5. agregação final
```

Cada etapa é uma pré-condição da seguinte. Um resultado da etapa 4 obtido sem as etapas 2 e
3 não é interpretável, porque não se saberia se mede a loss, o instrumento ou a arquitetura.

## 3. Parâmetros congelados

| item | valor |
|---|---|
| seeds de modelo | `42, 43, 44, 45, 46` |
| origens de pontuação | `2021, 2022, 2023, 2024, 2025` |
| hidden (`context_hidden`) | **64**, fixo |
| embedding | 8 |
| dropout | 0,20 |
| learning rate | 1e-3 |
| top-k de propagação | 28 |
| sweep de épocas | `25, 50, 100, 200` |
| seed do gerador | 8601 |
| zonas × setores × anos | 280 × 9 × 1998–2025 |

**Nenhuma alteração de capacidade.** A sensibilidade 32/64/128 já foi executada: a largura
comprou +0,028 de F1 de arestas, **−0,003** de eventos e **+0,038** de falsos positivos no
nulo. A largura 256 fica bloqueada por ausência de tendência compatível em eventos e nulo.

**Nenhuma seleção pelo melhor resultado final.** A época é escolhida só na validação; o
refit é reinicializado; a origem é pontuada uma vez.

## 4. Calibração do gerador (tarefa 2)

O `relation_strength` deixa de ser um número escolhido à mão. É derivado.

Definições, todas no espaço latente e antes de qualquer amostragem Negative Binomial:

```
raw_rel[t+1]    = A[t] @ centred(growth[t])
rel_inc[t+1]    = coef * raw_rel[t+1]                     # incremento relacional
nonrel_inc[t+1] = ar*growth[t] + macro[t+1] + eps[t+1]    # incremento não relacional
ratio           = RMS(rel_inc) / RMS(nonrel_inc)
```

`coef` é obtido por uma **passagem de sonda determinística**: simula-se primeiro a
trajetória sem qualquer efeito relacional (`coef = 0`), mede-se `RMS(raw_rel)` sobre essa
trajetória e `RMS(nonrel_inc)`, e fixa-se

```
coef = 0.25 * RMS(nonrel_inc) / RMS(raw_rel)
```

A sonda usa exclusivamente componentes internos do gerador. **Não usa F1, MSE de avaliação,
arestas recuperadas nem qualquer saída do modelo.** A mesma seed produz o mesmo `coef`.

Mantém-se a normalização por linha de `A` — é ela que torna o termo uma média sobre
vizinhos, e removê-la seria mudar a semântica do grafo para facilitar a tarefa. Mantém-se o
ruído. Mantém-se o cenário nulo com contribuição relacional **exatamente zero**.

A verdade exporta:

`requested_effective_ratio`, `realised_latent_effective_ratio`,
`realised_observable_effective_ratio`, `relational_rms`, `nonrelational_rms`,
`applied_coefficient`.

`realised_observable_effective_ratio` é a razão das mesmas RMS depois de propagadas para a
escala de contagens observadas. É reportada precisamente porque pode divergir da razão
latente: essa divergência é o objeto da etapa 2.

**Guarda de calibração:** razão latente realizada em `[0,23; 0,27]`; nulo exatamente `0,0`;
mesma seed, mesma razão; e nenhum destes diagnósticos alcançável por `model_inputs`.

## 5. Avaliação de eventos (tarefa 3)

A métrica antiga fica **`SUPERSEDED`**. Os números do HERALD 87 não são reescritos; passam a
ser lidos com a ressalva de que três das cinco origens não continham eventos verdadeiros.

Nova definição:

- um evento é `(ano, origem, destino, birth|death)`;
- nascimento e morte permanecem tipos distintos e nunca se compensam;
- o gate principal é o **micro-F1 sobre a união das cinco origens**, não a média de F1 por
  origem;
- um ano cuja verdade não contém eventos **não recebe F1 zero**. Reporta-se
  separadamente `false_event_count` e `false_event_rate` para esse ano;
- as métricas por ano continuam a ser exportadas, para auditoria, sem serem o gate.

## 6. Gates

**Etapa 2 — oráculo observável.** Sem rede. Para cada origem, ajusta-se um único `β` nos
anos de treino, decide-se apenas na validação e pontua-se uma vez no ano retido, usando
crescimento reconstruído das contagens observáveis. Nunca `latent_growth` nem
`relational_component`.

- `A_true` reduz o MSE em **≥ 10%** contra `A_permuted`, agregado;
- direção favorável em **≥ 4/5** origens;
- `A_true` supera também `A_prior`.

Se falhar: **parar**, reportar `CALIBRATED_BENCHMARK_STILL_UNIDENTIFIABLE`, não implementar
nem correr braços neurais.

**Etapa 3 — representabilidade.** Scorer com supervisão direta de `A_true`, só no sintético,
só como diagnóstico. Gate: correlação densa ≥ 0,80, F1 de arestas adicionadas ≥ 0,60,
micro-F1 de eventos ≥ 0,60, em ≥ 4/5 seeds.

Falha ⇒ o scorer não representa a verdade e o problema é arquitetural. Passagem ⇒ a
arquitetura representa, e qualquer falha preditiva é de identificabilidade ou otimização.
**Esta supervisão nunca é apresentada como solução aplicável a França**, onde não existem
rótulos de arestas.

**Etapa 4 — cada braço neural.**

1. `null_false_added_edge_rate ≤ 0,10` em ≥ 4/5 seeds;
2. `null_false_event_rate ≤ 0,10` em ≥ 4/5 seeds, declarado aqui antes da execução;
3. `added_edge_f1 ≥ 0,50` em ≥ 4/5 seeds;
4. `event_micro_f1 ≥ 0,30` em ≥ 4/5 seeds;
5. reportar quantas seeds atingem o alvo exploratório `0,60`, sem que substitua os gates;
6. estabilidade mediana entre seeds ≥ 0,80;
7. erro preditivo melhor que o prior permutado — **necessário, nunca suficiente**. Boa
   previsão não compensa má recuperação.

## 7. Fatorial 2×2 (tarefa 6)

| fator | nível 0 | nível 1 |
|---|---|---|
| **A** informação temporal | features atuais | feature temporal causal explícita |
| **B** propagação no treino | top-k duro | densa/soft no treino, top-k 28 só na exportação |

Braços: `A0B0` (referência HERALD 87), `A1B0`, `A0B1`, `A1B1`. Cada braço corre o cenário
`dynamic` calibrado **e** o `null`, com as mesmas seeds, origens, hidden 64 e candidatos de
época.

A feature temporal contém apenas informação conhecida em `t`: ano normalizado, distância
desde os cortes metodológicos já ocorridos, e indicadores de 2020 e 2021 **apenas quando
esses anos já são o passo corrente**. Nenhuma indicação de regime futuro ou do próximo
evento.

Um mecanismo por braço. Não se alteram simultaneamente top-k, learning rate, dropout,
embedding, baseline ou loss.

## 8. Teste de gradiente do top-k (tarefa 7)

Antes do array:

- no braço duro, uma aresta fora do top-k tem gradiente **exatamente** zero;
- no braço soft, a mesma aresta tem gradiente **não** zero;
- o braço soft continua sem criar suporte fora do commuting;
- o top-k continua a ser aplicado na exportação e na avaliação.

Cada guarda tem de matar um mutante que reponha o comportamento errado.

## 9. Execução fail-closed (tarefa 9)

Antes de qualquer `sbatch`: guardas, mutation testing, `python -m py_compile`, `bash -n` nos
scripts Slurm, dry-run imprimindo braços, seeds, origens e parâmetros, e um smoke de um fold
e uma época. O `sbatch` reexecuta guardas e mutantes antes do treino e aborta com `set -e`.

## 10. O que este documento não autoriza

Não autoriza aplicação ao painel real francês, alteração de capacidade, busca aberta de
hiperparâmetros, nem qualquer leitura dos resultados sintéticos como evidência sobre
relações económicas em França.
