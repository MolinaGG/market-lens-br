# Leitura das métricas e reação dos papéis a divulgações

O visitante de um portfólio quantitativo deve entender o que cada número mede, qual direção é melhor e onde a evidência termina. O painel atual calcula retornos, regressões e janelas de eventos, mas depende de documentação externa para a interpretação. A pesquisa local de ações mede apenas retorno total após fatos relevantes e não permite ver quanto o ajuste por proventos muda a leitura de cada divulgação.

## Experiência

- Explicações curtas e visíveis acompanham observações alinhadas, cupons, corte cronológico, R², RMSE em pontos base, coeficientes, intervalos de 95%, retorno acumulado e métricas de eventos. Linguagem simples e exemplo numérico quando útil. Informação histórica e ajuste estatístico não são apresentados como causalidade ou previsão negociável.
- O painel local de ações mostra, para cada divulgação oficial CVM elegível do emissor importado, janelas de 1, 3 e 5 pregões em dois modos: preço com desdobramentos neutralizados e retorno total bruto com dividendos/JCP. Cada modo mostra retorno observado, retorno esperado pelo modelo ajustado somente antes da divulgação e a diferença em pontos percentuais. Datas, fonte, categoria, amostra prévia e motivo de indisponibilidade ficam visíveis.
- Fatos relevantes e comunicados ao mercado entram na lista de eventos; documentos cancelados permanecem como evidência, sem resultado de impacto. Reapresentações não duplicam um evento.
- O cálculo usa apenas cotações importadas pelo pesquisador, no ambiente local. O retrato público não oferece cotações de ações. Links jornalísticos GDELT permanecem como contexto e não geram uma medida de impacto, pois não têm horário de publicação confirmado.

## Limites de interpretação

Retorno anormal é retorno observado menos retorno de referência **ex post**. Uma diferença positiva significa que o papel superou o referencial naquela janela, não que o documento causou a diferença. Fatores concorrentes, vazamento de informação, negociação antes da entrega à CVM e cotações importadas incompletas podem alterar a leitura. Um intervalo de confiança de uma coorte descreve incerteza da média sob hipóteses estatísticas, não a probabilidade de o próximo evento ter aquele retorno.

## Critérios de aceite

1. A mesma divulgação retorna janelas com e sem proventos sobre as mesmas datas, e um provento na janela muda somente o modo ajustado.
2. A interface explica unidades e direção de R², RMSE, coeficientes, intervalos, retornos e amostra, também para ações.
3. A interface informa claramente quando não há cotações locais, quando uma janela é indisponível ou quando a fonte é apenas menção jornalística.
