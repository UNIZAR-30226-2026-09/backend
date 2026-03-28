from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import Optional

from app.models.partida import (
    Partida,
    JugadoresPartida,
    EstadoPartida,
    EstadosPartida,
    TipoVisibilidad,
)
from app.schemas.partida import PartidaCreate


# ----------------------------------------------------------------------------
# 1. CREAR PARTIDA Y CREADOR
# ----------------------------------------------------------------------------
async def crear_partida_y_creador(
    db: AsyncSession, 
    partida_in: PartidaCreate, 
    codigo: str, 
    creador_username: str
) -> Partida:
    """
    Crea una nueva partida, hace commit, luego crea el JugadoresPartida 
    (turno 1, ColorJugador.ROJO), hace commit y devuelve la partida.
    
    Args:
        db: Sesión de base de datos
        partida_in: Datos de configuración de la partida
        codigo: Código de invitación generado
        creador_username: Username del usuario creador
        
    Returns:
        Objeto Partida creado y refrescado
    """
    nueva_partida = Partida(
        config_max_players=partida_in.config_max_players,
        config_visibility=partida_in.config_visibility,
        config_timer_seconds=partida_in.config_timer_seconds,
        codigo_invitacion=codigo,
        estado=EstadosPartida.CREANDO
    )
    
    db.add(nueva_partida)
    await db.commit()
    await db.refresh(nueva_partida)
    
    creador = JugadoresPartida(
        usuario_id=creador_username,
        partida_id=nueva_partida.id,
        turno=1,
    )
    db.add(creador)
    await db.commit()
    
    return nueva_partida

# ----------------------------------------------------------------------------
# 2. OBTENER PARTIDAS PÚBLICAS
# ----------------------------------------------------------------------------
async def obtener_partidas_publicas(db: AsyncSession) -> list[Partida]:
    """
    Devuelve la lista de partidas en estado CREANDO y visibilidad PUBLICA.
    
    Args:
        db: Sesión de base de datos
        
    Returns:
        Lista de partidas públicas disponibles
    """
    query = select(Partida).where(
        Partida.estado == EstadosPartida.CREANDO,
        Partida.config_visibility == TipoVisibilidad.PUBLICA
    )
    resultado = await db.execute(query)
    return resultado.scalars().all()

# ----------------------------------------------------------------------------
# 3. OBTENER PARTIDA POR CÓDIGO
# ----------------------------------------------------------------------------
async def obtener_partida_por_codigo(db: AsyncSession, codigo: str) -> Optional[Partida]:
    """
    Busca una partida por su código de invitación.
    
    Args:
        db: Sesión de base de datos
        codigo: Código de invitación de la partida
        
    Returns:
        Objeto Partida si existe, None en caso contrario
    """
    query = select(Partida).where(Partida.codigo_invitacion == codigo)
    resultado = await db.execute(query)
    return resultado.scalar_one_or_none()

# ----------------------------------------------------------------------------
# 4. OBTENER PARTIDA POR ID
# ----------------------------------------------------------------------------
async def obtener_partida_por_id(db: AsyncSession, partida_id: int) -> Optional[Partida]:
    """
    Busca una partida por su ID.
    
    Args:
        db: Sesión de base de datos
        partida_id: ID de la partida
        
    Returns:
        Objeto Partida si existe, None en caso contrario
    """
    query = select(Partida).where(Partida.id == partida_id)
    resultado = await db.execute(query)
    return resultado.scalar_one_or_none()

# ----------------------------------------------------------------------------
# 5. OBTENER JUGADORES DE UNA PARTIDA
# ----------------------------------------------------------------------------
async def obtener_jugadores_partida(db: AsyncSession, partida_id: int) -> list[JugadoresPartida]:
    """
    Devuelve la lista de jugadores de una partida, ordenados por turno ascendente.
    
    Args:
        db: Sesión de base de datos
        partida_id: ID de la partida
        
    Returns:
        Lista de jugadores ordenados por turno
    """
    query = select(JugadoresPartida).where(
        JugadoresPartida.partida_id == partida_id
    ).order_by(JugadoresPartida.turno.asc())
    
    resultado = await db.execute(query)
    return resultado.scalars().all()

# ----------------------------------------------------------------------------
# 6. UNIR JUGADOR A PARTIDA
# ----------------------------------------------------------------------------
async def unir_jugador(
    db: AsyncSession,
    username: str,
    partida_id: int,
    turno: int,
) -> JugadoresPartida:
    nuevo_jugador = JugadoresPartida(
        usuario_id=username,
        partida_id=partida_id,
        turno=turno,
    )

    db.add(nuevo_jugador)
    await db.commit()
    await db.refresh(nuevo_jugador)

    return nuevo_jugador

# ----------------------------------------------------------------------------
# 7. GUARDAR INICIO DE PARTIDA
# ----------------------------------------------------------------------------
async def guardar_inicio_partida(
    db: AsyncSession, 
    partida: Partida, 
    estado_tablero: EstadoPartida
) -> None:
    """
    Actualiza el estado de la partida a ACTIVA, añade el estado_tablero 
    a la base de datos y hace el commit.
    
    Args:
        db: Sesión de base de datos
        partida: Objeto Partida a actualizar
        estado_tablero: EstadoPartida a crear
        
    Returns:
        None
    """
    partida.estado = EstadosPartida.ACTIVA
    db.add(estado_tablero)
    await db.commit()

# ----------------------------------------------------------------------------
# 8. OBTENER ESTADO DE UNA PARTIDA
# ----------------------------------------------------------------------------
async def obtener_estado_partida(db: AsyncSession, partida_id: int) -> Optional[EstadoPartida]:
    """
    Busca el EstadoPartida por su partida_id.
    
    Args:
        db: Sesión de base de datos
        partida_id: ID de la partida
        
    Returns:
        Objeto EstadoPartida si existe, None en caso contrario
    """
    query = select(EstadoPartida).where(EstadoPartida.partida_id == partida_id)
    resultado = await db.execute(query)
    return resultado.scalar_one_or_none()


# ----------------------------------------------------------------------------
# 8. Eliminar a un judador de la partida
# ----------------------------
async def eliminar_jugador(db: AsyncSession, partida_id: int, username: str) -> None:
    await db.execute(
        delete(JugadoresPartida).where(
            JugadoresPartida.partida_id == partida_id,
            JugadoresPartida.usuario_id == username
        )
    )
    await db.commit()