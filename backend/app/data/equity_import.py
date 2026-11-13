"""Validated, local-only equity price and corporate-action import."""

import csv
import re
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from io import StringIO
from pathlib import Path
from typing import TextIO

from app.data.models import CashFlow, Observation, SplitEvent


LOCAL_DB = Path("data/local_equity.db")
TICKER = re.compile(r"^[A-Z]{4}[0-9]{1,2}$")
LOCAL_SCHEMA = """
CREATE TABLE IF NOT EXISTS equities (ticker TEXT PRIMARY KEY, rights TEXT NOT NULL, imported_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS prices (ticker TEXT NOT NULL, date TEXT NOT NULL, close TEXT NOT NULL, PRIMARY KEY (ticker, date));
CREATE TABLE IF NOT EXISTS actions (ticker TEXT NOT NULL, ex_date TEXT NOT NULL, kind TEXT NOT NULL, amount TEXT, split_factor TEXT);
CREATE INDEX IF NOT EXISTS actions_ticker_date ON actions(ticker, ex_date);
"""


@dataclass(frozen=True)
class ImportSummary:
    ticker: str
    rights: str
    price_count: int
    action_count: int
    start_date: date
    end_date: date


@dataclass(frozen=True)
class ImportedEquity:
    ticker: str
    rights: str
    prices: list[Observation]
    cash_flows: list[CashFlow]
    splits: list[SplitEvent]


def _csv_rows(file: Path | TextIO) -> list[dict[str, str]]:
    content = file.read_text(encoding="utf-8-sig") if isinstance(file, Path) else file.read()
    if isinstance(content, bytes):
        content = content.decode("utf-8-sig")
    if not content.strip():
        raise ValueError("empty CSV")
    delimiter = ";" if ";" in content.splitlines()[0] else ","
    return list(csv.DictReader(StringIO(content), delimiter=delimiter))


def _number(value: str | None, name: str) -> Decimal:
    if value is None or not value.strip():
        raise ValueError(f"missing {name}")
    try:
        parsed = Decimal(value.strip().replace(",", "."))
    except InvalidOperation as exc:
        raise ValueError(f"invalid {name}") from exc
    if not parsed.is_finite():
        raise ValueError(f"invalid {name}")
    return parsed


def import_equity_csv(
    price_file: Path | TextIO,
    action_file: Path | TextIO,
    rights: str = "local_only",
    database_path: Path = LOCAL_DB,
) -> ImportSummary:
    if rights != "local_only":
        raise ValueError("equity imports are local_only")
    price_rows = _csv_rows(price_file)
    action_rows = _csv_rows(action_file)
    if len(price_rows) < 2:
        raise ValueError("at least two prices are required")
    ticker = (price_rows[0].get("ticker") or "").strip().upper()
    if not TICKER.fullmatch(ticker):
        raise ValueError("invalid ticker")
    prices = []
    seen: set[date] = set()
    for row in price_rows:
        if (row.get("ticker") or "").strip().upper() != ticker:
            raise ValueError("mixed ticker in prices")
        try:
            day = date.fromisoformat(row["date"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("invalid price date") from exc
        if day in seen:
            raise ValueError("duplicate price date")
        seen.add(day)
        close = _number(row.get("close"), "close")
        if close <= 0:
            raise ValueError("prices must be positive")
        prices.append((ticker, day.isoformat(), str(close)))
    actions = []
    for row in action_rows:
        if (row.get("ticker") or "").strip().upper() != ticker:
            raise ValueError("action ticker differs from prices")
        try:
            day = date.fromisoformat(row["ex_date"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("invalid ex_date") from exc
        kind = (row.get("kind") or "").strip().lower()
        if kind not in {"split", "dividend", "jcp"}:
            raise ValueError("invalid action kind")
        if kind == "split":
            factor = _number(row.get("split_factor"), "split_factor")
            if factor <= 0:
                raise ValueError("split_factor must be positive")
            actions.append((ticker, day.isoformat(), kind, None, str(factor)))
        else:
            amount = _number(row.get("amount"), "amount")
            if amount <= 0:
                raise ValueError("amount must be positive")
            actions.append((ticker, day.isoformat(), kind, str(amount), None))
    days = sorted(seen)
    if any(date.fromisoformat(action[1]) <= days[0] or date.fromisoformat(action[1]) > days[-1] for action in actions):
        raise ValueError("action ex_date must fall after first and by last price")
    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.executescript(LOCAL_SCHEMA)
        connection.execute("DELETE FROM prices WHERE ticker = ?", (ticker,))
        connection.execute("DELETE FROM actions WHERE ticker = ?", (ticker,))
        connection.execute("INSERT OR REPLACE INTO equities VALUES (?, ?, ?)", (ticker, rights, datetime.now(timezone.utc).isoformat()))
        connection.executemany("INSERT INTO prices VALUES (?, ?, ?)", prices)
        connection.executemany("INSERT INTO actions VALUES (?, ?, ?, ?, ?)", actions)
    return ImportSummary(ticker, rights, len(prices), len(actions), days[0], days[-1])


def read_imported_equity(database_path: Path, ticker: str) -> ImportedEquity:
    path = Path(database_path)
    if not path.is_file():
        raise KeyError(ticker)
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.row_factory = sqlite3.Row
        metadata = connection.execute("SELECT * FROM equities WHERE ticker = ?", (ticker,)).fetchone()
        if metadata is None:
            raise KeyError(ticker)
        price_rows = connection.execute("SELECT * FROM prices WHERE ticker = ? ORDER BY date", (ticker,)).fetchall()
        action_rows = connection.execute("SELECT * FROM actions WHERE ticker = ? ORDER BY ex_date, kind", (ticker,)).fetchall()
    imported_at = datetime.fromisoformat(metadata["imported_at"])
    instrument = f"EQUITY:{ticker}"
    source = f"local://import/{ticker}"
    prices = [Observation(instrument, date.fromisoformat(row["date"]), Decimal(row["close"]), source, imported_at, "local-1") for row in price_rows]
    flows = [CashFlow(instrument, date.fromisoformat(row["ex_date"]), Decimal(row["amount"]), source, imported_at, "local-1") for row in action_rows if row["kind"] in {"dividend", "jcp"}]
    splits = [SplitEvent(instrument, date.fromisoformat(row["ex_date"]), Decimal(row["split_factor"]), source, imported_at, "local-1") for row in action_rows if row["kind"] == "split"]
    return ImportedEquity(ticker, metadata["rights"], prices, flows, splits)
