from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified
from typing import Optional

from app.models.partida import EstadoPartida

# ----------------------------------------------------------------------------
# 1. OBTENER ESTADO DE UNA PARTIDA
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
# 2. GUARDAR ESTADO DE UNA PARTIDA
# ----------------------------------------------------------------------------
async def guardar_estado_partida(db: AsyncSession, estado_partida: EstadoPartida) -> None:
    """
    Marca los campos JSONB (mapa y jugadores) como modificados y hace commit.
    Esta función es necesaria porque SQLAlchemy no detecta automáticamente 
    cambios dentro de campos JSON.
    
    Args:
        db: Sesión de base de datos
        estado_partida: Objeto EstadoPartida a guardar
        
    Returns:
        None
    """
    flag_modified(estado_partida, "mapa")
    flag_modified(estado_partida, "jugadores")
    await db.commit()
