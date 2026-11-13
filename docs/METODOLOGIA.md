# Metodologia da demonstração

## Retrato e unidades

O retrato de mercado incluído no repositório é `20261113T185107Z-09e85368904f`, coletado em 13 de novembro de 2026. Contém 63.708 observações de preços e fatores, 155 pagamentos por título e 100 comunicados do Copom. O recorte começa aproximadamente cinco anos antes da coleta. Um segundo retrato, `20261113T190028Z-e1632c68dbe2`, contém 660 documentos da CVM de 2025 e 2026 para seis companhias, além de 2 links de menções GDELT para BBDC4. A cobertura jornalística é parcial e depende da disponibilidade da consulta. Fontes e hashes estão em [FONTES.md](FONTES.md).

O exemplo principal usa `Tesouro Prefixado com Juros Semestrais:2033-01-01`. O preço é o **PU Venda Manhã** da base do Tesouro, em reais por título. O cupom é o campo **PU** do arquivo de pagamentos, também por unidade do mesmo tipo e vencimento; `Valor` agregado e `Quantidade` não entram no retorno individual. A data de pagamento pode não ter cotação, então o fluxo entra no intervalo `(data anterior, data atual]`.

## Retornos e fatores

Para duas cotações consecutivas `P(t−1)` e `P(t)` e a soma dos cupons `C` no intervalo:

```text
retorno_preço(t) = P(t) / P(t−1) − 1
retorno_total_bruto(t) = [P(t) + C] / P(t−1) − 1
```

O retorno total é uma aproximação de um período: não reinveste cupons, não inclui impostos, custódia, spread, liquidez, inflação nem valor final de resgate. Preços ausentes ou não positivos são rejeitados; fatores sem observação nas duas datas retiram o intervalo de **ambas** as regressões.

O fator USD/BRL é a variação percentual da série SGS 1, cotação de **venda** diária. A Selic diária da série SGS 11 entra como mudança em pontos percentuais da taxa `% a.d.` entre as datas. Brent diário da EIA entra como variação percentual do preço em USD/barril. O alinhamento exige observações de cada fator em ambas as datas do intervalo e elimina o mesmo intervalo dos dois modelos quando algum fator falta. A data da cotação EIA indica o dia observado, não garante que a informação estivesse disponível naquele horário; por isso, a regressão é descritiva e a separação de teste não deve ser interpretada como simulação operacional de negociação.

Ouro, cobre, café arábica e Brent da Pink Sheet do Banco Mundial são **médias mensais nominais em USD**. O primeiro dia do mês é apenas um rótulo de período no banco; o dado costuma ser publicado no mês seguinte. As séries são exibidas em cartões de comparação mensal, mas não entram na regressão diária e não são preenchidas para dias sem observação. O IPCA SGS 433 também não integra o retrato público: sua licença específica ainda não foi confirmada no catálogo oficial e associar o valor do mês à primeira data do mês anteciparia informação divulgada depois.

## Regressão e validação

O modelo OLS tem intercepto e os fatores diários selecionados. O alvo é o retorno de preço ou o retorno total bruto. As datas e a matriz de fatores são idênticas nos dois ajustes. O corte padrão usa aproximadamente 80% das observações iniciais para treinamento e 20% finais para teste cronológico. A página mostra `R²` e intervalos de confiança de 95% no treino, erro quadrático médio (RMSE) no treino e no teste, coeficientes e tamanhos das duas amostras. O RMSE é exibido em pontos base (`bp = 0,0001` do retorno). Intervalos de coeficientes são os intervalos usuais da OLS; não constituem prova de relação causal.

Na interface, `R²` indica a fração da variação do retorno descrita pelo modelo **no treino**; não é probabilidade de acerto. O RMSE resume o tamanho típico dos erros, e 100 bp equivalem a 1 ponto percentual de retorno. O coeficiente de cada fator mede a mudança associada no retorno com os demais fatores constantes; o intercepto é o retorno estimado quando todas as mudanças dos fatores são zero. O intervalo de 95% trata da incerteza do **coeficiente** sob as hipóteses da OLS, não da faixa do próximo retorno. Diferenças entre R², retornos ou retornos anormais são expressas em **pontos percentuais (p.p.)**, nunca como variação percentual relativa.

Essa validação ainda tem limites: coeficientes podem variar no tempo, resíduos podem ter dependência, eventos podem ocorrer junto com outras notícias e a separação em um único corte não substitui validação por janelas móveis. A diferença no erro fora da amostra depende do título, dos fatores e do período selecionados.

## Comunicados e janelas

O BCB informa a data do comunicado, mas a lista pública utilizada não informa o horário. Por isso o evento só entra no **primeiro pregão disponível após a data da publicação**. Para eventos com horário explícito no futuro, a regra considera a sessão da mesma data apenas antes das 17h de São Paulo; após esse horário, usa o próximo pregão.

Para cada janela de 1, 3 ou 5 sessões comuns, os retornos diários brutos são compostos separadamente para o título estudado e para `Tesouro Prefixado:2029-01-01`. A diferença exibida é `retorno_observado − retorno_referência`. A coorte exclui janelas sobrepostas, calcula a média da diferença e, com pelo menos dois episódios, um intervalo bilateral de 95% baseado na distribuição t. São exigidas 20 observações comuns antes do evento. Quando faltam sessões antes ou depois, a API devolve um motivo explícito.

O título de referência tem prazo e risco de mercado diferentes do título estudado. A diferença é **descritiva**, não um efeito isolado do comunicado. Não há inferência intradiária nem previsão no retrato atual.

## Ações, proventos e documentos

O pesquisador importa preços de fechamento, desdobramentos e proventos por ação em arquivos CSV próprios. Para um intervalo entre duas cotações, o retorno de preço considera a nova quantidade de ações após um desdobramento; o retorno total bruto soma os dividendos e JCP com data ex no intervalo, multiplicados pela quantidade de ações válida em cada pagamento. Os dois modos usam as mesmas datas de preços e fatores. Não há reinvestimento, ajuste de impostos, taxas ou verificação independente da integridade do arquivo fornecido. Sem um evento de provento completo, a comparação é desabilitada.

O arquivo IPE da CVM liga fatos relevantes e comunicados ao mercado ao código da companhia. A identidade do documento usa o link original, pois o protocolo pode se repetir. Reapresentações do mesmo assunto são reunidas e cancelamentos são preservados como evidência, mas excluídos do estudo de impacto. O arquivo fornece data de entrega sem horário verificável; o primeiro pregão analisado é o seguinte à entrega. O estudo quantitativo de ações considera **Fato Relevante e Comunicado ao Mercado** da CVM, jamais apenas uma menção jornalística.

Para cada divulgação elegível, **dois** modelos de fatores são ajustados separadamente em até 60 sessões anteriores, com no mínimo 20 sessões: um para retorno de preço e outro para retorno total bruto. Eles usam as mesmas datas, fatores e janelas posteriores de 1, 3 e 5 pregões. O retorno observado e o retorno esperado são compostos em cada janela; a diferença em p.p. é uma medida descritiva de retorno anormal. A diferença entre os retornos observados com e sem proventos mostra quanto o pagamento entrou naquela janela; a diferença entre os retornos anormais também pode mudar porque os dois modelos são reajustados. Fatores realizados no período posterior entram no referencial ex post, de modo que o resultado não é uma previsão negociável. A média de divulgações exclui janelas sobrepostas, e o intervalo de 95% descreve a incerteza dessa média sob hipóteses estatísticas. Eventos sobrepostos e dados ausentes podem limitar a coorte.

O GDELT fornece somente título, URL, domínio e horário de **detecção**; esse horário não é tratado como publicação confirmada. Um filtro exige o nome da companhia no título, mas isso não comprova relevância econômica para a ação. Cada link jornalístico aparece como contexto, com impacto não mensurado enquanto não houver horário de publicação verificável e identificação inequívoca do ativo afetado. Links jornalísticos não entram no cálculo. Notícias simultâneas, seleção de eventos, qualidade das cotações importadas e mudanças dos fatores impedem interpretação causal. A definição de retorno anormal segue o estudo de eventos de [MacKinlay](https://www.bu.edu/econ/files/2011/01/MacKinlay-1996-Event-Studies-in-Economics-and-Finance.pdf), adaptado aqui a um referencial de fatores estimado antes de cada divulgação.
