# Fontes, atribuição e versão do retrato

O retrato `backend/demo/open_data_snapshot.sqlite.gz` foi produzido em 13/11/2026, com normalização versão `1` e versão do retrato `20261113T181936Z-bb5f68ed69b0`. Seu SHA-256 é `07cd2bfc678aac83daff9c9961768de195d2ee9c69d173d0837402dd2a505826`. A base derivada é disponibilizada sob [Open Database License (ODbL) 1.0](https://opendatacommons.org/licenses/odbl/1-0/), com atribuição às organizações e conjuntos abaixo. O código do projeto tem licença própria em `LICENSE`.

| Dados usados | Titular / conjunto oficial | Licença indicada pelo portal | Uso neste projeto |
| --- | --- | --- | --- |
| [Preços e taxas do Tesouro Direto](https://www.tesourotransparente.gov.br/ckan/dataset/taxas-dos-titulos-ofertados-pelo-tesouro-direto) | Tesouro Nacional, Tesouro Transparente | ODbL | `PU Venda Manhã`, tipo, vencimento e data base. |
| [Pagamento de cupom de juros](https://www.tesourotransparente.gov.br/ckan/dataset/resgates-do-tesouro-direto) | Tesouro Nacional, Tesouro Transparente | ODbL | `PU` por unidade, tipo, vencimento e data de pagamento. |
| [USD/BRL venda, SGS 1](https://dadosabertos.bcb.gov.br/dataset/1-taxa-de-cambio---livre---dolar-americano-venda---diario) | Banco Central do Brasil, SGS | ODbL | Variação percentual diária do câmbio. |
| [Selic diária, SGS 11](https://dadosabertos.bcb.gov.br/dataset/11-taxa-de-juros---selic) | Banco Central do Brasil, SGS | ODbL | Variação da taxa diária em pontos percentuais. |
| [Documentos do Copom](https://dadosabertos.bcb.gov.br/dataset/atas-comunicados-copom) | Banco Central do Brasil | ODbL | Número, data, título e link do comunicado. |

Os endereços exatos dos arquivos e APIs consultados ficam em `backend/app/data/tesouro.py`, `bcb.py` e `copom.py`. Cada registro normalizado mantém o endereço da fonte e o horário de coleta. O identificador do retrato incorpora a hora UTC da coleta e os primeiros 12 caracteres do SHA-256 das respostas originais. O arquivo compactado permite reproduzir a demonstração mesmo se a fonte mudar depois; `python -m app.data.refresh` cria uma nova versão local.

O banco contém somente dados das fontes oficiais listadas. Não inclui preços de ações da B3, textos jornalísticos nem dados de serviços que restringem redistribuição. O IPCA SGS 433 ficou fora do retrato público até a confirmação de sua licença específica.
