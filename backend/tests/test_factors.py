from datetime import date, datetime, timezone
from decimal import Decimal
from io import BytesIO

import openpyxl
import pytest

from app.analysis.returns import build_return_frame
from app.data.models import Observation


FETCHED = datetime(2026, 11, 13, tzinfo=timezone.utc)


def test_eia_brent_reads_daily_prices_and_skips_missing_values(monkeypatch):
    from app.data.eia import parse_eia_brent

    class Sheet:
        nrows = 6

        def row_values(self, index):
            return {
                0: ["Back to Contents", "Brent"],
                1: ["Sourcekey", "RBRTE"],
                2: ["Date", "Europe Brent Spot Price FOB"],
                3: [46328.0, 71.25],
                4: [46329.0, ""],
                5: [46330.0, 72.50],
            }[index]

    class Workbook:
        def sheet_by_name(self, name):
            assert name == "Data 1"
            return Sheet()

        datemode = 0

    monkeypatch.setattr("app.data.eia.xlrd.open_workbook", lambda file_contents: Workbook())
    monkeypatch.setattr("app.data.eia.xlrd.xldate_as_datetime", lambda value, mode: datetime(2026, 11, 1 + int(value - 46328)))
    data = parse_eia_brent(b"xls", FETCHED)
    assert [(item.date, item.value) for item in data] == [(date(2026, 11, 1), Decimal("71.25")), (date(2026, 11, 3), Decimal("72.5"))]
    assert data[0].series_id == "EIA:BRENT"
    assert "eia.gov" in data[0].source_url


def test_world_bank_monthly_prices_keep_units_and_months():
    from app.data.world_bank import parse_world_bank_monthly

    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Monthly Prices"
    for _ in range(4):
        sheet.append([None])
    sheet.append([None, "Crude oil, Brent", "Gold", "Copper"])
    sheet.append([None, "($/bbl)", "($/troy oz)", "($/mt)"])
    sheet.append(["2026M09", 70.5, 2600.0, 9000.0])
    sheet.append(["2026M10", 72.5, 2700.0, 9100.0])
    output = BytesIO()
    workbook.save(output)
    values = parse_world_bank_monthly(output.getvalue(), FETCHED)
    assert {(item.series_id, item.date, item.value) for item in values} >= {
        ("WB:CMO:BRENT", date(2026, 10, 1), Decimal("72.5")),
        ("WB:CMO:GOLD", date(2026, 9, 1), Decimal("2600.0")),
    }


def test_monthly_factor_cannot_be_silently_forward_filled_into_daily_model():
    price = [Observation("TESOURO:TEST", date(2026, 10, d), Decimal(str(100 + d)), "source", FETCHED) for d in (1, 2, 3)]
    monthly = [Observation("WB:CMO:BRENT", date(2026, 10, 1), Decimal("70"), "source", FETCHED)]
    with pytest.raises(ValueError, match="monthly"):
        build_return_frame(price, [], {"WB:CMO:BRENT": monthly})
