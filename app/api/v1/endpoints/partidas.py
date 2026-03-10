from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified

import asyncio
import random
import string
from datetime import datetime, timedelta, timezone

from app.core.ws_manager import manager
from app.core.logica_juego.maquina_estados import avanzar_fase, iniciar_temporizador
from app.core.logica_juego.inicializacion import generar_reparto_inicial
from app.core.map_state import game_map_state

from app.schemas.partida import PartidaCreate, PartidaRead, JugadorPartidaRead
from app.schemas.estado_juego import TerritorioBase, JugadorBase
from app.schemas.combate import MovimientoConquistaCreate


from app.models.partida import Partida, EstadoPartida, EstadosPartida, TipoVisibilidad, JugadoresPartida, ColorJugador, FasePartida
from app.models.usuario import User

from app.api.v1.endpoints.usuarios import obtener_usuario_actual
from app.db.session import get_db

router = APIRouter()

# Fabrica codigos de 6 letras/numeros al azar
def generar_codigo_invitacion():
    caracteres = string.ascii_uppercase + string.digits
    return ''.join(random.choices(caracteres, k=6))

# ----------------------------------------------------------------------------
# 1. CREAR PARTIDA
# ----------------------------------------------------------------------------
@router.post("", response_model=PartidaRead)
async def crear_partida(
    partida_in: PartidaCreate,
    usuario_actual: User = Depends(obtener_usuario_actual),
    db: AsyncSession = Depends(get_db)
):
    nuevo_codigo = generar_codigo_invitacion()
    
    nueva_partida = Partida(
        config_max_players=partida_in.config_max_players,
        config_visibility=partida_in.config_visibility,
        config_timer_seconds=partida_in.config_timer_seconds,
        codigo_invitacion=nuevo_codigo,
        estado=EstadosPartida.CREANDO
    )
    
    db.add(nueva_partida)
    await db.commit()
    await db.refresh(nueva_partida)
    
    # El que crea la sala entra automáticamente como el jugador 1 (Rojo)
    creador = JugadoresPartida(
        usuario_id=usuario_actual.username,
        partida_id=nueva_partida.id,
        turno=1,
        color=ColorJugador.ROJO
    )
    db.add(creador)
    await db.commit()
    
    return nueva_partida

# ----------------------------------------------------------------------------
# 2. LISTAR PARTIDAS PÚBLICAS
# ----------------------------------------------------------------------------
@router.get("", response_model=list[PartidaRead])
async def listar_partidas_publicas(
    usuario_actual: User = Depends(obtener_usuario_actual),
    db: AsyncSession = Depends(get_db)
):
    query = select(Partida).where(
        Partida.estado == EstadosPartida.CREANDO,
        Partida.config_visibility == TipoVisibilidad.PUBLICA
    )
    resultado = await db.execute(query)
    partidas = resultado.scalars().all()
    
    return partidas

# ----------------------------------------------------------------------------
# 3. UNIRSE A UNA PARTIDA
# ----------------------------------------------------------------------------
@router.post("/{codigo}/unirse", response_model=JugadorPartidaRead)
async def unirse_partida(
    codigo: str,
    usuario_actual: User = Depends(obtener_usuario_actual),
    db: AsyncSession = Depends(get_db)
):
    # Buscamos si existe la sala con ese codigo
    query = select(Partida).where(Partida.codigo_invitacion == codigo)
    resultado = await db.execute(query)
    partida = resultado.scalar_one_or_none()

    if not partida:
        raise HTTPException(status_code=404, detail="Ese código no existe, revisa bien")
    
    if partida.estado != EstadosPartida.CREANDO:
        raise HTTPException(status_code=400, detail="La partida ya ha empezado o está cerrada")

    # Miramos quién hay dentro ya
    query_jugadores = select(JugadoresPartida).where(JugadoresPartida.partida_id == partida.id)
    resultado_jugadores = await db.execute(query_jugadores)
    jugadores_actuales = resultado_jugadores.scalars().all()

    if len(jugadores_actuales) >= partida.config_max_players:
        raise HTTPException(status_code=400, detail="La sala está llena")

    # Por si el notas le da dos veces al boton de unirse
    for j in jugadores_actuales:
        if j.usuario_id == usuario_actual.username:
            raise HTTPException(status_code=400, detail="Ya estás dentro de esta partida")

    # Pillamos los colores que quedan libres para darle uno
    colores_usados = {j.color for j in jugadores_actuales}
    todos_colores = set(ColorJugador)
    colores_libres = list(todos_colores - colores_usados)
    
    nuevo_jugador = JugadoresPartida(
        usuario_id=usuario_actual.username,
        partida_id=partida.id,
        turno=len(jugadores_actuales) + 1,
        color=colores_libres[0]
    )

    db.add(nuevo_jugador)
    await db.commit()
    await db.refresh(nuevo_jugador)

    return nuevo_jugador

# ----------------------------------------------------------------------------
# . Iniciar partida
# ----------------------------------------------------------------------------

def obtener_lista_comarcas() -> list[str]:
    return list(game_map_state.comarcas.keys())

async def validar_partida_y_jugadores(partida_id: int, usuario_actual: User, db: AsyncSession) -> tuple[Partida, list[str]]:
    query = select(Partida).where(Partida.id == partida_id)
    resultado = await db.execute(query)
    partida = resultado.scalar_one_or_none()
    if not partida:
        raise HTTPException(status_code=404, detail="Partida no encontrada")
    if partida.estado != EstadosPartida.CREANDO:
        raise HTTPException(status_code=400, detail="La partida ya ha comenzado o ha finalizado")
    
    query_jugadores = select(JugadoresPartida).where(JugadoresPartida.partida_id == partida_id).order_by(JugadoresPartida.turno.asc())
    resultado_jugadores = await db.execute(query_jugadores)
    jugadores = resultado_jugadores.scalars().all()
    
    if len(jugadores) < 2:
        raise HTTPException(status_code=400, detail="Se necesitan al menos 2 jugadores para empezar")
    
    if usuario_actual.username not in [j.usuario_id for j in jugadores]:
        raise HTTPException(status_code=403, detail="No perteneces a esta partida")
    
    return partida, [j.usuario_id for j in jugadores]

def inicializar_estado_jugadores(jugadores_ids: list[str]) -> dict:
    return {j_id: {
        "tropas_pendientes_despliegue": 0,
        "movimiento_conquista_pendiente": False,
        "origen_conquista": None,
        "destino_conquista": None
    } for j_id in jugadores_ids}

async def notificar_inicio(partida_id: int, primer_jugador: str, tiempo_limite: datetime):
    evento_ws = {
        "tipo_evento": "PARTIDA_INICIADA",
        "partida_id": partida_id,
        "jugador_activo": primer_jugador,
        "fin_fase_utc": tiempo_limite.isoformat()
    }
    await manager.broadcast(evento_ws, partida_id)

@router.post("/{partida_id}/iniciar", status_code=status.HTTP_200_OK)
async def iniciar_partida(
    partida_id: int,
    usuario_actual: User = Depends(obtener_usuario_actual),
    db: AsyncSession = Depends(get_db)
):
    partida, jugadores_ids = await validar_partida_y_jugadores(partida_id, usuario_actual, db)
    lista_comarcas = obtener_lista_comarcas()
    mapa_inicial = generar_reparto_inicial(jugadores_ids, lista_comarcas)
    jugadores_estado_inicial = inicializar_estado_jugadores(jugadores_ids)

    jugador_inicial = jugadores_ids[0]
    tiempo_limite = datetime.now(timezone.utc) + timedelta(seconds=partida.config_timer_seconds)

    nuevo_estado = EstadoPartida(
        partida_id=partida_id,
        fase_actual=FasePartida.REFUERZO,
        fin_fase_actual=tiempo_limite,
        user_turno_actual=jugador_inicial,
        mapa=mapa_inicial,
        jugadores=jugadores_estado_inicial
    )

    partida.estado = EstadosPartida.ACTIVA
    db.add(nuevo_estado)
    await db.commit()

    await notificar_inicio(partida_id, jugador_inicial, tiempo_limite)
    asyncio.create_task(iniciar_temporizador(partida_id, FasePartida.REFUERZO, tiempo_limite))

    return {"mensaje": "Partida iniciada correctamente", "primer_jugador": jugador_inicial}

# ----------------------------------------------------------------------------
# . Si ya has hecho lo que tocaba en la fase, se avanza
# ----------------------------------------------------------------------------

@router.post("/{partida_id}/pasar_fase", status_code=status.HTTP_200_OK)
async def pasar_fase_manual(
    partida_id: int,
    usuario_actual: User = Depends(obtener_usuario_actual),
    db: AsyncSession = Depends(get_db)
):
    estado = await obtener_estado_partida(db, partida_id)

    if estado.user_turno_actual != usuario_actual.username:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No es tu turno. No puedes pasar de fase."
        )

    nuevo_estado = await avanzar_fase(
        partida_id=partida_id,
        db=db,
        fase_actual_solicitada=estado.fase_actual
    )

    if not nuevo_estado:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se pudo avanzar la fase (posible colisión con temporizador)."
        )

    return {
        "mensaje": "Fase avanzada correctamente",
        "nueva_fase": nuevo_estado.fase_actual.value,
        "jugador_activo": nuevo_estado.user_turno_actual,
        "fin_fase_utc": nuevo_estado.fin_fase_actual.isoformat()
    }


# ----------------------------------------------------------------------------
# . Mover tropas despues de conquista
# ----------------------------------------------------------------------------

def validar_turno_y_movimiento(estado_partida: EstadoPartida, jugador_id: str) -> JugadorBase:
    """Valida que sea el turno del jugador y que tenga un movimiento de conquista pendiente."""
    if estado_partida.user_turno_actual != jugador_id:
        raise HTTPException(status_code=403, detail="No es tu turno.")
    
    datos_jugador = estado_partida.jugadores.get(jugador_id, {})
    jugador_estado = JugadorBase(**datos_jugador)
    if not jugador_estado.movimiento_conquista_pendiente:
        raise HTTPException(status_code=400, detail="No tienes ningún movimiento de conquista pendiente.")
    
    return jugador_estado


def obtener_territorios_conquista(estado_partida: EstadoPartida, jugador_estado: JugadorBase) -> tuple[TerritorioBase, TerritorioBase, str, str]:
    """Recupera los territorios origen y destino de la conquista."""
    origen_id = jugador_estado.origen_conquista
    destino_id = jugador_estado.destino_conquista
    t_origen = TerritorioBase(**estado_partida.mapa[origen_id])
    t_destino = TerritorioBase(**estado_partida.mapa[destino_id])
    return t_origen, t_destino, origen_id, destino_id


def validar_y_aplicar_tropas(t_origen: TerritorioBase, t_destino: TerritorioBase, tropas: int):
    """Valida que se pueden mover las tropas y actualiza los territorios."""
    if tropas <= 0:
        return
    if t_origen.units - tropas < 1:
        raise HTTPException(status_code=400, detail="Debes dejar al menos 1 tropa en el territorio de origen.")
    t_origen.units -= tropas
    t_destino.units += tropas


def limpiar_estado_jugador(jugador_estado: JugadorBase):
    """Limpia el mini-bucle de movimiento de conquista."""
    jugador_estado.movimiento_conquista_pendiente = False
    jugador_estado.origen_conquista = None
    jugador_estado.destino_conquista = None

#! FUNCION DUPLICADA EN COMBATES Y PARTIDAS.PY (posible modularización ??)
async def obtener_estado_partida(db: AsyncSession, partida_id: int):
    query = select(EstadoPartida).where(EstadoPartida.partida_id == partida_id)
    resultado = await db.execute(query)
    estado = resultado.scalar_one_or_none()
    if not estado:
        raise HTTPException(404, "Estado de partida no encontrado")
    return estado

@router.post("/{partida_id}/mover_conquista", status_code=status.HTTP_200_OK)
async def mover_tropas_conquista(
    partida_id: int,
    movimiento_in: MovimientoConquistaCreate,
    usuario_actual: User = Depends(obtener_usuario_actual),
    db: AsyncSession = Depends(get_db)
):
    estado_partida = await obtener_estado_partida(db, partida_id)
    jugador_id = usuario_actual.username

    jugador_estado = validar_turno_y_movimiento(estado_partida, jugador_id)
    t_origen, t_destino, origen_id, destino_id = obtener_territorios_conquista(estado_partida, jugador_estado)

    validar_y_aplicar_tropas(t_origen, t_destino, movimiento_in.tropas_a_mover)
    limpiar_estado_jugador(jugador_estado)

    # Guardar cambios
    estado_partida.mapa[origen_id] = t_origen.model_dump()
    estado_partida.mapa[destino_id] = t_destino.model_dump()
    estado_partida.jugadores[jugador_id] = jugador_estado.model_dump()
    flag_modified(estado_partida, "mapa")
    flag_modified(estado_partida, "jugadores")
    await db.commit()

    # Notificar a los clientes
    evento_ws = {
        "tipo_evento": "MOVIMIENTO_CONQUISTA",
        "jugador_id": jugador_id,
        "origen_id": origen_id,
        "destino_id": destino_id,
        "tropas_movidas": movimiento_in.tropas_a_mover,
        "unidades_origen_final": t_origen.units,
        "unidades_destino_final": t_destino.units
    }
    await manager.broadcast(evento_ws, partida_id)

    return {"mensaje": "Movimiento completado con éxito", "tropas_movidas": movimiento_in.tropas_a_mover}