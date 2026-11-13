"""Company filings and article context, with provenance and timing limits."""

from dataclasses import asdict
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Request

from app.api.schemas import CompanyNewsSchema
from app.data.cvm import CVM_CODES
from app.data.news_store import NewsStore


router = APIRouter(prefix="/company")


@router.get("/news", response_model=CompanyNewsSchema)
def company_news(request: Request, ticker: str, limit: int = Query(default=15, ge=1, le=50)):
    ticker = ticker.upper()
    if ticker not in CVM_CODES:
        raise HTTPException(404, detail={"reason": "company_not_mapped", "message": "A companhia ainda não tem código CVM verificado neste projeto."})
    path = Path(request.app.state.news_path)
    if not path.is_file():
        raise HTTPException(503, detail={"reason": "news_snapshot_missing", "message": "O retrato de documentos de companhias ainda não foi criado."})
    with NewsStore(path) as store:
        filings = store.filings(ticker, limit)
        articles = store.articles(ticker, min(limit, 15))
        return {
            "version": store.version(), "fetched_at": store.fetched_at(), "ticker": ticker,
            "company_code": CVM_CODES[ticker],
            "filings": [{**asdict(item), "impact_eligible": item.impact_eligible} for item in filings],
            "articles": [asdict(item) for item in articles],
            "method_note": "A data da entrega CVM não informa o horário; eventos são alinhados ao pregão seguinte. O horário GDELT indica detecção, não publicação confirmada. Menções passam por filtro de nome no título, que não comprova relevância econômica. Links servem como contexto, sem inferência causal.",
        }
