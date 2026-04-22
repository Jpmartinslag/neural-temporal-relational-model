# STGNN Readiness and Architecture Decision v0

> Methodological precedence note: use [METHODOLOGICAL_POSITIONING_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/METHODOLOGICAL_POSITIONING_V0.md) as the current canonical framing. If this report conflicts with it, the methodological positioning document prevails.


Data: 2026-04-12

Objetivo:

- separar prontidao de dados de decisao arquitetural
- evitar iniciar o `STGNN` como simples troca de modelo
- registrar o que precisa estar solido antes de desenhar uma arquitetura propria

## Estado atual

O projeto ja possui a base estrutural minima para uma etapa `STGNN`:

- grafo core com `280` nos `ZE2020`
- matriz de adjacencia `280 x 280`
- `1486` arestas nao nulas
- grafo simetrico
- painel de features com `1680` linhas: `280` zonas por `6` anos, de `2019` a `2024`
- target proxy anual com `7560` linhas: `280` zonas por `27` anos, de `2000` a `2026`
- pacote anual de modelagem separado em features, target e adjacencia

Isso significa que o projeto esta pronto para preparar tensores e experimentos controlados.

Isso ainda nao significa que esta pronto para treinar um modelo profundo como conclusao substantiva.

## Principal limite

O limite principal nao e mais organizacao territorial.

O limite principal e profundidade temporal efetiva das features.

Cobertura observada por ano:

- `2019`: `7` features com algum valor observado
- `2020`: `8` features com algum valor observado
- `2021`: `20` features com algum valor observado
- `2022`: `13` features com algum valor observado
- `2023`: `11` features com algum valor observado
- `2024`: `11` features com algum valor observado

Como consequencia, um `STGNN` profundo treinado agora teria alto risco de aprender padroes de imputacao, cobertura de fonte ou persistencia temporal, em vez de dinamica economica real.

Justificativa temporal:

- existem apenas `6` anos de features
- com horizonte `h = 1`, isso gera apenas `6` amostras anuais alinhadas porque o target vai ate `2026`
- o split efetivo fica com apenas `3` anos de treino, `1` de validacao, `1` de teste e `1` de holdout futuro
- esse desenho e suficiente para testar encadeamento, tensores e baselines, mas ainda e fraco para concluir superioridade substantiva de um modelo profundo

## Sinal do baseline

O baseline sem grafo mostrou um alerta importante:

- `persistence` teve desempenho melhor que `ridge_linear`
- isso sugere que o target proxy tem forte inercia temporal
- tambem sugere que adicionar features sem tratar janelas, mascaras e defasagens pode piorar o resultado

Leitura metodologica:

- o primeiro concorrente real do futuro `STGNN` deve ser persistencia temporal forte
- qualquer modelo com grafo precisa provar que supera persistencia, e nao apenas que roda

## Decisao arquitetural

Nao devemos escolher ainda uma arquitetura final.

Antes disso, precisamos construir uma camada intermediaria chamada aqui de `stgnn_tensor_package_v0`.

Essa camada deve transformar os artefatos atuais em objetos de modelagem auditaveis:

- `X`: tensor de features com forma conceitual `[time, node, feature]`
- `Y`: target alinhado por horizonte, por exemplo `target(t + h)`
- `A`: matriz de adjacencia normalizada
- `M`: mascara de observacao das features
- `splits`: treino, validacao e teste estritamente temporais
- `metadata`: nomes de features, anos, nos, escalonamento e regras de imputacao

Somente depois dessa camada devemos decidir a arquitetura.

## Hipoteses candidatas

As hipoteses de modelagem devem ser tratadas como concorrentes, nao como verdades:

- persistencia: `target(t + 1) = target(t)`
- modelo tabular temporal: defasagens do proprio target e features sem grafo
- modelo espacial simples: suavizacao por vizinhos ou regressao com agregados dos vizinhos
- `STGNN` leve: grafo mais recorrencia/convolucao temporal curta
- arquitetura propria: modelo com mascaras explicitas, auditoria por fonte e separacao entre sinal economico e sinal de cobertura

## Regras antes do primeiro STGNN

O primeiro experimento com grafo so deve acontecer depois de:

- congelar o horizonte inicial como `h = 1` ano, entendido como atribuicao temporal minima: features em `t` tentam explicar target em `t+1`
- registrar que `h = 1` preserva ordem temporal, mas nao prova causalidade por si so
- decidir se o target entra como historico autoregressivo nas features
- definir imputacao simples e auditavel
- explicitar que `0` em dado padronizado equivale a media do treino, nao a ausencia substantiva
- manter mascaras de observacao como entradas ou como controle de diagnostico
- normalizar features usando apenas periodo de treino
- documentar claramente o split temporal
- comparar contra persistencia antes de interpretar qualquer ganho

## Caminho recomendado

Proxima etapa tecnica:

1. construir `stgnn_tensor_package_v0`
2. validar shapes, anos, nos, masks e vazamento temporal
3. criar baseline autoregressivo forte com target defasado
4. criar baseline espacial simples usando vizinhos
5. so entao escolher a primeira arquitetura `STGNN`

## Baseline espacial formal

Antes de qualquer `STGNN`, o grafo precisa superar um teste simples.

Baseline espacial puro:

- `y_hat_i(t+1) = sum_j A_norm[i,j] * y_j(t)`

Baseline espacial com persistencia local:

- `y_hat_i(t+1) = alpha * y_i(t) + (1 - alpha) * sum_j A_norm[i,j] * y_j(t)`

Onde:

- `A_norm` e a matriz de adjacencia normalizada por linha
- `i` e a zona alvo
- `j` sao zonas vizinhas
- `alpha` pode ser escolhido por validacao temporal

Se esse baseline nao melhora a persistencia local, um modelo neural com grafo tem pouca justificativa inicial.

## Resultado inicial do baseline espacial

O baseline espacial `core_v0` foi executado apos a criacao do pacote tensorial.

Resultado principal:

- a media espacial dos vizinhos ficou muito pior que a persistencia local
- a mistura validada escolheu `alpha = 1.0`
- isso equivale a manter apenas persistencia local e dar peso zero ao componente espacial simples

Leitura:

- o grafo espacial estatico ainda nao demonstrou ganho preditivo simples
- isso nao invalida o grafo como estrutura para auditoria, visualizacao ou arquitetura futura
- mas impede interpretar um futuro ganho neural como garantido apenas porque existe uma adjacencia territorial
- antes de treinar `STGNN`, o projeto precisa decidir se o grafo sera enriquecido com mobilidade, pesos economicos ou grafo adaptativo, ou se o primeiro modelo com grafo sera explicitamente exploratorio

## Conclusao

Estamos em boa posicao para passar para a fase `STGNN`, mas nao para treinar um modelo profundo como se a arquitetura ja estivesse decidida.

O passo coerente agora e criar a camada tensorial auditavel e os baselines fortes.

Essa camada sera a fundacao para decidir se o projeto usa uma arquitetura conhecida ou se justifica uma arquitetura propria.
