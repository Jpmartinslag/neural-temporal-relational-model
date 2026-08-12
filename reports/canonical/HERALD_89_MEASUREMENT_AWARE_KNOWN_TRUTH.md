# HERALD 89 — verdade conhecida consciente da medição

**Estado:** pré-registo, escrito antes de qualquer resultado do HERALD 89.
**Âmbito:** sintético apenas. Nenhuma afirmação sobre França.
**Registo:** DEC-126.

## 1. O que mudou e porquê

O HERALD 88 calibrou o componente relacional para 25% do movimento latente e o oráculo
observável mesmo assim falhou: `A_true` perdeu para `A_permuted` por −0,0054%, com direção
favorável em 3/5 origens. O controlo latente ganhou +3,65% nos mesmos folds. O grafo existe
e a forma da loss está certa; o que falha é o instrumento.

A causa é identificável e mecânica. A formulação `Δlog c` partilha `c_t` entre entrada e
alvo com sinais opostos, o que impõe `corr(g, y) = −0,4975` no observável quando a dinâmica
latente é `+0,399`. O ruído de amostragem de uma única contagem aparece duas vezes, e domina.

**O HERALD 89 corrige o instrumento e mantém a verdade.** Mesmo grafo, mesmos regimes,
mesmo prior, mesma fórmula relacional, mesma razão latente de 0,25.

## 2. Hipóteses

- **H-A.** Prever a contagem futura `c_{t+1}` em vez da diferença adjacente de logs remove
  a colisão de ruído e torna o sinal relacional visível a um oráculo.
- **H-B.** Mesmo com o instrumento correto, o volume das células francesas limita quanto
  se pode recuperar; existe um teto observável que depende da exposição.
- **H-C.** Em células de baixo volume o comportamento correto não é descobrir relações, é
  abster-se e declarar baixa confiança.

As três são testadas separadamente. Confirmar H-A não confirma H-B, e nenhuma delas diz
algo sobre França.

## 3. Instrumento primário

```
c_{t+1} ~ NegativeBinomial(mu_{t+1}, phi)
log mu_{t+1} = log(exposure_t) + a_s + b_s * g_t + d_s * national_t
                                + beta_s * (A_t @ centred(g_t))
```

- `exposure_t` usa apenas informação publicada até `t`;
- `g_t = log1p(c_t) − log1p(c_{t−1})`, também só até `t`;
- `a_s, b_s, d_s, beta_s` e `phi` são estimados **somente nos anos de treino** de cada
  origem;
- o ano retido é pontuado **uma vez**;
- a média futura é positiva por construção, via link log.

O oráculo `A_true` conhece o grafo apenas para testar o instrumento. **Não** recebe
intensidade latente, resíduo latente, `relational_increment` nem qualquer decomposição
interna do gerador.

A regressão de diferenças adjacentes de logs do HERALD 88 permanece implementada como
**controlo negativo**. Nunca é o alvo principal.

## 4. Braços do oráculo

`A_true`, `A_prior`, `A_permuted` (derangement fixo, pesos e graus preservados) e
`null` (`beta = 0`). Avaliação emparelhada: mesmas seeds, mesmas origens, mesmos folds.

**Métrica primária:** redução da deviance/NLL Negative Binomial de `A_true` contra
`A_permuted`. Nunca MSE entre variáveis latentes.

## 5. Três níveis de informação

A topologia verdadeira é idêntica nos três. Só muda a exposição observável.

| nível | construção | pergunta |
|---|---|---|
| **IDENTIFIABLE** | exposição multiplicada pelo menor fator da grade pré-declarada que satisfaça o gate na calibração | o sinal é recuperável quando o observável chega? |
| **FRANCE_REALISTIC** | distribuição empírica de volumes das 280 ZE, heterogeneidade e dispersão realistas | quanto se recupera sob volumes franceses? |
| **LOW_INFORMATION** | quartil inferior da distribuição francesa de volumes | o modelo abstém-se quando não pode saber? |

**Grade de exposição, congelada antes de qualquer execução:**
`exposure_multiplier ∈ {1, 2, 4, 8, 16}`.

Multiplicar exposição significa observar mais unidades da mesma célula, não retirar ruído:
a contagem passa a `NB(M·mu, M·phi)`, cuja variância é `M·(mu + mu²/phi)` e cujo
coeficiente de variação cai exatamente `1/M`. A sobredispersão por unidade é preservada.

Se nenhum fator da grade satisfizer o gate, **o protocolo para**. A grade não é estendida
depois de vista, e o gate de 10% não é baixado.

## 6. Seeds

| papel | seeds |
|---|---|
| calibração do instrumento e escolha do `exposure_multiplier` | **8801–8820** |
| avaliação final: oráculo, representabilidade, fatorial | **8901–8905** |

Disjuntas por construção, e nenhuma delas foi usada no HERALD 88 (que usou 8601 no gerador
e 42–46 no modelo). **As seeds finais não participam de calibração, escolha de instrumento
ou de hiperparâmetros.** Uma guarda verifica a disjunção.

## 7. Ordem dos testes e regras de paragem

```
1. guardas + mutation testing            -> 100% ou pára
2. calibração (8801-8820)                -> congela o exposure_multiplier
3. oráculo observável (8901-8905)        -> falha => STOP, sem braço neural
4. representabilidade (supervisão A_true) -> falha => arquitetura rejeitada
5. fatorial 2x2 sem rótulos de arestas   -> só aqui a loss e o top-k são julgados
```

**Gates eliminatórios do oráculo, no IDENTIFIABLE, nas cinco seeds finais:**

- `A_true` melhora a deviance/NLL em **≥ 10%** contra `A_permuted`;
- direção favorável em **≥ 4/5** seeds;
- `A_true` bate também `A_prior`;
- o cenário `null` não mostra ganho relacional;
- nenhum diagnóstico latente entra na avaliação observável.

Para `FRANCE_REALISTIC` e `LOW_INFORMATION` **não** se exige recuperação de 50%. Reporta-se
o teto observável estratificado por exposição, variância NB estimada, setor e origem.

## 8. Métricas de arestas e eventos

- evento tipado `(origem, destino, ano, birth|death)`, agregação **micro** sobre todas as
  origens;
- anos sem eventos verdadeiros **não** recebem F1 = 0; reportam `false_event_rate`;
- nascimentos e mortes têm precision, recall e F1 **separados**;
- commuting já presente no prior **não** recebe crédito como aresta aprendida;
- o top-k de propagação **não** define sozinho o grafo denso exportado.

Para `LOW_INFORMATION`, adicionalmente: cobertura de decisões, taxa de abstenção, precisão
condicional entre relações emitidas, false discovery rate, e calibração confiança-acerto.

## 9. Gates do fatorial (etapa 5)

`edge F1 ≥ 0,50` no IDENTIFIABLE; `event micro-F1 tipado ≥ 0,30`; `dense correlation ≥
0,30`; `null predicted-added-edge-rate ≤ 0,10`; estabilidade entre seeds ≥ 0,90; o ganho não
pode depender apenas do prior; e no LOW_INFORMATION o FDR tem de ficar controlado com
abstenção disponível.

**Boa previsão com recuperação de arestas falhada continua a ser rejeição para descoberta
relacional.**

## 10. Diagnóstico contra evidência

A supervisão direta por `A_true` é **diagnóstico de representabilidade**. Responde a "esta
arquitetura consegue exprimir a regra?", nunca a "este método funciona em França", onde não
existem rótulos de arestas. Nenhum resultado do HERALD 89 é evidência sobre relações
económicas francesas.

Relações são descritas como **associação, precedência temporal e impacto preditivo**, nunca
como causalidade estrutural.

## 11. O que não pode ser reaberto

Não baixar o gate de 10% depois de ver resultados; não aumentar largura, rank, LR ou
épocas; não correr França real; não usar variáveis latentes como entrada ou alvo; não
reduzir ruído globalmente até o teste passar; não adicionar a Córsega nesta ronda — o âmbito
continua a ser as 280 ZE atuais.
