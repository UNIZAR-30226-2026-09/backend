import pytest
from app.core.logica_juego.combate import resolver_fortificacion
from app.core.logica_juego.validaciones import validar_fortificacion
from app.core.map_state import map_calculator, game_map_state
from app.models.partida import FasePartida
from app.schemas.estado_juego import TerritorioBase


class EstadoDummy:
    def __init__(self, turno="j1", fase=FasePartida.FORTIFICACION):
        self.user_turno_actual = turno
        self.fase_actual = fase


def _get_vecinas():
    comarcas = list(game_map_state.comarcas.keys())
    for a in comarcas:
        for b in comarcas:
            if a != b and map_calculator.son_vecinas(a, b):
                return a, b
    raise RuntimeError("No se encontró par de comarcas colindantes en el mapa")


def _get_no_vecinas():
    comarcas = list(game_map_state.comarcas.keys())
    for a in comarcas:
        for b in comarcas:
            if a != b and not map_calculator.son_vecinas(a, b):
                return a, b
    raise RuntimeError("No se encontró par de comarcas no colindantes en el mapa")


# ---------------------------------------------------------------------------
# resolver_fortificacion
# ---------------------------------------------------------------------------

def test_resolver_fortificacion_mueve_tropas_correctamente():
    mapa = {
        "A": {"owner_id": "j1", "units": 5},
        "B": {"owner_id": "j1", "units": 2},
    }
    resolver_fortificacion(mapa, "A", "B", 3)
    assert mapa["A"]["units"] == 2
    assert mapa["B"]["units"] == 5


def test_resolver_fortificacion_no_toca_otros_territorios():
    mapa = {
        "A": {"owner_id": "j1", "units": 5},
        "B": {"owner_id": "j1", "units": 2},
        "C": {"owner_id": "j2", "units": 4},
    }
    resolver_fortificacion(mapa, "A", "B", 2)
    assert mapa["C"]["units"] == 4


def test_resolver_fortificacion_mover_una_tropa():
    mapa = {
        "A": {"owner_id": "j1", "units": 3},
        "B": {"owner_id": "j1", "units": 1},
    }
    resolver_fortificacion(mapa, "A", "B", 1)
    assert mapa["A"]["units"] == 2
    assert mapa["B"]["units"] == 2


# ---------------------------------------------------------------------------
# validar_fortificacion — casos válidos
# ---------------------------------------------------------------------------

def test_validar_fortificacion_ok():
    origen_id, destino_id = _get_vecinas()
    t_origen = TerritorioBase(owner_id="j1", units=4)
    t_destino = TerritorioBase(owner_id="j1", units=1)
    resultado = validar_fortificacion(
        EstadoDummy(), "j1", origen_id, t_origen, destino_id, t_destino, 2, map_calculator
    )
    assert resultado is True


# ---------------------------------------------------------------------------
# validar_fortificacion — turno y fase
# ---------------------------------------------------------------------------

def test_validar_fortificacion_no_es_turno():
    origen_id, destino_id = _get_vecinas()
    t_origen = TerritorioBase(owner_id="j2", units=3)
    t_destino = TerritorioBase(owner_id="j2", units=2)
    with pytest.raises(ValueError, match="turno"):
        validar_fortificacion(
            EstadoDummy(turno="j1"), "j2", origen_id, t_origen, destino_id, t_destino, 1, map_calculator
        )


def test_validar_fortificacion_fase_incorrecta():
    origen_id, destino_id = _get_vecinas()
    t_origen = TerritorioBase(owner_id="j1", units=3)
    t_destino = TerritorioBase(owner_id="j1", units=2)
    with pytest.raises(ValueError, match="fase"):
        validar_fortificacion(
            EstadoDummy(fase=FasePartida.ATAQUE_CONVENCIONAL),
            "j1", origen_id, t_origen, destino_id, t_destino, 1, map_calculator
        )


# ---------------------------------------------------------------------------
# validar_fortificacion — propiedad de territorios
# ---------------------------------------------------------------------------

def test_validar_fortificacion_origen_no_propio():
    origen_id, destino_id = _get_vecinas()
    t_origen = TerritorioBase(owner_id="enemigo", units=3)
    t_destino = TerritorioBase(owner_id="j1", units=2)
    with pytest.raises(ValueError, match="origen"):
        validar_fortificacion(
            EstadoDummy(), "j1", origen_id, t_origen, destino_id, t_destino, 1, map_calculator
        )


def test_validar_fortificacion_destino_no_propio():
    origen_id, destino_id = _get_vecinas()
    t_origen = TerritorioBase(owner_id="j1", units=3)
    t_destino = TerritorioBase(owner_id="enemigo", units=2)
    with pytest.raises(ValueError, match="destino"):
        validar_fortificacion(
            EstadoDummy(), "j1", origen_id, t_origen, destino_id, t_destino, 1, map_calculator
        )


# ---------------------------------------------------------------------------
# validar_fortificacion — adyacencia
# ---------------------------------------------------------------------------

def test_validar_fortificacion_territorios_no_colindantes():
    origen_id, destino_id = _get_no_vecinas()
    t_origen = TerritorioBase(owner_id="j1", units=3)
    t_destino = TerritorioBase(owner_id="j1", units=2)
    with pytest.raises(ValueError, match="conectados"):
        validar_fortificacion(
            EstadoDummy(), "j1", origen_id, t_origen, destino_id, t_destino, 1, map_calculator
        )


# ---------------------------------------------------------------------------
# validar_fortificacion — cantidad de tropas
# ---------------------------------------------------------------------------

def test_validar_fortificacion_deja_origen_sin_tropas():
    origen_id, destino_id = _get_vecinas()
    t_origen = TerritorioBase(owner_id="j1", units=3)
    t_destino = TerritorioBase(owner_id="j1", units=1)
    with pytest.raises(ValueError, match="1 tropa"):
        validar_fortificacion(
            EstadoDummy(), "j1", origen_id, t_origen, destino_id, t_destino, 3, map_calculator
        )


def test_validar_fortificacion_tropas_superiores_a_las_disponibles():
    origen_id, destino_id = _get_vecinas()
    t_origen = TerritorioBase(owner_id="j1", units=2)
    t_destino = TerritorioBase(owner_id="j1", units=1)
    with pytest.raises(ValueError, match="suficientes tropas"):
        validar_fortificacion(
            EstadoDummy(), "j1", origen_id, t_origen, destino_id, t_destino, 10, map_calculator
        )


def test_validar_fortificacion_tropas_cero():
    origen_id, destino_id = _get_vecinas()
    t_origen = TerritorioBase(owner_id="j1", units=3)
    t_destino = TerritorioBase(owner_id="j1", units=1)
    with pytest.raises(ValueError, match="al menos una tropa"):
        validar_fortificacion(
            EstadoDummy(), "j1", origen_id, t_origen, destino_id, t_destino, 0, map_calculator
        )
