# Project Explanations

Data de inicio: 2026-04-08

Objetivo:

- registrar o que foi feito
- explicar por que cada acao foi necessaria
- manter uma base de texto reutilizavel para documentacao, relatorio e redacao futura

Regra:

- este arquivo nao substitui o `git`
- este arquivo nao substitui o `PROJECT_JOURNEY.md`
- ele guarda a explicacao metodologica e operacional de cada acao relevante

Os tres mecanismos permanentes do projeto passam a ser:

1. `git`
   - guarda historico de versao e diffs
2. `PROJECT_JOURNEY.md`
   - guarda a linha do tempo e as decisoes
3. `PROJECT_EXPLANATIONS.md`
   - guarda a explicacao do que foi feito e por que

## Explicacoes por acao

### 2026-04-08 - Catalogacao inicial do acervo

O que foi feito:

- inventario do acervo local
- validacao de integridade dos arquivos
- identificacao de arquivos corrompidos
- busca das descricoes oficiais e APIs Melodi quando disponiveis

Por que isso foi necessario:

- antes de modelar, precisavamos saber exatamente o que cada dataset representa
- datasets publicos com nomes tecnicos podem induzir erro sem leitura semantica
- arquivos corrompidos poderiam gerar falso problema de merge ou de treino
- a descricao oficial do INSEE e necessaria para justificar o uso posterior das variaveis

Resultado esperado:

- acervo confiavel
- visao clara do significado de cada base
- base de consulta para selecao de features

### 2026-04-08 - Complemento territorial oficial

O que foi feito:

- download e validacao dos arquivos territoriais atuais
- substituicao de URLs antigas que nao funcionavam

Por que isso foi necessario:

- o projeto depende de uma geografia funcional consistente
- a `zone d'emploi` e o objeto territorial central do prototipo
- sem os arquivos territoriais corretos, nao existe agregacao espacial valida

Resultado esperado:

- suporte oficial para mapeamento comunal
- base para geometrias, adjacencia e grafo

### 2026-04-08 - Construcao da ponte `commune -> ZE2020`

O que foi feito:

- extracao da tabela [commune_to_ze2020_2026.csv](/home/jpdark/Downloads/project_recomm/dataset/data/interim/mappings/commune_to_ze2020_2026.csv)

Por que isso foi necessario:

- os dados de entrada chegam majoritariamente em nivel `commune`
- o sistema recomenda em nivel `zone d'emploi`
- portanto, a ponte territorial e a condicao minima para unir as duas escalas

Resultado esperado:

- agregacao coerente de todas as fontes para a unidade analitica do projeto

### 2026-04-08 - Criacao da camada `interim`

O que foi feito:

- extracao de tabelas limpas por fonte em `data/interim/tables`

Por que isso foi necessario:

- os arquivos brutos do INSEE nao sao a melhor interface para pipeline
- era preciso estabilizar colunas, chaves e recortes antes da agregacao
- a camada `interim` reduz ambiguidade e facilita reproducao

Resultado esperado:

- cada fonte passa a ter uma tabela previsivel
- o pipeline deixa de depender de leitura manual de `zip`

### 2026-04-08 - Construcao do `zones_master`

O que foi feito:

- agregacao de varias fontes comunais para uma linha por `zone d'emploi`
- consolidacao do snapshot anual em [zones_master_annual_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/zones_master_annual_v0.csv)

Por que isso foi necessario:

- o projeto precisa de um dataset analitico por no territorial
- esse dataset e a base para o painel temporal, para o grafo e para o pre-STGNN
- sem um `zones_master`, o sistema continua fragmentado por fonte

Resultado esperado:

- uma tabela unica por zona
- ponto de partida para selecao de features e validacao de cobertura

### 2026-04-08 - Revisao do indicador de desemprego

O que foi feito:

- abandono da proxy antiga
- substituicao por estimativa derivada de `ativos - ocupados`

Por que isso foi necessario:

- a leitura inicial podia transformar ausencia estrutural em zero numerico
- isso seria um erro metodologico grave
- preferimos uma estimativa defensavel e explicitamente documentada

Resultado esperado:

- indicador mais coerente para uso analitico
- reducao do risco de contaminar o modelo com dado artificial

### 2026-04-08 - Investigacao e isolamento de Mayotte

O que foi feito:

- verificacao da cobertura de `976xx`
- confronto entre fontes locais e documentacao do INSEE
- isolamento de Mayotte como anomalia estrutural

Por que isso foi necessario:

- a falta de dados em Mayotte parecia inicialmente um problema de merge
- a investigacao mostrou que a lacuna e estrutural em parte das fontes
- isso precisava ser tratado como anomalia de cobertura, nao como zero real

Resultado esperado:

- manter Mayotte no universo territorial
- evitar que ela degrade o treino inicial
- deixar a limitacao explicitamente documentada

### 2026-04-08 - Flags de cobertura e elegibilidade

O que foi feito:

- adicao de flags de cobertura por fonte
- adicao de `is_structural_anomaly`
- adicao de `is_training_eligible_v0`

Por que isso foi necessario:

- nem toda zona tem cobertura identica em todas as fontes
- o modelo precisa saber quais nos podem entrar no recorte inicial
- o pipeline precisa distinguir dado ausente de anomalia estrutural

Resultado esperado:

- criterio operacional claro para treino
- transparencia sobre cobertura e missingness

### 2026-04-08 - Construcao do `panel_zones_v0`

O que foi feito:

- transformacao do `zones_master` em um painel minimo com uma linha por zona e por ano
- abertura da janela temporal `2021-2024`
- criacao de um registro que diz em que ano cada feature existe de fato

Por que isso foi necessario:

- o STGNN nao trabalha com uma fotografia unica; ele precisa sequencia temporal
- ainda nao temos um painel denso e alinhado, mas precisavamos estabilizar o formato `zone-year`
- era importante evitar imputacao silenciosa, porque isso criaria series artificiais cedo demais

Resultado esperado:

- painel minimo reprodutivel
- cobertura temporal documentada
- base correta para a proxima etapa: grafo e dataset pre-STGNN

### 2026-04-08 - Matriz de cobertura temporal e guia de coleta

O que foi feito:

- organizacao das familias de dados por papel analitico
- registro dos anos que ja existem localmente
- indicacao dos pontos oficiais onde buscar os anos faltantes

Por que isso foi necessario:

- sem uma matriz de cobertura, a expansao temporal vira coleta cega
- precisavamos saber o que ja existe, o que falta e onde procurar
- a janela temporal do projeto deve ser definida pela oferta oficial confiavel, nao por suposicao

Resultado esperado:

- criterio claro para priorizar novas coletas
- expansao temporal controlada e documentada
- base para decidir quando a janela temporal ficou suficientemente forte para modelagem

### 2026-04-08 - Triagem de downloads externos

O que foi feito:

- revisao do que foi baixado manualmente fora do fluxo principal
- separacao entre dado util ao pipeline, dado de apoio e documento institucional

Por que isso foi necessario:

- downloads manuais tendem a misturar material central e material periferico
- sem triagem, o repositorio perde clareza metodologica
- precisavamos saber o que realmente ajuda a ampliar a base temporal e o contexto politico

Resultado esperado:

- entrada controlada de novas fontes
- menor risco de poluir o pipeline com material redundante
- foco nos arquivos com maior valor para grafo, painel e contexto ZRR/FRR

### 2026-04-08 - Inspecao da camada FRR

O que foi feito:

- leitura tecnica do shapefile `FRR`
- verificacao da cobertura real do arquivo baixado

Por que isso foi necessario:

- um shapefile parcial poderia ser confundido com a camada nacional
- antes de integrar politica territorial ao pipeline, precisavamos confirmar a escala da fonte

Resultado esperado:

- evitar integracao errada de uma camada regional como se fosse nacional
- usar o arquivo como referencia de estrutura enquanto buscamos a cobertura completa

### 2026-04-08 - Extracao das tabelas ZRR

O que foi feito:

- transformacao das planilhas `ZRR` em tabelas CSV comunais
- captura do historico por ano e da versao alinhada ao `COG 2021`

Por que isso foi necessario:

- `ZRR` fornece uma camada de politica territorial bem documentada e de alta utilidade
- ela pode ser agregada para `ZE2020` e ajudar a contextualizar regimes territoriais
- precisavamos retirar essas planilhas do formato manual e trazelas para o pipeline

Resultado esperado:

- base comunal de politica territorial pronta para integracao futura
- historico institucional preservado
- ponto de comparacao para a transicao futura `ZRR -> FRR`

### 2026-04-08 - Releitura do projeto e reposicionamento da camada de politica

O que foi verificado:

- o desenho original do projeto ja previa restricoes e contexto de politica territorial
- `ZRR` aparece explicitamente no plano como camada normativa relevante
- o projeto tambem menciona `QPV`, `ZAN` e, em versoes mais recentes, `FRR/FRR+`

Por que isso importa:

- `ZRR` nao e um anexo periferico ao pipeline
- ela faz parte da futura camada do `policy_agent`
- portanto, a coleta e estruturacao de `ZRR/FRR/QPV/ZAN` esta alinhada ao projeto original

Resultado esperado:

- tratar as camadas de politica territorial como bloco proprio do acervo
- integrar essas camadas depois ao modulo de restricoes e conformidade

### 2026-04-08 - Extracao da serie historica de populacao

O que foi feito:

- conversao da planilha de series historicas de populacao em tabela comunal do pipeline

Por que isso foi necessario:

- o projeto precisava de uma expansao temporal confiavel
- essa base e uma das melhores oportunidades de ampliar o horizonte com dado oficial harmonizado
- ela permite separar melhor o horizonte historico disponivel da cobertura limitada de outras fontes

Resultado esperado:

- eixo temporal demografico forte
- possibilidade futura de agregacao por `ZE2020`
- base para features de tendencia e estabilidade territorial

### 2026-04-09 - Agregacao da populacao historica para ZE2020

O que foi feito:

- soma da serie comunal historica usando a ponte `commune -> ZE2020`

Por que isso foi necessario:

- o projeto nao modela em nivel comunal nesta fase
- para o painel e para o grafo, precisavamos trazer a serie temporal para a unidade final de decisao

Resultado esperado:

- uma base temporal demografica diretamente utilizavel no nivel do no territorial
- suporte a features de tendencia, estabilidade e dinamica populacional

### 2026-04-09 - Formalizacao das `policy_layers`

O que foi feito:

- abertura de uma familia formal para camadas de politica territorial
- definicao de um schema comunal canônico
- entrada da `ZRR` como primeira camada normalizada

Por que isso foi necessario:

- o projeto ja previa restricoes como `QPV/ZRR`, depois ampliadas para `FRR/FRR+` e `ZAN`
- essas camadas precisam de uma organizacao propria e nao devem ficar misturadas às features preditivas
- no futuro, elas ajudarao a treinar, validar e contextualizar os agentes

Resultado esperado:

- bloco institucional limpo e extensivel
- base comum para `policy_agent`
- caminho claro para integrar `QPV`, `FRR/FRR+` e `ZAN`

### 2026-04-09 - Organizacao dos downloads de politica

O que foi feito:

- criacao de uma estrutura bruta dedicada para os downloads de politica territorial

Por que isso foi necessario:

- os novos downloads estavam poluindo o topo do repositorio
- precisavamos separar melhor dado bruto institucional de artefatos ativos do pipeline
- essa separacao melhora rastreabilidade e manutencao do acervo

Resultado esperado:

- navegacao mais limpa
- menor risco de confundir bruto com dado processado
- base melhor para continuar `QPV`, `ZAN` e `FRR`

### 2026-04-09 - Organizacao dos brutos SIRENE

O que foi feito:

- criacao de uma pasta dedicada para os downloads de registro empresarial e geolocalizacao

Por que isso foi necessario:

- novos brutos estavam ficando no topo do repositorio
- isso mistura acervo, pipeline e downloads exploratorios
- separar `SIRENE` facilita manutencao e leitura do projeto

Resultado esperado:

- estrutura fisica mais limpa
- melhor separacao entre familias de dados
- continuidade metodologica do acervo

### 2026-04-09 - Posicionamento do OCS GE Artificialisation

O que foi decidido:

- `OCS GE Artificialisation` e relevante para o projeto

Por que ele e importante:

- ele e um referencial oficial forte para artificializacao
- tem conexao direta com `ZAN`
- pode reforcar o bloco de conformidade territorial

Por que ele nao entra agora:

- ja existem arquivos `ZAN` locais mais imediatos para estruturar primeiro
- a integracao do `OCS GE` tende a ser mais pesada e espacialmente custosa
- nesta fase, ele nao e o melhor proximo passo em custo-beneficio

Resultado esperado:

- a fonte fica registrada como importante
- mas fora do caminho critico imediato
- podera entrar mais tarde como refinamento da camada `ZAN`

### 2026-04-09 - Convencao de nomes do repositorio

O que foi feito:

- definicao de uma regra unica para nomes de scripts, datasets, relatorios tecnicos e documentos vivos

Por que isso foi necessario:

- o projeto esta crescendo em volume de artefatos
- sem um padrao, a arvore passa a misturar nomes por intuicao
- isso dificulta busca, manutencao e leitura metodologica do pipeline

Resultado esperado:

- nomes previsiveis
- menos ambiguidade entre arquivo de codigo e arquivo de dado
- menor custo de manutencao conforme a pesquisa avancar

### 2026-04-09 - Integracao do `QPV` nas `policy_layers`

O que foi feito:

- leitura da tabela comunal `QPV 2024`
- leitura da correspondencia `QP2024 -> QP2015`
- integracao dessas linhas no schema canônico `policy_commune_status_v0`

Por que isso foi necessario:

- `QPV` ja fazia parte do desenho normativo do projeto
- a familia `policy_layers` nao podia ficar apenas com `ZRR`
- `QPV` e importante para contexto social, prioridade territorial e treino futuro dos agentes

Resultado esperado:

- segunda camada institucional ativa no projeto
- base melhor para futuro `policy_agent`
- preparacao do caminho para `ZAN`

### 2026-04-09 - Abertura da camada quantitativa `ZAN`

O que foi feito:

- extracao da tabela comunal de consumo de espacos `2009-2024`
- normalizacao do CSV bruto em uma camada interim canônica
- registro de `ZAN` como fonte quantitativa ja carregada

Por que isso foi necessario:

- `ZAN` faz parte do desenho institucional do projeto
- os dados ja baixados eram suficientemente fortes para entrar no pipeline
- ao mesmo tempo, `ZAN` nao se comporta como um status binario simples, entao precisava de tratamento proprio

Resultado esperado:

- camada quantitativa pronta para derivar sinais de conformidade
- preparacao da futura agregacao para `ZE2020`
- evolucao coerente da familia `policy_layers` sem forcar simplificacoes cedo demais

### 2026-04-09 - Agregacao de `ZAN` para `ZE2020`

O que foi feito:

- soma das metricas comunais claramente aditivas de `ZAN`
- criacao de uma tabela quantitativa por `zone d'emploi`
- derivacao de indicadores simples de intensidade por populacao e por superficie

Por que isso foi necessario:

- o projeto decide em nivel `ZE2020`, nao em nivel comunal
- manter `ZAN` apenas em comuna limitaria seu uso no raciocinio territorial principal
- a agregacao traz a camada para o mesmo nivel das demais bases do sistema

Resultado esperado:

- uso de `ZAN` no nivel real do projeto
- base para sinais de conformidade territorial
- preparacao do terreno para futuras regras do `policy_agent`

### 2026-04-09 - Revisao de consistencia do pipeline atual

O que foi feito:

- revisao cruzada dos artefatos canônicos do projeto
- correcao da extração `QPV`
- limpeza do historico `ZRR`
- reconstrucao da camada `policy_commune_status_v0`

Por que isso foi necessario:

- antes de entrar em visualizacao e depois em grafo, precisavamos garantir que nao havia incoerencia estrutural escondida
- essa revisao evitou carregar parsing errado, linhas de legenda e corrupcao por escrita concorrente
- era o momento certo para eliminar passivos metodologicos baratos antes que eles ficassem caros

Resultado esperado:

- base mais confiavel para o proximo bloco
- entendimento claro do que ja esta solido
- lista objetiva do que ainda e passivo metodologico real

### 2026-04-09 - Visualizacao diagnostica inicial

O que foi feito:

- geracao de graficos simples de cobertura, distribuicao e intensidade
- leitura diagnostica do `zones_master`, do `panel_zones` e da camada `ZAN`

Por que isso foi necessario:

- antes do grafo, precisavamos enxergar o estado real dos dados
- a visualizacao ajuda a detectar outliers, rarefacoes e anomalias escondidas
- tambem serve como ponte entre limpeza de dados e construcao estrutural do grafo

Resultado esperado:

- base mais legivel
- maior confianca para abrir a fase do grafo
- suporte visual para justificar o estado atual do dataset

### 2026-04-09 - Revisao de prontidao antes do grafo

O que foi feito:

- revisao conceitual da proxima etapa
- separacao entre grafo estrutural e validacao final do sistema
- formalizacao do problema de avaliacao sem `ground truth`

Por que isso foi necessario:

- sem verdade-terreno, e facil superinterpretar o proximo passo
- precisavamos garantir que o grafo seria usado pelo motivo certo
- isso protege o projeto contra conclusoes fortes demais cedo demais

Resultado esperado:

- clareza metodologica
- menor risco de confundir infraestrutura com resultado final
- continuidade segura para a fase do grafo

### 2026-04-09 - Formalizacao da base de dependencias do ambiente

O que foi feito:

- definicao inicial das dependencias Python do projeto
- inclusao explicita da stack geoespacial

Por que isso foi necessario:

- a necessidade dessas ferramentas ja estava embutida no plano do grafo
- sem formalizar o ambiente, a reproducao da fase espacial ficaria fragil
- isso transforma uma dependencia implícita em parte oficial da infraestrutura do projeto

Resultado esperado:

- ambiente mais previsivel
- menor risco de bloqueio tecnico escondido
- base correta para iniciar o grafo sem improvisacao

### 2026-04-09 - Construcao do primeiro grafo `ZE2020`

O que foi feito:

- uso da stack geoespacial para ler o fundo territorial oficial
- construcao da adjacencia por contiguidade geografica
- validacao estrutural do grafo resultante

Por que isso foi necessario:

- o projeto precisava sair de uma colecao de tabelas para uma estrutura relacional espacial
- essa e a ponte natural entre os dados limpos e o bloco pre-STGNN
- sem o grafo, a camada espacial do sistema ficaria apenas conceitual

Resultado esperado:

- primeiro suporte formal para modelagem com grafo
- lista de nos e arestas reproduzivel
- base valida para a proxima etapa do projeto

### 2026-04-09 - Visualizacao inicial do grafo

O que foi feito:

- transformacao do grafo em mapas simples de leitura

Por que isso foi necessario:

- um grafo apenas em CSV e dificil de inspecionar intuitivamente
- a visualizacao ajuda a validar se a conectividade faz sentido territorialmente
- tambem facilita a comunicacao do estado atual do projeto

Resultado esperado:

- leitura espacial mais clara do grafo
- maior confianca antes do bloco pre-STGNN

### 2026-04-09 - Visualizacao interativa do grafo

O que foi feito:

- criacao de um mapa HTML navegavel para o grafo

Por que isso foi necessario:

- para inspecao real do grafo, o HTML e melhor do que imagens estaticas
- ele permite ligar e desligar camadas e explorar os componentes com mais clareza

Resultado esperado:

- leitura mais util do grafo
- artefato melhor para analise e comunicacao do projeto

### 2026-04-09 - Recorte `core_v0` do grafo

O que foi feito:

- reducao do grafo ao seu bloco continental principal

Por que isso foi necessario:

- o proprio governo oferece cobertura desigual nesses territorios
- ilhas e ultramarinos introduzem anomalias de conectividade e de cobertura no MVP
- o primeiro ciclo precisa de um recorte territorial mais controlado

Resultado esperado:

- grafo mais coerente para o MVP
- menor risco metodologico no bloco pre-STGNN
- possibilidade de reintroduzir os territorios excluidos depois, de forma controlada

### 2026-04-09 - Alinhamento dos datasets ao `core_v0`

O que foi feito:

- filtragem dos datasets principais para o mesmo recorte espacial do MVP
- geracao de uma visualizacao interativa restrita a Francia continental

Por que isso foi necessario:

- nao bastava filtrar o grafo e deixar o resto do pipeline em outro universo territorial
- o pre-STGNN precisa que nos, arestas e features falem exatamente do mesmo conjunto de zonas
- a visualizacao tambem precisava refletir o recorte decidido, sem poluicao externa

Resultado esperado:

- consistencia territorial total no MVP
- menor risco de merge ou treino em universos diferentes
- artefato visual mais fiel ao escopo atual do projeto

### 2026-04-09 - Pacote pre-STGNN do `core_v0`

O que foi feito:

- transformacao do recorte `core_v0` em um pacote estrutural pronto para modelagem

Por que isso foi necessario:

- o grafo sozinho nao basta para forecasting
- era preciso consolidar nos, arestas, painel, contexto estatico e masks no mesmo formato operacional
- isso reduz atrito tecnico para baseline e Graph WaveNet

Resultado esperado:

- base tecnica pronta para o bloco preditivo
- target ainda separado, como decisao metodologica propria
- continuidade mais segura para a proxima fase

### 2026-04-09 - Formalizacao da logica de auditabilidade

O que foi feito:

- registro da razao metodologica para manter o sistema modular

Por que isso foi necessario:

- a separacao entre predicao, decisao e validacao nao e detalhe de engenharia
- ela e o que permite auditar o sistema em politica publica sem colapsar tudo em uma unica caixa-preta

Resultado esperado:

- justificativa clara da arquitetura
- melhor base para redacao, defesa e implementacao futura

### 2026-04-09 - Revisao de prontidao do target inicial

O que foi feito:

- confronto entre o target previsto no plano e as bases de criacao disponiveis localmente

Por que isso foi necessario:

- o projeto ja define um target inicial, mas isso nao significa que ele esteja imediatamente operacional
- era importante nao confundir intencao metodologica com disponibilidade real de dado

Resultado esperado:

- evitar um target artificial ou fraco demais
- manter coerencia entre o plano e a implementacao

### 2026-04-09 - Derivacao do target via SIRENE

O que foi feito:

- verificacao direta dos arquivos `SIRENE` para descobrir se existe um caminho local de derivacao do target

Por que isso foi necessario:

- o projeto nao pode ficar bloqueado indefinidamente esperando uma fonte perfeita
- ao mesmo tempo, nao devemos fingir que um proxy e o target final

Resultado esperado:

- abrir um caminho tecnico realista para o primeiro baseline
- separar honestamente o `target oficial` do `target proxy`
- manter a auditabilidade metodologica do projeto

### 2026-04-09 - Materializacao do target proxy canonico

O que foi feito:

- agregacao mensal das criacoes de estabelecimentos `SIRENE` para `ZE2020 core_v0`
- limpeza de datas impossiveis para estabilizar o artefato final

Por que isso foi necessario:

- o projeto precisava sair do estado de target apenas conceitual
- ao mesmo tempo, era necessario evitar datas anômalas que contaminariam a serie temporal

Resultado esperado:

- primeiro target proxy utilizavel para benchmark e baseline tecnico
- trilha metodologica mais honesta entre o que e target oficial e o que e proxy operacional

### 2026-04-09 - Fechamento do baseline anual

O que foi feito:

- conversao do target proxy mensal para serie anual por `ZE2020`
- alinhamento das features anuais atuais com `target_t+1`

Por que isso foi necessario:

- as features do painel atual ainda sao majoritariamente anuais
- pular direto para treino mensal criaria um desalinhamento metodologico entre sinal explicativo e target

Resultado esperado:

- abrir um caminho de validacao tecnica limpo
- permitir baseline antes do STGNN
- preservar coerencia temporal do projeto

### 2026-04-09 - Avaliacao do baseline anual sem grafo

O que foi feito:

- execucao do primeiro experimento preditivo real do projeto
- comparacao entre persistencia e regressao linear simples

Por que isso foi necessario:

- o projeto precisava de um benchmark minimo antes de partir para o modelo com grafo
- sem isso, qualquer ganho posterior seria dificil de interpretar

Resultado esperado:

- congelar um baseline oficial para comparacao futura
- mostrar que o pipeline anual ja e treinavel
- orientar a proxima etapa na direcao certa: modelo com grafo, nao regressao tabular simples

### 2026-04-09 - Fechamento da base concreta antes da modelagem

O que foi feito:

- organizacao do que ja pode ser considerado fundacao estavel do projeto

Por que isso foi necessario:

- o usuario quer separar claramente a fase de base concreta da fase de modelagem
- isso melhora o controle de qualidade do repositorio e da narrativa metodologica

Resultado esperado:

- um commit de fundacao com escopo claro
- melhor rastreabilidade da transicao para o modelo com grafo

### 2026-04-09 - Pacote anual para o modelo com grafo

O que foi feito:

- montagem do formato anual especifico para a fase de modelagem com grafo

Por que isso foi necessario:

- antes de instalar ou treinar qualquer modelo com grafo, era preciso saber se o pacote anual estava minimamente pronto
- isso tambem permite separar prontidao estrutural de prontidao estatistica

Resultado esperado:

- confirmar que o grafo, os nos e o target ja conversam entre si
- explicitar que o gargalo restante agora e profundidade temporal, nao integracao de dados

### 2026-04-09 - Aprofundamento temporal antes do modelo com grafo

O que foi feito:

- transformacao do diagnostico de profundidade rasa em plano de coleta priorizado

Por que isso foi necessario:

- sem uma ordem clara, o projeto poderia voltar a mineracao difusa de dados
- era preciso ligar diretamente a lacuna metodologica atual ao que deve ser baixado em seguida

Resultado esperado:

- aumentar a profundidade anual das features com menor risco
- preparar um Graph WaveNet futuro em base mais defensavel

### 2026-04-10 - Efeito dos novos downloads sobre as lacunas

O que foi feito:

- confrontacao entre os arquivos novos e as lacunas temporais que bloqueiam a modelagem com grafo principal

Por que isso foi necessario:

- baixar mais arquivos nao significa automaticamente fechar a lacuna certa
- era preciso distinguir ganho tematico de ganho de profundidade temporal

Resultado esperado:

- manter a coleta focada
- evitar falsa sensacao de prontidao para o modelo com grafo

Complemento:

- a checagem fina mostrou que nem toda serie temporal adicional ajuda o mesmo problema
- `RP_SERIE_HISTORIQUE_2022` reforca o eixo comunal e pode virar feature util
- ja os `SIDE` em serie que apareceram nesta rodada sao agregados macro e servem mais para contexto do que para fechar a profundidade do painel em `ZE2020`

### 2026-04-10 - Download oficial de RP 2021 e Filosofi 2020

O que foi feito:

- download dos arquivos oficiais que ja tinham link direto confirmado
- organizacao desses brutos em `data/raw/temporal_depth/`
- validacao imediata da integridade dos zips

Por que isso foi necessario:

- a profundidade temporal do painel anual so melhora de verdade quando as fontes faltantes entram no acervo
- `RP 2021` e `Filosofi 2020` eram lacunas prioritarias e ja estavam suficientemente confirmadas para download

Resultado esperado:

- preparar a proxima rodada de integracao sem depender de nova busca para esses dois blocos
- reduzir o conjunto de lacunas abertas antes da modelagem com grafo

### 2026-04-10 - Integracao de RP 2021 e Filosofi 2020

O que foi feito:

- transformacao dos brutos baixados em tabelas comunais utilizaveis
- agregacao dessas tabelas para `ZE2020`
- injecao das colunas novas no `zones_master_annual_v0`
- reconstrucao do painel e dos artefatos derivados

Por que isso foi necessario:

- baixar os dados era apenas metade do trabalho
- o ganho metodologico real so aparece quando os novos anos entram no painel, no baseline e no pacote anual com grafo

Resultado esperado:

- ampliar a profundidade temporal efetiva do projeto de `2021-2024` para `2020-2024`
- reduzir a dependencia de features de um unico ano no bloco socioeconomico
- deixar o proximo gargalo concentrado nas familias que ainda faltam

### 2026-04-10 - Busca de links em data.gouv

O que foi feito:

- exploracao de `data.gouv.fr` como rota alternativa para os datasets ainda nao fechados por link bruto no Insee

Por que isso foi necessario:

- algumas paginas de metadados do Insee expõem a existencia do dataset, mas nao o link final de forma simples
- `data.gouv` frequentemente republica esses recursos com um endpoint direto e estavel por `resource id`

Resultado esperado:

- destravar a coleta dos blocos restantes sem depender de navegação manual repetitiva
- reduzir o conjunto de lacunas abertas antes da proxima rodada de integracao

Complemento:

- o commit de fundacao deve congelar apenas a camada analitica viva
- os brutos em `data/raw/` permanecem fora para evitar inflar o repositorio sem ganho metodologico imediato

### 2026-04-09 - Script de scan completo do repositorio

O que foi feito:

- criacao de um script shell unico para executar o levantamento estrutural do repositorio

Por que isso foi necessario:

- o projeto ja cresceu o suficiente para justificar uma inspecao completa e repetivel
- o usuario queria uma forma de rodar o scan por horas, se preciso, e depois devolver o resultado consolidado

Resultado esperado:

- reduzir trabalho manual
- produzir um pacote unico de revisao
- melhorar a capacidade de auditoria sobre o acervo e o pipeline

### 2026-04-09 - Leitura do scan completo

O que foi feito:

- revisao dos arquivos de saida do scan para transformar a varredura bruta em diagnostico util

Por que isso foi necessario:

- um scan completo sem interpretacao nao ajuda a tomada de decisao
- era importante separar problema de dado de problema de ambiente

Resultado esperado:

- confirmar que o acervo nao voltou a apresentar corrupcao
- reforcar o papel central de `SIRENE`
- confirmar tambem que os `parquet` centrais de `SIRENE` estao legiveis por metadados com `pyarrow`

### 2026-04-08 - Governanca do projeto

O que foi feito:

- inicializacao do repositório Git
- politica de versionamento
- roadmap da Fase 1
- journal continuo
- limpeza do repositorio para manter apenas o pipeline vivo

Por que isso foi necessario:

- um projeto de pesquisa com varias decisoes metodologicas precisa de rastreabilidade
- sem governanca, o repositorio vira deposito de tentativas
- a Fase 1 precisava ficar presa ao objetivo principal: construir o grafo

Resultado esperado:

- repositorio limpo
- historico de versao controlado
- memoria tecnica acumulativa

## Regra de manutencao

A partir desta rodada, sempre que uma acao relevante for executada:

1. o codigo e os artefatos entram no `git`
2. a linha do tempo entra no [PROJECT_JOURNEY.md](/home/jpdark/Downloads/project_recomm/dataset/reports/PROJECT_JOURNEY.md)
3. a explicacao do que foi feito e por que entra neste arquivo

### 2026-04-10 - Correcao metodologica da busca em data.gouv

O que foi feito:

- confirmacao da metadata oficial via API do `data.gouv`
- revisao dos links de `SIDE`, `FLORES` e `BPE`
- correcao da leitura sobre quais anos estavam realmente fechados por recurso bruto

Por que isso foi necessario:

- a primeira leitura do `data.gouv` sugeria que algumas familias multi-anuais ja fechariam `SIDE 2021` e `FLORES 2023`
- a verificacao pela API mostrou que os recursos expostos hoje apontam para `2022` em `SIDE` e `2024` em `FLORES`
- sem essa correcao, o projeto carregaria uma falsa sensacao de cobertura temporal resolvida

Resultado esperado:

- manter as lacunas abertas de forma honesta
- preservar a rastreabilidade da busca
- evitar integrar anos errados por inferencia otimista

### 2026-04-10 - Inspecao semantica do recurso BPE baixado

O que foi feito:

- download do recurso oficial associado a `BPE 2023`
- leitura amostral do zip, do shapefile e do csv do recurso
- verificacao do campo temporal presente no proprio conteudo

Por que isso foi necessario:

- um link oficial baixavel nao basta por si so
- para ampliar profundidade temporal, o ano do conteudo precisa bater com o ano que estamos tentando integrar
- neste caso, o recurso observado traz `2024` no proprio conteudo, apesar de a rota sugerir `2023`

Resultado esperado:

- impedir que uma camada temporal seja incorporada com ano errado
- manter `BPE 2023` como lacuna metodologicamente aberta
- documentar que a familia `BPE` esta acessivel, mas ainda nao com seguranca temporal suficiente para integracao

### 2026-04-10 - Busca ampliada em fontes oficiais confiaveis

O que foi feito:

- ampliacao da busca para alem do `data.gouv`
- leitura direta das paginas oficiais do `Insee` para `BPE 2021` e `BPE 2020`
- separacao entre tres situacoes: existencia oficial, link bruto fechado e adequacao ao nosso pipeline

Por que isso foi necessario:

- em projetos como este, um portal oficial sozinho nao resolve a coleta
- alguns anos aparecem documentados, mas sem link bruto evidente
- em outros casos, o link existe, mas o conteudo nao confirma o ano correto

Resultado esperado:

- reduzir buscas cegas
- evitar assumir que uma lacuna esta resolvida apenas porque a familia estatistica existe
- melhorar a estrategia de coleta futura com uma tipologia mais honesta das lacunas

Complemento importante:

- a leitura da propria pagina oficial do `Insee` para `BPE 2021` mostra que os arquivos da base sao publicos em `csv`
- isso muda a interpretacao do bloqueio: nao estamos diante de um dado fechado, mas de um endpoint publico ainda nao isolado com precisao

### 2026-04-10 - Integracao efetiva de BPE 2021

O que foi feito:

- validacao do arquivo bruto `bpe21-ensemble-csv.zip`
- confirmacao do ano correto no conteudo
- agregacao do `NB_EQUIP` por comuna e depois por `ZE2020`
- incorporacao da camada ao `zones_master` e ao painel temporal

Por que isso foi necessario:

- entre os downloads novos, este foi o primeiro caso em que a familia oficial veio acompanhada do ano correto no conteudo
- isso permitiu fechar uma lacuna temporal real sem introduzir ambiguidade

Resultado esperado:

- reforcar o eixo de servicos/acessibilidade em `2021`
- melhorar a densidade do painel anual sem inventar serie
- reduzir o numero de lacunas abertas na familia `BPE`

### 2026-04-10 - Verificacao dos downloads de FLORES

O que foi feito:

- leitura dos novos pacotes `FLORES` baixados localmente
- validacao do pacote nacional `2023`
- validacao dos arquivos detalhados `A17` de `2021` e `2020`

Por que isso foi necessario:

- a familia `FLORES` era uma das lacunas importantes para profundidade temporal
- os nomes dos arquivos sugeriam que parte dessa lacuna ja poderia estar resolvida localmente
- era necessario verificar o conteudo real antes de marcar a familia como fechada

Resultado esperado:

- confirmar que `FLORES 2023` ja esta disponivel localmente
- confirmar que `FLORES 2021` tambem pode entrar como reforco temporal
- reduzir o numero de lacunas abertas sem depender de nova coleta externa

### 2026-04-11 - Fechamento de SIDE 2021 e BPE 2023

O que foi feito:

- os arquivos `SIDE` atuais foram tratados como series multi-ano, nao como arquivos isolados de `2021`
- a integracao reteve apenas `TIME_PERIOD = 2021`, `GEO_OBJECT = COM` e `ACTIVITY = _T`
- o arquivo `BPE23.zip` foi validado como fonte real de `AN = 2023`
- os totais foram agregados de comuna para `ZE2020` e propagados ao painel anual

Por que isso foi necessario:

- o objetivo era aumentar a profundidade temporal sem introduzir dados rotulados incorretamente
- `DS_BPE_2023_CSV_FR.zip` foi rejeitado porque contem `DS_BPE_2024_data.csv`
- `BPE 2020` ainda nao foi aceito porque os candidatos locais nao possuem conteudo nacional valido de 2020

Resultado esperado:

- fortalecer `2021` com estoques economicos `SIDE`
- fortalecer `2023` com equipamentos `BPE`
- manter `BPE 2020` como unica lacuna principal antes de uma nova decisao de modelagem

### 2026-04-11 - Por que BPE 2020 ainda nao foi fechado

O que foi feito:

- busca especifica por `BPE 2020 Ensemble` fora da pagina dinamica do Insee
- validacao do historico `DoReMIFaSol`, que confirma o antigo arquivo `bpe20_ensemble_csv.zip`
- teste de candidatos locais e externos
- rejeicao explicita do candidato `data.gouv.fr` apos verificar que continha somente `2011` e `2012`

Por que isso foi necessario:

- marcar um arquivo errado como `BPE 2020` contaminaria o painel anual
- o ano do recurso ou da pagina nao basta; o ano precisa aparecer no conteudo
- o projeto precisa preservar rastreabilidade mesmo quando uma fonte historica deixa de estar diretamente disponivel

Resultado esperado:

- evitar integracao falsa de `BPE 2020`
- manter a lacuna documentada e verificavel
- permitir uma decisao metodologica posterior: recuperar o arquivo correto ou seguir sem `BPE 2020`
