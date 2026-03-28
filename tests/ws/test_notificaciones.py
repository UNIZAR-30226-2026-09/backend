from datetime import datetime, timezone
import inspect

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.ws_manager import manager
from app.core.notifier import GameNotifier
from app.api.v1.endpoints import combates as combates_endpoint
from app.core.logica_juego import maquina_estados
from app.core.logica_juego.maquina_estados import avanzar_fase
from app.models.partida import Partida, EstadoPartida, EstadosPartida, FasePartida, TipoVisibilidad
from app.models.usuario import User


class DummyFase:
    def __init__(self, value: str):
        self.value = value


class DummyEstado:
    def __init__(self):
        self.mapa = {"Huesca": {"owner_id": "jugador_1", "units": 3}}
        self.jugadores = {"jugador_1": {"tropas_reserva": 0}}
        self.user_turno_actual = "jugador_1"
        self.fase_actual = DummyFase("refuerzo")
        self.fin_fase_actual = datetime(2026, 3, 22, 15, 30, tzinfo=timezone.utc)


class DummySession:
    async def __aenter__(self):
        return object()

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.fixture(autouse=True)
def reset_manager():
    manager.active_connections = {}
    yield
    manager.active_connections = {}


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def patch_ws_db(monkeypatch):
    from app.api.v1.endpoints import websockets as ws_endpoint

    monkeypatch.setattr(ws_endpoint, "AsyncSessionLocal", lambda: DummySession())
    return ws_endpoint


def _assert_tipo_evento(payload: dict, expected: str):
    tipo = payload.get("tipo_evento")
    if tipo is None:
        return False
    return tipo.lower() == expected.lower()


def test_conexion_envia_actualizacion_mapa_si_existe_estado(client, patch_ws_db, monkeypatch):
    async def fake_obtener_estado_partida(db, id_partida):
        return DummyEstado()

    monkeypatch.setattr(patch_ws_db, "obtener_estado_partida", fake_obtener_estado_partida)

    with client.websocket_connect("/api/v1/ws/1/alice") as websocket:
        msg = websocket.receive_json()

    assert _assert_tipo_evento(msg, "ACTUALIZACION_MAPA")
    assert msg["mapa"]["Huesca"]["units"] == 3
    assert msg["turno_de"] == "jugador_1"
    assert msg["fase_actual"] == "refuerzo"
    assert msg["fin_fase_utc"] == "2026-03-22T15:30:00+00:00"


def test_conexion_sin_estado_no_envia_mapa(client, patch_ws_db, monkeypatch):
    async def fake_obtener_estado_partida(db, id_partida):
        return None

    monkeypatch.setattr(patch_ws_db, "obtener_estado_partida", fake_obtener_estado_partida)

    sent_messages = []

    async def spy_send_personal_message(message, id_partida, username):
        sent_messages.append((message, id_partida, username))

    monkeypatch.setattr(manager, "send_personal_message", spy_send_personal_message)

    with client.websocket_connect("/api/v1/ws/1/alice") as websocket:
        websocket.close()

    assert sent_messages == []


def test_chat_broadcast_a_otros_clientes(client, patch_ws_db, monkeypatch):
    async def fake_obtener_estado_partida(db, id_partida):
        return None

    monkeypatch.setattr(patch_ws_db, "obtener_estado_partida", fake_obtener_estado_partida)

    with client.websocket_connect("/api/v1/ws/10/a") as ws_a:
        with client.websocket_connect("/api/v1/ws/10/b") as ws_b:
            ws_a.send_json({"accion": "CHAT", "mensaje": "hola"})
            msg = ws_b.receive_json()

    assert _assert_tipo_evento(msg, "CHAT")
    assert msg["emisor"] == "a"
    assert msg["mensaje"] == "hola"


def test_json_malformado_devuelve_error_unicast(client, patch_ws_db, monkeypatch):
    async def fake_obtener_estado_partida(db, id_partida):
        return None

    monkeypatch.setattr(patch_ws_db, "obtener_estado_partida", fake_obtener_estado_partida)

    with client.websocket_connect("/api/v1/ws/99/a") as ws_a:
        ws_a.send_json({"mensaje": "falta accion"})
        msg = ws_a.receive_json()

    assert ("error" in msg) or _assert_tipo_evento(msg, "ERROR")
    assert "accion" in msg.get("error", msg.get("mensaje", "")).lower()


def test_accion_desconocida_no_hace_broadcast(client, patch_ws_db, monkeypatch):
    async def fake_obtener_estado_partida(db, id_partida):
        return None

    monkeypatch.setattr(patch_ws_db, "obtener_estado_partida", fake_obtener_estado_partida)

    broadcast_calls = []
    personal_calls = []

    async def spy_broadcast(message, id_partida):
        if _assert_tipo_evento(message, "DESCONEXION"):
            return
        broadcast_calls.append((message, id_partida))

    async def spy_personal(message, id_partida, username):
        personal_calls.append((message, id_partida, username))

    monkeypatch.setattr(manager, "broadcast", spy_broadcast)
    monkeypatch.setattr(manager, "send_personal_message", spy_personal)

    with client.websocket_connect("/api/v1/ws/7/a") as ws_a:
        ws_a.send_json({"accion": "ACCION_INVENTADA"})

    assert broadcast_calls == []
    assert personal_calls == []


def test_desconexion_emite_evento_a_los_demas(client, patch_ws_db, monkeypatch):
    async def fake_obtener_estado_partida(db, id_partida):
        return None

    monkeypatch.setattr(patch_ws_db, "obtener_estado_partida", fake_obtener_estado_partida)

    with client.websocket_connect("/api/v1/ws/55/a") as ws_a:
        with client.websocket_connect("/api/v1/ws/55/b") as ws_b:
            ws_a.close()
            msg = ws_b.receive_json()

    assert _assert_tipo_evento(msg, "DESCONEXION")
    assert msg["jugador"] == "a"


def test_aislamiento_partidas_no_filtra_mensajes(client, patch_ws_db, monkeypatch):
    async def fake_obtener_estado_partida(db, id_partida):
        return None

    monkeypatch.setattr(patch_ws_db, "obtener_estado_partida", fake_obtener_estado_partida)

    broadcast_ids = []
    original_broadcast = manager.broadcast

    async def spy_broadcast(message, id_partida):
        if _assert_tipo_evento(message, "CHAT"):
            broadcast_ids.append(id_partida)
        await original_broadcast(message, id_partida)

    monkeypatch.setattr(manager, "broadcast", spy_broadcast)
    # El handler usa notifier, pero el broadcast sale por manager

    with client.websocket_connect("/api/v1/ws/1/a") as ws_a:
        with client.websocket_connect("/api/v1/ws/2/b") as ws_b:
            ws_a.send_json({"accion": "CHAT", "mensaje": "solo partida 1"})

            timeout_supported = "timeout" in inspect.signature(ws_b.receive_json).parameters
            if timeout_supported:
                with pytest.raises(TimeoutError):
                    ws_b.receive_json(timeout=0.1)
            # Fallback: si no hay timeout, validamos por el id_partida del broadcast

    assert broadcast_ids
    assert all(str(pid) == "1" for pid in broadcast_ids)


@pytest.mark.asyncio
async def test_evento_ataque_resultado_broadcast(monkeypatch):
    broadcast_payloads = []

    async def spy_broadcast(message, id_partida):
        if _assert_tipo_evento(message, "ATAQUE_RESULTADO"):
            broadcast_payloads.append((message, id_partida))

    monkeypatch.setattr(manager, "broadcast", spy_broadcast)

    class DummyResultado:
        dados_atacante = [6, 4, 2]
        dados_defensor = [5, 1]
        bajas_atacante = 0
        bajas_defensor = 2
        victoria_atacante = True

    from app.core.notifier import notifier
    await notifier.enviar_resultado_ataque(1, "Huesca", "Barbastro", DummyResultado())

    assert broadcast_payloads
    payload, partida_id = broadcast_payloads[0]
    assert partida_id == 1
    assert _assert_tipo_evento(payload, "ATAQUE_RESULTADO")
    assert payload["origen"] == "Huesca"
    assert payload["destino"] == "Barbastro"


@pytest.mark.asyncio
async def test_evento_movimiento_conquista_broadcast(monkeypatch):
    async def fake_obtener_estado_partida(db, partida_id):
        class Estado:
            mapa = {
                "A": {"owner_id": "p1", "units": 5},
                "B": {"owner_id": "p1", "units": 1},
            }
            jugadores = {
                "p1": {
                    "tropas_reserva": 0,
                    "movimiento_conquista_pendiente": True,
                    "origen_conquista": "A",
                    "destino_conquista": "B",
                }
            }
        return Estado()

    async def fake_guardar_estado_partida(db, estado_partida):
        return None

    broadcast_payloads = []

    async def spy_broadcast(message, id_partida):
        if _assert_tipo_evento(message, "MOVIMIENTO_CONQUISTA"):
            broadcast_payloads.append((message, id_partida))

    monkeypatch.setattr(combates_endpoint, "obtener_estado_partida", fake_obtener_estado_partida)
    monkeypatch.setattr(combates_endpoint.crud_combates, "guardar_estado_partida", fake_guardar_estado_partida)
    monkeypatch.setattr(manager, "broadcast", spy_broadcast)

    usuario = User(username="p1", email="p1@example.com", passwd_hash="x")
    datos = combates_endpoint.MoverConquistaIn(tropas=2)

    await combates_endpoint.mover_tropas_conquista(
        partida_id=1,
        datos=datos,
        usuario_actual=usuario,
        db=object(),
    )

    assert broadcast_payloads
    payload, partida_id = broadcast_payloads[0]
    assert partida_id == 1
    assert _assert_tipo_evento(payload, "MOVIMIENTO_CONQUISTA")
    assert payload["origen"] == "A"
    assert payload["destino"] == "B"
    assert payload["tropas"] == 2
    assert payload["jugador"] == "p1"


@pytest.mark.asyncio
async def test_evento_tropas_colocadas_broadcast(monkeypatch):
    async def fake_obtener_estado_partida(db, partida_id):
        class Estado:
            mapa = {"A": {"owner_id": "p1", "units": 1}}
            jugadores = {"p1": {"tropas_reserva": 5}}
        return Estado()

    async def fake_guardar_estado_partida(db, estado_partida):
        return None

    def fake_validar_colocacion_tropas(*args, **kwargs):
        return None

    def fake_resolver_colocacion_tropas(jugador_estado, t_destino, tropas):
        jugador_estado.tropas_reserva -= tropas
        t_destino.units += tropas

    broadcast_payloads = []

    async def spy_broadcast(message, id_partida):
        if _assert_tipo_evento(message, "TROPAS_COLOCADAS"):
            broadcast_payloads.append((message, id_partida))

    monkeypatch.setattr(combates_endpoint, "obtener_estado_partida", fake_obtener_estado_partida)
    monkeypatch.setattr(combates_endpoint.crud_combates, "guardar_estado_partida", fake_guardar_estado_partida)
    monkeypatch.setattr(combates_endpoint, "validar_colocacion_tropas", fake_validar_colocacion_tropas)
    monkeypatch.setattr(combates_endpoint, "resolver_colocacion_tropas", fake_resolver_colocacion_tropas)
    monkeypatch.setattr(manager, "broadcast", spy_broadcast)

    usuario = User(username="p1", email="p1@example.com", passwd_hash="x")
    datos = combates_endpoint.ColocarTropasIn(territorio_id="A", tropas=3)

    await combates_endpoint.colocar_tropas_reserva(
        partida_id=1,
        datos=datos,
        usuario_actual=usuario,
        db=object(),
    )

    assert broadcast_payloads
    payload, partida_id = broadcast_payloads[0]
    assert partida_id == 1
    assert _assert_tipo_evento(payload, "TROPAS_COLOCADAS")
    assert payload["jugador"] == "p1"
    assert payload["territorio"] == "A"
    assert payload["tropas_añadidas"] == 3
    assert payload["tropas_totales_ahora"] == 4


@pytest.mark.asyncio
async def test_evento_cambio_fase_broadcast(db, monkeypatch):
    async def fake_timer(*args, **kwargs):
        return None

    monkeypatch.setattr(maquina_estados, "iniciar_temporizador", fake_timer)

    usuario = User(username="u1", email="u1@example.com", passwd_hash="x")
    partida = Partida(
        config_max_players=4,
        config_visibility=TipoVisibilidad.PUBLICA,
        config_timer_seconds=1,
        codigo_invitacion="ABC123",
        estado=EstadosPartida.ACTIVA,
        creador="u1",
    )
    db.add(usuario)
    db.add(partida)
    await db.commit()
    await db.refresh(partida)

    estado = EstadoPartida(
        partida_id=partida.id,
        fase_actual=FasePartida.REFUERZO,
        fin_fase_actual=datetime.now(timezone.utc),
        user_turno_actual="u1",
        mapa={},
        jugadores={},
    )
    db.add(estado)
    await db.commit()

    broadcast_payloads = []

    async def spy_broadcast(message, id_partida):
        if _assert_tipo_evento(message, "CAMBIO_FASE"):
            broadcast_payloads.append((message, id_partida))

    monkeypatch.setattr(manager, "broadcast", spy_broadcast)

    await avanzar_fase(partida.id, db, FasePartida.REFUERZO)

    assert broadcast_payloads
    payload, partida_id = broadcast_payloads[0]
    assert partida_id == partida.id
    assert _assert_tipo_evento(payload, "CAMBIO_FASE")
    assert payload["nueva_fase"] == FasePartida.ATAQUE_CONVENCIONAL.value
    assert payload["jugador_activo"] == "u1"
    assert "fin_fase_utc" in payload


@pytest.mark.asyncio
async def test_evento_partida_iniciada_broadcast(monkeypatch):
    broadcast_payloads = []

    async def spy_broadcast(message, id_partida):
        if _assert_tipo_evento(message, "PARTIDA_INICIADA"):
            broadcast_payloads.append((message, id_partida))

    monkeypatch.setattr(manager, "broadcast", spy_broadcast)

    await GameNotifier.enviar_inicio_partida(
        partida_id=3,
        mapa={"A": {"owner_id": "p1", "units": 1}},
        jugadores={"p1": {"tropas_reserva": 5}},
        turno_de="p1",
    )

    assert broadcast_payloads
    payload, partida_id = broadcast_payloads[0]
    assert partida_id == 3
    assert _assert_tipo_evento(payload, "PARTIDA_INICIADA")
    assert payload["turno_de"] == "p1"
