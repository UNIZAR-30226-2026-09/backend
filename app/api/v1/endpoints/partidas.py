from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import random
import string

from app.schemas.partida import PartidaCreate, PartidaRead, JugadorPartidaRead
from app.models.partida import Partida, EstadosPartida, TipoVisibilidad, JugadoresPartida, ColorJugador
from app.api.v1.endpoints.usuarios import obtener_usuario_actual
from app.models.usuario import User
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