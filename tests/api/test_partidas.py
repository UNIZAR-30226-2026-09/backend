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
    assert res_unirse.json()["usuario_id"] == "invitado"
    
    # 6. EL INVITADO INTENTA UNIRSE OTRA VEZ (Debe fallar con 400)
    res_doble_union = client.post(
        f"/api/v1/partidas/{codigo_invitacion}/unirse", 
        headers=headers_invitado
    )
    assert res_doble_union.status_code == 400
    assert "Ya estás dentro" in res_doble_union.json()["detail"]