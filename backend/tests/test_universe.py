import pytest

from app.domain.universe import UNIVERSE, get_asset


def test_escopo_inicial_tem_oito_ativos():
    codes = [asset.code for asset in UNIVERSE]
    assert codes == [
        "IBOV", "USDBRL", "PETR4", "VALE3", "ITUB4", "BBDC4", "WEGE3", "ABEV3",
    ]


def test_get_asset_fora_do_escopo_falha():
    with pytest.raises(KeyError):
        get_asset("MGLU3")
