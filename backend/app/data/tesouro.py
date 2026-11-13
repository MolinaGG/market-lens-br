"""Tesouro Direto CSV adapters: quoted sale PU and coupon PU per unit."""

import csv
from datetime import datetime
from decimal import Decimal
from io import StringIO

from app.data.models import CashFlow, Observation


PRICES_URL = "https://www.tesourotransparente.gov.br/ckan/dataset/df56aa42-484a-4a59-8184-7676580c81e3/resource/796d2059-14e9-44e3-80c9-2d9e30b405c1/download/precotaxatesourodireto.csv"
COUPONS_URL = "https://www.tesourotransparente.gov.br/ckan/dataset/f30db6e4-6123-416c-b094-be8dfc823601/resource/de2af5cf-9dbd-4566-b933-da6871cce030/download/cupomjurostesourodireto.csv"


def instrument_id(title: str, maturity: str) -> str:
    maturity_date = datetime.strptime(maturity.strip(), "%d/%m/%Y").date()
    return f"TESOURO:{title.strip()}:{maturity_date.isoformat()}"


def _rows(data: bytes):
    return csv.DictReader(StringIO(data.decode("utf-8-sig")), delimiter=";")


def _decimal(value: str) -> Decimal:
    return Decimal(value.replace(".", "").replace(",", "."))


def parse_prices(data: bytes, fetched_at: datetime) -> list[Observation]:
    observations = []
    for row in _rows(data):
        value = row["PU Venda Manha"].strip()
        if not value:
            continue
        observations.append(
            Observation(
                instrument_id(row["Tipo Titulo"], row["Data Vencimento"]),
                datetime.strptime(row["Data Base"], "%d/%m/%Y").date(),
                _decimal(value),
                PRICES_URL,
                fetched_at,
            )
        )
    return observations


def parse_coupons(data: bytes, fetched_at: datetime) -> list[CashFlow]:
    flows = []
    for row in _rows(data):
        amount = row["PU"].strip()
        if not amount:
            continue
        flows.append(
            CashFlow(
                instrument_id(row["Tipo Titulo"], row["Vencimento do Titulo"]),
                datetime.strptime(row["Data Resgate"], "%d/%m/%Y").date(),
                _decimal(amount),
                COUPONS_URL,
                fetched_at,
            )
        )
    return flows
