from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.core.ws_manager import manager
from app.api.v1.endpoints import combates as combates_endpoint
from app.models.usuario import User
from app.schemas.combate import AtaqueCreate


def _assert_tipo_evento(payload: dict, expected: str):
    tipo = payload.get("tipo_evento")
    if tipo is None:
        return False
    return tipo.lower() == expected.lower()


@pytest.fixture(autouse=True)
def reset_manager():
    manager.active_connections = {}
    yield
    manager.active_connections = {}


def test_empezar_partida_emite_partida_iniciada(client, monkeypatch):
    from app.api.v1.endpoints import partidas as partidas_endpoint

    async def fake_timer(*args, **kwargs):
        return None

    monkeypatch.setattr(partidas_endpoint, "iniciar_temporizador", fake_timer)

    broadcast_payloads = []

    async def spy_broadcast(message, id_partida):
        if _assert_tipo_evento(message, "PARTIDA_INICIADA"):
            broadcast_payloads.append((message, id_partida))

    monkeypatch.setattr(manager, "broadcast", spy_broadcast)

    async def mock_enviar_cambio_fase(*args, **kwargs):
        pass

    monkeypatch.setattr("app.core.notifier.notifier.enviar_cambio_fase", mock_enviar_cambio_fase)

    # 1. Registro y login creador
    res_reg_1 = client.post("/api/v1/usuarios/registro", json={
        "username": "creador_ws", "email": "creador_ws@test.com", "password": "password_segura_123"
    })
    assert res_reg_1.status_code == 200
    res_login_1 = client.post("/api/v1/usuarios/login", data={
        "username": "creador_ws", "password": "password_segura_123"
    })
    assert res_login_1.status_code == 200
    token_creador = res_login_1.json()["access_token"]
    headers_creador = {"Authorization": f"Bearer {token_creador}"}

    # 2. Crear partida
    res_crear = client.post("/api/v1/partidas", json={
        "config_max_players": 3,
        "config_visibility": "publica",
        "config_timer_seconds": 60
    }, headers=headers_creador)
    assert res_crear.status_code == 200
    partida_id = res_crear.json()["id"]
    codigo_invitacion = res_crear.json()["codigo_invitacion"]

    # 3. Registro y login invitado
    res_reg_2 = client.post("/api/v1/usuarios/registro", json={
        "username": "invitado_ws", "email": "invitado_ws@test.com", "password": "password_segura_123"
    })
    assert res_reg_2.status_code == 200
    res_login_2 = client.post("/api/v1/usuarios/login", data={
        "username": "invitado_ws", "password": "password_segura_123"
    })
    assert res_login_2.status_code == 200
    token_invitado = res_login_2.json()["access_token"]
    headers_invitado = {"Authorization": f"Bearer {token_invitado}"}

    # 4. Invitado se une
    res_unirse = client.post(f"/api/v1/partidas/{codigo_invitacion}/unirse", headers=headers_invitado)
    assert res_unirse.status_code == 200

    # 5. Empezar partida
    res_empezar = client.post(f"/api/v1/partidas/{partida_id}/empezar", headers=headers_creador)
    assert res_empezar.status_code == 200
    body = res_empezar.json()
    assert body["partida_id"] == partida_id
    assert body["turno_de"] in ["creador_ws", "invitado_ws"]
    assert body["fase"] == "refuerzo"

    # 6. Verificamos broadcast correcto
    assert broadcast_payloads
    payload, pid = broadcast_payloads[0]
    assert pid == partida_id
    assert payload["tipo_evento"] == "PARTIDA_INICIADA"
    assert payload["turno_de"] in ["creador_ws", "invitado_ws"]
    assert payload["fase_actual"] == "refuerzo"
    assert "mapa" in payload and "jugadores" in payload and "fin_fase_utc" in payload


def test_unirse_partida_emite_nuevo_jugador(client, monkeypatch):
    broadcast_payloads = []

    async def spy_broadcast(message, id_partida):
        if _assert_tipo_evento(message, "NUEVO_JUGADOR"):
            broadcast_payloads.append((message, id_partida))

    monkeypatch.setattr(manager, "broadcast", spy_broadcast)

    # 1. Registro y login creador
    res_reg_1 = client.post("/api/v1/usuarios/registro", json={
        "username": "creador_nuevo", "email": "creador_nuevo@test.com", "password": "password_segura_123"
    })
    assert res_reg_1.status_code == 200
    res_login_1 = client.post("/api/v1/usuarios/login", data={
        "username": "creador_nuevo", "password": "password_segura_123"
    })
    assert res_login_1.status_code == 200
    token_creador = res_login_1.json()["access_token"]
    headers_creador = {"Authorization": f"Bearer {token_creador}"}

    # 2. Crear partida
    res_crear = client.post("/api/v1/partidas", json={
        "config_max_players": 3,
        "config_visibility": "publica",
        "config_timer_seconds": 60
    }, headers=headers_creador)
    assert res_crear.status_code == 200
    codigo_invitacion = res_crear.json()["codigo_invitacion"]
    partida_id = res_crear.json()["id"]

    # 3. Registro y login invitado
    res_reg_2 = client.post("/api/v1/usuarios/registro", json={
        "username": "invitado_nuevo", "email": "invitado_nuevo@test.com", "password": "password_segura_123"
    })
    assert res_reg_2.status_code == 200
    res_login_2 = client.post("/api/v1/usuarios/login", data={
        "username": "invitado_nuevo", "password": "password_segura_123"
    })
    assert res_login_2.status_code == 200
    token_invitado = res_login_2.json()["access_token"]
    headers_invitado = {"Authorization": f"Bearer {token_invitado}"}

    # 4. Invitado se une
    res_unirse = client.post(f"/api/v1/partidas/{codigo_invitacion}/unirse", headers=headers_invitado)
    assert res_unirse.status_code == 200

    # 5. Verificamos broadcast correcto
    assert broadcast_payloads
    payload, pid = broadcast_payloads[0]
    assert pid == partida_id
    assert payload["tipo_evento"] == "NUEVO_JUGADOR"
    assert payload["jugador"] == "invitado_nuevo"
    assert payload["jugador"] == "invitado_nuevo"


@pytest.mark.asyncio
async def test_http_ataque_emite_ws(monkeypatch):
    from app.models.partida import FasePartida
    async def fake_obtener_estado_partida(db, partida_id):
        class Estado:
            mapa = {
                "A": {"owner_id": "p1", "units": 5},
                "B": {"owner_id": "p2", "units": 2},
            }
            jugadores = {"p1": {"tropas_reserva": 0, "movimiento_conquista_pendiente": False}}
            fase_actual = FasePartida.ATAQUE_CONVENCIONAL
            turno_actual = 1
        return Estado()

    async def fake_guardar_estado_partida(db, estado_partida):
        return None

    def fake_validar(*args, **kwargs):
        return None

    def fake_resolver_ataque_completo(*args, **kwargs):
        from app.schemas.combate import ResultadoAtaqueCompleto
        return ResultadoAtaqueCompleto(
            victoria_atacante=False,
            bajas_atacante=1,
            bajas_defensor=0,
            tropas_restantes_origen=4,
            tropas_restantes_defensor=2,
        )

    broadcast_payloads = []

    async def spy_broadcast(message, id_partida):
        if _assert_tipo_evento(message, "ATAQUE_RESULTADO"):
            broadcast_payloads.append((message, id_partida))

    async def fake_registrar_log(*args, **kwargs):
        return None

    monkeypatch.setattr(combates_endpoint, "obtener_estado_partida", fake_obtener_estado_partida)
    monkeypatch.setattr(combates_endpoint.crud_combates, "guardar_estado_partida", fake_guardar_estado_partida)
    monkeypatch.setattr(combates_endpoint, "registrar_log", fake_registrar_log)
    monkeypatch.setattr(combates_endpoint, "validar_ataque_convencional", fake_validar)
    monkeypatch.setattr(combates_endpoint, "resolver_ataque_completo", fake_resolver_ataque_completo)
    monkeypatch.setattr(manager, "broadcast", spy_broadcast)

    usuario = User(username="p1", email="p1@example.com", passwd_hash="x")
    ataque = AtaqueCreate(territorio_origen_id="A", territorio_destino_id="B")

    await combates_endpoint.ejecutar_ataque(
        partida_id=1,
        ataque_in=ataque,
        usuario_actual=usuario,
        db=object(),
    )

    assert broadcast_payloads
    payload, pid = broadcast_payloads[0]
    assert pid == 1
    assert _assert_tipo_evento(payload, "ATAQUE_RESULTADO")
    assert payload["origen"] == "A"
    assert payload["destino"] == "B"


@pytest.mark.asyncio
async def test_http_mover_conquista_emite_ws(monkeypatch):
    async def fake_obtener_estado_partida(db, partida_id):
        class Estado:
            turno_actual = 1
            fase_actual = type("Fase", (), {"value": "ataque_convencional"})()
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
    monkeypatch.setattr(combates_endpoint, "registrar_log", AsyncMock())
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
    payload, pid = broadcast_payloads[0]
    assert pid == 1
    assert _assert_tipo_evento(payload, "MOVIMIENTO_CONQUISTA")
    assert payload["origen"] == "A"
    assert payload["destino"] == "B"
    assert payload["tropas"] == 2
    assert payload["jugador"] == "p1"


@pytest.mark.asyncio
async def test_http_colocar_tropas_emite_ws(monkeypatch):
    async def fake_obtener_estado_partida(db, partida_id):
        class Estado:
            turno_actual = 1
            fase_actual = type("Fase", (), {"value": "refuerzo"})()
            mapa = {"A": {"owner_id": "p1", "units": 1}}
            jugadores = {"p1": {"tropas_reserva": 5}}
        return Estado()

    async def fake_guardar_estado_partida(db, estado_partida):
        return None

    def fake_validar_colocacion_tropas(*args, **kwargs):
        return None

    async def fake_resolver_colocacion_tropas(jugador_estado, t_destino, tropas, **kwargs):
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
    monkeypatch.setattr(combates_endpoint, "registrar_log", AsyncMock())
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
    payload, pid = broadcast_payloads[0]
    assert pid == 1
    assert _assert_tipo_evento(payload, "TROPAS_COLOCADAS")
    assert payload["jugador"] == "p1"
    assert payload["territorio"] == "A"
    assert payload["tropas_añadidas"] == 3
    assert payload["tropas_totales_ahora"] == 4
