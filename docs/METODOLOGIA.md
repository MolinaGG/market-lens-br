# Metodologia da demonstração

## Retrato e unidades

A versão incluída no repositório é `20261113T181936Z-bb5f68ed69b0`, coletada em 13 de novembro de 2026. Contém 62.209 observações de preço e fatores, 155 pagamentos por título e 100 comunicados do Copom. O recorte de preços e fatores começa aproximadamente cinco anos antes da coleta. O banco e as fontes estão identificados em [FONTES.md](FONTES.md).

O exemplo principal usa `Tesouro Prefixado com Juros Semestrais:2033-01-01`. O preço é o **PU Venda Manhã** da base do Tesouro, em reais por título. O cupom é o campo **PU** do arquivo de pagamentos, também por unidade do mesmo tipo e vencimento; `Valor` agregado e `Quantidade` não entram no retorno individual. A data de pagamento pode não ter cotação, então o fluxo entra no intervalo `(data anterior, data atual]`.

## Retornos e fatores

Para duas cotações consecutivas `P(t−1)` e `P(t)` e a soma dos cupons `C` no intervalo:

```text
retorno_preço(t) = P(t) / P(t−1) − 1
retorno_total_bruto(t) = [P(t) + C] / P(t−1) − 1
```

O retorno total é uma aproximação de um período: não reinveste cupons, não inclui impostos, custódia, spread, liquidez, inflação nem valor final de resgate. Preços ausentes ou não positivos são rejeitados; fatores sem observação nas duas datas retiram o intervalo de **ambas** as regressões.

O fator USD/BRL é a variação percentual da série SGS 1, cotação de **venda** diária. A Selic diária da série SGS 11 entra como mudança em pontos percentuais da taxa `% a.d.` entre as datas. O IPCA SGS 433 não integra o retrato público: sua licença específica ainda não foi confirmada no catálogo oficial e associar o valor do mês à primeira data do mês anteciparia informação divulgada depois.

## Regressão e validação

O modelo OLS tem intercepto e os fatores diários selecionados. O alvo é o retorno de preço ou o retorno total bruto. As datas e a matriz de fatores são idênticas nos dois ajustes. O corte padrão usa aproximadamente 80% das observações iniciais para treinamento e 20% finais para teste cronológico. A página mostra `R²` e intervalos de confiança de 95% no treino, erro quadrático médio (RMSE) no treino e no teste, coeficientes e tamanhos das duas amostras. O RMSE é exibido em pontos base (`bp = 0,0001` do retorno). Intervalos de coeficientes são os intervalos usuais da OLS; não constituem prova de relação causal.

Essa validação ainda tem limites: coeficientes podem variar no tempo, resíduos podem ter dependência, eventos podem ocorrer junto com outras notícias e a separação em um único corte não substitui validação por janelas móveis. A diferença no erro fora da amostra depende do título, dos fatores e do período selecionados.

## Comunicados e janelas

O BCB informa a data do comunicado, mas a lista pública utilizada não informa o horário. Por isso o evento só entra no **primeiro pregão disponível após a data da publicação**. Para eventos com horário explícito no futuro, a regra considera a sessão da mesma data apenas antes das 17h de São Paulo; após esse horário, usa o próximo pregão.

Para cada janela de 1, 3 ou 5 sessões comuns, os retornos diários brutos são compostos separadamente para o título estudado e para `Tesouro Prefixado:2029-01-01`. A diferença exibida é `retorno_observado − retorno_referência`. A coorte exclui janelas sobrepostas, calcula a média da diferença e, com pelo menos dois episódios, um intervalo bilateral de 95% baseado na distribuição t. São exigidas 20 observações comuns antes do evento. Quando faltam sessões antes ou depois, a API devolve um motivo explícito.

O título de referência tem prazo e risco de mercado diferentes do título estudado. A diferença é **descritiva**, não um efeito isolado do comunicado. Não há inferência intradiária nem previsão no retrato atual.
