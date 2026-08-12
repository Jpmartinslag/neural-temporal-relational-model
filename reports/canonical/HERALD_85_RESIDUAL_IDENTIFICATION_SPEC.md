# HERALD 85 — identificação relacional por resíduo congelado

## Evidência que autoriza o teste

No Slurm `7860588`, o grafo verdadeiro reduziu em `79.90%` o MSE do resíduo
observável contra o mesmo grafo com identidades permutadas e atingiu correlação
`0.9008`. Entregar o grafo verdadeiro ao HERALD82 completo, porém, não melhorou
o MAE contra o prior (`0.11003` contra `0.10932`). A regra pré-registrada do
HERALD84 selecionou `implement_relational_residual_objective`.

## Arquitetura

1. Um modelo linear local, sem relações entre zonas, é ajustado causalmente com
   história própria, nível, participação e média nacional do setor.
2. Suas previsões são congeladas; o alvo relacional é o erro restante.
3. A única previsão treinável desse segundo estágio é

   `r_hat[t+1] = beta_prior * A_prior[t] g_centered[t]
                + beta_dynamic * (A[t]-A_prior[t]) g_centered[t]`.

4. `A[t]` conserva a definição do HERALD82: prior commuting observado mais
   desvio dinâmico de posto 4, sem self-loop.

Não existe concatenação da representação do nó com a saída relacional, nem head
direto capaz de minimizar a loss residual. A história própria permanece no
primeiro estágio porque ela é necessária à previsão; fica congelada durante a
identificação do grafo.

## Seleção e controles

- rank, hidden, top-k, dropout e LR permanecem os valores sourced do HERALD82;
- épocas: `50,100,200`, grade já usada;
- regularização da distância `A-A_prior`: varredura declarada
  `0, 0.1, 1.0`, selecionada somente na validação;
- refit em treino+validação após congelar época e regularização;
- prior verdadeiro, prior com identidades permutadas e cenários nulos continuam
  controles obrigatórios;
- métricas primárias são recuperação de arestas/eventos e falsos positivos, não
  o erro preditivo total.

## Gates conhecidas

Mantêm-se as gates HERALD83: no cenário forte, F1 de arestas >= `0.50` e F1 de
eventos >= `0.30` em pelo menos 4/5 seeds; vantagem de F1 >= `0.10` contra o
controle permutado em 4/5; nos dois nulos, taxa de arestas adicionadas <= `0.10`
em 4/5; dose-resposta e direção do ruído devem ser coerentes.

O primeiro lançamento é somente um smoke de uma seed. França permanece
bloqueada até o benchmark completo passar.

## Relação com DEC-023 e DEC-072

Os resultados históricos não são apagados. DEC-023 testou L2 co-growth em NL
para WMAPE; DEC-072 testou ZE-similarity comprimida por PCA e concatenada ao
node-only para ranking. Ambos continuam `GATE_FAIL` nos seus contratos.

O HERALD84 torna suspeita apenas a interpretação ampla de que essas falhas
demonstram ausência de valor relacional: ambos permitiam que a previsão local
resolvesse a tarefa sem usar relações. Essa interpretação passa a
`SUSPECT_PENDING_MATCHED_RETEST`; as métricas históricas não mudam.
