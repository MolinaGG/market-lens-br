"""Validate user-reviewed article references for local event studies."""

import csv
import hashlib
from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from io import StringIO
from urllib.parse import urlsplit


@dataclass(frozen=True)
class VerifiedArticle:
    filing_id: str
    ticker: str
    title: str
    published_at: datetime
    publication_time_known: bool
    source_url: str
    fetched_at: datetime

    @property
    def impact_eligible(self) -> bool:
        return True


def parse_verified_articles(csv_text: str, ticker: str) -> list[VerifiedArticle]:
    reader = csv.DictReader(StringIO(csv_text))
    if reader.fieldnames is None or set(reader.fieldnames) != {"published_at", "title", "source_url"}:
        raise ValueError("expected columns: published_at,title,source_url")
    articles: dict[str, VerifiedArticle] = {}
    imported_at = datetime.now(timezone.utc)
    for row in reader:
        if len(articles) >= 50:
            raise ValueError("at most 50 article references are supported")
        raw_date = (row.get("published_at") or "").strip()
        title = (row.get("title") or "").strip()
        url = (row.get("source_url") or "").strip()
        if not title or len(title) > 250:
            raise ValueError("each article needs a title of at most 250 characters")
        parsed_url = urlsplit(url)
        if parsed_url.scheme != "https" or not parsed_url.hostname or len(url) > 2000:
            raise ValueError("each article needs a valid HTTPS source URL")
        try:
            if len(raw_date) == 10:
                published = datetime.combine(date.fromisoformat(raw_date), time.min, timezone.utc)
                time_known = False
            else:
                published = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
                if published.tzinfo is None or published.utcoffset() is None:
                    raise ValueError
                time_known = True
        except ValueError as exc:
            raise ValueError("published_at must be YYYY-MM-DD or an ISO timestamp with timezone") from exc
        key = hashlib.sha256(f"{url}|{published.isoformat()}".encode()).hexdigest()[:16]
        articles[key] = VerifiedArticle(
            f"ARTICLE:{ticker}:{key}", ticker, title, published, time_known, url, imported_at,
        )
    if not articles:
        raise ValueError("the article file has no references")
    return sorted(articles.values(), key=lambda article: article.published_at, reverse=True)
