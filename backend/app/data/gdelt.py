"""GDELT DOC article metadata; seen time is never promoted to publication time."""

import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlsplit, urlunsplit


GDELT_ABOUT_URL = "https://gdeltproject.org/about.html"
GDELT_API_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
HEADLINE_COMPANY = {"PETR4": "petrobras", "VALE3": "vale", "ITUB4": "itau", "BBDC4": "bradesco", "WEGE3": "weg", "ABEV3": "ambev"}


@dataclass(frozen=True)
class NewsItem:
    ticker: str
    title: str
    source_url: str
    domain: str
    language: str
    seen_at: datetime
    published_at: datetime | None
    publication_time_known: bool
    fetched_at: datetime
    metadata_source_url: str = GDELT_ABOUT_URL
    source_rights: str = "GDELT attribution"


def _canonical_url(url: str) -> str | None:
    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        return None
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/") or "/", parts.query, ""))


def relevant_headline(title: str, ticker: str) -> bool:
    company = HEADLINE_COMPANY.get(ticker)
    if not company:
        return False
    plain = "".join(char for char in unicodedata.normalize("NFKD", title.casefold()) if not unicodedata.combining(char))
    return bool(re.search(rf"\b{re.escape(company)}\b", plain))


def parse_gdelt_metadata(payload: bytes, ticker: str, fetched_at: datetime) -> list[NewsItem]:
    data = json.loads(payload)
    articles = data.get("articles", [])
    if not isinstance(articles, list):
        raise ValueError("GDELT articles must be a list")
    selected: dict[str, NewsItem] = {}
    for row in articles:
        url = _canonical_url(row.get("url", ""))
        if not url or not row.get("seendate") or not relevant_headline(row.get("title", ""), ticker):
            continue
        seen = datetime.strptime(row["seendate"], "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
        item = NewsItem(ticker, row.get("title", "").strip(), url, row.get("domain", urlsplit(url).netloc), row.get("language", ""), seen, None, False, fetched_at)
        prior = selected.get(url)
        if prior is None or seen < prior.seen_at:
            selected[url] = item
    return sorted(selected.values(), key=lambda item: item.seen_at, reverse=True)
