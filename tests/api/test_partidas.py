def test_flujo_completo_partida(client):
    # 1. CREAMOS AL CREADOR (Jugador 1)
    res_reg_1 = client.post("/api/v1/usuarios/registro", json={
        "username": "creador", "email": "creador@test.com", "password": "password_segura_123"
    })
    assert res_reg_1.status_code == 200, f"Error en registro creador: {res_reg_1.json()}"
    
    # 2. LOGUEAMOS AL CREADOR
    res_login_1 = client.post("/api/v1/usuarios/login", data={
        "username": "creador", "password": "password_segura_123"
    })
    assert res_login_1.status_code == 200, f"Error en login creador: {res_login_1.json()}"
    
    token_creador = res_login_1.json()["access_token"]
    headers_creador = {"Authorization": f"Bearer {token_creador}"}

    # 3. EL CREADOR CREA LA PARTIDA
    res_crear = client.post("/api/v1/partidas", json={
        "config_max_players": 3,
        "config_visibility": "publica",
        "config_timer_seconds": 60
    }, headers=headers_creador)
    
    assert res_crear.status_code == 200, f"Error al crear partida: {res_crear.json()}"
    partida_data = res_crear.json()
    codigo_invitacion = partida_data["codigo_invitacion"]
    assert len(codigo_invitacion) == 6

    # 4. CREAMOS Y LOGUEAMOS AL INVITADO (Jugador 2)
    res_reg_2 = client.post("/api/v1/usuarios/registro", json={
        "username": "invitado", "email": "invitado@test.com", "password": "password_segura_123"
    })
    assert res_reg_2.status_code == 200, f"Error en registro invitado: {res_reg_2.json()}"
    
    res_login_2 = client.post("/api/v1/usuarios/login", data={
        "username": "invitado", "password": "password_segura_123"
    })
    assert res_login_2.status_code == 200, f"Error en login invitado: {res_login_2.json()}"
    
    token_invitado = res_login_2.json()["access_token"]
    headers_invitado = {"Authorization": f"Bearer {token_invitado}"}

    # 5. EL INVITADO SE UNE A LA PARTIDA CON EL CÓDIGO
    res_unirse = client.post(
        f"/api/v1/partidas/{codigo_invitacion}/unirse", 
        headers=headers_invitado
    )
    assert res_unirse.status_code == 200, f"Error al unirse a la partida: {res_unirse.json()}"
    body = res_unirse.json()
    assert body["mensaje"] == "Unido a la partida"
    usernames = [j["usuario_id"] for j in body["jugadores_en_sala"]]
    assert "invitado" in usernames
    assert "creador" in usernames
    assert any(j["usuario_id"] == "invitado" for j in body["jugadores_en_sala"])
    
    # 6. EL INVITADO INTENTA UNIRSE OTRA VEZ (Debe fallar con 400)
    res_doble_union = client.post(
        f"/api/v1/partidas/{codigo_invitacion}/unirse",
        headers=headers_invitado
    )
    assert res_doble_union.status_code == 400
    assert "Ya estás dentro" in res_doble_union.json()["detail"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _registrar_y_login(client, username: str) -> dict:
    client.post("/api/v1/usuarios/registro", json={
        "username": username,
        "email": f"{username}@test.com",
        "password": "password_segura_123"
    })
    res = client.post("/api/v1/usuarios/login", data={
        "username": username, "password": "password_segura_123"
    })
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def _crear_partida(client, headers: dict) -> dict:
    res = client.post("/api/v1/partidas", json={
        "config_max_players": 3, "config_visibility": "publica", "config_timer_seconds": 60
    }, headers=headers)
    assert res.status_code == 200
    return res.json()  # contiene id y codigo_invitacion


# ---------------------------------------------------------------------------
# Tests: restricción de partida activa
# ---------------------------------------------------------------------------

def test_no_puede_unirse_si_ya_esta_en_otra_partida(client):
    headers_c1 = _registrar_y_login(client, "creador1")
    headers_c2 = _registrar_y_login(client, "creador2")
    headers_inv = _registrar_y_login(client, "invitado")

    partida1 = _crear_partida(client, headers_c1)
    partida2 = _crear_partida(client, headers_c2)

    # Invitado se une a la primera partida
    res1 = client.post(f"/api/v1/partidas/{partida1['codigo_invitacion']}/unirse", headers=headers_inv)
    assert res1.status_code == 200

    # Intenta unirse a la segunda → debe fallar
    res2 = client.post(f"/api/v1/partidas/{partida2['codigo_invitacion']}/unirse", headers=headers_inv)
    assert res2.status_code == 400
    assert "otra partida" in res2.json()["detail"].lower()


def test_puede_unirse_tras_abandonar_partida_anterior(client):
    headers_c1 = _registrar_y_login(client, "creador1")
    headers_c2 = _registrar_y_login(client, "creador2")
    headers_inv = _registrar_y_login(client, "invitado")

    partida1 = _crear_partida(client, headers_c1)
    partida2 = _crear_partida(client, headers_c2)

    # Invitado se une a la primera
    res1 = client.post(f"/api/v1/partidas/{partida1['codigo_invitacion']}/unirse", headers=headers_inv)
    assert res1.status_code == 200

    # Abandona la primera
    res_aban = client.post(f"/api/v1/partidas/{partida1['id']}/abandonar", headers=headers_inv)
    assert res_aban.status_code == 200

    # Ahora puede unirse a la segunda
    res2 = client.post(f"/api/v1/partidas/{partida2['codigo_invitacion']}/unirse", headers=headers_inv)
    assert res2.status_code == 200


# ---------------------------------------------------------------------------
# Helpers para tests de inicio de partida
# ---------------------------------------------------------------------------

def _empezar_partida(client, partida_id: int, headers_creador: dict) -> dict:
    res = client.post(f"/api/v1/partidas/{partida_id}/empezar", headers=headers_creador)
    assert res.status_code == 200, res.json()
    return res.json()


def _ver_estado(client, partida_id: int) -> dict:
    res = client.get(f"/api/v1/partidas/{partida_id}/estado")
    assert res.status_code == 200
    return res.json()


# ---------------------------------------------------------------------------
# Tests: numero_jugador y orden de turno aleatorio
# ---------------------------------------------------------------------------

def test_primer_turno_corresponde_a_jugador_con_numero_1(client, monkeypatch):
    async def mock_enviar_cambio_fase(*args, **kwargs): pass
    monkeypatch.setattr("app.core.notifier.notifier.enviar_cambio_fase", mock_enviar_cambio_fase)

    headers_c = _registrar_y_login(client, "creador")
    headers_j2 = _registrar_y_login(client, "jugador2")

    partida = _crear_partida(client, headers_c)
    client.post(f"/api/v1/partidas/{partida['codigo_invitacion']}/unirse", headers=headers_j2)

    inicio = _empezar_partida(client, partida["id"], headers_c)
    estado = _ver_estado(client, partida["id"])

    turno_de = inicio["turno_de"]
    jugadores = estado["jugadores"]

    # El jugador con turno actual debe ser el que tiene numero_jugador == 1
    assert jugadores[turno_de]["numero_jugador"] == 1


def test_numeros_jugador_son_unicos_y_en_rango(client, monkeypatch):
    async def mock_enviar_cambio_fase(*args, **kwargs): pass
    monkeypatch.setattr("app.core.notifier.notifier.enviar_cambio_fase", mock_enviar_cambio_fase)

    headers_c = _registrar_y_login(client, "creador")
    headers_j2 = _registrar_y_login(client, "jugador2")
    headers_j3 = _registrar_y_login(client, "jugador3")

    partida = _crear_partida(client, headers_c)
    client.post(f"/api/v1/partidas/{partida['codigo_invitacion']}/unirse", headers=headers_j2)
    client.post(f"/api/v1/partidas/{partida['codigo_invitacion']}/unirse", headers=headers_j3)

    _empezar_partida(client, partida["id"], headers_c)
    estado = _ver_estado(client, partida["id"])

    numeros = [v["numero_jugador"] for v in estado["jugadores"].values()]
    assert sorted(numeros) == list(range(1, len(numeros) + 1))


def test_jugador_1_recibe_tropas_al_empezar(client, monkeypatch):
    async def mock_enviar_cambio_fase(*args, **kwargs): pass
    monkeypatch.setattr("app.core.notifier.notifier.enviar_cambio_fase", mock_enviar_cambio_fase)

    headers_c = _registrar_y_login(client, "creador")
    headers_j2 = _registrar_y_login(client, "jugador2")

    partida = _crear_partida(client, headers_c)
    client.post(f"/api/v1/partidas/{partida['codigo_invitacion']}/unirse", headers=headers_j2)

    # Al empezar, el backend debe calcular y asignar tropas al Turno 1
    inicio = _empezar_partida(client, partida["id"], headers_c)
    estado = _ver_estado(client, partida["id"])

    turno_de = inicio["turno_de"]
    jugadores = estado["jugadores"]

    # Verificamos que el jugador que tiene el turno NO tenga 0 tropas
    # (Como mínimo debería tener 3 según la regla de territorios/3)
    assert jugadores[turno_de]["tropas_reserva"] >= 3