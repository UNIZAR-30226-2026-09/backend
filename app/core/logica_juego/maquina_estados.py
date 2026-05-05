import asyncio
import math

from datetime import datetime, timedelta, timezone
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import flag_modified

from app.db.session import AsyncSessionLocal

from app.models.partida import EstadoPartida, FasePartida, JugadoresPartida, EstadoJugador, Partida, EstadosPartida
from app.core.ws_manager import manager
from app.crud.crud_partidas import actualizar_tropas_reserva, obtener_partida_por_id
from app.crud.crud_logs import registrar_log

from app.core.logica_juego.utils import obtener_territorios_jugador
from app.core.logica_juego.constantes import ARBOL_TECNOLOGICO, HABILIDADES

from app.core.logica_juego.config_ataques_especiales import TipoAtaque, TipoEfecto
from app.core.logica_juego.ataques_especiales import calcular_refuerzos_academia, calcular_robo_propaganda
from app.core.logica_juego.efectos_persistentes import procesar_efectos_fin_de_turno, procesar_efectos_inicio_turno
from app.core.logica_juego.victoria import resolver_eliminaciones

from app.core.map_state import game_map_state

from app.core.notifier import notifier
# Guarda las tareas para que Python no las borre por error
tareas_en_segundo_plano = set()
timers_por_partida: dict[int, asyncio.Task] = {}
votos_pausa: dict[int, dict[str, bool]] = {}

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

        actualizar_regiones_dominadas(estado, estado.user_turno_actual)

        await procesar_efectos_fin_de_turno(estado)

        estado.user_turno_actual = await calcular_siguiente_jugador(partida_id, estado.user_turno_actual, db)

        await procesar_efectos_inicio_turno(estado, estado.user_turno_actual)  

        # Comporbar si el tick de gripe avias / coronavirus elimino al jugador
        while len(obtener_territorios_jugador(estado.mapa, estado.user_turno_actual)) == 0:
            jugador_tick_id = estado.user_turno_actual
            ganador = await resolver_eliminaciones(
                db=db,
                partida_id=partida_id,
                defensores={jugador_tick_id},
                mapa=estado.mapa,
                turno_actual=estado.turno_actual,
                fase_actual=estado.fase_actual.value,
            )
            if ganador:
                return estado
            # Avanzar al siguiente jugador vivo (el muerto ya está marcado en BD)
            estado.user_turno_actual = await calcular_siguiente_jugador(partida_id, jugador_tick_id, db)
            await procesar_efectos_inicio_turno(estado, estado.user_turno_actual)
        
        # Verificamos fin de investigacion / trabajo en el inicio del turno
        await resolver_gestion_ronda(estado, estado.user_turno_actual)

        tropas_recibidas, motivo_refuerzos = await asignar_tropas_reserva(estado, db)

        estado.turno_actual += 1

        await registrar_log(
            db=db,
            partida_id=partida_id,
            turno_numero=estado.turno_actual,
            fase=FasePartida.REFUERZO.value,
            tipo_evento="CAMBIO_FASE",
            user=estado.user_turno_actual,
            datos={
                "turno_de": estado.user_turno_actual,
                "tropas_recibidas": tropas_recibidas,
                "motivo_refuerzos": motivo_refuerzos,
            },
        )
    
    
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

    # Si la fase nueva no es REFUERZO, mandamos el aviso al frontend.
    # (En REFUERZO ya se manda el aviso por dentro de asignar_tropas_reserva)
    if nueva_fase != FasePartida.REFUERZO:
        await notifier.enviar_cambio_fase(
            partida_id=partida_id,
            nueva_fase=nueva_fase.value,
            jugador_activo=estado.user_turno_actual,
            tropas_recibidas=0,
            motivo_refuerzos="normal",
            fin_fase_utc=estado.fin_fase_actual.isoformat()
        )
        
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
            partida = await obtener_partida_por_id(db_session, partida_id)

            if partida and partida.estado == EstadosPartida.PAUSADA:
                return

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
    Reglas:
    - Base: territorios / 3 (mínimo 3).
    - Bonus: Según el valor 'bonus_troops' definido en cada región si se posee entera.
    """
    jugador_id = estado.user_turno_actual
    estado.jugadores[jugador_id]["ha_fortificado"] = False
    estado.jugadores[jugador_id]["ha_lanzado_especial"] = False

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

        return 0, "sancion"

    territorios_propios = obtener_territorios_jugador(estado.mapa, estado.user_turno_actual)

    # Minimo le damos 3 en cada ronda    
    tropas_recibidas = max(3, len(territorios_propios) // 3)

    set_territorios_propios = set(territorios_propios) 
    bonus_regiones = 0

    for datos_region in game_map_state.regions.values():
        
        lista_comarcas_region = datos_region.get("comarcas", []) if isinstance(datos_region, dict) else datos_region.comarcas
        
        # Verificamos si el jugador posee todas las comarcas de esta región
        if all(territorio in set_territorios_propios for territorio in lista_comarcas_region):
            
            bonus = datos_region.get("bonus_troops", 0) if isinstance(datos_region, dict) else getattr(datos_region, "bonus_troops", 0)

            bonus_regiones += bonus
            
    # Añadimos el bonus al total de tropas base
    tropas_recibidas += bonus_regiones

    # Si tengo ACADEMIA_MILITAR, se me multiplican las tropas.
    if jugador.get("academia_activa"):
        motivo_especial = "academia"
        tropas_recibidas = calcular_refuerzos_academia(tropas_recibidas)

    tropas_recibidas, beneficiario_id, robadas = calcular_robo_propaganda(jugador, tropas_recibidas)

    if robadas > 0:
        motivo_especial = "propaganda"

        if beneficiario_id in estado.jugadores:

            await actualizar_tropas_reserva(db, estado, beneficiario_id, robadas)
        
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
        fin_fase_utc=estado.fin_fase_actual.isoformat()
    )

    return tropas_recibidas, motivo_especial

def actualizar_regiones_dominadas(estado: EstadoPartida, jugador_id: str):
    """Al final del turno, registra las regiones que el jugador controla completamente."""
    jugador = estado.jugadores.get(jugador_id, {})
    territorios_propios = set(obtener_territorios_jugador(estado.mapa, jugador_id))
    regiones_dominadas = jugador.get("regiones_dominadas", [])

    for region_id, datos_region in game_map_state.regions.items():
        comarcas_region = datos_region.comarcas if hasattr(datos_region, "comarcas") else datos_region.get("comarcas", [])
        if all(c in territorios_propios for c in comarcas_region) and region_id not in regiones_dominadas:
            regiones_dominadas.append(region_id)

    jugador["regiones_dominadas"] = regiones_dominadas


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
    habilidad_id = jugador.get("habilidad_investigando")
    if t_invest_id and habilidad_id and t_invest_id in estado.mapa:
        territorio_inv = estado.mapa[t_invest_id]

        # Si esta fatigado, sigue investigando, todavia no nos da la recompensa
        if territorio_esta_fatigado(territorio_inv):
            await notifier.enviar_evento_fatiga(estado.partida_id, user_id, t_invest_id, "investigando")
        
        else:
            nodo = ARBOL_TECNOLOGICO.get(habilidad_id, {})

            if habilidad_id not in jugador["tecnologias_predesbloqueadas"]:
                jugador["tecnologias_predesbloqueadas"].append(habilidad_id)
            
            techs_siguientes = nodo.get("desbloquea", [])
            
            # Liberamos el territorio
            estado.mapa[t_invest_id]["estado_bloqueo"] = None
            jugador["territorio_investigando"] = None
            jugador["habilidad_investigando"] = None

            info = HABILIDADES.get(habilidad_id, {})             
            await notifier.enviar_investigacion_completada(estado.partida_id, user_id, info.get("rama", ""), info.get("nivel", 0), t_invest_id, [habilidad_id], techs_siguientes)

            await notifier.enviar_actualizacion_territorio(estado.partida_id, t_invest_id, estado.mapa[t_invest_id])

    # Notificar a SQLAlchemy que el JSON ha cambiado
    flag_modified(estado, "jugadores")
    flag_modified(estado, "mapa")
