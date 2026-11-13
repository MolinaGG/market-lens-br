"""Session-aligned descriptive event windows; association is not causation."""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from math import prod, sqrt
from statistics import mean, stdev

from scipy.stats import t

from app.analysis.returns import ReturnFrame
from app.data.models import MarketEvent


SAO_PAULO = timezone(timedelta(hours=-3))
MARKET_CLOSE = time(17, 0)


@dataclass(frozen=True)
class EventWindow:
    horizon: int
    session_dates: tuple[date, ...]
    observed_return: float | None
    benchmark_return: float | None
    abnormal_return: float | None
    reason: str | None = None

    @property
    def available(self) -> bool:
        return self.reason is None


@dataclass(frozen=True)
class EventStudyResult:
    event_id: str
    title: str
    source_url: str
    published_at: datetime
    publication_time_known: bool
    effective_session: date | None
    instrument_id: str
    benchmark_id: str
    windows: dict[int, EventWindow]


@dataclass(frozen=True)
class CohortSummary:
    horizon: int
    sample_count: int
    excluded_overlap: int
    mean_abnormal_return: float | None
    confidence_interval: tuple[float, float] | None


def _earliest_session_date(event: MarketEvent) -> date:
    local = event.published_at.astimezone(SAO_PAULO)
    publication_date = event.published_at.date() if not event.publication_time_known else local.date()
    if not event.publication_time_known or local.time() >= MARKET_CLOSE:
        return publication_date + timedelta(days=1)
    return publication_date


def study_event(
    event: MarketEvent,
    returns: ReturnFrame,
    benchmark: ReturnFrame,
    horizons: tuple[int, ...] = (1, 3, 5),
    min_pre: int = 20,
) -> EventStudyResult:
    if any(horizon < 1 for horizon in horizons):
        raise ValueError("horizons must be positive")
    observed = {point.date: point for point in returns.points}
    baseline = {point.date: point for point in benchmark.points}
    common_dates = sorted(observed.keys() & baseline.keys())
    earliest = _earliest_session_date(event)
    pre_count = sum(day < earliest for day in common_dates)
    post_dates = [day for day in common_dates if day >= earliest]
    effective = post_dates[0] if post_dates else None
    windows = {}
    for horizon in horizons:
        if pre_count < min_pre:
            windows[horizon] = EventWindow(horizon, (), None, None, None, "insufficient_pre_event")
        elif not post_dates:
            windows[horizon] = EventWindow(horizon, (), None, None, None, "no_post_event_session")
        elif len(post_dates) < horizon:
            windows[horizon] = EventWindow(horizon, tuple(post_dates), None, None, None, "insufficient_post_event")
        else:
            dates = tuple(post_dates[:horizon])
            observed_return = prod(1 + observed[day].total_return for day in dates) - 1
            benchmark_return = prod(1 + baseline[day].total_return for day in dates) - 1
            windows[horizon] = EventWindow(horizon, dates, observed_return, benchmark_return, observed_return - benchmark_return)
    return EventStudyResult(event.event_id, event.title, event.source_url, event.published_at, event.publication_time_known, effective, returns.instrument_id, benchmark.instrument_id, windows)


def summarize_cohort(results: list[EventStudyResult], horizon: int) -> CohortSummary:
    usable = sorted(
        (result for result in results if horizon in result.windows and result.windows[horizon].available),
        key=lambda result: result.effective_session or date.max,
    )
    selected = []
    occupied: set[date] = set()
    excluded = 0
    for result in usable:
        window = result.windows[horizon]
        if occupied.intersection(window.session_dates):
            excluded += 1
            continue
        occupied.update(window.session_dates)
        selected.append(window.abnormal_return)
    values = [value for value in selected if value is not None]
    if not values:
        return CohortSummary(horizon, 0, excluded, None, None)
    average = mean(values)
    interval = None
    if len(values) >= 2:
        margin = float(t.ppf(0.975, len(values) - 1)) * stdev(values) / sqrt(len(values))
        interval = (average - margin, average + margin)
    return CohortSummary(horizon, len(values), excluded, average, interval)
