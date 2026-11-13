"""Source-attributed public research API backed by one local snapshot."""

from dataclasses import asdict
from datetime import date
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Request

from app.analysis.event_study import study_event, summarize_cohort
from app.analysis.regression import compare_regressions
from app.analysis.returns import build_return_frame
from app.api.schemas import CatalogSchema, EventsResponseSchema, RegressionResponseSchema, SeriesResponseSchema
from app.data.store import SnapshotStore


router = APIRouter()
DEFAULT_INSTRUMENT = "TESOURO:Tesouro Prefixado com Juros Semestrais:2033-01-01"
DEFAULT_BENCHMARK = "TESOURO:Tesouro Prefixado:2029-01-01"
DEFAULT_FACTORS = ("BCB:SGS:1", "BCB:SGS:11")


def _unavailable(status: int, reason: str, message: str):
    raise HTTPException(status_code=status, detail={"reason": reason, "message": message})


def _store(request: Request) -> SnapshotStore:
    path = Path(request.app.state.snapshot_path)
    if not path.is_file():
        _unavailable(503, "snapshot_missing", "O retrato de dados ainda não foi criado. Execute a atualização das fontes abertas.")
    return SnapshotStore(path)


def _series_info(store: SnapshotStore, series_id: str):
    return next((item for item in store.list_series() if item.series_id == series_id), None)


@router.get("/catalog", response_model=CatalogSchema)
def catalog(request: Request):
    with _store(request) as store:
        infos = store.list_series()
        instruments = []
        factors = []
        for info in infos:
            item = {**asdict(info), "cash_flow_count": len(store.cash_flows(info.series_id)) if info.series_id.startswith("TESOURO:") else 0}
            (instruments if info.series_id.startswith("TESOURO:") else factors).append(item)
        instruments.sort(key=lambda item: (-item["cash_flow_count"], item["name"]))
        ids = {item["series_id"] for item in instruments}
        default = DEFAULT_INSTRUMENT if DEFAULT_INSTRUMENT in ids else (instruments[0]["series_id"] if instruments else "")
        benchmark = DEFAULT_BENCHMARK if DEFAULT_BENCHMARK in ids else (instruments[0]["series_id"] if instruments else "")
        return {"version": store.snapshot_version(), "fetched_at": store.fetched_at(), "instruments": instruments, "factors": factors, "default_instrument_id": default, "benchmark_id": benchmark}


@router.get("/series/{series_id:path}", response_model=SeriesResponseSchema)
def series(request: Request, series_id: str, start: date | None = None, end: date | None = None, limit: int = Query(default=2000, ge=1, le=2000)):
    if start and end and start > end:
        _unavailable(422, "invalid_window", "A data inicial deve anteceder a data final.")
    with _store(request) as store:
        info = _series_info(store, series_id)
        if info is None:
            _unavailable(404, "series_not_found", "A série solicitada não existe no retrato atual.")
        observations = store.observations(series_id, start, end)[-limit:]
        flows = [flow for flow in store.cash_flows(series_id) if (start is None or flow.date >= start) and (end is None or flow.date <= end)]
        return {
            "version": store.snapshot_version(),
            "series": {**asdict(info), "cash_flow_count": len(store.cash_flows(series_id))},
            "observations": [{"date": item.date, "value": float(item.value), "source_url": item.source_url} for item in observations],
            "cash_flows": [{"date": item.date, "amount": float(item.amount), "source_url": item.source_url} for item in flows],
        }


@router.get("/research/regression", response_model=RegressionResponseSchema)
def regression(request: Request, instrument_id: str, factor_ids: list[str] | None = Query(default=None), train_end: date | None = None):
    factor_ids = factor_ids or list(DEFAULT_FACTORS)
    if len(factor_ids) > 4 or len(set(factor_ids)) != len(factor_ids):
        _unavailable(422, "invalid_factors", "Escolha de uma a quatro variáveis distintas.")
    with _store(request) as store:
        info = _series_info(store, instrument_id)
        if info is None:
            _unavailable(404, "series_not_found", "O título solicitado não existe no retrato atual.")
        if not instrument_id.startswith("TESOURO:"):
            _unavailable(422, "invalid_instrument", "A regressão requer um título do Tesouro.")
        if any((_series_info(store, factor) is None or _series_info(store, factor).frequency != "daily") for factor in factor_ids):
            _unavailable(422, "insufficient_data", "Uma variável não tem observações comparáveis neste retrato.")
        prices = store.observations(instrument_id)
        flows = store.cash_flows(instrument_id)
        factors = {factor: store.observations(factor) for factor in factor_ids}
        try:
            frame = build_return_frame(prices, flows, factors)
            if not frame.points:
                raise ValueError("no aligned observations")
            split = train_end or frame.dates[int(len(frame.dates) * 0.8)]
            result = compare_regressions(frame, tuple(factor_ids), split)
        except ValueError as exc:
            _unavailable(422, "insufficient_data", f"Não há dados suficientes para uma regressão comparável: {exc}")
        return {
            "version": store.snapshot_version(),
            "instrument_id": instrument_id,
            "factor_ids": factor_ids,
            "train_end": split,
            "price": asdict(result.price),
            "total": asdict(result.total),
            "points": [asdict(point) for point in frame.points],
            "adjustment_convention": "Retorno bruto por preço de venda do Tesouro; retorno total soma PU de cupons pagos no intervalo (sem reinvestimento, custos ou impostos).",
            "source_urls": sorted({info.source_url, *(flow.source_url for flow in flows), *(item.source_url for series in factors.values() for item in series[:1])}),
        }


@router.get("/events", response_model=EventsResponseSchema)
def events(request: Request, topic: str = "copom", instrument_id: str = DEFAULT_INSTRUMENT, benchmark_id: str = DEFAULT_BENCHMARK, limit: int = Query(default=12, ge=1, le=100)):
    if topic != "copom":
        _unavailable(422, "unsupported_topic", "Este retrato contém comunicados do Copom.")
    with _store(request) as store:
        if _series_info(store, instrument_id) is None or _series_info(store, benchmark_id) is None:
            _unavailable(404, "series_not_found", "O título ou a referência não existe no retrato atual.")
        observed = build_return_frame(store.observations(instrument_id), store.cash_flows(instrument_id), {})
        benchmark = build_return_frame(store.observations(benchmark_id), store.cash_flows(benchmark_id), {})
        source_events = store.events(topic)
        studies = [study_event(event, observed, benchmark) for event in source_events]
        results = []
        for source, study in zip(source_events[:limit], studies[:limit]):
            results.append({
                "event_id": study.event_id, "title": study.title, "source_url": study.source_url,
                "published_at": study.published_at, "publication_time_known": study.publication_time_known,
                "observed_at": source.observed_at, "effective_session": study.effective_session,
                "windows": {horizon: {**asdict(window), "available": window.available} for horizon, window in study.windows.items()},
            })
        return {
            "version": store.snapshot_version(), "topic": topic, "instrument_id": instrument_id, "benchmark_id": benchmark_id,
            "events": results, "cohort": {horizon: asdict(summarize_cohort(studies, horizon)) for horizon in (1, 3, 5)},
            "method_note": "Diferença descritiva entre retorno total do título e retorno total da referência. O horário dos comunicados é desconhecido; usa-se o pregão seguinte. Associação temporal não implica causalidade.",
        }
