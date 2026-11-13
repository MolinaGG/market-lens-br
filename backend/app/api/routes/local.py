"""Opt-in loopback-only research with user-supplied equity CSVs."""

from dataclasses import asdict
from datetime import date
from io import StringIO
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from app.analysis.regression import compare_regressions
from app.analysis.returns import build_return_frame
from app.analysis.company_impact import study_filing_impact
from app.analysis.event_study import summarize_cohort
from app.api.schemas import LocalNewsImpactSchema, RegressionResponseSchema, SeriesResponseSchema
from app.data.equity_import import import_equity_csv, read_imported_equity
from app.data.article_import import parse_verified_articles
from app.data.news_store import NewsStore
from app.data.store import SnapshotStore


router = APIRouter(prefix="/local")
DEFAULT_FACTORS = ("BCB:SGS:1", "BCB:SGS:11")


class EquityUpload(BaseModel):
    prices_csv: str
    actions_csv: str


class ArticleStudyRequest(BaseModel):
    articles_csv: str
    factor_ids: list[str] | None = None


def _error(status: int, reason: str, message: str):
    raise HTTPException(status_code=status, detail={"reason": reason, "message": message})


def _check_local(request: Request) -> Path:
    if not request.app.state.local_import_enabled or request.client is None or request.client.host not in {"127.0.0.1", "::1", "testclient"}:
        _error(403, "local_import_disabled", "A importação de ações só está disponível no modo local habilitado pelo pesquisador.")
    return Path(request.app.state.local_equity_path)


def _equity(request: Request, ticker: str):
    path = _check_local(request)
    try:
        return read_imported_equity(path, ticker.upper())
    except KeyError:
        _error(404, "equity_not_found", "Esta ação ainda não foi importada no ambiente local.")


def _impact_row(source, total, price, category: str, status: str) -> dict:
    return {
        "filing_id": source.filing_id, "title": source.title, "category": category,
        "status": status, "source_url": source.source_url, "published_at": source.published_at,
        "publication_time_known": source.publication_time_known,
        "effective_session": total.event.effective_session, "train_count": total.train_count,
        "coefficients": total.coefficients, "reason": total.reason,
        "windows": {horizon: {**asdict(window), "available": window.available} for horizon, window in total.event.windows.items()},
        "price_windows": {horizon: {**asdict(window), "available": window.available} for horizon, window in price.event.windows.items()},
    }


@router.get("/status")
def local_status(request: Request):
    return {"enabled": bool(request.app.state.local_import_enabled and request.client and request.client.host in {"127.0.0.1", "::1", "testclient"})}


@router.post("/equity/import")
def import_equity(request: Request, payload: EquityUpload):
    path = _check_local(request)
    if len(payload.prices_csv) + len(payload.actions_csv) > 5_000_000:
        _error(413, "import_too_large", "Os arquivos excedem o limite local de 5 MB.")
    try:
        summary = import_equity_csv(StringIO(payload.prices_csv), StringIO(payload.actions_csv), database_path=path)
    except ValueError as exc:
        _error(422, "invalid_import", f"Os arquivos não passaram na validação: {exc}")
    return asdict(summary)


@router.get("/equity/{ticker}/series", response_model=SeriesResponseSchema)
def equity_series(request: Request, ticker: str):
    imported = _equity(request, ticker)
    info = {
        "series_id": f"EQUITY:{imported.ticker}", "name": imported.ticker, "unit": "BRL por ação",
        "source_url": f"local://import/{imported.ticker}", "observation_count": len(imported.prices),
        "start_date": imported.prices[0].date, "end_date": imported.prices[-1].date,
        "cash_flow_count": len(imported.cash_flows),
        "frequency": "daily", "source_rights": "local_only",
    }
    return {
        "version": "local-1", "series": info,
        "observations": [{"date": point.date, "value": float(point.value), "source_url": point.source_url} for point in imported.prices],
        "cash_flows": [{"date": flow.date, "amount": float(flow.amount), "source_url": flow.source_url} for flow in imported.cash_flows],
    }


@router.get("/equity/{ticker}/regression", response_model=RegressionResponseSchema)
def equity_regression(request: Request, ticker: str, factor_ids: list[str] | None = Query(default=None), train_end: date | None = None):
    imported = _equity(request, ticker)
    if not imported.cash_flows:
        _error(422, "cash_flows_missing", "Não há dividendos ou JCP completos para comparar retorno com e sem proventos.")
    factors = factor_ids or list(DEFAULT_FACTORS)
    if not factors or len(factors) > 4 or len(set(factors)) != len(factors):
        _error(422, "invalid_factors", "Escolha de uma a quatro variáveis distintas.")
    snapshot = Path(request.app.state.snapshot_path)
    if not snapshot.is_file():
        _error(503, "snapshot_missing", "O retrato público de fatores ainda não foi carregado.")
    with SnapshotStore(snapshot) as store:
        available = {item.series_id for item in store.list_series() if item.frequency == "daily" and not item.series_id.startswith("TESOURO:")}
        if any(factor not in available for factor in factors):
            _error(422, "factor_not_found", "Uma variável selecionada não está no retrato público.")
        observations = {factor: store.observations(factor) for factor in factors}
        try:
            frame = build_return_frame(imported.prices, imported.cash_flows, observations, splits=imported.splits)
            if not frame.points:
                raise ValueError("no aligned observations")
            split = train_end or frame.dates[int(len(frame.dates) * 0.8)]
            result = compare_regressions(frame, tuple(factors), split)
        except ValueError as exc:
            _error(422, "insufficient_data", f"Não há dados suficientes para a regressão: {exc}")
        return {
            "version": f"{store.snapshot_version()}+local-1", "instrument_id": frame.instrument_id,
            "factor_ids": factors, "train_end": split, "price": asdict(result.price), "total": asdict(result.total),
            "points": [asdict(point) for point in frame.points],
            "adjustment_convention": "Retorno de preço neutraliza desdobramentos; retorno total bruto inclui dividendos e JCP por ação na data ex, sem reinvestimento ou impostos.",
            "source_urls": [f"local://import/{imported.ticker}", *(observations[factor][0].source_url for factor in factors)],
        }


@router.get("/equity/{ticker}/news-impact", response_model=LocalNewsImpactSchema)
def equity_news_impact(request: Request, ticker: str, factor_ids: list[str] | None = Query(default=None), limit: int = Query(default=20, ge=1, le=50)):
    imported = _equity(request, ticker)
    factors = factor_ids or list(DEFAULT_FACTORS)
    snapshot = Path(request.app.state.snapshot_path)
    news_path = Path(request.app.state.news_path)
    if not snapshot.is_file():
        _error(503, "snapshot_missing", "O retrato público de fatores ainda não foi carregado.")
    if not news_path.is_file():
        _error(503, "news_snapshot_missing", "O retrato de documentos CVM ainda não foi carregado.")
    with SnapshotStore(snapshot) as store, NewsStore(news_path) as news:
        available = {item.series_id for item in store.list_series() if item.frequency == "daily" and not item.series_id.startswith("TESOURO:")}
        if not factors or any(factor not in available for factor in factors):
            _error(422, "factor_not_found", "Uma variável selecionada não está no retrato público.")
        frame = build_return_frame(imported.prices, imported.cash_flows, {factor: store.observations(factor) for factor in factors}, splits=imported.splits)
        filings = news.filings(imported.ticker, limit)
        impacts = [study_filing_impact(filing, frame, tuple(factors), return_mode="total") for filing in filings]
        price_impacts = [study_filing_impact(filing, frame, tuple(factors), return_mode="price") for filing in filings]
        event_rows = [_impact_row(filing, impact, price_impact, filing.category, filing.status) for filing, impact, price_impact in zip(filings, impacts, price_impacts)]
        return {
            "version": f"{store.snapshot_version()}+{news.version()}+local-1", "ticker": imported.ticker,
            "factor_ids": factors, "events": event_rows,
            "cohort": {horizon: asdict(summarize_cohort([item.event for item in impacts], horizon)) for horizon in (1, 3, 5)},
            "price_cohort": {horizon: asdict(summarize_cohort([item.event for item in price_impacts], horizon)) for horizon in (1, 3, 5)},
            "method_note": "Cada divulgação oficial CVM é comparada em retorno de preço e retorno total bruto a modelos de fatores ajustados somente com até 60 sessões anteriores. Documentos sem horário entram no pregão seguinte; cancelamentos não recebem medida. A diferença é descritiva, não causal. Metadados GDELT não entram no cálculo.",
        }


@router.post("/equity/{ticker}/article-impact", response_model=LocalNewsImpactSchema)
def equity_article_impact(request: Request, ticker: str, payload: ArticleStudyRequest):
    imported = _equity(request, ticker)
    if len(payload.articles_csv) > 200_000:
        _error(413, "article_file_too_large", "O arquivo de notícias excede 200 KB.")
    try:
        articles = parse_verified_articles(payload.articles_csv, imported.ticker)
    except ValueError as exc:
        _error(422, "invalid_articles", f"O arquivo de notícias não passou na validação: {exc}")
    factors = payload.factor_ids or list(DEFAULT_FACTORS)
    if not factors or len(factors) > 4 or len(set(factors)) != len(factors):
        _error(422, "invalid_factors", "Escolha de uma a quatro variáveis distintas.")
    snapshot = Path(request.app.state.snapshot_path)
    if not snapshot.is_file():
        _error(503, "snapshot_missing", "O retrato público de fatores ainda não foi carregado.")
    with SnapshotStore(snapshot) as store:
        available = {item.series_id for item in store.list_series() if item.frequency == "daily" and not item.series_id.startswith("TESOURO:")}
        if any(factor not in available for factor in factors):
            _error(422, "factor_not_found", "Uma variável selecionada não está no retrato público.")
        frame = build_return_frame(imported.prices, imported.cash_flows, {factor: store.observations(factor) for factor in factors}, splits=imported.splits)
        total = [study_filing_impact(article, frame, tuple(factors), return_mode="total") for article in articles]
        price = [study_filing_impact(article, frame, tuple(factors), return_mode="price") for article in articles]
        return {
            "version": f"{store.snapshot_version()}+local-articles-1", "ticker": imported.ticker,
            "factor_ids": factors,
            "events": [_impact_row(article, total_result, price_result, "Notícia verificada", "active") for article, total_result, price_result in zip(articles, total, price)],
            "cohort": {horizon: asdict(summarize_cohort([item.event for item in total], horizon)) for horizon in (1, 3, 5)},
            "price_cohort": {horizon: asdict(summarize_cohort([item.event for item in price], horizon)) for horizon in (1, 3, 5)},
            "method_note": "Notícias fornecidas pelo pesquisador, com URL e data de publicação verificadas, usam modelos ajustados com até 60 pregões anteriores. Horário com fuso conhecido segue a regra de fechamento das 17h; data sem horário começa no pregão seguinte. A diferença é associação temporal descritiva, não efeito causal.",
        }
