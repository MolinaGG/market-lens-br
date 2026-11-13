from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from app.analysis.event_study import study_event, summarize_cohort
from app.analysis.returns import ReturnFrame, ReturnPoint
from app.data.models import MarketEvent


SP = ZoneInfo("America/Sao_Paulo")
DATES = [date(2026, 1, d) for d in (2, 5, 6, 7, 8, 9, 12, 13, 14, 15)]


def event(number, day, hour=None):
    published = datetime.combine(day, datetime.min.time(), SP)
    if hour is not None:
        published += timedelta(hours=hour)
    return MarketEvent(f"COPOM:{number}", "copom", "Decisão do Copom", published, hour is not None, f"https://www.bcb.gov.br/comunicado/{number}", datetime.now(timezone.utc))


def frame(name, value):
    return ReturnFrame(name, tuple(ReturnPoint(day, value, value, {}) for day in DATES))


def test_publication_alignment_before_after_close_and_unknown_time():
    observed, benchmark = frame("title", 0.1), frame("benchmark", 0.02)
    before = study_event(event(1, date(2026, 1, 5), 16), observed, benchmark, (1,), min_pre=1)
    after = study_event(event(2, date(2026, 1, 5), 18), observed, benchmark, (1,), min_pre=1)
    unknown = study_event(event(3, date(2026, 1, 5)), observed, benchmark, (1,), min_pre=1)
    holiday = study_event(event(4, date(2026, 1, 10)), observed, benchmark, (1,), min_pre=1)
    assert before.effective_session == date(2026, 1, 5)
    assert after.effective_session == date(2026, 1, 6)
    assert unknown.effective_session == date(2026, 1, 6)
    assert holiday.effective_session == date(2026, 1, 12)
    assert before.windows[1].abnormal_return == pytest.approx(0.08)
    assert before.source_url.endswith("/1")


def test_compounded_windows_and_explicit_unavailability():
    observed, benchmark = frame("title", 0.1), frame("benchmark", 0.02)
    result = study_event(event(1, date(2026, 1, 5), 16), observed, benchmark, (1, 3, 5), min_pre=1)
    assert result.windows[3].observed_return == pytest.approx(1.1**3 - 1)
    assert result.windows[3].benchmark_return == pytest.approx(1.02**3 - 1)
    assert result.windows[3].abnormal_return == pytest.approx(1.1**3 - 1.02**3)
    late = study_event(event(2, date(2026, 1, 14), 16), observed, benchmark, (1, 3, 5), min_pre=1)
    assert late.windows[3].available is False
    assert late.windows[3].reason == "insufficient_post_event"
    early = study_event(event(3, date(2026, 1, 2), 16), observed, benchmark, (1,), min_pre=2)
    assert early.windows[1].reason == "insufficient_pre_event"


def test_cohort_excludes_overlapping_windows_and_reports_uncertainty():
    observed, benchmark = frame("title", 0.03), frame("benchmark", 0.01)
    results = [study_event(event(i, day, 16), observed, benchmark, (1,), min_pre=1) for i, day in [(1, date(2026, 1, 5)), (2, date(2026, 1, 5)), (3, date(2026, 1, 8))]]
    summary = summarize_cohort(results, 1)
    assert summary.sample_count == 2
    assert summary.excluded_overlap == 1
    assert summary.mean_abnormal_return == pytest.approx(0.02)
    assert summary.confidence_interval is not None
