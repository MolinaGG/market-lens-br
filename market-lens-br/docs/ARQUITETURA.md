# Arquitetura — market-lens-br

## Fluxo de análise

1. **Apify** coleta notícias preservando fonte, horário e endereço. O sistema elimina duplicatas.
2. **Groq** interpreta a pergunta e organiza os acontecimentos por empresa, setor e tema, em respostas estruturadas.
3. **Python** cruza notícias e preços históricos, procura eventos comparáveis e calcula cenários para os próximos pregões.
4. **Dashboard** apresenta notícias relevantes, movimentos históricos, projeções com faixas de incerteza, fontes e desempenho anterior do modelo.

A IA produz explicações. As probabilidades vêm do modelo estatístico. Associações observadas não são tratadas como causa sem investigação adicional.

## Benchmark de referência (Bloomberg)

Usado apenas como referência de organização da informação, com base nas páginas públicas Notícias e Pesquisa:

| Referência Bloomberg | Aplicação no projeto |
|---|---|
| Notícias integradas a gráficos e ativos | Cada notícia ligada aos ativos envolvidos e ao movimento observado |
| Briefings personalizados por lista de ativos | Resumo do dia conforme os interesses do usuário |
| News Trends: volume, atenção e sentimento | Identificar assuntos ganhando relevância e agrupar matérias sobre o mesmo acontecimento |
| Pesquisa integrada a dados e análises | Explicações acompanhadas de fontes e evidências verificáveis |

## Diferencial: rastreabilidade

Cada projeção deve permitir abrir: quais notícias entraram, quais episódios históricos foram comparados, quantas observações sustentam o resultado e como o modelo se saiu em testes. Quando faltar evidência, o sistema informa isso e deixa de apresentar a faixa estatística.

## Decisões em aberto

- Fonte histórica de notícias: será escolhida por regressão, medindo quais fontes têm maior relação com movimentos de mercado.
- Fonte de preços históricos: `yfinance` na primeira versão, atrás de uma interface substituível.
- Hospedagem do serviço Python: a definir antes da publicação pública.
