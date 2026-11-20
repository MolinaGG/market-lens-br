# Estudo de caso: definições de retorno comparáveis

[English](CASE_STUDY.md) · [Demonstração](https://market-lens-br-web.onrender.com/) · [Projeto](../README.pt-BR.md)

## Problema

Variações de preço omitem cupons recebidos pelo investidor. Comparar análises com datas ou fatores diferentes confundiria a mudança na definição de retorno com a mudança da amostra.

## Método

Market Lens calcula retorno de preço e retorno com cupons a partir das mesmas observações. Os cupons entram no intervalo entre cotações consecutivas. Fatores ausentes removem o intervalo dos dois modelos. As regressões OLS usam matrizes de fatores iguais e períodos cronológicos de treino e teste.

Para preços consecutivos P0 e P1 e cupons C no intervalo:

```text
retorno_preço = P1 / P0 - 1
retorno_com_cupons = (P1 + C) / P0 - 1
```

É retorno bruto de um período, não retorno líquido com reinvestimento. A interface mostra coeficientes, intervalos de confiança de 95%, R² e erro para permitir inspecionar o efeito da definição escolhida.

## Resultado observável

A entrega é uma comparação reproduzível e inspecionável. O portfólio não afirma um desempenho financeiro fixo: coeficientes e erros dependem do título, dos fatores e do período. O resultado metodológico é a comparabilidade da amostra, não uma comprovação de capacidade preditiva.

## Evidências

- [Implementação dos retornos](../backend/app/analysis/returns.py).
- [Regressão e teste cronológico](../backend/app/analysis/regression.py).
- [Testes de alocação dos cupons e amostras iguais](../backend/tests/test_returns_regression.py).
- [Metodologia completa](METODOLOGIA.md) e [origem dos dados](FONTES.md).

## Limites e discussão da contribuição

Não inclui reinvestimento de cupons, impostos, custódia, spread, liquidez ou ajuste de inflação. A observação diária de um fator não garante publicação contemporânea; o teste temporal não é um backtest operacional de negociação. Diferenças após eventos são associações descritivas, não efeitos causais. Cotações de ações permanecem nas importações locais.

Em uma entrevista, explorar seleção de fontes, alinhamento de intervalos, ausências, separação temporal e incerteza. O histórico do repositório deve apoiar a discussão da contribuição pessoal e do uso de IA; uma demonstração não comprova autoria independente de todos os componentes.
