"""Comparable price and gross coupon-adjusted interval returns."""

from dataclasses import dataclass
from datetime import date

from app.data.models import CashFlow, Observation, SplitEvent


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
    splits: list[SplitEvent] | None = None,
) -> ReturnFrame:
    if any(series_id.startswith("WB:CMO:") for series_id in factors):
        raise ValueError("monthly commodities cannot be aligned with daily returns")
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
    actions = sorted(
        [(split.date, 0, "split", float(split.factor)) for split in (splits or []) if split.instrument_id == instrument_id]
        + [(flow.date, 1, "cash", float(flow.amount)) for flow in cash_flows if flow.instrument_id == instrument_id],
        key=lambda item: (item[0], item[1]),
    )
    points = []
    action_index = 0
    for previous, current in zip(prices, prices[1:]):
        while action_index < len(actions) and actions[action_index][0] <= previous.date:
            action_index += 1
        shares = 1.0
        interval_flow = 0.0
        while action_index < len(actions) and actions[action_index][0] <= current.date:
            _, _, kind, value = actions[action_index]
            if kind == "split":
                shares *= value
            else:
                interval_flow += shares * value
            action_index += 1
        if any(previous.date not in series or current.date not in series for series in factor_maps.values()):
            continue
        changes = {
            series_id: _factor_change(series_id, series[previous.date], series[current.date])
            for series_id, series in factor_maps.items()
        }
        base = float(previous.value)
        adjusted_price = shares * float(current.value)
        points.append(ReturnPoint(current.date, adjusted_price / base - 1, (adjusted_price + interval_flow) / base - 1, changes))
    return ReturnFrame(instrument_id, tuple(points))
