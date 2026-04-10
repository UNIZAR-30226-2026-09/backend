import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from app.core.logica_juego.efectos_persistentes import procesar_efectos_fin_de_turno
from app.core.logica_juego.maquina_estados import asignar_tropas_reserva, resolver_gestion_ronda
from app.core.logica_juego.combate import resolver_colocacion_tropas
from app.core.logica_juego.config_ataques_especiales import TipoEfecto, TipoAtaque
from app.schemas.estado_juego import JugadorBase

class MockEstado:
    def __init__(self):
        self.mapa = {
            "T1": {"owner_id": "jugador1", "units": 10, "efectos": [], "estado_bloqueo": None},
            "T2": {"owner_id": "jugador2", "units": 10, "efectos": [], "estado_bloqueo": None},
        }
        self.jugadores = {
            "jugador1": {
                "tecnologias_compradas": [], 
                "efectos": [], 
                "monedas": 1000,
                "tropas_reserva": 0,
                "nivel_ramas": {},
                "tecnologias_predesbloqueadas": [],
                "territorio_trabajando": None,
                "territorio_investigando": None,
                "rama_investigando": None
            },
            "jugador2": {
                "tecnologias_compradas": [], 
                "efectos": [], 
                "monedas": 1000,
                "tropas_reserva": 0
            },
        }
        self.user_turno_actual = "jugador1"
        self.partida_id = 1
        self.fin_fase_actual = datetime.now(timezone.utc)

@pytest.fixture
def estado_mock():
    return MockEstado()

@pytest.mark.asyncio
async def test_gripe_aviar_dano_por_turno(estado_mock):
    estado_mock.mapa["T1"]["efectos"].append({
        "tipo_efecto": TipoEfecto.GRIPE_AVIAR,
        "duracion_restante": 2,
        "origen_jugador_id": "jugador2"
    })

    await procesar_efectos_fin_de_turno(estado_mock)

    # Daño por turno es 1
    assert estado_mock.mapa["T1"]["units"] == 9
    assert estado_mock.mapa["T1"]["efectos"][0]["duracion_restante"] == 1

@pytest.mark.asyncio
async def test_expiracion_efectos(estado_mock):
    estado_mock.mapa["T1"]["efectos"].append({
        "tipo_efecto": TipoEfecto.FATIGA,
        "duracion_restante": 1,
        "origen_jugador_id": "jugador2"
    })

    await procesar_efectos_fin_de_turno(estado_mock)

    # Duracion era 1, al restar queda 0 y se elimina
    assert len(estado_mock.mapa["T1"]["efectos"]) == 0

@patch("app.core.logica_juego.maquina_estados.actualizar_tropas_reserva")
@patch("app.core.logica_juego.maquina_estados.obtener_territorios_jugador")
async def test_sanciones_bloquean_refuerzos(mock_territorios, mock_actualizar, estado_mock):
    estado_mock.jugadores["jugador1"]["efectos"].append({
        "tipo_efecto": TipoEfecto.SANCIONES, 
        "duracion_restante": 1, 
        "origen_jugador_id": "jugador2"
    })
    mock_territorios.return_value = ["T1", "T2", "T3", "T4", "T5", "T6"] # Debería recibir 2
    
    db_mock = MagicMock()
    tropas = await asignar_tropas_reserva(estado_mock, db_mock)
    
    assert tropas == 0
    mock_actualizar.assert_called_with(db_mock, estado_mock, "jugador1", 0)

@patch("app.core.logica_juego.maquina_estados.actualizar_tropas_reserva")
@patch("app.core.logica_juego.maquina_estados.obtener_territorios_jugador")
async def test_academia_militar_multiplica_refuerzos(mock_territorios, mock_actualizar, estado_mock):
    estado_mock.jugadores["jugador1"]["tecnologias_compradas"] = [TipoAtaque.ACADEMIA_MILITAR]
    mock_territorios.return_value = ["T1", "T2", "T3", "T4", "T5", "T6"] # Recibe 3 (max(3, 6//3))
    
    # 3 * 1.5 = 4.5 -> ceil(4.5) = 5
    db_mock = MagicMock()
    await asignar_tropas_reserva(estado_mock, db_mock)

    mock_actualizar.assert_called_with(db_mock, estado_mock, "jugador1", 5)

@patch("app.core.logica_juego.maquina_estados.flag_modified")
async def test_fatiga_bloquea_gestion(mock_flag, estado_mock):
    estado_mock.jugadores["jugador1"]["territorio_trabajando"] = "T1"
    estado_mock.mapa["T1"]["estado_bloqueo"] = "trabajo"
    estado_mock.mapa["T1"]["efectos"].append({
        "tipo_efecto": TipoEfecto.FATIGA, 
        "duracion_restante": 1, 
        "origen_jugador_id": "jugador2"
    })
    
    await resolver_gestion_ronda(estado_mock, "jugador1")
    
    # No debe recibir dinero y el territorio sigue bloqueado
    assert estado_mock.jugadores["jugador1"]["monedas"] == 1000
    assert estado_mock.mapa["T1"]["estado_bloqueo"] == "trabajo"

@pytest.mark.asyncio
async def test_propaganda_subversiva_roba_colocacion(estado_mock):
    estado_mock.mapa["T2"]["efectos"].append({
        "tipo_efecto": TipoEfecto.PROPAGANDA,
        "duracion_restante": 2,
        "origen_jugador_id": "jugador1"  # Atacante
    })

    # Jugador 2 coloca 4 tropas en T2
    jugador2_obj = MagicMock()
    jugador2_obj.tropas_reserva = 10

    t2_obj = MagicMock()
    t2_obj.units = 5

    await resolver_colocacion_tropas(
        jugador2_obj,
        t2_obj,
        tropas_a_poner=4,
        data_territorio=estado_mock.mapa["T2"],
        jugadores_estado=estado_mock.jugadores,
        partida_id=1
    )
    
    # Roba el 50% (ceil(4 * 0.5) = 2)
    # Jugador 2: pierde 4 de reserva, pero solo 2 llegan al territorio.
    # Jugador 1: gana 2 en su reserva.
    assert t2_obj.units == 5 + 2
    assert jugador2_obj.tropas_reserva == 6
    assert estado_mock.jugadores["jugador1"]["tropas_reserva"] == 2
