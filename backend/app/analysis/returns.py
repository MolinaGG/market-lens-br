"""Comparable price and gross coupon-adjusted interval returns."""

from dataclasses import dataclass
from datetime import date

from app.data.models import CashFlow, Observation


@dataclass(frozen=True)
class ReturnPoint:
    date: date
    price_return: float
    total_return: float
    factor_changes: dict[str, float]


@dataclass(frozen=True)
class ReturnFrame:
    instrument_id: str
    points: tuple[ReturnPoint, ...]

    @property
    def dates(self) -> tuple[date, ...]:
        return tuple(point.date for point in self.points)


def _factor_change(series_id: str, previous: Observation, current: Observation) -> float:
    if series_id == "BCB:SGS:11":
        # Selic daily rate is already in percent; use a percentage-point change.
        return float(current.value - previous.value)
    if previous.value <= 0:
        raise ValueError("factor values used in percentage changes must be positive")
    return float(current.value / previous.value - 1)


def build_return_frame(
    prices: list[Observation],
    cash_flows: list[CashFlow],
    factors: dict[str, list[Observation]],
) -> ReturnFrame:
    if not prices:
        raise ValueError("price observations are required")
    prices = sorted(prices, key=lambda item: item.date)
    instrument_id = prices[0].series_id
    if any(item.series_id != instrument_id for item in prices):
        raise ValueError("prices must belong to one instrument")
    if any(item.value <= 0 for item in prices):
        raise ValueError("prices must be positive")
    if len({item.date for item in prices}) != len(prices):
        raise ValueError("duplicate price dates")
    factor_maps = {series_id: {item.date: item for item in observations} for series_id, observations in factors.items()}
    flows = sorted((flow for flow in cash_flows if flow.instrument_id == instrument_id), key=lambda flow: flow.date)
    points = []
    flow_index = 0
    for previous, current in zip(prices, prices[1:]):
        while flow_index < len(flows) and flows[flow_index].date <= previous.date:
            flow_index += 1
        interval_flow = 0.0
        while flow_index < len(flows) and flows[flow_index].date <= current.date:
            interval_flow += float(flows[flow_index].amount)
            flow_index += 1
        if any(previous.date not in series or current.date not in series for series in factor_maps.values()):
            continue
        changes = {
            series_id: _factor_change(series_id, series[previous.date], series[current.date])
            for series_id, series in factor_maps.items()
        }
        base = float(previous.value)
        points.append(ReturnPoint(current.date, float(current.value) / base - 1, (float(current.value) + interval_flow) / base - 1, changes))
    return ReturnFrame(instrument_id, tuple(points))
