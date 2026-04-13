# SIDE Model Decision Matrix Core v0

Data: 2026-04-13

## Objetivo

- transformar os baselines atuais em decisao auditavel
- impedir salto prematuro para STGNN
- separar modelo conservador, candidato e desafiante

## Regra Atual

- baseline de referencia: `persistence`
- tolerancia de validacao contra persistencia: `0.250` ponto de WMAPE
- ganho minimo para candidato forte: `0.050` ponto de WMAPE na validacao
- modelo que vence apenas no teste nao substitui o baseline principal
- modelo que vence validacao e teste vira candidato para proxima etapa
- metricas de pacotes diferentes nao sao equivalentes; o pacote longo e a referencia principal

## Matriz

| modelo | validation WMAPE | test WMAPE | delta val vs pers. | delta test vs pers. | status |
|---|---:|---:|---:|---:|---|
| `segmented_by_size_volatility_group` | `3.259` | `6.564` | `-0.110` | `-0.100` | `candidate_for_next_stage` |
| `segmented_by_volatility_group` | `3.278` | `6.588` | `-0.091` | `-0.076` | `candidate_for_next_stage` |
| `segmented_by_size_group` | `3.367` | `6.616` | `-0.002` | `-0.049` | `marginal_candidate` |
| `persistence` | `3.369` | `6.664` | `+0.000` | `+0.000` | `conservative_default` |
| `ridge_autoregressive` | `4.850` | `6.406` | `+1.482` | `-0.258` | `diagnostic_only` |
| `rich_lags_only` | `7.302` | `3.326` | `+3.933` | `-3.338` | `diagnostic_only` |
| `moving_average_3` | `11.508` | `7.085` | `+8.140` | `+0.420` | `diagnostic_only` |

## Decisao

- modelo conservador: `persistence`
- melhor validacao: `segmented_by_size_volatility_group` com WMAPE `3.259`
- melhor teste: `rich_lags_only` com WMAPE `3.326`
- candidato recomendado agora: `segmented_by_size_volatility_group`

## Leitura

- a segmentacao por tamanho+volatilidade e o primeiro ganho limpo sobre persistencia na validacao
- o ridge autoregressivo e desafiante forte no teste, mas perde demais na validacao
- `rich_lags_only` aparece forte no teste, mas vem de uma janela curta diferente e nao e comparacao decisiva
- a decisao correta agora e manter os tres caminhos no radar, com persistencia como referencia obrigatoria
- antes de STGNN, falta testar se a regra segmentada se mantem em outra janela ou validacao temporal adicional
