import pytest
from fastapi import HTTPException, status

from app.api.v1.endpoints.combates import (
    aplicar_bajas,
    gestionar_victoria,
    obtener_datos_territorio,
    verificar_movimiento_pendiente,
)
from app.core.logica_juego.validaciones import validar_ataque_convencional
from app.core.map_state import map_calculator, game_map_state
from app.models.partida import FasePartida
from app.schemas.combate import ResultadoCombate
from app.schemas.estado_juego import JugadorBase, TerritorioBase


def _resultado(victoria: bool, bajas_atacante: int = 0, bajas_defensor: int = 0) -> ResultadoCombate:
    return ResultadoCombate(
        dados_atacante=[6],
        dados_defensor=[1],
        bajas_atacante=bajas_atacante,
        bajas_defensor=bajas_defensor,
        victoria_atacante=victoria,
        tropas_restantes_defensor=0,
    )


def test_gestionar_victoria_actualiza_estado_de_conquista():
    t_destino = TerritorioBase(owner_id="defensor", units=2)
    jugador_estado = JugadorBase()

    gestionar_victoria(
        t_destino=t_destino,
        jugador_estado=jugador_estado,
        atacante_id="atacante",
        origen_id="A",
        destino_id="B",
        resultado=_resultado(victoria=True),
    )

    assert t_destino.owner_id == "atacante"
    assert jugador_estado.movimiento_conquista_pendiente is True
    assert jugador_estado.origen_conquista == "A"
    assert jugador_estado.destino_conquista == "B"


def test_gestionar_victoria_no_modifica_si_no_hay_conquista():
    t_destino = TerritorioBase(owner_id="defensor", units=2)
    jugador_estado = JugadorBase()

    gestionar_victoria(
        t_destino=t_destino,
        jugador_estado=jugador_estado,
        atacante_id="atacante",
        origen_id="A",
        destino_id="B",
        resultado=_resultado(victoria=False),
    )

    assert t_destino.owner_id == "defensor"
    assert jugador_estado.movimiento_conquista_pendiente is False
    assert jugador_estado.origen_conquista is None
    assert jugador_estado.destino_conquista is None


def test_verificar_movimiento_pendiente_lanza_error():
    jugadores = {
        "player1": {
            "movimiento_conquista_pendiente": True,
            "origen_conquista": "A",
            "destino_conquista": "B",
        }
    }

    with pytest.raises(HTTPException) as exc_info:
        verificar_movimiento_pendiente(jugadores, "player1")

    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert "Debes mover tropas" in exc_info.value.detail


def test_verificar_movimiento_pendiente_devuelve_estado():
    jugadores = {"player1": {"movimiento_conquista_pendiente": False}}

    jugador_estado = verificar_movimiento_pendiente(jugadores, "player1")

    assert isinstance(jugador_estado, JugadorBase)
    assert jugador_estado.movimiento_conquista_pendiente is False


def test_aplicar_bajas_actualiza_unidades():
    t_origen = TerritorioBase(owner_id="atacante", units=5)
    t_destino = TerritorioBase(owner_id="defensor", units=3)

    aplicar_bajas(t_origen, t_destino, _resultado(victoria=True, bajas_atacante=2, bajas_defensor=1))

    assert t_origen.units == 3
    assert t_destino.units == 2


def test_obtener_datos_territorio_ok():
    mapa = {"A": {"owner_id": "player", "units": 4}}

    territorio = obtener_datos_territorio(mapa, "A")

    assert territorio.owner_id == "player"
    assert territorio.units == 4


def test_obtener_datos_territorio_inexistente_lanza_error():
    mapa = {"A": {"owner_id": "player", "units": 4}}

    with pytest.raises(HTTPException) as exc_info:
        obtener_datos_territorio(mapa, "B")

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


def test_validar_ataque_no_colindante_lanza_error():
    class EstadoDummy:
        user_turno_actual = "player"
        fase_actual = FasePartida.ATAQUE_CONVENCIONAL

    # Buscamos dos comarcas que no sean vecinas en el mapa real
    origen_id = destino_id = None
    comarcas = list(game_map_state.comarcas.keys())
    for a in comarcas:
        for b in comarcas:
            if a != b and not map_calculator.son_vecinas(a, b):
                origen_id, destino_id = a, b
                break
        if origen_id:
            break
    assert origen_id is not None, "No se encontró un par de comarcas no colindantes para el test"

    t_origen = TerritorioBase(owner_id="player", units=3)
    t_destino = TerritorioBase(owner_id="enemy", units=2)

    with pytest.raises(ValueError, match="no están conectados"):
        validar_ataque_convencional(
            EstadoDummy(),
            origen_id,
            t_origen,
            destino_id,
            t_destino,
            1,
            "player",
            map_calculator,
        )
