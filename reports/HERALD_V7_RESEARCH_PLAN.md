# HERALD V7 - Plano de pesquisa para um modelo mais robusto que V6

Data: 2026-05-03  
Escopo: especificacao cientifica antes de implementacao  
Objetivo: definir uma linha HERALD V7 capaz de bater Ridge AR em 2025, preservar conexoes territoriais reais, ser mais estavel que V6, melhorar fortemente a previsao setorial A10 e abrir uma nova familia semi-supervisionada metodologicamente mais adequada.

## 1. Diagnostico atual

HERALD V6 h64 e o melhor candidato atual. Ele supera Ridge AR, ARIMA, LSTM e STGNNs na media 2021-2025, mas mostrou uma fragilidade importante: em 2025, Ridge AR pode vencer porque o ano parece mais local, regular e menos dependente de reconfiguracao territorial.

O HERALD Semi trouxe uma informacao cientifica importante, mesmo sem melhorar WMAPE: ele aprendeu novas conexoes e reorganizou o grafo, mas essas conexoes foram mais interpretativas do que preditivas. O mascaramento bruto de zonas piorou a previsao, especialmente em `spatial_block`, indicando que forcar dependencia de vizinhos pode destruir sinal local confiavel.

Tambem existe uma fragilidade setorial: a cabeca A10 atual nao e suficientemente forte para ser tratada como contribuicao preditiva central. Ela deve deixar de ser apenas uma saida auxiliar e passar a ser uma parte estruturante do V7, com baselines setoriais fortes e uso direto da composicao historica de cada zona.

Conclusao: o problema nao e que o grafo nao aprende. O problema e que o modelo ainda nao sabe quando usar o grafo para prever e quando confiar no componente local.

## 2. Hipotese central do V7

HERALD V7 deve aprender uma mistura adaptativa entre previsao local e previsao por grafo:

```text
pred_t,z = alpha_t,z * pred_local_t,z + (1 - alpha_t,z) * pred_graph_t,z
```

onde:

- `pred_local_t,z` e uma previsao local forte, inspirada em Ridge AR;
- `pred_graph_t,z` e a correcao neural com grafo dinamico;
- `alpha_t,z` e um gate por ano e zona que aprende o regime de previsibilidade.

Em anos estaveis, como 2025 parece ser, o modelo deve aumentar `alpha` e confiar mais no local. Em anos de choque ou recomposicao territorial, como 2020-2022, deve reduzir `alpha` e ativar mais o grafo.

O claim cientifico do V7 nao deve ser "usar mais grafo sempre". O claim correto deve ser: HERALD usa grafo dinamico quando existe ganho economico-territorial e volta ao componente local quando o grafo vira ruido.

O segundo claim cientifico do V7 deve ser setorial: HERALD nao deve prever apenas o total de criacoes, mas tambem decompor esse crescimento por A10 de forma melhor que baselines simples como `lag1_by_zone`.

## 3. HERALD V7-A: Ridge-Graph Mixture Gate

### Hipotese

Ridge AR vence 2025 porque o sinal local domina nesse ano. V6 perde quando aplica uma correcao grafica desnecessaria. Um gate de mistura local/grafo deve manter o ganho de HERALD nos anos de choque e recuperar a robustez do Ridge em 2025.

### Arquitetura minima

```text
ridge_t,z = RidgeAR(x_local_history)

e_t,z = encoder_local_quarterly_annual(...)
A_t   = dynamic_graph(e_t, mobility_prior, geo_prior, regime_t)
graph_t,z = HERALD_graph_head(e_t, A_t, h_t)

alpha_t,z = sigmoid(gate_alpha([features_stability_t,z,
                                regime_t,
                                local_uncertainty_t,z,
                                graph_uncertainty_t,z,
                                delta_graph_t]))

pred_t,z = alpha_t,z * ridge_t,z + (1 - alpha_t,z) * graph_t,z
```

### Features para o gate

- volatilidade recente da zona;
- erro recente do Ridge em validacao walk-forward;
- intensidade de mudanca do grafo `adj_delta`;
- regime COVID/rebound/normal;
- variacao do setor A10 local;
- dispersao dos vizinhos de mobilidade;
- confianca do grafo, medida por entropia da atencao.

### Loss

```text
loss = Huber(pred, y)
     + lambda_stable * alpha_regularizer_normal_years
     + lambda_shock  * graph_activation_reward_shock_years
     + lambda_smooth * smooth_alpha
```

Interpretacao:

- em anos normais, penalizar uso excessivo do grafo se ele nao reduz erro;
- em anos de choque, permitir maior uso do grafo;
- evitar que `alpha_t,z` oscile sem razao entre zonas vizinhas.

### Ablacoes obrigatorias

| Ablacao | Pergunta |
|---|---|
| `v7_full` | Mistura local/grafo completa |
| `ridge_only` | Limite local puro |
| `graph_only` | HERALD sem mistura |
| `fixed_alpha_0.5` | Mistura nao aprendida |
| `no_regime_gate` | Regime ajuda o gate? |
| `no_uncertainty_gate` | Incerteza ajuda a escolher local/grafo? |
| `fixed_graph_v7` | Dinamismo do grafo ajuda dentro do V7? |

### Criterio de sucesso

V7 so deve ser aceito se:

1. bater Ridge AR em 2025;
2. bater V6 h64 na media 2021-2025;
3. reduzir o desvio padrao entre seeds;
4. nao piorar 2021-2022, onde HERALD ja captava choque;
5. mostrar `alpha` maior em anos estaveis e menor em anos de choque.

## 4. HERALD V7-B: grafo interpretativo separado do grafo preditivo

### Hipotese

O Semi mostrou que o grafo pode aprender conexoes novas reais, mas essas conexoes nao necessariamente melhoram WMAPE. Entao o V7 deve separar:

- grafo estrutural: usado para interpretacao territorial;
- grafo preditivo: usado apenas quando melhora previsao.

### Arquitetura

```text
A_struct_t = graph_encoder_structural(mobility, geo, A10, regime)
A_pred_t   = graph_encoder_predictive(e_t, validation_error, uncertainty)

graph_signal = A_pred_t @ e_t
structural_report = diagnostics(A_struct_t)
```

O modelo pode preservar conexoes territoriais aprendidas sem ser obrigado a usa-las na previsao final.

### Criterio de sucesso

- `A_struct_t` deve continuar captando COVID/rebound e mobilidade > geografia;
- `A_pred_t` deve melhorar ou nao degradar WMAPE;
- diferenca entre os dois grafos deve ser reportada, nao escondida.

## 5. HERALD Semi V2: semi-supervisao economica, nao mascaramento bruto

### O que nao repetir

Nao repetir simplesmente:

- mascaramento aleatorio de zonas;
- `block` espacial bruto;
- `spatial_block` como estrategia principal;
- loss semi-supervisionada sem hipotese economica.

Essas estrategias forcaram o modelo a depender dos vizinhos mesmo quando o historico local era mais confiavel.

### Nova hipotese

Semi-supervisao deve aprender invariantes economico-territoriais, nao reconstruir zonas escondidas de forma artificial.

## 6. Semi V2-A: pretraining contrastivo territorial

### Hipotese

Zonas conectadas por mobilidade, composicao A10 parecida e trajetorias economicas semelhantes devem ter representacoes proximas. Zonas desconectadas ou setorialmente distintas devem ficar distantes.

### Pretraining

Aprender embeddings de zonas antes do forecasting:

```text
positive pairs:
  - zonas com alta mobilidade pendular
  - zonas com composicao A10 semelhante
  - zonas com trajetorias historicas correlacionadas

negative pairs:
  - zonas distantes em mobilidade
  - zonas com composicao setorial muito diferente
  - zonas com trajetorias divergentes
```

Loss:

```text
loss_pretrain = contrastive_loss(z_i, z_j, positives, negatives)
```

Depois, usar esses embeddings inicializados no HERALD V7.

### Criterio de sucesso

- V7 com pretraining deve bater V7 sem pretraining;
- ganho deve aparecer em 2025 e em seeds instaveis;
- embeddings devem agrupar zonas economicamente plausiveis.

## 7. Semi V2-B: masked economic variables

### Hipotese

Mascarar zonas inteiras e agressivo demais. Melhor mascarar variaveis economicas especificas e forecast-safe.

Mascaras possiveis:

- crescimento local recente;
- composicao A10 parcial;
- volatilidade local;
- features trimestrais URSSAF;
- lag setorial de alguns setores.

O modelo aprende a reconstruir estrutura economica, mas ainda preserva a identidade territorial da zona.

### Criterio de sucesso

- melhorar WMAPE total sem degradar setor;
- melhorar estabilidade de seeds;
- melhorar previsao 2025;
- bater o baseline sem mascaramento.

## 8. Semi V2-C: temporal consistency by regime

### Hipotese

O grafo deve mudar pouco em anos normais e muito em anos de choque. A semi-supervisao deve ensinar consistencia temporal estrutural, nao esconder zonas.

Loss:

```text
loss_temporal = stable_year_penalty * ||A_t - A_{t-1}||
              - shock_year_reward  * regime_delta_t * ||A_t - A_{t-1}||
```

Com controle para evitar explosao:

```text
loss_bound = max(0, ||A_t - A_{t-1}|| - delta_max)
```

### Criterio de sucesso

- `adj_delta` baixo em anos normais;
- `adj_delta` alto em COVID/rebound;
- WMAPE nao piora;
- 2025 nao sofre correcao grafica excessiva.

## 9. Semi V2-D: ranking economico territorial

### Hipotese

O objetivo do projeto tambem envolve recomendacao economica territorial. WMAPE pode nao capturar bem o valor de ordenar zonas com maior crescimento ou maior risco.

Adicionar uma loss auxiliar de ranking:

```text
loss_rank = pairwise_ranking_loss(growth_pred_i, growth_pred_j)
```

Tarefas:

- top-k zonas em crescimento;
- zonas de risco;
- setores A10 em aceleracao;
- territorios que mudam de regime.

### Criterio de sucesso

- melhorar top-k precision/recall;
- manter WMAPE proximo ou melhor;
- gerar recomendacoes territoriais mais estaveis.

## 10. Melhorias especificas para A10

O sector head atual nao deve ser tratado como contribuicao forte, pois perde para baselines simples como lag-1 por zona. No V7, A10 deve virar um objetivo principal do modelo, nao apenas uma cabeca auxiliar desacoplada. O modelo deve prever:

1. o total anual por zona;
2. a composicao A10 por zona;
3. o total setorial por zona, obtido de forma coerente entre total e proporcoes.

O V7 precisa dar acesso direto ao historico setorial e a estrutura setorial dos vizinhos. Sem isso, o modelo tende a aprender uma composicao media, nao a composicao economica especifica de cada territorio.

### Arquitetura

```text
sector_input = concat([
  h_t,
  pred_total_t,
  sector_props_lag1_z,
  sector_hist_mean_z,
  national_sector_trend_t,
  regional_sector_trend_t,
  graph_sector_lag_t,
  graph_sector_growth_t,
  zone_sector_volatility_z
])

sector_props_pred = sector_head_props(sector_input)
sector_total_pred = pred_total_t * sector_props_pred
```

### Restricao de coerencia

As proporcoes A10 devem somar 1 por zona:

```text
sum_s sector_props_pred[z, s] = 1
```

A soma dos setores deve reconstruir o total:

```text
sum_s sector_total_pred[z, s] ~= pred_total_t[z]
```

Essa restricao evita uma decomposicao setorial numericamente incoerente.

### Loss setorial proposta

```text
loss = loss_total
     + lambda_props * KL(sector_props_true, sector_props_pred)
     + lambda_sector_total * WMAPE(sector_total_true, sector_total_pred)
     + lambda_temporal_sector * smooth_sector_props
     + lambda_lag_guard * max(0, error_sector - error_lag1_baseline)
```

O ultimo termo e opcional e deve ser usado com cuidado: ele impede que o modelo aceite uma cabeca setorial pior que `lag1_by_zone` sem penalizacao.

### Inputs setoriais obrigatorios

- proporcao A10 da zona em `t-1`;
- media historica A10 da zona;
- tendencia nacional por setor;
- tendencia regional por setor, se disponivel;
- lag setorial dos vizinhos via mobilidade;
- lag setorial dos vizinhos via geografia;
- volatilidade setorial da zona;
- indicador de setores pequenos/raros para evitar que `JZ`, `KZ`, `LZ`, `BE` sejam ignorados.

### Ablacoes

| Ablacao | Pergunta |
|---|---|
| `sector_lag1_only` | baseline forte |
| `sector_head_no_lag1` | head atual |
| `sector_head_with_lag1` | historico setorial ajuda? |
| `sector_graph_lag` | setores dos vizinhos ajudam? |
| `sector_national_trend` | tendencia nacional basta? |
| `sector_regional_trend` | tendencia regional agrega? |
| `sector_coupled` | setor melhora total ou so setor? |
| `sector_consistency_loss` | coerencia total-setor melhora estabilidade? |

### Criterio de sucesso

- bater `sector_lag1_by_zone`;
- bater `sector_hist_mean_by_zone`;
- nao degradar WMAPE total;
- melhorar setores pequenos como `JZ`, `KZ`, `LZ`, `BE`.
- manter soma setorial coerente com o total;
- reduzir erro setorial por zona, nao apenas na media nacional.

### Metricas A10 obrigatorias

| Metrica | Por que importa |
|---|---|
| `sector_wmape_mean` | erro medio setorial |
| `sector_wmape_by_A10` | identifica setores fracos |
| `sector_wmape_by_zone` | verifica robustez territorial |
| `props_KL` | qualidade da distribuicao A10 |
| `top_sector_accuracy` | setor dominante previsto corretamente |
| `sector_growth_rank_corr` | ranking de setores em crescimento |
| `coherence_error` | soma setorial vs total |

O V7 so pode reivindicar contribuicao setorial se superar `lag1_by_zone` e `hist_mean_by_zone`. Bater apenas o baseline uniforme 1/9 nao e suficiente.

## 11. Bateria minima do V7

Rodar com 10 seeds:

```text
0 1 7 13 17 42 77 99 123 2025
```

### Secao A: modelos principais

| Modelo | Objetivo |
|---|---|
| Ridge AR | baseline local |
| HERALD V6 h64 | referencia atual |
| V7 full | novo candidato |
| V7 graph_only | sem mistura local |
| V7 ridge_graph_gate | mistura principal |
| V7 fixed_graph | controle dinamico vs fixo |

### Secao B: semi v2

| Modelo | Objetivo |
|---|---|
| V7 no pretrain | baseline |
| V7 contrastive_pretrain | semi estrutural |
| V7 masked_variables | semi economico |
| V7 temporal_regime_loss | semi temporal |
| V7 ranking_aux | recomendacao |

### Secao C: 2025 stress test

Comparar separadamente:

- WMAPE 2025;
- erro por zona em 2025;
- zonas onde Ridge vence HERALD;
- zonas onde grafo ajuda;
- `alpha_t,z` medio por ano e por zona;
- correlacao entre uso do grafo e erro.

## 12. Criterios de aprovacao cientifica

HERALD V7 so deve substituir V6 se cumprir:

| Criterio | Minimo aceitavel |
|---|---|
| V7 vs V6 media 2021-2025 | V7 menor WMAPE medio |
| V7 vs Ridge 2025 | V7 vence Ridge em 2025 |
| Estabilidade | std menor ou igual ao V6 |
| Grafo dinamico | vence fixed_graph ou explica quando nao vence |
| Interpretabilidade | alpha e adj_delta coerentes com regime |
| Semi V2 | qualquer semi deve bater seu controle sem semi |
| A10 | bater lag-1 by zone para claim setorial forte |
| Coerencia total-A10 | soma setorial consistente com total |

## 13. O que nao fazer agora

Nao priorizar:

- Transformer grande sem hipotese economica;
- aumentar epochs como solucao principal;
- repetir mask random/block como no Semi atual;
- escolher modelo pelo melhor seed;
- chamar interpretabilidade de ganho preditivo;
- misturar forecast prospectivo com avaliacao observada;
- defender A10 sem bater lag-1 setorial;
- defender grafo dinamico sem `fixed_graph` na mesma bateria.

## 14. Resumo executivo

O V7 deve resolver a fragilidade revelada em 2025: HERALD precisa saber quando o grafo ajuda e quando o Ridge local e suficiente. A proposta principal e um `Ridge-Graph Mixture Gate`, com `alpha_t,z` aprendendo a mistura local/grafo por ano e zona.

As novas conexoes aprendidas pelo Semi nao devem ser descartadas. Elas devem alimentar uma linha Semi V2 baseada em pretraining contrastivo territorial, mascaramento de variaveis economicas e regularizacao temporal por regime, nao mascaramento bruto de zonas.

O objetivo cientifico do V7 e ser melhor que V6 em quatro dimensoes:

1. melhor WMAPE medio;
2. melhor 2025 contra Ridge;
3. menor variancia entre seeds;
4. melhor previsao A10 contra baselines setoriais fortes;
5. interpretabilidade territorial preservada, com grafo usado apenas quando traz valor preditivo.
