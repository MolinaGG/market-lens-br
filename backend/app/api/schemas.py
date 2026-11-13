from datetime import date, datetime

from pydantic import BaseModel


class SeriesSchema(BaseModel):
    series_id: str
    name: str
    unit: str
    source_url: str
    observation_count: int
    start_date: date
    end_date: date
    cash_flow_count: int = 0


class CatalogSchema(BaseModel):
    version: str
    fetched_at: datetime
    instruments: list[SeriesSchema]
    factors: list[SeriesSchema]
    default_instrument_id: str
    benchmark_id: str


class ObservationSchema(BaseModel):
    date: date
    value: float
    source_url: str


class CashFlowSchema(BaseModel):
    date: date
    amount: float
    source_url: str


class SeriesResponseSchema(BaseModel):
    version: str
    series: SeriesSchema
    observations: list[ObservationSchema]
    cash_flows: list[CashFlowSchema]


class ReturnPointSchema(BaseModel):
    date: date
    price_return: float
    total_return: float
    factor_changes: dict[str, float]


class RegressionFitSchema(BaseModel):
    coefficients: dict[str, float]
    confidence_intervals: dict[str, tuple[float, float]]
    r_squared: float
    train_rmse: float
    holdout_rmse: float
    sample_dates: list[date]
    train_count: int
    holdout_count: int


class RegressionResponseSchema(BaseModel):
    version: str
    instrument_id: str
    factor_ids: list[str]
    train_end: date
    price: RegressionFitSchema
    total: RegressionFitSchema
    points: list[ReturnPointSchema]
    adjustment_convention: str
    source_urls: list[str]


class EventWindowSchema(BaseModel):
    horizon: int
    session_dates: list[date]
    observed_return: float | None
    benchmark_return: float | None
    abnormal_return: float | None
    reason: str | None
    available: bool


class EventSchema(BaseModel):
    event_id: str
    title: str
    source_url: str
    published_at: datetime
    publication_time_known: bool
    observed_at: datetime
    effective_session: date | None
    windows: dict[int, EventWindowSchema]


class CohortSchema(BaseModel):
    horizon: int
    sample_count: int
    excluded_overlap: int
    mean_abnormal_return: float | None
    confidence_interval: tuple[float, float] | None


class EventsResponseSchema(BaseModel):
    version: str
    topic: str
    instrument_id: str
    benchmark_id: str
    events: list[EventSchema]
    cohort: dict[int, CohortSchema]
    method_note: str
