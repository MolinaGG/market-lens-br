"""Pre-event factor benchmark for descriptive company filing windows."""

from dataclasses import dataclass
from datetime import date

import numpy as np

from app.analysis.event_study import EventStudyResult, EventWindow, study_event
from app.analysis.returns import ReturnFrame, ReturnPoint
from app.data.cvm import CompanyFiling
from app.data.models import MarketEvent


@dataclass(frozen=True)
class FilingImpact:
    filing_id: str
    ticker: str
    event: EventStudyResult
    train_count: int
    coefficients: dict[str, float] | None
    reason: str | None


def study_filing_impact(
    filing: CompanyFiling,
    frame: ReturnFrame,
    factor_ids: tuple[str, ...],
    lookback: int = 60,
    horizons: tuple[int, ...] = (1, 3, 5),
) -> FilingImpact:
    event = MarketEvent(
        filing.filing_id, f"company:{filing.ticker}", filing.title,
        filing.published_at, filing.publication_time_known, filing.source_url, filing.fetched_at,
    )
    earliest = filing.published_at.date()
    if not filing.publication_time_known:
        from datetime import timedelta
        earliest += timedelta(days=1)
    pre = [point for point in frame.points if point.date < earliest and all(factor in point.factor_changes for factor in factor_ids)][-lookback:]
    unavailable = None
    if not filing.impact_eligible:
        unavailable = "filing_cancelled"
    elif len(pre) < max(20, len(factor_ids) + 3):
        unavailable = "insufficient_pre_event_model"
    if unavailable:
        next_session = next((point.date for point in frame.points if point.date >= earliest), None)
        empty = EventStudyResult(
            event.event_id, event.title, event.source_url, event.published_at,
            event.publication_time_known, next_session, frame.instrument_id,
            "PRE_EVENT_FACTOR_MODEL", {horizon: EventWindow(horizon, (), None, None, None, unavailable) for horizon in horizons},
        )
        return FilingImpact(filing.filing_id, filing.ticker, empty, len(pre), None, unavailable)
    x = np.array([[1.0, *(point.factor_changes[factor] for factor in factor_ids)] for point in pre], dtype=float)
    y = np.array([point.total_return for point in pre], dtype=float)
    if not np.isfinite(x).all() or not np.isfinite(y).all() or np.linalg.matrix_rank(x) < x.shape[1]:
        empty = EventStudyResult(event.event_id, event.title, event.source_url, event.published_at, event.publication_time_known, None, frame.instrument_id, "PRE_EVENT_FACTOR_MODEL", {h: EventWindow(h, (), None, None, None, "rank_deficient_factors") for h in horizons})
        return FilingImpact(filing.filing_id, filing.ticker, empty, len(pre), None, "rank_deficient_factors")
    beta, *_ = np.linalg.lstsq(x, y, rcond=None)
    benchmark_points = []
    for point in frame.points:
        if not all(factor in point.factor_changes for factor in factor_ids):
            continue
        prediction = float(beta[0] + sum(beta[index + 1] * point.factor_changes[factor] for index, factor in enumerate(factor_ids)))
        benchmark_points.append(ReturnPoint(point.date, prediction, prediction, point.factor_changes))
    baseline = ReturnFrame("PRE_EVENT_FACTOR_MODEL", tuple(benchmark_points))
    result = study_event(event, frame, baseline, horizons=horizons, min_pre=20)
    return FilingImpact(filing.filing_id, filing.ticker, result, len(pre), dict(zip(("intercept", *factor_ids), (float(value) for value in beta))), None)
