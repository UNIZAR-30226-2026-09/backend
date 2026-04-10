import pytest
from unittest.mock import MagicMock, patch
from app.core.logica_juego.ataques_especiales import (
    ejecutar_mortero_tactico, ejecutar_misil_crucero, ejecutar_cabeza_nuclear,
    ejecutar_bomba_racimo, ejecutar_gripe_aviar, ejecutar_vacuna,
    ejecutar_coronavirus, ejecutar_fatiga, ejecutar_inhibidor,
    ejecutar_propaganda, ejecutar_muro, ejecutar_sanciones
)
from app.core.logica_juego.config_ataques_especiales import TipoAtaque, TipoEfecto, CONFIG_ATAQUES
from app.schemas.estado_juego import TerritorioBase

class MockEstado:
    def __init__(self):
        self.mapa = {
            "T1": {"owner_id": "jugador1", "units": 10, "efectos": [], "estado_bloqueo": None},
            "T2": {"owner_id": "jugador2", "units": 10, "efectos": [], "estado_bloqueo": None},
            "T3": {"owner_id": "jugador2", "units": 20, "efectos": [], "estado_bloqueo": None},
            "T4": {"owner_id": "jugador2", "units": 10, "efectos": [], "estado_bloqueo": None},
        }
        self.jugadores = {
            "jugador1": {"tecnologias_compradas": [], "efectos": [], "monedas": 1000},
            "jugador2": {"tecnologias_compradas": [], "efectos": [], "monedas": 1000},
        }

@pytest.fixture
def estado_mock():
    return MockEstado()

@patch("app.core.map_state.map_calculator.calcular_distancia")
def test_mortero_tactico_rango_exacto(mock_dist, estado_mock):
    # Mortero requiere rango EXACTO 2
    mock_dist.return_value = 2
    ejecutar_mortero_tactico(estado_mock, "jugador1", "T1", "T2")
    # El daño es aleatorio 1-4, así que units < 10
    assert estado_mock.mapa["T2"]["units"] < 10
    
    # Probar error si rango no es 2
    mock_dist.return_value = 1
    with pytest.raises(ValueError, match="exactamente 2"):
        ejecutar_mortero_tactico(estado_mock, "jugador1", "T1", "T2")

@patch("app.core.map_state.map_calculator.calcular_distancia")
def test_misil_crucero_dano_porcentual(mock_dist, estado_mock):
    mock_dist.return_value = 3 # Rango max 3
    # 10 unidades - 30% (3) = 7
    ejecutar_misil_crucero(estado_mock, "jugador1", "T1", "T2")
    assert estado_mock.mapa["T2"]["units"] == 7

@patch("app.core.map_state.map_calculator.calcular_distancia")
@patch("app.core.map_state.map_calculator.obtener_vecinos")
def test_bomba_racimo_area(mock_vecinos, mock_dist, estado_mock):
    mock_dist.return_value = 1
    mock_vecinos.return_value = ["T3"]
    
    # T2: 10 units -> -50% = 5
    # T3: 20 units -> -30% = 14
    ejecutar_bomba_racimo(estado_mock, "jugador1", "T1", "T2")
    
    assert estado_mock.mapa["T2"]["units"] == 5
    assert estado_mock.mapa["T3"]["units"] == 14

def test_vacuna_universal_limpia_enfermedades(estado_mock):
    estado_mock.mapa["T1"]["efectos"] = [
        {"tipo_efecto": TipoEfecto.GRIPE_AVIAR, "duracion_restante": 3, "origen_jugador_id": "jugador2"},
        {"tipo_efecto": TipoEfecto.PROPAGANDA, "duracion_restante": 2, "origen_jugador_id": "jugador2"}
    ]
    
    ejecutar_vacuna(estado_mock, "jugador1", "T1", "T1")
    
    # Gripe aviar debe desaparecer, Propaganda NO (no es enfermedad curable en config)
    tipos = [e["tipo_efecto"] for e in estado_mock.mapa["T1"]["efectos"]]
    assert TipoEfecto.GRIPE_AVIAR not in tipos
    assert TipoEfecto.PROPAGANDA in tipos

@patch("app.core.map_state.map_calculator.calcular_distancia")
def test_muro_fronterizo_bidireccional(mock_dist, estado_mock):
    mock_dist.return_value = 1
    ejecutar_muro(estado_mock, "jugador1", "T1", "T2")
    
    # T1 debe bloquear hacia T2
    efecto_t1 = next(e for e in estado_mock.mapa["T1"]["efectos"] if e["tipo_efecto"] == TipoEfecto.MURO)
    assert efecto_t1["bloquea_hacia"] == "T2"
    
    # T2 debe bloquear hacia T1
    efecto_t2 = next(e for e in estado_mock.mapa["T2"]["efectos"] if e["tipo_efecto"] == TipoEfecto.MURO)
    assert efecto_t2["bloquea_hacia"] == "T1"

def test_sanciones_internacionales_jugador(estado_mock):
    ejecutar_sanciones(estado_mock, "jugador1", None, "jugador2")
    
    assert any(e["tipo_efecto"] == TipoEfecto.SANCIONES for e in estado_mock.jugadores["jugador2"]["efectos"])
