import json
from datetime import datetime
from decimal import Decimal

from app.data.models import Observation


SGS_NAMES = {1: ("USD/BRL venda", "BRL por USD"), 11: ("Selic diária", "% a.d."), 433: ("IPCA mensal", "% a.m.")}


def sgs_url(series_number: int) -> str:
    return f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{series_number}/dados?formato=json"


def parse_sgs(data: bytes, series_number: int, fetched_at: datetime) -> list[Observation]:
    if series_number not in SGS_NAMES:
        raise ValueError(f"SGS series not configured: {series_number}")
    rows = json.loads(data)
    if not isinstance(rows, list):
        raise ValueError("SGS response must be a list")
    return [
        Observation(
            f"BCB:SGS:{series_number}",
            datetime.strptime(row["data"], "%d/%m/%Y").date(),
            Decimal(row["valor"].replace(",", ".")),
            sgs_url(series_number),
            fetched_at,
        )
        for row in rows
    ]
