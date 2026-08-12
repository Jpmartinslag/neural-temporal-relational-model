# HERALD 86 — benchmark sintético multifuente francês

**Status:** pré-registo de engenharia, antes de qualquer treino científico
**Âmbito:** 280 ZE2020 atuais, nove setores A10, França apenas
**Objetivo:** verificar se uma arquitetura consegue recuperar relações conhecidas e manter
incerteza honesta quando as fontes são curtas, voláteis ou ausentes.

## 1. O que este benchmark decide

O benchmark não tenta provar que as relações sintéticas existem em França. Ele decide uma
questão anterior: se uma relação conhecida existir sob condições parecidas com o painel
francês, o método consegue recuperá-la sem inventar arestas no nulo?

Boa previsão não compensa má recuperação do grafo. O teste francês real só é autorizado
depois de passarem separadamente especificidade no nulo, recuperação de arestas, recuperação
de eventos datados e robustez a fontes ausentes.

## 2. Dimensões e calendário

- anos: 1998–2025, 28 passos;
- territórios: 280 ZE2020;
- setores: nove A10 (`BE,FZ,GI,JZ,KZ,LZ,MN,OQ,RU`);
- nó atómico: `ZE × setor`;
- commuting: prior observado no papel do grafo estrutural, com snapshots sintéticos em
  2012, 2017 e 2022;
- toda simulação menor usada em guardas deve conservar as mesmas regras, mudando somente as
  dimensões.

## 3. Fontes simuladas e janelas

| fonte sintética | forma | janela | papel |
|---|---:|---:|---|
| Urssaf anual: estabelecimentos, emprego privado, massa salarial | ZE×ano | 1998–2024 | `CORE_LONG` |
| desemprego localizado | ZE×ano | 2003–2025 | `CORE_LONG` |
| SIDE criações | ZE×A10×ano | 2012–2025 | `CORE_TARGET` |
| SIDE stock ativo | ZE×A10×ano | 2014–2024 | `ENRICHMENT_SHORT` |
| FLORES estabelecimentos | ZE×A17×ano | 2017–2024 | `ENRICHMENT_SHORT`, nível apenas |
| FLORES emprego assalariado total | ZE×ano | 2017–2024 | `ENRICHMENT_SHORT`, nível apenas |

As fontes permanecem semanticamente separadas. Não se calcula `criações/stock`, não se
encadeia CLAP com FLORES, não se calcula crescimento entre milésimos FLORES e emprego Urssaf
privado nunca é tratado como emprego FLORES total.

## 4. Verdade geradora

Um estado latente causal produz tendências territoriais, setoriais e nacionais. A dinâmica
territorial do mesmo setor usa

`g[t+1,:,s] = AR_s g[t,:,s] + macro[t,s] + beta A[t] g[t,:,s] + epsilon`.

`A[t]` começa no prior de commuting e nunca cria suporte fora dele. Uma função compartilhada
e conhecida pelo gerador, mas não pelo modelo, repondera cada fluxo usando características
observáveis das zonas e cinco regimes (2012, 2017, 2020, 2021 e 2022). O grafo denso conserva
todas as arestas observadas; nascimentos e mortes referem-se somente à entrada e saída no
top-k de propagação. O gerador exporta `A[t]`, o desvio denso, as identidades e os anos dos
eventos. O cenário nulo usa as mesmas marginais e choques, mas nenhum efeito relacional.

As fontes observadas são medições distintas do estado latente, com ruído de contagem
sobredisperso. O choque de 2020–2021 e as quebras Urssaf de 2021 e 2023 são metadados
explícitos, não relações.

## 5. Ausência e informação disponível

- ausência é `NaN` com máscara zero;
- zero observado é `0` com máscara um;
- cada fonte mantém sua janela estrutural;
- faltas de blocos ZE×ano e faltas dependentes de baixo volume são simuladas separadamente;
- `release_year <= decision_year` é obrigatório para uma observação entrar num prefixo;
- alterar qualquer valor posterior a `t` não pode mudar entradas disponíveis até `t`.

O gerador completo conserva a verdade em um bloco `truth`. A interface de modelo recebe
somente `inputs`; as chaves de verdade são proibidas nessa interface.

## 6. Cenários mínimos

1. `null`: mesmas tendências, choques, quebras e missingness; nenhuma mutação relacional.
2. `stable`: commuting útil, sem nascimento ou morte.
3. `dynamic`: commuting mais arestas que nascem e morrem em anos conhecidos.
4. `dynamic_sparse`: mesma verdade de `dynamic`, maior sobredispersão, zeros e blocos ausentes.

Não haverá grade exploratória de arquiteturas. Uma arquitetura candidata será comparada aos
mesmos quatro cenários e seeds.

## 7. Gates científicos pré-declarados

Em cinco seeds, todos estes grupos são eliminatórios:

1. **Nulo:** taxa de falsas arestas adicionadas `<= 0,10` em pelo menos 4/5 seeds.
2. **Arestas:** F1 de arestas adicionadas `>= 0,50` em pelo menos 4/5 seeds no `dynamic`.
3. **Eventos:** F1 de nascimentos/mortes datados `>= 0,30` em pelo menos 4/5 seeds.
4. **Estabilidade:** correlação mediana do desvio recuperado entre seeds `>= 0,80` após
   alinhamento apenas quando a parametrização exigir alinhamento.
5. **Robustez:** no `dynamic_sparse`, F1 de arestas não pode cair mais de 0,20 absoluto
   relativamente ao `dynamic` em mais de uma seed.
6. **Informação:** nenhum resultado usa observação cuja publicação sintética seja posterior
   ao ano de decisão.

MSE, MAE, macro-F1 e ranking são auxiliares. Não resgatam falha relacional.

## 8. Guardas antes do treino

As guardas devem provar: dimensões e janelas; determinismo; zero diferente de ausência;
causalidade de prefixo e release; ausência de eventos no nulo; presença de eventos no
dinâmico; separação semântica das fontes; contagens válidas e sobredispersas; e impossibilidade
de acessar `truth` pela interface de entrada. Cada guarda precisa matar um mutante deliberado.

## 9. Regra de progressão

1. guardas e mutantes locais;
2. smoke de uma seed no `meso`;
3. somente se o smoke for mecanicamente válido, cinco seeds por cenário;
4. somente se os gates relacionais passarem, avaliação nas 280 ZE reais;
5. Córsega e outros universos ficam fora desta rodada.
