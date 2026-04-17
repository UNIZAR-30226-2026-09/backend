import asyncio
import math

from datetime import datetime, timedelta, timezone
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import flag_modified

from app.db.session import AsyncSessionLocal

from app.models.partida import EstadoPartida, FasePartida, JugadoresPartida, EstadoJugador
from app.core.ws_manager import manager
from app.crud.crud_partidas import actualizar_tropas_reserva
from app.core.logica_juego.utils import obtener_territorios_jugador
from app.core.logica_juego.constantes import ARBOL_TECNOLOGICO

from app.core.logica_juego.config_ataques_especiales import TipoAtaque, TipoEfecto
from app.core.logica_juego.ataques_especiales import calcular_refuerzos_academia, calcular_robo_propaganda
from app.core.logica_juego.efectos_persistentes import procesar_efectos_fin_de_turno, procesar_efectos_inicio_turno

from app.core.notifier import notifier
# Guarda las tareas para que Python no las borre por error
tareas_en_segundo_plano = set()
timers_por_partida: dict[int, asyncio.Task] = {}

TRANSICIONES = {
    FasePartida.REFUERZO: FasePartida.GESTION,
    FasePartida.GESTION: FasePartida.ATAQUE_CONVENCIONAL,
    FasePartida.ATAQUE_CONVENCIONAL: FasePartida.ATAQUE_ESPECIAL,
    FasePartida.ATAQUE_ESPECIAL: FasePartida.FORTIFICACION,
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
        .options(selectinload(EstadoPartida.partida))
        .where(EstadoPartida.partida_id == partida_id)
    )
    resultado = await db.execute(query)
    estado = resultado.scalar_one_or_none()

    if not estado or (fase_actual_solicitada and estado.fase_actual != fase_actual_solicitada):
        return None

    jugador_actual = estado.jugadores.get(estado.user_turno_actual, {})
    if jugador_actual.get("movimiento_conquista_pendiente", False):
        raise ValueError("Debes reubicar tus tropas antes de pasar de fase.")

    nueva_fase = TRANSICIONES[estado.fase_actual]

    # Cambio de jugador si se vuelve a Refuerzo
    if nueva_fase == FasePartida.REFUERZO:

        await procesar_efectos_fin_de_turno(estado)

        estado.user_turno_actual = await calcular_siguiente_jugador(partida_id, estado.user_turno_actual, db)

        await procesar_efectos_inicio_turno(estado, estado.user_turno_actual)  

        await asignar_tropas_reserva(estado, db)
    
    elif nueva_fase == FasePartida.GESTION:
        # Se re suelve para el jugador que tiene el turno actualmente
        await resolver_gestion_ronda(estado, estado.user_turno_actual)
    
    
    # Actualizamos fase y tiempo límite
    temporizador = estado.partida.config_timer_seconds
    estado.fase_actual = nueva_fase
    estado.fin_fase_actual = datetime.now(timezone.utc) + timedelta(seconds=temporizador)
    await db.commit()

    timer_anterior = timers_por_partida.get(partida_id)
    if timer_anterior and not timer_anterior.done():
        timer_anterior.cancel()

    tarea_timer = asyncio.create_task(
        iniciar_temporizador(partida_id, nueva_fase, estado.fin_fase_actual)
    )
    timers_por_partida[partida_id] = tarea_timer
    tareas_en_segundo_plano.add(tarea_timer)
    tarea_timer.add_done_callback(tareas_en_segundo_plano.discard)

    return estado


async def iniciar_temporizador(partida_id: int, fase_vigente: FasePartida, tiempo_limite: datetime):
    """
    Espera en background hasta el tiempo límite y fuerza el cambio de fase
    si el jugador activo no lo hizo manualmente.
    """
    ahora = datetime.now(timezone.utc)
    segundos_espera = (tiempo_limite - ahora).total_seconds()
    if segundos_espera > 0:
        await asyncio.sleep(segundos_espera)

    try:
        async with AsyncSessionLocal() as db_session:
            await avanzar_fase(
                partida_id=partida_id,
                db=db_session,
                fase_actual_solicitada=fase_vigente
            )
    except asyncio.CancelledError:
        pass
    except Exception as e:
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

async def asignar_tropas_reserva(estado: EstadoPartida, db: AsyncSession) -> int:
    """
    Calcula y asigna las tropas de refuerzo a un jugador basándose en sus territorios.
    Regla: territorios / 3 (mínimo 3).
    """
    jugador_id = estado.user_turno_actual
    estado.jugadores[jugador_id]["ha_fortificado"] = False

    jugador = estado.jugadores.get(jugador_id, {})

    motivo_especial = "normal"

    # Si me han aplicado una SANCION, recibo 0 tropas
    efectos_jugador = jugador.get("efectos", [])
    if any(e.get("tipo_efecto") == TipoEfecto.SANCIONES for e in efectos_jugador):
        motivo_especial = "sancion"
        await actualizar_tropas_reserva(db, estado, jugador_id, 0)
        
        await notifier.enviar_cambio_fase(
            partida_id=estado.partida_id,
            nueva_fase=FasePartida.REFUERZO.value,
            jugador_activo=jugador_id,
            tropas_recibidas=0,
            motivo_refuerzos="sancion",
            fin_fase_utc=estado.fin_fase_actual.isoformat()
        )


        return 0


    territorios_propios = obtener_territorios_jugador(estado.mapa, estado.user_turno_actual)

    # Minimo le damos 3 en cada ronda    
    tropas_recibidas = max(3, len(territorios_propios) // 3)

    # Si tengo ACADEMIA_MILITAR, se me multiplican las tropas.
    if TipoAtaque.ACADEMIA_MILITAR in jugador.get("tecnologias_compradas", []):
        motivo_especial = "academia"
        tropas_recibidas = calcular_refuerzos_academia(tropas_recibidas)

    tropas_recibidas, beneficiario_id, robadas = calcular_robo_propaganda(jugador, tropas_recibidas)

    if robadas > 0:
        motivo_especial = "propaganda"

        if beneficiario_id in estado.jugadores:
            estado.jugadores[beneficiario_id]["tropas_reserva"] += robadas
            await actualizar_tropas_reserva(db, estado, beneficiario_id, estado.jugadores[beneficiario_id]["tropas_reserva"])
        
            await notifier.enviar_propaganda_activada(
                partida_id=estado.partida_id,
                victima_id=jugador_id,
                beneficiario_id=beneficiario_id,
                cantidad=robadas
            )
    
    await actualizar_tropas_reserva(db, estado, jugador_id, tropas_recibidas)
    
    await notifier.enviar_cambio_fase(
        partida_id=estado.partida_id,
        nueva_fase=FasePartida.REFUERZO.value,
        jugador_activo=jugador_id,
        tropas_recibidas=tropas_recibidas,
        motivo_refuerzos=motivo_especial,
    )

def territorio_esta_fatigado(territorio_data: dict) -> bool:
    """
    Devuelve si un terriorio tiene el efecto de FATIGA
    """

    return any(e.get("tipo_efecto") == TipoEfecto.FATIGA for e in territorio_data.get("efectos", []))

async def resolver_gestion_ronda(estado: EstadoPartida, user_id: str):
    """
    Se ejecuta al iniciar la fase de GESTIÓN. 
    Resuelve el trabajo e investigación pendientes del turno anterior.
    """
    jugador = estado.jugadores.get(user_id)
    if not jugador:
        return

    # RESOLVER TRABAJO (Dinero)
    t_trabajo_id = jugador.get("territorio_trabajando")
    if t_trabajo_id and t_trabajo_id in estado.mapa:

        territorio = estado.mapa[t_trabajo_id]

        # si esta fatigado, sigue trabajando y todavia no me da monedas
        if territorio_esta_fatigado(territorio):
            await notifier.enviar_evento_fatiga(estado.partida_id, user_id, t_trabajo_id, "trabajando")

        else:
            tropas = estado.mapa[t_trabajo_id]["units"]
            ganancia = tropas * 100  # Tu fórmula: tropas * 100
            jugador["monedas"] += ganancia
            
            # Liberamos el territorio
            estado.mapa[t_trabajo_id]["estado_bloqueo"] = None
            jugador["territorio_trabajando"] = None
            
            await notifier.enviar_trabajo_completado(estado.partida_id, user_id, t_trabajo_id, ganancia)
            await notifier.enviar_actualizacion_territorio(estado.partida_id, t_trabajo_id, estado.mapa[t_trabajo_id])


    # RESOLVER INVESTIGACIÓN (Predesbloqueo)
    t_invest_id = jugador.get("territorio_investigando")
    rama = jugador.get("rama_investigando")
    if t_invest_id and rama and t_invest_id in estado.mapa:
        territorio_inv = estado.mapa[t_invest_id]

        # Si esta fatigado, sigue investigando, todavia no nos da la recompensa
        if territorio_esta_fatigado(territorio_inv):
            await notifier.enviar_evento_fatiga(estado.partida_id, user_id, t_invest_id, "investigando")
        
        else:
            # Avanzamos el nivel en esa rama
            actual_nivel = jugador["nivel_ramas"].get(rama, 0)
            nuevo_nivel = actual_nivel + 1
            jugador["nivel_ramas"][rama] = nuevo_nivel
            
            # Predesbloqueamos las tecnologías de ese nivel
            techs_a_desbloquear = ARBOL_TECNOLOGICO.get(rama, {}).get(nuevo_nivel, [])
            for tech in techs_a_desbloquear:
                if tech not in jugador["tecnologias_predesbloqueadas"]:
                    jugador["tecnologias_predesbloqueadas"].append(tech)
            
            # Liberamos el territorio
            estado.mapa[t_invest_id]["estado_bloqueo"] = None
            jugador["territorio_investigando"] = None
            jugador["rama_investigando"] = None

            await notifier.enviar_investigacion_completada(estado.partida_id, user_id, rama, nuevo_nivel, t_invest_id, techs_a_desbloquear)
            await notifier.enviar_actualizacion_territorio(estado.partida_id, t_invest_id, estado.mapa[t_invest_id])

    # Notificar a SQLAlchemy que el JSON ha cambiado
    flag_modified(estado, "jugadores")
    flag_modified(estado, "mapa")
