# HERALD 84 — diagnóstico-oráculo de utilidade relacional

## Pergunta

O benchmark HERALD83 mostrou que HERALD82 representa, mas não recupera, um
grafo dinâmico conhecido. Antes de alterar a arquitetura, este diagnóstico
separa duas hipóteses:

1. o sinal relacional observável não é utilizável nem com o grafo verdadeiro;
2. o sinal existe, mas o caminho preditivo direto consegue ignorar o grafo.

## Desenho congelado antes da execução

- cenário: `rep_strong_clean`;
- uma seed de modelo (`0`), 100 épocas, peso de magnitude `0.1`;
- mesmo painel, folds e inicialização nas três condições;
- `true`: adjacência dinâmica verdadeira fixada;
- `prior`: adjacência commuting estática fixada;
- `permuted`: adjacência verdadeira com identidades de zona permutadas por
  uma derangement fixa, preservando pesos e dinâmica;
- pontuação somente no último ano.

O segundo braço ajusta, nos anos anteriores, um único coeficiente para

`r[t+1] = beta * (A[t] - A_prior) @ centered_growth[t]`.

Ele é avaliado tanto com crescimento latente (controle positivo) quanto com
crescimento reconstruído das contagens (teste observável).

## Regras de decisão

- `signal_exists`: no braço observável, correlação do grafo verdadeiro >= 0.30
  e redução de MSE >= 20% contra o grafo permutado; no controle latente,
  correlação >= 0.90.
- `current_model_uses_graph`: o grafo verdadeiro reduz MAE >= 5% contra prior
  e permutado e aumenta rho >= 0.05 contra ambos.

Interpretação:

- sinal falha: não reescrever o modelo; corrigir tarefa/gerador/observabilidade;
- sinal passa e modelo falha: atalho preditivo confirmado; implementar objetivo
  residual relacional;
- ambos passam: o problema está na aprendizagem/identificação do grafo livre.

Este é um diagnóstico exploratório com regra de parada, não uma nova evidência
sobre relações francesas.
