import json
from datetime import date, datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.data.refresh import refresh_snapshot
from app.main import create_app


TITLE = "Tesouro Prefixado com Juros Semestrais"
MATURITY = "01/01/2033"
INSTRUMENT = "TESOURO:Tesouro Prefixado com Juros Semestrais:2033-01-01"
BENCHMARK = "TESOURO:Tesouro Prefixado:2029-01-01"


def research_client(tmp_path, monkeypatch):
    from app.data import refresh

    start = date(2026, 1, 2)
    header = "Tipo Titulo;Data Vencimento;Data Base;Taxa Compra Manha;Taxa Venda Manha;PU Compra Manha;PU Venda Manha;PU Base Manha"
    prices = [header]
    usd, title, benchmark = 5.0, 100.0, 100.0
    usd_rows, selic_rows = [], []
    for i in range(45):
        day = start + timedelta(days=i)
        x = (i % 7 - 3) / 1000
        usd *= 1 + x
        title *= 1 + 0.001 + 0.3 * x + (i % 3 - 1) / 10000
        benchmark *= 1 + 0.0005 + 0.2 * x
        for name, maturity, value in ((TITLE, MATURITY, title), ("Tesouro Prefixado", "01/01/2029", benchmark)):
            prices.append(f"{name};{maturity};{day:%d/%m/%Y};1;1;1;{value:.6f};1".replace(f"{value:.6f}", f"{value:.6f}".replace(".", ",")))
        usd_rows.append({"data": f"{day:%d/%m/%Y}", "valor": f"{usd:.6f}"})
        selic_rows.append({"data": f"{day:%d/%m/%Y}", "valor": f"{0.04 + (i % 5) * 0.001:.6f}"})
    coupon = f"Tipo Titulo;Vencimento do Titulo;Data Resgate;PU;Quantidade;Valor\n{TITLE};{MATURITY};16/01/2026;2,000000;1;2"
    news = {"conteudo": [{"nro_reuniao": 282, "dataReferencia": "2026-01-25", "titulo": "Copom decide sobre Selic"}]}
    monkeypatch.setattr(refresh, "fetch_sources", lambda: ("\n".join(prices).encode(), coupon.encode(), {1: json.dumps(usd_rows).encode(), 11: json.dumps(selic_rows).encode()}, json.dumps(news).encode()))
    path = tmp_path / "snapshot.sqlite"
    refresh_snapshot(path, datetime(2026, 2, 20, tzinfo=timezone.utc))
    return TestClient(create_app(snapshot_path=path))


def test_catalog_series_regression_and_events(tmp_path, monkeypatch):
    client = research_client(tmp_path, monkeypatch)
    catalog = client.get("/api/catalog").json()
    assert catalog["version"]
    assert any(item["series_id"] == INSTRUMENT for item in catalog["instruments"])
    assert catalog["benchmark_id"] == BENCHMARK
    series = client.get(f"/api/series/{INSTRUMENT}").json()
    assert len(series["observations"]) == 45
    assert series["cash_flows"][0]["amount"] == 2
    assert "tesourotransparente.gov.br" in series["series"]["source_url"]
    regression = client.get("/api/research/regression", params={"instrument_id": INSTRUMENT}).json()
    assert regression["price"]["sample_dates"] == regression["total"]["sample_dates"]
    assert regression["price"]["holdout_count"] > 1
    assert regression["price"]["r_squared"] != regression["total"]["r_squared"]
    assert regression["points"][13]["price_return"] != regression["points"][13]["total_return"]
    events = client.get("/api/events", params={"topic": "copom", "instrument_id": INSTRUMENT}).json()
    assert events["events"][0]["event_id"] == "COPOM:282"
    assert events["events"][0]["windows"]["3"]["available"]
    assert events["events"][0]["source_url"].startswith("https://www.bcb.gov.br/")
    assert events["cohort"]["3"]["sample_count"] == 1


def test_missing_series_and_insufficient_data_have_stable_reasons(tmp_path, monkeypatch):
    client = research_client(tmp_path, monkeypatch)
    missing = client.get("/api/series/missing")
    assert missing.status_code == 404
    assert missing.json()["detail"]["reason"] == "series_not_found"
    inadequate = client.get("/api/research/regression", params={"instrument_id": BENCHMARK, "factor_ids": "BCB:SGS:433"})
    assert inadequate.status_code == 422
    assert inadequate.json()["detail"]["reason"] == "insufficient_data"
