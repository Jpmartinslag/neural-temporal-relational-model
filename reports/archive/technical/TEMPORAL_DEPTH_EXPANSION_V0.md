# Temporal Depth Expansion v0

Data: 2026-04-09

Objetivo:

- decidir como aprofundar a profundidade temporal das features antes do primeiro modelo com grafo principal

## Diagnostico atual

O projeto ja tem:

- target anual: `2000 -> 2026`
- historico populacional: `2006 -> 2023`
- features anuais observadas no pacote preditivo: apenas `2021 -> 2024`

Isso cria um desbalanceamento:

- o target ja e profundo
- mas as features explicativas ainda sao rasas

## Regra de prioridade

Devemos ampliar primeiro o que:

1. entra diretamente no painel anual do nucleo preditivo
2. tem cobertura comunal ou facilmente agregavel para `ZE2020`
3. ja demonstrou disponibilidade oficial ou alta plausibilidade de disponibilidade

## Prioridades concretas

### 1. RP 2021

Por que primeiro:

- ja temos `RP 2022`
- a familia RP e central para populacao, atividade e emprego
- e a extensao mais limpa para sair de `4` para `5` anos observados no bloco principal

Evidencia oficial:

- a pagina de metadados do `Recensement de la population 2021` confirma difusao anual e cobertura de zonagens de estudo, inclusive `zones d'emploi`
- fonte: https://www.insee.fr/fr/metadonnees/source/operation/s2150/presentation
- comparabilidade geografica e cobertura territorial documentadas aqui:
  https://www.insee.fr/fr/metadonnees/source/operation/s2150/coherence-comparabilite

### 2. SIDE 2020-2021

Por que muito importante:

- SIDE entra diretamente no bloco economico estrutural
- hoje temos `stocks` em `2022-2023`
- ampliar para `2020-2021` aumenta substancialmente a serie anual antes do modelo com grafo

Estado:

- alta prioridade
- ainda depende de busca/baixa especifica no acervo oficial

### 3. BPE 2023, 2021 e 2020

Por que vale muito:

- BPE e anual
- e um sinal territorial interpretable e agregado por comuna
- ajuda a dar profundidade temporal a servicos/equipamentos sem depender de construcao complexa

Evidencia oficial:

- `BPE 2023` foi oficialmente difundida em 2026
  https://www.insee.fr/fr/metadonnees/source/operation/s2155/bases-donnees-ligne
- `BPE 2021` e `BPE 2020` tambem possuem paginas oficiais de base em linha:
  https://www.insee.fr/fr/metadonnees/source/operation/s2077/bases-donnees-ligne
  https://www.insee.fr/fr/metadonnees/source/operation/s2027/bases-donnees-ligne

### 4. Filosofi 2020

Por que vale agora:

- hoje temos `Filosofi 2021`
- adicionar `2020` aumenta a profundidade do bloco de renda/pobreza com a mesma familia estatistica

Evidencia oficial:

- `Filosofi 2020` continua documentada como fonte oficial:
  https://www.insee.fr/fr/metadonnees/source/operation/s2105/processus-statistique

### 5. Flores 2023

Por que entra depois:

- ajudaria a ampliar a estrutura de emprego salariado
- mas a familia Flores tem difusao publica menos direta que BPE/RP/Filosofi

Evidencia oficial:

- a pagina de `Flores 2023` confirma que tabelas publicas de contagem existem ate a comuna
  https://www.insee.fr/fr/metadonnees/source/operation/s2220/presentation
  https://www.insee.fr/fr/metadonnees/source/operation/s2220/publications

## Recomendacao operacional

Ordem recomendada de coleta:

1. `RP 2021`
2. `SIDE 2020-2021`
3. `BPE 2023`
4. `BPE 2021`
5. `BPE 2020`
6. `Filosofi 2020`
7. `Flores 2023`

## O que isso muda

Se conseguirmos esse bloco, o painel anual deixa de ser um recorte raso `2021-2024` e passa a ter chance real de sustentar um primeiro modelo com grafo com menos risco metodologico.

## Observacao importante

O caso `Mayotte` continua especial.

A documentacao do RP 2021 informa que o primeiro recensement millesime de Mayotte sera o `2023`, com difusao em junho de 2026. Isso reforca a decisao de manter o `core_v0` continental como universo ativo do MVP.

Fonte:

- https://www.insee.fr/fr/metadonnees/source/operation/s2150/coherence-comparabilite
