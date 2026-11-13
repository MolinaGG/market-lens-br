# Market Lens BR — desenho da plataforma de pesquisa quantitativa

## Intenção

Transformar o esqueleto atual em um projeto de portfólio para oportunidades em pesquisa quantitativa e mercado financeiro. O visitante deve conseguir formular uma pergunta sobre um ativo brasileiro, inspecionar séries de mercado e variáveis explicativas, executar uma análise estatística e conferir de onde vieram os dados e como o resultado foi validado. Um controle compara a mesma regressão com e sem a incorporação de fluxos pagos pelo ativo, revelando o efeito do ajuste. O produto também deve relacionar notícias a ativos e, quando houver evidência suficiente, mostrar cenários para 14 pregões.

## Situação atual

O repositório tem FastAPI, React/Vite e TypeScript. A API só expõe `/api/health`; o site exibe esse status e oito códigos de ativos. Apify e Groq ainda não coletam nem interpretam notícias. Não existem preços, banco implementado, cálculos, gráficos, regressões ou projeções. Há uma cópia antiga de quase todo o projeto em `market-lens-br/` dentro da raiz. A documentação da raiz é a referência mais recente.

## Metas

- Demonstrar pesquisa quantitativa reproduzível, com dados reais quando seu uso for permitido, fonte, unidade, frequência, fuso, data de observação, data de divulgação quando aplicável, data de coleta e versão do processamento.
- Cobrir os oito ativos já definidos e ampliar o catálogo para títulos públicos, commodities e variáveis macroeconômicas relevantes, começando com um título com cupom, Brent, câmbio e juros; inflação e outras commodities entram na sequência.
- Permitir comparação de séries, retornos, volatilidade, correlação, drawdown e regressões com períodos e variáveis selecionáveis.
- Mostrar tamanho da amostra, coeficientes, incerteza, diagnóstico e resultados fora da amostra. Separar associação estatística de causalidade.
- Comparar regressões de retorno de preço e retorno total com cupom, dividendo ou JCP, conforme o ativo, mantendo período, observações, fatores, defasagens e método iguais nas duas execuções. A tela mostra a diferença dos coeficientes e medidas de erro e identifica cada fluxo utilizado.
- Preservar notícias com fonte, URL e horário; associá-las a ativos e temas com explicação verificável.
- Oferecer projeções de 14 pregões apenas após backtest temporal e com faixa de incerteza, benchmark e aviso claro quando a evidência for insuficiente.
- Entregar uma interface agradável e utilizável por alguém que avalia o portfólio sem precisar de chaves externas.

## Limites e critérios de qualidade

- Não apresentar preço em tempo real, ordem de negociação, recomendação de investimento ou afirmação causal automática.
- Não chamar uma correlação ou o texto de um modelo de IA de probabilidade calibrada.
- Não preencher dados faltantes, misturar frequências ou usar revisões macroeconômicas futuras silenciosamente.
- Não depender da disponibilidade de Apify, Groq ou de um serviço gratuito acordar para a demonstração principal.
- Não publicar redistribuição de cotações ou notícias sem verificar os direitos da fonte. O [yfinance](https://github.com/ranaroussi/yfinance) diz que o uso da API do Yahoo se destina ao uso pessoal; o uso público dos dados precisa de avaliação própria.
- Não mascarar a comparação: quando falta preço bruto, valor por unidade, data do fluxo ou informação de desdobramento, desabilitar o controle e explicar a ausência, em vez de apresentar duas séries nominalmente diferentes com os mesmos números.
- Manter os segredos apenas no servidor. Respeitar a arquitetura FastAPI + React/TypeScript do repositório. Não introduzir autenticação nem infraestrutura distribuída nesta etapa.

## Abordagens consideradas

1. **Pesquisa reprodutível, escolhida pelo usuário.** Construir catálogo e coleta, um estudo quantitativo completo, interface de exploração e validação; integrar notícias e cenários sobre a mesma base. Evidência e método aparecem desde a primeira entrega. Demora mais para exibir todos os módulos.
2. **Dashboard integrado desde o início.** Exibir notícias, séries e projeções cedo com dados de demonstração. Produz uma vitrine visual mais rápido, mas deixa a parte quantitativa menos convincente no começo.
3. **Laboratório em notebooks primeiro.** Aprofunda regressões rapidamente, mas adia a experiência web que o projeto existente já começou.

## Desenho funcional e técnico

### Dados e proveniência

Um catálogo descreve cada série: identificador, nome, classe, unidade, moeda, frequência, calendário, fornecedor, URL, termos de uso e política de atualização. Adaptadores isolam cada fornecedor. A ingestão salva a resposta original ou seu hash, normaliza observações e registra a versão do processo; erros de coleta não sobrescrevem a última versão íntegra. A demonstração usa um conjunto congelado e identificado, enquanto uma atualização separada pode buscar dados novos. A interface sempre distingue dados históricos congelados de dados atualizados.

Fontes iniciais: [preços diários de títulos do Tesouro Direto](https://www.tesourotransparente.gov.br/ckan/dataset/taxas-dos-titulos-ofertados-pelo-tesouro-direto) e [pagamentos de cupom por título e data](https://www.tesourotransparente.gov.br/ckan/dataset/resgates-do-tesouro-direto), ambos sob ODbL; [SGS do Banco Central](https://dadosabertos.bcb.gov.br/dataset/11-taxa-de-juros---selic) para juros e outras séries nacionais; [PTAX do BCB](https://www.bcb.gov.br/conteudo/dadosabertos/BCBDepin/gnastportal-dados-abertostaxas-de-cambio---todos-os-boletins-diarios.pdf) para câmbio; [EIA via FRED](https://fred.stlouisfed.org/series/DCOILBRENTEU) para Brent diário; e [Pink Sheet do Banco Mundial](https://www.worldbank.org/en/research/commodity-markets) para commodities mensais. A API do [FRED exige chave](https://fred.stlouisfed.org/docs/api/fred/series_observations.html); cada série ainda precisa de revisão de licença e atribuição. O fornecedor de preços dos ativos da B3 fica atrás de um adaptador e o catálogo aceita CSV importado para pesquisa local. O uso público de cotações de ações só entra quando houver fonte gratuita com permissão clara; não bloqueia a primeira demonstração. A política do SGS para séries diárias exige consultas por períodos de até dez anos.

O armazenamento local começa em SQLite. O deploy pode usar Postgres conforme o `DATABASE_URL` já previsto; migração e atualização automatizada só entram quando a demonstração local estiver reproduzível. Uma camada de consulta fornece séries e metadados à API, independentemente do fornecedor.

### Análise

Transformações financeiras são explícitas e testáveis: preço ajustado quando disponível, retorno simples e logarítmico, volatilidade anualizada com convenção divulgada, drawdown, correlação em janela e alinhamento por calendário. O [arquivo histórico da B3](https://www.b3.com.br/pt_br/market-data-e-indices/servicos-de-dados/market-data/historico/mercado-a-vista/cotacoes-historicas/) não ajusta preços por proventos; portanto, retornos de ações só serão usados em estudos e gráficos de desempenho após ajuste documentado ou com restrição de janela e aviso explícito. A análise não inventa observações em feriados ou dias sem cotação. Variáveis mensais entram em estudos mensais ou são alinhadas pela data em que passaram a ser conhecidas; não são antecipadas para cada dia do mês.

No estudo do Tesouro, usa-se o preço unitário de venda matinal do mesmo título e vencimento; o [arquivo oficial de cupons contém o valor por unidade](https://www.tesourotransparente.gov.br/ckan/dataset/f30db6e4-6123-416c-b094-be8dfc823601/resource/445e38cf-b3b3-4e08-879a-2724febcd861/download/ResgatesdoTesouroDireto-Metadados.pdf). O retorno sem ajuste é `P_t/P_anterior - 1`. O retorno total bruto é `(P_t + soma_dos_cupons_desde_a_cotação_anterior)/P_anterior - 1`; a data do pagamento fica visível mesmo quando não há cotação nesse dia. A comparação usa apenas datas em que ambos os retornos e todos os fatores existem. Para ações importadas, a versão com proventos aplica a mesma lógica a dividendos e JCP e trata desdobramentos separadamente, com convenção bruta e sem simular impostos ou reinvestimento automático.

A primeira pesquisa pública estuda um título do Tesouro com juros semestrais que tenha pelo menos dois cupons e 250 pregões disponíveis. Compara a regressão dos retornos do preço unitário com a regressão dos retornos totais brutos, que incorporam o cupom por unidade na data correta. Uma pesquisa de PETR4 em relação a Ibovespa, Brent e USD/BRL entra no fluxo local por importação de CSV de preços e proventos; a mesma comparação fica disponível se os campos necessários estiverem completos. O usuário escolhe janela, variável dependente e fatores disponíveis. A regressão linear mostra especificação, tamanho de amostra, coeficientes, intervalos, qualidade de ajuste, resíduos e limites de interpretação. Uma divisão temporal e um benchmark simples comparam desempenho fora da amostra; o projeto registra as datas e parâmetros usados para reproduzir o resultado. Outras famílias de modelos só entram quando agregarem evidência mensurável.

Para cenários de 14 pregões, o pipeline usa apenas informações disponíveis em cada data de teste, compara com um benchmark ingênuo e calcula cobertura observada das faixas. O sistema registra número de episódios, erros e estabilidade por janelas. Se a amostra ou o desempenho não sustentar o resultado, a tela mostra “evidência insuficiente” e oferece apenas análise histórica. Os limites numéricos de publicação serão definidos e versionados antes de rodar a avaliação, para evitar escolher critérios após ver o resultado.

### Notícias e IA

Uma etapa posterior coleta notícias com Apify ou outra fonte autorizada, deduplica por URL e similaridade, guarda título, trecho permitido, veículo, horário de publicação e coleta, e liga cada notícia a ativo, setor e tema. Groq pode propor etiquetas e resumos estruturados, mas cada saída preserva as notícias usadas e pode ser revista. Nenhum texto gerado produz sozinho números de projeção. Estudos de eventos e backtests respeitam o horário em que a notícia se tornou pública.

### Interface e API

O site terá visão geral do universo, explorador de séries, laboratório quantitativo, painel de notícias/evidências e página de método/limitações. O primeiro fluxo público será: selecionar o título com cupom, inspecionar preços, cupons e fontes, escolher fatores, alternar entre preço e retorno total, rodar a regressão e ler a comparação fora da amostra. A interface explica que cupom de título e provento de ação são fluxos diferentes, embora o princípio do ajuste de retorno seja semelhante. A importação local permite repetir o fluxo com ações quando o usuário dispõe dos dados. Estados de carregamento, erro e ausência de dados devem explicar o que aconteceu. Gráficos devem ter legenda, unidade e data de atualização; tabelas e textos oferecem a mesma informação sem depender de cor.

A API expõe catálogo, observações filtradas e resultados de análises com contratos tipados. Coletas e cálculos pesados são feitos por tarefa de atualização ou resultados em cache, sem bloquear a requisição do visitante. O endpoint de saúde continua simples e não é a fonte do catálogo. A primeira versão pública pode servir dados congelados aprovados para exibição; a atualização ao vivo é uma capacidade separada, não uma condição para navegar na pesquisa.

## Entregas incrementais

1. **Base demonstrável:** organizar o repositório, validar o ambiente, catálogo e proveniência, ingestão do Tesouro e BCB, séries e métricas essenciais, estudo com cupom versus sem cupom, API e interface de exploração. Incluir conjunto reproduzível, licença/atribuição, instruções de execução e metodologia.
2. **Cobertura ampla:** integração local de PETR4 e demais ativos originais por importação de preços/proventos, commodities e indicadores adicionais; comparação de regressões com e sem proventos, seleção de variáveis, diagnósticos, testes fora da amostra e relatórios exportáveis. Fonte gratuita com direitos de exibição pública será avaliada continuamente; sua ausência não impede as demais entregas.
3. **Notícias e cenários:** coleta e interpretação auditável, estudos de eventos e projeções condicionadas a critérios de evidência, com desempenho histórico visível.
4. **Publicação:** versão pública estável, automação de atualização adequada ao provedor, observabilidade e README com captura de tela, arquitetura, limitações e exemplos reproduzíveis.

Cada entrega deve funcionar sozinha e deixar claros os recursos ainda em construção. A primeira entrega não será rotulada como previsão de mercado.

## Decisões assumidas para execução

- A experiência principal é uma pesquisa quantitativa explorável, porque o portfólio se destina a oportunidades de pesquisa quantitativa/mercado.
- A primeira demonstração pública usa títulos e cupons do Tesouro Transparente, fonte oficial gratuita e aberta; a pesquisa de ações usa dados importados localmente até encontrar uma fonte gratuita com direito claro de exibição pública.
- Frequência diária na primeira pesquisa, com juros e câmbio como fatores; Brent entra ao completar o adaptador FRED ou outra fonte autorizada. Dados mensais entram em análise própria ou com alinhamento por divulgação.
- Sem login e sem custos obrigatórios para quem visita a demonstração.
- O código pode funcionar localmente com fontes que exigem chave ou importação, mas a versão pública só expõe séries cuja licença e proveniência foram verificadas.
- A ordem acima evita que a interface prometa inferências que o projeto ainda não mediu.
