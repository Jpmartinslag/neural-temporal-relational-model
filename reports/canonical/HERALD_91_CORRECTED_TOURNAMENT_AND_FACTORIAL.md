# HERALD 91 — torneio corrigido e fatorial multissinal

**Registos:** DEC-128, DEC-129 e DEC-130.
**Estado atual:** `FINAL_MAJOR_EXPERIMENT_PENDING_CORRECTED_RERUN`.
**Estado do HERALD 90:** `EXPLORATORY_CANDIDATE_FOUND_BUT_MULTISIGNAL_STOP_INVALIDATED_BY_AUDIT`
— reclassificado, com os números originais preservados.
**Âmbito:** 280 ZE2020, sem Córsega.

## 1. Política de vintage — decidida por medição

O painel atribui **uma única data de publicação por fonte a todo o histórico**: Urssaf
trimestral `2026-06-19` para 1998–2026; Urssaf anual `2025-09-17` para 1998–2024; desemprego
`2026-06-19` para 2003–2026; SIDE criações `2026-04-14` para 2012–2025. Não existem vintages
históricos recuperáveis, logo não há join as-of possível.

Esta linha é formalmente **`RETROSPECTIVE_FINAL_VINTAGE_ANALYSIS`**:

- o alinhamento é causal **por período de observação**;
- os **valores** são os finais revistos;
- **não** se afirma que reproduzem o que era conhecido na época;
- risco de revisão **não quantificado**;
- **não** serve como validação prospetiva;
- nenhuma data histórica fictícia é criada.

A guarda correspondente distingue «`release_date` aparece no código» de «a disponibilidade é
efetivamente aplicada»: verifica que o painel tem uma só data por fonte e que o módulo
declara a política, em vez de aceitar a presença da coluna como prova.

## 2. Procedência real

| sinal | fonte bruta | coluna usada | transformação | freq. | vintage | ex ante? | limitações |
|---|---|---|---|---|---|---|---|
| efetivos privados | open.urssaf ZE regionalizada | `effectifs_salaries_brut` | soma das partes regionalizadas validada contra totais região×setor | T | final 2026-06-19 | **não** | sem dimensão setorial na fonte |
| massa salarial | open.urssaf ZE regionalizada | `masse_salariale_brut` | idem | T | final 2026-06-19 | **não** | idem |
| estabelecimentos empregadores | open.urssaf ZE anual | `nombre_d_etablissements` | idem | A | final 2025-09-17 | **não** | idem |
| desemprego localizado | Insee `chomage-zone`, folha `txcho_ze` | taxa CVS | **já ajustada sazonalmente pelo publicador** | T | final 2026-06-19 | **não** | local de residência, não de trabalho |
| criações | Insee SIDE, comunal agregado a ZE | contagens A10 | soma comunal → ZE2020 | A | final 2026-04-14 | **não** | só 14 anos |
| stock ativo | Insee SIDE `DS_SIDE_STOCKS_COM` | `UNIT_LOC` | leitura direta a nível ZE2020 | A | final 2026-07-23 | **não** | só 11 anos; revisto retroativamente (+2,12% em 2023) |

O sufixo `_raw` significa **não ajustado sazonalmente**, nunca «dado bruto da fonte»: todos
já foram agregados e harmonizados. Urssaf e desemprego **não têm** dimensão setorial ao nível
ZE — `TOTAL` é uma propriedade da fonte, não uma escolha.

## 3. Unidade de replicação

Nunca se escreve «5 replicações» quando só o placebo mudou. Reportam-se separadamente:

- **origens temporais** — a única contagem de unidades genuinamente distintas;
- **sorteios de placebo** — formam a distribuição nula e produzem um p-valor;
- **seeds de modelo** — só existem quando há rede;
- **observações efetivas** por origem.

## 4. Complementaridade não é bloqueada por triagem individual

A regra do HERALD 90 «o oráculo multissinal exige ≥2 sinais individualmente informativos» é
**removida**. Ela testa o oposto da hipótese: sinais podem falhar isolados e funcionar juntos
por complementaridade, supressão, interação, defasagens distintas, redução conjunta de ruído
ou informação condicional. A autorização para testar combinações depende de dados
disponíveis, guardas, controlos válidos e orçamento — não de duas vitórias marginais. Isto
autoriza apenas o experimento sintético/mecânico, nunca alegações francesas.

## 5. Definições congeladas

**Complementaridade.** Uma combinação é complementar apenas se, cumulativamente: melhorar o
melhor componente individual; o ganho incremental leave-one-signal-out for positivo para pelo
menos um sinal; e o braço de sinal duplicado **não** reproduzir o mesmo ganho.

**Redundância.** Dois canais são redundantes se o ganho conjunto não exceder o do braço
duplicado dentro do intervalo entre seeds.

**Abstenção.** Uma célula recebe abstenção quando a confiança estimada cai abaixo do limiar
declarado antes da execução; cobertura, taxa de abstenção, precisão condicional e FDR são
reportadas para o estrato de baixa informação.

## 6. Braços, congelados antes de qualquer seed final

**Individuais:** `I1` efetivos · `I2` massa salarial · `I3` estabelecimentos empregadores ·
`I4` desemprego · `I5` criações · `I6` modelo HERALD 87 sem alteração, como referência
histórica.

**Combinações:** `C1` I1+I2 · `C2` I1+I4 · `C3` I1+I3 · `C4` I1+I2+I3 · `C5` I1+I2+I4 ·
`C6` I1+I2+I3+I4 · `C7` C6+I5 · `C8` C7 + stock ativo.

**Redundância:** `R1` emprego duplicado em dois canais · `R2` emprego + cópia minimamente
perturbada de si próprio.

**Larguras:** 32, 64, 128. **Nunca 256.** Constantes entre braços: seeds, folds, learning
rate, rank, top-k, épocas candidatas, patience, inicialização emparelhada, regra de seleção.
Um mecanismo muda por braço.

**Seeds:** calibração do gerador `9301–9320`; avaliação final `9401–9405`. Disjuntas e novas.
Nenhuma seed final participa da calibração de intensidade, de pesos de loss ou da escolha de
largura.

## 7. Cenários sintéticos

`S0` NULL · `S1` SHARED · `S2` PARTIAL_SHARED · `S3` COMPLEMENTARY (nenhum sinal isolado
basta, a combinação basta) · `S4` REDUNDANT · `S5` CONFLICTING.

**Orçamento declarado antes da execução:** conjunto principal `S0, S1, S3, S4`; extensão
`S2, S5`. A seleção é declarada aqui e não depende de resultados.

O gerador reproduz as distribuições medidas no painel francês — escalas, volumes,
sazonalidade, autocorrelação, correlação entre sinais, sobredispersão, quebras como
perturbação, células de baixa informação, frequências mistas, máscaras e defasagens de
publicação. A verdade relacional é criada **antes** das observações e nenhuma feature a
reconstrói. A intensidade é calibrada por oráculos observáveis nas seeds de calibração e
congelada antes das seeds finais; **não** é ajustada até a rede atingir 50–70%.

## 8. Gates, congelados

`edge F1 ≥ 0,50`; `dense correlation ≥ 0,30`; `event F1` tipado `≥ 0,30`; estabilidade entre
seeds `≥ 0,90`; `predicted-added-edge-rate` no NULL `≤ 0,10`; AUPRC acima da prevalência; a
combinação melhora o melhor sinal individual; o sinal duplicado **não** reproduz o ganho.

**Boa previsão com recuperação de arestas má não autoriza descoberta relacional.**
A faixa 50–70% é resultado desejável, nunca parâmetro de calibração do gerador.

**Promoção de largura.** A triagem em `hidden=64` não força vencedores por ranking.
Um braço só segue para `32/128` se cumprir pelo menos um critério absoluto:

- `dense correlation >= 0,30`; ou
- `edge F1 >= 0,50`; ou
- complementaridade válida: melhora o melhor individual, tem contribuição incremental
  leave-one-signal-out, mantém o nulo controlado e não é reproduzida pelo sinal duplicado.

Se nenhum braço cumprir um critério, nenhum é promovido. `R1` e `R2` acompanham braços
promovidos como controlos; não autorizam sozinhos uma fase de largura. A regra anterior
"três melhores em edge F1" fica proibida porque sempre escolheria três braços, mesmo se
todos falhassem.

## 9. Ordem e paragens

```
1. inferência corrigida         (implementada e protegida por guardas)
2. torneio corrigido            (nova execução pendente)
3. gerador + oráculos           -> authorises_neural_synthetic
4. fatorial sintético           -> authorises_french_diagnostic
5. diagnóstico francês          (somente se autorizado)
```

Na França não existe `A_true`; reportam-se apenas ganho preditivo, estabilidade,
superioridade contra placebos, concordância entre sinais, confiança, abstenção, associação e
precedência temporal. Nenhuma alegação causal.

## 10. Resultado do torneio corrigido — superseded pending rerun

Os números de DEC-128/129 são preservados como histórico, mas ficam **SUPERSEDED_PENDING_RERUN**.
O torneio ainda ajustava contagens NB com pesos Poisson e permitia que cada braço estimasse
sua própria dispersão. Também construía o maxT com referências leave-one-out distintas.
Nenhuma classificação de sinal desse artefacto autoriza o gerador até o torneio ser
reexecutado com a inferência da secção 11.

## 11. Emenda de inferência antes do gerador

Para contagens, `Var(Y)=mu+mu^2/phi` e o IRLS usa
`w=mu/(1+mu/phi)`. Em cada origem rolling, `phi` é estimado uma vez no treino pelo nulo de
persistência sem grafo e congelado para B0, B1, B4 e todos os placebos. O período pontuado
nunca participa e nenhum braço escolhe sua própria escala de ruído.

O maxT usa a mesma estatística para observado e permutações:
`T=(mean(D_perm)-D_candidate)/sd(D_perm)`. O sorteio `b` preserva a mesma reetiquetagem
territorial entre sinais e o máximo de `T_b` forma o nulo conjunto. Quarenta sorteios são
apenas triagem exploratória (`p_min=1/41`); uma afirmação confirmatória exige pelo menos
199 sorteios, preferencialmente 999 se o probe NumPy mostrar custo aceitável.

As guardas específicas e seus mutantes ficam em
`tests/test_herald91_inference_guards.py` e
`tests/run_herald91_inference_mutations.py`. O gerador não é autorizado antes de ambas
passarem e o torneio corrigido ser reexecutado.

## 12. Regra de encerramento experimental

O HERALD 91 é a última investigação experimental ampla prevista para esta linha. A nova
execução do torneio corrigido e, somente se os gates autorizarem, o gerador, os oráculos, o
fatorial sintético e o diagnóstico francês formam uma única cadeia decisória. Um resultado
positivo, mediano ou negativo encerra a pergunta desde que os controlos sejam válidos e a
auditoria independente confirme os mecanismos. Resultado mediano ou negativo não autoriza
novas buscas abertas de arquitetura, largura ou hiperparâmetros.

Depois dessa cadeia, o trabalho autorizado passa a ser auditoria final, congelamento dos
artefactos, consolidação das tabelas e figuras e revisão do relatório e da apresentação.
Uma nova experiência só poderá ser aberta se a auditoria encontrar um defeito mecânico que
invalide o teste; nesse caso, a correção deve ser mínima e repetir a mesma hipótese, sem
expandir o espaço de procura depois de observados os resultados.

Esta regra separa suficiência científica de sucesso numérico. O objetivo do fecho é mostrar
o que os dados permitem identificar, onde a combinação de sinais ajuda e onde a informação
é insuficiente. Na França, os resultados continuam limitados a associação, precedência
temporal e impacto preditivo; não sustentam causalidade estrutural nem descoberta confirmada
de arestas sem recuperação no sintético de verdade conhecida.
