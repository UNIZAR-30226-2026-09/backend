import pytest
from unittest.mock import patch, MagicMock
from app.core.logica_juego.config_ataques_especiales import TipoAtaque
from app.api.deps import obtener_usuario_actual
from app.models.partida import FasePartida
from app.main import app

@pytest.fixture
def mock_user():
    user = MagicMock()
    user.username = "testuser"
    return user

def test_ejecutar_ataque_especial_exito(client, mock_user):
    # Sobrescribimos el usuario actual
    app.dependency_overrides[obtener_usuario_actual] = lambda: mock_user

    mock_estado = MagicMock()
    mock_estado.user_turno_actual = "testuser"
    mock_estado.turno_actual = 1
    mock_estado.fase_actual = FasePartida.ATAQUE_ESPECIAL
    mock_estado.jugadores = {
        "testuser": {
            "tecnologias_compradas": [TipoAtaque.MORTERO_TACTICO]
        }
    }
    mock_estado.mapa = {}

    try:
        with patch("app.api.v1.endpoints.combates.obtener_estado_partida", return_value=mock_estado), \
             patch("app.api.v1.endpoints.combates.REGISTRO_ATAQUES", {TipoAtaque.MORTERO_TACTICO: MagicMock()}), \
             patch("app.api.v1.endpoints.combates.crud_combates.guardar_estado_partida"), \
             patch("app.api.v1.endpoints.combates.registrar_log"), \
             patch("app.api.v1.endpoints.combates.notifier.enviar_ataque_especial") as mock_notify:

            payload = {
                "tipo_ataque": TipoAtaque.MORTERO_TACTICO,
                "origen": "T1",
                "destino": "T2"
            }
            response = client.post(
                "/api/v1/partidas/1/ataque_especial",
                json=payload
            )

            assert response.status_code == 200
            assert "con éxito" in response.json()["mensaje"]
            mock_notify.assert_called_once()
    finally:
        app.dependency_overrides.pop(obtener_usuario_actual, None)

def test_ejecutar_ataque_especial_sin_tecnologia(client, mock_user):
    app.dependency_overrides[obtener_usuario_actual] = lambda: mock_user

    mock_estado = MagicMock()
    mock_estado.user_turno_actual = "testuser"
    mock_estado.jugadores = {
        "testuser": {"tecnologias_compradas": []}
    }

    try:
        with patch("app.api.v1.endpoints.combates.obtener_estado_partida", return_value=mock_estado):
            payload = {
                "tipo_ataque": TipoAtaque.MORTERO_TACTICO,
                "origen": "T1",
                "destino": "T2"
            }
            response = client.post(
                "/api/v1/partidas/1/ataque_especial",
                json=payload
            )

            assert response.status_code == 400
            assert "No has desarrollado la tecnología" in response.json()["detail"]
    finally:
        app.dependency_overrides.pop(obtener_usuario_actual, None)

def test_ejecutar_ataque_especial_fuera_de_turno(client, mock_user):
    app.dependency_overrides[obtener_usuario_actual] = lambda: mock_user

    mock_estado = MagicMock()
    mock_estado.user_turno_actual = "otro_jugador"

    try:
        with patch("app.api.v1.endpoints.combates.obtener_estado_partida", return_value=mock_estado):
            payload = {
                "tipo_ataque": TipoAtaque.MORTERO_TACTICO,
                "origen": "T1",
                "destino": "T2"
            }
            response = client.post(
                "/api/v1/partidas/1/ataque_especial",
                json=payload
            )

            assert response.status_code == 403
            assert "fuera de tu turno" in response.json()["detail"]
    finally:
        app.dependency_overrides.pop(obtener_usuario_actual, None)


def test_ejecutar_ataque_especial_ya_usado(client, mock_user):
    # Sobrescribimos el usuario actual
    app.dependency_overrides[obtener_usuario_actual] = lambda: mock_user

    mock_estado = MagicMock()
    mock_estado.user_turno_actual = "testuser"
    mock_estado.jugadores = {
        "testuser": {
            "tecnologias_compradas": [TipoAtaque.MORTERO_TACTICO],
            "ha_lanzado_especial": True 
        }
    }

    try:
        with patch("app.api.v1.endpoints.combates.obtener_estado_partida", return_value=mock_estado):
            payload = {
                "tipo_ataque": TipoAtaque.MORTERO_TACTICO,
                "origen": "T1",
                "destino": "T2"
            }
            response = client.post(
                "/api/v1/partidas/1/ataque_especial",
                json=payload
            )

            # Comprobamos que el servidor nos para los pies
            assert response.status_code == 400
            assert "Solo puedes realizar un ataque especial por turno" in response.json()["detail"]
            
    finally:
        app.dependency_overrides.pop(obtener_usuario_actual, None)
