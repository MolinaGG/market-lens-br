"""Independent, versioned CVM and GDELT metadata snapshot."""

import argparse
import hashlib
import json
import os
import sqlite3
import tempfile
import time
from contextlib import closing
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path

import httpx

from app.data.cvm import CVM_ZIP_URL, CompanyFiling, normalize_subject, parse_cvm_ipe
from app.data.gdelt import GDELT_API_URL, NewsItem, parse_gdelt_metadata, relevant_headline


NEWS_SCHEMA = """
CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE filings (filing_id TEXT PRIMARY KEY, ticker TEXT NOT NULL, published_at TEXT NOT NULL, payload TEXT NOT NULL);
CREATE INDEX filings_ticker_date ON filings(ticker, published_at);
CREATE TABLE articles (ticker TEXT NOT NULL, source_url TEXT NOT NULL, seen_at TEXT NOT NULL, payload TEXT NOT NULL, PRIMARY KEY (ticker, source_url));
CREATE INDEX articles_ticker_date ON articles(ticker, seen_at);
"""
GDELT_QUERIES = {"PETR4": "Petrobras", "VALE3": "Vale S.A.", "ITUB4": "Itaú Unibanco", "BBDC4": "Bradesco", "WEGE3": "WEG", "ABEV3": "Ambev"}


@dataclass(frozen=True)
class NewsRefreshSummary:
    version: str
    filing_count: int
    article_count: int
    database_path: str


def fetch_news_sources() -> tuple[list[bytes], dict[str, bytes]]:
    year = datetime.now(timezone.utc).year
    with httpx.Client(timeout=httpx.Timeout(60, connect=20), follow_redirects=True, headers={"User-Agent": "market-lens-br/0.1 (open research)"}) as client:
        cvm_archives = []
        for item in (year - 1, year):
            response = client.get(CVM_ZIP_URL.format(year=item))
            response.raise_for_status()
            cvm_archives.append(response.content)

    gdelt_payloads = {}
    # GDELT asks clients to space requests at least five seconds apart.
    with httpx.Client(timeout=httpx.Timeout(40, connect=15), follow_redirects=True) as client:
        for index, (ticker, name) in enumerate(GDELT_QUERIES.items()):
            if index:
                time.sleep(6)
            for attempt in range(2):
                try:
                    response = client.get(GDELT_API_URL, params={"query": f'"{name}"', "mode": "artlist", "format": "json", "maxrecords": 15, "timespan": "1week", "sort": "datedesc"})
                    if response.status_code == 429 and attempt == 0:
                        time.sleep(15)
                        continue
                    response.raise_for_status()
                    json.loads(response.content)
                    gdelt_payloads[ticker] = response.content
                    break
                except (httpx.HTTPError, ValueError):
                    # CVM filings remain available if optional article discovery fails.
                    break
    return cvm_archives, gdelt_payloads


def _json_default(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    raise TypeError(type(value).__name__)


def refresh_news_snapshot(database_path: Path, fetched_at: datetime | None = None) -> NewsRefreshSummary:
    fetched_at = fetched_at or datetime.now(timezone.utc)
    archives, gdelt_payloads = fetch_news_sources()
    path = Path(database_path)
    filings: dict[tuple[str, str, date, str], CompanyFiling] = {}
    for archive in archives:
        for filing in parse_cvm_ipe(archive, fetched_at):
            key = (filing.company_code, filing.category, filing.reference_date, normalize_subject(filing.title))
            prior = filings.get(key)
            if prior is None or (filing.version, filing.published_at) > (prior.version, prior.published_at):
                filings[key] = filing
    articles = [item for ticker, payload in gdelt_payloads.items() for item in parse_gdelt_metadata(payload, ticker, fetched_at)]
    # Retain recently collected metadata when the optional GDELT endpoint is rate limited.
    if path.is_file():
        with NewsStore(path) as previous:
            for ticker in GDELT_QUERIES:
                if ticker not in gdelt_payloads:
                    articles.extend(item for item in previous.articles(ticker) if (fetched_at - item.fetched_at).days <= 14 and relevant_headline(item.title, ticker))
    if not filings:
        raise ValueError("CVM returned no filings for the tracked companies")
    digest = hashlib.sha256()
    for raw in (*archives, *(gdelt_payloads[ticker] for ticker in sorted(gdelt_payloads))):
        digest.update(raw)
    for item in sorted(articles, key=lambda article: (article.ticker, article.source_url)):
        digest.update(json.dumps(asdict(item), default=_json_default, sort_keys=True).encode())
    version = f"{fetched_at:%Y%m%dT%H%M%SZ}-{digest.hexdigest()[:12]}"
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    os.close(fd)
    try:
        with closing(sqlite3.connect(temporary)) as connection, connection:
            connection.executescript(NEWS_SCHEMA)
            connection.executemany("INSERT INTO metadata VALUES (?, ?)", [("version", version), ("fetched_at", fetched_at.isoformat()), ("gdelt_tickers", ",".join(sorted({item.ticker for item in articles}))), ("gdelt_refresh_tickers", ",".join(sorted(gdelt_payloads)))])
            connection.executemany("INSERT INTO filings VALUES (?, ?, ?, ?)", ((item.filing_id, item.ticker, item.published_at.isoformat(), json.dumps(asdict(item), default=_json_default, ensure_ascii=False)) for item in filings.values()))
            connection.executemany("INSERT INTO articles VALUES (?, ?, ?, ?)", ((item.ticker, item.source_url, item.seen_at.isoformat(), json.dumps(asdict(item), default=_json_default, ensure_ascii=False)) for item in articles))
            if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValueError("Company news snapshot failed integrity validation")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return NewsRefreshSummary(version, len(filings), len(articles), str(path))


def _filing_from_json(value: str) -> CompanyFiling:
    data = json.loads(value)
    data["published_at"] = datetime.fromisoformat(data["published_at"])
    data["reference_date"] = date.fromisoformat(data["reference_date"])
    data["fetched_at"] = datetime.fromisoformat(data["fetched_at"])
    return CompanyFiling(**data)


def _article_from_json(value: str) -> NewsItem:
    data = json.loads(value)
    data["seen_at"] = datetime.fromisoformat(data["seen_at"])
    data["published_at"] = datetime.fromisoformat(data["published_at"]) if data["published_at"] else None
    data["fetched_at"] = datetime.fromisoformat(data["fetched_at"])
    return NewsItem(**data)


class NewsStore:
    def __init__(self, path: Path):
        self.connection = sqlite3.connect(path)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.connection.close()

    def version(self) -> str:
        return self.connection.execute("SELECT value FROM metadata WHERE key = 'version'").fetchone()[0]

    def fetched_at(self) -> datetime:
        return datetime.fromisoformat(self.connection.execute("SELECT value FROM metadata WHERE key = 'fetched_at'").fetchone()[0])

    def filings(self, ticker: str, limit: int = 100) -> list[CompanyFiling]:
        rows = self.connection.execute("SELECT payload FROM filings WHERE ticker = ? ORDER BY published_at DESC LIMIT ?", (ticker, limit))
        return [_filing_from_json(value) for (value,) in rows]

    def articles(self, ticker: str, limit: int = 30) -> list[NewsItem]:
        rows = self.connection.execute("SELECT payload FROM articles WHERE ticker = ? ORDER BY seen_at DESC LIMIT ?", (ticker, limit))
        return [_article_from_json(value) for (value,) in rows]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build a frozen company filings and news metadata snapshot")
    parser.add_argument("--database", type=Path, default=Path("data/company_news.db"))
    args = parser.parse_args()
    print(refresh_news_snapshot(args.database))
