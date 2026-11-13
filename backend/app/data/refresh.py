"""Fetch official sources, validate, then atomically replace the public snapshot."""

import argparse
import hashlib
import os
import sqlite3
import tempfile
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

from app.data.bcb import parse_sgs, sgs_url
from app.data.copom import COMUNICADOS_URL, parse_comunicados
from app.data.models import RefreshSummary
from app.data.store import SCHEMA
from app.data.tesouro import COUPONS_URL, PRICES_URL, parse_coupons, parse_prices


def fetch_sources() -> tuple[bytes, bytes, dict[int, bytes], bytes]:
    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=365 * 5 + 2)
    with httpx.Client(timeout=httpx.Timeout(90, connect=20), follow_redirects=True, headers={"User-Agent": "market-lens-br/0.1 (open research)"}) as client:
        def get(url: str) -> bytes:
            response = client.get(url)
            response.raise_for_status()
            return response.content

        prices = get(PRICES_URL)
        coupons = get(COUPONS_URL)
        bcb = {}
        for number in (1, 11):
            url = f"{sgs_url(number)}&dataInicial={start:%d/%m/%Y}&dataFinal={today:%d/%m/%Y}"
            bcb[number] = get(url)
        comunicados = get(COMUNICADOS_URL)
    return prices, coupons, bcb, comunicados


def refresh_snapshot(database_path: Path, fetched_at: datetime | None = None) -> RefreshSummary:
    fetched_at = fetched_at or datetime.now(timezone.utc)
    if fetched_at.tzinfo is None:
        raise ValueError("fetched_at must include a timezone")
    prices_data, coupon_data, bcb_data, copom_data = fetch_sources()
    cutoff = fetched_at.date() - timedelta(days=365 * 5 + 2)
    prices = [x for x in parse_prices(prices_data, fetched_at) if x.date >= cutoff]
    coupons = [x for x in parse_coupons(coupon_data, fetched_at) if x.date >= cutoff]
    observations = prices + [x for number, raw in bcb_data.items() for x in parse_sgs(raw, number, fetched_at)]
    events = parse_comunicados(copom_data, fetched_at)
    if not prices or not coupons or not events or not any(x.series_id.startswith("BCB:") for x in observations):
        raise ValueError("Official sources returned an incomplete research snapshot")
    digest = hashlib.sha256()
    for raw in (prices_data, coupon_data, *(bcb_data[n] for n in sorted(bcb_data)), copom_data):
        digest.update(raw)
    version = f"{fetched_at:%Y%m%dT%H%M%SZ}-{digest.hexdigest()[:12]}"
    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    os.close(fd)
    try:
        with closing(sqlite3.connect(temporary)) as connection, connection:
            connection.executescript(SCHEMA)
            connection.executemany("INSERT INTO metadata VALUES (?, ?)", [("version", version), ("fetched_at", fetched_at.isoformat())])
            connection.executemany(
                "INSERT INTO observations VALUES (?, ?, ?, ?, ?, ?)",
                ((x.series_id, x.date.isoformat(), str(x.value), x.source_url, x.fetched_at.isoformat(), x.normalization_version) for x in observations),
            )
            connection.executemany(
                "INSERT INTO cash_flows VALUES (?, ?, ?, ?, ?, ?)",
                ((x.instrument_id, x.date.isoformat(), str(x.amount), x.source_url, x.fetched_at.isoformat(), x.normalization_version) for x in coupons),
            )
            connection.executemany(
                "INSERT INTO events VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                ((x.event_id, x.topic, x.title, x.published_at.isoformat(), int(x.publication_time_known), x.source_url, x.observed_at.isoformat(), x.normalization_version) for x in events),
            )
            check = connection.execute("PRAGMA integrity_check").fetchone()[0]
            if check != "ok":
                raise ValueError(f"Snapshot integrity check failed: {check}")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return RefreshSummary(version, len(observations), len(coupons), len(events), str(path))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build a versioned open-data research snapshot")
    parser.add_argument("--database", type=Path, default=Path("data/market_lens.db"))
    args = parser.parse_args()
    print(refresh_snapshot(args.database))
