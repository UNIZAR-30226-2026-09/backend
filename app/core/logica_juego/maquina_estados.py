import asyncio
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import AsyncSessionLocal

from app.models.partida import EstadoPartida, FasePartida, JugadoresPartida, EstadoJugador
from app.core.ws_manager import manager

# Guarda las tareas para que Python no las borre por error
tareas_en_segundo_plano = set()

TRANSICIONES = {
    FasePartida.REFUERZO: FasePartida.ATAQUE_CONVENCIONAL,
    FasePartida.ATAQUE_CONVENCIONAL: FasePartida.FORTIFICACION,
    FasePartida.FORTIFICACION: FasePartida.REFUERZO
}


async def avanzar_fase(
    partida_id: int,
    db: AsyncSession,
    fase_actual_solicitada: FasePartida | None = None
) -> EstadoPartida | None:
    """Avanza la partida a la siguiente fase y notifica a los jugadores."""
    query = (
        select(EstadoPartida)
        .options(selectinload(EstadoPartida.partida)) # Permite acceder al timer
        .where(EstadoPartida.partida_id == partida_id)
    )
    resultado = await db.execute(query)
    estado = resultado.scalar_one_or_none()
    if not estado or (fase_actual_solicitada and estado.fase_actual != fase_actual_solicitada):
        return None

    nueva_fase = TRANSICIONES[estado.fase_actual]

    # Cambio de jugador si se vuelve a Refuerzo
    if nueva_fase == FasePartida.REFUERZO:
        estado.user_turno_actual = await calcular_siguiente_jugador(partida_id, estado.user_turno_actual, db)

    # Actualizamos fase y tiempo límite
    temporizador = estado.partida.config_timer_seconds
    estado.fase_actual = nueva_fase
    estado.fin_fase_actual = datetime.now(timezone.utc) + timedelta(seconds=temporizador)
    await db.commit()

    # Notificación a front-end
    await manager.broadcast({
        "tipo_evento": "CAMBIO_FASE",
        "nueva_fase": nueva_fase.value,
        "jugador_activo": estado.user_turno_actual,
        "fin_fase_utc": estado.fin_fase_actual.isoformat()
    }, partida_id)

    # Lanzamos temporizador y lo guardamos a salvo
    tarea_timer = asyncio.create_task(iniciar_temporizador(partida_id, nueva_fase, estado.fin_fase_actual))
    tareas_en_segundo_plano.add(tarea_timer)
    tarea_timer.add_done_callback(tareas_en_segundo_plano.discard)
    
    return estado


async def iniciar_temporizador(partida_id: int, fase_vigente: FasePartida, tiempo_limite: datetime):
    """
    Espera en background hasta el tiempo límite y fuerza el cambio de fase
    si el jugador activo no lo hizo manualmente.
    """
    # Calculamos segundos restantes
    ahora = datetime.now(timezone.utc)
    segundos_espera = (tiempo_limite - ahora).total_seconds()
    if segundos_espera > 0:
        await asyncio.sleep(segundos_espera)

    # Abrimos sesión independiente y forzamos avance de fase
    try:
        async with AsyncSessionLocal() as db_session:
            await avanzar_fase(
                partida_id=partida_id,
                db=db_session,
                fase_actual_solicitada=fase_vigente
            )
    except Exception as e:
        # Log de errores de background
        print(f"[ERROR Timer Partida {partida_id}] Fallo al transicionar fase: {e}")


# -------------------------------------------------------------------------------------------------------
async def obtener_jugadores_partida(partida_id: int, db: AsyncSession) -> list[JugadoresPartida]:
    """Devuelve todos los jugadores de una partida ordenados por turno."""
    resultado = await db.execute(
        select(JugadoresPartida)
        .where(JugadoresPartida.partida_id == partida_id)
        .order_by(JugadoresPartida.turno.asc())
    )
    return resultado.scalars().all()


def indice_jugador_actual(jugadores: list[JugadoresPartida], jugador_actual: str) -> int:
    """Encuentra el índice del jugador actual en la lista."""
    return next((i for i, j in enumerate(jugadores) if j.usuario_id == jugador_actual), 0)


def siguiente_jugador_vivo(jugadores: list[JugadoresPartida], indice_actual: int) -> str:
    """Devuelve el usuario_id del siguiente jugador vivo usando round-robin."""
    total = len(jugadores)
    for offset in range(1, total + 1):
        candidato = jugadores[(indice_actual + offset) % total]
        if candidato.estado_jugador == EstadoJugador.VIVO:
            return candidato.usuario_id
    return jugadores[indice_actual].usuario_id  # fallback


async def calcular_siguiente_jugador(partida_id: int, jugador_actual: str, db: AsyncSession) -> str:
    """Función principal que devuelve el siguiente jugador vivo en turno."""
    jugadores = await obtener_jugadores_partida(partida_id, db)
    if not jugadores:
        return jugador_actual

    indice_actual = indice_jugador_actual(jugadores, jugador_actual)
    return siguiente_jugador_vivo(jugadores, indice_actual)