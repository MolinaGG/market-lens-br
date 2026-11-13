from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.analysis.regression import compare_regressions
from app.analysis.returns import ReturnFrame, ReturnPoint, build_return_frame
from app.data.models import CashFlow, Observation


NOW = datetime(2026, 11, 13, tzinfo=timezone.utc)
INSTRUMENT = "TESOURO:Tesouro Prefixado com Juros Semestrais:2033-01-01"
FACTOR = "BCB:SGS:1"


def obs(series, day, value):
    return Observation(series, day, Decimal(str(value)), "https://source.example/data", NOW)


def test_coupon_between_quotes_and_factor_alignment():
    prices = [obs(INSTRUMENT, date(2026, 1, 2), 100), obs(INSTRUMENT, date(2026, 1, 5), 99), obs(INSTRUMENT, date(2026, 1, 6), 101)]
    flows = [CashFlow(INSTRUMENT, date(2026, 1, 3), Decimal("2"), "https://source.example/coupon", NOW)]
    factors = {FACTOR: [obs(FACTOR, date(2026, 1, 2), 5), obs(FACTOR, date(2026, 1, 5), 5.1), obs(FACTOR, date(2026, 1, 6), 5.0)]}
    frame = build_return_frame(prices, flows, factors)
    assert frame.dates == (date(2026, 1, 5), date(2026, 1, 6))
    assert frame.points[0].price_return == pytest.approx(-0.01)
    assert frame.points[0].total_return == pytest.approx(0.01)
    assert frame.points[0].factor_changes[FACTOR] == pytest.approx(0.02)
    assert frame.points[1].price_return == frame.points[1].total_return
    assert build_return_frame(prices, flows, {FACTOR: factors[FACTOR][:-1]}).dates == (date(2026, 1, 5),)


@pytest.mark.parametrize("bad", [0, -1])
def test_zero_or_negative_price_is_rejected(bad):
    prices = [obs(INSTRUMENT, date(2026, 1, 2), 100), obs(INSTRUMENT, date(2026, 1, 5), bad)]
    with pytest.raises(ValueError, match="positive"):
        build_return_frame(prices, [], {})


def test_regressions_share_dates_and_chronological_holdout():
    start = date(2026, 1, 1)
    points = []
    for i in range(30):
        x = (i % 7 - 3) / 100
        y = 0.001 + 2 * x + (i % 3 - 1) / 10000
        points.append(ReturnPoint(start + timedelta(days=i), y, y + (0.03 if i == 14 else 0), {FACTOR: x}))
    comparison = compare_regressions(ReturnFrame(INSTRUMENT, tuple(points)), (FACTOR,), start + timedelta(days=20))
    assert comparison.price.sample_dates == comparison.total.sample_dates
    assert comparison.price.train_count == 21
    assert comparison.price.holdout_count == 9
    assert comparison.price.coefficients[FACTOR] == pytest.approx(2.0, abs=0.01)
    assert comparison.price.holdout_rmse is not None
    assert comparison.total.coefficients["intercept"] != comparison.price.coefficients["intercept"]
    assert FACTOR in comparison.price.confidence_intervals


def test_regression_requires_enough_training_and_holdout():
    start = date(2026, 1, 1)
    points = tuple(ReturnPoint(start + timedelta(days=i), 0.01, 0.01, {FACTOR: i / 100}) for i in range(3))
    with pytest.raises(ValueError, match="insufficient"):
        compare_regressions(ReturnFrame(INSTRUMENT, points), (FACTOR,), start + timedelta(days=1))
