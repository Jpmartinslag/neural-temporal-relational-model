# HERALD 87 — reponderação dinâmica compartilhada do commuting

**Status:** especificação pré-implementação
**Dependência:** HERALD 86 e DEC-123/124
**Âmbito:** relevância dinâmica de fluxos observados, não descoberta de uma rede arbitrária.

## 1. Arquitetura

O HERALD 85 tentou recuperar uma matriz territorial livre a partir de poucos vetores anuais
e falhou por não-identificabilidade. O candidato restringe o suporte ao commuting oficial e
compartilha a função de peso entre todos os pares:

`delta_ij,t = MLP([h_i,t, h_j,t, |h_i,t-h_j,t|, h_i,t*h_j,t, log(1+C_ij)])`

`A_dense[t] = row_normalize(C * exp(clip(delta_t,-1,1)))`

`A_prop[t] = topk_row_normalize(A_dense[t], k=28)`.

`h_i,t` usa somente níveis e máscaras causalmente disponíveis de Urssaf, desemprego, SIDE,
stock e emprego FLORES total. FLORES A17 não entra no braço primário porque ainda não existe
uma transformação A17→A10 semanticamente fechada. Não há embedding de ZE, tabela por par ou
parâmetro por aresta.

O top-k limita somente a propagação. `A_dense` é exportado integralmente: fluxo fraco
observado não é apagado nem chamado de ruído por ficar fora do top-k.

## 2. Objetivo sem caminho caroneiro

Uma Ridge causal local, incluindo reversão à média e médias nacionais setoriais, é ajustada
somente no treino e congelada. A única saída treinável do modelo relacional é

`r_hat[t+1,:,s] = beta_s * A_prop[t] @ centered_growth[t,:,s]`.

Não há head node-only, skip local treinável ou supervisão direta das arestas. A verdade do
gerador é usada somente na avaliação. Previsão total é baseline congelado mais resíduo.

## 3. Interpretação

A restrição não afirma descobrir relações fora do commuting. Ela testa quando e quanto
fluxos oficiais importam. Isso troca liberdade estrutural por afirmação mais estreita e
auditável. A função compartilhada permite testar generalização sem parâmetros próprios por
zona ou par, mas essa generalização será medida, não presumida.

Serão reportados parâmetros, transições de treino, posto dos vetores propagados, estabilidade
entre seeds e correlação entre `A_dense` aprendido e verdade sintética. Peso alto não será
chamado de causalidade.

## 4. Controles emparelhados

1. commuting estático, sem reponderação;
2. identidades do commuting permutadas, pesos preservados;
3. cenário nulo HERALD 86;
4. `dynamic_sparse`, com a mesma verdade e mais ausência/sobredispersão.

O controle de scorer constante é o próprio commuting estático: uma constante multiplica
todas as arestas de uma linha e desaparece na normalização. Ele não constitui um quinto
braço independente.

Todos usam os mesmos folds, seeds, baseline local e seleção. Nenhum controle recebe fonte
adicional.

## 5. Avaliação

- cinco seeds e origens rolantes;
- seeds de inicialização `42,43,44,45,46`; origens de pontuação `2021–2025`;
- para cada origem `τ`, treino usa todos os alvos até `τ-3`, valida em `τ-2,τ-1`,
  seleciona a menor época empatada no sweep `25,50,100,200`, reinicializa e refaz em
  treino+validação; o alvo `τ` é pontuado uma vez;
- para cada seed, a métrica do gate é a média dos seus cinco origins; os gates contam seeds,
  não origins, que não são independentes;
- recuperação avaliada entre arestas candidatas do commuting;
- eventos são mudanças do top-k; pesos densos também são avaliados continuamente;
- folds de zonas impedem que o resultado dependa de memorizar uma ZE.
- qualquer proxy estática de zona no painel real deve ser calculada apenas no período de
  treino do fold; não pode resumir anos de validação ou pontuação.

Gates eliminatórios são os do HERALD 86: falso positivo no nulo `<=0,10`, F1 de arestas
`>=0,50`, F1 de eventos `>=0,30`, estabilidade entre seeds `>=0,80` e queda máxima de 0,20
no cenário esparso. O smoke de uma seed verifica apenas execução, gradientes, ausência de
leak e exportação; não toma decisão científica.

## 6. Guardas antes do smoke

1. nenhum parâmetro contém identidade de zona ou par;
2. perturbar dados futuros não altera `A_dense[t]` nem a loss até `t`;
3. retirar uma fonte equivale a máscara zero, nunca valor zero;
4. gradiente da loss residual chega ao scorer e aos `beta_s`;
5. nenhum head direto consegue minimizar a loss;
6. suporte denso é exatamente o commuting, enquanto top-k é somente propagação;
7. prior permutado preserva graus e multiconjunto de pesos, mas muda identidades;
8. exportação em `eval()` é determinista;
9. runtime spies confirmam execução de todos os controles;
10. métricas de recuperação pontuam somente arestas adicionadas ao top-k do prior, e não
    recebem crédito pelas arestas estáticas já conhecidas;
11. o F1 de eventos distingue explicitamente nascimento de morte; cada guarda mata seu
    mutante correspondente.

Somente depois dessas guardas o código segue para auditoria externa e, se aprovado, recebe
um smoke no `meso`.

## 7. Sensibilidade de capacidade após o primeiro gate completo

O primeiro array conhecido-verdade não passou recuperação de arestas ou eventos. Uma única
sensibilidade OFAT é autorizada antes de alterar loss, features ou top-k: largura oculta
`32,64,128`, mantendo embedding 8, dropout 0,2, learning rate 1e-3, top-k 28, seeds, origens,
dados e seleção de época idênticos. O valor 64 é o valor fundamentado no HERALD 70; 32 é a
implementação corrente e 128 é a sensibilidade de capacidade. O alvo 0,60 é reportado, mas
não substitui os gates pré-declarados 0,50/0,30. Ganho só é atribuível à capacidade se for
pareado nas seeds e não elevar o nulo acima de 0,10 nem baixar estabilidade abaixo de 0,80.
