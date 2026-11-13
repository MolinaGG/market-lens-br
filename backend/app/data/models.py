from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal


NORMALIZATION_VERSION = "1"


@dataclass(frozen=True)
class Observation:
    series_id: str
    date: date
    value: Decimal
    source_url: str
    fetched_at: datetime
    normalization_version: str = NORMALIZATION_VERSION


@dataclass(frozen=True)
class CashFlow:
    instrument_id: str
    date: date
    amount: Decimal
    source_url: str
    fetched_at: datetime
    normalization_version: str = NORMALIZATION_VERSION


@dataclass(frozen=True)
class SplitEvent:
    instrument_id: str
    date: date
    factor: Decimal
    source_url: str
    fetched_at: datetime
    normalization_version: str = NORMALIZATION_VERSION


@dataclass(frozen=True)
class MarketEvent:
    event_id: str
    topic: str
    title: str
    published_at: datetime
    publication_time_known: bool
    source_url: str
    observed_at: datetime
    normalization_version: str = NORMALIZATION_VERSION


@dataclass(frozen=True)
class SeriesInfo:
    series_id: str
    name: str
    unit: str
    source_url: str
    observation_count: int
    start_date: date
    end_date: date
    frequency: str = "daily"
    source_rights: str = "open"


@dataclass(frozen=True)
class RefreshSummary:
    version: str
    observation_count: int
    cash_flow_count: int
    event_count: int
    database_path: str
