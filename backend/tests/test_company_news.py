import csv
import io
import json
import zipfile
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone

from fastapi.testclient import TestClient
import pytest

from app.data.cvm import parse_cvm_ipe
from app.data.gdelt import parse_gdelt_metadata
from app.data.news_store import NewsStore, refresh_news_snapshot
from app.analysis.company_impact import study_filing_impact
from app.analysis.returns import ReturnFrame, ReturnPoint
from app.main import create_app


FETCHED = datetime(2026, 11, 13, 18, tzinfo=timezone.utc)
FIELDS = ["CNPJ_Companhia", "Nome_Companhia", "Codigo_CVM", "Data_Referencia", "Categoria", "Tipo", "Especie", "Assunto", "Data_Entrega", "Tipo_Apresentacao", "Protocolo_Entrega", "Versao", "Link_Download"]


def cvm_zip(date_map=None, extra_rows=None):
    rows = [
        {"Codigo_CVM": "9512", "Data_Referencia": "2026-11-01", "Categoria": "Fato Relevante", "Assunto": "Nova descoberta", "Data_Entrega": "2026-11-02", "Tipo_Apresentacao": "AP - Apresentação", "Protocolo_Entrega": "P1", "Versao": "1", "Link_Download": "https://www.rad.cvm.gov.br/doc/1"},
        {"Codigo_CVM": "9512", "Data_Referencia": "2026-11-01", "Categoria": "Fato Relevante", "Assunto": "Nova descoberta", "Data_Entrega": "2026-11-03", "Tipo_Apresentacao": "RE - Reapresentação", "Protocolo_Entrega": "P2", "Versao": "2", "Link_Download": "https://www.rad.cvm.gov.br/doc/2"},
        {"Codigo_CVM": "9512", "Data_Referencia": "2026-11-04", "Categoria": "Comunicado ao Mercado", "Assunto": "Cancelamento de operação", "Data_Entrega": "2026-11-05", "Tipo_Apresentacao": "AP - Apresentação", "Protocolo_Entrega": "P3", "Versao": "1", "Link_Download": "https://www.rad.cvm.gov.br/doc/3"},
        {"Codigo_CVM": "999999", "Data_Referencia": "2026-11-01", "Categoria": "Fato Relevante", "Assunto": "Outro", "Data_Entrega": "2026-11-02", "Tipo_Apresentacao": "AP", "Protocolo_Entrega": "P4", "Versao": "1", "Link_Download": "https://www.rad.cvm.gov.br/doc/4"},
    ]
    rows.extend(extra_rows or [])
    content = io.StringIO()
    writer = csv.DictWriter(content, fieldnames=FIELDS, delimiter=";")
    writer.writeheader()
    writer.writerows(rows)
    output = io.BytesIO()
    source = content.getvalue()
    for old, new in (date_map or {}).items():
        source = source.replace(old, new)
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("ipe_cia_aberta_2026.csv", source.encode("cp1252"))
    return output.getvalue()


def gdelt_json():
    return json.dumps({"articles": [
        {"url": "https://news.example/petrobras?a=1", "title": "Petrobras amplia produção", "seendate": "20261103T204500Z", "domain": "news.example", "language": "Portuguese"},
        {"url": "https://news.example/petrobras?a=1", "title": "Petrobras amplia produção", "seendate": "20261103T210000Z", "domain": "news.example", "language": "Portuguese"},
    ]}).encode()


def test_cvm_refiling_and_cancellation_do_not_create_duplicate_study_events():
    filings = parse_cvm_ipe(cvm_zip(), FETCHED)
    assert len(filings) == 2
    revised = next(item for item in filings if item.status == "refiled")
    assert revised.ticker == "PETR4" and revised.company_code == "9512"
    assert revised.protocol == "P2" and revised.version == 2
    assert revised.published_at.date() == date(2026, 11, 3)
    assert revised.publication_time_known is False
    assert revised.source_url.endswith("/2")
    assert next(item for item in filings if item.status == "cancelled").impact_eligible is False


def test_cvm_protocol_collision_keeps_distinct_source_documents():
    extra = {"Codigo_CVM": "9512", "Data_Referencia": "2026-11-01", "Categoria": "Fato Relevante", "Assunto": "Outro fato", "Data_Entrega": "2026-11-03", "Tipo_Apresentacao": "AP", "Protocolo_Entrega": "P2", "Versao": "1", "Link_Download": "https://www.rad.cvm.gov.br/doc/another"}
    filings = parse_cvm_ipe(cvm_zip(extra_rows=[extra]), FETCHED)
    assert len({item.filing_id for item in filings}) == len(filings)


def test_gdelt_seen_time_is_not_claimed_as_publication_time_and_urls_dedupe():
    items = parse_gdelt_metadata(gdelt_json(), "PETR4", FETCHED)
    assert len(items) == 1
    assert items[0].seen_at == datetime(2026, 11, 3, 20, 45, tzinfo=timezone.utc)
    assert items[0].published_at is None
    assert items[0].publication_time_known is False
    assert items[0].source_url == "https://news.example/petrobras?a=1"
    assert items[0].source_rights == "GDELT attribution"


def test_gdelt_discards_generic_articles_without_company_in_headline():
    payload = json.dumps({"articles": [
        {"url": "https://example.org/banco-do-brasil", "title": "Banco do Brasil revisa dividendos", "seendate": "20261103T204500Z"},
        {"url": "https://example.org/bradesco", "title": "Bradesco divulga resultado", "seendate": "20261103T204500Z"},
    ]}).encode()
    items = parse_gdelt_metadata(payload, "BBDC4", FETCHED)
    assert [item.title for item in items] == ["Bradesco divulga resultado"]


def test_news_snapshot_is_atomic_and_api_exposes_sources(tmp_path, monkeypatch):
    from app.data import news_store

    monkeypatch.setattr(news_store, "fetch_news_sources", lambda: ([cvm_zip()], {"PETR4": gdelt_json()}))
    path = tmp_path / "news.sqlite"
    summary = refresh_news_snapshot(path, FETCHED)
    with NewsStore(path) as store:
        assert store.version() == summary.version
        assert len(store.filings("PETR4")) == 2
        assert len(store.articles("PETR4")) == 1
    monkeypatch.setattr(news_store, "fetch_news_sources", lambda: ([cvm_zip()], {}))
    refresh_news_snapshot(path, FETCHED + timedelta(days=1))
    with NewsStore(path) as store:
        assert len(store.articles("PETR4")) == 1
    prior = path.read_bytes()
    monkeypatch.setattr(news_store, "fetch_news_sources", lambda: (_ for _ in ()).throw(RuntimeError("CVM offline")))
    try:
        refresh_news_snapshot(path, FETCHED)
    except RuntimeError:
        pass
    assert path.read_bytes() == prior
    client = TestClient(create_app(snapshot_path=tmp_path / "public.sqlite", news_path=path))
    response = client.get("/api/company/news", params={"ticker": "PETR4"})
    assert response.status_code == 200
    body = response.json()
    assert body["filings"][0]["source_url"].startswith("https://www.rad.cvm.gov.br/")
    assert body["articles"][0]["publication_time_known"] is False


def test_news_refresh_coalesces_refiling_across_year_archives(tmp_path, monkeypatch):
    from app.data import news_store

    original = cvm_zip({"2026-11-03": "2026-11-02", "P2": "P1", "RE - Reapresentação": "AP - Apresentação", ";2;": ";1;"})
    revised = cvm_zip()
    monkeypatch.setattr(news_store, "fetch_news_sources", lambda: ([original, revised], {}))
    summary = refresh_news_snapshot(tmp_path / "news.sqlite", FETCHED)
    assert summary.filing_count == 2


def test_filing_impact_uses_only_pre_event_factor_model():
    filing = next(item for item in parse_cvm_ipe(cvm_zip(), FETCHED) if item.status == "refiled")
    filing = replace(filing, published_at=datetime(2026, 1, 35 - 4, tzinfo=timezone.utc))
    start = date(2026, 1, 1)
    points = []
    for i in range(55):
        day = start + timedelta(days=i)
        factor = (i % 7 - 3) / 1000
        expected = 0.001 + 2 * factor
        observed = expected + (0.03 if i == 31 else 0)
        points.append(ReturnPoint(day, observed, observed, {"BCB:SGS:1": factor}))
    result = study_filing_impact(filing, ReturnFrame("EQUITY:PETR4", tuple(points)), ("BCB:SGS:1",), lookback=30)
    assert result.event.effective_session == date(2026, 2, 1)
    assert result.train_count == 30
    assert result.event.windows[1].abnormal_return == pytest.approx(0.03)
    assert result.coefficients["BCB:SGS:1"] == pytest.approx(2)


def test_cash_distribution_changes_only_total_mode_for_the_same_event_sessions():
    filing = next(item for item in parse_cvm_ipe(cvm_zip(), FETCHED) if item.status == "refiled")
    filing = replace(filing, published_at=datetime(2026, 1, 31, tzinfo=timezone.utc))
    points = []
    for index in range(55):
        day = date(2026, 1, 1) + timedelta(days=index)
        factor = (index % 7 - 3) / 1000
        price = 0.001 + 2 * factor + (0.03 if index == 31 else 0)
        total = price + (0.02 if index == 31 else 0)
        points.append(ReturnPoint(day, price, total, {"BCB:SGS:1": factor}))
    frame = ReturnFrame("EQUITY:PETR4", tuple(points))
    price_study = study_filing_impact(filing, frame, ("BCB:SGS:1",), lookback=30, return_mode="price")
    total_study = study_filing_impact(filing, frame, ("BCB:SGS:1",), lookback=30, return_mode="total")
    price_window = price_study.event.windows[1]
    total_window = total_study.event.windows[1]
    assert price_window.session_dates == total_window.session_dates == (date(2026, 2, 1),)
    assert total_window.observed_return - price_window.observed_return == pytest.approx(0.02)
    assert total_window.abnormal_return - price_window.abnormal_return == pytest.approx(0.02)
    no_distribution = ReturnFrame(frame.instrument_id, tuple(replace(point, total_return=point.price_return) for point in points))
    assert study_filing_impact(filing, no_distribution, ("BCB:SGS:1",), lookback=30, return_mode="price").event.windows[1] == study_filing_impact(filing, no_distribution, ("BCB:SGS:1",), lookback=30, return_mode="total").event.windows[1]


def test_local_company_impact_api_links_filing_to_post_event_returns(tmp_path, monkeypatch):
    from tests.test_research_api import research_client

    public = research_client(tmp_path, monkeypatch)
    from app.data import news_store

    archive = cvm_zip({"2026-11-01": "2026-01-29", "2026-11-02": "2026-01-30", "2026-11-03": "2026-01-31"})
    monkeypatch.setattr(news_store, "fetch_news_sources", lambda: ([archive], {"PETR4": gdelt_json()}))
    news_path = tmp_path / "news.sqlite"
    refresh_news_snapshot(news_path, FETCHED)
    client = TestClient(create_app(snapshot_path=public.app.state.snapshot_path, news_path=news_path, local_import_enabled=True, local_equity_path=tmp_path / "equity.sqlite"))
    start = date(2026, 1, 2)
    prices = ["ticker,date,close"]
    close = 100.0
    for index in range(45):
        day = start + timedelta(days=index)
        close *= 1 + 0.001 + (index % 7 - 3) / 1000 + (0.03 if day == date(2026, 2, 1) else 0)
        prices.append(f"PETR4,{day},{close:.6f}")
    actions = "ticker,ex_date,kind,amount,split_factor\nPETR4,2026-01-15,dividend,2,"
    assert client.post("/api/local/equity/import", json={"prices_csv": "\n".join(prices), "actions_csv": actions}).status_code == 200
    response = client.get("/api/local/equity/PETR4/news-impact")
    assert response.status_code == 200
    body = response.json()
    assert len(body["events"]) == 2
    measured = next(item for item in body["events"] if item["category"] == "Fato Relevante")
    cancelled = next(item for item in body["events"] if item["category"] == "Comunicado ao Mercado")
    assert measured["effective_session"] == "2026-02-01"
    assert measured["windows"]["1"]["available"]
    assert measured["price_windows"]["1"]["session_dates"] == measured["windows"]["1"]["session_dates"]
    assert cancelled["windows"]["1"]["reason"] == "filing_cancelled"
    assert "price_cohort" in body
    assert measured["source_url"].startswith("https://www.rad.cvm.gov.br/")
    no_flows = "ticker,ex_date,kind,amount,split_factor\n"
    assert client.post("/api/local/equity/import", json={"prices_csv": "\n".join(prices), "actions_csv": no_flows}).status_code == 200
    assert client.get("/api/local/equity/PETR4/regression").status_code == 422
    assert client.get("/api/local/equity/PETR4/news-impact").status_code == 200
