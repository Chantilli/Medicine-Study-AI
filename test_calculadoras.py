import pytest

from calculadoras_clinicas import (
    calcular_aclaramiento_creatinina,
    calcular_imc,
    calcular_superficie_corporal,
)


def test_imc_normal():
    assert calcular_imc(70, 175)["valor"] == 22.9


def test_imc_error_peso_negativo():
    assert "error" in calcular_imc(-5, 175)


def test_superficie_corporal_mosteller():
    resultado = calcular_superficie_corporal(70, 175)
    assert resultado["valor"] == pytest.approx(1.84, abs=0.01)


def test_aclaramiento_rechaza_datos_invalidos():
    assert "error" in calcular_aclaramiento_creatinina(
        edad=-1, peso_kg=70, creatinina_mg_dl=1, sexo="M", altura_cm=175
    )
