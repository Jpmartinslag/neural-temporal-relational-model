# Local Feature Engineering Plan v0

Data: 2026-04-16

## Objetivo

O baseline temporal atual (`ridge_lag_only` com 7.66% WMAPE e persistência com 7.68% WMAPE) é muito forte. As features locais candidatas (SITADEL, Energia, REI) estão introduzindo instabilidade porque os níveis brutos ou lags simples contêm artefatos de escala, choques localizados (especialmente em construção) ou não-estacionariedade de tendência que modelos lineares têm dificuldade de generalizar.

Para melhorar a estabilidade e superar o baseline robustamente, o espaço de features deve mudar de **níveis absolutos** para **dinâmicas invariantes de escala** e **razões estruturais**.

## 1. Transformações Metodologicamente Válidas

Assumindo que o alvo de predição é o ano $t+1$, todas as features devem ser computadas usando dados estritamente disponíveis até o final do ano $t$.

*   **Diferença Logarítmica (Aproximação de Crescimento YoY):** $\ln(X_t + 1) - \ln(X_{t-1} + 1)$. **Altamente Válida.** Superior à variação percentual simples porque é simétrica, lida naturalmente com grandes variâncias entre zonas pequenas e grandes, e comprime outliers extremos de crescimento.
*   **Médias Móveis (2 ou 3 anos):** $\frac{1}{k} \sum_{i=0}^{k-1} X_{t-i}$. **Altamente Válida.** Essencial para SITADEL (construção), que é inerentemente irregular. Suaviza a atividade passada fornecendo um baseline mais estável do momentum econômico local.
*   **Intensidade por Estabelecimento:** $X_t / E_t$ (onde $E_t$ é o estoque de estabelecimentos no ano $t$). **Válida.** Normaliza o consumo de energia ou base fiscal pelo tamanho da economia local.
*   **Razão Eletricidade/Gás (ou Mix de Energia):** $Elec_t / (Elec_t + Gas_t)$. **Válida.** Captura a composição estrutural da economia local (ex: transição de manufatura pesada para serviços).
*   **Volatilidade Histórica:** Desvio padrão de $\ln(X)$ sobre a janela $[t-3, t]$. **Válida.** Permite ao modelo distinguir entre zonas estruturalmente estáveis e erráticas.

## 2. Transformações Arriscadas (Risco de Leakage)

*   **Intensidade com Denominador Futuro:** Calcular intensidade per capita ou por estabelecimento usando dados do ano $t+1$. *Solução: Usar estritamente o denominador do ano $t$ ou $t-1$.*
*   **Scaling/Standardization Global:** Aplicar `StandardScaler` sobre todo o dataset antes do split de validação cruzada. A média/variância do futuro vazaria para o treino do passado.
*   **Imputação Global:** Preencher valores ausentes em anos iniciais usando a média/mediana de toda a coluna.
*   **Denominadores Derivados do Target:** Usar as *criações* do ano $t$ como denominador para uma feature no ano $t$ para prever criações em $t+1$.

## 3. O Que Testar Primeiro e Por Quê

1.  **Diferenças Logarítmicas (Momentum de 1 e 2 anos):** Removem a escala absoluta da zona (que a persistência já resolve) e isolam a *aceleração* ou *desaceleração* da economia local.
2.  **Médias Móveis SITADEL:** Suavizam choques de permissões de construção, gerando coeficientes mais estáveis do que picos de um único ano.
3.  **Razões Estruturais/Intensidade:** Como a base CFE dividida pelo estoque total de estabelecimentos, medindo a pegada fiscal média das empresas locais.

## 4. Tabela Compacta de Features

| feature_name | source | formula | timing rule | safety | expected benefit | leakage risk |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `energy_nonres_log_diff_1y` | SDES | $\ln(E_t) - \ln(E_{t-1})$ | strictly past | forecast-safe | Captura aceleração econômica de curto prazo, invariante à escala. | Baixo |
| `energy_elec_gas_ratio_t` | SDES | $Elec_t / (Elec_t + Gas_t)$ | strictly past | forecast-safe | Captura mudanças estruturais (terciarização vs. indústria). | Baixo |
| `sitadel_nonres_roll_mean_2y` | SITADEL | $(S_t + S_{t-1})/2$ | strictly past | forecast-safe | Suaviza choques voláteis e irregulares de construção. | Baixo |
| `rei_cfe_base_per_estab_t` | REI | $CFE\_Base_t / Stock_t$ | strictly past | forecast-safe | Mede a pegada fiscal média/tamanho das empresas locais. | Médio (Garantir que $Stock_t$ é histórico) |
| `target_proxy_log_diff_1y` | SIDE | $\ln(Y_t) - \ln(Y_{t-1})$ | strictly past | forecast-safe | Sinal de momentum autorregressivo para complementar a persistência. | Baixo |
| `energy_nonres_volatility_3y` | SDES | $std(\ln(E_{t-2}), \ln(E_{t-1}), \ln(E_t))$ | strictly past | forecast-safe | Identifica zonas instáveis para regularizar predições. | Baixo |
| `sitadel_q1_nowcast_log` | SITADEL | $\ln(S_{Q1, t+1} + 1)$ | current yr Q1 | **nowcast** | Forte indicador inicial de intenção de construção no ano corrente. | **Alto** (Isolar estritamente para modelos nowcast) |

## 5. Protocolo de Validação Sugerido

Para provar definitivamente que uma feature supera o `ridge_lag_only`, o loop de validação deve aplicar limites temporais estritos:

1.  **Validação Cruzada de Origem Rolante (Rolling Origin):**
    *   Fold 1: Treino $\le 2020$, Validação $2021$, Teste $2022$
    *   Fold 2: Treino $\le 2021$, Validação $2022$, Teste $2023$
    *   Fold 3: Treino $\le 2022$, Validação $2023$, Teste $2024$
2.  **Execução de Pipeline por Fold:**
    *   **Imputação:** Calcular medianas de imputação *apenas* no subset de Treino do fold atual.
    *   **Scaling:** Ajustar `StandardScaler` *apenas* no subset de Treino.
3.  **Seleção Estrita de Features:** Otimizar a seleção usando apenas os conjuntos de Treino/Validação. O Teste de cada fold fica bloqueado até o modelo estar congelado.
4.  **Métrica de Avaliação:** Rastrear tanto a **Média do WMAPE** quanto o **Desvio Padrão do WMAPE** entre os folds de teste. Um modelo que reduz levemente a média mas dobra a variância deve ser rejeitado.

## 6. Lista Ranqueada de 10 Features Candidatas para Implementação

Implementar estritamente como features históricas ($T$) para prever criações em $T+1$:

1.  **`energy_nonres_log_diff_1y`**: (SDES) Aceleração de curto prazo do uso de energia não-residencial.
2.  **`sitadel_nonres_roll_mean_2y_log`**: (SITADEL) Log da média móvel de 2 anos de superfícies não-residenciais autorizadas.
3.  **`target_side_log_diff_1y`**: (SIDE) Diferença logarítmica de 1 ano do próprio target (momentum autorregressivo).
4.  **`target_side_roll_mean_3y_log`**: (SIDE) Log da média móvel de 3 anos de criações históricas (âncora de baseline).
5.  **`rei_cfe_base_log_diff_1y`**: (REI) Diferença logarítmica de 1 ano da base CFE (proxy para expansão imobiliária comercial).
6.  **`energy_elec_share_t`**: (SDES) Consumo de eletricidade como porcentagem do consumo total (Eletricidade + Gás) no ano T.
7.  **`sitadel_nonres_volatility_3y`**: (SITADEL) Desvio padrão das superfícies autorizadas nos últimos 3 anos.
8.  **`rei_cfe_base_per_estab_t`**: (REI / SIDE) Base CFE dividida pelo estoque total de estabelecimentos no ano T.
9.  **`energy_nonres_log_diff_2y`**: (SDES) $\ln(E_t) - \ln(E_{t-2})$ para capturar momentum de médio prazo, ignorando anomalias de um único ano.
10. **`target_side_acceleration_t`**: (SIDE) Diferença das diferenças: $(\ln(Y_t) - \ln(Y_{t-1})) - (\ln(Y_{t-1}) - \ln(Y_{t-2}))$. Captura se o crescimento de criações está acelerando ou desacelerando.

## 7. Codex Implementation Review

Status: partially useful as a research direction, not validated for canonical inclusion.

Implemented forecast-safe families:

- SIDE target momentum: log-diff, 2-year log-diff, 3-year rolling mean, acceleration.
- Energy: total non-residential log-diff, 2-year log-diff, 3-year volatility, electricity/gas shares, delivery-point log-diff.
- REI: CFE base/product/articles log-diff and base volatility.
- SITADEL: 2-year rolling log mean and 3-year volatility for authorized/started non-residential surfaces.

Rolling WMAPE result:

| Model | Mean WMAPE | Reading |
| :--- | :---: | :--- |
| `ridge_local_all` | `7.65%` | Still best candidate, but unstable |
| `ridge_lag_only` | `7.66%` | Current benchmark |
| `persistence` | `7.68%` | Strong baseline |
| `ridge_engineered_sitadel` | `7.97%` | Best engineered family, still below benchmark |
| `ridge_engineered_energy` | `8.04%` | Energy transformations did not improve enough |
| `ridge_engineered_target` | `8.77%` | Target momentum features unstable in Ridge |
| `ridge_engineered_rei` | `15.35%` | REI log-diff/volatility unstable |
| `ridge_engineered_all` | `16.89%` | Overreacts/overfits linearly |

Decision:

- Do not promote engineered features to the canonical tensor.
- Keep this plan as an experimental feature-engineering record.
- Avoid adding more raw feature families until there is a stability-oriented selection rule.
- Denominator-based intensity features remain postponed until historical establishment stock timing is audited.
