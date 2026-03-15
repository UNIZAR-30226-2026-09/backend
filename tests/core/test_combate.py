import pytest
from app.core.logica_juego.combate import calcular_dados, comparar_dados, validar_tropas

def test_calculo_cantidad_dados():
    # Regla: Si ataco con 3 y defienden 5, yo tiro 3 dados y él tira 2.
    dados_a, dados_d = calcular_dados(tropas_atacantes=3, tropas_defensoras=5)
    assert dados_a == 3
    assert dados_d == 2

    # Regla: Si defienden con 1, solo tira 1 dado.
    dados_a2, dados_d2 = calcular_dados(tropas_atacantes=3, tropas_defensoras=1)
    assert dados_d2 == 1

def test_comparacion_dados_victoria_atacante():
    # El atacante saca [6, 3, 1] y el defensor [5, 4]
    bajas_atacante, bajas_defensor = comparar_dados([6, 3, 1], [5, 4])
    
    # Combate 1: 6 vs 5 -> Gana Atacante (1 baja defensor)
    # Combate 2: 3 vs 4 -> Gana Defensor (1 baja atacante)
    # El tercer dado (1) se descarta porque el defensor no tiene más dados.
    assert bajas_atacante == 1
    assert bajas_defensor == 1

def test_comparacion_dados_empate_gana_defensor():
    # Regla de Risk: En caso de empate, gana el defensor.
    # Atacante saca [4, 2], Defensor saca [4, 1]
    bajas_atacante, bajas_defensor = comparar_dados([4, 2], [4, 1])
    
    # Combate 1: 4 vs 4 -> Empate, gana defensor (1 baja atacante)
    # Combate 2: 2 vs 1 -> Gana atacante (1 baja defensor)
    assert bajas_atacante == 1
    assert bajas_defensor == 1

def test_reglas_basicas_tropas():
    # No se puede atacar con 0 tropas
    with pytest.raises(ValueError, match="al menos 1"):
        validar_tropas(tropas_atacantes=0, tropas_defensoras=2)