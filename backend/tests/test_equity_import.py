from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from io import StringIO

import pytest
from fastapi.testclient import TestClient

from app.analysis.regression import compare_regressions
from app.analysis.returns import build_return_frame
from app.data.equity_import import import_equity_csv, read_imported_equity
from app.data.models import Observation
from app.main import create_app


PRICE_CSV = "ticker,date,close\nPETR4,2026-01-02,100\nPETR4,2026-01-05,49\n"
ACTION_CSV = "ticker,ex_date,kind,amount,split_factor\nPETR4,2026-01-05,split,,2\nPETR4,2026-01-05,dividend,1,\n"


def test_import_split_and_dividend_keep_same_calendar(tmp_path):
    db = tmp_path / "local.sqlite"
    result = import_equity_csv(StringIO(PRICE_CSV), StringIO(ACTION_CSV), database_path=db)
    assert result.ticker == "PETR4"
    assert result.rights == "local_only"
    assert result.price_count == 2 and result.action_count == 2
    imported = read_imported_equity(db, "PETR4")
    frame = build_return_frame(imported.prices, imported.cash_flows, {}, splits=imported.splits)
    assert frame.dates == (date(2026, 1, 5),)
    assert frame.points[0].price_return == pytest.approx(-0.02)
    assert frame.points[0].total_return == pytest.approx(0)


@pytest.mark.parametrize("prices,actions,part", [
    ("ticker,date,close\nPETR4,2026-01-02,100\nPETR4,2026-01-02,101", ACTION_CSV, "duplicate"),
    ("ticker,date,close\nPETR4,2026-01-02,0\nPETR4,2026-01-05,49", ACTION_CSV, "positive"),
    (PRICE_CSV, ACTION_CSV.replace("PETR4,2026-01-05,dividend", "VALE3,2026-01-05,dividend"), "ticker"),
    (PRICE_CSV, ACTION_CSV.replace("dividend,1,", "dividend,,"), "amount"),
    (PRICE_CSV, "", "empty CSV"),
    (PRICE_CSV, ACTION_CSV.replace("PETR4,2026-01-05,dividend", "PETR4,,dividend"), "ex_date"),
])
def test_import_rejects_invalid_or_incomplete_actions(tmp_path, prices, actions, part):
    with pytest.raises(ValueError, match=part):
        import_equity_csv(StringIO(prices), StringIO(actions), database_path=tmp_path / "local.sqlite")


def test_imported_equity_regressions_share_sample_dates(tmp_path):
    start = date(2026, 1, 1)
    prices = ["ticker,date,close"]
    factor = []
    close = 100.0
    usd = 5.0
    for i in range(35):
        day = start + timedelta(days=i)
        movement = (i % 6 - 2) / 1000
        close *= 1 + 0.001 + movement * 2
        usd *= 1 + movement
        prices.append(f"PETR4,{day},{close:.6f}")
        factor.append(Observation("BCB:SGS:1", day, Decimal(str(usd)), "https://bcb.example", datetime.now(timezone.utc)))
    actions = "ticker,ex_date,kind,amount,split_factor\nPETR4,2026-01-15,dividend,2,"
    db = tmp_path / "local.sqlite"
    import_equity_csv(StringIO("\n".join(prices)), StringIO(actions), database_path=db)
    imported = read_imported_equity(db, "PETR4")
    frame = build_return_frame(imported.prices, imported.cash_flows, {"BCB:SGS:1": factor}, splits=imported.splits)
    comparison = compare_regressions(frame, ("BCB:SGS:1",), frame.dates[25])
    assert comparison.price.sample_dates == comparison.total.sample_dates
    assert comparison.price.r_squared != comparison.total.r_squared


def test_public_api_rejects_import_and_local_api_requires_opt_in(tmp_path):
    public = TestClient(create_app(snapshot_path=tmp_path / "public.sqlite"))
    response = public.post("/api/local/equity/import", json={"prices_csv": PRICE_CSV, "actions_csv": ACTION_CSV})
    assert response.status_code == 403
    assert response.json()["detail"]["reason"] == "local_import_disabled"
    local = TestClient(create_app(snapshot_path=tmp_path / "public.sqlite", local_import_enabled=True, local_equity_path=tmp_path / "equity.sqlite"))
    uploaded = local.post("/api/local/equity/import", json={"prices_csv": PRICE_CSV, "actions_csv": ACTION_CSV})
    assert uploaded.status_code == 200
    assert uploaded.json()["ticker"] == "PETR4"
    assert len(local.get("/api/local/equity/PETR4/series").json()["observations"]) == 2


def test_local_equity_api_compares_proventos_on_public_factor_dates(tmp_path, monkeypatch):
    from tests.test_research_api import research_client

    public = research_client(tmp_path, monkeypatch)
    local = TestClient(create_app(snapshot_path=public.app.state.snapshot_path, local_import_enabled=True, local_equity_path=tmp_path / "equity.sqlite"))
    start = date(2026, 1, 2)
    prices = ["ticker,date,close"]
    close = 100.0
    for i in range(45):
        day = start + timedelta(days=i)
        close *= 1 + 0.001 + (i % 7 - 3) / 1000
        prices.append(f"PETR4,{day},{close:.6f}")
    actions = "ticker,ex_date,kind,amount,split_factor\nPETR4,2026-01-17,dividend,2,"
    assert local.post("/api/local/equity/import", json={"prices_csv": "\n".join(prices), "actions_csv": actions}).status_code == 200
    result = local.get("/api/local/equity/PETR4/regression")
    assert result.status_code == 200
    body = result.json()
    assert body["price"]["sample_dates"] == body["total"]["sample_dates"]
    assert body["price"]["r_squared"] != body["total"]["r_squared"]
