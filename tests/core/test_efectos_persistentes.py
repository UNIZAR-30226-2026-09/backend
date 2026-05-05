import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from app.core.logica_juego.efectos_persistentes import procesar_efectos_fin_de_turno, procesar_efectos_inicio_turno
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
                "tecnologias_predesbloqueadas": [],
                "territorio_trabajando": None,
                "territorio_investigando": None,
                "habilidad_investigando": None
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
@patch("app.crud.crud_partidas.flag_modified")
@patch("app.core.logica_juego.efectos_persistentes.notifier.enviar_actualizacion_territorio")
async def test_gripe_aviar_neutraliza_territorio_con_ultima_tropa(mock_notifier_ws, mock_flag, estado_mock):
    """Si gripe aviar consume la última tropa, el territorio debe pasar a neutral."""
    estado_mock.mapa["T1"]["units"] = 1
    estado_mock.mapa["T1"]["efectos"].append({
        "tipo_efecto": TipoEfecto.GRIPE_AVIAR,
        "duracion": 2,
        "origen_jugador_id": "jugador2"
    })

    await procesar_efectos_inicio_turno(estado_mock, "jugador1")

    assert estado_mock.mapa["T1"]["units"] == 0
    assert estado_mock.mapa["T1"]["owner_id"] == "neutral"


@pytest.mark.asyncio
@patch("app.crud.crud_partidas.flag_modified")
@patch("app.core.logica_juego.efectos_persistentes.notifier.enviar_actualizacion_territorio")
async def test_gripe_aviar_dano_por_turno(mock_notifier_ws, mock_flag, estado_mock):
    estado_mock.mapa["T1"]["efectos"].append({
        "tipo_efecto": TipoEfecto.GRIPE_AVIAR,
        "duracion": 2,
        "origen_jugador_id": "jugador2"
    })

    # El daño ahora se aplica al INICIO del turno del dueño
    await procesar_efectos_inicio_turno(estado_mock, "jugador1")

    # Daño por turno es 1
    assert estado_mock.mapa["T1"]["units"] == 9

@pytest.mark.asyncio
async def test_expiracion_efectos(estado_mock):
    estado_mock.mapa["T1"]["efectos"].append({
        "tipo_efecto": TipoEfecto.FATIGA,
        "duracion": 1,
        "origen_jugador_id": "jugador2"
    })

    await procesar_efectos_fin_de_turno(estado_mock)

    # Duracion era 1, al restar queda 0 y se elimina
    assert len(estado_mock.mapa["T1"]["efectos"]) == 0

@patch("app.core.logica_juego.maquina_estados.notifier.enviar_cambio_fase")
@patch("app.core.logica_juego.maquina_estados.actualizar_tropas_reserva")
@patch("app.core.logica_juego.maquina_estados.obtener_territorios_jugador")
async def test_sanciones_bloquean_refuerzos(mock_territorios, mock_actualizar, mock_notifier, estado_mock):
    estado_mock.jugadores["jugador1"]["efectos"].append({
        "tipo_efecto": TipoEfecto.SANCIONES, 
        "duracion": 1, 
        "origen_jugador_id": "jugador2"
    })
    mock_territorios.return_value = ["T1", "T2", "T3", "T4", "T5", "T6"] # Debería recibir 2 (pero minimo 3)
    
    db_mock = MagicMock()
    tropas, motivo = await asignar_tropas_reserva(estado_mock, db_mock)

    assert tropas == 0
    mock_actualizar.assert_called_with(db_mock, estado_mock, "jugador1", 0)

@patch("app.core.logica_juego.maquina_estados.notifier.enviar_cambio_fase")
@patch("app.core.logica_juego.maquina_estados.actualizar_tropas_reserva")
@patch("app.core.logica_juego.maquina_estados.obtener_territorios_jugador")
async def test_academia_militar_multiplica_refuerzos(mock_territorios, mock_actualizar, mock_notifier, estado_mock):
    estado_mock.jugadores["jugador1"]["academia_activa"] = True
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
        "duracion": 1, 
        "origen_jugador_id": "jugador2"
    })
    
    await resolver_gestion_ronda(estado_mock, "jugador1")
    
    # No debe recibir dinero y el territorio sigue bloqueado
    assert estado_mock.jugadores["jugador1"]["monedas"] == 1000
    assert estado_mock.mapa["T1"]["estado_bloqueo"] == "trabajo"

@pytest.mark.asyncio
@patch("app.core.logica_juego.maquina_estados.actualizar_tropas_reserva")
@patch("app.crud.crud_partidas.flag_modified")
@patch("app.core.logica_juego.maquina_estados.notifier.enviar_cambio_fase")
@patch("app.core.logica_juego.maquina_estados.notifier.enviar_propaganda_activada")
@patch("app.core.logica_juego.maquina_estados.obtener_territorios_jugador")
async def test_propaganda_subversiva_roba_colocacion(mock_territorios, mock_propaganda, mock_notifier, mock_flag, mock_actualizar, estado_mock):
    # La propaganda ahora roba al ASIGNAR RESERVAS
    estado_mock.jugadores["jugador2"] = {
        "tecnologias_compradas": [TipoAtaque.PROPAGANDA_SUBVERSIVA],
        "tropas_reserva": 0,
        "efectos": []
    }
    estado_mock.jugadores["jugador1"]["efectos"].append({
        "tipo_efecto": TipoEfecto.PROPAGANDA,
        "duracion": 2,
        "origen_jugador_id": "jugador2"  # Atacante/Beneficiario
    })
    estado_mock.user_turno_actual = "jugador1" # Víctima
    
    # Jugador 1 tiene 6 territorios -> Debería recibir 3 tropas (minimo)
    mock_territorios.return_value = ["T1"] * 6 
    
    # Recibe 3, roba floor(3 * 0.5) = 1. Quedan 2.
    db_mock = MagicMock()
    await asignar_tropas_reserva(estado_mock, db_mock)
    
    # Verificamos que se han calculado bien las tropas robadas
    # Jugador 1 recibe 2 (3 original - 1 robada)
    # Jugador 2 recibe 1 robada
    mock_actualizar.assert_any_call(db_mock, estado_mock, "jugador1", 2)
    mock_actualizar.assert_any_call(db_mock, estado_mock, "jugador2", 1)
    mock_propaganda.assert_called_once()
