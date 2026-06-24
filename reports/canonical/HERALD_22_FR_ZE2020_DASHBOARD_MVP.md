# HERALD 22 — France ZE2020 Dashboard MVP

**Created:** 2026-06-24. **Status:** `DASHBOARD_MVP_READY`. Primeiro dashboard
exploratório específico do bloco França/ZE2020 — separado e independente dos
dashboards Observatory (v0.3/v0.4/v0.5/v0.5.1), que permanecem intocados.

**Objetivo:** demonstrar visualmente a cadeia já auditada — previsão controlada
(persistence/ridge) + leitura descritiva/setorial + camada relacional exploratória
(HERALD_20/21) — para uma ZE2020 selecionada. Não cria nenhuma metodologia, não treina
nada, não otimiza previsão, não gera recomendação.

---

## Arquivo

- **Builder:** `src/data/france_ze2020/build_fr_ze2020_dashboard_mvp.py`
- **Output:** `reports/dashboards/fr_ze2020_dashboard_mvp.html` (HTML estático,
  Plotly embarcado localmente — mesma técnica já usada por
  `build_observatory_v04_dashboard.py`, duplicada como utilitário pequeno, não
  importada, para não acoplar este MVP francês à trilha europeia não relacionada)

## Arquivos lidos (todos read-only, canônicos ou já auditados)

```
data/processed/france_ze2020/fr_ze2020_clean_panel.csv               (série observada)
data/processed/france_ze2020/fr_ze2020_baseline_predictions_v1.csv   (previsão persistence/ridge --
                                                                        regenerável; se ausente, painel
                                                                        de previsão mostra só observado)
data/processed/france_ze2020/fr_ze2020_sector_panel.csv               (composição setorial descritiva)
data/processed/france_ze2020/fr_ze2020_sector_relational_features.csv (setor dominante, diversidade)
data/processed/france_ze2020/fr_ze2020_sector_graph_predictions_v1.csv (opcional -- comparação setor
                                                                        real vs. previsto, sector_graph_smoke)
data/processed/france_ze2020/fr_ze2020_exploratory_relation_signals.csv
data/processed/france_ze2020/fr_ze2020_exploratory_relation_examples.csv
data/external/ze2020_geometry.geojson                                  (geometria do mapa)
```

Nunca lê `dynamic_stgnn_feature_panel*`, `graph_adjacency_core_v0.csv`/
`graph_adjacency_mobility_v0.csv`, nem `train_herald_v6/v7/semi_v2/regime_experiment`
(verificado por teste).

---

## Geometria ZE2020 (Parte 1)

**Encontrada e confiável.** `data/external/ze2020_geometry.geojson` — já usada pelos
dashboards Observatory v0.3/v0.4 (`reports/HERALD_METHODOLOGICAL_DECISION_LOG.md`,
linha ~1131). 306 features no arquivo total (inclui Córsega+DOM), propriedade `ze2020`
já vem como string zero-padded de 4 caracteres.

**Cobertura verificada nesta pass:** join contra o painel canônico (280 zonas) —
**280/280 cobertos, 0 faltando.** As 26 features restantes do arquivo (306−280)
correspondem exatamente às zonas Córsega/DOM já excluídas por design metodológico
(HERALD_15 §4). O builder filtra a geometria para as 280 zonas do painel antes de
embutir no HTML — nunca usa as 26 extras.

**Mapa está funcional**, não bloqueado. Se o arquivo de geometria algum dia faltar ou
tiver zero cobertura, o builder retorna `None` e o dashboard mostra o aviso técnico
"Geometria ZE2020 ainda não auditada." em vez de fabricar um mapa — comportamento
testado.

---

## Blocos visuais implementados

### Bloco 1 — Arquitetura (placeholder deliberado)

6 cards vazios, só com o nome da etapa — **nenhum texto metodológico foi inventado**:

1. Dados brutos
2. Tratamento limpo
3. Painel causal / model-ready
4. Camada relacional ZE / setor
5. Modelo / controle preditivo
6. Sinais exploratórios

Cada card mostra literalmente `[conteudo a definir]`. O conteúdo detalhado é decisão
humana futura, fora do escopo desta pass.

### Bloco 2 — Dashboard exploratório

- **Cabeçalho:** título, subtítulo ("Previsão controlada e sinais relacionais
  exploratórios por ZE2020"), caveat global.
- **Mapa:** choropleth Plotly das 280 ZE2020, clicável, 4 métricas de cor selecionáveis
  (valor observado, erro |observado−ridge|, setor dominante, estabilidade relacional
  média).
- **Seletor de ZE2020:** dropdown, sincronizado com clique no mapa.
- **Painel de previsão:** série observada 2012-2025 + pontos previstos
  (persistence/ridge) onde existem (2019-2025) — **rotulado explicitamente como
  controle**, nunca como claim de previsão superior.
- **Painel setorial:** composição setorial (gráfico de barras empilhadas), badge de
  setor dominante + diversidade, e comparação real vs. previsto setorial (só quando
  `fr_ze2020_sector_graph_predictions_v1.csv` existe — rotulado `sector_graph_smoke`,
  com o caveat "não bateu baseline").
- **Painel relacional:** mini-grafo radial (ZE selecionada no centro, até 8 relações
  mais fortes ao redor, espessura=`signal_strength`, opacidade=`stability_score`),
  filtro por `relation_family`, tabelas top-5 por estabilidade e por força do sinal,
  exemplos interpretáveis de `fr_ze2020_exploratory_relation_examples.csv` quando a ZE
  selecionada tem um exemplo curado.

---

## O que é previsão / o que é sinal relacional (repetido deliberadamente)

| | Previsão | Sinal relacional |
|---|---|---|
| Papel | Controle | Objeto de leitura exploratória |
| Fonte | `fr_ze2020_baseline_predictions_v1.csv` (persistence/ridge, já auditado) | `fr_ze2020_exploratory_relation_signals.csv` (HERALD_20/21, já auditado) |
| Linguagem permitida | "previsão", "controle", "erro" | associação, sinal exploratório, correlação, estabilidade, hipótese para especialista |
| Linguagem proibida | "previsão superior" sem evidência | causalidade, prova, recomendação, prescrição |
| Comportamento se faltar dado | Mostra só observado + aviso explícito, nunca fabrica | N/A (sempre presente, já auditado) |

---

## Limitações explícitas

- Bloco 1 (arquitetura) é só espaço reservado — sem narrativa, por design desta pass.
- A comparação setorial real vs. previsto usa `graph_mlp`/`persistence_sector`
  (HERALD_19), que **não bateu baseline** — mostrado com esse caveat, nunca escondido.
- O mini-grafo relacional é uma visualização radial simplificada (não um layout de
  grafo físico/force-directed) — adequado para uma leitura exploratória rápida, não
  para análise topológica.
- `sector_to_sector_comovement` e `temporal_precedence_signal` continuam ausentes
  (lacuna já documentada em HERALD_20, não fabricada aqui).
- Validação visual: **nenhum browser real disponível neste ambiente** (mesma limitação
  já documentada para todos os dashboards Observatory anteriores) — validado
  estruturalmente (JSON embutido válido, IDs de DOM referenciados por JS existem no
  HTML, alvos do `Plotly.newPlot` existem como `<div>`, handlers `onchange`/`onclick`
  referenciam funções definidas) em vez de screenshot. Recomenda-se abrir o arquivo
  manualmente num navegador para confirmação visual antes de apresentar.

---

## Confirmações

- **Sem causalidade:** nenhuma das palavras/colunas proibidas (`causal_effect`,
  `causal_impact`, "causal claim") aparece no HTML (verificado por teste).
- **Sem recomendação automática:** nenhuma coluna/palavra `recommendation`,
  `recommended_action`, `policy_action` (verificado por teste).
- **Sem previsão fabricada:** se `fr_ze2020_baseline_predictions_v1.csv` estiver
  ausente, `build_ze_data` deixa `predictions={}` por zona — testado diretamente
  passando `predictions=None`.
- **Não toca** dashboard Observatory existente, `hpc_results/`, Italy/Austria, dados
  brutos, `train_herald_v6/v7/semi_v2/regime_experiment`, `dynamic_stgnn_feature_panel*`,
  `graph_adjacency_*` legado.

---

## Cross-reference

- Camada relacional exibida: `reports/canonical/HERALD_20_FR_ZE2020_EXPLORATORY_RELATION_SIGNALS.md`
- Auditoria da camada relacional: `reports/canonical/HERALD_21_FR_ZE2020_RELATION_LAYER_AUDIT.md`
- Resultado HPC (previsão não bateu baseline): `reports/canonical/HERALD_19_FR_ZE2020_HPC_SPEC.md`
