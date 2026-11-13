"""Monthly nominal commodity prices from the World Bank Pink Sheet workbook."""

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from io import BytesIO

import openpyxl

from app.data.models import Observation


MONTHLY_URL = "https://thedocs.worldbank.org/en/doc/74e8be41ceb20fa0da750cda2f6b9e4e-0050012026/related/CMO-Historical-Data-Monthly.xlsx"
DATASET_URL = "https://www.worldbank.org/en/research/commodity-markets"
COMMODITIES = {
    "Crude oil, Brent": ("WB:CMO:BRENT", "Brent · média mensal"),
    "Gold": ("WB:CMO:GOLD", "Ouro · média mensal"),
    "Copper": ("WB:CMO:COPPER", "Cobre · média mensal"),
    "Coffee, Arabica": ("WB:CMO:COFFEE_ARABICA", "Café arábica · média mensal"),
}


def parse_world_bank_monthly(raw: bytes, fetched_at: datetime) -> list[Observation]:
    workbook = openpyxl.load_workbook(BytesIO(raw), read_only=True, data_only=True)
    try:
        sheet = workbook["Monthly Prices"]
        rows = sheet.iter_rows(values_only=True)
        for _ in range(4):
            next(rows)
        headers = next(rows)
        units = next(rows)
        selected = {index: COMMODITIES[name][0] for index, name in enumerate(headers) if name in COMMODITIES}
        if not selected:
            raise ValueError("World Bank commodity columns not found")
        values = []
        for row in rows:
            period = row[0]
            if not isinstance(period, str) or len(period) != 7 or period[4] != "M":
                continue
            try:
                observed = date(int(period[:4]), int(period[5:]), 1)
            except ValueError:
                continue
            for index, series_id in selected.items():
                if index >= len(row) or row[index] in (None, "", "�"):
                    continue
                try:
                    price = Decimal(str(row[index]))
                except (ValueError, InvalidOperation):
                    continue
                if price > 0:
                    values.append(Observation(series_id, observed, price, DATASET_URL, fetched_at))
        return values
    finally:
        workbook.close()
