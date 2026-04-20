# Extended Core Verification Plan v0

Data: 2026-04-14

## Objetivo

- verificar se o `extended core` e metodologicamente defensavel
- separar evidencia real de correlacao espuria
- impedir vazamento temporal antes de qualquer STGNN
- decidir quais artefatos podem virar canonicos

## 1. Escopo Temporal Do Sinal

Pergunta:

- o `regime_leading_signal` e para `forecast` ou `nowcast`?

Verificar:

- se o sinal do ano `t` usa meses de `t`
- quais meses estariam disponiveis no momento da previsao
- se o objetivo e prever `SIDE(t)` antes do fim de `t` ou prever `SIDE(t+1)`

Testes:

- criar variantes `Jan-Mar`, `Jan-Jun`, `Jan-Sep`, `Jan-Dec`
- criar variante defasada: sinal de `t-1` para prever crescimento de `t`

Criterio:

- `forecast`: usar somente informacao disponivel antes do ano-alvo
- `nowcast`: documentar mes-limite e disponibilidade

Status atual:

- pendente

## 2. Correlacao Do Sinal

Problema:

- correlacao pooled global `0.695` pode refletir tendencia temporal comum
- correlacoes anuais sao fracas e varias negativas

Verificar:

- correlacao pooled
- correlacao por ano
- correlacao com efeito fixo de ano
- correlacao com sinal defasado
- correlacao por grupos territoriais

Testes obrigatorios:

- `corr(signal_t, growth_t)` pooled
- `corr(signal_t demeaned by year, growth_t demeaned by year)`
- `corr(signal_t-1, growth_t)`
- `corr(signal_t partial year, growth_t)`

Criterio:

- nao chamar de `leading signal` se so funcionar pooled
- aceitar como candidato se mantiver sinal positivo fora da amostra e sem contemporaneidade forte

Status atual:

- pooled: forte
- within-year: fraco
- defasado: fraco
- decisao: ainda nao defensavel como farol economico

## 3. Perfil Setorial Das Zonas

Problema:

- perfil setorial atual usa `FLORES 2024`
- aplicar perfil 2024 para anos desde 2012 pode introduzir vazamento estrutural
- `zone_sectoral_profile_quality_v0.json` tem bug: peso maximo impossivel

Verificar:

- quais anos de `FLORES A17` existem localmente
- se ha perfil historico `2019-2024`
- se o perfil 2024 deve ser tratado como feature estatica ou apenas proxy recente
- se pesos setoriais somam `1.0` por zona
- se `total_establishments` esta excluido do calculo de pesos

Testes:

- QA de soma de pesos por zona
- QA de pesos min/max entre `0` e `1`
- comparar perfil 2024 contra perfil historico se existir

Criterio:

- usar perfil 2024 para anos antigos apenas se rotulado como `static_recent_profile_proxy`
- preferir perfil historico quando disponivel

Status atual:

- pendente

## 4. Fonte Mensal Nacional

Problema:

- sinal real usa SIDE mensal nacional, mesma familia estatistica do target local SIDE
- isso pode capturar tendencia nacional comum, nao sinal territorial independente

Verificar:

- se a serie mensal e criacao de empresas ou estabelecimentos
- se o target local e empresas ou estabelecimentos
- se os conceitos sao equivalentes
- se ha alternativa externa: `DS_ICA`, volume de vendas, atividade setorial, contas regionais

Testes:

- comparar SIDE mensal nacional vs crescimento nacional do target anual
- comparar sinal SIDE mensal vs `DS_ICA`
- testar se sinal adiciona valor alem de ano/fold agregado

Criterio:

- se o sinal vier da mesma familia do target, classificar como `target-family regime proxy`
- nao chamar de sinal externo independente

Status atual:

- pendente

## 5. Tensor Extended

Problema:

- tensor antigo `stgnn_tensor_package_side_target_core_v0.npz` foi modificado
- extended core deve ficar separado para nao quebrar reprodutibilidade

Verificar:

- quais arquivos antigos foram alterados
- se `stgnn_tensor_package_side_target_core_v0.npz` deve ser restaurado
- se `stgnn_tensor_package_extended_core_v0.npz` contem apenas features permitidas
- se `Y` esta alinhado corretamente com `X`

Testes:

- shape check
- feature registry check
- split check
- leakage check por feature
- reproduzir baseline persistencia diretamente do tensor

Criterio:

- pacote antigo deve permanecer imutavel
- pacote extended deve ter registry proprio
- todo campo do tensor precisa ter ano de disponibilidade

Status atual:

- pendente

## 6. Baseline Extended

Problema:

- Ridge extended nao bate persistencia
- coeficiente do Ridge nao prova importancia robusta do sinal

Verificar:

- baseline persistencia no mesmo split
- Ridge com alpha validado, nao fixo
- Ridge com e sem `regime_leading_signal`
- Ridge com e sem populacao
- ablation por feature
- backtest rolante

Testes:

- persistence
- ridge_lags_only
- ridge_lags_population
- ridge_lags_regime
- ridge_lags_population_regime
- regime_selector usando sinal parcial

Criterio:

- sinal so entra como feature canonica se melhora validacao ou backtest rolante
- STGNN so avanca se baseline linear/regularizado estiver corretamente calibrado

Status atual:

- Ridge extended atual muito pior que persistencia
- pendente reexecucao com ablation

## 7. Justificativa Para STGNN

Problema:

- falha do Ridge nao prova necessidade de STGNN
- pode ser feature ruim, vazamento, escala, split ou target instavel

Verificar:

- se baselines fortes foram esgotados
- se ha ganho de sinal externo validado
- se grafo traz valor em alguma forma
- se nao-linearidade e espacialidade foram demonstradas por teste, nao assumidas

Testes:

- baseline linear calibrado
- baseline tree/boosting simples
- baseline regime-aware
- baseline com grafo como feature agregada
- comparacao contra persistencia e ridge em backtest rolante

Criterio:

- STGNN vira proximo passo se houver:
- alvo e tensor sem vazamento
- baseline conservador definido
- sinal externo ou estrutura espacial com evidencia minima
- protocolo de backtest fechado

Status atual:

- ainda nao justificado como necessidade
- justificado apenas como experimento futuro

## 8. Decisao De Linguagem

Evitar:

- `resolvemos o misterio`
- `prova relacao nao-linear e espacial`
- `valida tecnicamente que precisa ser STGNN`
- `farol economico` sem qualificador

Usar:

- `candidato a sinal antecipador`
- `evidencia pooled, ainda nao robusta dentro do ano`
- `pacote extended aumenta profundidade temporal`
- `Ridge extended ainda nao supera persistencia`
- `STGNN permanece hipotese de proxima etapa`

## Proxima Ordem De Execucao

1. corrigir QA do perfil setorial
2. auditar disponibilidade temporal de cada feature extended
3. criar variantes sem vazamento do sinal mensal
4. recalcular correlacoes robustas
5. rodar ablations do baseline extended
6. decidir se o extended core vira canonico
7. so depois avaliar STGNN
