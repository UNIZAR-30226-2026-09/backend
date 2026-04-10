import pytest
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.partida import Partida, EstadoPartida, FasePartida, JugadoresPartida, EstadosPartida
from app.models.usuario import User
from app.core.logica_juego.maquina_estados import avanzar_fase, asignar_tropas_reserva

@pytest.mark.asyncio
async def test_asignar_tropas_reserva_minimo(db: AsyncSession):
    # Setup: 1 territorio (debe dar 3 tropas)
    mapa = {"T1": {"owner_id": "user1", "units": 1}}
    estado = EstadoPartida(
        partida_id=1,
        fase_actual=FasePartida.REFUERZO,
        fin_fase_actual=datetime.now(timezone.utc),
        user_turno_actual="user1",
        mapa=mapa,
        jugadores={}
    )
    
    await asignar_tropas_reserva(estado, db)

    assert estado.jugadores["user1"]["tropas_reserva"] == 3

@pytest.mark.asyncio
async def test_asignar_tropas_reserva_calculo(db: AsyncSession):
    # Setup: 12 territorios (12 / 3 = 4 tropas)
    mapa = {f"T{i}": {"owner_id": "user1", "units": 1} for i in range(12)}
    estado = EstadoPartida(
        partida_id=1,
        fase_actual=FasePartida.REFUERZO,
        fin_fase_actual=datetime.now(timezone.utc),
        user_turno_actual="user1",
        mapa=mapa,
        jugadores={"user1": {"tropas_reserva": 5}} # Ya tenia 5
    )
    
    await asignar_tropas_reserva(estado, db)

    # 5 que tenia + 4 nuevas = 9
    assert estado.jugadores["user1"]["tropas_reserva"] == 9

@pytest.mark.asyncio
async def test_avanzar_fase_asigna_tropas(db: AsyncSession, monkeypatch):
    # Setup completo en BD
    user1 = User(username="u1", email="u1@test.com", passwd_hash="xxx")
    user2 = User(username="u2", email="u2@test.com", passwd_hash="xxx")
    db.add_all([user1, user2])
    await db.commit()

    partida = Partida(
        id=1,
        config_max_players=2,
        codigo_invitacion="TEST",
        creador="u1",
        estado=EstadosPartida.ACTIVA,
        config_timer_seconds=60
    )
    db.add(partida)
    await db.commit()

    jp1 = JugadoresPartida(usuario_id="u1", partida_id=1, turno=1)
    jp2 = JugadoresPartida(usuario_id="u2", partida_id=1, turno=2)
    db.add_all([jp1, jp2])
    
    # Estamos en FORTIFICACION, el siguiente es REFUERZO
    # Mapa: u2 tiene 9 territorios -> debe recibir 3 tropas al entrar en su turno
    mapa = {f"T{i}": {"owner_id": "u2", "units": 1} for i in range(9)}
    estado = EstadoPartida(
        partida_id=1,
        fase_actual=FasePartida.FORTIFICACION,
        fin_fase_actual=datetime.now(timezone.utc),
        user_turno_actual="u1", # Turno de u1 terminando
        mapa=mapa,
        jugadores={}
    )
    db.add(estado)
    await db.commit()

    # Mock del manager para evitar errores de broadcast
    async def mock_broadcast(msg, p_id): pass
    monkeypatch.setattr("app.core.ws_manager.manager.broadcast", mock_broadcast)

    # Act: Avanzamos de FORTIFICACION -> REFUERZO (cambio de turno a u2)
    await avanzar_fase(1, db)

    # Assert
    await db.refresh(estado)
    assert estado.fase_actual == FasePartida.REFUERZO
    assert estado.user_turno_actual == "u2"
    assert estado.jugadores["u2"]["tropas_reserva"] == 3
