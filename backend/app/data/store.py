"""Read-only access to a complete, versioned SQLite snapshot."""

import sqlite3
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from app.data.models import CashFlow, MarketEvent, Observation, SeriesInfo


SCHEMA = """
CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE observations (
  series_id TEXT NOT NULL, date TEXT NOT NULL, value TEXT NOT NULL,
  source_url TEXT NOT NULL, fetched_at TEXT NOT NULL, normalization_version TEXT NOT NULL,
  PRIMARY KEY (series_id, date)
);
CREATE TABLE cash_flows (
  instrument_id TEXT NOT NULL, date TEXT NOT NULL, amount TEXT NOT NULL,
  source_url TEXT NOT NULL, fetched_at TEXT NOT NULL, normalization_version TEXT NOT NULL,
  PRIMARY KEY (instrument_id, date)
);
CREATE TABLE events (
  event_id TEXT PRIMARY KEY, topic TEXT NOT NULL, title TEXT NOT NULL,
  published_at TEXT NOT NULL, publication_time_known INTEGER NOT NULL,
  source_url TEXT NOT NULL, observed_at TEXT NOT NULL, normalization_version TEXT NOT NULL
);
CREATE INDEX events_topic_date ON events(topic, published_at);
"""


class SnapshotStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def close(self):
        self.connection.close()

    def snapshot_version(self) -> str:
        row = self.connection.execute("SELECT value FROM metadata WHERE key = 'version'").fetchone()
        return row[0]

    def fetched_at(self) -> datetime:
        row = self.connection.execute("SELECT value FROM metadata WHERE key = 'fetched_at'").fetchone()
        return datetime.fromisoformat(row[0])

    def list_series(self) -> list[SeriesInfo]:
        rows = self.connection.execute(
            """SELECT series_id, MIN(source_url) source_url, COUNT(*) n,
                      MIN(date) first_date, MAX(date) last_date
               FROM observations GROUP BY series_id ORDER BY series_id"""
        )
        result = []
        for row in rows:
            sid = row["series_id"]
            if sid.startswith("TESOURO:"):
                parts = sid.split(":")
                name, unit = f"{parts[1]} · {parts[2]}", "BRL por título"
            else:
                from app.data.bcb import SGS_NAMES

                name, unit = SGS_NAMES[int(sid.rsplit(":", 1)[1])]
            result.append(SeriesInfo(sid, name, unit, row["source_url"], row["n"], date.fromisoformat(row["first_date"]), date.fromisoformat(row["last_date"])))
        return result

    def observations(self, series_id: str, start: date | None = None, end: date | None = None) -> list[Observation]:
        query = "SELECT * FROM observations WHERE series_id = ?"
        params: list[str] = [series_id]
        if start:
            query += " AND date >= ?"
            params.append(start.isoformat())
        if end:
            query += " AND date <= ?"
            params.append(end.isoformat())
        rows = self.connection.execute(query + " ORDER BY date", params)
        return [Observation(r["series_id"], date.fromisoformat(r["date"]), Decimal(r["value"]), r["source_url"], datetime.fromisoformat(r["fetched_at"]), r["normalization_version"]) for r in rows]

    def cash_flows(self, instrument_id: str) -> list[CashFlow]:
        rows = self.connection.execute("SELECT * FROM cash_flows WHERE instrument_id = ? ORDER BY date", (instrument_id,))
        return [CashFlow(r["instrument_id"], date.fromisoformat(r["date"]), Decimal(r["amount"]), r["source_url"], datetime.fromisoformat(r["fetched_at"]), r["normalization_version"]) for r in rows]

    def events(self, topic: str) -> list[MarketEvent]:
        rows = self.connection.execute("SELECT * FROM events WHERE topic = ? ORDER BY published_at DESC", (topic,))
        return [MarketEvent(r["event_id"], r["topic"], r["title"], datetime.fromisoformat(r["published_at"]), bool(r["publication_time_known"]), r["source_url"], datetime.fromisoformat(r["observed_at"]), r["normalization_version"]) for r in rows]
