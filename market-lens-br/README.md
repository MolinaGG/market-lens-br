# market-lens-br

Ferramenta para entender notícias e investigar seus possíveis efeitos sobre ativos da B3 e o câmbio USD/BRL nos próximos pregões.

> **Aviso:** este projeto é educacional e experimental. Não é recomendação de investimento. As projeções são estimativas estatísticas com incerteza e podem estar erradas.

## Arquitetura

Monorepo com dois pacotes que podem ser publicados juntos:

| Pacote | Tecnologia | Responsabilidade |
|---|---|---|
| `backend/` | FastAPI (Python) | Coleta, IA (Groq), cálculos estatísticos e relatórios |
| `frontend/` | React + Vite + TypeScript | Dashboard e interação com o usuário |

Integrações externas: **Apify** (coleta de notícias) e **Groq** (interpretação e organização dos acontecimentos). Armazenamento inicial em **SQLite**, com a camada de dados preparada para migração. Redis é opcional.

Detalhes do desenho em [`docs/ARQUITETURA.md`](docs/ARQUITETURA.md).

## Escopo inicial

- Mercado: Brasil
- Horizonte de projeção: 14 pregões
- Ativos: Ibovespa, USD/BRL, PETR4, VALE3, ITUB4, BBDC4, WEGE3, ABEV3

## Como rodar

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp ../.env.example ../.env   # preencha as chaves
uvicorn app.main:app --reload
pytest
```

### Frontend

```bash
cd frontend
npm install
npm run dev
npm run build
```

## Licença

Todos os direitos reservados. Veja [`LICENSE`](LICENSE).
