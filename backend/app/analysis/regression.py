"""Same-sample OLS for raw and coupon-adjusted returns, with holdout checks."""

from dataclasses import dataclass
from datetime import date
from math import sqrt

import numpy as np
import statsmodels.api as sm

from app.analysis.returns import ReturnFrame


@dataclass(frozen=True)
class RegressionFit:
    coefficients: dict[str, float]
    confidence_intervals: dict[str, tuple[float, float]]
    r_squared: float
    train_rmse: float
    holdout_rmse: float | None
    sample_dates: tuple[date, ...]
    train_count: int
    holdout_count: int


@dataclass(frozen=True)
class RegressionComparison:
    instrument_id: str
    factor_ids: tuple[str, ...]
    price: RegressionFit
    total: RegressionFit


def compare_regressions(frame: ReturnFrame, factor_ids: tuple[str, ...], train_end: date) -> RegressionComparison:
    if not factor_ids:
        raise ValueError("at least one factor is required")
    points = [point for point in frame.points if all(factor in point.factor_changes for factor in factor_ids)]
    dates = tuple(point.date for point in points)
    train_count = sum(day <= train_end for day in dates)
    holdout_count = len(dates) - train_count
    if train_count < len(factor_ids) + 3 or holdout_count < 2:
        raise ValueError("insufficient training or holdout observations")
    x = np.array([[1.0, *(point.factor_changes[factor] for factor in factor_ids)] for point in points], dtype=float)
    if not np.isfinite(x).all() or np.linalg.matrix_rank(x[:train_count]) < x.shape[1]:
        raise ValueError("insufficient independent factor variation")
    names = ("intercept", *factor_ids)

    def fit(target: str) -> RegressionFit:
        y = np.array([getattr(point, target) for point in points], dtype=float)
        if not np.isfinite(y).all():
            raise ValueError("returns must be finite")
        result = sm.OLS(y[:train_count], x[:train_count]).fit()
        predicted_train = result.predict(x[:train_count])
        predicted_holdout = result.predict(x[train_count:])
        intervals = result.conf_int(alpha=0.05)
        return RegressionFit(
            dict(zip(names, (float(value) for value in result.params))),
            dict(zip(names, ((float(low), float(high)) for low, high in intervals))),
            float(result.rsquared),
            sqrt(float(np.mean((y[:train_count] - predicted_train) ** 2))),
            sqrt(float(np.mean((y[train_count:] - predicted_holdout) ** 2))),
            dates,
            train_count,
            holdout_count,
        )

    return RegressionComparison(frame.instrument_id, factor_ids, fit("price_return"), fit("total_return"))
