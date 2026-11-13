# Market Lens BR

Pesquisa quantitativa reproduzível sobre mercado brasileiro, retornos de títulos e comunicados do Copom. A demonstração pública compara uma regressão de **retorno de preço** com a mesma regressão após incorporar **cupons por unidade**, usando exatamente as mesmas datas e variáveis.

![Painel de pesquisa do Market Lens BR](docs/assets/market-lens-dashboard.png)

## O que já funciona

- Catálogo de títulos do Tesouro, USD/BRL e Selic diária, com fonte, unidade, período e versão do retrato.
- Gráfico de retorno acumulado com e sem cupons; pagamentos no intervalo entre duas cotações são atribuídos ao retorno desse intervalo.
- Regressão OLS com coeficientes, intervalos de 95%, R², erro e validação temporal fora da amostra. O botão destaca cada modo sem trocar as datas ou os fatores.
- Comunicados oficiais do Copom ligados a janelas posteriores de 1, 3 e 5 pregões, comparados a outro título do Tesouro. A página mostra a fonte, o tamanho da amostra e a incerteza do conjunto de eventos.
- Retrato público congelado, incluído em `backend/demo/`, e comando separado para atualizá-lo a partir das fontes oficiais.

O projeto é uma análise histórica exploratória. Diferenças após um comunicado são associações temporais, não estimativas causais nem recomendações de investimento. O método completo está em [docs/METODOLOGIA.md](docs/METODOLOGIA.md).

## Executar localmente

Requisitos: Python 3.12+ e Node.js 20+.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -e "backend[dev]"
cd backend
python -m app.data.demo
uvicorn app.main:app --reload
```

Em outro terminal:

```bash
cd frontend
npm ci
npm run dev
```

Abra `http://localhost:5173`. O Vite encaminha `/api` ao backend local. Para atualizar o retrato com as fontes oficiais, rode na pasta `backend/`:

```bash
python -m app.data.refresh --database data/market_lens.db
```

Essa operação baixa os CSVs do Tesouro e as APIs do BCB, valida os dados e substitui o banco local somente após concluir a nova versão. O banco local fica fora do Git. Para voltar ao retrato do repositório, remova **apenas** `backend/data/market_lens.db` e execute `python -m app.data.demo` novamente.

## Verificar

```bash
cd backend
python -m pytest -q
cd ../frontend
npm run build
```

Os contratos estão disponíveis em `/api/catalog`, `/api/series/{series_id}`, `/api/research/regression` e `/api/events`; a documentação interativa fica em `/docs` no backend.

## Estrutura e próximos módulos

| Pasta | Responsabilidade |
| --- | --- |
| `backend/app/data/` | Coleta, normalização, proveniência e retrato SQLite. |
| `backend/app/analysis/` | Retornos, regressões e estudos de eventos. |
| `backend/app/api/` | API de pesquisa. |
| `frontend/src/` | Experiência de exploração em React e TypeScript. |
| `backend/demo/` | Retrato aberto congelado para a demonstração. |

A sequência de trabalho inclui importação local de ações e proventos, fatos relevantes da CVM, contexto jornalístico e commodities. Cotações de ações não entram no retrato público enquanto não houver direitos claros de redistribuição. O desenho está em [docs/ARQUITETURA.md](docs/ARQUITETURA.md) e as fontes e licenças em [docs/FONTES.md](docs/FONTES.md).

## Publicação

`render.yaml` prepara o backend e descompacta o retrato público na inicialização. `frontend/vercel.json` configura o frontend; a URL de destino `/api` deve corresponder ao serviço Render criado. Nenhuma chave de Apify ou Groq é necessária para a demonstração atual. A publicação externa depende da configuração das contas de hospedagem.

O código segue [LICENSE](LICENSE); o banco derivado em `backend/demo/` segue a [ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/) e mantém atribuição às fontes em [docs/FONTES.md](docs/FONTES.md).
