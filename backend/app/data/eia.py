"""Daily Brent spot prices from the public EIA historical workbook."""

from datetime import datetime
from decimal import Decimal, InvalidOperation

import xlrd

from app.data.models import Observation


BRENT_URL = "https://www.eia.gov/dnav/pet/hist_xls/RBRTED.xls"
BRENT_PAGE_URL = "https://www.eia.gov/dnav/pet/hist/RBRTED.htm"


def parse_eia_brent(raw: bytes, fetched_at: datetime) -> list[Observation]:
    workbook = xlrd.open_workbook(file_contents=raw)
    sheet = workbook.sheet_by_name("Data 1")
    if sheet.row_values(1)[1] != "RBRTE":
        raise ValueError("Unexpected EIA Brent source key")
    values: dict = {}
    for index in range(3, sheet.nrows):
        row = sheet.row_values(index)
        if len(row) < 2 or row[1] in ("", None):
            continue
        try:
            observed = xlrd.xldate_as_datetime(row[0], workbook.datemode).date()
            price = Decimal(str(row[1]))
        except (TypeError, ValueError, InvalidOperation):
            continue
        if price > 0:
            values[observed] = Observation("EIA:BRENT", observed, price, BRENT_PAGE_URL, fetched_at)
    return [values[day] for day in sorted(values)]
