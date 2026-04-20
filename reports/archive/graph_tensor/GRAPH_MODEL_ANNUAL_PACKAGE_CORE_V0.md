# Graph Model Annual Package Core v0

Data: 2026-04-09

Objetivo:

- preparar o pacote anual de modelagem com grafo no `core_v0`

## Estrutura produzida

- nos: `280`
- arestas direcionadas: `1486`
- anos de features: `[2019, 2020, 2021, 2022, 2023, 2024]`
- anos de target: `[2000, 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026]`
- linhas de features: `1680`
- linhas de target: `7560`
- numero de features: `25`

## Leitura metodologica

- o pacote anual com grafo esta estruturalmente pronto
- mas a profundidade temporal observada de features ainda e muito curta para um Graph WaveNet confiavel
- hoje o projeto tem apenas `6` anos efetivos de features (`2019-2024`)
- isso e suficiente para organizacao do pacote, mas fraco para treinamento serio de um modelo spatio-temporal profundo

## Conclusao

- antes do Graph WaveNet anual, o projeto deve decidir se aceita um experimento estritamente demonstrativo ou se amplia a profundidade temporal das features
