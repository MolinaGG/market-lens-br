import json
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from app.data.bcb import parse_sgs
from app.data.copom import parse_comunicados
from app.data.refresh import refresh_snapshot
from app.data.models import Observation
from app.data.store import SnapshotStore
from app.data.tesouro import parse_coupons, parse_prices


FIXTURES = Path(__file__).parent / "fixtures"
FETCHED = datetime(2026, 11, 13, 12, tzinfo=timezone.utc)


def test_tesouro_parsers_preserve_title_maturity_and_unit_coupon():
    prices = parse_prices((FIXTURES / "tesouro_prices.csv").read_bytes(), FETCHED)
    coupons = parse_coupons((FIXTURES / "tesouro_coupons.csv").read_bytes(), FETCHED)
    assert len(prices) == 2
    assert prices[0].series_id == "TESOURO:Tesouro Prefixado com Juros Semestrais:2033-01-01"
    assert prices[0].date == date(2026, 1, 2)
    assert prices[0].value == Decimal("747.23")
    assert coupons[0].instrument_id == prices[0].series_id
    assert coupons[0].date == date(2026, 1, 2)
    assert coupons[0].amount == Decimal("48.123456")
    assert "tesourotransparente.gov.br" in coupons[0].source_url
    assert coupons[0].fetched_at == FETCHED
    assert coupons[0].normalization_version


def test_bcb_and_copom_parsers_keep_provenance_and_unknown_time():
    sgs = parse_sgs(json.dumps([{"data": "03/11/2026", "valor": "0.050788"}]).encode(), 11, FETCHED)
    assert sgs[0].series_id == "BCB:SGS:11"
    assert sgs[0].date == date(2026, 11, 3)
    assert sgs[0].value == Decimal("0.050788")
    assert "api.bcb.gov.br" in sgs[0].source_url
    payload = {"conteudo": [{"nro_reuniao": 282, "dataReferencia": "2026-11-04", "titulo": "Copom mantém a Selic"}]}
    events = parse_comunicados(json.dumps(payload).encode(), FETCHED)
    assert events[0].event_id == "COPOM:282"
    assert events[0].published_at.date() == date(2026, 11, 4)
    assert events[0].publication_time_known is False
    assert events[0].source_url.startswith("https://www.bcb.gov.br/")


def test_refresh_is_atomic_and_store_reads_typed_records(tmp_path, monkeypatch):
    from app.data import refresh

    price = (FIXTURES / "tesouro_prices.csv").read_bytes()
    coupon = (FIXTURES / "tesouro_coupons.csv").read_bytes()
    sgs = json.dumps([{"data": "02/01/2026", "valor": "0.050788"}]).encode()
    copom = json.dumps({"conteudo": [{"nro_reuniao": 282, "dataReferencia": "2026-01-02", "titulo": "Copom"}]}).encode()
    monkeypatch.setattr(refresh, "fetch_sources", lambda: (price, coupon, {11: sgs}, copom))
    monkeypatch.setattr(refresh, "fetch_commodity_sources", lambda: (b"brent", b"monthly"))
    monkeypatch.setattr(refresh, "parse_eia_brent", lambda raw, fetched: [Observation("EIA:BRENT", date(2026, 1, 2), Decimal("70"), "https://www.eia.gov/", fetched)])
    monkeypatch.setattr(refresh, "parse_world_bank_monthly", lambda raw, fetched: [Observation("WB:CMO:GOLD", date(2026, 1, 1), Decimal("2500"), "https://www.worldbank.org/", fetched)])
    db = tmp_path / "snapshot.sqlite"
    summary = refresh_snapshot(db, FETCHED)
    assert summary.observation_count == 5
    with SnapshotStore(db) as store:
        series = store.list_series()
        assert len(series) == 4
        instrument = next(s.series_id for s in series if s.series_id.startswith("TESOURO:"))
        assert len(store.observations(instrument)) == 2
        assert store.cash_flows(instrument)[0].amount == Decimal("48.123456")
        assert store.events("copom")[0].event_id == "COPOM:282"
        assert store.snapshot_version() == summary.version
    before = db.read_bytes()
    monkeypatch.setattr(refresh, "fetch_sources", lambda: (_ for _ in ()).throw(RuntimeError("source down")))
    with pytest.raises(RuntimeError, match="source down"):
        refresh_snapshot(db, FETCHED)
    assert db.read_bytes() == before
