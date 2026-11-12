"""Escopo inicial de ativos. Símbolos do Yahoo Finance usados pelo yfinance."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Asset:
    code: str
    name: str
    yahoo_symbol: str


UNIVERSE: tuple[Asset, ...] = (
    Asset("IBOV", "Ibovespa", "^BVSP"),
    Asset("USDBRL", "Dólar / Real", "USDBRL=X"),
    Asset("PETR4", "Petrobras PN", "PETR4.SA"),
    Asset("VALE3", "Vale ON", "VALE3.SA"),
    Asset("ITUB4", "Itaú Unibanco PN", "ITUB4.SA"),
    Asset("BBDC4", "Bradesco PN", "BBDC4.SA"),
    Asset("WEGE3", "WEG ON", "WEGE3.SA"),
    Asset("ABEV3", "Ambev ON", "ABEV3.SA"),
)


def get_asset(code: str) -> Asset:
    for asset in UNIVERSE:
        if asset.code == code:
            return asset
    raise KeyError(f"Ativo fora do escopo inicial: {code}")
